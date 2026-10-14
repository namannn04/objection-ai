"""PlaybackManifestService: everything the courtroom player needs, in order.

The client preloads every segment (main trial, both verdict branches, and all
pre-generated intervention responses), so choices and verdicts play without
waiting on the network.
"""

from __future__ import annotations

from app.domain.models import DialogueTurn, subtitle_text
from app.models import Case, DialogueTurnRow, SceneRow
from app.services.audio_generation import SFX_NAMES, asset_url

DEFAULT_GAP_MS = 220

_BEFORE = {"objection", "dramatic_sting", "crowd_murmur"}
_AFTER = {"crowd_gasp", "crowd_laugh"}


def _sfx_split(turn: DialogueTurn) -> tuple[list[str], list[str]]:
    before, after = [], []
    for fx in turn.sfx:
        if fx == "gavel":
            (after if turn.kind in ("verdict", "sentence") else before).append(fx)
        elif fx in _BEFORE:
            before.append(fx)
        elif fx in _AFTER:
            after.append(fx)
    return before, after


def segment(row: DialogueTurnRow) -> dict:
    turn = DialogueTurn.model_validate(row.data)
    before, after = _sfx_split(turn)
    audio = None
    if row.audio is not None:
        a = row.audio
        audio = {
            "url": asset_url(a), "duration_ms": a.duration_ms, "provider": a.provider, "model": a.model,
            "words": a.timings.get("words", []), "timing_source": a.timings.get("source", "estimated"),
        }
    return {
        "turn_key": row.turn_key,
        "speaker": row.speaker,
        "kind": turn.kind,
        "text": turn.text,
        "subtitle": subtitle_text(turn.text),
        "emotion": turn.performance.emotion,
        "delivery": turn.performance.delivery,
        "intensity": turn.performance.intensity,
        "reactions": turn.reactions,
        "evidence_id": turn.evidence_id,
        "technique": turn.technique,
        "scores": turn.scores,
        "points": turn.points,
        "gap_before_ms": DEFAULT_GAP_MS + turn.performance.pause_before_ms,
        "sfx_before": before,
        "sfx_after": after,
        "audio": audio,
    }


def scene_payload(scene: SceneRow, session_id: str | None = None) -> dict:
    main = [segment(r) for r in scene.turns if r.branch_key is None and r.session_id is None]
    branches: dict[str, list[dict]] = {}
    for r in scene.turns:
        if r.branch_key and (r.session_id is None or r.session_id == session_id):
            branches.setdefault(r.branch_key, []).append(segment(r))
    window = None
    if scene.window:
        window = {
            **{k: v for k, v in scene.window.items() if k != "options"},
            "options": [
                {"id": o["id"], "label": o["label"], "text": o["text"], "favours": o.get("favours"),
                 "points": o.get("points", 0), "response": branches.get(o["id"], [])}
                for o in scene.window["options"]
            ],
        }
    return {
        "key": scene.scene_key, "order": scene.order, "phase": scene.phase, "title": scene.title,
        "branch": scene.branch, "strategy": scene.strategy, "humor_score": scene.humor_score,
        "segments": main, "window": window,
        "live_branches": {k: v for k, v in branches.items() if k.startswith("live-")},
    }


def build_manifest(case: Case, sfx_base: str = "/media/sfx") -> dict:
    scenes = [scene_payload(s) for s in case.scenes]
    all_segments = [seg for s in scenes for seg in s["segments"]] + [
        r for s in scenes if s["window"] for o in s["window"]["options"] for r in o["response"]
    ]
    missing = [s["turn_key"] for s in all_segments if s["audio"] is None]
    providers = sorted({s["audio"]["provider"] for s in all_segments if s["audio"]})
    main_ms = sum(seg["audio"]["duration_ms"] + seg["gap_before_ms"] for s in scenes if not s["branch"]
                  for seg in s["segments"] if seg["audio"])
    return {
        "case": {
            "id": case.id, "slug": case.slug, "title": case.title, "case_number": case.case_number,
            "defendant": case.defendant, "accusation": case.accusation, "status": case.status,
            "participation_mode": case.participation_mode, "trial_length": case.trial_length,
            "drama_level": case.drama_level, "is_showcase": case.is_showcase, "version": case.current_version,
        },
        "characters": [
            {"key": c.key, "role": c.role, "name": c.name, "title": c.spec.get("title", ""),
             "personality": c.spec.get("personality", ""), "relationship": c.spec.get("relationship_to_case", ""),
             "visual": c.spec.get("visual", {}), "surprise": c.spec.get("surprise", False),
             "voice": {"label": c.voice.voice_label, "direction": c.voice.base_direction} if c.voice else None}
            for c in sorted(case.characters, key=lambda c: c.key)
        ],
        "evidence": [{"id": e.exhibit, **e.spec} for e in sorted(case.evidence, key=lambda e: e.exhibit)],
        "scenes": scenes,
        "sfx": {name: f"{sfx_base}/{name}.mp3" for name in SFX_NAMES},
        "audio": {"ready": not missing, "missing": missing[:20], "providers": providers,
                  "estimated_main_duration_ms": main_ms},
    }
