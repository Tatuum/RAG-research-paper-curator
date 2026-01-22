import logging
from functools import lru_cache
from typing import Any, Tuple

import gradio as gr

from src.config import get_settings
from src.services.arxiv.arxiv_client import ArxivClient
from src.services.arxiv.factory import make_arxiv_client
from src.services.metadata_fetcher import make_metadata_fetcher
from src.services.pdf_parser.factory import make_pdf_parser_service
from src.services.pdf_parser.parser import PDFParserService

logger = logging.getLogger(__name__)
settings = get_settings()


@lru_cache(maxsize=1)
def get_cached_services() -> Tuple[Any, Any, Any]:
    """Get cached service instances using lru_cache for automatic memoization.

    :returns: Tuple of (arxiv_client, pdf_parser, metadata_fetcher)
    """
    logger.info("Initializing services (cached with lru_cache)")

    # Initialize core services
    arxiv_client = make_arxiv_client()
    pdf_parser = make_pdf_parser_service()

    # Create metadata fetcher with dependencies
    metadata_fetcher = make_metadata_fetcher(arxiv_client, pdf_parser)

    logger.info("All services initialized and cached with lru_cache")
    return arxiv_client, pdf_parser, metadata_fetcher


async def search_papers():
    """Search for papers and return formatted titles."""
    try:
        client = ArxivClient(settings=settings.arxiv)
        print("Fetching recent AI papers from arXiv...")
        papers = await client.fetch_papers(
            max_results=5,
        )

        if not papers:
            return "No papers found."

        result = f"Found {len(papers)} papers:\n\n"
        for i, paper in enumerate(papers, 1):
            logger.debug(f"Processing paper {i}: {paper.title}\n{paper.pdf_url}")
            result += f"{i}. {paper.title}\n{paper.pdf_url}\n"

        return result

    except Exception as e:
        return f"Error: {str(e)}"


async def show_context():
    """Show the first paragraph of each paper by parsing PDFs."""
    try:
        client = ArxivClient(settings=settings.arxiv)
        papers = await client.fetch_papers(max_results=3)  # Limit to 3 for testing

        if not papers:
            return "No papers found."

        # Initialize PDF parser
        pdf_parser = PDFParserService(
            max_pages=20,  # Limit pages for testing
            max_file_size_mb=50,
            do_ocr=False,
            do_table_structure=True,
        )

        result = f"Found {len(papers)} papers. Parsing PDFs...\n\n"

        for i, paper in enumerate(papers, 1):
            try:
                result += f"=== Paper {i}: {paper.title} ===\n"
                result += f"PDF URL: {paper.pdf_url}\n\n"

                # Download PDF using ArxivClient
                temp_path = await client.download_pdf(paper)

                if temp_path is None:
                    result += "Failed to download PDF.\n\n"
                    continue

                # Parse PDF
                pdf_content = await pdf_parser.parse_pdf(temp_path)

                if pdf_content and pdf_content.sections:
                    # Show first section or abstract
                    first_section = pdf_content.sections[0]
                    result += f"Section: {first_section.title}\n"
                    # Show first 500 characters of content
                    content_preview = first_section.content[:500]
                    if len(first_section.content) > 500:
                        content_preview += "..."
                    result += f"Content: {content_preview}\n\n"
                else:
                    result += "Could not extract structured content from PDF.\n"
                    if pdf_content and pdf_content.raw_text:
                        # Fallback to raw text
                        raw_preview = pdf_content.raw_text[:500]
                        if len(pdf_content.raw_text) > 500:
                            raw_preview += "..."
                        result += f"Raw text preview: {raw_preview}\n\n"
                    else:
                        result += "No content extracted from PDF.\n\n"

            except Exception as e:
                result += f"Error parsing paper {i}: {str(e)}\n\n"
                continue

        return result

    except Exception as e:
        return f"Error: {str(e)}"


async def test_metadata_fetcher():
    """Test the metadata fetcher."""
    try:
        arxiv_client, _, metadata_fetcher = get_cached_services()
        max_results = arxiv_client.max_results
        logger.info(f"Using default max_results from config: {max_results}")
        pdf_results = await metadata_fetcher.fetch_and_process_papers(max_results=max_results)
        return pdf_results
    except Exception as e:
        return f"Error: {str(e)}"


def main():
    with gr.Blocks() as interface:
        gr.Markdown("# arXiv Paper Search")

        search_btn = gr.Button("Start Search", variant="primary")
        output = gr.Textbox(label="Papers", lines=15)

        search_btn.click(fn=search_papers, outputs=output)

        context_btn = gr.Button("Show the first paragraph of each paper", variant="primary")
        context_output = gr.Textbox(label="Context", lines=15)

        context_btn.click(fn=test_metadata_fetcher, outputs=context_output)

    interface.launch(
        server_name="0.0.0.0",
        server_port=7861,  # Changed to avoid port conflict
        share=False,
        show_error=True,
        quiet=False,
    )


if __name__ == "__main__":
    main()
