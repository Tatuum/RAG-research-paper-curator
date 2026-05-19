"""OpenSearch index configuration for papers."""

# Index name constant
PAPERS_CHUNKS_INDEX = "arxiv-papers-chunks-v1"

# Index mapping definition
PAPERS_CHUNKS_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "index.knn": True,
        "analysis": {
            "analyzer": {
                "text_analyzer": {"type": "custom", "tokenizer": "standard", "filter": ["lowercase", "stop", "snowball"]},
            }
        },
    },
    "mappings": {
        "properties": {
            "arxiv_id": {"type": "keyword"},
            "chunk_index": {"type": "integer"},
            "chunk_text": {
                "type": "text",
                "analyzer": "text_analyzer",
            },
            "title": {
                "type": "text",
                "analyzer": "text_analyzer",
            },
            "authors": {"type": "keyword"},
            "categories": {"type": "keyword"},
            "published_date": {"type": "date"},
            "embedding": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                    "name": "hnsw",
                    "engine": "lucene",
                    "space_type": "l2",
                },
            },
        }
    },
}

HYBRID_RRF_PIPELINE = {
    "id": "hybrid-rrf-pipeline",
    "description": "Post processor for hybrid RRF search",
    "phase_results_processors": [
        {
            "score-ranker-processor": {
                "combination": {
                    "technique": "rrf",  # Reciprocal Rank Fusion
                    "rank_constant": 60,  # Default k=60 for RRF formula: 1/(k+rank)
                }
            }
        }
    ],
}
