import gradio as gr
import asyncio
import logging
from src.services.arxiv.arxiv_client import ArxivClient
from config import get_settings

logger = logging.getLogger(__name__)

async def search_papers():
    """Search for papers and return formatted titles."""
    try:
        settings = get_settings()
        client = ArxivClient(settings=settings.arxiv)
        print("Fetching recent AI papers from arXiv...")
        papers = await client.fetch_papers(
        max_results=5,
        )
        
        if not papers:
            return "No papers found."
        
        result = f"Found {len(papers)} papers:\n\n"
        for i, paper in enumerate(papers, 1):
            logger.debug(f"Processing paper {i}: {paper.title}")
            result += f"{i}. {paper.title}\n"
        
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