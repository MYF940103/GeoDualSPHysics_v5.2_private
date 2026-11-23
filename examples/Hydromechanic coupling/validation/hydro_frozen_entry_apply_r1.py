"""Verify or install only the reviewed, small formal-input overlay; default is read-only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from hydro_frozen_entry_stage_r1 import STAGE, SUITE

REPORT = Path(__file__).with_name("hydro_frozen_entry_release_r2.json")


def signature(path):
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError("Expected ordinary file: " + str(path))
    return {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def matches(path, wanted):
    actual=signature(path)
    if wanted==actual:
        return True
    if wanted is None or actual is None or path.parent.name=="frozen_xml" and path.suffix==".xml":
        return False
    # Working-tree checkout may materialize tracked text with a different EOL setting.
    if path.suffix.lower() not in (".xml",".bat",".ps1",".json") and path.name!=".gitattributes":
        return False
    lf=path.read_bytes().replace(b"\r\n",b"\n")
    return any(len(raw)==wanted["bytes"] and hashlib.sha256(raw).hexdigest()==wanted["sha256"]
               for raw in (lf,lf.replace(b"\n",b"\r\n")))


def guarded_path(root, rel):
    item = root / rel
    if item.resolve() != item or not item.is_relative_to(root):
        raise ValueError("Unexpected redirected or outside path: " + str(item))
    return item


def apply(root, backup, do_write, overlay):
    manifest = json.loads(REPORT.read_text())
    if all(matches(guarded_path(root,Path(r["path"])),r["proposed"]) for r in manifest["entries"]):
        print(f"All {len(manifest['entries'])} target files already match the release. No files written.")
        return
    if not overlay.is_dir():
        raise ValueError("Missing reviewed overlay. Rebuild it from the pinned Git history using hydro_frozen_git_rebuild_r2.py.")
    files = []
    for row in manifest["entries"]:
        rel = Path(row["path"])
        old, proposed = row["previous"], row["proposed"]
        src, dst = guarded_path(overlay, rel), guarded_path(root, rel)
        copy = guarded_path(backup, rel)
        if signature(src) != proposed:
            raise ValueError("Candidate changed: " + str(rel))
        current = signature(dst)
        installed=matches(dst,proposed)
        if not installed and not matches(dst,old):
            raise ValueError("Unrelated target change: " + str(rel))
        if copy.exists() and not matches(copy,old):
            raise ValueError("Previous backup has an unexpected value: " + str(rel))
        if installed and old != proposed and old is not None and not matches(copy,old):
            raise ValueError("Installed target missing its required previous backup: " + str(rel))
        files.append((src, dst, copy, old, proposed, current, installed))
    if not do_write:
        print(f"Read-only verification passed for {len(files)} files.")
        return
    # Prepare every old file before changing the first target.
    for src, dst, copy, old, proposed, current, installed in files:
        if old is not None and not copy.is_file():
            copy.parent.mkdir(parents=True, exist_ok=True)
            with copy.open("xb") as f, dst.open("rb") as original:
                shutil.copyfileobj(original, f)
            if signature(copy) != current:
                raise ValueError("Target changed while saving its original: " + str(dst))
    changed = 0
    for src, dst, copy, old, proposed, current, installed in files:
        if installed:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=dst.parent,prefix=".hydro_xml_",delete=False) as temp, src.open("rb") as origin:
            shutil.copyfileobj(origin,temp)
            tmp = Path(temp.name)
        if signature(dst) != current or signature(tmp) != proposed:
            raise ValueError("Target or prepared bytes changed during installation: " + str(dst))
        if current is None:
            os.rename(tmp, dst)  # On Windows a competing new destination is refused.
        else:
            os.replace(tmp, dst)
        changed += 1
    if any(not matches(dst,proposed) for _,dst,_,_,proposed,_,_ in files):
        raise ValueError("Final verification failed")
    print(f"Installed {changed} of {len(files)} verified files. Old files are in {backup}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=SUITE)
    parser.add_argument("--backup", type=Path, default=STAGE / "original_before_install")
    parser.add_argument("--overlay", type=Path, default=STAGE / "winrelease")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    dest, archive = args.root.resolve(), args.backup.resolve()
    if (dest != SUITE.resolve() and not dest.is_relative_to(STAGE.resolve())) or not archive.is_relative_to(STAGE.resolve()) or archive == dest:
        raise ValueError("Unexpected deployment or backup directory")
    apply(dest,archive,args.apply,args.overlay.resolve())

