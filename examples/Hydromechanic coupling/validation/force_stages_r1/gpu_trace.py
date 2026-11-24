"""Profile four C02 TPI steps or memcheck the two-step Debug program."""
import argparse
from collections import Counter
import csv
import json
import os
from pathlib import Path
import sqlite3
import subprocess


HERE = Path(__file__).resolve().parent
BIN = HERE.parents[3] / "bin/windows"
OUT = HERE / "gpu_tools"
NSYS = Path(r"C:\Program Files\NVIDIA Corporation\Nsight Systems 2023.3.3\target-windows-x64\nsys.exe")
MEMCHECK = Path(r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.3\compute-sanitizer\compute-sanitizer.exe")
SEED = HERE / "seeds/column2/upl_bigstep_2tv_CPU1_r1"


def save(path, data):
    with path.open("x", encoding="utf8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def run(mode, exe, name):
    out = OUT / name
    if not exe.is_file() or not SEED.with_suffix(".xml").is_file():
        raise FileNotFoundError("Missing program or prepared C02 seed")
    out.mkdir(parents=True)
    dest = out / "result"
    steps = 2 if mode == "memcheck" else 4
    solver = [str(exe.resolve()), "-gpu", "-stable", "-mdbc_freeslip", str(SEED),
              str(dest), "-dirdataout", "data", "-svres", f"-nsteps:{steps}"]
    if mode == "memcheck":
        cmd = [str(MEMCHECK), "--tool", "memcheck", "--error-exitcode", "87",
               "--log-file", str(out / "memcheck.log"), *solver]
    else:
        cmd = [str(NSYS), "profile", "--trace=cuda", "--sample=none",
               "--cpuctxsw=none", "--export=sqlite", "--output", str(out / "capture"), *solver]
    env = os.environ.copy()
    env["PATH"] = str(BIN) + os.pathsep + env["PATH"]
    save(out / "start.json", dict(command=cmd, requested_steps=steps))
    with (out / "console.log").open("xb") as console:
        try:
            proc = subprocess.run(cmd, cwd=BIN, env=env, stdout=console,
                                  stderr=subprocess.STDOUT, timeout=600,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
            tool_exit = proc.returncode
        except subprocess.TimeoutExpired:
            tool_exit = None
    receipt = dict(command=cmd, tool_exit=tool_exit, requested_steps=steps,
                   exe_bytes=exe.stat().st_size, exe_mtime_ns=exe.stat().st_mtime_ns)
    ok = tool_exit == 0
    if (dest / "Run.csv").is_file():
        with (dest / "Run.csv").open(encoding="utf8") as f:
            row, = csv.DictReader(f, delimiter=";")
        receipt.update(actual_steps=int(row["Steps"]), saved_parts=int(row["PartFiles"]),
                       exclusions=int(row["PartsOut"]), hardware=row["Hardware"])
        ok = ok and receipt["actual_steps"] == steps and receipt["exclusions"] == 0
    else:
        ok = False
    if mode == "memcheck":
        log = out / "memcheck.log"
        summary = [line for line in log.read_text(errors="replace").splitlines() if "ERROR SUMMARY" in line] if log.is_file() else []
        receipt["sanitizer_summary"] = summary
        ok = ok and len(summary) == 1 and summary[0].strip().endswith("ERROR SUMMARY: 0 errors")
    if mode == "trace":
        receipt["sqlite_present"] = (out / "capture.sqlite").is_file()
        ok = ok and receipt["sqlite_present"]
    receipt["passed"] = ok
    save(out / "run.json", receipt)
    if not ok:
        raise RuntimeError(str(out / "run.json"))


def kernels(name):
    directory = OUT / name
    # On Windows the Nsight agent can finish and export after its launching CLI times out.
    with (directory / "result/Run.csv").open(encoding="utf8") as f:
        row, = csv.DictReader(f, delimiter=";")
    if (int(row["Steps"]), int(row["PartFiles"]), int(row["PartsOut"])) != (4, 5, 0):
        raise ValueError("Incomplete solver window")
    if "Finished execution (code=0)." not in (directory / "result/Run.out").read_text(errors="replace"):
        raise ValueError("Solver did not report normal completion")
    with sqlite3.connect((directory / "capture.sqlite").as_uri() + "?mode=ro", uri=True) as con:
        if con.execute("PRAGMA quick_check").fetchall() != [("ok",)]:
            raise ValueError("Incomplete Nsight SQLite export")
        rows = list(con.execute("""
            SELECT k.correlationId,k.start,k.end,k.deviceId,k.contextId,k.streamId,n.value,
                   k.gridX,k.gridY,k.gridZ,k.blockX,k.blockY,k.blockZ,k.dynamicSharedMemory
            FROM CUPTI_ACTIVITY_KIND_KERNEL k
            JOIN StringIds n ON n.id = k.demangledName ORDER BY k.correlationId, k.start
        """))
    if not rows or len(set(r[0] for r in rows)) != len(rows):
        raise ValueError("Cannot identify unique kernel launches by CUDA correlation ID")
    if len({r[3:6] for r in rows}) != 1 or any(r[1] > r[2] for r in rows):
        raise ValueError("Expected one profiled GPU/context/stream and valid device intervals")
    if any(a[2] > b[1] for a,b in zip(rows,rows[1:])):
        raise ValueError("GPU device execution order differs from CUDA submission order")
    # Stream/context IDs can be process-specific. This profile requires exactly one.
    return [r[6:] for r in rows]


def compare(old, new):
    left, right = kernels(old), kernels(new)
    first = next((i for i in range(min(len(left), len(right))) if left[i] != right[i]), None)
    rec = dict(old=old, new=new, old_launches=len(left), new_launches=len(right),
               old_unique_kernels=len({r[0] for r in left}), new_unique_kernels=len({r[0] for r in right}),
               streams_each=1, cuda_device_execution_order_checked=True,
               counts_equal=Counter(left) == Counter(right), ordered_kernel_and_launch_geometry_equal=left == right)
    if first is not None:
        rec.update(first_different_launch=first+1, old_at_difference=left[first], new_at_difference=right[first])
    save(OUT / f"{old}_{new}.json", rec)
    if left != right:
        raise ValueError("Kernel launches differ")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(required=True, dest="mode")
    for mode in ("trace", "memcheck"):
        p = sub.add_parser(mode)
        p.add_argument("program", type=Path)
        p.add_argument("label")
    p = sub.add_parser("compare")
    p.add_argument("old")
    p.add_argument("new")
    args = parser.parse_args()
    if args.mode == "compare":
        compare(args.old, args.new)
    else:
        run(args.mode, args.program, args.label)
