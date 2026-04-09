"""
Tests for server.py MCP tool wrappers.

Verifies error handling, subject forwarding, and JSON key conversion
(generate_test receives string keys from JSON, must convert to int).
All underlying sdamgia_tools functions are mocked.
"""

from unittest.mock import patch, MagicMock

import pytest
import server


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patch_tools(name, return_value=None, side_effect=None):
    """Patch sdamgia_tools.<name> inside the server module."""
    kwargs = {}
    if side_effect is not None:
        kwargs["side_effect"] = side_effect
    else:
        kwargs["return_value"] = return_value
    return patch(f"server.tools.{name}", **kwargs)


# ---------------------------------------------------------------------------
# search_problems wrapper
# ---------------------------------------------------------------------------

class TestServerSearchProblems:
    def test_delegates_to_tools(self):
        expected = [{"id": "1", "condition_preview": "Условие"}]
        with _patch_tools("search_problems", return_value=expected) as mock:
            result = server.search_problems("math", "логарифм", 10)
        mock.assert_called_once_with("math", "логарифм", 10)
        assert result == expected

    def test_value_error_returns_error_list(self):
        with _patch_tools("search_problems", side_effect=ValueError("bad subject")):
            result = server.search_problems("xyz", "q", 5)
        assert isinstance(result, list)
        assert "error" in result[0]
        assert "bad subject" in result[0]["error"]

    def test_unexpected_exception_returns_error_list(self):
        with _patch_tools("search_problems", side_effect=RuntimeError("network")):
            result = server.search_problems("math", "q", 5)
        assert isinstance(result, list)
        assert "error" in result[0]


# ---------------------------------------------------------------------------
# get_problem wrapper
# ---------------------------------------------------------------------------

class TestServerGetProblem:
    def test_delegates_to_tools(self):
        expected = {"id": "77345", "answer": "3"}
        with _patch_tools("get_problem", return_value=expected) as mock:
            result = server.get_problem("math", "77345")
        mock.assert_called_once_with("math", "77345")
        assert result == expected

    def test_value_error_returns_error_dict(self):
        with _patch_tools("get_problem", side_effect=ValueError("unknown")):
            result = server.get_problem("bad", "1")
        assert "error" in result

    def test_unexpected_exception_returns_error_dict(self):
        with _patch_tools("get_problem", side_effect=Exception("timeout")):
            result = server.get_problem("math", "1")
        assert "error" in result


# ---------------------------------------------------------------------------
# get_catalog wrapper
# ---------------------------------------------------------------------------

class TestServerGetCatalog:
    def test_delegates_to_tools(self):
        expected = [{"topic_id": "1", "topic_name": "Алгебра", "categories": []}]
        with _patch_tools("get_catalog", return_value=expected) as mock:
            result = server.get_catalog("math")
        mock.assert_called_once_with("math")
        assert result == expected

    def test_value_error_returns_error_list(self):
        with _patch_tools("get_catalog", side_effect=ValueError("bad")):
            result = server.get_catalog("xyz")
        assert "error" in result[0]

    def test_unexpected_exception_returns_error_list(self):
        with _patch_tools("get_catalog", side_effect=OSError("disk")):
            result = server.get_catalog("math")
        assert "error" in result[0]


# ---------------------------------------------------------------------------
# get_problems_by_category wrapper
# ---------------------------------------------------------------------------

class TestServerGetProblemsByCategory:
    def test_delegates_to_tools(self):
        expected = ["10", "20", "30"]
        with _patch_tools("get_problems_by_category", return_value=expected) as mock:
            result = server.get_problems_by_category("phys", "55")
        mock.assert_called_once_with("phys", "55")
        assert result == expected

    def test_value_error_returns_error_in_list(self):
        with _patch_tools("get_problems_by_category", side_effect=ValueError("bad subject")):
            result = server.get_problems_by_category("bad", "1")
        assert isinstance(result, list)
        assert "bad subject" in result[0]

    def test_unexpected_exception_returns_error_in_list(self):
        with _patch_tools("get_problems_by_category", side_effect=Exception("fail")):
            result = server.get_problems_by_category("math", "1")
        assert isinstance(result, list)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# generate_test wrapper — critically tests int key conversion
# ---------------------------------------------------------------------------

class TestServerGenerateTest:
    def test_string_keys_converted_to_int(self):
        """JSON always delivers dict keys as strings; server must convert to int."""
        expected = {"test_id": "T1", "pdf_url": "https://..."}
        with _patch_tools("generate_test", return_value=expected) as mock:
            result = server.generate_test("math", {"1": 1, "2": 2, "3": 1})
        mock.assert_called_once_with("math", {1: 1, 2: 2, 3: 1})
        assert result == expected

    def test_int_keys_also_work(self):
        expected = {"test_id": "T2", "pdf_url": None}
        with _patch_tools("generate_test", return_value=expected) as mock:
            result = server.generate_test("inf", {1: 1, 5: 2})
        mock.assert_called_once_with("inf", {1: 1, 5: 2})

    def test_value_error_returns_error_dict(self):
        with _patch_tools("generate_test", side_effect=ValueError("bad subject")):
            result = server.generate_test("bad", {"1": 1})
        assert "error" in result

    def test_non_numeric_key_raises_and_returns_error(self):
        """Non-integer string keys should cause an exception caught by the wrapper."""
        result = server.generate_test("math", {"abc": 1})
        assert "error" in result

    def test_unexpected_exception_returns_error_dict(self):
        with _patch_tools("generate_test", side_effect=RuntimeError("net")):
            result = server.generate_test("math", {"1": 1})
        assert "error" in result


# ---------------------------------------------------------------------------
# get_problem_batch wrapper
# ---------------------------------------------------------------------------

class TestServerGetProblemBatch:
    def test_delegates_to_tools(self):
        expected = [{"id": "1"}, {"id": "2"}]
        with _patch_tools("get_problem_batch", return_value=expected) as mock:
            result = server.get_problem_batch("math", ["1", "2"])
        mock.assert_called_once_with("math", ["1", "2"])
        assert result == expected

    def test_value_error_returns_error_list(self):
        with _patch_tools("get_problem_batch", side_effect=ValueError("bad")):
            result = server.get_problem_batch("bad", ["1"])
        assert "error" in result[0]

    def test_unexpected_exception_returns_error_list(self):
        with _patch_tools("get_problem_batch", side_effect=Exception("fail")):
            result = server.get_problem_batch("math", ["1"])
        assert "error" in result[0]
