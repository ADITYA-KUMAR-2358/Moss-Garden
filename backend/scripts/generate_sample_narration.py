"""Generate the landing page's sample journal narration with ElevenLabs.

Run from backend/ after ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID are set:

    python -m scripts.generate_sample_narration
    python -m scripts.generate_sample_narration --force

The file is committed under frontend/public/audio/, so visitors never trigger
a request. SAMPLE must stay word for word with SAMPLE_JOURNAL in
frontend/src/components/Marketing.jsx, because the text on the page is the
transcript.
"""

import argparse
import sys
from pathlib import Path

from app.config import get_settings
from app.integrations.elevenlabs import ElevenLabsError, narrate

TARGET = Path(__file__).resolve().parents[2] / "frontend" / "public" / "audio" / "journal-sample.mp3"
SAMPLE = " ".join(
    [
        "The week the moss settled.",
        "Three quiet days, then a long Thursday in garden-api. Most of the work was small: "
        "a retry for a flaky request, a clearer error message, one test that had been skipped for months.",
        "The moss cushion by the stones filled in at its edges. Near the front, a lantern bud appeared, "
        "the first sign of late autumn. It will open when it is ready.",
    ]
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true", help="Replace the existing file")
    args = parser.parse_args()
    settings = get_settings()
    if not settings.elevenlabs_api_key or not settings.elevenlabs_voice_id:
        print("Set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in backend/.env first.")
        return 1
    if TARGET.exists() and not args.force:
        print(f"{TARGET.name} already exists. Use --force to replace it.")
        return 0
    try:
        audio = narrate(settings.elevenlabs_api_key, settings.elevenlabs_voice_id, SAMPLE, settings.elevenlabs_model_id)
    except ElevenLabsError as error:
        print(f"Narration failed: {error}")
        return 1
    TARGET.write_bytes(audio)
    print(f"Wrote {TARGET} ({len(audio)} bytes, {len(SAMPLE)} characters, model {settings.elevenlabs_model_id}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
