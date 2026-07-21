import openai
from openai import OpenAI
import streamlit as st

import prompts
from schemas import InterviewEvaluation
from ui import apply_custom_styles, render_evaluation, render_header, render_score_badge, render_step_indicator

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
if "user_message_count" not in st.session_state:
    st.session_state.user_message_count = 0
if "feedback_shown" not in st.session_state:
    st.session_state.feedback_shown = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_complete" not in st.session_state:
    st.session_state.chat_complete = False

# Initialize form defaults in session state
for key, default in [
    ("name", ""),
    ("experience", ""),
    ("skills", ""),
    ("level", "Junior"),
    ("position", "Data Scientist"),
    ("company", "Amazon"),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# Store finalized values safely outside form widget lifecycle
if "user_data" not in st.session_state:
    st.session_state.user_data = {
        "name": "",
        "experience": "",
        "skills": "",
        "level": "Junior",
        "position": "Data Scientist",
        "company": "Amazon",
    }


def complete_setup():
    # Save widget inputs into user_data dictionary upon submit
    st.session_state.user_data = {
        "name": st.session_state.get("input_name", ""),
        "experience": st.session_state.get("input_experience", ""),
        "skills": st.session_state.get("input_skills", ""),
        "level": st.session_state.get("input_level", "Junior"),
        "position": st.session_state.get("input_position", "Data Scientist"),
        "company": st.session_state.get("input_company", "Amazon"),
    }
    st.session_state.setup_complete = True


def show_feedback():
    st.session_state.feedback_shown = True


def reset_interview():
    """Reset all interview progress and return to Step 1."""
    st.session_state.setup_complete = False
    st.session_state.chat_complete = False
    st.session_state.feedback_shown = False
    st.session_state.user_message_count = 0
    st.session_state.messages = []
    
    # Remove cached feedback if it exists
    if "feedback_data" in st.session_state:
        del st.session_state["feedback_data"]


render_step_indicator(
    st.session_state.feedback_shown,
    st.session_state.setup_complete,
    st.session_state.chat_complete,
)

# ---------------------------
# Step 1: Setup Phase
# ---------------------------
if not st.session_state.setup_complete:
    with st.form("setup_form"):
        st.subheader("Personal Information")

        st.text_input(
            label="Name",
            max_chars=40,
            key="input_name",
            placeholder="Enter your name",
        )
        st.text_area(
            label="Experience",
            key="input_experience",
            max_chars=200,
            placeholder="Describe your experience",
        )
        st.text_area(
            label="Skills",
            key="input_skills",
            max_chars=200,
            placeholder="List your skills",
        )
        st.markdown("<hr/>", unsafe_allow_html=True)
        st.subheader("Company and Position")

        col1, col2 = st.columns(2)
        with col1:
            st.radio(
                "Choose level",
                key="input_level",
                options=["Junior", "Mid-level", "Senior"],
            )
        with col2:
            st.selectbox(
                "Choose a position",
                (
                    "Data Scientist",
                    "Data Engineer",
                    "AI Strategist",
                    "AI Developer",
                    "AI Engineer",
                    "ML Engineer",
                    "BI Analyst",
                    "Financial Analyst",
                ),
                key="input_position",
            )

        st.selectbox(
            "Choose a company",
            ("Amazon", "Meta", "Udemy", "365 Company", "Nestle", "LinkedIn", "Spotify"),
            key="input_company",
        )

        st.caption(f"You'll be asked {prompts.MAX_QUESTIONS} questions tailored to this role. Takes about 5 minutes.")
        st.form_submit_button("Start Interview →", type="primary", on_click=complete_setup)

# ---------------------------
# Step 2: Interview Phase
# ---------------------------
if st.session_state.setup_complete and not st.session_state.feedback_shown:
    data = st.session_state.user_data

    # Updated HTML card to include user's Experience and Skills
    st.markdown(
        f'<div class="card">'
        f'💼 Interviewing for <b>{data["level"]} {data["position"]}</b> at <b>{data["company"]}</b>'
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
        st.button("Get Feedback →", type="primary", on_click=show_feedback, key="btn_feedback")

# ---------------------------
# Step 3: Feedback Phase
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