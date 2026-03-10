from src.config import get_settings
from src.db.interfaces.base import BaseDatabase
from src.db.interfaces.postgresql import PostgreSQLDatabase


def make_database() -> BaseDatabase:
    """Factory function to create a database instance."""
    settings = get_settings()
    database = PostgreSQLDatabase(config=settings.postgres)
    database.startup()
    return database
