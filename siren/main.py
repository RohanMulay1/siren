import asyncio
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .observability.langsmith import setup_langsmith
from .observability.otel import setup_otel
from .api.routers import alerts, approvals, incidents, health, memory

log = structlog.get_logger()


async def _init_qdrant(settings) -> None:
    try:
        from .memory import get_qdrant_client, ensure_collection
        qdrant = get_qdrant_client()
        await asyncio.to_thread(ensure_collection, qdrant, settings.qdrant_collection)
        log.info("qdrant_ready", collection=settings.qdrant_collection)
    except Exception as e:
        log.warning("qdrant_unavailable", error=str(e))


async def _init_postgres(settings) -> None:
    try:
        from .db.session import create_tables
        await create_tables(settings.async_database_url)
        log.info("postgres_ready")
    except Exception as e:
        log.warning("postgres_unavailable", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    try:
        setup_otel()
    except Exception as e:
        log.warning("otel_setup_failed", error=str(e))

    try:
        if setup_langsmith():
            log.info("langsmith_enabled", project=settings.langsmith_project)
    except Exception as e:
        log.warning("langsmith_setup_failed", error=str(e))

    # Run infra init concurrently with a timeout so startup is never blocked
    try:
        await asyncio.wait_for(
            asyncio.gather(_init_qdrant(settings), _init_postgres(settings)),
            timeout=15.0,
        )
    except asyncio.TimeoutError:
        log.warning("infra_init_timeout", detail="Qdrant/Postgres init took >15s — continuing anyway")
    except Exception as e:
        log.warning("infra_init_error", error=str(e))

    log.info("siren_started", environment=settings.environment)
    yield
    log.info("siren_stopped")


app = FastAPI(
    title="SIREN",
    description="Self-Improving Incident Response Engine — autonomous AI agent for production incident response",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(alerts.router, tags=["alerts"])
app.include_router(approvals.router, tags=["approvals"])
app.include_router(incidents.router, tags=["incidents"], prefix="/api")
app.include_router(memory.router, tags=["memory"])
