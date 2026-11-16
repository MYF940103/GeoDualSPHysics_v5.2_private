"""One independently admitted fresh B GPU full-2Tv run; no decoder or chaining."""
from __future__ import annotations
import argparse
import csv
import math
from pathlib import Path
import re
import os
import subprocess
import xml.etree.ElementTree as ET
import upl_tpi_gpu_run_r3 as old

c, T, L = old.c, old.T, old.L
TAG = "upl_tpi_gpu_Release_B_full2tv_r1"
STAGE = "upl_tpi_gpu_full2tv_run_r1"
NOTE = T / "notes" / (STAGE + ".md")
PREP = L / "upl_tpi_gpu_full2tv_r1.prepare.json"
BUILD = L / "upl_tpi_gpu_full2tv_Release_r1.build.json"
OLD_A_RUN = L / "upl_bigstep_2tv_CPU1_r1.run.json"
OLD_A_PLAN = L / "upl_bigstep_full_r1.clock.csv"
B_REVIEW = L / "upl_tpi_gpu_Release_B_startup015_r1.native_review_r5.json"
SCIENCE = T / "figures/upl_tpi_gpu_startup_review_r2.metrics.json"
STEPS, FRAMES, POST = 11661219, 1682, 1564
DT, END, CAP = 6.250143051147461e-6, 72.88428689946836, 72.88428690075874
ROOT_THREAD = "01a07683-bc64-7463-8db7-9ee6243967d8"
C08_LOGS = T.parent.parent / "08_LianSaturatedColumnCollapse_u_pl/tests/logs"
QUEUE_PROOF_ATTEMPT = C08_LOGS / "c08_h18_hg_psi2p5_full3_r1.queue_attempt.json"
QUEUE_PROOF_RESULT = C08_LOGS / "c08_h18_hg_psi2p5_full3_r1.queue_result.json"


class Admission(c.Admission):
    def __init__(self, path):
        self.entry = c.stat(path); self.data = c.read(path)
        c.need(self.data.get("stage") == STAGE + ".run_admission" and self.data.get("passed") is True and
               self.data.get("one_job_only") is True, "One independently reviewed fresh-B full-run admission required")
        self.frozen = {str(Path(x["path"]).resolve()): x for x in self.data["inputs"]}; self.consumed = {}
        c.need(len(self.frozen) == len(self.data["inputs"]), "Duplicate frozen input")


def notification_profile(ad, args):
    if not args.notify:
        c.need(args.notify_admission is None and ad.data.get("notification_required") is not True,
               "Root-required single completion notification must be explicitly enabled")
        return None
    c.need(args.notify_admission is not None, "Notify requires its independent owner admission")
    entry = ad.pin(args.notify_admission); doc = c.read(entry["path"])
    c.need(doc.get("stage") == STAGE + ".notify_admission" and doc.get("passed") is True and doc.get("notify_only") is True and
           doc.get("tag") == TAG and doc.get("root_thread_id") == ROOT_THREAD and
           os.environ.get("CODEX_THREAD_ID") == ROOT_THREAD and
           Path(doc["run_admission_path"]).resolve() == Path(ad.entry["path"]).resolve() and
           doc.get("max_attempts") == 1 and doc.get("timeout_s") == 45 and doc.get("watcher") is False and
           doc.get("automatic_retry") is False, "Separate exact-current-root direct-owner completion admission required")
    for key, path in (("successful_queue_attempt", QUEUE_PROOF_ATTEMPT), ("successful_queue_result", QUEUE_PROOF_RESULT)):
        c.need(Path(doc[key]["path"]).resolve() == path.resolve(), "Actual successful same-thread queue proof differs")
        ad.pin(path); c.same(doc[key])
    attempt, reply = c.read(QUEUE_PROOF_ATTEMPT), c.read(QUEUE_PROOF_RESULT)
    c.need(reply.get("status") == "queued" and reply.get("actual_exit") == 0 and reply.get("attempts") == 1 and
           attempt.get("thread") == ROOT_THREAD and attempt["arguments"][1:5] == ["queue","--thread",ROOT_THREAD,"--message"],
           "Only the already verified actual Codex queue interface may be used")
    program = ad.pin(doc["codex"]["path"]); c.same(doc["codex"]); c.same(attempt["program"])
    c.need(program == {k:attempt["program"][k] for k in ("path","bytes","mtime_ns")} and
           Path(program["path"]).resolve() == Path(attempt["arguments"][0]).resolve(),
           "Actual verified Codex executable stat changed; never substitute a guessed service")
    return dict(admission=entry, root_thread_id=ROOT_THREAD, codex=program,
                successful_queue_attempt=doc["successful_queue_attempt"], successful_queue_result=doc["successful_queue_result"],
                max_attempts=1, timeout_s=45, watcher=False, automatic_retry=False)


def notify_once(ctx, result):
    profile = ctx["notification"]
    if profile is None: return
    terminal, attempt, reply = (ctx["paths"][x] for x in ("terminal", "queue_attempt", "queue_result"))
    c.need(all(not x.exists() for x in (terminal,attempt,reply)), "Any existing completion attempt is protected; never resend")
    event = "run_passed_pending_native_review" if result["passed"] else "run_or_postcheck_failed_preserved"
    sealed = dict(stage=STAGE+".terminal",tag=TAG,event=event,root_thread_id=ROOT_THREAD,
        owner=c.identity(os.getpid()),run=c.stat(ctx["paths"]["run"]),status=c.stat(ctx["paths"]["status"]),
        actual_Popen_wait_exit=result.get("actual_Popen_wait_exit"),actual_Win32_exit=result.get("actual_Win32_exit"),
        target_actual_Win32_exit=result.get("target_actual_Win32_exit"),
        last_original_console_PART_line=result.get("console_last_raw_PART_line"),
        first_actual_console_error=result.get("console_first_actual_error_line"),
        failure=result.get("failure"),notification_admission=profile["admission"],physical_acceptance=False,
        unsaved_native_time_inferred=False,solver_or_reader_relaunched=False)
    c.write_new(terminal,sealed)
    message=("用户已授权同线程C02 fresh B GPU full2Tv继续；event="+event+"，tag="+TAG+"。"
        "先读取tests/logs/"+TAG+".terminal.json及原start/call/run/status/queue_attempt，核真实所有权和出口、冻结程序输入/原A1682时钟。"
        "正常出口只代表待独立native/物理审查，不可自动验收。成功后先检查已有/活动reader，根独立准入一次新full读取；"
        "审1682帧/1040IDs/22arrays/1681signed intervals、实际scalar终点72.88428689946836、1564post/15640真排水、原HG和ledger；1600为preopen。"
        "审全孔压/材料沉降/Jn密度/总应力及100层交替X模态，按真实common clocks对保留B短窗和旧A full作合适比较，M0与finiteKw不套5Pa跨模型等价。"
        "失败保留真实退出/首因/最后原样PART，不推断未保存时间、不重跑/覆盖/重解码。继续中文分阶段汇报和原授权开发。"
        "本directowner只queue一次45秒，超时可能已送达；绝不重发/rearm/自测，无自动reader/Git/Cfull/half/ref/下一solver。")
    argv=[profile["codex"]["path"],"queue","--thread",ROOT_THREAD,"--message",message]
    c.write_new(attempt,dict(stage=STAGE+".queue_attempt",owner=sealed["owner"],terminal=c.stat(terminal),
        run=sealed["run"],status=sealed["status"],notification_admission=profile["admission"],program=profile["codex"],
        arguments=argv,attempt=1,max_attempts=1,timeout_s=45,timeout_may_have_delivered_no_resend=True))
    outcome=dict(stage=STAGE+".queue_result",attempt=c.stat(attempt),attempts=1,do_not_resend=True,automatic_retry=False)
    try:
        c.need(os.environ.get("CODEX_THREAD_ID")==ROOT_THREAD,"Current root-thread binding changed before the one queue attempt")
        c.same(profile["codex"]);c.same(profile["admission"])
        call=subprocess.run(argv,cwd=T.parent,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                            text=True,encoding="utf-8",errors="replace",timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        outcome.update(status="queued" if call.returncode==0 else "queue_failed",actual_exit=call.returncode,output=call.stdout)
    except subprocess.TimeoutExpired as exc:
        output=exc.stdout or ""
        outcome.update(status="queue_delivery_uncertain",output=output.decode("utf-8","replace") if isinstance(output,bytes) else output,
                       error=str(exc),timeout_may_have_delivered=True)
    except Exception as exc: outcome.update(status="queue_failed",error=str(exc))
    c.write_new(reply,outcome)


def retained_plan(ad):
    ad.pin(OLD_A_RUN); ad.pin(OLD_A_PLAN)
    original = c.read(OLD_A_RUN); job = original["job"]
    c.need(original.get("passed") is True and job.get("steps") == STEPS and job.get("expected_samples") == FRAMES and
           job.get("dt_s") == DT and job.get("end_s") == END and job.get("post_open_frames") == POST and
           job.get("runtime_TimeMax_s") == CAP and Path(job["input_prefix"]).resolve() == c.PREFIX.resolve() and
           Path(original["planned_clock_CSV"]["path"]).resolve() == OLD_A_PLAN.resolve() and
           Path(job["planned_clock_CSV"]["path"]).resolve() == OLD_A_PLAN.resolve() and
           OLD_A_PLAN.stat().st_size == original["planned_clock_CSV"]["bytes"],
           "Actual retained A full-run seed/clock identity differs; never regenerate a substitute")
    raw = OLD_A_PLAN.read_bytes()
    with OLD_A_PLAN.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f); rows = list(reader)
        c.need(reader.fieldnames == c.HEADER, "Retained original clock CSV8 layout differs")
    saved = job["saved_clock_table"]
    c.need(len(rows) == len(saved) == FRAMES, "Complete1682 original planned states required")
    integer = {"part", "completed_steps", "saved_step", "post_open_by_completed_step", "forced_final"}
    for i, (row, expected) in enumerate(zip(rows, saved)):
        c.need(set(row) == set(expected) == set(c.HEADER) and int(row["part"]) == i and
               all((int(row[k]) == expected[k] if k in integer else c.bits(float(row[k])) == c.bits(expected[k])) for k in c.HEADER),
               "Retained actual clock row differs from original sealed full run")
    c.need(int(rows[117]["completed_steps"]) == 1600 and int(rows[117]["post_open_by_completed_step"]) == 0 and
           int(rows[118]["completed_steps"]) == 1601 and sum(int(r["post_open_by_completed_step"]) for r in rows) == POST and
           int(rows[-1]["completed_steps"]) == STEPS and float(rows[-1]["time_s"]) == END and
           int(rows[-1]["forced_final"]) == 1, "Original event/final scalar clock plan differs")
    return raw, dict(method="byte-identical retained A full CSV8; binary64 scalar +=dt clocks were not regenerated",
        actual_scalar_end_s=END, actual_fixed_dt_s=DT, completed_updates=STEPS, native_frames=FRAMES,
        runtime_TimeMax_s=CAP, scalar_end_minus_runtime_cap_s=END-CAP,
        event_completed_step=1600, event_step_is_preopen=True, first_post_open_completed_step=1601,
        post_open_frames=POST, expected_true_drained_receivers=10*POST,
        retained_A_plan=ad.pin(OLD_A_PLAN), actual_native_clock_review_pending=True,
        no_steps_times_dt_clock_substitution=True)


def context(ad, notification):
    for p in (Path(__file__), NOTE, Path(old.__file__), old.NOTE, Path(c.__file__), c.SEED_XML, c.SEED_BI4, c.SEED_NORMALS,
              PREP, BUILD, B_REVIEW, SCIENCE): ad.pin(p)
    expected_job = dict(tag=TAG, configuration="Release", scheme="B", window="full2tv")
    c.need(all(ad.data["job"].get(k) == v for k,v in expected_job.items()), "Only this unique fresh B full2Tv job is admitted")
    prepared, build = c.read(PREP), c.read(BUILD)
    c.need(prepared.get("passed") is True and prepared.get("stage") == "upl_tpi_gpu_full2tv_r1.prepare" and
           prepared.get("source_count") == 269 and prepared.get("other268_files_byte_identical") is True and
           prepared.get("helper_h_and_cuh_byte_identical") is True and prepared.get("class_or_header_ABI_changed") is False and
           build.get("passed") is True and build.get("configuration") == "Release" and build.get("object_count") == 111 and
           build.get("compile_invocations") == build.get("link_invocations") == 1 and build.get("new_CUDA_compile_invocations") == 0 and
           build.get("retained_effective_object_count") == 110 and build.get("consumed_stats_unchanged") is True and
           Path(build["source_prepare"]["path"]).resolve() == PREP.resolve() and
           build.get("program_help_invocations") == build.get("solver_invocations") == build.get("native_invocations") == 0,
           "Actual passed one-host full-window program/source build required")
    for e in (build["source_prepare"], prepared["source_diff"], prepared["base_prepare"], prepared["base_build"]): ad.pin(e["path"]); c.same(e)
    source_entries = [*prepared["files"], prepared["source_diff"]]
    for e in source_entries: ad.pin(e["path"]); c.same(e)
    program = ad.pin(build["program"]["path"]); c.same(build["program"])
    c.need(Path(program["path"]).resolve() == (T / "outputs/upl_tpi_gpu_full2tv_Release_r1/out/DualSPHysics5.2_GEO_win64.exe").resolve(),
           "Exact new private full-window program required")
    runtime = [ad.pin(x["destination"]["path"]) for x in build["runtime"]]
    root = ET.parse(c.SEED_XML).getroot()
    c.need(c.xml_value(root,"DtFixed") == c.xml_value(root,"DtIni") == DT and c.xml_value(root,"TimeMax") == CAP,
           "Original full seed physical dt/cap changed")
    review, science = c.read(B_REVIEW), c.read(SCIENCE)
    bscope = science["schemes"]["B"]
    c.need(review.get("passed") is True and review.get("stage") == "upl_tpi_gpu_native_r5.review" and
           review["job"].get("scheme") == "B" and review["job"].get("window") == "startup015" and
           science.get("analysis_complete") is True and bscope.get("guard_first_failure") is None and
           bscope["post_01_max_layer_total_error_Pa"] <= 100. and bscope["post_01_max_top_pair_gap_Pa"] <= 100.,
           "Actual B startup native/unchanged post-.1s guards must pass; overall A failure is not hidden")
    checks = []
    c.need(ad.data.get("required_passed_checks"), "Root must bind actual independently passed full-run admission decisions")
    for e in ad.data["required_passed_checks"]:
        checks.append(ad.pin(e["path"])); c.need(c.read(e["path"]).get("passed") is True, "Root-declared prerequisite failed")
    plan_raw, clock = retained_plan(ad)
    out = T / "outputs" / TAG
    paths = {k: L / (TAG+v) for k,v in (("start",".start.json"),("tool_start",".tool.start.json"),("call",".call.json"),
            ("run",".run.json"),("status",".status.json"),("log",".log"),("memcheck",".memcheck.log"),("plan",".clock.csv"))}
    if notification is not None:
        paths.update({key:L/(TAG+suffix) for key,suffix in (("terminal",".terminal.json"),("queue_attempt",".queue_attempt.json"),("queue_result",".queue_result.json"))})
    c.need(not out.exists() and all(not p.exists() for p in paths.values()), "Existing run/partial/call is protected; no duplicate or rearm")
    ad.finish()
    with paths["plan"].open("xb") as f: f.write(plan_raw)
    c.need(paths["plan"].read_bytes() == plan_raw, "New launch plan must be an exact byte-copy of retained A")
    return dict(**expected_job, backend="GPU", program=program, source_build=ad.pin(BUILD), prepared=ad.pin(PREP),
        source_entries=source_entries, runtime=runtime, prerequisite_reviews=checks, input_prefix=str(c.PREFIX),
        output_directory=str(out), data=str(out/"data"), arguments=["-gpu","-stable","-mdbc_freeslip",str(c.PREFIX),str(out),
        "-dirdataout","data","-svres","-nsteps:"+str(STEPS)], plan=c.stat(paths["plan"]), clock=clock, paths=paths,
        memcheck_program=None, required_runtime_markers=ad.data["job"].get("required_runtime_markers",[]),
        original_seed=[ad.pin(p) for p in (c.SEED_XML,c.SEED_BI4,c.SEED_NORMALS)],
        GenCase_invocations=0, PART_restart=False, pressure_history_cold_start=True,
        planned_sidecar_saved_soil_rows=FRAMES*1000, sidecar_every_update=False, notification=notification)


def check_output(ctx):
    out = Path(ctx["output_directory"]); text = (out/"Run.out").read_text(encoding="utf-8-sig")
    c.need(text.count("Finished execution (code=0).") == 1 and 'RunMode="Stable - Pos-Cell - Single-GPU"' in text and
           re.search(r"Steps of simulation[.]+:\s*"+str(STEPS)+r"(?:\s|$)",text) and
           re.search(r"Excluded particles[.]+:\s*0(?:\s|$)",text), "Actual full GPU normal finish/steps/no-exclusion differs")
    for marker in ctx["required_runtime_markers"]:
        c.need(isinstance(marker,str) and marker and marker in text,"Required actual runtime marker missing")
    console = ctx["paths"]["log"].read_text(encoding="utf-8-sig",errors="replace")
    c.need(console.count(old.SOURCE_FIXTURE_R2) == 1,"Real16-case source/owner device fixture must run once")
    cap = re.search(r"(?m)^TimeMax=([-+0-9.eE]+)\s*$",text)
    c.need(cap and float(cap[1]) == float(format(CAP,".16g")),"Actual original XML TimeMax formatter/cap differs")
    hg = re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)",text)
    cache = re.search(r"SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)",text)
    c.need(hg and cache and tuple(map(int,hg.groups())) == (2*STEPS,STEPS,STEPS,2*STEPS) and
           tuple(map(int,cache.groups())) == (STEPS+1,STEPS-1),"Original full GPU HG stage/cache counters differ")
    guard = re.search(r"SoilHourglass: max\|sum\(M0\*Href\)\|=([^ ]+) max\|sum\(mi\*deltaAce\)\|=([^ ]+) max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)",text)
    c.need(guard,"Original full GPU HG safety summary missing")
    net,actual,tau,spin = map(float,guard.groups())
    c.need(all(math.isfinite(x) and x>=0 for x in (net,actual,tau,spin)) and tau<=.2 and spin<.01,
           "Original full HG stiffness/small-spin safety failed")
    c.need(sorted(p.name for p in (out/"data").glob("Part_*.bi4")) == ["Part_%04d.bi4"%i for i in range(FRAMES)],
           "Full1682 native file presence differs; content/actual time remains pending independent native review")
    with (out/"Run.csv").open(encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f,delimiter=";"))
    c.need(len(rows)==1 and int(rows[0]["Steps"])==STEPS and int(rows[0]["PartFiles"])==FRAMES and
           int(rows[0]["PartsOut"])==0 and int(rows[0]["Np"])==1040 and "gpu" in rows[0]["Hardware"].lower(),
           "Actual full GPU Run.csv metadata differs")
    for suffix in (".policy.json",".csv",".summary.json"): c.need((out/("UplTpiGpuR1"+suffix)).is_file(),"Actual saved-stage B sidecar missing")
    summary = c.read(out/"UplTpiGpuR1.summary.json")
    c.need(summary.get("completed") is True and summary.get("scheme")=="B_TPI_alpha_0p5_beta0" and
           summary.get("alpha")==.5 and summary.get("beta")==0 and summary.get("commits")==summary.get("endpoint_calls")==STEPS and
           summary.get("core_field_bit_checks")==7000*STEPS and summary.get("HG_readonly_snapshot_checks")==2000*STEPS and
           c.bits(summary["actual_end"])==c.bits(END) and summary.get("history_cold_start") is True and
           summary.get("full_restart_supported") is False,"Actual64-bit full lifecycle/cold-history summary differs")
    return dict(solver_summary_completed=True,native_frame_presence_only=True,reported_steps=STEPS,reported_native_frames=FRAMES,
        actual_device_from_Run_csv=rows[0]["Hardware"],actual_r2_device_fixture_marker_count=1,
        HG=dict(forcecalls=2*STEPS,predictorupdates=STEPS,correctorupdates=STEPS,ratecalls=2*STEPS,
                ratecalculations=STEPS+1,ratecachehits=STEPS-1,max_reference_net=net,max_actual_net=actual,max_dt_tau=tau,spinbound=spin),
        reported_64bit_core_checks=7000*STEPS,reported_64bit_HG_snapshots=2000*STEPS,
        native_and_sidecar_row_review_pending=True,actual_native_final_time_not_inferred_from_text=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--execution-authorized",action="store_true"); p.add_argument("--admission",required=True,type=Path)
    p.add_argument("--notify",action="store_true");p.add_argument("--notify-admission",type=Path)
    a=p.parse_args(); c.need(a.execution_authorized,"One root-admitted B full-run execution required")
    ad=ctx=None
    result=dict(stage=STAGE+".run",passed=False,failure=None,solver_invocations=0,native_invocations=0,
        GenCase_invocations=0,VTK_invocations=0,build_invocations=0,SHA_scans=0,automatic_follow_up=False,
        physical_acceptance=False,old_paused_processes_touched=False,direct_owner_no_scheduler=True,
        all22_native_clock_signed_ledger_drainage_and_HG_review_pending=True)
    try:
        ad=Admission(a.admission);profile=notification_profile(ad,a);ctx=context(ad,profile);result.update({k:v for k,v in ctx.items() if k!="paths"});result["root_admission"]=ad.entry
        old.run_owned(ad,ctx,result);result["actual_solver_handle_exit_zero"]=True
        result.update(check_output(ctx));result["passed"]=True
    except Exception as exc: result["failure"]=str(exc)
    finally:
        if ctx is not None:
            try: result.update(c.terminal_evidence(ctx))
            except Exception as exc:result.update(passed=False,terminal_evidence_failure=str(exc))
            try: result["consumed"]=ad.finish();result["consumed_stats_unchanged"]=True
            except Exception as exc:result.update(passed=False,consumed_stats_unchanged=False,final_stat_failure=str(exc))
            out=Path(ctx["output_directory"]);result["outputs_stat_only"]=[c.stat(x) for x in sorted(out.rglob("*")) if x.is_file()] if out.exists() else []
            c.write_new(ctx["paths"]["run"],result)
            c.write_new(ctx["paths"]["status"],dict(stage=TAG+".status",run=c.stat(ctx["paths"]["run"]),passed=result["passed"],
                state="pending_native_review" if result["passed"] else "failed_preserved",physical_acceptance=False,following_action_launched=False))
            notify_once(ctx,result)  # Sealed run/status first; at most one direct-owner queue, no watcher.
        print(c.json.dumps(dict(passed=result["passed"],tag=TAG,failure=result["failure"]),ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
