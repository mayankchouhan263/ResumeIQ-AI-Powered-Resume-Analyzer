from textwrap import dedent
from typing import Optional

import requests
import streamlit as st

from frontend.components.auth_card import render_auth_card
from frontend.components.dashboard import display_results_dashboard
from frontend.services import api_client


def _read_jd(jd_file, jd_text: str) -> str:
    """Convert the selected JD input into plain text."""
    if jd_text:
        return jd_text.strip()
    if jd_file is None:
        return ""
    if jd_file.name.lower().endswith(".txt"):
        return jd_file.getvalue().decode("utf-8", errors="ignore")
    st.warning(
        "Job description files must be `.txt` for now — paste the JD text instead "
        "if you have a PDF or DOCX."
    )
    return ""


def _show_backend_error(exc: Exception) -> None:
    """Translate a requests exception into a friendly Streamlit error."""
    if isinstance(exc, requests.ConnectionError):
        st.error(
            "Could not reach the backend. Is `uvicorn backend.main:app --reload` "
            "running on port 8000?"
        )
    elif isinstance(exc, requests.Timeout):
        st.error(
            "The backend took too long to respond. Try a smaller resume or check "
            "the server logs."
        )
    elif isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            detail = exc.response.json().get("detail", exc.response.text)
        except ValueError:
            detail = exc.response.text
        st.error(f"Backend returned {exc.response.status_code}: {detail}")
    else:
        st.error(f"Unexpected error: {exc}")


def _summary_text(analysis: dict) -> str:
    score = analysis.get("ATS_score", analysis.get("ats_score", 0))
    lines = [f"ATS Score: {score:.0f}/100", ""]
    if analysis.get("strengths"):
        lines.append("STRENGTHS:")
        lines.extend(f"  - {item}" for item in analysis["strengths"])
        lines.append("")
    if analysis.get("critical_issues"):
        lines.append("CRITICAL ISSUES:")
        lines.extend(f"  - {item}" for item in analysis["critical_issues"])
        lines.append("")
    if analysis.get("suggestions"):
        lines.append("SUGGESTIONS:")
        lines.extend(f"  - {item}" for item in analysis["suggestions"])
    return "\n".join(lines)


def _render_upload_area(analysis_mode: str):
    """Render the resume and optional JD inputs."""
    st.markdown(
        dedent(
            """
            <div class="resumeiq-section-card">
                <div class="resumeiq-section-title">📄 Resume Analysis</div>
                <div class="resumeiq-section-subtitle">
                    Upload your resume and optionally compare it with a job description.
                </div>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)

    with left:
        st.markdown("#### 📄 Resume")
        st.caption("PDF or DOCX · maximum 5 MB")

        resume_file = st.file_uploader(
            "Drop your resume here",
            type=["pdf", "docx"],
            help="Supported: PDF and DOCX (max 5 MB)",
            key="resume_upload",
            label_visibility="visible",
        )

        if resume_file:
            st.success(
                f"✅ {resume_file.name} ({resume_file.size / 1024:.1f} KB)"
            )

    jd_file: Optional[object] = None
    jd_text = ""

    with right:
        st.markdown("#### 📋 Job Description")

        if analysis_mode == "Job Description Comparison":
            jd_method = st.radio(
                "Input method",
                ["Paste Text", "Upload .txt File"],
                horizontal=True,
                key="jd_input_method",
            )

            if jd_method == "Upload .txt File":
                jd_file = st.file_uploader(
                    "Choose JD file (.txt only)",
                    type=["txt"],
                    key="jd_upload",
                )
                if jd_file:
                    st.success(f"✅ {jd_file.name}")
            else:
                jd_text = st.text_area(
                    "Paste job description text",
                    height=205,
                    placeholder="Paste the job description here...",
                    key="jd_text",
                )
                if jd_text:
                    st.success(f"✅ {len(jd_text)} characters")
        else:
            st.info(
                "General ATS mode analyzes the resume by itself. Switch to "
                "**Job Description Comparison** to compare against a specific role."
            )

    return resume_file, jd_file, jd_text


def _render_export_buttons(analysis: dict) -> None:
    st.markdown("### 📥 Export Results")
    c1, c2 = st.columns(2)

    with c1:
        if st.button(
            "📑 Generate PDF Report",
            use_container_width=True,
            type="primary",
            key="generate_pdf_btn",
        ):
            try:
                with st.spinner("Generating PDF report..."):
                    pdf_bytes = api_client.generate_pdf(
                        analysis,
                        access_token=st.session_state.get("access_token"),
                    )
                st.session_state["scorer_pdf_bytes"] = pdf_bytes
            except requests.RequestException as exc:
                _show_backend_error(exc)

        if st.session_state.get("scorer_pdf_bytes"):
            st.download_button(
                "⬇️ Download PDF",
                data=st.session_state["scorer_pdf_bytes"],
                file_name="ats_resume_report.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_pdf_report",
            )

    with c2:
        st.download_button(
            "📄 Download Summary (.txt)",
            data=_summary_text(analysis),
            file_name="ats_summary.txt",
            mime="text/plain",
            use_container_width=True,
            key="download_summary",
        )


def _save_to_history(analysis: dict) -> None:
    """Save the current analysis for the authenticated user."""
    st.session_state["scorer_save_pending"] = False
    filename = st.session_state.get("scorer_filename", "resume")

    try:
        with st.spinner("Saving to your history..."):
            api_client.save_analysis(
                filename=filename,
                analysis=analysis,
                access_token=st.session_state["access_token"],
            )
        st.session_state["scorer_saved"] = True
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 401:
            for key in ("access_token", "refresh_token", "user_id", "user_email"):
                st.session_state[key] = None
            st.session_state["scorer_save_pending"] = True
            st.session_state["save_auth_error"] = (
                "Your session expired — please sign in again."
            )
            st.rerun()
        _show_backend_error(exc)
    except requests.RequestException as exc:
        _show_backend_error(exc)


def _render_save_section(analysis: dict) -> None:
    """Optional final step: ask for authentication only when Save is clicked."""
    if st.session_state.get("scorer_saved"):
        st.markdown(
            """
            <div class="resumeiq-save-card resumeiq-save-success">
                <div class="resumeiq-save-kicker">✓ SAVED</div>
                <h3>Analysis saved successfully</h3>
                <p>Find it anytime from the <strong>History</strong> section.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        dedent(
            """
            <div class="resumeiq-save-card">
                <div class="resumeiq-save-kicker">OPTIONAL</div>
                <h3>💾 Keep this analysis</h3>
                <p>
                    Download your report now or save this result to your ResumeIQ
                    history. Login is requested only when you choose Save.
                </p>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    if st.button(
        "💾 Save to History",
        use_container_width=True,
        type="primary",
        key="save_history_btn",
    ):
        st.session_state["scorer_save_pending"] = True
        if st.session_state.get("access_token"):
            st.rerun()

    if (
        st.session_state.get("scorer_save_pending")
        and not st.session_state.get("access_token")
    ):
        render_auth_card("save")

    if (
        st.session_state.get("scorer_save_pending")
        and st.session_state.get("access_token")
        and not st.session_state.get("scorer_saved")
    ):
        _save_to_history(analysis)


def render() -> None:
    st.markdown(
        dedent(
            """
            <div class="resumeiq-hero scorer-hero">
                <div class="resumeiq-badge">✦ RESUME ANALYZER</div>
                <h1>
                    Optimize your<br>
                    <span>resume.</span>
                </h1>
                <p>
                    Upload your resume and optionally add a job description
                    for a detailed AI-powered ATS analysis.
                </p>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    analysis_mode = st.radio(
        "Select analysis mode",
        ["General ATS Score", "Job Description Comparison"],
        horizontal=True,
        key="analysis_mode",
    )

    resume_file, jd_file, jd_text = _render_upload_area(analysis_mode)

    if not resume_file:
        st.markdown(
            """
            <div class="resumeiq-placeholder">
                <div class="resumeiq-placeholder-icon">📄</div>
                <h3>Upload your resume to begin</h3>
                <p>
                    Your resume can be analyzed without an account.
                    Authentication is only needed if you choose to save the result.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.session_state.get("scorer_analysis"):
            display_results_dashboard(st.session_state["scorer_analysis"])
            _render_export_buttons(st.session_state["scorer_analysis"])
            _render_save_section(st.session_state["scorer_analysis"])
        return

    st.markdown("<div class='resumeiq-analyze-wrap'></div>", unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        analyze = st.button(
            "🚀 Analyze Resume",
            use_container_width=True,
            type="primary",
            key="analyze_resume_btn",
        )

    if not analyze:
        if st.session_state.get("scorer_analysis"):
            display_results_dashboard(st.session_state["scorer_analysis"])
            _render_export_buttons(st.session_state["scorer_analysis"])
            _render_save_section(st.session_state["scorer_analysis"])
        return

    st.session_state.pop("scorer_pdf_bytes", None)
    st.session_state["scorer_analysis"] = None
    st.session_state["scorer_saved"] = False
    st.session_state["scorer_save_pending"] = False

    job_description = (
        _read_jd(jd_file, jd_text)
        if analysis_mode == "Job Description Comparison"
        else ""
    )

    try:
        with st.spinner("Analyzing your resume... this can take 10–30 seconds."):
            analysis = api_client.analyze_resume(
                resume_file=resume_file,
                access_token=st.session_state.get("access_token"),
                job_description=job_description,
            )
    except requests.RequestException as exc:
        _show_backend_error(exc)
        return

    st.session_state["scorer_analysis"] = analysis
    st.session_state["scorer_filename"] = resume_file.name

    st.markdown(
        "<div class='resumeiq-analysis-complete'>✓ ANALYSIS COMPLETE</div>",
        unsafe_allow_html=True,
    )

    display_results_dashboard(analysis)
    _render_export_buttons(analysis)
    _render_save_section(analysis)
