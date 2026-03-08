"""Data extraction helpers for the smart manufacturing ETL pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

import pandas as pd


@dataclass
class ExtractedData:
    energy: pd.DataFrame
    csi: pd.DataFrame
    mes: pd.DataFrame


class DataExtractor:
    """Load raw Energy/CSI/MES sources into pandas DataFrames."""

    def __init__(self, energy_skiprows: int = 6):
        self.energy_skiprows = energy_skiprows

    def load_energy(self, energy_files: Iterable[str]) -> pd.DataFrame:
        if isinstance(energy_files, (str, bytes)):
            energy_list = [energy_files]
        else:
            energy_list = list(energy_files)

        frames: List[pd.DataFrame] = []
        for idx, path in enumerate(energy_list, 1):
            print(f"   Loading energy file {idx}/{len(energy_list)}: {path}")
            df = pd.read_excel(
                path,
                skiprows=self.energy_skiprows,
                names=["machine", "datetime", "electricity_kwh", "electricity_cost"],
            )
            df["machine"] = df["machine"].astype(str)
            df = df[~df["machine"].str.contains("合計|nan", na=False, case=False)]
            df = df[df["machine"] != "nan"]
            frames.append(df)
            print(f"     - Loaded {len(df)} records")

        if not frames:
            raise ValueError("No energy files were provided")

        combined = pd.concat(frames, ignore_index=True)
        combined["datetime"] = pd.to_datetime(combined["datetime"])
        combined = combined.sort_values("datetime")
        print(f"   Total energy records: {len(combined)}")
        return combined

    def load_csi(self, csi_file: str) -> pd.DataFrame:
        print("\n2. Loading CSI Data...")
        df = pd.read_excel(csi_file)
        print(f"   Loaded {len(df)} CSI records")
        return df

    def load_mes(self, mes_file: str) -> pd.DataFrame:
        print("\n3. Loading MES Data...")
        df = pd.read_excel(mes_file)
        print(f"   Loaded {len(df)} MES records")
        return df

    def extract_all(self, energy_files: Iterable[str], csi_file: str, mes_file: str) -> ExtractedData:
        print("=== EXTRACTING DATA FROM SOURCES ===")
        print("\n1. Loading Energy Data...")
        energy = self.load_energy(energy_files)
        csi = self.load_csi(csi_file)
        mes = self.load_mes(mes_file)
        return ExtractedData(energy=energy, csi=csi, mes=mes)
