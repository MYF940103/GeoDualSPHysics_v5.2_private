"""Resolve relocated evidence at read/replay time; never rewrite historical JSON."""
import json
from pathlib import Path, PurePosixPath

VALIDATION_ROOT = Path(__file__).resolve().parent
_MIGRATION = json.loads((VALIDATION_ROOT / "migration_20260907_before.json").read_text(encoding="utf-8-sig"))


def relocate_archived_argument(value):
    """Translate a whole path argument under one moved directory; leave flags alone.

    Both the old location and the recorded migration destination are recognized.
    The destination is computed from this module, so another repository relocation
    does not require editing immutable historical commands or result hashes.
    """
    normalized = value.replace("\\", "/")
    for entry in _MIGRATION["directories"]:
        for recorded_root in (entry["old_path"], entry["new_path"]):
            prefix = recorded_root.replace("\\", "/").rstrip("/")
            if normalized.casefold() == prefix.casefold() or normalized.casefold().startswith(prefix.casefold() + "/"):
                suffix = normalized[len(prefix):].lstrip("/")
                parts = PurePosixPath(suffix).parts
                if ".." in parts:
                    raise ValueError("Archived relocation path escapes its evidence directory")
                return str(VALIDATION_ROOT / entry["name"] / Path(*parts))
    return value
