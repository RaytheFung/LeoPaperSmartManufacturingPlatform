import io
import unittest

from openpyxl import Workbook
import pandas as pd

from modules.etl_module import (
    _build_upload_detection_overview,
    _detect_month_year_from_filename,
    _resolve_uploaded_file_detection,
)
from modules.unified_view_module import (
    _build_unified_audit_cards,
    _build_unified_state_energy_chart_data,
    _build_unified_state_row_chart_data,
    _format_unified_measure,
)


class FakeUploadedFile:
    def __init__(self, name: str, payload: bytes = b"test-bytes"):
        self.name = name
        self._payload = payload
        self.size = len(payload)

    def getvalue(self) -> bytes:
        return self._payload


def _build_workbook_bytes():
    workbook = Workbook()
    worksheet = workbook.active
    worksheet["A1"] = "hour_ts"
    worksheet["A2"] = "2025-06-01 08:00"
    worksheet["A3"] = "2025-06-02 09:00"
    worksheet["A4"] = "2025-06-03 10:00"
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


class ETLMonthDetectionHelperTests(unittest.TestCase):
    def test_detect_month_year_from_filename_reads_month_tokens(self):
        detection = _detect_month_year_from_filename("能耗、費用報表June(1-30).xlsx")
        self.assertEqual(detection["month"], "June")
        self.assertIsNone(detection["year"])
        self.assertEqual(detection["source"], "filename")
        self.assertEqual(detection["confidence"], "medium")

    def test_resolve_uploaded_file_detection_uses_workbook_fallback_when_filename_is_ambiguous(self):
        uploaded_file = FakeUploadedFile(
            "monthly_energy_upload.xlsx",
            payload=_build_workbook_bytes(),
        )
        detection = _resolve_uploaded_file_detection(uploaded_file, "Energy")
        self.assertEqual(detection["month"], "June")
        self.assertEqual(detection["year"], 2025)
        self.assertIn("workbook sample", detection["source"])
        self.assertEqual(detection["status"], "resolved")

    def test_build_upload_detection_overview_flags_cross_file_conflicts(self):
        energy_files = [
            FakeUploadedFile("能耗、費用報表June(1-30).xlsx"),
            FakeUploadedFile("能耗、費用報表May(1-31).xlsx"),
        ]
        csi_file = FakeUploadedFile("CSI印刷心電圖報表June.xlsx")
        mes_file = FakeUploadedFile("MES生產數據JunePrinter.xlsx")

        overview = _build_upload_detection_overview(energy_files, csi_file, mes_file)

        self.assertIsNone(overview["detected_month"])
        self.assertTrue(overview["blocking_issues"])
        self.assertIn("multiple months", overview["blocking_issues"][0].lower())


class UnifiedViewFormattingHelperTests(unittest.TestCase):
    def test_format_unified_measure_compacts_large_values_and_keeps_full_precision_text(self):
        primary, secondary = _format_unified_measure(119_306_012.8, unit="pcs")
        self.assertEqual(primary, "119.31M pcs")
        self.assertIn("119,306,012.8 pcs", secondary)

    def test_build_unified_audit_cards_exposes_explicit_denominators(self):
        cards = _build_unified_audit_cards(
            {
                "unknown_or_unattributed_rows": 13_980,
                "unknown_or_unattributed_ratio": 13_980 / 62_639,
                "positive_good_rows": 36_115,
                "positive_good_ratio": 36_115 / 62_639,
                "maintenance_flag_rows": 84,
                "maintenance_flag_ratio": 84 / 62_639,
            },
            total_rows=62_639,
        )
        self.assertEqual(len(cards), 3)
        self.assertEqual(cards[0]["primary"], "22.3%")
        self.assertEqual(cards[0]["secondary"], "13,980 / 62,639 rows")
        self.assertIn("weighted efficiency KPI", cards[1]["description"])

    def test_state_energy_chart_helper_sorts_by_energy_and_drops_zero_energy_states(self):
        state_summary = pd.DataFrame(
            [
                {"state_label": "Setup Changeover", "energy_kwh": 572903.5, "row_count": 26574},
                {"state_label": "Production", "energy_kwh": 592932.1, "row_count": 22041},
                {"state_label": "Maintenance", "energy_kwh": 0.0, "row_count": 12},
            ]
        )

        chart_df = _build_unified_state_energy_chart_data(state_summary)

        self.assertEqual(list(chart_df["state_label"]), ["Setup Changeover", "Production"])
        self.assertEqual(list(chart_df["energy_kwh"]), [572903.5, 592932.1])

    def test_state_row_chart_helper_keeps_row_composition_explicit(self):
        state_summary = pd.DataFrame(
            [
                {"state_label": "Production", "energy_kwh": 592932.1, "row_count": 22041},
                {"state_label": "Setup Changeover", "energy_kwh": 572903.5, "row_count": 26574},
            ]
        )

        chart_df = _build_unified_state_row_chart_data(state_summary)

        self.assertEqual(list(chart_df["state_label"]), ["Production", "Setup Changeover"])
        self.assertEqual(list(chart_df["row_count"]), [22041, 26574])


if __name__ == "__main__":
    unittest.main()
