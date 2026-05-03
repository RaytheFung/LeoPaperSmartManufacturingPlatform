"""UI utilities for the Smart Manufacturing Platform."""

from __future__ import annotations

import html
import os
from contextlib import contextmanager

import streamlit as st

from core.runtime_mode import (
    DEMO_READONLY_RUNTIME_MODE,
    PILOT_REVIEW_RUNTIME_MODE,
    get_runtime_mode_label,
    get_runtime_mode_summary,
    normalize_runtime_mode,
)

def load_custom_css():
    """Load custom CSS styles from the static folder"""
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'styles.css')
    
    if os.path.exists(css_path):
        with open(css_path, 'r') as f:
            css_content = f.read()
            st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
    else:
        # Fallback to minimal essential styles if CSS file not found
        st.markdown("""
            <style>
            [data-testid="metric-container"] {
                background-color: #f8f9fa;
                padding: 15px;
                border-radius: 12px;
                border: 1px solid #e1e4e8;
            }
            </style>
        """, unsafe_allow_html=True)


def build_surface_card(
    label: str,
    primary: str,
    secondary: str = "",
    *,
    accent: str = "#0f766e",
) -> dict[str, str]:
    return {
        "label": str(label),
        "primary": str(primary),
        "secondary": str(secondary),
        "accent": str(accent),
    }


def build_stat_card(
    label: str,
    value,
    *,
    unit: str = "",
    compact: bool = True,
    primary_decimals: int = 2,
    full_decimals: int = 1,
    none_secondary: str = "Full value unavailable.",
    accent: str = "#0f766e",
) -> dict[str, str]:
    if value is None:
        return build_surface_card(label, "N/A", none_secondary, accent=accent)

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return build_surface_card(label, "N/A", none_secondary, accent=accent)

    if compact:
        abs_value = abs(numeric_value)
        if abs_value >= 1_000_000:
            primary_value = f"{numeric_value / 1_000_000:.{primary_decimals}f}M"
        elif abs_value >= 1_000:
            primary_value = f"{numeric_value / 1_000:.{primary_decimals}f}K"
        else:
            primary_value = f"{numeric_value:,.{primary_decimals}f}"
    else:
        primary_value = f"{numeric_value:,.{primary_decimals}f}"

    primary = f"{primary_value} {unit}".strip()
    secondary = f"Full value {numeric_value:,.{full_decimals}f} {unit}".strip()
    return build_surface_card(label, primary, secondary, accent=accent)


def render_surface_card(card: dict[str, str]) -> None:
    st.markdown(
        f"""
        <div style="
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            padding: 1rem 1rem 0.9rem 1rem;
            background: #ffffff;
            min-height: 148px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06);
        ">
            <div style="
                display: inline-block;
                padding: 0.18rem 0.55rem;
                border-radius: 999px;
                background: #f0fdfa;
                color: {html.escape(card.get('accent', '#0f766e'))};
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.02em;
                text-transform: uppercase;
            ">
                {html.escape(card['label'])}
            </div>
            <div style="margin-top: 0.55rem; font-size: 1.75rem; line-height: 1.15; font-weight: 700; color: #0f172a;">
                {html.escape(card['primary'])}
            </div>
            <div style="margin-top: 0.6rem; font-size: 0.82rem; color: #64748b;">
                {html.escape(card['secondary'])}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_runtime_mode_banner(runtime_mode: str) -> None:
    normalized = normalize_runtime_mode(runtime_mode)
    if normalized == DEMO_READONLY_RUNTIME_MODE:
        accent = "#b45309"
        background = "#fffbeb"
        border = "#f59e0b"
    elif normalized == PILOT_REVIEW_RUNTIME_MODE:
        accent = "#1d4ed8"
        background = "#eff6ff"
        border = "#60a5fa"
    else:
        accent = "#0f766e"
        background = "#f0fdfa"
        border = "#14b8a6"
    st.markdown(
        f"""
        <div style="
            margin: 0.35rem 0 1rem 0;
            padding: 0.85rem 1rem;
            border-radius: 14px;
            border: 1px solid {border};
            background: {background};
        ">
            <div style="
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                color: {accent};
                margin-bottom: 0.2rem;
            ">
                Runtime Mode
            </div>
            <div style="font-size: 1rem; font-weight: 700; color: #0f172a;">
                {html.escape(get_runtime_mode_label(normalized))}
            </div>
            <div style="font-size: 0.88rem; color: #475569; margin-top: 0.2rem;">
                {html.escape(get_runtime_mode_summary(normalized))}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


@contextmanager
def section_shell(
    title: str,
    description: str | None = None,
    *,
    eyebrow: str | None = None,
):
    with st.container(border=True):
        if eyebrow:
            st.markdown(
                f"""
                <div style="
                    font-size: 0.75rem;
                    font-weight: 700;
                    letter-spacing: 0.08em;
                    text-transform: uppercase;
                    color: #0f766e;
                    margin-bottom: 0.15rem;
                ">
                    {html.escape(eyebrow)}
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown(
            f"""
            <div style="
                font-size: 1.15rem;
                line-height: 1.25;
                font-weight: 700;
                color: #0f172a;
                margin-bottom: 0.2rem;
            ">
                {html.escape(title)}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if description:
            st.caption(description)
        yield


__all__ = [
    "build_stat_card",
    "build_surface_card",
    "load_custom_css",
    "render_runtime_mode_banner",
    "render_surface_card",
    "section_shell",
]
