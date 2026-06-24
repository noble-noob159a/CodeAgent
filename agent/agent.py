import os
import sys
import json
import httpx
import asyncio
from openai import OpenAI
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


load_dotenv()
PROXY_URL =  os.environ.get("HTTP_PROXY") or None
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_PATH = os.path.join(BASE_DIR, "server.py")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
# print(PROXY_URL)
openai_client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("API_TOKEN"),
    http_client=httpx.Client(proxy=PROXY_URL) if PROXY_URL else None
)


MODEL_NAME = "gpt-4.1-mini"


def format_skill_catalog(skill_payload: str) -> str:
    catalog = skill_payload.strip()
    if not catalog:
        return "No markdown skills are available."

    return (
        f"{catalog}\n\n"
        "When a user request matches a skill, call `read_skill` to load the full markdown "
        "for only that skill before applying its workflow. Then strictly follow the instructions in the skill markdown to complete the task. "
    )


async def execute_llm_turn(messages: list[dict], openai_tools: list[dict], mcp_session: ClientSession) -> str:
    max_rounds = 8

    for _ in range(max_rounds):
        response = openai_client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=openai_tools,
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


async def run_mcp_agent():
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


            openai_tools = []
            for tool in mcp_tools:
                openai_tools.append({
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
            print("Type 'exit' to quit.")
            print("====================================================")


            while True:
                user_input = input("\nYou: ")
                if user_input.lower() == 'exit':
                    break


                messages.append({"role": "user", "content": user_input})

                final_reply = await execute_llm_turn(messages, openai_tools, mcp_session)
                messages.append({"role": "assistant", "content": final_reply})
                print(f"\n Agent:\n{final_reply}")




if __name__ == "__main__":
    asyncio.run(run_mcp_agent())

