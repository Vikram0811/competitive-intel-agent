"""
AgentOps instrumentation shim for competitive-intel-agent.

Same pattern as agentic-rag-orchestrator's core/observability.py — see that
file's docstring for the full rationale. Short version: `trace(...)` opens
one top-level AgentOps trace per request and stores it in a contextvar;
`span(...)` attaches to whatever trace is currently active, wherever it's
called from, without needing a client object threaded through every
function signature (agent/nodes.py, agent/graph.py's tool node, etc.).

Fails safe by design: if agentops-client isn't installed, or the AgentOps
server is unreachable, every function here becomes a no-op. Instrumentation
must never be able to break the agent it's observing.
"""

import contextlib
import contextvars
import logging
import os

logger = logging.getLogger("agentops.competitive_intel_agent")

_current_trace = contextvars.ContextVar("agentops_current_trace", default=None)

try:
    from agentops_client import AgentOpsClient

    _client = AgentOpsClient(
        project="competitive-intel-agent",
        base_url=os.environ.get("AGENTOPS_URL", "http://127.0.0.1:8123"),
    )
    ENABLED = True
except Exception as e:  # agentops-client not installed, or failed to init
    _client = None
    ENABLED = False
    logger.warning("AgentOps instrumentation disabled (agentops-client not available): %s", e)


# gpt-4o-mini pricing as of this writing, USD per token.
_PRICE_PER_TOKEN = {
    "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
    "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
}


def _normalize_model_name(model: str | None) -> str | None:
    """
    OpenAI's API returns dated model IDs in response_metadata (e.g.
    'gpt-4o-mini-2024-07-18'), not the stable alias used in config.py.
    Match by prefix so pricing keeps working across dated snapshots.
    """
    if not model:
        return model
    for known in _PRICE_PER_TOKEN:
        if model == known or model.startswith(known + "-"):
            return known
    return model


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    prices = _PRICE_PER_TOKEN.get(_normalize_model_name(model))
    if not prices or input_tokens is None or output_tokens is None:
        return None
    return round(input_tokens * prices["input"] + output_tokens * prices["output"], 8)


def usage_from_ai_message(msg) -> dict:
    """
    Best-effort extraction of token usage from a LangChain AIMessage.
    Degrades to Nones rather than raising if the shape doesn't match what
    we expect — an instrumentation helper must never crash the agent it's
    watching.
    """
    usage = getattr(msg, "usage_metadata", None)
    if usage:
        return {
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
        }
    meta = getattr(msg, "response_metadata", None) or {}
    token_usage = meta.get("token_usage") or {}
    return {
        "input_tokens": token_usage.get("prompt_tokens"),
        "output_tokens": token_usage.get("completion_tokens"),
    }


class _NullSpan:
    """No-op span returned when instrumentation is disabled or no trace is active."""

    def set_output(self, *_a, **_k):
        pass

    def set_attribute(self, *_a, **_k):
        pass

    def set_llm_usage(self, *_a, **_k):
        pass


@contextlib.contextmanager
def trace(name: str, metadata: dict | None = None, trace_id: str | None = None):
    """Open a top-level AgentOps trace for one end-to-end research run."""
    if not ENABLED:
        yield None
        return
    with _client.trace(name, metadata=metadata, trace_id=trace_id) as t:
        token = _current_trace.set(t)
        try:
            yield t
        finally:
            _current_trace.reset(token)


@contextlib.contextmanager
def span(name: str, kind: str = "chain", input_payload=None):
    """
    Attach a span to whatever trace is currently active (set by an
    enclosing `trace(...)` block higher up the call stack). Safe to call
    even when no trace is active or instrumentation is disabled — returns
    a no-op span in that case.
    """
    t = _current_trace.get()
    if not ENABLED or t is None:
        yield _NullSpan()
        return
    with t.span(name, kind=kind, input_payload=input_payload) as s:
        yield s


def record_eval(
    trace_id: str,
    check_name: str,
    check_type: str,
    passed: bool,
    score: float | None = None,
    rationale: str | None = None,
) -> None:
    """
    Write a check/judge verdict to AgentOps (POST /v1/evals), tied to a
    specific trace_id. Used for structural validation (this repo) and
    LLM-judge verdicts (agentic-rag-orchestrator's evals/run_judge.py
    uses the equivalent call directly).

    Fails safe like everything else here: a failed write is logged and
    swallowed, never raised — an eval-recording failure must not be able
    to break report generation itself.
    """
    if not ENABLED:
        return
    try:
        import httpx
        resp = httpx.post(
            f"{_client.base_url}/v1/evals",
            json={
                "trace_id": trace_id,
                "check_name": check_name,
                "check_type": check_type,
                "passed": passed,
                "score": score,
                "rationale": rationale,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.warning("AgentOps: failed to record eval '%s': %s", check_name, e)