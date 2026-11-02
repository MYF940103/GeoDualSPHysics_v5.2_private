"""One offline column pair; no decoder/solver/subprocess or fitted acceptance limits."""
import argparse, csv, hashlib, json, struct
from pathlib import Path
import numpy as np

T = Path(__file__).resolve().parents[1]
F = ["x","y","z","vx","vy","vz","PorePress","PorePress0","J","theta","sigma_xx","sigma_xy","sigma_xz","sigma_yy","sigma_yz","sigma_zz","Kplastic","FSType","FSNormal_x","FSNormal_y","FSNormal_z","ExcessPorePress","LoadAce_x","LoadAce_y","LoadAce_z","legacy_Rhop"]
SCHEMA = "case02_private26_col21_ExcessPorePress_NOT_wave26"
N, S = 769, 1000
TRACKED = {}
def require(ok, message):
    if not bool(ok): raise ValueError(message)
def readjson(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def entry(path):
    path = Path(path).resolve(); h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""): h.update(block)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=h.hexdigest())
def bind(e):
    path = str(Path(e["path"]).resolve())
    a = TRACKED.get(path)
    if a is None: a = entry(path); TRACKED[path] = a
    require(a["bytes"] == e["bytes"] and a["sha256"].lower() == e["sha256"].lower(), "Changed bound file: "+path)
    return Path(path)
def adopt(path):
    e = entry(path); bind(e); return e
def owned(e):
    c = readjson(bind(e)); require(c["owned_call_exited"] and c["typed_LASTEXITCODE_captured_immediately"] and type(c["exit_code"]) is int and c["exit_code"] == 0, "Missing owned typed exit0")
    bind(c["program"])
    if c.get("log"): bind(c["log"])
    return c
def dataset(window, gpu):
    stem = "upl_gpu_column_actual_" if gpu else "upl_case02_flux_window25_"
    cp = T/"logs"/(stem+window+("_r2" if gpu else "_r1")+(".native.json" if gpu else ".native.check.json"))
    ce = adopt(cp); c = readjson(cp)
    require(c["passed"] and c["physical_acceptance"] is False, "Native check rejected")
    for e in c["files"]: bind(e)
    q = readjson(bind(c["completion"])); dt = 1.25e-6 if window == "half" else 2.5e-6
    require(q["passed"] and q["backend"] == ("GPU_private" if gpu else "CPU_private") and q["window"] == "window25" and q["grid"] == ("h" if window == "half" else "c") and q["model"] == "constant", "Backend/window/model differs")
    require(q["samples"] == N and q["native_count"] == S and q["fixed_count"] == 40 and q["total_native_count"] == 1040 and q["physical_columns"] == 26 and q["physical_schema"] == SCHEMA, "Native physical26 identity/schema differs")
    require(q["actual_time_step_locked_dt_exact"] and q["declared_saved_completed_steps_exact"] and q["no_exclusions"] and q["dt_s"] == dt and q["physical_acceptance"] is False, "Native clocks/safety rejected")
    se = c["source_run"] if gpu else c["sealed_solver"]; r = readjson(bind(se))
    require(r["passed"] and r["physical_acceptance"] is False, "Source Run rejected")
    for e in r["files"]: bind(e)
    if gpu:
        require(c["source_input_raw_program_runtime_canonical_unchanged"] and c["live_final"]["byte_exact"] and c["saved_native_integrity_only"], "GPU native ownership/live gate rejected")
        owned(c["reader_call"]); owned(r["call"]); bind(r["actual_complete"]); h = readjson(bind(c["reader_build"]))
        be = r["source_build"]; b = readjson(bind(be)); source = readjson(bind(r["source_freeze"]))
        require(b["passed"] and b["objects_exclude_main"] and len(b["objects"]) == 110 and len(source["source"]) == 265 and len(source["current_source_snapshot"]) == 265 and len(source["canonical_programs_before"]) == 7, "Current GPU closure rejected")
        for e in source["source"]+source["canonical_programs_before"]+source["runtime_before"]+h["inputs"]+h["objects"]+h["author_files"]+h["tools"]+h["libraries"]: bind(e)
        for row in source["current_source_snapshot"]: bind(row["original"]); bind(row["snapshot"])
        for e in source["documentation_snapshot"].values(): bind(e)
        for row in h["runtime"]: bind(row["original"]); bind(row["copy"])
        bind(h["program"]); owned(h["compile_call"]); owned(h["link_call"])
        require(q["fixed_n_is_GPU_mirror_sample_not_CPU_zero_marker"], "GPU mirror semantics lost")
    else:
        require(c["bindings_unchanged"] and c["owned_reader_exit0"] and c["source_solver_exit_verified"], "CPU sealed native evidence rejected")
        owned(c["owned_exit_record"]); bind(c["log"]); owned(r["owned_exit_record"]); bind(r["program"]); bind(r["input_manifest"])
        require("-ompthreads:1" in r["arguments"], "Retained CPU OMP1 attribution differs")
        h = readjson(bind(r["build"])); be = h["source_build"]; b = readjson(bind(be)); bind(c["reader_build"])
        require(h["passed"] and b["passed"], "Historical CPU helper/build rejected")
        # Historical source copies only: NEVER check these original GPU paths as current.
        require(len(b["source_snapshot"]) == 265, "Historical CPU source snapshot count differs")
        for row in b["source_snapshot"]: bind(row["snapshot"])
    directory = Path(c["paths"]["native_dir"])
    files = {Path(e["path"]).name:e for e in c["files"]}
    def leaf(name):
        p = bind(files[name]); require(p.parent == directory, "Native export escaped sealed directory"); return p
    physical = leaf("physical.bin")
    with physical.open("rb") as f: require(struct.unpack("<III",f.read(12)) == (S,26,N), "Physical header differs")
    pd = np.dtype([("time","<f8"),("q","<f8",(S,26))])
    require(physical.stat().st_size == 12+N*pd.itemsize, "Physical length differs")
    values = np.memmap(physical, mode="r", dtype=pd, offset=12, shape=(N,))
    clock = leaf("clock.bin")
    with clock.open("rb") as f: require(struct.unpack("<II",f.read(8)) == (N,28), "Clock header differs")
    cd = np.dtype([("time","<f8"),("step","<u4"),("dt","<f8"),("error","<f8")])
    require(clock.stat().st_size == 8+N*cd.itemsize, "Clock length differs")
    clocks = np.memmap(clock, mode="r", dtype=cd, offset=8, shape=(N,))
    ids = np.genfromtxt(leaf("native_ids.csv"), delimiter=",", names=True, dtype=None, encoding="utf-8")
    require(np.array_equal(ids["id"],np.arange(40,1040)) and np.array_equal(ids["row"],np.arange(S)), "Exact1000 soil ID order differs")
    x0 = np.column_stack([ids[k] for k in ("x0","y0","z0")]).astype("<f8")
    cols = list(csv.DictReader(leaf("columns.csv").open(encoding="utf-8-sig",newline="")))
    require([v["name"] for v in cols] == F and [int(v["column"]) for v in cols] == list(range(26)), "All26 column names differ")
    require(np.array_equal(values["time"].view("<u8"),clocks["time"].view("<u8")) and np.all(clocks["dt"] == dt) and np.isfinite(clocks["time"]).all(), "Physical/native clock or locked dt differs")
    require(np.isfinite(clocks["error"]).all() and np.all(clocks["error"][1:] <= 1e-14) and np.all(clocks["error"][1:] != -np.finfo(float).max), "Noninitial signed dterror guard rejected")
    require(np.array_equal(values["q"][0,:,:3].view("<u8"),x0.view("<u8")), "Backend initial position/x0 not bitwise exact")
    return dict(check=ce,run=se,build=be,values=values,clock=clocks,x0=x0,backend="GPU" if gpu else "CPU",window=window)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--pair",required=True,choices=["cross-coarse","cross-half","half"]); arg = ap.parse_args()
    name = arg.pair.replace("-","_"); tag = "upl_gpu_column_pair_"+name+"_r1"
    check = T/"logs"/(tag+".check.json"); metrics = T/"figures"/(tag+".csv"); fields = T/"figures"/(tag+"_fields.csv")
    for p in (check,metrics,fields): require(not p.exists(), "Retained output protected: "+str(p))
    result = dict(stage="upl_gpu_column_pair_r1",pair=arg.pair,passed=False,physical_acceptance=False); failure = None
    try:
        adopt(__file__); adopt(T/"notes"/"upl_gpu_column_pair_r1.json")
        a = dataset("coarse" if arg.pair == "half" else arg.pair.split("-")[1],True)
        b = dataset("half",True) if arg.pair == "half" else dataset(a["window"],False)
        result.update(source_run=a["run"],source_runs=[a["run"],b["run"]],source_build=a["build"],native_checks=[a["check"],b["check"]])
        require(np.array_equal(a["x0"].view("<u8"),b["x0"].view("<u8")), "Cross-backend/grid initial soil positions differ")
        ca, cb = a["clock"], b["clock"]; ta, tb = ca["time"], cb["time"]
        completed_a = np.where(np.arange(N)==0,0,ca["step"].astype(np.int64)+1); completed_b = np.where(np.arange(N)==0,0,cb["step"].astype(np.int64)+1)
        require(np.array_equal(completed_b,completed_a*(2 if arg.pair == "half" else 1)), "Exact paired completed-step schedule differs")
        timegap = float(np.max(np.abs(ta-tb))); require(timegap <= 1e-14, "Actual paired time tolerance exceeded")
        x0 = a["x0"]; masks = [x0[:,2] < 2*float(np.float32(0.018)),x0[:,2] > 1-2*float(np.float32(0.018))]
        maxima = np.zeros(26); max_rms = np.zeros(26); pmax = 0.0; umax = 0.0; rows = 0
        with metrics.open("x",newline="",encoding="utf-8") as mf, fields.open("x",newline="",encoding="utf-8") as ff:
            w = csv.writer(mf); f = csv.writer(ff)
            w.writerow(["part","time_a_s","time_b_s","time_difference_s","pressure_RMS_Pa","material_XYZ_displacement_diff_max_mm","du_x_max_mm","du_y_max_mm","du_z_max_mm","velocity_XYZ_RMS_m_s","stress6_RMS_Pa","J_max_abs","theta_max_abs_s_inv","n_derived_max_abs","V_derived_max_abs_m2","rho_derived_max_abs_kg_m3","k_derived_max_abs_m_s","LoadAce_XYZ_RMS_m_s2","legacy_Rhop_max_abs","bottom_support_pressure_RMS_Pa","top_support_pressure_RMS_Pa"])
            f.writerow(["part","time_a_s","time_b_s","column","field","RMS_difference","max_abs_difference"])
            for part in range(N):
                av = np.asarray(a["values"]["q"][part]); bv = np.asarray(b["values"]["q"][part]); require(np.isfinite(av).all() and np.isfinite(bv).all(),"Nonfinite native physical values")
                d = av-bv; rms = np.sqrt(np.mean(d*d,axis=0)); ma = np.max(np.abs(d),axis=0); max_rms = np.maximum(max_rms,rms); maxima = np.maximum(maxima,ma)
                du = (av[:,:3]-x0)-(bv[:,:3]-x0); u = float(1000*np.max(np.linalg.norm(du,axis=1))); p = float(rms[6]); pmax=max(pmax,p); umax=max(umax,u)
                ja,jb=av[:,8],bv[:,8]; n0=float(np.float32(0.3)); v0=float(np.float32(0.21))/2100.0
                nd=float(np.max(np.abs((1-(1-n0)/ja)-(1-(1-n0)/jb)))); vd=float(np.max(np.abs(v0*ja-v0*jb))); rd=float(np.max(np.abs((1000+1100/ja)-(1000+1100/jb))))
                boundary=[float(np.sqrt(np.mean(d[m,6]**2))) for m in masks]
                w.writerow([part,float(ta[part]),float(tb[part]),float(ta[part]-tb[part]),p,u,*[float(v) for v in 1000*np.max(np.abs(du),axis=0)],float(np.sqrt(np.mean(np.sum(d[:,3:6]**2,axis=1)))),float(np.sqrt(np.mean(np.sum(d[:,10:16]**2,axis=1)))),float(ma[8]),float(ma[9]),nd,vd,rd,0.0,float(np.sqrt(np.mean(np.sum(d[:,22:25]**2,axis=1)))),float(ma[25]),*boundary])
                f.writerows([part,float(ta[part]),float(tb[part]),i,F[i],float(rms[i]),float(ma[i])] for i in range(26)); rows+=1
        gates=dict(pressure_RMS_all_times_le_5Pa=bool(pmax<=5.0),material_XYZ_displacement_diff_all_times_le_0_005mm=bool(umax<=0.005),actual_time_difference_le_1e_minus14_s=bool(timegap<=1e-14))
        result.update(passed=bool(all(gates.values())),gates=gates,samples=N,native_count=S,columns=26,metric_rows=rows,field_rows=rows*26,max_pressure_RMS_Pa=pmax,max_material_XYZ_displacement_difference_mm=umax,max_actual_time_difference_s=timegap,max_field_RMS={k:float(v) for k,v in zip(F,max_rms)},max_field_abs={k:float(v) for k,v in zip(F,maxima)},initial_soil_ID_and_x0_bits_exact=True,fixed_backend_fields_compared=False,near_boundary_bands="initial z<2h / z>1-2h, h=float(0.018), descriptive only",comparison_kind="independent_GPU_coarse_half" if arg.pair=="half" else "same_dt_GPU_CPU_native_not_theory",CPU_ompthreads=None if arg.pair=="half" else 1,all26_differences_reported_not_all26_equivalence=True)
        for e in list(TRACKED.values()):
            now=entry(e["path"]); require(now["bytes"]==e["bytes"] and now["sha256"]==e["sha256"],"Input changed during pair")
    except Exception as exc:
        failure = str(exc); result["passed"] = False
    result.update(inputs=list(TRACKED.values()),files=[entry(p) for p in (metrics,fields) if p.exists()],failure=failure,solver_or_decoder_invoked=False,CPU_source_originals_revalidated_as_current=False)
    with check.open("x",encoding="utf-8") as f: json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False); f.write("\n")
    return 0 if result["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())

