import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from core.etl.extractor import DataExtractor
from modules.etl_module import _uploaded_file_suffix


class DataExtractorCompatibilityTests(unittest.TestCase):
    def test_read_excel_with_variant_support_falls_back_to_converted_xlsx_for_xls(self):
        expected_df = pd.DataFrame([{"機台編號": "D-024-075"}])
        converted_path = Path("/tmp/task13_converted.xlsx")

        with patch(
            "core.etl.extractor.pd.read_excel",
            side_effect=[
                ImportError("Missing optional dependency 'xlrd'"),
                expected_df,
            ],
        ) as read_excel, patch.object(
            DataExtractor,
            "_convert_xls_with_helper",
            return_value=converted_path,
        ) as convert_xls:
            result_df = DataExtractor._read_excel_with_variant_support("/tmp/task13_source.xls")

        self.assertTrue(result_df.equals(expected_df))
        convert_xls.assert_called_once_with(Path("/tmp/task13_source.xls"))
        self.assertEqual(read_excel.call_args_list[0].kwargs["engine"], "xlrd")
        self.assertEqual(read_excel.call_args_list[1].args[0], converted_path)


class UploadedFileSuffixTests(unittest.TestCase):
    class _Upload:
        def __init__(self, name):
            self.name = name

    def test_uploaded_file_suffix_preserves_xls_variants(self):
        self.assertEqual(_uploaded_file_suffix(self._Upload("source.xls")), ".xls")
        self.assertEqual(_uploaded_file_suffix(self._Upload("source.xlsx")), ".xlsx")
        self.assertEqual(_uploaded_file_suffix(self._Upload("source.xlsm")), ".xlsm")

    def test_uploaded_file_suffix_defaults_when_name_is_missing(self):
        self.assertEqual(_uploaded_file_suffix(object()), ".xlsx")


if __name__ == "__main__":
    unittest.main()
