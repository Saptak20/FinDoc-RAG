from typing import Optional

from langchain_ollama import ChatOllama

from app.core.config import settings
from app.core.logger import logger


def get_llm(
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.0,
) -> ChatOllama:
    """
    Initialize and return a ChatOllama instance using configured application settings.
    """
    model_name = model or settings.LLM_MODEL
    api_base_url = base_url or settings.OLLAMA_BASE_URL

    logger.info(
        f"Initializing ChatOllama with model '{model_name}' at '{api_base_url}' (temperature={temperature})."
    )

    return ChatOllama(
        model=model_name,
        base_url=api_base_url,
        temperature=temperature,
    )
