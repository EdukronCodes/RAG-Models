import json
import logging
import time
import uuid
from collections import Counter

from flask import g, request

logger = logging.getLogger("rag_app")
logging.basicConfig(level=logging.INFO, format="%(message)s")

_metrics = Counter()


def configure_observability(app):
    @app.before_request
    def start_request_trace():
        g.request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        g.request_started_at = time.perf_counter()
        _metrics["http_requests_total"] += 1

    @app.after_request
    def finish_request_trace(response):
        duration_ms = round((time.perf_counter() - g.request_started_at) * 1000, 2)
        response.headers["X-Request-ID"] = g.request_id
        _metrics[f"http_status_{response.status_code}"] += 1
        logger.info(json.dumps({
            "event": "http_request",
            "request_id": g.request_id,
            "method": request.method,
            "path": request.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
        }))
        return response


def record_rag_run(strategy, duration_ms, success=True):
    _metrics["rag_runs_total"] += 1
    _metrics[f"rag_strategy_{strategy}_total"] += 1
    _metrics["rag_runs_failed_total" if not success else "rag_runs_succeeded_total"] += 1
    logger.info(json.dumps({
        "event": "rag_run",
        "strategy": strategy,
        "duration_ms": round(duration_ms, 2),
        "success": success,
    }))


def metrics_snapshot():
    return dict(_metrics)