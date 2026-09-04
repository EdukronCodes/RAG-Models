class RAGStrategy:
    name = "base_rag"

    def score(self, engine, query_terms, normalized_query, doc):
        return engine.keyword_score(query_terms, doc["search_text"])

    def explanation(self):
        return "I matched the request to the most relevant support context available."
