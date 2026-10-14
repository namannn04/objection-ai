"""Runtime configuration. Every setting has a safe default: mock audio, mock LLM, no paid calls."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]

AudioProviderName = Literal["mock", "fish-free", "drama3"]
LLMProviderName = Literal["mock", "ollama", "anthropic"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", ".env"), extra="ignore", case_sensitive=False
    )

    # audio
    audio_provider: AudioProviderName = "mock"
    fish_audio_api_key: str = ""
    fish_audio_base_url: str = "https://api.fish.audio"
    enable_paid_tts: bool = False
    drama3_max_projected_spend_usd: float = 2.0
    drama3_max_characters_per_case: int = 6000
    drama3_demo_reserve_usd: float = 3.0
    # Drama 3 list price is $50 / 1M characters (launch promo $10 until 2026-11-12).
    # Estimates use the list price on purpose: over-estimating protects the demo credit.
    drama3_usd_per_million_chars: float = 50.0
    # Experimental: synthesize whole scenes as Drama 3 multi-speaker blocks, then split per line.
    drama3_scene_strategy: bool = False

    # llm
    llm_provider: LLMProviderName = "mock"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5-5"
    llm_timeout_s: float = 120.0

    # infrastructure
    database_url: str = "postgresql+asyncpg://objection:objection@localhost:5434/objection"
    redis_url: str = "redis://localhost:6381/0"
    storage_dir: Path = Field(default=ROOT_DIR / "storage")
    run_worker_in_process: bool = True
    cors_origins: str = "http://localhost:3000"
    public_api_url: str = "http://localhost:8000"

    @property
    def audio_dir(self) -> Path:
        p = self.storage_dir / "audio"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def export_dir(self) -> Path:
        p = self.storage_dir / "exports"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def paid_tts_armed(self) -> bool:
        """Drama 3 is armed only with every explicit opt-in present."""
        return (
            self.audio_provider == "drama3"
            and self.enable_paid_tts
            and bool(self.fish_audio_api_key)
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
