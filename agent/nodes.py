"""
Agent nodes for the Competitive Intelligence LangGraph agent.
"""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from agent.prompts import SYSTEM_PROMPT, REPORT_TEMPLATE
from core import observability as obs
import config


def create_agent_node(llm_with_tools):
    """
    Returns the agent node function.
    The agent reasons about what to search next and calls tools.
    """
    def agent_node(state: dict) -> dict:
        messages = state["messages"]
        call_count = state.get("tool_call_count", 0) + 1

        # Add system prompt if this is the first call
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

        with obs.span(
            "agent_reasoning_step",
            kind="agent",
            input_payload={"company_name": state.get("company_name")},
        ) as sp:
            sp.set_attribute("tool_call_count", call_count)

            response = llm_with_tools.invoke(messages)

            usage = obs.usage_from_ai_message(response)
            model = (getattr(response, "response_metadata", {}) or {}).get("model_name", "unknown")
            sp.set_llm_usage(
                model=model,
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                cost_usd=obs.estimate_cost_usd(model, usage["input_tokens"], usage["output_tokens"]),
            )

            tool_calls = getattr(response, "tool_calls", None) or []
            sp.set_output({
                "content_preview": (response.content or "")[:200],
                "tool_calls": [tc.get("name") for tc in tool_calls],
            })

        return {"messages": messages + [response], "tool_call_count": call_count}

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

        with obs.span(
            "generate_report",
            kind="llm",
            input_payload={"company_name": company_name},
        ) as sp:
            response = llm.invoke(synthesis_messages)
            report   = response.content

            usage = obs.usage_from_ai_message(response)
            model = (getattr(response, "response_metadata", {}) or {}).get("model_name", "unknown")
            sp.set_llm_usage(
                model=model,
                input_tokens=usage["input_tokens"],
                output_tokens=usage["output_tokens"],
                cost_usd=obs.estimate_cost_usd(model, usage["input_tokens"], usage["output_tokens"]),
            )
            sp.set_output({"report_preview": (report or "")[:200]})

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

    return "generate_report"