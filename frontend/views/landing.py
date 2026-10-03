import streamlit as st


def render():

    # =========================================================
    # HERO
    # =========================================================

    st.html("""
    <div class="resumeiq-hero">

        <div class="resumeiq-badge">
            ✦ AI-POWERED RESUME ANALYZER
        </div>

        <div class="resumeiq-hero-title">
            Make your resume
            <span>stand out.</span>
        </div>

        <div class="resumeiq-hero-description">
            Analyze your resume with AI, understand your ATS compatibility,
            identify missing skills, and get actionable recommendations.
        </div>

    </div>
    """)

    # =========================================================
    # CTA
    # =========================================================

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if st.button(
            "🚀 Analyze My Resume",
            use_container_width=True,
            type="primary"
        ):
            st.session_state.current_view = "scorer"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # =========================================================
    # FEATURES HEADER
    # =========================================================

    st.html("""
    <div style="
        text-align:center;
        margin-bottom:25px;
    ">

        <div class="resumeiq-badge">
            ✦ WHAT RESUMEIQ DOES
        </div>

        <div style="
            color:#FFFFFF;
            font-family:'Playfair Display', Georgia, serif;
            font-size:2rem;
            font-weight:700;
            margin-bottom:8px;
        ">
            Everything you need to improve your resume
        </div>

        <div style="
            color:#7C8A9E;
            max-width:600px;
            margin:0 auto;
            font-size:0.95rem;
        ">
            Analyze ATS compatibility, identify skill gaps,
            and get actionable recommendations.
        </div>

    </div>
    """)

    # =========================================================
    # FEATURE CARDS
    # =========================================================

    col1, col2, col3 = st.columns(3)

    with col1:
        st.html("""
        <div class="resumeiq-feature">

            <div class="resumeiq-feature-icon">
                📊
            </div>

            <div style="
                color:#FFFFFF;
                font-family:'Playfair Display', Georgia, serif;
                font-size:1.1rem;
                font-weight:600;
                margin-bottom:8px;
            ">
                5-Factor ATS Scoring
            </div>

            <div style="
                color:#7C8A9E;
                font-size:0.88rem;
                line-height:1.65;
            ">
                Get a detailed score across formatting, keywords,
                content quality, skill validation, and ATS compatibility.
            </div>

        </div>
        """)

    with col2:
        st.html("""
        <div class="resumeiq-feature">

            <div class="resumeiq-feature-icon">
                🧠
            </div>

            <div style="
                color:#FFFFFF;
                font-family:'Playfair Display', Georgia, serif;
                font-size:1.1rem;
                font-weight:600;
                margin-bottom:8px;
            ">
                AI Skill Validation
            </div>

            <div style="
                color:#7C8A9E;
                font-size:0.88rem;
                line-height:1.65;
            ">
                Check whether the skills on your resume
                are actually supported by your projects and experience.
            </div>

        </div>
        """)

    with col3:
        st.html("""
        <div class="resumeiq-feature">

            <div class="resumeiq-feature-icon">
                🎯
            </div>

            <div style="
                color:#FFFFFF;
                font-family:'Playfair Display', Georgia, serif;
                font-size:1.1rem;
                font-weight:600;
                margin-bottom:8px;
            ">
                Job Description Matching
            </div>

            <div style="
                color:#7C8A9E;
                font-size:0.88rem;
                line-height:1.65;
            ">
                Compare your resume against a job description
                and identify missing skills and keywords.
            </div>

        </div>
        """)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # =========================================================
    # HOW IT WORKS
    # =========================================================

    st.html("""
    <div style="
        text-align:center;
        margin-bottom:25px;
    ">

        <div class="resumeiq-badge">
            ✦ SIMPLE WORKFLOW
        </div>

        <div style="
            color:#FFFFFF;
            font-family:'Playfair Display', Georgia, serif;
            font-size:2rem;
            font-weight:700;
            margin-bottom:8px;
        ">
            How It Works
        </div>

        <div style="
            color:#7C8A9E;
            font-size:0.95rem;
        ">
            Analyze your resume in three simple steps.
        </div>

    </div>
    """)

    col1, col2, col3 = st.columns(3)

    steps = [
        (
            "01",
            "📄",
            "Upload",
            "Upload your resume in PDF or DOCX format."
        ),
        (
            "02",
            "🤖",
            "Analyze",
            "Our AI analyzes your resume."
        ),
        (
            "03",
            "✨",
            "Improve",
            "Get actionable recommendations."
        )
    ]

    for col, (number, icon, title, description) in zip(
        [col1, col2, col3],
        steps
    ):
        with col:

            st.html(f"""
            <div class="resumeiq-feature">

                <div style="
                    color:#FFB700;
                    font-family:'DM Mono',monospace;
                    font-size:0.75rem;
                    font-weight:700;
                    margin-bottom:10px;
                ">
                    STEP {number}
                </div>

                <div class="resumeiq-feature-icon">
                    {icon}
                </div>

                <div style="
                    color:#FFFFFF;
                    font-family:'Playfair Display', Georgia, serif;
                    font-size:1.1rem;
                    font-weight:600;
                    margin-bottom:8px;
                ">
                    {title}
                </div>

                <div style="
                    color:#7C8A9E;
                    font-size:0.88rem;
                    line-height:1.65;
                ">
                    {description}
                </div>

            </div>
            """)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # =========================================================
    # NO LOGIN REQUIRED
    # =========================================================

    st.html("""
    <div class="resumeiq-save-card">

        <div style="
            color:#FFFFFF;
            font-family:'Playfair Display', Georgia, serif;
            font-size:1.2rem;
            font-weight:600;
            margin-bottom:8px;
        ">
            🔓 No account required
        </div>

        <div style="
            color:#7C8A9E;
            font-size:0.88rem;
            line-height:1.6;
        ">
            Analyze your resume and view the results without signing in.
            Sign in only when you choose to save an analysis to your history.
        </div>

    </div>
    """)

    st.html("""
    <div class="resumeiq-footer">
        ResumeIQ · AI-Powered Resume Intelligence
    </div>
    """)