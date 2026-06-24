from __future__ import annotations

import mcp.types as types

from .util import ToolSpec, write_local_file

DESCRIPTION = "Writes or overwrites text/code content to a local file."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Relative path where the file should be saved."},
        "content": {"type": "string", "description": "The exact string content or code block."},
    },
    "required": ["path", "content"],
}


async def call_tool(arguments: dict | None) -> list[types.TextContent]:
    if not arguments:
        raise ValueError("Missing tool arguments")

    path = arguments.get("path")
    content = arguments.get("content")

    try:
        write_local_file(path, content)
        return [types.TextContent(type="text", text=f"Successfully wrote to {path}")]
    except Exception as exc:
        return [types.TextContent(type="text", text=f"Error writing file: {exc}")]


TOOL_SPEC = ToolSpec(
    name="write_file",
    description=DESCRIPTION,
    input_schema=INPUT_SCHEMA,
    call_tool=call_tool,
)
