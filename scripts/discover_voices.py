"""List Fish Audio public voices (a free metadata GET) and suggest a voices.json.

    python scripts/discover_voices.py --language en --limit 30

Never synthesizes anything. Requires FISH_AUDIO_API_KEY in the environment or .env.
Write your chosen mapping to backend/voices.json, e.g.:
    {"judge": "<id>", "witness_1": "<id>", "defendant": "<id>"}
"""

import argparse
import json
import os
import sys
from pathlib import Path

import httpx


def key() -> str:
    k = os.environ.get("FISH_AUDIO_API_KEY", "")
    env = Path(__file__).resolve().parents[1] / ".env"
    if not k and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("FISH_AUDIO_API_KEY="):
                k = line.split("=", 1)[1].strip()
    if not k:
        sys.exit("FISH_AUDIO_API_KEY is not set")
    return k


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--language", default="en")
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--query", default="")
    a = ap.parse_args()
    params = {"page_size": min(a.limit, 100), "language": a.language, "sort_by": "score"}
    if a.query:
        params["title"] = a.query
    r = httpx.get("https://api.fish.audio/model", params=params, headers={"Authorization": f"Bearer {key()}"}, timeout=20)
    r.raise_for_status()
    items = r.json().get("items", [])
    for m in items:
        tags = ", ".join(m.get("tags", [])[:5])
        print(f"{m.get('_id')}  {m.get('title', '')[:40]:40}  {tags}")
    print(json.dumps({"hint": "copy ids into backend/voices.json keyed by character key"}, indent=2))


if __name__ == "__main__":
    main()
