from contextlib import contextmanager

from src.services.langfuse.client import LangfuseTracer


class RAGTracer:
    def __init__(self, tracer: LangfuseTracer):
        self.tracer = tracer

    @contextmanager
    def trace_request(self, query: str):
        if not self.tracer.client:
            yield None
            return

        # Start a new trace span
        with self.tracer.client.start_as_current_observation(as_type="span", name="RAG Query", input={"query": query}) as root:
            yield root
        self.tracer.flush()

    @contextmanager
    def trace_search(self, query: str):
        if not self.tracer.client:
            yield None
            return

        # Start a new trace span
        with self.tracer.client.start_as_current_observation(as_type="span", name="Search", input={"query": query}) as span:
            yield span

    @contextmanager
    def trace_generation(self, prompt: str, model: str):
        if not self.tracer.client:
            yield None
            return

        # Start a new trace span
        with self.tracer.client.start_as_current_observation(
            as_type="generation", model=model, name="Generation with LLM", input={"prompt": prompt}
        ) as span:
            yield span
