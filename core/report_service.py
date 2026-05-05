"""
ReportService — entry point for the UI.
Orchestrates the agent and handles saving the report.
"""
import os
import uuid
from pathlib import Path
from datetime import datetime
from langchain_core.messages import HumanMessage

from agent.graph import create_agent_graph
import config


class ReportService:

    def __init__(self):
        self._graph = create_agent_graph()
        Path(config.REPORTS_DIR).mkdir(parents=True, exist_ok=True)

    # ── Public ────────────────────────────────────────────────────

    def generate_report(self, company_name: str, progress_callback=None) -> str:
        """
        Runs the agent for the given company name.
        Returns the final markdown report as a string.
        """
        if not company_name or not company_name.strip():
            return "Please enter a company name."

        company_name = company_name.strip()

        if progress_callback:
            progress_callback(0.1, f"Starting research on {company_name}...")

        try:
            initial_state = {
                "messages":     [HumanMessage(content=f"Research this company: {company_name}")],
                "company_name": company_name,
                "report":       "",
            }

            config_dict = {
                "recursion_limit": config.RECURSION_LIMIT,
            }

            if progress_callback:
                progress_callback(0.3, "Searching the web...")

            result = self._graph.invoke(initial_state, config_dict)

            if progress_callback:
                progress_callback(0.8, "Generating report...")

            report = result.get("report", "")

            if not report:
                return "Could not generate a report. Please try again."

            # Save report to disk
            saved_path = self._save_report(company_name, report)

            if progress_callback:
                progress_callback(1.0, f"Report saved to {saved_path}")

            return report

        except Exception as e:
            return f"Error generating report: {str(e)}"

    # ── Private ───────────────────────────────────────────────────

    def _save_report(self, company_name: str, report: str) -> str:
        """
        Saves the report as a markdown file in the reports/ directory.
        Returns the file path.
        """
        timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name  = company_name.replace(" ", "_").replace("/", "_")
        filename   = f"{safe_name}_{timestamp}.md"
        filepath   = Path(config.REPORTS_DIR) / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)

        return str(filepath)