import logging

from opensearchpy import OpenSearch, helpers

from src.config import Settings
from src.schemas.indexing.chunk import TextChunk
from src.services.opensearch.index_config import PAPERS_CHUNKS_INDEX, PAPERS_CHUNKS_MAPPING

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
                return True
            else:
                logger.info(f"Index already exists: {self._index}")
                return False
        except Exception as e:
            logger.error(f"failed to create index. {e}")
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
