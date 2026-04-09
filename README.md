# sdamgia-mcp

An MCP (Model Context Protocol) server that wraps the [sdamgia-api](https://pypi.org/project/sdamgia-api/) library, giving Claude direct access to the [sdamgia.ru](https://sdamgia.ru) problem bank for ЕГЭ/ОГЭ exam preparation.

## Features

- Search exam problems by text query
- Fetch full problem details (condition, solution, answer, images)
- Browse the topic/category catalog
- List all problems in a category
- Generate custom test variants and download them as PDF
- Batch-fetch multiple problems at once

## Requirements

- Python 3.11+
- pip

## Installation

```bash
git clone https://github.com/veceno/sdamgia-mcp.git
cd sdamgia-mcp
pip install -r requirements.txt
```

## Running locally (stdio transport)

This is the default mode for use with **Claude Desktop** or the MCP inspector.

```bash
python server.py
```

Or use the MCP inspector to test interactively:

```bash
mcp dev server.py
```

### Claude Desktop configuration

Add the following to your Claude Desktop `claude_desktop_config.json`:

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

## Running remotely via SSE + cloudflared

Use this to connect from **Claude.ai** (web) as a remote connector.

### 1. Switch to SSE transport

Edit the last few lines of `server.py`:

```python
# Replace:
mcp.run()

# With:
mcp.run(transport="sse", host="0.0.0.0", port=8080)
```

Or set `HOST` / `PORT` in a `.env` file (copy `.env.example` → `.env`).

### 2. Start the server

```bash
python server.py
```

### 3. Create a cloudflared tunnel

```bash
cloudflared tunnel --url http://localhost:8080
```

Copy the generated URL (e.g. `https://xyz.trycloudflare.com`).

### 4. Add to Claude.ai

Go to **Settings → Connectors → Add remote MCP server** and paste the tunnel URL.

## Example Claude prompts

| Prompt | Tool triggered |
|--------|---------------|
| "Найди задачи по теме логарифмы для ЕГЭ профмат" | `search_problems` |
| "Дай мне задачу №77345 по математике с решением" | `get_problem` |
| "Сгенерируй вариант ЕГЭ по информатике: по 1 задаче из заданий 1-27" | `get_catalog` + `generate_test` |
| "Покажи каталог тем по физике" | `get_catalog` |
| "Покажи все задачи из категории 123 по химии" | `get_problems_by_category` |
| "Покажи задачи 100, 200, 300 по биологии" | `get_problem_batch` |

## Subject reference

| English code | Russian names |
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
| `eng` | английский, английский язык |
| `geo` | география |
| `lit` | литература |

Both Russian aliases and English codes are accepted by all tools.

## Notes

- sdamgia-api scrapes HTML pages rather than calling a REST API, so each request takes **1-3 seconds**. Claude will mention this when using the tools.
- `get_problem_batch` fetches problems **sequentially** with a 0.3-second delay between requests to avoid rate limiting.
- No authentication is required — sdamgia.ru is publicly accessible.

## License

MIT
