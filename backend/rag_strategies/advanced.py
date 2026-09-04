from .base import RAGStrategy


class AdvancedRAG(RAGStrategy):
    name = "advanced_rag"

    def score(self, engine, query_terms, normalized_query, doc):
        score = super().score(engine, query_terms, normalized_query, doc)
        if doc["category"] in normalized_query:
            score += 0.25
        return score + 0.1 * len(query_terms & set(engine.normalize(doc["category"]).split()))

    def explanation(self):
        return "I used category-aware ranking and weighted query matching to improve the result quality."
