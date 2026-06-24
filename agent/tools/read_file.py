from __future__ import annotations

import mcp.types as types

from .util import ToolSpec, read_local_file

DESCRIPTION = "Reads the text contents of a file inside the local workspace, including extractable text from PDFs."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Relative path to the file."}
    },
    "required": ["path"],
}


async def call_tool(arguments: dict | None) -> list[types.TextContent]:
    if not arguments:
        raise ValueError("Missing tool arguments")

    path = arguments.get("path")
    try:
        return [types.TextContent(type="text", text=read_local_file(path))]
    except Exception as exc:
        return [types.TextContent(type="text", text=f"Error reading file: {exc}")]


TOOL_SPEC = ToolSpec(
    name="read_file",
    description=DESCRIPTION,
    input_schema=INPUT_SCHEMA,
    call_tool=call_tool,
)
