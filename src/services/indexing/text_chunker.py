import logging

from src.schemas.indexing.chunk import TextChunk

logger = logging.getLogger(__name__)


class TextChunker:
    """Chunks paper text into segments for OpenSearch indexing.

    Uses section-aware chunking with three-tier rules:
    - < 100 words: combine with adjacent small sections
    - 100-800 words: single chunk (sweet spot)
    - > 800 words: split with word overlap
    - No sections: fallback to word-based chunking on raw_text
    """

    def __init__(self, chunk_size: int = 800, overlap_size: int = 100, min_chunk_size: int = 100):
        if overlap_size >= chunk_size:
            raise ValueError("overlap_size must be less than chunk_size")
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.min_chunk_size = min_chunk_size

        logger.info(f"TextChunker initialized: chunk_size={chunk_size}, overlap={overlap_size}, min={min_chunk_size}")

    def chunk_paper(
        self,
        arxiv_id: str,
        title: str,
        abstract: str,
        sections: list[dict],
        raw_text: str,
    ) -> list[TextChunk]:
        """Chunk paper using hybrid section-based approach.
        Strategy:
        - For sections 100-800 words: Use as single chunk with title+abstract
        - For sections <100 words: Combine with adjacent sections
        - For sections >800 words: Split using traditional word-based chunking
        - Fallback to traditional chunking if no sections available
        """
        # Create header (title + abstract)
        header = f"{title}\n\nAbstract: {abstract}\n\n"

        if sections:
            try:
                section_chunks = self._chunk_by_sections(header, arxiv_id, sections)
                if section_chunks:
                    logger.info(f"Created {len(section_chunks)} section-based chunks for {arxiv_id}")
                    return section_chunks
            except Exception as e:
                logger.warning(f"Section-based chunking failed for {arxiv_id}: {e}")

        logger.info(f"Using traditional word-based chunking for paper {arxiv_id}")
        return self._chunk_raw_text(header, arxiv_id, raw_text)

    def _chunk_by_sections(self, header: str, arxiv_id: str, sections: list[dict]) -> list[TextChunk]:
        """implement section-based chunking strategy
        :param header: Header constructed from title and abstract
        :param arxiv_id: ArXiv ID
        :param sections: Sections data
        :returns: List of text chunks
        """
        chunks: list[TextChunk] = []
        buffer: list[str] = []

        for section in sections:
            section_text = f"{section['title']}\n{section['content']}"
            section_words = len(section_text.split())
            if section_words < self.min_chunk_size:
                # Tier 1: small -accumulate in buffer
                buffer.append(section_text)
                if len(" ".join(buffer).split()) >= self.min_chunk_size:
                    joined = " ".join(buffer)
                    chunks.append(
                        TextChunk(
                            arxiv_id=arxiv_id,
                            chunk_index=len(chunks),
                            chunk_text=f"{header}{joined}",
                        )
                    )
                    buffer = []
            elif section_words <= self.chunk_size:
                # Tier 2: medium -flush buffer, then create one chunk
                if buffer:
                    joined = " ".join(buffer)
                    chunks.append(
                        TextChunk(
                            arxiv_id=arxiv_id,
                            chunk_index=len(chunks),
                            chunk_text=f"{header}{joined}",
                        )
                    )
                    buffer = []
                chunks.append(
                    TextChunk(
                        arxiv_id=arxiv_id,
                        chunk_index=len(chunks),
                        chunk_text=f"{header}{section_text}",
                    )
                )
            else:
                # Tier 3: large - flush buffer, then split with overlap
                if buffer:
                    joined = " ".join(buffer)
                    chunks.append(
                        TextChunk(
                            arxiv_id=arxiv_id,
                            chunk_index=len(chunks),
                            chunk_text=f"{header}{joined}",
                        )
                    )
                    buffer = []
                words = section_text.split()
                i = 0
                while i < len(words):
                    chunk_words = words[i : i + self.chunk_size]
                    chunks.append(
                        TextChunk(
                            arxiv_id=arxiv_id,
                            chunk_index=len(chunks),
                            chunk_text=f"{header}{' '.join(chunk_words)}",
                        )
                    )
                    i += self.chunk_size - self.overlap_size
                    if i + self.overlap_size >= len(words):
                        break
        if buffer:
            joined = " ".join(buffer)
            chunks.append(
                TextChunk(
                    arxiv_id=arxiv_id,
                    chunk_index=len(chunks),
                    chunk_text=f"{header}{joined}",
                )
            )
        return chunks

    def _chunk_raw_text(self, header: str, arxiv_id: str, raw_text: str) -> list[TextChunk]:
        """Word-based fallback chunking when no sections are available."""
        if not raw_text or not raw_text.strip():
            logger.warning(f"Empty raw_text for {arxiv_id}")
            return []
        words = raw_text.split()

        if len(words) < self.min_chunk_size:
            return [
                TextChunk(
                    arxiv_id=arxiv_id,
                    chunk_index=0,
                    chunk_text=f"{header}{raw_text}",
                )
            ]

        chunks: list[TextChunk] = []
        i = 0
        while i < len(words):
            chunk_words = words[i : i + self.chunk_size]
            chunks.append(
                TextChunk(
                    arxiv_id=arxiv_id,
                    chunk_index=len(chunks),
                    chunk_text=f"{header}{' '.join(chunk_words)}",
                )
            )
            i += self.chunk_size - self.overlap_size
            if i + self.overlap_size >= len(words):
                break
        logger.info(f"Raw-text chunking for {arxiv_id}: {len(words)} words -> {len(chunks)} chunks")
        return chunks
