"""Loader for the local interview question bank (see question_bank.json)."""
import json
import random
from pathlib import Path
from typing import Dict, List

_BANK_PATH = Path(__file__).parent / "question_bank.json"


def load_question_bank() -> List[Dict[str, str]]:
    with _BANK_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def sample_questions(n: int = 2) -> List[Dict[str, str]]:
    """Randomly sample n questions from the bank, e.g. for LLM 1 (Setup) to
    correct and fold into the final question set.
    """
    return random.sample(load_question_bank(), n)
