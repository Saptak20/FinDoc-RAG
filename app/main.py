from fastapi import FastAPI

from app.api.routes.chat import router as chat_router
from app.core.config import settings
from app.core.logger import logger

app = FastAPI(
    title=settings.APP_NAME,
    description="Production-oriented local-first Hybrid RAG API for financial documents.",
    version="1.0.0",
    debug=settings.DEBUG,
)


@app.on_event("startup")
async def startup_event():
    logger.info(
        f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode"
    )


# Register API routes
app.include_router(chat_router, prefix="/api/v1")


@app.get("/", tags=["system"])
def read_root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "environment": settings.APP_ENV,
        "status": "running",
    }


@app.get("/health", tags=["system"])
def health_check():
    return {
        "status": "healthy",
        "application": settings.APP_NAME,
    }