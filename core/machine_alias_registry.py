"""Canonical machine alias registry loader and resolver."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, Optional

from core.runtime_paths import get_repo_root


DEFAULT_REGISTRY_PATH = get_repo_root() / "docs" / "technical" / "v1_machine_alias_registry.csv"
DEFAULT_EXCEPTIONS_PATH = get_repo_root() / "docs" / "technical" / "v1_alias_exceptions.csv"
MAPPING_METADATA_FIELDS = (
    "canonical_machine_id",
    "matched_on",
    "matched_value",
    "exception_applied",
    "source_system",
    "scope_status",
    "join_status",
)

_SOURCE_SYSTEM_ALIASES = {
    "csi": "csi",
    "mes": "mes",
    "energy": "energy",
    "maintenance": "maintenance",
    "any": "any",
    "unknown": "any",
    "all": "any",
}


@dataclass(frozen=True)
class MachineAliasException:
    issue_type: str
    canonical_machine_id: str
    preferred_mes_resource: str
    secondary_mes_alias: str
    evidence: str
    action: str


@dataclass(frozen=True)
class MachineAliasRecord:
    canonical_machine_id: str
    machine_family: str
    csi_machine_id: str
    mes_primary_resource: str
    mes_secondary_aliases: tuple[str, ...]
    maintenance_asset_id: str
    maintenance_legacy_id: str
    maintenance_asset_desc: str
    energy_alias_count: int
    energy_alias_examples: tuple[str, ...]
    evidence_sources: str
    confidence: str
    notes: str
    scope_status: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "canonical_machine_id": self.canonical_machine_id,
            "machine_family": self.machine_family,
            "csi_machine_id": self.csi_machine_id,
            "mes_primary_resource": self.mes_primary_resource,
            "mes_secondary_aliases": list(self.mes_secondary_aliases),
            "maintenance_asset_id": self.maintenance_asset_id,
            "maintenance_legacy_id": self.maintenance_legacy_id,
            "maintenance_asset_desc": self.maintenance_asset_desc,
            "energy_alias_count": self.energy_alias_count,
            "energy_alias_examples": list(self.energy_alias_examples),
            "evidence_sources": self.evidence_sources,
            "confidence": self.confidence,
            "notes": self.notes,
            "scope_status": self.scope_status,
            "join_status": self.scope_status,
        }


@dataclass(frozen=True)
class AliasLookupEntry:
    canonical_machine_id: str
    alias_type: str
    alias_value: str


def _clean_value(value: object) -> str:
    return str(value or "").strip()


def _split_aliases(value: str) -> tuple[str, ...]:
    cleaned = _clean_value(value)
    if not cleaned:
        return ()
    parts = re.split(r"\s*[|;,]\s*", cleaned)
    return tuple(part for part in parts if part)


def _normalize_lookup_value(value: str) -> str:
    return re.sub(r"\s+", "", _clean_value(value)).upper()


def _normalize_source_system(source_system: Optional[str]) -> str:
    normalized = _normalize_lookup_value(source_system or "any").lower()
    return _SOURCE_SYSTEM_ALIASES.get(normalized, "any")


def _extract_lookup_candidates(raw_id: object) -> list[str]:
    raw_value = _clean_value(raw_id)
    if not raw_value:
        return []

    candidates: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        cleaned = _clean_value(value)
        if not cleaned:
            return
        lookup_key = _normalize_lookup_value(cleaned)
        if lookup_key in seen:
            return
        seen.add(lookup_key)
        candidates.append(cleaned)

    add(raw_value)
    compact_value = re.sub(r"\s+", "", raw_value)
    add(compact_value)

    for pattern in (
        r"D-\d{3}-\d{3}",
        r"\d{3,4}-\d{3,5}",
        r"\d{3,4}\s*-\s*\d{3,5}",
    ):
        for match in re.finditer(pattern, raw_value, flags=re.IGNORECASE):
            add(match.group(0))
        if compact_value != raw_value:
            for match in re.finditer(pattern, compact_value, flags=re.IGNORECASE):
                add(match.group(0))

    return candidates


class MachineAliasRegistry:
    """Load and resolve canonical machine identity from the v1 registry."""

    def __init__(
        self,
        records: Iterable[MachineAliasRecord],
        exceptions: Iterable[MachineAliasException],
        registry_path: Path,
        exceptions_path: Path,
    ):
        self.registry_path = Path(registry_path)
        self.exceptions_path = Path(exceptions_path)
        self.records_by_canonical: Dict[str, MachineAliasRecord] = {
            record.canonical_machine_id: record for record in records
        }
        self.exceptions = list(exceptions)
        self.exceptions_by_secondary_mes: Dict[str, MachineAliasException] = {}
        self.alias_maps: Dict[str, Dict[str, AliasLookupEntry]] = {
            "any": {},
            "csi": {},
            "mes": {},
            "energy": {},
            "maintenance": {},
        }
        self._build_indices()

    @classmethod
    def load(
        cls,
        registry_path: Path | str = DEFAULT_REGISTRY_PATH,
        exceptions_path: Path | str = DEFAULT_EXCEPTIONS_PATH,
    ) -> "MachineAliasRegistry":
        registry_path = Path(registry_path)
        exceptions_path = Path(exceptions_path)
        records = cls._load_registry_records(registry_path)
        exceptions = cls._load_exceptions(exceptions_path)
        return cls(records, exceptions, registry_path=registry_path, exceptions_path=exceptions_path)

    @staticmethod
    def _load_registry_records(path: Path) -> list[MachineAliasRecord]:
        if not path.exists():
            raise FileNotFoundError(f"Machine alias registry not found: {path}")

        records: list[MachineAliasRecord] = []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                records.append(
                    MachineAliasRecord(
                        canonical_machine_id=_clean_value(row.get("canonical_machine_id")),
                        machine_family=_clean_value(row.get("machine_family")),
                        csi_machine_id=_clean_value(row.get("csi_machine_id")),
                        mes_primary_resource=_clean_value(row.get("mes_primary_resource")),
                        mes_secondary_aliases=_split_aliases(row.get("mes_secondary_aliases", "")),
                        maintenance_asset_id=_clean_value(row.get("maintenance_asset_id")),
                        maintenance_legacy_id=_clean_value(row.get("maintenance_legacy_id")),
                        maintenance_asset_desc=_clean_value(row.get("maintenance_asset_desc")),
                        energy_alias_count=int(_clean_value(row.get("energy_alias_count")) or 0),
                        energy_alias_examples=_split_aliases(row.get("energy_alias_examples", "")),
                        evidence_sources=_clean_value(row.get("evidence_sources")),
                        confidence=_clean_value(row.get("confidence")),
                        notes=_clean_value(row.get("notes")),
                        scope_status=_clean_value(row.get("scope_status")),
                    )
                )
        return records

    @staticmethod
    def _load_exceptions(path: Path) -> list[MachineAliasException]:
        if not path.exists():
            raise FileNotFoundError(f"Machine alias exceptions file not found: {path}")

        exceptions: list[MachineAliasException] = []
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                exceptions.append(
                    MachineAliasException(
                        issue_type=_clean_value(row.get("issue_type")),
                        canonical_machine_id=_clean_value(row.get("canonical_machine_id")),
                        preferred_mes_resource=_clean_value(row.get("preferred_mes_resource")),
                        secondary_mes_alias=_clean_value(row.get("secondary_mes_alias")),
                        evidence=_clean_value(row.get("evidence")),
                        action=_clean_value(row.get("action")),
                    )
                )
        return exceptions

    def _register_alias(self, system: str, alias_value: str, canonical_machine_id: str, alias_type: str) -> None:
        cleaned = _clean_value(alias_value)
        if not cleaned:
            return

        lookup_key = _normalize_lookup_value(cleaned)
        entry = AliasLookupEntry(
            canonical_machine_id=canonical_machine_id,
            alias_type=alias_type,
            alias_value=cleaned,
        )

        existing = self.alias_maps[system].get(lookup_key)
        if existing and existing.canonical_machine_id != canonical_machine_id:
            raise ValueError(
                f"Alias collision for {cleaned!r}: "
                f"{existing.canonical_machine_id} vs {canonical_machine_id}"
            )
        self.alias_maps[system][lookup_key] = entry

    def _register_all_systems(self, alias_value: str, canonical_machine_id: str, alias_type: str) -> None:
        self._register_alias("any", alias_value, canonical_machine_id, alias_type)

    def _build_indices(self) -> None:
        for exception in self.exceptions:
            secondary_alias = _clean_value(exception.secondary_mes_alias)
            if secondary_alias:
                self.exceptions_by_secondary_mes[_normalize_lookup_value(secondary_alias)] = exception

        for record in self.records_by_canonical.values():
            canonical_id = record.canonical_machine_id

            self._register_alias("csi", canonical_id, canonical_id, "canonical_machine_id")
            self._register_alias("mes", canonical_id, canonical_id, "canonical_machine_id")
            self._register_alias("energy", canonical_id, canonical_id, "canonical_machine_id")
            self._register_alias("maintenance", canonical_id, canonical_id, "canonical_machine_id")
            self._register_all_systems(canonical_id, canonical_id, "canonical_machine_id")

            self._register_alias("csi", record.csi_machine_id, canonical_id, "csi_machine_id")
            self._register_all_systems(record.csi_machine_id, canonical_id, "csi_machine_id")

            self._register_alias("mes", record.mes_primary_resource, canonical_id, "mes_primary_resource")
            self._register_all_systems(record.mes_primary_resource, canonical_id, "mes_primary_resource")

            self._register_alias(
                "maintenance",
                record.maintenance_asset_id,
                canonical_id,
                "maintenance_asset_id",
            )
            self._register_all_systems(
                record.maintenance_asset_id,
                canonical_id,
                "maintenance_asset_id",
            )

            self._register_alias(
                "maintenance",
                record.maintenance_legacy_id,
                canonical_id,
                "maintenance_legacy_id",
            )
            self._register_all_systems(
                record.maintenance_legacy_id,
                canonical_id,
                "maintenance_legacy_id",
            )

            for secondary_alias in record.mes_secondary_aliases:
                self._register_alias("mes", secondary_alias, canonical_id, "mes_secondary_alias")
                self._register_all_systems(secondary_alias, canonical_id, "mes_secondary_alias")

            for energy_alias in record.energy_alias_examples:
                self._register_alias("energy", energy_alias, canonical_id, "energy_alias_example")
                self._register_all_systems(energy_alias, canonical_id, "energy_alias_example")
                for candidate in _extract_lookup_candidates(energy_alias):
                    if _normalize_lookup_value(candidate) == _normalize_lookup_value(energy_alias):
                        continue
                    self._register_alias("energy", candidate, canonical_id, "energy_extracted_id")
                    self._register_all_systems(candidate, canonical_id, "energy_extracted_id")

    def normalize_machine_id(self, raw_id: object) -> str | None:
        result = self.resolve_canonical_machine_id(raw_id, source_system="any")
        return result["canonical_machine_id"]

    def resolve_canonical_machine_id(self, raw_id: object, source_system: str = "any") -> Dict[str, object]:
        normalized_source_system = _normalize_source_system(source_system)
        candidates = _extract_lookup_candidates(raw_id)
        search_order = [normalized_source_system]
        if normalized_source_system != "any":
            search_order.append("any")

        for system in search_order:
            alias_map = self.alias_maps[system]
            for candidate in candidates:
                entry = alias_map.get(_normalize_lookup_value(candidate))
                if entry is None:
                    continue

                record = self.records_by_canonical[entry.canonical_machine_id]
                exception = self.exceptions_by_secondary_mes.get(_normalize_lookup_value(candidate))
                preferred_mes_resource = (
                    exception.preferred_mes_resource
                    if exception and exception.preferred_mes_resource
                    else record.mes_primary_resource
                )

                return {
                    "found": True,
                    "raw_id": _clean_value(raw_id),
                    "source_system": normalized_source_system,
                    "canonical_machine_id": record.canonical_machine_id,
                    "matched_on": entry.alias_type,
                    "matched_value": entry.alias_value,
                    "candidate_values": candidates,
                    "machine_family": record.machine_family,
                    "confidence": record.confidence,
                    "scope_status": record.scope_status,
                    "join_status": record.scope_status,
                    "evidence_sources": record.evidence_sources,
                    "notes": record.notes,
                    "exception_applied": exception is not None,
                    "exception_issue_type": exception.issue_type if exception else None,
                    "preferred_mes_resource": preferred_mes_resource,
                    "secondary_mes_aliases": list(record.mes_secondary_aliases),
                    "maintenance_asset_id": record.maintenance_asset_id,
                    "maintenance_legacy_id": record.maintenance_legacy_id,
                    "energy_alias_examples": list(record.energy_alias_examples),
                    "record": record.to_dict(),
                }

        return {
            "found": False,
            "raw_id": _clean_value(raw_id),
            "source_system": normalized_source_system,
            "canonical_machine_id": None,
            "matched_on": None,
            "matched_value": None,
            "candidate_values": candidates,
            "reason": "not_found",
        }


def load_machine_alias_registry(
    registry_path: Path | str = DEFAULT_REGISTRY_PATH,
    exceptions_path: Path | str = DEFAULT_EXCEPTIONS_PATH,
) -> MachineAliasRegistry:
    return MachineAliasRegistry.load(registry_path=registry_path, exceptions_path=exceptions_path)


_DEFAULT_REGISTRY: MachineAliasRegistry | None = None


def get_default_machine_alias_registry() -> MachineAliasRegistry:
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = load_machine_alias_registry()
    return _DEFAULT_REGISTRY


def normalize_machine_id(raw_id: object) -> str | None:
    return get_default_machine_alias_registry().normalize_machine_id(raw_id)


def resolve_canonical_machine_id(raw_id: object, source_system: str = "any") -> Dict[str, object]:
    return get_default_machine_alias_registry().resolve_canonical_machine_id(raw_id, source_system=source_system)


def build_machine_resolution_metadata(
    raw_id: object,
    source_system: str,
    registry: MachineAliasRegistry | None = None,
) -> Dict[str, object]:
    resolver = registry or get_default_machine_alias_registry()
    result = resolver.resolve_canonical_machine_id(raw_id, source_system=source_system)
    return {
        "canonical_machine_id": result.get("canonical_machine_id"),
        "matched_on": result.get("matched_on"),
        "matched_value": result.get("matched_value"),
        "exception_applied": bool(result.get("exception_applied", False)),
        "source_system": result.get("source_system"),
        "scope_status": result.get("scope_status"),
        "join_status": result.get("join_status"),
    }
