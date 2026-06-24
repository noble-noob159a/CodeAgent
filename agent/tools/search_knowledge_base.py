from __future__ import annotations

import mcp.types as types

from .util import ToolSpec, get_collection

DESCRIPTION = "Searches the local RAG vector database for text snippets relevant to the query."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "The search term or question to query the database with.",
        },
        "top_k": {
            "type": "integer",
            "description": "Number of relevant chunks to retrieve.",
            "default": 3,
        },
    },
    "required": ["query"],
}


async def call_tool(arguments: dict | None) -> list[types.TextContent]:
    if not arguments:
        raise ValueError("Missing tool arguments")

    query = arguments.get("query")
    top_k = int(arguments.get("top_k", 3))

    try:
        collection = get_collection()
        results = collection.query(query_texts=[query], n_results=top_k)

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        if not documents:
            return [types.TextContent(type="text", text="No relevant context found in the knowledge base.")]

        output_lines: list[str] = []
        for index, document in enumerate(documents):
            source = metadatas[index].get("source", "Unknown")
            output_lines.append(
                f"--- Context Snippet {index + 1} (Source: {source}) ---\n{document}\n"
            )

        return [types.TextContent(type="text", text="\n".join(output_lines))]
    except Exception as exc:
        return [types.TextContent(type="text", text=f"Search failed: {exc}")]


TOOL_SPEC = ToolSpec(
    name="search_knowledge_base",
    description=DESCRIPTION,
    input_schema=INPUT_SCHEMA,
    call_tool=call_tool,
)
