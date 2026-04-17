import logging

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
