from __future__ import annotations

try:
    from .agents.langchain.workflow import run_workflow
except ImportError:
    from agents.langchain.workflow import run_workflow


if __name__ == "__main__":
    result = run_workflow(
        {
            "post_id": "post_001",
            "raw_text": "Someone tried opening parked cars at around 9pm near Bugis.",
            "candidate": None,
            "category": None,
            "authenticity_score": None,
            "decision": None,
            "revision_count": 0,
            "notes": [],
        }
    )
    print(result)
