import os
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from core.runtime_mode import DEMO_READONLY_RUNTIME_MODE, RUNTIME_MODE_ENV_VAR


class DemoReadonlyModeSmokeTests(unittest.TestCase):
    def _load_app(self) -> AppTest:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        at = AppTest.from_file(str(app_path), default_timeout=240)
        at.run()
        return at

    def test_demo_readonly_mode_is_visible_and_etl_controls_are_gated(self):
        with patch.dict(os.environ, {RUNTIME_MODE_ENV_VAR: DEMO_READONLY_RUNTIME_MODE}, clear=False):
            at = self._load_app()

            combined_markdown = "\n".join(markdown.value for markdown in at.markdown)
            combined_text = "\n".join(
                [markdown.value for markdown in at.markdown]
                + [info.value for info in at.info]
                + [warning.value for warning in at.warning]
                + [caption.value for caption in at.caption]
            )
            self.assertIn("Demo Read-Only Mode", combined_markdown)

            button_labels = [widget.label for widget in at.button]
            info_text = [info.value for info in at.info]

            self.assertNotIn("1️⃣ Energy Consumption Files", combined_text)
            self.assertNotIn("🚀 Process", " | ".join(button_labels))
            self.assertNotIn("🔄 Bulk Select", button_labels)
            self.assertNotIn("↺ Reset Order", button_labels)
            self.assertIn(
                "Demo read-only mode is active. Upload/process/backfill controls and historical-run mutations are hidden. Latest run analytics and historical provenance remain available.",
                info_text,
            )

            route_selectbox = next(
                widget for widget in at.selectbox if widget.label == "Choose Analysis Module"
            )
            route_selectbox.select("⚡ Energy Analysis")
            at.run()

            self.assertIn("⚡ Energy Analysis Dashboard", [header.value for header in at.header])

    def test_demo_readonly_mode_hides_ml_and_maintenance_write_controls(self):
        with patch.dict(os.environ, {RUNTIME_MODE_ENV_VAR: DEMO_READONLY_RUNTIME_MODE}, clear=False):
            at = self._load_app()
            route_selectbox = next(
                widget for widget in at.selectbox if widget.label == "Choose Analysis Module"
            )

            route_selectbox.select("🤖 Efficiency Prediction & Governance")
            at.run()
            self.assertIn("🤖 Efficiency Prediction & Model Governance", [title.value for title in at.title])
            self.assertNotIn("Retrain from canonical Gold", [widget.label for widget in at.button])
            self.assertIn(
                "Demo read-only mode is active. Reviewer-facing inference, review, and Scenario Lab surfaces stay available. Retraining controls are hidden.",
                [info.value for info in at.info],
            )

            route_selectbox = next(
                widget for widget in at.selectbox if widget.label == "Choose Analysis Module"
            )
            route_selectbox.select("🔧 Maintenance")
            at.run()
            self.assertIn("🔧 Maintenance Evidence & Coverage", [title.value for title in at.title])
            self.assertNotIn("Process Maintenance Data", [widget.label for widget in at.button])
            combined_text = "\n".join(
                [markdown.value for markdown in at.markdown]
                + [info.value for info in at.info]
                + [warning.value for warning in at.warning]
                + [caption.value for caption in at.caption]
            )
            self.assertNotIn("Upload Maintenance Records", combined_text)
            self.assertNotIn("Choose Maintenance Excel File", combined_text)
            self.assertIn(
                "Demo read-only mode is active. Evidence and browse surfaces stay available, while upload/integration controls are hidden.",
                [info.value for info in at.info],
            )


if __name__ == "__main__":
    unittest.main()
