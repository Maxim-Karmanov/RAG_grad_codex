import logging
import os
import pathlib
import tempfile
from typing import Any
from langchain_core.documents import Document
from langchain_community.document_loaders import TextLoader

logging.basicConfig(level=logging.INFO, encoding="utf-8")
LOGGER = logging.getLogger(__name__)


class DocumentLoaderException(Exception):
    pass


class DocumentLoader(object):
    supported_extensions = {
        ".txt": TextLoader,
    }


def load_document(temp_filepath: str) -> list[Document]:
    """Load a file and return it as a list of documents.
    Doesn't handle a lot of errors at the moment.
    """
    ext = pathlib.Path(temp_filepath).suffix
    loader = DocumentLoader.supported_extensions.get(ext)
    if not loader:
        raise DocumentLoaderException(
            f"Invalid extension type {ext}, cannot load this type of file"
        )
    loaded = loader(temp_filepath)
    docs = loaded.load()
    logging.info(docs)
    return docs
