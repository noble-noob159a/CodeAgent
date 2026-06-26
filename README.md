---
title: CodeAgent Web UI
sdk: gradio
app_file: app/app.py
---

# CodeAgent

CodeAgent is a local MCP-enabled coding assistant. It runs a Python client that connects to a local MCP server over stdio, exposes local workspace tools to a chat model, and can optionally index/search local documents with ChromaDB.

## Features

- Local MCP server with file read/write tools.
- Web search helper using DuckDuckGo HTML search.
- Local document indexing for text and PDF files.
- ChromaDB-backed knowledge base search.
- Chat model integration through the GitHub Models-compatible OpenAI client.

## Project Structure

```text
CodeAgent/
|-- agent/
|   |-- __init__.py
|   |-- agent.py        # MCP client and interactive chat loop
|   `-- server.py       # Local MCP server and tool implementations
|-- chroma_db/          # Local ChromaDB persistence directory, ignored by git
|-- local_docs/         # Suggested location for documents to index, ignored by git
|-- index.html          # Static HTML file, if used for local UI experiments
|-- requirements.txt    # Python dependencies
|-- test.py             # Placeholder test file
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
API_TOKEN=your_github_models_token_here
```

### 4. Run the agent

```powershell
python agent\agent.py
```

When startup succeeds, you should see:

```text
MCP-Enabled Agent Ready!
Type 'exit' to quit.
```

Type a prompt at `You:`. Type `exit` to stop the agent.

### Deploy the web UI to Hugging Face Spaces

The repository now includes a Gradio entry point at `app/app.py`.

For Spaces, add your model API key as a secret and install the requirements from `requirements.txt`. The hosted UI supports provider selection, markdown chat output, text/PDF uploads, and a downloadable markdown response file.

Local-only tools such as workspace file read/write and the RAG knowledge base remain disabled in the deployed UI.

## Key Components

### `agent/agent.py`

The interactive client. It:

- Loads environment variables from `.env`.
- Creates an OpenAI-compatible client pointed at GitHub Models.
- Starts the local MCP server with Python stdio transport.
- Lists MCP tools and converts them into OpenAI tool definitions.
- Runs the chat loop and dispatches model-requested tool calls to the local MCP server.

### `agent/server.py`

The local MCP server. It defines and executes the tools exposed to the agent:

- `read_file`: reads text from a local file, including extractable text from PDFs.
- `write_file`: writes text to a local file.
- `web_search`: performs a simple web search through DuckDuckGo HTML results.
- `index_document`: reads a text or PDF file, splits it into chunks, and stores it in ChromaDB.
- `search_knowledge_base`: searches indexed document chunks by semantic similarity.

The ChromaDB collection and sentence-transformer embedding model are initialized lazily, so normal MCP startup does not depend on model download availability.



## Common Commands

Activate the virtual environment:

```powershell
.\venv\Scripts\Activate.ps1
```

Run the agent:

```powershell
python agent\agent.py
```

Run the MCP server directly for debugging:

```powershell
python agent\server.py
```

## Notes
- The MCP server communicates over stdio, so protocol messages must stay on stdout. Debug logs should go to stderr.
- If RAG tools fail on first use, check whether the sentence-transformer model can be downloaded or is already cached locally.
