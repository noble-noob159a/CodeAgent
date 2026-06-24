from __future__ import annotations

import mcp.types as types

from .util import (
    ToolSpec,
    list_skill_files,
    read_skill_markdown,
    resolve_skill_path,
)

DESCRIPTION = "Reads a single markdown skill file from the agent/skills folder."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "Skill name, file stem, or markdown filename.",
        }
    },
    "required": ["name"],
}


async def call_tool(arguments: dict | None) -> list[types.TextContent]:
    if not arguments:
        raise ValueError("Missing tool arguments")

    name = arguments.get("name")
    skill_path = resolve_skill_path(name)
    if skill_path is None:
        available = ", ".join(path.stem for path in list_skill_files()) or "none"
        return [
            types.TextContent(
                type="text",
                text=f"Skill not found: {name}. Available skills: {available}",
            )
        ]

    try:
        return [types.TextContent(type="text", text=read_skill_markdown(skill_path))]
    except Exception as exc:
        return [types.TextContent(type="text", text=f"Error reading skill: {exc}")]


TOOL_SPEC = ToolSpec(
    name="read_skill",
    description=DESCRIPTION,
    input_schema=INPUT_SCHEMA,
    call_tool=call_tool,
)
