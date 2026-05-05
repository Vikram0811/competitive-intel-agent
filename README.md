# Competitive Intelligence Agent

> An agentic side project built while learning Agentic AI - an autonomous agent that researches any company using live web search and produces a structured intelligence briefing.

Enter a company name. The agent searches the web, reads results, validates findings, and writes a structured markdown report - no documents to upload, no vector database, pure agentic tool use.

---

## What Makes This Agentic

Unlike a simple LLM call that answers from training data, this agent decides its own research steps at runtime using a ReAct (Reasoning + Acting) loop:

| Simple LLM Call | Competitive Intelligence Agent |
|---|---|
| Answers from training data | Searches live web for current information |
| Single prompt, single response | Multi-step research loop with adaptive queries |
| No tool use | Autonomous tool selection and execution |
| No validation | Flags unverifiable companies with a warning |
| Fixed steps | Agent decides queries and search depth at runtime |

---

## Features

- **Agentic ReAct Loop** - LangGraph agent that reasons, searches, observes, and loops until research is complete
- **Live Web Search** - Tavily Search API returns clean, structured results purpose-built for AI agents
- **Adaptive Query Generation** - Agent writes its own search queries based on what it finds
- **Company Validation** - Flags unverifiable or ambiguous companies with a warning rather than hallucinating
- **Structured Report Output** - Consistent markdown report covering overview, key facts, products, recent developments, and competitive position
- **Auto-Save** - Every report saved as a timestamped markdown file in `reports/`
- **Gradio UI** - Clean interface with rendered markdown display and raw markdown export

---

## Architecture

```
LAYER 1 - PRESENTATION
  Gradio UI (gradio_app.py)
  Company name input + rendered report display
        │
        ▼
LAYER 2 - SERVICE
  ReportService
  Orchestrates agent, handles errors, saves reports
        │
        ▼
LAYER 3 - ORCHESTRATION
  LangGraph Agent
  agent → should_continue → tools → agent (loop) → report → END
        │
        ▼
LAYER 4 - INFRASTRUCTURE
  GPT-4o-mini (OpenAI)   Tavily Search API
```

### LangGraph Agent Flow

```
Company Name Input
    │
    ▼
agent node         ← LLM reasons about what to search next
    │
    ├── has tool calls ──► tools node  ← Tavily search executes
    │                           │
    │                           └──► back to agent node (loop)
    │
    └── no tool calls ──► report node  ← synthesises final report
                                │
                                ▼
                              END    ← report returned to UI + saved to disk
```

---

## Tech Stack

| Component | Technology |
|---|---|
| LLM | GPT-4o-mini via OpenAI API |
| Agent Framework | LangGraph |
| Web Search | Tavily Search API |
| UI Framework | Gradio |

---

## Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key
- Tavily API key - free tier at [tavily.com](https://tavily.com) (1,000 searches/month)
- Conda or virtualenv (recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/Vikram0811/competitive-intel-agent.git
cd competitive-intel-agent

# Create and activate environment
conda create -n intel_env python=3.10
conda activate intel_env

# Install dependencies
pip install -r requirements.txt
```

### Configuration

```bash
# Copy environment template and add your API keys
cp .env.example .env
```

Edit `.env`:
```
OPENAI_API_KEY=your-openai-api-key-here
TAVILY_API_KEY=your-tavily-api-key-here
```

### Run

```bash
python app.py
```

Open your browser at `http://127.0.0.1:7860`

1. Enter a company name in the input box
2. Click **Generate Report**
3. The agent researches and streams the report - typically 20-40 seconds
4. Report is saved automatically to the `reports/` folder

---

## Configuration Reference

All tunable parameters are in `config.py`:

| Parameter | Default | Description |
|---|---|---|
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI model name |
| `LLM_TEMPERATURE` | `0` | LLM temperature - keep at 0 for factual research |
| `MAX_SEARCH_RESULTS` | `5` | Number of results returned per Tavily search |
| `MAX_SEARCHES` | `3` | Number of search queries the agent runs |
| `RECURSION_LIMIT` | `25` | LangGraph recursion limit - increase for deeper research |
| `REPORTS_DIR` | `reports` | Directory where markdown reports are saved |

---

## Project Structure

```
competitive-intel-agent/
├── app.py                  # Entry point
├── config.py               # All tunable parameters
├── agent/
│   ├── graph.py            # LangGraph agent definition and compilation
│   ├── nodes.py            # Agent node, report node, edge logic
│   ├── prompts.py          # System prompt and report template
│   └── tools.py            # Tavily search tool definition
├── core/
│   └── report_service.py   # Orchestrates agent, saves reports
├── ui/
│   └── gradio_app.py       # Gradio UI definition
└── reports/                # Saved markdown reports (gitignored)
```

---

## Known Limitations

- Search results may include outdated information depending on what Tavily returns
- Tavily free tier is limited to 1,000 searches per month
- Agent may occasionally find a different company with a similar name - the warning system catches most but not all cases
- No streaming - report appears all at once after the agent completes research

---

## Related Project

This is the second in a series of Agentic AI side projects. See also:

[Agentic RAG Orchestrator](https://github.com/Vikram0811/agentic-rag-orchestrator) - production-grade RAG system with hybrid retrieval, confidence scoring, and multi-user session isolation.

---

## License

MIT License