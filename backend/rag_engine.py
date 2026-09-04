import json
import os
import re
from collections import defaultdict

from backend.rag_strategies import STRATEGIES

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_PATH = os.path.join(ROOT_DIR, "customer_support_dataset.json")
FAQ_PATH = os.path.join(ROOT_DIR, "datasets", "customer_support", "customer_support_faq.json")
CONVO_PATH = os.path.join(ROOT_DIR, "datasets", "customer_support", "customer_support_conversations.json")


def normalize_text(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


class SupportRAGEngine:
    def __init__(self):
        self.documents = self._load_documents()
        self.graph = self._build_graph()

    def _load_documents(self):
        docs = []

        dataset_paths = [DATASET_PATH, FAQ_PATH, CONVO_PATH]
        for path in dataset_paths:
            if not os.path.exists(path):
                continue
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)

            if "faq" in data:
                for item in data["faq"]:
                    docs.append({
                        "id": item.get("faq_id", "faq"),
                        "title": item.get("question", "FAQ question"),
                        "answer": item.get("answer", ""),
                        "category": item.get("category", "general"),
                        "source": "faq",
                        "tags": item.get("tags", []),
                        "search_text": f"{item.get('question', '')} {item.get('answer', '')} {item.get('category', '')}"
                    })

            if "faqs" in data:
                for item in data["faqs"]:
                    docs.append({
                        "id": item.get("faq_id", "faq"),
                        "title": item.get("question", "FAQ question"),
                        "answer": item.get("answer", ""),
                        "category": item.get("category", "general"),
                        "source": "faq",
                        "tags": item.get("tags", []),
                        "search_text": f"{item.get('question', '')} {item.get('answer', '')} {item.get('category', '')}"
                    })

            if "conversations" in data:
                for conv in data["conversations"]:
                    text_blocks = []
                    for message in conv.get("messages", []):
                        text_blocks.append(message.get("text", ""))
                    combined_text = " ".join(text_blocks)
                    docs.append({
                        "id": conv.get("conversation_id", "conv"),
                        "title": f"{conv.get('intent', 'support')} - {conv.get('category', 'general')}",
                        "answer": conv.get("conversation_summary", combined_text[:250]),
                        "category": conv.get("category", "general"),
                        "source": "conversation",
                        "tags": conv.get("tags", []),
                        "search_text": f"{combined_text} {conv.get('intent', '')} {conv.get('category', '')}"
                    })

            if "conversations" not in data and "conversation_id" in data:
                # handle nested root dataset structure in original file.
                for conv in data.get("conversations", []):
                    text_blocks = []
                    for message in conv.get("messages", []):
                        text_blocks.append(message.get("text", ""))
                    combined_text = " ".join(text_blocks)
                    docs.append({
                        "id": conv.get("conversation_id", "conv"),
                        "title": f"{conv.get('intent', 'support')} - {conv.get('category', 'general')}",
                        "answer": conv.get("resolution", {}).get("summary", combined_text[:250]),
                        "category": conv.get("category", "general"),
                        "source": "conversation",
                        "tags": conv.get("tags", []),
                        "search_text": f"{combined_text} {conv.get('intent', '')} {conv.get('category', '')}"
                    })

        # fallback docs if no data loaded
        if not docs:
            docs = [
                {"id": "fallback-1", "title": "General support guidance", "answer": "Please check your account status, payment details, and order history. If the problem continues, contact support with your order number.", "category": "general", "source": "faq", "tags": ["support"], "search_text": "support account payment order contact"}
            ]

        return docs

    def _build_graph(self):
        graph = defaultdict(set)
        stop_words = {
            "the", "and", "for", "with", "from", "into", "that", "this", "your",
            "have", "what", "when", "where", "why", "how", "can", "could", "please",
            "will", "need", "issue", "problem", "support", "customer"
        }
        for doc in self.documents:
            category = doc["category"]
            graph[category].add(doc["title"])
            for token in re.findall(r"[a-zA-Z][a-zA-Z0-9_]{2,}", normalize_text(doc["search_text"])):
                if token in stop_words:
                    continue
                graph[token].add(category)
                graph[category].add(token)
        return dict(graph)

    def normalize(self, text):
        return normalize_text(text)

    def keyword_score(self, query_terms, doc_text):
        doc_terms = set(normalize_text(doc_text).split())
        matches = 0
        for term in query_terms:
            if term in doc_terms:
                matches += 1
        total = max(1, len(query_terms))
        return matches / total

    def _retrieve(self, query, strategy):
        normalized_query = normalize_text(query)
        query_terms = set(normalized_query.split())
        scored = []
        strategy_impl = STRATEGIES[strategy]

        for doc in self.documents:
            score = strategy_impl.score(self, query_terms, normalized_query, doc)

            if score > 0:
                scored.append({"score": round(score, 4), "doc": doc})

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:5]

    def _build_answer(self, query, top_results, strategy):
        query_lower = query.lower()
        if not top_results:
            return "I could not find a strong match in the support knowledge base. Please check your order number, plan, or error details and I can help narrow the issue."

        primary = top_results[0]["doc"]
        support_text = primary["answer"]

        explanation = STRATEGIES[strategy].explanation()

        if len(top_results) > 1:
            secondary = top_results[1]["doc"]["answer"]
            answer = f"{support_text} Additional context: {secondary[:250]}"
        else:
            answer = support_text

        if "refund" in query_lower or "billing" in query_lower:
            answer = answer + " Please confirm your order number, billing date, and payment method so I can verify the exact issue."
        elif "password" in query_lower or "login" in query_lower:
            answer = answer + " If the reset email is expired, request a fresh reset link and clear any stale tokens."
        elif "order" in query_lower or "shipping" in query_lower:
            answer = answer + " Please share your tracking number or order ID if you want a more precise delivery update."
        elif "subscription" in query_lower or "plan" in query_lower:
            answer = answer + " I can also help compare plans and explain billing cycles if needed."

        return {
            "answer": answer,
            "strategy": strategy,
            "retrieved_count": len(top_results),
            "confidence": round(min(0.99, max(0.35, top_results[0]["score"] + 0.35)), 2),
            "sources": [
                {
                    "title": item["doc"]["title"],
                    "category": item["doc"]["category"],
                    "source": item["doc"]["source"],
                    "score": item["score"],
                }
                for item in top_results[:3]
            ],
            "explanation": explanation,
        }

    def answer_query(self, query, strategy_name):
        strategy = strategy_name.lower().replace(" ", "_")
        if strategy not in {
            "naive_rag",
            "advanced_rag",
            "corrective_rag",
            "agent_rag",
            "adaptive_rag",
            "graph_rag",
            "hybrid_rag",
            "multimodal_rag",
        }:
            strategy = "naive_rag"

        top_results = self._retrieve(query, strategy)
        payload = self._build_answer(query, top_results, strategy)
        payload["model"] = strategy
        payload["query"] = query
        return payload
