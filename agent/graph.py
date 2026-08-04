"""
LangGraph agent graph for Competitive Intelligence research.
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

from agent.nodes import create_agent_node, create_report_node, should_continue
from agent.tools import create_search_tool
from core import observability as obs
import config


# ── State Definition ──────────────────────────────────────────────
class AgentState(TypedDict):
    messages:     Annotated[list, operator.add]
    company_name: str
    report:       str
    # Incremented once per agent_node pass. Purely observational for now —
    # visible on each span's attributes so we can see how many search
    # rounds a given company took. RECURSION_LIMIT already provides a hard
    # backstop (config.py) against runaway loops; this doesn't add a soft
    # cap of its own, just visibility. Revisit if trace data ever shows the
    # same unbounded-retry pattern found in agentic-rag-orchestrator.
    tool_call_count: int


# ── Tool Execution Node ───────────────────────────────────────────
def create_tool_node(tools: list):
    """
    Custom replacement for LangGraph's prebuilt ToolNode.

    Why not just use ToolNode: it gives no hook to attach an AgentOps span
    around each individual tool execution — every search would be
    invisible in trace data. Written by hand instead, doing the same job
    ToolNode does (execute each requested tool call, return ToolMessages),
    plus a span per call.

    Handles *all* tool calls in the last message, not just the first — a
    single agent turn here can request several searches at once (observed:
    3 parallel Tavily calls in one agent_reasoning_step, see
    PERFORMANCE.md), so this must loop over every call, not assume 1:1.
    """
    tools_by_name = {t.name: t for t in tools}

    def tool_node(state: dict) -> dict:
        last_message = state["messages"][-1]
        tool_calls = getattr(last_message, "tool_calls", None) or []
        result_messages = []

        for call in tool_calls:
            tool_name = call["name"]
            tool_args = call.get("args", {})
            tool = tools_by_name.get(tool_name)

            with obs.span(tool_name, kind="tool", input_payload=tool_args) as sp:
                if tool is None:
                    content = f"Error: unknown tool '{tool_name}'"
                    sp.set_attribute("error", content)
                else:
                    try:
                        output = tool.invoke(tool_args)
                        content = output if isinstance(output, str) else str(output)
                        result_count = len(output) if isinstance(output, list) else None
                        sp.set_output({
                            "result_count": result_count,
                            "preview": content[:300],
                        })
                    except Exception as e:
                        # Match the RAG repo's pattern: report the failure
                        # back to the agent as tool output rather than
                        # raising, so one bad search doesn't crash the run.
                        content = f"Error running {tool_name}: {e}"
                        sp.set_attribute("error", str(e))

            result_messages.append(
                ToolMessage(content=content, tool_call_id=call["id"], name=tool_name)
            )

        return {"messages": result_messages}

    return tool_node


# ── Graph Factory ─────────────────────────────────────────────────
def create_agent_graph():
    """
    Builds and compiles the LangGraph agent.

    Graph structure:
        agent → should_continue → tools → agent (loop)
                                → report → END
    """
    # LLM with tools bound — used in agent node
    llm = ChatOpenAI(
        model=config.LLM_MODEL,
        temperature=config.LLM_TEMPERATURE,
        api_key=config.OPENAI_API_KEY,
    )

    search_tool  = create_search_tool()
    llm_with_tools = llm.bind_tools([search_tool])

    # Nodes
    agent_node  = create_agent_node(llm_with_tools)
    report_node = create_report_node(llm)
    tool_node   = create_tool_node([search_tool])

    # Build graph
    graph = StateGraph(AgentState)

    graph.add_node("agent",  agent_node)
    graph.add_node("tools",  tool_node)
    graph.add_node("generate_report", report_node)

    # Entry point
    graph.set_entry_point("agent")

    # Conditional edge — tools or report
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools":          "tools",
            "generate_report": "generate_report",
        }
    )

    # After tools — always go back to agent
    graph.add_edge("tools", "agent")

    # After report — done
    graph.add_edge("generate_report", END)

    return graph.compile()