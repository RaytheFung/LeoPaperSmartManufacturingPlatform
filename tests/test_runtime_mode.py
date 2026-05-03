import unittest

from core.runtime_mode import (
    DEMO_READONLY_RUNTIME_MODE,
    PILOT_REVIEW_RUNTIME_MODE,
    RUNTIME_MODE_ENV_VAR,
    STANDARD_RUNTIME_MODE,
    get_runtime_mode_label,
    normalize_runtime_mode,
    resolve_runtime_mode,
)


class RuntimeModeTests(unittest.TestCase):
    def test_normalize_runtime_mode_defaults_to_standard(self):
        self.assertEqual(normalize_runtime_mode(None), STANDARD_RUNTIME_MODE)
        self.assertEqual(normalize_runtime_mode("unknown"), STANDARD_RUNTIME_MODE)

    def test_resolve_runtime_mode_prefers_session_state_then_query_then_env(self):
        self.assertEqual(
            resolve_runtime_mode(env={RUNTIME_MODE_ENV_VAR: DEMO_READONLY_RUNTIME_MODE}),
            DEMO_READONLY_RUNTIME_MODE,
        )
        self.assertEqual(
            resolve_runtime_mode(
                env={RUNTIME_MODE_ENV_VAR: STANDARD_RUNTIME_MODE},
                query_params={"runtime_mode": DEMO_READONLY_RUNTIME_MODE},
            ),
            DEMO_READONLY_RUNTIME_MODE,
        )
        self.assertEqual(
            resolve_runtime_mode(
                env={RUNTIME_MODE_ENV_VAR: STANDARD_RUNTIME_MODE},
                query_params={"runtime_mode": STANDARD_RUNTIME_MODE},
                session_state={"runtime_mode": DEMO_READONLY_RUNTIME_MODE},
            ),
            DEMO_READONLY_RUNTIME_MODE,
        )

    def test_runtime_mode_label(self):
        self.assertEqual(get_runtime_mode_label(DEMO_READONLY_RUNTIME_MODE), "Demo Read-Only Mode")
        self.assertEqual(get_runtime_mode_label(PILOT_REVIEW_RUNTIME_MODE), "Pilot Review Mode")
        self.assertEqual(get_runtime_mode_label(STANDARD_RUNTIME_MODE), "Standard Mode")


if __name__ == "__main__":
    unittest.main()
