import logging

from fastapi import APIRouter, HTTPException, Path

from src.dependencies import RedisDep, SessionDep
from src.repository.paper_repository import PaperRepository
from src.schemas.arxiv.paper import PaperResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get("/{arxiv_id}", response_model=PaperResponse)
def get_paper_details(
    session: SessionDep,
    redis_client: RedisDep,
    arxiv_id: str = Path(..., description="arXiv paper ID (e.g., '2401.00001' or '2401.00001v1')", regex=r"^\d{4}\.\d{4,5}(v\d+)?$"),
) -> PaperResponse:
    """Get details of a specific paper by arXiv ID."""
    # CACHE CHECK
    cache_key = f"paper:{arxiv_id}"
    try:
        cached = redis_client.get(cache_key)
        if cached:
            logger.info(f"Cache hit: {cache_key[:16]}...")
            return PaperResponse.model_validate_json(cached)
        logger.info(f"Paper not cached for key: {cache_key}")
    except Exception as e:
        logger.warning(f"Cache check failed, continuing without cache: {e}")

    # FETCH FROM DATABASE
    repo = PaperRepository(session)
    paper = repo.get_by_arxiv_id(arxiv_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    # CACHE STORE
    try:
        paper_response = PaperResponse.model_validate(paper)
        redis_client.set(cache_key, paper_response.model_dump_json())
        logger.info(f"Cache stored for key: {cache_key[:16]}...")
    except Exception as e:
        logger.warning(f"Cache store failed: {e}")

    return paper_response
