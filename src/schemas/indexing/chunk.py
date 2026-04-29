from pydantic import BaseModel


class TextChunk(BaseModel):
    """A chunk of text to index."""

    arxiv_id: str
    chunk_index: int
    chunk_text: str
