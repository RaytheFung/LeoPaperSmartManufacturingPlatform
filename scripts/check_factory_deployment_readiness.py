"""Read-only factory deployment readiness preflight.

This helper inspects repository paths, Git tracking metadata, and safe policy
constants only. It does not import Streamlit, open SQLite, or write files.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable


DB_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
LOCAL_ARTIFACT_DIR_NAMES = {".venv", ".conda311", ".miniforge", "temp_uploads"}
ALLOWED_TRACKED_ETL_OUTPUTS = {
    "etl_outputs/.gitkeep",
    "etl_outputs/ETL_OUTPUTS_GUIDE.md",
}

REQUIRED_FILES = (
    "README.md",
    "docs/operations/FACTORY_DEPLOYMENT_RUNBOOK.md",
    "docs/operations/LIVE_DB_MIGRATION_GATE_CHECKLIST.md",
    "docs/operations/FACTORY_PILOT_OPERATOR_ACCEPTANCE_CHECKLIST.md",
    "docs/technical/POSTFYP_STAGEC3_APP_LAUNCH_ROUTE_SMOKE_REPORT.md",
    "app.py",
    "core/runtime_mode.py",
    "core/runtime_capabilities.py",
    "core/runtime_paths.py",
    "config/source_manifest.v1.json",
    "config/data_quality_rules.v1.json",
)


def find_repo_root(start: Path | None = None) -> Path:
    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / "app.py").exists() and (candidate / "core").is_dir():
            return candidate
    return Path(__file__).resolve().parents[1]


def iter_paths_max_depth(root: Path, max_depth: int) -> Iterable[Path]:
    root = root.resolve()
    stack = [(root, 0)]
    while stack:
        current, depth = stack.pop()
        if depth > max_depth:
            continue
        if current != root:
            yield current
        if depth == max_depth or not current.is_dir():
            continue
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in reversed(children):
            if child.name == ".git":
                continue
            stack.append((child, depth + 1))


def _relative(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def get_tracked_files(repo_root: Path, pathspec: str | None = None) -> list[str]:
    command = ["git", "ls-files"]
    if pathspec:
        command.append(pathspec)
    try:
        completed = subprocess.run(
            command,
            cwd=repo_root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []
    if completed.returncode != 0:
        return []
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _check(name: str, passed: bool, details: object, severity: str = "critical") -> dict[str, object]:
    return {
        "name": name,
        "passed": bool(passed),
        "severity": severity,
        "details": details,
    }


def build_readiness_report(
    repo_root: Path,
    *,
    tracked_files_provider: Callable[[Path, str | None], list[str]] | None = None,
    include_policy_imports: bool = True,
) -> dict[str, object]:
    repo_root = repo_root.resolve()
    tracked_provider = tracked_files_provider or get_tracked_files
    checks: list[dict[str, object]] = []

    missing_required = [
        relative_path
        for relative_path in REQUIRED_FILES
        if not (repo_root / relative_path).exists()
    ]
    checks.append(_check("required_files_present", not missing_required, {"missing": missing_required}))

    tracked_db = tracked_provider(repo_root, "manufacturing_data.db")
    checks.append(
        _check(
            "manufacturing_data_db_not_tracked",
            not tracked_db,
            {"tracked_entries": tracked_db},
        )
    )

    db_files = [
        _relative(path, repo_root)
        for path in iter_paths_max_depth(repo_root, 5)
        if path.is_file() and path.suffix.lower() in DB_SUFFIXES
    ]
    checks.append(_check("no_repo_local_db_files", not db_files, {"paths": db_files}))

    local_artifact_dirs = [
        _relative(path, repo_root)
        for path in iter_paths_max_depth(repo_root, 5)
        if path.is_dir() and path.name in LOCAL_ARTIFACT_DIR_NAMES
    ]
    checks.append(
        _check("no_local_env_or_upload_dirs", not local_artifact_dirs, {"paths": local_artifact_dirs})
    )

    tracked_etl_outputs = set(tracked_provider(repo_root, "etl_outputs"))
    unexpected_etl_outputs = sorted(tracked_etl_outputs - ALLOWED_TRACKED_ETL_OUTPUTS)
    checks.append(
        _check(
            "etl_outputs_tracks_only_control_files",
            (repo_root / "etl_outputs").is_dir() and not unexpected_etl_outputs,
            {
                "tracked_entries": sorted(tracked_etl_outputs),
                "unexpected_tracked_entries": unexpected_etl_outputs,
            },
        )
    )

    if include_policy_imports:
        checks.extend(_build_policy_import_checks(repo_root))

    critical_failures = [
        check["name"]
        for check in checks
        if check["severity"] == "critical" and not check["passed"]
    ]
    return {
        "success": not critical_failures,
        "repo_root": str(repo_root),
        "checks": checks,
        "summary": {
            "check_count": len(checks),
            "passed_count": sum(1 for check in checks if check["passed"]),
            "critical_failures": critical_failures,
        },
    }


def _build_policy_import_checks(repo_root: Path) -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    repo_root_text = str(repo_root)
    inserted = False
    if repo_root_text not in sys.path:
        sys.path.insert(0, repo_root_text)
        inserted = True
    try:
        from core.csi_carry_forward_config import (
            DEFAULT_CARRY_FORWARD_MODE,
            build_default_carry_forward_config,
            require_disabled_by_default,
        )

        default_config = build_default_carry_forward_config()
        require_disabled_by_default(default_config)
        checks.append(
            _check(
                "carry_forward_default_disabled",
                DEFAULT_CARRY_FORWARD_MODE == "disabled" and default_config.mode == "disabled",
                {
                    "default_constant": DEFAULT_CARRY_FORWARD_MODE,
                    "default_config_mode": default_config.mode,
                },
            )
        )
    except Exception as exc:  # pragma: no cover - exercised by integration failure.
        checks.append(
            _check(
                "carry_forward_default_disabled",
                False,
                {"error": f"{type(exc).__name__}: {exc}"},
            )
        )

    try:
        from core.runtime_mode import VALID_RUNTIME_MODES

        required_modes = {"standard", "demo_readonly", "pilot_review"}
        missing_modes = sorted(required_modes - set(VALID_RUNTIME_MODES))
        checks.append(
            _check(
                "supported_runtime_modes_present",
                not missing_modes,
                {"modes": sorted(VALID_RUNTIME_MODES), "missing": missing_modes},
            )
        )
    except Exception as exc:  # pragma: no cover - exercised by integration failure.
        checks.append(
            _check(
                "supported_runtime_modes_present",
                False,
                {"error": f"{type(exc).__name__}: {exc}"},
            )
        )
    finally:
        if inserted:
            try:
                sys.path.remove(repo_root_text)
            except ValueError:
                pass
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only factory deployment readiness preflight.")
    parser.add_argument("--repo-root", type=Path, default=find_repo_root())
    args = parser.parse_args(argv)

    report = build_readiness_report(args.repo_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
