#!/usr/bin/env python3
"""
Automated ingestion loop for the smart manufacturing ETL pipeline.

This utility watches the staged data directories (energy, CSI, MES) for new or
updated Excel workbooks. When changes are detected it re-runs the existing ETL
processor (January–June 2025 sample pipeline) and, optionally, triggers the ML
retrain step.

Usage examples:

    # Run a single scan and exit (useful for cron jobs)
    python3 scripts/auto_ingest.py --once

    # Watch continuously, polling every 5 minutes and retraining after ETL
    python3 scripts/auto_ingest.py --interval 300 --retrain
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_ROOT = REPO_ROOT / "2025 DataSet(JAN to JUN)"
DEFAULT_STATE_PATH = REPO_ROOT / "etl_outputs" / "auto_ingest_state.json"

# Ensure local modules can be imported when this script is run directly
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))


def _collect_excel_files(directory: Path) -> Dict[str, float]:
    """Return a mapping of relative path -> last-modified timestamp for Excel files."""
    files: Dict[str, float] = {}
    if not directory.exists():
        return files

    for path in directory.glob("*.xlsx"):
        if path.name.startswith("~$"):
            # Ignore temporary Office lockfiles
            continue
        files[str(path.relative_to(REPO_ROOT))] = path.stat().st_mtime
    return files


def _build_snapshot(directories: Iterable[Path]) -> Dict[str, float]:
    snapshot: Dict[str, float] = {}
    for directory in directories:
        snapshot.update(_collect_excel_files(directory))
    return snapshot


def _diff_snapshots(previous: Dict[str, float], current: Dict[str, float]) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Return dictionaries of new_files, updated_files comparing two snapshots."""
    new_files = {
        path: current[path]
        for path in current
        if path not in previous
    }
    updated_files = {
        path: current[path]
        for path in current
        if path in previous and current[path] > previous[path] + 1e-6
    }
    return new_files, updated_files


@dataclass
class IngestionConfig:
    data_root: Path
    state_path: Path
    poll_interval: int
    retrain: bool
    run_once: bool


class IngestionState:
    """Persisted state of the last processed file snapshot."""

    def __init__(self, path: Path):
        self.path = path
        self.snapshot: Dict[str, float] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                self.snapshot = {str(k): float(v) for k, v in data.items()}
        except (json.JSONDecodeError, OSError, ValueError):
            # Corrupt or unreadable state file; start fresh
            self.snapshot = {}

    def save(self, snapshot: Dict[str, float]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, indent=2)
        self.snapshot = snapshot


class AutoIngestionLoop:
    """Polling-based ingestion watcher."""

    def __init__(self, config: IngestionConfig):
        self.config = config
        data_root = config.data_root
        self.energy_dir = data_root / "Energy Usage 1hr Interval(JAN to JUN)"
        self.csi_dir = data_root / "CSI Monthly(JAN to JUN)"
        self.mes_dir = data_root / "MES Monthly(JAN to JUN)"
        self.state = IngestionState(config.state_path)
        self._shutdown = False

    # ------------------------------------------------------------------
    # Pipeline execution helpers
    # ------------------------------------------------------------------
    def _run_etl(self) -> int:
        """Invoke the existing monthly processing script."""
        script_path = REPO_ROOT / "scripts" / "process_jan_to_june_2025.py"
        command = [sys.executable, str(script_path)]
        print(f"[auto-ingest] Running ETL command: {' '.join(command)}")
        return subprocess.call(command, cwd=str(REPO_ROOT))

    def _run_retrain(self) -> int:
        trainer_path = REPO_ROOT / "core" / "ml_trainer.py"
        command = [sys.executable, str(trainer_path)]
        print(f"[auto-ingest] Running ML retrain command: {' '.join(command)}")
        return subprocess.call(command, cwd=str(REPO_ROOT))

    # ------------------------------------------------------------------
    # Core ingestion loop
    # ------------------------------------------------------------------
    def _scan_for_changes(self) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float]]:
        directories = (self.energy_dir, self.csi_dir, self.mes_dir)
        current_snapshot = _build_snapshot(directories)
        new_files, updated_files = _diff_snapshots(self.state.snapshot, current_snapshot)
        return new_files, updated_files, current_snapshot

    def _handle_changes(self, new_files: Dict[str, float], updated_files: Dict[str, float], snapshot: Dict[str, float]) -> None:
        if not new_files and not updated_files:
            print("[auto-ingest] No changes detected.")
            return

        if new_files:
            print("[auto-ingest] New files detected:")
            for path in sorted(new_files):
                print(f"   + {path}")
        if updated_files:
            print("[auto-ingest] Updated files detected:")
            for path in sorted(updated_files):
                print(f"   * {path}")

        exit_code = self._run_etl()
        if exit_code != 0:
            print(f"[auto-ingest] ETL run failed with exit code {exit_code}; state not updated.")
            return

        if self.config.retrain:
            retrain_exit = self._run_retrain()
            if retrain_exit != 0:
                print(f"[auto-ingest] Retrain failed with exit code {retrain_exit}.")

        self.state.save(snapshot)
        print("[auto-ingest] Snapshot updated.")

    def run_once(self) -> None:
        new_files, updated_files, snapshot = self._scan_for_changes()
        self._handle_changes(new_files, updated_files, snapshot)

    def run_forever(self) -> None:
        print("[auto-ingest] Watching for dataset changes. Press Ctrl+C to exit.")
        while not self._shutdown:
            start_time = time.time()
            try:
                self.run_once()
            except Exception as exc:
                print(f"[auto-ingest] Error during ingestion loop: {exc}")

            elapsed = time.time() - start_time
            sleep_duration = max(0, self.config.poll_interval - elapsed)
            if self.config.run_once:
                break
            time.sleep(sleep_duration)

    def request_shutdown(self, *_args) -> None:
        self._shutdown = True


def _parse_args(argv: Iterable[str] | None = None) -> IngestionConfig:
    parser = argparse.ArgumentParser(description="Automate ETL ingestion when new files arrive.")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help="Root directory containing Energy/CSI/MES folders.",
    )
    parser.add_argument(
        "--state-path",
        type=Path,
        default=DEFAULT_STATE_PATH,
        help="Path to the JSON file used to store processed file timestamps.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Polling interval in seconds when running continuously (default: 300).",
    )
    parser.add_argument(
        "--retrain",
        action="store_true",
        help="Run the ML trainer after a successful ETL ingestion.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Execute a single scan instead of looping indefinitely.",
    )

    args = parser.parse_args(argv)

    return IngestionConfig(
        data_root=args.data_root.expanduser(),
        state_path=args.state_path.expanduser(),
        poll_interval=max(5, args.interval),
        retrain=args.retrain,
        run_once=args.once,
    )


def main(argv: Iterable[str] | None = None) -> int:
    config = _parse_args(argv)

    if not config.data_root.exists():
        print(f"[auto-ingest] Data root does not exist: {config.data_root}")
        return 2

    loop = AutoIngestionLoop(config)

    signal.signal(signal.SIGINT, loop.request_shutdown)
    signal.signal(signal.SIGTERM, loop.request_shutdown)

    mode = "single run" if config.run_once else f"continuous (interval {config.poll_interval}s)"
    print(f"[auto-ingest] Starting ingestion loop in {mode}")
    print(f"[auto-ingest] Monitoring data root: {config.data_root}")
    print(f"[auto-ingest] State file: {config.state_path}")
    if config.retrain:
        print("[auto-ingest] Retrain enabled: ML trainer will run after ETL.")

    if config.run_once:
        loop.run_once()
    else:
        loop.run_forever()

    print("[auto-ingest] Shutdown complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
