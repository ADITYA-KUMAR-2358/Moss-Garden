"""Generate static garden sound effects with ElevenLabs.

Run from backend/ after ELEVENLABS_API_KEY is set:

    python scripts/generate_sfx.py
    python scripts/generate_sfx.py --force
    python scripts/generate_sfx.py --only sprout.mp3,level-up.mp3 --variants 3

Ordinary page views do not call this. Files that already exist are skipped
unless --force is set. Variants are written beside the chosen file so a
person can pick one by ear. This script does not estimate a dollar cost.

Checked against the sound-generation reference on 2026-10-22:
POST /v1/sound-generation
body text, duration_seconds (0.5 to 30), prompt_influence (0 to 1), loop
query output_format=mp3_44100_128
model_id eleven_text_to_sound_v2
https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert
"""

import argparse
import json
import os
import sys
from pathlib import Path

from app.integrations.elevenlabs import ElevenLabsError, generate_sound, subscription_character_count

ROOT = Path(__file__).resolve().parents[2] / "frontend" / "public" / "audio"
PROMPTS = Path(__file__).with_name("sfx_prompts.json")


def load_cues() -> list[dict]:
    return json.loads(PROMPTS.read_text(encoding="utf-8"))


def _print_usage(api_key: str, label: str) -> int | None:
    try:
        count = subscription_character_count(api_key)
    except ElevenLabsError as error:
        print(f"{label}: account counter unavailable ({error})")
        return None
    if count is None:
        print(f"{label}: subscription.character_count was not an integer")
        return None
    print(f"{label}: subscription.character_count={count}")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Moss Garden sound effects")
    parser.add_argument("--force", action="store_true", help="Replace files that already exist")
    parser.add_argument("--variants", type=int, default=1, help="Write extra takes as name-vN.mp3")
    parser.add_argument("--only", default="", help="Comma-separated filenames to generate")
    args = parser.parse_args()
    if args.variants < 1:
        print("--variants must be at least 1")
        sys.exit(2)
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        print("ELEVENLABS_API_KEY is unset. No sound files were generated.")
        return
    chosen = {item.strip() for item in args.only.split(",") if item.strip()}
    cues = [cue for cue in load_cues() if not chosen or cue["file"] in chosen]
    ROOT.mkdir(parents=True, exist_ok=True)
    before = _print_usage(api_key, "before")
    for cue in cues:
        target = ROOT / cue["file"]
        takes = args.variants if args.variants > 1 else 1
        for index in range(takes):
            path = target if takes == 1 else target.with_name(f"{target.stem}-v{index + 1}{target.suffix}")
            if path.exists() and not args.force:
                print(f"skip {path.name}")
                continue
            audio = generate_sound(
                api_key,
                cue["text"],
                duration_seconds=float(cue["duration_seconds"]),
                loop=bool(cue["loop"]),
                prompt_influence=float(cue["prompt_influence"]),
            )
            path.write_bytes(audio)
            print(f"wrote {path.name} ({len(audio)} bytes)")
    after = _print_usage(api_key, "after")
    if before is not None and after is not None:
        print(f"subscription.character_count change: {after - before}")


if __name__ == "__main__":
    main()
