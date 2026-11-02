"""CPU-only r2: historical owned-call log provenance repair; all exact comparisons unchanged."""
import argparse, csv, hashlib, json, re, struct
from pathlib import Path
import numpy as np

T = Path(__file__).resolve().parents[1]
N, SOIL, FIXED, TOTAL = 769, 1000, 40, 1040
FIELDS = ["x","y","z","vx","vy","vz","PorePress","PorePress0","J","theta","sigma_xx","sigma_xy","sigma_xz","sigma_yy","sigma_yz","sigma_zz","Kplastic","FSType","FSNormal_x","FSNormal_y","FSNormal_z","ExcessPorePress","LoadAce_x","LoadAce_y","LoadAce_z","legacy_Rhop"]
BOUND = {}
def need(ok, why):
    if not bool(ok): raise ValueError(why)
def readjson(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def entry(path):
    p = Path(path).resolve(); h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024), b""): h.update(block)
    return dict(path=str(p), bytes=p.stat().st_size, sha256=h.hexdigest())
def bind(e):
    p = str(Path(e["path"]).resolve())
    if p not in BOUND: BOUND[p] = entry(p)
    a = BOUND[p]; need(a["bytes"] == e["bytes"] and a["sha256"].lower() == e["sha256"].lower(), "Changed bound file: "+p)
    return Path(p)
def adopt(path):
    e = entry(path); bind(e); return e
def owned(e, historical_log=None):
    c = readjson(bind(e)); need(c["owned_call_exited"] and c["typed_LASTEXITCODE_captured_immediately"] and type(c["exit_code"]) is int and c["exit_code"] == 0 and not c.get("invocation_failure"), "Actual owned typed exit0 required")
    bind(c["program"])
    if historical_log is not None: need("log" not in c, "Unexpected historical CPU call log alias")
    bind(c["log"] if historical_log is None else historical_log)
    if c.get("target_program"): bind(c["target_program"])
    return c
def leaves(c):
    directory = Path(c["paths"]["native_dir"]).resolve(); files = {}
    for e in c["files"]:
        p = bind(e); need(p.parent == directory and p.name not in files, "Duplicate/escaped native leaf"); files[p.name] = e
    return files
def completion(c, backend, public):
    q = readjson(bind(c["completion"]))
    need(q["passed"] and q["physical_acceptance"] is False and q["backend"] == backend+("_public" if public else "_private") and q["window"] == "window25" and q["grid"] == "c" and q["model"] == "constant", "Completion backend/window/model differs")
    need((q["samples"],q["native_count"],q["fixed_count"],q["total_native_count"],q["physical_columns"]) == (N,SOIL,FIXED,TOTAL,26) and q["dt_s"] == 2.5e-6 and q["declared_saved_completed_steps_exact"] and q["actual_time_step_locked_dt_exact"] and q["no_exclusions"], "Native identity/clock guard rejected")
    need(q["physical_schema"] == ("case02_common26_col21_ExcessPorePress_NOT_wave26" if public else "case02_private26_col21_ExcessPorePress_NOT_wave26"), "Undeclared physical schema")
    if public:
        need(q["public_schema"] and q["public_master_on"] and q["native_total_arrays"] == 22 and q["native_dynamic_double_arrays"] == 6 and q["native_PosDiv_present"] and q["native_V_rho_k_present"] and q["PART_typed_public_metadata_verified"] and q["conductivity_model"] == 0 and q["conductivity_Ck"] == 0, "Public native22/typed metadata rejected")
    else:
        need(q["native_J_arrays"] == 3 and q["public_model_metadata_absent_global_and_part"] and not q["native_PosDiv_present"] and not q["native_V_rho_k_present"], "Private native18 schema differs")
    return q
def proof(backend, public):
    name = "upl_column_public_"+backend+"_coarse_r1.native.json" if public else ("upl_case02_flux_window25_coarse_r1.native.check.json" if backend == "CPU" else "upl_gpu_column_actual_coarse_r2.native.json")
    ce = adopt(T/"logs"/name); c = readjson(ce["path"]); need(c["passed"] and c["physical_acceptance"] is False, "Native check rejected")
    q = completion(c,backend,public); files = leaves(c)
    rc = c["reader_call"] if public or backend == "GPU" else c["owned_exit_record"]; call = owned(rc, c["log"] if not public and backend == "CPU" else None)
    helper = readjson(bind(c["reader_helper"] if public else c["reader_build"])); need(helper["passed"], "Reader build rejected"); bind(helper["program"])
    need(helper["program"]["sha256"].lower() == call["program"]["sha256"].lower(), "Owned reader program differs from its build")
    se = c["source_run"] if public or backend == "GPU" else c["sealed_solver"]; r = readjson(bind(se)); need(r["passed"] and r["physical_acceptance"] is False and r["window"] == "coarse", "Source Run rejected")
    owned(r["call"] if public or backend == "GPU" else r["owned_exit_record"], r["log"] if not public and backend == "CPU" else None)
    for e in r["files"]: bind(e)
    need(sum(bool(re.fullmatch(r"Part_\d{4}\.bi4",Path(e["path"]).name)) for e in r["files"]) == N, "Raw PART ownership/count differs")
    if public:
        need(c["source_inputs_raw_objects_runtime_canonical_unchanged"] and r["source_inputs_objects_runtime_canonical_unchanged"] and r["public_project_main"] and not r["fixture_or_Run_override"] and r["backend"] == backend, "Current public main/closure rejected")
        for e in c["inputs"]+r["inputs"]: bind(e)
        for e in helper["author_files"]: bind(e)
        need(len(r["source_snapshot"]) == 265 and len(r["canonical_programs_before"]) == 7 and len(r["runtime"]) == 4, "Current265/canonical7/runtime4 closure differs")
        for row in r["source_snapshot"]:
            bind(row["original"]); bind(row["snapshot"]); need(row["original"]["sha256"] == row["snapshot"]["sha256"], "Current source copy differs")
        for e in r["documentation_snapshot"].values(): bind(e)
        for e in r["canonical_programs_before"]: bind(e)
        for row in r["runtime"]: bind(row["original"]); bind(row["copy"])
        be = r["source_build"]; bind(be); need(readjson(be["path"])["passed"], "Current source build rejected")
    else:
        # These are historical snapshots/raw/export receipts, NEVER historical mutable originals.
        if backend == "CPU":
            need(c["bindings_unchanged"] and c["owned_reader_exit0"] and c["source_solver_exit_verified"] and r["bindings_unchanged"], "Historical CPU ownership rejected")
            h = readjson(bind(r["build"])); be = h["source_build"]; b = readjson(bind(be)); rows = b["source_snapshot"]; bind(r["input_manifest"])
        else:
            need(c["source_input_raw_program_runtime_canonical_unchanged"] and c["live_final"]["byte_exact"] and r["source_inputs_objects_runtime_canonical_unchanged"], "Historical GPU ownership rejected")
            be = r["source_build"]; b = readjson(bind(be)); rows = readjson(bind(r["source_freeze"]))["current_source_snapshot"]
        need(b["passed"] and len(rows) == 265, "Historical build/snapshot rejected")
        for row in rows: bind(row["snapshot"])
    return dict(check=ce,run=se,build=be,files=files,complete=q)
def mapped(e, header, dtype):
    p = bind(e)
    with p.open("rb") as f: need(struct.unpack("<"+"I"*len(header),f.read(4*len(header))) == header, "Binary header differs: "+str(p))
    dt = np.dtype(dtype); need(p.stat().st_size == 4*len(header)+N*dt.itemsize, "Binary length differs")
    return np.memmap(p,mode="r",offset=4*len(header),dtype=dt,shape=(N,))
def bits(a, b):
    return np.asarray(a,dtype="<f8").view("<u8") == np.asarray(b,dtype="<f8").view("<u8")
def take(reader, part, time, first, count, keys):
    out = np.empty((count,len(keys)))
    for row in range(count):
        v = next(reader); need(int(v["part"]) == part and int(v["id"]) == first+row and struct.pack("<d",float(v["time_s"])) == struct.pack("<d",float(time)), "CSV part/ID/actual-time order differs")
        out[row] = [float(v[k]) for k in keys]
    need(np.isfinite(out).all(), "Nonfinite CSV native roundtrip"); return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--backend",required=True,choices=["CPU"]);backend=ap.parse_args().backend
    tag="upl_column_public_"+backend+"_coarse_r2"; check=T/"logs"/(tag+".exact.json"); summary=T/"logs"/(tag+".exact.csv")
    need(not check.exists() and not summary.exists(),"Retained comparison output protected")
    result=dict(stage="upl_column_public_exact_r2",backend=backend,passed=False,physical_acceptance=False,solver_or_decoder_invoked=False,failure=None)
    try:
        adopt(__file__);adopt(T/"notes"/"upl_column_public_exact_r2.json"); adopt(T/"support"/"upl_column_public_exact_r1.py"); adopt(T/"notes"/"upl_column_public_exact_r1.json")
        retired=adopt(T/"logs"/"upl_column_public_CPU_coarse_r1.exact.json"); need(readjson(retired["path"])["passed"] is False,"Retained CPU r1 failure must remain false")
        result.update(retained_CPU_r1_failure=retired,historical_CPU_call_logs_from_parent_receipts=True)
        new=proof(backend,True);old=proof(backend,False); nf,of=new["files"],old["files"]
        whole={leaf:bool(nf[leaf]["bytes"] == of[leaf]["bytes"] and nf[leaf]["sha256"].lower() == of[leaf]["sha256"].lower()) for leaf in ("original15.bin","physical.bin","clock.bin","native_ids.csv","fixed_ids.csv")}
        for f in (nf,of):
            with bind(f["columns.csv"]).open(encoding="utf-8-sig",newline="") as stream: cols=list(csv.DictReader(stream))
            need([r["name"] for r in cols] == FIELDS and [int(r["column"]) for r in cols] == list(range(26)), "Exact common26 field order differs")
            with bind(f["original15.bin"]).open("rb") as stream: need(struct.unpack("<III",stream.read(12)) == (TOTAL,15,N), "Original15 header differs")
            need(f["original15.bin"]["bytes"] == 12+N*166408, "Original15 typed payload length differs")
        p=mapped(of["physical.bin"],(SOIL,26,N),[("time","<f8"),("q","<f8",(SOIL,26))])
        c=mapped(of["clock.bin"],(N,28),[("time","<f8"),("step","<u4"),("dt","<f8"),("error","<f8")])
        nc=mapped(nf["clock.bin"],(N,28),c.dtype)
        j=mapped(nf["common_j_theta.bin"],(TOTAL,2,N),[("time","<f8"),("q","<f8",(TOTAL,2))])
        n=mapped(nf["soil_n.bin"],(SOIL,1,N),[("time","<f8"),("q","<f8",(SOIL,))])
        need(np.all(c["dt"] == 2.5e-6) and np.all(nc["dt"] == 2.5e-6),"Locked coarse dt differs")
        counts=np.zeros(3,dtype=np.int64); rows=0;schema_rows=0
        with bind(of["fixed_samples.csv"]).open(encoding="utf-8-sig",newline="") as ff, bind(of["ledger.csv"]).open(encoding="utf-8-sig",newline="") as lf, bind(nf["fixed_samples.csv"]).open(encoding="utf-8-sig",newline="") as pf, summary.open("x",encoding="utf-8",newline="") as sf:
            fixed,ledger,pubfixed=csv.DictReader(ff),csv.DictReader(lf),csv.DictReader(pf);w=csv.writer(sf)
            w.writerow(["part","actual_time_s","saved_step","J_mismatched_native_IDs","theta_mismatched_native_IDs","n_mismatched_soil_IDs","fixed_n_schema_change_rows","whole_original15_exact","whole_physical26_exact","whole_clock28_exact"])
            fk=("J","theta_zero_marker","n_zero_marker") if backend == "CPU" else ("J_native","theta_native","n_native_mirror_sample")
            for part in range(N):
                time=c["time"][part];need(all(bool(bits(time,a["time"][part])) for a in (p,nc,j,n)),"Exact per-part actual time differs")
                oldfixed=take(fixed,part,time,0,FIXED,fk); oldn=take(ledger,part,time,FIXED,SOIL,("n_native",))[:,0]
                marker=take(pubfixed,part,time,0,FIXED,("J_native","theta_native","n_zero_marker","V_zero_marker","rho_zero_marker","k_zero_marker"))
                expect=np.vstack((oldfixed[:,:2],p["q"][part][:,[8,9]]));got=j["q"][part]
                bad=np.count_nonzero(~bits(got,expect),axis=0);nb=int(np.count_nonzero(~bits(n["q"][part],oldn)));counts+=np.array([int(bad[0]),int(bad[1]),nb])
                need(bits(marker[:,:2],got[:FIXED]).all() and np.all(marker[:,2:] == 0),"Public fixed J/theta or zero markers differ")
                if backend == "CPU": need(bits(oldfixed[:,2],marker[:,2]).all(),"CPU fixed n must remain bitwise zero")
                else: need(np.all((oldfixed[:,2]>0)&(oldfixed[:,2]<1)),"Retained GPU mirror n domain differs")
                changed=int(np.count_nonzero(~bits(oldfixed[:,2],marker[:,2])));schema_rows+=changed
                w.writerow([part,float(time),int(c["step"][part]),int(bad[0]),int(bad[1]),nb,changed,whole["original15.bin"],whole["physical.bin"],whole["clock.bin"]]);rows+=1
            need(next(fixed,None) is None and next(ledger,None) is None and next(pubfixed,None) is None,"Uncompared trailing CSV rows")
        gates=dict(all_original15_typed_exact=whole["original15.bin"],all_common26_fields_exact=whole["physical.bin"],actual_clock_step_dterror_exact=whole["clock.bin"],IDs_exact=bool(whole["native_ids.csv"] and whole["fixed_ids.csv"]),all1040_J_exact=bool(counts[0]==0),all1040_theta_exact=bool(counts[1]==0),all1000_soil_n_exact=bool(counts[2]==0))
        for e in list(BOUND.values()):
            a=entry(e["path"]);need(a["bytes"]==e["bytes"] and a["sha256"]==e["sha256"],"Input changed during exact comparison")
        result.update(passed=bool(all(gates.values())),gates=gates,source_run=new["run"],source_build=new["build"],public_native_check=new["check"],private_native_check=old["check"],private_source_run=old["run"],private_source_build=old["build"],samples=N,native_count=SOIL,fixed_count=FIXED,total_native_count=TOTAL,common_columns=26,summary_rows=rows,all_native_J_theta_rows=TOTAL*N,soil_n_rows=SOIL*N,fixed_schema_rows=FIXED*N,fixed_n_different_rows=schema_rows,mismatches=dict(J=int(counts[0]),theta=int(counts[1]),soil_n=int(counts[2])),whole_files=whole,public_fixed_n_V_rho_k_zero_marker=True,GPU_private_fixed_n_only_schema_change=(backend=="GPU"),historical_mutable_source_originals_verified_as_current=False,CSV_native_values_parsed_once=True)
    except Exception as exc: result["failure"]=str(exc)
    result.update(inputs=list(BOUND.values()),files=[entry(summary)] if summary.exists() else [])
    with check.open("x",encoding="utf-8") as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n")
    print(json.dumps(dict(passed=result["passed"],check=str(check))))
    return 0 if result["passed"] else 1
if __name__=="__main__": raise SystemExit(main())



