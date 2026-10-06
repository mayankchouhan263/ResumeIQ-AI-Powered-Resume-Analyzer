import requests
import streamlit as st

from frontend.components.auth_card import render_auth_card
from frontend.services import api_client


def _show_backend_error(exc: Exception) -> None:
    if isinstance(exc, requests.ConnectionError):
        st.error("Could not reach the backend. Is it running on port 8000?")
    elif isinstance(exc, requests.HTTPError) and exc.response is not None:
        st.error(f"Backend returned {exc.response.status_code}: {exc.response.text}")
    else:
        st.error(f"Unexpected error: {exc}")


def render() -> None:
    st.markdown(
        """
        <div class="resumeiq-page-heading">
            <div class="resumeiq-badge">✦ YOUR HISTORY</div>
            <h1>Saved <span>analyses.</span></h1>
            <p>Revisit resume analyses you've chosen to save.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    access_token = st.session_state.get("access_token")

    if not access_token:
        render_auth_card("history")
        st.caption("No account is needed to analyze a resume.")

        if st.button("🎯 Go to ATS Scorer", use_container_width=True, type="primary"):
            st.session_state.current_view = "scorer"
            st.rerun()
        return

    try:
        history = api_client.get_history(access_token)
    except requests.RequestException as exc:
        _show_backend_error(exc)
        return

    if not history:
        st.info(
            "No saved analyses yet. Analyze a resume, then click 'Save to History'."
        )
        if st.button("🎯 Analyze a Resume", use_container_width=True, type="primary"):
            st.session_state.current_view = "scorer"
            st.rerun()
        return

    st.markdown(f"**Total saved analyses:** {len(history)}")
    st.markdown("<div class='resumeiq-divider'></div>", unsafe_allow_html=True)

    for idx, entry in enumerate(history):
        filename = entry.get("filename", "resume")
        ats_score = float(entry.get("ats_score", 0))
        created_at = entry.get("created_at", "")
        analysis = entry.get("analysis_result", {}) or {}

        component_scores = analysis.get("component_scores", {}) or {}
        jd_comparison = analysis.get("jd_comparison") or analysis.get("jd_match_analysis")

        with st.expander(
            f"📄 {filename} — {ats_score:.0f}/100 — {created_at}",
            expanded=False,
        ):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Overall", f"{ats_score:.0f}/100")
                st.metric("Formatting", f"{component_scores.get('formatting', 0):.0f}/20")
            with c2:
                st.metric("Keywords", f"{component_scores.get('keywords', 0):.0f}/25")
                st.metric("Content", f"{component_scores.get('content', 0):.0f}/25")
            with c3:
                st.metric(
                    "Skill Validation",
                    f"{component_scores.get('skill_validation', 0):.0f}/15",
                )
                st.metric(
                    "ATS Compatibility",
                    f"{component_scores.get('ats_compatibility', 0):.0f}/15",
                )

            if jd_comparison:
                st.markdown(
                    f"**JD Match:** {jd_comparison.get('match_percentage', 0):.0f}%"
                )

            entry_id = entry.get("id")
            if entry_id:
                if st.button("🗑️ Delete", key=f"delete_{idx}"):
                    try:
                        api_client.delete_history_entry(str(entry_id), access_token)
                        st.success("Deleted.")
                        st.rerun()
                    except requests.RequestException as exc:
                        _show_backend_error(exc)
