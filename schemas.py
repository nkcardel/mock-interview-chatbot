"""
Structured-output schema for interview evaluation.

Using OpenAI Structured Outputs (client.beta.chat.completions.parse with a
Pydantic response_format) guarantees the response is valid JSON matching
this exact schema: every required field present, every field the right
type. The model literally cannot return a missing "Overall Score" line or
a markdown format variant that slips past a regex — that failure mode is
eliminated at the API layer, not caught after the fact.

What this does NOT guarantee: semantic correctness. The JSON-schema subset
OpenAI enforces in strict mode doesn't support numeric range constraints
(min/max), so `overall_score` is guaranteed to be a float, but not
guaranteed to land in [0, 10]. We still clamp defensively wherever a score
is used — structured outputs remove a class of parsing bugs, not the need
for basic input validation.
"""
from typing import List

from pydantic import BaseModel, Field


class SetupQuestion(BaseModel):
    question_category: str = Field(
        ...,
        description=(
            "The category of this question: one of 'Background', 'Technical Knowledge', "
            "'Situational', 'Brain Teaser', or 'Analytical'."
        ),
    )
    question_text: str = Field(..., description="The finished interview question, verbatim.")


class SetupResult(BaseModel):
    questions: List[SetupQuestion] = Field(
        ..., description="Exactly six finished interview questions, in the order they'll be asked."
    )


class HumanizerTurn(BaseModel):
    previous_response_score: int = Field(
        ..., description="Score for the candidate's previous answer. Intended range: 1-10."
    )
    is_follow_up: bool = Field(
        ...,
        description=(
            "True if this turn's message is a follow-up built on the previous answer; false if it's "
            "the predefined question paired with a short remark."
        ),
    )
    message: str = Field(..., description="The finished message to show the candidate for this turn.")


class QuestionEvaluation(BaseModel):
    topic: str = Field(
        ...,
        description=(
            "The question's category: one of 'Background', 'Technical Knowledge', 'Situational', "
            "'Brain Teaser', or 'Analytical'."
        ),
    )
    question_asked: str = Field(..., description="The interviewer's question, verbatim or lightly summarized.")
    candidate_response_summary: str = Field(..., description="1-2 sentence summary of what the candidate said.")
    score: int = Field(..., description="Score for this single answer. Intended range: 1-10.")
    critique: str = Field(..., description="1-2 sentences on strengths or missing details in this answer.")


class InterviewEvaluation(BaseModel):
    questions: List[QuestionEvaluation] = Field(
        ..., description="One entry per question-answer exchange in the transcript, in order."
    )
    top_strengths: List[str] = Field(..., description="2-3 bullets on what the candidate did well overall.")
    areas_for_improvement: List[str] = Field(..., description="2-3 bullets on what to improve.")
    overall_score: float = Field(..., description="Overall interview score. Intended range: 0-10.")
    final_verdict: str = Field(..., description="2-3 sentences on the candidate's overall readiness for the role.")

    def clamped_overall_score(self) -> float:
        """Defensive clamp: the schema guarantees a float is present, not that it's in range."""
        return max(0.0, min(10.0, self.overall_score))