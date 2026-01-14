import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config import Settings
from src.exceptions import MetadataFetchingException, PipelineException
from src.schemas.arxiv.paper import ArxivPaper
from src.schemas.pdf_parser.models import ArxivMetadata, ParsedPaper
from src.services.arxiv.arxiv_client import ArxivClient
from src.services.pdf_parser.parser import PDFParserService

logger = logging.getLogger(__name__)

class MetadataFetcher:
    """Service for fetching arXiv papers with PDF processing."""

    def __init__(self,
                 arxiv_client: ArxivClient,
                 pdf_parser: PDFParserService,
                 pdf_cache_dir: Optional[Path] = None,
                 max_concurrent_downloads: int = 5,
                 max_concurrent_parsing: int = 3,
                 settings: Optional[Settings] = None,
                 ):
        """Initialize metadata fetcher with services and settings.

        :param arxiv_client: Client for arXiv API operations
        :param pdf_parser: Service for parsing PDF documents
        :param pdf_cache_dir: Directory for caching downloaded PDFs
        :param max_concurrent_downloads: Maximum concurrent PDF downloads
        :param max_concurrent_parsing: Maximum concurrent PDF parsing operations
        :param settings: Application settings instance

        :type arxiv_client: ArxivClient
        :type pdf_parser: PDFParserService
        :type pdf_cache_dir: Optional[Path]
        :type max_concurrent_downloads: int
        :type max_concurrent_parsing: int
        :type settings: Optional[Settings]
        """
        from src.config import get_settings

        self.arxiv_client = arxiv_client
        self.pdf_parser = pdf_parser
        self.pdf_cache_dir = pdf_cache_dir or self.arxiv_client.pdf_cache_dir
        self.max_concurrent_downloads = max_concurrent_downloads
        self.max_concurrent_parsing = max_concurrent_parsing
        self.settings = settings or get_settings()


    async def fetch_and_process_papers(
        self,
        max_results: Optional[int] = None,
        ) -> Dict[str, Any]:
        """Fetch papers from arXiv, process PDFs.

        :param max_results: Maximum papers to fetch
        :type max_results: Optional[int]
        :returns: Dictionary with processing results and statistics
        :rtype: Dict[str, Any]
        """

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

            pdf_results = await self._process_pdfs_batch(papers)
            results["pdfs_downloaded"] = pdf_results["downloaded"]
            results["pdfs_parsed"] = pdf_results["parsed"]
            results["errors"].extend(pdf_results["errors"])
            #pdf_results = await self.pdf_parser.parse_pdf(papers[0].pdf_url)

        #    results["pdfs_downloaded"] = pdf_results["downloaded"]
        #    results["pdfs_parsed"] = pdf_results["parsed"]
        #    results["errors"].extend(pdf_results["errors"])

            logger.info(
                f"Pipeline completed: {results['papers_fetched']} papers, {results['pdfs_downloaded']} PDFs, {len(results['errors'])} errors"
            )
            return results
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            results["errors"].append(f"Pipeline error: {str(e)}")
            raise PipelineException(f"Pipeline execution failed: {e}") from e

    async def _process_pdfs_batch(self, papers: List[ArxivPaper]) -> Dict[str, Any]:
        """
        Process PDFs for a batch of papers with async concurrency.

        Uses overlapping download+parse pipeline:
        - Downloads happen concurrently (up to max_concurrent_downloads)
        - As each download completes, parsing starts immediately
        - Multiple PDFs can be parsing while others are still downloading

        This is optimal for production workloads like 100 papers/day.

        Args:
            papers: List of ArxivPaper objects

        Returns:
            Dictionary with processing results and statistics
        """
        results = {
            "downloaded": 0,
            "parsed": 0,
            "parsed_papers": {},
            "errors": [],
            "download_failures": [],
            "parse_failures": [],
        }

        logger.info(f"Starting async pipeline for {len(papers)} PDFs...")
        logger.info(f"Concurrent downloads: {self.max_concurrent_downloads}")
        logger.info(f"Concurrent parsing: {self.max_concurrent_parsing}")

        # Create semaphores for controlled concurrency
        download_semaphore = asyncio.Semaphore(self.max_concurrent_downloads)
        parse_semaphore = asyncio.Semaphore(self.max_concurrent_parsing)

        # Start all download+parse pipelines concurrently
        pipeline_tasks = [self._download_and_parse_pipeline(paper, download_semaphore, parse_semaphore) for paper in papers]

        # Wait for all pipelines to complete
        pipeline_results = await asyncio.gather(*pipeline_tasks, return_exceptions=True)

        # Process results with detailed error tracking
        for paper, result in zip(papers, pipeline_results, strict=False):
            if isinstance(result, Exception):
                error_msg = f"Pipeline error for {paper.arxiv_id}: {str(result)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
            elif result:
                # Check if result is a tuple before unpacking
                # Handle AirflowTaskTerminated and other non-tuple results
                if isinstance(result, tuple) and len(result) == 2:
                    # Result is tuple: (download_success, parsed_paper)
                    download_success, parsed_paper = result
                else:
                    # Result is not a tuple (could be AirflowTaskTerminated or other error)
                    error_msg = f"Pipeline error for {paper.arxiv_id}: Unexpected result type {type(result).__name__}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
                    continue

                if download_success:
                    results["downloaded"] += 1

                    if parsed_paper:
                        results["parsed"] += 1
                        results["parsed_papers"][paper.arxiv_id] = parsed_paper
                    else:
                        # Download succeeded but parsing failed
                        results["parse_failures"].append(paper.arxiv_id)
                else:
                    # Download failed
                    results["download_failures"].append(paper.arxiv_id)
            else:
                # No result returned (shouldn't happen but handle gracefully)
                results["download_failures"].append(paper.arxiv_id)

        # Simple processing summary
        logger.info(f"PDF processing: {results['downloaded']}/{len(papers)} downloaded, {results['parsed']} parsed")

        if results["download_failures"]:
            logger.warning(f"Download failures: {len(results['download_failures'])}")

        if results["parse_failures"]:
            logger.warning(f"Parse failures: {len(results['parse_failures'])}")

        # Add specific failure info to general errors list for backward compatibility
        if results["download_failures"]:
            results["errors"].extend([f"Download failed: {arxiv_id}" for arxiv_id in results["download_failures"]])
        if results["parse_failures"]:
            results["errors"].extend([f"PDF parse failed: {arxiv_id}" for arxiv_id in results["parse_failures"]])

        return results

    async def _download_and_parse_pipeline(
        self, paper: ArxivPaper, download_semaphore: asyncio.Semaphore, parse_semaphore: asyncio.Semaphore
    ) -> tuple:
        """
        Complete download+parse pipeline for a single paper with true parallelism.
        Downloads PDF, then immediately starts parsing while other downloads continue.

        Returns:
            Tuple of (download_success: bool, parsed_paper: Optional[ParsedPaper])
        """
        download_success = False
        parsed_paper = None

        try:
            # Step 1: Download PDF with download concurrency control
            async with download_semaphore:
                logger.debug(f"Starting download: {paper.arxiv_id}")
                pdf_path = await self.arxiv_client.download_pdf(paper, False)

                if pdf_path:
                    download_success = True
                    logger.debug(f"Download complete: {paper.arxiv_id}")
                else:
                    logger.error(f"Download failed: {paper.arxiv_id}")
                    return (False, None)

            # Step 2: Parse PDF with parse concurrency control (happens AFTER download completes)
            # This allows other downloads to continue while this PDF is being parsed
            async with parse_semaphore:
                logger.debug(f"Starting parse: {paper.arxiv_id}")
                pdf_content = await self.pdf_parser.parse_pdf(pdf_path)

                if pdf_content:
                    # Create ArxivMetadata from the paper
                    arxiv_metadata = ArxivMetadata(
                        title=paper.title,
                        authors=paper.authors,
                        abstract=paper.abstract,
                        arxiv_id=paper.arxiv_id,
                        categories=paper.categories,
                        pdf_url=paper.pdf_url,
                    )

                    # Combine into ParsedPaper
                    parsed_paper = ParsedPaper(arxiv_metadata=arxiv_metadata, pdf_content=pdf_content)
                    logger.debug(f"Parse complete: {paper.arxiv_id} - {len(pdf_content.raw_text)} chars extracted")
                else:
                    # PDF parsing failed, but this is not critical - we can continue with metadata only
                    logger.warning(f"PDF parsing failed for {paper.arxiv_id}, continuing with metadata only")

        except Exception as e:
            logger.error(f"Pipeline error for {paper.arxiv_id}: {e}")
            raise MetadataFetchingException(f"Pipeline error for {paper.arxiv_id}: {e}") from e

        return (download_success, parsed_paper)

def make_metadata_fetcher(
    arxiv_client: ArxivClient,
    pdf_parser: PDFParserService,
    pdf_cache_dir: Optional[Path] = None,
    settings: Optional[Settings] = None,
) -> MetadataFetcher:
    """Create MetadataFetcher instance with configuration settings.

    :param arxiv_client: Client for arXiv API operations
    :param pdf_parser: Service for parsing PDF documents
    :param pdf_cache_dir: Directory for caching downloaded PDFs
    :param settings: Application settings instance (uses default if None)
    :type arxiv_client: ArxivClient
    :type pdf_parser: PDFParserService
    :type pdf_cache_dir: Optional[Path]
    :type settings: Optional[Settings]
    :returns: Configured MetadataFetcher instance
    :rtype: MetadataFetcher
    """
    from src.config import get_settings

    if settings is None:
        settings = get_settings()

    return MetadataFetcher(
        arxiv_client=arxiv_client,
        pdf_parser=pdf_parser,
        pdf_cache_dir=pdf_cache_dir,
        max_concurrent_downloads=settings.arxiv.max_concurrent_downloads,
        max_concurrent_parsing=settings.arxiv.max_concurrent_parsing,
        settings=settings,
    )
