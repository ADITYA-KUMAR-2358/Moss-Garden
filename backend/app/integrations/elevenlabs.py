"""ElevenLabs speech and sound effects.

Sound generation: POST /v1/sound-generation
Narration: POST /v1/text-to-speech/{voice_id}, model eleven_v4 by default
https://elevenlabs.io/docs/overview/models
https://elevenlabs.io/docs/api-reference/text-to-sound-effects/convert
https://elevenlabs.io/docs/api-reference/text-to-speech/convert
"""

import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_API = "https://api.elevenlabs.io"
_VOICE = re.compile(r"^[A-Za-z0-9]{8,40}$")


class ElevenLabsError(Exception):
    pass


def _post(path: str, api_key: str, body: dict) -> bytes:
    request = Request(
        f"{_API}{path}",
        data=json.dumps(body).encode(),
        method="POST",
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
    )
    try:
        with urlopen(request, timeout=60) as response:
            return response.read()
    except (HTTPError, URLError) as error:
        raise ElevenLabsError("ElevenLabs request failed") from error


def generate_sound(
    api_key: str,
    prompt: str,
    duration_seconds: float = 1.5,
    *,
    loop: bool = False,
    prompt_influence: float = 0.3,
) -> bytes:
    if duration_seconds < 0.5 or duration_seconds > 30:
        raise ElevenLabsError("Sound duration must be between 0.5 and 30 seconds")
    if prompt_influence < 0 or prompt_influence > 1:
        raise ElevenLabsError("prompt_influence must be between 0 and 1")
    return _post(
        "/v1/sound-generation?output_format=mp3_44100_128",
        api_key,
        {
            "text": prompt,
            "duration_seconds": duration_seconds,
            "prompt_influence": prompt_influence,
            "loop": loop,
            "model_id": "eleven_text_to_sound_v2",
        },
    )


FALLBACK_MODEL = "eleven_multilingual_v2"
_MODEL = re.compile(r"^[a-z0-9_]{3,40}$")


def narrate(api_key: str, voice_id: str, text: str, model_id: str = "eleven_v4") -> bytes:
    """Calm narration. Falls back to Multilingual v2 when the account cannot use the preferred model."""
    if not _VOICE.fullmatch(voice_id):
        raise ElevenLabsError("ELEVENLABS_VOICE_ID is missing or not a voice id")
    if not _MODEL.fullmatch(model_id):
        raise ElevenLabsError("ELEVENLABS_MODEL_ID is not a model id")
    cleaned = " ".join(text.split())
    if not cleaned:
        raise ElevenLabsError("Narration text is empty")
    models = [model_id] if model_id == FALLBACK_MODEL else [model_id, FALLBACK_MODEL]
    for index, model in enumerate(models):
        try:
            return _post(
                f"/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128",
                api_key,
                {
                    "text": cleaned[:1500],
                    "model_id": model,
                    # v4 reads only stability and similarity; older models also accept speaker boost.
                    "voice_settings": {"stability": 0.6, "similarity_boost": 0.75},
                },
            )
        except ElevenLabsError:
            if index == len(models) - 1:
                raise
    raise ElevenLabsError("ElevenLabs request failed")


def subscription_character_count(api_key: str) -> int | None:
    """Read the account subscription counter when the payload includes it.

    TODO(verify): GET /v1/user/subscription on the current account docs.
    The generator prints character_count only when that field is an integer.
    It does not turn the number into a price.
    """
    request = Request(
        f"{_API}/v1/user/subscription",
        headers={"xi-api-key": api_key, "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode())
    except (HTTPError, URLError, json.JSONDecodeError) as error:
        raise ElevenLabsError("ElevenLabs account lookup failed") from error
    if not isinstance(payload, dict):
        return None
    count = payload.get("character_count")
    nested = payload.get("subscription")
    if count is None and isinstance(nested, dict):
        count = nested.get("character_count")
    return count if isinstance(count, int) else None
