"""
sdamgia-mcp — MCP server wrapping the sdamgia-api library.

Transport is configured via environment variables (see .env.example):
  MCP_TRANSPORT=stdio   — local mode for Claude Desktop / mcp dev (default)
  MCP_TRANSPORT=sse     — HTTP/SSE mode for remote access via cloudflared
  HOST=0.0.0.0          — bind address for SSE mode (default: 0.0.0.0)
  PORT=8080             — port for SSE mode (default: 8080)

Quick start
-----------
Local (stdio):
    python server.py
    mcp dev server.py          # with MCP Inspector UI

Remote (SSE + cloudflared):
    cp .env.example .env
    # edit .env: set MCP_TRANSPORT=sse
    python server.py &
    cloudflared tunnel --url http://localhost:8080
    # paste the *.trycloudflare.com URL into Claude.ai → Settings → Connectors
"""

import os
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

import sdamgia_tools as tools

load_dotenv()

_transport = os.getenv("MCP_TRANSPORT", "stdio")
_host = os.getenv("HOST", "0.0.0.0")
_port = int(os.getenv("PORT", "8080"))

mcp = FastMCP("sdamgia-mcp", host=_host, port=_port)


# ---------------------------------------------------------------------------
# Tool: search_problems
# ---------------------------------------------------------------------------

@mcp.tool()
def search_problems(subject: str, query: str, limit: int = 20) -> list[dict]:
    """
    Search for exam problems (ЕГЭ/ОГЭ) by text query on sdamgia.ru.

    Each result contains the problem ID and a short preview of the condition.
    Note: sdamgia.ru is scraped, not a REST API — each request may take 1-3 seconds.

    Args:
        subject: Subject name in Russian or English code.
                 Examples: "математика профиль", "math", "физика", "phys",
                 "информатика", "inf", "русский", "rus", "английский", "en".
        query:   Text to search for, e.g. "логарифмы", "производная", "ДНК".
        limit:   Maximum number of results to return (default 20, max 20).

    Returns:
        List of {"id": str, "condition_preview": str} dicts.
    """
    try:
        return tools.search_problems(subject, query, limit)
    except ValueError as exc:
        return [{"error": str(exc)}]
    except Exception as exc:
        print(f"[sdamgia-mcp] search_problems error: {exc}", file=sys.stderr)
        return [{"error": f"Search failed: {exc}"}]


# ---------------------------------------------------------------------------
# Tool: get_problem
# ---------------------------------------------------------------------------

@mcp.tool()
def get_problem(subject: str, problem_id: str) -> dict:
    """
    Fetch full details of a single exam problem from sdamgia.ru.

    Returns the problem condition (statement), solution, answer, a list of
    analog problem IDs, and the direct URL to the problem page.
    Image URLs are included when the condition or solution contains figures.
    Note: may take 1-3 seconds per request.

    Args:
        subject:    Subject name in Russian or English code.
                    Examples: "математика профиль", "math", "физика", "phys".
        problem_id: Numeric problem ID as a string, e.g. "77345".

    Returns:
        Dict with keys: id, subject, topic, condition (text + images?), solution
        (text + images?), answer, analogs (list of IDs), url.
        On error: {"error": "..."}.
    """
    try:
        return tools.get_problem(subject, problem_id)
    except ValueError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        print(f"[sdamgia-mcp] get_problem error: {exc}", file=sys.stderr)
        return {"error": f"Failed to fetch problem {problem_id}: {exc}"}


# ---------------------------------------------------------------------------
# Tool: get_catalog
# ---------------------------------------------------------------------------

@mcp.tool()
def get_catalog(subject: str) -> list[dict]:
    """
    Get the full problem catalog for a subject, organized as topics and categories.

    Use this to discover topic numbers before calling generate_test, or to find
    category IDs before calling get_problems_by_category.
    Note: may take 1-3 seconds.

    Args:
        subject: Subject name in Russian or English code.
                 Examples: "математика профиль", "math", "информатика", "inf".

    Returns:
        List of topic dicts: {topic_id, topic_name, categories: [{category_id,
        category_name}]}.
    """
    try:
        return tools.get_catalog(subject)
    except ValueError as exc:
        return [{"error": str(exc)}]
    except Exception as exc:
        print(f"[sdamgia-mcp] get_catalog error: {exc}", file=sys.stderr)
        return [{"error": f"Failed to fetch catalog: {exc}"}]


# ---------------------------------------------------------------------------
# Tool: get_problems_by_category
# ---------------------------------------------------------------------------

@mcp.tool()
def get_problems_by_category(subject: str, category_id: str) -> list[str]:
    """
    Get all problem IDs within a specific catalog category on sdamgia.ru.

    Use get_catalog first to discover category IDs.
    Note: may take 1-3 seconds.

    Args:
        subject:     Subject name in Russian or English code.
        category_id: Category ID string obtained from get_catalog.

    Returns:
        List of problem ID strings. On error, list with a single error string.
    """
    try:
        return tools.get_problems_by_category(subject, category_id)
    except ValueError as exc:
        return [str(exc)]
    except Exception as exc:
        print(f"[sdamgia-mcp] get_problems_by_category error: {exc}", file=sys.stderr)
        return [f"Failed to fetch category {category_id}: {exc}"]


# ---------------------------------------------------------------------------
# Tool: generate_test
# ---------------------------------------------------------------------------

@mcp.tool()
def generate_test(subject: str, topics: dict) -> dict:
    """
    Generate a custom exam variant (тест / вариант) on sdamgia.ru.

    The server picks random problems from the specified topics, assembles a
    test, and returns a direct PDF download link (horizontal layout).
    Note: may take 2-5 seconds.

    Args:
        subject: Subject name in Russian or English code.
                 Examples: "математика профиль", "информатика", "inf".
        topics:  Dict mapping topic_number (int or string key) to the number of
                 problems from that topic (int).
                 Example: {"1": 1, "2": 1, "3": 2} — 1 problem from topic 1,
                 1 from topic 2, 2 from topic 3.
                 Use get_catalog to discover valid topic numbers.

    Returns:
        Dict with {"test_id": str, "pdf_url": str | null}.
        On error: {"error": "..."}.
    """
    try:
        int_topics = {int(k): int(v) for k, v in topics.items()}
        return tools.generate_test(subject, int_topics)
    except ValueError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        print(f"[sdamgia-mcp] generate_test error: {exc}", file=sys.stderr)
        return {"error": f"Failed to generate test: {exc}"}


# ---------------------------------------------------------------------------
# Tool: get_problem_batch
# ---------------------------------------------------------------------------

@mcp.tool()
def get_problem_batch(subject: str, problem_ids: list[str]) -> list[dict]:
    """
    Fetch multiple exam problems at once by their IDs (max 20 per call).

    Problems are fetched sequentially with a 0.3-second delay between requests
    to avoid rate limiting. Expect roughly 1-4 seconds per problem.

    Args:
        subject:     Subject name in Russian or English code.
        problem_ids: List of problem ID strings (max 20). IDs beyond 20 are ignored.

    Returns:
        List of full problem dicts (same schema as get_problem).
    """
    try:
        return tools.get_problem_batch(subject, problem_ids)
    except ValueError as exc:
        return [{"error": str(exc)}]
    except Exception as exc:
        print(f"[sdamgia-mcp] get_problem_batch error: {exc}", file=sys.stderr)
        return [{"error": f"Batch fetch failed: {exc}"}]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the MCP server using the transport configured in environment variables."""
    mcp.run(transport=_transport)


if __name__ == "__main__":
    main()
