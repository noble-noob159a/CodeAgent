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
# print(PROXY_URL)
openai_client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ.get("API_TOKEN"),
    http_client=httpx.Client(proxy=PROXY_URL) if PROXY_URL else None
)


MODEL_NAME = "gpt-4.1-mini"


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


            # System baseline prompt
            messages = [{"role": "system", "content": "You are a senior coding assistant. Use your available tools to manage files."}]
           
            print("====================================================")
            print("MCP-Enabled Agent Ready!")
            print("Type 'exit' to quit.")
            print("====================================================")


            while True:
                user_input = input("\nYou: ")
                if user_input.lower() == 'exit':
                    break


                messages.append({"role": "user", "content": user_input})


                # Call LLM via GitHub Models proxy
                response = openai_client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    tools=openai_tools,
                    tool_choice="auto"
                )


                response_message = response.choices[0].message
                messages.append(response_message)


                # Process Tool calls requested by the Cloud LLM via local MCP Server
                if response_message.tool_calls:
                    print("\n->  [Executing MCP Server Action...]")
                   
                    for tool_call in response_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                       
                        print(f"-> Dispatching to MCP: {tool_name}({tool_args})")
                       
                        # Execute tool on the local MCP server session
                        mcp_result = await mcp_session.call_tool(tool_name, arguments=tool_args)
                        # Extract string content response
                        result_text = mcp_result.content[0].text if mcp_result.content else ""
                       
                        # Return tool results back to LLM context
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": tool_name,
                            "content": result_text
                        })


                    # Request final response after tool execution output is attached
                    follow_up_response = openai_client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=messages
                    )
                    final_reply = follow_up_response.choices[0].message.content
                    messages.append({"role": "assistant", "content": final_reply})
                    print(f"\n Agent:\n{final_reply}")
                else:
                    print(f"\n Agent:\n{response_message.content}")




if __name__ == "__main__":
    asyncio.run(run_mcp_agent())

