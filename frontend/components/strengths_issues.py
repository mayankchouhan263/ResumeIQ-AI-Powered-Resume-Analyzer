from typing import Any, Dict, List
import streamlit as st

from frontend.components._helpers import normalize_severity


def display_strengths(strengths: List[str]) -> None:
    st.markdown("### 💪 Strengths")
    if not strengths:
        st.info("Keep improving your resume to unlock strengths!")
        return
    for item in strengths:
        st.markdown(f"- {item}")


def _high_severity_titles(analysis: Dict[str, Any]) -> List[str]:
    return [
        fb["issue_title"]
        for fb in (analysis.get("detailed_feedback") or [])
        if isinstance(fb, dict)
        and normalize_severity(fb.get("severity_level")) in ("critical", "high")
        and fb.get("issue_title")
    ]


def display_critical_issues(analysis: Dict[str, Any]) -> None:
    # Older saved analyses have no critical_issues, so fall back to the High-severity items.
    critical = analysis.get("critical_issues") or _high_severity_titles(analysis)
    summary = analysis.get("issues_summary") or []

    if not critical and not summary:
        st.success("### ✅ No Critical Issues Found!")
        st.markdown("Your resume doesn't have any urgent issues. Nice work.")
        return

    extra = [s for s in summary if s not in critical]

    if critical:
        st.markdown("### 🚨 Critical Issues")
        st.error("These issues should be addressed first for better ATS performance.")
        for item in critical:
            st.markdown(f"- {item}")
    else:
        st.markdown("### ⚠️ Issues to Review")
        st.info("No critical blockers, but these items can still improve your score.")

    if extra:
        with st.expander("📋 Additional flagged items", expanded=not critical):
            for item in extra:
                st.markdown(f"- {item}")
