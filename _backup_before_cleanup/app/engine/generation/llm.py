from langchain_ollama import ChatOllama, OllamaEmbeddings
from app.core.config import settings

def get_llm():
    """
    Initialize and return ChatOllama LLM configured for local model.
    """
    return ChatOllama(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_LLM_MODEL,
        temperature=0.2,
        # We can increase context window if needed, e.g. num_ctx=8192
        num_ctx=8192
    )

def get_embeddings():
    """
    Initialize and return OllamaEmbeddings configured for local nomic-embed-text.
    """
    return OllamaEmbeddings(
        base_url=settings.OLLAMA_BASE_URL,
        model=settings.OLLAMA_EMBED_MODEL
    )
