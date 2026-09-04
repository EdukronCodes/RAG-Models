import time

from backend.observability import record_rag_run

try:
    from langchain_core.runnables import RunnableLambda
    from langgraph.graph import END, StateGraph
except ImportError:  # The fallback keeps health checks useful before install.
    RunnableLambda = None
    StateGraph = None
    END = "__end__"


class RAGPipeline:
    """LangGraph orchestration boundary for retrieval and answer generation."""

    def __init__(self, engine):
        self.engine = engine
        self.graph = self._build_graph() if StateGraph else None

    def _build_graph(self):
        workflow = StateGraph(dict)
        workflow.add_node("retrieve", RunnableLambda(self._retrieve))
        workflow.add_node("generate", RunnableLambda(self._generate))
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)
        return workflow.compile()

    def _retrieve(self, state):
        state["results"] = self.engine._retrieve(state["query"], state["strategy"])
        return state

    def _generate(self, state):
        state["result"] = self.engine._build_answer(state["query"], state["results"], state["strategy"])
        return state

    def invoke(self, query, strategy):
        started = time.perf_counter()
        try:
            state = {"query": query, "strategy": strategy}
            if self.graph:
                result = self.graph.invoke(state)["result"]
            else:
                result = self._generate(self._retrieve(state))["result"]
            record_rag_run(strategy, (time.perf_counter() - started) * 1000)
            return result
        except Exception:
            record_rag_run(strategy, (time.perf_counter() - started) * 1000, success=False)
            raise