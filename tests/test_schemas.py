"""Unit tests for schemas.py: pure validation/clamping logic, no LLM calls."""
import pytest

from schemas import InterviewEvaluation, QuestionEvaluation, _clamp


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (5.0, 5.0),
        (0.0, 0.0),
        (10.0, 10.0),
        (-3.5, 0.0),
        (13.2, 10.0),
        (-0.0001, 0.0),
        (10.0001, 10.0),
    ],
)
def test_clamp_bounds_to_zero_ten(value, expected):
    assert _clamp(value) == expected


def _make_evaluation(**overrides) -> InterviewEvaluation:
    defaults = dict(
        questions=[
            QuestionEvaluation(
                topic="Background",
                score=7,
                critique="Solid answer with a concrete example.",
                key_takeaways=["Used a specific project as evidence"],
            )
        ],
        overall_score=7.5,
        communication_score=8.0,
        depth_score=6.0,
        problem_solving_score=7.0,
        role_fit_score=9.0,
        overall_summary="A strong performance overall.",
        top_strengths=["Clear communicator"],
        areas_for_improvement=["Could go deeper on technical tradeoffs"],
    )
    defaults.update(overrides)
    return InterviewEvaluation(**defaults)


def test_clamped_overall_score_within_range_is_unchanged():
    evaluation = _make_evaluation(overall_score=7.5)
    assert evaluation.clamped_overall_score() == 7.5


def test_clamped_overall_score_clamps_out_of_range_value():
    evaluation = _make_evaluation(overall_score=42.0)
    assert evaluation.clamped_overall_score() == 10.0


def test_criteria_scores_returns_labeled_clamped_pairs_in_order():
    evaluation = _make_evaluation(
        communication_score=-5.0,
        depth_score=6.0,
        problem_solving_score=15.0,
        role_fit_score=3.0,
    )
    assert evaluation.criteria_scores() == [
        ("Communication", 0.0),
        ("Depth & Substance", 6.0),
        ("Problem-Solving", 10.0),
        ("Role Fit", 3.0),
    ]
