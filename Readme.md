## Multi-RAG Customer Support

This Flask app provides eight independent retrieval strategies:
`naive_rag`, `advanced_rag`, `corrective_rag`, `agent_rag`, `adaptive_rag`,
`graph_rag`, `hybrid_rag`, and `multimodal_rag`. Each strategy lives in its
own module under `backend/rag_strategies/` and is selected from the UI.

### Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FLASK_SECRET_KEY="replace-with-a-long-random-value"
python app.py
```

Open `http://localhost:5000`, register an account, and sign in. User accounts,
login sessions, chat sessions, and messages are stored in SQLite at
`instance/app.db`. Set `DATABASE_PATH` to use a different database.

The chat API requires authentication and accepts `message`, `model`, and an
optional `session_id`. Session management is available through
`/api/sessions` and `/api/sessions/<id>`.

