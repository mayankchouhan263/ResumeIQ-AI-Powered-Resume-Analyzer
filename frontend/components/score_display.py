from typing import Any, Dict, Tuple

import streamlit as st


# =========================================================
# RESUMEIQ SCORE COMPONENTS
# =========================================================

COMPONENTS = [
    ("Formatting", "formatting", 20, "📝"),
    ("Keywords & Skills", "keywords", 25, "🔑"),
    ("Content Quality", "content", 25, "📄"),
    ("Skill Validation", "skill_validation", 15, "✅"),
    ("ATS Compatibility", "ats_compatibility", 15, "🤖"),
]


# =========================================================
# HELPERS
# =========================================================

def _safe_float(
    value: Any,
    default: float = 0.0
) -> float:
    """Safely convert a value to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_ring_colors(score: float) -> Tuple[str, str]:
    """
    Return ring color and glow color based on ATS score.

    80–100 → Green
    60–79  → Teal
    40–59  → CreditWise Gold
    0–39   → Red
    """

    if score >= 80:
        return (
            "#34D399",
            "rgba(52, 211, 153, 0.18)"
        )

    if score >= 60:
        return (
            "#6DADBE",
            "rgba(109, 173, 190, 0.18)"
        )

    if score >= 40:
        return (
            "#E8C96A",
            "rgba(201, 168, 76, 0.20)"
        )

    return (
        "#F87171",
        "rgba(248, 113, 113, 0.18)"
    )


def _get_verdict(score: float) -> str:
    """Return a short ATS interpretation."""

    if score >= 80:
        return "Excellent ATS Compatibility"

    if score >= 60:
        return "Good ATS Compatibility"

    if score >= 40:
        return "Needs Improvement"

    return "Significant Improvement Needed"


# =========================================================
# OVERALL ATS SCORE — CIRCULAR RING
# =========================================================

def display_overall_score(
    analysis: Dict[str, Any]
) -> None:
    """
    Render the overall ATS score using a CSS circular
    progress ring similar to the CreditWise design.
    """

    score = _safe_float(
        analysis.get(
            "ATS_score",
            analysis.get("ats_score", 0)
        )
    )

    # Keep score between 0 and 100
    score = max(
        0.0,
        min(
            score,
            100.0
        )
    )

    interpretation = analysis.get(
        "interpretation",
        ""
    )

    # -----------------------------------------------------
    # Score-based colors
    # -----------------------------------------------------

    if score >= 80:
        ring_color = "#34D399"
        glow_color = "rgba(52, 211, 153, 0.22)"
        verdict = "Excellent ATS Compatibility"

    elif score >= 60:
        ring_color = "#6DADBE"
        glow_color = "rgba(109, 173, 190, 0.22)"
        verdict = "Good ATS Compatibility"

    elif score >= 40:
        # CreditWise gold
        ring_color = "#E8C96A"
        glow_color = "rgba(201, 168, 76, 0.22)"
        verdict = "Needs Improvement"

    else:
        ring_color = "#F87171"
        glow_color = "rgba(248, 113, 113, 0.22)"
        verdict = "Significant Improvement Needed"

    # -----------------------------------------------------
    # Heading
    # -----------------------------------------------------

    st.markdown(
        "## 📊 Analysis Results"
    )

    # -----------------------------------------------------
    # CSS circular progress ring
    # -----------------------------------------------------

    st.html(
        f"""
        <div class="resumeiq-ring-section">

            <div class="resumeiq-ring-title">
                OVERALL ATS SCORE
            </div>


            <div class="resumeiq-ring-wrapper">

                <div
                    class="resumeiq-css-ring"
                    style="
                        --score: {score:.1f};
                        --ring-color: {ring_color};
                        --ring-glow: {glow_color};
                    "
                >

                    <div class="resumeiq-ring-inner">

                        <div class="resumeiq-ring-pct">
                            {score:.0f}<span>%</span>
                        </div>

                        <div class="resumeiq-ring-label">
                            ATS SCORE
                        </div>

                    </div>

                </div>

            </div>


            <div
                class="resumeiq-ring-verdict"
                style="color:{ring_color};"
            >
                {verdict}
            </div>


            <div class="resumeiq-ring-description">
                {interpretation}
            </div>

        </div>
        """
    )

# =========================================================
# SCORE BREAKDOWN
# =========================================================

def display_score_breakdown(
    analysis: Dict[str, Any]
) -> None:
    """
    Render the five ResumeIQ scoring factors.

    80–100 → Green
    60–79  → Teal
    40–59  → CreditWise Gold
    0–39   → Red
    """

    component_scores = (
        analysis.get("component_scores")
        or {}
    )

    st.markdown(
        "### 📈 Score Breakdown"
    )

    left, right = st.columns(
        2,
        gap="medium"
    )

    for index, (
        label,
        key,
        max_score,
        icon
    ) in enumerate(COMPONENTS):

        value = _safe_float(
            component_scores.get(
                key,
                0
            )
        )

        value = max(
            0.0,
            min(
                value,
                float(max_score)
            )
        )

        percentage = (
            (value / max_score) * 100.0
            if max_score
            else 0.0
        )

        percentage = max(
            0.0,
            min(
                percentage,
                100.0
            )
        )

        # -------------------------------------------------
        # Determine bar color
        # -------------------------------------------------

        if percentage >= 80:

            bar_background = (
                "linear-gradient("
                "90deg,"
                "#2FA66A,"
                "#34D399"
                ")"
            )

        elif percentage >= 60:

            bar_background = (
                "linear-gradient("
                "90deg,"
                "#12768A,"
                "#6DADBE"
                ")"
            )

        elif percentage >= 40:

            bar_background = (
                "linear-gradient("
                "90deg,"
                "#C9A84C,"
                "#E8C96A"
                ")"
            )

        else:

            bar_background = (
                "linear-gradient("
                "90deg,"
                "#C95151,"
                "#F87171"
                ")"
            )

        current_column = (
            left
            if index % 2 == 0
            else right
        )

        with current_column:

            st.html(
                f"""
                <div class="resumeiq-factor">

                    <div class="resumeiq-factor-head">

                        <div class="resumeiq-factor-name">
                            {icon} {label}
                        </div>

                        <div class="resumeiq-factor-score">
                            {value:.0f}/{max_score}
                        </div>

                    </div>

                    <div class="resumeiq-factor-track">

                        <div
                            class="resumeiq-factor-fill"
                            style="
                                width:{percentage:.1f}%;
                                background:{bar_background};
                            "
                        ></div>

                    </div>

                </div>
                """
            )