import json
from pathlib import Path

_BASE = Path(__file__).parent / "data"
_BASE.mkdir(exist_ok=True)

SEEN_FILE = _BASE / "seen.json"
HISTORY_FILE = _BASE / "holding_history.json"


def load_seen() -> set[str]:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
    return set()


def save_seen(seen: set[str]) -> None:
    SEEN_FILE.write_text(
        json.dumps(sorted(seen), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_history() -> dict[str, float]:
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    return {}


def save_history(history: dict[str, float]) -> None:
    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )
