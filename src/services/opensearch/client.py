import logging

from opensearchpy import OpenSearch, helpers

from src.config import Settings
from src.schemas.indexing.chunk import TextChunk
from src.services.opensearch.index_config import HYBRID_RRF_PIPELINE, PAPERS_CHUNKS_INDEX, PAPERS_CHUNKS_MAPPING
from src.services.opensearch.query_builder import QueryBuilder

logger = logging.getLogger(__name__)


class OpenSearchClient:
    def __init__(self, settings: Settings):
        self._client = OpenSearch(hosts=[settings.opensearch.host])
        self._index = PAPERS_CHUNKS_INDEX

    def health_check(self) -> bool:
        """Return True if cluster is reachable."""
        try:
            health = self._client.cluster.health()
            return health["status"] in ["green", "yellow"]
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def ensure_index(self) -> bool:
        """Create index if doesn't exist."""
        try:
            if not self._client.indices.exists(index=self._index):
                self._client.indices.create(index=self._index, body=PAPERS_CHUNKS_MAPPING)
                logger.info(f"Created index: {self._index}")
                self._create_rrf_pipeline()
                return True
            else:
                logger.info(f"Index already exists: {self._index}")
                self._create_rrf_pipeline()
                return False
        except Exception as e:
            logger.error(f"failed to create index. {e}")
            raise

    def _create_rrf_pipeline(self) -> bool:
        """Create RRF search pipeline for native hybrid search.
        :returns: True if created, False if already exists
        """
        try:
            pipeline_id = HYBRID_RRF_PIPELINE["id"]
            try:
                self._client.ingest.get_pipeline(id=pipeline_id)
                logger.info(f"RRF pipeline already exists: {pipeline_id}")
                return False
            except Exception:
                pass
            pipeline_body = {
                "description": HYBRID_RRF_PIPELINE["description"],
                "phase_results_processors": HYBRID_RRF_PIPELINE["phase_results_processors"],
            }

            self._client.transport.perform_request("PUT", f"/_search/pipeline/{pipeline_id}", body=pipeline_body)

            logger.info(f"Created RRF search pipeline: {pipeline_id}")
            return True

        except Exception as e:
            logger.error(f"Error creating RRF pipeline: {e}")
            raise

    def bulk_index_chunks(
        self,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
        title: str,
        authors: list[str],
        categories: list[str],
        published_date: str,
    ) -> int:
        """Bulk index multiple chunks with embeddings.
        :returns: number of chunks indexed
        """
        if len(chunks) != len(embeddings):
            logger.error("The length of chunks and embeddings doesn't match")
            raise ValueError(f"chunks and embeddings length mismatch: {len(chunks)} vs {len(embeddings)}")
        try:
            actions = [
                {
                    "_index": self._index,
                    "_source": {
                        "arxiv_id": chunk.arxiv_id,
                        "chunk_index": chunk.chunk_index,
                        "chunk_text": chunk.chunk_text,
                        "embedding": embedding,
                        "title": title,
                        "authors": authors,
                        "categories": categories,
                        "published_date": published_date,
                    },
                }
                for chunk, embedding in zip(chunks, embeddings, strict=False)
            ]

            success_count, errors = helpers.bulk(self._client, actions)
            logger.info(f"indexed {success_count}/{len(chunks)} chunks")
            return int(success_count)
        except Exception as e:
            logger.error(f"Failed to bulk index chunks: {e}")
            raise

    def search_bm25(self, query: str, size: int = 10, categories: list[str] | None = None, latest: bool = False) -> dict:
        """Search using BM25 full-text ranking across chunk_text and title fields.

        :param query: Search query string
        :param size: Maximum number of results to return (default 10)
        :param categories: Optional list of arXiv category codes to filter by (e.g. ["cs.AI", "cs.LG"])
        :param latest: If True, sort results by published_date descending instead of relevance score
        :returns: Dict with keys:
            - total (int): total number of matching documents
            - hits (list[dict]): matched chunks, each with arxiv_id, chunk_index, chunk_text,
              title, authors, categories, published_date, score
        """
        # Step 1: build the query dict
        search_body = QueryBuilder(query=query, size=size, categories=categories, latest=latest).build()
        # Step 2: send to OpenSearch
        response = self._client.search(index=self._index, body=search_body)
        # Step 3: extract results into a clean dict
        hits = []
        for hit in response["hits"]["hits"]:
            chunk = hit["_source"].copy()
            chunk["score"] = hit["_score"]
            hits.append(chunk)
        return {"total": response["hits"]["total"]["value"], "hits": hits}

    def search_hybrid(self, query: str, query_embedding: list[float], size: int = 10, categories: list[str] | None = None) -> dict:
        """Search using hybrid BM25 + vector similarity, combined with RRF pipeline.

        :param query: Search query string (used for BM25 leg)
        :param query_embedding: Query vector (1024-dim) from Jina embed_query() (used for kNN leg)
        :param size: Maximum number of results to return (default 10)
        :param categories: Optional list of arXiv category codes to filter by (e.g. ["cs.AI", "cs.LG"])
        :returns: Dict with keys:
            - total (int): total number of matching documents
            - hits (list[dict]): matched chunks, each with arxiv_id, chunk_index, chunk_text,
              title, authors, categories, published_date, score
        """
        # Step 1: Build BM25 query
        bm25_body = QueryBuilder(query=query, size=size, categories=categories).build()
        bm25_query = bm25_body["query"]
        # Step 2: Wrap both in hybrid
        search_body = {
            "size": size,
            "query": {"hybrid": {"queries": [bm25_query, {"knn": {"embedding": {"vector": query_embedding, "k": size * 2}}}]}},
            "_source": bm25_body["_source"],
        }
        # Step 3: Send with RRF pipeline
        response = self._client.search(index=self._index, body=search_body, params={"search_pipeline": HYBRID_RRF_PIPELINE["id"]})
        # Step 4: extract results into a clean dict
        hits = []
        for hit in response["hits"]["hits"]:
            chunk = hit["_source"].copy()
            chunk["score"] = hit["_score"]
            hits.append(chunk)
        return {"total": response["hits"]["total"]["value"], "hits": hits}
