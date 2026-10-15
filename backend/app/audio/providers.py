"""Audio providers. Provider-specific logic lives here and nowhere else.

The Fish provider only ever sends one of two exact model headers. An unknown
value would be silently billed as s2.1-pro by the API, so anything else is
refused before a request is built.
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.audio import mock_synth
from app.audio.compiler import CompiledRequest
from app.audio.mock_synth import MockVoice
from app.config import Settings

FISH_MODELS = {"drama3": "drama-3", "fish-free": "s2.1-pro-free"}


class ProviderError(Exception):
    """Definitive failure: the provider says no, nothing was (or will be) billed for a retry."""

    def __init__(self, message: str, status: int | None = None, retryable: bool = False, uncertain: bool = False):
        super().__init__(message)
        self.status = status
        self.retryable = retryable
        self.uncertain = uncertain  # request may have been processed (and billed) — never auto-retry


@dataclass(slots=True)
class SynthesisResult:
    audio: bytes
    format: str
    sample_rate: int
    pcm: bool = False
    word_timings: list[dict] = field(default_factory=list)
    timing_source: str = "estimated"  # "exact" for mock


class AudioProvider(Protocol):
    name: str
    model: str
    billable: bool

    async def synthesize(self, req: CompiledRequest, voice: MockVoice | None = None) -> SynthesisResult: ...


class MockAudioProvider:
    name = "mock"
    model = "mock-blips-v3"
    billable = False

    async def synthesize(self, req: CompiledRequest, voice: MockVoice | None = None) -> SynthesisResult:
        s = req.settings
        seed = int(hashlib.sha256(f"{req.text}|{s.get('seed', '')}".encode()).hexdigest()[:8], 16)
        samples, words = await asyncio.to_thread(
            mock_synth.synthesize, req.text, voice or MockVoice(), s.get("emotion", "neutral"), s.get("intensity", 3), seed
        )
        return SynthesisResult(mock_synth.to_pcm16(samples), "pcm", mock_synth.SR, pcm=True,
                               word_timings=words, timing_source="exact")


class FishAudioProvider:
    billable: bool

    def __init__(self, settings: Settings, mode: str):
        if mode not in FISH_MODELS:
            raise ValueError(f"unsupported fish mode {mode!r}")
        self.name = mode
        self.model = FISH_MODELS[mode]
        self.billable = mode == "drama3"
        self.key = settings.fish_audio_api_key
        self.base = settings.fish_audio_base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        if self.model not in FISH_MODELS.values():  # belt and braces
            raise ProviderError(f"refusing unknown model header {self.model!r}")
        return {"Authorization": f"Bearer {self.key}", "model": self.model, "Content-Type": "application/json"}

    def body(self, req: CompiledRequest) -> dict:
        s = req.settings
        return {
            "text": req.text,
            "reference_id": req.reference_ids[0] if len(req.reference_ids) == 1 else req.reference_ids,
            "format": s.get("format", "mp3"),
            "mp3_bitrate": s.get("mp3_bitrate", 128),
            "latency": s.get("latency", "normal"),
            "normalize": s.get("normalize", True),
            "temperature": s.get("temperature", 0.7),
            "top_p": s.get("top_p", 0.7),
            **({"prosody": {"speed": s["prosody"]["speed"], "normalize_loudness": True}} if s.get("prosody") else {}),
        }

    async def synthesize(self, req: CompiledRequest, voice: MockVoice | None = None) -> SynthesisResult:
        if not self.key:
            raise ProviderError("FISH_AUDIO_API_KEY is not set")
        if req.model != self.model:
            raise ProviderError(f"request compiled for {req.model}, provider is {self.model}")
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10)) as client:
                r = await client.post(f"{self.base}/v1/tts", headers=self._headers(), json=self.body(req))
        except httpx.ConnectError as exc:  # never reached the server: safe to retry
            raise ProviderError(f"connection failed: {exc}", retryable=True) from exc
        except httpx.TimeoutException as exc:  # may have been processed: do not auto-retry
            raise ProviderError("timed out waiting for audio; the request may have been billed", uncertain=True) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(f"transport error: {exc}", uncertain=True) from exc
        if r.status_code != 200:
            try:
                msg = r.json().get("message", r.text[:200])
            except ValueError:
                msg = r.text[:200]
            raise ProviderError(f"Fish Audio {r.status_code}: {msg}", status=r.status_code,
                                retryable=r.status_code in (429, 503) or (r.status_code >= 500 and r.status_code != 501))
        if not r.content or len(r.content) < 256:
            raise ProviderError("empty audio response", uncertain=True)
        return SynthesisResult(r.content, "mp3", 44100)

    async def balance(self) -> dict:
        """Verified balance endpoint (free GET)."""
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{self.base}/wallet/self/api-credit", headers={"Authorization": f"Bearer {self.key}"})
            r.raise_for_status()
            return r.json()


def get_audio_provider(settings: Settings, name: str | None = None) -> AudioProvider:
    name = name or settings.audio_provider
    if name in FISH_MODELS:
        return FishAudioProvider(settings, name)
    return MockAudioProvider()
