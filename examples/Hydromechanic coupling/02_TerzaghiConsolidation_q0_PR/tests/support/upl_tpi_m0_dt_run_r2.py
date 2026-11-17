"""One private M0 necessary-step qualification; never decode or chain solvers."""
from __future__ import annotations
import argparse
import csv
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
import upl_tpi_gpu_run_r3 as gpu

c, T, L = gpu.c, gpu.T, gpu.L
STAGE = "upl_tpi_m0_dt_run_r2"
NOTE = T / "notes" / (STAGE + ".md")
EVENT = .010000228881835938
ROOT_THREAD = "01a07683-bc64-7463-8db7-9ee6243967d8"


def notification(ad, path):
    if path is None:
        c.need(ad.data.get("notification_required") is not True,"Root-required direct-owner completion missing")
        return None
    e=ad.pin(path);v=c.read(path)
    c.need(v.get("stage")==STAGE+".notify_admission" and v.get("passed") is True and
           v.get("root_thread_id")==ROOT_THREAD==os.environ.get("CODEX_THREAD_ID") and
           Path(v["run_admission_path"]).resolve()==Path(ad.entry["path"]).resolve() and
           v.get("max_attempts")==1 and v.get("timeout_s")==45 and v.get("watcher") is False,
           "Exact same-root one-attempt completion admission required")
    for key in ("codex","successful_queue_attempt","successful_queue_result"):
        ad.pin(v[key]["path"]);c.same(v[key])
    a,r=c.read(v["successful_queue_attempt"]["path"]),c.read(v["successful_queue_result"]["path"])
    c.need(r.get("status")=="queued" and r.get("actual_exit")==0 and r.get("attempts")==1 and
           a["arguments"][1:5]==["queue","--thread",ROOT_THREAD,"--message"] and
           a["program"]==v["codex"],"Actual already-successful queue protocol required; no self-test")
    return dict(admission=e,**v)


def notify_once(ctx,result,profile):
    if profile is None:return
    tag=ctx["tag"];terminal,attempt,reply=[L/(tag+x) for x in (".terminal.json",".queue_attempt.json",".queue_result.json")]
    c.need(not any(x.exists() for x in (terminal,attempt,reply)),"Existing queue attempt protected; never resend")
    event="run_passed_pending_native_review" if result["passed"] else "failed_preserved_pending_diagnosis"
    c.write_new(terminal,dict(stage=STAGE+".terminal",event=event,tag=tag,owner=c.identity(os.getpid()),
        run=c.stat(ctx["paths"]["run"]),status=c.stat(ctx["paths"]["status"]),
        actual_Win32_exit=result.get("actual_Win32_exit"),target_actual_Win32_exit=result.get("target_actual_Win32_exit"),
        first_actual_error=result.get("console_first_actual_error_line"),
        last_original_console_PART_line=result.get("console_last_raw_PART_line"),physical_acceptance=False))
    msg=("已授权同线程C02 TPI M0大步长单窗继续，tag="+tag+"，event="+event+"。先审tests/logs/"+tag+
         ".run.json与原start/call/status/terminal/queue_attempt，核真实所有权/出口/程序/输入/原scalar plan。"
         "本次仅约2s/私有Eq40 Rh1，非完整2Tv或物理验收；旧小步长full已保留退役，不恢复/rearm。"
         "先查已有/活动reader，根独立审阅新dt profile后才能唯一解码；保持全部1040IDs/22typed/真实clock/signed/ledger/排水/HG门。"
         "检查每帧100层孔压/材料顶底沉降/应力Q/Jn密度及1.5至2s交替X模态，原Kw波速是诊断而非新方法硬界。"
         "跨dt差异不套5Pa half界，不插值重写时钟；不自动half/下一dt/新reference/full。"
         "失败保留真实首因/最后原始PART/partial，不推断未保存时间或重跑已完成solver。"
         "继续用户授权大步长开发并中文阶段汇报。此directowner仅queue一次45s，timeout可能已投递，禁止重发/rearm/selftest。")
    argv=[profile["codex"]["path"],"queue","--thread",ROOT_THREAD,"--message",msg]
    c.write_new(attempt,dict(stage=STAGE+".queue_attempt",terminal=c.stat(terminal),program=profile["codex"],
        arguments=argv,attempt=1,max_attempts=1,timeout_s=45,timeout_may_have_delivered_no_resend=True))
    outcome=dict(stage=STAGE+".queue_result",attempt=c.stat(attempt),attempts=1,do_not_resend=True)
    try:
        c.need(os.environ.get("CODEX_THREAD_ID")==ROOT_THREAD,"Root thread changed before queue")
        c.same(profile["codex"])
        r=subprocess.run(argv,cwd=T.parent,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,encoding="utf-8",errors="replace",timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        outcome.update(status="queued" if r.returncode==0 else "queue_failed",actual_exit=r.returncode,output=r.stdout)
    except subprocess.TimeoutExpired as exc:
        output=exc.stdout or ""
        outcome.update(status="delivery_uncertain",output=output.decode("utf-8","replace") if isinstance(output,bytes) else output,
            error=str(exc),timeout_may_have_delivered=True)
    except Exception as exc:outcome.update(status="queue_failed",error=str(exc))
    c.write_new(reply,outcome)


class Admission(c.Admission):
    def __init__(self, path):
        self.entry, self.data = c.stat(path), c.read(path)
        c.need(self.data.get("stage") == STAGE + ".run_admission" and self.data.get("passed") is True
               and self.data.get("one_job_only") is True, "Reviewed single-job admission required")
        self.frozen = {str(Path(e["path"]).resolve()): e for e in self.data["inputs"]}
        c.need(len(self.frozen) == len(self.data["inputs"]), "Duplicate admitted input")
        self.consumed = {}


def plan(root, dt, cap, upper, event_step):
    nodes = root.findall(".//timeout")
    c.need(len(nodes) == 1 and nodes[0].get("active") == "true", "Retained special schedule required")
    segments = [(float(x.get("time")), float(x.get("timeout"))) for x in nodes[0].findall("tout")]
    c.need(segments == [(0.,2.**-13),(.009765625,2.**-19),(.01025390625,2.**-13),
                       (.0250244140625,2.**-9),(2.0000457763671875,.18218571428571428)], "Original cadence changed")
    actual, target = 0., c.next_time(0., segments)
    rows = [dict(zip(c.HEADER, (0,0,0,0.,dt,0,0.,0)))]
    for completed in range(1, upper + 1):
        actual += dt
        ordinary, stop = actual >= target, actual >= cap or completed == upper
        if ordinary or stop:
            rows.append(dict(zip(c.HEADER, (len(rows),completed,completed-1,actual,dt,
                int(completed > event_step),target,int(stop and not ordinary)))))
            target = c.next_time(actual, segments)
        if stop:
            break
    return rows, dict(method="binary64 scalar +=dt; original output-target operation order",
        actual_fixed_dt_s=dt, actual_scalar_end_s=actual, completed_updates=completed,
        native_frames=len(rows), runtime_TimeMax_s=cap, nsteps_upper_cap=upper,
        event_completed_step=event_step, event_step_is_preopen=True,
        first_post_open_completed_step=event_step+1,
        post_open_frames=sum(x["post_open_by_completed_step"] for x in rows),
        expected_true_drained_receivers=10*sum(x["post_open_by_completed_step"] for x in rows),
        actual_native_review_pending=True, n_times_dt_clock_used=False)


def context(ad):
    for p in (Path(__file__), NOTE, Path(gpu.__file__), Path(c.__file__), c.SEED_XML, c.SEED_BI4, c.SEED_NORMALS):
        ad.pin(p)
    j = ad.data["job"]
    mode, cfg, scheme, tag = (j[x] for x in ("mode","configuration","scheme","tag"))
    valid = (mode,cfg,scheme) in (("Acontrol","Release","A"),("debug2","Debug","B"),
                                  ("cpu_debug2ms","DebugCPU","B"),("window2s","Release","B"))
    c.need(valid and re.fullmatch(r"upl_tpi_m0_dt_[A-Za-z0-9_]+_r[1-9][0-9]*",tag), "Unsupported single qualification")
    div = j.get("event_divisor",1000)
    c.need(div in (1000,500) and (div == 1000 or mode == "window2s"), "Only independently admitted 10/20us window")
    build_e = ad.pin(j["build"]["path"]); build = c.read(build_e["path"])
    c.need(build.get("passed") is True and build.get("stage")==("upl_tpi_m0_dt_build_r3" if cfg=="DebugCPU" else "upl_tpi_m0_dt_build_r2") and
           build.get("configuration") == cfg and Path(build_e["path"]).resolve()==
           (L/("upl_tpi_m0_dt_"+cfg+("_r3.build.json" if cfg=="DebugCPU" else "_r2.build.json"))).resolve(), "Actual matched passed new M0 build required")
    prepared_e=ad.pin(build["source_prepare"]["path"]);c.same(build["source_prepare"])
    backend="CPU" if cfg=="DebugCPU" else "GPU"
    prepared=c.read(prepared_e["path"])
    c.need(Path(prepared_e["path"]).resolve()==(L/("upl_tpi_m0_dt_"+backend+"_r2.prepare.json")).resolve() and
           prepared.get("stage")=="upl_tpi_m0_dt_r2.prepare" and prepared.get("passed") is True and
           prepared.get("backend")==backend and prepared.get("public_class_or_virtual_ABI_changed") is False and
           prepared.get("shared_device_structures_or_inline_tokens_changed") is False,
           "New host-only M0 preparation/build provenance differs")
    program = ad.pin(build["program"]["path"]); c.same(build["program"])
    runtime = [ad.pin(e["destination"]["path"]) for e in build["runtime"]]
    checks = []
    for e in ad.data["required_passed_checks"]:
        checks.append(ad.pin(e["path"])); c.need(c.read(e["path"]).get("passed") is True, "Prerequisite failed")
    c.need(checks, "At least actual source/build review is required")
    paths = {k:L/(tag+suffix) for k,suffix in (("start",".start.json"),("tool_start",".tool.start.json"),
        ("call",".call.json"),("run",".run.json"),("status",".status.json"),("log",".log"),
        ("memcheck",".memcheck.log"),("plan",".clock.csv"))}
    c.need(all(not (L/(tag+x)).exists() for x in (".terminal.json",".queue_attempt.json",".queue_result.json")),"Prior terminal protected")
    out, seed = T/"outputs"/tag, T/"outputs"/(tag+"_seed")
    c.need(not out.exists() and not seed.exists() and all(not x.exists() for x in paths.values()), "Existing work protected")
    dt = c.DT if scheme == "A" else EVENT/div
    cap = c.f32(.002) if mode == "Acontrol" else 2.
    upper = {"Acontrol":320,"debug2":2,"cpu_debug2ms":200,"window2s":200000 if div==1000 else 100000}[mode]
    event_step = 1600 if scheme == "A" else div
    xml = c.SEED_XML.read_text(encoding="utf-8-sig")
    if scheme != "A":
        for key, value in (("DtFixed",dt),("DtIni",dt),("TimeMax",cap)):
            pat = r'(<parameter\s+key="'+key+r'"\s+value=")[^"]+("[^>]*>)'
            xml, count = re.subn(pat,lambda m:m[1]+repr(value)+m[2],xml)
            c.need(count == 1, "Unique runtime parameter missing: "+key)
    root = ET.fromstring(xml)
    c.need(c.xml_value(root,"DtFixed") == c.xml_value(root,"DtIni") == dt, "New seed dt differs")
    rows, clock = plan(root,dt,cap,upper,event_step)
    seed.mkdir(); prefix = seed/c.PREFIX.name
    prefix.with_suffix(".xml").write_text(xml,encoding="utf-8",newline="")
    shutil.copy2(c.SEED_BI4,prefix.with_suffix(".bi4"))
    shutil.copy2(c.SEED_NORMALS,Path(str(prefix)+"_Normals.nbi4"))
    with paths["plan"].open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=c.HEADER);w.writeheader();w.writerows(rows)
    argv = ["-cpu","-ompthreads:1"] if cfg=="DebugCPU" else ["-gpu"]
    argv += ["-stable","-mdbc_freeslip",str(prefix),str(out),"-dirdataout","data","-svres","-nsteps:"+str(upper)]
    if mode=="Acontrol": argv.append("-tmax:0.002")
    mem = ad.pin(j["memcheck_program"]["path"]) if cfg=="Debug" else None
    if mem: c.need(Path(mem["path"]).name.lower()=="compute-sanitizer.exe", "Actual memcheck tool required")
    return dict(tag=tag,mode=mode,configuration=cfg,scheme=scheme,window=mode,program=program,
        source_build=build_e,runtime=runtime,prerequisite_reviews=checks,paths=paths,clock=clock,
        input_prefix=str(prefix),original_input_prefix=str(prefix),output_directory=str(out),data=str(out/"data"),
        plan=c.stat(paths["plan"]),arguments=argv,memcheck_program=mem,required_runtime_markers=[],
        seed=[c.stat(x) for x in (prefix.with_suffix(".xml"),prefix.with_suffix(".bi4"),Path(str(prefix)+"_Normals.nbi4"))],
        GenCase_invocations=0,PART_restart=False,pressure_history_cold_start=True,
        policy_environment="absent" if scheme=="A" else "EQ40_RH1",event_divisor=div)


def check_output(ctx):
    out=Path(ctx["output_directory"]);w=ctx["clock"];n=w["completed_updates"]
    text=(out/"Run.out").read_text(encoding="utf-8-sig")
    c.need(text.count("Finished execution (code=0).") == 1 and
           re.search(r"Steps of simulation[.]+:\s*"+str(n)+r"(?:\s|$)",text) and
           re.search(r"Excluded particles[.]+:\s*0(?:\s|$)",text), "Actual normal summary differs")
    with (out/"Run.csv").open(encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f,delimiter=";"))
    c.need(len(rows)==1 and int(rows[0]["Steps"])==n and int(rows[0]["PartFiles"])==w["native_frames"] and
           int(rows[0]["Np"])==1040 and int(rows[0]["PartsOut"])==0, "Actual run metadata differs")
    console=ctx["paths"]["log"].read_text(encoding="utf-8-sig",errors="replace")
    if ctx["configuration"]!="DebugCPU":
        c.need('RunMode="Stable - Pos-Cell - Single-GPU"' in text and "gpu" in rows[0]["Hardware"].lower() and
               console.count(gpu.SOURCE_FIXTURE_R2)==(0 if ctx["scheme"]=="A" else 1),
               "Actual GPU mode/hardware/once16 device fixture differs")
    else:
        c.need('RunMode="Stable - Pos-Double - Single core"' in text,"Actual one-core CPU mode differs")
    c.need(sorted(x.name for x in (out/"data").glob("Part_*.bi4"))==["Part_%04d.bi4"%i for i in range(w["native_frames"])], "Native frame presence differs")
    hg=re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)",text)
    cache=re.search(r"SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)",text)
    c.need(hg and cache and tuple(map(int,hg.groups()))==(2*n,n,n,2*n) and tuple(map(int,cache.groups()))==(n+1,n-1), "HG lifecycle differs")
    guard=re.search(r"SoilHourglass: max\|sum\(M0\*Href\)\|=([^ ]+) max\|sum\(mi\*deltaAce\)\|=([^ ]+) max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)",text)
    c.need(guard,"Original HG summary absent");net,actual,tau,spin=map(float,guard.groups())
    c.need(all(math.isfinite(x) and x>=0 for x in (net,actual,tau,spin)) and tau<=.2 and spin<.01,"Original HG safety failed")
    policy=out/"UplTpiM0DtR1.policy.json";summary=out/"UplTpiM0DtR1.summary.json"
    if ctx["scheme"]=="A":
        c.need(not policy.exists() and not summary.exists() and not (out/"UplTpiM0DtR1.csv").exists(),"A entered M0 timestep branch")
    else:
        p,s=c.read(policy),c.read(summary)
        c.need(p["dt_policy"]==s["dt_policy"]=="M0_Eq40_Rh1" and p["R_h"]==s["R_h"]==1 and
               p["HG_limit_reference_available"] is False and s["HG_limit_reference_available"] is False and
               s["completed"] is True and s["updates"]==s["pre"]==s["cor"]==s["endpoint"]==n and
               s["saved_intervals_including_initial"]==w["native_frames"] and
               c.bits(s["actual_end_s"])==c.bits(w["actual_scalar_end_s"]) and
               s["max_dt_minus_bound_s"]<=1e-14,"Actual M0 timestep summary failed")
    if ctx["memcheck_program"]:
        mem=ctx["paths"]["memcheck"].read_text(encoding="utf-8-sig",errors="replace")
        c.need(re.search(r"ERROR SUMMARY:\s*0 errors",mem),"Memcheck error summary failed")
    return dict(solver_summary_completed=True,native_and_physical_review_pending=True,
        actual_HG_max_dt_tau=tau,actual_HG_spinbound=spin,actual_Hardware=rows[0]["Hardware"])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--admission",type=Path,required=True)
    p.add_argument("--notify-admission",type=Path)
    p.add_argument("--execution-authorized",action="store_true");a=p.parse_args()
    c.need(a.execution_authorized,"Independent reviewed single-job execution required")
    ad=ctx=profile=None;result=dict(stage=STAGE+".run",passed=False,failure=None,solver_invocations=0,
        native_invocations=0,VTK_invocations=0,physical_acceptance=False,automatic_follow_up=False,SHA_scans=0)
    prior=os.environ.get("UPL_TPI_M0_DT_R1")
    try:
        ad=Admission(a.admission);profile=notification(ad,a.notify_admission);ctx=context(ad)
        c.need(profile is None or ctx["mode"]=="window2s","Completion queue only for the longer independent window")
        result.update({k:v for k,v in ctx.items() if k!="paths"});result["root_admission"]=ad.entry
        if ctx["scheme"]=="A":os.environ.pop("UPL_TPI_M0_DT_R1",None)
        else:os.environ["UPL_TPI_M0_DT_R1"]="EQ40_RH1"
        for e in [*ctx["seed"],ctx["plan"]]:c.same(e)
        if ctx["configuration"]=="DebugCPU":c.own_solver(ad,ctx,result)
        else:gpu.run_owned(ad,ctx,result)
        result.update(check_output(ctx));result["passed"]=True
    except Exception as exc:result["failure"]=str(exc)
    finally:
        if prior is None:os.environ.pop("UPL_TPI_M0_DT_R1",None)
        else:os.environ["UPL_TPI_M0_DT_R1"]=prior
        if ctx is not None:
            try:
                result.update(c.terminal_evidence(ctx))
                for e in [*ctx["seed"],ctx["plan"]]:c.same(e)
                result["generated_seed_and_plan_stats_unchanged"]=True;result["consumed"]=ad.finish()
            except Exception as exc:result.update(passed=False,terminal_audit_failure=str(exc))
            c.write_new(ctx["paths"]["run"],result)
            c.write_new(ctx["paths"]["status"],dict(stage=ctx["tag"]+".status",passed=result["passed"],
                run=c.stat(ctx["paths"]["run"]),state="pending_native_review" if result["passed"] else "failed_preserved"))
            notify_once(ctx,result,profile)
        print(c.json.dumps(dict(passed=result["passed"],tag=result.get("tag"),failure=result["failure"]),ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__=="__main__":raise SystemExit(main())
