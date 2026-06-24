from __future__ import annotations

from functools import lru_cache
from importlib import import_module
from pkgutil import iter_modules
from pathlib import Path

from .util import ToolSpec

TOOLS_PACKAGE_PATH = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def get_tool_specs() -> tuple[ToolSpec, ...]:
    specs: list[ToolSpec] = []
    for module_info in iter_modules([str(TOOLS_PACKAGE_PATH)]):
        if module_info.name.startswith("_") or module_info.name == "util":
            continue

        module = import_module(f"{__name__}.{module_info.name}")
        spec = getattr(module, "TOOL_SPEC", None)
        if spec is not None:
            specs.append(spec)

    return tuple(sorted(specs, key=lambda spec: spec.name))


@lru_cache(maxsize=1)
def get_tool_map() -> dict[str, ToolSpec]:
    return {spec.name: spec for spec in get_tool_specs()}
