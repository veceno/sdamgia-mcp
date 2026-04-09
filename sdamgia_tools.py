"""
sdamgia_tools.py — wrappers around the sdamgia-api library.

The sdamgia-api library (SdamGIA class) takes no arguments on construction;
every method receives the subject code as its first argument.

All functions are synchronous (sdamgia-api uses requests internally).
"""

import sys
import time
from typing import Any

from sdamgia import SdamGIA

# ---------------------------------------------------------------------------
# Subject resolution
# ---------------------------------------------------------------------------

# Maps human-readable aliases → canonical sdamgia-api subject codes.
# Note: the library uses 'en', not 'eng', for English.
SUBJECT_ALIASES: dict[str, str] = {
    # math (profile)
    "математика профиль": "math",
    "профмат": "math",
    "профильная математика": "math",
    "math": "math",
    # math (base)
    "математика база": "mathb",
    "матбаза": "mathb",
    "базовая математика": "mathb",
    "mathb": "mathb",
    # russian
    "русский": "rus",
    "русский язык": "rus",
    "rus": "rus",
    # informatics
    "информатика": "inf",
    "inf": "inf",
    # physics
    "физика": "phys",
    "phys": "phys",
    # chemistry
    "химия": "chem",
    "chem": "chem",
    # biology
    "биология": "bio",
    "bio": "bio",
    # history
    "история": "hist",
    "hist": "hist",
    # social studies
    "обществознание": "soc",
    "общество": "soc",
    "soc": "soc",
    # english — library key is 'en'
    "английский": "en",
    "английский язык": "en",
    "eng": "en",
    "en": "en",
    # geography
    "география": "geo",
    "geo": "geo",
    # literature
    "литература": "lit",
    "lit": "lit",
}

VALID_SUBJECTS = sorted(set(SUBJECT_ALIASES.values()))


def resolve_subject(subject: str) -> str:
    """Normalize a subject name (Russian alias or English code) to its canonical code."""
    key = subject.strip().lower()
    code = SUBJECT_ALIASES.get(key)
    if code is None:
        valid = ", ".join(VALID_SUBJECTS)
        raise ValueError(
            f"Unknown subject '{subject}'. Valid subject codes: {valid}. "
            "Russian aliases are also accepted, e.g. 'математика профиль', 'физика'."
        )
    return code


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Single shared client — SdamGIA() has no per-subject state.
_CLIENT = SdamGIA()


def _clean(text: str | None) -> str | None:
    """Strip non-breaking spaces and zero-width characters."""
    if text is None:
        return None
    return text.replace("\xa0", " ").replace("\u200b", "").strip()


def _retry(fn, *args, retries: int = 1, delay: float = 1.0, **kwargs):
    """Call fn(*args, **kwargs), retrying once after `delay` seconds on exception."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        if retries <= 0:
            raise
        print(f"[sdamgia] error, retrying: {exc}", file=sys.stderr)
        time.sleep(delay)
        return fn(*args, **kwargs)


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def search_problems(subject: str, query: str, limit: int = 20) -> list[dict[str, Any]]:
    """
    Search problems by text query.
    Returns a list of {"id": str, "condition_preview": str} dicts.
    The search endpoint only returns IDs; we fetch a short preview for each via
    get_problem_by_id (up to `limit` results).
    """
    code = resolve_subject(subject)

    # search() returns a list of ID strings
    ids: list[str] = _retry(_CLIENT.search, code, query)
    ids = ids[:limit]

    results = []
    for pid in ids:
        try:
            raw = _CLIENT.get_problem_by_id(code, pid)
            condition = raw.get("condition") if raw else None
            text = _clean(condition.get("text", "")) if condition else ""
            preview = (text or "")[:200]
        except Exception:
            preview = ""
        results.append({"id": str(pid), "condition_preview": preview})

    return results


def get_problem(subject: str, problem_id: str) -> dict[str, Any]:
    """
    Fetch full problem details: condition, solution, answer, analogs, url.
    Returns an error dict if the problem is not found.
    """
    code = resolve_subject(subject)

    try:
        raw = _retry(_CLIENT.get_problem_by_id, code, problem_id)
    except Exception as exc:
        print(f"[sdamgia] get_problem error: {exc}", file=sys.stderr)
        return {"error": f"Problem {problem_id} not found for subject {subject}"}

    if raw is None:
        return {"error": f"Problem {problem_id} not found for subject {subject}"}

    def extract_part(part: dict | None) -> dict | None:
        if not part:
            return None
        text = _clean(part.get("text", ""))
        images = part.get("images", [])
        out: dict[str, Any] = {"text": text}
        if images:
            out["images"] = images
        return out

    return {
        "id": str(problem_id),
        "subject": code,
        "topic": raw.get("topic", ""),
        "condition": extract_part(raw.get("condition")),
        "solution": extract_part(raw.get("solution")),
        "answer": _clean(raw.get("answer", "")),
        "analogs": [str(a) for a in (raw.get("analogs") or [])],
        "url": raw.get("url", ""),
    }


def get_catalog(subject: str) -> list[dict[str, Any]]:
    """
    Return the full problem catalog tree:
    [{topic_id, topic_name, categories: [{category_id, category_name}]}]
    The library already returns this structure; we just clean text.
    """
    code = resolve_subject(subject)
    raw: list[dict] = _retry(_CLIENT.get_catalog, code)

    catalog = []
    for topic in raw:
        categories = [
            {
                "category_id": str(cat.get("category_id", "")),
                "category_name": _clean(cat.get("category_name", "")) or "",
            }
            for cat in topic.get("categories", [])
        ]
        catalog.append(
            {
                "topic_id": str(topic.get("topic_id", "")),
                "topic_name": _clean(topic.get("topic_name", "")) or "",
                "categories": categories,
            }
        )

    return catalog


def get_problems_by_category(subject: str, category_id: str) -> list[str]:
    """Return all problem IDs within a specific category."""
    code = resolve_subject(subject)
    raw: list[str] = _retry(_CLIENT.get_category_by_id, code, category_id)
    return [str(pid) for pid in (raw or [])]


def generate_test(subject: str, topics: dict[int, int]) -> dict[str, Any]:
    """
    Generate a custom test and return {"test_id": str, "pdf_url": str | None}.
    `topics` maps topic_number (int) → problem count (int).
    """
    code = resolve_subject(subject)

    try:
        test_id: str = _retry(_CLIENT.generate_test, code, topics)
    except Exception as exc:
        print(f"[sdamgia] generate_test error: {exc}", file=sys.stderr)
        return {"error": f"Failed to generate test: {exc}"}

    if not test_id:
        return {"error": "Test generation returned no ID"}

    # Generate horizontal PDF (pdf='h')
    try:
        pdf_url: str | None = _retry(
            _CLIENT.generate_pdf, code, test_id, pdf="h"
        )
    except Exception as exc:
        print(f"[sdamgia] generate_pdf error: {exc}", file=sys.stderr)
        pdf_url = None

    return {"test_id": str(test_id), "pdf_url": pdf_url}


def get_problem_batch(subject: str, problem_ids: list[str]) -> list[dict[str, Any]]:
    """
    Fetch multiple problems sequentially with 0.3s delay between requests.
    Maximum 20 IDs per call.
    """
    if len(problem_ids) > 20:
        problem_ids = problem_ids[:20]

    results = []
    for i, pid in enumerate(problem_ids):
        if i > 0:
            time.sleep(0.3)
        results.append(get_problem(subject, pid))

    return results
