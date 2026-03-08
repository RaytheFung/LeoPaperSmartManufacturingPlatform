#!/usr/bin/env python3
"""
Orchestrator for the Smart Manufacturing ETL pipeline.

This lightweight wrapper composes the dedicated extractor, mapper, and reporter
components located under `core.etl`.  The intent is to keep backwards
compatibility with callers that still instantiate `EnhancedSmartManufacturingETL`
while allowing the heavy lifting to live in smaller, testable modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from core.etl import (
    DataExtractor,
    ExtractedData,
    MachineMapper,
    MappingResult,
    ETLReporter,
    ReportContext,
)


@dataclass
class ETLState:
    energy_data: Optional[pd.DataFrame] = None
    csi_data: Optional[pd.DataFrame] = None
    mes_data: Optional[pd.DataFrame] = None
    energy_aggregated: Optional[pd.DataFrame] = None
    machine_mapping: Optional[dict] = None
    partial_matches: Optional[dict] = None
    integrated_metrics: Optional[pd.DataFrame] = None


class EnhancedSmartManufacturingETL:
    """Backwards-compatible ETL façade built on top of modular components."""

    def __init__(self):
        self.state = ETLState()
        self._extractor = DataExtractor()
        self._mapper: Optional[MachineMapper] = None

    # ------------------------------------------------------------------
    # Data extraction
    # ------------------------------------------------------------------
    def extract_all_sources(self, energy_files, csi_file, mes_file) -> ExtractedData:
        extracted = self._extractor.extract_all(energy_files, csi_file, mes_file)
        self.state.energy_data = extracted.energy
        self.state.csi_data = extracted.csi
        self.state.mes_data = extracted.mes
        self.state.energy_aggregated = None
        self.state.machine_mapping = None
        self.state.partial_matches = None
        self.state.integrated_metrics = None
        self._mapper = None
        return extracted

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------
    def _ensure_mapper(self) -> MachineMapper:
        if self.state.energy_data is None or self.state.csi_data is None or self.state.mes_data is None:
            raise ValueError("Data not loaded. Call extract_all_sources first.")

        mapper = MachineMapper(self.state.energy_data, self.state.csi_data, self.state.mes_data)
        if self.state.energy_aggregated is not None:
            mapper.energy_aggregated = self.state.energy_aggregated.copy()
        self._mapper = mapper
        return mapper

    def aggregate_energy_data(self) -> pd.DataFrame:
        mapper = self._ensure_mapper()
        aggregated = mapper.aggregate_energy()
        self.state.energy_aggregated = aggregated
        return aggregated

    def create_comprehensive_mapping(self):
        mapper = self._ensure_mapper()
        result: MappingResult = mapper.create_mapping()

        self.state.energy_aggregated = result.energy_aggregated
        self.state.machine_mapping = {
            'energy_to_csi': result.energy_to_csi,
            'energy_to_mes': result.energy_to_mes,
            'csi_to_mes': result.csi_to_mes,
            'three_way_matches': result.three_way_matches,
            'mapping_stats': result.mapping_stats,
        }
        self.state.partial_matches = result.partial_matches
        return self.state.machine_mapping

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def _build_reporter(self) -> ETLReporter:
        if not self.state.machine_mapping:
            raise ValueError("Machine mapping not computed. Call create_comprehensive_mapping first.")
        context = ReportContext(
            energy_aggregated=self.state.energy_aggregated,
            csi_df=self.state.csi_data,
            mes_df=self.state.mes_data,
            mapping_result=self.state.machine_mapping,
            partial_matches=self.state.partial_matches or {},
        )
        return ETLReporter(context)

    def calculate_integrated_metrics(self) -> pd.DataFrame:
        reporter = self._build_reporter()
        metrics = reporter.calculate_integrated_metrics()
        self.state.integrated_metrics = metrics
        return metrics

    def generate_enhanced_report(self, filename='enhanced_manufacturing_report.xlsx'):
        reporter = self._build_reporter()
        reporter.generate_report(filename)

    # ------------------------------------------------------------------
    # Convenience accessors maintained for backwards compatibility
    # ------------------------------------------------------------------
    @property
    def energy_data(self):
        return self.state.energy_data

    @property
    def csi_data(self):
        return self.state.csi_data

    @property
    def mes_data(self):
        return self.state.mes_data

    @property
    def energy_aggregated(self):
        return self.state.energy_aggregated

    @property
    def machine_mapping(self):
        return self.state.machine_mapping or {}

    @property
    def partial_matches(self):
        return self.state.partial_matches or {}

    @property
    def integrated_metrics(self):
        return self.state.integrated_metrics

