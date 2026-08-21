import logging

from langfuse import Langfuse

from src.config import Settings

logger = logging.getLogger(__name__)


class LangfuseTracer:
    def __init__(self, settings: Settings):
        self.settings = settings.langfuse
        self.client: Langfuse | None = None

        if self.settings.enabled and self.settings.public_key and self.settings.secret_key:
            try:
                self.client = Langfuse(
                    public_key=self.settings.public_key,
                    secret_key=self.settings.secret_key,
                    host=self.settings.host,
                    flush_at=self.settings.flush_at,
                    flush_interval=self.settings.flush_interval,
                    debug=self.settings.debug,
                )
                logger.info(f"Langfuse tracing initialized (host: {self.settings.host})")
            except Exception as e:
                logger.error(f"Failed to initialize Langfuse: {e}")
                self.client = None
        else:
            logger.info("Langfuse disabled or missing credentials")

    def health_check(self) -> bool:
        if not self.client:
            logger.warning("Langfuse client is not initialized")
            return False
        try:
            # Perform a simple operation to check if the client is working
            self.client.auth_check()
            logger.info("Langfuse health check passed")
            return True
        except Exception as e:
            logger.error(f"Langfuse health check failed: {e}")
            return False

    def flush(self) -> None:
        if not self.client:
            return
        try:
            self.client.flush()
            logger.info("Langfuse flush successful")
        except Exception as e:
            logger.error(f"Langfuse flush failed: {e}")

    def shutdown(self) -> None:
        if not self.client:
            return
        try:
            self.client.flush()
            self.client.shutdown()
            logger.info("Langfuse shutdown successful")
        except Exception as e:
            logger.error(f"Langfuse shutdown failed: {e}")
