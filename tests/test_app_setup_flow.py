"""Tests for the setup-step state machine in app.py (steps 1-3, before any LLM
call happens). Driven with Streamlit's official AppTest harness, which runs
the real script and widget callbacks end to end without a network dependency
or a running server.
"""

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest


@pytest.fixture(autouse=True)
def _no_openai_secret(monkeypatch):
    """These tests only exercise the setup-step state machine (steps 1-3), which
    never calls the OpenAI API. Force st.secrets to look empty so a real
    OPENAI_API_KEY in a local secrets.toml can't cause a real network call to
    fire once setup_complete flips to True and the app reaches step 4.
    """
    monkeypatch.setattr(type(st.secrets), "get", lambda self, *args, **kwargs: None)


def _fresh_app() -> AppTest:
    at = AppTest.from_file("../app.py")
    at.run()
    assert not at.exception
    return at


def _fill_step1(
    at: AppTest, name="Jamie", experience="3 years in data", skills="Python, SQL"
) -> AppTest:
    at.text_input(key="input_name").set_value(name)
    at.text_area(key="input_experience").set_value(experience)
    at.text_area(key="input_skills").set_value(skills)
    at.button(key="FormSubmitter:personal_info_form-Next").click().run()
    return at


class TestStep1PersonalInfo:
    def test_starts_on_step_1(self):
        at = _fresh_app()
        assert at.session_state.setup_step == 1
        assert at.session_state.setup_complete is False

    def test_submitting_empty_form_blocks_advance_and_sets_error(self):
        at = _fresh_app()
        at.button(key="FormSubmitter:personal_info_form-Next").click().run()

        assert at.session_state.setup_step == 1
        assert at.session_state.setup_error
        assert at.session_state.invalid_fields == {"input_name", "input_experience", "input_skills"}

    def test_partial_fill_only_flags_missing_fields(self):
        at = _fresh_app()
        at.text_input(key="input_name").set_value("Jamie")
        at.button(key="FormSubmitter:personal_info_form-Next").click().run()

        assert at.session_state.setup_step == 1
        assert at.session_state.invalid_fields == {"input_experience", "input_skills"}

    def test_valid_fill_advances_to_step_2_and_persists_data(self):
        at = _fresh_app()
        _fill_step1(at, name="Jamie", experience="3 years in data", skills="Python, SQL")

        assert at.session_state.setup_step == 2
        assert at.session_state.setup_error is None
        assert at.session_state.invalid_fields == set()
        assert at.session_state.user_data["name"] == "Jamie"
        assert at.session_state.user_data["experience"] == "3 years in data"
        assert at.session_state.user_data["skills"] == "Python, SQL"

    def test_whitespace_only_fields_are_treated_as_missing(self):
        at = _fresh_app()
        at.text_input(key="input_name").set_value("   ")
        at.text_area(key="input_experience").set_value("  ")
        at.text_area(key="input_skills").set_value("  ")
        at.button(key="FormSubmitter:personal_info_form-Next").click().run()

        assert at.session_state.setup_step == 1
        assert at.session_state.invalid_fields == {"input_name", "input_experience", "input_skills"}


class TestStep2CompanySelection:
    def test_selecting_predefined_company_skips_to_step_3(self):
        at = _fresh_app()
        _fill_step1(at)
        at.button(key="company_btn_Amazon").click().run()

        assert at.session_state.setup_step == 3
        assert at.session_state.company_option == "select"
        assert at.session_state.user_data["company"] == "Amazon"
        assert at.session_state.user_data["industry"] == ""

    def test_no_target_company_clears_company_fields_and_skips_to_step_3(self):
        at = _fresh_app()
        _fill_step1(at)
        # Pick a company first, then back out to the generic option, to
        # confirm stale company/industry data doesn't leak through.
        at.button(key="company_btn_Meta").click().run()
        assert at.session_state.user_data["company"] == "Meta"

        at.button(key="step_nav_2").click().run()
        at.button(key="FormSubmitter:company_select_form-No target company").click().run()

        assert at.session_state.setup_step == 3
        assert at.session_state.user_data["company"] == ""
        assert at.session_state.user_data["industry"] == ""
        assert at.session_state.user_data["job_description"] == ""
        assert at.session_state.user_data["job_requirements"] == ""

    def test_custom_company_link_switches_to_custom_subview(self):
        at = _fresh_app()
        _fill_step1(at)
        at.button(
            key="FormSubmitter:company_select_form-Create a custom company profile"
        ).click().run()

        assert at.session_state.company_option == "custom"
        assert at.session_state.setup_step == 2


class TestStep2CustomCompany:
    def _to_custom_company(self, at: AppTest) -> AppTest:
        _fill_step1(at)
        at.button(
            key="FormSubmitter:company_select_form-Create a custom company profile"
        ).click().run()
        return at

    def test_submitting_empty_custom_form_blocks_advance(self):
        at = self._to_custom_company(_fresh_app())
        at.button(key="FormSubmitter:company_custom_form-Next").click().run()

        assert at.session_state.setup_step == 2
        assert at.session_state.company_option == "custom"
        assert at.session_state.setup_error
        assert "input_industry" in at.session_state.invalid_fields
        assert "input_custom_company" in at.session_state.invalid_fields

    def test_other_industry_without_custom_text_is_flagged(self):
        at = self._to_custom_company(_fresh_app())
        at.selectbox(key="input_industry").set_value("Other").run()
        at.text_input(key="input_custom_company").set_value("Acme Robotics")
        at.button(key="FormSubmitter:company_custom_form-Next").click().run()

        assert at.session_state.setup_step == 2
        assert "input_industry" in at.session_state.invalid_fields
        assert "input_custom_industry" in at.session_state.invalid_fields

    def test_valid_custom_company_advances_to_step_3(self):
        at = self._to_custom_company(_fresh_app())
        at.selectbox(key="input_industry").set_value("Healthcare").run()
        at.text_input(key="input_custom_company").set_value("Acme Robotics")
        at.text_area(key="input_job_description").set_value("Build robots.")
        at.button(key="FormSubmitter:company_custom_form-Next").click().run()

        assert at.session_state.setup_step == 3
        assert at.session_state.user_data["company"] == "Acme Robotics"
        assert at.session_state.user_data["industry"] == "Healthcare"
        assert at.session_state.user_data["job_description"] == "Build robots."

    def test_custom_other_industry_saves_free_text_industry(self):
        at = self._to_custom_company(_fresh_app())
        at.selectbox(key="input_industry").set_value("Other").run()
        at.text_input(key="input_custom_industry").set_value("Aerospace").run()
        at.text_input(key="input_custom_company").set_value("Acme Robotics")
        at.button(key="FormSubmitter:company_custom_form-Next").click().run()

        assert at.session_state.setup_step == 3
        assert at.session_state.user_data["industry"] == "Aerospace"

    def test_back_button_returns_to_company_select(self):
        at = self._to_custom_company(_fresh_app())
        at.button(key="FormSubmitter:company_custom_form-Back").click().run()

        assert at.session_state.company_option == "select"
        assert at.session_state.setup_step == 2


class TestStep3Position:
    def _to_position(self, at: AppTest) -> AppTest:
        _fill_step1(at)
        at.button(key="company_btn_Amazon").click().run()
        return at

    def test_submitting_without_position_blocks_completion(self):
        at = self._to_position(_fresh_app())
        at.button(key="FormSubmitter:position_form-Start Interview").click().run()

        assert at.session_state.setup_complete is False
        assert "input_position" in at.session_state.invalid_fields

    def test_other_position_without_custom_text_is_flagged(self):
        at = self._to_position(_fresh_app())
        at.selectbox(key="input_position").set_value("Other").run()
        at.button(key="FormSubmitter:position_form-Start Interview").click().run()

        assert at.session_state.setup_complete is False
        assert "input_position" in at.session_state.invalid_fields
        assert "input_custom_position" in at.session_state.invalid_fields

    def test_valid_position_completes_setup(self):
        at = self._to_position(_fresh_app())
        at.selectbox(key="input_position").set_value("Data Scientist").run()
        at.button(key="FormSubmitter:position_form-Start Interview").click().run()

        assert at.session_state.setup_complete is True
        assert at.session_state.user_data["position"] == "Data Scientist"

    def test_custom_position_saves_free_text(self):
        at = self._to_position(_fresh_app())
        at.selectbox(key="input_position").set_value("Other").run()
        at.text_input(key="input_custom_position").set_value("Chief Vibes Officer").run()
        at.button(key="FormSubmitter:position_form-Start Interview").click().run()

        assert at.session_state.setup_complete is True
        assert at.session_state.user_data["position"] == "Chief Vibes Officer"

    def test_level_button_selects_then_deselects_on_second_click(self):
        at = self._to_position(_fresh_app())
        at.button(key="level_btn_Senior").click().run()
        assert at.session_state.user_data["level"] == "Senior"

        at.button(key="level_btn_Senior").click().run()
        assert at.session_state.user_data["level"] == ""

    def test_selecting_a_different_level_replaces_the_previous_one(self):
        at = self._to_position(_fresh_app())
        at.button(key="level_btn_Junior").click().run()
        at.button(key="level_btn_Senior").click().run()

        assert at.session_state.user_data["level"] == "Senior"


class TestStepIndicatorNavigation:
    def test_clicking_earlier_step_node_navigates_back_without_losing_data(self):
        at = _fresh_app()
        _fill_step1(at, name="Priya")
        at.button(key="company_btn_Google").click().run()
        assert at.session_state.setup_step == 3

        at.button(key="step_nav_1").click().run()

        assert at.session_state.setup_step == 1
        assert at.session_state.user_data["name"] == "Priya"
        assert at.session_state.user_data["company"] == "Google"

    def test_navigating_back_to_step_2_after_custom_company_reopens_custom_view(self):
        at = _fresh_app()
        _fill_step1(at)
        at.button(
            key="FormSubmitter:company_select_form-Create a custom company profile"
        ).click().run()
        at.selectbox(key="input_industry").set_value("Healthcare").run()
        at.text_input(key="input_custom_company").set_value("Acme Robotics")
        at.button(key="FormSubmitter:company_custom_form-Next").click().run()
        assert at.session_state.setup_step == 3

        at.button(key="step_nav_2").click().run()

        assert at.session_state.setup_step == 2
        assert at.session_state.company_option == "custom"


class TestResetInterview:
    def test_reset_returns_to_step_1_with_cleared_user_data(self):
        # The restart button only renders once feedback is generated, which
        # requires a full LLM-driven interview. Seed session_state directly
        # to land on that screen instead, so this test stays focused on
        # reset_interview()'s state-clearing logic rather than the LLM flow.
        from schemas import InterviewEvaluation, QuestionEvaluation

        evaluation = InterviewEvaluation(
            questions=[
                QuestionEvaluation(
                    topic="Background", score=7, critique="Fine.", key_takeaways=["x"]
                )
            ],
            overall_score=7.5,
            communication_score=8.0,
            depth_score=6.0,
            problem_solving_score=7.0,
            role_fit_score=9.0,
            overall_summary="Good.",
            top_strengths=["a"],
            areas_for_improvement=["b"],
        )

        at = AppTest.from_file("../app.py")
        at.session_state["setup_complete"] = True
        at.session_state["feedback_shown"] = True
        at.session_state["chat_complete"] = True
        at.session_state["turns"] = [
            {
                "category": "Background",
                "predefined_question": "q",
                "displayed_question": "q",
                "answer": "a",
                "is_follow_up": False,
            }
        ]
        at.session_state["feedback_data"] = evaluation
        at.session_state["user_data"] = {
            "name": "Jamie",
            "experience": "3 years",
            "skills": "Python",
            "level": "Senior",
            "position": "Data Scientist",
            "company": "Amazon",
            "industry": "",
            "job_description": "",
            "job_requirements": "",
        }
        at.session_state["usage_totals"] = {
            "prompt_tokens": 10,
            "completion_tokens": 10,
            "total_tokens": 20,
            "cost": 0.01,
        }
        at.run()
        assert not at.exception

        at.button(key="btn_restart").click().run()

        assert not at.exception
        assert at.session_state.setup_complete is False
        assert at.session_state.setup_step == 1
        assert at.session_state.company_option == "select"
        assert at.session_state.feedback_shown is False
        assert at.session_state.user_data["name"] == ""
        assert at.session_state.user_data["company"] == ""
        assert at.session_state.turns == []
        assert at.session_state.usage_totals["total_tokens"] == 0
        assert "feedback_data" not in at.session_state
        assert "setup_questions" not in at.session_state
