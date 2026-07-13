import json
import os
from typing import List

from langchain_core.documents import Document

from app.core.config import settings
from app.core.logger import logger


class ChunkStore:
    """
    Persist and load the canonical document chunk corpus.

    The chunk corpus is stored as JSONL:
    one JSON object per line, one object per chunk.
    """

    def __init__(
        self,
        persist_dir: str | None = None,
        filename: str = "chunks.jsonl",
    ):
        self.persist_dir = (
            persist_dir or settings.VECTOR_STORE_PATH
        )

        self.filename = filename

        self.file_path = os.path.join(
            self.persist_dir,
            self.filename,
        )

    def save_chunks(
        self,
        chunks: List[Document],
    ) -> None:
        """Persist document chunks to the JSONL corpus."""

        if not chunks:
            raise ValueError(
                "Cannot save an empty chunk list."
            )

        os.makedirs(
            self.persist_dir,
            exist_ok=True,
        )

        logger.info(
            f"Saving {len(chunks)} chunks to: {self.file_path}"
        )

        seen_chunk_ids = set()

        with open(
            self.file_path,
            "w",
            encoding="utf-8",
        ) as file:
            for chunk in chunks:
                chunk_id = chunk.metadata.get("chunk_id")

                if not chunk_id:
                    raise ValueError(
                        "Cannot save chunk without 'chunk_id' metadata."
                    )

                if chunk_id in seen_chunk_ids:
                    raise ValueError(
                        f"Duplicate chunk ID detected: {chunk_id}"
                    )

                seen_chunk_ids.add(chunk_id)

                record = {
                    "chunk_id": chunk_id,
                    "page_content": chunk.page_content,
                    "metadata": chunk.metadata,
                }

                file.write(
                    json.dumps(
                        record,
                        ensure_ascii=False,
                    )
                )

                file.write("\n")

        logger.info(
            f"Successfully saved {len(chunks)} chunks."
        )

    def load_chunks(self) -> List[Document]:
        """Load the persisted JSONL corpus as LangChain Documents."""

        if not os.path.exists(self.file_path):
            raise FileNotFoundError(
                f"Chunk corpus not found: {self.file_path}"
            )

        logger.info(
            f"Loading chunk corpus from: {self.file_path}"
        )

        chunks = []
        seen_chunk_ids = set()

        with open(
            self.file_path,
            "r",
            encoding="utf-8",
        ) as file:
            for line_number, line in enumerate(
                file,
                start=1,
            ):
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)

                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"Invalid JSON at line {line_number}."
                    ) from error

                page_content = record.get("page_content")
                metadata = record.get("metadata")
                chunk_id = record.get("chunk_id")

                if not isinstance(page_content, str):
                    raise ValueError(
                        f"Invalid page_content at line {line_number}."
                    )

                if not isinstance(metadata, dict):
                    raise ValueError(
                        f"Invalid metadata at line {line_number}."
                    )

                if not chunk_id:
                    raise ValueError(
                        f"Missing chunk_id at line {line_number}."
                    )

                if metadata.get("chunk_id") != chunk_id:
                    raise ValueError(
                        f"Chunk ID mismatch at line {line_number}."
                    )

                if chunk_id in seen_chunk_ids:
                    raise ValueError(
                        f"Duplicate chunk ID at line {line_number}: "
                        f"{chunk_id}"
                    )

                seen_chunk_ids.add(chunk_id)

                chunks.append(
                    Document(
                        page_content=page_content,
                        metadata=metadata,
                    )
                )

        if not chunks:
            raise ValueError(
                "Loaded chunk corpus is empty."
            )

        logger.info(
            f"Successfully loaded {len(chunks)} chunks."
        )

        return chunks