from typing import cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.paper import Paper
from src.schemas.arxiv.paper import PaperCreate


class PaperRepository:
    """Repository for Paper entity - handles all database operations."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, paper: PaperCreate) -> Paper:
        db_paper = Paper(**paper.model_dump())
        self.session.add(db_paper)
        self.session.flush()
        return db_paper

    def get_by_arxiv_id(self, arxiv_id: str) -> Paper | None:
        stmt = select(Paper).where(Paper.arxiv_id == arxiv_id)
        return cast(Paper | None, self.session.scalar(stmt))

    def get_all(self, limit: int = 100, offset: int = 0) -> list[Paper]:
        stmt = select(Paper).order_by(Paper.published_date.desc()).limit(limit).offset(offset)
        return cast(list[Paper], self.session.scalars(stmt).all())

    def update(self, paper: Paper) -> Paper:
        self.session.add(paper)
        self.session.flush()
        return paper

    def upsert(self, paper: PaperCreate) -> Paper:
        existing_paper = self.get_by_arxiv_id(paper.arxiv_id)
        if not existing_paper:
            return self.create(paper)
        else:
            for key, value in paper.model_dump(exclude_unset=True).items():
                setattr(existing_paper, key, value)
            return self.update(existing_paper)
