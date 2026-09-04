from .base import RAGStrategy


class AgentRAG(RAGStrategy):
    name = "agent_rag"

    def score(self, engine, query_terms, normalized_query, doc):
        score = super().score(engine, query_terms, normalized_query, doc) + (0.2 if doc["source"] == "faq" else 0.1)
        issue_terms = {"refund", "billing", "order", "password", "shipping"}
        if issue_terms.intersection(query_terms):
            score += 0.15 if issue_terms.intersection(set(engine.normalize(doc["search_text"]).split())) else 0
        return score

    def explanation(self):
        return "I decomposed the request into issue and context signals before retrieving the best support answer."
