import numpy as np

from app.audio import pacing


def _tone(ms: int) -> np.ndarray:
    t = np.arange(int(pacing.SR * ms / 1000)) / pacing.SR
    return (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def _quiet(ms: int) -> np.ndarray:
    return np.zeros(int(pacing.SR * ms / 1000), dtype=np.float32)


def test_tighten_shortens_dead_air_but_keeps_speech():
    x = np.concatenate([_quiet(600), _tone(800), _quiet(1500), _tone(700), _quiet(900)])
    y = pacing.tighten(x)
    before, after = pacing.voiced_segments(x), pacing.voiced_segments(y)
    assert len(after) == len(before) == 2
    for (a0, a1), (b0, b1) in zip(after, before, strict=True):
        assert abs((a1 - a0) - (b1 - b0)) <= 20  # speech untouched (10 ms frame resolution)
    assert after[0][0] <= pacing.LEAD_MS + 10
    assert after[1][0] - after[0][1] <= pacing.MAX_GAP_MS + 10
    assert len(y) < len(x) * 0.7


def test_captions_follow_pauses_in_the_audio():
    x = np.concatenate([_quiet(100), _tone(900), _quiet(400), _tone(1400), _quiet(150)])
    segs = pacing.voiced_segments(x)
    words = pacing.align_words("[angry] Order, order! [pause] Sit down right now, please.", segs, 2950)
    assert [w["w"] for w in words] == ["Order,", "order!", "Sit", "down", "right", "now,", "please."]
    second = segs[1][0]
    assert words[1]["e"] <= segs[0][1] + 5  # first sentence ends before the pause
    assert abs(words[2]["s"] - second) <= 5  # next sentence starts when the voice comes back
    assert all(a["s"] <= b["s"] for a, b in zip(words, words[1:]))
