import pytest

from app.domain.models import Phase
from app.domain.state_machine import IllegalTransition, TransitionContext, transition

ALL = frozenset({"judge", "prosecutor", "defense", "defendant", "witness"})


def ctx(**kw):
    return TransitionContext(roles_present=ALL, evidence_count=3, **kw)


def test_happy_path_preparation():
    p = Phase.CASE_CREATED
    for target, kw in [
        (Phase.CASE_PREPARATION, {}), (Phase.SCRIPT_PLANNING, {}), (Phase.SCRIPT_VALIDATION, {}),
        (Phase.AUDIO_PREPARATION, {"script_valid": True}), (Phase.COURTROOM_READY, {"audio_ready": True}),
        (Phase.OPENING_STATEMENTS, {}),
    ]:
        p = transition(p, target, ctx(**kw))
    assert p is Phase.OPENING_STATEMENTS


def test_cannot_skip_validation():
    with pytest.raises(IllegalTransition):
        transition(Phase.SCRIPT_PLANNING, Phase.AUDIO_PREPARATION, ctx())


def test_invalid_script_blocks_audio():
    with pytest.raises(IllegalTransition, match="validation"):
        transition(Phase.SCRIPT_VALIDATION, Phase.AUDIO_PREPARATION, ctx(script_valid=False))


def test_courtroom_requires_audio():
    with pytest.raises(IllegalTransition, match="Audio"):
        transition(Phase.AUDIO_PREPARATION, Phase.COURTROOM_READY, ctx(audio_ready=False))


def test_opening_requires_core_cast():
    with pytest.raises(IllegalTransition, match="requires"):
        transition(Phase.COURTROOM_READY, Phase.OPENING_STATEMENTS, TransitionContext(roles_present=frozenset({"judge"})))


def test_intervention_needs_open_window():
    with pytest.raises(IllegalTransition, match="interventions"):
        transition(Phase.OPENING_STATEMENTS, Phase.PLAYER_INTERVENTION, ctx(window_open=False))
    assert transition(Phase.OPENING_STATEMENTS, Phase.PLAYER_INTERVENTION, ctx(window_open=True)) is Phase.PLAYER_INTERVENTION


def test_unresolved_window_blocks_resume():
    with pytest.raises(IllegalTransition, match="resolved"):
        transition(Phase.PLAYER_INTERVENTION, Phase.EVIDENCE_PRESENTATION, ctx(window_resolved=False))


def test_verdict_requires_decision():
    with pytest.raises(IllegalTransition, match="verdict"):
        transition(Phase.DELIBERATION, Phase.VERDICT, ctx(verdict_ready=False))
    assert transition(Phase.DELIBERATION, Phase.VERDICT, ctx(verdict_ready=True)) is Phase.VERDICT


def test_completed_is_terminal():
    for target in Phase:
        with pytest.raises(IllegalTransition):
            transition(Phase.CASE_COMPLETED, target, ctx())
