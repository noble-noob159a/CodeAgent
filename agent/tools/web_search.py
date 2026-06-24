from __future__ import annotations

import os

import requests
from bs4 import BeautifulSoup
import mcp.types as types

from .util import ToolSpec

DESCRIPTION = "Searches the live internet for up-to-date documentation, technical explanations, or programming errors."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The search query (e.g., 'What's the weather today at Japan?')",
        }
    },
    "required": ["query"],
}


async def call_tool(arguments: dict | None) -> list[types.TextContent]:
    if not arguments:
        raise ValueError("Missing tool arguments")

    query = arguments.get("query")
    proxy_url = os.environ.get("HTTP_PROXY") or None

    try:
        proxies = {"http": proxy_url, "https": proxy_url}
        response = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
            },
            proxies=proxies,
            verify=False,
            timeout=15,
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        if not soup:
            return [types.TextContent(type="text", text="Error: Search tool returned an empty response.")]

        results: list[str] = []
        for result in soup.find_all("div", class_="result"):
            title_tag = result.find("h2", class_="result__title")
            snippet_tag = result.find("a", class_="result__snippet")

            if title_tag and snippet_tag:
                title = title_tag.text.strip()
                link = snippet_tag.get("href", "")
                snippet = snippet_tag.text.strip()
                results.append(f"Title: {title}\nLink: {link}\nSnippet: {snippet}\n---")

        output = "\n".join(results[:5])
        return [types.TextContent(type="text", text=output or "No results found.")]
    except Exception as exc:
        return [types.TextContent(type="text", text=f"Search failed: {exc}")]


TOOL_SPEC = ToolSpec(
    name="web_search",
    description=DESCRIPTION,
    input_schema=INPUT_SCHEMA,
    call_tool=call_tool,
)
