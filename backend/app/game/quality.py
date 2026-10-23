"""Deterministic commit-quality weights. See docs/02-GAME-DESIGN.md."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Quality:
    weight: float
    signals: tuple[str, ...]
    source: str
    note: str = ""


_LOW_MESSAGES = {"wip", "update", "fix", "misc", ".", "commit"}
_SIGNAL_WORDS = {
    "test": ("test", "spec"),
    "docs": ("doc", "docs", "readme"),
    "fix": ("fix", "bug"),
    "maintenance": ("refactor", "clean"),
}


def score_message(message: str) -> Quality:
    text = " ".join(message.lower().split())
    if text in _LOW_MESSAGES:
        return Quality(0.45, (), "rules")
    signals: list[str] = []
    for signal, words in _SIGNAL_WORDS.items():
        if any(re.search(rf"\b{re.escape(word)}\b", text) for word in words):
            signals.append(signal)
    if len(text) < 4:
        weight = 0.35
    elif signals:
        weight = 0.85
    else:
        weight = 0.7
    return Quality(weight, tuple(signals), "rules")
