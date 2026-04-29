import logging

from opensearchpy import OpenSearch

from src.config import OpenSearchSettings
from src.services.opensearch.index_config import PAPERS_CHUNKS_INDEX, PAPERS_CHUNKS_MAPPING

logger = logging.getLogger(__name__)


class OpenSearchClient:
    def __init__(self, settings: OpenSearchSettings):
        self._client = OpenSearch(hosts=[settings.host])
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
