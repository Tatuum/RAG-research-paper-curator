from typing import Annotated, Generator, cast

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.db.interfaces.base import BaseDatabase
from src.services.cache.redis_client import RedisClient
from src.services.embeddings.jina_client import JinaEmbeddingsClient
from src.services.llm.ollama_client import OllamaClient
from src.services.metadata_fetcher import MetadataFetcher
from src.services.opensearch.client import OpenSearchClient


def get_database(request: Request) -> BaseDatabase:
    """Get database from the request state"""
    return cast(BaseDatabase, request.app.state.database)


def get_db_session(database: Annotated[BaseDatabase, Depends(get_database)]) -> Generator[Session, None, None]:
    """Get database session dependency"""
    with database.get_session() as session:
        yield session


def get_opensearch_client(request: Request) -> OpenSearchClient:
    """Get OpenSearch client from the request state."""
    return cast(OpenSearchClient, request.app.state.opensearch)


def get_embeddings_client(request: Request) -> JinaEmbeddingsClient:
    """Get embeddings client from the request state."""
    return cast(JinaEmbeddingsClient, request.app.state.embeddings)


def get_redis_client(request: Request) -> RedisClient:
    """Get Redis client from the request state."""
    return cast(RedisClient, request.app.state.redis)


def get_ollama_client(request: Request) -> OllamaClient:
    """Get Ollama client from the request state."""
    return cast(OllamaClient, request.app.state.llm)


def get_metadata_fetcher(request: Request) -> MetadataFetcher:
    """Get MetadataFetcher from the request state"""
    return cast(MetadataFetcher, request.app.state.metadata_fetcher)


SessionDep = Annotated[Session, Depends(get_db_session)]
OpenSearchDep = Annotated[OpenSearchClient, Depends(get_opensearch_client)]
EmbeddingsDep = Annotated[JinaEmbeddingsClient, Depends(get_embeddings_client)]
RedisDep = Annotated[RedisClient, Depends(get_redis_client)]
OllamaDep = Annotated[OllamaClient, Depends(get_ollama_client)]
MetadataFetcherDep = Annotated[MetadataFetcher, Depends(get_metadata_fetcher)]
