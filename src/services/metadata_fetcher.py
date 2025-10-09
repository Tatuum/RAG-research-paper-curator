import asyncio
from src.services.arxiv.arxiv_client import ArxivClient
from src.services.pdf_parser.parser import PdfParser
from src.schemas.arxiv.paper import ArxivPaper
from src.schemas.pdf_parser.models import PdfContent

class MetadataFetcher:
    """Service for fetching arXiv papers with PDF processing."""

    def __init__(self, 
                 arxiv_client: ArxivClient,
                 pdf_parser: PdfParser,
                 ):
        self.arxiv_client = arxiv_client
        self.pdf_parser = pdf_parser

        self.paper = paper

    def fetch_metadata(self):
        """Fetch metadata for the paper."""
        return self.paper.metadata