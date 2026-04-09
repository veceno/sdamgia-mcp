"""
Tests for sdamgia_tools functions.

All SdamGIA HTTP calls are mocked — no real network requests are made.
"""

import time
from unittest.mock import MagicMock, patch, call

import pytest
import sdamgia_tools as tools


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def mock_client(monkeypatch):
    """Replace the shared _CLIENT with a fresh MagicMock for every test."""
    client = MagicMock()
    monkeypatch.setattr(tools, "_CLIENT", client)
    return client


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Disable time.sleep in sdamgia_tools to keep tests fast."""
    monkeypatch.setattr(tools.time, "sleep", lambda s: None)


# ---------------------------------------------------------------------------
# search_problems
# ---------------------------------------------------------------------------

class TestSearchProblems:
    def test_returns_list_of_dicts(self, mock_client):
        mock_client.search.return_value = ["101", "202"]
        mock_client.get_problem_by_id.side_effect = [
            {"condition": {"text": "Задача 101", "images": []}, "answer": "42"},
            {"condition": {"text": "Задача 202", "images": []}, "answer": "7"},
        ]
        result = tools.search_problems("math", "логарифм")
        assert len(result) == 2
        assert result[0]["id"] == "101"
        assert "Задача 101" in result[0]["condition_preview"]

    def test_limit_applied(self, mock_client):
        mock_client.search.return_value = [str(i) for i in range(50)]
        mock_client.get_problem_by_id.return_value = {
            "condition": {"text": "x", "images": []}, "answer": ""
        }
        result = tools.search_problems("math", "x", limit=5)
        assert len(result) == 5

    def test_preview_truncated_to_200(self, mock_client):
        long_text = "A" * 500
        mock_client.search.return_value = ["1"]
        mock_client.get_problem_by_id.return_value = {
            "condition": {"text": long_text, "images": []}, "answer": ""
        }
        result = tools.search_problems("math", "anything")
        assert len(result[0]["condition_preview"]) == 200

    def test_nbsp_stripped_from_preview(self, mock_client):
        mock_client.search.return_value = ["1"]
        mock_client.get_problem_by_id.return_value = {
            "condition": {"text": "hello\xa0world", "images": []}, "answer": ""
        }
        result = tools.search_problems("math", "q")
        assert "\xa0" not in result[0]["condition_preview"]
        assert "hello world" in result[0]["condition_preview"]

    def test_preview_empty_when_problem_fetch_fails(self, mock_client):
        mock_client.search.return_value = ["999"]
        mock_client.get_problem_by_id.side_effect = Exception("network error")
        result = tools.search_problems("math", "q")
        assert result[0]["id"] == "999"
        assert result[0]["condition_preview"] == ""

    def test_empty_search_results(self, mock_client):
        mock_client.search.return_value = []
        result = tools.search_problems("phys", "ничего")
        assert result == []

    def test_invalid_subject_raises(self):
        with pytest.raises(ValueError):
            tools.search_problems("неизвестный", "q")

    def test_russian_subject_alias(self, mock_client):
        mock_client.search.return_value = []
        tools.search_problems("физика", "волна")
        mock_client.search.assert_called_once_with("phys", "волна")

    def test_no_condition_key(self, mock_client):
        """Problem dict with no 'condition' key gives empty preview."""
        mock_client.search.return_value = ["5"]
        mock_client.get_problem_by_id.return_value = {"answer": "3"}
        result = tools.search_problems("math", "q")
        assert result[0]["condition_preview"] == ""


# ---------------------------------------------------------------------------
# get_problem
# ---------------------------------------------------------------------------

class TestGetProblem:
    def _raw(self, **overrides):
        base = {
            "id": "77345",
            "topic": "Логарифмы",
            "condition": {"text": "Найдите\xa0x", "images": ["https://img/1.png"]},
            "solution": {"text": "Решение", "images": []},
            "answer": "3",
            "analogs": ["100", "200"],
            "url": "https://math-ege.sdamgia.ru/problem?id=77345",
        }
        base.update(overrides)
        return base

    def test_happy_path_structure(self, mock_client):
        mock_client.get_problem_by_id.return_value = self._raw()
        result = tools.get_problem("math", "77345")
        assert result["id"] == "77345"
        assert result["subject"] == "math"
        assert result["topic"] == "Логарифмы"
        assert result["answer"] == "3"
        assert result["analogs"] == ["100", "200"]
        assert "math-ege.sdamgia.ru" in result["url"]

    def test_nbsp_stripped_from_condition_text(self, mock_client):
        mock_client.get_problem_by_id.return_value = self._raw()
        result = tools.get_problem("math", "77345")
        assert "\xa0" not in result["condition"]["text"]
        assert result["condition"]["text"] == "Найдите x"

    def test_images_included_when_present(self, mock_client):
        mock_client.get_problem_by_id.return_value = self._raw()
        result = tools.get_problem("math", "77345")
        assert result["condition"]["images"] == ["https://img/1.png"]

    def test_images_omitted_when_empty(self, mock_client):
        mock_client.get_problem_by_id.return_value = self._raw()
        result = tools.get_problem("math", "77345")
        # solution images list is empty → key should not appear
        assert "images" not in result["solution"]

    def test_none_response_returns_error_dict(self, mock_client):
        mock_client.get_problem_by_id.return_value = None
        result = tools.get_problem("math", "99999")
        assert "error" in result
        assert "99999" in result["error"]

    def test_exception_returns_error_dict(self, mock_client):
        mock_client.get_problem_by_id.side_effect = Exception("timeout")
        result = tools.get_problem("phys", "1")
        assert "error" in result

    def test_retry_on_first_failure(self, mock_client):
        mock_client.get_problem_by_id.side_effect = [
            Exception("flaky"),
            self._raw(),
        ]
        result = tools.get_problem("math", "77345")
        assert result["id"] == "77345"
        assert mock_client.get_problem_by_id.call_count == 2

    def test_both_retries_fail_returns_error(self, mock_client):
        mock_client.get_problem_by_id.side_effect = Exception("persistent")
        result = tools.get_problem("math", "1")
        assert "error" in result

    def test_missing_condition_is_none(self, mock_client):
        raw = self._raw()
        raw["condition"] = None
        mock_client.get_problem_by_id.return_value = raw
        result = tools.get_problem("math", "77345")
        assert result["condition"] is None

    def test_analogs_cast_to_str(self, mock_client):
        raw = self._raw(analogs=[100, 200, 300])
        mock_client.get_problem_by_id.return_value = raw
        result = tools.get_problem("math", "77345")
        assert all(isinstance(a, str) for a in result["analogs"])

    def test_empty_analogs(self, mock_client):
        raw = self._raw(analogs=[])
        mock_client.get_problem_by_id.return_value = raw
        result = tools.get_problem("math", "77345")
        assert result["analogs"] == []

    def test_invalid_subject_raises(self):
        with pytest.raises(ValueError):
            tools.get_problem("неизвестный", "1")


# ---------------------------------------------------------------------------
# get_catalog
# ---------------------------------------------------------------------------

class TestGetCatalog:
    def _raw_catalog(self):
        return [
            {
                "topic_id": "1",
                "topic_name": "Алгебра\xa0и начала анализа",
                "categories": [
                    {"category_id": "10", "category_name": "Логарифмы\xa0"},
                    {"category_id": "11", "category_name": "Степени"},
                ],
            },
            {
                "topic_id": "2",
                "topic_name": "Геометрия",
                "categories": [],
            },
        ]

    def test_returns_list(self, mock_client):
        mock_client.get_catalog.return_value = self._raw_catalog()
        result = tools.get_catalog("math")
        assert isinstance(result, list)
        assert len(result) == 2

    def test_topic_structure(self, mock_client):
        mock_client.get_catalog.return_value = self._raw_catalog()
        result = tools.get_catalog("math")
        topic = result[0]
        assert topic["topic_id"] == "1"
        assert "категории" not in topic  # not leaking raw keys
        assert "categories" in topic

    def test_nbsp_stripped_from_topic_name(self, mock_client):
        mock_client.get_catalog.return_value = self._raw_catalog()
        result = tools.get_catalog("math")
        assert "\xa0" not in result[0]["topic_name"]

    def test_nbsp_stripped_from_category_name(self, mock_client):
        mock_client.get_catalog.return_value = self._raw_catalog()
        result = tools.get_catalog("math")
        assert "\xa0" not in result[0]["categories"][0]["category_name"]

    def test_category_ids_are_strings(self, mock_client):
        mock_client.get_catalog.return_value = self._raw_catalog()
        result = tools.get_catalog("math")
        for topic in result:
            for cat in topic["categories"]:
                assert isinstance(cat["category_id"], str)

    def test_empty_categories_list(self, mock_client):
        mock_client.get_catalog.return_value = self._raw_catalog()
        result = tools.get_catalog("math")
        assert result[1]["categories"] == []

    def test_calls_correct_subject_code(self, mock_client):
        mock_client.get_catalog.return_value = []
        tools.get_catalog("профмат")
        mock_client.get_catalog.assert_called_once_with("math")

    def test_invalid_subject_raises(self):
        with pytest.raises(ValueError):
            tools.get_catalog("unknown_subj")


# ---------------------------------------------------------------------------
# get_problems_by_category
# ---------------------------------------------------------------------------

class TestGetProblemsByCategory:
    def test_returns_string_list(self, mock_client):
        mock_client.get_category_by_id.return_value = ["101", "202", "303"]
        result = tools.get_problems_by_category("math", "42")
        assert result == ["101", "202", "303"]

    def test_ids_cast_to_str(self, mock_client):
        mock_client.get_category_by_id.return_value = [101, 202]
        result = tools.get_problems_by_category("math", "42")
        assert all(isinstance(pid, str) for pid in result)

    def test_empty_category(self, mock_client):
        mock_client.get_category_by_id.return_value = []
        result = tools.get_problems_by_category("math", "99")
        assert result == []

    def test_none_response_returns_empty(self, mock_client):
        mock_client.get_category_by_id.return_value = None
        result = tools.get_problems_by_category("math", "99")
        assert result == []

    def test_passes_correct_subject_and_category(self, mock_client):
        mock_client.get_category_by_id.return_value = []
        tools.get_problems_by_category("физика", "55")
        mock_client.get_category_by_id.assert_called_once_with("phys", "55")

    def test_invalid_subject_raises(self):
        with pytest.raises(ValueError):
            tools.get_problems_by_category("xyz", "1")


# ---------------------------------------------------------------------------
# generate_test
# ---------------------------------------------------------------------------

class TestGenerateTest:
    def test_happy_path_returns_test_id_and_pdf_url(self, mock_client):
        mock_client.generate_test.return_value = "TEST123"
        mock_client.generate_pdf.return_value = "https://math-ege.sdamgia.ru/pdf/abc.pdf"
        result = tools.generate_test("math", {1: 1, 2: 1, 3: 2})
        assert result["test_id"] == "TEST123"
        assert result["pdf_url"] == "https://math-ege.sdamgia.ru/pdf/abc.pdf"

    def test_pdf_url_none_when_generate_pdf_fails(self, mock_client):
        mock_client.generate_test.return_value = "TEST123"
        mock_client.generate_pdf.side_effect = Exception("pdf error")
        result = tools.generate_test("math", {1: 1})
        assert result["test_id"] == "TEST123"
        assert result["pdf_url"] is None

    def test_generate_test_failure_returns_error(self, mock_client):
        mock_client.generate_test.side_effect = Exception("server error")
        result = tools.generate_test("math", {1: 1})
        assert "error" in result

    def test_empty_test_id_returns_error(self, mock_client):
        mock_client.generate_test.return_value = ""
        result = tools.generate_test("math", {1: 1})
        assert "error" in result

    def test_generate_pdf_called_with_horizontal_layout(self, mock_client):
        mock_client.generate_test.return_value = "T1"
        mock_client.generate_pdf.return_value = "https://..."
        tools.generate_test("math", {1: 1})
        args, kwargs = mock_client.generate_pdf.call_args
        # pdf='h' can arrive as positional or keyword
        assert kwargs.get("pdf") == "h" or (len(args) >= 3 and args[2] == "h")

    def test_passes_topics_to_library(self, mock_client):
        mock_client.generate_test.return_value = "T1"
        mock_client.generate_pdf.return_value = ""
        topics = {1: 2, 3: 1}
        tools.generate_test("inf", topics)
        mock_client.generate_test.assert_called_once_with("inf", topics)

    def test_invalid_subject_raises(self):
        with pytest.raises(ValueError):
            tools.generate_test("nope", {1: 1})


# ---------------------------------------------------------------------------
# get_problem_batch
# ---------------------------------------------------------------------------

class TestGetProblemBatch:
    def _stub_problem(self, pid):
        return {
            "id": str(pid),
            "subject": "math",
            "topic": "",
            "condition": {"text": f"Условие {pid}"},
            "solution": {"text": "Решение"},
            "answer": str(pid),
            "analogs": [],
            "url": f"https://math-ege.sdamgia.ru/problem?id={pid}",
        }

    def test_returns_list_for_each_id(self, mock_client):
        mock_client.get_problem_by_id.side_effect = [
            self._stub_problem(1), self._stub_problem(2), self._stub_problem(3)
        ]
        result = tools.get_problem_batch("math", ["1", "2", "3"])
        assert len(result) == 3
        assert result[0]["id"] == "1"
        assert result[2]["id"] == "3"

    def test_max_20_ids_enforced(self, mock_client):
        ids = [str(i) for i in range(30)]
        mock_client.get_problem_by_id.return_value = self._stub_problem(0)
        result = tools.get_problem_batch("math", ids)
        assert len(result) == 20
        assert mock_client.get_problem_by_id.call_count == 20

    def test_delay_called_between_requests(self, mock_client, monkeypatch):
        sleep_calls = []
        monkeypatch.setattr(tools.time, "sleep", lambda s: sleep_calls.append(s))
        mock_client.get_problem_by_id.return_value = self._stub_problem(1)
        tools.get_problem_batch("math", ["1", "2", "3"])
        # sleep should be called n-1 times (not before the first request)
        assert len(sleep_calls) == 2
        assert all(s == 0.3 for s in sleep_calls)

    def test_no_delay_before_first_request(self, mock_client, monkeypatch):
        sleep_calls = []
        monkeypatch.setattr(tools.time, "sleep", lambda s: sleep_calls.append(s))
        mock_client.get_problem_by_id.return_value = self._stub_problem(1)
        tools.get_problem_batch("math", ["1"])
        assert len(sleep_calls) == 0

    def test_error_dict_in_batch_on_failure(self, mock_client):
        mock_client.get_problem_by_id.side_effect = [
            self._stub_problem(1),
            Exception("not found"),
        ]
        result = tools.get_problem_batch("math", ["1", "bad"])
        assert result[0]["id"] == "1"
        assert "error" in result[1]

    def test_empty_list_returns_empty(self, mock_client):
        result = tools.get_problem_batch("math", [])
        assert result == []

    def test_invalid_subject_raises(self):
        with pytest.raises(ValueError):
            tools.get_problem_batch("bad_subj", ["1"])
