import unittest

from core.runtime_capabilities import (
    experimental_exports_are_allowed,
    experimental_real_input_upload_is_allowed,
    experimental_route_is_exposed,
    get_visible_pages,
    suppress_write_controls,
)
from core.runtime_mode import (
    DEMO_READONLY_RUNTIME_MODE,
    PILOT_REVIEW_RUNTIME_MODE,
    STANDARD_RUNTIME_MODE,
)


class RuntimeCapabilityTests(unittest.TestCase):
    def test_demo_readonly_hides_experimental_route_and_suppresses_writes(self):
        self.assertTrue(suppress_write_controls(DEMO_READONLY_RUNTIME_MODE))
        self.assertFalse(experimental_route_is_exposed(DEMO_READONLY_RUNTIME_MODE))
        self.assertFalse(experimental_real_input_upload_is_allowed(DEMO_READONLY_RUNTIME_MODE))
        self.assertFalse(experimental_exports_are_allowed(DEMO_READONLY_RUNTIME_MODE))
        self.assertNotIn("🧪 Experimental Intelligence Lab", get_visible_pages(DEMO_READONLY_RUNTIME_MODE))

    def test_pilot_review_exposes_experimental_route_but_keeps_core_read_only(self):
        self.assertTrue(suppress_write_controls(PILOT_REVIEW_RUNTIME_MODE))
        self.assertTrue(experimental_route_is_exposed(PILOT_REVIEW_RUNTIME_MODE))
        self.assertTrue(experimental_real_input_upload_is_allowed(PILOT_REVIEW_RUNTIME_MODE))
        self.assertTrue(experimental_exports_are_allowed(PILOT_REVIEW_RUNTIME_MODE))
        self.assertIn("🧪 Experimental Intelligence Lab", get_visible_pages(PILOT_REVIEW_RUNTIME_MODE))

    def test_standard_mode_keeps_operational_controls_available(self):
        self.assertFalse(suppress_write_controls(STANDARD_RUNTIME_MODE))
        self.assertTrue(experimental_route_is_exposed(STANDARD_RUNTIME_MODE))
        self.assertTrue(experimental_real_input_upload_is_allowed(STANDARD_RUNTIME_MODE))
        self.assertTrue(experimental_exports_are_allowed(STANDARD_RUNTIME_MODE))


if __name__ == "__main__":
    unittest.main()
