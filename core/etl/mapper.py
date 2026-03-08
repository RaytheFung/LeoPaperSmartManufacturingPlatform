"""Machine mapping helpers for the smart manufacturing ETL pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd
import numpy as np
import re


@dataclass
class MappingResult:
    three_way_matches: List[Dict]
    mapping_stats: Dict[str, object]
    partial_matches: Dict[str, List[Dict]]
    energy_to_csi: Dict[str, str]
    energy_to_mes: Dict[str, str]
    csi_to_mes: Dict[str, str]
    energy_aggregated: pd.DataFrame


class MachineMapper:
    def __init__(self, energy_df: pd.DataFrame, csi_df: pd.DataFrame, mes_df: pd.DataFrame):
        self.energy_df = energy_df.copy()
        self.csi_df = csi_df.copy()
        self.mes_df = mes_df.copy()
        self.energy_aggregated: Optional[pd.DataFrame] = None
        self.partial_matches: Dict[str, List[Dict]] = {}

    # ------------------------------------------------------------------
    # Pattern helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_machine_code(prefix: str, suffix: str) -> str:
        if prefix.startswith('1') and len(prefix) == 4:
            core_prefix = prefix[1:]
        else:
            core_prefix = prefix
        core_prefix = core_prefix.zfill(3)

        if len(suffix) == 5 and suffix.startswith('00'):
            normalized_suffix = suffix[2:]
        else:
            normalized_suffix = suffix

        return f"{core_prefix}-{normalized_suffix}"

    @classmethod
    def extract_machine_pattern(cls, machine_name: str) -> Tuple[Optional[str], Optional[str]]:
        components = [
            '主機', '馬達', 'UV', 'IR', '水冷', 'Main',
            '六期', '四期', 'UV上光機', '印刷機', '印刷机',
            '數碼印刷機', '印刷上光機', 'IR+UV', 'IR+水冷', '主機+水冷'
        ]

        clean_name = str(machine_name).strip()
        component = None

        for comp in sorted(components, key=len, reverse=True):
            if comp in clean_name:
                component = comp
                clean_name = clean_name.replace(comp, '').strip()

        clean_name = re.sub(r'[（(]', '(', clean_name)
        clean_name = re.sub(r'[）)]', ')', clean_name)
        clean_name = re.sub(r'\([^)]*\)', '', clean_name)
        clean_name = clean_name.strip()

        patterns = [
            (r'^D-(\d{3})-(\d{3})$', lambda m: f"{m.group(1)}-{m.group(2)}"),
            (r'^1(\d{3})-00(\d{3})$', lambda m: f"{m.group(1)}-{m.group(2)}"),
            (r'^(\d{3})-(\d{3})$', lambda m: f"{m.group(1)}-{m.group(2)}"),
            (r'^(\d{4})-(\d{3,5})$', lambda m: cls._normalize_machine_code(m.group(1), m.group(2))),
            (r'^(\d{3,4})\s*-\s*(\d{3,5})$', lambda m: cls._normalize_machine_code(m.group(1), m.group(2))),
            (r'(\d{3,4})\s*-\s*(\d{3,5})', lambda m: cls._normalize_machine_code(m.group(1), m.group(2))),
            (r'^(\d{3,4})[-\s]+(\d{3,5})', lambda m: cls._normalize_machine_code(m.group(1), m.group(2))),
        ]

        for pattern, formatter in patterns:
            match = re.search(pattern, clean_name)
            if match:
                return formatter(match), component

        return None, None

    # ------------------------------------------------------------------
    # Aggregation / mapping
    # ------------------------------------------------------------------
    def aggregate_energy(self) -> pd.DataFrame:
        print("\n=== AGGREGATING ENERGY DATA TO MACHINE LEVEL ===")
        print(f"Original energy rows: {len(self.energy_df)}")

        self.energy_df['pattern'], self.energy_df['component'] = zip(
            *self.energy_df['machine'].apply(self.extract_machine_pattern)
        )

        valid_energy = self.energy_df[self.energy_df['pattern'].notna()].copy()
        valid_energy = valid_energy[valid_energy['electricity_kwh'] > 0]

        machine_aggregates: Dict[str, Dict] = {}
        for pattern, group in valid_energy.groupby('pattern'):
            components = group['component'].dropna().unique()
            machine_aggregates[pattern] = {
                'total_kwh': group['electricity_kwh'].sum(),
                'avg_kwh': group['electricity_kwh'].mean(),
                'min_kwh': group['electricity_kwh'].min(),
                'max_kwh': group['electricity_kwh'].max(),
                'records': len(group),
                'components': list(components),
                'original_names': list(group['machine'].unique()),
                'date_range': {
                    'start': group['datetime'].min(),
                    'end': group['datetime'].max()
                }
            }

        print(f"Unique machines after aggregation: {len(machine_aggregates)}")
        print(f"Reduction: {(1 - len(machine_aggregates)/len(self.energy_df))*100:.1f}%")

        aggregated = pd.DataFrame.from_dict(machine_aggregates, orient='index')
        aggregated['unique_components'] = aggregated['components'].apply(lambda x: len(set(x)))
        aggregated['machine_id'] = aggregated.index
        self.energy_aggregated = aggregated
        return aggregated

    def _identify_pattern(self, machine_id: str) -> str:
        prefix = machine_id.split('-')[0]
        if len(prefix) == 3:
            if prefix == '024':
                return '024 series'
            if prefix == '035':
                return '035 series'
            if prefix == '166':
                return '166 series'
            return f'{prefix} series'
        return 'Direct 4-digit'

    def _analyze_partial_matches(
        self,
        energy_machines: Set[str],
        csi_machines: Set[str],
        mes_machines: Set[str],
        energy_to_csi: Dict[str, str],
        energy_to_mes: Dict[str, str],
        csi_to_mes: Dict[str, str],
        three_way_ids: Set[str],
    ) -> None:
        energy_csi_only = []
        energy_mes_only = []
        csi_mes_only = []

        for energy_machine, csi_machine in energy_to_csi.items():
            if energy_machine not in three_way_ids:
                energy_info = self.energy_aggregated.loc[energy_machine]
                energy_csi_only.append({
                    'energy': energy_machine,
                    'csi': csi_machine,
                    'energy_samples': list(energy_info['original_names'])[:3],
                    'total_kwh': energy_info['total_kwh']
                })

        for energy_machine, mes_machine in energy_to_mes.items():
            if energy_machine not in three_way_ids:
                energy_info = self.energy_aggregated.loc[energy_machine]
                energy_mes_only.append({
                    'energy': energy_machine,
                    'mes': mes_machine,
                    'energy_samples': list(energy_info['original_names'])[:3],
                    'total_kwh': energy_info['total_kwh']
                })

        for csi_machine, mes_machine in csi_to_mes.items():
            is_three_way = any(
                match['csi'] == csi_machine and match['mes'] == mes_machine
                for match in getattr(self, '_three_way_matches', [])
            )
            if not is_three_way:
                csi_mes_only.append({
                    'csi': csi_machine,
                    'mes': mes_machine
                })

        energy_only = list(energy_machines - csi_machines - mes_machines)
        csi_only = list(csi_machines - energy_machines - mes_machines)
        mes_only = list(mes_machines - energy_machines - csi_machines)

        self.partial_matches = {
            'energy_csi_only': energy_csi_only,
            'energy_mes_only': energy_mes_only,
            'csi_mes_only': csi_mes_only,
            'energy_only': energy_only,
            'csi_only': csi_only,
            'mes_only': mes_only
        }

    def create_mapping(self) -> MappingResult:
        aggregated = self.energy_aggregated if self.energy_aggregated is not None else self.aggregate_energy()

        def _normalized_series(series: pd.Series) -> pd.Series:
            patterns = [self.extract_machine_pattern(x)[0] for x in series]
            return pd.Series(patterns, index=series.index)

        self.csi_df['_pattern'] = _normalized_series(self.csi_df['機台編號'])
        if '資源' in self.mes_df.columns:
            self.mes_df['_pattern'] = _normalized_series(self.mes_df['資源'])
        else:
            self.mes_df['_pattern'] = pd.Series([None] * len(self.mes_df))

        energy_machines = set(aggregated.index)
        csi_machines = set(self.csi_df['機台編號'].dropna().unique())
        mes_machines = set(self.mes_df['資源'].dropna().unique()) if '資源' in self.mes_df.columns else set()
        csi_lookup = (
            self.csi_df.dropna(subset=['_pattern'])
            .groupby('_pattern')['機台編號']
            .first()
            .to_dict()
        )
        mes_lookup = (
            self.mes_df.dropna(subset=['_pattern'])
            .groupby('_pattern')['資源']
            .first()
            .to_dict()
        )

        energy_to_csi: Dict[str, str] = {}
        energy_to_mes: Dict[str, str] = {}
        csi_to_mes: Dict[str, str] = {}
        three_way_matches: List[Dict] = []

        for pattern, csi_machine in csi_lookup.items():
            if pattern in mes_lookup:
                csi_to_mes[csi_machine] = mes_lookup[pattern]

        for machine_id in energy_machines:
            pattern = machine_id
            if pattern in csi_lookup:
                energy_to_csi[machine_id] = csi_lookup[pattern]
            if pattern in mes_lookup:
                energy_to_mes[machine_id] = mes_lookup[pattern]

            if machine_id in energy_to_csi and machine_id in energy_to_mes:
                csi_machine = energy_to_csi[machine_id]
                mes_machine = energy_to_mes[machine_id]
                csi_pattern = self.csi_df.loc[self.csi_df['機台編號'] == csi_machine, '_pattern'].iloc[0]
                mes_pattern = self.mes_df.loc[self.mes_df['資源'] == mes_machine, '_pattern'].iloc[0]
                if csi_pattern == mes_pattern == pattern:
                    energy_info = aggregated.loc[machine_id]
                    three_way_matches.append({
                        'machine_id': machine_id,
                        'energy_samples': list(set(energy_info['original_names']))[:3],
                        'csi': csi_machine,
                        'mes': mes_machine,
                        'components': energy_info['unique_components'],
                        'total_kwh': energy_info['total_kwh'],
                        'pattern': self._identify_pattern(machine_id)
                    })

        self._three_way_matches = three_way_matches
        self._analyze_partial_matches(
            energy_machines,
            csi_machines,
            mes_machines,
            energy_to_csi,
            energy_to_mes,
            csi_to_mes,
            {match['machine_id'] for match in three_way_matches}
        )

        mapping_stats = {
            'energy_original_rows': len(self.energy_df),
            'energy_unique_machines': len(energy_machines),
            'csi_machines': len(csi_machines),
            'mes_machines': len(mes_machines),
            'three_way_matches': len(three_way_matches),
            'mes_coverage_percent': f"{len(three_way_matches)/len(mes_machines)*100:.1f}%" if mes_machines else "0%"
        }

        print(f"\n🎉 THREE-WAY MATCHES: {len(three_way_matches)}")
        print(f"📊 Partial matches: {len(self.partial_matches['energy_csi_only']) + len(self.partial_matches['energy_mes_only']) + len(self.partial_matches['csi_mes_only'])}")

        return MappingResult(
            three_way_matches=three_way_matches,
            mapping_stats=mapping_stats,
            partial_matches=self.partial_matches,
            energy_to_csi=energy_to_csi,
            energy_to_mes=energy_to_mes,
            csi_to_mes=csi_to_mes,
            energy_aggregated=aggregated,
        )
