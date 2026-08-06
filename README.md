# Mock Job Interview Chatbot

A Streamlit interview-practice chatbot with structured-output scoring and a dedicated LLM evaluation suite — built with the OpenAI API, Pydantic, and pytest.

## 📌 Project Overview

This app runs a candidate through a role-specific mock interview (tailored to their stated experience, skill set, seniority level, and target company), then scores the transcript question-by-question using OpenAI **structured outputs** rather than parsing free-form model text.

Beyond the app itself, the project includes a separate **evaluation suite** that tests the interviewer and grader's *behavior*, not just the code — using an LLM-as-judge to check whether generated questions stay on-topic and level-appropriate, and a variance test to check whether the grader scores an identical transcript consistently across repeated runs.

## 🧾 Background

This project began from a course exercise (a basic Streamlit mock-interview chatbot) and has been substantially extended since. What's original to this repo:

- **Eval suite** (`tests/test_evals.py`, `eval_cache.py`) — LLM-as-judge tests that check whether interview questions stay on-topic and appropriately scoped for the candidate's seniority level, plus a grader-consistency test that measures scoring variance across repeated runs on an identical transcript.
- **Unit test suite** (`tests/test_schemas.py`, `tests/test_question_bank.py`, `tests/test_app_setup_flow.py`) — deterministic, no-network tests for score clamping, question sampling, and the setup-step state machine (steps 1-3 of `app.py`), the latter driven with Streamlit's `AppTest` harness against the real widget callbacks.
- **Disk-based response caching** — API calls in the eval suite are cached by a hash of their full payload (model, prompt, temperature, run index), so the suite replays for free and deterministically after the first live run, with an `EVAL_CACHE_REFRESH` env var to force fresh recordings.
- **Structured outputs** (`schemas.py`) — feedback generation uses `response_format` with a Pydantic schema instead of parsing markdown, with defensive score clamping since schema conformance doesn't guarantee the value lands in the intended numeric range.
- **Granular error handling** — auth, rate-limit, timeout, and other API errors are caught and surfaced separately in the UI rather than one blanket exception handler.

## 🛠️ Libraries Used

- **LLM:** `openai` (Chat Completions API, structured outputs via `.beta.chat.completions.parse`)
- **UI:** `streamlit`
- **Schema / validation:** `pydantic`
- **Testing:** `pytest`, Streamlit's `AppTest` harness for widget-driven state-machine tests (custom `model_eval` marker for API-calling tests)

## 🚀 Key Implementation Steps

**1. Setup → Interview → Feedback flow**

- Three-step session-state machine (`setup_complete`, `chat_complete`, `feedback_shown`) drives which screen renders, with a step-indicator progress bar (`ui.py`).
- Candidate profile (name, experience, skills, level, position, company) is collected via a form and used to build the tailored Setup prompt (`prompts.get_setup_prompt`) described below.

**2. Setup → Humanizer two-LLM interview pipeline**

- LLM 1 (Setup, `prompts.get_setup_prompt`) runs once at interview start and generates a fixed set of six questions — 2 sampled from a local question bank, 4 freshly generated — each tagged with a category (`SetupResult`): Background, Technical Knowledge, Situational, Brain Teaser, or Analytical.
- LLM 2 (Humanizer, `prompts.get_humanizer_prompt`) runs after each answer, scoring that single answer and phrasing the next predefined question — optionally as a natural follow-up on the candidate's previous response (`HumanizerTurn`, capped by `MAX_FOLLOW_UPS`).
- The chat input disables itself (with a "Waiting for the interviewer's response..." placeholder) while a Humanizer call is in flight, via a two-phase submit that reruns once to render the disabled state before the blocking API call starts.
- API failures (`AuthenticationError`, `RateLimitError`, timeout/connection errors, refusals, generic `OpenAIError`) are each caught and surfaced with a distinct, user-facing message that persists across the rerun that re-enables the input, so the turn stays retryable.

**3. Structured-output feedback (`schemas.py`)**

- `InterviewEvaluation` defines a per-question `QuestionEvaluation` list (score, critique, and 1-3 key takeaways) plus an overall score, four independently-scored supporting criteria — Communication, Depth & Substance, Problem-Solving, Role Fit — an `overall_summary`, top strengths, and areas for improvement.
- Passed as `response_format` to `client.beta.chat.completions.parse`, which guarantees the response matches the schema — no regex-parsing markdown, no missing fields.
- Structured outputs guarantee *shape*, not *range*: scores are guaranteed to be floats, not guaranteed to fall in `[0, 10]`, so a shared `_clamp` helper defensively clamps all five before display (`clamped_overall_score()`, `criteria_scores()`).
- The API can also return a `refusal` instead of a parsed result; this is checked explicitly rather than assumed away.
- The feedback screen renders this as a circular overall-score ring plus a 2x2 grid of criterion bars, and a collapsible per-question accordion (topic, question, a mini score ring, the candidate's answer, and key takeaways).

**4. Evaluation suite (`tests/test_evals.py`, `eval_cache.py`)**

- `test_setup_questions_stay_on_topic` — runs a simulated 3-turn interview per fixed candidate profile, then uses a second LLM call (`QuestionJudgement`, also a structured output) to judge whether each generated question was topically relevant and level-appropriate.
- `test_grader_score_consistency` — runs the grader against one fixed transcript 5 times and asserts the score spread stays within a tolerance, to catch cases where the evaluator's scoring drifts across identical inputs.
- Every live API call in the suite is routed through `cached_call(name, payload, live_fn)`, which hashes the full call payload (model, prompt/messages, temperature, and any intentional per-run variation like `run_index`) and replays a recorded JSON result on cache hit — so the suite only costs money and varies non-deterministically on the *first* run, and is free and reproducible after that. `EVAL_CACHE_REFRESH=1` forces fresh recordings when prompts change.
- Marked with a custom `model_eval` pytest marker and excluded from the default test run, since these tests call a paid, non-deterministic API.

**5. Unit tests (`tests/test_schemas.py`, `tests/test_question_bank.py`, `tests/test_app_setup_flow.py`)**

- `test_schemas.py` — covers `_clamp()`'s boundary behavior and `InterviewEvaluation.clamped_overall_score()` / `criteria_scores()`.
- `test_question_bank.py` — covers `sample_questions()`'s count, no-replacement sampling, and over-request behavior against the local question bank.
- `test_app_setup_flow.py` — drives the setup-step state machine (personal info → company → position, validation errors, back-navigation via the stepper, and reset) through Streamlit's `AppTest` harness, which runs `app.py`'s real widgets and `on_click` callbacks without a live server or network call.
- These run under the default `pytest` invocation (no marker, no API key needed) — see [Running the unit tests](#-running-the-unit-tests).

## 📊 Feature Summary

| Area | What it does |
| --- | --- |
| Interview generation | Role/level/company-tailored questions via a Setup + Humanizer LLM pipeline, with optional natural follow-ups |
| Feedback scoring | Structured-output per-question score + key takeaways, plus an overall score and four supporting criteria (communication, depth, problem-solving, role fit) |
| Feedback UI | Circular score rings, segmented criteria bars, and a collapsible per-question accordion |
| Error handling | Distinct handling for auth, rate-limit, timeout, refusal, and generic API errors, with the chat input disabled/re-enabled around each LLM call |
| Eval suite | LLM-as-judge topic/level checks + grader score-consistency variance test |
| Cost control | Disk-based cache keyed on full call payload, with forced-refresh option |

## 📂 Repository Structure

```
├── app.py                 # Streamlit app — setup, interview, and feedback flow
├── ui.py                  # Custom CSS, header, step indicator, evaluation rendering
├── prompts.py             # System prompts and interview constants
├── schemas.py             # Pydantic schemas for structured-output evaluation
├── eval_cache.py          # Disk-based cache for eval-suite API calls
├── tests/
│   ├── test_evals.py          # LLM-as-judge + grader-consistency eval suite (pytest, model_eval marker)
│   ├── test_schemas.py        # Unit tests for score clamping (schemas.py)
│   ├── test_question_bank.py  # Unit tests for question sampling (question_bank.py)
│   └── test_app_setup_flow.py # AppTest-driven tests for the setup-step state machine (app.py)
├── requirements.txt       # Python dependencies
├── pyproject.toml         # Project metadata, pytest marker config, ruff + mypy config
├── .pre-commit-config.yaml # Pre-commit hooks (ruff lint + format, mypy)
├── .gitignore
└── README.md
```

## 👩‍💻 How to Run

1. Clone this repository
2. Create and activate a virtual environment, then install requirements:
   ```
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   pip install -r requirements.txt
   ```
3. Add your OpenAI API key to Streamlit secrets — copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and fill in your key:
   ```
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
   ```
   OPENAI_API_KEY = "your_key_here"
   ```
4. Run the app:
   ```
   streamlit run app.py
   ```

## 🧹 Linting, Formatting & Type Checking

Lint checks and formatting are handled by [ruff](https://docs.astral.sh/ruff/); static type checking by [mypy](https://mypy-lang.org/):

```
pip install -e ".[dev]"
ruff check .      # lint
ruff format .     # format
mypy .            # type check
```

Optionally, install the pre-commit hook so all three run automatically before each commit:

```
pre-commit install
```

## ✅ Running the Unit Tests

Deterministic, no network, no API key required:

```
pytest
```

## 🧪 Running the Eval Suite

The eval suite calls the OpenAI API and is excluded from a plain `pytest` run. Run it explicitly:

```
$env:OPENAI_API_KEY = "your_key_here"   # PowerShell
pytest tests/test_evals.py -v -m model_eval
```

> Note: this only sets the variable for the current terminal session — you'll need to set it again each time you open a new one. For cmd.exe instead of PowerShell, use `set OPENAI_API_KEY=your_key_here`.

First run records live API responses to `.eval_cache/` (not committed — see `.gitignore`); subsequent runs replay from cache for free. Set `EVAL_CACHE_REFRESH=1` to force fresh recordings, e.g. after changing `prompts.py`.

---

**Developed by:**   
Nicole Kaye A. Cardel    
nkcardel@gmail.com  
*Software Designer & Developer* | *AI Engineer*
