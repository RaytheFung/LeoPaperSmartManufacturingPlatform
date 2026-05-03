from __future__ import annotations

from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_WORKSPACE_ROOT = _REPO_ROOT.parent
_SOURCE_DATA_ROOT_NAME = "source_data"
_RAW_DATASET_ROOT_NAME = "2025_jan_jun_initial"
_EXTENDED_RAW_DATASET_ROOT_NAME = "2025_jul_2026_feb_collected"
_LEGACY_RAW_DATASET_ROOT_NAME = "2025 DataSet(JAN to JUN)"
_LEGACY_EXTENDED_RAW_DATASET_ROOT_NAME = "DataSet Package(New Collected)"


def get_repo_root() -> Path:
    return _REPO_ROOT


def get_workspace_root() -> Path:
    return _WORKSPACE_ROOT


def get_database_path() -> Path:
    return _REPO_ROOT / "manufacturing_data.db"


def get_data_dir() -> Path:
    return _REPO_ROOT / "data"


def get_models_dir() -> Path:
    return _REPO_ROOT / "models"


def get_etl_outputs_dir() -> Path:
    return _REPO_ROOT / "etl_outputs"


def get_raw_dataset_root() -> Path:
    repo_local = _REPO_ROOT / _SOURCE_DATA_ROOT_NAME / _RAW_DATASET_ROOT_NAME
    if repo_local.exists():
        return repo_local
    legacy_repo_local = _REPO_ROOT / _LEGACY_RAW_DATASET_ROOT_NAME
    if legacy_repo_local.exists():
        return legacy_repo_local
    return _WORKSPACE_ROOT / _LEGACY_RAW_DATASET_ROOT_NAME


def get_extended_raw_dataset_root() -> Path:
    repo_local = _REPO_ROOT / _SOURCE_DATA_ROOT_NAME / _EXTENDED_RAW_DATASET_ROOT_NAME
    if repo_local.exists():
        return repo_local
    legacy_repo_local = _REPO_ROOT / _LEGACY_EXTENDED_RAW_DATASET_ROOT_NAME
    if legacy_repo_local.exists():
        return legacy_repo_local
    return _WORKSPACE_ROOT / _LEGACY_EXTENDED_RAW_DATASET_ROOT_NAME


def resolve_dataset_subdir(data_root: Path | str | None, live_name: str, *legacy_names: str) -> Path:
    root = Path(data_root) if data_root is not None else get_raw_dataset_root()
    for folder_name in (live_name, *legacy_names):
        candidate = root / folder_name
        if candidate.exists():
            return candidate
    return root / live_name


def get_energy_dataset_dir(data_root: Path | str | None = None) -> Path:
    return resolve_dataset_subdir(
        data_root,
        "Energy Usage 1hr Interval",
        "Energy Usage 1hr Interval(JAN to JUN)",
    )


def get_csi_dataset_dir(data_root: Path | str | None = None) -> Path:
    return resolve_dataset_subdir(
        data_root,
        "CSI Monthly",
        "CSI Monthly(JAN to JUN)",
    )


def get_mes_dataset_dir(data_root: Path | str | None = None) -> Path:
    return resolve_dataset_subdir(
        data_root,
        "MES Monthly",
        "MES Monthly(JAN to JUN)",
    )
