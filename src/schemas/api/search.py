from typing import Literal

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    size: int = Field(10, ge=1, le=50)
    categories: list[str] | None = None
    mode: Literal["bm25", "hybrid"] = "hybrid"
    latest: bool = False


class SearchHit(BaseModel):
    arxiv_id: str
    chunk_index: int
    chunk_text: str
    title: str
    authors: list[str]
    categories: list[str]
    published_date: str
    score: float


class SearchResponse(BaseModel):
    total: int
    hits: list[SearchHit]
    mode: str
