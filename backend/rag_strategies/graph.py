from .base import RAGStrategy


class GraphRAG(RAGStrategy):
    name = "graph_rag"

    def score(self, engine, query_terms, normalized_query, doc):
        score = super().score(engine, query_terms, normalized_query, doc)
        connected = engine.graph.get(doc["category"], set())
        return score + (0.18 if query_terms.intersection(connected) else 0)

    def explanation(self):
        return "I used linked support concepts and related categories to improve retrieval context."
