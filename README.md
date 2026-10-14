# Objection AI: The Court of Absolute Nonsense

> **Order in the court. Absolutely none in the arguments.**

You put literally anything on trial: your alarm clock, JavaScript, Monday mornings. A cast of AI agents then argues the case with a straight face:

- a judge who has had enough;
- a prosecutor who treats tiny inconveniences as crimes against humanity;
- a smooth defense attorney;
- the defendant;
- witnesses who crack under cross-examination.

You watch, object, question the witness and vote, and the verdict follows the record. Every line is performed, and the showcase target is **Fish Audio Drama 3**. Each finished trial can be exported as a podcast.

Built as a hackathon showcase for Fish Audio Drama 3, it is designed to run entirely on localhost and to protect a small credit budget.

---

## Quick start (mock mode, no API keys, $0)

Requirements: Docker, Python 3.12+, Node 20.9+.

```bash
make setup     # venv + npm + playwright chromium + .env from .env.example
make dev       # Postgres/Redis in Docker → migrations → seed → API :8000 + web :3000
```

Open **http://localhost:3000** and click **Watch a ridiculous case**.

The showcase, *The People vs. JavaScript*, is fully cached. It plays with zero generation and no network.

Everything runs in **mock mode** by default:

- The **audio** is a local procedural "voice-blip" synthesizer, in the Ace Attorney tradition. It gives every character a stable pitch and timbre, emotion-driven prosody, synthesized laughs, gasps and pauses, and exact word timings.
- The **writing** comes from a deterministic offline comedy engine.

Neither touches the network.

Running everything in Docker instead:

```bash
docker compose up --build    # web :3000, API :8000, worker, Postgres :5434, Redis :6381
```

## What's inside

| | |
|---|---|
| **Frontend** | Next.js 16 (App Router), TypeScript, Tailwind v4, Motion, Zustand, TanStack Query, React Hook Form + Zod, Wavesurfer.js, Lucide |
| **Backend** | FastAPI, Pydantic, LangGraph, SQLAlchemy 2 + Alembic, PostgreSQL, Redis (pub/sub + coordination), FFmpeg |
| **Jobs** | DB-backed queue (`SELECT … FOR UPDATE SKIP LOCKED`), in-process or `python -m app.worker` |
| **LLM** | `mock` (offline) · `ollama` (local) · `anthropic` (Claude), all with structured outputs and scripted fallback |
| **Audio** | `mock` (local) · `fish-free` (S2.1 Pro Free, after verification) · `drama3` (paid, opt-in) |

For design notes, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). The verified API facts are in [docs/FISH_AUDIO_NOTES.md](docs/FISH_AUDIO_NOTES.md).

## The experience

1. **File a case** at `/file`. It's three short steps: the accused, the crime, then intensity, drama meter, length and your role.
2. **Case preparation.** The agents plan and write the trial live. The *rehearsal room* streams each line as its character writes it, over SSE. The rotating jokes run only while a job is actually running.
3. **The courtroom.** Lines play gaplessly. The speaker is spotlit, the subtitles are word-synced, characters react, and exhibits fly in. The surprise witness and the plot twist each get their moment.
4. **The jury speaks.** There are controlled windows for an opening vote, an objection (the **OBJECTION!** button), a question to the witness, and the final vote. All responses are pre-generated, so choices play instantly. In **chaos mode** you can type your own intervention, which the agents answer live.
5. **The verdict** is computed from the record (argument points, evidence strength and your input) and then performed: the stamp, the sentence, highlights, the jury tally, sharing and a replay with a different verdict.
6. **Podcast mode** (`/podcast/<case>`) gives you the whole trial mixed into MP3/WAV, with chapters, a following transcript, speed control and an episode history.

## Multi-agent architecture

The agents are genuinely separate, not one prompt with name tags:

- **Narrative Director:** casts the case, plans the arc and comedic beats, and briefs each scene with what every line must accomplish.
- **Judge, Prosecutor, Defense, Defendant, Witnesses, Reporter:** each has its own persona, objective, bias, *private knowledge* and allowed line kinds.
  - Only the defense knows the plot twist and the sealed exhibit.
  - Each witness knows the embarrassing truth they'll eventually admit.
- **Humor evaluator:** scores every scene on a rubric (originality, relevance, character consistency, timing, freshness, coherence, escalation, punchline) by blending a heuristic with an LLM critic. A weak scene is regenerated alone. *These are editorial heuristics, not laugh predictions.*
- **LangGraph orchestration:** `plan → strategize → [brief → perform → evaluate → retry|accept]* → windows → validate`.

**The LLM never changes the trial phase.** An explicit state machine (`app/domain/state_machine.py`) validates every transition, covering the 15 lifecycle states. During a trial the server is authoritative. The client plays prepared audio and reports when a scene finishes. The server checks the order, opens windows, records votes and reaches the verdict.

Model output passes through guards:

- lines are kept to short beats;
- internal labels never leak;
- verdict and ruling lines must actually state the ruling.

If a guard fails, or the LLM is down, that one line falls back to the scripted engine and is labelled `fallback` in diagnostics.

## Fish Audio Drama 3 and credit protection

Drama 3 is the performance target. The compiler (`app/audio/compiler.py`) turns structured direction into verified Drama 3 syntax:

```
[deadpan; flat and glacial after a long blink] The defendant will pick a type and commit to it.
<|speaker:0|>[smug; silky menace] To <emphasis>what</emphasis>?
```

Every character has a stable voice and a base direction. Each line carries an emotion, a delivery note, an intensity, comic timing pauses and sound cues (`[sighs]`, `[small laugh]`, `[long pause]`).

### Spending is off by default and needs four separate opt-ins

1. `AUDIO_PROVIDER=drama3`
2. `ENABLE_PAID_TTS=true`
3. `FISH_AUDIO_API_KEY=…`
4. **Per-case authorization in the UI.** You review the exact estimate (lines, characters, cost at the conservative $50 per 1M characters list price, limits and verified balance) and type `SPEND CREDITS`.

### The BudgetGuard (`app/audio/budget.py`)

It enforces the following, all as application-level limits:

- a per-case character cap (`DRAMA3_MAX_CHARACTERS_PER_CASE`);
- a projected-spend ceiling (`DRAMA3_MAX_PROJECTED_SPEND_USD`);
- a demo reserve (`DRAMA3_DEMO_RESERVE_USD`);
- duplicate detection;
- in-flight locks.

A whole batch is checked *before* the first request. One block stops the batch, so there is no partial surprise spending.

Retries happen only for requests that provably never billed: a connection error, 429 or 503. A timeout or an ambiguous response is recorded as `uncertain` and is never retried automatically.

Every attempt lands in the audit log at `/settings`, including cache hits and blocks.

### Caching

Audio is cached by content: provider, model, voices, compiled text and settings. An unchanged line is never paid for twice.

### Model header

The model header is hard-coded to the two verified values, `drama-3` and `s2.1-pro-free`. The Fish API silently bills unknown values as `s2.1-pro`, so the adapter refuses anything else.

### Free tier

`fish-free` (S2.1 Pro Free) is selectable only after `POST /api/usage/verify-free`. That call checks the balance, makes one tiny free call, checks the balance again, and enables the tier only if the credit is unchanged.

### Balance

The only verified balance is `GET /wallet/self/api-credit`, via **Refresh verified balance** in Settings. All other spend figures are estimates.

### Optional scene strategy

With `DRAMA3_SCENE_STRATEGY=true`, a scene is synthesized as a single multi-speaker request for more natural back-and-forth. It is then split into per-line clips at the longest silences, with a proportional fallback that never re-bills. The default is line-by-line, which keeps timing and editing precise.

### Picking voices

```bash
python scripts/discover_voices.py --language en --limit 30   # free metadata GET, no synthesis
# then map character keys → voice ids in backend/voices.json
```

Only authorized public or preset voices are used. No real person is cloned.

## Running a live Drama 3 demo safely

1. Seed the showcase (`make seed`). It is fully playable at $0 with mock audio.
2. In `.env`, set `AUDIO_PROVIDER=drama3`, `ENABLE_PAID_TTS=true` and your `FISH_AUDIO_API_KEY`, then restart the backend.
3. In Settings, click **Refresh verified balance**.
4. File a new **quick** case. Review the plan and the estimate, type `SPEND CREDITS`, and play it.
5. If anything fails, the cached showcase still runs, and the UI always labels which provider recorded what.

Cached audio is never presented as newly generated. The case hub, the side panel and the manifest all name the provider for every line.

## Tests

```bash
make test   # 49 backend tests: SQLite, mock LLM + mock audio, zero network, zero paid calls
make e2e    # Playwright: landing → showcase verdicts + replay → file a new case → verdict (needs `make dev`)
make lint   # eslint + tsc
```

The backend tests cover:

- the state machine and agent role separation;
- structured generation, determinism and evidence consistency;
- budget enforcement and Fish error classification (402/401/429/503 and timeouts);
- the exact model header, audio caching and manifest ordering;
- exact mock timings and scene splitting;
- jury votes deciding verdicts, replays, chaos interventions and podcast export.

## Configuration

See [`.env.example`](.env.example). The most useful settings:

| Variable | Default | |
|---|---|---|
| `LLM_PROVIDER` | `mock` | `ollama` uses `OLLAMA_MODEL` (e.g. `llama3.2`); `anthropic` needs `ANTHROPIC_API_KEY` |
| `AUDIO_PROVIDER` | `mock` | `fish-free` / `drama3` (see above) |
| `RUN_WORKER_IN_PROCESS` | `true` | set `false` and run `make worker` for a separate worker |
| `DATABASE_URL` / `REDIS_URL` | ports 5434 / 6381 | Redis is optional locally (an in-memory event bus is the fallback) |

You can also switch the defaults for new cases at runtime in **Settings**.

## Troubleshooting

- **"The courthouse is unreachable."** The API isn't running on `:8000`. Run `make backend` and check `NEXT_PUBLIC_API_URL`.
- **Port already in use.** Compose maps Postgres to 5434 and Redis to 6381 to avoid clashing with local installs.
- **No sound.** Browsers need a click before audio. That is what the **All rise** button is for. Check the volume control in the courtroom too.
- **A case is stuck on "Recording voices".** The job may have failed or been blocked. The case page shows the reason, and you can switch to free mock voices from there.
- **The Ollama trial is slow.** Small local models take a few minutes for a full trial. Pick a *quick* hearing, and watch the rehearsal room stream it.
- **FFmpeg.** The backend uses a system `ffmpeg`/`ffprobe` if installed, and otherwise falls back to the binary bundled with `imageio-ffmpeg`.

## Project layout

```
backend/app/
  agents/        director, role agents, blueprint, humor evaluator, LangGraph graph, offline comedy engine
  audio/         compiler, providers (mock/Fish), budget guard, mock synth, ffmpeg, scene split, voices
  domain/        Pydantic domain models, state machine, script validation
  services/      case, pipeline, sessions/verdicts, interventions, audio generation, manifest, podcast, jobs, events
  showcase/      hand-authored "The People vs. JavaScript"
  api/routes/    cases, sessions, podcasts, system (settings/usage/jobs)
frontend/src/
  app/           /, /file, /case/[ref], /case/[ref]/court, /podcast/[ref], /docket, /settings
  components/    characters (SVG art), court (stage, player, HUD, verdict), case, landing, podcast, settings
  lib/           API client, types, Web Audio engine
```

All cases, evidence and testimony are fictional. No Wi-Fi was harmed.
