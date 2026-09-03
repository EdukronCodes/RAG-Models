from flask import Flask, jsonify, render_template, request

from backend.rag_engine import SupportRAGEngine

app = Flask(__name__)
engine = SupportRAGEngine()

MODEL_OPTIONS = [
    "naive_rag",
    "advanced_rag",
    "corrective_rag",
    "agent_rag",
    "adaptive_rag",
    "graph_rag",
    "hybrid_rag",
    "multimodal_rag",
]


@app.route("/")
def index():
    return render_template("index.html", models=MODEL_OPTIONS)


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "multi-rag-chatbot", "models": MODEL_OPTIONS})


@app.route("/api/chat", methods=["POST"])
def chat():
    payload = request.get_json(silent=True) or {}
    user_query = (payload.get("message") or "").strip()
    selected_model = (payload.get("model") or "naive_rag").strip().lower()

    if not user_query:
        return jsonify({"error": "Please provide a question or issue description."}), 400

    if selected_model not in MODEL_OPTIONS:
        return jsonify({"error": "Unsupported model selection."}), 400

    result = engine.answer_query(user_query, selected_model)
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
