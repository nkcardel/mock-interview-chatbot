import logging
import time

import openai
import streamlit as st
from openai import OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

import prompts
import question_bank
from schemas import HumanizerTurn, InterviewEvaluation, SetupResult
from components import (
    render_evaluation,
    render_header,
    render_invalid_field_borders,
    render_score_overview,
    render_step_indicator,
    scroll_chat_to_bottom,
)
from styles import (
    BRIEFCASE_ICON_URI,
    EXPERIENCE_ICON_URI,
    FEEDBACK_ICON_URI,
    SKILLS_ICON_URI,
    apply_custom_styles,
    render_company_logo_styles,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------
# Page Config & Initial Setup
# ---------------------------
st.set_page_config(
    page_title="Mock Job Interview Chatbot",
    page_icon="🤖",
    layout="centered",
)

apply_custom_styles()
render_header()


def render_usage_sidebar():
    """Running total of LLM token usage/cost for this session, for cost visibility."""
    totals = st.session_state.usage_totals
    if totals["total_tokens"] == 0:
        return
    with st.sidebar:
        st.caption("Session LLM usage")
        st.metric("Estimated cost", f"${totals['cost']:.4f}")
        st.caption(
            f"{totals['total_tokens']:,} tokens "
            f"({totals['prompt_tokens']:,} in / {totals['completion_tokens']:,} out) · {prompts.MODEL_NAME}"
        )


CLOSING_MESSAGE = (
    "Thank you for your time today — that concludes the interview! Nice work getting through "
    "all the questions."
)

# Floor on how long the "Thinking..." spinner stays up
MIN_SPINNER_SECONDS = 0.5

# Without this, the client falls back to the SDK default of 10 minutes per
# request, which leaves the UI spinner hanging far past what a user will wait.
OPENAI_REQUEST_TIMEOUT_SECONDS = 30.0


def get_openai_client():
    """Safely initialize OpenAI client checking for secrets."""
    api_key = st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY is not set in Streamlit secrets.")
        st.error(
            "Missing OpenAI API Key. Please add `OPENAI_API_KEY` to your Streamlit secrets.",
            icon="🔑",
        )
        return None
    return OpenAI(api_key=api_key, timeout=OPENAI_REQUEST_TIMEOUT_SECONDS)


# Rate limits and transient network/server hiccups are worth a few automatic
# retries; auth failures, refusals, and length errors are not.
@retry(
    retry=retry_if_exception_type(
        (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError)
    ),
    wait=wait_exponential(multiplier=1, min=1, max=20),
    stop=stop_after_attempt(4),
    reraise=True,
)
def parse_with_retry(client, **kwargs):
    return client.beta.chat.completions.parse(**kwargs)


def track_usage(completion):
    """Accumulate this call's token usage/cost into the session total and log it."""
    usage = completion.usage
    if usage is None:
        return

    call_cost = (
        usage.prompt_tokens / 1_000_000 * prompts.PRICE_PER_1M_INPUT_TOKENS
        + usage.completion_tokens / 1_000_000 * prompts.PRICE_PER_1M_OUTPUT_TOKENS
    )

    totals = st.session_state.usage_totals
    totals["prompt_tokens"] += usage.prompt_tokens
    totals["completion_tokens"] += usage.completion_tokens
    totals["total_tokens"] += usage.total_tokens
    totals["cost"] += call_cost

    logger.info(
        "usage: %s: +%d tokens ($%.4f) - session total: %d tokens ($%.4f)",
        prompts.MODEL_NAME,
        usage.total_tokens,
        call_cost,
        totals["total_tokens"],
        totals["cost"],
    )


# ---------------------------
# Session State Initialization
# ---------------------------
if "setup_complete" not in st.session_state:
    st.session_state.setup_complete = False
if "setup_step" not in st.session_state:
    st.session_state.setup_step = 1
if "company_option" not in st.session_state:
    st.session_state.company_option = "select"
if "turns" not in st.session_state:
    st.session_state.turns = []
if "follow_up_count" not in st.session_state:
    st.session_state.follow_up_count = 0
if "last_turn_was_follow_up" not in st.session_state:
    st.session_state.last_turn_was_follow_up = False
if "feedback_shown" not in st.session_state:
    st.session_state.feedback_shown = False
if "chat_complete" not in st.session_state:
    st.session_state.chat_complete = False
if "awaiting_llm" not in st.session_state:
    st.session_state.awaiting_llm = False
if "interview_error" not in st.session_state:
    st.session_state.interview_error = None
if "setup_error" not in st.session_state:
    st.session_state.setup_error = None
if "invalid_fields" not in st.session_state:
    st.session_state.invalid_fields = set()
if "usage_totals" not in st.session_state:
    st.session_state.usage_totals = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cost": 0.0,
    }

render_usage_sidebar()

# Store finalized values safely outside form widget lifecycle
if "user_data" not in st.session_state:
    st.session_state.user_data = {
        "name": "",
        "experience": "",
        "skills": "",
        "level": "",
        "position": "",
        "company": "",
        "industry": "",
        "job_description": "",
        "job_requirements": "",
    }

COMPANY_LOGO_FILES = {
    "Meta": "meta.svg",
    "Google": "google.svg",
    "LinkedIn": "linkedin.svg",
    "Spotify": "spotify.svg",
    "IBM": "ibm.svg",
    "Microsoft": "microsoft.svg",
    "Apple": "apple.svg",
    "Samsung": "samsung.svg",
    "Amazon": "amazon.svg",
    "Accenture": "accenture.svg",
}
COMPANY_OPTIONS = tuple(COMPANY_LOGO_FILES.keys())
POSITION_PLACEHOLDER = "Select a position"
POSITION_OPTIONS = (
    POSITION_PLACEHOLDER,
    "Accountant",
    "Administrative Assistant",
    "Business Development Manager",
    "Content Strategist",
    "Customer Success Manager",
    "Customer Support Specialist",
    "Data Engineer",
    "Data Scientist",
    "Financial Analyst",
    "Human Resources Manager",
    "Legal Counsel",
    "Marketing Manager",
    "Operations Manager",
    "Product Manager",
    "Recruiter",
    "Sales Representative",
    "Software Engineer",
    "Supply Chain Analyst",
    "UX/UI Designer",
    "Other",
)
OTHER_POSITION_OPTION = "Other"
INDUSTRY_PLACEHOLDER = "Select an industry"
INDUSTRY_OPTIONS = (
    INDUSTRY_PLACEHOLDER,
    "Technology",
    "Finance & Banking",
    "Healthcare",
    "Retail & E-commerce",
    "Manufacturing",
    "Education",
    "Consulting",
    "Media & Entertainment",
    "Government & Public Sector",
    "Other",
)
OTHER_INDUSTRY_OPTION = "Other"
REQUIRED_FIELD_ERROR = "Please fill in all required fields."


def advance_to_company():
    name = st.session_state.get("input_name", "")
    experience = st.session_state.get("input_experience", "")
    skills = st.session_state.get("input_skills", "")
    st.session_state.user_data["name"] = name
    st.session_state.user_data["experience"] = experience
    st.session_state.user_data["skills"] = skills

    missing = {
        field
        for field, value in {
            "input_name": name,
            "input_experience": experience,
            "input_skills": skills,
        }.items()
        if not value.strip()
    }
    if missing:
        st.session_state.setup_error = REQUIRED_FIELD_ERROR
        st.session_state.invalid_fields = missing
        return

    st.session_state.setup_error = None
    st.session_state.invalid_fields = set()
    st.session_state.setup_step = 2


def choose_generic_company():
    st.session_state.user_data["company"] = ""
    st.session_state.user_data["industry"] = ""
    st.session_state.user_data["job_description"] = ""
    st.session_state.user_data["job_requirements"] = ""
    st.session_state.setup_error = None
    st.session_state.invalid_fields = set()
    st.session_state.setup_step = 3


def go_to_custom_company():
    if not st.session_state.user_data["industry"]:
        st.session_state.user_data["company"] = ""
    st.session_state.setup_error = None
    st.session_state.invalid_fields = set()
    st.session_state.company_option = "custom"


def select_predefined_company(company):
    st.session_state.user_data["company"] = company
    st.session_state.user_data["industry"] = ""
    st.session_state.user_data["job_description"] = ""
    st.session_state.user_data["job_requirements"] = ""
    st.session_state.setup_error = None
    st.session_state.invalid_fields = set()
    st.session_state.setup_step = 3


def back_to_select():
    st.session_state.setup_error = None
    st.session_state.invalid_fields = set()
    st.session_state.company_option = "select"


def advance_to_position_from_custom():
    industry = st.session_state.get("input_industry", INDUSTRY_PLACEHOLDER)
    custom_industry = st.session_state.get("input_custom_industry", "").strip()
    company_name = st.session_state.get("input_custom_company", "").strip()
    job_description = st.session_state.get("input_job_description", "")
    job_requirements = st.session_state.get("input_job_requirements", "")

    missing = set()
    if industry == INDUSTRY_PLACEHOLDER:
        missing.add("input_industry")
    elif industry == OTHER_INDUSTRY_OPTION and not custom_industry:
        # The Target Industry selectbox mirrors the custom industry text
        # input's error state whenever that field is showing.
        missing.add("input_industry")
        missing.add("input_custom_industry")
    if not company_name:
        missing.add("input_custom_company")

    if missing:
        st.session_state.setup_error = REQUIRED_FIELD_ERROR
        st.session_state.invalid_fields = missing
        return

    st.session_state.user_data["company"] = company_name
    st.session_state.user_data["industry"] = (
        custom_industry if industry == OTHER_INDUSTRY_OPTION else industry
    )
    st.session_state.user_data["job_description"] = job_description
    st.session_state.user_data["job_requirements"] = job_requirements
    st.session_state.setup_error = None
    st.session_state.invalid_fields = set()
    st.session_state.setup_step = 3


def select_level(level):
    if st.session_state.user_data["level"] == level:
        st.session_state.user_data["level"] = ""
    else:
        st.session_state.user_data["level"] = level


def complete_setup():
    position = st.session_state.get("input_position", POSITION_PLACEHOLDER)
    custom_position = st.session_state.get("input_custom_position", "").strip()

    missing = set()
    if position == POSITION_PLACEHOLDER:
        missing.add("input_position")
    elif position == OTHER_POSITION_OPTION and not custom_position:
        missing.add("input_position")
        missing.add("input_custom_position")

    if missing:
        st.session_state.setup_error = REQUIRED_FIELD_ERROR
        st.session_state.invalid_fields = missing
        return

    st.session_state.user_data["position"] = (
        custom_position if position == OTHER_POSITION_OPTION else position
    )
    st.session_state.setup_error = None
    st.session_state.invalid_fields = set()
    st.session_state.setup_complete = True


def show_feedback():
    st.session_state.feedback_shown = True


def reset_interview():
    """Reset all interview progress and return to Step 1."""
    st.session_state.setup_complete = False
    st.session_state.setup_step = 1
    st.session_state.company_option = "select"
    st.session_state.chat_complete = False
    st.session_state.awaiting_llm = False
    st.session_state.interview_error = None
    st.session_state.feedback_shown = False
    st.session_state.turns = []
    st.session_state.follow_up_count = 0
    st.session_state.last_turn_was_follow_up = False
    st.session_state.user_data = {
        "name": "",
        "experience": "",
        "skills": "",
        "level": "",
        "position": "",
        "company": "",
        "industry": "",
        "job_description": "",
        "job_requirements": "",
    }
    st.session_state.setup_error = None
    st.session_state.invalid_fields = set()
    st.session_state.usage_totals = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "cost": 0.0,
    }

    # Remove cached feedback and interview setup if they exist
    if "feedback_data" in st.session_state:
        del st.session_state["feedback_data"]
    if "setup_questions" in st.session_state:
        del st.session_state["setup_questions"]
    if "closing_message" in st.session_state:
        del st.session_state["closing_message"]


render_step_indicator(
    st.session_state.feedback_shown,
    st.session_state.setup_complete,
    st.session_state.setup_step,
)

# ---------------------------
# Step 1: Setup Phase (Personal Information → Company → Position)
# ---------------------------
if not st.session_state.setup_complete:
    saved = st.session_state.user_data

    if st.session_state.setup_step == 1:
        with st.form("personal_info_form"):
            st.subheader("Personal Information")
            with st.container(key="step_caption"):
                st.caption(
                    "You're about to practice a mock job interview with an AI interviewer. "
                    "Fill in your name, experience, and skills below so the questions can be "
                    "tailored to you."
                )
            if st.session_state.setup_error:
                with st.container(key="required_field_error"):
                    st.error(st.session_state.setup_error)
                render_invalid_field_borders(st.session_state.invalid_fields)

            st.text_input(
                label="Name *",
                max_chars=40,
                key="input_name",
                value=saved["name"],
                placeholder="Enter your name",
            )
            st.text_area(
                label="Experience *",
                key="input_experience",
                max_chars=200,
                value=saved["experience"],
                placeholder="Describe your experience (e.g. 3 years in software development)",
            )
            st.text_area(
                label="Skills *",
                key="input_skills",
                max_chars=200,
                value=saved["skills"],
                placeholder="List your skills (e.g. Python, Data Analysis, Project Management)",
            )
            with st.container(key="personal_info_next_row"):
                _, next_col = st.columns([5.15, 1])
                with next_col:
                    st.form_submit_button(
                        "Next",
                        type="primary",
                        on_click=advance_to_company,
                        use_container_width=True,
                    )

    elif st.session_state.setup_step == 2 and st.session_state.company_option == "select":
        with st.form("company_select_form"):
            st.subheader("Specific Company")
            with st.container(key="step_caption"):
                st.caption(
                    "Pick the company you're interviewing with so the questions match how it "
                    "actually interviews, or skip this using the options below to practice with "
                    "a generic interview instead."
                )
            if st.session_state.setup_error:
                with st.container(key="required_field_error"):
                    st.error(st.session_state.setup_error)
                render_invalid_field_borders(st.session_state.invalid_fields)

            # Each company is its own clickable container
            render_company_logo_styles(COMPANY_LOGO_FILES)
            if saved["company"] in COMPANY_OPTIONS:
                # Highlight whichever tile the user picked on a previous visit to this
                # screen, so coming back via the stepper shows their prior choice.
                st.markdown(
                    f'<style>.st-key-company_btn_{saved["company"]} button[kind="secondaryFormSubmit"] {{'
                    f"border: 2px solid #0054A3 !important;"
                    f"background-color: rgba(28, 131, 255, 0.10) !important;"
                    f"}}</style>",
                    unsafe_allow_html=True,
                )
            with st.container(key="company_grid"):
                grid_cols = st.columns(2)
                for i, company in enumerate(COMPANY_OPTIONS):
                    with grid_cols[i % 2]:
                        st.form_submit_button(
                            company,
                            key=f"company_btn_{company}",
                            type="secondary",
                            on_click=select_predefined_company,
                            args=(company,),
                            use_container_width=True,
                        )

            st.markdown(
                '<div style="display:flex; align-items:center; justify-content:center; margin: 0.8rem 0;">'
                '<div style="width:180px; height:1px; background:rgba(148,163,184,0.35);"></div>'
                '<span style="padding:0 0.8rem; color:#6b7280; font-size:0.85rem;">or</span>'
                '<div style="width:180px; height:1px; background:rgba(148,163,184,0.35);"></div>'
                "</div>",
                unsafe_allow_html=True,
            )
            custom_col, no_company_col = st.columns([1, 1])
            with custom_col:
                st.form_submit_button(
                    "Create a custom company profile",
                    type="secondary",
                    on_click=go_to_custom_company,
                    use_container_width=True,
                )
            with no_company_col:
                st.form_submit_button(
                    "No target company",
                    type="secondary",
                    on_click=choose_generic_company,
                    use_container_width=True,
                )

    elif st.session_state.setup_step == 2 and st.session_state.company_option == "custom":
        with st.container(key="company_custom_wrapper"):
            st.subheader("Custom Company")
            with st.container(key="step_caption"):
                st.caption(
                    "Tell us the industry and company name — and optionally paste the job "
                    "posting and its requirements — so the interview questions can be tailored "
                    "to this specific role."
                )
            if st.session_state.setup_error:
                with st.container(key="required_field_error"):
                    st.error(st.session_state.setup_error)
                render_invalid_field_borders(st.session_state.invalid_fields)

            # Rendered outside the form below so picking "Other" reveals the
            # follow-up field immediately: st.form only reruns on submit, and
            # Streamlit disallows on_change callbacks on widgets inside a form.
            industry_is_custom = (
                bool(saved["industry"]) and saved["industry"] not in INDUSTRY_OPTIONS
            )
            industry_index = (
                INDUSTRY_OPTIONS.index(OTHER_INDUSTRY_OPTION)
                if industry_is_custom
                else (
                    INDUSTRY_OPTIONS.index(saved["industry"])
                    if saved["industry"] in INDUSTRY_OPTIONS
                    else 0
                )
            )
            st.selectbox(
                "Target Industry *",
                INDUSTRY_OPTIONS,
                index=industry_index,
                key="input_industry",
            )
            if st.session_state.get("input_industry") == OTHER_INDUSTRY_OPTION:
                st.text_input(
                    label="Custom industry",
                    label_visibility="collapsed",
                    max_chars=60,
                    key="input_custom_industry",
                    value=saved["industry"] if industry_is_custom else "",
                    placeholder="Please specify your industry (e.g. Real Estate)",
                )

            with st.form("company_custom_form"):
                st.text_input(
                    label="Company Name *",
                    max_chars=60,
                    key="input_custom_company",
                    value=saved["company"],
                    placeholder="e.g. Google",
                )
                st.text_area(
                    label="Job Description (Optional)",
                    key="input_job_description",
                    max_chars=500,
                    value=saved["job_description"],
                    placeholder="Paste or describe the job posting",
                )
                st.text_area(
                    label="Job Requirements (Optional)",
                    key="input_job_requirements",
                    max_chars=500,
                    value=saved["job_requirements"],
                    placeholder="List specific requirements for the role",
                )

                with st.container(key="custom_company_next_row"):
                    _, back_col, next_col = st.columns([4, 1, 1])
                    with back_col:
                        st.form_submit_button(
                            "Back",
                            type="secondary",
                            on_click=back_to_select,
                            use_container_width=True,
                        )
                    with next_col:
                        st.form_submit_button(
                            "Next",
                            type="primary",
                            on_click=advance_to_position_from_custom,
                            use_container_width=True,
                        )

    elif st.session_state.setup_step == 3:
        with st.container(key="position_wrapper"):
            st.subheader("Position")
            with st.container(key="step_caption"):
                st.caption(
                    "Choose your experience level and the job role you're practicing for — "
                    "this decides how hard the questions are and what topics they cover."
                )
            if st.session_state.setup_error:
                with st.container(key="required_field_error"):
                    st.error(st.session_state.setup_error)
                render_invalid_field_borders(st.session_state.invalid_fields)

            position_is_custom = (
                bool(saved["position"]) and saved["position"] not in POSITION_OPTIONS
            )
            position_index = (
                POSITION_OPTIONS.index(OTHER_POSITION_OPTION)
                if position_is_custom
                else (
                    POSITION_OPTIONS.index(saved["position"])
                    if saved["position"] in POSITION_OPTIONS
                    else 0
                )
            )
            st.selectbox(
                "Choose a position *",
                POSITION_OPTIONS,
                index=position_index,
                key="input_position",
            )
            if st.session_state.get("input_position") == OTHER_POSITION_OPTION:
                st.text_input(
                    label="Custom position",
                    label_visibility="collapsed",
                    max_chars=60,
                    key="input_custom_position",
                    value=saved["position"] if position_is_custom else "",
                    placeholder="Please specify your position (e.g. Product Marketing Manager)",
                )

            level_options = ["Junior", "Mid-level", "Senior"]
            level_highlight_style = ""
            if saved["level"] in level_options:
                # Highlight whichever tile is currently selected
                level_highlight_style = (
                    f'<style>.st-key-level_btn_{saved["level"]} button[kind="secondary"] {{'
                    f"border: 2px solid #0054A3 !important;"
                    f"background-color: rgba(28, 131, 255, 0.10) !important;"
                    f"}}</style>"
                )

            st.markdown(
                '<p style="font-size:14px; font-weight:400; color:rgb(49,51,63); '
                f'margin-bottom:0;">Choose a level (Optional)</p>{level_highlight_style}',
                unsafe_allow_html=True,
            )
            with st.container(key="level_grid"):
                level_cols = st.columns(3)
                for i, level in enumerate(level_options):
                    with level_cols[i]:
                        st.button(
                            level,
                            key=f"level_btn_{level}",
                            type="secondary",
                            on_click=select_level,
                            args=(level,),
                            use_container_width=True,
                        )

            with st.form("position_form"):
                total_questions = prompts.DB_QUESTION_COUNT + prompts.GENERATED_QUESTION_COUNT
                st.caption(
                    f"You'll be asked {total_questions} questions tailored to this role. Takes about 5 minutes."
                )

                _, next_col = st.columns([4, 2])
                with next_col:
                    st.form_submit_button(
                        "Start Interview",
                        type="primary",
                        on_click=complete_setup,
                        use_container_width=True,
                    )

# ---------------------------
# Step 4: Interview Phase
# ---------------------------
if st.session_state.setup_complete and not st.session_state.feedback_shown:
    data = st.session_state.user_data

    # Updated HTML card to include user's Experience and Skills
    company_suffix = f" at <b>{data['company']}</b>" if data["company"] else ""
    level_prefix = f"{data['level']} " if data["level"] else ""
    st.markdown(
        f'<div class="card">'
        f'<img src="{BRIEFCASE_ICON_URI}" style="height:1em; vertical-align:-0.15em; margin-right:4px;"/> '
        f"Interviewing for <b>{level_prefix}{data['position']}</b>{company_suffix}"
        f'<hr style="margin: 8px 0; border: none; border-top: 1px solid #eee;"/>'
        f'<b><img src="{EXPERIENCE_ICON_URI}" style="height:1em; vertical-align:-0.15em; margin-right:4px;"/> '
        f"Experience:</b> {data['experience'] or 'None provided'}<br/>"
        f'<b><img src="{SKILLS_ICON_URI}" style="height:1em; vertical-align:-0.15em; margin-right:4px;"/> '
        f"Skills:</b> {data['skills'] or 'None provided'}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # LLM 1 (Setup): runs once, builds the 6-question set the whole interview draws from.
    if "setup_questions" not in st.session_state:
        client = get_openai_client()
        if client:
            with st.spinner("Preparing your interview questions..."):
                db_questions = question_bank.sample_questions(prompts.DB_QUESTION_COUNT)
                try:
                    completion = parse_with_retry(
                        client,
                        model=prompts.MODEL_NAME,
                        messages=[
                            {
                                "role": "system",
                                "content": prompts.get_setup_prompt(
                                    data["name"],
                                    data["experience"],
                                    data["skills"],
                                    data["level"],
                                    data["position"],
                                    data["company"],
                                    data["industry"],
                                    data["job_description"],
                                    data["job_requirements"],
                                    db_questions,
                                ),
                            }
                        ],
                        temperature=0.7,
                        response_format=SetupResult,
                    )
                    track_usage(completion)
                    message = completion.choices[0].message

                    if message.refusal:
                        logger.warning(
                            "Setup LLM refused to generate questions: %s", message.refusal
                        )
                        st.error(
                            f"Could not prepare interview questions: {message.refusal}", icon="⚠️"
                        )
                    else:
                        st.session_state.setup_questions = [
                            {"category": q.question_category, "text": q.question_text}
                            for q in message.parsed.questions
                        ]
                        st.rerun()
                except openai.AuthenticationError:
                    logger.exception("OpenAI authentication failed during setup.")
                    st.error("Authentication failed. Check your OpenAI API key.", icon="🚨")
                except openai.RateLimitError:
                    logger.exception("OpenAI rate limit hit during setup.")
                    st.error(
                        "Rate limit exceeded or insufficient quota. Please try again later.",
                        icon="⏳",
                    )
                except (openai.APITimeoutError, openai.APIConnectionError):
                    logger.exception("OpenAI network error during setup.")
                    st.error("Network timeout or connectivity issue. Please retry.", icon="📡")
                except openai.LengthFinishReasonError:
                    logger.exception("OpenAI response cut off during setup.")
                    st.error(
                        "The response was cut off before it completed. Please try again.", icon="✂️"
                    )
                except openai.OpenAIError as e:
                    logger.exception("OpenAI API error during setup.")
                    st.error(f"An API error occurred: {e.message}", icon="❌")
    else:
        questions = st.session_state.setup_questions
        total_questions = len(questions)

        if not st.session_state.turns:
            st.session_state.turns = [
                {
                    "category": questions[0]["category"],
                    "predefined_question": questions[0]["text"],
                    "displayed_question": questions[0]["text"],
                    "answer": None,
                    "is_follow_up": False,
                }
            ]

        with st.container(key="feedback_loading_chat"):
            # Render conversation so far
            for turn in st.session_state.turns:
                with st.chat_message("assistant"):
                    st.markdown(turn["displayed_question"])
                if turn["answer"] is not None:
                    with st.chat_message("user"):
                        st.markdown(turn["answer"])

            if "closing_message" in st.session_state:
                with st.chat_message("assistant"):
                    st.markdown(st.session_state.closing_message)

            scroll_chat_to_bottom()

            if st.session_state.chat_complete:
                st.success("Interview complete — nice work! Ready to see how you did?", icon="✅")
                st.button(
                    "Get Feedback", type="primary", on_click=show_feedback, key="btn_feedback"
                )

                scroll_chat_to_bottom()

        if not st.session_state.chat_complete:
            current_index = len(st.session_state.turns) - 1
            current_turn = st.session_state.turns[current_index]
            st.caption(
                f"Question {current_index + 1} of {total_questions} — {current_turn['category']}"
            )

            if st.session_state.interview_error:
                error_message, error_icon = st.session_state.interview_error
                st.error(error_message, icon=error_icon)
                st.session_state.interview_error = None

            # Two-phase submit: capture the answer and rerun once so the browser
            # actually renders the input as disabled before the blocking LLM
            # call starts, rather than disabling and calling the API in the same
            # pass (which would send the disabled state and the response together).
            chat_input_placeholder = (
                "Waiting for the interviewer's response..."
                if st.session_state.awaiting_llm
                else "Your answer."
            )
            prompt = st.chat_input(
                chat_input_placeholder, max_chars=1000, disabled=st.session_state.awaiting_llm
            )
            if prompt and not st.session_state.awaiting_llm:
                current_turn["answer"] = prompt
                st.session_state.awaiting_llm = True
                st.rerun()

            if st.session_state.awaiting_llm:
                client = get_openai_client()
                if not client:
                    st.session_state.awaiting_llm = False
                else:
                    prompt = current_turn["answer"]
                    scroll_chat_to_bottom()

                    next_index = current_index + 1
                    if next_index >= total_questions:
                        # All predefined questions answered — static farewell, no LLM call.
                        st.session_state.closing_message = CLOSING_MESSAGE
                        st.session_state.chat_complete = True
                        st.session_state.awaiting_llm = False
                        st.rerun()
                    else:
                        # LLM 2 (Humanizer): scores the just-given answer and phrases the
                        # next predefined question, given only that one Q/A pair.
                        follow_up_allowed = (
                            st.session_state.follow_up_count < prompts.MAX_FOLLOW_UPS
                            and not st.session_state.last_turn_was_follow_up
                        )
                        with st.chat_message("assistant", avatar="💼"):
                            typing_placeholder = st.empty()
                            typing_placeholder.markdown(
                                '<div class="typing-indicator"><span></span><span></span><span></span></div>',
                                unsafe_allow_html=True,
                            )
                            try:
                                spinner_start = time.monotonic()
                                completion = parse_with_retry(
                                    client,
                                    model=prompts.MODEL_NAME,
                                    messages=[
                                        {
                                            "role": "system",
                                            "content": prompts.get_humanizer_prompt(
                                                current_question=questions[next_index]["text"],
                                                current_category=questions[next_index]["category"],
                                                previous_question=current_turn[
                                                    "predefined_question"
                                                ],
                                                previous_response=prompt,
                                                follow_up_allowed=follow_up_allowed,
                                            ),
                                        }
                                    ],
                                    temperature=0.7,
                                    response_format=HumanizerTurn,
                                )
                                track_usage(completion)
                                remaining = MIN_SPINNER_SECONDS - (time.monotonic() - spinner_start)
                                if remaining > 0:
                                    time.sleep(remaining)
                                typing_placeholder.empty()
                                message = completion.choices[0].message

                                if message.refusal:
                                    logger.warning(
                                        "Humanizer LLM refused to continue: %s", message.refusal
                                    )
                                    st.session_state.interview_error = (
                                        f"The interviewer declined to continue: {message.refusal}",
                                        "⚠️",
                                    )
                                    current_turn["answer"] = None
                                    st.session_state.awaiting_llm = False
                                    st.rerun()
                                else:
                                    humanized = message.parsed
                                    # Defensive clamp: the budget/consecutive-turn rule is
                                    # enforced here, not trusted from the model's own output.
                                    is_follow_up = humanized.is_follow_up and follow_up_allowed
                                    st.markdown(humanized.message)
                                    scroll_chat_to_bottom()
                                    st.session_state.turns.append(
                                        {
                                            "category": questions[next_index]["category"],
                                            "predefined_question": questions[next_index]["text"],
                                            "displayed_question": humanized.message,
                                            "answer": None,
                                            "is_follow_up": is_follow_up,
                                        }
                                    )
                                    st.session_state.follow_up_count += 1 if is_follow_up else 0
                                    st.session_state.last_turn_was_follow_up = is_follow_up
                                    st.session_state.awaiting_llm = False
                                    st.rerun()
                            except openai.AuthenticationError:
                                logger.exception(
                                    "OpenAI authentication failed during interview turn."
                                )
                                typing_placeholder.empty()
                                st.session_state.interview_error = (
                                    "Authentication failed. Check your OpenAI API key.",
                                    "🚨",
                                )
                                current_turn["answer"] = None
                                st.session_state.awaiting_llm = False
                                st.rerun()
                            except openai.RateLimitError:
                                logger.exception("OpenAI rate limit hit during interview turn.")
                                typing_placeholder.empty()
                                st.session_state.interview_error = (
                                    "Rate limit exceeded or insufficient quota. Please try again later.",
                                    "⏳",
                                )
                                current_turn["answer"] = None
                                st.session_state.awaiting_llm = False
                                st.rerun()
                            except (openai.APITimeoutError, openai.APIConnectionError):
                                logger.exception("OpenAI network error during interview turn.")
                                typing_placeholder.empty()
                                st.session_state.interview_error = (
                                    "Network timeout or connectivity issue. Please retry.",
                                    "📡",
                                )
                                current_turn["answer"] = None
                                st.session_state.awaiting_llm = False
                                st.rerun()
                            except openai.LengthFinishReasonError:
                                logger.exception("OpenAI response cut off during interview turn.")
                                typing_placeholder.empty()
                                st.session_state.interview_error = (
                                    "The interviewer's response was cut off before it completed. "
                                    "Please try again.",
                                    "✂️",
                                )
                                current_turn["answer"] = None
                                st.session_state.awaiting_llm = False
                                st.rerun()
                            except openai.OpenAIError as e:
                                logger.exception("OpenAI API error during interview turn.")
                                typing_placeholder.empty()
                                st.session_state.interview_error = (
                                    f"An API error occurred: {e.message}",
                                    "❌",
                                )
                                current_turn["answer"] = None
                                st.session_state.awaiting_llm = False
                                st.rerun()

# ---------------------------
# Step 5: Feedback Phase
# ---------------------------
if st.session_state.feedback_shown:
    st.markdown(
        "<style>.st-key-feedback_loading_chat { display: none !important; }</style>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<h3><img src="{FEEDBACK_ICON_URI}" style="height:1em; vertical-align:-0.15em; margin-right:4px;"/> '
        f"Feedback</h3>",
        unsafe_allow_html=True,
    )
    with st.container(key="feedback_step_caption"):
        st.caption(
            "Here's how you did: a score and critique for each answer, plus your overall "
            "strengths and areas to improve."
        )

    if "feedback_data" not in st.session_state:
        feedback_client = get_openai_client()

        if feedback_client:
            conversation_history = "\n".join(
                f"interviewer [{turn['category']}]: {turn['displayed_question']}\nuser: {turn['answer']}"
                for turn in st.session_state.turns
            )

            with st.spinner("Reviewing your answers..."):
                try:
                    feedback_completion = parse_with_retry(
                        feedback_client,
                        model=prompts.MODEL_NAME,
                        messages=[
                            {"role": "system", "content": prompts.EVALUATION_SYSTEM_PROMPT},
                            {
                                "role": "user",
                                "content": prompts.get_evaluation_user_prompt(conversation_history),
                            },
                        ],
                        temperature=0.2,
                        top_p=0.9,
                        response_format=InterviewEvaluation,
                    )
                    track_usage(feedback_completion)
                    message = feedback_completion.choices[0].message

                    # Structured outputs adds a failure mode .create() didn't have:
                    # the model can decline to answer instead of returning the schema.
                    if message.refusal:
                        logger.warning(
                            "Evaluation LLM refused to generate feedback: %s", message.refusal
                        )
                        st.error(
                            f"The model declined to generate feedback: {message.refusal}", icon="⚠️"
                        )
                    else:
                        evaluation = message.parsed
                        # We already know each question's real category from LLM 1 — use
                        # that ground truth instead of trusting the evaluator to re-derive it.
                        for q_eval, turn in zip(
                            evaluation.questions, st.session_state.turns, strict=False
                        ):
                            q_eval.topic = turn["category"]
                        st.session_state.feedback_data = evaluation

                except openai.AuthenticationError:
                    logger.exception("OpenAI authentication failed during evaluation.")
                    st.error(
                        "Authentication failed while fetching evaluation. Check API key.", icon="🚨"
                    )
                except openai.RateLimitError:
                    logger.exception("OpenAI rate limit hit during evaluation.")
                    st.error(
                        "Rate limit hit during evaluation. Please try again shortly.", icon="⏳"
                    )
                except (openai.APITimeoutError, openai.APIConnectionError):
                    logger.exception("OpenAI network error during evaluation.")
                    st.error("Network timeout during feedback generation.", icon="📡")
                except openai.LengthFinishReasonError:
                    logger.exception("OpenAI response cut off during evaluation.")
                    st.error(
                        "The evaluation response was cut off before it completed. Please try again.",
                        icon="✂️",
                    )
                except openai.OpenAIError as e:
                    logger.exception("OpenAI API error during evaluation.")
                    st.error(
                        f"Failed to generate feedback due to an API error: {e.message}", icon="❌"
                    )

    if "feedback_data" in st.session_state:
        evaluation = st.session_state.feedback_data

        render_score_overview(evaluation)
        render_evaluation(evaluation, st.session_state.turns)

        st.button("Restart Interview", type="primary", on_click=reset_interview, key="btn_restart")
