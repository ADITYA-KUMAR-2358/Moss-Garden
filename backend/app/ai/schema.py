"""Commit-score schema. Model text is untrusted until it passes these checks."""

import re

from app.game.quality import Quality

_SIGNALS = {"maintenance", "test", "docs", "fix", "feature", "uncertain"}


def parse_quality_payload(data: object) -> Quality | None:
    if not isinstance(data, dict):
        return None
    weight = data.get("quality")
    if isinstance(weight, bool) or not isinstance(weight, (int, float)):
        return None
    if weight < 0 or weight > 1:
        return None
    signals = data.get("signals", [])
    if not isinstance(signals, list) or len(signals) > 6:
        return None
    clean: list[str] = []
    for signal in signals:
        if not isinstance(signal, str) or signal not in _SIGNALS:
            return None
        clean.append(signal)
    note = data.get("note", "")
    if not isinstance(note, str) or len(note) > 180:
        return None
    return Quality(float(weight), tuple(clean), "model", note)


_JOURNAL_BANNED = ("streak", "<", ">", "http://", "https://", "```")
_DASH = re.compile(r"\s*[\u2013\u2014]\s*")


def parse_journal_payload(data: object) -> str | None:
    if not isinstance(data, dict):
        return None
    body = data.get("body")
    if not isinstance(body, str):
        return None
    body = " ".join(_DASH.sub(", ", body).split())
    if len(body) < 20 or len(body) > 700:
        return None
    lowered = body.lower()
    if any(mark in lowered for mark in _JOURNAL_BANNED):
        return None
    return body


def parse_name_payload(data: object) -> tuple[str, str] | None:
    if not isinstance(data, dict):
        return None
    name = data.get("name")
    description = data.get("description")
    if not isinstance(name, str) or not isinstance(description, str):
        return None
    name = " ".join(name.split())
    description = " ".join(description.split())
    if not name or len(name) > 40 or len(description) > 140:
        return None
    if any(mark in name or mark in description for mark in ("<", ">", "/", "\\")):
        return None
    return name, description
