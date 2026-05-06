import copy
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from core.data_contracts import load_source_manifest
from core.csi_boundary_inventory import (
    build_csi_boundary_candidate_inventory,
    canonical_csi_event_month,
    classify_boundary_direction,
)


class CsiBoundaryInventoryTests(unittest.TestCase):
    def test_canonical_month_assignment_uses_first_available_timestamp(self):
        row = {
            "工程開始時間": None,
            "工程結束時間": "2025-08-01 01:00:00",
            "準備結束時間": "2025-07-31 23:55:00",
            "班次內日期": "2025-07-31",
        }

        self.assertEqual(canonical_csi_event_month(row), "2025-08")

    def test_forward_spill_classification_works(self):
        self.assertEqual(
            classify_boundary_direction("2025-07", "2025-08"),
            "forward_spill_to_next_month",
        )

    def test_backward_spill_classification_works(self):
        self.assertEqual(
            classify_boundary_direction("2025-08", "2025-07"),
            "backward_spill_to_previous_month",
        )

    def test_same_month_rows_are_not_candidates(self):
        self.assertEqual(classify_boundary_direction("2025-08", "2025-08"), "same_month")

    def test_missing_required_timestamp_columns_fail_clearly(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = self._manifest_with_csi_file("CSI(July2025 to Feb2026)/fixture.xlsx")
            self._create_placeholder_support_files(root, manifest)
            self._write_manifest_csi_file(
                root,
                "CSI(July2025 to Feb2026)/fixture.xlsx",
                pd.DataFrame(
                    [
                        {
                            "工程開始時間": "2025-07-01 00:00:00",
                            "工程結束時間": "2025-07-01 01:00:00",
                        }
                    ]
                ),
            )

            inventory = build_csi_boundary_candidate_inventory(
                data_root=root,
                month_keys=("2025-07",),
                manifest=manifest,
            )

        self.assertEqual(inventory["unresolved_package_count"], 1)
        self.assertIn("missing required timestamp columns", inventory["unresolved_packages"][0]["error"]["message"])

    def test_inventory_helper_does_not_create_db_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = self._manifest_with_csi_file("CSI(July2025 to Feb2026)/fixture.xlsx")
            self._create_placeholder_support_files(root, manifest)
            self._write_manifest_csi_file(
                root,
                "CSI(July2025 to Feb2026)/fixture.xlsx",
                self._fixture_dataframe(),
            )
            before_db_files = set(root.glob("*.db"))

            inventory = build_csi_boundary_candidate_inventory(
                data_root=root,
                month_keys=("2025-07",),
                manifest=manifest,
            )

            after_db_files = set(root.glob("*.db"))

        self.assertEqual(before_db_files, after_db_files)
        self.assertEqual(inventory["resolved_package_count"], 1)
        self.assertEqual(inventory["source_packages"][0]["boundary_candidate_count"], 2)
        self.assertEqual(inventory["source_packages"][0]["forward_spill_count"], 1)
        self.assertEqual(inventory["source_packages"][0]["backward_spill_count"], 1)

    def test_source_paths_must_remain_under_supplied_data_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = self._manifest_with_csi_file("../outside.xlsx")

            inventory = build_csi_boundary_candidate_inventory(
                data_root=root,
                month_keys=("2025-07",),
                manifest=manifest,
            )

        self.assertEqual(inventory["unresolved_package_count"], 1)
        self.assertIn("data_root", inventory["unresolved_packages"][0]["error"]["message"])

    def _fixture_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "班次內日期": "2025-07-15",
                    "機台編號": "D-001",
                    "作业": "J1",
                    "物料": "M1",
                    "工程開始時間": "2025-07-15 08:00:00",
                    "準備結束時間": "2025-07-15 07:55:00",
                    "工程結束時間": "2025-07-15 09:00:00",
                    "正品數量": 10,
                },
                {
                    "班次內日期": "2025-07-31",
                    "機台編號": "D-002",
                    "作业": "J2",
                    "物料": "M2",
                    "工程開始時間": "2025-08-01 00:05:00",
                    "準備結束時間": "2025-08-01 00:00:00",
                    "工程結束時間": "2025-08-01 01:00:00",
                    "正品數量": 20,
                },
                {
                    "班次內日期": "2025-07-01",
                    "機台編號": "D-003",
                    "作业": "J3",
                    "物料": "M3",
                    "工程開始時間": "2025-06-30 23:55:00",
                    "準備結束時間": "2025-06-30 23:50:00",
                    "工程結束時間": "2025-07-01 00:30:00",
                    "正品數量": 30,
                },
            ]
        )

    def _write_manifest_csi_file(self, root: Path, relative_path: str, df: pd.DataFrame) -> None:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(path, index=False)

    def _manifest_with_csi_file(self, relative_path: str) -> dict:
        manifest = copy.deepcopy(load_source_manifest())
        spec = manifest["month_source_files"]["2025-07"]
        spec["csi_file"] = relative_path
        spec["energy_files"] = ["energy.xlsx"]
        spec["mes_file"] = "mes.xlsx"
        return manifest

    def _create_placeholder_support_files(self, root: Path, manifest: dict) -> None:
        spec = manifest["month_source_files"]["2025-07"]
        for relative_path in [*spec["energy_files"], spec["mes_file"]]:
            path = root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"placeholder")


if __name__ == "__main__":
    unittest.main()
