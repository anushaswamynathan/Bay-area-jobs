#!/usr/bin/env python3

import json
import sys
from pathlib import Path

import server


def load_payload() -> dict:
    if len(sys.argv) > 1:
        return json.loads(Path(sys.argv[1]).read_text())

    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("Provide a JSON file path or pipe JSON via stdin")
    return json.loads(raw)


def import_payload_to_state(payload: dict) -> dict:
    normalized = server.normalize_import_payload(payload)
    state = server.load_state()
    state["criteria"] = normalized["criteria"]
    state.setdefault("digestsByDate", {})[normalized["date"]] = {
        "generatedAt": server.utc_now_iso(),
        "summary": normalized["summary"],
        "jobs": normalized["jobs"],
    }
    state["lastUpdatedAt"] = server.utc_now_iso()
    server.save_state(state)
    return normalized


def main() -> int:
    try:
        payload = load_payload()
        normalized = import_payload_to_state(payload)
    except Exception as error:
        print(f"Import failed: {error}", file=sys.stderr)
        return 1

    print(f"Imported {len(normalized['jobs'])} jobs for {normalized['date']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
