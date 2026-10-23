"""Backboard chat calls.

The documented message route is POST /threads/messages with header X-API-Key.
Provider and model are always sent. The API uses a closed default model when
they are omitted, so this client refuses to call without both values.
TODO(verify): confirm the Gemma 4 provider string and model name against
GET /models on the account that will run the app.
"""

import json
from collections.abc import Callable
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from app.ai.budget import reserve_request
from app.config import Settings
from app.models import AiCache

Transport = Callable[[str, dict, dict], tuple[int, dict]]


def _default_transport(url: str, headers: dict, body: dict) -> tuple[int, dict]:
    request = Request(
        url,
        data=json.dumps(body).encode(),
        method="POST",
        headers=headers,
    )
    try:
        with urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode())
    except HTTPError as error:
        detail = error.read().decode(errors="replace")[:300]
        return error.code, {"error": detail}
    except URLError as error:
        return 0, {"error": str(error.reason)}


class BackboardLLMClient:
    def __init__(self, settings: Settings, session: Session, today, transport: Transport | None = None):
        self.settings = settings
        self.session = session
        self.today = today
        self.transport = transport or _default_transport
        self.calls = 0

    def complete_json(self, *, cache_key: str, prompt: str) -> dict | None:
        settings = self.settings
        if not settings.ai_enabled:
            return None
        if not settings.backboard_api_key or not settings.backboard_llm_provider or not settings.backboard_model_name:
            return None
        cached = self.session.get(AiCache, cache_key)
        if cached is not None:
            try:
                return json.loads(cached.payload)
            except json.JSONDecodeError:
                return None
        if not reserve_request(self.session, self.today, settings.ai_daily_request_budget):
            return None
        self.calls += 1
        url = settings.backboard_base_url.rstrip("/") + "/threads/messages"
        status, payload = self.transport(
            url,
            {
                "X-API-Key": settings.backboard_api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            {
                "content": prompt,
                "llm_provider": settings.backboard_llm_provider,
                "model_name": settings.backboard_model_name,
                "json_output": True,
                "memory": "off",
                "stream": False,
            },
        )
        if status != 200 or not isinstance(payload, dict):
            return None
        parsed = _content_json(payload.get("content"))
        if parsed is None:
            return None
        self.session.add(
            AiCache(
                cache_key=cache_key,
                payload=json.dumps(parsed),
                created_at=datetime.now(timezone.utc),
            )
        )
        return parsed


def _content_json(content: object) -> dict | None:
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        return None
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None
