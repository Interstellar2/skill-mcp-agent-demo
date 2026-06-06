"""FastAPI App：lifespan、CORS、router 挂载."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config import load_env, LOGS_DIR
from ..logging_utils import setup_logging
from ..mcp_pool import get_mcp_pool
from .routes import router as rest_router
from .ws import router as ws_router

load_env()
logger = setup_logging("kitchen_agent", log_dir=str(LOGS_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MCP Connection Pool...")
    pool = get_mcp_pool()
    await pool.start()
    logger.info("MCP Connection Pool started.")
    yield
    logger.info("Stopping MCP Connection Pool...")
    await pool.stop()
    logger.info("MCP Connection Pool stopped.")


app = FastAPI(title="Kitchen SOP API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rest_router, prefix="/api")
app.include_router(ws_router)
