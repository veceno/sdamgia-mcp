"""
sdamgia-mcp — MCP server wrapping the sdamgia-api library.

HOW TO RUN
----------

Local (stdio) — for use with Claude Desktop / mcp dev:
    python server.py
    # or
    mcp dev server.py

Remote (SSE) — expose via cloudflared for Claude.ai remote connectors:
    # 1. Start the SSE server:
    #    Edit the last block below: replace mcp.run() with
    #    mcp.run(transport="sse", host="0.0.0.0", port=8080)
    # 2. In a separate terminal:
    #    cloudflared tunnel --url http://localhost:8080
    # 3. Copy the generated *.trycloudflare.com URL into Claude.ai
    #    Settings → Connectors → Add → paste the URL.
"""

import sys

from mcp.server.fastmcp import FastMCP

import sdamgia_tools as tools

mcp = FastMCP("sdamgia-mcp")


# ---------------------------------------------------------------------------
# Tool: search_problems
# ---------------------------------------------------------------------------

@mcp.tool()
def search_problems(subject: str, query: str, limit: int = 20) -> list[dict]:
    """
    Search for exam problems (ЕГЭ/ОГЭ) by text query on sdamgia.ru.

    Each result contains the problem ID and a short preview of the condition.
    Note: sdamgia.ru is a web scraper; each request may take 1-3 seconds.

    Args:
        subject: Subject name in Russian or English code.
                 Examples: "математика профиль", "math", "физика", "phys",
                 "информатика", "inf", "русский", "rus", etc.
        query:   Text to search for, e.g. "логарифмы", "производная", "ДНК".
        limit:   Maximum number of results to return (default 20, max 20).

    Returns:
        List of {"id": str, "condition_preview": str} dicts.
    """
    try:
        return tools.search_problems(subject, query, limit)
    except ValueError as exc:
        # Subject resolution error — surface as readable message
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
        Dict with keys: id, subject, condition (text + images), solution
        (text + images), answer, analogs (list of IDs), url.
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

    Use this to discover what topic numbers exist before calling generate_test,
    or to find category IDs before calling get_problems_by_category.
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
        topics:  Dict mapping topic_number (int, as string key in JSON) to the
                 number of problems from that topic (int).
                 Example: {"1": 1, "2": 1, "3": 2} — 1 problem from topic 1,
                 1 from topic 2, 2 from topic 3.
                 Use get_catalog to discover valid topic numbers.

    Returns:
        Dict with {"test_id": str, "pdf_url": str | null}.
        On error: {"error": "..."}.
    """
    try:
        # JSON keys are always strings; convert to int keys as the library expects.
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

if __name__ == "__main__":
    # Default: stdio transport for local use with Claude Desktop / mcp dev.
    # To switch to SSE for remote access:
    #   mcp.run(transport="sse", host="0.0.0.0", port=8080)
    mcp.run()
