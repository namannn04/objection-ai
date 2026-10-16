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
    # Generic community voices from the public library (no impersonations of real people or characters).
    "brian_british": "65c0b8155c464a648161af8877404f11",  # male, old, calm narrator
    "deep_smooth": "bb742915b1fa41b389a850b11efae0c8",  # male, middle-aged, smooth
    "sarah": "933563129e564b19a115bedd57b7406a",  # female, young, soft narration
    "energetic_male": "802e3bc2b27e49c2995d23ef70e6ac89",  # male, young, energetic
    "ethan": "536d3a5e000945adb7038665781a4aca",  # male, middle-aged, professional
    "robot": "175d7d5358b644d2ad2e8b7e4e13ece3",  # male, deep, calm, robotic
    "dramatic_male": "7a18a1851d2649108c48ec9f2c80eb2c",  # male, old, dramatic character
    "friendly_woman": "57d4a7fa3d944ca5b2407f916ce5f4d5",  # female, middle-aged, friendly
    "old_man": "00731df901a74de5b9b000713f14718c",  # male, old, deep, raspy, lived-in
    "man_mae": "48b83695ea7f4b2d8ebcd63a0775a3bd",  # male, middle-aged, calm, conversational, smooth
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
    "judge": VoiceChoice(FISH_PUBLIC["old_man"], "Old Man (deep, raspy, lived-in)",
                         "deep, authoritative, restrained; long weighty pauses",
                         MockVoice(f0=98, speed=4.6, brightness=0.35, breath=0.03, wobble=0.012, shape="reed")),
    "prosecutor": VoiceChoice(FISH_PUBLIC["delia"], "Delia (bright, assertive)",
                              "fast, dramatic, assertive, theatrical",
                              MockVoice(f0=215, speed=7.4, brightness=0.75, breath=0.04, wobble=0.025, shape="square")),
    "defense": VoiceChoice(FISH_PUBLIC["man_mae"], "Mae (calm, conversational)",
                           "smooth, sarcastic, unhurried, confident",
                           MockVoice(f0=132, speed=5.6, brightness=0.5, breath=0.05, wobble=0.02, shape="round")),
    "reporter": VoiceChoice(FISH_PUBLIC["sarah"], "Sarah (soft narrator)",
                            "crisp broadcast narrator, dry and wry",
                            MockVoice(f0=190, speed=6.2, brightness=0.55, breath=0.03, wobble=0.015, shape="round")),
}

# Per-case characters cycle through the remaining palette with distinct timbres.
_POOL = [
    (FISH_PUBLIC["energetic_male"], "Energetic Male", MockVoice(f0=165, speed=7.2, brightness=0.6, breath=0.05, wobble=0.04, shape="square")),
    (FISH_PUBLIC["ethan"], "Ethan", MockVoice(f0=140, speed=6.6, brightness=0.5, breath=0.04, wobble=0.02, shape="round")),
    (FISH_PUBLIC["robot"], "Robot", MockVoice(f0=104, speed=5.0, brightness=0.3, breath=0.02, wobble=0.005, shape="reed")),
    (FISH_PUBLIC["dramatic_male"], "Dramatic Male", MockVoice(f0=118, speed=5.4, brightness=0.7, breath=0.1, wobble=0.04, shape="reed")),
    (FISH_PUBLIC["sheila"], "Sheila", MockVoice(f0=255, speed=6.8, brightness=0.6, breath=0.06, wobble=0.04, shape="round")),
    (FISH_PUBLIC["friendly_woman"], "Friendly Woman", MockVoice(f0=230, speed=6.4, brightness=0.55, breath=0.05, wobble=0.03, shape="round")),
    (FISH_PUBLIC["adrian"], "Adrian", MockVoice(f0=118, speed=6.4, brightness=0.8, breath=0.08, wobble=0.03, shape="square")),
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
        if c.voice.fish_voice:
            choice = VoiceChoice(c.voice.fish_voice, c.voice.fish_label or c.name,
                                 c.voice.description.rstrip(".").lower(), choice.mock)
        if c.key in ov:
            choice = VoiceChoice(ov[c.key], f"override:{c.key}", choice.base_direction, choice.mock)
        out[c.key] = choice
    return out
