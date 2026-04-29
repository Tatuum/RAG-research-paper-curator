"""OpenSearch index configuration for papers."""

# Index name constant
PAPERS_CHUNKS_INDEX = "arxiv-papers-chunks-v1"

# Index mapping definition
PAPERS_CHUNKS_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "index.knn": True,
    },
    "mappings": {
        "properties": {
            "arxiv_id": {"type": "keyword"},
            "chunk_index": {"type": "integer"},
            "chunk_text": {"type": "text"},
            "title": {"type": "text"},
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
