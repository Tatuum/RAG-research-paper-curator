from pydantic import BaseModel


class IngestRequest(BaseModel):
    date: str
    max_results: int = 300


class IngestResponse(BaseModel):
    papers_fetched: int
    papers_stored: int
    chunks_indexed: int
