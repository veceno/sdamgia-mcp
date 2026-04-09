# Changelog

All notable changes to sdamgia-mcp are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [1.0.0] — 2026-04-09

Initial release.

### Added

- **`search_problems`** — search ЕГЭ/ОГЭ problems by text query; returns IDs + condition previews
- **`get_problem`** — fetch full problem details: condition, solution, answer, image URLs, analog IDs
- **`get_catalog`** — browse the full topic/category tree for any subject
- **`get_problems_by_category`** — list all problem IDs within a catalog category
- **`generate_test`** — generate a custom exam variant and return a PDF download link (horizontal layout)
- **`get_problem_batch`** — fetch up to 20 problems in one call with rate-limit protection
- Subject alias resolution: accepts Russian names ("математика профиль", "физика") and English codes ("math", "phys") in every tool; case-insensitive, whitespace-tolerant
- Supported subjects: math, mathb, rus, inf, phys, chem, bio, hist, soc, en, geo, lit
- `\xa0` / zero-width space stripping from all scraped text
- Retry-once logic (1 s delay) for transient network errors
- Transport configured via environment variables: `MCP_TRANSPORT`, `HOST`, `PORT`
- stdio transport (default) for Claude Desktop / `mcp dev`
- SSE transport for remote access via cloudflared tunnel
- 119-test suite (mocked, offline, < 1 s)
