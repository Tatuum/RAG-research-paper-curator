import logging
from pathlib import Path
import pypdfium2 as pdfium

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

logger = logging.getLogger(__name__)

class DoclingParser:
    """Docling PDF parser for scientific document processing."""
    def __init__(
            self, 
            max_pages: int, 
            max_file_size_mb: int, 
            do_ocr: bool = False, 
            do_table_structure: bool = True):
        """Initialize DocumentConverter with optimized pipeline options.

        :param max_pages: Maximum number of pages to process
        :param max_file_size_mb: Maximum file size in MB
        :param do_ocr: Enable OCR for scanned PDFs (default: False, very slow)
        :param do_table_structure: Extract table structures (default: True)
        """
        # Configure pipeline options
        pipeline_options = PdfPipelineOptions(
            do_table_structure=do_table_structure,
            do_ocr=do_ocr,  # Usually disabled for speed
        )

        self._converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
        )
        self._warmed_up = False
        self.max_pages = max_pages
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024

    def _warm_up_models(self):
        """Pre-warm the models with a small dummy document to avoid cold start."""
        if not self._warmed_up:
            # This happens only once per DoclingParser instance
            self._warmed_up = True

    def _validate_pdf(self, pdf_path: Path) -> bool:
        """Comprehensive PDF validation including size and page limits.

        :param pdf_path: Path to PDF file
        :returns: True if PDF appears valid and within limits, False otherwise
        """
        try:
            # Check file exists and is not empty
            if pdf_path.stat().st_size == 0:
                logger.error(f"PDF file is empty: {pdf_path}")
                raise PDFValidationError(f"PDF file is empty: {pdf_path}")

            # Check file size limit
            file_size = pdf_path.stat().st_size
            if file_size > self.max_file_size_bytes:
                logger.warning(
                    f"PDF file size ({file_size / 1024 / 1024:.1f}MB) exceeds limit ({self.max_file_size_bytes / 1024 / 1024:.1f}MB), skipping processing"
                )
                raise PDFValidationError(
                    f"PDF file too large: {file_size / 1024 / 1024:.1f}MB > {self.max_file_size_bytes / 1024 / 1024:.1f}MB"
                )

            # Check if file starts with PDF header
            with open(pdf_path, "rb") as f:
                header = f.read(8)
                if not header.startswith(b"%PDF-"):
                    logger.error(f"File does not have PDF header: {pdf_path}")
                    raise PDFValidationError(f"File does not have PDF header: {pdf_path}")

            # Check page count limit
            pdf_doc = pdfium.PdfDocument(str(pdf_path))
            actual_pages = len(pdf_doc)
            pdf_doc.close()

            if actual_pages > self.max_pages:
                logger.warning(
                    f"PDF has {actual_pages} pages, exceeding limit of {self.max_pages} pages. Skipping processing to avoid performance issues."
                )
                raise PDFValidationError(f"PDF has too many pages: {actual_pages} > {self.max_pages}")

            return True

        except PDFValidationError:
            raise
        except Exception as e:
            logger.error(f"Error validating PDF {pdf_path}: {e}")
            raise PDFValidationError(f"Error validating PDF {pdf_path}: {e}")

