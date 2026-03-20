"""Loading LLMs and Embeddings."""

from langchain_classic.storage import LocalFileStore
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_classic.embeddings import CacheBackedEmbeddings
import dotenv
import os

dotenv.load_dotenv()

BASE_URL = os.getenv("BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

chat_model = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    base_url=BASE_URL,
    api_key=OPENAI_API_KEY,
)

store = LocalFileStore("./cache/")

underlying_embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    base_url=BASE_URL,
    api_key=OPENAI_API_KEY,
)

# Кэширование эмбеддингов
EMBEDDINGS = CacheBackedEmbeddings.from_bytes_store(
    underlying_embeddings, store, namespace=underlying_embeddings.model
)
