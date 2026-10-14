"""Explicit courtroom lifecycle. Phases change only through `transition()`, never via an LLM."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.models import Phase

P = Phase

TRANSITIONS: dict[Phase, frozenset[Phase]] = {
    P.CASE_CREATED: frozenset({P.CASE_PREPARATION, P.FAILED}),
    P.CASE_PREPARATION: frozenset({P.SCRIPT_PLANNING, P.FAILED}),
    P.SCRIPT_PLANNING: frozenset({P.SCRIPT_VALIDATION, P.FAILED}),
    P.SCRIPT_VALIDATION: frozenset({P.AUDIO_PREPARATION, P.SCRIPT_PLANNING, P.FAILED}),
    P.AUDIO_PREPARATION: frozenset({P.COURTROOM_READY, P.FAILED}),
    P.COURTROOM_READY: frozenset({P.OPENING_STATEMENTS, P.AUDIO_PREPARATION}),
    P.OPENING_STATEMENTS: frozenset({P.EVIDENCE_PRESENTATION, P.PLAYER_INTERVENTION}),
    P.EVIDENCE_PRESENTATION: frozenset(
        {P.WITNESS_EXAMINATION, P.CLOSING_ARGUMENTS, P.PLAYER_INTERVENTION}
    ),
    P.WITNESS_EXAMINATION: frozenset({P.CROSS_EXAMINATION, P.CLOSING_ARGUMENTS, P.PLAYER_INTERVENTION}),
    P.CROSS_EXAMINATION: frozenset({P.WITNESS_EXAMINATION, P.CLOSING_ARGUMENTS, P.PLAYER_INTERVENTION}),
    # Leaving an intervention returns to a trial phase; the caller supplies which.
    P.PLAYER_INTERVENTION: frozenset(
        {
            P.EVIDENCE_PRESENTATION,
            P.WITNESS_EXAMINATION,
            P.CROSS_EXAMINATION,
            P.CLOSING_ARGUMENTS,
            P.DELIBERATION,
        }
    ),
    P.CLOSING_ARGUMENTS: frozenset({P.DELIBERATION, P.PLAYER_INTERVENTION}),
    P.DELIBERATION: frozenset({P.VERDICT, P.PLAYER_INTERVENTION}),
    P.VERDICT: frozenset({P.CASE_COMPLETED}),
    P.CASE_COMPLETED: frozenset(),
    P.FAILED: frozenset({P.CASE_PREPARATION}),
}

# Which roles must be present before a phase may begin.
REQUIRED_ROLES: dict[Phase, frozenset[str]] = {
    P.OPENING_STATEMENTS: frozenset({"judge", "prosecutor", "defense", "defendant"}),
    P.WITNESS_EXAMINATION: frozenset({"witness"}),
    P.CROSS_EXAMINATION: frozenset({"witness", "defense"}),
    P.VERDICT: frozenset({"judge"}),
}


class IllegalTransition(Exception):
    pass


@dataclass(slots=True)
class TransitionContext:
    roles_present: frozenset[str] = field(default_factory=frozenset)
    evidence_count: int = 0
    phase_complete: bool = True
    window_resolved: bool = True
    verdict_ready: bool = False
    script_valid: bool = False
    audio_ready: bool = False
    window_open: bool = False


def check(current: Phase, target: Phase, ctx: TransitionContext) -> None:
    if target not in TRANSITIONS.get(current, frozenset()):
        raise IllegalTransition(f"{current} → {target} is not a legal courtroom transition")
    if target is P.FAILED:
        return
    missing = REQUIRED_ROLES.get(target, frozenset()) - ctx.roles_present
    if missing:
        raise IllegalTransition(f"{target} requires {sorted(missing)} in the courtroom")
    if target is P.AUDIO_PREPARATION and current is P.SCRIPT_VALIDATION and not ctx.script_valid:
        raise IllegalTransition("Script has not passed validation")
    if target is P.COURTROOM_READY and not ctx.audio_ready:
        raise IllegalTransition("Audio is not prepared")
    if target is P.EVIDENCE_PRESENTATION and current is not P.PLAYER_INTERVENTION and ctx.evidence_count < 1:
        raise IllegalTransition("No evidence has been entered into the record")
    if target is P.PLAYER_INTERVENTION and not ctx.window_open:
        raise IllegalTransition("The court is not accepting interventions right now")
    if current is P.PLAYER_INTERVENTION and not ctx.window_resolved:
        raise IllegalTransition("The pending intervention has not been resolved")
    if current in _TRIAL and target is not P.PLAYER_INTERVENTION and not ctx.phase_complete:
        raise IllegalTransition(f"{current} still has unfinished business")
    if target is P.VERDICT and not ctx.verdict_ready:
        raise IllegalTransition("The verdict has not been reached")


def transition(current: Phase | str, target: Phase | str, ctx: TransitionContext) -> Phase:
    cur, tgt = Phase(current), Phase(target)
    check(cur, tgt, ctx)
    return tgt


_TRIAL = frozenset(
    {
        P.OPENING_STATEMENTS,
        P.EVIDENCE_PRESENTATION,
        P.WITNESS_EXAMINATION,
        P.CROSS_EXAMINATION,
        P.CLOSING_ARGUMENTS,
        P.DELIBERATION,
    }
)
