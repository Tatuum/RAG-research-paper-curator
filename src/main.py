import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import get_settings
from src.db.factory import make_database
from src.routers.papers import router as papers_router
from src.routers.search import router as search_router
from src.services.embeddings.factory import make_embeddings_client
from src.services.opensearch.factory import make_opensearch_client

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
    logger.info("Starting up the API...")

    settings = get_settings()
    app.state.settings = settings

    database = make_database()
    app.state.database = database
    logger.info("Database connected")

    # Initialize search service
    opensearch_client = make_opensearch_client()
    app.state.opensearch = opensearch_client
    # Verify OpenSearch connectivity and create index if needed
    if opensearch_client.health_check():
        logger.info("Opensearch client connected successfully")
        opensearch_client.ensure_index()
    else:
        logger.warning("OpenSearch connection failed - search features will be limited")

    embeddings_client = make_embeddings_client()
    app.state.embeddings = embeddings_client

    logger.info("Services initialized: OpenSearch, Embeddings")
    logger.info("API ready")

    yield

    # Cleanup
    database.teardown()
    await embeddings_client.close()
    logger.info("API shutdown complete")


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
app.include_router(search_router, prefix="/api/v1")
