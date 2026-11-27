"""Own one local run of the smoke-qualified Cryer weak-full package."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
from time import monotonic


CASE = Path(__file__).resolve().parents[2]
PACKAGE = CASE / "tests/outputs/cryer_weak_full_build_r1/package"
OUTPUT = CASE / "CaseCryerWeakFull_nu030_1Tv_GPU_out"
TAG = CASE / "tests/logs/cryer_weak_full_local_r1"


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, data):
    with path.open("x", encoding="utf8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main(cli):
    thread = os.environ.get("CODEX_THREAD_ID")
    if not cli.is_file() or not thread:
        raise ValueError("The direct owner requires the current thread and queue executable")
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    write(TAG.with_suffix(".owner.json"), {"pid": os.getpid(), "utc": now(), "output": str(OUTPUT)})
    stage, error, exit_code = "package", None, None
    timer = monotonic()
    try:
        manifest = PACKAGE / "manifest.json"
        manifest_sha = sha(manifest)
        for entry in json.loads(manifest.read_text(encoding="utf-8-sig"))["files"]:
            path = PACKAGE / entry["name"]
            if path.stat().st_size != entry["bytes"] or sha(path) != entry["sha256"].lower():
                raise ValueError(f"The smoke-qualified package binding changed: {path}")
        hardware = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,uuid,driver_version,memory.total", "--format=csv"],
            text=True,
        ).splitlines()
        args = [str(PACKAGE / "weak_full.exe"), "full", str(OUTPUT)]
        stage = "solver"
        start = {"argv": args, "cwd": str(PACKAGE), "program_sha256": sha(Path(args[0])),
                 "manifest_sha256": manifest_sha, "owner": os.getpid(), "utc": now(),
                 "gpu_inventory": hardware}
        with TAG.with_suffix(".console.log").open("xb") as console:
            with subprocess.Popen(args, cwd=PACKAGE, stdout=console, stderr=subprocess.STDOUT) as child:
                start["pid"] = child.pid
                write(TAG.with_suffix(".start.json"), start)
                print(f"Cryer weak-full launched, GPU child pid={child.pid}, output={OUTPUT}", flush=True)
                exit_code = child.wait()
        write(TAG.with_suffix(".call.json"), dict(start, returncode=exit_code, ended_utc=now()))
        if exit_code != 0:
            raise RuntimeError(f"Original solver returned {exit_code}; inspect its console and last actual save")
        stage = "seal"
        steps = sorted(set(map(int, (PACKAGE / "inputs/steps.txt").read_text().split()))
                       | {4097, 4160, 25984, 36864})
        clock_path = OUTPUT / "actual_clock.csv"
        with clock_path.open(encoding="utf8", newline="") as stream:
            clock = list(csv.DictReader(stream))
        if (OUTPUT / "complete.txt").read_text().strip() != "full" or len(clock) != 269 or steps[-1] != 481685:
            raise ValueError("Missing completed weak full-cycle clock or end marker")
        if [int(row["step"]) for row in clock] != steps or any(
            float(row["time_s"]) != int(row["step"]) * (2.0**-19) for row in clock
        ):
            raise ValueError("Actual saved clock differs from the frozen weak full-cycle plan")
        files = sorted(p for p in OUTPUT.iterdir() if p.is_file())
        if {p.name for p in files} != {clock_path.name, "complete.txt", *(f"state_{step}.bin" for step in steps)}:
            raise ValueError("Unexpected saved state inventory")
        write(OUTPUT / "server_run.json", {
            "mode": "full", "package": manifest_sha, "gpu_inventory": hardware,
            "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
            "utc_finished": now(), "elapsed_seconds": monotonic() - timer,
            "files": [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in files],
        })
        stage = "completed_pending_native_review"
    except Exception as exc:
        error = str(exc)
        print(error, flush=True)
    terminal = TAG.with_suffix(".terminal.json")
    write(terminal, {"stage": stage, "solver_exit_code": exit_code, "error": error,
                     "output": str(OUTPUT), "ended_utc": now()})
    message = (f"已授权同线程 Cryer weak-full ν=.30 本地 1 Tv 计算终态：{terminal}。"
               "核原 start/call/console、真实保存时刻、269 个原生状态和封存输入，正常后做独立审查及旧方案对比图表。"
               "求解失败保留首因和原始保存帧；已完成求解只补派生，禁止重跑、重发及重新布防。")
    write(TAG.with_suffix(".queue_attempt.json"), {"utc": now(), "terminal": str(terminal)})
    try:
        rc = subprocess.run([str(cli), "queue", "--thread", thread, "--message", message],
                            cwd=CASE, capture_output=True, timeout=45).returncode
        delivery = {"returncode": rc}
    except (OSError, subprocess.TimeoutExpired) as exc:
        delivery = {"delivery": "unknown", "reason": str(exc)}
    write(TAG.with_suffix(".queue_result.json"), delivery)
    return int(error is not None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", required=True, type=Path)
    raise SystemExit(main(parser.parse_args().cli))
