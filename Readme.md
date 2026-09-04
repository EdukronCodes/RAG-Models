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

For local development, the first database initialization creates this default
account: username `admin`, password `admin1234`. Override it with
`DEFAULT_USERNAME` and `DEFAULT_PASSWORD`, or set either variable to an empty
value to disable automatic seeding. Change or disable this account before
production deployment.

The chat API requires authentication and accepts `message`, `model`, and an
optional `session_id`. Session management is available through
`/api/sessions` and `/api/sessions/<id>`.

### Architecture and observability

- `backend/rag_strategies/` contains one strategy implementation per RAG type.
- `backend/rag_pipeline.py` runs retrieval and generation as a LangGraph graph
	using LangChain `RunnableLambda` nodes.
- `backend/observability.py` emits JSON request/RAG events with request IDs.
	Counters are available at `/metrics`; health is available at `/health`.
- The browser workspace uses React 18 for the account control and standard
	HTML/CSS/JavaScript for the chat surface, keeping the page lightweight.

For production, use `gunicorn --bind 0.0.0.0:5000 app:app`, set a strong
`FLASK_SECRET_KEY`, and put the service behind HTTPS and a reverse proxy. For
larger deployments, move SQLite to PostgreSQL and send structured logs to an
OpenTelemetry-compatible collector or LangSmith by configuring a LangChain
tracing environment.

