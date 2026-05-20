import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI

from .config import get_settings
from .memory import get_qdrant_client, ensure_collection
from .db import create_tables
from .observability.langsmith import setup_langsmith
from .observability.otel import setup_otel
from .api.routers import alerts, approvals, incidents, health

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # Observability
    setup_otel()
    if setup_langsmith():
        log.info("langsmith_enabled", project=settings.langsmith_project)

    # Qdrant collection
    try:
        qdrant = get_qdrant_client()
        ensure_collection(qdrant, settings.qdrant_collection)
        log.info("qdrant_ready", collection=settings.qdrant_collection)
    except Exception as e:
        log.warning("qdrant_unavailable", error=str(e))

    # Postgres tables (create_all is idempotent)
    try:
        await create_tables(settings.database_url)
        log.info("postgres_ready")
    except Exception as e:
        log.warning("postgres_unavailable", error=str(e))

    log.info("siren_started", environment=settings.environment)
    yield
    log.info("siren_stopped")


app = FastAPI(
    title="SIREN",
    description="Self-Improving Incident Response Engine — autonomous AI agent for production incident response",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health.router, tags=["health"])
app.include_router(alerts.router, tags=["alerts"])
app.include_router(approvals.router, tags=["approvals"])
app.include_router(incidents.router, tags=["incidents"], prefix="/api")
