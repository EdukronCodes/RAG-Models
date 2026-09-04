import json
import os

from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for

from backend.auth import AuthStore, load_user, login_required
from backend.observability import configure_observability, metrics_snapshot
from backend.rag_engine import SupportRAGEngine

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-this-secret")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
store = AuthStore()
engine = SupportRAGEngine()
configure_observability(app)

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


@app.before_request
def authenticate_request():
    load_user(store)


@app.route("/")
def index():
    if not g.user:
        return redirect(url_for("login"))
    return render_template("index.html", models=MODEL_OPTIONS, user=g.user)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("auth.html", mode="login")
    payload = request.get_json(silent=True) or request.form
    user = store.authenticate(payload.get("username", ""), payload.get("password", ""))
    if not user:
        return jsonify({"error": "Invalid username or password."}), 401
    session["login_session"] = store.create_login_session(user["id"])
    return jsonify({"user": {"id": user["id"], "username": user["username"]}})


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("auth.html", mode="register")
    payload = request.get_json(silent=True) or request.form
    try:
        user = store.create_user(payload.get("username", ""), payload.get("password", ""))
    except (TypeError, ValueError) as error:
        return jsonify({"error": str(error)}), 400
    session["login_session"] = store.create_login_session(user["id"])
    return jsonify({"user": {"id": user["id"], "username": user["username"]}}), 201


@app.post("/logout")
def logout():
    store.delete_login_session(session.pop("login_session", None))
    return jsonify({"ok": True})


@app.get("/api/me")
def me():
    return jsonify({"user": g.user}) if g.user else (jsonify({"user": None}), 401)


@app.get("/api/sessions")
@login_required
def list_sessions():
    return jsonify({"sessions": store.list_chat_sessions(g.user["id"])})


@app.post("/api/sessions")
@login_required
def create_chat_session():
    payload = request.get_json(silent=True) or {}
    return jsonify({"session": store.create_chat_session(g.user["id"], payload.get("title", "New support session"))}), 201


@app.get("/api/sessions/<int:chat_id>")
@login_required
def get_session_messages(chat_id):
    messages = store.get_messages(g.user["id"], chat_id)
    if messages is None:
        return jsonify({"error": "Session not found."}), 404
    return jsonify({"messages": messages})


@app.delete("/api/sessions/<int:chat_id>")
@login_required
def delete_chat_session(chat_id):
    if not store.delete_chat_session(g.user["id"], chat_id):
        return jsonify({"error": "Session not found."}), 404
    return jsonify({"ok": True})


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "multi-rag-chatbot", "models": MODEL_OPTIONS, "langgraph": engine.pipeline.graph is not None})


@app.get("/metrics")
def metrics():
    return jsonify(metrics_snapshot())


@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    if not g.user:
        return jsonify({"error": "Authentication required."}), 401
    payload = request.get_json(silent=True) or {}
    user_query = (payload.get("message") or "").strip()
    selected_model = (payload.get("model") or "naive_rag").strip().lower()
    chat_id = payload.get("session_id")

    if not user_query:
        return jsonify({"error": "Please provide a question or issue description."}), 400

    if selected_model not in MODEL_OPTIONS:
        return jsonify({"error": "Unsupported model selection."}), 400
    if not chat_id:
        chat_id = store.create_chat_session(g.user["id"], user_query[:60])["id"]
    if not store.add_message(g.user["id"], chat_id, "user", user_query):
        return jsonify({"error": "Chat session not found."}), 404

    result = engine.answer_query(user_query, selected_model)
    store.add_message(g.user["id"], chat_id, "assistant", result["answer"], json.dumps(result))
    result["session_id"] = chat_id
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
