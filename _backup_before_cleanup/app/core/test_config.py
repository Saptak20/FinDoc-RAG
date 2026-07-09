from app.core.config import settings 
from app.core.logger import get_logger 

logger = get_logger("TestModule")

if __name__ == "__main__":
    logger.info(f"Successfully booted: {settings.APP_NAME}")
    logger.info(f"Targeting Local LLM: {settings.LLM_MODEL}")
    logger.debug("This will only print if DEBUG=True")

    