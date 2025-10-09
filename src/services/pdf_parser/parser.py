import logging
from .docling import DoclingParser
from pathlib import Path
from typing import Optional
from src.schemas.pdf_parser.models import PdfContent
from src.exceptions import PDFValidationError, PDFParsingException

logger = logging.getLogger(__name__)

class PDFParserService:
    "Main service for parsing PDFs."

    def __init__(self, 
                 max_pages: int, 
                 max_file_size_mb: int, 
                 do_ocr: bool = False, 
                 do_table_structure: bool = True):
        
        self.parser_service = DoclingParser(max_pages=max_pages, max_file_size_mb=max_file_size_mb, do_ocr=do_ocr, do_table_structure=do_table_structure)

    async def parse_pdf(self, pdf_path: Path) -> Optional[PdfContent]:
        """Parse a PDF file and return the content.
        :param pdf_path: Path to PDF file
        :returns: PdfContent object or None if parsing failed
        """
        if not pdf_path.exists():
            logger.error(f"PDF file not found: {pdf_path}")
            raise PDFValidationError(f"PDF file not found: {pdf_path}")

        try:
            result = await self.parser_service.parse_pdf(pdf_path)
            if result:
                logger.info(f"Parsed {pdf_path.name}")
                return result
            else:
                logger.error(f"Docling parsing returned no result for {pdf_path.name}")
                raise PDFParsingException(f"Docling parsing returned no result for {pdf_path.name}")

        except (PDFValidationError, PDFParsingException):
            raise
        except Exception as e:
            logger.error(f"Docling parsing error for {pdf_path.name}: {e}")
            raise PDFParsingException(f"Docling parsing error for {pdf_path.name}: {e}")
    