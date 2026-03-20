import re
from typing import List

from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from .llms import EMBEDDINGS

# ---------------------------------------------------------------------------
# Load the pre-built FAISS index
# ---------------------------------------------------------------------------
vector_store = FAISS.load_local(
    "faiss_index", EMBEDDINGS, allow_dangerous_deserialization=True
)


# ---------------------------------------------------------------------------
# Extract all documents from the FAISS docstore for BM25
# ---------------------------------------------------------------------------
def _get_all_docs_from_faiss(vs: FAISS) -> List[Document]:
    """Extract all documents from a FAISS InMemoryDocstore."""
    docstore = vs.docstore
    index_to_id = vs.index_to_docstore_id
    docs = []
    for idx in sorted(index_to_id.keys()):
        doc_id = index_to_id[idx]
        doc = docstore.search(doc_id)
        if isinstance(doc, Document):
            docs.append(doc)
    return docs


def _russian_tokenizer(text: str) -> List[str]:
    """Tokenize Russian text: lowercase, keep Cyrillic/Latin/digits."""
    tokens = re.findall(r'[а-яёa-z\d]+', text.lower())
    return tokens if tokens else text.split()


ALL_DOCS: List[Document] = _get_all_docs_from_faiss(vector_store)

# Словарь статей по номеру — для API-эндпоинта полного просмотра
ARTICLES_BY_NUMBER: dict[str, Document] = {}
for _doc in ALL_DOCS:
    _raw = _doc.metadata.get("Статья", "")
    _m = re.search(r'(\d+(?:\.\d+)?)', _raw)
    if _m:
        ARTICLES_BY_NUMBER[_m.group(1)] = _doc

bm25_retriever = BM25Retriever.from_documents(
    ALL_DOCS,
    preprocess_func=_russian_tokenizer,
    k=10,
)


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------
def _reciprocal_rank_fusion(
    ranked_lists: List[List[Document]],
    k: int = 60,
) -> List[Document]:
    """Merge multiple ranked document lists using RRF scoring."""
    scores: dict[str, float] = {}
    doc_map: dict[str, Document] = {}

    for ranked_list in ranked_lists:
        for rank, doc in enumerate(ranked_list):
            key = doc.page_content[:200]
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            doc_map[key] = doc

    sorted_keys = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [doc_map[kk] for kk in sorted_keys]


# ---------------------------------------------------------------------------
# Public retriever function
# ---------------------------------------------------------------------------
def hybrid_retrieve(query: str, k_final: int = 10) -> List[Document]:
    """
    Hybrid retrieval: BM25 + FAISS MMR merged via Reciprocal Rank Fusion.

    Args:
        query: Search query (typically the HyDE-generated hypothetical document).
        k_final: Number of documents to return after fusion.

    Returns:
        Deduplicated, RRF-merged list of Documents.
    """
    # FAISS MMR for semantic search with diversity
    faiss_docs = vector_store.max_marginal_relevance_search(
        query=query,
        k=10,
        fetch_k=20,
        lambda_mult=0.6,  # 0=max diversity, 1=max relevance
    )

    # BM25 keyword search
    bm25_docs = bm25_retriever.invoke(query)

    # Merge via Reciprocal Rank Fusion
    merged = _reciprocal_rank_fusion([faiss_docs, bm25_docs])
    return merged[:k_final]
