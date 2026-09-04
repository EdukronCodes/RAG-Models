from .base import RAGStrategy


class HybridRAG(RAGStrategy):
    name = "hybrid_rag"

    def score(self, engine, query_terms, normalized_query, doc):
        score = super().score(engine, query_terms, normalized_query, doc)
        return score + 0.12 * len(query_terms.intersection(set(doc["tags"])))

    def explanation(self):
        return "I combined keyword similarity with contextual support metadata to improve ranking."
