from functools import lru_cache

from app.engine.pipelines import RAGPipeline


@lru_cache(maxsize=1)
def get_rag_pipeline() -> RAGPipeline:
    """
    Singleton dependency providing the initialized LangGraph RAG pipeline.
    The models (FAISS, BM25, CrossEncoder, ChatOllama) are loaded once and reused.
    """
    return RAGPipeline()
