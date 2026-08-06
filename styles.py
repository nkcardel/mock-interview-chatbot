import base64
from pathlib import Path

import streamlit as st

LOGO_DIR = Path(__file__).parent / "assets" / "logos"
ICON_DIR = Path(__file__).parent / "assets" / "icons"


def _svg_data_uri(path: Path) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


REQUIRED_FIELD_ICON_URI = _svg_data_uri(ICON_DIR / "warning.svg")
BRIEFCASE_ICON_URI = _svg_data_uri(ICON_DIR / "briefcase.svg")
EXPERIENCE_ICON_URI = _svg_data_uri(ICON_DIR / "experience.svg")
SKILLS_ICON_URI = _svg_data_uri(ICON_DIR / "skills.svg")
BAR_CHART_ICON_URI = _svg_data_uri(ICON_DIR / "bar-chart.svg")
STRENGTHS_ICON_URI = _svg_data_uri(ICON_DIR / "strengths.svg")
IMPROVEMENT_ICON_URI = _svg_data_uri(ICON_DIR / "improvement.svg")
EVALUATION_ICON_URI = _svg_data_uri(ICON_DIR / "evaluation.svg")
CHAT_ICON_URI = _svg_data_uri(ICON_DIR / "chat.svg")
KEY_ICON_URI = _svg_data_uri(ICON_DIR / "key.svg")
FEEDBACK_ICON_URI = _svg_data_uri(ICON_DIR / "feedback.svg")
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
        margin: 1.2rem 0;
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
    .st-key-feedback_step_caption {
        margin-top: 6px !important;
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
        white-space: nowrap !important;
    }

    /* ---- Restart Interview button: extra breathing room above it, since
       it sits directly under the response evaluation accordion. ---- */
    .st-key-btn_restart {
        margin-top: 2rem;
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

    /* ---- Score ring: a circular progress ring (conic-gradient) with the
       numeric score in a plain circle cut out of its center. The two
       .score-ring-cap dots are absolutely positioned (in Python, via
       trig on the score percentage) at the start and end of the arc to
       fake a round linecap, since conic-gradient itself only draws hard
       edges. ---- */
    .score-ring {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 128px;
        height: 128px;
        border-radius: 50%;
        margin: 0 auto 0.6rem auto;
    }
    .score-ring-cap {
        position: absolute;
        width: 14px;
        height: 14px;
        border-radius: 50%;
    }
    .score-ring-inner {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 98px;
        height: 98px;
        border-radius: 50%;
        background: #04203f;
    }
    .score-ring-value {
        font-size: 1.5rem;
        font-weight: 800;
    }
    .score-caption {
        color: #94a3b8;
        font-size: 0.85rem;
    }
    .score-verdict {
        color: #fff;
        font-weight: 700;
        font-size: 0.85rem;
        text-align: center;
        max-width: 150px;
    }

    /* ---- Combined score overview card: circular overall score box on the
       left, four criterion boxes in a 2x2 grid on the right, each with a
       segmented 3-tier bar. Styled as a dark navy panel with teal-accented
       bordered sub-boxes so it stands apart from the rest of the (light)
       feedback screen. ---- */
    .card.score-overview-card {
        background: #04203f;
        border: 1px solid rgba(59, 130, 246, 0.25);
        margin-bottom: 3rem;
    }
    .score-overview-card {
        display: flex;
        align-items: stretch;
        gap: 1.2rem;
        flex-wrap: wrap;
    }
    .score-ring-box,
    .score-criterion-box {
        border: 1.5px solid rgba(45, 212, 191, 0.45);
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.03);
    }
    .score-ring-box {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
        padding: 1.4rem 1.4rem 1.2rem 1.4rem;
        margin: 0 auto;
    }
    .score-overview-bars {
        flex: 1 1 320px;
        min-width: 300px;
        display: grid;
        grid-template-columns: 1fr 1fr;
        column-gap: 1rem;
        row-gap: 1rem;
    }
    .score-criterion-box {
        padding: 1rem 1.1rem;
    }
    .score-criterion-title {
        color: #f1f5f9;
        font-weight: 500;
        font-size: 0.95rem;
        margin-bottom: 0.25rem;
    }
    .score-criterion-helper {
        color: rgba(226, 232, 240, 0.55);
        font-size: 0.65rem;
        line-height: 1.35;
        margin-bottom: 0.7rem;
    }
    .score-tier-track {
        width: 100%;
        height: 8px;
        border-radius: 4px;
        background: rgba(255, 255, 255, 0.12);
        overflow: hidden;
        margin-bottom: 6px;
    }
    .score-tier-fill {
        height: 100%;
        border-radius: 4px;
    }
    .score-tier-label {
        display: flex;
        justify-content: space-between;
        font-size: 0.78rem;
        font-weight: 500;
    }

    /* ---- Insight cards: Overall Performance / Top Strengths / Areas for
       Improvement, each a light bordered card with an icon+heading row ---- */
    .insight-card {
        background: #fff;
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 14px;
        padding: 1.3rem 1.5rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
    }
    .insight-card-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1.05rem;
        font-weight: 700;
        color: #111827;
        margin-bottom: 0.7rem;
    }
    .insight-card ul {
        margin: 0;
        padding-left: 1.2rem;
    }
    .insight-card li {
        margin-bottom: 4px;
    }
    .insight-card p {
        margin: 0;
    }

    /* ---- Response evaluation: each question renders as an accordion item
       built from native <details>/<summary>, so expanding/collapsing needs
       no Streamlit rerun. The <summary> header holds the topic pill,
       question text, and score; the body holds the answer and key
       takeaways. ---- */
    /* Streamlit's flex column adds each element's own margins rather than
       collapsing them, so this must net out to the same total gap as
       .card's margin-bottom above: 3rem total minus the preceding
       .insight-card's own 1.2rem margin-bottom = 1.8rem here. */
    .st-key-response_eval_title {
        margin-top: 1.8rem;
    }
    .response-eval-accordion {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        margin: 1rem 0;
    }
    .response-eval-accordion-item {
        background: #fff;
        border: 1px solid rgba(148, 163, 184, 0.18);
        border-radius: 14px;
        padding: 0 1.6rem;
    }
    .response-eval-accordion-item[open] {
        padding-bottom: 1.5rem;
    }
    .response-eval-accordion-header {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 1.2rem 0;
        cursor: pointer;
        list-style: none;
    }
    .response-eval-accordion-header::-webkit-details-marker {
        display: none;
    }
    .response-eval-accordion-header::after {
        content: "";
        flex-shrink: 0;
        width: 8px;
        height: 8px;
        margin-left: 4px;
        border-right: 2px solid #6b7280;
        border-bottom: 2px solid #6b7280;
        transform: rotate(-45deg);
        transition: transform 0.15s ease;
    }
    .response-eval-accordion-item[open] > .response-eval-accordion-header::after {
        transform: rotate(45deg);
    }
    .response-eval-accordion-body > .response-eval-section-label:first-child {
        margin-top: 0.5rem;
    }
    /* Topic pill + question stack in one column; the mini score ring sits
       beside that column as its own flex item. */
    .response-eval-header-text {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 6px;
        flex: 1;
        min-width: 0;
    }
    .response-eval-accordion-header .score-ring {
        margin: 0 0 0 32px;
        flex-shrink: 0;
    }
    .response-eval-topic-pill {
        display: inline-block;
        padding: 5px 14px;
        border-radius: 999px;
        background: rgba(0, 84, 163, 0.08);
        color: #0054a3;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .response-eval-question {
        font-size: 1.05rem;
        font-weight: 500;
        color: #111827;
        margin: 0;
    }
    .response-eval-section-label {
        display: flex;
        align-items: center;
        gap: 6px;
        font-weight: 700;
        color: #374151;
        font-size: 1.05rem;
        margin-bottom: 5px;
        margin-top: 2rem;
    }
    .response-eval-answer-box {
        background: rgba(148, 163, 184, 0.07);
        border-radius: 10px;
        padding: 0.9rem 1rem;
        color: #374151;
        margin-bottom: 1.3rem;
    }
    .response-eval-takeaways-list {
        margin: 0 0 16px 0;
        padding-left: 1.2rem;
        color: #374151;
    }
    .response-eval-takeaways-list li {
        margin-bottom: 4px;
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

    /* ---- Chat input box ---- */
    /* -webkit-appearance/appearance: none is needed for Safari on macOS,
       which otherwise applies its native rounded "capsule" search-field
       chrome to the textarea, overriding the authored border-radius below
       and making the box look pill/circular regardless of this rule. */
    [data-testid="stChatInput"] > div {
        border-radius: 20px !important;
    }
    [data-testid="stChatInputTextArea"] {
        -webkit-appearance: none;
        appearance: none;
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
            f"color: transparent !important;"
            f'background-image: url("{data_uri}");'
            f"background-repeat: no-repeat;"
            f"background-position: center;"
            f"background-size: contain;"
            f"background-origin: content-box;"
            f"height: 90px !important;"
            f"padding: 10px 12px !important;"
            f"}}"
        )
    if rules:
        st.markdown(f"<style>{''.join(rules)}</style>", unsafe_allow_html=True)
