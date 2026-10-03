from typing import Any, Dict

import streamlit as st


COMPONENTS = [
    ("Formatting", "formatting", 20, "📝"),
    ("Keywords & Skills", "keywords", 25, "🔑"),
    ("Content Quality", "content", 25, "📄"),
    ("Skill Validation", "skill_validation", 15, "✅"),
    ("ATS Compatibility", "ats_compatibility", 15, "🤖"),
]


def display_overall_score(analysis: Dict[str, Any]) -> None:
    """Render the main ATS score in the ResumeIQ premium theme."""
    score = float(analysis.get("ATS_score", analysis.get("ats_score", 0)))
    interpretation = analysis.get("interpretation", "")

    st.markdown("## 📊 Analysis Results")
    st.markdown(
        f"""
        <div class="resumeiq-score-card">
            <div class="resumeiq-score-label">OVERALL ATS SCORE</div>
            <div class="resumeiq-score">{score:.0f}</div>
            <div class="resumeiq-score-max">OUT OF 100</div>
            <div class="resumeiq-score-interpretation">{interpretation}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def display_score_breakdown(analysis: Dict[str, Any]) -> None:
    """Render the five scoring factors as premium horizontal bars."""
    component_scores = analysis.get("component_scores") or {}

    st.markdown("### 📈 Score Breakdown")

    left, right = st.columns(2)

    for index, (label, key, max_score, icon) in enumerate(COMPONENTS):
        value = float(component_scores.get(key, 0))
        percentage = min(max(value / max_score if max_score else 0.0, 0.0), 1.0)

        with left if index % 2 == 0 else right:
            st.markdown(
                f"""
                <div class="resumeiq-factor">
                    <div class="resumeiq-factor-head">
                        <div class="resumeiq-factor-name">{icon} {label}</div>
                        <div class="resumeiq-factor-score">{value:.0f}/{max_score}</div>
                    </div>
                    <div class="resumeiq-factor-track">
                        <div
                            class="resumeiq-factor-fill"
                            style="width:{percentage * 100:.1f}%;"
                        ></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
