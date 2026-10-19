"""One fresh GPU 15-s coarse/half stage, with a single same-thread terminal queue."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from mdbc_gpu_vector_run import TESTS, bound, read, verify

TAG = "gpu_spr_15_r1"
RUNNER = Path(__file__).with_name("gpu_coupled_run.py")
CHECKER = Path(__file__).with_name("gpu_coupled_compare.py")
PREFIX = Path(__file__).with_name("gpu_prefix_check.py")
BUILD = TESTS / "logs/gpu_coupled_Release_r2.build.json"
STATE = TESTS / "logs" / (TAG + ".status.json")


def utc():
    return datetime.now(timezone.utc).isoformat()


def save(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf8")
    for attempt in range(6):
        try:
            tmp.replace(path)
            return
        except PermissionError:
            if attempt == 5:
                # A reader must not kill an owned solver or prevent its terminal queue.
                print("Status replace temporarily blocked; retained temporary snapshot: " + str(tmp), file=sys.stderr, flush=True)
                return
            time.sleep(.2)


def prerequisites():
    entries = [bound(p) for p in (Path(__file__), RUNNER, CHECKER, PREFIX, Path(__file__).with_name("mdbc_gpu_vector_run.py"), BUILD)]
    observer_path = TESTS / "logs/gpu_safety_r1.check.json"
    observer = read(observer_path)
    assert observer["passed"] and len(observer["rejected"]) == 11
    entries += [bound(observer_path)] + observer["sources"]
    for tag in ("gpu_spr_015_c_review_r1", "gpu_spr_015_h_review_r1", "gpu_spr_015_pair_review_r1"):
        path = TESTS / "logs" / (tag + ".check.json")
        check = read(path)
        assert check["passed"] and check["frames"] == 151
        assert all(all(s.values()) for s in check["safety"].values()) and all(check["hourglass_checks"].values())
        if "pair" in tag:
            assert check["half_step_gate_applied"] and check["comparison"]["within_limits"]
        entries += [bound(path), check["figure"], check["metrics"]]
    visual = TESTS / "logs/gpu_spr_short_r1.visual.json"
    checked = read(visual)
    assert checked["reviewed"]
    entries += [bound(visual)] + checked["evidence"]
    build = read(BUILD)
    assert build["built"]
    entries += build["inputs"] + build["runtime"] + [dict(path=build["executable"], sha256=build["executable_sha256"])]
    for name in ("gpu_spr_15_c_r1", "gpu_spr_15_h_r1"):
        assert not (TESTS / "outputs" / name).exists() and not (TESTS / "logs" / (name + ".run.json")).exists()
    verify(entries)
    return entries


def notify(args, report):
    # Record intent before the one allowed queue call; never retry uncertain delivery.
    message = (f"User-authorized same-thread GPU SPR delivery continuation {TAG}, not a new human observation. "
        f"Detected {report['status']}. Read {STATE}, {TESTS / 'logs' / (TAG + '.queue_attempt.json')} and "
        f"{TESTS / 'notes/gpu_spr_r1.md'} plus hg_release_plan.md before claims. This is the new GPU vector-SPR/fixed-grid "
        "15-s coarse/half stage, not an old CPU boundary/KEEP notifier. Check actual times, native IDs, owned exits, "
        "build/input/output hashes, original all-sample geometry/load/drainage and post-.1-s 100-Pa stress/top-gap safety, "
        "HG histories/natural dt/work identity and the original all-15001-sample 5-Pa/.005-mm GPU half gate. "
        "Compare actual matched CPU/GPU material pressure/settlement/stress/Q, inspect the new comparison PNGs and report "
        "Chinese quantified findings proactively. Coarse CPU control is hg_release_continue_r2_spr15_c, half is its _h; "
        "these are retained same-physics CPU controls, not newly run GPU truth or a full-cycle claim. "
        "If failed/interrupted inspect exact time/reason and owned processes, preserve evidence and repair within scope "
        "without relaxed thresholds, duplicate solvers or restarting old workers. On pass continue the user's delivery: "
        "controlled CPU/GPU timing, fresh full k=1e-4 CPU/GPU 2Tv validation as required by the plan, then verified selective "
        "local/remote Git, formal k=1e-3/1e-4/1e-5 XML/BAT and full plots, dependency-aware cleanup. "
        "The user provisionally accepted 1D accuracy on Oct16; do not restart KEEP diagnosis or let old late-Q indefinitely "
        "block delivery. Keep fixed-plane elastic limitations; general corners/curves/NoPen stay at their later planned stage. "
        "Do not claim full GPU/2Tv acceptance from 15 s. Do not rearm/restart this one-shot worker or send connectivity tests. "
        "Use one verified same-thread completion mechanism for the next active long stage; continue without waiting for a progress question.")
    attempt = TESTS / "logs" / (TAG + ".queue_attempt.json")
    payload = dict(thread=args.thread, recorded_utc=utc(), message=message, terminal=report.copy())
    try:
        with attempt.open("x", encoding="utf8") as stream:
            json.dump(payload, stream, indent=2)
    except OSError as error:
        report["queue_intent_record_error"] = str(error)
        print(json.dumps(payload), file=sys.stderr, flush=True)
    try:
        queued = subprocess.run([args.codex, "queue", "--thread", args.thread, "--message", message],
                                stdin=subprocess.DEVNULL, capture_output=True, timeout=45,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        report.update(queue_attempted=True, queue_exit_code=queued.returncode,
                      queue_status="queued" if queued.returncode == 0 else "failed_no_retry",
                      queue_reply=(queued.stdout + queued.stderr).decode("utf8", errors="replace"))
    except Exception as error:
        report.update(queue_attempted=True, queue_status="uncertain_no_retry", queue_error=str(error))
    save(STATE, report)


def child(args, report, key, argv):
    report.update(stage=key, updated_utc=utc())
    save(STATE, report)
    log = TESTS / "logs" / (TAG + "_" + key + ".log")
    with log.open("xb") as stream:
        process = subprocess.Popen(argv, cwd=TESTS.parent, stdout=stream, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        report["children"].append(dict(stage=key, pid=process.pid, argv=argv, log=str(log)))
        save(STATE, report)
        while process.poll() is None:
            report["updated_utc"] = utc()
            save(STATE, report)
            time.sleep(15)
        report["children"][-1].update(exit_code=process.returncode, owned_process_exited=True, log_hash=bound(log))
    save(STATE, report)
    if process.returncode != 0:
        raise RuntimeError(key + " failed; inspect its log and run/check receipt")


def worker(args):
    if STATE.exists():
        raise FileExistsError("Frozen worker must not be restarted")
    report = dict(status="checking_prerequisites", stage="prerequisites", worker_pid=os.getpid(),
                  started_utc=utc(), children=[], queue_attempted=False, physical_acceptance=False)
    with STATE.open("x", encoding="utf8") as stream:
        json.dump(report, stream)
    try:
        report["prerequisites"] = prerequisites()
        for suffix, dt in (("c", "0.00001"), ("h", "0.000005")):
            name = "gpu_spr_15_" + suffix + "_r1"
            child(args, report, suffix + "_run", [sys.executable, "-B", str(RUNNER), "--name", name,
                  "--duration", "15", "--dt", dt, "--build", str(BUILD), "--run"])
            child(args, report, suffix + "_prefix", [sys.executable, "-B", str(PREFIX), "--candidate", name,
                  "--reference", "gpu_spr_015_" + suffix + "_r1", "--tag", "gpu_spr_15_" + suffix + "_prefix_r1"])
            child(args, report, suffix + "_cpu_comparison", [sys.executable, "-B", str(CHECKER), "--candidate", name,
                  "--reference", "hg_release_continue_r2_spr15_" + suffix, "--tag", "gpu_spr_15_" + suffix + "_review_r1"])
        child(args, report, "half_pair", [sys.executable, "-B", str(CHECKER), "--candidate", "gpu_spr_15_c_r1",
              "--reference", "gpu_spr_15_h_r1", "--tag", "gpu_spr_15_pair_review_r1", "--half-gate"])
        report.update(status="gpu_15s_pair_passed_pending_visual_and_full_review", stage="review")
    except Exception as error:
        report.update(status="gpu_15s_rejected_or_interrupted", reason=str(error))
    report["finished_utc"] = utc()
    save(STATE, report)
    notify(args, report)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--launch", action="store_true")
    mode.add_argument("--worker", action="store_true")
    p.add_argument("--thread", default=os.environ.get("CODEX_THREAD_ID"))
    p.add_argument("--codex", required=True)
    args = p.parse_args()
    assert args.thread and Path(args.codex).is_file()
    if args.worker:
        return worker(args)
    assert not STATE.exists() and not (TESTS / "logs" / (TAG + ".launch.json")).exists()
    entries = prerequisites()
    if args.check:
        print(json.dumps(dict(status="checked_not_started", bound_files=len(entries))))
        return
    # At launch no solver is active. Never adopt/restart a partial run implicitly.
    idle = subprocess.run(["powershell", "-NoProfile", "-Command",
        "@(Get-Process -Name 'DualSPHysics*','gpu_coupled','mdbc_gpu_vector' -ErrorAction SilentlyContinue).Count"],
        capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    assert idle.returncode == 0 and idle.stdout.strip() == "0"
    log = TESTS / "logs" / (TAG + ".worker.log")
    argv = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", "--thread", args.thread, "--codex", args.codex]
    with log.open("xb") as stream:
        process = subprocess.Popen(argv, cwd=TESTS.parent, stdout=stream, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
    with (TESTS / "logs" / (TAG + ".launch.json")).open("x", encoding="utf8") as stream:
        json.dump(dict(pid=process.pid, argv=argv, thread=args.thread, prerequisites=entries, utc=utc()), stream, indent=2)
    print(json.dumps(dict(started_pid=process.pid, state=str(STATE))))


if __name__ == "__main__":
    main()
