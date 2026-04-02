import logging
from typing import List

import httpx

from src.schemas.embeddings.jina import JinaEmbeddingRequest, JinaEmbeddingResponse

logger = logging.getLogger(__name__)


class JinaEmbeddingsClient:
    def __init__(self, api_key: str, base_url: str = "https://api.jina.ai/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(timeout=30.0)
        logger.info("Jina embeddings client initialized")

    async def embed_passages(self, texts: List[str]) -> List[List[float]]:
        request = JinaEmbeddingRequest(model="jina-embeddings-v3", task="retrieval.passage", dimensions=1024, input=texts)
        try:
            response = await self.client.post(f"{self.base_url}/embeddings", headers=self.headers, json=request.model_dump())
            response.raise_for_status()

            result = JinaEmbeddingResponse(**response.json())
            embeddings: List[List[float]] = [item["embedding"] for item in result.data]

        except httpx.HTTPError as e:
            logger.error(f"Error embedding passages: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in embed_passages: {e}")
            raise
        logger.info(f"Successfully embedded {len(texts)} passages")
        return embeddings

    async def embed_query(self, query: str) -> List[float]:
        request = JinaEmbeddingRequest(
            task="retrieval.query",  # Optimized for search queries
            model="jina-embeddings-v3",
            dimensions=1024,
            input=[query],
        )
        try:
            response = await self.client.post(f"{self.base_url}/embeddings", headers=self.headers, json=request.model_dump())
            response.raise_for_status()

            result = JinaEmbeddingResponse(**response.json())
            embedding: List[float] = result.data[0]["embedding"]

            logger.debug(f"Embedded query: '{query[:50]}...'")
            return embedding

        except httpx.HTTPError as e:
            logger.error(f"Error embedding query: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in embed_query: {e}")
            raise

    async def close(self):
        await self.client.aclose()
