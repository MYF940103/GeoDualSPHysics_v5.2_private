"""Observe only saved prefix2s of a retired job; never create solver completion."""
from __future__ import annotations
import argparse
import csv
from fractions import Fraction
import math
import os
from pathlib import Path
import re
import shutil
import struct
import sys
sys.dont_write_bytecode=True
import upl_tpi_gpu_full2tv_native_r1 as original
import upl_tpi_cpu_build_r2 as b

T,L,S=b.T,b.L,b.S
TAG="upl_tpi_gpu_partial2s_native_r1"
SCRIPT=Path(__file__).resolve();CPP=T/"support"/(TAG+".cpp");NOTE=T/"notes"/(TAG+".md")
BASE,COMPILE,LINK,NEUTRAL=original.BASE,original.COMPILE,original.LINK,original.NEUTRAL
BUILDROOT=T/"outputs"/(TAG+"_build");BUILD=L/(TAG+".build.json");PROGRAM=BUILDROOT/(TAG+".exe")
SOURCE_TAG="upl_tpi_gpu_Release_B_full2tv_r1"
START=L/(SOURCE_TAG+".start.json");RUN_AD=L/(SOURCE_TAG+".run_admission.json")
STOP_REQUEST=L/(SOURCE_TAG+".timestep_retirement_r1.request.json")
STOP_RESULT=L/(SOURCE_TAG+".timestep_retirement_r1.result.json")
SOURCE_BUILD=L/"upl_tpi_gpu_full2tv_Release_r1.build.json"
OUTPUT=T/"outputs"/SOURCE_TAG;DATA=OUTPUT/"data"
NATIVE_OUT=T/"outputs"/(SOURCE_TAG+"_observed_partial_2s_native_r1")
DT=original.DT;FULL_STEPS=11661219;FULL_END=72.88428689946836
PROFILE=dict(steps=320001,frames=1292,end=2.0000520265024098,post=1174)
WINDOWS={"observed_partial_2s":PROFILE}
SIDECAR_COLUMNS=original.SIDECAR_COLUMNS
PTX_TAG,PTX_BINDING,PTX_COMPILE=original.PTX_TAG,original.PTX_BINDING,original.PTX_COMPILE
bits,finite,f32,pressure_f32_ftz=original.bits,original.finite,original.f32,original.pressure_f32_ftz
environment,no_active_reader=original.environment,original.no_active_reader


class Admission:
    def __init__(self,action,path):
        self.entry,self.data=b.stat(path),b.read(path)
        b.need(self.data.get("stage")==TAG+"."+action+"_admission" and self.data.get("passed")is True
               and self.data.get("action_only")is True,"One root-read exact-action admission required")
        self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]};self.consumed={}
        b.need(len(self.frozen)==len(self.data["inputs"]),"Duplicated admitted input")
        for p in (SCRIPT,CPP,NOTE,Path(b.__file__),Path(original.__file__),NEUTRAL):self.pin(p)
    def pin(self,p):
        key=str(Path(p).resolve());b.need(key in self.frozen,"Unadmitted observation input: "+key)
        self.consumed[key]=b.same(self.frozen[key]);return self.consumed[key]
    def finish(self):
        for e in self.consumed.values():b.same(e)
        b.same(self.entry);return list(self.consumed.values())


def get_job(ad):
    for p in (START,RUN_AD,STOP_REQUEST,STOP_RESULT,SOURCE_BUILD):ad.pin(p)
    start,runad,request,stopped,built=[b.read(p)for p in (START,RUN_AD,STOP_REQUEST,STOP_RESULT,SOURCE_BUILD)]
    b.need(start["stage"]==SOURCE_TAG+".start" and runad.get("passed")is True and runad.get("one_job_only")is True
           and runad["job"]==dict(tag=SOURCE_TAG,configuration="Release",scheme="B",window="full2tv"),"Original start/admission profile differs")
    for e in (start["root_admission"],start["source_build"],start["program"],start["plan"],request["source_start"],stopped["request"]):ad.pin(e["path"]);b.same(e)
    b.need(Path(start["root_admission"]["path"]).resolve()==RUN_AD.resolve() and Path(start["source_build"]["path"]).resolve()==SOURCE_BUILD.resolve()
           and Path(request["source_start"]["path"]).resolve()==START.resolve() and Path(stopped["request"]["path"]).resolve()==STOP_REQUEST.resolve(),"Original evidence bindings differ")
    b.need(request["intentional_retirement"]is True and request["requested_order"]==["owner","target"]
           and request["requested_TerminateProcess_exit"]==0xC000013A and request["requested_exit_is_external_not_original_solver_return"]is True
           and stopped["passed"]is True and stopped["owner_stopped_before_solver_action"]is True and stopped["all_outputs_preserved"]is True
           and stopped["solver_reruns"]==stopped["queue_invocations"]==0 and stopped["notifier_rearmed"]is False
           and stopped["unsaved_native_time_inferred"]is False,"Genuine intentional owner-first retirement required")
    for role,pid in (("owner",38740),("target",41920)):
        native=request["processes"][role];old=native["original"];exit=stopped["actual_exit_captures"][role]
        b.need(old==start[role] and old["pid"]==pid and native["initial_actual_Win32_exit"]==exit["exit_before_external_stop"]==259
               and exit["external_terminate_requested"]is True and exit["actual_Win32_exit"]==0xC000013A
               and native["native_creation_FILETIME_ticks"]==exit["creation_FILETIME_ticks"]
               and abs((exit["creation_FILETIME_ticks"]-116444736000000000)/1e7-old["created"])<=1e-6,"Actual original native handle/creation/exit differs: "+role)
    b.need(start["target"]==start["tool"] and start["target"]["parent"]==start["owner"]["pid"]
           and Path(start["target"]["exe"]).resolve()==Path(start["program"]["path"]).resolve()
           and start["target"]["argv"][1:]==start["arguments"] and start["actual_environment"]=={"UPL_TPI_GPU_R1":"B"},"Original direct GPU ownership/argv/selector differs")
    b.need(not any((L/(SOURCE_TAG+suffix)).exists()for suffix in (".call.json",".run.json",".queue_attempt.json"))
           and stopped["original_final_run_receipt_exists"]is False and stopped["queue_attempt_exists"]is False,
           "Missing final source run must remain missing; no replacement receipt or queue is allowed")
    b.need(built["passed"]is True and built["configuration"]=="Release" and built["stage"]=="upl_tpi_gpu_full2tv_build_r1"
           and {k:built["program"][k]for k in ("path","bytes","mtime_ns")}==start["program"] and built["object_count"]==111
           and built["consumed_stats_unchanged"]is True,"Original actual passed program/build differs")
    ad.pin(built["source_prepare"]["path"]);b.same(built["source_prepare"])
    prep=b.read(built["source_prepare"]["path"]);b.need(prep["passed"]is True and prep["stage"]=="upl_tpi_gpu_full2tv_r1.prepare","Original full-window source preparation differs")
    for e in runad["required_passed_checks"]:ad.pin(e["path"]);b.same(e);b.need(b.read(e["path"]).get("passed")is True,"Original implementation prerequisite did not pass")
    source_inputs={str(Path(e["path"]).resolve()):e for e in runad["inputs"]}
    prefix=Path(start["input_prefix"])
    for p in (prefix.with_suffix(".xml"),prefix.with_suffix(".bi4"),Path(str(prefix)+"_Normals.nbi4")):
        key=str(p.resolve());b.need(key in source_inputs,"Original seed absent from original admission");ad.pin(p);b.same(source_inputs[key])
    for e in built["runtime"]:ad.pin(e["destination"]["path"]);b.same(e["destination"])
    b.need(Path(start["output_directory"]).resolve()==OUTPUT.resolve() and stopped["raw_BI4_count"]==len(stopped["retained_raw_BI4_files"])==1353,"Original output/retained file manifest differs")
    entries=stopped["retained_raw_BI4_files"]
    b.need([Path(e["path"]).name for e in entries]==["Part_%04d.bi4"%i for i in range(1353)],"Retained original raw sequence differs")
    for e in entries[:PROFILE["frames"]]:ad.pin(e["path"]);b.same(e)
    for key in ("console_stat","Run_out_stat"):ad.pin(stopped[key]["path"]);b.same(stopped[key])
    b.need(stopped["first_actual_console_exception"]is None and stopped["first_actual_Run_out_exception"]is None,"Original recorded runtime exception requires diagnosis")
    return dict(tag=SOURCE_TAG,window="observed_partial_2s",scheme="B",backend="GPU",configuration="Release",profile=PROFILE,
        output_directory=str(OUTPUT),data=str(DATA),plan=start["plan"],source_build=start["source_build"],native_output=str(NATIVE_OUT),source_start=b.stat(START),
        source_retirement_request=b.stat(STOP_REQUEST),source_retirement_result=b.stat(STOP_RESULT),
        source_actual_exit_captures=stopped["actual_exit_captures"],source_full_completed=False,source_final_run_receipt_exists=False,
        observed_raw_prefix_files=1292,retained_raw_manifest_count=1353,later_raw_files_not_certified=61,partial_observation=True,
        last_original_console_PART_line=stopped["last_original_console_PART_line"],last_original_Run_out_PART_line=stopped["last_original_Run_out_PART_line"])


def load_plan(ad,job):
    ad.pin(job["plan"]["path"])
    with Path(job["plan"]["path"]).open(encoding="utf-8-sig",newline="")as f:
        reader=csv.DictReader(f);b.need(reader.fieldnames=="part,completed_steps,saved_step,time_s,dt_s,post_open_by_completed_step,target_time_s,forced_final".split(","),"Original eight-column full plan differs");all_rows=list(reader)
    b.need(len(all_rows)==1682 and int(all_rows[-1]["completed_steps"])==FULL_STEPS and bits(float(all_rows[-1]["time_s"]))==bits(FULL_END),"Original full1682 plan endpoint differs")
    rows=all_rows[:1292];needed={0}|{int(r["completed_steps"])for r in rows}|{max(0,int(r["completed_steps"])-1)for r in rows};clock={0:0.}
    time=0.;index=1
    for n in range(1,FULL_STEPS+1):
        time+=DT
        if n in needed:clock[n]=time
        if index<len(all_rows) and n==int(all_rows[index]["completed_steps"]):
            r=all_rows[index];b.need(int(r["part"])==index and int(r["saved_step"])==n-1 and bits(float(r["time_s"]))==bits(time)
                and bits(float(r["dt_s"]))==bits(DT) and int(r["post_open_by_completed_step"])==int(n>1600),"Original full plan scalar/identity differs");index+=1
    b.need(index==1682 and int(rows[-1]["completed_steps"])==320001 and bits(float(rows[-1]["time_s"]))==bits(PROFILE["end"])
           and rows[-1]["forced_final"]=="0" and sum(int(r["post_open_by_completed_step"])for r in rows)==1174,"Original observed prefix selection differs")
    return rows,clock


def read_native(ad,job,result):
    pin_reader(ad);out=Path(job["native_output"]);cp=L/(TAG+".read.call.json");log=L/(TAG+".read.log")
    b.need(not out.exists()and not cp.exists()and not log.exists(),"Existing/partial observation read protected; never decode twice")
    import psutil
    ad.pin(psutil.__file__);no_active_reader(PROGRAM,job["data"]);env=os.environ.copy()
    for key in ("UPL_TPI_GPU_R1","UPL_TPI_CPU_R1","UPL_TPI_M0_DT_R1"):env.pop(key,None)
    ad.finish()
    try:
        call,_=b.invoke(TAG+".read",[str(PROGRAM),"--read","GPU",job["data"],job["plan"]["path"],job["window"],str(out)],BUILDROOT,env)
    finally:
        if cp.is_file():
            actual=b.read(cp);result["reader_call"]=b.stat(cp)
            result["reader_invocations"]=int(isinstance(actual.get("child"),dict))
            result["reader_actual_Popen_wait_exit"]=actual.get("actual_Popen_wait_exit")
            result["reader_actual_Win32_exit"]=actual.get("actual_Win32_exit")
    done=b.read(out/"completion.json")
    b.need(done["passed"]is True and done["stage"]==TAG and done["window"]=="observed_partial_2s"
           and done["partial_observation"]is True and done["source_full_completed"]is False and done["observed_prefix_complete"]is True
           and done["samples"]==1292 and done["planned_completed_steps"]==320001 and done["post_open_frames"]==1174
           and bits(done["actual_end_s"])==bits(PROFILE["end"]),"Observed-only native declaration differs")
    result.update(passed=True,reader_call=call,reader_invocations=1,native_output=str(out),completion=done,
        products=[b.stat(p)for p in out.iterdir()if p.is_file()],consumed=ad.finish(),source_full_completed=False,partial_observation=True)


def review(ad,job,result):
    pin_reader(ad);receipt=L/(TAG+".read.json");ad.pin(receipt);decoded=b.read(receipt)
    b.need(decoded["passed"]is True and decoded["reader_invocations"]==1 and decoded["native_output"]==job["native_output"],"One actual completed prefix read required")
    ad.pin(decoded["reader_call"]["path"]);b.same(decoded["reader_call"]);call=b.read(decoded["reader_call"]["path"])
    b.need(call["passed"]is True and call["actual_Popen_wait_exit"]==call["actual_Win32_exit"]==0,"Actual prefix reader exits differ")
    for p in Path(job["native_output"]).iterdir():
        if p.is_file():ad.pin(p)
    plan,clock=load_plan(ad,job)
    result["actual_retained_pressure_PTX"]=ptx_evidence(ad,job)
    result["pressure_sidecar_observed_prefix"]=sidecar(ad,job,plan,clock)
    result.update(passed=True,reader_invocations=0,completion=decoded["completion"],consumed=ad.finish(),consumed_stats_unchanged=True,
        all22_original_prefix_guards_not_relaxed=True,original_signed_guard_preserved=True,source_full_completed=False,partial_observation=True,
        selected_native_frames=1292,later_original_frames_not_certified=True,full_solver_final_HG_summary_available=False,
        new_byte_prefix_chain_performed=False,raw22_all_array_bitproof_claimed=False,physical_theory_full_or_half_acceptance=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("action",choices=("build","read","review"))
    parser.add_argument("--admission",type=Path,required=True);parser.add_argument("--execution-authorized",action="store_true")
    args=parser.parse_args();b.need(args.execution_authorized,"One exact-action root admission required");ad=Admission(args.action,args.admission)
    if args.action=="build":build(ad);return 0
    receipt=L/(TAG+"."+args.action+".json");b.need(not receipt.exists(),"Existing observation receipt/failure protected")
    result=dict(stage=TAG+"."+args.action,passed=False,solver_invocations=0,build_invocations=0,reader_invocations=0,VTK_invocations=0,
        SHA_scans=0,source_full_completed=False,partial_observation=True,physical_acceptance=False,automatic_follow_up=False)
    try:
        result["root_admission"]=ad.entry;job=get_job(ad);result["job"]=job
        (read_native if args.action=="read"else review)(ad,job,result)
    except Exception as exc:result.update(first_error=str(exc),partials_preserved=True)
    b.write_new(receipt,result);print(str(receipt));return 0 if result["passed"]else 1



def build(ad):
    b.need(not BUILDROOT.exists() and not BUILD.exists(), "Existing reader build/failure is protected")
    for p in (BASE, COMPILE, LINK, NEUTRAL, b.VCVARS):
        ad.pin(p)
    base, compile_call, link_call = b.read(BASE), b.read(COMPILE), b.read(LINK)
    b.need(base.get("passed") is True and base.get("private_offline_reader") is True,
           "Retained successful pure-reader recipe required")
    old_object = Path(base["object"]["path"]).resolve()
    old_source = Path(base["source"]["path"]).resolve()
    old_args = compile_call["arguments"]
    link_args = link_call["arguments"]
    dependencies = [b.stat(x["path"]) for x in base["actual_archived_headers"] + base["runtime"]]
    dependencies += [b.stat(x) for x in link_args if not str(x).startswith("/")
                     and str(x).lower().endswith((".obj", ".lib"))
                     and Path(x).resolve() != old_object]
    for x in dependencies:
        ad.pin(x["path"])
    ad.pin(compile_call["program"]["path"])
    ad.pin(link_call["program"]["path"])
    BUILDROOT.mkdir()
    result = dict(stage=TAG + ".build", passed=False, root_admission=ad.entry,
                  actual_common_reader_build_helper=ad.pin(Path(b.__file__)),
                  calls=[], solver_invocations=0, reader_invocations=0,
                  old_reader_or_loader_changed=False, physical_acceptance=False)
    try:
        env, batch = environment(TAG, BUILDROOT, result["calls"])
        obj = BUILDROOT / "reader.obj"
        dep = BUILDROOT / "dependencies.json"
        args, skip, source_removed = [], False, 0
        for x in old_args:
            if skip:
                skip = False
                continue
            if x.lower() == "/sourcedependencies":
                skip = True
            elif not x.startswith("/") and Path(x).resolve() == old_source:
                source_removed += 1
            elif x.lower().startswith(("/fo", "/fd")):
                continue
            else:
                args.append(x)
        b.need(source_removed==1,"Actual structured compile argv must contain one complete original source token")
        args += ["/Fo" + str(obj), "/Fd" + str(BUILDROOT / "reader.pdb"),
                 "/sourceDependencies", str(dep), str(CPP)]
        call, _ = b.invoke(TAG + ".compile", [compile_call["program"]["path"], *args], S / "VS", env)
        result["calls"].append(call)
        dependency_data=b.read(dep)["Data"]
        b.need(Path(dependency_data["Source"]).resolve()==CPP.resolve(), "Actual reader dependency Source differs from the single full-path CPP argument")
        included = {Path(x).resolve() for x in dependency_data["Includes"]}
        b.need(NEUTRAL.resolve() in included and all(not p.is_relative_to((S / "source").resolve()) for p in included),
               "Reader missed its retained neutral loader or consumed live source headers")
        args = []
        for x in link_args:
            if x.lower().endswith(".obj") and not x.startswith("/") and Path(x).resolve() == old_object:
                args.append(str(obj))
            elif x.lower().startswith("/out:"):
                args.append("/OUT:" + str(PROGRAM))
            elif x.lower().startswith(("/pdb:", "/implib:", "/ltcgout:", "/ilk:", "/pgd:")):
                prefix = x.split(":", 1)[0]
                ext = {"/pdb": ".pdb", "/implib": ".lib", "/ltcgout": ".iobj", "/ilk": ".ilk", "/pgd": ".pgd"}[prefix.lower()]
                args.append(prefix + ":" + str(BUILDROOT / ("reader" + ext)))
            else:
                args.append(x)
        args.append("/ILK:" + str(BUILDROOT / "reader.ilk"))
        call, _ = b.invoke(TAG + ".link", [link_call["program"]["path"], *args], S / "VS", env)
        result["calls"].append(call)
        copies = []
        for entry in base["runtime"]:
            target = BUILDROOT / Path(entry["path"]).name
            shutil.copy2(entry["path"], target)
            copies.append(dict(source=b.stat(entry["path"]), destination=b.stat(target)))
        for entry in dependencies:
            b.same(entry)
        ad.finish()
        result.update(passed=True, program=b.stat(PROGRAM), object=b.stat(obj),
                      compiler_dependencies=b.stat(dep), environment_batch=batch,
                      runtime=copies, original_dependencies=dependencies,
                      original_dependencies_stats_unchanged=True, SHA_scans=0)
    except Exception as exc:
        result["failure"] = str(exc)
        raise
    finally:
        b.write_new(BUILD, result)


def pin_reader(ad):
    """Bind this observed-prefix reader program/runtime, never source completion."""
    ad.pin(BUILD); built = b.read(BUILD)
    b.need(built.get("stage") == TAG + ".build" and built.get("passed") is True and
           built.get("solver_invocations") == built.get("reader_invocations") == 0 and
           built.get("old_reader_or_loader_changed") is False and
           built.get("original_dependencies_stats_unchanged") is True,
            "Independent observed-prefix reader implementation build is required")
    ad.pin(PROGRAM); b.same(built["program"])
    b.need(Path(built["program"]["path"]).resolve() == PROGRAM.resolve(),
            "Actual observed-prefix reader program path differs")
    for entry in built["runtime"]:
        ad.pin(entry["destination"]["path"]); b.same(entry["destination"])
    return built


def ptx_evidence(ad, job):
    # Read the one genuinely dumped new object; no cuobjdump/reader/program invocation.
    ad.pin(PTX_BINDING); binding = b.read(PTX_BINDING)
    b.need(binding.get("stage") == PTX_TAG + ".binding" and binding.get("passed") is True and
           binding.get("object_and_tool_stat_unchanged") is True and
           all(binding.get(k) == 0 for k in ("solver_invocations", "GPU_kernel_invocations", "reader_invocations", "build_invocations", "SHA_scans")),
           "Actual read-only PTX object/tool evidence is required")
    for key in ("input_object", "actual_tool", "call"):
        ad.pin(binding[key]["path"]); b.same(binding[key])
    call = b.read(binding["call"]["path"])
    b.need(call.get("passed") is True and call.get("actual_Popen_wait_exit") == call.get("actual_Win32_exit") == 0 and
           call["arguments"] == ["--dump-ptx", binding["input_object"]["path"]] and
           Path(call["program"]["path"]).resolve() == Path(binding["actual_tool"]["path"]).resolve() and
           Path(call["program"]["path"]).name.lower() == "cuobjdump.exe",
           "Actual cuobjdump command/exits differ")
    ad.pin(call["log"]["path"]); b.same(call["log"])
    # The source was intentionally retired and has NO final run receipt.
    ad.pin(job["source_build"]["path"]);b.same(job["source_build"])
    build = b.read(job["source_build"]["path"])
    obj = [e for e in build["objects"] if Path(e["path"]).resolve() == Path(binding["input_object"]["path"]).resolve()]
    b.need(len(obj) == 1 and {k: obj[0][k] for k in ("path", "bytes", "mtime_ns")} == binding["input_object"],
           "This actual solver build does not contain the dumped CUDA object")
    ad.pin(PTX_COMPILE); compiled = b.read(PTX_COMPILE)
    args = compiled["arguments"]
    b.need(compiled.get("passed") is True and compiled.get("actual_Popen_wait_exit") == compiled.get("actual_Win32_exit") == 0 and
           "-use_fast_math" in args and args[args.index("-o")+1] == binding["input_object"]["path"],
           "Actual CUDA compile flags/output do not match the PTX object")
    lines = Path(call["log"]["path"]).read_text(encoding="utf-8", errors="strict").splitlines()
    found = {}
    for name in ("BeginRowsKernel", "GuessKernel", "PrepareKernel"):
        starts = [i for i, line in enumerate(lines) if ".entry" in line and name in line]
        b.need(len(starts) == 1, "Actual private PTX entry is not unique: " + name)
        start = starts[0]
        end = next((i for i in range(start+1, len(lines)) if ".entry" in lines[i]), len(lines))
        body = lines[start:end]
        casts = [start+i+1 for i, line in enumerate(body) if "cvt.rn.ftz.f32.f64" in line]
        b.need(len(casts) == 1, "Actual pressure conversion is not one RN-f32 FTZ: " + name)
        input_casts = [start+i+1 for i, line in enumerate(body) if "cvt.ftz.f64.f32" in line]
        b.need(len(input_casts) == {"BeginRowsKernel": 2, "GuessKernel": 0, "PrepareKernel": 1}[name],
               "Actual float-input FTZ conversion count differs: " + name)
        found[name] = dict(entry_line=start+1, pressure_cast_line=casts[0], float_input_FTZ_lines=input_casts)
        if name == "PrepareKernel":
            b.need(sum("div.rn.f64" in x for x in body) == 1 and sum("add.rn.f64" in x for x in body) == 1 and
                   not any("div.approx" in x or "rcp." in x or "fma." in x for x in body),
                   "Actual raw correction must retain separate RN-double divide/add, not an inferred FMA/approx path")
            found[name].update(double_divide_line=start+next(i for i,x in enumerate(body) if "div.rn.f64" in x)+1,
                               double_add_line=start+next(i for i,x in enumerate(body) if "add.rn.f64" in x)+1)
    return dict(actual_binding=ad.pin(PTX_BINDING), actual_call=ad.pin(binding["call"]["path"]), actual_PTX=ad.pin(call["log"]["path"]),
                entry_instructions=found, model="RN_f32_then_sign_preserving_result_FTZ", pressure_added_ULP_tolerance=0,
                double_prediction_and_J_arithmetic_changed=False, solver_reader_or_tool_invocations=0)


def sidecar(ad, job, plan, clock):
    output = Path(job["output_directory"])
    paths = [output / ("UplTpiGpuR1" + suffix) for suffix in (".policy.json", ".csv")]
    b.need(not (output / "UplTpiGpuR1.summary.json").exists(), "Stopped source must not acquire a fabricated full completion summary")
    if job["scheme"] == "A":
        b.need(not any(p.exists() for p in paths), "Untaken default-A branch must not create TPI sidecars")
        return dict(expected_absent=True, native_scheme_evidence="Actual owned environment plus default-A branch")
    for p in paths:
        ad.pin(p)
    policy = b.read(paths[0])
    scheme = "B_TPI_alpha_0p5_beta0" if job["scheme"] == "B" else "C_PPE_t_alpha0_beta0"
    alpha = .5 if job["scheme"] == "B" else 0.
    b.need(policy.get("stage") == "upl_tpi_gpu_r1" and policy.get("scheme") == scheme
           and policy.get("alpha") == alpha and policy.get("beta") == 0 and policy.get("M0") is True
           and policy.get("native_count") == 1040 and policy.get("soil_count") == 1000
           and policy.get("history_ID_owned") is True and policy.get("history_cold_start") is True
           and policy.get("half_equals_endpoint_history_guess") is True
           and policy.get("endpoint_source_clock_is_original_n") is True,
           "Actual private M0 scheme/history policy differs")
    for document in (policy,):
        b.need(document.get("full_restart_supported") is False and document.get("paper_literal_LF") is False
               and document.get("second_order_claimed") is False and document.get("true_implicit_solution") is False
               and document.get("physical_acceptance") is False, "Prototype limits must remain explicit")
    w = PROFILE
    rowcount, max_rounding = 0, 0.
    observed_input_subnormals = dict(pn=0, previous=0, endpoint_q=0)
    J_nonfused_matches = J_fused_matches = J_both_matches = 0
    import numpy as np
    physical = Path(job["native_output"]) / "physical.bin"
    with paths[1].open(encoding="utf-8-sig", newline="") as f, physical.open("rb") as native:
        reader = csv.DictReader(f)
        b.need(reader.fieldnames == SIDECAR_COLUMNS, "Exact 28-column sidecar schema differs")
        b.need(struct.unpack("<III", native.read(12)) == (1000, 26, w["frames"]), "Case02 physical export header differs")
        for part, planned in enumerate(plan):
            n = int(planned["completed_steps"])
            actual_time = struct.unpack("<d", native.read(8))[0]
            state = np.frombuffer(native.read(1000 * 26 * 8), dtype="<f8").reshape(1000, 26)
            b.need(bits(actual_time) == bits(clock[n]), "Sidecar/native actual saved time differs")
            seen, source_count, endpoint_count, commit_count = set(), 0, 0, 0
            for _ in range(1000):
                row = next(reader, None)
                b.need(row is not None and list(row) == SIDECAR_COLUMNS, "Missing/extra sidecar columns or rows")
                values = {k: finite(v) for k, v in row.items()}
                k = int(values["native_id"])
                b.need(values["native_id"] == k and 40 <= k < 1040 and k not in seen and values["part"] == part,
                       "Sidecar native ownership/part duplicated or changed")
                seen.add(k)
                b.need(values["completed_step"] == values["commits"] == values["endpoint_calls"] == n
                       and values["source_step_zero_based"] == (n - 1 if n else 0)
                       and values["core_field_bit_checks"] == 7000 * n and values["hg_snapshot_checks"] == 2000 * n
                       and bits(values["source_time_s"]) == bits(clock[n - 1 if n else 0])
                       and bits(values["actual_save_time_s"]) == bits(clock[n]) and values["dt_s"] == DT,
                       "Saved actual source/commit/history counters or scalar clock differ")
                final, J = state[k - 40, 6], state[k - 40, 8]
                b.need(bits(values["final_float_Pa"], "f") == bits(final, "f")
                       and bits(values["Jfull"]) == bits(J), "Saved sidecar pressure/J differs from native state")
                flags = [values[x] for x in ("source_drained", "endpoint_drained", "commit_drained")]
                b.need(all(x in (0., 1.) for x in flags), "Dirichlet flags are not exact booleans")
                source_count += int(flags[0]); endpoint_count += int(flags[1]); commit_count += int(flags[2])
                if not n:
                    b.need(all(values[x] == 0. for x in ("pn_Pa", "previous_Pa", "prediction_double_Pa", "half_actual_float_Pa", "endpoint_q_actual_float_Pa", "S_1_per_m_s", "Rgamma_Pa_per_m_s", "raw_final_float_Pa", "final_float_Pa"))
                           and values["Jn"] == values["Jhalf"] == values["Jfull"] == 1., "Cold initial sidecar state differs")
                    rowcount += 1
                    continue
                # PTX cvt.ftz.f64.f32 preserves normal float inputs but flushes
                # a subnormal float to signed zero BEFORE ordinary RN-double math.
                for label, field in (("pn", "pn_Pa"), ("previous", "previous_Pa"), ("endpoint_q", "endpoint_q_actual_float_Pa")):
                    observed = f32(values[field])
                    observed_input_subnormals[label] += int(0. < abs(observed) < 2.**-126)
                pn_input, previous_input = pressure_f32_ftz(values["pn_Pa"]), pressure_f32_ftz(values["previous_Pa"])
                prediction = pn_input if alpha == 0 else pn_input + alpha * (pn_input - previous_input)
                b.need(bits(values["prediction_double_Pa"]) == bits(prediction), "Actual history pressure prediction differs")
                half = 0. if flags[0] else pressure_f32_ftz(prediction)
                b.need(bits(values["half_actual_float_Pa"], "f") == bits(half, "f"), "Mechanical half pressure history/Dirichlet differs")
                diagonal, residual, q = (values[x] for x in ("S_1_per_m_s", "Rgamma_Pa_per_m_s", "endpoint_q_actual_float_Pa"))
                b.need(bits(q, "f") == bits(0. if flags[1] else pressure_f32_ftz(prediction), "f"),
                       "Actual endpoint q is not the same history prediction under original endpoint BC")
                if flags[1]:
                    b.need(diagonal == residual == 0., "A constrained endpoint row must not claim an elliptic residual")
                    raw = 0.
                else:
                    b.need(diagonal > 0., "Nonpositive/nonfinite elliptic diagonal is not masked or regularized")
                    q_input = pressure_f32_ftz(q)  # Actual cvt.ftz.f64.f32 before div.rn/add.rn.
                    exact = q_input + residual / diagonal
                    raw = pressure_f32_ftz(exact)
                    max_rounding = max(max_rounding, abs(raw - exact))
                b.need(bits(values["raw_final_float_Pa"], "f") == bits(raw, "f")
                       and bits(values["final_float_Pa"], "f") == bits(0. if flags[2] else raw, "f"),
                       "Actual beta0 float writeback or original final Dirichlet policy differs")
                # Preserve original CUDA -use_fast_math/fmad. Original expression
                # is left-associated DT*Jhalf*theta followed by add to Jn.
                # First product is rounded binary64. Final multiply/add can be
                # separate or legally fused, both replayed exactly, no ULP slack.
                product = DT * values["Jhalf"]
                plain = values["Jn"] + product * values["theta_half_for_J_1_per_s"]
                fused = float(Fraction.from_float(values["Jn"]) + Fraction.from_float(product) *
                              Fraction.from_float(values["theta_half_for_J_1_per_s"]))
                nmatch = bits(values["Jfull"]) == bits(plain)
                fmatch = bits(values["Jfull"]) == bits(fused)
                b.need(nmatch or fmatch, "Original CUDA single J expression matches neither reviewed exact compiler path")
                J_nonfused_matches += int(nmatch); J_fused_matches += int(fmatch)
                J_both_matches += int(nmatch and fmatch)
                rowcount += 1
            expected_drain = 10 if n > 1600 else 0
            b.need(len(seen) == 1000 and source_count == endpoint_count == commit_count == expected_drain,
                   "All actual source/endpoint/commit Dirichlet owner counts differ")
        # Read only the declared saved prefix. Later CSV rows exist in the
        # retained stopped source and are deliberately not consumed/certified.
        b.need(native.read(1) == b"", "Extra native records beyond selected1292 prefix")
    return dict(rows=rowcount, expected_rows=1000 * w["frames"], actual_ID_owned_history=True,
                partial_observation=True,source_full_completed=False,source_summary_absent=True,
                subsequent_source_CSV_rows_consumed_or_certified=False,
                actual_M0_alpha=alpha, beta=0, max_actual_pressure_float_writeback_rounding_Pa=max_rounding,
                per_saved_row_formula_and_J_corrector_checked=True,
                J_noninitial_rows_checked=J_nonfused_matches + J_fused_matches - J_both_matches,
                J_nonfused_path_matches=J_nonfused_matches, J_fused_path_matches=J_fused_matches,
                J_both_paths_match=J_both_matches, J_added_ULP_tolerance=0,
                original_CUDA_fast_math_and_fmad_preserved=True,
                actual_pressure_cast_RN_f32_signed_FTZ=True, actual_float_input_to_double_signed_FTZ=True,
                observed_nonzero_subnormal_pressure_inputs=observed_input_subnormals,
                input_subnormal_count_is_descriptive_not_a_physical_limit=True, pressure_added_ULP_tolerance=0,
                unsaved_history_values_independently_observed=False,
                PorePressRate_is_legacy_scaled_endpoint_residual_not_actual_dpdt=True,
                no_finite_Kw_or_half_equivalence_claim=True)


if __name__=="__main__":raise SystemExit(main())
