"""
LangGraph agent graph for Competitive Intelligence research.
"""
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated
import operator

from agent.nodes import create_agent_node, create_report_node, should_continue
from agent.tools import create_search_tool
import config


# ── State Definition ──────────────────────────────────────────────
class AgentState(TypedDict):
    messages:     Annotated[list, operator.add]
    company_name: str
    report:       str


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
    tool_node   = ToolNode([search_tool])

    # Build graph
    graph = StateGraph(AgentState)

    graph.add_node("agent",  agent_node)
    graph.add_node("tools",  tool_node)
    graph.add_node("report", report_node)

    # Entry point
    graph.set_entry_point("agent")

    # Conditional edge — tools or report
    graph.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools":  "tools",
            "report": "report",
        }
    )

    # After tools — always go back to agent
    graph.add_edge("tools", "agent")

    # After report — done
    graph.add_edge("report", END)

    return graph.compile()