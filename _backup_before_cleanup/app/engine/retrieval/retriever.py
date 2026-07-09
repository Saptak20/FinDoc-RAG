from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.models import DocumentChunk, Document
from app.engine.generation.llm import get_embeddings
from app.core.logger import logger

async def retrieve_context(query: str, db: AsyncSession, limit: int = 5):
    """
    Given a query, embeds it using local Ollama model and retrieves the top similar chunks 
    from the PostgreSQL pgvector database.
    """
    try:
        embeddings = get_embeddings()
        # Embed the query
        query_vector = await embeddings.aembed_query(query)
        
        # Select matching chunks and load the associated Document metadata (filename)
        stmt = (
            select(DocumentChunk)
            .options(selectinload(DocumentChunk.document))
            .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
            .limit(limit)
        )
        
        result = await db.execute(stmt)
        chunks = result.scalars().all()
        
        # Format chunks as context
        context_items = []
        sources = []
        for chunk in chunks:
            source_info = chunk.document.filename if chunk.document else "Unknown"
            context_items.append(f"[Source: {source_info}]\n{chunk.content}")
            if source_info not in sources:
                sources.append(source_info)
                
        context = "\n\n---\n\n".join(context_items)
        return context, sources
    except Exception as e:
        logger.error(f"Error retrieving context: {e}")
        return "", []
