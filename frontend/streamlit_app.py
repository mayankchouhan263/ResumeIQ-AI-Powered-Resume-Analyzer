import sys
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------
# Make repo root available for imports
# ---------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent.parent))

from frontend.services import supabase_client
from frontend.services.supabase_client import sign_out

# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="ResumeIQ | AI Resume Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------
# Session state
# ---------------------------------------------------------
for key, default in [
    ("access_token", None),
    ("refresh_token", None),
    ("user_id", None),
    ("user_email", None),
    ("auth_error", None),
    ("auth_info", None),
    ("current_view", "landing"),
    ("scorer_analysis", None),
    ("scorer_filename", None),
    ("scorer_pdf_bytes", None),
    ("scorer_save_pending", False),
    ("scorer_saved", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ---------------------------------------------------------
# Google OAuth callback
# ---------------------------------------------------------
if (
    not st.session_state.access_token
    and "code" in st.query_params
):
    result = supabase_client.exchange_code_for_session(
        st.query_params["code"]
    )

    st.query_params.clear()

    if "error" in result:
        st.session_state.auth_error = (
            f"Google sign-in failed: {result['error']}"
        )
    else:
        st.session_state.access_token = result["access_token"]
        st.session_state.refresh_token = result["refresh_token"]
        st.session_state.user_id = result["user_id"]
        st.session_state.user_email = result["email"]

        # Go back to the page the user started from; if it was "Save to History",
        # restore the analysis so scorer.py can save it.
        pending = result.get("pending") or {}
        st.session_state.current_view = pending.get("view", "landing")
        if pending.get("analysis"):
            st.session_state.scorer_analysis = pending["analysis"]
            st.session_state.scorer_filename = pending.get("filename") or "resume"
            st.session_state.scorer_saved = False
            st.session_state.scorer_save_pending = True
        st.rerun()


# ---------------------------------------------------------
# Load CSS
# ---------------------------------------------------------
def load_css():
    css_path = Path(__file__).parent / "assets" / "styles.css"

    try:
        return (
            "<style>"
            + css_path.read_text(encoding="utf-8")
            + "</style>"
        )
    except FileNotFoundError:
        return ""


st.markdown(
    load_css(),
    unsafe_allow_html=True
)


# =========================================================
# TOP NAVIGATION BAR
# =========================================================

with st.container(key="resumeiq_topbar"):
    is_logged_in = bool(st.session_state.get("access_token"))

    if is_logged_in:
        brand_col, home_col, analyze_col, history_col, resources_col, auth_col = st.columns(
            [3.0, 1.0, 1.15, 1.1, 1.25, 1.0],
            gap="small",
            vertical_alignment="center",
    )
    else:
        brand_col, home_col, analyze_col, history_col, resources_col = st.columns(
            [3.3, 1.1, 1.25, 1.15, 1.35],
            gap="small",
            vertical_alignment="center",
    )
    # brand_col, home_col, analyze_col, history_col, resources_col = st.columns(
    #     [3.3, 1.1, 1.25, 1.15, 1.35],
    #     gap="small",
    #     vertical_alignment="center",
    # )

    # -----------------------------------------------------
    # BRAND
    # -----------------------------------------------------

    with brand_col:
        st.html("""
        <div class="ri-topbar-brand">

            <div class="ri-topbar-name">
                Resume<span>IQ</span>
            </div>

            <div class="ri-topbar-tagline">
                AI Resume Intelligence
            </div>

        </div>
        """)

    # -----------------------------------------------------
    # HOME
    # -----------------------------------------------------

    with home_col:
        if st.button(
            "⌂  Home",
            key="top_home",
            use_container_width=True,
        ):
            st.session_state.current_view = "landing"
            st.rerun()

    # -----------------------------------------------------
    # ANALYZE
    # -----------------------------------------------------

    with analyze_col:
        if st.button(
            "✦  Analyze",
            key="top_analyze",
            use_container_width=True,
        ):
            st.session_state.current_view = "scorer"
            st.rerun()

    # -----------------------------------------------------
    # HISTORY
    # -----------------------------------------------------

    with history_col:
        if st.button(
            "▣  History",
            key="top_history",
            use_container_width=True,
        ):
            st.session_state.current_view = "history"
            st.rerun()

    # -----------------------------------------------------
    # RESOURCES
    # -----------------------------------------------------

    with resources_col:
        if st.button(
            "◇  Resources",
            key="top_resources",
            use_container_width=True,
        ):
            st.session_state.current_view = "resources"
            st.rerun()

    # -----------------------------------------------------
    # LOGOUT
    # -----------------------------------------------------


    if is_logged_in:
        with auth_col:
            if st.button(
                "↪ Logout",
                key="top_logout",
                use_container_width=True,
            ):
                sign_out()

                for key in [
                    "access_token",
                    "refresh_token",
                    "user_id",
                    "email",
                    "scorer_save_pending",
                    "scorer_saved",
                ]:
                    st.session_state.pop(key, None)

                st.session_state.current_view = "landing"
                st.rerun()


            
# =========================================================
# MAIN VIEW
# =========================================================

if st.session_state.current_view == "landing":

    from frontend.views import landing

    landing.render()


elif st.session_state.current_view == "scorer":

    from frontend.views import scorer

    scorer.render()


elif st.session_state.current_view == "history":

    from frontend.views import history

    history.render()


elif st.session_state.current_view == "resources":

    from frontend.views import resources

    resources.render()