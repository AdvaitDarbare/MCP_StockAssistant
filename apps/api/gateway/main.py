from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.config import settings
from .stream import router as stream_router
from .routers.market_data import router as market_data_router
from .routers.reports import router as reports_router
from .routers.schwab import router as schwab_router
from .routers.tooling import router as tooling_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of shared resources."""
    # Startup
    from apps.api.db.database import init_db
    from apps.api.services.cache import init_cache, close_cache
    await init_db()
    await init_cache()
    yield
    # Shutdown
    from apps.api.db.database import close_db
    await close_db()
    await close_cache()


app = FastAPI(title="AI Stock Assistant API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stream_router, prefix="/api")
app.include_router(market_data_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(schwab_router, prefix="/api")
app.include_router(tooling_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
