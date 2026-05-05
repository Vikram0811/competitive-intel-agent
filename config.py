import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY   = os.getenv("TAVILY_API_KEY")

# ── Model ─────────────────────────────────────────────────────────
LLM_MODEL        = "gpt-4o-mini"
LLM_TEMPERATURE  = 0

# ── Agent ─────────────────────────────────────────────────────────
MAX_SEARCH_RESULTS   = 5      # results per Tavily search
MAX_SEARCHES         = 3      # number of search queries the agent runs
RECURSION_LIMIT      = 25     # LangGraph recursion limit

# ── Report ────────────────────────────────────────────────────────
REPORTS_DIR      = "reports"