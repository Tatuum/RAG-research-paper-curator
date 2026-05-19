from typing import Annotated, Generator, cast

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.db.interfaces.base import BaseDatabase
from src.services.embeddings.jina_client import JinaEmbeddingsClient
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


SessionDep = Annotated[Session, Depends(get_db_session)]
OpenSearchDep = Annotated[OpenSearchClient, Depends(get_opensearch_client)]
EmbeddingsDep = Annotated[JinaEmbeddingsClient, Depends(get_embeddings_client)]
