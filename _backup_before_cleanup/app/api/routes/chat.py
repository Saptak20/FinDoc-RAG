from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.engine.pipelines import create_rag_graph
from app.core.logger import logger

router = APIRouter()

@router.post("/", response_model=ChatResponse)
async def chat_interaction(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    RAG Chat endpoint. Searches the pgvector database for similar financial chunks
    and uses the local Ollama LLM to answer the question.
    """
    try:
        # Compile our RAG graph
        app_graph = create_rag_graph(db)
        
        # Build initial state
        initial_state = {
            "question": request.message,
            "context": "",
            "sources": [],
            "response": ""
        }
        
        # Execute the graph
        result = await app_graph.ainvoke(initial_state)
        
        return ChatResponse(
            response=result["response"],
            sources=result["sources"]
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process chat: {str(e)}")
