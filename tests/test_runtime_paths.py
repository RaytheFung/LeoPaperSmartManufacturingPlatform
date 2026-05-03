import unittest

from core.runtime_paths import get_extended_raw_dataset_root, get_raw_dataset_root, get_repo_root


class RuntimePathsTests(unittest.TestCase):
    def test_raw_dataset_prefers_repo_local_source_data_tree(self):
        expected = get_repo_root() / "source_data" / "2025_jan_jun_initial"

        self.assertTrue(expected.exists())
        self.assertEqual(get_raw_dataset_root(), expected)

    def test_extended_raw_dataset_prefers_repo_local_copy(self):
        expected = get_repo_root() / "source_data" / "2025_jul_2026_feb_collected"

        self.assertTrue(expected.exists())
        self.assertEqual(get_extended_raw_dataset_root(), expected)


if __name__ == "__main__":
    unittest.main()
