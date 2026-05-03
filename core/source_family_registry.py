"""Lightweight source-family registration for Bronze and Silver contracts."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceFamilyContract:
    source_family: str
    status: str
    description: str
    reader_dependency: str | None = None
    reader_available: bool | None = None


def _reader_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


_SOURCE_FAMILY_CONTRACTS = {
    "energy_hourly_report_v1": SourceFamilyContract(
        source_family="energy_hourly_report_v1",
        status="supported",
        description="Canonical hourly energy workbook contract.",
    ),
    "energy_daily_report_v1": SourceFamilyContract(
        source_family="energy_daily_report_v1",
        status="supplementary_only",
        description="Daily energy is registered but excluded from Silver hourly normalization.",
    ),
    "energy_tariff_aggregate_v1": SourceFamilyContract(
        source_family="energy_tariff_aggregate_v1",
        status="separate_family",
        description="Tariff aggregate energy remains separate from the hourly backbone.",
    ),
    "csi_monthly_xlsx_v1": SourceFamilyContract(
        source_family="csi_monthly_xlsx_v1",
        status="supported",
        description="CSI monthly xlsx contract used by the June samples.",
    ),
    "csi_monthly_xls_variant_v1": SourceFamilyContract(
        source_family="csi_monthly_xls_variant_v1",
        status="registered_variant",
        description="Legacy CSI xls variant is registered but remains reader-dependent.",
        reader_dependency="xlrd",
        reader_available=_reader_available("xlrd"),
    ),
    "mes_monthly_report_v1": SourceFamilyContract(
        source_family="mes_monthly_report_v1",
        status="supported",
        description="June MES monthly report contract.",
    ),
    "maintenance_transaction_v1": SourceFamilyContract(
        source_family="maintenance_transaction_v1",
        status="supported",
        description="Maintenance transaction export with skiprows=2 header handling.",
    ),
}


def get_registered_source_families() -> dict[str, SourceFamilyContract]:
    return dict(_SOURCE_FAMILY_CONTRACTS)


def get_source_family_contract(source_family: str) -> SourceFamilyContract:
    try:
        return _SOURCE_FAMILY_CONTRACTS[source_family]
    except KeyError as exc:
        raise KeyError(f"Unknown source family: {source_family}") from exc
