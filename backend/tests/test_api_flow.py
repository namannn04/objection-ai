"""End-to-end through the HTTP API with mock providers."""

import pytest
from sqlalchemy import func, select

from app.db import session_factory
from app.models import AudioAsset, UsageRecord


async def _ready_case(client, drain, **body):
    r = await client.post("/api/cases", json={"defendant": "my alarm clock", "accusation": "destroying my dreams", **body})
    assert r.status_code == 201, r.text
    case_id = r.json()["case"]["id"]
    await drain()
    st = (await client.get(f"/api/cases/{case_id}/status")).json()
    assert st["status"] == "COURTROOM_READY", st
    return case_id


async def test_validation_errors(client):
    r = await client.post("/api/cases", json={"defendant": "x", "accusation": "y"})
    assert r.status_code == 422


async def test_case_creation_and_persistence(client, drain):
    case_id = await _ready_case(client, drain)
    detail = (await client.get(f"/api/cases/{case_id}")).json()
    assert detail["plan"]["title"].startswith("The People vs.")
    assert detail["validation"]["valid"] is True
    assert len(detail["evidence"]) == 3
    lst = (await client.get("/api/cases")).json()
    assert any(c["id"] == case_id for c in lst)


async def test_manifest_ordering_and_audio(client, drain):
    case_id = await _ready_case(client, drain, trial_length="standard")
    m = (await client.get(f"/api/cases/{case_id}/manifest")).json()
    assert m["audio"]["ready"] and m["audio"]["providers"] == ["mock"]
    keys = [s["key"] for s in m["scenes"]]
    assert keys[0] == "s01" and keys[-2:] == ["v_guilty", "v_not_guilty"]
    for sc in m["scenes"]:
        turns = [seg["turn_key"] for seg in sc["segments"]]
        assert turns == sorted(turns)
        for seg in sc["segments"]:
            a = seg["audio"]
            assert a["duration_ms"] > 300 and a["timing_source"] == "exact"
            assert a["words"][-1]["e"] <= a["duration_ms"]
    audio = await client.get(m["scenes"][0]["segments"][0]["audio"]["url"])
    assert audio.status_code == 200 and len(audio.content) > 1000


async def test_audio_cache_reused(client, drain):
    case_id = await _ready_case(client, drain)
    async with session_factory()() as s:
        n_assets = (await s.execute(select(func.count(AudioAsset.id)))).scalar_one()
    r = await client.post(f"/api/cases/{case_id}/audio/prepare", json={"provider": "mock"})
    assert r.status_code == 200
    await drain()
    async with session_factory()() as s:
        assert (await s.execute(select(func.count(AudioAsset.id)))).scalar_one() == n_assets
        hits = (await s.execute(select(func.count()).where(UsageRecord.case_id == case_id, UsageRecord.outcome == "cache_hit"))).scalar_one()
    assert hits > 10


async def test_paid_authorization_refused_when_disarmed(client, drain):
    case_id = await _ready_case(client, drain)
    est = (await client.get(f"/api/cases/{case_id}/audio/estimate?provider=drama3")).json()
    assert est["billable"] and est["estimated_cost_usd"] > 0 and est["provider_available"] is False
    r = await client.post(f"/api/cases/{case_id}/audio/authorize",
                          json={"confirm": "SPEND CREDITS", "expected_cost_usd": est["estimated_cost_usd"]})
    assert r.status_code == 409
    r = await client.post(f"/api/cases/{case_id}/audio/prepare", json={"provider": "fish-free"})
    assert r.status_code == 409


async def _post(client, path, body=None):
    r = await client.post(path, json=body or {})
    return r


async def _play_to_verdict(client, sid, final_choice: str, objection: str | None = "o1"):
    st = (await _post(client, f"/api/sessions/{sid}/start")).json()
    assert st["phase"] == "OPENING_STATEMENTS"
    while st["phase"] not in ("VERDICT", "CASE_COMPLETED"):
        if st["open_window"]:
            sc = st["open_window"]
            if sc == "s08":
                r = await _post(client, f"/api/sessions/{sid}/windows/{sc}/choose", {"option_id": f"s08-w-{final_choice}"})
                assert r.status_code == 200, r.text
            elif sc == "s02" and objection:
                r = await _post(client, f"/api/sessions/{sid}/windows/{sc}/choose", {"option_id": f"s02-w-{objection}"})
                assert r.json()["response_turn_keys"]
            st = (await _post(client, f"/api/sessions/{sid}/windows/resolve")).json()
            continue
        r = await _post(client, f"/api/sessions/{sid}/scenes/{st['next_scene']}/complete")
        assert r.status_code == 200, r.text
        st = r.json()
    return st


@pytest.mark.parametrize("choice,guilty", [("prosecution", True), ("defense", False)])
async def test_jury_vote_drives_verdict(client, drain, choice, guilty):
    case_id = await _ready_case(client, drain)
    sid = (await _post(client, f"/api/cases/{case_id}/sessions", {"mode": "jury"})).json()["state"]["session_id"]
    st = await _play_to_verdict(client, sid, choice)
    assert st["phase"] == "VERDICT"
    v = (await client.get(f"/api/sessions/{sid}/verdict")).json()
    assert v["guilty"] is guilty
    assert v["scoreboard"]["jury"]["guilty"] + v["scoreboard"]["jury"]["not_guilty"] == 12
    done = (await _post(client, f"/api/sessions/{sid}/scenes/{st['verdict_scene']}/complete")).json()
    assert done["phase"] == "CASE_COMPLETED"


async def test_out_of_order_and_double_objection_rejected(client, drain):
    case_id = await _ready_case(client, drain)
    sid = (await _post(client, f"/api/cases/{case_id}/sessions", {"mode": "jury"})).json()["state"]["session_id"]
    await _post(client, f"/api/sessions/{sid}/start")
    assert (await _post(client, f"/api/sessions/{sid}/scenes/s02/complete")).status_code == 409
    await _post(client, f"/api/sessions/{sid}/scenes/s01/complete")
    assert (await _post(client, f"/api/sessions/{sid}/scenes/s02/complete")).status_code == 409  # window open
    ok = await _post(client, f"/api/sessions/{sid}/windows/s01/choose", {"option_id": "s01-w-defense"})
    assert ok.status_code == 200
    again = await _post(client, f"/api/sessions/{sid}/windows/s01/choose", {"option_id": "s01-w-prosecution"})
    assert again.status_code == 429


async def test_spectator_mode_has_no_windows(client, drain):
    case_id = await _ready_case(client, drain)
    sid = (await _post(client, f"/api/cases/{case_id}/sessions", {"mode": "spectator"})).json()["state"]["session_id"]
    st = await _play_to_verdict(client, sid, "prosecution")
    assert st["phase"] == "VERDICT" and not st["votes"]


async def test_replay_preserves_history(client, drain):
    case_id = await _ready_case(client, drain)
    sid = (await _post(client, f"/api/cases/{case_id}/sessions", {"mode": "jury"})).json()["state"]["session_id"]
    await _play_to_verdict(client, sid, "prosecution")
    new = (await _post(client, f"/api/sessions/{sid}/replay", {})).json()["state"]["session_id"]
    await _play_to_verdict(client, new, "defense")
    assert (await client.get(f"/api/sessions/{sid}/verdict")).json()["guilty"] is True
    assert (await client.get(f"/api/sessions/{new}/verdict")).json()["guilty"] is False
