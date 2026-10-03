from textwrap import dedent

import streamlit as st


def render() -> None:
    st.markdown(
        dedent(
            """
            <div class="resumeiq-page-heading">
                <div class="resumeiq-badge">✦ RESOURCES & TIPS</div>
                <h1>Build a more <span>ATS-friendly</span> resume.</h1>
                <p>Practical guidelines you can apply before sending your resume.</p>
            </div>
            """
        ),
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            dedent(
                """
                <div class="resumeiq-feature">
                    <div class="resumeiq-feature-icon">✅</div>
                    <h3>Do's</h3>
                    <p>
                        Use standard section headings, include relevant keywords,
                        keep formatting simple, list skills explicitly,
                        quantify achievements, and use common document formats.
                    </p>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown(
            dedent(
                """
                <div class="resumeiq-feature">
                    <div class="resumeiq-feature-icon">❌</div>
                    <h3>Don'ts</h3>
                    <p>
                        Avoid unnecessary tables, text boxes, decorative graphics,
                        unusual fonts, excessive columns, and keyword stuffing.
                    </p>
                </div>
                """
            ),
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("### 🔑 Common ATS Keywords by Industry")
    tab1, tab2, tab3 = st.tabs(["💻 Tech", "💼 Business", "🎨 Creative"])

    with tab1:
        st.markdown(
            "**Software Development:** Python, Java, JavaScript, React, Django, "
            "Spring, Git, Docker, Kubernetes, Agile, Scrum, CI/CD"
        )

    with tab2:
        st.markdown(
            "**Business & Management:** project management, stakeholder engagement, "
            "budget management, strategic planning, team leadership"
        )

    with tab3:
        st.markdown(
            "**Creative & Design:** Adobe Creative Suite, UI/UX design, wireframing, "
            "prototyping, brand identity, visual communication"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        """
        <div class="resumeiq-save-card">
            <div class="resumeiq-save-kicker">RESUMEIQ TIP</div>
            <h3>Run ResumeIQ before you apply</h3>
            <p>
                Analyze the resume against the specific job description whenever
                possible. That gives you a targeted view of missing keywords and skills.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
