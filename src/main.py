import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.db.factory import make_database
from src.routers.papers import router as papers_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan for the API.
    """
    print("Starting up the API...")

    database = make_database()
    app.state.database = database
    logger.info("Database connected")

    print("Database tables ready!")
    yield

    print("Shutting down the API...")
    # Cleanup
    database.teardown()


app = FastAPI(
    title="Scientific Paper Curator API",
    description="Personal scientific paper curator with RAG capabilities",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


app.include_router(papers_router, prefix="/api/v1")
