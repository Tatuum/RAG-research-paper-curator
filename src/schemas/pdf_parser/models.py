from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Dict, Any
    
class ParserType(str, Enum):
    """PDF parser types."""

    DOCLING = "docling"

class PaperSection(BaseModel):
    """Represents a section of a paper."""

    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Section content")
    level: int = Field(default=1, description="Section hierarchy level")

class PdfContent(BaseModel):
    """PDF-specific content extracted by parsers like Docling."""

    sections: List[PaperSection] = Field(default_factory=list, description="Paper sections")
    raw_text: str = Field(..., description="Full extracted text")
    parser_used: ParserType = Field(..., description="Parser used for extraction")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Parser metadata")
