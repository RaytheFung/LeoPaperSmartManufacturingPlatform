import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class Task11RuntimeReconciliationSmokeTests(unittest.TestCase):
    def _load_app(self) -> AppTest:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        at = AppTest.from_file(str(app_path), default_timeout=180)
        at.run()
        return at

    def test_defended_sidebar_and_key_tabs_match_baseline(self):
        at = self._load_app()

        route_selectbox = next(
            widget for widget in at.selectbox if widget.label == "Choose Analysis Module"
        )
        self.assertEqual(
            route_selectbox.options,
            [
                "🔄 ETL Pipeline",
                "📊 Canonical Operations Overview",
                "⚡ Energy Analysis",
                "🎯 Operational Decision Support",
                "🤖 Efficiency Prediction & Governance",
                "🔧 Maintenance",
                "🧪 Experimental Intelligence Lab",
            ],
        )
        self.assertEqual(
            [tab.label for tab in at.tabs],
            ["📤 Upload New Data", "🧭 Latest Run Snapshot", "📈 Historical Runs"],
        )

        route_selectbox.select("🧪 Experimental Intelligence Lab")
        at.run()

        self.assertIn("🧪 Experimental Intelligence Lab", [title.value for title in at.title])
        self.assertIn(
            "Anchor month for current-state view",
            [widget.label for widget in at.selectbox],
        )
        self.assertEqual(
            [tab.label for tab in at.tabs],
            [
                "Constraint-Aware Scheduling Prototype",
                "Predictive Maintenance Prototype",
            ],
        )


if __name__ == "__main__":
    unittest.main()
