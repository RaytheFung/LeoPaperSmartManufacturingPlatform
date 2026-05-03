import os
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from core.runtime_mode import PILOT_REVIEW_RUNTIME_MODE, RUNTIME_MODE_ENV_VAR


class PilotReviewModeSmokeTests(unittest.TestCase):
    def _load_app(self) -> AppTest:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        at = AppTest.from_file(str(app_path), default_timeout=240)
        at.run()
        return at

    def test_pilot_review_mode_exposes_experimental_lane_and_keeps_core_read_only(self):
        with patch.dict(os.environ, {RUNTIME_MODE_ENV_VAR: PILOT_REVIEW_RUNTIME_MODE}, clear=False):
            at = self._load_app()

            combined_markdown = "\n".join(markdown.value for markdown in at.markdown)
            self.assertIn("Pilot Review Mode", combined_markdown)

            route_selectbox = next(
                widget for widget in at.selectbox if widget.label == "Choose Analysis Module"
            )
            self.assertIn("🧪 Experimental Intelligence Lab", route_selectbox.options)

            route_selectbox.select("⚡ Energy Analysis")
            at.run()
            self.assertIn("⚡ Energy Analysis Dashboard", [header.value for header in at.header])

            route_selectbox = next(
                widget for widget in at.selectbox if widget.label == "Choose Analysis Module"
            )
            route_selectbox.select("🔄 ETL Pipeline")
            at.run()
            self.assertIn(
                "Pilot review mode is active. Upload/process/backfill controls and historical-run mutations are hidden. Latest run analytics and historical provenance remain available.",
                [info.value for info in at.info],
            )
            self.assertNotIn("🚀 Process", [widget.label for widget in at.button])

            route_selectbox = next(
                widget for widget in at.selectbox if widget.label == "Choose Analysis Module"
            )
            route_selectbox.select("🧪 Experimental Intelligence Lab")
            at.run()

            combined_markdown = "\n".join(markdown.value for markdown in at.markdown)
            combined_captions = [caption.value for caption in at.caption]
            self.assertIn(
                "Pilot review mode is active. Defended-core write controls stay hidden, while this experimental lane keeps real-input review, export, and provenance surfaces available for pilot evaluation.",
                [info.value for info in at.info],
            )
            self.assertIn(
                "Required columns: `preferred_machine_family`, `material_code`, `task_name`, `quantity`",
                combined_markdown,
            )
            self.assertIn(
                "Pilot Provenance & Export",
                combined_markdown,
            )
            self.assertIn(
                "Scheduling exports package the current review state for handoff without claiming defended production capability.",
                combined_captions,
            )

            warning_text = [warning.value for warning in at.warning]
            self.assertIn(
                "Experimental bonus function only. Not part of current defended production scope. No DB writes. No artifact promotion. No solver claim. No predictive-maintenance production claim.",
                warning_text,
            )


if __name__ == "__main__":
    unittest.main()
