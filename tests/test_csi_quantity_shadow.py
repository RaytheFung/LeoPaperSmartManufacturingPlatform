import unittest

from core.csi_quantity_shadow import (
    CSI_QTY_SHADOW_CONTRACT,
    evaluate_shadow_quantity,
)


class CsiQuantityShadowTests(unittest.TestCase):
    def test_shadow_keeps_single_row_anchor_groups_unchanged(self):
        rows = [
            {
                "canonical_machine_id": "035-017",
                "hour_ts": "2025-06-03T05:00:00",
                "csi_source_row_hash": "hash-035-017",
                "production_minutes": 54.36760896495606,
                "good_qty": 1550.0,
                "scrap_qty": 0.0,
                "csi_qty_row_basis_minutes": 18.0,
                "csi_qty_minute_budget_anomaly_flag": 0,
            },
            {
                "canonical_machine_id": "035-018",
                "hour_ts": "2025-02-17T15:00:00",
                "csi_source_row_hash": "hash-035-018",
                "production_minutes": 53.787058030794725,
                "good_qty": 1607.0,
                "scrap_qty": 0.0,
                "csi_qty_row_basis_minutes": 16.890202582335295,
                "csi_qty_minute_budget_anomaly_flag": 0,
            },
        ]

        evaluated = evaluate_shadow_quantity(rows)
        self.assertEqual(len(evaluated), 2)
        for row in evaluated:
            self.assertEqual(row["shadow_contract"], CSI_QTY_SHADOW_CONTRACT)
            self.assertEqual(row["shadow_group_eligible"], 1)
            self.assertIsNone(row["shadow_group_ineligible_reason"])
            self.assertEqual(row["shadow_good_qty"], row["good_qty"])
            self.assertEqual(row["shadow_scrap_qty"], row["scrap_qty"])
            self.assertEqual(row["shadow_material_change_flag"], 0)

    def test_shadow_excludes_anchor_anomaly_group(self):
        rows = [
            {
                "canonical_machine_id": "166-002",
                "hour_ts": "2025-04-17T14:00:00",
                "csi_source_row_hash": "hash-166-002",
                "production_minutes": 276.57559944183396,
                "good_qty": 130.7339444849789,
                "scrap_qty": 0.0,
                "csi_qty_row_basis_minutes": 51.94954109797846,
                "csi_qty_minute_budget_anomaly_flag": 1,
            },
            {
                "canonical_machine_id": "166-002",
                "hour_ts": "2025-04-17T15:00:00",
                "csi_source_row_hash": "hash-166-002",
                "production_minutes": 40.0,
                "good_qty": 784.2660555150211,
                "scrap_qty": 0.0,
                "csi_qty_row_basis_minutes": 311.69724774903354,
                "csi_qty_minute_budget_anomaly_flag": 0,
            },
        ]

        evaluated = evaluate_shadow_quantity(rows)
        self.assertEqual(len(evaluated), 2)
        for row in evaluated:
            self.assertEqual(row["shadow_group_eligible"], 0)
            self.assertEqual(row["shadow_group_ineligible_reason"], "minute_budget_anomaly")
            self.assertEqual(row["shadow_good_qty"], row["good_qty"])
            self.assertEqual(row["shadow_material_change_flag"], 0)

    def test_shadow_reallocates_fully_eligible_multi_row_group_by_production_share(self):
        rows = [
            {
                "canonical_machine_id": "024-143",
                "hour_ts": "2025-05-29T21:00:00",
                "csi_source_row_hash": "hash-multi",
                "production_minutes": 45.0,
                "good_qty": 20.0,
                "scrap_qty": 2.0,
                "csi_qty_row_basis_minutes": 10.0,
                "csi_qty_minute_budget_anomaly_flag": 0,
            },
            {
                "canonical_machine_id": "024-143",
                "hour_ts": "2025-05-29T22:00:00",
                "csi_source_row_hash": "hash-multi",
                "production_minutes": 15.0,
                "good_qty": 80.0,
                "scrap_qty": 8.0,
                "csi_qty_row_basis_minutes": 40.0,
                "csi_qty_minute_budget_anomaly_flag": 0,
            },
        ]

        evaluated = sorted(evaluate_shadow_quantity(rows), key=lambda row: row["hour_ts"])
        self.assertEqual(evaluated[0]["shadow_group_eligible"], 1)
        self.assertAlmostEqual(evaluated[0]["shadow_good_qty"], 75.0)
        self.assertAlmostEqual(evaluated[0]["shadow_scrap_qty"], 7.5)
        self.assertEqual(evaluated[0]["shadow_material_change_flag"], 1)
        self.assertAlmostEqual(evaluated[1]["shadow_good_qty"], 25.0)
        self.assertAlmostEqual(evaluated[1]["shadow_scrap_qty"], 2.5)
        self.assertEqual(evaluated[1]["shadow_material_change_flag"], 1)

    def test_shadow_marks_null_basis_group_ineligible(self):
        rows = [
            {
                "canonical_machine_id": "024-147",
                "hour_ts": "2025-05-29T21:00:00",
                "csi_source_row_hash": "hash-null-basis",
                "production_minutes": 14.201757,
                "good_qty": 6544.0,
                "scrap_qty": 0.0,
                "csi_qty_row_basis_minutes": None,
                "csi_qty_minute_budget_anomaly_flag": 0,
            }
        ]

        evaluated = evaluate_shadow_quantity(rows)
        self.assertEqual(evaluated[0]["shadow_group_eligible"], 0)
        self.assertEqual(
            evaluated[0]["shadow_group_ineligible_reason"],
            "missing_positive_quantity_basis_minutes",
        )
        self.assertEqual(evaluated[0]["shadow_good_qty"], 6544.0)


if __name__ == "__main__":
    unittest.main()
