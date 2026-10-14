from app.agents.agents import DefenseAgent, ProsecutorAgent, TurnContext, WitnessAgent, agent_for
from app.agents.blueprint import blueprint
from app.agents.director import CaseInput, SceneBrief, default_brief, fallback_plan_draft, assemble_plan
from app.agents.graph import generate_trial
from app.domain.models import CUE_TAGS, DialogueTurn, Phase, subtitle_text
from app.domain.validation import validate_script
from app.llm.providers import MockLLM

CI = CaseInput(case_id="t1", defendant="the office Wi-Fi", accusation="disappearing during my meetings",
               trial_length="standard", case_number="CR-TEST-1")


def _plan():
    return assemble_plan(fallback_plan_draft(CI), CI)


def _ctx(plan, slot_idx=0):
    spec = blueprint("standard")[0]
    return TurnContext(plan=plan, case=CI, spec=spec, slot=spec.slots[slot_idx], slot_index=slot_idx,
                       brief=default_brief(spec, plan), transcript=[], strategy="secret plan")


def test_plan_has_full_cast_and_evidence():
    plan = _plan()
    roles = {c.role for c in plan.characters}
    assert {"judge", "prosecutor", "defense", "defendant", "witness", "reporter"} <= roles
    assert [e.id for e in plan.evidence] == ["A", "B", "C"]
    assert plan.evidence[2].favours == "defense" and plan.evidence[2].is_twist
    assert any(c.surprise for c in plan.characters)


def test_agents_have_distinct_private_context():
    plan = _plan()
    t = _ctx(plan)
    pros = ProsecutorAgent(plan.character("prosecutor")).user_prompt(t)
    defense_sys = DefenseAgent(plan.character("defense")).system_prompt(t)
    defense_user = DefenseAgent(plan.character("defense")).user_prompt(t)
    twist_ev = plan.evidence[2].title
    # Only the defense knows the twist and the twist exhibit.
    assert plan.plot_twist in defense_sys
    assert twist_ev in defense_user and twist_ev not in pros
    witness = next(c for c in plan.characters if c.key == "witness_1")
    wsys = WitnessAgent(witness).system_prompt(t)
    assert witness.private_knowledge[1] in wsys
    assert witness.private_knowledge[1] not in ProsecutorAgent(plan.character("prosecutor")).system_prompt(t)


def test_agent_types_follow_roles():
    plan = _plan()
    for c in plan.characters:
        assert agent_for(c).role == c.role


async def test_generated_trial_is_valid_and_structured():
    state = await generate_trial(MockLLM(), CI)
    script, plan = state["script"], state["plan"]
    report = validate_script(plan, script)
    assert report.valid, report.errors
    phases = [s.phase for s in script.main_scenes()]
    assert phases[0] is Phase.OPENING_STATEMENTS and phases[-1] is Phase.DELIBERATION
    assert script.verdict_scene(True) and script.verdict_scene(False)
    for t in script.all_turns():
        assert isinstance(t, DialogueTurn) and t.subtitle
        for tag in __import__("re").findall(r"\[([^\]]+)\]", t.text):
            assert tag in CUE_TAGS
    # Windows carry pre-generated responses.
    windows = [s.window for s in script.scenes if s.window]
    assert any(w.kind == "objection" and all(o.response for o in w.options) for w in windows)


async def test_mock_trial_is_deterministic():
    a = await generate_trial(MockLLM(), CI)
    b = await generate_trial(MockLLM(), CI)
    assert [t.text for t in a["script"].all_turns()] == [t.text for t in b["script"].all_turns()]


async def test_no_repeated_templates_within_trial():
    state = await generate_trial(MockLLM(), CI)
    texts = [t.subtitle for s in state["script"].main_scenes() for t in s.turns]
    assert len(texts) == len(set(texts))


def test_evidence_consistency():
    state_plan = _plan()
    ids = {e.id for e in state_plan.evidence}
    for spec in blueprint("full"):
        for slot in spec.slots:
            if slot.evidence is not None:
                assert "ABC"[slot.evidence] in ids


def test_subtitles_strip_cues_and_emphasis():
    assert subtitle_text("[sigh] I was *going* through [pause] something.") == "I was going through something."


async def test_llm_failure_uses_scripted_fallback():
    from app.llm.providers import OllamaLLM
    from app.config import get_settings

    llm = OllamaLLM(get_settings())
    llm.base = "http://127.0.0.1:1"  # nothing listens here
    llm.timeout = 0.5
    plan = _plan()
    turn, source = await agent_for(plan.character("judge")).speak(llm, _ctx(plan), "x-1")
    assert source == "fallback" and turn.subtitle


def test_tighten_and_intent_checks():
    from app.agents.agents import intent_satisfied, tighten

    long = "One two three. " * 30
    assert len(tighten(long).split()) <= 48
    assert "witness_1" not in tighten("I call witness_1 to the stand.")
    assert intent_satisfied("verdict_guilty", "This court finds you guilty.")
    assert not intent_satisfied("verdict_guilty", "This court finds you not guilty.")
    assert not intent_satisfied("rule_on_objection", "Hmm, interesting point.")
    assert intent_satisfied("testify", "anything goes")
