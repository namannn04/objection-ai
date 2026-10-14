# Fish Audio — verified API notes

Source: `fishaudio/docs` repo (commit `c7aeab2`, 2026-10-13), its `api-reference/openapi.json`,
the live pricing page, and the Drama 3 launch blog. Verified 2026-10-14. Nothing below was learned
by calling a paid endpoint.

## Endpoint
`POST https://api.fish.audio/v1/tts`
- `Authorization: Bearer <key>`
- `model: drama-3 | s2.1-pro-free | s2.1-pro | s2-pro | s1`
  **Unknown/missing values silently fall back to (paid) `s2.1-pro`.** The adapter hard-codes the
  exact strings and refuses anything else.
- `Content-Type: application/json` (msgpack only needed for inline reference audio)
- Body: `text` (required), `reference_id` (str | str[] for multi-speaker), `format`
  (`wav|pcm|mp3|opus`, default mp3), `mp3_bitrate` (64|128|192), `sample_rate`, `latency`
  (`low|normal|balanced`), `normalize`, `prosody {speed 0.5–2, volume dB, normalize_loudness}`,
  `temperature`, `top_p`, `chunk_length` (100–300), `max_new_tokens`, ...
- Response: 200, raw audio bytes (chunked).
- Errors: `{message, status}`. 400/401/402/403/404 → never retry. 429/503/5xx → backoff
  (but see "uncertain results" policy in `app/audio/budget.py`).

## Drama 3 script syntax
- Multi-speaker: `reference_id: ["voiceA","voiceB"]`, each turn starts `<|speaker:0|>`, `<|speaker:1|>`…
- Performance direction: free-form `[barely holding it together, forcing a smile]` before the words.
- Sounds/pauses: free-form brackets at the moment they occur: `[small laugh]`, `[shaky breath]`.
- Paired word-level tags (official list): `<whisper> <emphasis> <soft> <fast> <slow> <stress> <forceful>`.
- No documented max characters / max speakers → we keep scenes short (≤ ~900 chars, ≤ 4 speakers).

## Pricing (application estimates use the conservative figure)
| model | price |
|---|---|
| `drama-3` | $50 / M characters list; launch promo $10 / M chars until 2026-11-12 (blog only) |
| `s2.1-pro`, `s2-pro`, `s1` | $15 / M UTF-8 bytes |
| `s2.1-pro-free` | $0 (fair use, "through Nov 30 2026" — end date inconsistent in sources) |

Concurrency: 5 concurrent requests under $100 prepaid; 429 has no `Retry-After`.

## Balance
`GET /wallet/self/api-credit` → `{credit: string, ...}`. The only verified balance source.
No per-request usage endpoint exists, so per-request cost is an application estimate.

## Voices (public, from the Drama 3 docs)
- Adrian (EN-US male) `bf322df2096a46f18c579d0baa36f41d`
- Delia (EN-US female) `c70cfb98867a4bfb9ae20d2401257b92`
- Sheila (EN-US female) `f3a2b90078d54a65af4b95f63bc7798e`
- S2 example voice `9a9cf47702da476aa4629e2506d4a857`

Further voices: `GET /model?page_size=..&language=en&sort_by=score` (free metadata call).

## Unverified / not relied upon
- Character counting rule for Drama 3 billing (we count Unicode code points of the full request text,
  including tags — an over-estimate on purpose).
- Whether `/v1/tts/stream/with-timestamp` alignment supports `drama-3`.
