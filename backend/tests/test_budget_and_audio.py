import httpx
import pytest

from app.audio.budget import BudgetGuard, record
from app.audio.compiler import compile_line, compile_scene
from app.audio.providers import FishAudioProvider, ProviderError
from app.config import Settings
from app.domain.models import DialogueTurn, Performance
from app.models import Case

T = DialogueTurn(id="s1-t1", speaker="judge", text="[sigh] Overruled. *Emotionally*, I understand.",
                 performance=Performance(emotion="deadpan", delivery="dry", intensity=3))


def armed(**kw) -> Settings:
    base = dict(audio_provider="drama3", enable_paid_tts=True, fish_audio_api_key="k",
                drama3_max_projected_spend_usd=1.0, drama3_max_characters_per_case=500, drama3_demo_reserve_usd=3.0)
    return Settings(**{**base, **kw})


def test_drama3_compiler_syntax():
    req = compile_line("drama3", "drama-3", T, "voice-1", "deep")
    assert req.text.startswith("[deadpan; dry] ")
    assert "<emphasis>Emotionally</emphasis>" in req.text and "[sighs]" in req.text
    scene = compile_scene("drama-3", [T, T.model_copy(update={"id": "s1-t2", "speaker": "defense"})],
                          {"judge": ("A", "deep"), "defense": ("B", "smooth")})
    assert scene.text.splitlines()[0].startswith("<|speaker:0|>") and scene.text.splitlines()[1].startswith("<|speaker:1|>")
    assert scene.reference_ids == ["A", "B"]


def test_cache_key_stable_and_sensitive():
    a = compile_line("drama3", "drama-3", T, "v", "d")
    b = compile_line("drama3", "drama-3", T, "v", "d")
    c = compile_line("drama3", "drama-3", T, "v2", "d")
    d = compile_line("drama3", "drama-3", T.model_copy(update={"text": "Sustained."}), "v", "d")
    assert a.cache_key == b.cache_key
    assert len({a.cache_key, c.cache_key, d.cache_key}) == 3


async def _case(session, authorized=True) -> Case:
    c = Case(slug=f"b-{id(session)}-{authorized}", defendant="x", accusation="y", paid_audio_authorized=authorized)
    session.add(c)
    await session.flush()
    return c


async def test_paid_disabled_by_default(session):
    guard = BudgetGuard(Settings(fish_audio_api_key="k"))  # provider still mock
    c = await _case(session)
    d = await guard.check(session, c, compile_line("drama3", "drama-3", T, "v", "d"), billable=True)
    assert not d.allowed and d.code == "paid_disabled"


async def test_requires_case_authorization(session):
    d = await BudgetGuard(armed()).check(session, await _case(session, False), compile_line("drama3", "drama-3", T, "v", "d"), billable=True)
    assert not d.allowed and d.code == "not_authorized"


async def test_case_character_limit(session):
    guard = BudgetGuard(armed(drama3_max_characters_per_case=40))
    d = await guard.check(session, await _case(session), compile_line("drama3", "drama-3", T, "v", "d"), billable=True)
    assert not d.allowed and d.code == "case_limit"


async def test_spend_ceiling_counts_prior_spend(session):
    s = armed(drama3_max_projected_spend_usd=0.0001)
    c = await _case(session)
    req = compile_line("drama3", "drama-3", T, "v", "d")
    await record(session, case_id="other", req=req, outcome="synthesized", cost=0.0001, billable=True)
    await session.flush()
    d = await BudgetGuard(s).check(session, c, req, billable=True)
    assert not d.allowed and d.code == "spend_ceiling"


async def test_uncertain_duplicate_never_retried(session):
    c = await _case(session)
    req = compile_line("drama3", "drama-3", T.model_copy(update={"text": "Unique uncertain line."}), "v", "d")
    await record(session, case_id=c.id, req=req, outcome="uncertain", cost=0.00001, billable=True)
    await session.flush()
    d = await BudgetGuard(armed(drama3_max_projected_spend_usd=100)).check(session, c, req, billable=True)
    assert not d.allowed and d.code == "uncertain_duplicate"


async def test_allowed_when_everything_in_order(session):
    c = await _case(session)
    req = compile_line("drama3", "drama-3", T.model_copy(update={"text": "A brand new line."}), "v", "d")
    d = await BudgetGuard(armed(drama3_max_projected_spend_usd=100)).check(session, c, req, billable=True)
    assert d.allowed and d.cost_usd > 0


def _fish(handler) -> FishAudioProvider:
    p = FishAudioProvider(armed(), "drama3")
    real = httpx.AsyncClient

    class Patched(real):
        def __init__(self, *a, **kw):
            kw["transport"] = httpx.MockTransport(handler)
            super().__init__(*a, **kw)

    httpx.AsyncClient = Patched  # restored by the caller
    return p, real


@pytest.mark.parametrize("status,retryable", [(402, False), (401, False), (429, True), (503, True)])
async def test_fish_error_classification(status, retryable):
    p, real = _fish(lambda req: httpx.Response(status, json={"message": "nope", "status": status}))
    try:
        with pytest.raises(ProviderError) as e:
            await p.synthesize(compile_line("drama3", "drama-3", T, "v", "d"))
        assert e.value.retryable is retryable and not e.value.uncertain
    finally:
        httpx.AsyncClient = real


async def test_fish_sends_exact_model_header():
    seen = {}

    def handler(req: httpx.Request):
        seen.update(model=req.headers["model"], body=req.content)
        return httpx.Response(200, content=b"\xff" * 2048)

    p, real = _fish(handler)
    try:
        await p.synthesize(compile_line("drama3", "drama-3", T, "v", "d"))
    finally:
        httpx.AsyncClient = real
    assert seen["model"] == "drama-3"


def test_fish_refuses_unknown_mode():
    with pytest.raises(ValueError):
        FishAudioProvider(armed(), "s2.1-pro")


async def test_timeout_is_uncertain():
    def handler(req):
        raise httpx.ReadTimeout("slow", request=req)

    p, real = _fish(handler)
    try:
        with pytest.raises(ProviderError) as e:
            await p.synthesize(compile_line("drama3", "drama-3", T, "v", "d"))
        assert e.value.uncertain and not e.value.retryable
    finally:
        httpx.AsyncClient = real


def test_mock_synth_exact_timings():
    from app.audio import mock_synth
    from app.audio.mock_synth import MockVoice

    samples, words = mock_synth.synthesize("Order. [pause] This court is in session.", MockVoice(), "stern", 3, 1)
    assert [w["w"] for w in words] == ["Order.", "This", "court", "is", "in", "session."]
    assert all(a["e"] <= b["s"] for a, b in zip(words, words[1:]))
    assert words[1]["s"] - words[0]["e"] >= 450  # the [pause]
    assert words[-1]["e"] <= len(samples) * 1000 / mock_synth.SR


def test_scene_split_by_silence(tmp_path):
    """Three mock lines joined with clear gaps split back into three clips at the gaps."""
    import numpy as np

    from app.audio import ffmpeg, mock_synth
    from app.audio.mock_synth import MockVoice
    from app.audio.scene_split import cut_points, split_scene

    parts, lens = [], []
    for i, text in enumerate(["Order in the court.", "Objection! That is arithmetic.", "Overruled."]):
        samples, _ = mock_synth.synthesize(text, MockVoice(f0=120 + 60 * i), "neutral", 3, i)
        parts += [samples, np.zeros(int(mock_synth.SR * 0.9), dtype=np.float32)]
        lens.append(len(text))
    src = tmp_path / "scene.mp3"
    ffmpeg.encode_pcm(mock_synth.to_pcm16(np.concatenate(parts[:-1])), mock_synth.SR, src)
    pieces, method = split_scene(src, [tmp_path / f"{i}.mp3" for i in range(3)], lens)
    assert method == "silence" and len(pieces) == 3 and all(d > 300 for _, d in pieces)
    # Not enough gaps → proportional cuts, never a re-request.
    cuts, how = cut_points([], 3, 9000, [10, 20, 30])
    assert how == "proportional" and cuts == [1500, 4500]


def test_word_timings_never_show_provider_markup():
    from app.services.audio_generation import estimate_word_timings

    words = [w["w"] for w in estimate_word_timings("[stern, slow] Uphill. <emphasis>Both ways</emphasis>. <|speaker:1|>Hi", 4000)]
    assert words == ["Uphill.", "Both", "ways.", "Hi"]


def test_hand_authored_specials_validate_and_cast_their_own_voices():
    from app.audio.voices import cast
    from app.domain.validation import validate_script
    from app.showcase import monday

    assert validate_script(monday.PLAN, monday.SCRIPT).valid
    voices = cast(monday.PLAN.characters)
    assert voices["judge"].fish_voice_id == monday.PLAN.character("judge").voice.fish_voice
    assert len({v.fish_voice_id for v in voices.values()}) == len(voices)  # everyone sounds different
