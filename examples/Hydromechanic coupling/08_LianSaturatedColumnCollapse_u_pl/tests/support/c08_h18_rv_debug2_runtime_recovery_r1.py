"""Offline recovery of the one completed Debug2 run's known policy-type check failure."""
import argparse
import re
import struct
from pathlib import Path
import c08_h18_rv_gpu_run_r2 as future

m,T,L=future.m,future.T,future.L
TAG="c08_h18_rv_debug2_runtime_recovery_r1"
SCRIPT=Path(__file__).resolve();NOTE=T/"notes"/(TAG+".md")
OLD=L/"c08_h18_rv_debug2_GPU_r1.run.json"
OUT=L/"c08_h18_rv_debug2_GPU_r1.runtime_review_r1.check.json"
KNOWN="Actual schema2 RV policy differs"

def transformed(text):
    edits=[('"""Prepare/run one separately root-admitted H1.8 RV GPU profile; no reader/VTK/next job."""','"""Future root-admitted RV Release window only; prior OFF/Debug results stay protected."""'),
        ("import shutil\n","import shutil\nimport struct\n"),
        ("notes/c08_h18_rv_gpu_run_r1.md","notes/c08_h18_rv_gpu_run_r2.md"),
        ("kernel_h_sph_float=m.f32(.072)",'kernel_h_sph_float=struct.unpack("<f",struct.pack("<f",.072))[0]'),
        ("choices=tuple(JOBS),required=True",'choices=("window",),required=True')]
    for old,new in edits:
        m.need(text.count(old)==1,"Nonunique intended future-runner text replacement")
        text=text.replace(old,new)
    return text

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument("--execution-authorized",action="store_true");args=a.parse_args()
    m.need(args.execution_authorized,"Root-reviewed offline recovery only")
    m.need(not OUT.exists(),"Existing runtime recovery protected; no repeat/overwrite")
    consumed=[]
    def add(entry):
        q=m.bind(entry)
        if q not in consumed:consumed.append(q)
        return Path(q["path"])
    def fresh(path):return add(m.stat(path))
    original=fresh(OLD);run=m.read(original)
    result=dict(stage=TAG,passed=False,original_run=m.stat(original),original_run_preserved=True,
        original_passed_false_preserved=True,known_original_failure=KNOWN,solver_invocations=0,
        reader_invocations=0,VTK_invocations=0,GenCase_invocations=0,SHA_scans=0,
        native_review_pending=True,physical_acceptance=False,automatic_next_job=False,
        unsaved_state_reconstructed=False,runtime_review_only=True)
    try:
        fresh(SCRIPT);fresh(NOTE);fresh(future.SCRIPT);fresh(future.NOTE)
        m.need(run.get("passed") is False and run.get("solver_completed") is True and run.get("first_failure")==KNOWN,
            "Only the preserved named completed Debug2 post-type failure is recoverable here")
        m.need(run.get("profile")=="debug2" and run.get("solver_invocations")==run.get("solver_launch_attempts")==1
            and run.get("reader_invocations")==run.get("VTK_invocations")==run.get("GenCase_invocations")==0
            and run.get("actual_exit")==run.get("actual_Win32_exit")==run.get("actual_tool_exit")==0
            and run.get("ownership_failure") is None and run.get("solver_program_identity_matches") is True
            and run.get("consumed_stats_unchanged") is True,"Original owned run/tool completion differs")
        for entry in run["consumed"]:add(entry)
        callpath=add(run["actual_call"]);call=m.read(callpath)
        startpath=fresh(L/"c08_h18_rv_debug2_GPU_r1.start.json");start=m.read(startpath)
        prep=m.read(add(run["preparation"]))
        m.need(start["owner"]==run["owner"] and call["owner"]=={k:run["owner"][k] for k in ("pid","created_epoch")},"Original owner bindings differ")
        m.need(call["actual_Popen_wait_exit"]==call["actual_Win32_exit"]==call["actual_target_Win32_exit"]==0
            and call["ownership_failure"] is None and call["child"]["parent_pid"]==run["owner"]["pid"]
            and call["actual_target"]["parent_pid"]==call["child"]["pid"],"Actual native handle/tool/parent exits differ")
        m.need(call["child"]["creation_filetime_100ns"]>0 and call["actual_target"]["creation_filetime_100ns"]>0
            and Path(call["actual_target"]["exe"]).resolve()==Path(run["program"]["path"]).resolve()
            and call["actual_target"]["argv"]==run["solver_argv"]==start["solver_argv"]
            and call["child"]["argv"]==run["argv"]==start["argv"],"Captured actual program/argv identities differ")
        for key in ("program","source_build","source_capture","source_archive","source_pre_file","input_xml","planned_steps"):
            m.need(start[key]==run[key]==prep[key],"Frozen start/run/prepare field differs: "+key);add(run[key])
        m.need(start["preparation"]==run["preparation"] and start["root_admission"]==run["root_admission"],"Original admissions differ")
        add(run["root_admission"])
        for entry in list(run["private_sources"].values())+run["runtime"]+run["seed"]:add(entry)
        oldscript=add(prep["execution_script"]);add(prep["note"])
        m.need(transformed(oldscript.read_text(encoding="utf-8"))==future.SCRIPT.read_text(encoding="utf-8"),
            "Future runner differs beyond disclosed type/note/window-CLI substitutions")
        plan=m.table(add(run["planned_steps"]));m.need(len(plan)==len(prep["planned_rows"])==2,"Original Debug2 plan count differs")
        for i,row in enumerate(plan):
            planned=prep["planned_rows"][i]
            m.need(list(row)==["part","completed_step","saved_step","time_s","dt_s"] and int(row["part"])==i
                and int(row["completed_step"])==int(planned["completed_step"])==2000001+i
                and int(row["saved_step"])==2000000+i and float(row["time_s"])==float(planned["time_s"])
                and float(row["dt_s"])==5e-6
                and float(prep["save_source_clocks_s"][i])+5e-6==float(row["time_s"]),"Original scalar Debug2 clock/step record differs")
        m.need(run["actual_steps"]==prep["global_nsteps_limit"]==2000002 and run["saved_frames"]==run["observed_saved_files"]==2
            and run["new_updates"]==2 and run["fixed_dt_s"]==5e-6 and run["environment_override"]=={"C08_RV_H18":"1"}
            and run["planned_actual_end_s"]==float(plan[-1]["time_s"]),"Original two-update extent differs")
        out=Path(run["output"]);text=add(run["Run_out"]).read_text(encoding="utf-8-sig")
        m.need("Finished execution (code=0)." in text and "[Simulation INTERRUPTED" not in text
            and "certified same-material plastic schema/contract2" in text,"Actual normal schema2 completion absent")
        summary=future.run_summary(add(run["Run_csv"]))
        m.need(summary==run["summary"] and int(summary["Steps"])==2000002 and int(summary["PartFiles"])==2
            and int(summary["PartsOut"])==0 and "Wendland" in summary["Configuration"],"Original Run.csv coverage differs")
        parts=sorted((out/"data").glob("Part_*.bi4"));m.need([q.name for q in parts]==["Part_0000.bi4","Part_0001.bi4"],"Original PART file coverage differs")
        m.need([m.stat(q) for q in parts]==run["PARTs"],"Original saved native stat differs")
        for entry in run["PARTs"]:add(entry)
        for name in future.RVFILES:fresh(out/name)
        policy=m.read(out/future.RVFILES[0]);packed=m.f32(.072);correct=struct.unpack("<f",struct.pack("<f",.072))[0]
        m.need(isinstance(packed,bytes) and len(packed)==4 and isinstance(policy["kernel_h_sph_float"],float)
            and policy["kernel_h_sph_float"]==correct and policy["kernel_h_sph_float"]!=packed,
            "Known bytes-versus-float policy mismatch is not the observed case")
        telemetry=future.telemetry(out,future.JOBS["debug2"],prep)
        logpath=add(call["log"]);log=logpath.read_text(encoding="mbcs",errors="replace")
        errors=re.findall(r"ERROR SUMMARY: ([0-9,]+) errors",log);leaks=re.findall(r"LEAK SUMMARY: ([0-9,]+) bytes leaked in ([0-9,]+) allocations",log)
        m.need(errors and leaks and all(int(q.replace(",",""))==0 for q in errors)
            and all(int(x.replace(",",""))==int(y.replace(",",""))==0 for x,y in leaks),"Actual memcheck zero errors/leaks absent")
        m.verify(consumed)
        result.update(telemetry,passed=True,solver_completed=True,consumed_stats_unchanged=True,
            actual_call=m.stat(callpath),memcheck_actual_call=m.stat(callpath),memcheck_log=m.stat(logpath),
            memcheck_zero_errors_and_leaks=True,original_start=m.stat(startpath),preparation=run["preparation"],
            actual_steps=2000002,saved_frames=2,actual_end_s=float(plan[-1]["time_s"]),planned_steps=run["planned_steps"],
            original_actual_exit=0,original_actual_Win32_exit=0,original_actual_tool_exit=0,
            policy_type_bug=dict(key="kernel_h_sph_float",old_expected_type="bytes",old_expected_hex=packed.hex(),
                actual_type="float",actual_value=policy["kernel_h_sph_float"],correct_float32_value=correct,
                all_remaining_original_runtime_checks_passed=True),native_RV_certificate_review_pending=True)
    except Exception as error:result["first_failure"]=str(error)
    unchanged=False
    try:unchanged=all(m.stat(e["path"])==e for e in consumed)
    except Exception as error:result["terminal_stat_error"]=str(error)
    result.update(consumed=consumed,consumed_stats_unchanged=unchanged)
    if not unchanged:result["passed"]=False;result.setdefault("first_failure","Consumed stat changed during offline recovery")
    m.save(OUT,result)
    return 0 if result["passed"] else 1

if __name__=="__main__":raise SystemExit(main())
