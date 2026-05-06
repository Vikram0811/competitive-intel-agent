# Workflow Walkthrough

Step-by-step trace of what happens from the moment a user enters a company name to the moment the report appears on screen.

---

## Overview

The agent completes research in five stages. Unlike a fixed pipeline, the middle stages loop dynamically - the agent decides how many searches to run and what to search for based on what it finds.

```
User Input → Agent Initialisation → ReAct Research Loop → Report Generation → Save + Display
```

---

## Stage 1 - User Input

1. User enters a company name in the Gradio UI and clicks **Generate Report**
2. `gradio_app.py` calls `report_service.generate_report(company_name)`
3. Progress bar initialises at 0%

---

## Stage 2 - Agent Initialisation

1. `ReportService` builds the initial LangGraph state:
   ```
   {
     messages:     [HumanMessage("Research this company: {company_name}")],
     company_name: "{company_name}",
     report:       ""
   }
   ```
2. The compiled LangGraph graph is invoked with this state
3. Entry point is the **agent node**

---

## Stage 3 - ReAct Research Loop

This is the core agentic behavior. The loop runs until the agent decides it has enough information.

### Step 3a - Agent Reasons

The agent node sends the current messages to GPT-4o-mini with the system prompt. The system prompt instructs the agent to:
- Search for company overview first
- Search for recent news second
- Search for products and services third
- Validate that results match the requested company

The LLM responds with either:
- A **tool call** - specifying a Tavily search query to run next
- A **plain text response** - signalling research is complete

### Step 3b - Edge Decision (`should_continue`)

The `should_continue` function checks the last message:
- If it contains tool calls → route to **tools node**
- If it contains no tool calls → route to **report node**

### Step 3c - Tools Node Executes Search

The `ToolNode` calls Tavily Search with the query the agent specified.

Tavily returns up to `MAX_SEARCH_RESULTS = 5` results per search, each containing:
- Title
- URL
- Clean text content (no raw HTML)
- An AI-generated answer summary

Results are appended to the messages list as a `ToolMessage`.

### Step 3d - Loop Back to Agent

After the tools node completes, the graph always routes back to the agent node. The agent now has the search results in its message history and reasons about what to do next - search again with a different query, or move to report generation.

**Typical research loop for a well-known company:**
```
agent → search "Salesforce company overview" → agent
      → search "Salesforce recent news 2024" → agent
      → search "Salesforce products and customers" → agent
      → no more tool calls → report node
```

**Typical loop for an unknown company:**
```
agent → search "XYZ Nonexistent Corp" → agent
      → results are thin or ambiguous
      → agent decides research is insufficient
      → no more tool calls → report node (with warning)
```

---

## Stage 4 - Report Generation

1. The **report node** is called once the agent stops making tool calls
2. The full message history (all search results) is passed to GPT-4o-mini
3. The report template is appended as a final `HumanMessage`
4. The LLM synthesises all research into a structured markdown report
5. If research was thin or ambiguous, the agent adds a warning at the top:
   ```
   ⚠️ Warning: Limited or ambiguous information found. 
   Verify this company independently before using this report.
   ```
6. The report is stored in the LangGraph state under the `report` key

---

## Stage 5 - Save and Display

1. `ReportService` receives the completed report string
2. Report is saved as a timestamped markdown file:
   ```
   reports/{CompanyName}_{YYYYMMDD_HHMMSS}.md
   ```
3. Progress callback fires at 100%
4. Report is returned to `gradio_app.py`
5. Gradio renders the markdown in the display panel
6. Raw markdown is available via the **Show Raw Markdown** toggle

---

## Timing

| Stage | Typical Duration |
|---|---|
| Agent initialisation | < 1 second |
| Each Tavily search | 1-3 seconds |
| Report generation (LLM synthesis) | 5-10 seconds |
| **Total for well-known company** | **20-40 seconds** |
| **Total for unknown company** | **10-20 seconds** (fewer searches) |

---

## State at Each Stage

LangGraph passes a single state dict through every node. Here is what it contains at each point:

| Stage | `messages` | `company_name` | `report` |
|---|---|---|---|
| Initial | `[HumanMessage]` | set | `""` |
| After first search | `[Human, AI, Tool]` | set | `""` |
| After N searches | `[Human, AI, Tool, AI, Tool...]` | set | `""` |
| After report node | full history + report | set | full report string |