"""
Model evaluation suite.

Run explicitly:
    pytest test_evals.py -v -m model_eval

Requires OPENAI_API_KEY in the environment.
"""
import os
import statistics

import pytest
from openai import OpenAI
from pydantic import BaseModel, Field

import prompts
from eval_cache import cached_call
from schemas import InterviewEvaluation, SetupResult

pytestmark = pytest.mark.model_eval

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ---------------------------------------------------------------------------
# Fixed candidate profiles — this is the "eval dataset."
# ---------------------------------------------------------------------------
CANDIDATE_PROFILES = [
    dict(
        name="Alex",
        experience="2 years as a data analyst using SQL and Tableau",
        skills="SQL, Python (pandas), Tableau, basic statistics",
        level="Junior",
        position="Data Scientist",
        company="Amazon",
    ),
    dict(
        name="Priya",
        experience="6 years building recommendation systems at a mid-size retailer",
        skills="PyTorch, distributed training, feature stores, A/B testing",
        level="Senior",
        position="ML Engineer",
        company="Spotify",
    ),
    dict(
        name="Jordan",
        experience="1 year internship doing ETL pipelines",
        skills="Airflow, dbt, SQL",
        level="Junior",
        position="Data Engineer",
        company="Nestle",
    ),
]


class QuestionJudgement(BaseModel):
    on_topic: bool = Field(
        ..., description="Does the question relate to the candidate's stated profile and target role?"
    )
    appropriate_for_level: bool = Field(
        ..., description="Is the question appropriately scoped for the candidate's stated seniority level?"
    )
    reasoning: str = Field(..., description="One sentence justifying the two judgements above.")

FIXED_DB_QUESTIONS = [
    {"category": "Background", "text": "Walk me through your career so far and what led you to apply for this role."},
    {
        "category": "Technical Knowledge",
        "text": "What best practices do you follow to make sure your work is reliable and maintainable over time?",
    },
]


def generate_setup_questions(profile: dict, db_questions: list) -> list:
    system_prompt = prompts.get_setup_prompt(
        profile["name"], profile["experience"], profile["skills"], profile["level"], profile["position"],
        profile.get("company", ""), "", "", "", db_questions,
    )
    payload = {"model": prompts.MODEL_NAME, "system_prompt": system_prompt, "temperature": 0.7, "schema": "SetupResult"}

    def _live():
        completion = client.beta.chat.completions.parse(
            model=prompts.MODEL_NAME,
            messages=[{"role": "system", "content": system_prompt}],
            temperature=0.7,
            response_format=SetupResult,
        )
        return completion.choices[0].message.parsed.model_dump()

    return cached_call("setup_questions", payload, _live)["questions"]


def judge_question(question: str, profile: dict) -> QuestionJudgement:
    judge_prompt = (
        "You are auditing an AI-conducted job interview. Given the candidate profile "
        "and one question the interviewer asked, judge whether the question is topically "
        "relevant to the candidate's background/role, and appropriately scoped for their "
        "stated seniority level.\n\n"
        f"Candidate: {profile['name']}, applying for {profile['level']} {profile['position']} "
        f"at {profile['company']}\n"
        f"Experience: {profile['experience']}\n"
        f"Skills: {profile['skills']}\n\n"
        f"Interviewer question: {question}"
    )
    payload = {"model": prompts.MODEL_NAME, "prompt": judge_prompt, "temperature": 0, "schema": "QuestionJudgement"}

    def _live():
        completion = client.beta.chat.completions.parse(
            model=prompts.MODEL_NAME,
            messages=[{"role": "user", "content": judge_prompt}],
            response_format=QuestionJudgement,
            temperature=0,
        )
        return completion.choices[0].message.parsed.model_dump()

    return QuestionJudgement(**cached_call("judge_question", payload, _live))


@pytest.mark.parametrize("profile", CANDIDATE_PROFILES, ids=lambda p: p["name"])
def test_setup_questions_stay_on_topic(profile):
    questions = generate_setup_questions(profile, FIXED_DB_QUESTIONS)
    judgements = [judge_question(q["question_text"], profile) for q in questions]

    off_topic = [j for j in judgements if not j.on_topic]
    assert not off_topic, (
        f"Off-topic question(s) for {profile['name']}: {[j.reasoning for j in off_topic]}"
    )

    wrong_level = [j for j in judgements if not j.appropriate_for_level]
    assert len(wrong_level) <= 1, (
        f"Multiple level-inappropriate questions for {profile['name']}: "
        f"{[j.reasoning for j in wrong_level]}"
    )


# ---------------------------------------------------------------------------
# Grader consistency — same transcript, repeated scoring, measure variance.
# ---------------------------------------------------------------------------
FIXED_TRANSCRIPT = """
system: You are interviewing a Junior Data Scientist candidate at Amazon.
assistant: Can you walk me through a time you used SQL to solve a business problem?
user: I once optimized a slow query joining five tables by adding indexes and rewriting it as a CTE, cutting runtime from 40s to 2s.
assistant: Nice. How do you approach explaining a technical result to a non-technical stakeholder?
user: I focus on the business impact first, then offer to go deeper into methodology if they want it.
""".strip()


def test_grader_score_consistency():
    scores = []
    for run_index in range(5):
        # run_index stays part of the cache key so replay preserves 5
        # distinct recorded samples rather than collapsing to one.
        payload = {
            "model": prompts.MODEL_NAME,
            "prompt": prompts.get_evaluation_user_prompt(FIXED_TRANSCRIPT),
            "temperature": 0.2,
            "run_index": run_index,
        }

        def _live():
            completion = client.beta.chat.completions.parse(
                model=prompts.MODEL_NAME,
                messages=[
                    {"role": "system", "content": prompts.EVALUATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompts.get_evaluation_user_prompt(FIXED_TRANSCRIPT)},
                ],
                temperature=0.2,
                response_format=InterviewEvaluation,
            )
            return {"overall_score": completion.choices[0].message.parsed.overall_score}

        scores.append(cached_call("grader_consistency", payload, _live)["overall_score"])

    spread = max(scores) - min(scores)
    stdev = statistics.pstdev(scores)
    print(f"Scores across 5 runs: {scores} | spread={spread} | stdev={stdev:.2f}")

    assert spread <= 2.0, f"Grader score spread too high across identical transcript: {scores}"