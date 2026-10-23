"""Per-user exam state stored outside the candidate's Git repository."""

import json
import os
import re
from pathlib import Path


STATE_DIR = Path(os.environ.get("EXAMSHELL_STATE_DIR", "/var/lib/examshell/sessions"))


def state_path(username: str | None = None) -> Path:
    if username is None:
        return STATE_DIR / f"{os.getuid()}.json"
    safe_username = re.sub(r"[^a-zA-Z0-9_-]", "", username)
    if not safe_username:
        raise ValueError("Nome de usuário inválido para o estado da sessão.")
    return STATE_DIR / f"{safe_username}.json"


def load_state(username: str | None = None, *, migrate_legacy: bool = False) -> dict | None:
    path = state_path(username)
    if not path.exists() and username == "trial" and migrate_legacy:
        legacy_path = state_path()
        if legacy_path.exists():
            legacy_state = _read_state(legacy_path)
            if legacy_state is not None:
                legacy_state["username"] = username
                legacy_state.setdefault("mode", "trial")
                save_state(legacy_state, username)
                return legacy_state
    return _read_state(path)


def _read_state(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_state(state: dict, username: str | None = None) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = state_path(username or state.get("username"))
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2), encoding="utf-8")
    temporary.replace(path)
