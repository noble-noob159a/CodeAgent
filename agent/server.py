import os
import sys
import asyncio
import requests
from bs4 import BeautifulSoup
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from dotenv import load_dotenv
server = Server("workspace-server")
load_dotenv()
PROXY_URL = os.environ.get("HTTP_PROXY") or None

import pypdf
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter

DB_PATH = os.path.join(os.getcwd(), "chroma_db")
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=600, 
    chunk_overlap=60
)
collection = None


def get_collection():
    global collection
    if collection is None:
        chroma_client = chromadb.PersistentClient(path=DB_PATH)
        embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        collection = chroma_client.get_or_create_collection(
            name="local_documents",
            embedding_function=embedding_func
        )
    return collection

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="read_file",
            description="Reads the text contents of a file inside the local workspace.",
            inputSchema={
                "type": "object",
                "properties": {"path": {"type": "string", "description": "Relative path to the file."}},
                "required": ["path"],
            },
        ),
        types.Tool(
            name="write_file",
            description="Writes or overwrites text/code content to a local file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path where the file should be saved."},
                    "content": {"type": "string", "description": "The exact string content or code block."}
                },
                "required": ["path", "content"],
            },
        ),
        types.Tool(
            name="web_search",
            description="Searches the live internet for up-to-date documentation, technical explanations, or programming errors.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query (e.g., 'What's the weather today at Japan?')"}
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="index_document",
            description="Reads a local text file, splits it into semantic chunks, and adds it to the RAG vector database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative or absolute path to the local text file."}
                },
                "required": ["file_path"],
            },
        ),
        types.Tool(
            name="search_knowledge_base",
            description="Searches the local RAG vector database for text snippets relevant to the query.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search term or question to query the database with."},
                    "top_k": {"type": "integer", "description": "Number of relevant chunks to retrieve.", "default": 3}
                },
                "required": ["query"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
    if not arguments:
        raise ValueError("Missing tool arguments")

    if name == "read_file":
        path = arguments.get("path")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return [types.TextContent(type="text", text=f.read())]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error reading file: {str(e)}")]


    elif name == "write_file":
        path = arguments.get("path")
        content = arguments.get("content")
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return [types.TextContent(type="text", text=f"Successfully wrote to {path}")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error writing file: {str(e)}")]


    elif name == "web_search":
        query = arguments.get("query")
        try:
            proxies = {"http": PROXY_URL, "https": PROXY_URL}
            url = "https://html.duckduckgo.com/html/"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            data = {"q": query}
            response = requests.post(
                url,
                data=data,
                headers=headers,
                proxies=proxies,
                verify=False,
                timeout=15
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            if not soup:
                return [types.TextContent(type="text", text="Error: Search tool returned an empty response.")]
            results = []
            for result in soup.find_all('div', class_='result'):
                title_tag = result.find('h2', class_='result__title')
                snippet_tag = result.find('a', class_='result__snippet')
               
                if title_tag and snippet_tag:
                    title = title_tag.text.strip()
                    link = snippet_tag.get('href', '')
                    snippet = snippet_tag.text.strip()
                    results.append(f"Title: {title}\nLink: {link}\nSnippet: {snippet}\n---")


            output = "\n".join(results[:5])
            return [types.TextContent(type="text", text=output)]
                       
        except Exception as e:
            return [types.TextContent(type="text", text=f"Search failed: {str(e)}")]


    elif name == "index_document":
        file_path = arguments.get("file_path")
        if not os.path.exists(file_path):
            return [types.TextContent(type="text", text=f"Error: File not found at {file_path}")]
        
        try:
            content = ""
            if file_path.lower().endswith(".pdf"):
                with open(file_path, "rb") as f:
                    pdf_reader = pypdf.PdfReader(f)
                    for page_num, page in enumerate(pdf_reader.pages):
                        text = page.extract_text()
                        if text:
                            content += f"\n[Page {page_num + 1}]\n{text}\n"
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            
            if not content.strip():
                return [types.TextContent(type="text", text=f"Error: No readable text could be extracted from {file_path}")]
            
            chunks = text_splitter.split_text(content)
            ids = [f"{os.path.basename(file_path)}_chunk_{i}" for i in range(len(chunks))]
            metadatas = [{"source": file_path, "chunk_index": i} for i in range(len(chunks))]
            
            local_collection = get_collection()
            local_collection.upsert(
                ids=ids,
                documents=chunks,
                metadatas=metadatas
            )
            
            output_msg = f"Successfully indexed '{file_path}'. Split into {len(chunks)} chunks and stored in the vector database."
            return [types.TextContent(type="text", text=output_msg)]
            
        except Exception as e:
            return [types.TextContent(type="text", text=f"Indexing failed: {str(e)}")]


    elif name == "search_knowledge_base":
        query = arguments.get("query")
        top_k = int(arguments.get("top_k", 3))
        
        try:
            local_collection = get_collection()
            results = local_collection.query(
                query_texts=[query],
                n_results=top_k
            )
            
            output_lines = []
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            
            if not documents:
                return [types.TextContent(type="text", text="No relevant context found in the knowledge base.")]
                
            for idx, doc in enumerate(documents):
                source = metadatas[idx].get("source", "Unknown")
                output_lines.append(f"--- Context Snippet {idx+1} (Source: {source}) ---\n{doc}\n")
                
            final_context = "\n".join(output_lines)
            return [types.TextContent(type="text", text=final_context)]
            
        except Exception as e:
            return [types.TextContent(type="text", text=f"Search failed: {str(e)}")]

    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    print("Starting MCP Workspace Server...", file=sys.stderr)
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="workspace-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())

