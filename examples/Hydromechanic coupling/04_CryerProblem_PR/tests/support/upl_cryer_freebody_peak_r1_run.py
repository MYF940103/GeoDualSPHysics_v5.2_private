"""One fresh GPU peak owner and one terminal same-thread queue attempt; no watcher."""
from pathlib import Path
from datetime import datetime, timezone
import csv, json, os, re, subprocess, sys
import psutil

T = Path(__file__).resolve().parents[1]
C, L = T.parent, T / "logs"
TAG, INPUT = "upl_cryer_freebody_peak_GPU_r1", "upl_cryer_freebody_peak_r1"
PREFIX, OUT = T / "outputs" / (INPUT + "_seed") / INPUT, T / "outputs" / TAG
THREAD = "01a07683-bc64-7463-8db7-9ee6243967d8"
CODEX = Path("c:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1021.22027-win32-x64/bin/windows-x86_64/codex.exe")
P = {key: L / (TAG + suffix) for key, suffix in (("start", ".start.json"), ("call", ".call.json"),
     ("run", ".run.json"), ("log", ".log"), ("attempt", ".queue_attempt.json"), ("queue", ".queue_result.json"))}

def utc(): return datetime.now(timezone.utc).isoformat()
def stat(path):
    path = Path(path).resolve(); s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)
def save(path, value):
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n"); f.flush(); os.fsync(f.fileno())
def read(path): return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def identity(process):
    return dict(pid=process.pid, parent_pid=process.ppid(), creation_time=process.create_time(), exe=process.exe(), command=process.cmdline(), cwd=process.cwd())

def queue_once(code, passed):
    message = ("这是用户已授权的同一线程 Cryer u-pl 开发续接，不是新的人类观察。GPU 粗步峰值窗口已终止；原始退出码=" + str(code) +
        "，Run 元数据正常完成=" + str(passed) + "。先读取 " + str(P["start"]) + "、" + str(P["call"]) + "、" + str(P["run"]) +
        "，核对原始 PID/创建时间/exe/argv、源码/输入/程序 stat；只有身份不明确时才核验实际 hash，不扫旧源码/对象/原始 BI4 SHA。" +
        "退出0/Run.csv/Run.out正常只表示待原生审查，不是物理或正式验收。先检查已有或活动 reader/新鲜分析，避免重复解码。" +
        "新读取器为tests/outputs/upl_cryer_public_native_DebugCPU_r2/reader.exe，构建收据同名，命令--read GPU DATA tests/configs/upl_cryer_freebody_peak_r1.clock.csv FRESHOUT；r1不支持577帧。" +
        "成功时继续已授权的577帧全部37181原生ID、22 typed数组、实际时钟/Step/dt、signed dterror<=1e-14、J/n/V/rho/k ledger及512个post-drain帧审查；" +
        "Part64为tD且仍pre-open，FS2/3零压仅t>tD；固定18材料ID r0/a=.05，不重选中心，不把FSNormal跨后端bit差当新门槛。" +
        "saved-J质量乘LoadAce是proxy，不能代替原力阶段.001检查。保留原生字段、峰值/相位/窗口局限和旧u-pw比较条件，不能宣称5Pa跨模型等价。" +
        "用实际tau=t-tD和原18材料点有限Kw参考，Mandel窗口仍为legacyTv>=.005；保留启动波动，不拟合半径/时间/荷载。报告采样峰值、连续/同时间采样理论峰及相位，RMS仅同一窗口可比。检查首69个common26与signed-clock记录对保留短窗的真实字节前缀，不伪造全部22原始数组bit证明。" +
        "失败时保留实际退出/日志和原样最后已保存Run.out行，不虚构未保存停止时间，不盲目重跑。只用当前这一新GPU粗步峰值任务，不额外半步/对照/正式长跑。" +
        "请用中文定量汇报并继续原授权开发。本直接owner是唯一完成机制：只queue一次，45秒超时可能已送达，禁止重发/重启owner/重挂通知。")
    argv = [str(CODEX), "queue", "--thread", THREAD, "--message", message]
    save(P["attempt"], dict(stage=TAG + ".queue_attempt", utc=utc(), attempt=1, max_attempts=1, arguments=argv,
         terminal_record=str(P["run"]), timeout_s=45, timeout_may_have_delivered_no_resend=True))
    outcome = dict(stage=TAG + ".queue_result", attempt=1, automatic_retry=False, do_not_resend=True)
    try:
        done = subprocess.run(argv, cwd=C, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
               text=True, encoding="utf-8", errors="replace", timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        outcome.update(status="queued" if done.returncode == 0 else "queue_failed", exit_code=done.returncode, output=done.stdout)
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""; outcome.update(status="queue_delivery_uncertain", error=str(exc), output=output.decode("utf-8", "replace") if isinstance(output, bytes) else output)
    except OSError as exc: outcome.update(status="queue_failed", error=str(exc))
    save(P["queue"], dict(**outcome, ended_utc=utc()))

def main():
    # Claim only this absent output directory. Collisions never write into an old owner's receipts.
    assert not OUT.exists() and not any(path.exists() for path in P.values()), "Existing run/notification protected; no restart"
    OUT.mkdir()
    owner, observed, child, code, started, failure = identity(psutil.Process()), {}, None, None, False, None
    common = dict(owner=owner, started_utc=utc()); build = None; row = {}; lines = []; changed = []
    def remember(path):
        item = stat(path); observed[item["path"]] = item; return item
    def seal_call():
        if child is not None and not P["call"].exists():
            save(P["call"], dict(stage=TAG + ".call", **common, exit_code=code, direct_exit_captured=type(code) is int, ended_utc=utc()))
    try:
        assert os.environ.get("CODEX_THREAD_ID") == THREAD and CODEX.is_file(), "Exact authorized thread/Codex CLI required"
        assert not any((p.info["name"] or "").lower().startswith("dualsphysics") for p in psutil.process_iter(["name"])), "Another solver is active"
        buildpath = L / "upl_cryer_freebody_r1_Release.build.json"; build = read(buildpath); remember(buildpath)
        assert build["stage"] == "upl_cryer_freebody_r1_Release" and build["passed"] and build["configuration"] == "Release" and build["exit_code"] == 0 and build["source_and_canonical_stats_unchanged"]
        program = build["program"]; assert stat(program["path"]) == {k: program[k] for k in ("path", "bytes", "mtime_ns")}, "Sealed program stat differs"
        for item in build["runtime"]:
            assert remember(item["path"]) == item, "Sealed runtime stat differs"
        sourcepath = Path(build["source_snapshot"]); source = read(sourcepath); remember(sourcepath)
        codefiles = [item for item in source["before"] if Path(item["path"]).parent == T.parents[3] / "src/source"]
        assert len(codefiles) == 8 and all(remember(item["path"]) == item for item in codefiles), "Current eight-file source stat differs from built snapshot"
        for path in (program["path"], str(PREFIX) + ".xml", str(PREFIX) + ".bi4", T / "configs" / (INPUT + "_Def.xml"),
                     T / "configs" / (INPUT + ".clock.csv"), Path(__file__), T / "notes/upl_cryer_freebody_peak_r1_run.json", CODEX): remember(path)
        with (T / "configs" / (INPUT + ".clock.csv")).open(newline="", encoding="utf-8-sig") as stream: ticks = list(csv.DictReader(stream))
        assert len(ticks) == 577 and all(int(r["part"]) == i and int(r["completed_step"]) == 128*i and int(r["saved_step"]) == max(0,128*i-1) and float(r["time_s"]) == 128*i*2.**-20 and float(r["dt_s"]) == 2.**-20 for i,r in enumerate(ticks)), "Peak input clock differs"
        argv = [str(program["path"]), "-gpu", "-stable", str(PREFIX), str(OUT), "-dirdataout", "data", "-svres", "-nsteps:73728"]
        common.update(program=program, arguments=argv[1:], command_line=subprocess.list2cmdline(argv), working_directory=str(C))
        with P["log"].open("xb") as stream:
            child = subprocess.Popen(argv, cwd=C, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
                                     creationflags=subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS)
            common["child"] = dict(pid=child.pid); actual = identity(psutil.Process(child.pid)); common["child"] = actual
            assert actual["parent_pid"] == owner["pid"] and Path(actual["exe"]).resolve() == Path(program["path"]).resolve() and actual["command"][1:] == argv[1:], "Actual owned solver identity differs"
            save(P["start"], dict(stage=TAG + ".start", **common, planned_steps=73728, planned_frames=577, planned_end_s=.0703125,
                 source_build=str(buildpath), observations=list(observed.values()), single_completion_mechanism="This direct owner waits and queues once; no watcher", fresh_SHA_scans=0))
            started = True; print(json.dumps(dict(event="owned_solver_started", child=actual)), flush=True)
            code = child.wait()
        seal_call()
    except Exception as exc:
        failure = type(exc).__name__ + ": " + str(exc)
        if child is not None and code is None: code = child.wait()
        seal_call()
    try:
        runout = OUT / "Run.out"
        if runout.is_file(): lines = runout.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        if (OUT / "Run.csv").is_file():
            with (OUT / "Run.csv").open(newline="", encoding="utf-8-sig") as stream: records = list(csv.DictReader(stream, delimiter=";"))
            assert len(records) == 1, "Run.csv requires one actual summary row"
            row = records[0]
        if failure is None:
            assert type(code) is int and code == 0 and int(row["Steps"]) == 73728 and int(row["PartFiles"]) == 577, "Original exit/Run.csv steps/frames failed"
            assert any(line.startswith("[Simulation finished") for line in lines) and "Finished execution (code=0)." in lines, "Normal Run.out completion missing"
    except Exception as exc: failure = failure or type(exc).__name__ + ": " + str(exc)
    for path, before in observed.items():
        try:
            if stat(path) != before: changed.append(path)
        except OSError as exc: changed.append(path + ": " + str(exc))
    if changed: failure = failure or "Source/input/program/runtime stat changed"
    passed = started and failure is None and code == 0
    save(P["run"], dict(stage=TAG + ".run", passed=passed, **common, actual_owned_exit=code, Run_csv=row, failure=failure,
         observed_last_saved_Run_out_line=next((line for line in reversed(lines) if re.match(r"^Part_\d+\s", line)), None),
         observations=list(observed.values()), changed_paths=changed, source_input_program_stats_unchanged=not changed,
         actual_native_577_frames_IDs_22arrays_clocks_ledger_and_512_postdrain_pending=True, decoder_executed=False,
         physical_acceptance=False, automatic_solver_followup=False, fresh_SHA_scans=0, original_call=str(P["call"]) if child is not None else None,
         genuine_owned_start_record_written=started, one_terminal_queue_planned=started, ended_utc=utc()))
    if started: queue_once(code, passed)
    return 0 if passed else 1

if __name__ == "__main__": sys.exit(main())
