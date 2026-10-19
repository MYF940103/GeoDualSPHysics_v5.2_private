"""Fresh CPU integration/cache regression, .15-s pair then 15-s pair.

Not a new physical candidate. Original online guards are retained; each new
trajectory must equal its same-dt retained SPR trajectory. The old half-step
metrics are inherited only after both complete trajectories match, not rerun.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import re
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
import hg_bd_d04_15_r2 as retained
import hg_release_check as check
import hg_release_bench as bench

seq, gate, base, TESTS = retained.seq, retained.gate, bench.base, bench.TESTS
HERE = Path(__file__).resolve().parent
RUNNER, CHECKER = HERE/"hg_release_run.py", HERE/"hg_release_check.py"
THREAD = "01a07683-bc64-7463-8db7-9ee6243967d8"
CODEX = r"C:\Users\syosh\.vscode\extensions\openai.chatgpt-26.1007.21434-win32-x64\bin\windows-x86_64\codex.exe"
HALVES = {"015": "hg_bd_d04_next_r1_gate15_spr", "15": "hg_bd_spr15_half_r1_half"}


def plan(args):
    return [dict(name=f"{args.tag}_spr{window}_{role}", window=window, duration=duration,
                 dt=dt, reference=reference, samples=samples)
        for window, duration, samples, references in (
            ("015", ".15", 151, ("hg_bd_align_d04_spr_r1", "hg_bd_d04_next_r1_h15_spr")),
            ("15", "15", 15001, ("hg_bd_spr15_r1_dt", "hg_bd_spr15_half_r1_dt")))
        for role, dt, reference in zip(("c", "h"), (".00001", ".000005"), references)]


def bind(records, item):
    path, digest = str(Path(item["path"]).resolve()), item["sha256"].lower()
    gate.require(path not in records or records[path] == digest, "Conflicting evidence: "+path)
    gate.require(gate.sha(path) == digest, "Changed evidence: "+path)
    records[path] = digest


def half_receipt(window, stages):
    path = TESTS/f"logs/{HALVES[window]}.check.json"; result = gate.load(path)
    gate.require(result.get("half_dt_short_gate_passed") is True and not result["reasons"]
        and result["candidate"] == stages[0]["reference"] and result["half"] == stages[1]["reference"]
        and result["sample_count"] == stages[0]["samples"]
        and result["thresholds"] == dict(material_pressure_rms_pa=5.,
            top_material_settlement_difference_mm=.005, actual_time_tolerance_s=1e-7, maximum_duration_s=15.)
        and all(result["matched_time_checks"].values()), "Retained original half gate failed or changed")
    for stage in stages:
        reference = stage["reference"]
        gate.require(result["evidence"][reference]["run_manifest_sha256"].lower()
            == gate.sha(TESTS/f"logs/{reference}.run.json"), "Half receipt does not bind retained run")
    return path, result


def prerequisites(args):
    paths = [TESTS/f"logs/{tag}.check.json" for tag in (
        "hg_release_spr03_check_r1", "hg_release_hgoff_check_r2", "hg_cpu_cache_r1rel", args.bench_check)]
    paths.append(TESTS/f"logs/{args.debug_run}.smoke.check.json")
    missing = [str(p) for p in paths if not p.is_file()]
    gate.require(not missing, "Pending prerequisite receipts: "+", ".join(missing))
    spr, off, cache, timing, debug = [gate.load(p) for p in paths]
    gate.require(spr["passed"] and off["passed"] and not spr["reasons"] and not off["reasons"]
        and spr["candidate"] == "hg_release_spr03_r1" and off["candidate"] == "hg_release_hgoff_r1",
        "SPR/default-off integration regression not passed")
    gate.require(cache["passed"] and cache["required_max_ulp"] == cache["differing_field_bytes"] == 0
        and len(cache["scenarios"]) == len(cache["unchanged_rejections"]) == 11
        and cache["xi_zero_class_rejection_unchanged"], "Independent frozen-class cache regression failed")
    gate.require(debug["passed"] and debug["name"] == args.debug_run
        and debug["native_initial_final_ids_and_binary_csv_verified"], "CPU Debug smoke not passed")
    gate.require(timing["efficiency_gate_passed"] and timing["all_physical_pairs_byte_identical"]
        and not timing["failure"] and len(timing["runs"]) == 8 and len(timing["pair_checks"]) == 4
        and all(p["passed"] for p in timing["pair_checks"]), "Whole-loop efficiency/equivalence gate not passed")
    for field in ("solver_loop_seconds", "runner_elapsed_seconds"):
        data = timing["timing"][field]
        actual = bench.timing(data["old"]["samples"], data["new"]["samples"])
        gate.require(actual == data and actual["passed"], "Need >5% median benefit beyond observed spread")
    records = {}; [bind(records, base.entry(p)) for p in paths]
    record = TESTS/f"logs/mech_bin_{args.binary_label}.build.json"; build = gate.load(record)
    exe, runtime = base.runtime_inputs(SimpleNamespace(engine="wrapper", binary_label=args.binary_label,
                                                       exe=None, build_record=None))
    gate.require(build["configuration"] == "ReleaseCPU"
        and timing["plan"]["binaries"]["new"]["executable_sha256"] == gate.sha(exe), "Bench/new executable mismatch")
    for item in runtime+build["inputs"]+build["resolved_compile_link_inputs"]+timing["plan"]["inputs"]:
        bind(records,item)
    cache_build_path = TESTS/"logs/hg_cpu_cache_r1rel.build.json"
    cache_build = gate.load(cache_build_path); bind(records,base.entry(cache_build_path))
    for item in cache_build["inputs"]+cache_build["resolved_compile_link_inputs"]:
        bind(records,item)
    bind(records,dict(path=cache_build["exe"],sha256=cache_build["exe_sha256"]))
    evidence = check.Evidence()
    for receipt, name in ((spr,spr["candidate"]),(off,off["candidate"]),(debug,args.debug_run)):
        meta = check.metadata(name,evidence)
        expected = receipt.get("candidate_evidence",receipt.get("evidence"))
        gate.require(meta["receipt"]["run"] == expected["run"], "Admission run receipt mismatch")
        for item in meta["run"]["inputs"]+meta["run"]["outputs"]:
            bind(records,item)
        bind(records,base.entry(TESTS/f"logs/{name}.run.json"))
    for result in timing["runs"]:
        bind(records,result["run_manifest"])
        manifest = gate.load(result["run_manifest"]["path"])
        for item in manifest["inputs"]+manifest["outputs"]:
            bind(records,item)
    for window in HALVES:
        stages = [s for s in plan(args) if s["window"] == window]
        path, _ = half_receipt(window,stages); bind(records,base.entry(path))
        for stage in stages: bind(records,base.entry(TESTS/f"logs/{stage['reference']}.run.json"))
    return str(exe), records


def fresh(args):
    paths = [seq.state_path(args), TESTS/f"logs/{args.tag}.queue_attempt.json"]
    for stage in plan(args):
        name = stage["name"]
        paths += [TESTS/f"outputs/{name}",TESTS/f"outputs/{name}_input",TESTS/f"configs/CaseTCq0_{name}_Def.xml"]
        paths += list((TESTS/"logs").glob(name+".*"))+list((TESTS/"logs").glob(name+"_check.*"))
    paths += list((TESTS/"logs").glob(args.tag+"_half*.json"))
    # Launch redirects TAG.worker.stdout/stderr.log before this function runs.
    gate.require(not any(p.exists() for p in paths), "Refusing duplicate sequence or retained-output overwrite")


def idle():
    bench.quiet_machine()
    for process in retained.psutil.process_iter(["pid","name","cmdline"]):
        info = process.info; command = info.get("cmdline") or []
        if info["pid"] != os.getpid() and (info.get("name") or "").lower().startswith("python"):
            relevant = any("hg_" in part.lower() and part.lower().endswith(".py") for part in command)
            gate.require(not (relevant and ("--worker" in command or "--run" in command)), "Another HG worker/runner is active")


def completion_guard(run,steps,dt):
    c,h=run["completion"],run["hourglass"]
    gate.require(c["mode"]=="production_symplectic" and c["native_step_calls"]==steps
        and c["steps"]==h["steps"]==steps and abs(c["final_time"]-steps*dt)<1e-6
        and c["dt"]==dt and c["xi"]==h["xi"]==.1 and c["top_load_mode"]==5
        and c["max_fixed_dt_minus_mechanical_limit_s"]<=0 and c["pore_dt_limit_s"]>=dt
        and h["hg_force_calls"]==h["hg_updates"]==h["hg_rate_calls"]==2*steps
        and h["predictor_updates"]==h["corrector_updates"]==steps
        and 0<=h["integrated_max_skew_rad"]<.01 and h["max_dt_over_hg_tau"]<=.2,
        "Original full-run endpoint/dt/history/scope gate failed")


def run_stage(args,report,stage):
    retained.verify(report); idle()
    name, dt = stage["name"], float(stage["dt"])
    current = dict(stage,status="running_original_safety_gates")
    report.update(stage=name,current=current); retained.save(args,report)
    command = [sys.executable,"-B",str(RUNNER),"--name",name,"--duration",stage["duration"],
        "--dt",stage["dt"],"--output-interval",".001","--xi",".1","--spr","1","--event-grid","1",
        "--damping","0.04","--binary-label",args.binary_label,"--threads","1","--save","0","--run"]
    steps = int(round(float(stage["duration"])/dt)); stride = int(round(.001/dt))
    samples = seq.Samples(name,dt,steps,stride,current); wrapper = None
    try:
        with (TESTS/f"logs/{name}.wrapper.log").open("xb") as output:
            wrapper = seq.subprocess.Popen(command,cwd=base.CASE,stdin=seq.subprocess.DEVNULL,
                stdout=output,stderr=seq.subprocess.STDOUT,creationflags=seq.subprocess.CREATE_NO_WINDOW)
            current.update(command=command,wrapper_pid=wrapper.pid)
            while True:
                samples.poll(); retained.save(args,report)
                if wrapper.poll() is not None: break
                try: wrapper.wait(timeout=5)
                except seq.subprocess.TimeoutExpired: pass
        gate.require(wrapper.returncode == 0, "Release runner failed: "+name)
        samples.poll(); samples.finish()
        gate.require(current["checked_full_step_frames"] == stage["samples"], "Incomplete safety sample coverage")
        gate.require(retained.solver_absent(name,report["executable"]), "Owned solver survives wrapper")
        path = TESTS/f"logs/{name}.run.json"; result = gate.load(path)
        gate.require(result["completion_valid"] and result["inputs_unchanged"] and result["exit_code"] == 0,
            "Invalid run completion or changed input")
        completion_guard(result,steps,dt)
        current.update(status="completed_pending_bitwise_regression",wrapper_exit_code=wrapper.returncode,
                       actual_final_time=result["completion"]["final_time"])
        bind(report["prerequisite_hashes"],base.entry(path))
    except BaseException as error:
        current.update(status="rejected_or_interrupted",stop_reason=f"{type(error).__name__}: {error}")
        if wrapper is not None:
            try: current["stop"] = retained.stop_owned(wrapper,name,report["executable"])
            except Exception as stop_error: current["stop_error"] = str(stop_error)
        raise
    finally:
        current["wrapper_exited"] = wrapper is None or wrapper.poll() is not None
        current["owned_solver_absent"] = retained.solver_absent(name,report["executable"])
        report["runs"][name] = copy.deepcopy(current); retained.save(args,report)


def review_stage(args,report,stage):
    retained.verify(report); name=stage["name"]; tag=name+"_check"
    report["stage"]=tag; retained.save(args,report)
    command=[sys.executable,"-B",str(CHECKER),"--candidate",name,"--reference",stage["reference"],"--tag",tag]
    with (TESTS/f"logs/{tag}.analysis.log").open("xb") as output:
        result=seq.subprocess.run(command,cwd=base.CASE,stdin=seq.subprocess.DEVNULL,
            stdout=output,stderr=seq.subprocess.STDOUT,creationflags=seq.subprocess.CREATE_NO_WINDOW)
    path=TESTS/f"logs/{tag}.check.json"
    gate.require(result.returncode==0,"Same-dt integration regression failed: "+str(path))
    receipt=gate.load(path); same=receipt["comparison"]
    gate.require(receipt["passed"] and not receipt["reasons"] and not receipt["prefix"]
        and receipt["candidate"]==name and receipt["reference"]==stage["reference"]
        and same["compared_frames"]==stage["samples"] and same["native_ids_per_frame"]==1000
        and same["actual_times_bit_equal"] and same["initial_binary_equal"] and same["final_binary_equal"]
        and same["hg_sample_csv_byte_equal"] and same["final_hg_history_rate_csv_byte_equal"]
        and all(same["fields_bit_equal"][field] for field in check.PHYSICAL)
        and not same["unexpected_field_difference"],"Incomplete whole-trajectory 0-ULP regression")
    bind(report["prerequisite_hashes"],base.entry(path)); report["checks"][name]=base.entry(path)
    retained.save(args,report)


def inherit_half(args,report,window):
    retained.verify(report); stages=[s for s in plan(args) if s["window"]==window]
    path,old=half_receipt(window,stages)
    gate.require(all(s["name"] in report["checks"] for s in stages),"Both complete same-dt trajectories must pass first")
    result=dict(status="retained_half_metrics_inherited_via_complete_same_dt_zero_ulp",passed=True,
        candidate=stages[0]["name"],half=stages[1]["name"],sample_count=old["sample_count"],
        original_half_receipt=base.entry(path),zero_ulp_receipts=[report["checks"][s["name"]] for s in stages],
        thresholds=old["thresholds"],maximum_over_matched_times=old["maximum_over_matched_times"],
        matched_time_checks=old["matched_time_checks"],half_metrics_recomputed=False,
        original_online_safety_rerun=True,physical_accuracy_accepted=False,full_cycle_admitted=False,
        limitation="Complete same-dt pressure/material position/time/native-ID equality transfers the original half-step metrics; not a new physical acceptance.")
    target=TESTS/f"logs/{args.tag}_half{window}.check.json"; base.save_new(target,result)
    bind(report["prerequisite_hashes"],base.entry(target)); report["half_inheritance"][window]=base.entry(target)
    retained.save(args,report)


def stages(args,report):
    for stage in plan(args):
        run_stage(args,report,stage); review_stage(args,report,stage)
        if stage["name"].endswith("_h"): inherit_half(args,report,stage["window"])


def admitted_stages(args,report):
    exe,receipts=prerequisites(args);report.update(executable=exe,prerequisite_hashes=receipts)
    retained.save(args,report);stages(args,report);retained.verify(report)


def notify(args,report):
    if report.get("queue_attempted"): return
    message=(f"User-authorized same-thread CPU release regression continuation {args.tag}, not a new human observation. "
        f"Detected {report['status']}. Read {seq.state_path(args)} and {TESTS/f'logs/{args.tag}.queue_attempt.json'}, "
        "its prerequisite receipts, four fresh run/0-ULP checks and two half-inheritance receipts before claiming success. "
        "Verify actual times/native IDs/run-build-input-output hashes/owned exits; original 100-Pa post-.1-s safety and "
        "5-Pa/.005-mm half metrics remain required. Half metrics are inherited through complete same-dt 0-ULP trajectories, "
        "not recomputed; the recorded .01-s drained-display exception is not a physical field exception. "
        "This is CPU integration/cache equivalence, not a new physical candidate or a new 2Tv acceptance. The user on "
        "2026-10-16 provisionally accepted the existing 1D accuracy and explicitly resumed delivery: old late-Q growth "
        "must not indefinitely block delivery or restart KEEP diagnosis. New implementation regressions still require repair. "
        "Report the outcome proactively in Chinese. If these integration gates pass, continue the authorized GPU G1/G2/G3 "
        "synchronization and verification, then verified local/remote Git and formal k=1e-3/1e-4/1e-5 runs/plots in order, "
        "without waiting for another progress question. If failed/interrupted, inspect exact reason/time and owned processes, "
        "preserve evidence and repair within scope; do not duplicate solvers or publish failed results. Never restart/rearm "
        "this one-shot worker or send connectivity tests.")
    report.update(queue_attempted=True,queue_status="queueing",queued_message=message)
    try:
        base.save_new(TESTS/f"logs/{args.tag}.queue_attempt.json",dict(thread=args.thread,recorded_utc=base.utc(),report=copy.deepcopy(report)))
    except OSError as error:
        report["queue_record_error"]=str(error)
    try:
        result=seq.subprocess.run([args.codex,"queue","--thread",args.thread,"--message",message],cwd=base.CASE,
            stdin=seq.subprocess.DEVNULL,stdout=seq.subprocess.PIPE,stderr=seq.subprocess.STDOUT,text=True,
            encoding="utf-8",errors="replace",timeout=45,creationflags=seq.subprocess.CREATE_NO_WINDOW)
        report.update(queue_status="queued" if result.returncode==0 else "queue_failed_no_retry",
                      queue_exit_code=result.returncode,queue_reply=result.stdout)
    except (OSError,seq.subprocess.TimeoutExpired) as error:
        report.update(queue_status="delivery_uncertain_no_retry",queue_error=str(error))
    try:retained.save(args,report)
    except OSError as error:
        report["queue_status_publication_error"]=str(error)
        print(json.dumps(report),file=sys.stderr,flush=True)


def worker(args):
    fresh(args); idle()
    sources={Path(__file__).resolve(),RUNNER,CHECKER}
    sources.update(Path(m.__file__).resolve() for m in tuple(sys.modules.values())
        if getattr(m,"__file__",None) and Path(m.__file__).suffix==".py" and Path(m.__file__).resolve().parent==HERE)
    report=dict(status="checking_release_prerequisites",stage="prerequisites",scope="cpu_same_physics_integration_only",
        worker_pid=os.getpid(),scripts={str(p):gate.sha(p) for p in sources},prerequisite_hashes={},
        runs={},checks={},half_inheritance={},queue_attempted=False,new_physical_acceptance_claimed=False,
        user_provisional_1d_acceptance_date="2026-10-16",production_changes_during_sequence=False)
    with seq.state_path(args).open("x",encoding="utf-8") as stream: json.dump(report,stream)
    try:
        admitted_stages(args,report)
        report.update(status="cpu_release_regression_passed_pending_gpu_continuation",stage="gpu_continuation")
    except BaseException as error:
        report.update(status="cpu_release_regression_rejected_or_interrupted",stop_reason=f"{type(error).__name__}: {error}")
    try:retained.save(args,report)
    except OSError as error:report["terminal_publication_error"]=str(error)
    notify(args,report)
    return 0 if report["status"]=="cpu_release_regression_passed_pending_gpu_continuation" else 1


def self_test(args):
    from unittest.mock import patch
    with patch.dict(globals(),prerequisites=lambda a:(_ for _ in ()).throw(ValueError("mock prerequisite failure"))), \
         patch(__name__+".stages") as later:
        try:admitted_stages(args,{})
        except ValueError:pass
        assert later.call_count==0
    c=dict(mode="production_symplectic",native_step_calls=1,steps=1,final_time=1e-5,dt=1e-5,xi=.1,
        top_load_mode=5,max_fixed_dt_minus_mechanical_limit_s=0,pore_dt_limit_s=1e-5)
    h=dict(steps=1,xi=.1,hg_force_calls=2,hg_updates=2,hg_rate_calls=2,predictor_updates=1,
        corrector_updates=1,integrated_max_skew_rad=0,max_dt_over_hg_tau=.2)
    completion_guard(dict(completion=c,hourglass=h),1,1e-5)
    for group,field,value in (("completion","max_fixed_dt_minus_mechanical_limit_s",1e-12),
        ("completion","pore_dt_limit_s",0),("hourglass","hg_force_calls",1),
        ("hourglass","hg_updates",1),("hourglass","hg_rate_calls",1),
        ("hourglass","predictor_updates",0),("hourglass","corrector_updates",0),
        ("hourglass","integrated_max_skew_rad",.01),("hourglass","max_dt_over_hg_tau",.200001)):
        bad=copy.deepcopy(dict(completion=c,hourglass=h));bad[group][field]=value
        try:completion_guard(bad,1,1e-5)
        except ValueError:pass
        else:raise AssertionError("Original summary guard not enforced: "+field)
    expected=[(s["name"],kind) for s in plan(args) for kind in ("run","review")]
    expected.insert(4,("015","half"));expected.append(("15","half"))
    for fail in (None,*range(len(expected))):
        calls=[]
        def mark(name,kind):
            calls.append((name,kind))
            if fail is not None and len(calls)-1==fail:raise ValueError("mock stage failure")
        with patch.dict(globals(),run_stage=lambda a,r,s:mark(s["name"],"run"),
            review_stage=lambda a,r,s:mark(s["name"],"review"),inherit_half=lambda a,r,w:mark(w,"half")):
            try:stages(args,{})
            except ValueError:pass
        assert calls==expected[:len(calls)] and len(calls)==(len(expected) if fail is None else fail+1)
    for reply in (SimpleNamespace(returncode=0,stdout="mock"),SimpleNamespace(returncode=1,stdout="mock"),
                  OSError("mock"),seq.subprocess.TimeoutExpired("mock",45)):
        with patch.object(base,"save_new") as saved,patch.object(retained,"save"), \
             patch.object(seq.subprocess,"run",side_effect=[reply]) as queued:
            report=dict(status="mock");notify(args,report);notify(args,report)
            assert saved.call_count==queued.call_count==1
    with patch.object(base,"save_new",side_effect=OSError("mock receipt I/O")) as saved, \
         patch.object(retained,"save",side_effect=OSError("mock terminal I/O")),patch.object(sys,"stderr"), \
         patch.object(seq.subprocess,"run",return_value=SimpleNamespace(returncode=0,stdout="mock")) as queued:
        report=dict(status="mock");notify(args,report);notify(args,report)
        assert saved.call_count==queued.call_count==1 and report["queue_reply"]=="mock"
        assert "queue_record_error" in report and "queue_status_publication_error" in report
    with patch.object(Path,"exists",return_value=True),patch.object(Path,"glob",return_value=[]):
        try:fresh(args)
        except ValueError:pass
        else:raise AssertionError("Duplicate worker admitted")
    print("PASS serial order, every-stage short-circuit, duplicate refusal and once-only mocked queue; no files/solver/notification")


def main():
    parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group(required=True)
    for key in ("self-test","dry-run","worker"):mode.add_argument("--"+key,action="store_true")
    parser.add_argument("--tag",default="hg_release_sequence_r1")
    parser.add_argument("--binary-label",default="hg_release_rel_r3")
    parser.add_argument("--bench-check",default="hg_release_bench_r2")
    parser.add_argument("--debug-run",default="hg_release_dbg03_r2")
    parser.add_argument("--thread",default=THREAD);parser.add_argument("--codex",default=CODEX)
    args=parser.parse_args()
    for value in (args.tag,args.binary_label,args.bench_check,args.debug_run):
        gate.require(re.fullmatch(r"[A-Za-z0-9_-]{1,48}",value),"Use a shallow alphanumeric label")
    if args.self_test:self_test(args);return 0
    gate.require(args.thread==THREAD and Path(args.codex).is_file(),"Verified same-thread callback required")
    if args.dry_run:
        try:
            fresh(args);exe,records=prerequisites(args)
            print(json.dumps(dict(status="checked_not_prepared_or_run",executable=exe,prerequisites=len(records),
                stages=plan(args),solver_launched=False,notification_sent=False)))
            return 0
        except (ValueError,OSError) as error:
            print(json.dumps(dict(status="blocked_not_run",reason=str(error),solver_launched=False,notification_sent=False)))
            return 2
    return worker(args)


if __name__=="__main__":raise SystemExit(main())
