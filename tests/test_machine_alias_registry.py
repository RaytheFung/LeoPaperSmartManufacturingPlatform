import unittest

from core.machine_alias_registry import (
    DEFAULT_EXCEPTIONS_PATH,
    DEFAULT_REGISTRY_PATH,
    MAPPING_METADATA_FIELDS,
    build_machine_resolution_metadata,
    load_machine_alias_registry,
)


class MachineAliasRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_machine_alias_registry()

    def test_registry_files_exist_in_repo(self):
        self.assertTrue(DEFAULT_REGISTRY_PATH.exists())
        self.assertTrue(DEFAULT_EXCEPTIONS_PATH.exists())

    def test_loader_reads_expected_record_and_exception_counts(self):
        self.assertEqual(len(self.registry.records_by_canonical), 101)
        self.assertEqual(len(self.registry.exceptions), 5)

    def test_normalize_machine_id_handles_csi_identifier(self):
        self.assertEqual(self.registry.normalize_machine_id("D-024-018"), "024-018")

    def test_resolve_csi_machine_id(self):
        result = self.registry.resolve_canonical_machine_id("D-024-003", source_system="csi")
        self.assertTrue(result["found"])
        self.assertEqual(result["canonical_machine_id"], "024-003")
        self.assertEqual(result["matched_on"], "csi_machine_id")

    def test_resolve_mes_primary_resource(self):
        result = self.registry.resolve_canonical_machine_id("1024-00003", source_system="mes")
        self.assertTrue(result["found"])
        self.assertEqual(result["canonical_machine_id"], "024-003")
        self.assertEqual(result["preferred_mes_resource"], "1024-00003")

    def test_resolve_energy_label_with_embedded_machine_id(self):
        result = self.registry.resolve_canonical_machine_id("印刷机024-018主機+IR", source_system="energy")
        self.assertTrue(result["found"])
        self.assertEqual(result["canonical_machine_id"], "024-018")
        self.assertIn(result["matched_on"], {"energy_alias_example", "energy_extracted_id"})

    def test_resolve_energy_label_for_mes_alias_exception_family(self):
        result = self.registry.resolve_canonical_machine_id(
            "UV上光機1035-10005 主機合計用量",
            source_system="energy",
        )
        self.assertTrue(result["found"])
        self.assertEqual(result["canonical_machine_id"], "035-017")
        self.assertEqual(result["preferred_mes_resource"], "1035-10005")

    def test_resolve_maintenance_legacy_alias(self):
        result = self.registry.resolve_canonical_machine_id("342-002", source_system="maintenance")
        self.assertTrue(result["found"])
        self.assertEqual(result["canonical_machine_id"], "1264-00003")
        self.assertEqual(result["matched_on"], "maintenance_legacy_id")

    def test_exception_resolution_for_035_017(self):
        result = self.registry.resolve_canonical_machine_id("1035-00017", source_system="mes")
        self.assertTrue(result["found"])
        self.assertEqual(result["canonical_machine_id"], "035-017")
        self.assertTrue(result["exception_applied"])
        self.assertEqual(result["exception_issue_type"], "MES_alias_inconsistency")
        self.assertEqual(result["preferred_mes_resource"], "1035-10005")

    def test_exception_resolution_for_035_018(self):
        result = self.registry.resolve_canonical_machine_id("1035-00018", source_system="mes")
        self.assertTrue(result["found"])
        self.assertEqual(result["canonical_machine_id"], "035-018")
        self.assertTrue(result["exception_applied"])
        self.assertEqual(result["preferred_mes_resource"], "1035-10007")

    def test_energy_only_candidate_is_resolved_but_flagged(self):
        result = self.registry.resolve_canonical_machine_id("(四期)印刷机024-070合計用量", source_system="energy")
        self.assertTrue(result["found"])
        self.assertEqual(result["canonical_machine_id"], "024-070")
        self.assertEqual(result["scope_status"], "energy_only")

    def test_unknown_machine_returns_not_found(self):
        result = self.registry.resolve_canonical_machine_id("UNKNOWN-MACHINE", source_system="mes")
        self.assertFalse(result["found"])
        self.assertIsNone(result["canonical_machine_id"])

    def test_task13_new_machine_024_075_is_resolved_across_sources(self):
        csi_result = self.registry.resolve_canonical_machine_id("D-024-075", source_system="csi")
        mes_result = self.registry.resolve_canonical_machine_id("1024-00075", source_system="mes")
        energy_result = self.registry.resolve_canonical_machine_id("印刷機024-075主機", source_system="energy")

        self.assertEqual(csi_result["canonical_machine_id"], "024-075")
        self.assertEqual(mes_result["canonical_machine_id"], "024-075")
        self.assertEqual(energy_result["canonical_machine_id"], "024-075")

    def test_task13_new_machine_024_080_is_resolved_across_sources(self):
        csi_result = self.registry.resolve_canonical_machine_id("D-024-080", source_system="csi")
        mes_result = self.registry.resolve_canonical_machine_id("1024-00080", source_system="mes")
        energy_result = self.registry.resolve_canonical_machine_id("印刷機024-080 UV", source_system="energy")

        self.assertEqual(csi_result["canonical_machine_id"], "024-080")
        self.assertEqual(mes_result["canonical_machine_id"], "024-080")
        self.assertEqual(energy_result["canonical_machine_id"], "024-080")

    def test_build_machine_resolution_metadata_returns_expected_fields(self):
        metadata = build_machine_resolution_metadata("1035-00017", "mes", registry=self.registry)
        self.assertEqual(set(metadata.keys()), set(MAPPING_METADATA_FIELDS))
        self.assertEqual(metadata["canonical_machine_id"], "035-017")
        self.assertEqual(metadata["matched_on"], "mes_secondary_alias")
        self.assertTrue(metadata["exception_applied"])


if __name__ == "__main__":
    unittest.main()
