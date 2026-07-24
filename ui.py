import html

import streamlit as st

CUSTOM_CSS = """
<style>
    /* ---- Typography & base spacing ---- */
    html, body, [class*="css"]  {
        font-family: "Inter", "Source Sans Pro", sans-serif;
    }
    .block-container {
        padding-top: 2.2rem;
        padding-bottom: 3rem;
        max-width: 760px;
    }

    /* ---- Hero header ---- */
    .hero-title {
        font-size: 2.1rem;
        font-weight: 800;
        margin-bottom: 0.15rem;
        color: #0054A3;
    }
    .hero-subtitle {
        color: #6b7280;
        font-size: 1rem;
        margin-bottom: 1.6rem;
    }

    /* ---- Section cards ---- */
    .card {
        background: rgba(148, 163, 184, 0.06);
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 14px;
        padding: 1.4rem 1.5rem;
        margin-bottom: 1.2rem;
    }

    /* ---- Step pill ---- */
    .step-pill {
        display: inline-block;
        padding: 0.15rem 0.7rem;
        border-radius: 999px;
        background: rgba(28, 131, 255, 0.1);
        color: #0054A3 !important;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        margin-bottom: 0.6rem;
    }

    /* ---- Step progress indicator ---- */
    div[data-testid="stProgress"] > div > div > div {
        background-color: #0054A3 !important;
    }

    /* ---- Buttons ---- */
    /* Base button sizing & typography for all buttons */
    div.stButton > button,
    div[data-testid="stFormSubmitButton"] > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.4rem !important;
        border: none !important;
    }

    /* ---- Secondary form submit buttons ---- */
    button[kind="secondaryFormSubmit"] {
        background-color: #97a6c326 !important;
        transition: background-color 0.15s ease !important;
    }
    button[kind="secondaryFormSubmit"]:hover {
        background-color: #97a6c359 !important;
    }

    /* ---- Score badge ---- */
    .score-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 92px;
        height: 92px;
        border-radius: 50%;
        font-size: 1.9rem;
        font-weight: 800;
        color: white;
        margin: 0 auto 0.4rem auto;
    }
    .score-wrap {
        text-align: center;
    }
    .score-caption {
        color: #6b7280;
        font-size: 0.85rem;
    }

    hr {
        margin: 1.4rem 0;
        border-color: rgba(148, 163, 184, 0.25);
    }
</style>
"""


def apply_custom_styles():
    """Injects custom CSS styles into Streamlit."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header():
    """Renders main application headers."""
    st.markdown('<div class="hero-title">Mock Interview Chatbot</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Practice a realistic role-specific interview and get structured, '
        'question-by-question feedback.</div>',
        unsafe_allow_html=True,
    )


SETUP_STEP_LABELS = {
    1: "Personal Information",
    2: "Company",
    3: "Position",
}


def render_step_indicator(feedback_shown: bool, setup_complete: bool, setup_step: int = 1):
    """Renders the step indicator progress bar across the 5-step flow:
    Personal Information -> Company -> Position -> Interview -> Feedback.
    """
    if feedback_shown:
        step_label, step_num = "Step 5 of 5 · Feedback", 5
    elif setup_complete:
        step_label, step_num = "Step 4 of 5 · Interview", 4
    else:
        step_num = setup_step
        step_label = f"Step {step_num} of 5 · {SETUP_STEP_LABELS.get(step_num, 'Personal Information')}"

    st.markdown(f'<span class="step-pill">{step_label}</span>', unsafe_allow_html=True)
    st.progress(step_num / 5)


def render_evaluation(evaluation):
    """Renders a structured InterviewEvaluation (see schemas.py).

    Replaces the old approach of dumping the model's raw markdown response
    with st.markdown(feedback_text). Now the response is a validated
    Pydantic object, so rendering means iterating typed fields instead of
    trusting the model to have followed a formatting instruction exactly.

    Model-generated text is still untrusted input from a rendering
    standpoint (candidate_response_summary in particular is derived from
    the user's own free-text answers), so it's HTML-escaped before being
    interpolated into unsafe_allow_html markup.
    """
    for i, q in enumerate(evaluation.questions, start=1):
        st.markdown(
            f'<div class="card">'
            f'<b>Question {i}: {html.escape(q.topic)}</b>'
            f'<hr style="margin: 8px 0; border: none; border-top: 1px solid #eee;"/>'
            f'<span style="color:#6b7280;">Asked:</span> {html.escape(q.question_asked)}<br/>'
            f'<span style="color:#6b7280;">Candidate:</span> {html.escape(q.candidate_response_summary)}<br/>'
            f'<b>Score:</b> {q.score}/10<br/>'
            f'<span style="color:#6b7280;">{html.escape(q.critique)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**✅ Top Strengths**")
        for item in evaluation.top_strengths:
            st.markdown(f"- {item}")
    with col2:
        st.markdown("**📈 Areas for Improvement**")
        for item in evaluation.areas_for_improvement:
            st.markdown(f"- {item}")

    st.markdown("---")
    st.markdown(f"**Final Verdict:** {evaluation.final_verdict}")


def render_score_badge(score_val: float):
    """Renders the circular score badge."""
    color = "#22C55E" if score_val >= 7.5 else "#F59E0B" if score_val >= 5 else "#EF4444"
    st.markdown(
        f"""
        <div class="score-wrap">
            <div class="score-badge" style="background:{color};">{score_val:g}</div>
            <div class="score-caption">Overall score out of 10</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<hr/>", unsafe_allow_html=True)