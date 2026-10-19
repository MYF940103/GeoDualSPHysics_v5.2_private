"""One completion follow-up for the already-running production merge sequence.

Never launches solvers, retries computations, changes numerical inputs, or
rearms the older traction notifier. --self-test is read-only and queues nothing.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil

TESTS = Path(__file__).resolve().parents[1]
SEQUENCE = TESTS/"logs/hg_merge_sequence.status.json"
RECORD = TESTS/"logs/hg_merge_followup.status.json"
ANALYSIS = TESTS/"support/hg_merge_compare.py"


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def decision(state, live, now):
    if state["status"] == "completed_2tv_pending_full_physical_review":
        return "completed_pending_analysis"
    if state["status"] == "sequence_rejected":
        return "sequence_failed"
    age = now-datetime.fromisoformat(state["updated_utc"]).timestamp()
    if not live and age > 120:
        return "sequence_unexpected_exit"
    return "waiting"


def save(state):
    state["updated_utc"] = datetime.now(timezone.utc).isoformat()
    temporary = RECORD.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(state, indent=2)+"\n", encoding="utf-8")
    os.replace(temporary, RECORD)


def worker(args):
    report = dict(status="waiting", worker_pid=os.getpid(), thread_id=args.thread,
        sequence_pid=args.sequence_pid, sequence_created=args.sequence_created,
        script_sha256=sha(Path(__file__)), analysis_sha256=sha(ANALYSIS),
        physical_accuracy_accepted=False, solver_launched=False,
        started_utc=datetime.now(timezone.utc).isoformat())
    save(report)
    unreadable_since = None
    while True:
        try:
            state = read(SEQUENCE)
            if state["worker_pid"] != args.sequence_pid:
                raise ValueError("Sequence status belongs to a different worker")
            try:
                owner = psutil.Process(args.sequence_pid)
                live = owner.is_running() and abs(owner.create_time()-args.sequence_created) < .001
            except psutil.Error:
                live = False  # The sequence can finish between launch and worker startup.
            event = decision(state, live, time.time())
            unreadable_since = None
            report.update(event=event, sequence_stage=state["stage"],
                          sequence_status=state["status"], stop_reason=state.get("stop_reason"))
        except (OSError, ValueError, KeyError, psutil.Error) as error:
            unreadable_since = unreadable_since or time.time()
            event = "sequence_status_unreadable" if time.time()-unreadable_since >= 180 else "waiting"
            report.update(event=event, read_error=str(error))
        save(report)
        if event != "waiting": break
        time.sleep(30)
    if event == "completed_pending_analysis":
        report["status"] = "analysing_retained_outputs";save(report)
        try:
            if sha(ANALYSIS) != report["analysis_sha256"]:
                raise RuntimeError("Analysis script changed since follow-up was armed")
            with (TESTS/"logs/hg_merge_full_r1.analysis.log").open("x", encoding="utf-8") as stream:
                analysis = subprocess.Popen([sys.executable, "-B", str(ANALYSIS)],
                    cwd=TESTS.parent, stdin=subprocess.DEVNULL, stdout=stream,
                    stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
                report["analysis_pid"] = analysis.pid;save(report)
                while analysis.poll() is None:
                    try: analysis.wait(timeout=20)
                    except subprocess.TimeoutExpired: save(report)
            report["analysis_exit_code"] = analysis.returncode
            report["analysis_check"] = str(TESTS/"logs/hg_merge_full_r1.check.json")
        except (OSError, ValueError, RuntimeError) as error:
            report["analysis_error"] = str(error)
    message = (
        "Automatic completion follow-up and staged continuation authorized by the user's 2026-10-12 request; "
        "not a new human observation. This is the hg_merge sequence, NOT the old traction sequence. "
        f"Detected event: {event}. Read {SEQUENCE} and {RECORD} before making claims. "
        f"Read the authorized execution plan {TESTS/'notes/hg_release_plan.md'} before proceeding. "
        "Do not start duplicate solvers, rearm this same one-shot follow-up, or overwrite retained outputs. "
        "Preserve the completed baseline while reviewing it; production edits, formal input updates and "
        "Git commit/push are authorized only at their later gated stages in that plan. "
        "If completed, verify hg_merge_2tv run/completion "
        "manifests, input/output hashes, native IDs, actual final time ~72.88429 s, and the 15 s/half-dt gate. "
        f"Read {TESTS/'logs/hg_merge_full_r1.check.json'} and its analysis log; if analysis failed, diagnose and "
        "repair only the new analysis artifacts without rerunning the physical solver. Inspect all three "
        "hg_merge_full_r1 PNGs under tests/figures and give the user a Chinese quantified pressure, settlement, "
        "stress/staggering and late-dissipation comparison. NoHG retained control stops at 55.8 s; old "
        "stress_full_r1_float/dt1/dt05 differ in load/gradient and are not HG-only controls. Include each "
        "production source modification and purposes vs hg_merge_base, builds, 0-ULP merge regression, and "
        "the isolated loading benchmark 1.652x (39.47% region reduction, not whole-run speedup). "
        "State limitations: CPU elastic small rotation, xi=.1, no exact HG restart/GPU support, only 15 s "
        "half-dt validation. Never equate solver completion with physical acceptance. If failed or exited "
        "unexpectedly, inspect and promptly explain the exact reason and actual time; do not call it a "
        "completed 2Tv run. The user explicitly requested automatic continuation, not just a completion "
        "report. Report the full-cycle conclusion proactively. If the physical acceptance gates pass, "
        "continue in the same work sequence without asking for another approval: benchmark and validate "
        "CPU HG efficiency changes (retain the accepted baseline if optimization fails), synchronize and "
        "validate GPU double stress/band loading/HG including full 2Tv and CPU/GPU timing, commit and push "
        "only verified task changes, prepare formal k=1e-3/1e-4/1e-5 XML/BAT and complete their 2Tv plots, "
        "then dependency-aware tests cleanup and a final results commit/push. Synchronize XML parameter "
        "documentation and report each changed location. If an acceptance check fails, report it and "
        "continue authorized diagnosis without bypassing gates or publishing failed results. Pause only "
        "for a genuine need for user authority or an external blocker; explain it proactively. During "
        "later long runs use a single verified completion mechanism for the active stage, preserving "
        "this same conversation; do not finish a stage with only an offer to continue or wait for the "
        "user to ask for progress. This notifier itself queues exactly once and does not run solvers."
    )
    report.update(status="queueing_terminal_followup", message=message);save(report)
    try:
        queued = subprocess.run([args.codex, "queue", "--thread", args.thread, "--message", message],
            cwd=TESTS.parent, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        report.update(status="queued_for_review" if queued.returncode == 0 else "queue_failed",
                      queue_exit_code=queued.returncode, queue_reply=queued.stdout)
    except (OSError, subprocess.TimeoutExpired) as error:
        # A timed-out request might already have queued; never blindly resend.
        report.update(status="queue_delivery_uncertain", queue_error=str(error))
    save(report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--launch", action="store_true")
    modes.add_argument("--worker", action="store_true")
    modes.add_argument("--self-test", action="store_true")
    parser.add_argument("--thread");parser.add_argument("--codex")
    parser.add_argument("--sequence-pid", type=int);parser.add_argument("--sequence-created", type=float)
    args = parser.parse_args()
    if args.self_test:
        for status, live, age, expected in (
            ("running_not_accepted", True, 300, "waiting"),
            ("running_not_accepted", False, 30, "waiting"),
            ("running_not_accepted", False, 300, "sequence_unexpected_exit"),
            ("sequence_rejected", False, 0, "sequence_failed"),
            ("completed_2tv_pending_full_physical_review", True, 0, "completed_pending_analysis")):
            state = dict(status=status, updated_utc=datetime.fromtimestamp(1000-age, timezone.utc).isoformat())
            assert decision(state, live, 1000) == expected
        print("PASS: five terminal decisions; no files written/messages queued/solvers launched.")
        return
    if not args.thread or not args.codex or not Path(args.codex).is_file():
        raise ValueError("Existing thread and installed Codex executable are required")
    if args.worker: worker(args);return
    state = read(SEQUENCE);owner = psutil.Process(state["worker_pid"])
    command = owner.cmdline()
    if state["status"] != "running_not_accepted" or "--worker" not in command or not any(
            Path(item).name == "hg_merge_sequence.py" for item in command):
        raise RuntimeError("Expected the already-running hg_merge sequence worker")
    lock = TESTS/"logs/hg_merge_followup.lock"
    if RECORD.exists() or lock.exists():
        raise RuntimeError("Refusing duplicate follow-up/rearming")
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(args.thread+"\n")
    with (TESTS/"logs/hg_merge_followup.worker.log").open("x", encoding="utf-8") as stream:
        process = subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()), "--worker",
            "--thread", args.thread, "--codex", args.codex, "--sequence-pid", str(owner.pid),
            "--sequence-created", repr(owner.create_time())], cwd=TESTS.parent, stdin=subprocess.DEVNULL,
            stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    print(json.dumps(dict(status="followup_started", pid=process.pid, record=str(RECORD), solver_launched=False)))


if __name__ == "__main__":
    main()
