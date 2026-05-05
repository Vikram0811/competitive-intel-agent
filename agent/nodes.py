"""
Agent nodes for the Competitive Intelligence LangGraph agent.
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from agent.prompts import SYSTEM_PROMPT, REPORT_TEMPLATE
import config


def create_agent_node(llm_with_tools):
    """
    Returns the agent node function.
    The agent reasons about what to search next and calls tools.
    """
    def agent_node(state: dict) -> dict:
        messages = state["messages"]

        # Add system prompt if this is the first call
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

        response = llm_with_tools.invoke(messages)
        return {"messages": messages + [response]}

    return agent_node


def create_report_node(llm):
    """
    Returns the report generation node.
    Called after research is complete — synthesises findings into final report.
    """
    def report_node(state: dict) -> dict:
        company_name = state["company_name"]
        messages     = state["messages"]

        # Build the report generation prompt
        report_prompt = REPORT_TEMPLATE.format(company_name=company_name)

        # Include all research messages for context
        synthesis_messages = messages + [
            HumanMessage(content=report_prompt)
        ]

        response = llm.invoke(synthesis_messages)
        report   = response.content

        return {
            "messages": messages + [response],
            "report":   report,
        }

    return report_node


def should_continue(state: dict) -> str:
    """
    Edge function — decides whether to call tools or move to report generation.
    If the last message has tool calls → continue to tools node.
    If no tool calls → research is done, generate report.
    """
    last_message = state["messages"][-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return "report"