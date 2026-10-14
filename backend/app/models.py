"""Relational schema. PostgreSQL holds authoritative case state; media lives on disk."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class Profile(Base, TimestampMixin):
    """Local, anonymous profile. No auth: the app runs on localhost."""

    __tablename__ = "profiles"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    display_name: Mapped[str] = mapped_column(String(80), default="Anonymous Juror")


class AppSetting(Base, TimestampMixin):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)


class Case(Base, TimestampMixin):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    profile_id: Mapped[str | None] = mapped_column(ForeignKey("profiles.id"), nullable=True)
    defendant: Mapped[str] = mapped_column(String(120))
    accusation: Mapped[str] = mapped_column(Text)
    context: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(12), default="en")
    comedy_intensity: Mapped[str] = mapped_column(String(16), default="unserious")
    drama_level: Mapped[int] = mapped_column(Integer, default=60)
    trial_length: Mapped[str] = mapped_column(String(16), default="quick")
    participation_mode: Mapped[str] = mapped_column(String(16), default="jury")
    status: Mapped[str] = mapped_column(String(32), default="CASE_CREATED", index=True)
    status_detail: Mapped[str] = mapped_column(Text, default="")
    title: Mapped[str] = mapped_column(String(200), default="")
    case_number: Mapped[str] = mapped_column(String(40), default="")
    is_showcase: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    llm_provider: Mapped[str] = mapped_column(String(24), default="mock")
    audio_provider: Mapped[str] = mapped_column(String(24), default="mock")
    current_version: Mapped[int] = mapped_column(Integer, default=0)
    paid_audio_authorized: Mapped[bool] = mapped_column(Boolean, default=False)

    versions: Mapped[list[CaseVersion]] = relationship(back_populates="case", cascade="all, delete-orphan")
    characters: Mapped[list[Character]] = relationship(back_populates="case", cascade="all, delete-orphan")
    evidence: Mapped[list[EvidenceItem]] = relationship(back_populates="case", cascade="all, delete-orphan")
    scenes: Mapped[list[SceneRow]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="SceneRow.order"
    )
    sessions: Mapped[list[CourtroomSession]] = relationship(back_populates="case", cascade="all, delete-orphan")


class CaseVersion(Base, TimestampMixin):
    """Immutable snapshot of a plan + script (+ humor report). New version on every regeneration."""

    __tablename__ = "case_versions"
    __table_args__ = (UniqueConstraint("case_id", "version"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    plan: Mapped[dict] = mapped_column(JSON)
    script: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    humor_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validation_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generator: Mapped[str] = mapped_column(String(60), default="")

    case: Mapped[Case] = relationship(back_populates="versions")


class AgentConfiguration(Base, TimestampMixin):
    """Per-role agent definition: system prompt template, temperature, allowed actions."""

    __tablename__ = "agent_configurations"
    role: Mapped[str] = mapped_column(String(24), primary_key=True)
    system_prompt: Mapped[str] = mapped_column(Text)
    temperature: Mapped[float] = mapped_column(Float, default=0.9)
    allowed_actions: Mapped[list] = mapped_column(JSON, default=list)


class Character(Base, TimestampMixin):
    __tablename__ = "characters"
    __table_args__ = (UniqueConstraint("case_id", "key"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(48))
    role: Mapped[str] = mapped_column(String(24))
    name: Mapped[str] = mapped_column(String(80))
    spec: Mapped[dict] = mapped_column(JSON)

    case: Mapped[Case] = relationship(back_populates="characters")
    voice: Mapped[VoiceAssignment | None] = relationship(
        back_populates="character", cascade="all, delete-orphan", uselist=False
    )


class VoiceAssignment(Base, TimestampMixin):
    __tablename__ = "voice_assignments"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    character_id: Mapped[str] = mapped_column(ForeignKey("characters.id", ondelete="CASCADE"), unique=True)
    provider: Mapped[str] = mapped_column(String(24))
    voice_id: Mapped[str] = mapped_column(String(80))
    voice_label: Mapped[str] = mapped_column(String(80), default="")
    base_direction: Mapped[str] = mapped_column(Text, default="")
    mock_params: Mapped[dict] = mapped_column(JSON, default=dict)

    character: Mapped[Character] = relationship(back_populates="voice")


class EvidenceItem(Base, TimestampMixin):
    __tablename__ = "evidence_items"
    __table_args__ = (UniqueConstraint("case_id", "exhibit"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    exhibit: Mapped[str] = mapped_column(String(2))
    title: Mapped[str] = mapped_column(String(200))
    spec: Mapped[dict] = mapped_column(JSON)

    case: Mapped[Case] = relationship(back_populates="evidence")


class SceneRow(Base, TimestampMixin):
    """A scene of the trial. `phase` doubles as the trial-phase record."""

    __tablename__ = "scenes"
    __table_args__ = (UniqueConstraint("case_id", "scene_key"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    scene_key: Mapped[str] = mapped_column(String(48))
    order: Mapped[int] = mapped_column(Integer)
    phase: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(200))
    strategy: Mapped[str] = mapped_column(String(8), default="line")
    branch: Mapped[str | None] = mapped_column(String(32), nullable=True)
    window: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    humor_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    case: Mapped[Case] = relationship(back_populates="scenes")
    turns: Mapped[list[DialogueTurnRow]] = relationship(
        back_populates="scene", cascade="all, delete-orphan", order_by="DialogueTurnRow.order"
    )


class DialogueTurnRow(Base, TimestampMixin):
    __tablename__ = "dialogue_turns"
    __table_args__ = (Index("ix_turns_scene_branch_order", "scene_id", "branch_key", "order"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("courtroom_sessions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    turn_key: Mapped[str] = mapped_column(String(64), index=True)
    branch_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    order: Mapped[int] = mapped_column(Integer)
    speaker: Mapped[str] = mapped_column(String(48))
    text: Mapped[str] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSON)
    audio_asset_id: Mapped[str | None] = mapped_column(ForeignKey("audio_assets.id"), nullable=True)

    scene: Mapped[SceneRow] = relationship(back_populates="turns")
    audio: Mapped[AudioAsset | None] = relationship()


class WitnessStatement(Base, TimestampMixin):
    """Facts a witness committed to on the record; used to detect and stage contradictions."""

    __tablename__ = "witness_statements"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    witness_key: Mapped[str] = mapped_column(String(48))
    turn_key: Mapped[str] = mapped_column(String(64))
    statement: Mapped[str] = mapped_column(Text)
    contradicted_by: Mapped[str | None] = mapped_column(String(64), nullable=True)


class CourtroomSession(Base, TimestampMixin):
    """One viewing of a case. Replays and alternate verdicts are new sessions."""

    __tablename__ = "courtroom_sessions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    case_version: Mapped[int] = mapped_column(Integer)
    participation_mode: Mapped[str] = mapped_column(String(16))
    phase: Mapped[str] = mapped_column(String(32), default="COURTROOM_READY")
    cursor_scene: Mapped[int] = mapped_column(Integer, default=0)
    open_window_scene: Mapped[str | None] = mapped_column(String(48), nullable=True)
    phase_history: Mapped[list] = mapped_column(JSON, default=list)
    parent_session_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    case: Mapped[Case] = relationship(back_populates="sessions")
    interventions: Mapped[list[UserIntervention]] = relationship(cascade="all, delete-orphan")
    votes: Mapped[list[JuryVote]] = relationship(cascade="all, delete-orphan")
    verdict: Mapped[Verdict | None] = relationship(cascade="all, delete-orphan", uselist=False)


class UserIntervention(Base, TimestampMixin):
    __tablename__ = "user_interventions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("courtroom_sessions.id", ondelete="CASCADE"), index=True)
    scene_key: Mapped[str] = mapped_column(String(48))
    kind: Mapped[str] = mapped_column(String(16))  # objection | question | vote | free
    option_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    free_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="accepted")  # accepted|generating|ready|fallback|rejected
    response_turn_keys: Mapped[list] = mapped_column(JSON, default=list)
    effect: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(16), default="pregenerated")  # pregenerated|live|fallback


class Objection(Base, TimestampMixin):
    __tablename__ = "objections"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("courtroom_sessions.id", ondelete="CASCADE"), index=True)
    intervention_id: Mapped[str] = mapped_column(ForeignKey("user_interventions.id", ondelete="CASCADE"))
    grounds: Mapped[str] = mapped_column(Text)
    ruling: Mapped[str] = mapped_column(String(12))  # sustained | overruled


class JuryVote(Base, TimestampMixin):
    __tablename__ = "jury_votes"
    __table_args__ = (UniqueConstraint("session_id", "scene_key"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("courtroom_sessions.id", ondelete="CASCADE"), index=True)
    scene_key: Mapped[str] = mapped_column(String(48))
    choice: Mapped[str] = mapped_column(String(16))  # prosecution | defense
    weight: Mapped[int] = mapped_column(Integer, default=3)


class Verdict(Base, TimestampMixin):
    __tablename__ = "verdicts"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("courtroom_sessions.id", ondelete="CASCADE"), unique=True)
    guilty: Mapped[bool] = mapped_column(Boolean)
    headline: Mapped[str] = mapped_column(String(200))
    reasoning: Mapped[str] = mapped_column(Text)
    sentence: Mapped[str] = mapped_column(Text)
    scoreboard: Mapped[dict] = mapped_column(JSON)
    highlights: Mapped[dict] = mapped_column(JSON, default=dict)


class AudioAsset(Base, TimestampMixin):
    """A synthesized (or fixture) audio file, addressed by content cache key."""

    __tablename__ = "audio_assets"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    cache_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(24))
    model: Mapped[str] = mapped_column(String(40))
    path: Mapped[str] = mapped_column(String(300))
    format: Mapped[str] = mapped_column(String(8))
    duration_ms: Mapped[int] = mapped_column(Integer)
    size_bytes: Mapped[int] = mapped_column(Integer)
    characters: Mapped[int] = mapped_column(Integer, default=0)
    timings: Mapped[dict] = mapped_column(JSON, default=dict)  # per-turn offsets / word timings
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class AudioGenerationJob(Base, TimestampMixin):
    __tablename__ = "audio_generation_jobs"
    __table_args__ = (Index("ix_jobs_status_created", "status", "created_at"),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String(32))  # prepare_case | synthesize_case | intervention | export
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued|running|done|failed|blocked
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    progress: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UsageRecord(Base, TimestampMixin):
    """Audit log of every synthesis attempt (including cache hits and blocked requests)."""

    __tablename__ = "usage_records"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(24), index=True)
    model: Mapped[str] = mapped_column(String(40))
    request_hash: Mapped[str] = mapped_column(String(64), index=True)
    characters: Mapped[int] = mapped_column(Integer)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    outcome: Mapped[str] = mapped_column(String(16))  # cache_hit|synthesized|blocked|failed|uncertain
    detail: Mapped[str] = mapped_column(Text, default="")
    billable: Mapped[bool] = mapped_column(Boolean, default=False)


class PodcastEpisode(Base, TimestampMixin):
    __tablename__ = "podcast_episodes"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    session_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    mp3_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    wav_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    chapters: Mapped[list] = mapped_column(JSON, default=list)
    transcript: Mapped[list] = mapped_column(JSON, default=list)


class Highlight(Base, TimestampMixin):
    __tablename__ = "highlights"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(32))
    turn_keys: Mapped[list] = mapped_column(JSON)
    label: Mapped[str] = mapped_column(String(200))
    clip_path: Mapped[str | None] = mapped_column(String(300), nullable=True)
    share_token: Mapped[str] = mapped_column(String(32), default=_uuid, unique=True)
