import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from app.models import user
from app.models.user import User
from sqlalchemy.orm import sessionmaker
from app.api.auth import router as auth_router
from app.api.auth import ensure_default_admin, ensure_default_organization
from app.api.analytics import router as analytics_router
from app.api.autonomous_agent import router as autonomous_agent_router
from app.api.donors import router as donors_router
from app.api.embryos import router as embryos_router
from app.api.import_data import router as import_router
from app.api.grading import router as grading_router
from app.api.health import router as health_router
from app.api.ivf_batches import router as ivf_batches_router
from app.api.opu_sessions import router as opu_sessions_router
from app.api.organizations import router as organizations_router
from app.api.predictions import router as predictions_router
from app.api.protocols import router as protocols_router
from app.api.qc import router as qc_router
from app.api.recipients import router as recipients_router
from app.api.sires import router as sires_router
from app.api.technicians import router as technicians_router
from app.api.transfers import router as transfers_router
from app.middleware import (
    error_handling_middleware,
    rate_limit_middleware,
    register_exception_handlers,
)
from app.logging_config import setup_logging

# Initialize structured JSON logging before anything else
setup_logging()

logger = logging.getLogger(__name__)


def _warm_analytics_cache():
    """Pre-compute analytics artifacts in background during startup."""
    try:
        logger.info("Warming analytics cache...")
        _project_root = Path(__file__).resolve().parent.parent.parent
        if str(_project_root) not in sys.path:
            sys.path.insert(0, str(_project_root))
        
        from ml.analytics.run_analytics import run_analytics
        run_analytics()
        logger.info("Analytics cache warmed successfully")
    except Exception as e:
        logger.warning("Failed to warm analytics cache: %s", e)


def _warm_qc_cache():
    """Pre-compute QC artifacts in background during startup."""
    try:
        logger.info("Warming QC cache...")
        _project_root = Path(__file__).resolve().parent.parent.parent
        if str(_project_root) not in sys.path:
            sys.path.insert(0, str(_project_root))
        
        from ml.qc.run_pipeline import run_qc_pipeline
        run_qc_pipeline()
        logger.info("QC cache warmed successfully")
    except Exception as e:
        logger.warning("Failed to warm QC cache: %s", e)


from app.database import Base, engine, SessionLocal


def init_db():
    """Initialize database."""
    pass


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Lifespan context for the FastAPI app."""
    init_db()
    Base.metadata.create_all(bind=engine)
    logger.info("Ovulite API started")

    # Seed the default admin for local/dev databases when no users exist.
    db = SessionLocal()
    try:
        ensure_default_organization(db)
        seeded = ensure_default_admin(db)
        if seeded:
            logger.info("Seeded default admin user during startup")
    finally:
        db.close()
    
    yield
    
    logger.info("Ovulite API shutdown")


app = FastAPI(title="Ovulite API", version="0.1.0", lifespan=lifespan)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(autonomous_agent_router, tags=["autonomous_agent"])
app.include_router(donors_router, prefix="/donors", tags=["donors"])
app.include_router(sires_router, prefix="/sires", tags=["sires"])
app.include_router(recipients_router, prefix="/recipients", tags=["recipients"])
app.include_router(embryos_router, prefix="/embryos", tags=["embryos"])
app.include_router(opu_sessions_router, prefix="/opu-sessions", tags=["opu_sessions"])
app.include_router(ivf_batches_router, prefix="/ivf-batches", tags=["ivf_batches"])
app.include_router(transfers_router, prefix="/transfers", tags=["transfers"])
app.include_router(technicians_router, prefix="/technicians", tags=["technicians"])
app.include_router(protocols_router, prefix="/protocols", tags=["protocols"])
app.include_router(import_router, prefix="/import", tags=["import"])
app.include_router(predictions_router, prefix="/predict", tags=["predictions"])
app.include_router(grading_router, prefix="/grade", tags=["grading"])
app.include_router(qc_router, prefix="/qc", tags=["qc"])
app.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
app.include_router(organizations_router)
app.include_router(health_router, tags=["health"])


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log every request with method, path, status, duration, and a unique request_id."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)

    logger.info(
        "%s %s → %s (%.2fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.middleware("http")
async def rate_limit_http_middleware(request: Request, call_next):
    return await rate_limit_middleware(request, call_next)


@app.middleware("http")
async def error_handler_http_middleware(request: Request, call_next):
    return await error_handling_middleware(request, call_next)
