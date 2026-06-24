from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Awaitable, Callable

import chromadb
import mcp.types as types
import pypdf
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "chroma_db"
SKILL_DIRS = PROJECT_ROOT / "agent" / "skills"
TEXT_SPLITTER = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=60)


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict
    call_tool: Callable[[dict | None], Awaitable[list[types.TextContent]]]

    def to_mcp_tool(self) -> types.Tool:
        return types.Tool(
            name=self.name,
            description=self.description,
            inputSchema=self.input_schema,
        )


@lru_cache(maxsize=1)
def get_collection() -> chromadb.Collection:
    chroma_client = chromadb.PersistentClient(path=str(DB_PATH))
    embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    return chroma_client.get_or_create_collection(
        name="local_documents",
        embedding_function=embedding_func,
    )


def extract_pdf_text(path: str) -> str:
    content: list[str] = []
    with open(path, "rb") as file_handle:
        pdf_reader = pypdf.PdfReader(file_handle)
        for page_number, page in enumerate(pdf_reader.pages, start=1):
            text = page.extract_text()
            if text:
                content.append(f"[Page {page_number}]\n{text}")
    return "\n\n".join(content)


def extract_pdf_pages(path: str, start_page: int, end_page: int) -> str:
    if start_page < 1:
        raise ValueError("start_page must be greater than or equal to 1")
    if end_page < start_page:
        raise ValueError("end_page must be greater than or equal to start_page")

    content: list[str] = []
    with open(path, "rb") as file_handle:
        pdf_reader = pypdf.PdfReader(file_handle)
        max_page = min(end_page, len(pdf_reader.pages))
        if start_page > len(pdf_reader.pages):
            return ""

        for page_number in range(start_page, max_page + 1):
            page = pdf_reader.pages[page_number - 1]
            text = page.extract_text()
            if text:
                content.append(f"[Page {page_number}]\n{text}")
    return "\n\n".join(content)


def count_pdf_pages(path: str) -> int:
    with open(path, "rb") as file_handle:
        pdf_reader = pypdf.PdfReader(file_handle)
        return len(pdf_reader.pages)


def read_local_file(path: str) -> str:
    if path.lower().endswith(".pdf"):
        content = extract_pdf_text(path)
        if not content.strip():
            raise ValueError(f"No readable text could be extracted from {path}")
        return content

    with open(path, "r", encoding="utf-8") as file_handle:
        return file_handle.read()


def write_local_file(path: str, content: str) -> None:
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")


def _parse_frontmatter(markdown: str) -> dict[str, str]:
    if not markdown.startswith("---"):
        return {}

    lines = markdown.splitlines()
    if len(lines) < 3:
        return {}

    try:
        closing_index = lines[1:].index("---") + 1
    except ValueError:
        return {}

    frontmatter: dict[str, str] = {}
    for line in lines[1:closing_index]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        frontmatter[key.strip().lower()] = value.strip()
    return frontmatter


def list_skill_files() -> list[Path]:
    skill_files: list[Path] = []
    if not SKILL_DIRS.exists():
        raise FileNotFoundError(f"Skills directory not found: {SKILL_DIRS}")
    skill_files.extend(path for path in SKILL_DIRS.glob("*.md") if path.is_file())
    return sorted(skill_files)


def read_skill_markdown(skill_path: Path) -> str:
    return skill_path.read_text(encoding="utf-8")


def read_skill_frontmatter(skill_path: Path) -> dict[str, str]:
    frontmatter: dict[str, str] = {}
    with open(skill_path, "r", encoding="utf-8") as file_handle:
        first_line = file_handle.readline().strip()
        if first_line != "---":
            return frontmatter

        for raw_line in file_handle:
            line = raw_line.strip()
            if line == "---":
                break
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            frontmatter[key.strip().lower()] = value.strip()
    return frontmatter


def resolve_skill_path(skill_name: str) -> Path | None:
    if not skill_name:
        return None

    normalized = skill_name.strip().lower()
    candidate_name = Path(skill_name).name
    if not SKILL_DIRS.exists():
        raise FileNotFoundError(f"Skills directory not found: {SKILL_DIRS}")
    if Path(candidate_name).suffix.lower() == ".md":
        candidate = SKILL_DIRS / candidate_name
    else:
        candidate = SKILL_DIRS / f"{candidate_name}.md"

    if candidate.exists():
        resolved = candidate.resolve()
        skills_root = SKILL_DIRS.resolve()
        if skills_root in resolved.parents or resolved.parent == skills_root:
            return resolved

    for skill_path in list_skill_files():
        skill_text = read_skill_markdown(skill_path)
        frontmatter = _parse_frontmatter(skill_text)
        aliases = {
            skill_path.stem.lower(),
            skill_path.name.lower(),
            frontmatter.get("name", "").lower(),
        }
        if normalized in aliases:
            return skill_path.resolve()

    return None


def describe_skill(skill_path: Path) -> dict[str, str]:
    frontmatter = read_skill_frontmatter(skill_path)
    description = frontmatter.get("description", "").strip()
    return {
        "name": frontmatter.get("name", skill_path.stem).strip(),
        "description": description,
        "file_name": skill_path.name,
    }
