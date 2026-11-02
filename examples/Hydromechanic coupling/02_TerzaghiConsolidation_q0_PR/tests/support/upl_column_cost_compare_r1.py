"""Bounded025 cost-run compatibility only: old export exact or CPU1/8 original error gates."""
import argparse, csv, hashlib, importlib.util, json, re
from pathlib import Path
import numpy as np

T = Path(__file__).resolve().parents[1]
TAG = "upl_column_cost_compare_r1"
PINS = {"support/upl_column_public_exact_r1.py": "d41fdb6c4003bf6ca65212c4c11449ec0dee89ce721b00c4adec3dd23482482f",
        "notes/upl_column_public_exact_r1.json": "87e50b8c219aea05fe58d2d218b2af6485b583c52839f3c3b708dfecc71ff8cc"}
parent = T / "support/upl_column_public_exact_r1.py"
source = parent.read_bytes()
if hashlib.sha256(source).hexdigest() != PINS["support/upl_column_public_exact_r1.py"]:
    raise ValueError("Pinned neutral export helpers changed before import")
base = importlib.util.module_from_spec(importlib.util.spec_from_file_location("retained_cost_export_helpers", parent))
exec(compile(source, str(parent), "exec"), base.__dict__)  # Only neutral functions; old proof/main never called.
need, entry, adopt, bind, readjson = base.need, base.entry, base.adopt, base.bind, base.readjson
N, S = 769, 1000
EXPORTS = ("original15.bin", "physical.bin", "clock.bin", "common_j_theta.bin", "soil_n.bin", "native_ids.csv", "fixed_ids.csv", "history.csv", "ledger.csv", "fixed_samples.csv", "last_poro.csv", "columns.csv")
SAVE = np.array(list(range(0,3991,10))+list(range(3991,4011))+list(range(4020,5001,10))+list(range(5020,10001,20)), dtype=np.int64)

def dataset(job, retained=False):
    backend = "GPU" if job == "gpu" else "CPU"
    tag = "upl_column_public_"+backend+"_coarse_r1" if retained else "upl_column_cost_r1_"+job
    ce = adopt(T/"logs"/(tag+".native.json")); c = readjson(ce["path"])
    need(c["passed"] and c["physical_acceptance"] is False and c["backend"] == backend and c["window"] == "coarse" and c["source_inputs_raw_objects_runtime_canonical_unchanged"] and c["drainage_nonempty_per_frame_independently_verified"], "Single native safety rejected")
    if not retained:
        need(c["stage"] == "upl_column_cost_native_r1" and c["job"] == job, "Wrong fresh cost native job")
        for e in c["inputs"]: bind(e)
    done = base.completion(c, backend, True); files = base.leaves(c)
    need(len(files) == 13 and set(files) == set(EXPORTS)|{"completion.json"}, "Public13 leaf scope differs")
    need(done["planned_completed_steps"] == 10000 and done["post_open_frames"] == 359 and done["post_open_drained_particle_checks"] == 3590 and done["max_activeDrainCount"] == 10 and done["max_ledger_relative_error"] <= 5e-13, "Original native clock/ledger/drain coverage differs")
    se = c["source_run"]; r = readjson(bind(se))
    need(r["passed"] and r["physical_acceptance"] is False and r["public_project_main"] and not r["fixture_or_Run_override"] and r["backend"] == backend and r["window"] == "coarse" and r["source_inputs_objects_runtime_canonical_unchanged"] and r["all_raw_outputs_hash_bound"] and r["native_frame_sequence_exact"] and r["native_frames"] == N and r["planned_samples"] == N and r["planned_steps"] == 10000 and r["planned_dt_s"] == 2.5e-6 and r["planned_end_s"] == .025, "Actual same-setting Run rejected")
    if not retained:
        need(r["stage"] == "upl_column_cost_r1" and r["job"] == job and r["threads"] == {"cpu1":1,"cpu8":8,"gpu":None}[job], "Cost thread/job identity differs")
        for e in r["inputs"]: bind(e)
    solver, reader = base.owned(r["call"]), base.owned(c["reader_call"])
    need(solver["public_project_main"] and not solver["fixture_or_Run_override"] and solver["target_program"] == r["program"], "Actual main identity differs")
    h = readjson(bind(c["reader_helper"])); need(h["passed"] and h["exact_link_closure_verified"] and h["program"] == reader["program"], "Actual pure reader/helper differs")
    need(reader["arguments"] == ["--read",backend,str(Path(c["paths"]["solver_dir"])/"data"),"769","0.0000025",c["paths"]["native_dir"]], "Actual reader argv differs")
    for e in r["files"]: bind(e)
    need(sum(bool(re.fullmatch(r"Part_\d{4}\.bi4",Path(e["path"]).name)) for e in r["files"]) == N, "Raw PART ownership/count differs")
    bind(r["runtime_input"]); bind(r["input_manifest"]); b = readjson(bind(r["source_build"])); need(b["passed"], "Source build rejected")
    need(len(r["source_snapshot"]) == 265 and len(r["runtime"]) == 4 and len(r["canonical_programs_before"]) == 7, "Actual265/runtime4/canonical7 shape differs")
    for row in r["source_snapshot"]:
        bind(row["snapshot"])
        if not retained: bind(row["original"])
        need(row["original"]["sha256"] == row["snapshot"]["sha256"], "Captured source copy differs")
    bind(r["documentation_snapshot"]["snapshot"])
    for row in r["runtime"]: bind(row["copy"])
    if not retained:
        bind(r["documentation_snapshot"]["original"])
        for e in r["canonical_programs_before"]: bind(e)
        for row in r["runtime"]: bind(row["original"])
    # Historical mutable originals/inputs are deliberately not recursively revalidated as current.
    p = base.mapped(files["physical.bin"],(S,26,N),[("time","<f8"),("q","<f8",(S,26))])
    clock = base.mapped(files["clock.bin"],(N,28),[("time","<f8"),("step","<u4"),("dt","<f8"),("error","<f8")])
    with bind(files["columns.csv"]).open(encoding="utf-8-sig",newline="") as f: cols=list(csv.DictReader(f))
    need([v["name"] for v in cols] == base.FIELDS and [int(v["column"]) for v in cols] == list(range(26)), "Common26 named order differs")
    ids=np.genfromtxt(bind(files["native_ids.csv"]),delimiter=",",names=True,encoding="utf-8")
    fixed=np.genfromtxt(bind(files["fixed_ids.csv"]),delimiter=",",names=True,encoding="utf-8")
    need(np.array_equal(ids["id"],np.arange(40,1040)) and np.array_equal(ids["row"],np.arange(S)) and np.array_equal(fixed["id"],np.arange(40)) and np.array_equal(fixed["row"],np.arange(40)), "Original material IDs differ")
    x0=np.column_stack([ids[k] for k in ("x0","y0","z0")]).astype("<f8")
    need(np.array_equal(np.where(np.arange(N)==0,0,clock["step"].astype(np.int64)+1),SAVE) and np.all(clock["dt"]==2.5e-6) and base.bits(p["time"],clock["time"]).all() and np.isfinite(clock["error"]).all() and np.all(clock["error"][1:]<=1e-14) and np.all(clock["error"][1:]!=-np.finfo(float).max), "Actual saved-clock/signed safety differs")
    need(base.bits(p["q"][0,:,:3],x0).all(), "Initial material coordinates differ")
    return dict(check=ce,run=se,build=r["source_build"],program=r["program"],runtime=r["runtime_input"],manifest=r["input_manifest"],files=files,p=p,clock=clock,x0=x0)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--case",required=True,choices=("cpu1_exact","gpu_exact","threads"));case=ap.parse_args().case
    token="threads.compare" if case=="threads" else case.split("_")[0]+".exact"
    check=T/"logs"/("upl_column_cost_r1_"+token+".json"); summary=T/"logs"/("upl_column_cost_r1_threads.compare.csv")
    need(not check.exists() and (case!="threads" or not summary.exists()), "Retained comparison protected")
    result=dict(stage=TAG,case=case,passed=False,physical_acceptance=False,solver_decoder_or_build_invoked=False,timing_speedup_verified=False,failure=None)
    try:
        adopt(__file__);adopt(T/"notes"/(TAG+".json"))
        for rel,digest in PINS.items(): need(adopt(T/rel)["sha256"]==digest,"Pinned neutral source/note changed")
        a=dataset("cpu1" if case=="threads" else case.split("_")[0]); b=dataset("cpu8") if case=="threads" else dataset(case.split("_")[0],True)
        need(a["build"]==b["build"] and a["program"]["sha256"]==b["program"]["sha256"] and a["program"]["bytes"]==b["program"]["bytes"] and a["runtime"]==b["runtime"] and a["manifest"]==b["manifest"], "Same backend/program/source/input identity differs")
        need(base.bits(a["x0"],b["x0"]).all(),"Initial material coordinates differ")
        if case!="threads":
            equal={name:bool(a["files"][name]["bytes"]==b["files"][name]["bytes"] and a["files"][name]["sha256"]==b["files"][name]["sha256"]) for name in EXPORTS}
            gates=dict(all_original15_typed_exact=equal["original15.bin"],actual_clock_step_dterror_exact=equal["clock.bin"],all_common26_exact=equal["physical.bin"],all_native_J_theta_exact=equal["common_j_theta.bin"],all_soil_n_exact=equal["soil_n.bin"],public_extra_saved_export_representations_exact=equal["ledger.csv"] and equal["fixed_samples.csv"],all12_named_exports_exact=all(equal.values()))
            result.update(gates=gates,whole_export_files=equal,completion_whole_bytes_compared=False,all22_BI4_array_raw_bytes_compared=False,extra_scope="Actual native V/rho/k/PosDiv are compared via existing17-digit soil ledger/fixed CSV exports, not fabricated raw22 binaries.")
        else:
            need(a["files"]["native_ids.csv"]["sha256"]==b["files"]["native_ids.csv"]["sha256"] and a["files"]["fixed_ids.csv"]["sha256"]==b["files"]["fixed_ids.csv"]["sha256"], "Thread comparison ID/fixed geometry differs")
            gap=float(np.max(np.abs(a["clock"]["time"]-b["clock"]["time"])));pmax=umax=0.;rmsmax=np.zeros(26);absmax=np.zeros(26)
            with summary.open("x",encoding="utf-8",newline="") as f:
                w=csv.writer(f);w.writerow(["part","CPU1_actual_time_s","CPU8_actual_time_s","pressure_RMS_Pa","material_XYZ_displacement_difference_max_mm","velocity_XYZ_RMS_m_s","stress6_RMS_Pa"])
                for part in range(N):
                    av,bv=np.asarray(a["p"]["q"][part]),np.asarray(b["p"]["q"][part]);need(np.isfinite(av).all() and np.isfinite(bv).all(),"Nonfinite actual field")
                    d=av-bv;rms=np.sqrt(np.mean(d*d,axis=0));ma=np.max(np.abs(d),axis=0);need(np.isfinite(rms).all() and np.isfinite(ma).all(),"Nonfinite diagnostic reduction")
                    rmsmax=np.maximum(rmsmax,rms);absmax=np.maximum(absmax,ma);du=(av[:,:3]-a["x0"])-(bv[:,:3]-b["x0"])
                    p=float(rms[6]);u=float(1000*np.max(np.linalg.norm(du,axis=1)));pmax=max(pmax,p);umax=max(umax,u)
                    w.writerow([part,float(a["clock"]["time"][part]),float(b["clock"]["time"][part]),p,u,float(np.sqrt(np.mean(np.sum(d[:,3:6]**2,axis=1)))),float(np.sqrt(np.mean(np.sum(d[:,10:16]**2,axis=1))))])
            gates=dict(pressure_RMS_all769_le_5Pa=bool(pmax<=5),material_XYZ_difference_all769_le_0_005mm=bool(umax<=.005),actual_time_difference_le_1e_minus14_s=bool(gap<=1e-14))
            result.update(gates=gates,max_pressure_RMS_Pa=pmax,max_material_XYZ_displacement_difference_mm=umax,max_actual_time_difference_s=gap,max_common26_RMS=dict(zip(base.FIELDS,map(float,rmsmax))),max_common26_abs=dict(zip(base.FIELDS,map(float,absmax))),other_common26_metrics_descriptive=True,no_interpolation_or_time_snap=True,temporal_half_study=False)
        for e in list(base.BOUND.values()): need(entry(e["path"])==e,"Input changed during offline comparison")
        result.update(passed=bool(all(gates.values())),native_checks=[a["check"],b["check"]],source_runs=[a["run"],b["run"]],source_build=a["build"],samples=N,native_count=S,fixed_count=40,common_columns=26,historical_mutable_source_originals_checked_as_current=False,implementation_and_thread_timing_compatibility_only=True)
    except Exception as exc: result["failure"]=str(exc)
    result.update(inputs=list(base.BOUND.values()),files=[entry(summary)] if case=="threads" and summary.exists() else [])
    with check.open("x",encoding="utf-8") as f: json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n")
    print(json.dumps(dict(passed=result["passed"],check=str(check))))
    return 0 if result["passed"] else 1

if __name__=="__main__": raise SystemExit(main())
