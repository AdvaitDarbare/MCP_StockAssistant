from __future__ import annotations

import pathlib
import sys
import unittest
from unittest.mock import AsyncMock, patch

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.services.report_templates import (  # noqa: E402
    get_effective_prompt,
    list_templates,
    reset_template_override,
    save_template_override,
)


class ReportTemplatesServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_templates_with_override(self) -> None:
        with patch("apps.api.services.report_templates.get_overrides", new=AsyncMock(return_value={"morgan_dcf": "edited"})):
            templates = await list_templates("user-1")
        self.assertEqual(len(templates), 10)
        morgan = next(item for item in templates if item["id"] == "morgan_dcf")
        self.assertTrue(morgan["is_overridden"])
        self.assertEqual(morgan["effective_prompt"], "edited")

    async def test_save_and_reset_template_override(self) -> None:
        with patch(
            "apps.api.services.report_templates.upsert_override",
            new=AsyncMock(return_value={"updated_at": "2026-02-18T00:00:00Z"}),
        ):
            saved = await save_template_override("user-1", "morgan_dcf", "new prompt")
        self.assertTrue(saved["is_overridden"])

        with patch("apps.api.services.report_templates.delete_override", new=AsyncMock(return_value=True)):
            reset = await reset_template_override("user-1", "morgan_dcf")
        self.assertFalse(reset["is_overridden"])
        self.assertTrue(reset["removed"])

    async def test_effective_prompt_precedence(self) -> None:
        prompt = await get_effective_prompt("morgan_dcf", "user-1", inline_override="inline")
        self.assertEqual(prompt, "inline")

        with patch("apps.api.services.report_templates.get_override", new=AsyncMock(return_value="saved")):
            prompt = await get_effective_prompt("morgan_dcf", "user-1", inline_override=None)
        self.assertEqual(prompt, "saved")


if __name__ == "__main__":
    unittest.main()
