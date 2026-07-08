import logging

from fastapi import APIRouter, HTTPException

from src.dependencies import EmbeddingsDep, OllamaDep, OpenSearchDep
from src.schemas.api.ask import AskRequest, AskResponse
from src.schemas.api.search import SearchHit

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ask", tags=["ask"])


@router.post("", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    embedding_client: EmbeddingsDep,
    opensearch_client: OpenSearchDep,
    ollama_client: OllamaDep,
) -> AskResponse:
    """
    Ask endpoint
    """
    try:
        # Embedding
        query_embedding = None
        try:
            query_embedding = await embedding_client.embed_query(request.question)
            logger.info("generated embedding for question")
        except Exception as e:
            logger.warning(f"Failed to generate embedding for question, falling back to BM25: {e}")

        # Search
        if query_embedding is not None:
            result = opensearch_client.search_hybrid(query=request.question, query_embedding=query_embedding, size=request.top_k)
        else:
            result = opensearch_client.search_bm25(query=request.question, size=request.top_k)
        hits = [SearchHit(**hit) for hit in result["hits"]]

        # Build context string
        context = "\n\n".join(f"[arXiv:{hit.arxiv_id}]\n{hit.chunk_text}" for hit in hits)

        # Build sources
        sources = list({f"https://arxiv.org/pdf/{hit.arxiv_id.split('v')[0] if 'v' in hit.arxiv_id else hit.arxiv_id}.pdf" for hit in hits})

        # Ollama call
        answer = ollama_client.chat(question=request.question, context=context)

        return AskResponse(question=request.question, answer=answer, sources=sources)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ask failed, {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
