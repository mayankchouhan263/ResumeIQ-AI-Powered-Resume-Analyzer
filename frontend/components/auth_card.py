"""Shared sign-in / sign-up card (email + 'Continue with Google').

Used in two places:
  mode="save"     -> ATS Scorer, after the user clicks "Save to History"
  mode="history"  -> History page, when nobody is signed in
"""
import html
from textwrap import dedent

import streamlit as st

from frontend.services import supabase_client

_TEXT = {
    "save": {
        "kicker":  "🔐 SAVE TO HISTORY",
        "title":   "Sign in to keep this analysis",
        "body":    ("Your analysis is already complete. Sign in or create a free account "
                    "and we'll save this result to your personal history."),
        "in_btn":  "Sign in & save",
        "up_btn":  "Create account & save",
        "confirm": "Confirm it, then sign in here and your analysis will be saved.",
    },
    "history": {
        "kicker":  "🔐 YOUR HISTORY",
        "title":   "Sign in to view your history",
        "body":    ("Sign in to see the analyses you've saved. New here? Create a free account — "
                    "analyzing a resume never requires one."),
        "in_btn":  "Sign in",
        "up_btn":  "Create account",
        "confirm": "Confirm it, then sign in here to see your history.",
    },
}


def _store_session(result: dict) -> None:
    st.session_state.access_token = result["access_token"]
    st.session_state.refresh_token = result["refresh_token"]
    st.session_state.user_id = result["user_id"]
    st.session_state.user_email = result["email"]


def _google_button(mode: str) -> None:
    """'Continue with Google'. What to restore after the redirect is parked server-side, because
    Google sends the browser back as a brand-new Streamlit session."""
    if mode == "save":
        analysis = st.session_state.get("scorer_analysis")
        pending = (
            {
                "view": "scorer",
                "analysis": analysis,
                "filename": st.session_state.get("scorer_filename") or "resume",
            }
            if analysis else {"view": "scorer"}
        )
    else:
        pending = {"view": "history"}

    result = supabase_client.google_oauth_url(pending)
    if "error" in result:
        st.caption(f"Google sign-in is unavailable: {result['error']}")
        return

    href = html.escape(result["url"], quote=True)
    st.markdown(
        f"""
        <a href="{href}" target="_blank" style="display:flex;align-items:center;justify-content:center;
           gap:10px;padding:0.6rem 1rem;border:1px solid #d0d5dd;border-radius:10px;background:#fff;
           color:#1f2937;font-weight:600;text-decoration:none;">
            <span style="font-weight:800;color:#4285F4;font-size:1.1rem;">G</span>
            Continue with Google
        </a>
        <div style="text-align:center;color:#94a3b8;font-size:0.85rem;margin:10px 0 4px;">
            or use email
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_auth_card(mode: str = "save") -> None:
    text = _TEXT[mode]
    st.markdown(
        dedent(
            f"""
            <div class="resumeiq-auth-card">
                <div class="resumeiq-save-kicker">{text['kicker']}</div>
                <h3>{text['title']}</h3>
                <p>{text['body']}</p>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    if st.session_state.get("save_auth_error"):
        st.error(st.session_state.pop("save_auth_error"))
    if st.session_state.get("save_auth_info"):
        st.info(st.session_state.pop("save_auth_info"))

    _google_button(mode)

    tab_in, tab_up = st.tabs(["Sign in", "Sign up"])

    with tab_in:
        with st.form(f"{mode}_signin_form", clear_on_submit=False):
            email = st.text_input("Email", key=f"{mode}_signin_email")
            password = st.text_input("Password", type="password", key=f"{mode}_signin_pw")
            submitted = st.form_submit_button(text["in_btn"], use_container_width=True)

        if submitted:
            result = supabase_client.sign_in_with_password(email, password)
            if "error" in result:
                st.session_state["save_auth_error"] = result["error"]
            else:
                _store_session(result)
            st.rerun()

    with tab_up:
        with st.form(f"{mode}_signup_form", clear_on_submit=False):
            email_up = st.text_input("Email", key=f"{mode}_signup_email")
            password_up = st.text_input(
                "Password (min 6 chars)", type="password", key=f"{mode}_signup_pw"
            )
            submitted_up = st.form_submit_button(text["up_btn"], use_container_width=True)

        if submitted_up:
            result = supabase_client.sign_up_with_password(email_up, password_up)
            if "error" in result:
                st.session_state["save_auth_error"] = result["error"]
            elif result.get("pending_confirmation"):
                st.session_state["save_auth_info"] = (
                    f"Confirmation email sent to {result['email']}. {text['confirm']}"
                )
            else:
                _store_session(result)
            st.rerun()
