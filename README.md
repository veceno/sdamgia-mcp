# sdamgia-mcp

An [MCP](https://modelcontextprotocol.io) server that gives Claude direct access to the [sdamgia.ru](https://sdamgia.ru) problem bank — the largest Russian ЕГЭ/ОГЭ exam preparation resource. Built on the [sdamgia-api](https://pypi.org/project/sdamgia-api/) library.

---

## Table of contents

1. [Features](#features)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Running locally (stdio)](#running-locally-stdio)
5. [Running remotely via SSE + cloudflared](#running-remotely-via-sse--cloudflared)
6. [Configuration reference](#configuration-reference)
7. [Available tools](#available-tools)
8. [Subject reference](#subject-reference)
9. [Example Claude prompts](#example-claude-prompts)
10. [Testing](#testing)
11. [Architecture](#architecture)
12. [License](#license)

---

## Features

| Tool | What it does |
|------|-------------|
| `search_problems` | Search problems by text query, returns IDs + condition previews |
| `get_problem` | Fetch full problem details — condition, solution, answer, image URLs |
| `get_catalog` | Browse the full topic/category tree for a subject |
| `get_problems_by_category` | List all problem IDs within a category |
| `generate_test` | Generate a custom exam variant and get a PDF download link |
| `get_problem_batch` | Fetch up to 20 problems in one call |

All tools accept subject names in **Russian** ("математика профиль", "физика") or **English codes** ("math", "phys").

---

## Requirements

- Python 3.11+
- pip

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/veceno/sdamgia-mcp.git
cd sdamgia-mcp
```

### 2. Install dependencies

**Standard install (try this first):**

```bash
pip install -r requirements.txt
```

**If you get a `grabzit` build error** (known issue on some systems — grabzit is an optional screenshot dependency that sdamgia-api doesn't actually need for our use case):

```bash
pip install --no-deps sdamgia-api
pip install -r requirements.txt
```

### 3. (Optional) Copy config

```bash
cp .env.example .env
# Edit .env to change transport, host, or port
```

---

## Running locally (stdio)

Stdio transport is the default — Claude Desktop and `mcp dev` communicate with the server over stdin/stdout.

```bash
python server.py
```

Or use the MCP Inspector for interactive testing:

```bash
mcp dev server.py
```

### Claude Desktop configuration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sdamgia": {
      "command": "python",
      "args": ["/absolute/path/to/sdamgia-mcp/server.py"]
    }
  }
}
```

Config file locations:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

---

## Running remotely via SSE + cloudflared

Use this to connect from [Claude.ai](https://claude.ai) (web) as a remote connector — no installation needed on Claude's side.

### 1. Configure SSE mode

Edit `.env` (copy from `.env.example` first):

```env
MCP_TRANSPORT=sse
HOST=0.0.0.0
PORT=8080
```

Or pass via environment directly:

```bash
MCP_TRANSPORT=sse PORT=8080 python server.py
```

### 2. Start the server

```bash
python server.py
# Server is now listening on http://0.0.0.0:8080
```

### 3. Create a cloudflared tunnel

```bash
cloudflared tunnel --url http://localhost:8080
```

Copy the generated URL (e.g. `https://xyz.trycloudflare.com`).

### 4. Add to Claude.ai

Go to **Settings → Connectors → Add remote MCP server** and paste the tunnel URL.

---

## Configuration reference

All settings are read from environment variables (or `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | Transport: `stdio` for local, `sse` for remote |
| `HOST` | `0.0.0.0` | Bind address (SSE mode only) |
| `PORT` | `8080` | Port number (SSE mode only) |

---

## Available tools

### `search_problems`

Search problems by text query. Returns IDs and short condition previews.

```
subject: str       — subject name or code (see Subject reference)
query:   str       — search text, e.g. "логарифмы", "ДНК", "второй закон Ньютона"
limit:   int = 20  — max results (capped at 20)
```

Returns: `[{"id": "...", "condition_preview": "..."}, ...]`

---

### `get_problem`

Fetch full problem details. Includes condition, solution, answer, image URLs, and analog IDs.

```
subject:    str  — subject name or code
problem_id: str  — problem ID, e.g. "77345"
```

Returns:
```json
{
  "id": "77345",
  "subject": "math",
  "topic": "Логарифмические уравнения",
  "condition": {"text": "...", "images": ["https://..."]},
  "solution":  {"text": "..."},
  "answer": "3",
  "analogs": ["77346", "77347"],
  "url": "https://math-ege.sdamgia.ru/problem?id=77345"
}
```

Images key is omitted if there are no images in that part.

---

### `get_catalog`

Get the full topic/category tree for a subject.

```
subject: str  — subject name or code
```

Returns:
```json
[
  {
    "topic_id": "1",
    "topic_name": "Простейшие математические модели",
    "categories": [
      {"category_id": "10", "category_name": "Линейные уравнения"},
      {"category_id": "11", "category_name": "Квадратные уравнения"}
    ]
  }
]
```

---

### `get_problems_by_category`

List all problem IDs in a specific category. Use `get_catalog` to find category IDs.

```
subject:     str  — subject name or code
category_id: str  — category ID from get_catalog
```

Returns: `["101", "102", "103", ...]`

---

### `generate_test`

Generate a custom exam variant on sdamgia.ru and return a PDF link.

```
subject: str   — subject name or code
topics:  dict  — {topic_number: problem_count, ...}
               Example: {"1": 1, "2": 1, "3": 2}
               Use get_catalog to find valid topic numbers
```

Returns:
```json
{"test_id": "abc123", "pdf_url": "https://math-ege.sdamgia.ru/..."}
```

The PDF uses horizontal (landscape) layout. `pdf_url` is `null` if PDF generation failed (the test itself is still created and accessible via `test_id`).

---

### `get_problem_batch`

Fetch multiple problems in one call. Problems are fetched sequentially with 0.3 s delays.

```
subject:     str        — subject name or code
problem_ids: list[str]  — up to 20 problem IDs (extras are ignored)
```

Returns: list of full problem dicts (same schema as `get_problem`).

---

## Subject reference

Both English codes and Russian aliases are accepted by every tool.

| English code | Russian aliases |
|---|---|
| `math` | математика профиль, профмат, профильная математика |
| `mathb` | математика база, матбаза, базовая математика |
| `rus` | русский, русский язык |
| `inf` | информатика |
| `phys` | физика |
| `chem` | химия |
| `bio` | биология |
| `hist` | история |
| `soc` | обществознание, общество |
| `en` | английский, английский язык, eng |
| `geo` | география |
| `lit` | литература |

Subject names are case-insensitive and trimmed: `"  ФИЗИКА  "` → `phys`.

---

## Example Claude prompts

| Prompt | Tools used |
|--------|-----------|
| "Найди задачи по теме логарифмы для ЕГЭ профмат" | `search_problems` |
| "Дай мне задачу №77345 по математике с решением" | `get_problem` |
| "Сгенерируй вариант ЕГЭ по информатике: по 1 задаче из каждого задания 1-27" | `get_catalog` → `generate_test` |
| "Покажи каталог тем по физике" | `get_catalog` |
| "Покажи все задачи из категории 123 по химии" | `get_problems_by_category` |
| "Дай мне задачи 100, 200 и 300 по биологии" | `get_problem_batch` |
| "Найди аналоги к задаче 77345 и покажи их все" | `get_problem` → `get_problem_batch` |

---

## Testing

```bash
python -m pytest tests/ -v
```

The test suite has **119 tests** across three files. All SdamGIA HTTP calls are mocked — tests run offline in under 1 second.

| File | Coverage |
|------|---------|
| `tests/test_subject_resolution.py` | All aliases, case tolerance, `_clean()` |
| `tests/test_tools.py` | All 6 tool functions — happy paths, errors, retries, delays |
| `tests/test_server.py` | MCP wrapper layer, JSON key conversion, error propagation |

---

## Architecture

```
Claude
  │  MCP protocol (stdio or SSE)
  ▼
server.py          — FastMCP tool definitions, transport config, error handling
  │
  ▼
sdamgia_tools.py   — sdamgia-api wrappers, subject resolution, text cleanup, retry logic
  │
  ▼
sdamgia-api        — HTML scraping of sdamgia.ru (requests + BeautifulSoup)
  │  HTTP
  ▼
sdamgia.ru         — exam problem bank
```

**Notes:**
- sdamgia-api scrapes HTML, not a REST API → each request takes 1–3 s. Tool docstrings mention this so Claude sets user expectations.
- Errors are logged to **stderr** (stdout is reserved for the MCP protocol in stdio mode).
- `get_problem_batch` fetches sequentially with 0.3 s gaps to avoid rate-limiting.
- Retry logic: each sdamgia call retries once after 1 s on transient failure.

---

## License

MIT
