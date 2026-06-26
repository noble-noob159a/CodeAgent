# CodeAgent

CodeAgent is a local MCP-enabled coding assistant with both CLI and web interfaces. It connects to a local MCP server over stdio, exposes local workspace tools to a chat model, and supports document indexing with ChromaDB.

## Features

- **Interactive CLI Agent**: Run a conversational AI assistant with file operations, web search, and knowledge base access
- **Web UI**: Gradio-based web interface with real-time tool monitoring and markdown output
- **Multiple Model Providers**: GitHub Models, OpenAI, Gemini, and GLM support
- **Local MCP Server**: File read/write, web search, and knowledge base tools
- **Document Indexing**: Text and PDF indexing with semantic search using ChromaDB
- **Skill System**: Reusable markdown-based workflows for common tasks

## Project Structure

```text
CodeAgent/
|-- agent/
|   |-- __init__.py
|   |-- agent.py        # Interactive CLI agent with MCP integration
|   |-- router.py       # Model provider routing and OpenAI client
|   |-- server.py       # Local MCP server and tool implementations
|   |-- skills/         # Markdown skill definitions
|   |   |-- analyze-research-paper.md
|   |   |-- code-review.md
|   |-- tools/          # MCP tool implementations
|       |-- index_document.py
|       |-- list_skills.py
|       |-- read_file.py
|       |-- read_skill.py
|       |-- search_knowledge_base.py
|       |-- util.py
|       |-- web_search.py
|       |-- write_file.py
|-- app/                # Gradio web UI
|   |-- app.py          # Web interface with tool monitoring
|   `-- app.css         # Custom styling
|-- chroma_db/          # Local ChromaDB persistence directory, ignored by git
|-- local_docs/         # Suggested location for documents to index, ignored by git
|-- output/             # Generated output files
|-- requirements.txt    # Python dependencies
|-- .env                # Local environment variables, ignored by git
|-- .gitignore
`-- README.md
```

## Setup Guide

### 1. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If script execution is blocked, run PowerShell as your user and allow local scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

The RAG tools use `sentence-transformers`. The first call to `index_document` or `search_knowledge_base` may download the `all-MiniLM-L6-v2` model if it is not already cached.

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
# Required for model providers
GITHUB_API_KEY=your_github_token_here
OPENAI_API_KEY=your_openai_token_here
GEMINI_API_KEY=your_gemini_token_here
GLM_API_KEY=your_glm_token_here

# Optional: Proxy configuration
HTTP_PROXY=http://proxy.example.com:8080
DEFAULT_PROVIDER=glm/4.5-flash
PORT=7862
```

### 4. Run the CLI agent

```powershell
python agent\agent.py
```

When startup succeeds, you should see:

```text
====================================================
MCP-Enabled Agent Ready!
Model: glm/4.5-flash
Type 'exit' to quit.
====================================================

You: [your prompt]
```

Type a prompt at `You:`. Type `exit` to stop the agent.

### 5. Run the web UI

```powershell
python app\app.py
```

The web UI will launch at `http://localhost:7862` (or the port specified in `.env`). You can select different model providers and monitor tool calls in real-time.

## Key Components

### `agent/agent.py`

The interactive CLI agent. It:

- Loads environment variables from `.env`
- Creates an OpenAI-compatible client with provider routing
- Starts the local MCP server with Python stdio transport
- Lists MCP tools and converts them into OpenAI tool definitions
- Runs the chat loop and dispatches model-requested tool calls
- Supports skill-based workflows for common tasks

### `agent/router.py`

Model provider configuration and routing. It:

- Supports multiple providers: GitHub, OpenAI, Gemini, GLM
- Provides default models for each provider
- Handles proxy configuration
- Creates OpenAI-compatible clients

### `agent/server.py`

The local MCP server. It defines and executes the tools exposed to the agent:

- `read_file`: reads text from a local file, including extractable text from PDFs
- `write_file`: writes text to a local file
- `web_search`: performs a simple web search through DuckDuckGo HTML results
- `index_document`: reads a text or PDF file, splits it into chunks, and stores it in ChromaDB
- `search_knowledge_base`: searches indexed document chunks by semantic similarity
- `read_skill`: loads a markdown skill file for execution
- `list_skills`: lists all available skills

### `app/app.py`

The Gradio web interface. It:

- Provides a web-based chat UI
- Supports multiple model provider selection
- Shows real-time tool calls and responses in the terminal
- Displays markdown-formatted responses
- Manages conversation history

### Skills

Skills are markdown files that define reusable workflows:

- `analyze-research-paper.md`: Step-by-step research paper analysis workflow
- `code-review.md`: Code review and improvement suggestions workflow

Skills are loaded dynamically and executed when requested by the model.


## Notes

- The MCP server communicates over stdio, so protocol messages must stay on stdout. Debug logs should go to stderr.
- If RAG tools fail on first use, check whether the sentence-transformer model can be downloaded or is already cached locally.
- The web UI logs tool calls and responses to the terminal for monitoring.
- ChromaDB and the sentence-transformer embedding model are initialized lazily, so normal MCP startup does not depend on model download availability.
