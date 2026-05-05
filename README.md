# Competitive Intelligence Agent

> A side project built while learning Agentic AI — an autonomous agent that researches any company using live web search and produces a structured intelligence briefing.

---

## What It Does

Enter a company name. The agent searches the web multiple times with targeted queries, reads the results, validates what it found, and writes a structured markdown report covering company overview, key facts, products, recent developments, and competitive position.

If the company cannot be verified from search results, the report flags it with a warning rather than hallucinating details.

---

## What Makes It Agentic

This is not a RAG system — there are no documents or vector databases. The agent decides its own research steps using a ReAct (Reasoning + Acting) loop:

1. **Reason** — what do I need to search for next?
2. **Act** — call the Tavily search tool
3. **Observe** — are the results sufficient?
4. **Loop** — search again with a different query if needed
5. **Synthesise** — write the final report once research is complete

The number of searches and the queries themselves are decided by the agent at runtime, not hardcoded.

---

## Tech Stack

| Component | Technology |
|---|---|
| Agent Framework | LangGraph |
| LLM | GPT-4o-mini via OpenAI API |
| Web Search | Tavily Search API |
| UI | Gradio |

---

## Quick Start

### Prerequisites

- Python 3.10+
- OpenAI API key
- Tavily API key (free tier at [tavily.com](https://tavily.com))

### Installation

```bash
git clone https://github.com/Vikram0811/competitive-intel-agent.git
cd competitive-intel-agent

conda create -n intel_env python=3.10
conda activate intel_env

pip install -r requirements.txt
```

### Configuration

```bash
cp .env.example .env
```

Edit `.env`:
```
OPENAI_API_KEY=your-openai-key-here
TAVILY_API_KEY=your-tavily-key-here
```

### Run

```bash
python app.py
```

Open your browser at `http://127.0.0.1:7860`

---

## Project Structure

```
competitive-intel-agent/
├── app.py                  # Entry point
├── config.py               # Settings and API config
├── agent/
│   ├── graph.py            # LangGraph agent definition
│   ├── nodes.py            # Agent and report nodes
│   ├── prompts.py          # System prompt and report template
│   └── tools.py            # Tavily search tool
├── core/
│   └── report_service.py   # Orchestrates agent, saves reports
├── ui/
│   └── gradio_app.py       # Gradio UI
└── reports/                # Saved markdown reports (gitignored)
```

---

## Known Limitations

- Search results may include outdated information depending on what Tavily returns
- Tavily free tier is limited to 1,000 searches per month
- Agent may occasionally find a different company with a similar name — the warning system catches most but not all cases

---

## Related Project

This is the second in a series of Agentic AI side projects. See also:

[Agentic RAG Orchestrator](https://github.com/Vikram0811/agentic-rag-orchestrator) — production-grade RAG system with hybrid retrieval, confidence scoring, and multi-user session isolation.

---

## License

MIT License