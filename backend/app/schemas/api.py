from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CaseCreate(BaseModel):
    defendant: str = Field(min_length=2, max_length=120, examples=["My alarm clock"])
    accusation: str = Field(min_length=4, max_length=500, examples=["Destroying my dreams every single morning"])
    context: str = Field(default="", max_length=1000)
    language: str = Field(default="en", max_length=12)
    comedy_intensity: Literal["mild", "unserious", "chaos"] = "unserious"
    drama_level: int = Field(default=60, ge=1, le=100)
    trial_length: Literal["quick", "standard", "full"] = "quick"
    participation_mode: Literal["spectator", "jury", "chaos"] = "jury"
    llm_provider: Literal["mock", "ollama", "anthropic"] | None = None
    audio_provider: Literal["mock", "fish-free", "drama3"] | None = None

    @field_validator("defendant", "accusation", "context")
    @classmethod
    def _strip(cls, v: str) -> str:
        return " ".join(v.split())


class CaseSummary(BaseModel):
    id: str
    slug: str
    title: str
    case_number: str
    defendant: str
    accusation: str
    status: str
    status_detail: str
    trial_length: str
    participation_mode: str
    comedy_intensity: str
    drama_level: int
    is_showcase: bool
    is_featured: bool
    llm_provider: str
    audio_provider: str
    paid_audio_authorized: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CaseCreated(BaseModel):
    case: CaseSummary
    job_id: str


class JobOut(BaseModel):
    id: str
    kind: str
    status: str
    progress: dict
    result: dict
    error: str | None
    created_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class AudioPrepareIn(BaseModel):
    provider: Literal["mock", "fish-free"] = "mock"


class AudioAuthorizeIn(BaseModel):
    confirm: Literal["SPEND CREDITS"] = Field(description="Type exactly 'SPEND CREDITS'")
    expected_cost_usd: float = Field(ge=0, description="The estimate you were shown; must still match")
    allow_reserve: bool = Field(default=False, description="Allow dipping into the demo reserve (demo day only)")


class SessionCreate(BaseModel):
    mode: Literal["spectator", "jury", "chaos"] | None = None


class OptionChoice(BaseModel):
    option_id: str


class FreeIntervention(BaseModel):
    text: str = Field(min_length=3, max_length=240)

    @field_validator("text")
    @classmethod
    def _strip(cls, v: str) -> str:
        return " ".join(v.split())


class PodcastCreate(BaseModel):
    verdict: Literal["guilty", "not_guilty"] | None = None
    session_id: str | None = None


class SettingsPatch(BaseModel):
    default_llm_provider: Literal["mock", "ollama", "anthropic"] | None = None
    default_audio_provider: Literal["mock", "fish-free", "drama3"] | None = None
