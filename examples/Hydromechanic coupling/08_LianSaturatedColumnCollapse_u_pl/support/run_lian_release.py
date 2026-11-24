"""Run the Lian column validation cases with the public explicit u-pl GPU solver."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

CASE = Path(__file__).resolve().parents[1]
BIN = Path(os.environ.get("C08_BIN", CASE.parents[2] / "bin" / "windows")).resolve()
GROUPS = ("psi0", "psi2p5", "psim5")

# These existing same-material inputs were checked against the migrated public XML.
# A changed XML always requires a fresh solve. Existing raw results are read-only.
ARCHIVES = {
    ("psi0", "preload"): ("c08_h18_wend_psi0_pre_r2", "native_r1",
        "84a6bde4cd75757af78f4ac3c9fd5db865b0d6e8a9fa72ddde2b1708f851e47c"),
    ("psi2p5", "preload"): ("c08_h18_wend_branches_psi2p5_pre_r1", "native_r2",
        "6a7194eac4069c48affc77797590c19e35001f1f14c86ffd2035a6c9375fe707"),
    ("psi0", "collapse"): ("c08_h18_as03n255_full3_r1", "native_r1",
        "78b3c3da1323d385bff7d49d4a913cd255691e545c1b8a08196907eb7c924c0c"),
}


def result_name(group, stage):
    return "CaseLianCollapse_" + group + ("_pre" if stage == "preload" else "")


def output_path(group, stage):
    return CASE / (result_name(group, stage) + "_GPU_out")


def contract(stage):
    if stage == "preload":
        return 2000000, 1001, 10.0
    return 2600000, 301, 13.0


def write_record(path, data):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def validate_solver(directory, stage):
    steps, frames, end = contract(stage)
    # Configuration itself may contain semicolons. The named summary columns below
    # all precede Configuration in the native writer.
    with (directory / "Run.csv").open(encoding="utf-8-sig") as f:
        headers, row = list(csv.reader(f, delimiter=";"))
    def field(name):
        return row[headers.index(name)]
    if (int(field("Steps")) != steps or int(field("PartFiles")) != frames
            or int(field("PartsOut")) != 0 or not math.isclose(float(field("PhysicalTime")), end, abs_tol=1e-6)):
        raise RuntimeError(f"Unexpected solver endpoint in {directory / 'Run.csv'}")
    data = directory / "data"
    expected = {f"Part_{n:04}.bi4" for n in range(frames)}
    records = {p.name for p in data.glob("Part_[0-9][0-9][0-9][0-9].bi4") if p.stat().st_size > 0}
    if records != expected or not (data / "Part_Head.ibi4").is_file():
        raise RuntimeError(f"Incomplete particle series in {data} (expected {frames}, found {len(records)})")
    log = (directory / "Run.out").read_text(encoding="utf-8", errors="replace")
    if "Finished execution (code=0)" not in log:
        raise RuntimeError(f"Missing successful solver footer in {directory / 'Run.out'}")
    if stage == "collapse" and ("retired=255" not in log or "completed_step=2000000" not in log):
        raise RuntimeError(f"Missing same-material wall release in {directory / 'Run.out'}")


def call(argv):
    args = list(map(str, argv))
    print(subprocess.list2cmdline(args), flush=True)
    subprocess.run(args, cwd=CASE, check=True)


def archive_for(group, stage, digest):
    record = ARCHIVES.get((group, stage))
    if not record or record[2] != digest:
        return None
    tag, audit, _ = record
    source = CASE / "tests" / "outputs" / tag
    if not source.is_dir():
        return None
    if stage == "collapse":
        # Reuse the receiver only with the same checkpoint that fed that run.
        # A new source may have the same material but a different saved state.
        old_pre = CASE / "tests" / "outputs" / ARCHIVES[(group, "preload")][0] / "data/Part_1000.bi4"
        current_pre = output_path(group, "preload") / "data/Part_1000.bi4"
        if not old_pre.is_file() or not current_pre.is_file():
            return None
        if not os.path.samefile(current_pre, old_pre):
            if current_pre.read_bytes() != old_pre.read_bytes():
                return None
    receipt_path = source / audit / "completion.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
    steps, frames, _ = contract(stage)
    if not (receipt["passed"] and receipt["group"] == group and receipt["samples"] == frames
            and receipt["completed_steps"] == steps and (stage != "preload" or receipt["certified_PRE"])):
        raise RuntimeError(f"Archive native evidence mismatch in {receipt_path}")
    call_path = CASE / "tests" / "logs" / (tag + ".call.json")
    original_call = json.loads(call_path.read_text(encoding="utf-8-sig"))
    if original_call["actual_Popen_wait_exit"] != 0 or original_call["actual_solver_Win32_exit"] != 0:
        raise RuntimeError(f"Archive solver exit mismatch in {call_path}")
    validate_solver(source, stage)
    return source, receipt_path, call_path, original_call["actual_solver"]["exe"]


def mirror_native(source, dest):
    # data is a new directory. Only native inputs/logs are linked; derived files
    # always get separate paths. The runner never opens a linked file for writing.
    (dest / "data").mkdir()
    original = [p for p in source.iterdir() if p.name in {"Run.csv", "Run.out"} or
                p.suffix.lower() in {".xml", ".bi4", ".nbi4"}]
    original.extend(p for p in (source / "data").iterdir() if p.is_file())
    copied = 0
    for src in original:
        target = dest / src.relative_to(source)
        try:
            os.link(src, target)
        except OSError:
            shutil.copy2(src, target)
            copied += 1
    return len(original) - copied, copied


def ensure_stage(group, stage, require_existing=False):
    name = result_name(group, stage)
    definition = CASE / (name + "_Def.xml")
    digest = hashlib.sha256(definition.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    dest = output_path(group, stage)
    receipt = dest / "provenance.json"
    if dest.exists():
        if not receipt.is_file():
            raise RuntimeError(f"Existing output has no completed provenance; preserve and inspect {dest}")
        record = json.loads(receipt.read_text(encoding="utf-8-sig"))
        if (record.get("group") != group or record.get("stage") != stage
                or record.get("definition_sha256") != digest):
            raise RuntimeError(f"Output already exists with a different configuration: {dest}")
        if record.get("state") != "completed":
            # The wrapper can be interrupted after the solver wrote its footer.
            # Offline postprocessing may read a fully sealed solve; it does not
            # rewrite the interruption record or restart a partially saved run.
            if not (require_existing and record.get("method") == "fresh"):
                raise RuntimeError(f"Incomplete launch in {dest}. Preserve its logs and particle data.")
        validate_solver(dest, stage)
        print(f"Using complete {stage}: {dest}", flush=True)
        return dest

    archive = archive_for(group, stage, digest)
    if require_existing and archive is None:
        raise RuntimeError(f"No completed {stage} available for {group}")
    if archive is None:
        gencase = BIN / "GenCase_win64.exe"
        solver = BIN / "DualSPHysics5.2_GEO_win64.exe"
        for tool in (gencase, solver):
            if not tool.is_file():
                raise FileNotFoundError(tool)
    dest.mkdir()  # Atomic claim: a second launcher cannot enter the same output.
    record = dict(group=group, stage=stage, definition=definition.name, definition_sha256=digest,
                  state="started", started_utc=datetime.now(timezone.utc).isoformat())
    write_record(receipt, record)
    try:
        if archive:
            source, native_check, original_call, original_solver = archive
            record.update(method="adopted", original=source.relative_to(CASE).as_posix(),
                          original_solver=original_solver, original_call=original_call.relative_to(CASE).as_posix(),
                          native_receipt=native_check.relative_to(CASE).as_posix())
            record["hardlinked_files"], record["copied_files"] = mirror_native(source, dest)
        else:
            steps, _, _ = contract(stage)
            prefix = dest / name
            record.update(method="fresh", solver=str(solver), solver_bytes=solver.stat().st_size,
                          solver_mtime_ns=solver.stat().st_mtime_ns)
            write_record(receipt, record)
            call([gencase, str(definition.with_suffix("")), prefix, "-save:all"])
            boundary = "-mdbc_freeslip" if stage == "preload" else "-mdbc_freeslip:1"
            call([solver, "-gpu:0", "-stable", boundary, prefix, dest, "-dirdataout", "data",
                  "-svres", f"-nsteps:{steps}"])
        validate_solver(dest, stage)
    except Exception as exc:
        record.update(state="failed", error=str(exc))
        write_record(receipt, record)
        raise
    record.update(state="completed", completed_utc=datetime.now(timezone.utc).isoformat())
    write_record(receipt, record)
    print(f"Complete {stage}: {dest}", flush=True)
    return dest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", choices=(*GROUPS, "all"), required=True)
    parser.add_argument("--stage", choices=("preload", "collapse", "all"), default="all")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--solver-only", action="store_true", help="stop before making figures and particle exports")
    modes.add_argument("--postprocess-only", action="store_true", help="use completed solver data only")
    args = parser.parse_args()
    for group in GROUPS if args.group == "all" else (args.group,):
        pre = ensure_stage(group, "preload", args.stage == "collapse" or args.postprocess_only)
        python = [sys.executable, "-B", "-X", "utf8"]
        post = [*python, CASE / "support/postprocess_lian_release.py", "--group", group, "--preload", pre]
        if not args.solver_only:
            call([*post, "--preload-only"])
        if args.stage == "preload":
            continue
        result = ensure_stage(group, "collapse", args.postprocess_only)
        if not args.solver_only:
            call([*post, "--output", result])
            call([*python, CASE / "support/compare_lian_release.py", "--group", group])
    if args.group == "all" and args.stage != "preload" and not args.solver_only:
        call([*python, CASE / "support/compare_lian_release.py", "--all"])


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as error:
        sys.exit(str(error))
