import asyncio
from arxiv_client import ArxivClient


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
