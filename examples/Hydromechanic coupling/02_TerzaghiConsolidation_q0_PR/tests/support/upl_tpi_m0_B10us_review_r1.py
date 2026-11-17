"""One offline B10us two-second scientific review; no solver/native/build/hash/old analysis."""
from __future__ import annotations
import argparse
import csv
import json
import math
import os
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
TAG = "upl_tpi_m0_B10us_review_r1"
RUN_TAG = "upl_tpi_m0_dt_B10us_window2s_GPU_r1"
NOTE = T / "notes" / (TAG + ".md")
BASE_XML = T / "configs/upl_bigstep_c625_r1.xml"
PLAN_NOTE = T.parent.parent / "validation/upl_tpi_three_scheme_plan_r1.md"
REVIEW = T / "logs" / (RUN_TAG + ".native_review_m0_r1.json")
READ = T / "logs" / (RUN_TAG + ".native_m0_r1.json")
RUN = T / "logs" / (RUN_TAG + ".run.json")
NATIVE = T / "outputs" / (RUN_TAG + "_native_m0_r1")
A_REVIEW = T / "logs/upl_bigstep_full_r1.review.json"
A_HISTORY = T / "figures/upl_bigstep_full_r1.history.csv"
A_PROFILES = T / "figures/upl_bigstep_full_r1.profiles.csv"
A_TIMES = T / "figures/upl_bigstep_full_r1.profile_times.csv"
A_EXTENDED_CHECK = T / "logs/upl_full_upw_compare_r1.check.json"
A_EXTENDED = T / "figures/upl_full_upw_compare_r1.history.csv"
SHORT_CHECK = T / "logs/upl_tpi_gpu_startup_review_r2.check.json"
SHORT_METRICS = T / "figures/upl_tpi_gpu_startup_review_r2.metrics.json"
SHORT_HISTORY = T / "figures/upl_tpi_gpu_startup_review_r2.history.csv"
DEFINITIONS = (T / "support/upl_tpi_gpu_startup_review_r2.py", T / "support/upl_bigstep_full_review_r1.py", T / "support/gpu_coupled_compare.py")
CHECK = T / "logs" / (TAG + ".check.json")
PRODUCTS = {n: T / "figures" / (TAG + "." + n) for n in
            ("history.csv", "layers.csv", "history.png", "profiles.png", "modes.png", "metrics.json")}
N, SOIL, STEPS, POST = 1263, 1000, 199996, 1159
EVENT, DT, END = .010000228881835938, .010000228881835938/1000., 2.00000577545594
TARGETS = (.005, .05)
COMPONENTS = ("xx", "xy", "xz", "yy", "yz", "zz")
FIELDS = "x y z vx vy vz PorePress PorePress0 J theta sigma_xx sigma_xy sigma_xz sigma_yy sigma_yz sigma_zz Kplastic FSType FSNormal_x FSNormal_y FSNormal_z ExcessPorePress LoadAce_x LoadAce_y LoadAce_z legacy_Rhop".split()


def need(ok, message):
    if not bool(ok): raise ValueError(message)


def stat(path):
    p = Path(path).resolve(); s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def write_json(path, value):
    with path.open("x", encoding="utf8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False); f.write("\n")


def write_csv(path, rows):
    need(bool(rows), "An empty scientific output cannot be published")
    with path.open("x", encoding="utf8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def save_png(fig, path):
    with path.open("xb") as f: fig.savefig(f, format="png", dpi=165)


class Admission:
    def __init__(self, path):
        self.entry = stat(path); self.data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        need(self.data.get("stage") == TAG + ".admission" and self.data.get("passed") is True and
             self.data.get("offline_only") is True, "Root full-read unique offline admission required")
        self.frozen = {str(Path(e["path"]).resolve()): e for e in self.data["inputs"]}
        need(len(self.frozen) == len(self.data["inputs"]), "Duplicated admission input")
        self.used = {}
        for p in (Path(__file__), NOTE, BASE_XML, PLAN_NOTE, *DEFINITIONS): self.pin(p)

    def pin(self, path):
        key = str(Path(path).resolve()); need(key in self.frozen, "Consumed input absent from admission: " + key)
        expected = {k: self.frozen[key][k] for k in ("path", "bytes", "mtime_ns")}
        need(stat(key) == expected, "Root-frozen input stat differs: " + key); self.used[key] = expected
        return Path(key)

    def read(self, path): return json.loads(self.pin(path).read_text(encoding="utf-8-sig"))

    def table(self, path):
        with self.pin(path).open(encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f))

    def finish(self):
        for x in self.used.values(): need(stat(x["path"]) == x, "Consumed input changed during offline review")
        need(stat(self.entry["path"]) == self.entry, "Root admission changed")


def binary(ad, path, header, dtype, np):
    path = ad.pin(path); size = 4*len(header)
    with path.open("rb") as f: need(struct.unpack("<"+"I"*len(header), f.read(size)) == header, "Native export declaration differs: " + path.name)
    need(path.stat().st_size == size+N*dtype.itemsize, "Native export size/stride differs: " + path.name)
    return np.memmap(path, dtype=dtype, mode="r", offset=size, shape=(N,))


def load(ad, np, result):
    review, decoded, run = ad.read(REVIEW), ad.read(READ), ad.read(RUN)
    need(review.get("stage") == "upl_tpi_m0_dt_native_r1.review" and review.get("passed") is True and
         review.get("all22_original_guards_not_relaxed") is True and review.get("method_signed_interval_bit_replay") is True and
         review.get("old_Kw_wave_is_diagnostic_not_method_bound") is True, "Actual unique new-M0 native review must pass first")
    job = review["job"]
    need((job["tag"], job["mode"], job["configuration"], job["scheme"], job["backend"]) ==
         (RUN_TAG, "window2s", "Release", "B", "GPU") and Path(job["native_output"]).resolve() == NATIVE.resolve(), "Actual native job/directory association differs")
    need(decoded.get("stage") == "upl_tpi_m0_dt_native_r1.read" and decoded.get("passed") is True and
         decoded.get("reader_invocations") == 1 and Path(decoded["native_output"]).resolve() == NATIVE.resolve(), "One completed native read required")
    need(run.get("passed") is True and run.get("solver_invocations") == 1 and run.get("mode") == "window2s" and
         run.get("configuration") == "Release" and run.get("scheme") == "B" and run.get("event_divisor") == 1000 and
         run["clock"]["completed_updates"] == STEPS and run["clock"]["native_frames"] == N and
         run["clock"]["post_open_frames"] == POST, "Actual TimeMax crossing is199996 updates, not the200000 upper cap")
    done = ad.read(NATIVE / "completion.json")
    required = dict(passed=True, stage="upl_tpi_m0_dt_native_r1", backend="GPU_M0_private", window="window2s", samples=N,
        native_count=1000, fixed_count=40, total_native_count=1040, native_total_arrays=22, physical_columns=26,
        physical_schema="case02_common26_col21_ExcessPorePress_NOT_wave26", actual_end_s=END, planned_completed_steps=STEPS,
        noninitial_signed_dterror_intervals=N-1, soil_ledger_checks=N*1000, fixed_public_zero_marker_checks=N*40,
        all_native_J_theta_rows=N*1040, post_open_frames=POST, post_open_drained_particle_checks=POST*10,
        post_open_completed_step_threshold=1000, no_exclusions=True, all_exported_physical_fields_finite=True)
    for key, value in required.items(): need(done.get(key) == value, "Native completion differs: " + key)
    need(ad.table(NATIVE / "columns.csv") == [dict(column=str(i), name=s) for i,s in enumerate(FIELDS)], "Case02 common26 columns differ")
    ids = ad.table(NATIVE / "native_ids.csv")
    need(len(ids) == SOIL and [int(r["row"]) for r in ids] == list(range(SOIL)) and [int(r["id"]) for r in ids] == list(range(40,1040)), "All original soil IDs/order differ")
    x0 = np.array([[float(r[c]) for c in ("x0","y0","z0")] for r in ids]); layer = np.rint(x0[:,2]/.01-.5).astype(int); column = np.rint(x0[:,0]/.01-.5).astype(int)
    need(np.array_equal(np.sort(10*layer+column), np.arange(SOIL)) and np.all((layer>=0)&(layer<100)) and
         np.all((column>=0)&(column<10)) and np.all(x0[:,1] == 0), "Original100-by10 material lattice differs")
    order = np.argsort(10*layer+column)
    p = binary(ad,NATIVE/"physical.bin",(1000,26,N),np.dtype([("t","<f8"),("q","<f8",(1000,26))]),np)
    n = binary(ad,NATIVE/"soil_n.bin",(1000,1,N),np.dtype([("t","<f8"),("n","<f8",(1000,))]),np)
    clock = binary(ad,NATIVE/"clock.bin",(N,28),np.dtype([("t","<f8"),("step","<u4"),("dt","<f8"),("signed","<f8")]),np)
    plan, native_history = ad.table(run["plan"]["path"]), ad.table(NATIVE/"history.csv")
    need(len(plan) == len(native_history) == N, "All1263 actual plan/history states required")
    completed = np.array([int(r["completed_steps"]) for r in plan], dtype=np.int64); times = np.array([float(r["time_s"]) for r in plan],dtype="<f8")
    # Unique native phase already replayed scalar +=dt; consume its real payloads without another200k-step replay.
    need(completed[-1] == STEPS and times[-1] == END and np.all(np.diff(times)>0) and
         times.tobytes() == p["t"].tobytes() == n["t"].tobytes() == clock["t"].tobytes(), "Actual scalar-time payloads differ")
    need(np.array_equal(clock["step"],np.maximum(completed-1,0)) and np.all(clock["dt"] == DT), "Native Step/locked-dt differs")
    need(np.isfinite(clock["signed"]).all() and np.all(clock["signed"][1:]<=1e-14) and
         np.all(clock["signed"][1:]!=-np.finfo(float).max), "Original method-specific signed nonempty interval guard failed")
    need(int(np.sum(completed == 1000)) == 1 and int(np.sum(completed>1000)) == POST and
         1001 in completed, "Event1000 preopen/post1001 receiver coverage differs")
    for i,(r,h) in enumerate(zip(plan,native_history)):
        need(int(r["part"]) == int(h["part"]) == i and float(h["time_s"]) == times[i] and
             int(h["completed_step"]) == completed[i] and int(h["saved_step"]) == int(clock["step"][i]), "Actual saved history/plan association differs")
    need(np.isfinite(p["q"]).all() and np.isfinite(n["n"]).all(), "Nonfinite original exports")
    rho = np.empty((N,SOIL)); count=0
    with ad.pin(NATIVE/"ledger.csv").open(encoding="utf8",newline="") as f:
        for r in csv.DictReader(f):
            part,slot=divmod(count,SOIL)
            need(part<N and int(r["part"])==part and int(r["id"])==slot+40 and float(r["time_s"])==times[part] and
                 float(r["J"])==p["q"][part,slot,8] and float(r["n_native"])==n["n"][part,slot], "Native rho ledger ownership/time/J/n differs")
            rho[part,slot]=float(r["rho_native_kg_m3"]);count+=1
    need(count==N*SOIL and np.isfinite(rho).all() and np.all(rho>0), "All native rho rows required")
    runtime=Path(run["output_directory"])
    with ad.pin(runtime/"Run.csv").open(encoding="utf-8-sig",newline="") as f: rt=list(csv.DictReader(f,delimiter=";"))
    need(len(rt)==1 and int(rt[0]["Steps"])==STEPS and int(rt[0]["PartFiles"])==N and int(rt[0]["Np"])==1040 and
         int(rt[0]["PartsOut"])==0 and "gpu" in rt[0]["Hardware"].lower(), "Actual GPU runtime identity differs")
    loop,total=float(rt[0]["TSimul"]),float(rt[0]["TTotal"])
    need(all(math.isfinite(x) and x>0 for x in (loop,total)), "Nonpositive/nonfinite observed runtime")
    result["native_qualification"]=dict(native_review=stat(REVIEW), unique_read=stat(READ), actual_run=stat(RUN),
        method_intervals=review["method_intervals"], pressure_history=review["pressure_sidecar"], HG_original_guards=review["HG_original_guards"],
        old_Kw_wave_is_diagnostic_not_method_bound=True, all22_original_guards_inherited=True)
    timing=dict(TSimul_s=loop,TTotal_s=total,actual_steps=STEPS,native_frames=N,observed_steps_per_TSimul_s=STEPS/loop,
        Hardware=rt[0]["Hardware"],PhysicalTime_rounded_display_not_clock=rt[0]["PhysicalTime"],nonisolated_instrumented_runtime=True,controlled_speedup_benchmark=False)
    return dict(p=p,n=n,clock=clock,completed=completed,x0=x0,order=order,rho=rho,native_history=native_history,
        z0=x0[order,2].reshape(100,10).mean(axis=1),timing=timing,run=run)


def references(ad, d, np):
    root=ET.parse(ad.pin(BASE_XML)).getroot(); value=lambda name:float(next(root.iter(name)).get("value"))
    names=("ModulusE","PRvs","HydraulicConductivity","PoreWaterRho","PoreWaterBulkModulus","Porosity","HydroMechTopLoadQ0","HydroMechDrainageStartTime","HydroMechTopLoadRampTime")
    values=[value(n) for n in names]
    need(values==[2e6,.3,1e-4,1000.,2e8,.3,10000.,EVENT,EVENT], "Original companion physical constants changed")
    seedxml=[x for x in d["run"]["seed"] if Path(x["path"]).suffix==".xml"]
    need(len(seedxml)==1, "Unique actual runtime XML required")
    actual=ET.parse(ad.pin(seedxml[0]["path"])).getroot()
    need([float(next(actual.iter(name)).get("value")) for name in names]==values, "Actual new runtime physical constants differ")
    params={e.get("key"):float(e.get("value")) for e in actual.iter("parameter")}
    need(params["DtFixed"]==params["DtIni"]==DT and params["TimeMax"]==2. and params["SoilHourglassXi"]==.1 and
         params["SoilBoundaryDerivativeSPR"]==1 and params["Visco"]==.1 and params["SoilDampingCoef"]==.04,
         "New runtime numerical options/dt differ; this is HGxi.1, not an HG0 experiment")
    E,nu,k,water,Kw,n0,q0,tD,ramp=values;H,g=1.,9.81;M=E*(1-nu)/((1+nu)*(1-2*nu));Cv=k*M/(water*g);capacity=1/(1+n0*M/Kw)
    lam=(np.arange(512)+.5)*np.pi;coef=2*(-1.)**np.arange(512)/lam
    co=np.cos(lam[:,None]*d["z0"][None,:]/H);si=np.sin(lam[:,None]*d["z0"][None,:]/H)
    valid=d["clock"]["t"]>=tD;P=np.full((N,100),np.nan);settle=np.full((N,100),np.nan)
    decay=np.exp(-Cv*lam[None,:]**2*(d["clock"]["t"][valid,None]-tD)/H**2)
    P[valid]=q0*((decay*coef)@co);settle[valid]=1000*q0/M*(d["z0"][None,:]-H*((decay*coef/lam)@si))
    constants=dict(E_Pa=E,nu=nu,Mc_reference_Pa=M,k_m_s=k,rhow_kg_m3=water,Kw_XML_Pa=Kw,n0=n0,q0_Pa=q0,H_m=H,
        drain_time_s=tD,ramp_time_s=ramp,reference_g_m_s2=g,Cv_M0_m2_s=Cv,Cv_finite_Kw_m2_s=capacity*Cv,
        finite_Kw_capacity=capacity,S_infinity_continuum_surface_mm=1000*q0*H/M,series_modes=512)
    return dict(P=P,settle=settle),constants


def describe(d, ref, c, np):
    rows,layers,failures=[],[],[];sign=np.where(np.arange(10)%2,-1.,1.);arrays={k:[] for k in ("P","settle","total","effective","aUz","aT")}
    for part,q in enumerate(d["p"]["q"]):
        order=d["order"];P=q[order,6].reshape(100,10);settle=-1000*(q[order,2]-d["x0"][order,2]).reshape(100,10)
        effective=q[order,10:16].reshape(100,10,6);total=effective.copy();total[:,:,[0,3,5]]-=P[:,:,None]
        J=q[order,8].reshape(100,10);n=d["n"]["n"][part,order].reshape(100,10);rho=d["rho"][part,order].reshape(100,10)
        aUz=((-settle+settle.mean(axis=1,keepdims=True))*sign).mean(axis=1)
        aT=((total-total.mean(axis=1,keepdims=True))*sign[None,:,None]).mean(axis=1)
        aE=((effective-effective.mean(axis=1,keepdims=True))*sign[None,:,None]).mean(axis=1)
        vertical=total[:,:,5].mean(axis=1);stress=float(max(abs(vertical+c["q0_Pa"])));gap=float(abs(vertical[-1]-vertical[-2]));time=float(d["clock"]["t"][part]);post=time>=.1-1e-7
        if post and (stress>100. or gap>100.):failures.append(dict(part=part,time_s=time,completed_steps=int(d["completed"][part]),max_layer_total_error_Pa=stress,worst_layer=int(np.argmax(abs(vertical+c["q0_Pa"]))),top_pair_total_gap_Pa=gap,original_limit_Pa=100.))
        r=dict(series="new_B10us_M0_GPU_HG0p1",part=part,time_s=time,completed_steps=int(d["completed"][part]),actual_dt_s=DT,
            signed_dterror_s=float(d["clock"]["signed"][part]),legacy_Tv_since_drain=c["Cv_M0_m2_s"]*(time-EVENT),
            pressure_mean_Pa=float(P.mean()),pressure_J_weighted_mean_Pa=float(np.sum(q[:,6]*q[:,8])/np.sum(q[:,8])),pressure_min_Pa=float(P.min()),pressure_max_Pa=float(P.max()),
            top10_settlement_mm=float(settle[-1].mean()),bottom10_settlement_mm=float(settle[0].mean()),speed_XYZ_RMS_m_s=float(np.sqrt(np.mean(np.sum(q[:,3:6]**2,axis=1)))),
            effective_compression_zz_mean_Pa=float(-effective[:,:,5].mean()),total_compression_zz_mean_Pa=float(-total[:,:,5].mean()),max_layer_total_error_Pa=stress,top_pair_total_gap_Pa=gap,
            Q_total_zz_second_difference_RMS_Pa=float(np.sqrt(np.mean(np.diff(vertical,n=2)**2))),original_post_01_guard_applies=post,
            original_stress_guard_passed=not post or stress<=100.,original_top_gap_guard_passed=not post or gap<=100.,
            A_pi_Uz_RMS_mm=float(np.sqrt(np.mean(aUz**2))),A_pi_Uz_abs_max_mm=float(max(abs(aUz))),A_pi_total_stress_6component_RMS_Pa=float(np.sqrt(np.mean(aT**2))),
            J_min=float(J.min()),J_mean=float(J.mean()),J_max=float(J.max()),n_min=float(n.min()),n_mean=float(n.mean()),n_max=float(n.max()),
            rho_native_min_kg_m3=float(rho.min()),rho_native_mean_kg_m3=float(rho.mean()),rho_native_max_kg_m3=float(rho.max()),
            **{"effective_sigma_"+name+"_mean_Pa":float(effective[:,:,j].mean()) for j,name in enumerate(COMPONENTS)},
            **{"total_sigma_"+name+"_mean_Pa":float(total[:,:,j].mean()) for j,name in enumerate(COMPONENTS)},
            companion="M0",companion_mean_pressure_Pa=None,companion_top_settlement_mm=None,companion_bottom_settlement_mm=None,
            P_layer_mean_profile_RMS_error_Pa=None,P_all_native_points_RMS_error_Pa=None,P_all_native_points_abs_error_max_Pa=None,
            top_settlement_signed_error_mm=None,bottom_settlement_signed_error_mm=None)
        valid=bool(np.isfinite(ref["P"][part]).all())
        if valid:r.update(companion_mean_pressure_Pa=float(ref["P"][part].mean()),companion_top_settlement_mm=float(ref["settle"][part,-1]),companion_bottom_settlement_mm=float(ref["settle"][part,0]),
            P_layer_mean_profile_RMS_error_Pa=float(np.sqrt(np.mean((P.mean(axis=1)-ref["P"][part])**2))),P_all_native_points_RMS_error_Pa=float(np.sqrt(np.mean((P-ref["P"][part,:,None])**2))),
            P_all_native_points_abs_error_max_Pa=float(np.max(abs(P-ref["P"][part,:,None]))),top_settlement_signed_error_mm=float(settle[-1].mean()-ref["settle"][part,-1]),bottom_settlement_signed_error_mm=float(settle[0].mean()-ref["settle"][part,0]))
        old=d["native_history"][part]
        for key,oldkey in (("pressure_mean_Pa","pressure_mean_Pa"),("top10_settlement_mm","top10_settlement_mean_mm"),("bottom10_settlement_mm","bottom10_settlement_mean_mm"),("rho_native_mean_kg_m3","native_current_rho_mean_kg_m3")):
            need(math.isclose(r[key],float(old[oldkey]),rel_tol=2e-12,abs_tol=2e-9),"Native summary definition differs: "+key)
        rows.append(r)
        for key,value in (("P",P),("settle",settle),("total",total),("effective",effective),("aUz",aUz),("aT",aT)):arrays[key].append(value)
        for level in range(100):layers.append(dict(part=part,time_s=time,completed_steps=int(d["completed"][part]),initial_layer=level,z0_m=float(d["z0"][level]),
            P_mean_Pa=float(P[level].mean()),P_min_Pa=float(P[level].min()),P_max_Pa=float(P[level].max()),P_std_across_X_Pa=float(P[level].std()),material_settlement_mean_mm=float(settle[level].mean()),
            J_min=float(J[level].min()),J_mean=float(J[level].mean()),J_max=float(J[level].max()),n_native_min=float(n[level].min()),n_native_mean=float(n[level].mean()),n_native_max=float(n[level].max()),
            rho_native_min_kg_m3=float(rho[level].min()),rho_native_mean_kg_m3=float(rho[level].mean()),rho_native_max_kg_m3=float(rho[level].max()),A_pi_Uz_signed_mm=float(aUz[level]),
            **{"effective_sigma_"+name+"_mean_Pa":float(effective[level,:,j].mean()) for j,name in enumerate(COMPONENTS)},
            **{"total_sigma_"+name+"_mean_Pa":float(total[level,:,j].mean()) for j,name in enumerate(COMPONENTS)},
            **{"A_pi_effective_sigma_"+name+"_signed_Pa":float(aE[level,j]) for j,name in enumerate(COMPONENTS)},
            **{"A_pi_total_sigma_"+name+"_signed_Pa":float(aT[level,j]) for j,name in enumerate(COMPONENTS)},
            M0_companion_pressure_Pa=float(ref["P"][part,level]) if valid else None,M0_companion_material_settlement_mm=float(ref["settle"][part,level]) if valid else None))
    d.update(rows=rows,arrays={k:np.array(v) for k,v in arrays.items()});return rows,layers,failures


def contexts(ad, template):
    old=ad.read(A_REVIEW);need(old.get("passed") is True and old.get("stage")=="upl_bigstep_full_review_r1.review", "Retained A compact review required")
    extended=ad.read(A_EXTENDED_CHECK);need(extended.get("passed") is True and extended.get("stage")=="upl_full_upw_compare_r1", "Retained descriptive compact stress/Q source required")
    extra={int(r["part"]):r for r in ad.table(A_EXTENDED) if r["series"]=="current_upl_CPU1_FreeSlip3"}
    a=ad.table(A_HISTORY);need(len(a)==1682 and len(extra)==1682, "Complete retained compact A history association differs")
    out=[]
    for r in a:
        if float(r["time_s"])>END:break
        e=extra[int(r["part"])];need(float(e["time_s"])==float(r["time_s"]), "Retained A stress/Q actual time differs")
        x={key:None for key in template};x.update(series="retained_A_finiteKw_CPU1_FreeSlip_context",part=int(r["part"]),time_s=float(r["time_s"]),completed_steps=int(r["completed_steps"]),actual_dt_s=6.250143051147461e-6,
            legacy_Tv_since_drain=float(r["legacy_Tv_since_drain"]),pressure_mean_Pa=float(r["pressure_mean_Pa"]),pressure_J_weighted_mean_Pa=float(r["pressure_J_weighted_mean_Pa"]),
            top10_settlement_mm=float(r["top_settlement_mm"]),bottom10_settlement_mm=float(r["bottom_settlement_mm"]),total_compression_zz_mean_Pa=float(r["total_compression_zz_mean_Pa"]),
            max_layer_total_error_Pa=float(e["max_layer_total_error_pa"]),top_pair_total_gap_Pa=float(e["top_gap_pa"]),Q_total_zz_second_difference_RMS_Pa=float(e["Q_pa"]),
            A_pi_Uz_RMS_mm=float(r["A_pi_Uz_RMS_mm"]),companion="finite_Kw_context_no_new_reference")
        for key in ["J_min","J_mean","J_max","n_min","n_mean","n_max","rho_native_min_kg_m3","rho_native_mean_kg_m3","rho_native_max_kg_m3",*["total_sigma_"+c+"_mean_Pa" for c in COMPONENTS]]:x[key]=float(r[key])
        out.append(x)
    check,metrics=ad.read(SHORT_CHECK),ad.read(SHORT_METRICS)
    need(check.get("analysis_complete") is True and check["scheme_status"]["B"]["qualified"] is True and
         metrics["schemes"]["B"]["post_01_max_layer_total_error_Pa"]<=100. and metrics["schemes"]["B"]["post_01_max_top_pair_gap_Pa"]<=100., "Retained .15s B qualification differs; failed A must not be hidden")
    short=[r for r in ad.table(SHORT_HISTORY) if r["scheme"]=="B"];need(len(short)==344, "Actual344-state short B history required")
    for r in short:
        x={key:None for key in template};x.update(series="retained_B6p25us_M0_GPU_startup_context",part=int(r["part"]),time_s=float(r["time_s"]),completed_steps=int(r["completed_steps"]),actual_dt_s=6.250143051147461e-6,
            legacy_Tv_since_drain=float(r["legacy_Tv_since_drain"]),pressure_mean_Pa=float(r["pressure_mean_Pa"]),top10_settlement_mm=float(r["top10_settlement_mm"]),bottom10_settlement_mm=float(r["bottom10_settlement_mm"]),
            total_compression_zz_mean_Pa=float(r["total_compression_zz_mean_Pa"]),max_layer_total_error_Pa=float(r["max_layer_total_error_Pa"]),top_pair_total_gap_Pa=float(r["top_pair_total_gap_Pa"]),
            Q_total_zz_second_difference_RMS_Pa=float(r["Q_total_zz_second_difference_RMS_Pa"]),A_pi_Uz_RMS_mm=float(r["A_pi_Uz_RMS_over100layers_mm"]),companion="M0_context_no_new_reference")
        out.append(x)
    a_post=[r for r in out if r["series"].startswith("retained_A") and r["time_s"]>=.1-1e-7]
    a_failed=[r for r in a_post if r["max_layer_total_error_Pa"]>100. or r["top_pair_total_gap_Pa"]>100.]
    return out,ad.table(A_PROFILES),ad.table(A_TIMES),dict(retained_startup_overall_passed=check["passed"],retained_startup_A_failure_preserved=True,
        old_A_compact_history_rows_before_2s=sum(r["series"].startswith("retained_A") for r in out),old_B_context_rows=344,old_A_full_native_or_layer_tables_read=False,
        old_A_post_01_context_states=len(a_post),old_A_post_01_context_100Pa_failure_count=len(a_failed),old_A_first_context_100Pa_failure=a_failed[0] if a_failed else None,
        old_A_description="CPU1/FreeSlip,finiteKw; old100Pa failure remains a failure",old_B_description="GPU6.25us/M0 .15s only; not a2s reference or half control")


def targets(d,ref,c,a_profiles,a_times,np):
    result=[];selected=[]
    for tv in TARGETS:
        target=EVENT+tv/c["Cv_M0_m2_s"];part=int(np.argmin(abs(d["clock"]["t"]-target)))
        need(d["clock"]["t"][0]<=target<=d["clock"]["t"][-1], "Requested Tv outside real2s coverage")
        aa=sorted([r for r in a_profiles if float(r["requested_Tv"])==tv],key=lambda r:int(r["initial_layer"]))
        at=[r for r in a_times if float(r["requested_Tv"])==tv]
        need(len(aa)==100 and len(at)==1 and [int(r["initial_layer"]) for r in aa]==list(range(100)), "Actual retained100-layer A target required")
        at=at[0];need(all(float(r["actual_time_s"])==float(at["actual_time_s"]) for r in aa), "A target own-time association differs")
        epA=float(np.sqrt(np.mean([(float(r["actual_P_mean_Pa"])-float(r["H1_finite_Kw_P_at_actual_time_Pa"]))**2 for r in aa])))
        esA=abs(float(aa[-1]["actual_settlement_mean_mm"])-float(aa[-1]["H1_finite_Kw_settlement_at_actual_time_mm"]))
        ebA=abs(float(aa[0]["actual_settlement_mean_mm"])-float(aa[0]["H1_finite_Kw_settlement_at_actual_time_mm"]))
        b=d["rows"][part];epB=b["P_layer_mean_profile_RMS_error_Pa"];esB=abs(b["top_settlement_signed_error_mm"]);ebB=abs(b["bottom_settlement_signed_error_mm"])
        ppass=epB<=epA+10.;spass=esB<=esA+.001*c["S_infinity_continuum_surface_mm"];bpass=ebB<=.005 and ebB<=ebA+.002
        result.append(dict(requested_legacy_Tv=tv,target_time_s=target,B_actual_part=part,B_actual_time_s=b["time_s"],B_actual_completed_steps=b["completed_steps"],B_signed_target_gap_s=b["time_s"]-target,
            B_actual_Tv=b["legacy_Tv_since_drain"],B_signed_Tv_gap=b["legacy_Tv_since_drain"]-tv,A_actual_part=int(at["actual_part"]),A_actual_time_s=float(at["actual_time_s"]),
            A_signed_target_gap_s=float(at["signed_time_gap_s"]),A_actual_legacy_Tv=float(at["actual_Tv"]),A_applicable_finiteKw_Tv=c["finite_Kw_capacity"]*float(at["actual_Tv"]),
            signed_B_minus_A_time_gap_s=b["time_s"]-float(at["actual_time_s"]),A_P_layer_RMS_error_Pa=epA,B_P_layer_RMS_error_Pa=epB,
            P_error_increment_Pa=epB-epA,P_increment_limit_Pa=10.,P_noninferiority_passed=ppass,
            A_top_abs_error_mm=esA,B_top_abs_error_mm=esB,top_error_increment_percentage_points=100*(esB-esA)/c["S_infinity_continuum_surface_mm"],top_increment_limit_percentage_points=.1,top_noninferiority_passed=spass,
            A_bottom_abs_error_mm=ebA,B_bottom_abs_error_mm=ebB,bottom_abs_limit_mm=.005,bottom_increment_limit_mm=.002,bottom_absolute_and_noninferiority_passed=bpass,
            all_target_budgets_passed=ppass and spass and bpass,A_reference="finite_Kw_at_A_actual_time",B_reference="M0_at_B_actual_time",interpolation=False,sameclock_or_half_equivalence_claim=False))
        selected.append((tv,part,aa))
    return result,selected


def figures(d,ref,contexts,selected,np):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    panels=(("pressure_mean_Pa","Mean native pressure (Pa)"),("top10_settlement_mm","Fixed initial top10 settlement (mm)"),("bottom10_settlement_mm","Fixed initial bottom10 settlement (mm)"),
        ("effective_compression_zz_mean_Pa","Mean effective compression zz (Pa)"),("total_compression_zz_mean_Pa","Mean total compression zz (Pa)"),("max_layer_total_error_Pa","Original total-stress error / top gap (Pa)"),
        ("Q_total_zz_second_difference_RMS_Pa","Total-stress second-difference Q (Pa)"),("J_mean","Native J mean/min/max"),("n_mean","Native porosity mean/min/max"),
        ("rho_native_mean_kg_m3","Native mixture density (kg/m3)"),("speed_XYZ_RMS_m_s","XYZ velocity RMS (m/s)"),("A_pi_Uz_RMS_mm","All100 layers alternating-X Uz RMS (mm)"))
    fig,axes=plt.subplots(4,3,figsize=(18,16),constrained_layout=True);time=d["clock"]["t"]
    for ax,(key,label) in zip(axes.flat,panels):
        ax.plot(time,[r[key] for r in d["rows"]],color="tab:orange",label="New B10us M0 GPU HGxi=.1",lw=1.)
        for series,color in (("retained_A_finiteKw_CPU1_FreeSlip_context","tab:blue"),("retained_B6p25us_M0_GPU_startup_context","tab:green")):
            rr=[r for r in contexts if r["series"]==series and r[key] is not None]
            if rr:ax.plot([r["time_s"] for r in rr],[r[key] for r in rr],color=color,lw=.8,alpha=.8,label="A finiteKw CPU1 context" if color=="tab:blue" else "Old B6.25us .15s context")
        refkey={"pressure_mean_Pa":"companion_mean_pressure_Pa","top10_settlement_mm":"companion_top_settlement_mm","bottom10_settlement_mm":"companion_bottom_settlement_mm"}.get(key)
        if refkey:ax.plot(time,[r[refkey] for r in d["rows"]],"k--",lw=.8,label="M0 quasistatic companion")
        if key=="max_layer_total_error_Pa":
            ax.plot(time,[r["top_pair_total_gap_Pa"] for r in d["rows"]],color="tab:orange",ls=":",label="B top-pair gap");ax.plot([.1,END],[100,100],"k--",label="Original100Pa gate")
        bounds={"J_mean":("J_min","J_max"),"n_mean":("n_min","n_max"),"rho_native_mean_kg_m3":("rho_native_min_kg_m3","rho_native_max_kg_m3")}.get(key)
        if bounds:ax.fill_between(time,[r[bounds[0]] for r in d["rows"]],[r[bounds[1]] for r in d["rows"]],color="tab:orange",alpha=.1)
        ax.set(xlabel="Each source's actual saved time (s)",ylabel=label);ax.grid(True,alpha=.3);ax.legend(fontsize=6)
    fig.suptitle("B10us actual2s window: all startup retained; contexts differ in dt/model/backend, no half-equivalence gate")
    save_png(fig,PRODUCTS["history.png"]);plt.close(fig)
    fig,axes=plt.subplots(3,2,figsize=(13,15),constrained_layout=True)
    for col,(tv,part,a) in enumerate(selected):
        z=d["z0"];az=[float(r["z0_m"]) for r in a]
        values=(d["arrays"]["P"][part].mean(axis=1),d["arrays"]["settle"][part].mean(axis=1),-d["arrays"]["total"][part,:,:,5].mean(axis=1))
        for row,(v,key,label) in enumerate(zip(values,("actual_P_mean_Pa","actual_settlement_mean_mm","actual_total_compression_zz_mean_Pa"),("Pressure (Pa)","Material settlement (mm)","Total compression zz (Pa)"))):
            axes[row,col].plot(v,z,color="tab:orange",marker="x",markevery=8,ms=3,label="B at own actual saved time")
            axes[row,col].plot([float(r[key]) for r in a],az,color="tab:blue",marker="o",fillstyle="none",markevery=8,ms=3,label="A at own actual saved time")
            if row<2:
                axes[row,col].plot(ref["P" if row==0 else "settle"][part],z,"k--",label="M0 companion at B time")
                oldkey="H1_finite_Kw_P_at_actual_time_Pa" if row==0 else "H1_finite_Kw_settlement_at_actual_time_mm"
                axes[row,col].plot([float(r[oldkey]) for r in a],az,"k:",label="FiniteKw companion at A time")
            axes[row,col].set(xlabel=label,ylabel="Initial material z0 (m)");axes[row,col].grid(True,alpha=.3)
        axes[0,col].set_title("Target Tv=%g\nB t=%.10g s, A t=%.10g s"%(tv,float(time[part]),float(a[0]["actual_time_s"])))
    axes[0,-1].legend(fontsize=7);fig.suptitle("Actual nearest Tv=.005/.05 frames: no time/height/load fit or interpolation")
    save_png(fig,PRODUCTS["profiles.png"]);plt.close(fig)
    fig,axes=plt.subplots(3,1,figsize=(13,14),constrained_layout=True)
    for row,(v,title) in enumerate(((d["arrays"]["aUz"],"Signed alternating-X Uz (mm)"),(d["arrays"]["aT"][:,:,5],"Signed alternating total sigma zz (Pa)"))):
        span=float(np.max(abs(v))) or 1.;mesh=axes[row].pcolormesh(time,d["z0"],v.T,shading="nearest",cmap="coolwarm",vmin=-span,vmax=span)
        fig.colorbar(mesh,ax=axes[row],label=title);axes[row].set(xlabel="Actual saved time (s)",ylabel="Initial material z0 (m)",title="All1263 states /100 layers; own symmetric scale")
    axes[2].plot(time,[r["A_pi_Uz_RMS_mm"] for r in d["rows"]],label="100-layer RMS")
    axes[2].plot(time,[r["A_pi_Uz_abs_max_mm"] for r in d["rows"]],label="Max absolute layer mode")
    axes[2].set(xlabel="Actual saved time (s)",ylabel="Alternating-X Uz amplitude (mm)");axes[2].grid(True);axes[2].legend()
    fig.suptitle("B10us fixed-material modes, including1.5–2s; no filtering or inferred late/full-cycle acceptance")
    save_png(fig,PRODUCTS["modes.png"]);plt.close(fig)


def science(ad,result):
    for name in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):os.environ[name]="1"
    import numpy as np
    d=load(ad,np,result);ref,c=references(ad,d,np);history,layers,failures=describe(d,ref,c,np)
    context,a_profiles,a_times,limits=contexts(ad,history[0]);budgets,selected=targets(d,ref,c,a_profiles,a_times,np)
    post=[r for r in history if r["original_post_01_guard_applies"]];late=[r for r in history if r["time_s"]>=1.5]
    passed=not failures and all(r["all_target_budgets_passed"] for r in budgets)
    metrics=dict(stage=TAG,analysis_complete=True,physical_acceptance=False,constants=c,actual_frames=N,actual_updates=STEPS,actual_end_s=END,
        nsteps_upper_cap_200000_is_not_actual_updates=True,actual_runtime=d["timing"],context_limits=limits,noninferiority_targets=budgets,
        pressure_reference="Unfitted H1 M0 at B actual time; retained A finiteKw already evaluated at A own actual time",
        reference_limits="Quasistatic closed-load/top-drainage companion is not exact finite-ramp/band/inertial/current-J startup truth; no fit",
        total_stress_definition="Saved sigma is skeleton effective stress; total=saved_sigma-pI; all six components kept",
        Q_definition="RMS of98 second differences of100 original-layer mean total sigma_zz, not the alternating-X mode",
        original_post_01_stress=dict(start_s=.1-1e-7,max_layer_error_limit_Pa=100.,top_pair_gap_limit_Pa=100.,failures=failures,
            observed_states=len(post),maximum_layer_error_Pa=max(r["max_layer_total_error_Pa"] for r in post),maximum_top_gap_Pa=max(r["top_pair_total_gap_Pa"] for r in post)),
        final=history[-1],all_startup_pressure_min_Pa=min(r["pressure_min_Pa"] for r in history),all_startup_pressure_max_Pa=max(r["pressure_max_Pa"] for r in history),
        late_1p5_2s=dict(actual_saved_states=len(late),max_alternating_Uz_abs_mm=max(r["A_pi_Uz_abs_max_mm"] for r in late),max_alternating_total_stress_RMS_Pa=max(r["A_pi_total_stress_6component_RMS_Pa"] for r in late)),
        HGxi=.1,HG0_test_or_new_control=False,old_A_same_clock_asserted=False,cross_dt_or_cross_model_5Pa_half_gate=False,all22_bit_prefix_proof_claimed=False,
        native_unique_read_not_repeated=True,signed_initial_diagnostic_preserved=True,interpolation=False,pressure_clipping_smoothing_fitting=False,
        new_reference_or_half_run=False,full2Tv_or_general_restart_acceptance=False,public_source_or_formal_admission=False,planned_budgets_passed=passed)
    ad.finish();write_csv(PRODUCTS["history.csv"],history+context);write_csv(PRODUCTS["layers.csv"],layers);write_json(PRODUCTS["metrics.json"],metrics)
    figures(d,ref,context,selected,np);ad.finish()
    result.update(passed=passed,analysis_complete=True,rows=dict(new_history=len(history),context_history=len(context),new_all100_layer_rows=len(layers)),
        original_100Pa_failure_count=len(failures),target_budget_failure_count=sum(not r["all_target_budgets_passed"] for r in budgets),
        metrics=stat(PRODUCTS["metrics.json"]),files=[stat(p) for p in PRODUCTS.values()],physical_acceptance=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--execution-authorized",action="store_true");p.add_argument("--admission",type=Path,required=True);args=p.parse_args()
    need(args.execution_authorized,"Root complete-read unique offline execution required")
    need(not CHECK.exists() and not any(p.exists() for p in PRODUCTS.values()),"Existing/partial science outputs protected; never overwrite")
    ad=Admission(args.admission);result=dict(stage=TAG,passed=False,analysis_complete=False,root_admission=ad.entry,solver_invocations=0,native_invocations=0,
        build_invocations=0,old_analysis_invocations=0,SHA_scans=0,physical_acceptance=False,automatic_follow_up=False)
    try:science(ad,result)
    except Exception as exc:result.update(first_failure=str(exc),partial_outputs_preserved=True);raise
    finally:result["consumed"]=list(ad.used.values());write_json(CHECK,result)
    print(str(CHECK));return 0 if result["passed"] else 2


if __name__=="__main__":raise SystemExit(main())
