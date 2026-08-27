from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
from sqlalchemy import text

from app.api.dependencies import get_rag_pipeline
from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router
from app.core.config import settings
from app.core.logger import logger, request_id_ctx
from app.core.middleware import RequestCorrelationMiddleware
from app.db.session import AsyncSessionLocal, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifespan management."""
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode...")

    # Initialize database tables
    await init_db()

    # Pre-warm RAG pipeline singleton (loads FAISS, BM25, CrossEncoder, ChatOllama)
    try:
        get_rag_pipeline()
        logger.info("RAG Pipeline and models pre-warmed successfully.")
    except Exception as exc:
        logger.warning(f"RAG Pipeline pre-warm encountered notice: {exc}")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Production-oriented local-first Hybrid RAG API for financial documents.",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# 1. Add Request Correlation and Security Headers Middleware
app.add_middleware(RequestCorrelationMiddleware)

# 2. Hardened CORS Configuration
cors_origins = settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Retry-After"],
)

# 3. Global Unhandled Exception Handler (Security: Never leak stack traces)
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", request_id_ctx.get() or "unknown")
    logger.exception(f"Unhandled server exception [request_id={req_id}]: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred while processing the request.",
            "request_id": req_id,
        },
        headers={"X-Request-ID": req_id},
    )


# Register API routes
app.include_router(chat_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")


@app.get("/", tags=["system"])
def read_root():
    """Root endpoint returning basic service metadata."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "environment": settings.APP_ENV,
        "status": "running",
    }


@app.get("/health", tags=["system"])
def health_check():
    """Lightweight liveness probe verifying process health."""
    return {
        "status": "healthy",
        "application": settings.APP_NAME,
        "environment": settings.APP_ENV,
    }


@app.get("/ready", tags=["system"])
async def readiness_check(response: Response):
    """
    Readiness probe verifying availability of local storage, vector artifacts, database, and Ollama.
    """
    checks = {}
    is_ready = True

    # 1. Check FAISS Index and Canonical Corpus files
    faiss_path = os.path.join(settings.VECTOR_STORE_PATH, "index.faiss")
    corpus_path = os.path.join(settings.VECTOR_STORE_PATH, "chunks.jsonl")

    checks["faiss_index"] = os.path.exists(faiss_path)
    checks["chunk_corpus"] = os.path.exists(corpus_path)

    if not checks["faiss_index"] or not checks["chunk_corpus"]:
        is_ready = False

    # 2. Check Database Connectivity
    db_ok = False
    try:
        async with AsyncSessionLocal() as session:
            res = await session.execute(text("SELECT 1"))
            if res.scalar() == 1:
                db_ok = True
    except Exception as db_exc:
        logger.warning(f"Database readiness check failed: {db_exc}")
        db_ok = False

    checks["database"] = db_ok
    if not db_ok:
        is_ready = False

    # 3. Check Ollama Connectivity
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code == 200:
                ollama_ok = True
    except Exception:
        ollama_ok = False

    checks["ollama_service"] = ollama_ok
    if not ollama_ok:
        is_ready = False

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "checks": checks,
            "application": settings.APP_NAME,
        }

    return {
        "status": "ready",
        "checks": checks,
        "application": settings.APP_NAME,
    }