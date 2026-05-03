"""Read-only helpers for comparing current CSI quantity against a shadow contract."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping

CSI_QTY_SHADOW_CONTRACT = "shadow_production_minutes_share_on_fully_eligible_dominant_groups"
CSI_QTY_SHADOW_MATERIAL_DIFF_THRESHOLD = 0.5


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _has_quantity(row: Mapping[str, object]) -> bool:
    return _float_or_none(row.get("good_qty")) is not None or _float_or_none(row.get("scrap_qty")) is not None


def _row_ineligible_reason(row: Mapping[str, object]) -> str | None:
    if not _has_quantity(row):
        return "row_has_no_quantity"
    if _clean_text(row.get("csi_source_row_hash")) is None:
        return "missing_source_hash"
    if int(_float_or_none(row.get("csi_qty_minute_budget_anomaly_flag")) or 0) == 1:
        return "minute_budget_anomaly"
    row_basis_minutes = _float_or_none(row.get("csi_qty_row_basis_minutes"))
    if row_basis_minutes is None or row_basis_minutes <= 0:
        return "missing_positive_quantity_basis_minutes"
    production_minutes = _float_or_none(row.get("production_minutes"))
    if production_minutes is None or production_minutes <= 0:
        return "missing_positive_production_minutes"
    return None


def _group_ineligible_reason(rows: list[dict[str, object]]) -> str | None:
    quantity_rows = [row for row in rows if _has_quantity(row)]
    if not quantity_rows:
        return "group_has_no_quantity_rows"

    precedence = [
        "minute_budget_anomaly",
        "missing_positive_quantity_basis_minutes",
        "missing_positive_production_minutes",
        "missing_source_hash",
    ]
    row_reasons = [_row_ineligible_reason(row) for row in quantity_rows]
    for reason in precedence:
        if reason in row_reasons:
            return reason
    return None


def evaluate_shadow_quantity(rows: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    """Compare current landed quantity against a read-only shadow contract.

    The shadow contract is intentionally narrow:
    - dominant-event identity remains fixed by `csi_source_row_hash`
    - a group is replaceable only when every quantity-bearing row in that source-hash group is eligible
    - for eligible groups, quantity is reallocated by persisted row `production_minutes` share
    - for ineligible groups, shadow quantity falls back to current quantity and the rows are marked retained
    """

    grouped_rows: dict[str, list[dict[str, object]]] = defaultdict(list)
    for raw_row in rows:
        row = dict(raw_row)
        source_row_hash = _clean_text(row.get("csi_source_row_hash")) or "__missing_source_hash__"
        grouped_rows[source_row_hash].append(row)

    evaluated_rows: list[dict[str, object]] = []
    for source_row_hash, group_rows in grouped_rows.items():
        group_reason = _group_ineligible_reason(group_rows)
        quantity_rows = [row for row in group_rows if _has_quantity(row)]
        current_good_total = sum(_float_or_none(row.get("good_qty")) or 0.0 for row in quantity_rows)
        current_scrap_total = sum(_float_or_none(row.get("scrap_qty")) or 0.0 for row in quantity_rows)
        shadow_basis_total = sum(
            _float_or_none(row.get("production_minutes")) or 0.0
            for row in quantity_rows
        )
        group_eligible = group_reason is None and shadow_basis_total > 0
        if group_reason is None and shadow_basis_total <= 0:
            group_reason = "non_positive_shadow_basis_total"

        for row in group_rows:
            current_good_qty = _float_or_none(row.get("good_qty"))
            current_scrap_qty = _float_or_none(row.get("scrap_qty"))
            production_minutes = _float_or_none(row.get("production_minutes")) or 0.0
            shadow_good_qty = current_good_qty
            shadow_scrap_qty = current_scrap_qty
            if group_eligible and _has_quantity(row):
                share = production_minutes / shadow_basis_total
                shadow_good_qty = current_good_total * share if current_good_qty is not None or current_good_total != 0 else None
                shadow_scrap_qty = current_scrap_total * share if current_scrap_qty is not None or current_scrap_total != 0 else None

            current_total_qty = (current_good_qty or 0.0) + (current_scrap_qty or 0.0)
            shadow_total_qty = (shadow_good_qty or 0.0) + (shadow_scrap_qty or 0.0)
            total_abs_diff = abs(shadow_total_qty - current_total_qty)

            evaluated_rows.append(
                {
                    **row,
                    "shadow_contract": CSI_QTY_SHADOW_CONTRACT,
                    "shadow_group_eligible": int(group_eligible and _has_quantity(row)),
                    "shadow_group_ineligible_reason": None if group_eligible else group_reason,
                    "shadow_basis_minutes": production_minutes if group_eligible and _has_quantity(row) else None,
                    "shadow_basis_total_minutes": shadow_basis_total if group_eligible else None,
                    "shadow_good_qty": shadow_good_qty,
                    "shadow_scrap_qty": shadow_scrap_qty,
                    "shadow_total_abs_qty_diff": total_abs_diff,
                    "shadow_material_change_flag": int(
                        group_eligible and _has_quantity(row) and total_abs_diff > CSI_QTY_SHADOW_MATERIAL_DIFF_THRESHOLD
                    ),
                }
            )
    return evaluated_rows


__all__ = [
    "CSI_QTY_SHADOW_CONTRACT",
    "CSI_QTY_SHADOW_MATERIAL_DIFF_THRESHOLD",
    "evaluate_shadow_quantity",
]
