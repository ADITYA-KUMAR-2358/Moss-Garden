"""Commit-score schema. Model text is untrusted until it passes these checks."""

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
