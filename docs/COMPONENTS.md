# Component Reference

Detailed explanation of every component in the Competitive Intelligence Agent.

---

## System Overview

The system is organised into four layers. Each layer has a single responsibility and communicates only with the layer directly adjacent to it.

```
LAYER 1 - PRESENTATION    gradio_app.py
LAYER 2 - SERVICE         report_service.py
LAYER 3 - ORCHESTRATION   graph.py + nodes.py + prompts.py
LAYER 4 - INFRASTRUCTURE  tools.py + OpenAI API + Tavily API
```

---

## Layer 1 - Presentation

### `ui/gradio_app.py`

**Responsibility:** Render the UI, handle user input, display the report.

**What it knows about:** `ReportService` only. It has no knowledge of LangGraph, OpenAI, or Tavily.

**Key functions:**

| Function | What It Does |
|---|---|
| `generate_handler` | Called when user clicks Generate Report. Passes company name to ReportService, feeds progress callbacks to Gradio progress bar. |
| `clear_handler` | Clears the input field and report display. |

**UI components:**

| Component | Purpose |
|---|---|
| `company_input` | Text input for company name |
| `generate_btn` | Triggers report generation |
| `report_display` | Rendered markdown view of the report |
| `report_raw` | Raw markdown textbox - hidden by default, toggled by Show Raw Markdown button |
| `show_raw_btn` | Toggles visibility of raw markdown |

---

## Layer 2 - Service

### `core/report_service.py`

**Responsibility:** Single entry point for the UI. Owns the agent graph lifecycle, handles errors, saves reports.

**What it knows about:** `create_agent_graph()`, `config`, file system for saving reports.

**Key methods:**

| Method | What It Does |
|---|---|
| `__init__` | Compiles the LangGraph agent once at startup. Creates `reports/` directory. |
| `generate_report` | Builds initial state, invokes the graph, extracts the report, calls `_save_report`. Returns the report string to the UI. |
| `_save_report` | Saves the report as a timestamped markdown file in `reports/`. Returns the file path. |

**Error handling:** All exceptions are caught and returned as a plain error string to the UI - the UI never sees a Python exception.

**Progress callbacks:** Four progress checkpoints reported to Gradio:
- `0.1` - Starting research
- `0.3` - Searching the web
- `0.8` - Generating report
- `1.0` - Done, report saved

---

## Layer 3 - Orchestration

### `agent/graph.py`

**Responsibility:** Define, wire, and compile the LangGraph state machine.

**State definition (`AgentState`):**

| Field | Type | Description |
|---|---|---|
| `messages` | `Annotated[list, operator.add]` | Full conversation history - accumulates across all nodes |
| `company_name` | `str` | Company being researched - passed through unchanged |
| `report` | `str` | Final report string - set by report node, empty until then |

**Graph structure:**

```
agent node ──► should_continue ──► tools node ──► agent node (loop)
                               └──► report node ──► END
```

**Why `operator.add` on messages:** LangGraph merges state updates by addition for list fields. This means each node appends to the message list rather than replacing it - the full research history accumulates automatically.

---

### `agent/nodes.py`

**Responsibility:** Define what each node does when called.

**`create_agent_node(llm_with_tools)`**

Returns the agent node function. On each call:
1. Checks if a system prompt is already in messages - adds it if not
2. Invokes the LLM with the full message history
3. Returns the LLM response appended to messages

The LLM has tools bound to it - it can choose to call `tavily_search` or respond with plain text.

**`create_report_node(llm)`**

Returns the report generation node. On each call:
1. Takes the full research message history
2. Appends the report template as a final HumanMessage
3. Invokes the LLM to synthesise a structured report
4. Returns the report string in the state

Uses a plain LLM without tools bound - report generation is a synthesis task, not a research task.

**`should_continue(state)`**

Edge function - not a node. Inspects the last message:
- If `tool_calls` present → return `"tools"` → route to tools node
- If no `tool_calls` → return `"report"` → route to report node

---

### `agent/prompts.py`

**Responsibility:** Define all LLM instructions.

**`SYSTEM_PROMPT`**

Instructs the agent to:
- Follow a three-step research sequence (overview → news → products)
- Search again with different queries if results are insufficient
- Validate that results actually match the requested company
- Never invent information not found in search results
- Flag ambiguous results rather than using them

**`REPORT_TEMPLATE`**

Defines the exact output format the agent must follow:
- Company Overview
- Key Facts (founded, HQ, employees, revenue, public/private)
- Products and Services
- Recent Developments
- Customers and Market
- Competitive Position

Also instructs the agent to add a warning at the top if the company could not be verified.

---

## Layer 4 - Infrastructure

### `agent/tools.py`

**Responsibility:** Define the Tavily search tool and expose it to the agent.

**`create_search_tool()`**

Returns a configured `TavilySearchResults` tool with:

| Parameter | Value | Why |
|---|---|---|
| `max_results` | `5` | Balances depth vs token cost per search |
| `search_depth` | `"advanced"` | Returns more complete content than basic |
| `include_answer` | `True` | Tavily generates an AI summary per search - useful for synthesis |
| `include_raw_content` | `False` | Reduces token usage - clean text only |
| `include_images` | `False` | Not needed for text reports |

**Why Tavily over Google/Bing:** Tavily is purpose-built for AI agents. It returns clean, structured text without HTML, JavaScript, or navigation elements. Standard web scrapers require significant post-processing to get usable text. Tavily handles this automatically.

---

### `config.py`

**Responsibility:** Single source of truth for all tunable parameters.

| Parameter | Default | Description |
|---|---|---|
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI model. Switch to `gpt-4o` for higher quality at higher cost. |
| `LLM_TEMPERATURE` | `0` | Zero temperature for factual, deterministic research output |
| `MAX_SEARCH_RESULTS` | `5` | Results per Tavily search. Increase for more comprehensive research. |
| `MAX_SEARCHES` | `3` | Intended max searches - the agent may do fewer or more depending on findings |
| `RECURSION_LIMIT` | `25` | LangGraph safety limit - prevents infinite loops |
| `REPORTS_DIR` | `reports` | Directory for saved markdown reports |

---

## Data Flow Summary

```
User types "Salesforce"
    │
    ▼
gradio_app.py → report_service.generate_report("Salesforce")
    │
    ▼
report_service → graph.invoke({ messages: [HumanMessage], company_name: "Salesforce" })
    │
    ▼
agent node → LLM decides: search "Salesforce company overview"
    │
    ▼
tools node → Tavily returns 5 results
    │
    ▼
agent node → LLM decides: search "Salesforce recent news 2024"
    │
    ▼
tools node → Tavily returns 5 results
    │
    ▼
agent node → LLM decides: search "Salesforce products customers"
    │
    ▼
tools node → Tavily returns 5 results
    │
    ▼
agent node → LLM decides: research complete, no more tool calls
    │
    ▼
report node → LLM synthesises all results into structured markdown
    │
    ▼
report_service → saves to reports/Salesforce_20250506_143022.md
    │
    ▼
gradio_app.py → renders markdown report in UI
```