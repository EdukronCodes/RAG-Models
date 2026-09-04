from .base import RAGStrategy


class NaiveRAG(RAGStrategy):
    name = "naive_rag"

    def score(self, engine, query_terms, normalized_query, doc):
        return super().score(engine, query_terms, normalized_query, doc) + (0.05 if doc["source"] == "faq" else 0)

    def explanation(self):
        return "I used direct keyword matching across the support knowledge base to find the closest answer."
