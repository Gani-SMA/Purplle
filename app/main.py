"""
app/main.py — FastAPI entrypoint.
Wires all routes, middleware, exception handlers, and WebSocket broadcast.
"""
from __future__ import annotations


import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

import structlog
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import redis.asyncio as aioredis
import logging

# ── Local imports ─────────────────────────────────────────────────────────────
from models import (
    AnomalyResponse,
    FunnelResponse,
    HeatmapResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
    MetricsResponse,
    StoreHealthItem,
)

# ── Environment ───────────────────────────────────────────────────────────────
DATABASE_URL        = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@db:5432/storedb")
REDIS_URL           = os.getenv("REDIS_URL",    "redis://redis:6379/0")
LOG_LEVEL           = os.getenv("LOG_LEVEL",    "INFO")
CORS_ORIGINS        = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
VALID_API_KEYS      = set(os.getenv("VALID_API_KEYS", "test_key_1,test_key_2").split(","))
STALE_FEED_THRESHOLD_MIN = int(os.getenv("STALE_FEED_THRESHOLD_MIN", "10"))

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(message)s",
)
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
logger = structlog.get_logger("store_intelligence")

# ── Database ──────────────────────────────────────────────────────────────────
engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# ── Redis ─────────────────────────────────────────────────────────────────────
redis_client = aioredis.from_url(REDIS_URL, decode_responses=True)

# ── WebSocket connection manager ──────────────────────────────────────────────
class _ConnectionManager:
    def __init__(self) -> None:
        self._active: dict[str, list[WebSocket]] = {}

    async def connect(self, store_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._active.setdefault(store_id, []).append(ws)

    def disconnect(self, store_id: str, ws: WebSocket) -> None:
        if store_id in self._active:
            try:
                self._active[store_id].remove(ws)
            except ValueError:
                pass

    async def broadcast(self, store_id: str, payload: dict) -> None:
        for ws in list(self._active.get(store_id, [])):
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                self.disconnect(store_id, ws)

ws_manager = _ConnectionManager()

# ── FastAPI app ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown."""
    logger.info("startup", database_url=DATABASE_URL, redis_url=REDIS_URL)
    yield
    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(
    title="Purplle Store Intelligence API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Security ──────────────────────────────────────────────────────────────────
_api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

async def verify_api_key(api_key: str = Depends(_api_key_header)) -> str:
    if not api_key or api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API Key")
    return api_key

# ── DB session dependency ─────────────────────────────────────────────────────
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

# ── Middleware ────────────────────────────────────────────────────────────────
@app.middleware("http")
async def log_and_trace(request: Request, call_next):
    trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())
    request.state.trace_id = trace_id
    start = time.perf_counter()
    response: Response = await call_next(request)
    latency_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["x-trace-id"] = trace_id
    logger.info(
        "request",
        trace_id=trace_id,
        endpoint=request.url.path,
        latency_ms=latency_ms,
        status_code=response.status_code,
    )
    return response

# ── Exception handlers ────────────────────────────────────────────────────────
@app.exception_handler(HTTPException)
async def http_exc_handler(request: Request, exc: HTTPException):
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    return Response(
        status_code=exc.status_code,
        content=json.dumps({"error": "HTTPException", "message": exc.detail, "trace_id": trace_id}),
        media_type="application/json",
    )

@app.exception_handler(Exception)
async def global_exc_handler(request: Request, exc: Exception):
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    logger.error("unhandled_exception", error=str(exc), trace_id=trace_id)
    return Response(
        status_code=500,
        content=json.dumps({"error": "Internal Server Error", "message": str(exc), "trace_id": trace_id}),
        media_type="application/json",
    )

# startup/shutdown handled by lifespan context manager above

# ═══════════════════════════════════════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════════════════════════════════════

# ── POST /events/ingest ───────────────────────────────────────────────────────
@app.post("/events/ingest", response_model=IngestResponse)
async def ingest(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(verify_api_key),
):
    try:
        body_dict = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    raw_events = body_dict.get("events")
    if raw_events is None:
        raise HTTPException(status_code=422, detail="Missing 'events' field")
        
    if not isinstance(raw_events, list):
        raise HTTPException(status_code=422, detail="'events' must be a list")

    if len(raw_events) > 500:
        raise HTTPException(status_code=400, detail="Batch size exceeds maximum limit of 500 events")

    from models import StoreEvent, IngestError
    from ingestion import ingest_events

    valid_events: list[StoreEvent] = []
    rejected_count = 0
    errors: list[IngestError] = []

    for raw_ev in raw_events:
        try:
            store_event = StoreEvent.model_validate(raw_ev)
            valid_events.append(store_event)
        except Exception as e:
            rejected_count += 1
            ev_id = None
            if isinstance(raw_ev, dict):
                ev_id = raw_ev.get("event_id")
            if not ev_id:
                ev_id = str(uuid.uuid4())
            # Format validation error nicely
            errors.append(IngestError(event_id=str(ev_id), reason=str(e)))

    if valid_events:
        result = await ingest_events(valid_events, db, redis_client)
        final_result = IngestResponse(
            accepted=result.accepted,
            rejected=result.rejected + rejected_count,
            errors=result.errors + errors
        )
        # Broadcast to WebSocket listeners grouped by store
        stores: dict[str, list] = {}
        for ev in valid_events:
            stores.setdefault(ev.store_id, []).append(ev.event_type.value)
        for store_id, types in stores.items():
            await ws_manager.broadcast(store_id, {"event_types": types, "count": len(types)})
    else:
        final_result = IngestResponse(
            accepted=0,
            rejected=rejected_count,
            errors=errors
        )

    return final_result


# ── GET /stores/{id}/metrics ──────────────────────────────────────────────────
@app.get("/stores/{id}/metrics", response_model=MetricsResponse)
async def get_metrics(
    id: str,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(verify_api_key),
):
    await _assert_store_exists(id, db)
    from metrics import compute_metrics
    return await compute_metrics(id, db, redis_client)


# ── GET /stores/{id}/funnel ───────────────────────────────────────────────────
@app.get("/stores/{id}/funnel", response_model=FunnelResponse)
async def get_funnel(
    id: str,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(verify_api_key),
):
    await _assert_store_exists(id, db)
    from funnel import compute_funnel
    return await compute_funnel(id, db)


# ── GET /stores/{id}/heatmap ──────────────────────────────────────────────────
@app.get("/stores/{id}/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    id: str,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(verify_api_key),
):
    await _assert_store_exists(id, db)
    from heatmap import compute_heatmap
    return await compute_heatmap(id, db)


# ── GET /stores/{id}/anomalies ────────────────────────────────────────────────
@app.get("/stores/{id}/anomalies", response_model=AnomalyResponse)
async def get_anomalies(
    id: str,
    db: AsyncSession = Depends(get_db),
    _key: str = Depends(verify_api_key),
):
    await _assert_store_exists(id, db)
    from anomalies import compute_anomalies
    return await compute_anomalies(id, db, redis_client)


# ── GET /health ───────────────────────────────────────────────────────────────
@app.get("/health", response_model=HealthResponse)
async def health_check():
    # DB check
    try:
        async with AsyncSessionLocal() as s:
            await s.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(status_code=503, detail="database_unavailable")

    # Redis check
    try:
        await redis_client.ping()
    except Exception as e:
        raise HTTPException(status_code=503, detail="redis_unavailable")

    # Per-store feed staleness
    stores_health: list[StoreHealthItem] = []
    has_stale = False
    try:
        async with AsyncSessionLocal() as s:
            result = await s.execute(text("SELECT store_id FROM stores ORDER BY store_id"))
            store_ids = [r[0] for r in result.fetchall()]
        for sid in store_ids:
            last_ts = await redis_client.get(f"stale_feed:{sid}")
            lag_min: Optional[float] = None
            st = "stale"
            if last_ts:
                try:
                    last_dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
                    lag_sec = (datetime.now(timezone.utc) - last_dt).total_seconds()
                    lag_min = max(0.0, round(lag_sec / 60, 2))
                    st = "stale" if lag_min > STALE_FEED_THRESHOLD_MIN else "live"
                    if st == "stale":
                        has_stale = True
                except Exception:
                    has_stale = True
            else:
                has_stale = True
            stores_health.append(StoreHealthItem(store_id=sid, last_event_ts=last_ts, lag_minutes=lag_min, status=st))
    except Exception:
        pass

    return HealthResponse(status="stale" if has_stale else "healthy", stores=stores_health)


# ── WebSocket /ws/stores/{id} ─────────────────────────────────────────────────
@app.websocket("/ws/stores/{id}")
async def websocket_endpoint(id: str, websocket: WebSocket):
    await ws_manager.connect(id, websocket)
    try:
        while True:
            await websocket.receive_text()   # keep-alive; ignore client messages
    except WebSocketDisconnect:
        ws_manager.disconnect(id, websocket)


# ── Helper ────────────────────────────────────────────────────────────────────
async def _assert_store_exists(store_id: str, db: AsyncSession) -> None:
    result = await db.execute(text("SELECT 1 FROM stores WHERE store_id = :id"), {"id": store_id})
    if not result.fetchone():
        raise HTTPException(status_code=404, detail=f"Store '{store_id}' not found")
