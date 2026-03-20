# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG-система (Retrieval-Augmented Generation) по **Градостроительному кодексу РФ**. FastAPI-бэкенд + vanilla HTML/CSS/JS фронтенд, запускается в Docker. FAISS-индекс (~140 чанков) построен заранее и хранится в `faiss_index/`.

## Commands

### Local development (Python 3.13, uv)
```bash
# Install dependencies
uv sync

# Run the API server (must be run from project root — FAISS path is relative)
# NOTE: `uvicorn` CLI fails on Windows when path contains spaces ("8. RAG") — use python -m instead:
.venv/Scripts/python.exe -m uvicorn app.api:app --reload --port 8001

# App opens at http://localhost:8001
```

### Dependencies
```bash
uv add <package>             # Add dependency (updates pyproject.toml + uv.lock)
```

## Environment

Requires a `.env` file in the project root:
```
OPENAI_API_KEY=...
BASE_URL=...     # Optional: custom OpenAI-compatible base URL (e.g. proxy)
```
- LLM: `gpt-4o-mini` (temperature=0, used for all pipeline nodes)
- Embeddings: `text-embedding-3-large`, cached in `./cache/` via `langchain_classic.storage.LocalFileStore`

## Architecture

### Request flow
```
Browser → GET /               → static/index.html
Browser → POST /api/chat      → LangGraph pipeline → JSON response
Browser → GET /api/article/{n}→ full article text from FAISS docstore
Browser → GET /api/health     → {"status": "ok"}
```

### LangGraph pipeline (`app/rag.py`) — 6 nodes
```
transform_query  → HyDE: LLM generates a hypothetical codex passage for embedding
retrieve         → Hybrid search using HyDE text as query
rerank           → LLM scores each doc 1–10, keeps top 5
generate         → Answer with mandatory [Статья N] inline citations
check_consistency→ LLM verifies claims, returns JSON {verified, unverified, score}
finalize         → Builds sources list [{article, title, excerpt}], appends disclaimer if score < 0.8
```
Graph is compiled with `MemorySaver`, supporting multi-turn conversations via `thread_id`.

### Retriever (`app/retriever.py`)
- All ~140 documents extracted from FAISS `InMemoryDocstore` at startup via `vs.docstore` + `vs.index_to_docstore_id`
- **BM25** built from extracted docs using a Russian tokenizer (`re.findall(r'[а-яёa-z\d]+', text.lower())`)
- **FAISS MMR** (`lambda_mult=0.6`, `k=10`, `fetch_k=20`) for semantic diversity
- Results merged via manual **Reciprocal Rank Fusion** (RRF, k=60) — `EnsembleRetriever` is not available in the installed langchain-community version
- `ARTICLES_BY_NUMBER: dict[str, Document]` — article number → Document, used by `/api/article/{n}`

### Critical behaviour: Статья 1 pinning
- **Статья 1** (definitions) is always prepended to context if not returned by search
- It is **excluded from LLM re-ranking** (pinned at top regardless of score)
- It is passed to the LLM **without any truncation** (`_smart_truncate` skipped for article "1")
- All other articles are truncated at 8000 chars (generation) / 2000 chars (reranking) at paragraph boundaries (`\n\n` split) to avoid cutting markdown tables

### Frontend (`static/index.html`)
Single-file vanilla HTML/CSS/JS. Uses `marked.js` (CDN) for markdown rendering.
- Citation chips `[Статья N]` call `openArticleFromCitation(num)` → opens article modal + highlights matching excerpt via `TreeWalker` DOM search
- `lastSources` global caches the last API response's `sources` array for citation chip → excerpt lookup
- Consistency badge: ✓ ≥80%, ~ ≥50%, ! <50%

### Module imports
All Python modules are in the `app/` package and use **relative imports** (`from .rag import`, `from .llms import`, etc.). `uvicorn` must be invoked as `uvicorn app.api:app` from the project root.

## Key constraints

- **FAISS index path** (`"faiss_index"`) and **embedding cache** (`"./cache/"`) are resolved relative to the working directory — always run `uvicorn` / `docker compose` from the project root.
- `app/api.py` resolves the static dir as `Path(__file__).parent.parent / "static"` (two levels up from `app/api.py`).
- Use `langchain_classic` (not `langchain`) for `LocalFileStore` and `CacheBackedEmbeddings` — this is intentional.
- `BM25Retriever` must be called with `.invoke()`, not the deprecated `.get_relevant_documents()`.
