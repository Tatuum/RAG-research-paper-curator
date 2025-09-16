import asyncio
import logging
import time
import xml.etree.ElementTree as ET
from typing import List, Optional
from urllib.parse import urlencode

from paper import ArxivPaper
import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ArxivClient:
    """Minimal client for fetching papers from arXiv API."""

    def __init__(self, rate_limit_delay: float = 3.0, timeout_seconds: int = 30):
        self.base_url = "https://export.arxiv.org/api/query"
        self.rate_limit_delay = rate_limit_delay
        self.timeout_seconds = timeout_seconds
        self._last_request_time: Optional[float] = None

    async def _rate_limit(self):
        """Implement rate limiting to respect arXiv's 3-second delay requirement."""
        if self._last_request_time is not None:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - elapsed)
        self._last_request_time = time.time()

    async def fetch_papers(
        self,
        query: str = "cat:cs.AI",
        max_results: int = 10,
        start: int = 0,
    ) -> List[ArxivPaper]:
        """
        Fetch papers from arXiv API.

        Args:
            query: Search query (default: cs.AI category)
            max_results: Maximum number of papers to fetch
            start: Starting index for pagination

        Returns:
            List of ArxivPaper objects
        """
        await self._rate_limit()

        params = {
            "search_query": query,
            "start": start,
            "max_results": min(max_results, 2000),  # arXiv limit
        }
        safe = ":+[]"  # Don't encode :, +, [, ] characters needed for arXiv queries
        url = f"{self.base_url}?{urlencode(params, safe=safe)}"
        
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            return self._parse_response(response.text)

    def _parse_response(self, xml_content: str) -> List[ArxivPaper]:
        """Parse arXiv API XML response."""
        root = ET.fromstring(xml_content)
        
        # Define namespaces
        namespaces = {
            'atom': 'http://www.w3.org/2005/Atom',
            'arxiv': 'http://arxiv.org/schemas/atom'
        }
        
        papers = []
        
        # Find all entry elements
        for entry in root.findall('.//atom:entry', namespaces):
            try:
                # Extract paper ID
                paper_id = entry.find('atom:id', namespaces).text
                if paper_id:
                    paper_id = paper_id.split('/')[-1]  # Extract ID from URL
                
                # Extract title
                title_elem = entry.find('atom:title', namespaces)
                title = title_elem.text.strip() if title_elem is not None else ""
                
                # Extract abstract
                summary_elem = entry.find('atom:summary', namespaces)
                abstract = summary_elem.text.strip() if summary_elem is not None else ""
                
                
                paper = ArxivPaper(
                    paper_id=paper_id,
                    title=title,
                    abstract=abstract
                )
                papers.append(paper)
                
            except Exception as e:
                logger.warning(f"Failed to parse paper entry: {e}")
                continue
        
        return papers



async def main():
    """Example usage of the arXiv client."""
    client = ArxivClient()
    
    print("Fetching recent AI papers from arXiv...")
    papers = await client.fetch_papers(
        query="cat:cs.AI",
        max_results=5
    )
    
    for i, paper in enumerate(papers, 1):
        print(f"\n{i}. {paper.title}")
   #     print(f"   PDF: {paper.pdf_url}")
        print("-" * 80)


if __name__ == "__main__":
    asyncio.run(main()) 