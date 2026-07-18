"""crw MCP bridge — streamable HTTP server for Home Assistant's MCP client."""

import json
import logging
import os

from mcp.server.fastmcp import FastMCP

import tools
from providers import engines_for_tool, missing_key_hints

logging.basicConfig(level=logging.INFO, format="[mcp-bridge] %(message)s")
log = logging.getLogger(__name__)

mcp = FastMCP(
    "CRW Web Tools",
    host="0.0.0.0",
    port=8099,
    stateless_http=True,
)


def load_options() -> dict:
    """Add-on options; tolerate absence for bare-docker smoke runs."""
    path = os.environ.get("BRIDGE_OPTIONS_PATH", "/data/options.json")
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


@mcp.tool()
async def web_search(query: str, num_results: int | None = None) -> dict:
    """Search the internet for current information on a topic.

    Use this when the user asks a question requiring current information,
    facts, or general knowledge. Returns web results with titles and
    snippets — follow the returned instruction when answering.
    """
    return await tools.search(query, num_results)


@mcp.tool()
async def web_scrape(url: str) -> dict:
    """Fetch a web page and return its main content as markdown.

    Use this when the user shares a URL or asks about the content of a
    specific page. Summarize the returned markdown for the user.
    """
    return await tools.scrape(url)


def register_provider_tools(options: dict) -> list[str]:
    """Register media/news/wiki tools for tools with configured providers."""
    active: list[str] = []

    video_engines = engines_for_tool("video", options)
    if video_engines:
        @mcp.tool()
        async def video_search(query: str, num_results: int | None = None) -> dict:
            """Search for videos on the configured video platforms.

            Use this when the user asks for a video, clip, or something to
            watch. Follow the returned instruction when answering.
            """
            return await tools.engines_search(
                "videos", video_engines, query, num_results
            )
        active.append("video_search")

    image_engines = engines_for_tool("image", options)
    if image_engines:
        @mcp.tool()
        async def image_search(query: str, num_results: int | None = None) -> dict:
            """Search for images.

            Use this when the user asks to see a picture or photo of
            something. Follow the returned instruction when answering.
            """
            return await tools.engines_search(
                "images", image_engines, query, num_results
            )
        active.append("image_search")

    news_engines = engines_for_tool("news", options)
    if news_engines:
        @mcp.tool()
        async def news_search(query: str, num_results: int | None = None) -> dict:
            """Search recent news coverage on the configured news sources.

            Use this when the user asks about current events or headlines.
            Follow the returned instruction when answering.
            """
            return await tools.engines_search(
                "news", news_engines, query, num_results
            )
        active.append("news_search")

    wiki_engines = engines_for_tool("wiki", options)
    if wiki_engines:
        @mcp.tool()
        async def wiki_search(query: str, num_results: int | None = None) -> dict:
            """Look up encyclopedic knowledge on the configured wikis.

            Use this for definitions, historical facts, and general
            reference questions. Follow the returned instruction.
            """
            return await tools.engines_search(
                "wiki", wiki_engines, query, num_results
            )
        active.append("wiki_search")

    return active


if __name__ == "__main__":
    options = load_options()
    extra = register_provider_tools(options)
    for hint in missing_key_hints(options):
        log.info(hint)
    log.info(
        "tools: web_search, web_scrape%s",
        (", " + ", ".join(extra)) if extra else " (no provider tools configured)",
    )
    mcp.run(transport="streamable-http")
