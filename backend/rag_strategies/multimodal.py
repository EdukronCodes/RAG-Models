from .base import RAGStrategy


class MultimodalRAG(RAGStrategy):
    name = "multimodal_rag"

    def score(self, engine, query_terms, normalized_query, doc):
        score = super().score(engine, query_terms, normalized_query, doc)
        if {"image", "visual", "screen"}.intersection(query_terms):
            score += 0.1
        return score + (0.08 if doc["source"] == "conversation" else 0)

    def explanation(self):
        return "I combined textual retrieval with multimodal context cues and support examples for richer grounding."
