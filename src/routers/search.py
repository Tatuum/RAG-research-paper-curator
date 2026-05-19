import logging

from fastapi import APIRouter, HTTPException

from src.dependencies import EmbeddingsDep, OpenSearchDep
from src.schemas.api.search import SearchHit, SearchRequest, SearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search_papers(
    request: SearchRequest,
    opensearch_client: OpenSearchDep,
    embedding_client: EmbeddingsDep,
) -> SearchResponse:
    """
    Search endpoint supporting multiple search modes.
    """
    try:
        if not opensearch_client.health_check():
            raise HTTPException(status_code=503, detail="Search service is currently unavailable")

        query_embedding = None
        if request.mode == "hybrid":
            try:
                query_embedding = await embedding_client.embed_query(request.query)
                logger.info("generated query embedding for hybrid search")
            except Exception as e:
                logger.warning(f"Failed to generate embeddings for hybrid search, falling back to BM25 only, error: {e}")

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
            total=result.get("total", 0),
            hits=hits,
            mode="hybrid" if query_embedding is not None else "bm25",
        )
        logger.info(f"Search completed, total results returned: {search_response.total}")
        return search_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hybrid search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {e}") from e
