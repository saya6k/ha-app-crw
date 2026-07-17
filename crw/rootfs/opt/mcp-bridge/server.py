"""crw MCP bridge — streamable HTTP server for Home Assistant's MCP client."""

import logging

from mcp.server.fastmcp import FastMCP

import tools

logging.basicConfig(level=logging.INFO, format="[mcp-bridge] %(message)s")

mcp = FastMCP(
    "CRW Web Tools",
    host="0.0.0.0",
    port=8099,
    stateless_http=True,
)


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


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
