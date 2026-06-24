from __future__ import annotations

import mcp.types as types

from .util import ToolSpec, describe_skill, list_skill_files

DESCRIPTION = "Lists the markdown-based skills available in the agent/skills folder."
INPUT_SCHEMA = {
    "type": "object",
    "properties": {},
}


async def call_tool(arguments: dict | None) -> list[types.TextContent]:
    skills = [describe_skill(path) for path in list_skill_files()]
    if not skills:
        return [types.TextContent(type="text", text="No skills were found in agent/skills.")]

    lines = ["Available skills:"]
    for skill in skills:
        description = skill.get("description") or "No description provided."
        lines.append(f"- {skill['name']} ({skill['file_name']}): {description}")

    lines.append("")
    lines.append("Use `read_skill` to load the full markdown for any skill you want to apply.")
    return [types.TextContent(type="text", text="\n".join(lines))]


TOOL_SPEC = ToolSpec(
    name="list_skills",
    description=DESCRIPTION,
    input_schema=INPUT_SCHEMA,
    call_tool=call_tool,
)
