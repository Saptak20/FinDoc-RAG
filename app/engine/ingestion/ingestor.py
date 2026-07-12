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
        """
        Initialize the SEC document ingestion pipeline.

        The ingestor uses:

        - Local PDF documents
        - Recursive text chunking
        - Ollama embeddings
        - FAISS vector storage
        """

        self.data_dir = data_dir or settings.RAW_DATA_PATH
        self.persist_dir = persist_dir or settings.VECTOR_STORE_PATH

        self.embeddings = OllamaEmbeddings(
            model=settings.EMBEDDING_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
        )

    def load_documents(self) -> List[Document]:
        """
        Load all PDF documents from the raw data directory.

        Each PDF page is returned as a LangChain Document object.
        """

        logger.info(
            f"Loading PDF documents from: {self.data_dir}"
        )

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
        """
        Split loaded PDF pages into overlapping text chunks.

        Chunk size and overlap are controlled through application settings.
        """

        if not documents:
            raise ValueError(
                "Cannot chunk an empty document list."
            )

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
            raise ValueError(
                "No chunks were generated."
            )

        logger.info(
            f"Generated {len(chunks)} chunks."
        )

        return chunks

    def build_vector_store(
        self,
        chunks: List[Document],
        batch_size: int = 32,
    ) -> FAISS:
        """
        Embed document chunks in controlled batches,
        incrementally build a FAISS index,
        and persist the completed index locally.

        Batching prevents sending the entire document corpus
        to Ollama in one embedding request.
        """

        if not chunks:
            raise ValueError(
                "Cannot build a vector store from an empty chunk list."
            )

        if batch_size <= 0:
            raise ValueError(
                "batch_size must be greater than zero."
            )

        total_chunks = len(chunks)

        total_batches = (
            total_chunks + batch_size - 1
        ) // batch_size

        logger.info(
            f"Building FAISS vector store from {total_chunks} chunks "
            f"using batch size {batch_size}."
        )

        logger.info(
            f"Total embedding batches: {total_batches}."
        )

        os.makedirs(
            self.persist_dir,
            exist_ok=True,
        )

        vector_store = None

        for batch_number, start_index in enumerate(
            range(0, total_chunks, batch_size),
            start=1,
        ):
            end_index = min(
                start_index + batch_size,
                total_chunks,
            )

            batch = chunks[start_index:end_index]

            logger.info(
                f"Embedding batch "
                f"{batch_number}/{total_batches} "
                f"| chunks {start_index + 1}-{end_index} "
                f"| batch size {len(batch)}."
            )

            if vector_store is None:

                # First batch creates the FAISS index.

                vector_store = FAISS.from_documents(
                    documents=batch,
                    embedding=self.embeddings,
                )

            else:

                # Remaining batches are embedded and
                # incrementally added to the existing index.

                vector_store.add_documents(
                    documents=batch,
                )

            logger.info(
                f"FAISS vectors indexed: "
                f"{vector_store.index.ntotal}/{total_chunks}"
            )

        if vector_store is None:
            raise RuntimeError(
                "FAISS vector store creation failed."
            )

        if vector_store.index.ntotal != total_chunks:
            raise RuntimeError(
                f"FAISS vector count mismatch. "
                f"Expected {total_chunks}, "
                f"found {vector_store.index.ntotal}."
            )

        logger.info(
            "All embedding batches processed successfully."
        )

        logger.info(
            f"Saving FAISS vector store to: {self.persist_dir}"
        )

        vector_store.save_local(
            self.persist_dir
        )

        logger.info(
            f"FAISS vector store saved successfully."
        )

        logger.info(
            f"Total vectors stored: {vector_store.index.ntotal}"
        )

        return vector_store


if __name__ == "__main__":

    logger.info(
        "Starting standalone ingestion pipeline."
    )

    ingestor = SECIngestor()

    documents = ingestor.load_documents()

    chunks = ingestor.chunk_documents(documents)

    vector_store = ingestor.build_vector_store(
        chunks=chunks,
        batch_size=32,
    )

    logger.info(
        f"Ingestion pipeline completed successfully. "
        f"Total vectors indexed: {vector_store.index.ntotal}"
    )