import openai
from openai import OpenAI
import streamlit as st

import prompts
from schemas import InterviewEvaluation
from ui import (
    apply_custom_styles,
    render_company_logo_styles,
    render_evaluation,
    render_header,
    render_invalid_field_borders,
    render_score_badge,
    render_step_indicator,
)

# ---------------------------
# Page Config & Initial Setup
# ---------------------------
st.set_page_config(
    page_title="Mock Interview Chatbot",
    page_icon="🤖",
    layout="centered",
)

apply_custom_styles()
render_header()


def get_openai_client():
    """Safely initialize OpenAI client checking for secrets."""
    api_key = st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        st.error("Missing OpenAI API Key. Please add `OPENAI_API_KEY` to your Streamlit secrets.", icon="🔑")
        return None
    return OpenAI(api_key=api_key)


# ---------------------------
# Session State Initialization
# ---------------------------
if "setup_complete" not in st.session_state:
    st.session_state.setup_complete = False
if "setup_step" not in st.session_state:
    st.session_state.setup_step = 1
if "company_option" not in st.session_state:
    st.session_state.company_option = "select"
if "user_message_count" not in st.session_state:
    st.session_state.user_message_count = 0
if "feedback_shown" not in st.session_state:
    st.session_state.feedback_shown = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_complete" not in st.session_state:
    st.session_state.chat_complete = False
if "setup_error" not in st.session_state:
    st.session_state.setup_error = None
if "invalid_fields" not in st.session_state:
    st.session_state.invalid_fields = set()

# Store finalized values safely outside form widget lifecycle
if "user_data" not in st.session_state:
    st.session_state.user_data = {
        "name": "",
        "experience": "",
        "skills": "",
        "level": "Junior",
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
    st.session_state.user_data["industry"] = custom_industry if industry == OTHER_INDUSTRY_OPTION else industry
    st.session_state.user_data["job_description"] = job_description
    st.session_state.user_data["job_requirements"] = job_requirements
    st.session_state.setup_error = None
    st.session_state.invalid_fields = set()
    st.session_state.setup_step = 3


def complete_setup():
    position = st.session_state.get("input_position", POSITION_PLACEHOLDER)
    st.session_state.user_data["level"] = st.session_state.get("input_level", "Junior")
    st.session_state.user_data["position"] = "" if position == POSITION_PLACEHOLDER else position

    if position == POSITION_PLACEHOLDER:
        st.session_state.setup_error = REQUIRED_FIELD_ERROR
        st.session_state.invalid_fields = {"input_position"}
        return

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
    st.session_state.feedback_shown = False
    st.session_state.user_message_count = 0
    st.session_state.messages = []
    st.session_state.user_data = {
        "name": "",
        "experience": "",
        "skills": "",
        "level": "Junior",
        "position": "",
        "company": "",
        "industry": "",
        "job_description": "",
        "job_requirements": "",
    }
    st.session_state.setup_error = None
    st.session_state.invalid_fields = set()

    # Remove cached feedback if it exists
    if "feedback_data" in st.session_state:
        del st.session_state["feedback_data"]


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
                placeholder="Describe your experience",
            )
            st.text_area(
                label="Skills *",
                key="input_skills",
                max_chars=200,
                value=saved["skills"],
                placeholder="List your skills",
            )
            with st.container(key="personal_info_next_row"):
                _, next_col = st.columns([5.15, 1])
                with next_col:
                    st.form_submit_button(
                        "Next", type="primary", on_click=advance_to_company, use_container_width=True
                    )

    elif st.session_state.setup_step == 2 and st.session_state.company_option == "select":
        with st.form("company_select_form"):
            st.subheader("Specific Company")
            st.caption("Click a company to continue.")
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
                    f'border: 2px solid #0054A3 !important;'
                    f'background-color: rgba(28, 131, 255, 0.10) !important;'
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
                '</div>',
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
            st.caption("Create a specific company profile.")
            if st.session_state.setup_error:
                with st.container(key="required_field_error"):
                    st.error(st.session_state.setup_error)
                render_invalid_field_borders(st.session_state.invalid_fields)

            # Rendered outside the form below so picking "Other" reveals the
            # follow-up field immediately: st.form only reruns on submit, and
            # Streamlit disallows on_change callbacks on widgets inside a form.
            industry_is_custom = bool(saved["industry"]) and saved["industry"] not in INDUSTRY_OPTIONS
            industry_index = (
                INDUSTRY_OPTIONS.index(OTHER_INDUSTRY_OPTION)
                if industry_is_custom
                else (INDUSTRY_OPTIONS.index(saved["industry"]) if saved["industry"] in INDUSTRY_OPTIONS else 0)
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
                            "Back", type="secondary", on_click=back_to_select, use_container_width=True
                        )
                    with next_col:
                        st.form_submit_button(
                            "Next",
                            type="primary",
                            on_click=advance_to_position_from_custom,
                            use_container_width=True,
                        )

    elif st.session_state.setup_step == 3:
        with st.form("position_form"):
            st.subheader("Position")
            if st.session_state.setup_error:
                with st.container(key="required_field_error"):
                    st.error(st.session_state.setup_error)
                render_invalid_field_borders(st.session_state.invalid_fields)

            col1, col2 = st.columns(2)
            with col1:
                level_options = ["Junior", "Mid-level", "Senior"]
                st.radio(
                    "Choose a level",
                    key="input_level",
                    options=level_options,
                    index=level_options.index(saved["level"]),
                )
            with col2:
                position_options = (
                    POSITION_PLACEHOLDER,
                    "Data Scientist",
                    "Data Engineer",
                    "AI Strategist",
                    "AI Developer",
                    "AI Engineer",
                    "ML Engineer",
                    "BI Analyst",
                    "Financial Analyst",
                )
                position_index = (
                    position_options.index(saved["position"]) if saved["position"] in position_options else 0
                )
                st.selectbox(
                    "Choose a position *",
                    position_options,
                    index=position_index,
                    key="input_position",
                )

            st.caption(f"You'll be asked {prompts.MAX_QUESTIONS} questions tailored to this role. Takes about 5 minutes.")

            _, next_col = st.columns([5, 1.5])
            with next_col:
                st.form_submit_button(
                    "Start Interview", type="primary", on_click=complete_setup, use_container_width=True
                )

# ---------------------------
# Step 4: Interview Phase
# ---------------------------
if st.session_state.setup_complete and not st.session_state.feedback_shown:
    data = st.session_state.user_data

    # Updated HTML card to include user's Experience and Skills
    company_suffix = f' at <b>{data["company"]}</b>' if data["company"] else ""
    st.markdown(
        f'<div class="card">'
        f'💼 Interviewing for <b>{data["level"]} {data["position"]}</b>{company_suffix}'
        f'<hr style="margin: 8px 0; border: none; border-top: 1px solid #eee;"/>'
        f'<b>🧠 Experience:</b> {data["experience"] or "None provided"}<br/>'
        f'<b>🛠️ Skills:</b> {data["skills"] or "None provided"}'
        f'</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.messages:
        st.info("Start by introducing yourself.", icon="👋")
        # Seed chat history with System Prompt
        st.session_state.messages = [
            {
                "role": "system",
                "content": prompts.get_interviewer_system_prompt(
                    data["name"],
                    data["experience"],
                    data["skills"],
                    data["level"],
                    data["position"],
                    data["company"],
                    data["industry"],
                    data["job_description"],
                    data["job_requirements"],
                ),
            }
        ]

    # Render previous messages
    for message in st.session_state.messages:
        if message["role"] != "system":
            avatar = "💼" if message["role"] == "assistant" else "🙋"
            with st.chat_message(message["role"], avatar=avatar):
                st.markdown(message["content"])

    # Chat execution logic
    if not st.session_state.chat_complete and st.session_state.user_message_count <= prompts.MAX_QUESTIONS:
        if st.session_state.user_message_count < prompts.MAX_QUESTIONS:
            st.caption(f"Question {st.session_state.user_message_count + 1} of {prompts.MAX_QUESTIONS}")
        else:
            st.caption("Wrapping up")

        if prompt := st.chat_input("Your answer.", max_chars=1000):
            client = get_openai_client()
            if client:
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user", avatar="🙋"):
                    st.markdown(prompt)

                api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

                # Closing remark request on the final turn
                if st.session_state.user_message_count >= prompts.MAX_QUESTIONS:
                    api_messages.append({"role": "system", "content": prompts.CLOSING_REMARK_PROMPT})

                with st.chat_message("assistant", avatar="💼"):
                    try:
                        stream = client.chat.completions.create(
                            model=prompts.MODEL_NAME,
                            messages=api_messages,
                            temperature=0.7,
                            top_p=0.9,
                            presence_penalty=0.2,
                            frequency_penalty=0.1,
                            stream=True,
                        )
                        response = st.write_stream(stream)
                        st.session_state.messages.append({"role": "assistant", "content": response})

                        st.session_state.user_message_count += 1

                        if st.session_state.user_message_count > prompts.MAX_QUESTIONS:
                            st.session_state.chat_complete = True

                        st.rerun()
                    except openai.AuthenticationError:
                        st.error("Authentication failed. Check your OpenAI API key.", icon="🚨")
                        st.session_state.messages.pop()
                    except openai.RateLimitError:
                        st.error("Rate limit exceeded or insufficient quota. Please try again later.", icon="⏳")
                        st.session_state.messages.pop()
                    except (openai.APITimeoutError, openai.APIConnectionError):
                        st.error("Network timeout or connectivity issue. Please retry.", icon="📡")
                        st.session_state.messages.pop()
                    except openai.OpenAIError as e:
                        st.error(f"An API error occurred: {e.message}", icon="❌")
                        st.session_state.messages.pop()

    elif st.session_state.chat_complete:
        st.success("Interview complete — nice work! Ready to see how you did?", icon="✅")
        st.button("Get Feedback", type="primary", on_click=show_feedback, key="btn_feedback")

# ---------------------------
# Step 5: Feedback Phase
# ---------------------------
if st.session_state.feedback_shown:
    st.subheader("📋 Feedback")

    if "feedback_data" not in st.session_state:
        feedback_client = get_openai_client()

        if feedback_client:
            conversation_history = "\n".join(
                [f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages]
            )

            with st.spinner("Reviewing your answers..."):
                try:
                    feedback_completion = feedback_client.beta.chat.completions.parse(
                        model=prompts.MODEL_NAME,
                        messages=[
                            {"role": "system", "content": prompts.EVALUATION_SYSTEM_PROMPT},
                            {"role": "user", "content": prompts.get_evaluation_user_prompt(conversation_history)},
                        ],
                        temperature=0.2,
                        top_p=0.9,
                        response_format=InterviewEvaluation,
                    )
                    message = feedback_completion.choices[0].message

                    # Structured outputs adds a failure mode .create() didn't have:
                    # the model can decline to answer instead of returning the schema.
                    if message.refusal:
                        st.error(f"The model declined to generate feedback: {message.refusal}", icon="⚠️")
                    else:
                        st.session_state.feedback_data = message.parsed

                except openai.AuthenticationError:
                    st.error("Authentication failed while fetching evaluation. Check API key.", icon="🚨")
                except openai.RateLimitError:
                    st.error("Rate limit hit during evaluation. Please try again shortly.", icon="⏳")
                except (openai.APITimeoutError, openai.APIConnectionError):
                    st.error("Network timeout during feedback generation.", icon="📡")
                except openai.LengthFinishReasonError:
                    st.error("The evaluation response was cut off before it completed. Please try again.", icon="✂️")
                except openai.OpenAIError as e:
                    st.error(f"Failed to generate feedback due to an API error: {e.message}", icon="❌")

    if "feedback_data" in st.session_state:
        evaluation = st.session_state.feedback_data

        render_score_badge(evaluation.clamped_overall_score())
        render_evaluation(evaluation)

        st.markdown("---")
        st.button("Restart Interview", type="primary", on_click=reset_interview, key="btn_restart")