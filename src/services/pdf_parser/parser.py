import logging
from .docling import DoclingParser
from pathlib import Path
from typing import Optional
from src.schemas.pdf_parser.models import PdfContent

logger = logging.getLogger(__name__)
class PDFParserService:
    "Main service for parsing PDFs."

    def __init__(self, 
                 max_pages: int, 
                 max_file_size_mb: int, 
                 do_ocr: bool = False, 
                 do_table_structure: bool = True):
        self.docling_parser = DoclingParser(max_pages=max_pages, max_file_size_mb=max_file_size_mb, do_ocr=do_ocr, do_table_structure=do_table_structure)

    async def parse_pdf(self, pdf_path: Path) -> Optional[PdfContent]:
        """Parse a PDF file and return the content."""
        return await self.docling_parser.parse_pdf(pdf_path)