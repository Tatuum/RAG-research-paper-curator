from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ArxivPaper(BaseModel):
    """Schema for arXiv API response data."""

    paper_id: str = Field(..., description="arXiv paper ID")
    title: str = Field(..., description="Paper title")
    abstract: str = Field(..., description="Paper abstract")
