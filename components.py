import html
import json
import math
import time

import streamlit as st
import streamlit.components.v1 as components

from styles import (
    BAR_CHART_ICON_URI,
    CHAT_ICON_URI,
    EVALUATION_ICON_URI,
    IMPROVEMENT_ICON_URI,
    KEY_ICON_URI,
    STRENGTHS_ICON_URI,
)

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


def render_header():
    """Renders main application headers."""
    st.markdown('<div class="hero-title">Mock Job Interview Chatbot</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Practice a realistic role-specific interview and get structured, '
        "question-by-question feedback.</div>",
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
                f"<style>.st-key-step_nav_{current} div.stButton > button {{"
                f"background: #fff !important;"
                f"color: #0054A3 !important;"
                f"border: 2px solid #0054A3 !important;"
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
                    st.markdown(
                        f'<div class="stepper-node {state}">{node_content}</div>',
                        unsafe_allow_html=True,
                    )
                st.markdown(
                    f'<div class="stepper-label {state}">{STEP_LABELS[step_num]}</div>',
                    unsafe_allow_html=True,
                )


def _icon_img(uri: str, size: str = "1em") -> str:
    return f'<img src="{uri}" style="height:{size}; vertical-align:-0.15em; margin-right:4px;"/>'


def _render_insight_card(icon: str, title: str, body_html: str):
    st.markdown(
        f'<div class="insight-card">'
        f'<div class="insight-card-title"><span>{icon}</span><span>{html.escape(title)}</span></div>'
        f"{body_html}"
        f"</div>",
        unsafe_allow_html=True,
    )


def render_evaluation(evaluation, turns):
    """Renders a structured InterviewEvaluation (see schemas.py) alongside the
    original interview turns, which supply the ground-truth question text and
    the candidate's verbatim answer for each entry.
    """
    _render_insight_card(
        _icon_img(BAR_CHART_ICON_URI),
        "Overall Performance",
        f"<p>{html.escape(evaluation.overall_summary)}</p>",
    )

    strengths_html = (
        "<ul>"
        + "".join(f"<li>{html.escape(item)}</li>" for item in evaluation.top_strengths)
        + "</ul>"
    )
    _render_insight_card(_icon_img(STRENGTHS_ICON_URI), "Top Strengths", strengths_html)

    improvements_html = (
        "<ul>"
        + "".join(f"<li>{html.escape(item)}</li>" for item in evaluation.areas_for_improvement)
        + "</ul>"
    )
    _render_insight_card(
        _icon_img(IMPROVEMENT_ICON_URI), "Areas for Improvement", improvements_html
    )

    with st.container(key="response_eval_title"):
        st.markdown(
            f"<h4>{_icon_img(EVALUATION_ICON_URI, size='1.2em')} Response Evaluation</h4>",
            unsafe_allow_html=True,
        )
    render_response_evaluation(evaluation, turns)


TIER_LABELS = ("Poor", "Average", "Excellent")
TIER_COLORS = ("#EF4444", "#F59E0B", "#2DD4BF")
TIER_VERDICTS = ("Needs Improvement", "Solid Performance", "Strong Performance")


def _tier_index(score_val: float) -> int:
    """0 = Poor (1-3), 1 = Average (4-7), 2 = Excellent (8-10)."""
    if score_val >= 8:
        return 2
    if score_val >= 4:
        return 1
    return 0


def _score_color(score_val: float) -> str:
    return TIER_COLORS[_tier_index(score_val)]


# Visual order for the 2x2 criteria grid: Role Fit / Problem-Solving on top,
# Depth & Substance / Communication on the bottom.
SCORE_GRID_ORDER = ("Role Fit", "Problem-Solving", "Depth & Substance", "Communication")

CRITERIA_HELP_TEXT = {
    "Communication": "How clear, articulate, and well-structured the candidate's communication was.",
    "Depth & Substance": "How much concrete depth, detail, and evidence the candidate's answers contained.",
    "Problem-Solving": "The quality of the candidate's reasoning and problem-solving approach.",
    "Role Fit": "How well the candidate's background and answers align with what the role requires.",
}


RING_SIZE = 128
RING_THICKNESS = 14


MINI_RING_SIZE = 60
MINI_RING_THICKNESS = 6


def _render_ring_html(
    value: float,
    color: str,
    size: int = RING_SIZE,
    thickness: int = RING_THICKNESS,
    inner_bg: str = "#04203f",
    font_size: str = "1.5rem",
    show_denominator: bool = True,
    track_color: str = "rgba(255, 255, 255, 0.12)",
) -> str:
    """Builds a circular progress ring (conic-gradient) for a 0-10 value.

    Two small dots are positioned at the start and end of the arc (via trig
    on the percentage) to fake a round linecap, since conic-gradient itself
    can only draw a hard edge. Reused for both the large overall-score ring
    and the small per-question rings, which sit on different backgrounds
    (dark score card vs. light response-evaluation card) — hence inner_bg
    and track_color, which need to stay visible against whichever it is.
    """
    pct = value / 10 * 100
    center = size / 2
    radius = center - thickness / 2

    def cap_style(p):
        theta = (p / 100) * 2 * math.pi
        x = center + radius * math.sin(theta) - thickness / 2
        y = center - radius * math.cos(theta) - thickness / 2
        return f"left:{x:.1f}px; top:{y:.1f}px; width:{thickness}px; height:{thickness}px; background:{color};"

    inner_size = size - thickness * 2
    value_text = f"{value:g}/10" if show_denominator else f"{value:g}"
    return (
        f'<div class="score-ring" style="width:{size}px; height:{size}px; '
        f'background: conic-gradient({color} {pct}%, {track_color} 0%);">'
        f'<div class="score-ring-cap" style="{cap_style(0)}"></div>'
        f'<div class="score-ring-cap" style="{cap_style(pct)}"></div>'
        f'<div class="score-ring-inner" style="width:{inner_size}px; height:{inner_size}px; background:{inner_bg};">'
        f'<span class="score-ring-value" style="color:{color}; font-size:{font_size};">{value_text}</span>'
        f"</div>"
        f"</div>"
    )


def _criterion_box_html(label: str, value: float) -> str:
    tier = _tier_index(value)
    color = TIER_COLORS[tier]
    pct = value / 10 * 100
    helper_text = html.escape(CRITERIA_HELP_TEXT.get(label, ""))
    return (
        f'<div class="score-criterion-box">'
        f'<div class="score-criterion-title">{html.escape(label)}</div>'
        f'<div class="score-criterion-helper">{helper_text}</div>'
        f'<div class="score-tier-track">'
        f'<div class="score-tier-fill" style="width:{pct}%; background:{color};"></div>'
        f"</div>"
        f'<div class="score-tier-label" style="color:{color};">'
        f"<span>{TIER_LABELS[tier]}</span><span>{value:.1f}/10</span>"
        f"</div>"
        f"</div>"
    )


def render_score_overview(evaluation):
    """Renders one card combining a circular overall score progress ring with
    a 2x2 grid of criterion boxes, each showing a segmented 3-tier bar
    (Poor / Average / Excellent) for the four supporting criteria.
    """
    overall = evaluation.clamped_overall_score()
    overall_color = _score_color(overall)
    overall_verdict = TIER_VERDICTS[_tier_index(overall)]
    scores_by_label = dict(evaluation.criteria_scores())

    boxes_html = "".join(
        _criterion_box_html(label, scores_by_label[label]) for label in SCORE_GRID_ORDER
    )
    ring_html = _render_ring_html(overall, overall_color)

    st.markdown(
        f'<div class="card score-overview-card">'
        f'<div class="score-ring-box">'
        f"{ring_html}"
        f'<div class="score-caption">Overall Score</div>'
        f'<div class="score-verdict">{overall_verdict}</div>'
        f"</div>"
        f'<div class="score-overview-bars">{boxes_html}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def render_response_evaluation(evaluation, turns):
    """Renders each question as a collapsible accordion item.

    The header (a <summary>) holds the topic pill and question text
    stacked in one column, plus a mini score ring; the body holds the
    candidate's answer and the key takeaways. All items start collapsed.
    """
    items_html = []
    for i, q in enumerate(evaluation.questions):
        turn = turns[i]
        color = _score_color(q.score)
        takeaways_html = "".join(f"<li>{html.escape(t)}</li>" for t in q.key_takeaways)
        ring_html = _render_ring_html(
            q.score,
            color,
            size=MINI_RING_SIZE,
            thickness=MINI_RING_THICKNESS,
            inner_bg="#fff",
            font_size="0.78rem",
            track_color="rgba(148, 163, 184, 0.25)",
        )
        items_html.append(
            f'<details class="response-eval-accordion-item">'
            f'<summary class="response-eval-accordion-header">'
            f'<div class="response-eval-header-text">'
            f'<span class="response-eval-topic-pill">{html.escape(q.topic)}</span>'
            f'<span class="response-eval-question">{html.escape(turn["displayed_question"])}</span>'
            f"</div>"
            f"{ring_html}"
            f"</summary>"
            f'<div class="response-eval-accordion-body">'
            f'<div class="response-eval-section-label"><span>{_icon_img(CHAT_ICON_URI)}</span><span>Your Answer</span></div>'
            f'<div class="response-eval-answer-box">{html.escape(turn["answer"] or "")}</div>'
            f'<div class="response-eval-section-label"><span>{_icon_img(KEY_ICON_URI)}</span><span>Key Takeaways</span></div>'
            f'<ul class="response-eval-takeaways-list">{takeaways_html}</ul>'
            f"</div>"
            f"</details>"
        )

    st.markdown(
        f'<div class="response-eval-accordion">{"".join(items_html)}</div>',
        unsafe_allow_html=True,
    )
