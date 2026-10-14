# Architecture

A modular monolith: one FastAPI app, one background worker (in-process by default), PostgreSQL as the
source of truth, Redis for live events, the local filesystem for media.

```
 Next.js (3000) ──REST/SSE──▶ FastAPI (8000) ──▶ PostgreSQL (cases, scripts, sessions, assets, audit)
      │                          │  ▲
      │  Web Audio playback      │  └── Redis pub/sub (live prep + job events; in-memory fallback)
      └── /media/* (MP3) ◀───────┤
                                 └──▶ Worker: LangGraph agents → validator → audio service → FFmpeg
                                              │                     │
                                       LLM provider          Audio provider (mock | fish-free | drama3)
                                    (mock|ollama|anthropic)       └── BudgetGuard + content cache
```

## Lifecycle

`CASE_CREATED → CASE_PREPARATION → SCRIPT_PLANNING → SCRIPT_VALIDATION → AUDIO_PREPARATION → COURTROOM_READY`
then per session: `OPENING_STATEMENTS → EVIDENCE_PRESENTATION → WITNESS_EXAMINATION ⇄ CROSS_EXAMINATION →
CLOSING_ARGUMENTS → DELIBERATION → VERDICT → CASE_COMPLETED`, with `PLAYER_INTERVENTION` entered only through an open
window. Transitions are checked against required roles, evidence, validity, audio readiness, window state and verdict
readiness (`app/domain/state_machine.py`).

## Hybrid generation (why playback never stalls)

* The whole trial — main scenes, both verdict branches, and every pre-written intervention response — is generated,
  validated and voiced before the courtroom opens.
* The player preloads every clip, so choices and verdicts play instantly.
* Only chaos-mode free text is generated live; the trial waits at a safe point (end of scene) while it runs.
* If live generation fails, a scripted response is used and labelled as such.

## Data model (22 tables)

profiles, app_settings, cases, case_versions (immutable plan+script snapshots), agent_configurations, characters,
voice_assignments, evidence_items, scenes, dialogue_turns (main / option branch / session-only live branch),
witness_statements, courtroom_sessions (replays & alternate verdicts are new sessions), user_interventions, objections,
jury_votes, verdicts, audio_assets (content-addressed), audio_generation_jobs, usage_records (audit), podcast_episodes,
highlights.

## Verdict

Deterministic from the record: argument points scored by the director's rules, half of each exhibit's strength, the
plan's leaning (+1), the jury's intervention effects, and votes (the final vote weighs 6). Ties follow the plan's
leaning. The 11 simulated jurors lean with the record; the user is the 12th.

## Audio timing

Durations are measured with ffprobe (or a full ffmpeg decode) — never estimated from text. Word timings are exact for
mock audio and distributed across the measured duration (by syllable weight) for provider audio, marked
`timing_source: estimated`. The browser compiles each scene into a sample-accurate timeline with the same SFX lead/tail
rules the podcast mixer uses.
