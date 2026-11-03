"""One notification for the fixed current CPU half owner; no computation runner."""
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
TAG = "upl_hg_column_ReleaseCPU_half_r1"
NAME = "upl_hg_column_half_followup_r1"
ROOT_THREAD = "01a07683-bc64-7463-8db7-9ee6243967d8"
OWNER_PID = 52308
OWNER_CREATED_UTC = "2026-11-03T06:49:30.5392510Z"
START = T / "logs" / (TAG + ".start.json")
RUN = T / "logs" / (TAG + ".run.json")
CALL = T / "logs" / (TAG + ".call.json")
NOTE = T / "notes" / (NAME + ".json")
LOCK = T / "logs" / (NAME + ".lock.json")
STATUS = T / "logs" / (NAME + ".status.json")
WORKER_LOG = T / "logs" / (NAME + ".worker.log")
TERMINAL = T / "logs" / (NAME + ".terminal.json")
ATTEMPT = T / "logs" / (NAME + ".queue_attempt.json")
RESULT = T / "logs" / (NAME + ".queue_result.json")
STATUS_TEMP = T / "logs" / (NAME + ".status.json.tmp")
START_SHA256 = "aa9191c599daad0deb115dff9e4f6a68c8a621924ed5bdf46bb24c0364bda882"
START_BYTES = 551831


def need(ok, why):
    if not ok:
        raise ValueError(why)


def utc():
    return datetime.now(timezone.utc).isoformat()


def epoch(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def entry(path):
    path = Path(path).resolve(strict=True)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest.hexdigest())


def verify(expected):
    actual = entry(expected["path"])
    need(actual == expected, "Immutable artifact changed: " + expected["path"])
    return Path(expected["path"])


def fresh(paths):
    need(all(not p.exists() for p in paths), "Existing follow-up artifact/lock protected; never rearm or restart")


def seal(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def save_status(state):
    if STATUS.exists():
        old = read(STATUS)
        need(old["stage"] == NAME and old["worker_pid"] == state["worker_pid"] and
             old["lock_sha256"] == state["lock_sha256"], "Status belongs to another watcher")
    state["updated_utc"] = utc()
    seal(STATUS_TEMP, state)
    os.replace(STATUS_TEMP, STATUS)


def expected_arguments():
    return ["-cpu", "-ompthreads:8", "-stable", "-mdbc_freeslip",
            str(T / "outputs/upl_hg_column_seed_r1/upl_hg_column_half_r1"),
            str(T / "outputs" / TAG), "-dirdataout", "data", "-svres", "-nsteps:524288"]


def validate_start():
    identity = entry(START)
    need(identity["bytes"] == START_BYTES and identity["sha256"] == START_SHA256,
         "This notifier is pinned to the original current half start, not a replacement run")
    start = read(START)
    expected = dict(stage="upl_hg_column_start_r1", tag=TAG, configuration="ReleaseCPU", window="half",
                    owner_pid=OWNER_PID, owner_creation_utc=OWNER_CREATED_UTC, physical_acceptance=False)
    need(all(start.get(k) == v for k, v in expected.items()), "Start owner/tag/schema differs")
    need(Path(start["owner_script"]["path"]).resolve() == (T / "support/upl_hg_column_run_r2.ps1").resolve(),
         "Actual current half owner must be run_r2")
    need(Path(start["program"]["path"]).resolve() ==
         (T / "outputs/upl_hg_column_ReleaseCPU_r1/DualSPHysics5.2CPU_win64.exe").resolve(),
         "Current isolated CPU program differs")
    job = start["job"]
    expected_job = dict(tag=TAG, configuration="ReleaseCPU", window="half", input_variant="half",
                        threads=8, dt_s=2.0 ** -20, end_s=.5, steps=524288, expected_samples=1469,
                        event_completed_step=10486, post_open_frames=1265,
                        expected_native_total_arrays=22, expected_total_native_count=1040)
    need(all(job.get(k) == v for k, v in expected_job.items()) and
         start["arguments"] == job["arguments"] == expected_arguments() and
         job["output_directory"] == str(T / "outputs" / TAG), "Current half job/program arguments differ")
    clock = job["saved_clock_table"]
    need(len(clock) == 1469 and clock[0]["completed_steps"] == 0 and clock[-1]["completed_steps"] == 524288,
         "Current half declared schedule differs")
    immutable = [identity]
    for key in ("owner_script", "program", "input_manifest", "source_build", "admission"):
        verify(start[key])
        immutable.append(start[key])
    return start, identity, immutable


def option(command, key):
    matches = [i for i, value in enumerate(command) if value.casefold() == key.casefold()]
    need(len(matches) == 1 and matches[0] + 1 < len(command), "Unique owner command option required: " + key)
    return command[matches[0] + 1]


def owner_identity(start):
    owner = psutil.Process(OWNER_PID)
    need(owner.is_running() and abs(owner.create_time() - epoch(OWNER_CREATED_UTC)) <= .002,
         "Fixed current half owner PID/creation differs")
    command, cwd = owner.cmdline(), Path(owner.cwd()).resolve()
    def resolved(value):
        path = Path(value)
        return (path if path.is_absolute() else cwd / path).resolve()
    need(resolved(option(command, "-File")) == Path(start["owner_script"]["path"]).resolve() and
         option(command, "-Configuration") == "ReleaseCPU" and option(command, "-Window") == "half" and
         resolved(option(command, "-Admission")) == Path(start["admission"]["path"]).resolve() and
         sum(value.casefold() == "-executionauthorized" for value in command) == 1,
         "Live owner command line is not the authorized current CPU half action")
    return dict(pid=owner.pid, created_epoch=owner.create_time(), command=command, cwd=str(cwd), exe=owner.exe())


def owner_state(frozen):
    try:
        owner = psutil.Process(OWNER_PID)
        if not owner.is_running() or owner.status() == psutil.STATUS_ZOMBIE:
            return "dead"
        if abs(owner.create_time() - frozen["created_epoch"]) > .002:
            return "identity_changed"
        if owner.cmdline() != frozen["command"] or str(Path(owner.cwd()).resolve()) != frozen["cwd"] or owner.exe() != frozen["exe"]:
            return "identity_changed"
        return "live"
    except psutil.NoSuchProcess:
        return "dead"
    except psutil.AccessDenied:
        return "unobservable"  # Missing observation is never evidence of owner exit.


def sealed_run(start, start_entry):
    before = entry(RUN)
    run = read(RUN)
    need(entry(RUN) == before, "Run receipt changed while being read")
    need(run.get("stage") == "upl_hg_column_run_r2" and run.get("tag") == TAG and
         run.get("configuration") == "ReleaseCPU" and run.get("window") == "half" and
         run.get("backend") == "CPU" and type(run.get("passed")) is bool and
         run.get("physical_acceptance") is False and run.get("start_record") == start_entry and
         run.get("program") == start["program"] and run.get("arguments") == start["arguments"] and
         run.get("source_build") == start["source_build"] and run.get("input_manifest") == start["input_manifest"] and
         run.get("admission") == start["admission"], "Sealed Run belongs to a changed owner/tag/program/job")
    need(all(run["job"].get(k) == start["job"][k] for k in
             ("tag", "configuration", "window", "input_variant", "threads", "steps", "expected_samples", "arguments")),
         "Sealed Run changed the fixed half job")
    need(Path(run["call"]["path"]).resolve() == CALL.resolve(), "Run points to another solver call")
    verify(run["call"])
    call = read(CALL)
    need(call.get("tag") == TAG and call.get("configuration") == "ReleaseCPU" and call.get("window") == "half" and
         call.get("program") == call.get("target_program") == start["program"] and
         call.get("arguments") == call.get("target_arguments") == start["arguments"] and
         call.get("start_record") == start_entry and call.get("direct_native_call") is True and
         call.get("actual_solver_call") is True and call.get("public_project_main") is True and
         call.get("fixture_or_Run_override") is False, "Owned call identity differs from the fixed current half run")
    if run["passed"]:
        need(call.get("owned_call_exited") and call.get("typed_LASTEXITCODE_captured_immediately") and
             type(call.get("exit_code")) is int and call["exit_code"] == 0 and not call.get("invocation_failure") and
             run.get("bindings_unchanged") and run.get("steps") == 524288 and run.get("native_frames") == 1469,
             "Passed half Run lacks its original typed-exit/step/frame/binding guards")
    artifacts = [before, run["call"]]
    for item in (call.get("log"), run.get("run_out")):
        if item:
            verify(item)
            artifacts.append(item)
    return dict(event="half_run_passed" if run["passed"] else "half_run_failed",
                run_receipt=before, call_receipt=run["call"], passed=run["passed"],
                owned_exit_code=call.get("exit_code"), failure=run.get("failure"),
                reported_steps=run.get("steps"), reported_native_frames=run.get("native_frames"),
                physical_acceptance=False, native_decoding_or_physical_review_performed_by_notifier=False), artifacts


def message(event):
    return (
        "这是用户已授权的同一线程自动续办提醒，不是新增的人类观察。当前阶段是已经在运行的 CPU HG xi=.1 独立half "
        + TAG + "，通知事件：" + event + "。先读取并核验 " + str(TERMINAL) + "、" + str(ATTEMPT)
        + " 及其全部预期/实测冻结哈希，再检查原始 half.start/call/run 所有权、程序/输入/输出绑定、原生IDs和实际时间。"
        "不得仅凭 call、进程退出或本提醒宣称完成；正常退出也不等于物理验收。若 run 失败、绑定或owner改变，或owner消失"
        "但缺少有效最终run，保留证据，报告确切状态和已观测时间，继续已授权诊断，不重复求解、不覆盖输出。"
        "若half有效run已完成，先检查half .native_r2.json、读取器call/日志/完成记录和当前读取器进程；"
        "解码正在运行或已有完成记录时不得重复启动。只有确认尚未解码且没有活动/既有读取器输出时，才运行一次已有 "
        "tests/support/upl_hg_column_native_run_r2.ps1 -Configuration ReleaseCPU -Window half -ExecutionAuthorized。"
        "已有失败或部分解码则诊断保留证据，禁止自动覆盖、重跑求解器或重复解码。"
        "仅在coarse和half各自原始native收据均通过后，先检查是否已经有pair审查/活动分析；未执行时才运行一次 "
        "D:/anaconda3/python.exe -B tests/support/upl_hg_column_full_review_r1.py --phase pair --execution-authorized。"
        "先完整阅读该审查脚本和note，已有结果则核验并使用，不重复运行。"
        "必须检查所有1469个实际配对时刻：孔压RMS<=5Pa、每个材料ID的XYZ位移差最大值<=.005mm、实际时钟差<=1e-14s，"
        "以及两个full结果各自全部五个二进制导出的458状态原始记录前缀逐字节一致；clock及signed dterror全部字节均包含，"
        "不得掩盖初始或非初始有符号诊断、删掉记录或放宽任何原始IDs/22数组/ledger/排水/HG门槛。"
        "比较孔压、固定初始材料顶部/底部沉降、总应力和交替X列Uz模态，HG0是描述性不同算子对照，不是half误差。"
        "本次0.5s独立half通过也不能证明旧1.5s以后模态已解决；禁止自动扩展mid、完整固结或正式工况。"
        "先查看当前独立GPU component和清理任务的实际状态再继续授权工作，不沿用过时运行状态，不停止、不重启、不修改其依赖。"
        "coarse旧通知器已经投递过一次，禁止重新布防；本half通知器也只尝试一次队列投递。"
        "保护活动计算依赖、原始BI4/NBI4、重启链、哈希绑定程序/源码快照和正式图表CSV。"
        "请用中文主动汇报定量结果并继续已授权诊断，不等待用户追问进度。"
        "本通知器不运行求解器、读取器、离线分析、构建、Git、删除或压缩；禁止自动重发本提醒。"
    )


def worker(args):
    need(args.owner_pid == OWNER_PID and args.owner_created is not None and
         abs(args.owner_created - epoch(OWNER_CREATED_UTC)) <= .002, "Worker fixed owner arguments differ")
    lock_entry = entry(LOCK)
    need(lock_entry["sha256"] == args.lock_sha256, "Launch lock changed before worker startup")
    lock = read(LOCK)
    need(lock["thread"] == args.thread == ROOT_THREAD and lock["codex"] == args.codex and
         lock["owner"]["pid"] == OWNER_PID and lock["owner"]["created_epoch"] == args.owner_created,
         "Worker does not belong to its frozen launch")
    fresh([STATUS, STATUS_TEMP, TERMINAL, ATTEMPT, RESULT])
    for item in lock["immutable"]:
        verify(item)
    start, start_entry, _ = validate_start()
    report = dict(stage=NAME, status="waiting", worker_pid=os.getpid(), worker_created_epoch=psutil.Process().create_time(),
                  lock_sha256=lock_entry["sha256"], owner_pid=OWNER_PID, owner_created_epoch=args.owner_created,
                  thread=args.thread, started_utc=utc(), solver_or_decoder_or_analysis_or_build_launched=False,
                  queue_attempts=0, physical_acceptance=False)
    save_status(report)
    dead_since = None
    terminal = None
    terminal_inputs = []
    while terminal is None:
        poll_started = time.monotonic()
        try:
            need(entry(START) == start_entry, "Frozen start record changed during watch")
            state = owner_state(lock["owner"])
            report.update(owner_state=state, last_poll_utc=utc())
            if RUN.exists():
                try:
                    terminal, terminal_inputs = sealed_run(start, start_entry)
                except (json.JSONDecodeError, OSError) as error:
                    report["run_read_error"] = str(error)  # A writer can still be sealing the final JSON.
                except (ValueError, KeyError, TypeError) as error:
                    terminal = dict(event="half_run_receipt_rejected", failure=str(error), physical_acceptance=False)
                    if RUN.is_file():
                        terminal_inputs.append(entry(RUN))
            if terminal is None and state == "identity_changed":
                terminal = dict(event="fixed_owner_identity_changed", failure="PID creation/command/cwd/exe no longer match", physical_acceptance=False)
            if state == "dead":
                dead_since = dead_since or time.monotonic()
                report["owner_dead_observed_for_s"] = time.monotonic() - dead_since
                if terminal is None and time.monotonic() - dead_since > 120:
                    terminal = dict(event="owner_exited_without_valid_run_receipt", failure=report.get("run_read_error"),
                                    physical_acceptance=False, completed_window_claimed=False)
            else:
                dead_since = None
            save_status(report)
        except (OSError, ValueError, KeyError, psutil.Error) as error:
            terminal = dict(event="watch_binding_or_identity_rejected", failure=str(error), physical_acceptance=False)
        if terminal is None:
            time.sleep(max(0., 30. - (time.monotonic() - poll_started)))
    # Only consumed immutable artifacts are rehashed here. The continuation owns
    # raw output/native-ID/actual-clock checks; a call alone never triggers success.
    expected_inputs = lock["immutable"] + terminal_inputs + [lock_entry]
    observations = []
    mismatches = []
    for item in expected_inputs:
        observation = dict(expected=item, actual=None, unchanged=False, error=None)
        try:
            observation["actual"] = entry(item["path"])
            observation["unchanged"] = observation["actual"] == item
            if not observation["unchanged"]:
                observation["error"] = "Immutable artifact changed"
        except (OSError, ValueError) as error:
            observation["error"] = str(error)
        observations.append(observation)
        if not observation["unchanged"]:
            mismatches.append(observation)
    if mismatches:
        terminal.update(previous_event=terminal["event"], event="watch_final_binding_rejected",
                        reported_run_passed=terminal.get("passed"), passed=False,
                        failure="Frozen consumed artifact identities changed or became unreadable; inspect all mismatches",
                        completed_window_claimed=False, immutable_binding_mismatches=mismatches)
    terminal.update(stage=NAME, observed_utc=utc(), tag=TAG, owner=lock["owner"], thread=args.thread,
                    start_record=start_entry, inputs=expected_inputs,
                    immutable_hashes_reverified=not mismatches, immutable_hash_observations=observations,
                    raw_PART_hashes_or_native_physics_checked=False)
    seal(TERMINAL, terminal)
    text = message(terminal["event"])
    argv = [args.codex, "queue", "--thread", args.thread, "--message", text]
    attempt = dict(stage=NAME, utc=utc(), attempt=1, max_attempts=1, thread=args.thread,
                   terminal_report=terminal, terminal_file=entry(TERMINAL),
                   immutable_inputs=terminal["inputs"], immutable_hash_observations=observations,
                   arguments=argv, timeout_s=45,
                   timeout_may_have_delivered_no_resend=True, solver_or_analysis_invoked=False)
    seal(ATTEMPT, attempt)  # Immutable intent is sealed BEFORE the sole external queue call.
    report.update(status="queue_attempt_sealed", event=terminal["event"], queue_attempts=1,
                  terminal=entry(TERMINAL), queue_attempt=entry(ATTEMPT))
    save_status(report)
    outcome = dict(stage=NAME, utc=utc(), queue_attempt=entry(ATTEMPT), attempts=1, automatic_retry=False)
    try:
        queued = subprocess.run(argv, cwd=T.parent, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                                timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        outcome.update(status="queued" if queued.returncode == 0 else "queue_failed",
                       return_code=queued.returncode, output=queued.stdout)
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        outcome.update(status="queue_delivery_uncertain", return_code=None, output=output,
                       error=str(error), may_already_have_queued=True, do_not_resend=True)
    except OSError as error:
        outcome.update(status="queue_failed", return_code=None, output="", error=str(error), do_not_resend=True)
    seal(RESULT, outcome)
    report.update(status=outcome["status"], queue_result=entry(RESULT), ended_utc=utc())
    save_status(report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--launch", action="store_true")
    modes.add_argument("--worker", action="store_true")
    parser.add_argument("--thread", required=True)
    parser.add_argument("--codex", required=True)
    parser.add_argument("--owner-pid", type=int)
    parser.add_argument("--owner-created", type=float)
    parser.add_argument("--lock-sha256")
    args = parser.parse_args()
    need(args.thread == ROOT_THREAD, "Pass the explicit authorized root thread; never use an agent/environment thread")
    codex = Path(args.codex)
    need(codex.is_absolute() and codex.is_file(), "Existing literal absolute Codex executable path required")
    args.codex = str(codex.resolve())
    if args.worker:
        worker(args)
        return
    need(args.owner_pid is None and args.owner_created is None and args.lock_sha256 is None,
         "Launch derives the fixed owner from the pinned start, not caller-supplied replacements")
    fresh([LOCK, STATUS, STATUS_TEMP, WORKER_LOG, TERMINAL, ATTEMPT, RESULT])
    start, _, immutable = validate_start()
    owner = owner_identity(start)
    immutable += [entry(Path(__file__)), entry(NOTE), entry(sys.executable), entry(psutil.__file__), entry(args.codex)]
    for item in immutable:
        verify(item)
    seal(LOCK, dict(stage=NAME, tag=TAG, utc=utc(), thread=args.thread, codex=args.codex,
                    owner=owner, immutable=immutable, one_shot=True, rearm_or_restart_allowed=False,
                    solver_or_analysis_or_build_launched=False))
    lock_entry = entry(LOCK)
    argv = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", "--thread", args.thread,
            "--codex", args.codex, "--owner-pid", str(OWNER_PID), "--owner-created", repr(owner["created_epoch"]),
            "--lock-sha256", lock_entry["sha256"]]
    with WORKER_LOG.open("x", encoding="utf-8") as stream:
        process = subprocess.Popen(argv, cwd=T.parent, stdin=subprocess.DEVNULL, stdout=stream,
                                   stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    print(json.dumps(dict(status="one_followup_started", worker_pid=process.pid, owner_pid=OWNER_PID,
                          lock=lock_entry, status_file=str(STATUS), solver_or_decoder_launched=False)))


if __name__ == "__main__":
    main()
