from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    top_k: int = 5


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]
