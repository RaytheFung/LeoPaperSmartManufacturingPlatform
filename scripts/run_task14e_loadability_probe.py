#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


PICKLE_LOADER_CODE = r"""
import json
import pickle
import sys
import time
from pathlib import Path

path = Path(sys.argv[1])
started = time.perf_counter()
with path.open("rb") as file_obj:
    payload = pickle.load(file_obj)
elapsed = time.perf_counter() - started
result = {
    "elapsed_seconds": elapsed,
    "payload_type": type(payload).__name__,
}
if isinstance(payload, dict):
    result["dict_keys"] = sorted(payload.keys())
    result["model_name"] = payload.get("model_name")
print(json.dumps(result))
"""

JOBLIB_LOADER_CODE = r"""
import json
import sys
import time
from pathlib import Path

import joblib

path = Path(sys.argv[1])
started = time.perf_counter()
payload = joblib.load(path)
elapsed = time.perf_counter() - started
result = {
    "elapsed_seconds": elapsed,
    "payload_type": type(payload).__name__,
}
if isinstance(payload, dict):
    result["dict_keys"] = sorted(payload.keys())
    result["model_name"] = payload.get("model_name")
print(json.dumps(result))
"""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark Task14E artifact loadability from live, staged, and local-copy paths."
    )
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--local-root", required=True)
    parser.add_argument("--timeout-seconds", type=int, default=7200)
    return parser


def _run_loader(
    *,
    python_executable: str,
    path: Path,
    loader: str,
    timeout_seconds: int,
) -> dict[str, object]:
    code = PICKLE_LOADER_CODE if loader == "pickle" else JOBLIB_LOADER_CODE
    started = time.perf_counter()
    completed = subprocess.run(
        [python_executable, "-c", code, str(path)],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    elapsed = time.perf_counter() - started
    result: dict[str, object] = {
        "loader": loader,
        "path": str(path),
        "wall_seconds": elapsed,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }
    if completed.returncode == 0 and completed.stdout.strip():
        try:
            result["payload"] = json.loads(completed.stdout.strip())
        except json.JSONDecodeError:
            result["payload"] = None
    else:
        result["payload"] = None
    return result


def _size_bytes(path: Path) -> int:
    return path.stat().st_size


def _classify(
    *,
    live_pickle_seconds: float,
    staged_pickle_seconds: float,
    local_pickle_seconds: float,
    staged_joblib_seconds: float | None,
    local_joblib_seconds: float | None,
) -> str:
    locality_factor = staged_pickle_seconds / max(local_pickle_seconds, 1e-9)
    live_factor = local_pickle_seconds / max(live_pickle_seconds, 1e-9)

    local_is_practical = local_pickle_seconds <= max(60.0, live_pickle_seconds * 20.0)
    path_gap_is_material = locality_factor >= 3.0

    if local_is_practical and path_gap_is_material:
        return "repo/iCloud/offloaded path problem"

    if (
        staged_joblib_seconds is not None
        and local_joblib_seconds is not None
        and local_joblib_seconds <= max(60.0, live_pickle_seconds * 20.0)
        and local_pickle_seconds > max(local_joblib_seconds * 3.0, live_pickle_seconds * 20.0)
    ):
        return "serialization/load-format problem"

    if (
        local_pickle_seconds > max(300.0, live_pickle_seconds * 20.0)
        and (
            local_joblib_seconds is None
            or local_joblib_seconds > max(300.0, live_pickle_seconds * 20.0)
        )
    ):
        return "candidate artifact intrinsic load problem"

    if path_gap_is_material or live_factor > 20.0:
        return "mixed"

    return "mixed"


def main() -> None:
    args = _build_parser().parse_args()
    repo_root = Path(args.repo_root).resolve()
    local_root = Path(args.local_root).resolve()
    local_root.mkdir(parents=True, exist_ok=True)

    live_model = repo_root / "models/production_efficiency_model.pkl"
    staged_model = (
        repo_root
        / "models/task14c_artifacts/staged_candidate_20260418_070130/production_efficiency_model.candidate.task14c.pkl"
    )
    staged_preprocessor = (
        repo_root
        / "models/task14c_artifacts/staged_candidate_20260418_070130/production_preprocessor.candidate.task14c.pkl"
    )
    local_model_copy = local_root / staged_model.name
    local_preprocessor_copy = local_root / staged_preprocessor.name

    shutil.copy2(staged_model, local_model_copy)
    shutil.copy2(staged_preprocessor, local_preprocessor_copy)

    python_executable = sys.executable

    live_pickle = _run_loader(
        python_executable=python_executable,
        path=live_model,
        loader="pickle",
        timeout_seconds=args.timeout_seconds,
    )
    staged_pickle = _run_loader(
        python_executable=python_executable,
        path=staged_model,
        loader="pickle",
        timeout_seconds=args.timeout_seconds,
    )
    local_pickle = _run_loader(
        python_executable=python_executable,
        path=local_model_copy,
        loader="pickle",
        timeout_seconds=args.timeout_seconds,
    )
    staged_joblib = _run_loader(
        python_executable=python_executable,
        path=staged_model,
        loader="joblib",
        timeout_seconds=args.timeout_seconds,
    )
    local_joblib = _run_loader(
        python_executable=python_executable,
        path=local_model_copy,
        loader="joblib",
        timeout_seconds=args.timeout_seconds,
    )

    live_pickle_seconds = float((live_pickle.get("payload") or {}).get("elapsed_seconds") or live_pickle["wall_seconds"])
    staged_pickle_seconds = float((staged_pickle.get("payload") or {}).get("elapsed_seconds") or staged_pickle["wall_seconds"])
    local_pickle_seconds = float((local_pickle.get("payload") or {}).get("elapsed_seconds") or local_pickle["wall_seconds"])
    staged_joblib_seconds = (
        float((staged_joblib.get("payload") or {}).get("elapsed_seconds"))
        if staged_joblib.get("payload")
        else None
    )
    local_joblib_seconds = (
        float((local_joblib.get("payload") or {}).get("elapsed_seconds"))
        if local_joblib.get("payload")
        else None
    )

    payload = {
        "python_executable": python_executable,
        "repo_root": str(repo_root),
        "local_root": str(local_root),
        "sizes": {
            "live_model_bytes": _size_bytes(live_model),
            "staged_candidate_model_bytes": _size_bytes(staged_model),
            "staged_candidate_preprocessor_bytes": _size_bytes(staged_preprocessor),
            "local_candidate_model_bytes": _size_bytes(local_model_copy),
            "local_candidate_preprocessor_bytes": _size_bytes(local_preprocessor_copy),
        },
        "benchmarks": {
            "live_model_pickle_current_path": live_pickle,
            "staged_candidate_pickle_current_path": staged_pickle,
            "staged_candidate_pickle_local_copy": local_pickle,
            "staged_candidate_joblib_current_path": staged_joblib,
            "staged_candidate_joblib_local_copy": local_joblib,
        },
        "diagnosis": _classify(
            live_pickle_seconds=live_pickle_seconds,
            staged_pickle_seconds=staged_pickle_seconds,
            local_pickle_seconds=local_pickle_seconds,
            staged_joblib_seconds=staged_joblib_seconds,
            local_joblib_seconds=local_joblib_seconds,
        ),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
