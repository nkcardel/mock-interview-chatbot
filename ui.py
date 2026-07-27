import base64
import html
import json
import time
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

LOGO_DIR = Path(__file__).parent / "assets" / "logos"
ICON_DIR = Path(__file__).parent / "assets" / "icons"


def _svg_data_uri(path: Path) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


REQUIRED_FIELD_ICON_URI = _svg_data_uri(ICON_DIR / "warning.svg")
BRIEFCASE_ICON_URI = _svg_data_uri(ICON_DIR / "briefcase.svg")
EXPERIENCE_ICON_URI = _svg_data_uri(ICON_DIR / "experience.svg")
SKILLS_ICON_URI = _svg_data_uri(ICON_DIR / "skills.svg")

CUSTOM_CSS = """
<style>
    /* ---- Hide default Streamlit menu and footer ---- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* ---- Typography & base spacing ---- */
    html, body, [class*="css"]  {
        font-family: "Poppins", sans-serif;
    }
    .block-container {
        padding-top: 2.2rem;
        padding-bottom: 3rem;
        max-width: 760px;
    }
    .st-emotion-cache-6shykm {
        padding: 1rem 1rem 2rem;
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

    /* ---- Custom company card: the Target Industry field lives outside the
       nested form (so picking "Other" can rerun immediately), so this wrapper
       carries the card border/padding instead, and the nested form is
       stripped of its own so there's no double box. ---- */
    .st-key-company_custom_wrapper {
        border: 1px solid rgba(49, 51, 63, 0.2);
        border-radius: 8px;
        padding: 1.78rem;
    }
    .st-key-company_custom_wrapper div[data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
    }
    .st-key-position_wrapper {
        border: 1px solid rgba(49, 51, 63, 0.2);
        border-radius: 8px;
        padding: 1.78rem;
    }
    .st-key-position_wrapper div[data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
    }
    .st-key-personal_info_next_row,
    .st-key-custom_company_next_row {
        margin-top: 8px;
    }
    .st-key-step_caption {
        margin-top: -10px !important;
        margin-bottom: 0 !important;
    }

    /* ---- Required-field error banner: custom warning icon, mask-colored to match the alert text ---- */
    .st-key-required_field_error div[data-testid="stAlertContainer"] {
        position: relative;
        padding-left: 3rem !important;
    }
    .st-key-required_field_error div[data-testid="stAlertContainer"]::before {
        content: "";
        position: absolute;
        left: 1.2rem;
        top: 55%;
        transform: translateY(-50%);
        width: 1.4rem;
        height: 1.4rem;
        background-color: currentColor;
        -webkit-mask-size: contain;
        mask-size: contain;
        -webkit-mask-repeat: no-repeat;
        mask-repeat: no-repeat;
        -webkit-mask-position: center;
        mask-position: center;
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
    /* Scoped to [data-stale="false"] rather than a bare div.stButton: a
       superseded step-3 button can still be sitting in the DOM (hidden via
       the data-stale rule below) while the interview's button-free stepper
       is the current render, and :has() matches on DOM presence regardless
       of display, so an unscoped check would misfire during that window. */
    .st-key-stepper:not(:has([data-stale="false"] div.stButton)) .stepper-node {
        margin-top: 16px !important;
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
    .st-key-stepper:not(:has([data-stale="false"] div.stButton)) div[data-testid="stElementContainer"]:has(.stepper-node) {
        height: 50px !important;
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
    .st-key-level_grid {
        margin-top: 5px !important;
    }
    .st-key-level_grid button[kind="secondary"] {
        background-color: rgba(148, 163, 184, 0.06) !important;
        border: 1px solid rgba(148, 163, 184, 0.25) !important;
        padding: 0.85rem 1.1rem !important;
    }
    .st-key-level_grid button[kind="secondary"]:hover {
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

    /* ---- Stale-element hiding ---- */
    [data-stale="true"] {
        display: none !important;
    }

    /* ---- Hide the avatar for assistant chat messages ---- */
    div[data-testid="stChatMessage"]:has(> div[data-testid="stChatMessageContent"][aria-label="Chat message from assistant"])
    > *:not([data-testid="stChatMessageContent"]) {
        display: none !important;
    }

    /* ---- Hide the avatar for user chat messages ---- */
    div[data-testid="stChatMessage"]:has(> div[data-testid="stChatMessageContent"][aria-label="Chat message from user"])
    > *:not([data-testid="stChatMessageContent"]) {
        display: none !important;
    }

    /* ---- User chat bubble: avatar and bubble on the right, background
       hugs the text instead of stretching the full row width ---- */
    div[data-testid="stChatMessage"]:has(> div[data-testid="stChatMessageContent"][aria-label="Chat message from user"]) {
        flex-direction: row-reverse;
        background: transparent;
    }
    div[data-testid="stChatMessage"]:has(> div[data-testid="stChatMessageContent"][aria-label="Chat message from user"])
    > div[data-testid="stChatMessageContent"] {
        flex-grow: 0;
        max-width: 80%;
        margin-left: auto;
        margin-right: 0;
        background-color: rgba(240, 242, 246, 0.5);
        border-radius: 8px;
        padding: 16px;
    }

    /* ---- Typing indicator ---- */
    .typing-indicator {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 4px 0 4px 2px;
    }
    .typing-indicator span {
        width: 5.5px;
        height: 5.5px;
        border-radius: 50%;
        background-color: #94a3b8;
        animation: typing-bounce 1.2s infinite ease-in-out both;
    }
    .typing-indicator span:nth-child(1) { animation-delay: 0s; }
    .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
    .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

    @keyframes typing-bounce {
        0%, 80%, 100% {
            transform: scale(0.6);
            opacity: 0.4;
        }
        40% {
            transform: scale(1);
            opacity: 1;
        }
    }
</style>
"""


INVALID_FIELD_BORDER_COLOR = "#BD4043"


def render_invalid_field_borders(field_keys):
    """Outlines the given widget keys in red to flag them as missing required input.

    Covers the three widget shapes used in the setup forms: plain text
    inputs/textareas (stTextInputRootElement / stTextAreaRootElement) and
    react-aria selectboxes (the [role="group"] wrapper).

    The red border is cleared the moment the user interacts with that specific
    field (focuses or types into it) rather than waiting for the next form
    submit — st.form fields don't trigger a rerun on their own, so this is
    done with a small injected script instead of a plain CSS rule.

    Note: this re-attaches a fresh listener on every call rather than
    guarding against re-attachment. components.html() tears down and
    recreates its iframe on each render, and Chrome silently detaches
    listeners whose closures live in an iframe realm that gets destroyed —
    even though the target DOM node (in the parent document) survives the
    Streamlit rerun untouched. A "already attached" flag would just leave
    the field listener-less after the first rerun.

    A timestamp nonce is embedded in the payload so consecutive calls never
    produce byte-identical HTML: Streamlit skips reloading the component
    (and thus never re-runs the script) when a call's content is unchanged
    from the last render, which would otherwise leave a field's red border
    un-reapplied when the same field fails validation twice in a row.
    """
    if not field_keys:
        return
    keys_json = json.dumps(list(field_keys))
    nonce = time.time_ns()
    components.html(
        f"""
        <script>
        (function() {{
            // nonce: {nonce}
            const invalidKeys = {keys_json};
            const doc = window.parent.document;

            let styleEl = doc.getElementById('invalid-field-style');
            if (!styleEl) {{
                styleEl = doc.createElement('style');
                styleEl.id = 'invalid-field-style';
                styleEl.textContent =
                    '.field-invalid {{ border: 1.5px solid {INVALID_FIELD_BORDER_COLOR} !important; ' +
                    'border-radius: 8px; }}';
                doc.head.appendChild(styleEl);
            }}

            const targetSelector =
                '[data-testid="stTextInputRootElement"], [data-testid="stTextAreaRootElement"], [role="group"]';

            invalidKeys.forEach(function(key) {{
                const container = doc.querySelector('.st-key-' + key);
                if (!container) return;
                const target = container.querySelector(targetSelector);
                if (!target) return;
                target.classList.add('field-invalid');

                const interactive = container.querySelector('input, textarea');
                if (!interactive) return;

                // Re-look up the wrapper by key on every event instead of closing over
                // `target`: Streamlit recreates that ancestor div on each rerun even when
                // it reuses this same input/textarea node, so a captured reference would
                // go stale and clear the border on a detached, invisible copy.
                const clearError = function() {{
                    const freshContainer = doc.querySelector('.st-key-' + key);
                    const freshTarget = freshContainer && freshContainer.querySelector(targetSelector);
                    if (freshTarget) freshTarget.classList.remove('field-invalid');

                    // The Target Industry selectbox's error border mirrors the
                    // custom industry text input's whenever that field is shown.
                    if (key === 'input_custom_industry') {{
                        const industryContainer = doc.querySelector('.st-key-input_industry');
                        const industryTarget = industryContainer && industryContainer.querySelector(targetSelector);
                        if (industryTarget) industryTarget.classList.remove('field-invalid');
                    }}

                    if (key === 'input_custom_position') {{
                        const positionContainer = doc.querySelector('.st-key-input_position');
                        const positionTarget = positionContainer && positionContainer.querySelector(targetSelector);
                        if (positionTarget) positionTarget.classList.remove('field-invalid');
                    }}
                }};
                interactive.addEventListener('focus', clearError);
                interactive.addEventListener('input', clearError);
            }});
        }})();
        </script>
        """,
        height=0,
    )


def scroll_chat_to_bottom():
    """Keeps the latest chat message in view after a rerun."""
    nonce = time.time_ns()
    components.html(
        f"""
        <script>
        (function() {{
            // nonce: {nonce}
            const doc = window.parent.document;
            function scrollToBottom() {{
                const se = doc.scrollingElement || doc.documentElement;
                se.scrollTop = se.scrollHeight;
                window.parent.scrollTo(0, doc.body.scrollHeight);
                const container = doc.querySelector(
                    '[data-testid="stAppScrollToBottomContainer"], [data-testid="stMain"]'
                );
                if (container) {{
                    container.scrollTop = container.scrollHeight;
                }}
            }}
            scrollToBottom();
            const target = doc.querySelector(
                '[data-testid="stAppScrollToBottomContainer"], [data-testid="stMain"]'
            ) || doc.body;
            const observer = new MutationObserver(scrollToBottom);
            observer.observe(target, {{childList: true, subtree: true}});
            setTimeout(() => observer.disconnect(), 2000);
            [0, 50, 150, 300, 600, 1000].forEach(delay => setTimeout(scrollToBottom, delay));
        }})();
        </script>
        """,
        height=0,
    )


def apply_custom_styles():
    """Injects custom CSS styles into Streamlit."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    st.markdown(
        f'<style>.st-key-required_field_error div[data-testid="stAlertContainer"]::before {{'
        f'mask-image: url("{REQUIRED_FIELD_ICON_URI}");'
        f'-webkit-mask-image: url("{REQUIRED_FIELD_ICON_URI}");'
        f"}}</style>",
        unsafe_allow_html=True,
    )


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
    st.markdown('<div class="hero-title">Mock Job Interview Chatbot</div>', unsafe_allow_html=True)
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
        # Land back on whichever Company sub-screen the user actually used
        user_data = st.session_state.get("user_data", {})
        st.session_state.company_option = "custom" if user_data.get("industry") else "select"
    st.session_state.setup_error = None
    st.session_state.invalid_fields = set()


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
    """Renders a structured InterviewEvaluation (see schemas.py)."""
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