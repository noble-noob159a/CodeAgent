import os
import sys
import asyncio
import requests
from bs4 import BeautifulSoup
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from dotenv import load_dotenv
server = Server("workspace-server")
load_dotenv()
PROXY_URL = os.environ.get("HTTP_PROXY") or None


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="read_file",
            description="Reads the text contents of a file inside the local workspace.",
            inputSchema={
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Relative path to the file."}},
                "required": ["path"],
            },
        ),
        types.Tool(
            name="write_file",
            description="Writes or overwrites text/code content to a local file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path where the file should be saved."},
                    "content": {"type": "string", "description": "The exact string content or code block."}
                },
                "required": ["path", "content"],
            },
        ),
        types.Tool(
            name="web_search",
            description="Searches the live internet for up-to-date documentation, technical explanations, or programming errors.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query (e.g., 'What's the weather today at Japan?')"}
                },
                "required": ["query"],
            },
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    if not arguments:
        raise ValueError("Missing tool arguments")


    if name == "read_file":
        path = arguments.get("path")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return [types.TextContent(type="text", text=f.read())]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error reading file: {str(e)}")]


    elif name == "write_file":
        path = arguments.get("path")
        content = arguments.get("content")
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return [types.TextContent(type="text", text=f"Successfully wrote to {path}")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error writing file: {str(e)}")]


    elif name == "web_search":
        query = arguments.get("query")
        try:
            proxies = {"http": PROXY_URL, "https": PROXY_URL}
            url = "https://html.duckduckgo.com/html/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            data = {"q": query}
            response = requests.post(
                url,
                data=data,
                headers=headers,
                proxies=proxies,
                verify=False,
                timeout=15
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            if not soup:
                return [types.TextContent(type="text", text="Error: Search tool returned an empty response.")]
            results = []
            for result in soup.find_all('div', class_='result'):
                title_tag = result.find('h2', class_='result__title')
                snippet_tag = result.find('a', class_='result__snippet')
               
                if title_tag and snippet_tag:
                    title = title_tag.text.strip()
                    link = snippet_tag.get('href', '')
                    snippet = snippet_tag.text.strip()
                    results.append(f"Title: {title}\nLink: {link}\nSnippet: {snippet}\n---")


            output = "\n".join(results[:5])
            return [types.TextContent(type="text", text=output)]  
       
            # with DDGS(proxies=proxies, timeout=10) as ddgs:
            #     # Fetch text results
            #     raw_results = ddgs.text(query, max_results=4)
               
            #     if not raw_results:
            #         return [types.TextContent(type="text", text="Error: DuckDuckGo returned an empty response. Your proxy or IP might be rate-limited.")]
               
            #     results = []
            #     for item in raw_results:
            #         title = item.get("title", "No Title")
            #         snippet = item.get("body", "No Snippet")
            #         link = item.get("href", "")
            #         results.append(f"Title: {title}\nLink: {link}\nSnippet: {snippet}\n---")
               
            #     output = "\n".join(results)
            #     return [types.TextContent(type="text", text=output)]
                       
        except Exception as e:
            return [types.TextContent(type="text", text=f"Search failed: {str(e)}")]


    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    print("Starting MCP Workspace Server...", file=sys.stderr)
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="cv-workspace-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())

