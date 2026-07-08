import logging
from pathlib import Path
from typing import cast

from ollama import Client
from src.config import Settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, settings: Settings):
        self.client = Client(host=settings.ollama.host)
        self.model = settings.ollama.model

        self.prompts_dir = Path(__file__).parent / "prompts"
        self.system_prompt = (self.prompts_dir / "system_prompt.txt").read_text()

    def health_check(self) -> bool:
        try:
            self.client.list()
            return True
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    def chat(self, question: str, context: str) -> str:
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion:\n{question}"},
            ]
            response = self.client.chat(model=self.model, messages=messages)
            content = response.message.content
            if content is None:
                logger.warning("Ollama chat response is None")
                raise ValueError("Ollama chat response is None")
            return cast(str, content)
        except Exception as e:
            logger.error(f"Ollama chat failed: {e}")
            raise
