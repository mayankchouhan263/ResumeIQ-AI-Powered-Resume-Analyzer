import streamlit as st


def render():

    # =========================================================
    # HERO
    # =========================================================
    st.markdown("""
    <div class="resumeiq-hero">

        <div class="resumeiq-badge">
            ✦ AI-POWERED RESUME ANALYZER
        </div>

        <h1>
            Make your resume
            <span>stand out.</span>
        </h1>

        <p>
            Analyze your resume with AI, understand your ATS compatibility,
            identify missing skills, and get actionable recommendations.
        </p>

    </div>
    """, unsafe_allow_html=True)

    # =========================================================
    # MAIN CTA
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
    # FEATURES
    # =========================================================
    st.markdown("""
    <div style="text-align:center; margin-bottom:25px;">
        <div class="resumeiq-badge">
            ✦ WHAT RESUMEIQ DOES
        </div>

        <h2 style="
            color:#FFFFFF;
            font-family:'Playfair Display', Georgia, serif;
            margin-bottom:8px;
        ">
            Everything you need to improve your resume
        </h2>

        <p style="
            color:#7C8A9E;
            max-width:600px;
            margin:0 auto;
        ">
            Get a deeper understanding of how your resume performs
            against ATS systems and job requirements.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="resumeiq-feature">

            <div class="resumeiq-feature-icon">
                📊
            </div>

            <h3>
                5-Factor ATS Scoring
            </h3>

            <p>
                Get a detailed score across formatting, keywords,
                content quality, skill validation, and ATS compatibility.
            </p>

        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="resumeiq-feature">

            <div class="resumeiq-feature-icon">
                🧠
            </div>

            <h3>
                AI Skill Validation
            </h3>

            <p>
                Check whether the skills listed on your resume
                are actually supported by your projects and experience.
            </p>

        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="resumeiq-feature">

            <div class="resumeiq-feature-icon">
                🎯
            </div>

            <h3>
                Job Description Matching
            </h3>

            <p>
                Compare your resume against a job description
                and identify missing skills and keywords.
            </p>

        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # =========================================================
    # HOW IT WORKS
    # =========================================================
    st.markdown("""
    <div style="text-align:center; margin-bottom:25px;">
        <div class="resumeiq-badge">
            ✦ SIMPLE WORKFLOW
        </div>

        <h2 style="
            color:#FFFFFF;
            font-family:'Playfair Display', Georgia, serif;
            margin-bottom:8px;
        ">
            How It Works
        </h2>

        <p style="
            color:#7C8A9E;
        ">
            Analyze your resume in three simple steps.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        <div class="resumeiq-feature">

            <div style="
                color:#FFB700;
                font-family:'DM Mono', monospace;
                font-size:0.75rem;
                font-weight:700;
                margin-bottom:10px;
            ">
                STEP 01
            </div>

            <div class="resumeiq-feature-icon">
                📄
            </div>

            <h3>
                Upload
            </h3>

            <p>
                Upload your resume in PDF or DOCX format.
            </p>

        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="resumeiq-feature">

            <div style="
                color:#FFB700;
                font-family:'DM Mono', monospace;
                font-size:0.75rem;
                font-weight:700;
                margin-bottom:10px;
            ">
                STEP 02
            </div>

            <div class="resumeiq-feature-icon">
                🤖
            </div>

            <h3>
                Analyze
            </h3>

            <p>
                ResumeIQ analyzes your resume using AI-powered
                scoring and semantic matching.
            </p>

        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="resumeiq-feature">

            <div style="
                color:#FFB700;
                font-family:'DM Mono', monospace;
                font-size:0.75rem;
                font-weight:700;
                margin-bottom:10px;
            ">
                STEP 03
            </div>

            <div class="resumeiq-feature-icon">
                ✨
            </div>

            <h3>
                Improve
            </h3>

            <p>
                Get actionable recommendations to strengthen
                your resume.
            </p>

        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # =========================================================
    # NO LOGIN MESSAGE
    # =========================================================
    st.markdown("""
    <div class="resumeiq-save-card">

        <h3>
            🔓 No account required
        </h3>

        <p>
            Analyze your resume and view your results without signing in.
            You only need an account if you choose to save an analysis
            to your history.
        </p>

    </div>
    """, unsafe_allow_html=True)

    # =========================================================
    # FOOTER
    # =========================================================
    st.markdown("""
    <div class="resumeiq-footer">
        ResumeIQ · AI-Powered Resume Intelligence
    </div>
    """, unsafe_allow_html=True)