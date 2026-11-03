"""One notification for the exact future larger-step full2Tv start; no computation."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import psutil

T = Path(__file__).resolve().parents[1]
NAME, TAG, THREAD = "upl_bigstep_full_followup_r1", "upl_bigstep_2tv_CPU1_r1", "01a07683-bc64-7463-8db7-9ee6243967d8"
STEPS, N, DT, END = 11661219, 1682, float("6.2501430511474609e-6"), 72.88428689946836
OUT = T / "outputs" / TAG
START, CALL, RUN = (T / "logs" / (TAG + s) for s in (".start.json", ".call.json", ".run.json"))
LOCK, STATUS, TEMP, LOG, TERMINAL, ATTEMPT, RESULT = (T / "logs" / (NAME + s) for s in
    (".lock.json", ".status.json", ".status.tmp", ".worker.log", ".terminal.json", ".queue_attempt.json", ".queue_result.json"))
PINS = {
    "support/upl_bigstep_followup_r1.py": (18644, "a4b1cc3db3ed077569e212214db2e51d919f1e5edc36b1d33155c7566b8c1f68"),
    "notes/upl_bigstep_followup_r1.json": (5443, "1f1677fc3e7784ec3fb7e7752651bb998bd2a12c133031cd63e9e601e7804c21"),
    "support/upl_bigstep_full_r1_run.py": (16765, "74c26315d254a99b6f4fdac62fb6c957c3d90fa18e2cde7601fb8fa15f5bf62f"),
    "notes/upl_bigstep_full_r1_run.json": (4808, "74e3a547627df8b5822386cc27f861c36599c58009daad7443703e1ef5b14aa1"),
    "support/upl_bigstep_full_r1_prepare.py": (14548, "0223aa1782b1391c53a47ae77da02c448b90730d0e044897dfa40e87b7f3a305"),
    "notes/upl_bigstep_full_r1_prepare.json": (4935, "7c691ce7e5629e18b200209a3efbe07839ce8c6264ac9874f556d6279110e134"),
}


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def definitions():
    sys.dont_write_bytecode = True
    path = T / "support/upl_bigstep_followup_r1.py"
    data = path.read_bytes()
    need((len(data), hashlib.sha256(data).hexdigest()) == PINS["support/upl_bigstep_followup_r1.py"], "Frozen generic watcher definitions changed")
    spec = importlib.util.spec_from_file_location("bigstep_full_frozen_watch_helpers", path)
    b = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(b)  # Only generic utilities()/observations(); never candidate start/call/run/status/worker/main.
    return b.utilities(), b


def status(u, report):
    if STATUS.exists():
        old = u.read(STATUS)
        need(old["worker_pid"] == report["worker_pid"] and old["lock_sha256"] == report["lock_sha256"], "Status owner changed")
    report["updated_utc"] = u.utc()
    u.seal(TEMP, report)
    os.replace(TEMP, STATUS)


def start_record(u, b, e):
    u.verify(e)
    s = u.read(START)
    need(s.get("stage") == TAG + ".start" and s.get("direct_owner_no_scheduler") is True and
         s.get("actual_solver_identity_verified") is True and s.get("physical_acceptance") is False, "Actual full start differs")
    j, c = s["job"], s["solver"]
    argv = ["-cpu", "-ompthreads:1", "-stable", "-mdbc_freeslip", str(T / "outputs/upl_bigstep_full_r1_seed" / TAG),
            str(OUT), "-dirdataout", "data", "-svres", "-nsteps:11661219"]
    need(j["tag"] == TAG and j["window"] == "candidate_full2Tv" and j["threads"] == 1 and j["steps"] == STEPS and
         j["expected_samples"] == N and j["dt_s"] == DT and j["end_s"] == END and j["event_completed_step"] == 1600 and
         j["runtime_TimeMax_s"] == 72.88428690075874 and j["nominal_2Tv_target_s"] == 51019 / 700 and
         j["post_open_frames"] == 1564 and j["post_open_drained_particle_checks_expected"] == 15640 and
         (j["master"], j["SPR"], j["Visco"], j["eta"], j["HG"], j["SlipMode"]) == (1, 1, .1, .04, .1, 3) and
         j["arguments"] == argv and j["output_directory"] == str(OUT) and len(j["saved_clock_table"]) == N and
         j["saved_clock_table"][-1]["completed_steps"] == STEPS and j["saved_clock_table"][-1]["time_s"] == END and
         j["saved_clock_table"][1291]["completed_steps"] == 320001 and s["clock"]["actual_scalar_end_s"] == END and
         s["clock"]["candidate_final_only_shared"] is False and s["program"] == j["program"] and
         s["source_build"] == j["source_build"] and s["planned_clock_CSV"] == j["planned_clock_CSV"], "Exact full job/program/clock/argv differs")
    need(all(s["solver_" + k] == c[k] for k in ("pid", "created_epoch", "command", "parent_pid")) and
         s["solver_executable"] == c["exe"] and c["parent_pid"] == s["owner_pid"] and c["command"][1:] == argv and
         Path(c["exe"]).resolve() == Path(s["program"]["path"]).resolve(), "Sealed full child identity differs")
    for item in [s[k] for k in ("owner_script", "program", "source_input_manifest", "source_build", "planned_clock_CSV", "admission")] + list(s["candidate_proofs"].values()):
        need(any(u.same(item, x) for x in s["inputs"]), "Start omitted immutable prerequisite: " + item["path"])
    pins = [dict(path=str(T / name), bytes=size, sha256=sha) for name, (size, sha) in PINS.items()]
    for name in ("support/upl_spr_av_2tv_followup_r1.py", "notes/upl_spr_av_2tv_followup_r1.json"):
        size, sha = b.PINS[name]
        pins.append(dict(path=str(T / name), bytes=size, sha256=sha))
    need(u.same(s["owner_script"], pins[2]), "Frozen actual full owner differs")
    m = u.read(s["source_input_manifest"]["path"])
    need(m.get("stage") == "upl_bigstep_full_r1_prepare" and m.get("passed") is True and m["jobs"] == [j] and
         m["candidate_proofs"] == s["candidate_proofs"], "Actual prepared full job/proofs differ")
    return s, u.unique([e] + s["inputs"] + pins)


def actual_call(u, start, start_e):
    e, c = u.entry(CALL), u.read(CALL)
    need(u.same(u.entry(CALL), e), "Call changed while read")
    need(c.get("stage") == TAG + ".run_call" and c.get("direct_native_call") is True and c.get("shell") is False and
         c.get("actual_solver_call") is True and c.get("public_project_main") is True and c.get("fixture_or_Run_override") is False and
         c.get("physical_acceptance") is False and c["program"] == c["target_program"] == start["program"] and
         c["arguments"] == c["target_arguments"] == start["job"]["arguments"] and c["working_directory"] == start["working_directory"] and
         c["start_record"] == start_e and c["solver"] == start["solver"], "Original full call/start/target differs")
    need(c.get("typed_returncode_captured_immediately") is True and c.get("owned_call_exited") is True and
         type(c.get("exit_code")) is int, "Original typed native returncode missing")
    return e, c


def sealed_run(u, start, start_e):
    e, r = u.entry(RUN), u.read(RUN)
    need(u.same(u.entry(RUN), e), "Run changed while read")
    need(r.get("stage") == TAG + ".run" and r.get("tag") == TAG and type(r.get("passed")) is bool and
         (r.get("backend"), r.get("configuration"), r.get("window"), r.get("threads")) == ("CPU", "ReleaseCPU", "candidate_full2Tv", 1) and
         all(r.get(k) is False for k in ("physical_acceptance", "native_decoder_invoked", "automatic_follow_up", "following_action_launched", "watcher_or_queue_invoked", "old_fine_or_control_liveness_required")) and
         r.get("direct_owner_no_scheduler") is True and r.get("public_project_main") is True and r.get("fixture_or_Run_override") is False and
         all(r.get(k) is True for k in ("all22_native_fields_review_pending", "actual_scalar_native_clocks_review_pending", "measured_common1291_prefix_review_pending", "signed_noninitial_dterror_and_full_physical_review_pending")) and
         r["job"] == start["job"] and r["start_record"] == start_e and r["solver"] == start["solver"] and
         all(r[k] == start[k] for k in ("program", "source_build", "source_input_manifest", "planned_clock_CSV", "clock", "admission", "candidate_proofs")), "Terminal full scope/start differs")
    ce, c = actual_call(u, start, start_e)
    need(u.same(r["call"], ce), "Run points to another call")
    if r["passed"]:
        need(c["exit_code"] == 0 and c["invocation_failure"] is None and not c["owner_exception_terminated_owned_child"] and
             r.get("bindings_unchanged") is True and r.get("independent_final_rehash_performed") is True and
             r["steps"] == STEPS and r["native_frames"] == N, "Passed full Run lacks actual exit/steps/unchanged inputs")
    files, root = r.get("files", []), OUT.resolve()
    paths = {Path(x["path"]).resolve() for x in files}
    need(len(paths) == len(files) and all(p.is_relative_to(root) for p in paths) and
         paths == {p.resolve() for p in root.rglob("*") if p.is_file()}, "Sealed full raw membership differs")
    if r["passed"]:
        need({p.name for p in paths if p.parent == root / "data" and p.name.startswith("Part_") and p.suffix == ".bi4"} ==
             {"Part_%04d.bi4" % i for i in range(N)}, "Passed1682 PART sequence differs")
    return dict(event="run_passed_pending_native_review" if r["passed"] else "failure", reason="full_run_sealed", passed=r["passed"],
        owned_exit_code=c["exit_code"], native_call_started_utc=c["started_utc"], native_call_ended_utc=c["ended_utc"], failure=r.get("failure"),
        run_receipt=e, call_receipt=ce, raw_native_files_sealed=len(files)), [e, ce] + r["inputs"] + files + ([c["log"]] if c.get("log") else [])


def continuation(event):
    return ("Authorized same-thread full2Tv continuation; event=" + event + "; run=" + TAG + ". "
        "Verify terminal/queue_attempt hashes and original actual start/call/run, owner+child creation/argv/program/source archives/admission. "
        "Failure: retain actual exit, console/log evidence, exact reported native time/reason and ownership; never invent an unsaved stop state or blindly rerun/requeue/rearm. "
        "On success first check current active work, then independently decode/analyze once with fully reviewed current scripts. Exit0 and this notification mean native/physical review is pending, not acceptance or a new solver launch. "
        "Review all 1682 frames, 1040 IDs, 22 typed arrays, 1681 signed nonempty dterror intervals, actual scalar clocks/end 72.88428689946836, ledger/fixed markers/HG and 1564 post-open frames/15640 true drained receivers; event 1600 is preopen. "
        "Measure the common first 1291 candidate records in all five binary exports including signed dterror; candidate forced final 320000 is not shared, full next frame is 320001. No count/header/stage rewrite or inferred bitproof. "
        "Complete full pressure/material settlement and J/n/rho profiles, total stress and all 100-layer alternating-X Uz/stress histories, PNGs/CSVs, and qualified unfitted theory/u-pw comparison at actual clocks. Disclose finite Kw, ramp/band loading and FreeSlip versus old formal Vel0 boundaries. "
        "Continue the original user-authorized development and report quantitatively in Chinese. No extra half/reference chain or automatic solver follows. This watcher calls no solver/decoder/analysis/build/stop/Git; one 45s notification attempt, timeout may already have delivered, never resend.")


def worker(u, b, args):
    lock_e = u.entry(LOCK)
    need(lock_e["sha256"] == args.lock_sha256, "Launch lock changed")
    lock = u.read(LOCK)
    need(lock["stage"] == NAME and lock["thread"] == args.thread == THREAD and lock["codex"] == args.codex, "Worker/lock differs")
    u.fresh([STATUS, TEMP, TERMINAL, ATTEMPT, RESULT])
    report = dict(stage=NAME, worker_pid=os.getpid(), worker_created_epoch=psutil.Process().create_time(), lock_sha256=lock_e["sha256"], status="waiting", queue_attempts=0)
    terminal, extra, dead_since, snapshots = None, [], None, {}
    try:
        for e in lock["immutable"]:
            u.verify(e)
        start, _ = start_record(u, b, lock["start_record"])
        snapshots = {e["path"]: u.metadata(e["path"]) for e in lock["immutable"]}
    except (OSError, ValueError, KeyError, TypeError) as error:
        start, terminal = lock["start"], dict(event="failure", reason="startup_binding_rejected", passed=False, failure=str(error))
    while terminal is None:
        began = time.monotonic()
        try:
            for path, expected in snapshots.items():
                need(u.metadata(path) == expected, "Immutable polling metadata changed: " + path)
            seen = {role: u.process_state(lock[role]) for role in ("owner", "child")}
            states = {role: row["state"] for role, row in seen.items()}
            report.update(process_states=states, observed_processes=seen, last_poll_utc=u.utc())
            if "identity_changed" in states.values():
                terminal = dict(event="failure", reason="process_identity_changed", passed=False, failure=str(states))
            else:
                try:
                    if RUN.exists():
                        extra = [u.entry(RUN)]
                        terminal, extra = sealed_run(u, start, lock["start_record"])
                    elif CALL.exists():
                        extra = [u.entry(CALL)]
                        ce, c = actual_call(u, start, lock["start_record"])
                        if c["exit_code"] != 0 or c["invocation_failure"] is not None or c["owner_exception_terminated_owned_child"]:
                            terminal = dict(event="failure", reason="native_call_failed", passed=False, owned_exit_code=c["exit_code"],
                                native_call_started_utc=c["started_utc"], native_call_ended_utc=c["ended_utc"], failure=c["invocation_failure"], call_receipt=ce)
                            extra = [ce] + ([c["log"]] if c.get("log") else [])
                except (json.JSONDecodeError, OSError) as error:
                    report["receipt_read_error"] = str(error)
            dead_since = (dead_since or time.monotonic()) if states["owner"] == "dead" else None
            if terminal is None and dead_since is not None and time.monotonic() - dead_since > 120:
                terminal = dict(event="failure", reason="owner_dead_without_valid_run", passed=False, failure=report.get("receipt_read_error"))
        except (OSError, ValueError, KeyError, TypeError, psutil.Error) as error:
            terminal = dict(event="failure", reason="binding_or_receipt_rejected", passed=False, failure=str(error))
        status(u, report)
        if terminal is None:
            time.sleep(max(0., 30. - (time.monotonic() - began)))
    rows = b.observations(u, lock["immutable"] + extra + [lock_e])
    unchanged = all(r["unchanged"] for r in rows)
    if not unchanged:
        terminal.update(previous_event=terminal["event"], event="failure", reason="terminal_hash_rejected", passed=False)
    terminal.update(stage=NAME, tag=TAG, observed_utc=u.utc(), owner=lock["owner"], child=lock["child"], start_record=lock["start_record"],
        process_states=report.get("process_states"), observed_processes=report.get("observed_processes"), thread=args.thread,
        immutable_hash_observations=rows, immutable_hashes_reverified=unchanged, startup_and_terminal_full_hash=True,
        active_poll_scope="size+mtime_ns and full owner/child identities; no growing raw reads", decoded_native_fields_or_physics_checked=False, physical_acceptance=False)
    u.seal(TERMINAL, terminal)
    argv = [args.codex, "queue", "--thread", args.thread, "--message", continuation(terminal["event"])]
    u.seal(ATTEMPT, dict(stage=NAME, utc=u.utc(), attempt=1, max_attempts=1, terminal=u.entry(TERMINAL), arguments=argv, timeout_s=45, timeout_may_have_delivered_no_resend=True))
    report.update(status="queue_attempt_sealed", event=terminal["event"], queue_attempts=1, terminal=u.entry(TERMINAL))
    status(u, report)
    outcome = dict(stage=NAME, utc=u.utc(), attempt=u.entry(ATTEMPT), attempts=1, automatic_retry=False)
    try:
        c = subprocess.run(argv, cwd=T.parent, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        code = c.returncode
        outcome.update(status="queued" if code == 0 else "queue_failed", return_code=code, output=c.stdout)
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ""
        outcome.update(status="queue_delivery_uncertain", output=output.decode("utf-8", "replace") if isinstance(output, bytes) else output, error=str(error), do_not_resend=True)
    except OSError as error:
        outcome.update(status="queue_failed", error=str(error), do_not_resend=True)
    u.seal(RESULT, outcome)
    report.update(status=outcome["status"], queue_result=u.entry(RESULT), ended_utc=u.utc())
    status(u, report)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    modes = p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--launch", action="store_true")
    modes.add_argument("--worker", action="store_true")
    for key in ("thread", "codex", "start-sha256", "lock-sha256"):
        p.add_argument("--" + key, required=key in ("thread", "codex"))
    p.add_argument("--start-bytes", type=int)
    args = p.parse_args()
    u, b = definitions()
    need(args.thread == THREAD and Path(args.codex).is_absolute() and Path(args.codex).is_file(), "Exact root thread/literal Codex executable required")
    args.codex = str(Path(args.codex).resolve())
    if args.worker:
        worker(u, b, args)
        return
    need(args.start_bytes is not None and args.start_bytes > 0 and args.start_sha256 is not None and u.rehash_format(args.start_sha256) and args.lock_sha256 is None, "Root must pin actual future full start bytes/SHA")
    u.fresh([LOCK, STATUS, TEMP, LOG, TERMINAL, ATTEMPT, RESULT])
    start_e = dict(path=str(START.resolve()), bytes=args.start_bytes, sha256=args.start_sha256)
    start, immutable = start_record(u, b, start_e)
    owner = u.observed_identity(start["owner_pid"], start["owner_created_epoch"], start["owner_executable"], start["owner_command"])
    command = owner["command"]
    resolve = lambda a: (Path(a) if Path(a).is_absolute() else Path(owner["cwd"]) / a).resolve()
    need(sum(resolve(a) == Path(start["owner_script"]["path"]).resolve() for a in command) == 1 and
         command.count("--execution-authorized") == command.count("--admission") == 1 and
         resolve(command[command.index("--admission") + 1]) == Path(start["admission"]["path"]).resolve(), "Actual full owner command/admission differs")
    c = start["solver"]
    child = u.observed_identity(c["pid"], c["created_epoch"], c["exe"], c["command"], start["working_directory"], owner["pid"])
    immutable = u.unique(immutable + [u.entry(__file__), u.entry(T / "notes" / (NAME + ".json")), u.entry(sys.executable), u.entry(psutil.__file__), u.entry(args.codex)])
    for e in immutable:
        u.verify(e)
    u.seal(LOCK, dict(stage=NAME, tag=TAG, utc=u.utc(), thread=args.thread, codex=args.codex, start_record=start_e, start=start,
        owner=owner, child=child, immutable=immutable, one_shot=True, rearm_allowed=False))
    lock_e = u.entry(LOCK)
    argv = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", "--thread", args.thread, "--codex", args.codex, "--lock-sha256", lock_e["sha256"]]
    with LOG.open("x", encoding="utf-8") as stream:
        watch = subprocess.Popen(argv, cwd=T.parent, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    print(json.dumps(dict(status="one_followup_started", worker_pid=watch.pid, owner=owner, solver=child, lock=lock_e)))


if __name__ == "__main__":
    main()
