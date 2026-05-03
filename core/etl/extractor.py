"""Data extraction helpers for the smart manufacturing ETL pipeline."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Iterable, List, Tuple

import pandas as pd

from core.machine_alias_registry import build_machine_resolution_metadata, load_machine_alias_registry
from core.runtime_paths import get_etl_outputs_dir


@dataclass
class ExtractedData:
    energy: pd.DataFrame
    csi: pd.DataFrame
    mes: pd.DataFrame


class DataExtractor:
    """Load raw Energy/CSI/MES sources into pandas DataFrames."""

    _XLS_HELPER_PYTHON: str | None | bool = None
    _CSI_REQUIRED_COLUMNS = {
        "班次內日期",
        "班次",
        "區域",
        "機台編號",
        "作业",
        "作业后缀",
        "操作",
        "物料",
        "任務",
        "工程開始時間",
        "準備開始時間",
        "準備結束時間",
        "工程結束時間",
        "正品數量",
        "廢品數量",
        "纍計數量",
        "心電圖整體運作時間",
        "實際生產時間",
        "實際速度_本_時",
        "心電圖實際轉版時間",
        "實際計劃停機時間",
        "實際無計劃停機時間",
        "停機原因",
        "運作中途總停機次數",
        "效率",
        "機長姓名1",
        "機長姓名2",
        "機組人員姓名1",
        "機組人員姓名2",
        "機組人員姓名3",
        "機組人員姓名4",
        "心電圖轉版次數",
    }
    _MES_REQUIRED_COLUMNS = {
        "工序",
        "作業",
        "後綴",
        "操作",
        "任務",
        "物料",
        "報工時間",
        "要求生產數量",
        "生產數量",
        "累計生產數量",
        "報工類型",
        "設備總用時",
        "準備時間",
        "設備生產時間",
        "人數",
        "班次",
        "資源",
        "上傳CSI狀態",
        "狀態變更時間",
        "記錄新增時間",
    }

    def __init__(self, energy_skiprows: int = 6):
        self.energy_skiprows = energy_skiprows
        self._machine_alias_registry = load_machine_alias_registry()

    def _apply_machine_resolution(self, df: pd.DataFrame, raw_value_column: str, source_system: str) -> pd.DataFrame:
        metadata_rows = [
            build_machine_resolution_metadata(value, source_system, registry=self._machine_alias_registry)
            for value in df[raw_value_column]
        ]
        metadata_df = pd.DataFrame(metadata_rows, index=df.index)
        return pd.concat([df, metadata_df], axis=1)

    @classmethod
    def _read_excel_with_variant_support(cls, path: str | Path, **kwargs) -> pd.DataFrame:
        file_path = Path(path)
        suffix = file_path.suffix.lower()
        first_kwargs = dict(kwargs)
        if suffix == ".xls" and "engine" not in first_kwargs:
            first_kwargs["engine"] = "xlrd"

        try:
            return pd.read_excel(file_path, **first_kwargs)
        except (ImportError, ModuleNotFoundError, ValueError) as exc:
            if suffix != ".xls" or "xlrd" not in str(exc).lower():
                raise

        converted_path = cls._convert_xls_with_helper(file_path)
        second_kwargs = dict(kwargs)
        second_kwargs.pop("engine", None)
        return pd.read_excel(converted_path, **second_kwargs)

    @classmethod
    def _convert_xls_with_helper(cls, path: Path) -> Path:
        helper_python = cls._resolve_xls_helper_python()
        if not helper_python:
            raise RuntimeError(
                "No compatible helper Python was found for .xls reading. "
                "Install `xlrd` into the active environment or keep the repo `.venv` available."
            )

        try:
            stat = path.stat()
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Excel source file not found: {path}") from exc

        cache_dir = get_etl_outputs_dir() / "xls_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_key = hashlib.sha256(
            f"{path.resolve()}::{stat.st_size}::{stat.st_mtime_ns}".encode("utf-8")
        ).hexdigest()
        converted_path = cache_dir / f"{cache_key}.xlsx"
        if converted_path.exists():
            return converted_path

        conversion_script = (
            "from pathlib import Path\n"
            "import pandas as pd\n"
            "import sys\n"
            "src = Path(sys.argv[1])\n"
            "dst = Path(sys.argv[2])\n"
            "df = pd.read_excel(src, engine='xlrd')\n"
            "df.to_excel(dst, index=False)\n"
        )
        result = subprocess.run(
            [helper_python, "-c", conversion_script, str(path), str(converted_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not converted_path.exists():
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            detail = stderr or stdout or f"exit code {result.returncode}"
            raise RuntimeError(f"Controlled .xls conversion failed for {path.name}: {detail}")
        return converted_path

    @classmethod
    def _resolve_xls_helper_python(cls) -> str | None:
        if cls._XLS_HELPER_PYTHON is False:
            return None
        if isinstance(cls._XLS_HELPER_PYTHON, str):
            return cls._XLS_HELPER_PYTHON

        repo_root = Path(__file__).resolve().parents[2]
        candidates: list[str] = []
        repo_venv_python = repo_root / ".venv" / "bin" / "python"
        if repo_venv_python.exists():
            candidates.append(str(repo_venv_python))
        python3_path = shutil.which("python3")
        if python3_path:
            candidates.append(python3_path)

        probe_script = (
            "import importlib.util, sys\n"
            "mods = ('pandas', 'xlrd', 'openpyxl')\n"
            "sys.exit(0 if all(importlib.util.find_spec(name) for name in mods) else 1)\n"
        )
        current_executable = str(Path(sys.executable).resolve())
        for candidate in candidates:
            if str(Path(candidate).resolve()) == current_executable:
                continue
            result = subprocess.run(
                [candidate, "-c", probe_script],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                cls._XLS_HELPER_PYTHON = candidate
                return candidate

        cls._XLS_HELPER_PYTHON = False
        return None

    def load_energy(self, energy_files: Iterable[str]) -> pd.DataFrame:
        if isinstance(energy_files, (str, bytes)):
            energy_list = [energy_files]
        else:
            energy_list = list(energy_files)

        frames: List[pd.DataFrame] = []
        for idx, path in enumerate(energy_list, 1):
            print(f"   Loading energy file {idx}/{len(energy_list)}: {path}")
            df = self._read_excel_with_variant_support(
                path,
                skiprows=self.energy_skiprows,
                names=["machine", "datetime", "electricity_kwh", "electricity_cost"],
            )
            df["machine"] = df["machine"].astype(str)
            df["source_file"] = str(Path(path))
            df = df[~df["machine"].str.contains("合計|nan", na=False, case=False)]
            df = df[df["machine"] != "nan"]
            frames.append(df)
            print(f"     - Loaded {len(df)} records")

        if not frames:
            raise ValueError("No energy files were provided")

        combined = pd.concat(frames, ignore_index=True)
        combined["datetime"] = pd.to_datetime(combined["datetime"])
        combined = combined.sort_values("datetime")
        combined = self._apply_machine_resolution(combined, "machine", "energy")
        print(f"   Total energy records: {len(combined)}")
        return combined

    def load_csi(self, csi_file: str) -> pd.DataFrame:
        print("\n2. Loading CSI Data...")
        df = self._read_excel_with_variant_support(
            csi_file,
            usecols=lambda name: name in self._CSI_REQUIRED_COLUMNS,
        )
        df["source_file"] = str(Path(csi_file))
        if "機台編號" in df.columns:
            df = self._apply_machine_resolution(df, "機台編號", "csi")
        print(f"   Loaded {len(df)} CSI records")
        return df

    def load_mes(self, mes_file: str) -> pd.DataFrame:
        print("\n3. Loading MES Data...")
        df = self._read_excel_with_variant_support(
            mes_file,
            usecols=lambda name: name in self._MES_REQUIRED_COLUMNS,
        )
        df["source_file"] = str(Path(mes_file))
        if "資源" in df.columns:
            df = self._apply_machine_resolution(df, "資源", "mes")
        print(f"   Loaded {len(df)} MES records")
        return df

    def extract_all(self, energy_files: Iterable[str], csi_file: str, mes_file: str) -> ExtractedData:
        print("=== EXTRACTING DATA FROM SOURCES ===")
        print("\n1. Loading Energy Data...")
        energy = self.load_energy(energy_files)
        csi = self.load_csi(csi_file)
        mes = self.load_mes(mes_file)
        return ExtractedData(energy=energy, csi=csi, mes=mes)
