from typing import Any


class QueryBuilder:
    def __init__(self, query: str, size: int = 10, categories: list[str] | None = None, latest: bool = False):
        self.query = query
        self.size = size
        self.categories = categories
        self.latest = latest

    def build(self) -> dict[str, Any]:
        """Build the complete OpenSearch query.

        :returns: Complete query dictionary ready for OpenSearch
        """
        query_body = {
            "query": self._build_query(),
            "size": self.size,
            "_source": {"excludes": ["embedding"]},
        }
        sort = self._build_sort()
        if sort:
            query_body["sort"] = sort
        return query_body

    def _build_query(self) -> dict[str, Any]:
        must_clauses = [
            {
                "multi_match": {
                    "query": self.query,
                    "fields": ["chunk_text^1", "title^3"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            }
        ]
        bool_query: dict = {"must": must_clauses}
        if self.categories:
            bool_query["filter"] = [{"terms": {"categories": self.categories}}]
        return {"bool": bool_query}

    def _build_sort(self) -> list | None:
        if self.latest:
            return [{"published_date": {"order": "desc"}}]
        return None
