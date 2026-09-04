from .base import RAGStrategy


class CorrectiveRAG(RAGStrategy):
    name = "corrective_rag"

    def score(self, engine, query_terms, normalized_query, doc):
        score = super().score(engine, query_terms, normalized_query, doc) + (0.15 if doc["source"] == "faq" else 0.05)
        return score if query_terms.intersection(set(engine.normalize(doc["search_text"]).split())) else score - 0.4

    def explanation(self):
        return "I filtered weak or low-confidence matches and kept the most relevant evidence."
