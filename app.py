import streamlit as st

# Import custom modules
from core.runtime_capabilities import get_visible_pages
from core.runtime_mode import resolve_runtime_mode
from core.ui_utils import render_runtime_mode_banner
from modules.dormant_legacy_app_helpers import (
    DORMANT_LEGACY_HELPER_NAMES,
    load_data as _load_dormant_legacy_data,
    show_etl_page as _show_dormant_legacy_etl_page,
    show_optimization_page as _show_dormant_legacy_optimization_page,
    show_overview_page as _show_dormant_legacy_overview_page,
    show_team_performance_page as _show_dormant_legacy_team_performance_page,
)
from modules.energy_module import render_energy_module
from modules.etl_module import render_etl_page as render_etl_upload_page
from modules.unified_view_module import render_unified_view_page
from modules.maintenance_module import render_maintenance_page
from modules.experimental_intelligence_lab_module import render_experimental_intelligence_lab
from modules.ml_module import render_ml_module
from modules.optimization_module import render_optimization_module


_DEFENDED_CORE_ROUTE_LABELS = (
    "🔄 ETL Pipeline",
    "📊 Canonical Operations Overview",
    "⚡ Energy Analysis",
    "🎯 Operational Decision Support",
    "🤖 Efficiency Prediction & Governance",
    "🔧 Maintenance",
)
_EXPERIMENTAL_BONUS_ROUTE_LABEL = "🧪 Experimental Intelligence Lab"


def get_defended_core_route_labels():
    return list(_DEFENDED_CORE_ROUTE_LABELS)


def get_experimental_bonus_route_label():
    return _EXPERIMENTAL_BONUS_ROUTE_LABEL


def get_routed_shell_route_labels():
    return [*get_defended_core_route_labels(), get_experimental_bonus_route_label()]


def get_dormant_legacy_helper_names():
    return list(DORMANT_LEGACY_HELPER_NAMES)


def is_defended_core_route(page_label):
    return page_label in _DEFENDED_CORE_ROUTE_LABELS


def is_experimental_bonus_route(page_label):
    return page_label == _EXPERIMENTAL_BONUS_ROUTE_LABEL


def is_routed_shell_route(page_label):
    return is_defended_core_route(page_label) or is_experimental_bonus_route(page_label)


def route_uses_dormant_legacy_loader(page_label):
    return not is_routed_shell_route(page_label)


def get_app_shell_contract(runtime_mode):
    visible_pages = list(get_visible_pages(runtime_mode))
    return {
        "runtime_mode": runtime_mode,
        "defended_core_routes": get_defended_core_route_labels(),
        "experimental_bonus_route": get_experimental_bonus_route_label(),
        "visible_pages": visible_pages,
        "loader_dependent_visible_pages": [
            page_label
            for page_label in visible_pages
            if route_uses_dormant_legacy_loader(page_label)
        ],
        "dormant_legacy_helpers": get_dormant_legacy_helper_names(),
    }

# Page config
st.set_page_config(
    page_title="Smart Manufacturing Analytics",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title and description
st.title("🏭 Smart Manufacturing Analytics Platform")
st.markdown(
    "One canonical machine-hour backbone with focused analytical lenses for ETL audit, "
    "operations overview, energy, decision support, prediction governance, and maintenance evidence."
)
runtime_mode = resolve_runtime_mode(
    session_state=st.session_state,
    query_params=getattr(st, "query_params", None),
)
visible_pages = get_visible_pages(runtime_mode)
render_runtime_mode_banner(runtime_mode)
st.sidebar.caption(f"Runtime mode: {runtime_mode}")

# Sidebar for navigation
page = st.sidebar.selectbox(
    "Choose Analysis Module",
    visible_pages,
)

def load_data():
    """Compatibility wrapper for dormant June ETL/EUVG helpers only."""

    return _load_dormant_legacy_data()

# Initialize variables
etl, euvg, unified_view = None, None, None

# Current sidebar-routed pages stay on canonical readers/modules directly.
# The dormant legacy loader path below is retained only for non-routed helper paths.
if route_uses_dormant_legacy_loader(page):
    # Load data for other pages that still need it
    with st.spinner("Loading and processing data..."):
        etl, euvg, unified_view = load_data()
    
    # Check if data loaded successfully
    if etl is None or euvg is None or unified_view is None:
        st.error("Failed to load data. Please check your data files.")
        st.stop()

# Dormant legacy helper pages below are preserved for historical reference only.
# The current defended-core and experimental sidebar routes do not dispatch into them.
def show_overview_page(etl, euvg, unified_view):
    """Compatibility wrapper for the dormant overview helper."""

    return _show_dormant_legacy_overview_page(etl, euvg, unified_view)

def show_etl_page(etl):
    """Compatibility wrapper for the dormant ETL status helper."""

    return _show_dormant_legacy_etl_page(etl)

def show_unified_view_page():
    """Display the unified hourly view data"""
    render_unified_view_page()

def show_energy_analysis_page():
    """Display canonical energy analysis dashboard."""
    render_energy_module(runtime_mode=runtime_mode)

def show_team_performance_page(euvg, unified_view):
    """Compatibility wrapper for the dormant team-performance helper."""

    return _show_dormant_legacy_team_performance_page(euvg, unified_view)

def show_ml_module(runtime_mode=None):
    """Display the Machine Learning module"""
    render_ml_module(runtime_mode=runtime_mode)

def show_optimization_page(euvg, unified_view):
    """Compatibility wrapper for the dormant optimization helper."""

    return _show_dormant_legacy_optimization_page(euvg, unified_view)

# Page routing
if page == "🔄 ETL Pipeline":
    render_etl_upload_page(runtime_mode=runtime_mode)
elif page == "📊 Canonical Operations Overview":
    show_unified_view_page()
elif page == "⚡ Energy Analysis":
    show_energy_analysis_page()
elif page == "🎯 Operational Decision Support":
    try:
        render_optimization_module()
    except Exception as exc:
        st.error(f"Optimization module unavailable: {exc}")
        st.info("The Optimization route no longer falls back to legacy or synthetic data.")
elif page == "🤖 Efficiency Prediction & Governance":
    show_ml_module(runtime_mode=runtime_mode)
elif page == "🔧 Maintenance":
    render_maintenance_page(runtime_mode=runtime_mode)
elif page == "🧪 Experimental Intelligence Lab":
    render_experimental_intelligence_lab(runtime_mode=runtime_mode)
