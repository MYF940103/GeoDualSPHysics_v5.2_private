"""One notification for the exact started CPU1 full2Tv owner/child; no computation."""
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

T = Path(__file__).resolve().parents[1]
NAME, TAG = "upl_spr_av_2tv_followup_r1", "upl_spr_av_2tv_CPU1_r1"
THREAD = "01a07683-bc64-7463-8db7-9ee6243967d8"
STEPS, N = 38212357, 858
OUT = T / "outputs" / TAG
START, CALL, RUN = (T / "logs" / (TAG + s) for s in (".start.json", ".call.json", ".run.json"))
LOCK, STATUS, TEMP, LOG, TERMINAL, ATTEMPT, RESULT = (
    T / "logs" / (NAME + s) for s in (".lock.json", ".status.json", ".status.tmp", ".worker.log",
                                      ".terminal.json", ".queue_attempt.json", ".queue_result.json"))
PINS = {
    "support/upl_spr_av_2tv_run_r1.py": (15889, "44bbd5b05173e56aa2d6593fdac3059eaead55e451660cf7a77a65f404d65c3f"),
    "notes/upl_spr_av_2tv_run_r1.json": (4047, "9d07cc71cbe63041092ba9ef7de01dea0887c8c0de0c06e4afbd8c235d61ad20"),
}


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def utc():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def entry(path):
    path = Path(path).resolve(strict=True)
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def same(a, b):
    return (str(Path(a["path"]).resolve()).casefold(), a["bytes"], a["sha256"].lower()) == (
        str(Path(b["path"]).resolve()).casefold(), b["bytes"], b["sha256"].lower())


def verify(e):
    need(same(entry(e["path"]), e), "Immutable bytes changed: " + e["path"])


def metadata(path):
    s = Path(path).stat()
    return dict(bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def unique(values):
    result = {}
    for e in values:
        key = str(Path(e["path"]).resolve()).casefold()
        need(key not in result or same(result[key], e), "Conflicting immutable Entries")
        result[key] = e
    return list(result.values())


def fresh(paths):
    need(all(not p.exists() for p in paths), "Existing watcher artifacts protected; no rearm/retry")


def seal(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def status(report):
    if STATUS.exists():
        old = read(STATUS)
        need(old["worker_pid"] == report["worker_pid"] and old["lock_sha256"] == report["lock_sha256"],
             "Status belongs to another worker")
    report["updated_utc"] = utc()
    seal(TEMP, report)
    os.replace(TEMP, STATUS)


def start_record(e):
    verify(e)
    s = read(START)
    need(s.get("stage") == TAG + ".start" and s.get("direct_owner_no_scheduler") is True and
         s.get("actual_solver_identity_verified") is True and s.get("physical_acceptance") is False,
         "Actual fixed full owner start schema differs")
    j, child = s["job"], s["solver"]
    argv = ["-cpu", "-ompthreads:1", "-stable", "-mdbc_freeslip",
            str(T / "outputs/upl_spr_av_2tv_seed_r1/upl_spr_av_2tv_r1"), str(OUT),
            "-dirdataout", "data", "-svres", "-nsteps:38212357"]
    need(j["tag"] == TAG and j["window"] == "full2Tv" and j["threads"] == 1 and j["steps"] == STEPS and
         j["expected_samples"] == N and j["dt_s"] == 2.0 ** -19 and j["end_s"] == STEPS * 2.0 ** -19 and
         (j["master"], j["SPR"], j["Visco"], j["eta"], j["HG"], j["SlipMode"]) == (1, 1, .1, .04, .1, 3) and
         j["arguments"] == argv and j["output_directory"] == str(OUT) and
         len(j["saved_clock_table"]) == N and j["saved_clock_table"][-1]["completed_steps"] == STEPS and
         s["program"] == j["program"] and s["source_build"] == j["source_build"],
         "Actual full job/program/argv differs")
    need(all(s["solver_" + k] == child[k] for k in ("pid", "created_epoch", "command", "parent_pid")) and
         s["solver_executable"] == child["exe"] and
         child["parent_pid"] == s["owner_pid"] and child["command"][1:] == argv and
         Path(child["exe"]).resolve() == Path(s["program"]["path"]).resolve(),
         "Sealed child PID/creation/parent/executable/argv differs")
    expected = [e] + s["inputs"]
    for key in ("owner_script", "program", "source_input_manifest", "source_build", "admission"):
        need(any(same(s[key], x) for x in s["inputs"]), "Start omitted frozen prerequisite: " + key)
    for name, (size, sha) in PINS.items():
        item = dict(path=str(T / name), bytes=size, sha256=sha)
        expected.append(item)
        if name.endswith(".py"):
            need(same(s["owner_script"], item), "Exact frozen full owner source differs")
    return s, unique(expected)


def observed_identity(pid, created, exe, command, cwd=None, parent=None):
    p = psutil.Process(pid)
    need(p.is_running() and abs(p.create_time() - created) <= .002 and p.exe() == exe and p.cmdline() == command,
         "Actual PID/creation/executable/command differs")
    if cwd is not None:
        need(Path(p.cwd()).resolve() == Path(cwd).resolve(), "Actual solver working directory differs")
    if parent is not None:
        need(p.ppid() == parent, "Actual solver parent differs")
    return dict(pid=pid, created_epoch=created, exe=exe, command=command, cwd=p.cwd(), parent_pid=p.ppid())


def process_state(expected):
    try:
        p = psutil.Process(expected["pid"])
        if not p.is_running() or p.status() == psutil.STATUS_ZOMBIE:
            return dict(state="dead", actual=None)
        actual = dict(pid=p.pid, created_epoch=p.create_time(), exe=p.exe(), command=p.cmdline(), cwd=p.cwd(), parent_pid=p.ppid())
        ok = (abs(actual["created_epoch"] - expected["created_epoch"]) <= .002 and
              all(actual[k] == expected[k] for k in ("exe", "command", "parent_pid")) and
              Path(actual["cwd"]).resolve() == Path(expected["cwd"]).resolve())
        return dict(state="live" if ok else "identity_changed", actual=actual)
    except psutil.NoSuchProcess:
        return dict(state="dead", actual=None)
    except psutil.AccessDenied as error:
        return dict(state="unobservable", actual=None, error=str(error))


def actual_call(start, start_e):
    e = entry(CALL)
    c = read(CALL)
    need(same(entry(CALL), e), "Call changed while read")
    need(c.get("stage") == TAG + ".run_call" and c.get("direct_native_call") is True and c.get("shell") is False and
         c.get("actual_solver_call") is True and c.get("public_project_main") is True and
         c.get("fixture_or_Run_override") is False and c.get("physical_acceptance") is False and
         c["program"] == c["target_program"] == start["program"] and
         c["arguments"] == c["target_arguments"] == start["job"]["arguments"] and
         c["working_directory"] == start["working_directory"] and c["start_record"] == start_e and
         c["solver"] == start["solver"], "Original typed full call belongs to another target/start")
    need(c.get("typed_returncode_captured_immediately") is True and c.get("owned_call_exited") is True and
         type(c.get("exit_code")) is int, "Original integer native returncode missing")
    return e, c


def sealed_run(start, start_e):
    e = entry(RUN)
    r = read(RUN)
    need(same(entry(RUN), e), "Run changed while read")
    need(r.get("stage") == TAG + ".run" and r.get("tag") == TAG and type(r.get("passed")) is bool and
         r.get("backend") == "CPU" and r.get("configuration") == "ReleaseCPU" and r.get("window") == "full2Tv" and
         r.get("threads") == 1 and r.get("physical_acceptance") is False and
         r.get("native_decoder_invoked") is False and r.get("automatic_follow_up") is False and
         r.get("direct_owner_no_scheduler") is True and r.get("public_project_main") is True and
         r.get("fixture_or_Run_override") is False and r["job"] == start["job"] and
         r["start_record"] == start_e and r["solver"] == start["solver"] and
         all(r[k] == start[k] for k in ("program", "source_build", "source_input_manifest", "admission")) and
         all(r.get(k) is True for k in ("all22_native_fields_review_pending", "actual_native_clocks_review_pending",
                                      "measured458_prefix_review_pending")), "Terminal Run/start/scope differs")
    ce, c = actual_call(start, start_e)
    need(same(r["call"], ce), "Run points to another native call")
    if r["passed"]:
        need(c["exit_code"] == 0 and c["invocation_failure"] is None and not c["owner_exception_terminated_owned_child"] and
             r.get("bindings_unchanged") is True and r.get("independent_final_rehash_performed") is True and
             r["steps"] == STEPS and r["native_frames"] == N, "Passed run lacks original exit/steps/inputs")
    files = r.get("files", [])
    paths = {Path(x["path"]).resolve() for x in files}
    root = OUT.resolve()
    need(len(paths) == len(files) and all(p.is_relative_to(root) for p in paths) and
         paths == {p.resolve() for p in root.rglob("*") if p.is_file()}, "Sealed raw membership differs")
    if r["passed"]:
        need({p.name for p in paths if p.parent == root / "data" and p.name.startswith("Part_") and p.suffix == ".bi4"} ==
             {"Part_%04d.bi4" % i for i in range(N)}, "Passed raw858 PART sequence differs")
    artifacts = [e, ce] + r["inputs"] + files + ([c["log"]] if c.get("log") else [])
    return dict(event="full_run_passed" if r["passed"] else "full_run_failed", passed=r["passed"],
                owned_exit_code=c["exit_code"], failure=r.get("failure"), run_receipt=e, call_receipt=ce,
                raw_native_files_sealed=len(files), physical_acceptance=False), artifacts


def continuation(event):
    return ("这是用户已授权的同一线程 2Tv 工作流继续提醒，不是新的人工观测。事件：" + event + "；运行：" + TAG + "。"
        "先完整核验 " + str(TERMINAL) + " 和 queue_attempt 的实际哈希、start/call/run、owner 与 child 的 PID/创建时间、程序、argv、输入及源存档。"
        "出口0或本提醒不代表原生数据或物理验收。失败、PID复用、绑定变化或缺少有效run时保留证据，按实际原因继续已授权诊断，不盲目重跑。"
        "成功时先检查已有/活动的解码与分析任务，仅按已完整审阅的脚本独立解码一次；复核858帧、1040 IDs、22数组、真实时钟、857个非空signed dterror区间、ledger、固定样本和原HG门。"
        "逐帧检查5243步及以前排水接收数0、之后10，共654帧/6540接收检查；实际核对与已通过短算的前458帧所有导出及signed dterror，不从计划整数表推定逐位一致。"
        "按实际Tv完成孔压/材料沉降理论与剖面、总应力/交替列模式审阅，生成并检查图和CSV，明确有限Kw/斜坡/初态及旧Vel0参考的边界差异。"
        "保留原始BI4/NBI4、正式结果和冻结依赖；不自动增加half、mid、OFF全程或新后端扫描。请用中文主动定量汇报并继续原始u-pl工作流，无需等待用户追问。"
        "本watcher不运行求解、解码、分析、构建、Git或清理；通知最多一次，45秒超时可能已投递，禁止重发或重新布防。")


def worker(args):
    lock_e = entry(LOCK)
    need(lock_e["sha256"] == args.lock_sha256, "Frozen launch lock changed")
    lock = read(LOCK)
    need(lock["stage"] == NAME and lock["thread"] == args.thread == THREAD and lock["codex"] == args.codex, "Worker/lock differs")
    fresh([STATUS, TEMP, TERMINAL, ATTEMPT, RESULT])
    report = dict(stage=NAME, worker_pid=os.getpid(), worker_created_epoch=psutil.Process().create_time(),
                  lock_sha256=lock_e["sha256"], status="waiting", queue_attempts=0, physical_acceptance=False)
    status(report)
    terminal, extra, dead_since = None, [], None
    try:
        for e in lock["immutable"]:
            verify(e)
        start, _ = start_record(lock["start_record"])
        snapshots = {e["path"]: metadata(e["path"]) for e in lock["immutable"]}
    except (OSError, ValueError, KeyError, TypeError) as error:
        start, snapshots = lock["start"], {}
        terminal = dict(event="watch_startup_binding_rejected", failure=str(error), passed=False)
    while terminal is None:
        began = time.monotonic()
        try:
            for path, expected in snapshots.items():
                need(metadata(path) == expected, "Frozen polling metadata changed: " + path)
            observed = {role: process_state(lock[role]) for role in ("owner", "child")}
            states = {role: value["state"] for role, value in observed.items()}
            report.update(process_states=states, observed_processes=observed, last_poll_utc=utc())
            if "identity_changed" in states.values():
                terminal = dict(event="fixed_process_identity_changed", failure=str(states), passed=False)
            elif RUN.exists():
                try:
                    terminal, extra = sealed_run(start, lock["start_record"])
                except (json.JSONDecodeError, OSError) as error:
                    report["run_read_error"] = str(error)
                except (ValueError, KeyError, TypeError) as error:
                    terminal, extra = dict(event="full_run_receipt_rejected", passed=False, failure=str(error)), [entry(RUN)]
            elif CALL.exists():
                try:
                    ce, c = actual_call(start, lock["start_record"])
                    if c["exit_code"] != 0 or c["invocation_failure"] is not None or c["owner_exception_terminated_owned_child"]:
                        terminal = dict(event="full_native_call_failed", passed=False, call_receipt=ce,
                                        owned_exit_code=c["exit_code"], failure=c["invocation_failure"])
                        extra = [ce] + ([c["log"]] if c.get("log") else [])
                except (json.JSONDecodeError, OSError) as error:
                    report["call_read_error"] = str(error)
                except (ValueError, KeyError, TypeError) as error:
                    terminal, extra = dict(event="full_call_receipt_rejected", passed=False, failure=str(error)), [entry(CALL)]
            dead_since = (dead_since or time.monotonic()) if states["owner"] == "dead" else None
            if terminal is None and dead_since is not None and time.monotonic() - dead_since > 120:
                terminal = dict(event="owner_exited_without_valid_run", passed=False, completed_window_claimed=False,
                                failure=report.get("run_read_error") or report.get("call_read_error"))
            status(report)
        except (OSError, ValueError, KeyError, TypeError, psutil.Error) as error:
            terminal = dict(event="watch_binding_or_receipt_rejected", passed=False, failure=str(error))
        if terminal is None:
            time.sleep(max(0., 30. - (time.monotonic() - began)))
    observations, actuals, claims = [], {}, set()
    for e in lock["immutable"] + extra + [lock_e]:
        key = str(Path(e["path"]).resolve()).casefold()
        claim = (key, e["bytes"], e["sha256"].lower())
        if claim in claims:
            continue
        claims.add(claim)
        row = dict(expected=e, actual=None, unchanged=False, error=None)
        if key not in actuals:
            try:
                actuals[key] = (entry(e["path"]), None)
            except (OSError, ValueError) as error:
                actuals[key] = (None, str(error))
        row["actual"], row["error"] = actuals[key]
        row["unchanged"] = row["actual"] is not None and same(row["actual"], e)
        observations.append(row)
    mismatches = [r for r in observations if not r["unchanged"]]
    if mismatches:
        terminal.update(previous_event=terminal["event"], event="watch_final_binding_rejected", passed=False,
                        failure="Inspect expected/actual immutable hash mismatches")
    terminal.update(stage=NAME, tag=TAG, observed_utc=utc(), owner=lock["owner"], child=lock["child"],
        process_states=report.get("process_states"), observed_processes=report.get("observed_processes"),
        start_record=lock["start_record"], thread=args.thread,
        immutable_hash_observations=observations, immutable_hashes_reverified=not mismatches,
        startup_and_terminal_full_hash=True, active_poll_scope="size+mtime_ns only; no full raw output reads while active",
        decoded_native_fields_or_physics_checked=False, physical_acceptance=False)
    seal(TERMINAL, terminal)
    argv = [args.codex, "queue", "--thread", args.thread, "--message", continuation(terminal["event"])]
    seal(ATTEMPT, dict(stage=NAME, utc=utc(), attempt=1, max_attempts=1, terminal=entry(TERMINAL),
        arguments=argv, timeout_s=45, timeout_may_have_delivered_no_resend=True, physical_acceptance=False))
    report.update(status="queue_attempt_sealed", event=terminal["event"], queue_attempts=1, terminal=entry(TERMINAL))
    status(report)
    outcome = dict(stage=NAME, utc=utc(), attempt=entry(ATTEMPT), attempts=1, automatic_retry=False)
    try:
        c = subprocess.run(argv, cwd=T.parent, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        outcome.update(status="queued" if c.returncode == 0 else "queue_failed", return_code=c.returncode, output=c.stdout)
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ""
        outcome.update(status="queue_delivery_uncertain", output=output.decode("utf-8", "replace") if isinstance(output, bytes) else output,
                       error=str(error), may_already_have_queued=True, do_not_resend=True)
    except OSError as error:
        outcome.update(status="queue_failed", error=str(error), do_not_resend=True)
    seal(RESULT, outcome)
    report.update(status=outcome["status"], queue_result=entry(RESULT), ended_utc=utc())
    status(report)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    modes = p.add_mutually_exclusive_group(required=True)
    modes.add_argument("--launch", action="store_true")
    modes.add_argument("--worker", action="store_true")
    p.add_argument("--thread", required=True)
    p.add_argument("--codex", required=True)
    p.add_argument("--start-bytes", type=int)
    p.add_argument("--start-sha256")
    p.add_argument("--lock-sha256")
    args = p.parse_args()
    need(args.thread == THREAD and Path(args.codex).is_absolute() and Path(args.codex).is_file(),
         "Explicit same root thread and root-inspected literal Codex executable required")
    args.codex = str(Path(args.codex).resolve())
    if args.worker:
        worker(args)
        return
    need(args.start_bytes is not None and args.start_bytes > 0 and args.start_sha256 is not None and
         rehash_format(args.start_sha256) and args.lock_sha256 is None, "Root must pin actual start bytes/SHA256")
    fresh([LOCK, STATUS, TEMP, LOG, TERMINAL, ATTEMPT, RESULT])
    start_e = dict(path=str(START.resolve()), bytes=args.start_bytes, sha256=args.start_sha256)
    start, immutable = start_record(start_e)
    owner = observed_identity(start["owner_pid"], start["owner_created_epoch"], start["owner_executable"], start["owner_command"])
    resolve_arg = lambda value: (Path(value) if Path(value).is_absolute() else Path(owner["cwd"]) / value).resolve()
    command = owner["command"]
    need(sum(resolve_arg(a) == Path(start["owner_script"]["path"]).resolve() for a in command) == 1 and
         command.count("--execution-authorized") == command.count("--admission") == 1 and
         resolve_arg(command[command.index("--admission") + 1]) == Path(start["admission"]["path"]).resolve(),
         "Actual owner command/admission differs")
    c = start["solver"]
    child = observed_identity(c["pid"], c["created_epoch"], c["exe"], c["command"], start["working_directory"], owner["pid"])
    immutable = unique(immutable + [entry(__file__), entry(T / "notes" / (NAME + ".json")),
                                   entry(sys.executable), entry(psutil.__file__), entry(args.codex)])
    for e in immutable:
        verify(e)
    seal(LOCK, dict(stage=NAME, tag=TAG, utc=utc(), thread=args.thread, codex=args.codex, start_record=start_e,
                    start=start, owner=owner, child=child, immutable=immutable, one_shot=True, rearm_allowed=False))
    lock_e = entry(LOCK)
    argv = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", "--thread", args.thread,
            "--codex", args.codex, "--lock-sha256", lock_e["sha256"]]
    with LOG.open("x", encoding="utf-8") as stream:
        childwatch = subprocess.Popen(argv, cwd=T.parent, stdin=subprocess.DEVNULL, stdout=stream,
                                     stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    print(json.dumps(dict(status="one_followup_started", worker_pid=childwatch.pid, owner=owner, solver=child, lock=lock_e)))


def rehash_format(value):
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


if __name__ == "__main__":
    main()
