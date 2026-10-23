"""Update backend/.env without printing secret values."""

from pathlib import Path

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def upsert_env(updates: dict[str, str], path: Path | None = None) -> None:
    target = path or ENV_PATH
    lines = target.read_text(encoding="utf-8").splitlines() if target.exists() else []
    seen: set[str] = set()
    rewritten: list[str] = []
    for line in lines:
        if not line or line.lstrip().startswith("#") or "=" not in line:
            rewritten.append(line)
            continue
        key = line.split("=", 1)[0]
        if key in updates:
            rewritten.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            rewritten.append(line)
    for key, value in updates.items():
        if key not in seen:
            rewritten.append(f"{key}={value}")
    target.write_text("\n".join(rewritten) + "\n", encoding="utf-8")
