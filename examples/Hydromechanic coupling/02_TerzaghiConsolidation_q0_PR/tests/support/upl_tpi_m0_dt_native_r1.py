"""Four independently admitted M0 timestep native profiles; build/read/review only."""
from __future__ import annotations
import argparse,csv,math,os,re,shutil,struct,sys
from fractions import Fraction
from pathlib import Path
sys.dont_write_bytecode=True
import upl_tpi_gpu_full2tv_native_r1 as original
import upl_tpi_cpu_build_r2 as b
T,L,S=b.T,b.L,b.S
TAG="upl_tpi_m0_dt_native_r1";SCRIPT=Path(__file__).resolve();CPP=T/"support"/(TAG+".cpp");NOTE=T/"notes"/(TAG+".md")
BASE,COMPILE,LINK,NEUTRAL=original.BASE,original.COMPILE,original.LINK,original.NEUTRAL
BUILDROOT=T/"outputs"/(TAG+"_build");BUILD=L/(TAG+".build.json");PROGRAM=BUILDROOT/(TAG+".exe")
EVENT=.0100002288818359375
WINDOWS={"cpu_debug2ms":dict(steps=200,frames=18,post=0),"debug2":dict(steps=2,frames=2,post=0),
         "Acontrol":dict(steps=320,frames=18,post=0),"window2s":dict(steps=199996,frames=1263,post=1159)}
A_REVIEW=L/"upl_tpi_gpu_Release_A_startup015_r1.native_review_r4.json"
A_NATIVE=T/"outputs/upl_tpi_gpu_Release_A_startup015_r1_native_r4"
SIDECAR_COLUMNS=original.SIDECAR_COLUMNS
bits,finite,f32,pressure_f32_ftz=original.bits,original.finite,original.f32,original.pressure_f32_ftz
no_active_reader,environment=original.no_active_reader,original.environment
INTERVAL_COLUMNS="part,actual_save_time_s,saved_step,completed_updates,dt_s,interval_pre,interval_cor,interval_endpoint,total_pre,total_cor,total_endpoint,interval_empty,min_force_CFL_s,min_skeleton_wave_AV_CFL_s,min_Rh_hydro_s,min_legacy_Kw_wave_CFL_reference_s,min_HG_limit_reference_s,min_selected_bound_s,max_dt_minus_bound_s".split(",")
class Admission:
    def __init__(self,action,path):
        self.entry=b.stat(path);self.data=b.read(path);self.consumed={}
        b.need(self.data.get("stage")==TAG+"."+action+"_admission" and self.data.get("passed")is True and self.data.get("action_only")is True,"One exact-action native admission required")
        self.frozen={str(Path(e["path"]).resolve()):e for e in self.data["inputs"]}
        b.need(len(self.frozen)==len(self.data["inputs"]),"Duplicate admitted input")
        for x in [SCRIPT,CPP,NOTE,Path(b.__file__),Path(original.__file__),NEUTRAL]:self.pin(x)
    def pin(self,p):
        k=str(Path(p).resolve());b.need(k in self.frozen,"Consumed input absent from root admission: "+k)
        self.consumed[k]=b.same(self.frozen[k]);return self.consumed[k]
    def finish(self):
        for e in self.consumed.values():b.same(e)
        b.same(self.entry);return list(self.consumed.values())

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
        args, skip = [], False
        for x in old_args:
            if skip:
                skip = False
                continue
            if x.lower() == "/sourcedependencies":
                skip = True
            elif x.lower().startswith(("/fo", "/fd")) or (not x.startswith("/") and Path(x).resolve() == old_source):
                continue
            else:
                args.append(x)
        args += ["/Fo" + str(obj), "/Fd" + str(BUILDROOT / "reader.pdb"),
                 "/sourceDependencies", str(dep), str(CPP)]
        call, _ = b.invoke(TAG + ".compile", [compile_call["program"]["path"], *args], S / "VS", env)
        result["calls"].append(call)
        included = {Path(x).resolve() for x in b.read(dep)["Data"]["Includes"]}
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
        if not any(x.lower().startswith("/ilk:") for x in args):args.append("/ILK:" + str(BUILDROOT / "reader.ilk"))
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


def get_job(ad):
    tag=ad.data["job"]["tag"];b.need(re.fullmatch(r"upl_tpi_m0_dt_[A-Za-z0-9_]+_r[1-9][0-9]*",tag),"Exact new M0 tag required")
    rp=L/(tag+".run.json");ad.pin(rp);run=b.read(rp);mode=run["mode"];cfg=run["configuration"];scheme=run["scheme"]
    b.need(run["stage"]in("upl_tpi_m0_dt_run_r1.run","upl_tpi_m0_dt_run_r2.run") and run["passed"] and run["solver_invocations"]==1 and not run["PART_restart"] and run["pressure_history_cold_start"],"Actual completed unique cold solver required")
    b.need((mode,cfg,scheme)in(("cpu_debug2ms","DebugCPU","B"),("debug2","Debug","B"),("Acontrol","Release","A"),("window2s","Release","B")),"Only the four declared profiles admitted")
    b.need(mode=="Acontrol" or run["event_divisor"]==1000,"This reader does not admit the future 20us profile")
    runner=run["stage"][:-4];ad.pin(T/"support"/(runner+".py"));ad.pin(T/"notes"/(runner+".md"))
    for key in ["call","program","source_build","root_admission","plan"]:ad.pin(run[key]["path"]);b.same(run[key])
    for e in run["seed"]:ad.pin(e["path"]);b.same(e)
    for e in run["runtime"]:ad.pin(e["path"]);b.same(e)
    startpath=L/(tag+".start.json");ad.pin(startpath);start=b.read(startpath);call=b.read(run["call"]["path"])
    b.need(call["passed"] and call["actual_Popen_wait_exit"]==call["actual_Win32_exit"]==0 and run["actual_Popen_wait_exit"]==run["actual_Win32_exit"]==0
      and start["owner"]==call["owner"],"Genuine solver handle exits/owner differ")
    program=run["program"];b.same(start["program"]);b.need(start["program"]==program,"Start program differs")
    if cfg=="DebugCPU":
        target=call["child"];b.need(target==start["child"] and call["native_handle_acquired_before_wait"],"Original CPU child/handle missing")
        ticks=call["original_Win32_creation_FILETIME_ticks"];b.need(target["parent"]==call["owner"]["pid"],"CPU parent owner differs")
    else:
        target=call["target"];b.need(target==start["target"]==run["target"] and call["target_handle_acquired_before_wait"]
          and call["target_actual_Win32_exit"]==run["target_actual_Win32_exit"]==0,"Original GPU target/handle missing")
        b.need(call["tool_is_solver"]==(cfg=="Release"),"Actual memcheck/tool role differs")
        ticks=call["target_creation_FILETIME_ticks"];b.need(call["child"]==start["tool"] and call["child"]["parent"]==call["owner"]["pid"],"GPU tool parent owner differs")
    b.need(Path(target["exe"]).resolve()==Path(program["path"]).resolve() and target["argv"][1:]==run["arguments"]==start["arguments"]
      and abs((ticks-116444736000000000)/1e7-target["created"])<=1e-6,"Actual program/argv/creation mismatch")
    if cfg=="Debug":
        mem=L/(tag+".memcheck.log");ad.pin(mem);b.need(re.search(r"ERROR SUMMARY:\s*0 errors",mem.read_text(encoding="utf-8-sig",errors="replace")),"Actual memcheck did not pass")
    if cfg!="DebugCPU":
        console=L/(tag+".log");ad.pin(console)
        b.need(console.read_text(encoding="utf-8-sig",errors="replace").count(original.SOURCE_FIXTURE_R2)==(0 if scheme=="A"else 1),"Actual GPU source/role fixture count differs")
    key="UPL_TPI_CPU_R1"if cfg=="DebugCPU"else"UPL_TPI_GPU_R1"
    b.need(run["actual_environment"][key]==scheme and start["actual_environment"]==call["actual_environment"]==run["actual_environment"],"Actual pressure selector differs")
    built=b.read(run["source_build"]["path"]);b.need(built["passed"] and built["configuration"]==cfg and {k:built["program"][k]for k in ("path","bytes","mtime_ns")}==program,"Matched genuine new M0 build required")
    pe=built["prepared"];ad.pin(pe["path"]);b.same(pe);prep=b.read(pe["path"])
    b.need(prep["passed"] and prep["stage"]=="upl_tpi_m0_dt_r2.prepare" and prep["backend"]==("CPU"if cfg=="DebugCPU"else"GPU"),"Actual new source closure differs")
    source_header=Path(prep["source_root"])/"upl_tpi_m0_dt_r2.h";ad.pin(source_header)
    output=Path(run["output_directory"]);plan=Path(run["plan"]["path"]);ad.pin(output/"Run.out")
    dt=original.DT if scheme=="A"else EVENT/1000.
    rows=list(csv.DictReader(plan.open(encoding="utf-8-sig",newline="")))
    p=dict(WINDOWS[mode]);clock=[0.]
    for _ in range(p["steps"]):clock.append(clock[-1]+dt)
    p["end"]=clock[-1]
    b.need(len(rows)==p["frames"] and int(rows[-1]["completed_steps"])==p["steps"] and bits(float(rows[-1]["time_s"]))==bits(p["end"]),"Actual owner plan declaration differs")
    for i,r in enumerate(rows):
        n=int(r["completed_steps"]);b.need(int(r["part"])==i and int(r["saved_step"])==(n-1 if n else 0) and bits(float(r["time_s"]))==bits(clock[n]) and bits(float(r["dt_s"]))==bits(dt),"Plan is not actual scalar clock")
    b.need(run["clock"]["completed_updates"]==p["steps"] and run["clock"]["native_frames"]==p["frames"] and run["clock"]["post_open_frames"]==p["post"],"Sealed clock profile differs")
    return dict(tag=tag,mode=mode,window=mode,configuration=cfg,scheme=scheme,backend="CPU"if cfg=="DebugCPU"else"GPU",run_receipt=b.stat(rp),
      source_build=run["source_build"],prepared=pe,source_root=prep["source_root"],run=run,output_directory=str(output),data=run["data"],run_out=b.stat(output/"Run.out"),plan=run["plan"],dt=dt,
      drain_step=1600 if scheme=="A"else 1000,profile=p,clock=clock,rows=rows,native_output=str(T/"outputs"/(tag+"_native_m0_r1")))
def pin_reader(ad):
    ad.pin(BUILD);v=b.read(BUILD);b.need(v["passed"] and v["solver_invocations"]==v["reader_invocations"]==0,"New native tool build required")
    ad.pin(PROGRAM);b.same(v["program"])
    for e in v["runtime"]:ad.pin(e["destination"]["path"]);b.same(e["destination"])
    return v
def read_native(ad,job,result):
    pin_reader(ad);out=Path(job["native_output"]);cp=L/(job["tag"]+".native_m0_r1.call.json");log=L/(job["tag"]+".native_m0_r1.log")
    b.need(not out.exists() and not cp.exists() and not log.exists(),"Existing/partial read is protected; do not decode twice")
    import psutil
    ad.pin(psutil.__file__);no_active_reader(PROGRAM,job["data"]);env=os.environ.copy()
    for k in ["UPL_TPI_CPU_R1","UPL_TPI_GPU_R1","UPL_TPI_M0_DT_R1"]:env.pop(k,None)
    ad.finish();call,_=b.invoke(job["tag"]+".native_m0_r1",[str(PROGRAM),"--read",job["backend"],job["data"],job["plan"]["path"],job["mode"],str(out)],BUILDROOT,env)
    done=b.read(out/"completion.json");p=job["profile"]
    b.need(done["passed"] and done["stage"]==TAG and done["backend"]==job["backend"]+"_M0_private" and done["samples"]==p["frames"] and done["planned_completed_steps"]==p["steps"] and done["post_open_frames"]==p["post"],"Original complete native guards/profile differ")
    result.update(passed=True,reader_call=call,reader_invocations=1,native_output=str(out),completion=done,products=[b.stat(x)for x in out.iterdir()if x.is_file()],consumed=ad.finish())
def intervals(ad,job):
    out=Path(job["output_directory"]);paths=[out/("UplTpiM0DtR1"+s)for s in [".policy.json",".csv",".summary.json"]]
    if job["scheme"]=="A":
        b.need(not any(p.exists()for p in paths),"A entered M0 dt policy");return dict(expected_absent=True)
    for p in paths:ad.pin(p)
    policy,summary=b.read(paths[0]),b.read(paths[2]);p=job["profile"]
    b.need(policy["dt_policy"]==summary["dt_policy"]=="M0_Eq40_Rh1" and policy["R_h"]==summary["R_h"]==1 and policy["HG_limit_reference_available"]is False and summary["HG_limit_reference_available"]is False and policy["stage"]==summary["stage"]=="upl_tpi_m0_dt_r2","Actual r2 method policy/HG-unavailable metadata differs")
    b.need(bits(policy["fixed_dt_s"])==bits(job["dt"]) and policy["signed_dterror_is_method_specific"] and summary["completed"]
      and summary["updates"]==summary["pre"]==summary["cor"]==summary["endpoint"]==p["steps"] and summary["saved_intervals_including_initial"]==p["frames"],"Actual method lifecycle summary differs")
    clock=Path(job["native_output"])/"clock.bin";ad.pin(clock)
    with clock.open("rb")as f:
        b.need(struct.unpack("<II",f.read(8))==(p["frames"],28),"Original clock shape differs");native=[struct.unpack("<dIdd",f.read(28))for _ in range(p["frames"])];b.need(f.read(1)==b"","Extra clock payload")
    mins={k:float.fromhex("0x1.fffffffffffffp+1023")for k in INTERVAL_COLUMNS[12:18]};maximum=-float.fromhex("0x1.fffffffffffffp+1023");prev=0;count=0
    with paths[1].open(encoding="utf-8-sig",newline="")as f:
        reader=csv.DictReader(f);b.need(reader.fieldnames==INTERVAL_COLUMNS,"Exact interval schema differs");records=list(reader)
        b.need(len(records)==p["frames"],"Exact interval record count differs")
        for i,(row,plan,raw)in enumerate(zip(records,job["rows"],native)):
            v={k:finite(x)for k,x in row.items()};n=int(plan["completed_steps"]);delta=n-prev;prev=n
            b.need(v["part"]==i and bits(v["actual_save_time_s"])==bits(raw[0]) and v["saved_step"]==raw[1]
              and v["completed_updates"]==n and bits(v["dt_s"])==bits(raw[2])==bits(job["dt"]),"Genuine interval clock/step/dt differs")
            b.need(all(v[k]==delta for k in ["interval_pre","interval_cor","interval_endpoint"])and all(v[k]==n for k in ["total_pre","total_cor","total_endpoint"]),"Real three-phase interval counts differ")
            b.need(v["min_HG_limit_reference_s"]==float.fromhex("0x1.fffffffffffffp+1023"),"Unavailable HG sentinel was replaced by a physical value")
            if not i:
                b.need(v["interval_empty"]==1 and all(v[k]==float.fromhex("0x1.fffffffffffffp+1023")for k in INTERVAL_COLUMNS[12:18]) and v["max_dt_minus_bound_s"]==-float.fromhex("0x1.fffffffffffffp+1023"),"Initial explicit sentinel layout differs")
            else:
                chosen=min(v["min_force_CFL_s"],v["min_skeleton_wave_AV_CFL_s"],v["min_Rh_hydro_s"])
                error=job["dt"]-chosen
                b.need(v["interval_empty"]==0 and delta>0 and bits(chosen)==bits(v["min_selected_bound_s"])
                  and bits(error)==bits(v["max_dt_minus_bound_s"])==bits(raw[3]) and error<=1e-14,"Method-specific signed native interval does not equal genuine Eq40 expression")
                for k in mins:mins[k]=min(mins[k],v[k])
                maximum=max(maximum,error)
            count+=1
        b.need(count==p["frames"],"Incomplete interval record review")
    b.need(bits(summary["actual_end_s"])==bits(job["profile"]["end"]) and bits(summary["max_dt_minus_bound_s"])==bits(maximum),"Total scalar/max signed summary differs")
    for key,value in mins.items():b.need(bits(summary[key])==bits(value),"Total interval minimum differs: "+key)
    return dict(saved_interval_rows=count,noninitial_native_signed_bit_checks=count-1,initial_native_diagnostic_preserved=True,
      initial_sentinels_excluded_from_physical_statistics=True,HG_reference_unavailable=True,all_phase_counts_checked=True,method_specific_bound=True,ULP_tolerance_added=0)

def sidecar_gpu(ad, job, plan, clock):
    DT=job["dt"]
    output = Path(job["output_directory"])
    paths = [output / ("UplTpiGpuR1" + suffix) for suffix in (".policy.json", ".csv", ".summary.json")]
    if job["scheme"] == "A":
        b.need(not any(p.exists() for p in paths), "Untaken default-A branch must not create TPI sidecars")
        return dict(expected_absent=True, native_scheme_evidence="Actual owned environment plus default-A branch")
    for p in paths:
        ad.pin(p)
    policy, summary = b.read(paths[0]), b.read(paths[2])
    scheme = "B_TPI_alpha_0p5_beta0" if job["scheme"] == "B" else "C_PPE_t_alpha0_beta0"
    alpha = .5 if job["scheme"] == "B" else 0.
    b.need(policy.get("stage") == "upl_tpi_gpu_r1" and policy.get("scheme") == scheme
           and policy.get("alpha") == alpha and policy.get("beta") == 0 and policy.get("M0") is True
           and policy.get("native_count") == 1040 and policy.get("soil_count") == 1000
           and policy.get("history_ID_owned") is True and policy.get("history_cold_start") is True
           and policy.get("half_equals_endpoint_history_guess") is True
           and policy.get("endpoint_source_clock_is_original_n") is True,
           "Actual private M0 scheme/history policy differs")
    for document in (policy, summary):
        b.need(document.get("full_restart_supported") is False and document.get("paper_literal_LF") is False
               and document.get("second_order_claimed") is False and document.get("true_implicit_solution") is False
               and document.get("physical_acceptance") is False, "Prototype limits must remain explicit")
    w = job["profile"]
    b.need(summary.get("completed") is True and summary.get("scheme") == scheme and summary.get("alpha") == alpha
           and summary.get("beta") == 0 and summary.get("commits") == summary.get("endpoint_calls") == w["steps"]
           and summary.get("core_field_bit_checks") == 7000 * w["steps"]
           and summary.get("HG_readonly_snapshot_checks") == 2000 * w["steps"]
           and summary.get("PorePressRate_is_legacy_scaled_residual_not_dpdt") is True
           and bits(float(summary["actual_end"])) == bits(w["end"]), "Actual completed lifecycle summary differs")
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
            expected_drain = 10 if n > job["drain_step"] else 0
            b.need(len(seen) == 1000 and source_count == endpoint_count == commit_count == expected_drain,
                   "All actual source/endpoint/commit Dirichlet owner counts differ")
        b.need(next(reader, None) is None and native.read(1) == b"", "Trailing sidecar or native records differ")
    return dict(rows=rowcount, expected_rows=1000 * w["frames"], actual_ID_owned_history=True,
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

def hg_run(job):
    text=Path(job["run_out"]["path"]).read_text(encoding="utf-8-sig",errors="strict");steps=job["profile"]["steps"]
    first=re.search(r"SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)",text)
    second=re.search(r"SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)",text)
    guard=re.search(r"SoilHourglass: max\|sum\(M0\*Href\)\|=([^ ]+) max\|sum\(mi\*deltaAce\)\|=([^ ]+) max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)",text)
    b.need(first and second and guard and tuple(map(int,first.groups()))==(2*steps,steps,steps,2*steps)
      and tuple(map(int,second.groups()))==(steps+1,steps-1),"Original HG lifecycle/cache differs")
    net,actual,tau,spin=map(finite,guard.groups());b.need(min(net,actual,tau,spin)>=0 and tau<=.2 and spin<.01,"Original HG stiffness/spin guard failed")
    return dict(forcecalls=2*steps,predictorupdates=steps,correctorupdates=steps,ratecalls=2*steps,
      ratecalculations=steps+1,cachehits=steps-1,max_reference_net=net,max_actual_float_net=actual,max_dt_tau=tau,spinbound=spin)

def prefix_A(ad,job):
    ad.pin(A_REVIEW);oldreview=b.read(A_REVIEW);b.need(oldreview["passed"],"Actual retained A qualification missing")
    done=A_NATIVE/"completion.json";ad.pin(done);olddone=b.read(done);b.need(olddone["passed"] and olddone["samples"]==344,"Retained actual344 native declaration differs")
    current=Path(job["native_output"])
    def clocks(path,count):
        ad.pin(path)
        with path.open("rb")as f:
            b.need(struct.unpack("<II",f.read(8))==(count,28),"Original clock declaration differs")
            data=[f.read(28)for _ in range(count)];b.need(all(len(x)==28 for x in data)and f.read(1)==b"","Clock payload truncated/extra")
        keys=[(x[:8],struct.unpack_from("<I",x,8)[0])for x in data];b.need(len(set(keys))==len(keys),"Repeated actual clock/Step key")
        return data,keys
    old,ok=clocks(A_NATIVE/"clock.bin",344);new,nk=clocks(current/"clock.bin",18);lookup={x:i for i,x in enumerate(ok)}
    shared=[(lookup[x],i)for i,x in enumerate(nk)if x in lookup]
    b.need(shared==[(i,i)for i in range(17)] and nk[-1]not in lookup and nk[-1][1]==319,"Only first17 states share; forced320 is not shared")
    decl={"original15.bin":((1040,15),166408),"physical.bin":((1000,26),208008),"common_j_theta.bin":((1040,2),16648),"soil_n.bin":((1000,1),8008),"clock.bin":(None,28)}
    files=[]
    for name,(shape,stride)in decl.items():
        op,np=A_NATIVE/name,current/name;ad.pin(op);ad.pin(np);hs=8 if shape is None else 12
        with op.open("rb")as a,np.open("rb")as z:
            ah=struct.unpack("<"+"I"*(hs//4),a.read(hs));zh=struct.unpack("<"+"I"*(hs//4),z.read(hs))
            b.need((ah==(344,28)and zh==(18,28))if shape is None else(ah==(*shape,344)and zh==(*shape,18)),"Original separate headers differ; never rewrite")
            for oi,ni in shared:
                a.seek(hs+oi*stride);z.seek(hs+ni*stride);x,y=a.read(stride),z.read(stride)
                b.need(len(x)==len(y)==stride and x==y,"Shared exported record/signed bytes differ: "+name)
        files.append(dict(file=name,old_header=ah,new_header=zh,actual_shared_records=17,all_shared_payload_bytes_equal=True))
    return dict(files=files,actual_shared_indices=shared,new_forced320_unshared=True,headers_rewritten=False,all22_raw_array_bit_proof=False)

def review(ad,job,result):
    pin_reader(ad);receipt=L/(job["tag"]+".native_m0_r1.json");ad.pin(receipt);decoded=b.read(receipt)
    b.need(decoded["passed"] and decoded["reader_invocations"]==1 and decoded["native_output"]==job["native_output"],"One completed native read required")
    ad.pin(decoded["reader_call"]["path"]);b.same(decoded["reader_call"]);call=b.read(decoded["reader_call"]["path"])
    b.need(call["passed"] and call["actual_Popen_wait_exit"]==call["actual_Win32_exit"]==0,"Actual reader exits differ")
    for x in Path(job["native_output"]).iterdir():
        if x.is_file():ad.pin(x)
    result["HG_original_guards"]=hg_run(job);result["method_intervals"]=intervals(ad,job)
    if job["backend"]=="CPU":result["pressure_sidecar"]=sidecar_cpu(ad,job,job["rows"],job["clock"])
    else:
        if job["scheme"]!="A" and job["configuration"]=="Release":result["actual_retained_pressure_PTX"]=original.ptx_evidence(ad,job)
        result["pressure_sidecar"]=sidecar_gpu(ad,job,job["rows"],job["clock"])
    if job["scheme"]=="A":result["default_A_actual_prefix"]=prefix_A(ad,job)
    result.update(passed=True,reader_invocations=0,completion=decoded["completion"],consumed=ad.finish(),consumed_stats_unchanged=True,
      all22_original_guards_not_relaxed=True,method_signed_interval_bit_replay=job["scheme"]!="A",original_signed_guard_preserved=True,initial_native_diagnostic_not_masked=True,
      old_Kw_wave_is_diagnostic_not_method_bound=True,cross_dt_half_or_5Pa_equivalence_claimed=False,
      raw22_all_array_bit_proof=False,physical_theory_or_full_cycle_acceptance=False)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("action",choices=["build","read","review"])
    ap.add_argument("--admission",required=True,type=Path);ap.add_argument("--execution-authorized",action="store_true");args=ap.parse_args()
    b.need(args.execution_authorized,"One exact-action root admission required");ad=Admission(args.action,args.admission)
    if args.action=="build":build(ad);return
    tag=ad.data["job"]["tag"];b.need(re.fullmatch(r"upl_tpi_m0_dt_[A-Za-z0-9_]+_r[1-9][0-9]*",tag),"Exact new tag required")
    path=L/(tag+(".native_m0_r1.json"if args.action=="read"else".native_review_m0_r1.json"));b.need(not path.exists(),"Existing receipt protected")
    result=dict(stage=TAG+"."+args.action,tag=tag,passed=False,solver_invocations=0,build_invocations=0,VTK_invocations=0,SHA_scans=0,
      physical_acceptance=False,automatic_follow_up=False,old_raw_retired_B_partial_read=False)
    try:
        result["root_admission"]=ad.entry;job=get_job(ad);result["job"]={k:v for k,v in job.items()if k not in ["run","rows","clock"]}
        (read_native if args.action=="read"else review)(ad,job,result)
    except Exception as exc:result.update(passed=False,first_error=str(exc),partials_preserved=True)
    b.write_new(path,result);print(__import__("json").dumps(dict(passed=result["passed"],receipt=str(path),first_error=result.get("first_error")),ensure_ascii=False))
    return 0 if result["passed"]else 1

def sidecar_cpu(ad, job, plan, clock):
    DT=job["dt"]
    output = Path(job["output_directory"])
    paths = [output / ("UplTpiCpuR1" + suffix) for suffix in (".policy.json", ".csv", ".summary.json")]
    if job["scheme"] == "A":
        b.need(not any(p.exists() for p in paths), "Untaken default-A branch must not create TPI sidecars")
        return dict(expected_absent=True, native_scheme_evidence="Actual owned environment plus default-A branch")
    for p in paths:
        ad.pin(p)
    policy, summary = b.read(paths[0]), b.read(paths[2])
    scheme = "B_TPI_alpha_0p5_beta0" if job["scheme"] == "B" else "C_PPE_t_alpha0_beta0"
    alpha = .5 if job["scheme"] == "B" else 0.
    b.need(policy.get("stage") == "upl_tpi_cpu_r1" and policy.get("scheme") == scheme
           and policy.get("alpha") == alpha and policy.get("beta") == 0 and policy.get("M0") is True
           and policy.get("native_count") == 1040 and policy.get("soil_count") == 1000
           and policy.get("history_ID_owned") is True and policy.get("history_cold_start") is True
           and policy.get("half_equals_endpoint_history_guess") is True
           and policy.get("endpoint_source_clock_is_original_n") is True,
           "Actual private M0 scheme/history policy differs")
    for document in (policy, summary):
        b.need(document.get("full_restart_supported") is False and document.get("paper_literal_LF") is False
               and document.get("second_order_claimed") is False and document.get("true_implicit_solution") is False
               and document.get("physical_acceptance") is False, "Prototype limits must remain explicit")
    w = job["profile"]
    b.need(summary.get("completed") is True and summary.get("scheme") == scheme and summary.get("alpha") == alpha
           and summary.get("beta") == 0 and summary.get("commits") == summary.get("endpoint_calls") == w["steps"]
           and summary.get("core_field_bit_checks") == 7000 * w["steps"]
           and summary.get("HG_readonly_snapshot_checks") == 2000 * w["steps"]
           and bits(float(summary["actual_end"])) == bits(w["end"]), "Actual completed lifecycle summary differs")
    rowcount, max_rounding = 0, 0.
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
                prediction = values["pn_Pa"] if alpha == 0 else values["pn_Pa"] + alpha * (values["pn_Pa"] - values["previous_Pa"])
                b.need(bits(values["prediction_double_Pa"]) == bits(prediction), "Actual history pressure prediction differs")
                half = 0. if flags[0] else f32(prediction)
                b.need(bits(values["half_actual_float_Pa"], "f") == bits(half, "f"), "Mechanical half pressure history/Dirichlet differs")
                diagonal, residual, q = (values[x] for x in ("S_1_per_m_s", "Rgamma_Pa_per_m_s", "endpoint_q_actual_float_Pa"))
                if flags[1]:
                    b.need(diagonal == residual == 0., "A constrained endpoint row must not claim an elliptic residual")
                    raw = 0.
                else:
                    b.need(diagonal > 0., "Nonpositive/nonfinite elliptic diagonal is not masked or regularized")
                    exact = q + residual / diagonal
                    raw = f32(exact)
                    max_rounding = max(max_rounding, abs(raw - exact))
                b.need(bits(values["raw_final_float_Pa"], "f") == bits(raw, "f")
                       and bits(values["final_float_Pa"], "f") == bits(0. if flags[2] else raw, "f"),
                       "Actual beta0 float writeback or original final Dirichlet policy differs")
                Jexpected = values["Jn"] + DT * values["Jhalf"] * values["theta_half_for_J_1_per_s"]
                b.need(bits(values["Jfull"]) == bits(Jexpected), "Original single J corrector was advanced or reinterpreted")
                rowcount += 1
            expected_drain = 10 if n > job["drain_step"] else 0
            b.need(len(seen) == 1000 and source_count == endpoint_count == commit_count == expected_drain,
                   "All actual source/endpoint/commit Dirichlet owner counts differ")
        b.need(next(reader, None) is None and native.read(1) == b"", "Trailing sidecar or native records differ")
    return dict(rows=rowcount, expected_rows=1000 * w["frames"], actual_ID_owned_history=True,
                actual_M0_alpha=alpha, beta=0, max_actual_pressure_float_writeback_rounding_Pa=max_rounding,
                per_saved_row_formula_and_J_corrector_checked=True,
                unsaved_history_values_independently_observed=False,
                PorePressRate_is_legacy_scaled_endpoint_residual_not_actual_dpdt=True,
                no_finite_Kw_or_half_equivalence_claim=True)

if __name__=="__main__":raise SystemExit(main())
