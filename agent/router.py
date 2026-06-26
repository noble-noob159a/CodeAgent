from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv
import httpx
from openai import OpenAI


load_dotenv()


@dataclass(frozen=True)
class ModelRoute:
    """OpenAI-compatible client plus the concrete model name to call."""

    client: OpenAI
    model: str
    provider: str
    base_url: str


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key_env: str
    default_model: str


PROVIDERS: dict[str, ProviderConfig] = {
    "github": ProviderConfig(
        name="github",
        base_url="https://models.inference.ai.azure.com",
        api_key_env="GITHUB_API_KEY",
        default_model="gpt-4.1-mini",
    ),
    "openai": ProviderConfig(
        name="openai",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        default_model="gpt-4.1-mini",
    ),
    "gemini": ProviderConfig(
        name="gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key_env="GEMINI_API_KEY",
        default_model="gemini-2.5-flash",
    ),
    "glm": ProviderConfig(
        name="glm",
        base_url="https://api.z.ai/api/paas/v4/",
        api_key_env="GLM_API_KEY",
        default_model="glm-4.5-flash",
    ),
}


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def resolve_model(provider_name: str | None = None) -> tuple[ProviderConfig, str]:
    """Resolve a friendly model/provider name into a provider config and model id."""

    normalized_provider = _normalize(provider_name)

    if normalized_provider:
        if normalized_provider not in PROVIDERS:
            known = ", ".join(sorted(PROVIDERS))
            raise ValueError(f"Unknown provider '{provider_name}'. Known providers: {known}")
        provider = PROVIDERS[normalized_provider]
        return provider, provider.default_model


    provider = PROVIDERS["github"]
    return provider, provider.default_model


def build_model_route(
    provider_name: str | None = None,
    proxy_url: str | None = None,
) -> ModelRoute:
    """Create the chat-completions client and model id for inference."""

    provider, model = resolve_model(provider_name)
    selected_base_url = provider.base_url.strip()
    selected_api_key = os.environ.get(provider.api_key_env)
    

    if not selected_api_key:
        raise ValueError(
            f"Missing API key for provider '{provider.name}'. Set {provider.api_key_env}, "
            "MODEL_API_KEY, API_TOKEN, or pass --api-key."
        )

    http_client = httpx.Client(proxy=proxy_url) if proxy_url else None
    client = OpenAI(
        base_url=selected_base_url,
        api_key=selected_api_key,
        http_client=http_client,
    )

    return ModelRoute(
        client=client,
        model=model,
        provider=provider.name,
        base_url=selected_base_url,
    )
