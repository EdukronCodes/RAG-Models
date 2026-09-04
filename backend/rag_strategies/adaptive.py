from .base import RAGStrategy


class AdaptiveRAG(RAGStrategy):
    name = "adaptive_rag"

    def score(self, engine, query_terms, normalized_query, doc):
        return super().score(engine, query_terms, normalized_query, doc) + (0.2 if len(query_terms) <= 3 else 0.1)

    def explanation(self):
        return "I adjusted retrieval depth based on how complex the issue appears to be."
