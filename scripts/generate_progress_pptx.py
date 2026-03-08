#!/usr/bin/env python3
"""
Generate a lightweight 5-minute progress PPTX without external dependencies.

Why this exists:
- Network access is restricted (cannot pip install python-pptx reliably).
- We still want a real .pptx artifact for presentations.

Output:
- docs/presentation/FYP_Progress_Update_2026-03-06.pptx
"""

from __future__ import annotations

import datetime as dt
import os
import sqlite3
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
from xml.sax.saxutils import escape as xml_escape


EMU_PER_INCH = 914400
SLIDE_CX = 12192000  # 13.333" (16:9)
SLIDE_CY = 6858000   # 7.5"  (16:9)


@dataclass(frozen=True)
class Metrics:
    unified_rows: int
    unified_machines: int
    unified_valid_kwhpu: int
    total_kwh: float
    total_qty: float
    avg_kwh_per_unit: float

    etl_matches_min: int
    etl_matches_max: int
    etl_rate_min: float
    etl_rate_max: float

    maintenance_records: int

    latest_model_type: str | None
    latest_r2: float | None
    latest_mae: float | None
    latest_training_date: str | None


def _query_one(conn: sqlite3.Connection, sql: str, params: Sequence[object] = ()) -> tuple:
    cur = conn.cursor()
    cur.execute(sql, params)
    row = cur.fetchone()
    return tuple(row) if row else tuple()


def load_metrics(db_path: Path) -> Metrics:
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        unified_rows, unified_machines = _query_one(
            conn,
            "SELECT COUNT(*), COUNT(DISTINCT machine_id) FROM unified_view;",
        )
        unified_valid_kwhpu, = _query_one(
            conn,
            "SELECT COUNT(*) FROM unified_view WHERE kwh_per_unit IS NOT NULL;",
        )
        total_kwh, total_qty, avg_kwhpu = _query_one(
            conn,
            "SELECT COALESCE(SUM(energy_kwh),0), COALESCE(SUM(production_qty),0), COALESCE(AVG(kwh_per_unit),0) FROM unified_view;",
        )

        etl_matches_min, etl_matches_max, etl_rate_min, etl_rate_max = _query_one(
            conn,
            "SELECT COALESCE(MIN(three_way_matches),0), COALESCE(MAX(three_way_matches),0), "
            "COALESCE(MIN(match_rate),0), COALESCE(MAX(match_rate),0) "
            "FROM etl_runs;",
        )

        maintenance_records, = _query_one(conn, "SELECT COUNT(*) FROM maintenance_records;")

        # Latest model record (if present)
        latest = _query_one(
            conn,
            "SELECT model_type, r2_score, mae, training_date FROM ml_models ORDER BY training_date DESC LIMIT 1;",
        )
        if latest:
            latest_model_type, latest_r2, latest_mae, latest_training_date = latest
        else:
            latest_model_type, latest_r2, latest_mae, latest_training_date = None, None, None, None
    finally:
        conn.close()

    return Metrics(
        unified_rows=int(unified_rows),
        unified_machines=int(unified_machines),
        unified_valid_kwhpu=int(unified_valid_kwhpu),
        total_kwh=float(total_kwh),
        total_qty=float(total_qty),
        avg_kwh_per_unit=float(avg_kwhpu),
        etl_matches_min=int(etl_matches_min),
        etl_matches_max=int(etl_matches_max),
        etl_rate_min=float(etl_rate_min),
        etl_rate_max=float(etl_rate_max),
        maintenance_records=int(maintenance_records),
        latest_model_type=str(latest_model_type) if latest_model_type else None,
        latest_r2=float(latest_r2) if latest_r2 is not None else None,
        latest_mae=float(latest_mae) if latest_mae is not None else None,
        latest_training_date=str(latest_training_date) if latest_training_date else None,
    )


def _xml_decl() -> str:
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'


def _rels_xml(relationships: Iterable[tuple[str, str, str]]) -> str:
    rels = [
        f'  <Relationship Id="{xml_escape(rid)}" Type="{xml_escape(rtype)}" Target="{xml_escape(target)}"/>'
        for rid, rtype, target in relationships
    ]
    return (
        _xml_decl()
        + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        + "\n".join(rels)
        + "\n</Relationships>\n"
    )


def _content_types_xml(slide_count: int) -> str:
    overrides = [
        ('/ppt/presentation.xml', 'application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml'),
        ('/ppt/slideMasters/slideMaster1.xml', 'application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml'),
        ('/ppt/slideLayouts/slideLayout1.xml', 'application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml'),
        ('/ppt/theme/theme1.xml', 'application/vnd.openxmlformats-officedocument.theme+xml'),
        ('/docProps/core.xml', 'application/vnd.openxmlformats-package.core-properties+xml'),
        ('/docProps/app.xml', 'application/vnd.openxmlformats-officedocument.extended-properties+xml'),
    ]
    for i in range(1, slide_count + 1):
        overrides.append(
            (f'/ppt/slides/slide{i}.xml', 'application/vnd.openxmlformats-officedocument.presentationml.slide+xml')
        )

    override_xml = "\n".join(
        f'  <Override PartName="{xml_escape(part)}" ContentType="{xml_escape(ct)}"/>'
        for part, ct in overrides
    )

    return (
        _xml_decl()
        + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        + '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        + '  <Default Extension="xml" ContentType="application/xml"/>\n'
        + override_xml
        + "\n</Types>\n"
    )


def _docprops_core_xml(now: dt.datetime) -> str:
    # Use UTC timestamps in core props (PowerPoint will localize in UI).
    ts = now.replace(microsecond=0, tzinfo=dt.timezone.utc).isoformat().replace("+00:00", "Z")
    return (
        _xml_decl()
        + '<cp:coreProperties '
        + 'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        + 'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        + 'xmlns:dcterms="http://purl.org/dc/terms/" '
        + 'xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        + 'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        + f"<dc:title>{xml_escape('FYP Progress Update')}</dc:title>"
        + f"<dc:creator>{xml_escape('Fung Cheuk Hin')}</dc:creator>"
        + f"<cp:lastModifiedBy>{xml_escape('Codex')}</cp:lastModifiedBy>"
        + f'<dcterms:created xsi:type="dcterms:W3CDTF">{ts}</dcterms:created>'
        + f'<dcterms:modified xsi:type="dcterms:W3CDTF">{ts}</dcterms:modified>'
        + "</cp:coreProperties>\n"
    )


def _docprops_app_xml() -> str:
    return (
        _xml_decl()
        + '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        + 'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        + "<Application>Microsoft Office PowerPoint</Application>"
        + "<DocSecurity>0</DocSecurity>"
        + "<ScaleCrop>false</ScaleCrop>"
        + "<LinksUpToDate>false</LinksUpToDate>"
        + "<SharedDoc>false</SharedDoc>"
        + "<HyperlinksChanged>false</HyperlinksChanged>"
        + "<AppVersion>16.0000</AppVersion>"
        + "</Properties>\n"
    )


def _presentation_xml(slide_count: int) -> str:
    sld_ids = []
    base_id = 256
    for i in range(1, slide_count + 1):
        sld_ids.append(f'    <p:sldId id="{base_id + (i - 1)}" r:id="rId{1 + i}"/>')
    sld_id_lst = "\n".join(sld_ids)
    return (
        _xml_decl()
        + '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        + 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        + 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        + "<p:sldMasterIdLst>"
        + '  <p:sldMasterId id="2147483648" r:id="rId1"/>'
        + "</p:sldMasterIdLst>"
        + "<p:sldIdLst>"
        + sld_id_lst
        + "</p:sldIdLst>"
        + f'<p:sldSz cx="{SLIDE_CX}" cy="{SLIDE_CY}" type="screen16x9"/>'
        + '<p:notesSz cx="6858000" cy="9144000"/>'
        + "<p:defaultTextStyle><a:defPPr/></p:defaultTextStyle>"
        + "</p:presentation>\n"
    )


def _presentation_rels_xml(slide_count: int) -> str:
    rels = [
        (
            "rId1",
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster",
            "slideMasters/slideMaster1.xml",
        )
    ]
    for i in range(1, slide_count + 1):
        rels.append(
            (
                f"rId{1 + i}",
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide",
                f"slides/slide{i}.xml",
            )
        )
    return _rels_xml(rels)


def _theme1_xml() -> str:
    # Minimal theme (enough for Office/Keynote to render).
    return (
        _xml_decl()
        + '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office Theme">'
        + "<a:themeElements>"
        + '<a:clrScheme name="Office">'
        + '<a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>'
        + '<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1>'
        + '<a:dk2><a:srgbClr val="1F2937"/></a:dk2>'
        + '<a:lt2><a:srgbClr val="F3F4F6"/></a:lt2>'
        + '<a:accent1><a:srgbClr val="2563EB"/></a:accent1>'
        + '<a:accent2><a:srgbClr val="16A34A"/></a:accent2>'
        + '<a:accent3><a:srgbClr val="F59E0B"/></a:accent3>'
        + '<a:accent4><a:srgbClr val="DC2626"/></a:accent4>'
        + '<a:accent5><a:srgbClr val="7C3AED"/></a:accent5>'
        + '<a:accent6><a:srgbClr val="0EA5E9"/></a:accent6>'
        + '<a:hlink><a:srgbClr val="0000FF"/></a:hlink>'
        + '<a:folHlink><a:srgbClr val="800080"/></a:folHlink>'
        + "</a:clrScheme>"
        + '<a:fontScheme name="Office">'
        + "<a:majorFont><a:latin typeface=\"Calibri Light\"/><a:ea typeface=\"\"/><a:cs typeface=\"\"/></a:majorFont>"
        + "<a:minorFont><a:latin typeface=\"Calibri\"/><a:ea typeface=\"\"/><a:cs typeface=\"\"/></a:minorFont>"
        + "</a:fontScheme>"
        + '<a:fmtScheme name="Office">'
        + "<a:fillStyleLst>"
        + "<a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill>"
        + "</a:fillStyleLst>"
        + "<a:lnStyleLst>"
        + "<a:ln w=\"9525\" cap=\"flat\" cmpd=\"sng\" algn=\"ctr\">"
        + "<a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill>"
        + "<a:prstDash val=\"solid\"/>"
        + "</a:ln>"
        + "</a:lnStyleLst>"
        + "<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>"
        + "<a:bgFillStyleLst><a:solidFill><a:schemeClr val=\"phClr\"/></a:solidFill></a:bgFillStyleLst>"
        + "</a:fmtScheme>"
        + "</a:themeElements>"
        + "<a:objectDefaults/>"
        + "<a:extraClrSchemeLst/>"
        + "</a:theme>\n"
    )


def _slide_master1_xml() -> str:
    return (
        _xml_decl()
        + '<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        + 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        + 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        + '<p:cSld name="Blank Master"><p:spTree>'
        + '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        + "<p:grpSpPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"0\" cy=\"0\"/>"
        + "<a:chOff x=\"0\" y=\"0\"/><a:chExt cx=\"0\" cy=\"0\"/></a:xfrm></p:grpSpPr>"
        + "</p:spTree></p:cSld>"
        + '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" '
        + 'accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" '
        + 'accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
        + '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
        + "<p:txStyles>"
        + "<p:titleStyle><a:lvl1pPr algn=\"l\"><a:defRPr sz=\"4400\" b=\"1\" kern=\"1200\">"
        + "<a:solidFill><a:schemeClr val=\"tx1\"/></a:solidFill><a:latin typeface=\"Calibri Light\"/>"
        + "</a:defRPr></a:lvl1pPr></p:titleStyle>"
        + "<p:bodyStyle><a:lvl1pPr marL=\"457200\" indent=\"-228600\" algn=\"l\">"
        + "<a:defRPr sz=\"2800\" kern=\"1200\"><a:solidFill><a:schemeClr val=\"tx1\"/></a:solidFill>"
        + "<a:latin typeface=\"Calibri\"/></a:defRPr></a:lvl1pPr></p:bodyStyle>"
        + "<p:otherStyle><a:lvl1pPr marL=\"457200\" indent=\"-228600\" algn=\"l\">"
        + "<a:defRPr sz=\"1800\"><a:solidFill><a:schemeClr val=\"tx1\"/></a:solidFill>"
        + "<a:latin typeface=\"Calibri\"/></a:defRPr></a:lvl1pPr></p:otherStyle>"
        + "</p:txStyles>"
        + "</p:sldMaster>\n"
    )


def _slide_master1_rels_xml() -> str:
    return _rels_xml(
        [
            (
                "rId1",
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout",
                "../slideLayouts/slideLayout1.xml",
            ),
            (
                "rId2",
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme",
                "../theme/theme1.xml",
            ),
        ]
    )


def _slide_layout1_xml() -> str:
    return (
        _xml_decl()
        + '<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        + 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        + 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        + 'type="blank" preserve="1" name="Blank">'
        + '<p:cSld name="Blank"><p:spTree>'
        + '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        + "<p:grpSpPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"0\" cy=\"0\"/>"
        + "<a:chOff x=\"0\" y=\"0\"/><a:chExt cx=\"0\" cy=\"0\"/></a:xfrm></p:grpSpPr>"
        + "</p:spTree></p:cSld>"
        + "<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>"
        + "</p:sldLayout>\n"
    )


def _slide_layout1_rels_xml() -> str:
    return _rels_xml(
        [
            (
                "rId1",
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster",
                "../slideMasters/slideMaster1.xml",
            )
        ]
    )


def _shape_with_text(
    shape_id: int,
    name: str,
    x: int,
    y: int,
    cx: int,
    cy: int,
    paragraphs: Sequence[tuple[str, int, bool]],
) -> str:
    """
    paragraphs: list of (text, font_size_hundredths_pt, bold)
    """
    p_xml = []
    for text, sz, bold in paragraphs:
        text = xml_escape(text)
        b_attr = ' b="1"' if bold else ""
        p_xml.append(
            "<a:p>"
            f"<a:r><a:rPr lang=\"en-US\" sz=\"{sz}\"{b_attr}/><a:t>{text}</a:t></a:r>"
            "<a:endParaRPr lang=\"en-US\"/>"
            "</a:p>"
        )

    return (
        "<p:sp>"
        "<p:nvSpPr>"
        f"<p:cNvPr id=\"{shape_id}\" name=\"{xml_escape(name)}\"/>"
        "<p:cNvSpPr/>"
        "<p:nvPr/>"
        "</p:nvSpPr>"
        "<p:spPr>"
        "<a:xfrm>"
        f"<a:off x=\"{x}\" y=\"{y}\"/>"
        f"<a:ext cx=\"{cx}\" cy=\"{cy}\"/>"
        "</a:xfrm>"
        "<a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom>"
        "</p:spPr>"
        "<p:txBody><a:bodyPr wrap=\"square\"/><a:lstStyle/>"
        + "".join(p_xml)
        + "</p:txBody>"
        "</p:sp>"
    )


def _slide_xml(title: str, body_lines: Sequence[str]) -> str:
    title_shape = _shape_with_text(
        shape_id=2,
        name="Title",
        x=int(0.6 * EMU_PER_INCH),
        y=int(0.35 * EMU_PER_INCH),
        cx=SLIDE_CX - int(1.2 * EMU_PER_INCH),
        cy=int(1.0 * EMU_PER_INCH),
        paragraphs=[(title, 4400, True)],
    )

    body_paragraphs = []
    for line in body_lines:
        if not line.strip():
            body_paragraphs.append(("", 2200, False))
            continue
        is_header = line.endswith(":")
        body_paragraphs.append((line, 2600 if is_header else 2400, is_header))

    body_shape = _shape_with_text(
        shape_id=3,
        name="Body",
        x=int(0.85 * EMU_PER_INCH),
        y=int(1.55 * EMU_PER_INCH),
        cx=SLIDE_CX - int(1.7 * EMU_PER_INCH),
        cy=SLIDE_CY - int(2.0 * EMU_PER_INCH),
        paragraphs=body_paragraphs,
    )

    return (
        _xml_decl()
        + '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        + 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        + 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        + "<p:cSld><p:spTree>"
        + '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        + "<p:grpSpPr><a:xfrm><a:off x=\"0\" y=\"0\"/><a:ext cx=\"0\" cy=\"0\"/>"
        + "<a:chOff x=\"0\" y=\"0\"/><a:chExt cx=\"0\" cy=\"0\"/></a:xfrm></p:grpSpPr>"
        + title_shape
        + body_shape
        + "</p:spTree></p:cSld>"
        + "<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>"
        + "</p:sld>\n"
    )


def _slide_rels_xml() -> str:
    return _rels_xml(
        [
            (
                "rId1",
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout",
                "../slideLayouts/slideLayout1.xml",
            )
        ]
    )


def build_deck(metrics: Metrics, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now()

    date_str = "6 Mar 2026"
    slide_title = "Smart Manufacturing ETL + ML Platform"

    etl_matches = (
        f"{metrics.etl_matches_min}–{metrics.etl_matches_max} machines/month"
        if metrics.etl_matches_min and metrics.etl_matches_max
        else "N/A"
    )
    etl_rate = f"{metrics.etl_rate_min:.1f}% – {metrics.etl_rate_max:.1f}%"

    model_line = "Baseline model: not trained yet"
    if metrics.latest_model_type and metrics.latest_r2 is not None and metrics.latest_mae is not None:
        model_line = (
            f"{metrics.latest_model_type} (R² {metrics.latest_r2:.3f}, MAE {metrics.latest_mae:.4f}) "
            f"@ {metrics.latest_training_date.split('.')[0] if metrics.latest_training_date else 'N/A'}"
        )

    slides: list[tuple[str, list[str]]] = [
        (
            slide_title,
            [
                f"FYP Progress Update (HW105) — {date_str}",
                "Fung Cheuk Hin (UID: 3036068943)",
            ],
        ),
        (
            "1. Problem & Goal",
            [
                "Current Bottlenecks:",
                "• Manual reporting (Excel) causes high latency and data silos (Energy, MES, Maintenance).",
                "• Inconsistent schema & timestamps prevent cross-system analysis.",
                "",
                "Project Goal:",
                "• Architect a unified, hourly 'Single Source of Truth' (SQLite).",
                "• Deliver a Streamlit DSS (Decision Support System) with ML to minimize energy waste.",
            ],
        ),
        (
            "2. System Architecture (Stage 3)",
            [
                "End-to-End Pipeline:",
                "• Monthly Excel Ingestion → Modular ETL Engine → SQLite → Streamlit UI.",
                "",
                "Engineering Highlights:",
                "• Refactored ETL into modular components with a backward-compatible façade.",
                "• Implemented automated verification tests for critical data transformation paths.",
            ],
        ),
        (
            "3. Data Integration Results (Jan–Jun 2025)",
            [
                "ETL Performance:",
                f"• 3-Way System Matches: {etl_matches}",
                f"• MES Coverage Rate: {etl_rate}",
                "",
                "Unified Data Warehouse (manufacturing_data.db):",
                f"• Records: {metrics.unified_rows:,} machine-hour rows across {metrics.unified_machines} machines.",
                f"• Valid ML Samples: {metrics.unified_valid_kwhpu:,} (Non-null kWh/unit).",
                f"• Production Volume: {metrics.total_qty:,.0f} units ({metrics.total_kwh:,.1f} kWh total).",
                f"• Global Avg Efficiency: {metrics.avg_kwh_per_unit:.4f} kWh/unit.",
            ],
        ),
        (
            "4. Analytics & ML Progress",
            [
                "Predictive Modeling (kWh/unit):",
                f"• {model_line}",
                "",
                "Decision Support Features:",
                "• Automated Opportunity Ranking (Identifies low-efficiency periods -> Estimates savings).",
                "• Action logging system initialized for user feedback loop.",
                "",
                "Maintenance Integration:",
                f"• {metrics.maintenance_records:,} maintenance records ingested.",
                "• Next step: Backfill maintenance features to enable downtime-aware ML models.",
            ],
        ),
        (
            "5. Next 4 Weeks Roadmap",
            [
                "Week 1–2 (Data Integrity & Feature Engineering):",
                "• Regenerate unified_view: Correct energy attribution & backfill maintenance data.",
                "• Deploy data guardrails (drift detection, overlap handling).",
                "",
                "Week 3 (Core Deliverable):",
                "• Implement 1-click 'Monthly Insights Report' export (KPIs + Top Saving Opportunities).",
                "",
                "Week 4 (Finalization):",
                "• Model evaluation, final report drafting, and demo preparation.",
                "",
                "Discussion Point:",
                "• Request feedback on evaluation rubric weighting (System Integration vs. ML Novelty).",
            ],
        ),
    ]

    slide_count = len(slides)

    files: dict[str, str] = {}
    files["[Content_Types].xml"] = _content_types_xml(slide_count)
    files["_rels/.rels"] = _rels_xml(
        [
            ("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument", "ppt/presentation.xml"),
            ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties", "docProps/core.xml"),
            ("rId3", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties", "docProps/app.xml"),
        ]
    )
    files["docProps/core.xml"] = _docprops_core_xml(now)
    files["docProps/app.xml"] = _docprops_app_xml()
    files["ppt/presentation.xml"] = _presentation_xml(slide_count)
    files["ppt/_rels/presentation.xml.rels"] = _presentation_rels_xml(slide_count)
    files["ppt/theme/theme1.xml"] = _theme1_xml()
    files["ppt/slideMasters/slideMaster1.xml"] = _slide_master1_xml()
    files["ppt/slideMasters/_rels/slideMaster1.xml.rels"] = _slide_master1_rels_xml()
    files["ppt/slideLayouts/slideLayout1.xml"] = _slide_layout1_xml()
    files["ppt/slideLayouts/_rels/slideLayout1.xml.rels"] = _slide_layout1_rels_xml()

    for i, (title, body) in enumerate(slides, start=1):
        files[f"ppt/slides/slide{i}.xml"] = _slide_xml(title, body)
        files[f"ppt/slides/_rels/slide{i}.xml.rels"] = _slide_rels_xml()

    # Write the zip (pptx)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            zf.writestr(path, content)


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    db_path = repo_root / "manufacturing_data.db"
    output_path = repo_root / "docs" / "presentation" / "FYP_Progress_Update_2026-03-06.pptx"

    metrics = load_metrics(db_path)
    build_deck(metrics, output_path)
    print(f"Generated: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

