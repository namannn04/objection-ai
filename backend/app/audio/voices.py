"""Voice casting. Stable voice per character; only authorised preset voices
(Fish Audio public library) — no cloning of real people.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.audio.mock_synth import MockVoice
from app.domain.models import CharacterSpec

# Public voices listed in the Fish Audio Drama 3 docs (see docs/FISH_AUDIO_NOTES.md).
FISH_PUBLIC = {
    "adrian": "bf322df2096a46f18c579d0baa36f41d",  # EN-US male
    "delia": "c70cfb98867a4bfb9ae20d2401257b92",  # EN-US female
    "sheila": "f3a2b90078d54a65af4b95f63bc7798e",  # EN-US female
    "s2_example": "9a9cf47702da476aa4629e2506d4a857",
}

# Optional local overrides: backend/voices.json {"judge": "<fish voice id>", "witness_1": "...", ...}
OVERRIDES_FILE = Path(__file__).resolve().parents[2] / "voices.json"


@dataclass(slots=True)
class VoiceChoice:
    fish_voice_id: str
    label: str
    base_direction: str
    mock: MockVoice = field(default_factory=MockVoice)


_ENSEMBLE: dict[str, VoiceChoice] = {
    "judge": VoiceChoice(FISH_PUBLIC["adrian"], "Adrian (deep, measured)",
                         "deep, authoritative, restrained; long weighty pauses",
                         MockVoice(f0=98, speed=4.6, brightness=0.35, breath=0.03, wobble=0.012, shape="reed")),
    "prosecutor": VoiceChoice(FISH_PUBLIC["delia"], "Delia (bright, assertive)",
                              "fast, dramatic, assertive, theatrical",
                              MockVoice(f0=215, speed=7.4, brightness=0.75, breath=0.04, wobble=0.025, shape="square")),
    "defense": VoiceChoice(FISH_PUBLIC["s2_example"], "S2 example voice (smooth)",
                           "smooth, sarcastic, unhurried, confident",
                           MockVoice(f0=132, speed=5.6, brightness=0.5, breath=0.05, wobble=0.02, shape="round")),
    "reporter": VoiceChoice(FISH_PUBLIC["sheila"], "Sheila (crisp narrator)",
                            "crisp broadcast narrator, dry and wry",
                            MockVoice(f0=190, speed=6.2, brightness=0.55, breath=0.03, wobble=0.015, shape="round")),
}

# Per-case characters cycle through the remaining palette with distinct timbres.
_POOL = [
    (FISH_PUBLIC["sheila"], "Sheila", MockVoice(f0=255, speed=6.8, brightness=0.6, breath=0.06, wobble=0.04, shape="round")),
    (FISH_PUBLIC["adrian"], "Adrian", MockVoice(f0=118, speed=6.4, brightness=0.8, breath=0.08, wobble=0.03, shape="square")),
    (FISH_PUBLIC["delia"], "Delia", MockVoice(f0=300, speed=7.8, brightness=0.45, breath=0.05, wobble=0.05, shape="reed")),
    (FISH_PUBLIC["s2_example"], "S2 example", MockVoice(f0=165, speed=5.2, brightness=0.3, breath=0.12, wobble=0.03, shape="reed")),
]

_PITCH = {"low": 0.78, "mid": 1.0, "high": 1.3}


def _overrides() -> dict[str, str]:
    try:
        return json.loads(OVERRIDES_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def cast(characters: list[CharacterSpec]) -> dict[str, VoiceChoice]:
    out: dict[str, VoiceChoice] = {}
    ov = _overrides()
    i = 0
    for c in characters:
        if c.key in _ENSEMBLE:
            choice = _ENSEMBLE[c.key]
        else:
            vid, label, mv = _POOL[i % len(_POOL)]
            i += 1
            mv = MockVoice(f0=mv.f0 * _PITCH.get(c.voice.pitch, 1.0), speed=mv.speed, brightness=mv.brightness,
                           breath=mv.breath, wobble=mv.wobble, shape=mv.shape)
            choice = VoiceChoice(vid, label, c.voice.description.rstrip(".").lower(), mv)
        if c.key in ov:
            choice = VoiceChoice(ov[c.key], f"override:{c.key}", choice.base_direction, choice.mock)
        out[c.key] = choice
    return out
