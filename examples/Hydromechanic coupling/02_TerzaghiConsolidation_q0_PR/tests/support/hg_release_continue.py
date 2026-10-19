"""Adopt completed r1 .15-s pair; audit its event display, then only fresh 15-s pair.

Never restart r1, overwrite its checks, or change production/physical gates.
Original run/Samples/completion/ownership and half-inheritance bodies are reused.
"""
import argparse
import copy
import json
import os
from pathlib import Path
import sys
from types import FunctionType

sys.dont_write_bytecode=True
import hg_release_sequence as prior
import hg_release_event_check as event

TESTS,base,gate,retained,seq=prior.TESTS,prior.base,prior.gate,prior.retained,prior.seq
OLD="hg_release_sequence_r1"
CHECKER=Path(event.__file__).resolve()


def plan(args):
    result=prior.plan(args)
    for stage in result:
        stage["adopted"]=stage["window"]=="015"
        if stage["adopted"]:stage["name"]=stage["name"].replace(args.tag,OLD,1)
    return result


# Private globals copy replaces only the actual plan, not the frozen module or
# function body. Every inherited receipt names real adopted/fresh output labels.
inherit_half=FunctionType(prior.inherit_half.__code__,dict(prior.inherit_half.__globals__,plan=plan),
                         prior.inherit_half.__name__)


def prerequisites(args):
    path=TESTS/f"logs/{OLD}.status.json";previous=gate.load(path)
    gate.require(previous["status"]=="cpu_release_regression_rejected_or_interrupted"
        and previous["stage"]==OLD+"_spr015_h_check" and previous["queue_status"]=="queued",
        "Expected the terminated r1 display-audit rejection, not a live/restartable worker")
    retained.verify(previous)  # All original scripts and prerequisites remain at their recorded hashes.
    exe,records=prior.prerequisites(args)
    for group in (previous["scripts"],previous["prerequisite_hashes"]):
        for name,digest in group.items():prior.bind(records,dict(path=name,sha256=digest))
    prior.bind(records,base.entry(path));prior.bind(records,base.entry(TESTS/f"logs/{OLD}.queue_attempt.json"))
    adopted={}
    for stage in plan(args)[:2]:
        name=stage["name"];saved=previous["runs"][name]
        gate.require(saved["wrapper_exited"] and saved["owned_solver_absent"]
            and saved["wrapper_exit_code"]==0 and saved["checked_full_step_frames"]==151
            and retained.solver_absent(name,exe),"Adopted short run incomplete or still owned")
        run_path=TESTS/f"logs/{name}.run.json";run=gate.load(run_path)
        prior.completion_guard(run,int(round(.15/float(stage["dt"]))),float(stage["dt"]))
        prior.bind(records,base.entry(run_path))
        old_check=TESTS/f"logs/{name}_check.check.json";prior.bind(records,base.entry(old_check))
        adopted[name]=dict(copy.deepcopy(saved),adopted_completed_run=True,solver_restarted=False)
    return exe,records,adopted


def fresh(args):
    paths=[seq.state_path(args),TESTS/f"logs/{args.tag}.queue_attempt.json"]
    for stage in plan(args):
        paths+=list((TESTS/"logs").glob(f"{args.tag}_{stage['window']}_{stage['name'][-1]}_check.*"))
        if not stage["adopted"]:
            name=stage["name"]
            paths += [TESTS/f"outputs/{name}",TESTS/f"outputs/{name}_input",TESTS/f"configs/CaseTCq0_{name}_Def.xml"]
            paths += list((TESTS/"logs").glob(name+".*"))
    paths+=list((TESTS/"logs").glob(args.tag+"_half*.json"))
    gate.require(not any(p.exists() for p in paths),"Refusing duplicate continuation or retained-output overwrite")


def review_stage(args,report,stage):
    retained.verify(report);name=stage["name"];tag=f"{args.tag}_{stage['window']}_{name[-1]}_check"
    report.update(stage=tag,current=dict(stage,action="offline_event_display_audit"));retained.save(args,report)
    command=[sys.executable,"-B",str(CHECKER),"--candidate",name,"--reference",stage["reference"],"--tag",tag]
    with (TESTS/f"logs/{tag}.analysis.log").open("xb") as output:
        result=seq.subprocess.run(command,cwd=base.CASE,stdin=seq.subprocess.DEVNULL,stdout=output,
            stderr=seq.subprocess.STDOUT,creationflags=seq.subprocess.CREATE_NO_WINDOW)
    path=TESTS/f"logs/{tag}.check.json";gate.require(result.returncode==0,"Exact event/physical audit failed: "+str(path))
    receipt=gate.load(path);same=receipt["comparison"]
    gate.require(receipt["passed"] and not receipt["reasons"] and receipt["candidate"]==name
        and receipt["reference"]==stage["reference"] and not receipt["prefix"]
        and same["compared_frames"]==stage["samples"] and same["native_ids_per_frame"]==1000
        and same["initial_binary_equal"] and same["final_binary_equal"] and same["actual_times_bit_equal"]
        and same["hg_sample_csv_byte_equal"] and same["final_hg_history_rate_csv_byte_equal"]
        and all(same["fields_bit_equal"][key] for key in event.old.PHYSICAL+event.old.DIAGNOSTIC)
        and not same["unexpected_field_difference"],"Incomplete physical/HG/native whole-trajectory equivalence")
    prior.bind(report["prerequisite_hashes"],base.entry(path));report["checks"][name]=base.entry(path)
    retained.save(args,report)


def stages(args,report):
    for stage in plan(args):
        if not stage["adopted"]:prior.run_stage(args,report,stage)
        review_stage(args,report,stage)
        if stage["name"].endswith("_h"):inherit_half(args,report,stage["window"])


def admitted_stages(args,report):
    exe,records,adopted=prerequisites(args)
    report.update(executable=exe,prerequisite_hashes=records,runs=adopted)
    retained.save(args,report);stages(args,report);retained.verify(report)


def notify(args,report):
    if report.get("queue_attempted"):return
    message=(f"User-authorized current-stage CPU release continuation {args.tag}, not a new human observation. "
        f"Detected {report['status']}. Read {seq.state_path(args)} and {TESTS/f'logs/{args.tag}.queue_attempt.json'}, "
        "new exact-event checks and half-inheritance receipts. Frozen r1 was not restarted: its completed .15-s coarse/half "
        "were adopted and re-audited offline; only the previously unrun 15-s coarse/half were fresh starts. Verify owned exits, "
        "actual times, native IDs, all build/input/output hashes and original 100-Pa/full-history guards. Compare retained "
        "raw_comparison with the sole exact .01-s drained-display exception: event/dt integer grid, old observed_tn and "
        "policy, exactly ten top native IDs, new=1/old=0. The drained equality flag remains false, all physical/native/HG "
        "bits must remain exact. Original 5-Pa/.005-mm half metrics are inherited via both complete same-dt trajectories, "
        "not recomputed. Normal exit is not new physical acceptance. Under the user's 2026-10-16 provisional 1D acceptance, "
        "old late-Q no longer indefinitely blocks delivery; do not resume KEEP diagnosis. Report proactively in Chinese, "
        "then on passed integration continue authorized GPU G1/G2/G3 synchronization/validation, verified local/remote "
        "Git, formal k=1e-3/1e-4/1e-5 full runs/plots in order without waiting for a progress query. If rejected, repair the "
        "new implementation/audit cause without changing physical thresholds or publishing failed results. Do not duplicate "
        "solvers, overwrite evidence, restart r1, rearm this one-shot worker, or send connectivity tests.")
    report.update(queue_attempted=True,queue_status="queueing",queued_message=message)
    try:base.save_new(TESTS/f"logs/{args.tag}.queue_attempt.json",dict(thread=args.thread,recorded_utc=base.utc(),report=copy.deepcopy(report)))
    except OSError as error:report["queue_record_error"]=str(error)
    try:
        reply=seq.subprocess.run([args.codex,"queue","--thread",args.thread,"--message",message],cwd=base.CASE,
            stdin=seq.subprocess.DEVNULL,stdout=seq.subprocess.PIPE,stderr=seq.subprocess.STDOUT,text=True,
            encoding="utf-8",errors="replace",timeout=45,creationflags=seq.subprocess.CREATE_NO_WINDOW)
        report.update(queue_status="queued" if reply.returncode==0 else "queue_failed_no_retry",
                      queue_exit_code=reply.returncode,queue_reply=reply.stdout)
    except (OSError,seq.subprocess.TimeoutExpired) as error:report.update(queue_status="delivery_uncertain_no_retry",queue_error=str(error))
    try:retained.save(args,report)
    except OSError as error:
        report["queue_status_publication_error"]=str(error);print(json.dumps(report),file=sys.stderr,flush=True)


def worker(args):
    fresh(args);prior.idle()
    sources={Path(__file__).resolve(),CHECKER}
    sources.update(Path(m.__file__).resolve() for m in tuple(sys.modules.values()) if getattr(m,"__file__",None)
        and Path(m.__file__).suffix==".py" and Path(m.__file__).resolve().parent==prior.HERE)
    report=dict(status="checking_continuation_prerequisites",stage="prerequisites",scope="adopt015_fresh15_integration_only",
        worker_pid=os.getpid(),scripts={str(p):gate.sha(p) for p in sources},prerequisite_hashes={},runs={},checks={},
        half_inheritance={},queue_attempted=False,old_worker_restarted=False,new_physical_acceptance_claimed=False,
        user_provisional_1d_acceptance_date="2026-10-16",production_changes_during_sequence=False)
    with seq.state_path(args).open("x",encoding="utf-8") as stream:json.dump(report,stream)
    try:
        admitted_stages(args,report)
        report.update(status="cpu_release_continuation_passed_pending_gpu",stage="gpu_continuation")
    except BaseException as error:report.update(status="cpu_release_continuation_rejected_or_interrupted",stop_reason=f"{type(error).__name__}: {error}")
    try:retained.save(args,report)
    except OSError as error:report["terminal_publication_error"]=str(error)
    notify(args,report)
    return 0 if report["status"]=="cpu_release_continuation_passed_pending_gpu" else 1


def self_test(args):
    from unittest.mock import patch
    expected=[]
    for stage in plan(args):
        if not stage["adopted"]:expected.append((stage["name"],"run"))
        expected.append((stage["name"],"review"))
        if stage["name"].endswith("_h"):expected.append((stage["window"],"half"))
    assert len([x for x in expected if x[1]=="run"])==2 and all(x[0].startswith(args.tag+"_spr15_") for x in expected if x[1]=="run")
    for fail in (None,*range(len(expected))):
        calls=[]
        def mark(name,kind):
            calls.append((name,kind))
            if fail is not None and len(calls)-1==fail:raise ValueError("mock stage failure")
        with patch.object(prior,"run_stage",side_effect=lambda a,r,s:mark(s["name"],"run")), \
             patch.dict(globals(),review_stage=lambda a,r,s:mark(s["name"],"review"),inherit_half=lambda a,r,w:mark(w,"half")):
            try:stages(args,{})
            except ValueError:pass
        assert calls==expected[:len(calls)] and len(calls)==(len(expected) if fail is None else fail+1)
    with patch.dict(globals(),prerequisites=lambda a:(_ for _ in ()).throw(ValueError("mock admission"))),patch(__name__+".stages") as later:
        try:admitted_stages(args,{})
        except ValueError:pass
        assert not later.called
    for answer in (prior.SimpleNamespace(returncode=0,stdout="mock"),OSError("mock"),seq.subprocess.TimeoutExpired("mock",45)):
        with patch.object(base,"save_new",side_effect=OSError("mock receipt")) as saved, \
             patch.object(retained,"save"),patch.object(seq.subprocess,"run",side_effect=[answer]) as queued:
            report=dict(status="mock");notify(args,report);notify(args,report);assert saved.call_count==queued.call_count==1
    with patch.object(Path,"exists",return_value=True),patch.object(Path,"glob",return_value=[]):
        try:fresh(args)
        except ValueError:pass
        else:raise AssertionError("Duplicate continuation admitted")
    assert inherit_half.__globals__["plan"] is plan and prior.inherit_half.__globals__["plan"] is prior.plan
    print("PASS only two fresh 15-s runs, adopted short pair, every-stage short-circuit, original globals unchanged, duplicate/once-queue mocks; no artifacts")


def main():
    parser=argparse.ArgumentParser(description=__doc__);mode=parser.add_mutually_exclusive_group(required=True)
    for key in ("self-test","dry-run","worker"):mode.add_argument("--"+key,action="store_true")
    parser.add_argument("--tag",default="hg_release_continue_r2");parser.add_argument("--binary-label",default="hg_release_rel_r3")
    parser.add_argument("--bench-check",default="hg_release_bench_r2");parser.add_argument("--debug-run",default="hg_release_dbg03_r2")
    parser.add_argument("--thread",default=prior.THREAD);parser.add_argument("--codex",default=prior.CODEX)
    args=parser.parse_args()
    for value in (args.tag,args.binary_label,args.bench_check,args.debug_run):event.old.label(value)
    if args.self_test:self_test(args);return 0
    gate.require(args.thread==prior.THREAD and Path(args.codex).is_file(),"Verified current-thread callback required")
    if args.dry_run:
        fresh(args);exe,records,adopted=prerequisites(args)
        print(json.dumps(dict(status="checked_not_prepared_or_run",executable=exe,prerequisites=len(records),
            adopted=list(adopted),fresh=[s["name"] for s in plan(args) if not s["adopted"]],
            offline_rechecks_still_required=True,solver_launched=False,notification_sent=False)));return 0
    return worker(args)


if __name__=="__main__":raise SystemExit(main())
