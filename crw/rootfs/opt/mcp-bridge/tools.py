"""Tool logic for the crw MCP bridge — pure formatting plus backend calls.

Kept import-light (no mcp dependency) so unit tests run anywhere.
"""

import os
from urllib.parse import urlparse

import httpx

CRW_URL = os.environ.get("BRIDGE_CRW_URL", "http://127.0.0.1:3000")
SCRAPE_TIMEOUT_S = 60
SEARCH_TIMEOUT_S = 30
DEFAULT_MAX_RESULTS = 3

# Cap what a single tool call feeds back into the LLM context.
MAX_MARKDOWN_CHARS = 16000

# Result scheme mirrors voice-satellite-card-llm-tools so a future companion
# integration (or card-side MCP trace support) can render these visually.
SEARCH_INSTRUCTION = (
    "Summarize the key information from these search results in 2-3 concise "
    "sentences. Do NOT list individual URLs, titles, or sources. The user "
    "cannot see the raw results — synthesize the information into a helpful "
    "answer."
)


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


def _site_name(url: str) -> str:
    hostname = urlparse(url).hostname or ""
    return hostname.removeprefix("www.")


def effective_limit(requested: int | None) -> int:
    """Clamp the requested result count to the configured maximum."""
    try:
        cap = int(os.environ.get("BRIDGE_MAX_RESULTS", DEFAULT_MAX_RESULTS))
    except ValueError:
        cap = DEFAULT_MAX_RESULTS
    if requested is None:
        return cap
    return max(1, min(requested, cap))


def format_search_response(payload: dict, query: str) -> dict:
    """Map a crw /v1/search response onto the voice-satellite card scheme."""
    if not payload.get("success"):
        return {"error": payload.get("error") or "search failed", "query": query}
    rows = (payload.get("data") or {}).get("results") or []
    results = [
        {
            "url": r.get("url", ""),
            "title": r.get("title", ""),
            "snippet": r.get("snippet") or r.get("description") or "",
            "site_name": _site_name(r.get("url", "")),
        }
        for r in rows
    ]
    featured = next(
        (
            r["thumbnailUrl"]
            for r in rows
            if str(r.get("thumbnailUrl", "")).startswith("http")
        ),
        None,
    )
    out = {
        "source": "searxng",
        "query": query,
        "num_results": len(results),
        "results": results,
        "featured_image": featured,
        "instruction": SEARCH_INSTRUCTION,
    }
    if not results:
        out["message"] = "No results found for this query."
    return out


async def search(query: str, num_results: int | None = None) -> dict:
    """Search the web via crw /v1/search (SearXNG-backed)."""
    limit = effective_limit(num_results)
    try:
        async with httpx.AsyncClient(timeout=SEARCH_TIMEOUT_S) as client:
            resp = await client.post(
                f"{CRW_URL}/v1/search", json={"query": query, "limit": limit}
            )
            payload = resp.json()
    except httpx.HTTPError as err:
        return {"error": f"search request failed: {err}", "query": query}
    return format_search_response(payload, query)


async def scrape(url: str) -> dict:
    """Fetch a page as markdown via crw-server."""
    try:
        async with httpx.AsyncClient(timeout=SCRAPE_TIMEOUT_S) as client:
            resp = await client.post(f"{CRW_URL}/v1/scrape", json={"url": url})
            payload = resp.json()
    except httpx.HTTPError as err:
        return {"error": f"scrape request failed: {err}", "url": url}
    return format_scrape_response(payload, url)
