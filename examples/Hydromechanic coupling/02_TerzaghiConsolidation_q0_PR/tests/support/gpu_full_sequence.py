"""One fresh CPU/GPU 2Tv delivery sequence; reuse the verified ownership/queue machinery."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import gpu_spr_sequence as sequence
from mdbc_gpu_vector_run import TESTS, bound, read, verify

TAG = "gpu_full_2tv_r1"
STATE = TESTS / "logs" / (TAG + ".status.json")
sequence.TAG, sequence.STATE = TAG, STATE
RUNNER = Path(__file__).with_name("gpu_coupled_run.py")
CHECKER = Path(__file__).with_name("gpu_coupled_compare.py")
REVIEW = Path(__file__).with_name("gpu_full_review.py")
BUILDS = dict(gpu=TESTS / "logs/gpu_coupled_Release_r2.build.json",
              cpu=TESTS / "logs/mech_bin_gpu_full_rel_r1.build.json")


def prerequisites():
    entries = [bound(p) for p in (Path(__file__), RUNNER, CHECKER, REVIEW, Path(sequence.__file__))]
    visual = TESTS / "logs/gpu_spr_15_r1.visual.json"
    v = read(visual)
    assert v["reviewed"] and v["passed"]
    entries += [bound(visual)] + v["evidence"]
    test_path = TESTS / "logs/gpu_full_selftest_r1.check.json"
    test = read(test_path)
    assert test["passed"] and test["original_safety_class_ast_identical"]
    entries += [bound(test_path)] + test["evidence"]
    pair = read(TESTS / "logs/gpu_spr_15_pair_review_r1.check.json")
    assert pair["passed"] and pair["half_step_gate_applied"] and pair["frames"] == 15001
    assert pair["comparison"]["within_limits"]
    for path in BUILDS.values():
        build = read(path)
        entries += [bound(path)] + build["inputs"] + build["runtime"] + build.get("resolved_compile_link_inputs", [])
    for backend in BUILDS:
        for name in ("gpu_full_save_" + backend + "_r1", "gpu_full_2tv_" + backend + "_r1"):
            assert not (TESTS / "outputs" / name).exists()
            assert not (TESTS / "logs" / (name + ".run.json")).exists()
    verify(entries)
    return entries


def run(args, report, backend, smoke):
    name = ("gpu_full_save_" if smoke else "gpu_full_2tv_") + backend + "_r1"
    sequence.child(args, report, name, [sys.executable, "-B", str(RUNNER), "--name", name,
        "--duration", "0.15" if smoke else "72.88429", "--dt", "0.00001", "--interval", "0.01",
        "--backend", backend, "--build", str(BUILDS[backend]), "--save", "--run"])
    return name


def compare(args, report, name, reference, tag, prefix=False, exact=False):
    argv = [sys.executable, "-B", str(CHECKER), "--candidate", name, "--reference", reference, "--tag", tag]
    if prefix:
        argv += ["--prefix"]
    if exact:
        argv += ["--exact-fields"]
    sequence.child(args, report, tag, argv)
    check = read(TESTS / "logs" / (tag + ".check.json"))
    assert check["passed"]
    if not exact:
        # Predeclared same-physics cross-backend delivery bound, NOT a half-step test or theoretical truth.
        assert check["comparison"]["within_limits"], "CPU/GPU delivery comparison exceeds 5 Pa / .005 mm"


def notify(args, report):
    message = (f"User-authorized same-thread CPU/GPU full-cycle delivery continuation {TAG}, not a new human observation. "
        f"Detected {report['status']}. First read {STATE}, {TESTS / 'logs' / (TAG + '.queue_attempt.json')}, "
        f"{TESTS / 'notes/gpu_full_r1.md'} and hg_release_plan.md. This is fresh k=1e-4 eta=.04 xi=.1 band5 vector-SPR/fixed-grid "
        "CPU/GPU 2Tv, not an old KEEP/SPR/traction worker. Inspect exact owned exits, actual times near 72.88429 s, "
        "native IDs, hashes and all preceding saved-output short regressions. Both production integrators are used; "
        "sample interval .01 s plus final partial interval, particle BI4 retained, stress double/pressure float. "
        "Review each completed run and same-backend 15-s prefix, all original geometry/load/drainage/post-.1-s 100-Pa "
        "safety and HG/natural-dt guards. The CPU/GPU 5-Pa/.005-mm bound is a predeclared cross-backend delivery comparison, "
        "not a full-cycle half-step or theory reference. Check gpu_full_2tv_r1_pair and gpu_full_2tv_r1.check.json; "
        "if missing or analysis failed, repair only new analysis, never rerun a completed solver. Inspect full history and "
        "all-Tv profile PNGs, theory at actual saved times and native material settlement. Quantify pressure, settlement, "
        "stress/Q, bottom bias, late dissipation and CPU/GPU loop timing; the separate short controlled benchmark was "
        "1.33649x, not automatically the long-run ratio. Preserve old results and disclose elastic/fixed-plane/small-rotation/fresh-HG "
        "limitations and only 15-s half-step evidence. Report proactively in Chinese and continue the authorized selective "
        "verified local/remote Git, formal k=1e-3/1e-4/1e-5 XML/BAT/full runs/plots, later complex-boundary tests and "
        "dependency-aware cleanup. User provisionally accepted 1D accuracy on Oct16; old late-Q must not indefinitely block "
        "delivery or restart KEEP. New regressions must still be repaired. If rejected/interrupted report exact cause/time "
        "and inspect surviving owned processes; do not duplicate solvers, overwrite evidence or relax guards. This worker "
        "queues once; never rearm/restart it or send connectivity tests. Use one verified same-thread completion mechanism "
        "for the next long stage and do not wait for another progress question.")
    path = TESTS / "logs" / (TAG + ".queue_attempt.json")
    payload = dict(thread=args.thread, recorded_utc=sequence.utc(), terminal=report.copy(), message=message)
    try:
        with path.open("x", encoding="utf8") as stream:
            json.dump(payload, stream, indent=2)
    except OSError as error:
        print(json.dumps(payload), file=sys.stderr, flush=True)
        report["queue_record_error"] = str(error)
    try:
        result = subprocess.run([args.codex, "queue", "--thread", args.thread, "--message", message],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        report.update(queue_attempted=True, queue_exit_code=result.returncode,
            queue_status="queued" if result.returncode == 0 else "failed_no_retry",
            queue_reply=(result.stdout + result.stderr).decode("utf8", errors="replace"))
    except Exception as error:
        report.update(queue_attempted=True, queue_status="uncertain_no_retry", queue_error=str(error))
    sequence.save(STATE, report)


def worker(args):
    assert not STATE.exists(), "Never restart this one-shot worker"
    report = dict(status="running", stage="prerequisites", worker_pid=os.getpid(), children=[],
                  started_utc=sequence.utc(), queue_attempted=False, physical_acceptance=False)
    sequence.save(STATE, report)
    try:
        report["prerequisites"] = prerequisites()
        names = {backend: run(args, report, backend, True) for backend in ("gpu", "cpu")}
        for backend, control in (("gpu", "gpu_spr_15_c_r1"), ("cpu", "hg_release_continue_r2_spr15_c")):
            compare(args, report, names[backend], control, "gpu_full_save_" + backend + "_prefix_r1", True, True)
        compare(args, report, names["gpu"], names["cpu"], "gpu_full_save_pair_r1")
        names = {}
        # Sequential long runs avoid uncontrolled CPU/GPU contention during timing.
        for backend, control in (("gpu", "gpu_spr_15_c_r1"), ("cpu", "hg_release_continue_r2_spr15_c")):
            names[backend] = run(args, report, backend, False)
            compare(args, report, names[backend], control, "gpu_full_2tv_" + backend + "_prefix_r1", True, True)
        compare(args, report, names["gpu"], names["cpu"], TAG + "_pair")
        sequence.child(args, report, "full_review", [sys.executable, "-B", str(REVIEW), "--gpu", names["gpu"],
            "--cpu", names["cpu"], "--tag", TAG])
        verify(report["prerequisites"])
        report.update(status="cpu_gpu_2tv_completed_pending_visual_physical_review", stage="review")
    except Exception as error:
        report.update(status="cpu_gpu_2tv_rejected_or_interrupted", reason=str(error))
    report["finished_utc"] = sequence.utc()
    sequence.save(STATE, report)
    notify(args, report)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    modes = p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--launch", action="store_true")
    modes.add_argument("--worker", action="store_true")
    p.add_argument("--thread", default=os.environ.get("CODEX_THREAD_ID"))
    p.add_argument("--codex", required=True)
    args = p.parse_args()
    assert args.thread and Path(args.codex).is_file()
    if args.worker:
        return worker(args)
    assert not STATE.exists()
    entries = prerequisites()
    if args.check:
        print(json.dumps(dict(checked=True, evidence_count=len(entries))))
        return
    idle = subprocess.run(["powershell", "-NoProfile", "-Command",
        "@(Get-Process -Name 'DualSPHysics*','gpu_coupled','mechanics','mdbc_gpu_vector' -ErrorAction SilentlyContinue).Count"],
        capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    assert idle.returncode == 0 and idle.stdout.strip() == "0"
    path = TESTS / "logs" / (TAG + ".worker.log")
    with path.open("xb") as stream:
        argv = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", "--thread", args.thread, "--codex", args.codex]
        child = subprocess.Popen(argv, cwd=TESTS.parent, stdout=stream, stderr=subprocess.STDOUT,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
    with (TESTS / "logs" / (TAG + ".launch.json")).open("x", encoding="utf8") as stream:
        json.dump(dict(pid=child.pid, argv=argv, thread=args.thread, evidence=entries, utc=sequence.utc()), stream, indent=2)
    print(json.dumps(dict(pid=child.pid, state=str(STATE))))


if __name__ == "__main__":
    main()
