"""LLM providers behind one structured-output interface.

Every call site supplies a deterministic `fallback` producing the same schema.
The mock provider always uses it; real providers use it when generation fails
or returns invalid output. Results report which path produced them so
diagnostics never confuse scripted fallback with model output.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings

log = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass(slots=True)
class LLMResult(Generic[T]):
    value: T
    source: str  # "mock" | "ollama" | "anthropic" | "fallback"
    error: str | None = None


class LLMProvider(Protocol):
    name: str

    async def structured(
        self,
        *,
        system: str,
        prompt: str,
        schema: type[T],
        fallback: Callable[[], T],
        temperature: float = 0.9,
        effort: str = "low",
        max_tokens: int = 4000,
    ) -> LLMResult[T]: ...


class MockLLM:
    """Deterministic comedy engine: no network, no randomness beyond seeded choices."""

    name = "mock"

    async def structured(self, *, system, prompt, schema, fallback, **_):  # type: ignore[override]
        return LLMResult(fallback(), "mock")


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rsplit("```", 1)[0]
    return t.strip()


class OllamaLLM:
    name = "ollama"

    def __init__(self, settings: Settings):
        self.base = settings.ollama_base_url.rstrip("/")
        self.model = settings.ollama_model
        self.timeout = settings.llm_timeout_s

    async def structured(self, *, system, prompt, schema, fallback, temperature=0.9, max_tokens=4000, **_):
        body = {
            "model": self.model,
            "stream": False,
            "format": schema.model_json_schema(),
            "options": {"temperature": temperature, "num_predict": max_tokens},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt + "\n\nRespond with JSON matching the schema."},
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(f"{self.base}/api/chat", json=body)
                r.raise_for_status()
                content = r.json()["message"]["content"]
            return LLMResult(schema.model_validate_json(_strip_fences(content)), "ollama")
        except (httpx.HTTPError, KeyError, ValidationError, json.JSONDecodeError) as exc:
            log.warning("ollama structured call failed, using scripted fallback: %s", exc)
            return LLMResult(fallback(), "fallback", error=str(exc)[:300])


class AnthropicLLM:
    name = "anthropic"

    def __init__(self, settings: Settings):
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key or None, timeout=settings.llm_timeout_s, max_retries=2
        )
        self.model = settings.anthropic_model

    async def structured(self, *, system, prompt, schema, fallback, effort="low", max_tokens=4000, **_):
        a = self._anthropic
        try:
            response = await self.client.messages.parse(
                model=self.model,
                max_tokens=max(max_tokens, 2000),
                system=system,
                messages=[{"role": "user", "content": prompt}],
                output_format=schema,
                output_config={"effort": effort},
            )
            if response.stop_reason == "refusal" or response.parsed_output is None:
                raise ValueError(f"no parsed output (stop_reason={response.stop_reason})")
            # Re-validate against the full domain constraints.
            return LLMResult(schema.model_validate(response.parsed_output.model_dump()), "anthropic")
        except (a.APIStatusError, a.APIConnectionError, ValidationError, ValueError) as exc:
            log.warning("anthropic structured call failed, using scripted fallback: %s", exc)
            return LLMResult(fallback(), "fallback", error=str(exc)[:300])


def get_llm(name: str | None = None) -> LLMProvider:
    s = get_settings()
    name = name or s.llm_provider
    if name == "ollama":
        return OllamaLLM(s)
    if name == "anthropic":
        return AnthropicLLM(s)
    return MockLLM()
