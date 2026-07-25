import base64
import html
from pathlib import Path

import streamlit as st

LOGO_DIR = Path(__file__).parent / "assets" / "logos"

CUSTOM_CSS = """
<style>
    /* ---- Hide default Streamlit menu and footer ---- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

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

    /* ---- Setup form container ---- */
    div[data-testid="stForm"] {
        padding: 1.78rem !important;
    }

    /* ---- Setup form headings ---- */
    div[data-testid="stForm"] h3 {
        padding-top: 0 !important;
    }
    .st-key-personal_info_next_row,
    .st-key-custom_company_next_row {
        margin-top: 8px;
    }

    /* ---- Numbered stepper ---- */
    .st-key-stepper {
        position: relative;
        margin-bottom: 1.8rem;
    }
    .st-key-stepper::before {
        content: "";
        position: absolute;
        top: 33px;
        left: 10%;
        right: 10%;
        height: 1.5px;
        background: rgba(148, 163, 184, 0.35);
        z-index: 0;
    }
    .stepper-node {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 1rem;
        margin: 0 auto;
        position: relative;
        z-index: 1;
        background: #fff;
    }
    .stepper-node.done {
        background: #0054A3;
        color: #fff;
        border: none;
    }
    .stepper-node.current {
        background: #fff;
        color: #0054A3;
        border: 2px solid #0054A3;
    }
    .stepper-node.upcoming {
        background: #fff;
        color: #9ca3af;
        border: 2px solid #d1d5db;
    }
    .stepper-label {
        text-align: center;
        font-size: 0.72rem;
        font-weight: 700;
        color: #6b7280;
    }
    .stepper-label.current {
        color: #0054A3;
    }

    .st-key-stepper div.stButton > button {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 34px !important;
        height: 34px !important;
        min-height: 34px !important;
        border-radius: 50% !important;
        padding: 0 !important;
        margin: 0 auto !important;
        background: #0054A3 !important;
        color: #fff !important;
        font-weight: 700 !important;
        position: relative;
        z-index: 1;
    }
    .st-key-stepper div.stButton > button p {
        font-weight: 700 !important;
        font-size: 1.05rem !important;
    }
    .st-key-stepper div[data-testid="stElementContainer"]:has(.stepper-node),
    .st-key-stepper div[data-testid="stElementContainer"]:has(> div.stButton) {
        height: 34px !important;
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

    /* ---- Company grid */
    .st-key-company_grid button[kind="secondaryFormSubmit"] {
        background-color: rgba(148, 163, 184, 0.06) !important;
        border: 1px solid rgba(148, 163, 184, 0.25) !important;
        padding: 0.85rem 1.1rem !important;
        margin-bottom: 0.5rem;
    }
    .st-key-company_grid button[kind="secondaryFormSubmit"] > div {
        justify-content: flex-start !important;
    }
    .st-key-company_grid button[kind="secondaryFormSubmit"]:hover {
        background-color: rgba(28, 131, 255, 0.08) !important;
        border-color: #0054A3 !important;
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


LOGO_MIME_TYPES = {
    ".svg": "image/svg+xml",
}


def render_company_logo_styles(company_logo_files: dict):
    """Swaps each company tile's visible text for its logo image, when one is present.

    Companies without a file in assets/logos/ (see LOGO_DIR) simply keep showing
    as plain text tiles
    """
    rules = []
    for company, filename in company_logo_files.items():
        path = LOGO_DIR / filename
        if not path.exists():
            continue
        mime = LOGO_MIME_TYPES.get(path.suffix.lower())
        if not mime:
            continue
        data_uri = f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")
        rules.append(
            f'.st-key-company_btn_{company} button[kind="secondaryFormSubmit"] {{'
            f'color: transparent !important;'
            f'background-image: url("{data_uri}");'
            f'background-repeat: no-repeat;'
            f'background-position: center;'
            f'background-size: contain;'
            f'background-origin: content-box;'
            f'height: 90px !important;'
            f'padding: 10px 12px !important;'
            f"}}"
        )
    if rules:
        st.markdown(f"<style>{''.join(rules)}</style>", unsafe_allow_html=True)


def render_header():
    """Renders main application headers."""
    st.markdown('<div class="hero-title">Mock Interview Chatbot</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Practice a realistic role-specific interview and get structured, '
        'question-by-question feedback.</div>',
        unsafe_allow_html=True,
    )


STEP_LABELS = {
    1: "Personal Info",
    2: "Company",
    3: "Position",
    4: "Interview",
    5: "Feedback",
}


def _goto_setup_step(step_num: int):
    st.session_state.setup_step = step_num
    if step_num == 2:
        # Land back on whichever Company sub-screen the user actually used —
        # "industry" is only ever set by the custom-profile path, so its
        # presence is what distinguishes "custom" from "select" (which also
        # covers the "no target company" shortcut, since that starts there).
        user_data = st.session_state.get("user_data", {})
        st.session_state.company_option = "custom" if user_data.get("industry") else "select"
    st.session_state.setup_error = None


def render_step_indicator(feedback_shown: bool, setup_complete: bool, setup_step: int = 1):
    """Renders a 5-node numbered stepper: Personal Info -> Company -> Position ->
    Interview -> Feedback.
    """
    if feedback_shown:
        current = 5
    elif setup_complete:
        current = 4
    else:
        current = setup_step

    in_setup_phase = not setup_complete and not feedback_shown

    with st.container(key="stepper"):
        if in_setup_phase:
            # The current node is a clickable button too, but it
            # should still look outlined/"current" rather than filled/"done" —
            # override the general clickable-button style for just this one key.
            st.markdown(
                f'<style>.st-key-step_nav_{current} div.stButton > button {{'
                f'background: #fff !important;'
                f'color: #0054A3 !important;'
                f'border: 2px solid #0054A3 !important;'
                f"}}</style>",
                unsafe_allow_html=True,
            )

        cols = st.columns(5)
        for step_num, col in enumerate(cols, start=1):
            if step_num < current:
                state = "done"
            elif step_num == current:
                state = "current"
            else:
                state = "upcoming"

            node_content = "✓" if state == "done" else str(step_num)

            with col:
                if in_setup_phase and state in ("done", "current"):
                    st.button(
                        node_content,
                        key=f"step_nav_{step_num}",
                        on_click=_goto_setup_step,
                        args=(step_num,),
                        use_container_width=True,
                    )
                else:
                    st.markdown(f'<div class="stepper-node {state}">{node_content}</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="stepper-label {state}">{STEP_LABELS[step_num]}</div>', unsafe_allow_html=True
                )


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