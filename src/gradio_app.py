import gradio as gr
import asyncio
import logging
import tempfile
import requests
from pathlib import Path
from src.services.arxiv.arxiv_client import ArxivClient
from src.services.pdf_parser.parser import PDFParserService
from config import get_settings
#from src.services.metadata_fetcher import MetadataFetcher

logger = logging.getLogger(__name__)
settings = get_settings()

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
            do_table_structure=True
        )
        
        result = f"Found {len(papers)} papers. Parsing PDFs...\n\n"
        
        for i, paper in enumerate(papers, 1):
            try:
                result += f"=== Paper {i}: {paper.title} ===\n"
                result += f"PDF URL: {paper.pdf_url}\n\n"
                
                # Download PDF to temporary file
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                    temp_path = Path(temp_file.name)
                    
                    # Download PDF
                    response = requests.get(paper.pdf_url, timeout=30)
                    response.raise_for_status()
                    temp_path.write_bytes(response.content)
                    
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
                    
                    # Clean up temp file
                    temp_path.unlink()
                    
            except Exception as e:
                result += f"Error parsing paper {i}: {str(e)}\n\n"
                continue
        
        return result
        
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
        
        context_btn.click(fn=show_context, outputs=context_output)
    
    interface.launch(
        server_name="0.0.0.0",
        server_port=7861,  # Changed to avoid port conflict
        share=False,
        show_error=True,
        quiet=False,
    )


if __name__ == "__main__":
    main()