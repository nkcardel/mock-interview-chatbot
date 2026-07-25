# Mock Job Interview Chatbot

A Streamlit interview-practice chatbot with structured-output scoring and a dedicated LLM evaluation suite — built with the OpenAI API, Pydantic, and pytest.

## 📌 Project Overview

This app runs a candidate through a role-specific mock interview (tailored to their stated experience, skill set, seniority level, and target company), then scores the transcript question-by-question using OpenAI **structured outputs** rather than parsing free-form model text.

Beyond the app itself, the project includes a separate **evaluation suite** that tests the interviewer and grader's *behavior*, not just the code — using an LLM-as-judge to check whether generated questions stay on-topic and level-appropriate, and a variance test to check whether the grader scores an identical transcript consistently across repeated runs.

## 🧾 Background

This project began from a course exercise (a basic Streamlit mock-interview chatbot) and has been substantially extended since. What's original to this repo:

- **Eval suite** (`test_evals.py`, `eval_cache.py`) — LLM-as-judge tests that check whether interview questions stay on-topic and appropriately scoped for the candidate's seniority level, plus a grader-consistency test that measures scoring variance across repeated runs on an identical transcript.
- **Disk-based response caching** — API calls in the eval suite are cached by a hash of their full payload (model, prompt, temperature, run index), so the suite replays for free and deterministically after the first live run, with an `EVAL_CACHE_REFRESH` env var to force fresh recordings.
- **Structured outputs** (`schemas.py`) — feedback generation uses `response_format` with a Pydantic schema instead of parsing markdown, with defensive score clamping since schema conformance doesn't guarantee the value lands in the intended numeric range.
- **Granular error handling** — auth, rate-limit, timeout, and other API errors are caught and surfaced separately in the UI rather than one blanket exception handler.

## 🛠️ Libraries Used

- **LLM:** `openai` (Chat Completions API, streaming, structured outputs via `.beta.chat.completions.parse`)
- **UI:** `streamlit`
- **Schema / validation:** `pydantic`
- **Testing:** `pytest` (custom `model_eval` marker for API-calling tests)

## 🚀 Key Implementation Steps

**1. Setup → Interview → Feedback flow**

- Three-step session-state machine (`setup_complete`, `chat_complete`, `feedback_shown`) drives which screen renders, with a step-indicator progress bar (`ui.py`).
- Candidate profile (name, experience, skills, level, position, company) is collected via a form and used to build a tailored system prompt (`prompts.get_interviewer_system_prompt`).

**2. Streaming interview turns**

- Each candidate answer is appended to `st.session_state.messages` and sent to the model with `stream=True`, rendered live via `st.write_stream`.
- On the final question, a `CLOSING_REMARK_PROMPT` system message is appended so the model wraps up instead of asking another question.
- API failures (`AuthenticationError`, `RateLimitError`, timeout/connection errors, generic `OpenAIError`) are each caught and surfaced with a distinct, user-facing message; the failed turn is popped off history so the conversation state stays consistent.

**3. Structured-output feedback (`schemas.py`)**

- `InterviewEvaluation` (a Pydantic model) defines a per-question `QuestionEvaluation` list plus overall strengths, areas for improvement, an overall score, and a final verdict.
- Passed as `response_format` to `client.beta.chat.completions.parse`, which guarantees the response matches the schema — no regex-parsing markdown, no missing fields.
- Structured outputs guarantee *shape*, not *range*: `overall_score` is guaranteed to be a float, not guaranteed to fall in `[0, 10]`, so `clamped_overall_score()` defensively clamps it before display.
- The API can also return a `refusal` instead of a parsed result; this is checked explicitly rather than assumed away.

**4. Evaluation suite (`test_evals.py`, `eval_cache.py`)**

- `test_interviewer_stays_on_topic` — runs a simulated 3-turn interview per fixed candidate profile, then uses a second LLM call (`QuestionJudgement`, also a structured output) to judge whether each generated question was topically relevant and level-appropriate.
- `test_grader_score_consistency` — runs the grader against one fixed transcript 5 times and asserts the score spread stays within a tolerance, to catch cases where the evaluator's scoring drifts across identical inputs.
- Every live API call in the suite is routed through `cached_call(name, payload, live_fn)`, which hashes the full call payload (model, prompt/messages, temperature, and any intentional per-run variation like `run_index`) and replays a recorded JSON result on cache hit — so the suite only costs money and varies non-deterministically on the *first* run, and is free and reproducible after that. `EVAL_CACHE_REFRESH=1` forces fresh recordings when prompts change.
- Marked with a custom `model_eval` pytest marker and excluded from the default test run, since these tests call a paid, non-deterministic API.

## 📊 Feature Summary

| Area | What it does |
| --- | --- |
| Interview generation | Role/level/company-tailored system prompt, streamed responses |
| Feedback scoring | Structured-output (schema-guaranteed) per-question + overall evaluation |
| Error handling | Distinct handling for auth, rate-limit, timeout, and generic API errors |
| Eval suite | LLM-as-judge topic/level checks + grader score-consistency variance test |
| Cost control | Disk-based cache keyed on full call payload, with forced-refresh option |

## 📂 Repository Structure

```
├── app.py                 # Streamlit app — setup, interview, and feedback flow
├── ui.py                  # Custom CSS, header, step indicator, evaluation rendering
├── prompts.py             # System prompts and interview constants
├── schemas.py             # Pydantic schemas for structured-output evaluation
├── eval_cache.py          # Disk-based cache for eval-suite API calls
├── test_evals.py          # LLM-as-judge + grader-consistency eval suite (pytest, model_eval marker)
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Project metadata, pytest marker config
├── .gitignore
└── README.md
```

## 🔭 Future Enhancements

### Interview setup options
Currently the app builds one tailored system prompt per session. Planned setup
flow will let the user pick between three modes:
1. **Select a company** — choose from a curated list of companies, each with
   its own set of interview questions.
2. **Custom company** — define a company and specific requirements, and have
   the interview generated around that context.
3. **No company in mind** — run a generic, role-based interview with no
   company-specific framing.

### HR interview question categories
HR-track interviews will draw from five distinct question categories rather
than a single undifferentiated pool:
1. Background questions
2. Technical knowledge questions
3. Situational questions
4. Brain teaser questions
5. Analytical questions

### Enhanced feedback screen
The feedback screen will move beyond a single overall score to a fuller
evaluation:
- **Five scored metrics**: an overall score, plus four criteria — role-related
  knowledge, problem-solving skills, communication skills, and workplace
  culture fit — with the specific criteria weighting varying depending on
  whether the interviewer was HR or technical.
- **Text summary**, covering:
  1. Overall performance
  2. Areas for improvement
  3. A detailed, question-by-question evaluation with key takeaways

## 👩‍💻 How to Run

1. Clone this repository
2. Create and activate a virtual environment, then install requirements:
   ```
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```
3. Add your OpenAI API key to Streamlit secrets — create `.streamlit/secrets.toml` in the project root:
   ```
   OPENAI_API_KEY = "your_key_here"
   ```
4. Run the app:
   ```
   streamlit run app.py
   ```

## 🧪 Running the Eval Suite

The eval suite calls the OpenAI API and is excluded from a plain `pytest` run. Run it explicitly:

```
$env:OPENAI_API_KEY = "your_key_here"   # PowerShell
pytest test_evals.py -v -m model_eval
```

> Note: this only sets the variable for the current terminal session — you'll need to set it again each time you open a new one. For cmd.exe instead of PowerShell, use `set OPENAI_API_KEY=your_key_here`.

First run records live API responses to `.eval_cache/` (not committed — see `.gitignore`); subsequent runs replay from cache for free. Set `EVAL_CACHE_REFRESH=1` to force fresh recordings, e.g. after changing `prompts.py`.

---

**Developed by:**   
Nicole Kaye A. Cardel    
nkcardel@gmail.com  
*Software Designer & Developer*
