"""
Lightweight on-disk cache for model_eval API calls.

test_evals.py calls the OpenAI API directly (interview turns, judge
calls, grader-consistency runs). Those calls cost money and are
non-deterministic, so every call site wraps its live API call in
cached_call():

    payload = {...}  # everything that identifies this specific call

    def _live():
        completion = client.chat.completions.create(...)
        return {"content": completion.choices[0].message.content}

    result = cached_call("interview_turn", payload, _live)

Behavior:
  - First run for a given (name, payload): calls _live(), records the
    JSON-serializable result to disk, returns it.
  - Every later run with the same (name, payload): replays the recorded
    result instead of hitting the API. Changing anything in payload
    (model, prompt, temperature, run_index, ...) produces a different
    cache key, so it's treated as a new call rather than a stale hit.

Cache files live under .eval_cache/<name>/<hash>.json as plain JSON.
Delete the whole .eval_cache/ directory (or just one bucket) to force
everything in it to re-run live.

Set EVAL_CACHE_REFRESH=1 in the environment to bypass existing cache
entries for a run and re-record fresh ones (useful when you've changed
prompts.py and want new recordings without deleting old ones by hand).
"""

import hashlib
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

CACHE_DIR = Path(__file__).parent / ".eval_cache"


def _cache_key(payload: dict[str, Any]) -> str:
    """Stable hash of a JSON-serializable payload dict."""
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _force_refresh() -> bool:
    return os.environ.get("EVAL_CACHE_REFRESH", "") == "1"


def cached_call(
    name: str, payload: dict[str, Any], live_fn: Callable[[], dict[str, Any]]
) -> dict[str, Any]:
    """Return a cached JSON-serializable result for (name, payload), calling
    live_fn() and recording its result on a cache miss (or on forced refresh).

    Args:
        name: logical bucket for this call site, e.g. "interview_turn",
            "judge_question", "grader_consistency". Keeps unrelated call
            sites from colliding even if a payload happened to match.
        payload: JSON-serializable dict that uniquely identifies this call
            (model, messages/prompt, temperature, and anything else that
            would change the output, e.g. a run_index for intentionally
            repeated calls).
        live_fn: zero-arg callable that performs the real API call and
            returns a JSON-serializable dict.

    Returns:
        The cached or freshly-recorded dict.
    """
    bucket_dir = CACHE_DIR / name
    bucket_dir.mkdir(parents=True, exist_ok=True)
    cache_file = bucket_dir / f"{_cache_key(payload)}.json"

    if cache_file.exists() and not _force_refresh():
        with cache_file.open("r", encoding="utf-8") as f:
            return json.load(f)

    result = live_fn()

    with cache_file.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True)

    return result
