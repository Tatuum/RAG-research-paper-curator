import hashlib
import json
import logging

from fastapi import APIRouter, HTTPException

from src.dependencies import EmbeddingsDep, OpenSearchDep, RedisDep
from src.schemas.api.search import SearchHit, SearchRequest, SearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


def make_search_cache_key(request: SearchRequest) -> str:
    """Make a cache key for the search request."""
    data = {
        "query": request.query,
        "mode": request.mode,
        "size": request.size,
        "categories": sorted(request.categories or []),
        "latest": request.latest,
    }
    serialized = json.dumps(data, sort_keys=True)
    return f"search:{hashlib.md5(serialized.encode()).hexdigest()}"


@router.post("", response_model=SearchResponse)
async def search_papers(
    request: SearchRequest,
    opensearch_client: OpenSearchDep,
    embedding_client: EmbeddingsDep,
    redis_client: RedisDep,
) -> SearchResponse:
    """
    Search endpoint supporting multiple search modes.
    """
    # CACHE CHECK
    cache_key = None
    try:
        cache_key = make_search_cache_key(request)
        cached = redis_client.get(cache_key)
        if cached:
            logger.info(f"Cache hit: {cache_key[:16]}...")
            return SearchResponse.model_validate_json(cached)
        logger.info(f"Search results not cached for key: {cache_key}")
    except Exception as e:
        logger.warning(f"Cache check failed, continuing without cache: {e}")

    try:
        if not opensearch_client.health_check():
            raise HTTPException(status_code=503, detail="Search service is currently unavailable")

        # EMBEDDING
        query_embedding = None
        if request.mode == "hybrid":
            try:
                query_embedding = await embedding_client.embed_query(request.query)
                logger.info("generated query embedding for hybrid search")
            except Exception as e:
                logger.warning(f"Failed to generate embeddings for hybrid search, falling back to BM25 only, error: {e}")

        # SEARCH
        if query_embedding is not None:
            result = opensearch_client.search_hybrid(
                query=request.query,
                query_embedding=query_embedding,
                size=request.size,
                categories=request.categories,
            )
        else:
            result = opensearch_client.search_bm25(
                query=request.query,
                size=request.size,
                categories=request.categories,
                latest=request.latest,
            )
        hits = [SearchHit(**hit) for hit in result["hits"]]

        search_response = SearchResponse(
            total=result["total"],
            hits=hits,
            mode="hybrid" if query_embedding is not None else "bm25",
        )

        # CACHE STORE
        try:
            if cache_key is not None:
                redis_client.set(cache_key, search_response.model_dump_json())
                logger.info(f"Cache stored for key: {cache_key[:16]}...")
        except Exception as e:
            logger.warning(f"Cache store failed: {e}")

        logger.info(f"Search completed, total results returned: {search_response.total}")
        return search_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hybrid search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}") from e
