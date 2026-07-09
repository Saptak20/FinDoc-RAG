import os
from typing import List

from langchain_core.documents import Document
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS

from app.core.config import settings
from app.core.logger import logger


class SECIngestor:
    def __init__(
        self,
        data_dir: str | None = None,
        persist_dir: str | None = None,
    ):
        self.data_dir = data_dir or settings.RAW_DATA_PATH
        self.persist_dir = persist_dir or settings.VECTOR_STORE_PATH

        self.embeddings = OllamaEmbeddings(
            model=settings.EMBEDDING_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )

    def load_documents(self) -> List[Document]:
        """Load all PDF documents from the raw data directory."""

        logger.info(f"Loading PDF documents from: {self.data_dir}")

        if not os.path.exists(self.data_dir):
            raise FileNotFoundError(
                f"Raw data directory does not exist: {self.data_dir}"
            )

        loader = DirectoryLoader(
            path=self.data_dir,
            glob="**/*.pdf",
            loader_cls=PyPDFLoader,
            show_progress=True,
            use_multithreading=True,
        )

        documents = loader.load()

        if not documents:
            raise ValueError(
                f"No PDF documents found in: {self.data_dir}"
            )

        logger.info(
            f"Loaded {len(documents)} document pages."
        )

        return documents

    def chunk_documents(
        self,
        documents: List[Document],
    ) -> List[Document]:
        """Split loaded PDF pages into overlapping text chunks."""

        if not documents:
            raise ValueError("Cannot chunk an empty document list.")

        logger.info(
            f"Chunking {len(documents)} document pages."
        )

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
            separators=[
                "\n\n",
                "\n",
                ". ",
                " ",
                "",
            ],
        )

        chunks = text_splitter.split_documents(documents)

        if not chunks:
            raise ValueError("No chunks were generated.")

        logger.info(
            f"Generated {len(chunks)} chunks."
        )

        return chunks

    def build_vector_store(
        self,
        chunks: List[Document],
    ) -> FAISS:
        """Embed document chunks, build a FAISS index, and persist it."""

        if not chunks:
            raise ValueError(
                "Cannot build a vector store from an empty chunk list."
            )

        logger.info(
            f"Building FAISS vector store from {len(chunks)} chunks."
        )

        os.makedirs(
            self.persist_dir,
            exist_ok=True,
        )

        vector_store = FAISS.from_documents(
            documents=chunks,
            embedding=self.embeddings,
        )

        vector_store.save_local(
            self.persist_dir
        )

        logger.info(
            f"FAISS vector store saved to: {self.persist_dir}"
        )

        return vector_store


if __name__ == "__main__":
    ingestor = SECIngestor()

    documents = ingestor.load_documents()

    chunks = ingestor.chunk_documents(documents)

    ingestor.build_vector_store(chunks)

    logger.info("Ingestion pipeline completed successfully.")