"""Performance compiler: structured direction → provider script syntax.

Drama 3 (verified, docs/FISH_AUDIO_NOTES.md):
  - free-form bracket direction before the words:   [deadpan; slow, icy] Overruled.
  - bracket sounds where they occur:                [sigh] [small laugh]
  - paired word tags:                               <emphasis>…</emphasis> <whisper>…</whisper>
  - multi-speaker turns:                            <|speaker:0|>… with reference_id: [...]
S2.1 Pro (Free): free-form bracket cues; we keep only short emotion + sound cues.
Mock: plain text with our own cue tags (rendered by mock_synth).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass

from app.domain.models import DialogueTurn

_EMPH = re.compile(r"\*([^*]+)\*")
_WHISPER = re.compile(r"\[whisper\]\s*(.*)$", re.S)

EMOTION_WORDS = {
    "deadpan": "deadpan", "stern": "stern", "serious": "serious", "angry": "angry", "smug": "smug",
    "sarcastic": "sarcastic", "desperate": "desperate", "shocked": "shocked", "confused": "confused",
    "amused": "amused", "sad": "sad", "proud": "proud", "nervous": "nervous", "triumphant": "triumphant",
    "dramatic": "dramatic", "whispering": "whispering", "exasperated": "exasperated", "neutral": "",
}
_SOUND_MAP = {"laugh": "laughs", "chuckle": "small laugh", "sigh": "sighs", "gasp": "gasps", "scoff": "scoffs",
              "sobs": "sobs", "clears throat": "clears throat", "pause": "pause", "long pause": "long pause"}


def _drama3_line(turn: DialogueTurn, base_direction: str) -> str:
    text = turn.text
    m = _WHISPER.search(text)
    if m:
        text = text[: m.start()] + f"<whisper>{m.group(1).strip()}</whisper>"
    text = _EMPH.sub(r"<emphasis>\1</emphasis>", text)
    text = re.sub(r"\[([^\]]+)\]", lambda mm: f"[{_SOUND_MAP.get(mm.group(1).lower(), mm.group(1))}]", text)
    p = turn.performance
    bits = [b for b in (EMOTION_WORDS.get(p.emotion, p.emotion), p.delivery or base_direction) if b]
    if p.intensity >= 5:
        bits.append("at full intensity")
    elif p.intensity <= 1:
        bits.append("very understated")
    direction = "; ".join(bits)
    return f"[{direction}] {text}" if direction else text


def _s2_line(turn: DialogueTurn, base_direction: str = "") -> str:
    """S2.1 reads free-form bracket cues: give it the full acting note, not just one word."""
    text = _EMPH.sub(r"[emphasis] \1", turn.text)
    p = turn.performance
    emo = EMOTION_WORDS.get(p.emotion, p.emotion)
    note = p.delivery or base_direction
    bits = [b for b in (emo, note) if b]
    if p.intensity >= 5:
        bits.append("loud, at full intensity")
    direction = ", ".join(bits)[:120]
    return f"[{direction}] {text}" if direction else text


_PACE = {"slow": 0.9, "measured": 1.0, "fast": 1.1}
_EMOTION_PACE = {"angry": 0.06, "desperate": 0.08, "nervous": 0.07, "shocked": 0.04, "triumphant": 0.03,
                 "sad": -0.06, "deadpan": -0.03, "stern": -0.03, "whispering": -0.05}


def speech_speed(pace: str, emotion: str) -> float:
    return round(max(0.75, min(1.3, _PACE.get(pace, 1.0) + _EMOTION_PACE.get(emotion, 0.0))), 2)


@dataclass(slots=True)
class CompiledRequest:
    provider: str
    model: str
    text: str
    reference_ids: list[str]
    settings: dict
    turn_ids: list[str]

    @property
    def characters(self) -> int:
        # Conservative: every code point of the request text, tags included.
        return len(self.text)

    @property
    def cache_key(self) -> str:
        blob = json.dumps(
            {"p": self.provider, "m": self.model, "v": self.reference_ids, "t": self.text, "s": self.settings},
            sort_keys=True, ensure_ascii=False,
        )
        return hashlib.sha256(blob.encode()).hexdigest()


DEFAULT_SETTINGS = {"format": "mp3", "mp3_bitrate": 128, "latency": "normal", "normalize": True,
                    "temperature": 0.7, "top_p": 0.7}


def compile_line(provider: str, model: str, turn: DialogueTurn, voice_id: str, base_direction: str,
                 mock_seed: str = "", pace: str = "measured") -> CompiledRequest:
    speed = speech_speed(pace, turn.performance.emotion)
    if provider == "drama3":
        text = _drama3_line(turn, base_direction)
        settings = {**DEFAULT_SETTINGS, "prosody": {"speed": speed}}
    elif provider == "fish-free":
        text = _s2_line(turn, base_direction)
        settings = {**DEFAULT_SETTINGS, "prosody": {"speed": speed}}
    else:
        text = turn.text
        settings = {"emotion": turn.performance.emotion, "intensity": turn.performance.intensity, "seed": mock_seed, "v": 3}
    return CompiledRequest(provider, model, text, [voice_id], settings, [turn.id])


def compile_scene(model: str, turns: list[DialogueTurn], voices: dict[str, tuple[str, str]]) -> CompiledRequest:
    """Drama 3 multi-speaker block: one request, one coherent exchange."""
    speakers = list(dict.fromkeys(t.speaker for t in turns))  # speaker index = first appearance
    lines = [f"<|speaker:{speakers.index(t.speaker)}|>{_drama3_line(t, voices[t.speaker][1])}" for t in turns]
    order = [voices[k][0] for k in speakers]
    return CompiledRequest("drama3", model, "\n".join(lines), order, dict(DEFAULT_SETTINGS), [t.id for t in turns])
