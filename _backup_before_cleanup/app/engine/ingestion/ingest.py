import io
from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Document, DocumentChunk
from app.engine.generation.llm import get_embeddings
from app.core.logger import logger

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
    """
    Split text into overlapping chunks.
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - chunk_overlap
    return chunks

async def ingest_document(filename: str, file_bytes: bytes, db: AsyncSession) -> Document:
    """
    Ingest a PDF or text file, extract content, generate embeddings locally using Ollama, 
    and store them in PostgreSQL.
    """
    logger.info(f"Starting ingestion for file: {filename}")
    
    # 1. Extract text
    text_content = ""
    if filename.lower().endswith(".pdf"):
        pdf_file = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_file)
        for page in reader.pages:
            text_content += page.extract_text() or ""
    else:
        # Treat as plain text
        text_content = file_bytes.decode("utf-8", errors="ignore")
        
    if not text_content.strip():
        raise ValueError("Could not extract any text from the document.")

    # 2. Create parent Document in database
    db_doc = Document(filename=filename, content=text_content)
    db.add(db_doc)

    
    await db.flush()  # Populates db_doc.id
    
    # 3. Chunk the text
    chunks = chunk_text(text_content)
    logger.info(f"Split {filename} into {len(chunks)} chunks.")
    
    # 4. Generate embeddings and save chunks
    embeddings_service = get_embeddings()
    
    # We can embed them sequentially or in batches.
    # To avoid overloading local Ollama, we can do it sequentially or chunk batches.
    chunk_embeddings = await embeddings_service.aembed_documents(chunks)
    
    for idx, (chunk_text_content, emb) in enumerate(zip(chunks, chunk_embeddings)):
        db_chunk = DocumentChunk(
            document_id=db_doc.id,
            chunk_index=idx,
            content=chunk_text_content,
            embedding=emb
        )
        db.add(db_chunk)
        
    await db.commit()
    logger.info(f"Successfully ingested {filename} with ID {db_doc.id}")
    return db_doc
