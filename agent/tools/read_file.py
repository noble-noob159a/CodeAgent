from __future__ import annotations

import mcp.types as types

from .util import (
    ToolSpec,
    count_pdf_pages,
    extract_pdf_pages,
    read_local_file,
)

DESCRIPTION = "Reads the text contents of a file inside the local workspace, including extractable text from PDFs."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "path": {"type": "string", "description": "Relative path to the file."},
        "page_start": {
            "type": "integer",
            "description": "Optional first PDF page to read, starting at 1.",
        },
        "page_end": {
            "type": "integer",
            "description": "Optional last PDF page to read, starting at 1.",
        },
    },
    "required": ["path"],
}


async def call_tool(arguments: dict | None) -> list[types.TextContent]:
    if not arguments:
        raise ValueError("Missing tool arguments")

    path = arguments.get("path")
    page_start = arguments.get("page_start")
    page_end = arguments.get("page_end")

    try:
        if path and path.lower().endswith(".pdf"):
            total_pages = count_pdf_pages(path)
            if page_start is None and page_end is None:
                end_page = min(3, total_pages)
                text = extract_pdf_pages(path, 1, end_page)
                suffix = (
                    f"\n\n[Showing pages 1-{end_page} of {total_pages}. "
                    "Call read_file again with page_start/page_end to continue.]"
                    if total_pages > end_page
                    else ""
                )
                return [types.TextContent(type="text", text=f"{text}{suffix}")]

            start = int(page_start or 1)
            end = int(page_end or start)
            text = extract_pdf_pages(path, start, end)
            if not text.strip():
                return [
                    types.TextContent(
                        type="text",
                        text=f"No readable text found in pages {start}-{end} of {path}.",
                    )
                ]
            return [types.TextContent(type="text", text=text)]

        return [types.TextContent(type="text", text=read_local_file(path))]
    except Exception as exc:
        return [types.TextContent(type="text", text=f"Error reading file: {exc}")]


TOOL_SPEC = ToolSpec(
    name="read_file",
    description=DESCRIPTION,
    input_schema=INPUT_SCHEMA,
    call_tool=call_tool,
)
