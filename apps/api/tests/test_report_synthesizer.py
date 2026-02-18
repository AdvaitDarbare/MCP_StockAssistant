from __future__ import annotations

import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.services.report_synthesizer import synthesize_report_markdown  # noqa: E402


class ReportSynthesizerTests(unittest.TestCase):
    def test_clean_body_present(self) -> None:
        """The cleaned report body must appear in the output."""
        report = {
            "markdown": "# Title\n- Item one\n- Item two",
            "tool_plan": [{"tool": "market_data", "reason": "quote"}],
            "sources_used": ["finviz"],
            "assumptions": ["A"],
            "limitations": ["L"],
        }
        out = synthesize_report_markdown(report=report, effective_prompt="You are a banker.")
        text = out["markdown"]
        # The cleaned report body must be present
        self.assertIn("# Title", text)
        self.assertIn("Item one", text)
        self.assertIn("Item two", text)

    def test_limitation_note_appended(self) -> None:
        """A limitation note should appear after the divider when limitations are present."""
        report = {
            "markdown": "# Report\nSome content.",
            "tool_plan": [],
            "sources_used": [],
            "assumptions": [],
            "limitations": ["This is a limitation."],
        }
        out = synthesize_report_markdown(report=report, effective_prompt="Prompt")
        text = out["markdown"]
        self.assertIn("---", text)
        self.assertIn("**Note:**", text)
        self.assertIn("This is a limitation.", text)

    def test_no_raw_object_placeholder(self) -> None:
        report = {"markdown": "[object Object]", "tool_plan": [], "sources_used": []}
        out = synthesize_report_markdown(report=report, effective_prompt="Prompt")
        self.assertNotIn("[object Object]", out["markdown"])

    def test_full_body_appended(self) -> None:
        """The full base report markdown should appear in the output."""
        report = {
            "markdown": "# My Report\n\nDetailed analysis here.",
            "tool_plan": [],
            "sources_used": [],
        }
        out = synthesize_report_markdown(report=report, effective_prompt="Prompt")
        text = out["markdown"]
        self.assertIn("# My Report", text)
        self.assertIn("Detailed analysis here.", text)

    def test_follow_up_label_present(self) -> None:
        """Follow-up question label should appear at the top when provided."""
        report = {"markdown": "# Report\nContent.", "tool_plan": [], "sources_used": []}
        out = synthesize_report_markdown(
            report=report,
            effective_prompt="Prompt",
            follow_up_question="What is the P/E ratio?",
        )
        self.assertIn("**Follow-up Analysis:**", out["markdown"])
        self.assertIn("What is the P/E ratio?", out["markdown"])

    def test_no_caveats_section_when_no_limitations(self) -> None:
        """No divider or Note should appear when there are no limitations."""
        report = {
            "markdown": "# Clean Report\nAll good.",
            "tool_plan": [],
            "sources_used": [],
            "limitations": [],
            "assumptions": [],
        }
        out = synthesize_report_markdown(report=report, effective_prompt="Prompt")
        self.assertNotIn("**Note:**", out["markdown"])


if __name__ == "__main__":
    unittest.main()
