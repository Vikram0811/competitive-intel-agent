"""
agent/report_validation.py — structural validation for generated reports.

Why this instead of an LLM judge: agentic-rag-orchestrator's answers are
single, verifiable values (hash strings) — exact-match against a golden
answer is the right tool there. This repo's output is an open-ended
report — there's no single "correct" report to match against, so
exact-match doesn't apply. What *can* be checked cheaply and reliably is
structure: does the report contain the sections the prompt template
(agent/prompts.py REPORT_TEMPLATE) actually requires? No LLM call needed —
this is a pure string check, fast and free to run on every report.
"""

from dataclasses import dataclass, field

# Exact section headers required by REPORT_TEMPLATE in agent/prompts.py.
# Kept as a single source of truth here rather than re-deriving it from
# the prompt text at runtime — if the template changes, this list needs a
# matching update, which is a deliberate coupling (the check should fail
# loudly if the two drift apart, not silently pass).
REQUIRED_SECTIONS = [
    "## Company Overview",
    "## Key Facts",
    "## Products and Services",
    "## Recent Developments",
    "## Customers and Market",
    "## Competitive Position",
]


@dataclass
class StructuralValidationResult:
    passed: bool
    present_sections: list[str] = field(default_factory=list)
    missing_sections: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        total = len(REQUIRED_SECTIONS)
        return len(self.present_sections) / total if total else 0.0

    @property
    def rationale(self) -> str:
        if self.passed:
            return f"All {len(REQUIRED_SECTIONS)} required sections present."
        return f"Missing {len(self.missing_sections)}/{len(REQUIRED_SECTIONS)} required sections: {', '.join(self.missing_sections)}"


def validate_report_structure(report_text: str) -> StructuralValidationResult:
    """
    Checks that every required section header appears in the report.
    Case-sensitive, exact-header match — the prompt template specifies an
    exact format ("Use exactly this format"), so a report that doesn't
    follow it is a real structural failure, not a stylistic difference.
    """
    if not report_text:
        return StructuralValidationResult(passed=False, missing_sections=list(REQUIRED_SECTIONS))

    present = [s for s in REQUIRED_SECTIONS if s in report_text]
    missing = [s for s in REQUIRED_SECTIONS if s not in report_text]

    return StructuralValidationResult(
        passed=len(missing) == 0,
        present_sections=present,
        missing_sections=missing,
    )
