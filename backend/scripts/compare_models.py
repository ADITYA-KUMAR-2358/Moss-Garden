"""Offline model comparison. Not imported by the web app or the nightly job.

Run it by hand. It calls Backboard only when --run-models is passed and
BACKBOARD_API_KEY is set. Agreement with the labels is not proof that one
model is better.
"""

import argparse
import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen

from app.ai.schema import parse_quality_payload
from app.game.quality import score_message

DATASET = Path(__file__).with_name("eval_commits.json")


def load_rows() -> list[dict]:
    return json.loads(DATASET.read_text(encoding="utf-8"))


def rules_report(rows: list[dict]) -> dict:
    matched = 0
    for row in rows:
        scored = score_message(row["message"])
        high = scored.weight >= 0.8
        if high == row["expect_high"]:
            matched += 1
    return {
        "runner": "rules",
        "rows": len(rows),
        "label_matches": matched,
        "note": "A match count is not a claim that this scorer is better than another model.",
    }


def run_models(rows: list[dict]) -> list[dict]:
    key = os.environ.get("BACKBOARD_API_KEY", "").strip()
    raw_pairs = os.environ.get("COMPARE_MODELS", "").strip()
    if not key or not raw_pairs:
        return [{"status": "skipped", "reason": "Set BACKBOARD_API_KEY and COMPARE_MODELS as provider:model pairs. TODO(verify) the Gemma id first."}]
    base = os.environ.get("BACKBOARD_BASE_URL", "https://app.backboard.io/api").rstrip("/")
    results = []
    for pair in raw_pairs.split(","):
        provider, _, model = pair.strip().partition(":")
        matched = 0
        invalid = 0
        failures = 0
        started = time.perf_counter()
        for row in rows:
            body = {
                "content": (
                    "Score this commit message only. Reply as JSON with quality, signals, and note. "
                    f"Message: {row['message']}"
                ),
                "llm_provider": provider,
                "model_name": model,
                "json_output": True,
                "memory": "off",
                "stream": False,
            }
            request = Request(
                base + "/threads/messages",
                data=json.dumps(body).encode(),
                method="POST",
                headers={"X-API-Key": key, "Content-Type": "application/json"},
            )
            try:
                with urlopen(request, timeout=40) as response:
                    payload = json.loads(response.read().decode())
                content = payload.get("content")
                data = json.loads(content) if isinstance(content, str) else content
                parsed = parse_quality_payload(data)
                if parsed is None:
                    invalid += 1
                elif (parsed.weight >= 0.8) == row["expect_high"]:
                    matched += 1
            except Exception:
                failures += 1
        results.append(
            {
                "provider": provider,
                "model": model,
                "rows": len(rows),
                "label_matches": matched,
                "invalid_payloads": invalid,
                "failures": failures,
                "seconds": round(time.perf_counter() - started, 2),
                "note": "Match counts are not a ranking. The set is small and the labels are coarse.",
            }
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-models", action="store_true")
    args = parser.parse_args()
    rows = load_rows()
    report = {"rules": rules_report(rows), "models": []}
    if args.run_models:
        report["models"] = run_models(rows)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
