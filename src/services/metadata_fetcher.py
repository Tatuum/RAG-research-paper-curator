import asyncio
from typing import Dict, Any
import logging
from src.services.arxiv.arxiv_client import ArxivClient
from src.services.pdf_parser.parser import PDFParserService
from src.schemas.arxiv.paper import ArxivPaper
from src.schemas.pdf_parser.models import PdfContent

logger = logging.getLogger(__name__)

class MetadataFetcher:
    """Service for fetching arXiv papers with PDF processing."""

    def __init__(self, 
                 arxiv_client: ArxivClient,
                 pdf_parser: PdfParserService,
                 ):
        self.arxiv_client = arxiv_client
        self.pdf_parser = pdf_parser


    async def fetch_and_process_papers(self) -> Dict[str, Any]:
        """Fetch metadata for the paper."""

        results = {
            "papers_fetched": 0,
            "pdfs_downloaded": 0,
            "pdfs_parsed": 0,
            "papers_stored": 0,
            "papers_indexed": 0,
            "errors": [],
            "processing_time": 0,
        }
        try:
            # Step 1: Fetch paper metadata from arXiv
            papers = await self.arxiv_client.fetch_papers(
                max_results=5, 
            )
            results["papers_fetched"] = len(papers)

            if not papers:
                logger.warning("No papers found")
                return results

            # Step 2: Process the first PDF
            pdf_results = {}
           
            pdf_results = await self.pdf_parser.parse_pdf(papers[0].pdf_url)

        #    results["pdfs_downloaded"] = pdf_results["downloaded"]
        #    results["pdfs_parsed"] = pdf_results["parsed"]
        #    results["errors"].extend(pdf_results["errors"])
            return pdf_results
        except Exception as e:
            logger.error(f"Error fetching and processing papers: {e}")
            raise