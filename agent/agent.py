import os
import sys
import json
import asyncio
import argparse
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

try:
    from .router import build_model_route, ModelRoute
except ImportError:
    from router import build_model_route, ModelRoute


load_dotenv()
PROXY_URL =  os.environ.get("HTTP_PROXY") or None
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_PATH = os.path.join(BASE_DIR, "server.py")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def format_skill_catalog(skill_payload: str) -> str:
    catalog = skill_payload.strip()
    if not catalog:
        return "No markdown skills are available."

    return (
        f"{catalog}\n\n"
        "When a user request matches a skill, call `read_skill` to load the full markdown "
        "for only that skill before applying its workflow. Then strictly follow the instructions in the skill markdown to complete the task. "
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the MCP-enabled coding agent.")
    parser.add_argument(
        "--provider",
        required=False,
        default='glm',
        help="Provider to use: github, openai, gemini, or glm. Optional when using a known model alias.",
    )
    return parser.parse_args()


async def execute_llm_turn(
    messages: list[dict],
    tools: list[dict],
    mcp_session: ClientSession,
    model_route: ModelRoute,
) -> str:
    max_rounds = 15

    for _ in range(max_rounds):
        response = model_route.client.chat.completions.create(
            model=model_route.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        response_message = response.choices[0].message
        messages.append(response_message)

        if response_message.tool_calls:
            print("\n->  [Executing MCP Server Action...]")
            for tool_call in response_message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments or "{}")

                print(f"-> Dispatching to MCP: {tool_name}({tool_args})")

                mcp_result = await mcp_session.call_tool(tool_name, arguments=tool_args)
                result_text = mcp_result.content[0].text if mcp_result.content else ""

                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": tool_name,
                    "content": result_text,
                })
            continue

        if response_message.content:
            return response_message.content

        # Some models return an assistant message with no text but also no tool calls.
        # Ask once more with the updated conversation so it can finish the answer.

    return "The model did not produce a final answer."


async def run_mcp_agent(model_route: ModelRoute):
    # Run mcp server
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[SERVER_PATH],
        env=os.environ.copy()
    )


    print(" Connecting to Local MCP Server...")
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as mcp_session:
            # connect to MCP Server
            await mcp_session.initialize()
           
            # fetch tools from the server
            mcp_tools_response = await mcp_session.list_tools()
            mcp_tools = mcp_tools_response.tools


            tools = []
            for tool in mcp_tools:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                })

            skill_catalog_response = await mcp_session.call_tool("list_skills", arguments={})
            skill_catalog_text = (
                skill_catalog_response.content[0].text
                if skill_catalog_response.content
                else "No markdown skills are available."
            )
            skill_catalog = format_skill_catalog(skill_catalog_text)
            # print("Skill Catalog:\n", skill_catalog)
            # System baseline prompt
            messages = [{
                "role": "system",
                "content": (
                    "You are a AI researcher assistant. Use your available tools and skills to assist with research tasks.\n\n"
                    f"{skill_catalog}"
                ),
            }]
           
            print("====================================================")
            print("MCP-Enabled Agent Ready!")
            print(f"Model: {model_route.provider}/{model_route.model}")
            print("Type 'exit' to quit.")
            print("====================================================")


            while True:
                user_input = input("\nYou: ")
                if user_input.lower() == 'exit':
                    break


                messages.append({"role": "user", "content": user_input})

                final_reply = await execute_llm_turn(messages, tools, mcp_session, model_route)
                messages.append({"role": "assistant", "content": final_reply})
                print(f"\n🤖 Agent:\n{final_reply}")




if __name__ == "__main__":
    args = parse_args()
    route = build_model_route(
        provider_name=args.provider,
        proxy_url=PROXY_URL,
    )
    asyncio.run(run_mcp_agent(route))

