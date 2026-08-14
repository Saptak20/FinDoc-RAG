import time
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_rag_pipeline
from app.core.logger import logger
from app.engine.pipelines import RAGPipeline
from app.schemas.chat import ChatMetrics, ChatRequest, ChatResponse, SourceItem

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question about financial documents",
    description="Executes hybrid retrieval (FAISS + BM25), Cross-Encoder reranking, and local Ollama generation using LangGraph.",
)
async def chat_endpoint(
    request: ChatRequest,
    pipeline: RAGPipeline = Depends(get_rag_pipeline),
) -> ChatResponse:
    """
    Process a financial query through the LangGraph RAG pipeline.
    """
    if not request.query or not request.query.strip():
        logger.warning("Empty or whitespace query received in /chat endpoint.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty or contain only whitespace.",
        )

    logger.info(f"Received API chat request: {request.query!r}")

    start_time = time.perf_counter()

    try:
        result = pipeline.invoke(
            query=request.query,
            dense_top_k=request.dense_top_k,
            sparse_top_k=request.sparse_top_k,
            final_top_k=request.final_top_k,
        )
    except Exception as exc:
        logger.exception(f"Unhandled error during RAG pipeline execution: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the financial query.",
        )

    latency = time.perf_counter() - start_time

    if result.get("error") and not result.get("answer"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error"),
        )

    sources = [
        SourceItem(
            source=src.get("filename", "unknown"),
            page=src.get("page", 0),
            chunk_id=src.get("chunk_id", ""),
            rerank_score=src.get("rerank_score"),
            rrf_score=src.get("rrf_score"),
        )
        for src in result.get("sources", [])
    ]

    metrics = ChatMetrics(
        retrieval_candidates=len(result.get("retrieval_results", [])),
        reranked_chunks=len(result.get("reranked_results", [])),
        latency_seconds=round(latency, 3),
    )

    logger.info(
        f"Chat request completed in {latency:.2f}s | "
        f"candidates={metrics.retrieval_candidates}, "
        f"reranked={metrics.reranked_chunks}"
    )

    return ChatResponse(
        query=request.query,
        answer=result.get("answer", ""),
        sources=sources,
        metrics=metrics,
    )
