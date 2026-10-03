from typing import Optional

import requests
import streamlit as st

from frontend.services import api_client, supabase_client
from frontend.components.dashboard import display_results_dashboard


def _read_jd(jd_file, jd_text: str) -> str:
    """
    Turn whatever the user provided into a plain JD string for the backend.

    For .txt files we decode in-process — that's a trivial operation, no need
    for a backend round-trip. For PDF/DOCX, we'd need the backend's parser;
    we don't have a public endpoint for that, so we ask the user to paste text
    instead for non-txt JDs.
    """
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
    """Translate a `requests` exception into a friendly Streamlit error."""
    if isinstance(exc, requests.ConnectionError):
        st.error("Could not reach the backend. Is `uvicorn backend.main:app` running on port 8000?")
    elif isinstance(exc, requests.Timeout):
        st.error("The backend took too long to respond. Try a smaller resume or check the server logs.")
    elif isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            detail = exc.response.json().get("detail", exc.response.text)
        except ValueError:
            detail = exc.response.text
        st.error(f"Backend returned {exc.response.status_code}: {detail}")
    else:
        st.error(f"Unexpected error: {exc}")


def _summary_text(analysis: dict) -> str:
    """Tiny client-side text summary for the Download button."""
    score = analysis.get("ATS_score", analysis.get("ats_score", 0))
    lines = [f"ATS Score: {score:.0f}/100", ""]
    if analysis.get("strengths"):
        lines.append("STRENGTHS:")
        lines.extend(f"  - {s}" for s in analysis["strengths"])
        lines.append("")
    if analysis.get("critical_issues"):
        lines.append("CRITICAL ISSUES:")
        lines.extend(f"  - {s}" for s in analysis["critical_issues"])
        lines.append("")
    if analysis.get("suggestions"):
        lines.append("SUGGESTIONS:")
        lines.extend(f"  - {s}" for s in analysis["suggestions"])
    return "\n".join(lines)


def _render_upload_area(analysis_mode: str):
    """Two-column upload widgets. Returns (resume_file, jd_file, jd_text)."""
    st.markdown("""
    <div class="resumeiq-section-card">

        <div class="resumeiq-section-title">
            📄 Resume Analysis
        </div>

        <div class="resumeiq-section-subtitle">
            Upload your resume and optionally compare it with a job description.
        </div>

    </div>
    """, unsafe_allow_html=True)

    left, right = st.columns(2)

    with left:
        st.markdown("### 📄 Upload Resume")
        resume_file = st.file_uploader(
            "Choose your resume file",
            type=["pdf", "doc", "docx"],
            help="Supported: PDF, DOC, DOCX (max 5 MB)",
            key="resume_upload",
        )
        if resume_file:
            st.success(f"✅ {resume_file.name} ({resume_file.size / 1024:.1f} KB)")

    jd_file: Optional[object] = None
    jd_text = ""

    with right:
        if analysis_mode == "Job Description Comparison":
            st.markdown("### 📋 Job Description")
            jd_method = st.radio(
                "Input method:",
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
                    "Paste job description text:",
                    height=200,
                    placeholder="Paste the JD here...",
                    key="jd_text",
                )
                if jd_text:
                    st.success(f"✅ {len(jd_text)} characters")
        else:
            st.markdown("### 📋 Job Description")
            st.info("Switch to 'Job Description Comparison' mode to enable JD matching.")

    return resume_file, jd_file, jd_text


def _render_export_buttons(analysis: dict) -> None:
    st.markdown("### 📥 Export Results")
    c1, c2 = st.columns(2)

    with c1:
        # Lazy: only call the backend the first time the user clicks expand.
        if st.button("📑 Generate PDF Report", use_container_width=True, type="primary"):
            try:
                with st.spinner("Generating PDF on backend..."):
                    pdf_bytes = api_client.generate_pdf(
                        analysis,
                        access_token=st.session_state.get("access_token"),
                    )
                st.session_state["scorer_pdf_bytes"] = pdf_bytes
            except requests.RequestException as exc:
                _show_backend_error(exc)

        if "scorer_pdf_bytes" in st.session_state:
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


def _store_session(result: dict) -> None:
    st.session_state.access_token  = result["access_token"]
    st.session_state.refresh_token = result["refresh_token"]
    st.session_state.user_id       = result["user_id"]
    st.session_state.user_email    = result["email"]


def _render_inline_auth() -> None:
    """Sign in / sign up form shown only after the user clicks 'Save to History'."""
    st.info("🔐 Sign in or create a free account to save this analysis to your history.")

    if st.session_state.get("save_auth_error"):
        st.error(st.session_state.pop("save_auth_error"))
    if st.session_state.get("save_auth_info"):
        st.info(st.session_state.pop("save_auth_info"))

    tab_in, tab_up = st.tabs(["Sign in", "Sign up"])

    with tab_in:
        with st.form("save_signin_form", clear_on_submit=False):
            email = st.text_input("Email", key="save_signin_email")
            password = st.text_input("Password", type="password", key="save_signin_pw")
            submitted = st.form_submit_button("Sign in & save", use_container_width=True)
        if submitted:
            result = supabase_client.sign_in_with_password(email, password)
            if "error" in result:
                st.session_state["save_auth_error"] = result["error"]
            else:
                _store_session(result)
            st.rerun()

    with tab_up:
        with st.form("save_signup_form", clear_on_submit=False):
            email_up = st.text_input("Email", key="save_signup_email")
            password_up = st.text_input("Password (min 6 chars)", type="password", key="save_signup_pw")
            submitted_up = st.form_submit_button("Create account & save", use_container_width=True)
        if submitted_up:
            result = supabase_client.sign_up_with_password(email_up, password_up)
            if "error" in result:
                st.session_state["save_auth_error"] = result["error"]
            elif result.get("pending_confirmation"):
                st.session_state["save_auth_info"] = (
                    f"Confirmation email sent to {result['email']}. "
                    "Confirm it, then sign in here and your analysis will be saved."
                )
            else:
                _store_session(result)
            st.rerun()

    st.caption(
        "Tip: use email sign-in here. 'Continue with Google' reloads the page, "
        "so you would have to run the analysis again."
    )


def _save_to_history(analysis: dict) -> None:
    """POST the current analysis to the backend. Clears the 'pending' flag either way."""
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
            # Token expired / invalid -> force a fresh sign-in, then retry the save.
            for k in ("access_token", "refresh_token", "user_id", "user_email"):
                st.session_state[k] = None
            st.session_state["scorer_save_pending"] = True
            st.session_state["save_auth_error"] = "Your session expired — please sign in again."
            st.rerun()
        _show_backend_error(exc)
    except requests.RequestException as exc:
        _show_backend_error(exc)


def _render_save_section(analysis: dict) -> None:
    """Optional 'Save to History' step. Login is requested only if the user clicks Save."""
    st.markdown("---")
    st.markdown("### 💾 Save to History")

    if st.session_state.get("scorer_saved"):
        st.success("✅ Saved! Find it under **History** in the sidebar.")
        return

    # Signed in and a save was requested (just logged in, or clicked Save) -> do it now.
    if st.session_state.get("access_token") and st.session_state.get("scorer_save_pending"):
        _save_to_history(analysis)
        if st.session_state.get("scorer_saved"):
            st.success("✅ Saved! Find it under **History** in the sidebar.")
            return

    st.caption("Want to keep this result? Save it to your account to revisit it later. Totally optional.")
    if st.button("💾 Save to History", use_container_width=True, key="save_history_btn"):
        st.session_state["scorer_save_pending"] = True
        if st.session_state.get("access_token"):
            st.rerun()          # re-enter this function; the block above performs the save

    if st.session_state.get("scorer_save_pending") and not st.session_state.get("access_token"):
        _render_inline_auth()


def render() -> None:
    st.markdown("""
        <div class="resumeiq-hero" style="padding-top:30px;padding-bottom:25px;">
            <div class="resumeiq-badge">
                ✦ RESUME ANALYZER
            </div>

            <h1>
                Optimize your
                <span>resume.</span>
            </h1>

            <p>
                Upload your resume and optionally add a job description
                for a detailed AI-powered ATS analysis.
            </p>
        </div>
        """, unsafe_allow_html=True)
            
    with st.sidebar:
        st.markdown("---")
        st.markdown("## 📊 Analysis Options")
        st.info(
            "**General ATS Score**: resume only — overall compatibility.\n\n"
            "**JD Comparison**: resume + job description — targeted match analysis."
        )

    st.markdown("---")

    analysis_mode = st.radio(
        "Select Analysis Mode:",
        ["General ATS Score", "Job Description Comparison"],
        horizontal=True,
    )

    st.markdown("---")

    resume_file, jd_file, jd_text = _render_upload_area(analysis_mode)

    st.markdown("---")

    if not resume_file:
        st.info("👆 Upload your resume to begin.")
        # If we have a prior result in session, render it again.
        if st.session_state.get("scorer_analysis"):
            display_results_dashboard(st.session_state["scorer_analysis"])
        return

    # Login is optional: the token is only sent if the user happens to be signed in.
    access_token = st.session_state.get("access_token")

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        analyze = st.button("🚀 Analyze Resume", use_container_width=True, type="primary")

    if not analyze:
        # Re-show previous result on rerun (e.g. after PDF generation).
        if st.session_state.get("scorer_analysis"):
            display_results_dashboard(st.session_state["scorer_analysis"])
            _render_export_buttons(st.session_state["scorer_analysis"])
            _render_save_section(st.session_state["scorer_analysis"])
        return

    # Fresh analysis — drop any cached PDF/result.
    st.session_state.pop("scorer_pdf_bytes", None)
    st.session_state.pop("scorer_analysis", None)
    st.session_state["scorer_saved"] = False
    st.session_state["scorer_save_pending"] = False

    job_description = _read_jd(jd_file, jd_text) if analysis_mode == "Job Description Comparison" else ""

    try:
        with st.spinner("Analyzing your resume... this can take 10–30 seconds."):
            analysis = api_client.analyze_resume(
                resume_file=resume_file,
                access_token=access_token,
                job_description=job_description,
            )
    except requests.RequestException as exc:
        _show_backend_error(exc)
        return

    st.session_state["scorer_analysis"] = analysis
    st.session_state["scorer_filename"] = resume_file.name
    st.success("✅ Analysis complete!")
    display_results_dashboard(analysis)
    _render_export_buttons(analysis)
    _render_save_section(analysis)