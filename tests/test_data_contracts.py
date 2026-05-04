import copy
import unittest
from pathlib import Path

from core.data_contracts import (
    get_accepted_canonical_months,
    get_config_dir,
    get_source_scope_for_month,
    load_data_quality_rules,
    load_source_manifest,
    validate_data_quality_rules_shape,
    validate_manifest_shape,
)


class DataContractsTests(unittest.TestCase):
    def test_source_manifest_loads(self):
        manifest = load_source_manifest()

        self.assertEqual(manifest["schema_version"], "source_manifest.v1")
        self.assertEqual(get_config_dir(), Path(__file__).resolve().parents[1] / "config")

    def test_accepted_months_cover_jan_2025_through_feb_2026(self):
        months = get_accepted_canonical_months()

        self.assertEqual(months[0], "2025-01")
        self.assertEqual(months[-1], "2026-02")
        self.assertEqual(len(months), 14)
        self.assertIn("2025-07", months)
        self.assertIn("2026-02", months)

    def test_march_2026_is_not_accepted_canonical_scope_by_default(self):
        manifest = load_source_manifest()

        self.assertNotIn("2026-03", get_accepted_canonical_months(manifest))
        with self.assertRaisesRegex(ValueError, "2026-03"):
            get_source_scope_for_month("2026-03", manifest)

    def test_expected_source_families_are_present(self):
        manifest = load_source_manifest()
        families = manifest["source_families"]

        for family_name in (
            "energy_hourly_report_v1",
            "csi_monthly_xlsx_v1",
            "csi_monthly_xls_variant_v1",
            "mes_monthly_report_v1",
            "maintenance_transaction_v1",
            "energy_daily_report_v1",
            "energy_tariff_aggregate_v1",
        ):
            self.assertIn(family_name, families)
        self.assertEqual(families["energy_daily_report_v1"]["status"], "supplementary_only")
        self.assertEqual(families["energy_tariff_aggregate_v1"]["status"], "separate_family")

    def test_source_scope_for_month_uses_relative_folders(self):
        initial_scope = get_source_scope_for_month("2025-01")
        extended_scope = get_source_scope_for_month("2026-02")

        self.assertEqual(initial_scope["scope_id"], "2025_jan_jun_initial")
        self.assertEqual(extended_scope["scope_id"], "2025_jul_2026_feb_collected")
        self.assertFalse(Path(initial_scope["root_folder"]).is_absolute())
        self.assertFalse(Path(extended_scope["root_folder"]).is_absolute())

    def test_data_quality_rules_load(self):
        rules = load_data_quality_rules()

        self.assertEqual(rules["schema_version"], "data_quality_rules.v1")
        self.assertEqual(rules["accepted_month_range"]["start_month"], "2025-01")
        self.assertEqual(rules["accepted_month_range"]["end_month"], "2026-02")
        self.assertIn("2026-03", rules["accepted_month_range"]["excluded_by_default"])
        self.assertGreaterEqual(len(rules["partial_energy_month_flags"]), 1)
        self.assertGreaterEqual(len(rules["accepted_sentinel_anomalies"]), 1)

    def test_malformed_manifest_raises_value_error(self):
        manifest = load_source_manifest()
        malformed = copy.deepcopy(manifest)
        malformed.pop("source_families")

        with self.assertRaisesRegex(ValueError, "source_families"):
            validate_manifest_shape(malformed)

    def test_manifest_with_absolute_path_raises_value_error(self):
        manifest = load_source_manifest()
        malformed = copy.deepcopy(manifest)
        malformed["source_scopes"][0]["root_folder"] = "/tmp/source_data"

        with self.assertRaisesRegex(ValueError, "absolute local paths"):
            validate_manifest_shape(malformed)

    def test_malformed_data_quality_rules_raise_value_error(self):
        rules = load_data_quality_rules()
        malformed = copy.deepcopy(rules)
        malformed.pop("accepted_sentinel_anomalies")

        with self.assertRaisesRegex(ValueError, "accepted_sentinel_anomalies"):
            validate_data_quality_rules_shape(malformed)


if __name__ == "__main__":
    unittest.main()
