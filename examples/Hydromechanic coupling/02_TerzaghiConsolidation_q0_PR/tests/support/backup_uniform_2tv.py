"""Verified local raw-data snapshot; no solver, deletion, or remote upload."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import zipfile

TESTS = Path(__file__).resolve().parents[1]
CASE = TESTS.parent
REPO = CASE.parents[2]
TAG = "k5em5_hg05_full_cpu_r1"
ARCHIVE = TESTS/"outputs/k5em5_uniform_2tv_verified_r1.zip"
RECEIPT = TESTS/"logs/k5em5_uniform_2tv_snapshot_r1.json"


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest().upper()


def main():
    assert not ARCHIVE.exists() and not RECEIPT.exists(), "Preserve the existing snapshot"
    state = json.loads((TESTS/"logs"/(TAG+".status.json")).read_text(encoding="utf-8-sig"))
    review = json.loads((TESTS/"logs"/(TAG+".review.json")).read_text(encoding="utf-8-sig"))
    assert review["passed"] and review["visual_inspected"] and state["owned_exited"]
    assert state["exit_code"] == state["bat_exit_code"] == 0
    folder = Path(state["output"])
    assert folder.parent == CASE and folder.name.endswith("_CPU_uniform_out")
    # VTK particle exports are regenerable; keep every native BI4 and all run records.
    paths = {p for p in folder.rglob("*") if p.is_file() and "particles" not in p.relative_to(folder).parts}
    for item in state["inputs"]:
        path = Path(item["path"])
        assert digest(path) == item["sha256"].upper(), path
        paths.add(path)
    expected = {Path(item["path"]): item["sha256"].upper() for item in state["outputs"]}
    for path in paths & expected.keys():
        assert digest(path) == expected[path], path
    paths.update(p for p in (TESTS/"logs").glob(TAG+".*") if p.is_file())
    paths.update(p for p in (TESTS/"figures").glob(TAG+"_*.csv") if p.is_file())
    paths.update(p for p in (CASE/"figures").glob("full_validation_three*") if p.is_file())
    paths.update(p for p in (CASE/"figures").glob("full_validation_release_k5em5_uniform_CPU*") if p.is_file())
    paths.update([Path(__file__).resolve(), TESTS/"support/k5em5_hg05_full_review.py",
                  CASE/"support/publish_three_permeabilities.py", CASE/"README.md",
                  CASE/"figures/README.md", TESTS/"notes/k5em5_uniform_r1.md"])
    entries = [dict(path=str(p), member=p.relative_to(REPO).as_posix(), bytes=p.stat().st_size,
                    sha256=digest(p)) for p in sorted(paths)]
    assert len({e["member"] for e in entries}) == len(entries)
    manifest = dict(utc=datetime.now(timezone.utc).isoformat(), source_checkpoint=state["checkpoint"],
                    accepted_review=str(TESTS/"logs"/(TAG+".review.json")), entries=entries,
                    exclusions=["Regenerable particles/*.vtk; original exports remain untouched"],
                    limitations=["Local same-disk copy, not off-site disaster recovery or an exact-HG restart"])
    with zipfile.ZipFile(ARCHIVE, "x", zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
        for entry in entries:
            archive.write(entry["path"], entry["member"])
        archive.writestr("SNAPSHOT_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    with zipfile.ZipFile(ARCHIVE) as archive:
        assert archive.testzip() is None
        for entry in entries:
            with archive.open(entry["member"]) as stream:
                assert hashlib.file_digest(stream, "sha256").hexdigest().upper() == entry["sha256"]
            assert digest(entry["path"]) == entry["sha256"], "Source changed during backup"
    result = dict(passed=True, archive=str(ARCHIVE), archive_sha256=digest(ARCHIVE),
                  archive_bytes=ARCHIVE.stat().st_size, files=len(entries),
                  source_bytes=sum(e["bytes"] for e in entries), local_only=True,
                  verified_all_members=True, original_data_untouched=True,
                  utc=datetime.now(timezone.utc).isoformat())
    with RECEIPT.open("x", encoding="utf8") as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
