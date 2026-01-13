import logging
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from src.db.interfaces.base import BaseDatabase
from src.config import PostgresSettings

logger = logging.getLogger(__name__)

Base = declarative_base()

class PostgreSQLDatabase(BaseDatabase):
      """PostgreSQL database implementation."""

      def __init__(self, config: PostgresSettings):
          self.config = config
          self.engine: Optional[Engine] = None
          self.session_factory: Optional[sessionmaker] = None

      def startup(self) -> None:
          """Initialize the database connection."""
          try:
              logger.info("Connecting to PostgreSQL database...")

              self.engine = create_engine(
                  self.config.database_url,
                  echo=self.config.echo_sql,
                  pool_size=self.config.pool_size,
                  max_overflow=self.config.max_overflow,
                  pool_pre_ping=True,  # Verify connections before use
              )

              self.session_factory = sessionmaker(
                  bind=self.engine,
                  expire_on_commit=False
              )

              # Test the connection
              assert self.engine is not None
              with self.engine.connect() as conn:
                  conn.execute(text("SELECT 1"))
                  logger.info("Database connection test successful")

              # Check existing tables
              inspector = inspect(self.engine)
              existing_tables = inspector.get_table_names()

              # Import models so Base knows about them
              from src.models.paper import Paper

              # Create tables if they don't exist
              Base.metadata.create_all(bind=self.engine)

              # Check if any new tables were created
              updated_tables = inspector.get_table_names()
              new_tables = set(updated_tables) - set(existing_tables)

              if new_tables:
                  logger.info(f"Created new tables: {', '.join(new_tables)}")
              else:
                  logger.info("All tables already exist")

              logger.info("PostgreSQL database initialized successfully")
              logger.info(f"Database: {self.engine.url.database}")
              logger.info(f"Tables: {', '.join(updated_tables) if updated_tables else 'None'}")

          except Exception as e:
              logger.error(f"Failed to initialize PostgreSQL database: {e}")
              raise

      def teardown(self) -> None:
          """Close the database connection."""
          if self.engine:
              self.engine.dispose()
              logger.info("PostgreSQL database connections closed")

      @contextmanager
      def get_session(self) -> Generator[Session, None, None]:
          """Get a database session context manager."""
          if not self.session_factory:
              raise RuntimeError("Database not initialized. Call startup() first.")

          session = self.session_factory()
          try:
              yield session
              session.commit()  # Auto-commit on success
          except Exception:
              session.rollback()  # Auto-rollback on error
              raise
          finally:
              session.close()