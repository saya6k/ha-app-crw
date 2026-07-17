"""Tool logic for the crw MCP bridge — pure formatting plus backend calls.

Kept import-light (no mcp dependency) so unit tests run anywhere.
"""

import os

import httpx

CRW_URL = os.environ.get("BRIDGE_CRW_URL", "http://127.0.0.1:3000")
SCRAPE_TIMEOUT_S = 60

# Cap what a single tool call feeds back into the LLM context.
MAX_MARKDOWN_CHARS = 16000


def format_scrape_response(payload: dict, url: str) -> dict:
    """Map a crw /v1/scrape response onto the tool result shape."""
    if not payload.get("success"):
        return {"error": payload.get("error") or "scrape failed", "url": url}
    data = payload.get("data") or {}
    markdown = data.get("markdown") or ""
    meta = data.get("metadata") or {}
    return {
        "url": meta.get("sourceURL") or url,
        "title": meta.get("title"),
        "status_code": meta.get("statusCode"),
        "markdown": markdown[:MAX_MARKDOWN_CHARS],
        "truncated": len(markdown) > MAX_MARKDOWN_CHARS,
    }


async def scrape(url: str) -> dict:
    """Fetch a page as markdown via crw-server."""
    try:
        async with httpx.AsyncClient(timeout=SCRAPE_TIMEOUT_S) as client:
            resp = await client.post(f"{CRW_URL}/v1/scrape", json={"url": url})
            payload = resp.json()
    except httpx.HTTPError as err:
        return {"error": f"scrape request failed: {err}", "url": url}
    return format_scrape_response(payload, url)
