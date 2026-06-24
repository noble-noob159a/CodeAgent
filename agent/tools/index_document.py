from __future__ import annotations

import os

import mcp.types as types

from .util import TEXT_SPLITTER, ToolSpec, get_collection, read_local_file

DESCRIPTION = "Reads a local text file, splits it into semantic chunks, and adds it to the RAG vector database."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "file_path": {
            "type": "string",
            "description": "Relative or absolute path to the local text file.",
        }
    },
    "required": ["file_path"],
}


async def call_tool(arguments: dict | None) -> list[types.TextContent]:
    if not arguments:
        raise ValueError("Missing tool arguments")

    file_path = arguments.get("file_path")
    if not file_path:
        return [types.TextContent(type="text", text="Error: file_path is required.")]

    if not os.path.exists(file_path):
        return [types.TextContent(type="text", text=f"Error: File not found at {file_path}")]

    try:
        content = read_local_file(file_path)
        if not content.strip():
            return [types.TextContent(type="text", text=f"Error: No readable text could be extracted from {file_path}")]

        chunks = TEXT_SPLITTER.split_text(content)
        ids = [f"{os.path.basename(file_path)}_chunk_{index}" for index in range(len(chunks))]
        metadatas = [{"source": file_path, "chunk_index": index} for index in range(len(chunks))]

        collection = get_collection()
        collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)

        message = (
            f"Successfully indexed '{file_path}'. "
            f"Split into {len(chunks)} chunks and stored in the vector database."
        )
        return [types.TextContent(type="text", text=message)]
    except Exception as exc:
        return [types.TextContent(type="text", text=f"Indexing failed: {exc}")]


TOOL_SPEC = ToolSpec(
    name="index_document",
    description=DESCRIPTION,
    input_schema=INPUT_SCHEMA,
    call_tool=call_tool,
)
