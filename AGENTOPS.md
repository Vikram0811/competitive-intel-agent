# AgentOps Instrumentation

This repo is instrumented with [AgentOps](../agentops) — every company
research run now produces a real execution trace covering the agent's
reasoning steps, every individual web search, and the final report
synthesis, with cost and latency on each.

## What changed

- **`core/observability.py`** (new) — same `trace(...)`/`span(...)` shim
  used in `agentic-rag-orchestrator`, repointed at
  `project="competitive-intel-agent"`. Fails safe: no-ops if
  `agentops-client` isn't installed or the server is unreachable.
- **`core/report_service.py`** — `generate_report()` opens one trace per
  research run, keyed to a generated `request_id`. The trace wraps only
  `self._graph.invoke(...)`, placed *inside* this method's existing
  `try/except` rather than around it — so if the graph raises, the trace
  correctly records `status: "error"` with the real exception, even though
  this method's own `except` catches it afterward and returns a friendly
  string to the UI. Verified both paths (success and induced failure)
  record the correct trace status.
- **`agent/graph.py`** —
  - `AgentState` gained `tool_call_count`, incremented once per
    `agent_node` pass. Observational only for now — no soft cap like the
    one added to `agentic-rag-orchestrator`, since this repo's
    `config.RECURSION_LIMIT = 25` was already correctly defined and
    provides a real backstop against runaway loops (unlike the RAG repo,
    which had a dead config reference — see that repo's `PERFORMANCE.md`).
  - **`ToolNode` was replaced with a hand-written `create_tool_node()`.**
    This is the one structural change in this integration: LangGraph's
    prebuilt `ToolNode` gives no hook to attach a span around individual
    tool calls, so it's swapped for an equivalent implementation that does
    the same job (execute each requested tool call, return `ToolMessage`s)
    plus a span per call. Errors in one tool call are caught and reported
    back to the agent as tool output rather than crashing the run,
    matching the RAG repo's tool-error-handling pattern.
- **`agent/nodes.py`** — `agent_node`'s reasoning call wrapped in
  `obs.span(kind="agent")`; `report_node`'s synthesis call wrapped in
  `obs.span(kind="llm")`. Both capture token usage and cost.

## A real finding from building this

This agent can request **multiple tool calls in a single reasoning turn** —
observed in production trace data: 3 parallel Tavily searches from one
`agent_reasoning_step`, matching `config.MAX_SEARCHES = 3`. The first draft
of `create_tool_node()` was built assuming one tool call per turn (copying
the RAG repo's pattern too directly) and would have silently captured only
the first of three searches. Caught by testing against real trace data
before considering the file done — see conversation history / commit log
for the correction. Worth knowing if extending this further: **don't
assume 1:1 between agent turns and tool calls in this repo.**

## Trace shape you'll see

```
generate_report (trace, trace_id = request_id)
├── agent_reasoning_step        [kind=agent]
│   ├── tavily_search_results_json   [kind=tool]  ← one span per
│   ├── tavily_search_results_json   [kind=tool]     parallel call,
│   └── tavily_search_results_json   [kind=tool]     not nested
├── agent_reasoning_step        [kind=agent]   ← loops back after tools
└── generate_report             [kind=llm]     ← final synthesis
```

Note tool spans are **siblings**, not nested under their triggering
`agent_reasoning_step` — same flat pattern as `search_child_chunks` in the
RAG repo, since `obs.span()` attaches to the trace's current active span
context, and the tool node runs as a separate graph step after the agent
span has already closed.

## Configuration

```bash
export AGENTOPS_URL=http://127.0.0.1:8123   # default
```

## Running it

Start the AgentOps server (see the root `agentops` repo's README), then
`pip install -e ../agentops/client` in this repo's environment, then run
`python app.py` as usual. Every research run now produces a trace visible
via `GET http://127.0.0.1:8123/v1/traces?project=competitive-intel-agent`.