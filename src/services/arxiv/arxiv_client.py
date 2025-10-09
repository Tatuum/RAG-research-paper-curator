import asyncio
import logging
import time
import xml.etree.ElementTree as ET
from typing import List, Optional
from functools import cached_property
from urllib.parse import urlencode
from pathlib import Path
from src.config import get_settings
from src.schemas.arxiv.paper import ArxivPaper
from src.exceptions import ArxivAPIException, ArxivAPITimeoutError, ArxivAPIRateLimitError, ArxivParseError
import httpx
from src.config import ArxivSettings
from pydantic import BaseModel

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
            raise ArxivAPITimeoutError(f"arXiv API request timed out: {e}")
        
        except httpx.HTTPStatusError as e:
            logger.error(f"arXiv API HTTP error: {e}")
            raise ArxivAPIException(f"arXiv API returned error {e.response.status_code}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to fetch papers from arXiv: {e}")
            raise ArxivAPIException(f"Unexpected error fetching papers from arXiv: {e}")
    def _parse_single_entry(self, entry: ET.Element) -> Optional[ArxivPaper]:
        """
        Parse a single entry from arXiv XML response.

        Args:
            entry: XML entry element

        Returns:
            ArxivPaper object or None if parsing fails
        """

        try:
            # Extract basic metadata
            arxiv_id = self._get_arxiv_id(entry)
            if not arxiv_id:
                return None
            

        except Exception as e:
            logger.error(f"Failed to parse entry: {e}")
            return None
        
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
    def __parse_single_entry(self, entry: ET.Element) -> Optional[ArxivPaper]:
        """
        Parse a single entry from arXiv XML response.

        Args:
            entry: XML entry element

        Returns:
            ArxivPaper object or None if parsing fails
        """
        try:

            # Extract paper ID
            paper_id = entry.find('atom:id', self.namespaces)
            if paper_id and paper_id.text:
                paper_id = paper_id.text.split('/')[-1]  # Extract ID from URL
            else: return None   #logger.info(f"Fetched {paper_id} paper from arXiv")

            

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
                
            paper = ArxivPaper(
                paper_id=paper_id,
                title=title,
                abstract=abstract,
                authors=authors,
                pdf_url=pdf_url
            )
            return paper
        
        except ET.ParseError as e:
            logger.error(f"Failed to parse arXiv XML response: {e}")
            raise ArxivParseError(f"Failed to parse arXiv XML response: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing arXiv response: {e}")
            raise ArxivParseError(f"Unexpected error parsing arXiv response: {e}")
        
    def _parse_response(self, xml_content: str) -> List[ArxivPaper]:
        """Parse arXiv API XML response."""
        root = ET.fromstring(xml_content)
        
        papers = []
        
        # Find all entry elements
        entries = root.findall('.//atom:entry', self.namespaces)
        total_entries = len(entries)
        logger.info(f"Found {total_entries} entries in XML response")
        for i, entry in entries:
            logger.info(f"Processing entry {i}/{total_entries}")
            
                papers.append(paper)
                
            except Exception as e:
                logger.warning(f"Failed to parse paper entry: {e}")
                continue
        #logger.info(f"Returning {len(papers)} papers")
        return papers



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