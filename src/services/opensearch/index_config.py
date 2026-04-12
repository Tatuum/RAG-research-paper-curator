"""OpenSearch index configuration for papers."""

# Index name constant
PAPERS_INDEX = "arxiv-papers"

# Index mapping definition
PAPERS_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "index.knn": True,
    },
    "mappings": {
        "properties": {
            "arxiv_id": {"type": "keyword"},
            "title": {"type": "text"},
            "abstract": {"type": "text"},
            "authors": {"type": "keyword"},
            "categories": {"type": "keyword"},
            "published_date": {"type": "date"},
            "embedding": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                    "name": "hnsw",
                    "engine": "lucene",
                    "space_type": "cosine",
                },
            },
        }
    },
}
