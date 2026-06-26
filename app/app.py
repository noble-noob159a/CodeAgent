from __future__ import annotations

import asyncio
import inspect
import json
import os
import sys
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")
import gradio as gr
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
SERVER_PATH = PROJECT_ROOT / "agent" / "server.py"
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.router import build_model_route

server_params = StdioServerParameters(
    command=sys.executable,
    args=[str(SERVER_PATH)],
    env=os.environ.copy(),
)
load_dotenv()

PROXY_URL = os.environ.get("HTTP_PROXY") or None
DEFAULT_PROVIDER = os.environ.get("DEFAULT_PROVIDER", "glm/4.7-flash")

PROVIDER_CHOICES = [
    ("GitHub Models · GPT-4.1 Mini", "github/gpt-4.1-mini"),
    ("Gemini · 2.5 Flash", "gemini/2.5-flash"),
    ("GLM · 4.7 Flash", "glm/4.7-flash"),
]
PROVIDER_OPTIONS = [value for _, value in PROVIDER_CHOICES]


def _supports_kwarg(callable_obj: object, kwarg_name: str) -> bool:
    try:
        return kwarg_name in inspect.signature(callable_obj).parameters
    except (TypeError, ValueError):
        return False


CHATBOT_USES_MESSAGES = _supports_kwarg(gr.Chatbot, "type")


def _format_chatbot_history(history: list[dict[str, str]]) -> object:
    return history


def _tool_result_text(tool_result: object) -> str:
    content = getattr(tool_result, "content", None) or []
    parts: list[str] = []
    for item in content:
        text = getattr(item, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


async def _load_tool_metadata() -> tuple[list[dict[str, object]], str]:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_PATH)],
        env=os.environ.copy(),
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as mcp_session:
            await mcp_session.initialize()
            tools_response = await mcp_session.list_tools()
            skill_catalog_response = await mcp_session.call_tool("list_skills", arguments={})

            tools: list[dict[str, object]] = []
            for tool in tools_response.tools:
                tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema,
                        },
                    }
                )

            skill_catalog_text = _tool_result_text(skill_catalog_response)
            if not skill_catalog_text:
                skill_catalog_text = "No markdown skills are available."

            return tools, skill_catalog_text


async def _continue_workspace_turn(
    route: object,
    messages: list[dict[str, object]],
    tools: list[dict[str, object]],
    initial_tool_calls: list[object],
) -> str:
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as mcp_session:
            await mcp_session.initialize()

            for tool_call in initial_tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments or "{}")
                tool_result = await mcp_session.call_tool(tool_name, arguments=tool_args)
                result_text = _tool_result_text(tool_result)
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_name,
                        "content": result_text or f"Tool {tool_name} returned no text.",
                    }
                )

            for _ in range(10):
                response = route.client.chat.completions.create(
                    model=route.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )

                response_message = response.choices[0].message
                messages.append(response_message)

                if response_message.tool_calls:
                    for tool_call in response_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments or "{}")
                        tool_result = await mcp_session.call_tool(tool_name, arguments=tool_args)
                        result_text = _tool_result_text(tool_result)
                        messages.append(
                            {
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": tool_name,
                                "content": result_text or f"Tool {tool_name} returned no text.",
                            }
                        )
                    continue

                return (response_message.content or "").strip() or "The model returned an empty response."

    return "The model did not produce a final answer."


def build_system_prompt(provider: str, model: str, skill_catalog: str) -> str:
    base_prompt = (
        "You are CodeAgent, a helpful assistant with access to a local MCP workspace server. "
        "You can inspect and modify local files, read markdown skills, and search the local knowledge base. "
        "Use tools when the user asks about workspace files, code edits, file contents, or skill-based workflows. "
        "Keep answers concise, practical, and markdown-friendly."
    )

    capability_note = (
        f"\n\nCurrent model route: {provider}/{model}. "
        "When a request needs local context, use the available tools instead of pretending the capability is unavailable. "
        "If a skill matches the request, load it with read_skill and follow it strictly."
    )

    skill_note = f"\n\nAvailable skills:\n{skill_catalog}"
    return base_prompt + capability_note + skill_note


# Load CSS from file before creating Blocks
APP_CSS = ""
try:
    with open(os.path.join(BASE_DIR, "app.css"), "r", encoding="utf-8") as file_handle:
        APP_CSS = file_handle.read()
except Exception:
    pass

blocks_kwargs = {"title": "CodeAgent Web UI"}
launch_extra_kwargs = {}
theme = gr.themes.Ocean()
if _supports_kwarg(gr.Blocks.launch, "css"):
    launch_extra_kwargs["css"] = APP_CSS
else:
    blocks_kwargs["css"] = APP_CSS
if _supports_kwarg(gr.Blocks.launch, "theme"):
    launch_extra_kwargs["theme"] = theme
elif _supports_kwarg(gr.Blocks, "theme"):
    blocks_kwargs["theme"] = theme

with gr.Blocks(**blocks_kwargs) as demo:
    gr.Markdown(
        "<div id='app-title'>"
        "<h1>CodeAgent</h1>"
        "<p>AI assistant for research and analysis</p>"
        "</div>",
        elem_id="app-title",
    )
    gr.Markdown("<div id='title-divider'></div>", elem_id="title-divider-wrap")

    chat_state = gr.State([])
    model_panel_visible = gr.State(False)

    chatbot_kwargs = {"label": "Conversation", "height": 560, "show_label": False}
    if CHATBOT_USES_MESSAGES:
        chatbot_kwargs["type"] = "messages"
    chatbot = gr.Chatbot(**chatbot_kwargs, elem_id="chatbot")

    status_box = gr.Markdown("Ready. Send a message to start.", elem_id="status-box")

    with gr.Row(scale=1, elem_id="composer-row"):
        textbox_kwargs = {
            "label": "Message",
            "placeholder": "Message CodeAgent",
            "lines": 1,
            "scale": 8,
            "show_label": False,
            "container": False,
        }
        if _supports_kwarg(gr.Textbox, "submit_on_enter"):
            textbox_kwargs["submit_on_enter"] = True
        user_input = gr.Textbox(**textbox_kwargs)
        send_btn = gr.Button("↑", elem_id="send-arrow")

    with gr.Row(scale=1, elem_id="settings-row"):
        toggle_model_btn = gr.Button("Model settings", scale=1)

    with gr.Column(visible=False, elem_id="model-panel") as model_panel:
        provider = gr.Dropdown(
            choices=PROVIDER_CHOICES,
            value=DEFAULT_PROVIDER if DEFAULT_PROVIDER in PROVIDER_OPTIONS else PROVIDER_OPTIONS[0],
            label="Model provider",
            info="Choose where the request is sent",
        )

    def toggle_model_panel(is_visible: bool):
        new_visible = not is_visible
        return new_visible, gr.update(visible=new_visible)

    toggle_model_btn.click(
        fn=toggle_model_panel,
        inputs=[model_panel_visible],
        outputs=[model_panel_visible, model_panel],
    )

    def handle_message(user_text: str, history: list[dict[str, str]], selected_provider: str):
        if not user_text or not user_text.strip():
            raise gr.Error("Please enter a message.")

        current_history = history or []
        stripped_text = user_text.strip()

        updated_history = current_history + [{"role": "user", "content": stripped_text}]
        yield updated_history, _format_chatbot_history(updated_history), "Model is connecting to local workspace tools...", ""

        try:
            provider = (selected_provider or DEFAULT_PROVIDER).strip().lower()
            if provider not in PROVIDER_OPTIONS:
                raise gr.Error(f"Unknown provider '{provider}'. Choose one of: {', '.join(PROVIDER_OPTIONS)}")

            provider_name = provider.split("/")[0]
            route = build_model_route(provider_name=provider_name, proxy_url=PROXY_URL)
            tools, skill_catalog = asyncio.run(_load_tool_metadata())
            system_prompt = build_system_prompt(provider, route.model, skill_catalog)

            messages: list[dict[str, object]] = [{"role": "system", "content": system_prompt}]
            messages.extend(current_history)
            messages.append({"role": "user", "content": stripped_text})

            response = route.client.chat.completions.create(
                model=route.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )

            response_message = response.choices[0].message
            messages.append(response_message)

            if response_message.tool_calls:
                tool_names_used: list[str] = []
                for tool_call in response_message.tool_calls:
                    tool_name = tool_call.function.name
                    if tool_name not in tool_names_used:
                        tool_names_used.append(tool_name)

                tool_list = ", ".join(tool_names_used) if tool_names_used else "workspace tools"
                tool_history = current_history + [
                    {"role": "user", "content": stripped_text},
                    {
                        "role": "assistant",
                        "content": f"-> **Using tools**\n-> Connecting to local MCP server to use `{tool_list}`.",
                    },
                ]
                yield tool_history, _format_chatbot_history(tool_history), "Model is using local workspace tools...", ""

                assistant_text = asyncio.run(
                    _continue_workspace_turn(route, messages, tools, list(response_message.tool_calls))
                )
                final_history = tool_history + [{"role": "assistant", "content": assistant_text}]
                final_status = "Model used MCP tools and returned a markdown response."
            else:
                assistant_text = (response_message.content or "").strip() or "The model returned an empty response."
                final_history = current_history + [
                    {"role": "user", "content": stripped_text},
                    {"role": "assistant", "content": assistant_text},
                ]
                final_status = "Model returned a markdown response."
        except Exception as exc:
            raise gr.Error(str(exc)) from exc

        yield final_history, _format_chatbot_history(final_history), final_status, ""

    send_btn.click(
        fn=handle_message,
        inputs=[user_input, chat_state, provider],
        outputs=[chat_state, chatbot, status_box, user_input],
        show_progress="hidden",
    )

    user_input.submit(
        fn=handle_message,
        inputs=[user_input, chat_state, provider],
        outputs=[chat_state, chatbot, status_box, user_input],
        show_progress="hidden",
    )

if __name__ == "__main__":
    launch_kwargs = {
        "server_name": "0.0.0.0",
        "server_port": int(os.environ.get("PORT", "7862")),
    }
    launch_kwargs.update(launch_extra_kwargs)

    demo.queue().launch(**launch_kwargs)
