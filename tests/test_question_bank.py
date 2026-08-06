"""Unit tests for question_bank.py: local JSON loading and sampling, no LLM calls."""

import pytest

import question_bank


def test_load_question_bank_returns_category_and_text_dicts():
    bank = question_bank.load_question_bank()
    assert len(bank) > 0
    for entry in bank:
        assert set(entry.keys()) == {"category", "text"}
        assert entry["category"]
        assert entry["text"]


def test_sample_questions_default_returns_two():
    sample = question_bank.sample_questions()
    assert len(sample) == 2


@pytest.mark.parametrize("n", [0, 1, 3, 5])
def test_sample_questions_returns_requested_count(n):
    assert len(question_bank.sample_questions(n)) == n


def test_sample_questions_draws_without_replacement():
    bank_size = len(question_bank.load_question_bank())
    sample = question_bank.sample_questions(bank_size)
    texts = [entry["text"] for entry in sample]
    assert len(texts) == len(set(texts))


def test_sample_questions_more_than_bank_size_raises():
    bank_size = len(question_bank.load_question_bank())
    with pytest.raises(ValueError):
        question_bank.sample_questions(bank_size + 1)


def test_sample_questions_only_returns_entries_from_bank():
    bank = question_bank.load_question_bank()
    bank_texts = {entry["text"] for entry in bank}
    sample = question_bank.sample_questions(5)
    assert all(entry["text"] in bank_texts for entry in sample)
