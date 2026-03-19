from typing import Annotated, Generator, cast

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.db.interfaces.base import BaseDatabase


def get_database(request: Request) -> BaseDatabase:
    """Get database from the request state"""
    return cast(BaseDatabase, request.app.state.database)


def get_db_session(database: Annotated[BaseDatabase, Depends(get_database)]) -> Generator[Session, None, None]:
    """Get database session dependency"""
    with database.get_session() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db_session)]
