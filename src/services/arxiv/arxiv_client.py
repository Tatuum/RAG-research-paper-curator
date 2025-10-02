import asyncio
import logging
import time
import xml.etree.ElementTree as ET
from typing import List, Optional
from urllib.parse import urlencode
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
            
                return self._parse_response(response.text)
            
        except httpx.TimeoutException as e:
            logger.error(f"arXiv API timeout: {e}")
            raise ArxivAPITimeoutError(f"arXiv API request timed out: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"arXiv API HTTP error: {e}")
            raise ArxivAPIException(f"arXiv API returned error {e.response.status_code}: {e}")
        except Exception as e:
            logger.error(f"Failed to fetch papers from arXiv: {e}")
            raise ArxivAPIException(f"Unexpected error fetching papers from arXiv: {e}")

    def _parse_response(self, xml_content: str) -> List[ArxivPaper]:
        """Parse arXiv API XML response."""
        root = ET.fromstring(xml_content)
        
        papers = []
        
        # Find all entry elements
        entries = root.findall('.//atom:entry', self.namespaces)
        total_entries = len(entries)
        logger.info(f"Found {total_entries} entries in XML response")
        for i, entry in enumerate(entries, 1):
            logger.info(f"Processing entry {i}/{total_entries}")
            try:
                # Extract paper ID
                paper_id = entry.find('atom:id', self.namespaces).text
                if paper_id:
                    paper_id = paper_id.split('/')[-1]  # Extract ID from URL
                    #logger.info(f"Fetched {paper_id} paper from arXiv")

                # Extract title
                title_elem = entry.find('atom:title', self.namespaces)
                title = title_elem.text.strip() if title_elem is not None else ""
                #logger.info(f"Fetched {title} paper from arXiv")

                #Extract authors
                authors = []
                author_elems = entry.findall("atom:author", self.namespaces)
                #logger.info(f"Entry {i}: Found {len(author_elems)} author elements")

                for j, author in enumerate(author_elems):
                    name_elem = author.find("atom:name", self.namespaces)
                    name = name_elem.text.strip() if name_elem is not None and name_elem.text else ""
                    if name:
                        authors.append(name)
               # logger.info(f"Entry {i}: Extracted {len(authors)} authors")
            
                
                # Extract abstract
                summary_elem = entry.find('atom:summary', self.namespaces)
                abstract = summary_elem.text.strip() if summary_elem is not None else ""
                

                # Extract PDF URL
                pdf_url = ""
                for link in entry.findall("atom:link", self.namespaces):
                    if link.get("type") == "application/pdf":
                        url = link.get("href", "")
                        # Convert HTTP to HTTPS for arXiv URLs
                        if url.startswith("http://arxiv.org/"):
                            url = url.replace("http://arxiv.org/", "https://arxiv.org/")
                        pdf_url = url
                       # logger.info(f"Entry {i}: Found PDF URL: {pdf_url}")
                        break
                    
                paper = ArxivPaper(
                    paper_id=paper_id,
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    pdf_url=pdf_url
                )
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