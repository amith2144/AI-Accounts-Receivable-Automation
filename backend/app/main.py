import logging
import uuid
from typing import Any, Dict
from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.database.session import get_async_db, engine
from app.models.base import Base
import app.models  # noqa: F401

# Configure structured logging on startup
setup_logging(log_level="INFO" if not settings.DEBUG else "DEBUG")
logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database schema is created and initialized on application boot."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema initialized and verified successfully.")
    except Exception as exc:
        logger.warning(f"Database schema initialization notice: {exc}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="High-performance asynchronous Accounts Receivable automation engine and ledger service.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Standard 4 & Security Hygiene: Configure Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:
    """Assigns or propagates unique request correlation ID and sanitizes unhandled server errors."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception as exc:
        # Standard 8: Full internal trace logged; sanitized generic message returned externally
        logger.exception(
            f"Uncaught internal exception on {request.method} {request.url.path}: {str(exc)}",
            extra={"request_id": request_id},
        )
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "An internal server error occurred. Please contact support.",
                "code": "INTERNAL_SERVER_ERROR",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )
    response.headers["X-Request-ID"] = request_id
    return response


# Register global sanitized exception handlers
register_exception_handlers(app)

# Register centralized API router
from app.api.v1.router import api_v1_router
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Root"])
async def root() -> Dict[str, str]:
    """Root metadata probe."""
    return {
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
        "status": "online",
        "docs": "/docs",
    }


@app.get(f"{settings.API_V1_STR}/health", tags=["Health & Observability"])
async def healthcheck(db: AsyncSession = Depends(get_async_db)) -> Dict[str, Any]:
    """
    Standard 6: Container and service healthcheck probe.
    Validates PostgreSQL database connection pooling and liveness.
    """
    db_status = "connected"
    try:
        result = await db.execute(text("SELECT 1"))
        scalar = result.scalar()
        if scalar != 1:
            db_status = "unhealthy_response"
    except Exception as exc:
        logger.error(f"Healthcheck database probe failed: {str(exc)}")
        db_status = "disconnected"

    overall_status = "healthy" if db_status == "connected" else "degraded"
    response_payload = {
        "status": overall_status,
        "database": db_status,
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
    }

    if overall_status != "healthy":
        return Response(
            content=str(response_payload),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json",
        )

    return response_payload
