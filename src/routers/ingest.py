import logging

from fastapi import APIRouter, HTTPException

from src.dependencies import EmbeddingsDep, MetadataFetcherDep, OpenSearchDep, SessionDep
from src.repository.paper_repository import PaperRepository
from src.schemas.api.ingest import IngestRequest, IngestResponse
from src.services.indexing.text_chunker import TextChunker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post("", response_model=IngestResponse)
async def ingest_papers(
    request: IngestRequest,
    session: SessionDep,
    metadata_fetcher: MetadataFetcherDep,
    embedding_client: EmbeddingsDep,
    opensearch_client: OpenSearchDep,
) -> IngestResponse:
    try:
        # Step 1. Fetch and store
        results = await metadata_fetcher.fetch_and_process_papers(
            from_date=request.date,
            to_date=request.date,
            max_results=request.max_results,
            db_session=session,
        )
        papers_stored = results["papers_stored"]

        # Step 2. Get stored papers
        repo = PaperRepository(session)
        papers = repo.get_recently_created(limit=papers_stored)

        # Step 3. Chunk -> Embed -> Index
        chunker = TextChunker()
        chunks_indexed = 0

        for paper in papers:
            if not paper.raw_text and not paper.sections:
                continue
            chunks = chunker.chunk_paper(
                arxiv_id=str(paper.arxiv_id),
                title=str(paper.title),
                abstract=str(paper.abstract),
                sections=paper.sections or [],
                raw_text=paper.raw_text or "",
            )
            if not chunks:
                continue
            embeddings = await embedding_client.embed_passages([c.chunk_text for c in chunks])
            chunks_indexed += opensearch_client.bulk_index_chunks(
                chunks=chunks,
                embeddings=embeddings,
                title=str(paper.title),
                authors=list(paper.authors),
                categories=list(paper.categories),
                published_date=paper.published_date.strftime("%Y-%m-%d"),
            )

        return IngestResponse(
            papers_fetched=results["papers_fetched"],
            papers_stored=papers_stored,
            chunks_indexed=chunks_indexed,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
