"""One fresh formal k1e-5 GPU run, existing native guards, one same-thread follow-up."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import formal_release_sequence as flow
from mdbc_gpu_vector_run import read, bound, verify

TAG = "formal_release_k5_r1"
CASE, TESTS, REPO = flow.CASE, flow.TESTS, flow.REPO
STATE = TESTS/"logs"/(TAG+".status.json")
OUTPUT = CASE/(flow.STEM+"k1em5_release_GPU_out")
BAT = CASE/("x"+flow.STEM+"k1em5_win64_GPU.bat")
flow.TAG, flow.STATE = TAG, STATE


def prerequisites():
    audited = TESTS/"logs/formal_release_k34_r1.review.json"
    assert read(audited)["passed"]
    for key in ("k1em3", "k1em4"):
        assert read(CASE/"figures"/("full_validation_release_"+key+"_GPU.check.json"))["passed"]
    head = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
    remote = subprocess.check_output(["git", "-C", str(REPO), "ls-remote", "--heads", "origin", "u-pw"], text=True).split()[0]
    assert head == remote, "Keep the release checkpoint locally and remotely"
    assert not subprocess.check_output(["git", "-C", str(REPO), "diff", "--name-only", "--", "src/source", "src/VS"], text=True).strip()
    assert not OUTPUT.exists(), "Never overwrite or restart a retained formal run"
    entries = [bound(p) for p in (Path(__file__), Path(flow.__file__), CASE/"support/release_case.py",
        CASE/"support/compare_precision_q0.py", flow.READER, BAT, CASE/(flow.STEM+"k1em5_Def.xml"),
        REPO/"bin/windows/DualSPHysics5.2_GEO_win64.exe", REPO/"bin/windows/GenCase_win64.exe",
        REPO/"bin/windows/PartVTK_win64.exe", REPO/"src/source/JSphCpuSingle.cpp", REPO/"src/source/JSphGpuSingle.cpp", audited)]
    verify(entries)
    return head, entries


def worker(args):
    assert not STATE.exists(), "One-shot worker must not be restarted"
    report = dict(status="running", stage="prerequisites", worker_pid=os.getpid(), started_utc=flow.utc(), children=[],
        expected_steps=72875286, dt_s=.00001, target_time_s=728.75286)
    flow.save(STATE, report)
    try:
        report["checkpoint"], report["inputs"] = prerequisites()
        flow.child(report, "formal_k1em5", [os.environ["ComSpec"], "/d", "/c", str(BAT)], OUTPUT)
        check_path = CASE/"figures/full_validation_release_k1em5_GPU.check.json"
        result = read(check_path)
        assert result["passed"] and result["numerical_safety_passed"]
        assert abs(result["final"]["time_s"]-report["target_time_s"]) < report["dt_s"]+1e-7
        verify(result["evidence"])
        verify(report["inputs"])
        report.update(status="formal_k5_completed_pending_visual_review", stage="review", result=bound(check_path),
            final=result["final"], frames=result["frames"])
    except Exception as error:
        report.update(status="formal_k5_rejected_or_interrupted", reason=str(error))
    report["finished_utc"] = flow.utc(); flow.save(STATE, report)
    message = (f"User-authorized same-thread formal k1e-5 delivery continuation {TAG}, not a new human observation. Detected {report['status']}. "
        f"Read {STATE}, {TESTS/'logs'/(TAG+'.queue_attempt.json')}, tests/notes/formal_release_r1.md and logs/formal_release_k34_r1.review.json before claims. "
        "This is the new actual root k1e-5 GPU BAT, dt=1e-5, TimeMax=728.75286, 72875286 steps, not an old k3/k4 worker. "
        "Never restart/rearm this worker, overwrite retained data, start duplicate solvers or send connectivity tests. "
        "Verify exact owned exits, native IDs, actual final time/Tv, input/executable/output hashes, runtime HG/natural-step and all original geometry/load/drainage/100-Pa guards. "
        "If a completed solver's postprocessing failed, repair only new analysis without rerunning it. On runtime failure report exact reason/time and diagnose without relaxed thresholds. "
        "Inspect root full_validation_release_k1em5_GPU profile/history PNGs and full native records; quantify theory pressure/settlement/Q/bottom bias and late dissipation. "
        "k1e-3 has completed and k1e-4 was explicitly adopted from accepted CPU/GPU data; do not rerun them. On pass finish the requested all-three permeability comparisons/plots, "
        "later planned complex-boundary validation, dependency-aware tests cleanup and selective verified final local/remote Git backup. "
        "The user provisionally accepted 1D accuracy Oct16: residual old Q does not indefinitely block delivery or justify restarting KEEP. "
        "No full-cycle half-step, plasticity, large-rotation, complex-boundary or exact-HG-restart claim. Proactively report in Chinese and continue without another progress request. "
        "Use one verified same-thread completion mechanism only for a genuinely new later long stage.")
    with (TESTS/"logs"/(TAG+".queue_attempt.json")).open("x", encoding="utf8") as stream:
        json.dump(dict(thread=args.thread, utc=flow.utc(), terminal=report.copy(), message=message), stream, indent=2)
    try:
        q = subprocess.run([args.codex, "queue", "--thread", args.thread, "--message", message], capture_output=True,
            timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        report.update(queue_attempted=True, queue_status="queued" if q.returncode == 0 else "failed_no_retry",
            queue_reply=(q.stdout+q.stderr).decode(errors="replace"))
    except Exception as error:
        report.update(queue_attempted=True, queue_status="uncertain_no_retry", queue_error=str(error))
    flow.save(STATE, report)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--codex", required=True)
    p.add_argument("--thread", required=True)
    modes = p.add_mutually_exclusive_group(required=True)
    for name in ("check", "launch", "worker"):
        modes.add_argument("--"+name, action="store_true")
    args = p.parse_args()
    assert Path(args.codex).is_file() and args.thread
    if args.worker:
        return worker(args)
    assert not STATE.exists()
    checkpoint, entries = prerequisites()
    if args.check:
        print(json.dumps(dict(checked=True, checkpoint=checkpoint, inputs=len(entries)))); return
    idle = subprocess.run(["powershell", "-NoProfile", "-Command", "@(Get-Process -Name 'DualSPHysics*','gpu_coupled','mechanics' -ErrorAction SilentlyContinue).Count"], capture_output=True, text=True)
    assert idle.returncode == 0 and idle.stdout.strip() == "0", "No duplicate solver or competing run"
    with (TESTS/"logs"/(TAG+".worker.log")).open("xb") as stream:
        argv = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", "--codex", args.codex, "--thread", args.thread]
        process = subprocess.Popen(argv, cwd=CASE, stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    with (TESTS/"logs"/(TAG+".launch.json")).open("x", encoding="utf8") as stream:
        json.dump(dict(pid=process.pid, thread=args.thread, argv=argv, checkpoint=checkpoint, inputs=entries), stream, indent=2)
    print(json.dumps(dict(pid=process.pid, state=str(STATE))))


if __name__ == "__main__":
    main()
