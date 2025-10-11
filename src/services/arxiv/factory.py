from src.services.arxiv.arxiv_client import ArxivClient
from src.config import get_settings
from src.config import ArxivSettings

def make_arxiv_client(settings: ArxivSettings) -> ArxivClient:
    """Factory function to create an arXiv client instance.

    :returns: An instance of the arXiv client ArxivClient
    """
    settings = get_settings()
    client = ArxivClient(settings=settings.arxiv)
    return client