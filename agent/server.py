from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv()

server = Server("workspace-server")

from agent.tools import get_tool_map, get_tool_specs


tool_map = None  # Initialize tool_map to None
tool_lists = None  # Initialize tool_lists to None

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return tool_lists


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    if not arguments:
        raise ValueError("Missing tool arguments")

    
    tool = tool_map.get(name)
    if tool is None:
        raise ValueError(f"Unknown tool: {name}")

    return await tool.call_tool(arguments)


async def main():
    global tool_map, tool_lists
    tool_lists = [tool_spec.to_mcp_tool() for tool_spec in get_tool_specs()]
    tool_map = get_tool_map()
    print("Starting MCP Workspace Server...", file=sys.stderr)
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="workspace-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
