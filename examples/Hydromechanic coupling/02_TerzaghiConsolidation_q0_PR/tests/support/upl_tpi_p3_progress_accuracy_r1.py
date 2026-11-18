"""Read sealed selected PARTs of the live P3 run; preliminary, not full native acceptance."""
import csv
import datetime as dtm
import json
import os
from pathlib import Path
import struct
import sys

sys.dont_write_bytecode = True
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"
import numpy as np
import psutil
from upl_tpi_partial_bi4_r1 import read

T = Path(__file__).resolve().parents[1]
TAG = "upl_tpi_p3_progress_accuracy_r1"
JOB = "upl_tpi_p3_B10us_full2tv_GPU_r1"
DATA = T / "outputs" / JOB / "data"
OLD = T / "outputs/upl_tpi_p3_B10us_window2s_GPU_r1_native_p3_r1"
RAW = T / "outputs/upl_tpi_p3_B10us_window2s_GPU_r1/data"
FIG = T / "figures"
CONSUMED = {}


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def stat(path):
    path = Path(path).resolve(); s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def pin(path):
    e = stat(path); CONSUMED[e["path"]] = e
    return Path(path)


def table(path):
    with pin(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def json_native(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError("Unsupported JSON value: " + type(value).__name__)


def load(path):
    e = stat(path); d = read(path)
    need(stat(path) == e == d["file"], "PART changed while being read")
    CONSUMED[e["path"]] = e
    a = d["arrays"]; order = np.argsort(a["Idp"])
    need(np.array_equal(a["Idp"][order], np.arange(1040)), "All1040 unique IDs required")
    return d, {k: v[order] for k, v in a.items()}


def physical(a):
    p = a["PorePress"].astype(float); sk = a["SigmaState_kk"]; si = a["SigmaState_ij"]
    return np.column_stack((a["Posd"], a["Vel"], p, a["PorePress0"],
        a["PoroVolumeRatio"], a["PoroThetaLastStage"], sk[:, 0], si[:, 0], si[:, 2],
        sk[:, 1], si[:, 1], sk[:, 2], a["Kplastic"], a["FSType"], a["FSNormal"],
        a["ExcessPorePress"], a["HydroMechLoadAce"], a["Rhop"]))[40:]


def binary_record(path, header, part, size):
    with pin(path).open("rb") as f:
        need(f.read(len(header)*4) == struct.pack("<"+"I"*len(header), *header), "Original export header changed")
        f.seek(len(header)*4 + part*size)
        payload = f.read(size); need(len(payload) == size, "Truncated original export")
        return payload


def crosscheck():
    """Actual old independent C++ exports, unchanged headers and signed clock bytes."""
    checks = []
    names = "Idp Posd Vel Sigma_kk Sigma_ij FSNormal HydroMechLoadAce Rhop Kplastic PorePress PorePress0 ExcessPorePress SigmaState_kk SigmaState_ij FSType".split()
    for part in (0, 1261):
        d, a = load(RAW / ("Part_%04d.bi4" % part)); v = d["part"]["values"]; t = v["TimeStep"]
        raw = struct.pack("<d", t) + b"".join(a[n].tobytes() for n in names)
        phy = struct.pack("<d", t) + physical(a).astype("<f8").tobytes()
        jt = struct.pack("<d", t) + np.column_stack((a["PoroVolumeRatio"], a["PoroThetaLastStage"])).astype("<f8").tobytes()
        sn = struct.pack("<d", t) + a["PoroPorosity"][40:].astype("<f8").tobytes()
        clock = struct.pack("<dIdd", t, v["Step"], v["SymplecticDtPre"], v["dterror"])
        for name, header, payload in (("original15.bin", (1040,15,1263), raw), ("physical.bin", (1000,26,1263), phy),
                ("common_j_theta.bin", (1040,2,1263), jt), ("soil_n.bin", (1000,1,1263), sn), ("clock.bin", (1263,28), clock)):
            need(binary_record(OLD/name, header, part, len(payload)) == payload, "Independent parser/export byte discrepancy: "+name)
        checks.append(dict(part=part, five_original_exports_byte_equal=True, signed_clock_included=True))
    return checks


def guards(d, a, planned, x0):
    r, v = d["root"]["values"], d["part"]["values"]
    types = {"Idp":8, "Posd":23, "Vel":22, "Rhop":11, "Sigma_kk":22, "Sigma_ij":22,
        "SigmaState_kk":23, "SigmaState_ij":23, "Kplastic":11, "FSType":8, "FSNormal":22,
        "HydroMechLoadAce":22, "PorePress":11, "PorePress0":11, "ExcessPorePress":11, "PosDiv":11}
    types.update({n:12 for n in ("PoroVolumeRatio", "PoroPorosity", "PoroThetaLastStage", "PoroCurrentVolume", "PoroMixtureDensity", "PoroHydraulicConductivity")})
    need(set(a) == set(types) and all(d["types"][n]["type_id"] == typ and len(a[n]) == 1040 for n,typ in types.items()), "Original22 array schema/type/count differs")
    need(all(np.isfinite(x).all() for x in a.values()), "Nonfinite native array")
    need(all(r[k] == n for k,n in dict(CaseNp=1040,CaseNfixed=40,CaseNfluid=1000,CaseNmoving=0,CaseNfloat=0,Npiece=1).items()), "Native counts differ")
    need(r["Dp"] == .01 and r["H"] == float(np.float32(.018)) and r["Rhop0"] == 2100 and r["MassFluid"] == float(np.float32(.21)), "Native geometry/reference mass changed")
    need(v["Npok"] == 1040 and v["Nout"] == 0, "Particle exclusion")
    t, completed = float(planned["time_s"]), int(planned["completed_steps"])
    need(struct.pack("d",v["TimeStep"]) == struct.pack("d",t) and v["Step"] == max(0,completed-1) and v["SymplecticDtPre"] == float(planned["dt_s"]), "Actual clock/Step/dt differs from untouched scalar plan")
    need(v["dterror"] <= 1e-14 and (not completed or v["dterror"] != -sys.float_info.max), "Original nonempty signed dterror guard")
    need(np.all(a["Kplastic"] == 0) and np.all(a["PorePress0"] == 0) and np.all((a["Rhop"]>=700)&(a["Rhop"]<=3000)) and np.all(a["FSType"]<=4), "Elastic/p0/density/FS guard")
    need(np.array_equal(a["ExcessPorePress"], (a["PorePress"]-a["PorePress0"]).astype("<f4")), "Float excess differs")
    need(np.array_equal(a["Sigma_kk"],a["SigmaState_kk"].astype("<f4")) and np.array_equal(a["Sigma_ij"],a["SigmaState_ij"].astype("<f4")), "Double/legacy stress writeback differs")
    need(a["Posd"][:40].tobytes() == x0[:40].tobytes() and np.all(a["Vel"][:40] == 0), "Fixed markers moved")
    need(all(np.all(a[k][:40] == 0) for k in ("PoroPorosity","PoroCurrentVolume","PoroMixtureDensity","PoroHydraulicConductivity","PoroThetaLastStage")), "Fixed public zero markers differ")
    j=a["PoroVolumeRatio"][40:]; n0=float(np.float32(.3)); mass=float(np.float32(.21)); refs={
        "PoroPorosity":1-(1-n0)/j,"PoroCurrentVolume":mass/2100*j,
        "PoroMixtureDensity":1000+1100/j,"PoroHydraulicConductivity":np.full(1000,float(np.float32(.0001)))}
    errors=[float(np.max(np.abs(a[k][40:]-ref)/np.abs(ref))) for k,ref in refs.items()]
    need(np.all(j>1-n0) and max(errors)<=5e-13 and np.all(a["Posd"][40:,2]>0), "Original J/n/V/rho/k or geometry guard")
    fs=a["FSType"][40:]; drain=(fs==2)|(fs==3)
    if completed>=1000: need(int(drain.sum()) == 10, "True drain receiver set differs")
    if completed>1000: need(np.all(a["PorePress"][40:][drain] == 0), "True post-open receiver not drained")
    if completed==1000: need(np.max(np.abs(a["PorePress"][40:][drain]))>0, "Event must remain pre-open")
    return max(errors)


def main():
    need(not (T/"logs"/(TAG+".json")).exists(), "Existing analysis protected")
    psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    started=json.loads(pin(T/"logs"/(JOB+".start.json")).read_text(encoding="utf-8"))
    for key in ("owner","target"):
        e=started[key]; p=psutil.Process(e["pid"])
        need(abs(p.create_time()-e["created"])<1e-6 and p.ppid()==e["parent"] and Path(p.exe()).resolve()==Path(e["exe"]).resolve() and p.cmdline()==e["argv"], "Live ownership changed")
    need(stat(started["program"]["path"]) == started["program"], "Live program stat changed")
    need(stat(started["plan"]["path"]) == started["plan"], "Frozen original scalar plan changed")
    plan=table(started["plan"]["path"])
    log=(T/"outputs"/JOB/"Run.out").read_text(encoding="utf-8")
    lines=[s for s in log.splitlines() if s.startswith("Part_") and len(s.split())>=5]
    latest=int(lines[-1].split()[0].split("_")[1]); last=latest-1
    need(last>1262, "No new sealed long-run coverage")
    constants=json.loads(pin(FIG/"upl_tpi_p3_window_review_r1.metrics.json").read_text(encoding="utf-8"))["constants"]
    cv=constants["Cv_M0_m2_s"]; event=constants["drain_time_s"]
    target_tvs=(.005,.05,.1,.25,.4,.5,.7,.9)
    times=np.array([float(r["time_s"]) for r in plan]); chosen={0,103,104,1261,1262,last}
    chosen.update(int(np.argmin(abs(times[:last+1]-(event+tv/cv)))) for tv in target_tvs if event+tv/cv<=times[last])
    evidence=crosscheck(); first,aa=load(DATA/"Part_0000.bi4"); x0=aa["Posd"].copy()
    old0,oa=load(RAW/"Part_0000.bi4"); need(all(aa[k].tobytes()==oa[k].tobytes() for k in aa), "Initial22 arrays changed")
    soil0=x0[40:]; level=np.rint(soil0[:,2]/.01-.5).astype(int); column=np.rint(soil0[:,0]/.01-.5).astype(int)
    order=np.argsort(10*level+column); need(np.array_equal(np.sort(10*level+column),np.arange(1000)), "Original100x10 lattice differs")
    z=soil0[order,2].reshape(100,10).mean(axis=1); sign=np.where(np.arange(10)%2,-1.,1.)
    rows=[]; profiles=[]; ledgermax=0.; m=constants["Mc_reference_Pa"]; lam=(np.arange(512)+.5)*np.pi; coef=2*(-1.)**np.arange(512)/lam
    theory=table(FIG/"upl_bigstep_full_r1.theory.csv"); at=np.array([float(r["time_s"]) for r in theory])
    for part in sorted(chosen):
        d,a=load(DATA/("Part_%04d.bi4"%part)); ledgermax=max(ledgermax,guards(d,a,plan[part],x0))
        q=physical(a); p=q[order,6].reshape(100,10); s=-1000*(q[order,2]-soil0[order,2]).reshape(100,10)
        effective=q[order,10:16].reshape(100,10,6); total=effective.copy(); total[:,:,[0,3,5]]-=p[:,:,None]
        zz=total[:,:,5].mean(axis=1); alt=((-s+s.mean(axis=1,keepdims=True))*sign).mean(axis=1)
        t=d["part"]["values"]["TimeStep"]; tv=cv*(t-event)
        r=dict(part=part,time_s=t,completed_steps=int(plan[part]["completed_steps"]),legacy_Tv=tv,pressure_mean_Pa=float(p.mean()),top_settlement_mm=float(s[-1].mean()),bottom_settlement_mm=float(s[0].mean()),max_layer_total_error_Pa=float(max(abs(zz+10000))),top_pair_gap_Pa=float(abs(zz[-1]-zz[-2])),Q_Pa=float(np.sqrt(np.mean(np.diff(zz,n=2)**2))),alternating_Uz_max_mm=float(max(abs(alt))),J_mean=float(a["PoroVolumeRatio"][40:].mean()),n_mean=float(a["PoroPorosity"][40:].mean()),signed_dterror_s=d["part"]["values"]["dterror"])
        pr=sr=None
        if int(plan[part]["completed_steps"])>1000:
            decay=np.exp(-lam**2*tv); pr=10000*(decay*coef)@np.cos(lam[:,None]*z); sr=1000*10000/m*(z-(decay*coef/lam)@np.sin(lam[:,None]*z))
            r.update(pressure_profile_RMS_error_Pa=float(np.sqrt(np.mean((p.mean(axis=1)-pr)**2))),theory_top_settlement_mm=float(sr[-1]),top_settlement_error_mm=float(s[-1].mean()-sr[-1]),theory_pressure_mean_Pa=float(pr.mean()))
            old=theory[int(np.argmin(abs(at-t)))]; r.update(A_actual_time_s=float(old["time_s"]),own_minus_A_clock_gap_s=t-float(old["time_s"]),A_pressure_profile_RMS_error_Pa=float(old["H1_finite_Kw_same_node_P_profile_RMS_difference_Pa"]),A_top_settlement_error_mm=float(old["H1_finite_Kw_native_minus_material_top_settlement_mm"]))
        r["original_post01_stress_guard_applies"] = t >= .1-1e-7
        r["original_post01_100Pa_guards_passed"] = not r["original_post01_stress_guard_applies"] or (r["max_layer_total_error_Pa"] <= 100 and r["top_pair_gap_Pa"] <= 100)
        rows.append(r)
        for k in range(100): profiles.append(dict(part=part,time_s=t,legacy_Tv=tv,initial_layer=k,z0_m=float(z[k]),pressure_Pa=float(p[k].mean()),theory_pressure_Pa=None if pr is None else float(pr[k]),settlement_mm=float(s[k].mean()),theory_settlement_mm=None if sr is None else float(sr[k]),total_sigma_zz_Pa=float(zz[k]),alternating_Uz_mm=float(alt[k])))
    for e in CONSUMED.values(): need(stat(e["path"])==e, "Consumed sealed input changed")
    for suffix,data in (("history.csv",rows),("profiles.csv",profiles)):
        keys=list(dict.fromkeys(k for r in data for k in r))
        with (FIG/(TAG+"."+suffix)).open("x",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); w.writerows(data)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    valid=[r for r in rows if "pressure_profile_RMS_error_Pa" in r]
    fig,axs=plt.subplots(2,2,figsize=(12,8),layout="constrained")
    for ax,(field,ref,label) in zip(axs.flat,(("pressure_mean_Pa","theory_pressure_mean_Pa","Mean pressure (Pa)"),("top_settlement_mm","theory_top_settlement_mm","Top material settlement (mm)"),("pressure_profile_RMS_error_Pa","A_pressure_profile_RMS_error_Pa","Own-reference pressure profile RMS error (Pa)"),("top_settlement_error_mm","A_top_settlement_error_mm","Own-reference top settlement error (mm)"))):
        ax.plot([r["legacy_Tv"] for r in valid],[r[field] for r in valid],"o-",label="P3 selected saves",ms=4)
        ax.plot([r["legacy_Tv"] for r in valid],[r[ref] for r in valid],"x--",label="M0 companion" if field in ("pressure_mean_Pa","top_settlement_mm") else "Retained finite-Kw A / own reference",ms=4)
        ax.set(xlabel="Actual legacy Tv since drainage",ylabel=label); ax.grid(alpha=.25); ax.legend(fontsize=8)
    fig.suptitle("P3 live-run snapshots: preliminary, not full-history acceptance")
    with (FIG/(TAG+".png")).open("xb") as f: fig.savefig(f,dpi=160)
    plt.close(fig)
    result=dict(stage=TAG,analysis_complete=True,full_native_review=False,physical_acceptance=False,observed_at=dtm.datetime.now(dtm.timezone(dtm.timedelta(hours=9))).isoformat(),latest_console_line=lines[-1],latest_console_part=latest,analysis_last_part=last,selected_parts=sorted(chosen),sampled_frames=len(rows),selected22_type_ID_clock_ledger_drainage_checks_passed=True,selected_post01_100Pa_failures=[r for r in rows if not r["original_post01_100Pa_guards_passed"]],max_ledger_relative_error=ledgermax,parser_crosscheck=evidence,constant_reference=constants,limits="Selected immutable saves only; not all saved frames, method rounds/HG full counters or full-cycle acceptance. Unfitted H1 M0 versus retained finite-Kw own companion; nearest A clocks retained without interpolation.",inputs=list(CONSUMED.values()),rows=rows,solver_invocations=0,build_invocations=0,SHA_scans=0)
    with (T/"logs"/(TAG+".json")).open("x",encoding="utf-8") as f: json.dump(result,f,indent=2,allow_nan=False,default=json_native)
    print(json.dumps(dict(selected_parts=sorted(chosen),last=rows[-1]),indent=2))


if __name__=="__main__":
    main()
