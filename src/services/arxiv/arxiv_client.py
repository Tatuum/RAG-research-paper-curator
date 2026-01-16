import asyncio
import logging
import time
import xml.etree.ElementTree as ET
from functools import cached_property
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlencode

import aiofiles
import httpx
from src.config import ArxivSettings, get_settings
from src.exceptions import (
    ArxivAPIException,
    ArxivAPITimeoutError,
    ArxivParseError,
    PDFDownloadException,
    PDFDownloadTimeoutError,
)
from src.schemas.arxiv.paper import ArxivPaper

logger = logging.getLogger(__name__)


class ArxivClient:
    """Minimal client for fetching papers from arXiv API."""

    def __init__(self, settings: ArxivSettings):
        self._settings = settings
        self._last_request_time: Optional[float] = None

    @cached_property
    def pdf_cache_dir(self) -> Path:
        """PDF cache directory."""
        cache_dir = Path(self._settings.pdf_cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    @property
    def base_url(self) -> str:
        return self._settings.base_url

    @property
    def namespaces(self) -> dict:
        return self._settings.namespaces

    @property
    def rate_limit_delay(self) -> float:
        return self._settings.rate_limit_delay

    @property
    def timeout_seconds(self) -> int:
        return self._settings.timeout_seconds

    @property
    def max_results(self) -> int:
        return self._settings.max_results

    @property
    def search_category(self) -> str:
        return self._settings.search_category

    async def _rate_limit(self):
        """Implement rate limiting to respect arXiv's 3-second delay requirement."""
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    async def fetch_papers(
        self,
        start: int = 0,
        max_results: Optional[int] = None,
    ) -> List[ArxivPaper]:
        """
        Fetch papers from arXiv API.

        Args:
            start: Starting index for pagination
            max_results: Maximum number of papers to fetch


        Returns:
            List of ArxivPaper objects
        """
        if max_results is None:
            max_results = self.max_results

        # Build search query
        search_query = f"cat:{self.search_category}"

        params = {
            "search_query": search_query,
            "start": start,
            "max_results": min(max_results, 2000),  # arXiv limit
        }
        safe = ":+[]"  # Don't encode :, +, [, ] characters needed for arXiv queries
        url = f"{self.base_url}?{urlencode(params, safe=safe)}"

        try:
            logger.info(f"Fetching {max_results} {self.search_category} papers from arXiv")
        # Add rate limiting delay between all requests (arXiv recommends 3 seconds)
            await self._rate_limit()

            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(url)
                response.raise_for_status()
                xml_data = response.text

            papers = self._parse_response(xml_data)
            logger.info(f"Fetched {len(papers)} papers")

            return papers

        except httpx.TimeoutException as e:
            logger.error(f"arXiv API timeout: {e}")
            raise ArxivAPITimeoutError(f"arXiv API request timed out: {e}") from e

        except httpx.HTTPStatusError as e:
            logger.error(f"arXiv API HTTP error: {e}")
            raise ArxivAPIException(f"arXiv API returned error {e.response.status_code}: {e}") from e

        except Exception as e:
            logger.error(f"Failed to fetch papers from arXiv: {e}")
            raise ArxivAPIException(f"Unexpected error fetching papers from arXiv: {e}") from e

    def _get_text(self, element: ET.Element, path: str, clean_newlines: bool = False) -> str:
        """
        Extract text from XML element safely.

        Args:
            element: Parent XML element
            path: XPath to find the text element
            clean_newlines: Whether to replace newlines with spaces

        Returns:
            Extracted text or empty string
        """
        elem = element.find(path, self.namespaces)
        if elem is None or elem.text is None:
            return ""

        text = elem.text.strip()
        return text.replace("\n", " ") if clean_newlines else text

    def _get_categories(self, entry: ET.Element) -> List[str]:
        """
        Extract categories from entry.

        Args:
            entry: XML entry element

        Returns:
            List of category terms
        """
        categories = []
        for category in entry.findall("atom:category", self.namespaces):
            term = category.get("term")
            if term:
                categories.append(term)
        return categories

    def _get_pdf_url(self, entry: ET.Element) -> str:
        """
        Extract PDF URL from entry links.

        Args:
            entry: XML entry element

        Returns:
            PDF URL or empty string (always HTTPS)
        """
        for link in entry.findall("atom:link", self.namespaces):
            if link.get("type") == "application/pdf":
                url = link.get("href", "")
                # Convert HTTP to HTTPS for arXiv URLs
                if url.startswith("http://arxiv.org/"):
                    url = url.replace("http://arxiv.org/", "https://arxiv.org/")
                return url
        return ""
    def _parse_single_entry(self, entry: ET.Element) -> Optional[ArxivPaper]:
        """
        Parse a single entry from arXiv XML response.

        Args:
            entry: XML entry element

        Returns:
            ArxivPaper object or None if parsing fails
        """
        try:

            # Extract paper ID
            arxiv_id_elem = entry.find('atom:id', self.namespaces)
            if arxiv_id_elem is None or arxiv_id_elem.text is None:
                logger.warning(f"No arxiv_id found in entry: {entry}")
                return None
            else:
                arxiv_id = arxiv_id_elem.text.split('/')[-1]  # Extract ID from URL
                logger.info(f"Fetched {arxiv_id} paper from arXiv")

            #Extract authors
            authors = []
            author_elems = entry.findall("atom:author", self.namespaces)
            #logger.info(f"Entry {i}: Found {len(author_elems)} author elements")

            for author in author_elems:
                name_elem = author.find("atom:name", self.namespaces)
                name = name_elem.text.strip() if name_elem is not None and name_elem.text else ""
                if name:
                    authors.append(name)
            # logger.info(f"Entry {i}: Extracted {len(authors)} authors")

            title = self._get_text(entry, "atom:title", clean_newlines=True)
            abstract = self._get_text(entry, "atom:summary", clean_newlines=True)
            pdf_url = self._get_pdf_url(entry)
            categories = self._get_categories(entry)

            paper = ArxivPaper(
                arxiv_id=arxiv_id,
                title=title,
                abstract=abstract,
                authors=authors,
                categories=categories,
                pdf_url=pdf_url
            )
            return paper

        except Exception as e:
            logger.error(f"Failed to parse entry: {e}")
            return None

    def _parse_response(self, xml_content: str) -> List[ArxivPaper]:
        """Parse arXiv API XML response."""
        try:
            root = ET.fromstring(xml_content)
            papers = []

            # Find all entry elements
            entries = root.findall('.//atom:entry', self.namespaces)
            total_entries = len(entries)
            logger.info(f"Found {total_entries} entries in XML response")
            for i, entry in enumerate(entries):
                logger.info(f"Processing entry {i+1}/{total_entries}")
                paper = self._parse_single_entry(entry)
                if paper:
                    papers.append(paper)
            return papers
        except ET.ParseError as e:
            logger.error(f"Failed to parse arXiv XML response: {e}")
            raise ArxivParseError(f"Failed to parse arXiv XML response: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error parsing arXiv response: {e}")
            raise ArxivParseError(f"Unexpected error parsing arXiv response: {e}") from e
        #logger.info(f"Returning {len(papers)} papers")

    async def download_pdf(self, paper: ArxivPaper, force_download: bool = False) -> Optional[Path]:
        """
        Download PDF for a given paper to local cache.

        Args:
            paper: ArxivPaper object containing PDF URL
            force_download: Force re-download even if file exists

        Returns:
            Path to downloaded PDF file or None if download failed
        """
        if not paper.pdf_url:
            logger.error(f"No PDF URL for paper {paper.arxiv_id}")
            return None

        pdf_path = self._get_pdf_path(paper.arxiv_id)

        # Return cached PDF if exists
        if pdf_path.exists() and not force_download:
            logger.info(f"Using cached PDF: {pdf_path.name}")
            return pdf_path

        # Download with retry
        if await self._download_with_retry(paper.pdf_url, pdf_path):
            return pdf_path
        else:
            return None

    def _get_pdf_path(self, arxiv_id: str) -> Path:
        """
        Get the local path for a PDF file.

        Args:
            arxiv_id: arXiv paper ID

        Returns:
            Path object for the PDF file
        """
        safe_filename = arxiv_id.replace("/", "_") + ".pdf"
        return self.pdf_cache_dir / safe_filename

    async def _download_with_retry(self, url: str, path: Path, max_retries: Optional[int] = None) -> bool:
        """Download a file with retry logic."""
        if max_retries is None:
            max_retries = self._settings.download_max_retries

        logger.info(f"Downloading PDF from {url}")

        # Respect rate limits
        await asyncio.sleep(self.rate_limit_delay)

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=float(self.timeout_seconds)) as client:
                    async with client.stream("GET", url) as response:
                        response.raise_for_status()
                        async with aiofiles.open(path, "wb") as f:
                            async for chunk in response.aiter_bytes():
                                await f.write(chunk)
                logger.info(f"Successfully downloaded to {path.name}")
                return True

            except httpx.TimeoutException as e:
                if attempt < max_retries - 1:
                    wait_time = self._settings.download_retry_delay_base * (attempt + 1)
                    logger.warning(f"PDF download timeout (attempt {attempt + 1}/{max_retries}): {e}")
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"PDF download failed after {max_retries} attempts due to timeout: {e}")
                    raise PDFDownloadTimeoutError(f"PDF download timed out after {max_retries} attempts: {e}") from e
            except httpx.HTTPError as e:
                if attempt < max_retries - 1:
                    wait_time = self._settings.download_retry_delay_base * (attempt + 1)  # Exponential backoff
                    logger.warning(f"Download failed (attempt {attempt + 1}/{max_retries}): {e}")
                    logger.info(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Failed after {max_retries} attempts: {e}")
                    raise PDFDownloadException(f"PDF download failed after {max_retries} attempts: {e}") from e
            except Exception as e:
                logger.error(f"Unexpected download error: {e}")
                raise PDFDownloadException(f"Unexpected error during PDF download: {e}") from e

        # Clean up partial download
        if path.exists():
            path.unlink()

        return False



async def main():
    """Example usage of the arXiv client."""
    settings = get_settings()

    # Create arXiv client with explicit settings
    client = ArxivClient(settings=settings.arxiv)

    print("Fetching recent AI papers from arXiv...")
    papers = await client.fetch_papers(
        max_results=5,
    )

    for i, paper in enumerate(papers, 1):
        print(f"\n{i}. {paper.title}")
   #     print(f"   PDF: {paper.pdf_url}")
        print("-" * 80)


if __name__ == "__main__":
    asyncio.run(main())
