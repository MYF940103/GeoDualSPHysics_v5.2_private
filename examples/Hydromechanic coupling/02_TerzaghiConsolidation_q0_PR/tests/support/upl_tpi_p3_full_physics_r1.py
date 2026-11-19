"""C02 full P3 scientific diagnostics, using completed native and pressure-method reviews."""
import json
import os
from pathlib import Path

for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[name] = "1"

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import upl_tpi_m0_dt_causal_r1 as prior

T = Path(__file__).resolve().parents[1]
FIG = T.parent / "figures"
TAG = "upl_tpi_p3_full_physics_r1"
JOB = "upl_tpi_p3_B10us_full2tv_GPU_r1"
NATIVE = T / "outputs" / (JOB + "_native_full10us_r1")
DEST = FIG / "upl_tpi_p3_full_diagnostic_r1"
REVIEW = T / "logs" / (JOB + ".native_review_full10us_r1.json")
CHECK = T / "logs" / (TAG + ".check.json")
LAYERS = T / "figures" / (TAG + ".layers.csv.gz")
TARGETS = (.005, .05, .1, .25, .4, .5, .7, 1., 1.5, 2.)
COMPONENTS = ("xx", "xy", "xz", "yy", "yz", "zz")
N = 1653


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_table(path, **kwargs):
    return pd.read_csv(path, float_precision="round_trip", **kwargs)


class Inputs:
    """Bind existing immutable inputs by stat while sharing original binary/theory helpers."""
    def __init__(self):
        self.stats = {}

    def pin(self, path):
        path = Path(path).resolve()
        st = path.stat()
        old = self.stats.setdefault(path, (st.st_size, st.st_mtime_ns))
        require(old == (st.st_size, st.st_mtime_ns), f"Input changed: {path}")
        return path

    def table(self, path, **kwargs):
        return read_table(self.pin(path), **kwargs)


def read_data(inputs):
    review = load_json(inputs.pin(REVIEW))
    require(review["passed"] and review["stage"] == "upl_tpi_p3_full_native_r1.review"
            and review["all22_original_guards_not_relaxed"]
            and review["job"]["tag"] == JOB
            and Path(review["job"]["native_output"]).resolve() == NATIVE.resolve(),
            "A completed, genuine full P3 method/native review is required")
    require(review["completion"]["samples"] == N, "Unexpected native coverage")
    frame = inputs.table(NATIVE / "history.csv")
    plan = inputs.table(T / "logs/upl_tpi_p3_full_plan_r1.clock.csv")
    ids = inputs.table(NATIVE / "native_ids.csv")
    schema = inputs.table(NATIVE / "columns.csv")
    require(list(schema.name) == list(prior.FIELDS) and np.array_equal(ids.id, np.arange(40, 1040)),
            "Physical column or original material ID association changed")
    xy = ids[["x0", "z0"]].to_numpy()
    key = np.rint(xy[:, 0] / .01 - .5).astype(int) + 10*np.rint(xy[:, 1] / .01 - .5).astype(int)
    require(np.array_equal(np.sort(key), np.arange(1000)), "Unexpected material lattice")
    ix = np.argsort(key)
    z = xy[ix, 1].reshape(100, 10).mean(axis=1)
    expect_t = plan.time_s.to_numpy()
    require(np.array_equal(plan.part, np.arange(N)) and np.array_equal(plan.completed_steps, frame.completed_step)
            and np.array_equal(expect_t, frame.time_s) and expect_t[-1] == 72.88428815806371,
            "Native and planned clocks differ")
    records = prior.binary(inputs, NATIVE / "physical.bin", (1000, 26, N),
                           np.dtype([("t","<f8"),("q","<f8",(1000,26))]), np)
    poro = prior.binary(inputs, NATIVE / "soil_n.bin", (1000, 1, N),
                        np.dtype([("t","<f8"),("n","<f8",(1000,))]), np)
    require(np.array_equal(records["t"], expect_t) and np.array_equal(poro["t"], expect_t), "Native clock association")
    # Read the stored mixture density, which differs from the single-precision legacy Rhop.
    ledger = inputs.table(NATIVE / "ledger.csv", usecols=["part","id","time_s","rho_native_kg_m3"])
    require(len(ledger) == N*1000 and np.array_equal(ledger.part, np.repeat(np.arange(N), 1000))
            and np.array_equal(ledger.id, np.tile(ids.id, N))
            and np.array_equal(ledger.time_s, np.repeat(expect_t, 1000)), "Ledger order/identity/time differs")
    rho = ledger.rho_native_kg_m3.to_numpy().reshape(N, 1000)
    return frame, records["q"], poro["n"], rho, xy[ix,1].reshape(100,10), ix, z


def collapse_layers(q, n, rho, z0_by_id, order):
    """Use blockwise access to the sealed common26 export and keep every layer and frame."""
    keys = ("p", "pmin", "pmax", "settlement", "J", "n", "rho", "alt_Uz")
    layers = {name: np.empty((N,100)) for name in keys}
    for name in COMPONENTS:
        for prefix in ("effective_", "total_", "alt_total_"):
            layers[prefix+name] = np.empty((N,100))
    within_pressure_var = np.empty((N,100))
    signs = np.where(np.arange(10)%2, -1., 1.)
    for i in range(N):
        a = q[i, order].reshape(100,10,26)
        p = a[:,:,6]
        settle = 1000*(z0_by_id - a[:,:,2])
        layers["p"][i] = p.mean(axis=1)
        layers["pmin"][i] = p.min(axis=1)
        layers["pmax"][i] = p.max(axis=1)
        within_pressure_var[i] = p.var(axis=1)
        layers["settlement"][i] = settle.mean(axis=1)
        layers["alt_Uz"][i] = ((-settle+layers["settlement"][i,:,None])*signs).mean(axis=1)
        layers["J"][i] = a[:,:,8].mean(axis=1)
        layers["n"][i] = n[i,order].reshape(100,10).mean(axis=1)
        layers["rho"][i] = rho[i,order].reshape(100,10).mean(axis=1)
        for j, name in enumerate(COMPONENTS):
            eff = a[:,:,10+j]
            total = eff - p if name in ("xx","yy","zz") else eff
            layers["effective_"+name][i] = eff.mean(axis=1)
            layers["total_"+name][i] = total.mean(axis=1)
            layers["alt_total_"+name][i] = ((total-total.mean(axis=1,keepdims=True))*signs).mean(axis=1)
    return layers, within_pressure_var


def rms(a, axis):
    return np.sqrt(np.mean(a*a, axis=axis))


def target_rows(h, ah, c, upw_targets):
    rows = []
    for tv in TARGETS:
        target = c["drain_time_s"] + tv/c["Cv_M0_m2_s"]
        i = int(np.argmin(abs(h.time_s.to_numpy()-target)))
        j = int(np.argmin(abs(ah.time_s.to_numpy()-target)))
        b, a = h.iloc[i], ah.iloc[j]
        upw = upw_targets.loc[tv]
        require(int(upw.current_part)==j and abs(upw.current_layer_mean_RMS_vs_H1_finite_Kw_Pa-a.pressure_layer_rms_Pa)<1e-9,
                "Retained A declared-target RMS or clock differs")
        cp = b.pressure_layer_rms_Pa-a.pressure_layer_rms_Pa
        ct = abs(b.top_err_mm)-abs(a.top_err_mm)
        cb = abs(b.bottom_err_mm)-abs(a.bottom_err_mm)
        pp = cp <= 10 and (tv < 1 or cp <= 5)
        sp = ct <= .001*c["S_infinity_continuum_surface_mm"]
        bp = cb <= .002 and abs(b.bottom_err_mm) <= .005
        rows.append(dict(target_Tv=tv,target_time_s=target,P3_part=i,A_part=j,
                         P3_time_s=b.time_s,A_time_s=a.time_s,upw_time_s=upw.old_actual_time_s,
                         P3_actual_Tv=b.Tv,A_actual_Tv=a.Tv,upw_actual_Tv=upw.old_actual_Tv,
                         P3_layer_RMS_Pa=b.pressure_layer_rms_Pa,A_layer_RMS_Pa=a.pressure_layer_rms_Pa,
                         upw_classical_layer_RMS_Pa=upw.old_layer_mean_RMS_vs_own_classical_Pa,
                         P3_particle_RMS_Pa=b.all_points_rms_Pa,P3_pressure_min_Pa=b.pressure_min_Pa,
                         P3_pressure_max_Pa=b.pressure_max_Pa,P3_max_alt_Uz_mm=b.alt_Uz_max_mm,
                         pressure_increment_Pa=cp,pressure_limit_Pa=5 if tv>=1 else 10,
                         P3_top_err_mm=b.top_err_mm,A_top_err_mm=a.top_err_mm,abs_top_increment_mm=ct,
                         top_increment_limit_mm=.001*c["S_infinity_continuum_surface_mm"],
                         P3_bottom_err_mm=b.bottom_err_mm,A_bottom_err_mm=a.bottom_err_mm,abs_bottom_increment_mm=cb,
                         bottom_increment_limit_mm=.002,bottom_absolute_limit_mm=.005,
                         pressure_pass=pp,top_pass=sp,bottom_pass=bp,all_targets_here_pass=pp and sp and bp))
    return pd.DataFrame(rows)


def nearest(times, target):
    right = np.clip(np.searchsorted(times, target), 0, len(times)-1)
    left = np.maximum(0, right-1)
    return np.where(abs(times[right]-target) < abs(times[left]-target), right, left)


def histories(inputs, frame, layers, variance, z):
    # The reference helper evaluates the original, unfitted 512-mode solution on each
    # material layer at actual times. Suppress closed-drain values using completed step.
    old_layers = inputs.table(T/"figures/upl_bigstep_full_r1.layers.csv",
                              usecols=["part","initial_layer","time_s","z0_m","P_mean_Pa"])
    old_raw = inputs.table(T/"figures/upl_bigstep_full_r1.history.csv")
    require(np.array_equal(old_layers.part, np.repeat(old_raw.part,100)) and
            np.array_equal(old_layers.initial_layer, np.tile(np.arange(100),len(old_raw))) and
            np.array_equal(old_layers.time_s,np.repeat(old_raw.time_s,100)), "Retained A layer indexing differs")
    ref = {"B":{"z0":z,"clock":{"t":frame.time_s.to_numpy()}},
           "A":{"z0":old_layers.z0_m.to_numpy()[:100],"clock":{"t":old_raw.time_s.to_numpy()}}}
    c = prior.references(inputs, ref, np)
    b_ref, a_ref = ref["B"]["ref"], ref["A"]["ref"]
    for fields, closed in ((b_ref, frame.completed_step.to_numpy()<=1000),
                           (a_ref, old_raw.completed_steps.to_numpy()<=1600)):
        fields["P"][closed] = np.nan
        fields["settle"][closed] = np.nan

    pe = layers["p"] - b_ref["P"]
    se = layers["settlement"] - b_ref["settle"]
    zz = layers["total_zz"]
    error = abs(zz+c["q0_Pa"])
    h = pd.DataFrame(dict(part=frame.part,time_s=frame.time_s,completed_step=frame.completed_step,
        Tv=c["Cv_M0_m2_s"]*(frame.time_s-c["drain_time_s"]),mean_pressure_Pa=layers["p"].mean(axis=1),
        reference_mean_pressure_Pa=b_ref["P"].mean(axis=1),pressure_layer_rms_Pa=rms(pe,1),
        all_points_rms_Pa=np.sqrt((pe**2+variance).mean(axis=1)),
        pressure_min_Pa=layers["pmin"].min(axis=1),pressure_max_Pa=layers["pmax"].max(axis=1),
        bottom_pressure_Pa=layers["p"][:,0],ref_bottom_pressure_Pa=b_ref["P"][:,0],
        top_settlement_mm=layers["settlement"][:,-1],ref_top_mm=b_ref["settle"][:,-1],top_err_mm=se[:,-1],
        bottom_settlement_mm=layers["settlement"][:,0],ref_bottom_mm=b_ref["settle"][:,0],bottom_err_mm=se[:,0],
        mean_total_zz_Pa=zz.mean(axis=1),max_layer_stress_error_Pa=error.max(axis=1),
        worst_layer=error.argmax(axis=1),top_gap_Pa=abs(zz[:,-1]-zz[:,-2]),
        Q_Pa=rms(np.diff(zz,n=2,axis=1),1),alt_Uz_max_mm=abs(layers["alt_Uz"]).max(axis=1),
        alt_stress_zz_max_Pa=abs(layers["alt_total_zz"]).max(axis=1),
        mean_J=layers["J"].mean(axis=1),mean_n=layers["n"].mean(axis=1),mean_rho=layers["rho"].mean(axis=1),
        speed_RMS_m_s=frame.velocity_XYZ_RMS_m_s))
    for a,b in ((h.mean_pressure_Pa,frame.pressure_mean_Pa),(h.mean_rho,frame.native_current_rho_mean_kg_m3),
                (h.top_settlement_mm,frame.top10_settlement_mean_mm),(h.bottom_settlement_mm,frame.bottom10_settlement_mean_mm)):
        require(np.allclose(a,b,rtol=2e-12,atol=2e-9), "Independent native history disagrees")
    h["stress_guard_applies"] = h.time_s>=.1-1e-7
    h["violating_layers"] = np.count_nonzero(error>100,axis=1)
    h["stress_guard_failed"] = h.stress_guard_applies & (h.max_layer_stress_error_Pa>100)
    h["top_gap_guard_failed"] = h.stress_guard_applies & (h.top_gap_Pa>100)
    ap = old_layers.P_mean_Pa.to_numpy().reshape(-1,100)
    ah = pd.DataFrame(dict(part=old_raw.part,time_s=old_raw.time_s,Tv=old_raw.legacy_Tv_since_drain,
        mean_pressure_Pa=old_raw.pressure_mean_Pa,bottom_pressure_Pa=old_raw.bottom_pressure_Pa,
        top_settlement_mm=old_raw.top_settlement_mm,bottom_settlement_mm=old_raw.bottom_settlement_mm,
        pressure_layer_rms_Pa=rms(ap-a_ref["P"],1),top_err_mm=old_raw.top_settlement_mm-a_ref["settle"][:,-1],
        bottom_err_mm=old_raw.bottom_settlement_mm-a_ref["settle"][:,0]))
    old_ph = inputs.table(FIG/"full_validation_upl_CPU1_r1_focus_history.csv")
    a_stress = old_ph[old_ph.series=="current_upl_CPU1_FreeSlip3"].reset_index(drop=True)
    require(np.array_equal(a_stress.time_s,ah.time_s), "Retained A stress history clock differs")
    ah["max_layer_stress_error_Pa"] = a_stress.max_layer_total_error_Pa
    ah["top_gap_Pa"] = a_stress.top_gap_Pa
    ah["Q_Pa"] = a_stress.Q_Pa
    j = nearest(ah.time_s.to_numpy(),h.time_s.to_numpy())
    h["nearest_A_part"] = j
    h["P3_minus_A_time_s"] = h.time_s.to_numpy()-ah.time_s.to_numpy()[j]
    h["pressure_increment_at_nearest_A_Pa"] = h.pressure_layer_rms_Pa.to_numpy()-ah.pressure_layer_rms_Pa.to_numpy()[j]
    return h,ah,c,b_ref,error

def csv_outputs(h, ah, layers, xref, z, targets, old_profiles, upw, c):
    h.to_csv(DEST/"history.csv", index=False)
    ah.to_csv(DEST/"explicit_A_history.csv", index=False)
    upw.to_csv(DEST/"upw_history.csv", index=False)
    targets.to_csv(DEST/"targets.csv", index=False)
    # The 401 requested uniform comparison times are indices, not new/interpolated states.
    requested = np.arange(401)*.005
    target_times = c["drain_time_s"]+requested/c["Cv_M0_m2_s"]
    picked = nearest(h.time_s.to_numpy(), target_times)
    grid = h.iloc[picked].reset_index(drop=True).copy()
    grid.insert(0,"target_Tv",requested)
    grid.insert(1,"target_time_s",target_times)
    grid["actual_minus_target_s"] = grid.time_s-target_times
    grid.to_csv(DEST/"standard_grid.csv", index=False)
    p3rows = []
    for r in targets.itertuples():
        i = r.P3_part
        p3rows.append(pd.DataFrame(dict(target_Tv=r.target_Tv,part=i,time_s=r.P3_time_s,actual_Tv=r.P3_actual_Tv,
            initial_layer=np.arange(100),z0_m=z,pressure_Pa=layers["p"][i],reference_pressure_Pa=xref["P"][i],
            settlement_mm=layers["settlement"][i],reference_settlement_mm=xref["settle"][i],
            total_zz_Pa=layers["total_zz"][i],J=layers["J"][i],n=layers["n"][i],rho_kg_m3=layers["rho"][i])))
    profiles = pd.concat(p3rows,ignore_index=True)
    joint = profiles.merge(old_profiles, on=["target_Tv","initial_layer"],how="left",validate="one_to_one")
    require(len(joint)==1000 and np.isfinite(joint["old_pressure_Pa"]).all(),"Missing comparison layer")
    joint.to_csv(DEST/"profiles.csv",index=False)
    table = {"part":np.repeat(h.part,100),"time_s":np.repeat(h.time_s,100),
             "actual_Tv":np.repeat(h.Tv,100),"initial_layer":np.tile(np.arange(100),N),"z0_m":np.tile(z,N)}
    names = {"p":"pressure_Pa","pmin":"min_pressure_Pa","pmax":"max_pressure_Pa","settlement":"settlement_mm",
             "J":"J","n":"n","rho":"rho_kg_m3","alt_Uz":"alternating_Uz_mm"}
    for name, val in layers.items():
        table[names.get(name,name+"_Pa")] = val.reshape(-1)
    table["reference_pressure_Pa"] = xref["P"].reshape(-1)
    table["reference_settlement_mm"] = xref["settle"].reshape(-1)
    pd.DataFrame(table).to_csv(LAYERS, index=False, compression={"method":"gzip","compresslevel":3})
    return joint


def intervals(h):
    mask = h.stress_guard_failed.to_numpy() | h.top_gap_guard_failed.to_numpy()
    transitions = np.diff(np.r_[False,mask,False].astype(int))
    brackets = []
    for start, stop in zip(np.flatnonzero(transitions==1),np.flatnonzero(transitions==-1)):
        final = stop-1
        worst = h.iloc[start:stop].max_layer_stress_error_Pa.idxmax()
        brackets.append(dict(first_failed_part=int(start),last_failed_part=int(final),failed_saves=stop-start,
            preceding_pass_s=float(h.time_s[start-1]) if start else None,
            first_failed_s=float(h.time_s[start]),last_failed_s=float(h.time_s[final]),
            next_pass_s=float(h.time_s[stop]) if stop<len(h) else None,
            observed_span_s=float(h.time_s[final]-h.time_s[start]),worst_saved_part=int(worst),
            worst_time_s=float(h.time_s[worst]),max_layer_error_Pa=float(h.max_layer_stress_error_Pa[worst]),
            worst_layer=int(h.worst_layer[worst])))
    return pd.DataFrame(brackets,columns=["first_failed_part","last_failed_part","failed_saves","preceding_pass_s",
        "first_failed_s","last_failed_s","next_pass_s","observed_span_s","worst_saved_part","worst_time_s","max_layer_error_Pa","worst_layer"])


def plots(h, ah, uh, profiles, targets):
    plt.rcParams.update({"font.size":10,"axes.spines.top":False,"axes.spines.right":False,
                         "axes.titlelocation":"left","axes.grid":True,"grid.alpha":.18,"axes.axisbelow":True})
    main, base, old, ref = "#17638a","#d37623","#776991","#171c25"
    colors = plt.colormaps["plasma"](np.linspace(.05,.86,len(TARGETS)))
    fig, axs = plt.subplots(2,2,figsize=(13,9),layout="constrained")
    for (tv, group),color in zip(profiles.groupby("target_Tv",sort=True),colors):
        axs[0,0].plot(group.reference_pressure_Pa/1000,group.z0_m,color=color,lw=1.25,label=f"{tv:g}")
        axs[0,0].plot(group.pressure_Pa.iloc[::5]/1000,group.z0_m.iloc[::5],ls="none",marker="o",mfc="white",
                      mec=color,ms=3)
    axs[0,0].set(title="a   Pore-pressure profiles",xlabel="Pore pressure (kPa)",ylabel="Initial material height (m)")
    axs[0,0].legend(title="Target $T_v$  ·  lines: reference, circles: P3",ncol=5,loc="upper right",fontsize=8,title_fontsize=8)
    def series(ax, field, aref, ylab, title, upfield=None):
        ax.plot(h.Tv,h[aref],color=ref,ls="--",lw=1.8,label="M0 reference")
        ax.plot(ah.Tv,ah[field],color=base,ls=":",lw=1.6,label="Explicit A")
        if upfield:
            ax.plot(uh.tv,uh[upfield],color=old,ls="-.",lw=1,label="u-pw (Vel0)")
        ax.plot(h.Tv,h[field],color=main,lw=1,marker="o",markevery=63,ms=2.5,label="P3")
        ax.set(title=title,xlabel="Drainage time factor $T_v$",ylabel=ylab,xlim=(-.012,2.035))
        ax.legend(fontsize=8)
    series(axs[0,1],"mean_pressure_Pa","reference_mean_pressure_Pa","Mean pore pressure (Pa)","b   Pressure dissipation","mean_pressure_pa")
    series(axs[1,0],"bottom_pressure_Pa","ref_bottom_pressure_Pa","Bottom pore pressure (Pa)","c   Bottom material layer")
    series(axs[1,1],"top_settlement_mm","ref_top_mm","Downward settlement (mm)","d   Top material settlement","top_settlement_mm")
    fig.suptitle("Full-cycle C02 consolidation   |   P3 and analytical reference",fontsize=17)
    fig.savefig(DEST/"overview.png",dpi=170); plt.close(fig)
    # Dedicated panels keep small late-time pressure profiles legible without clipping.
    fig, ax = plt.subplots(2,5,figsize=(16,7.3),sharey=True,layout="constrained")
    styles=[("reference_pressure_Pa","M0 theory",ref,"-"),("old_pressure_Pa","u-pw (Vel0)",old,"-."),
            ("new_pressure_Pa","Explicit A",base,"--"),("pressure_Pa","P3",main,"none")]
    for a,(tv,g) in zip(ax.flat, profiles.groupby("target_Tv",sort=True)):
        for field,label,color,ls in styles:
            a.plot(g[field]/1000,g.z0_m,label=label,color=color,ls=ls,lw=1.1,marker="o" if ls=="none" else None,
                   markevery=4,ms=2.8,mfc="white",mec=color)
        a.set_title(f"Target $T_v$ = {tv:g}",fontsize=11)
        a.set_xlabel("Pore pressure (kPa)",fontsize=9);a.tick_params(labelsize=8)
    for a in ax[:,0]: a.set_ylabel("Initial height (m)")
    ax[1,-1].legend(fontsize=8,loc="upper right")
    fig.suptitle("C02 pore-pressure profiles at ten target times",fontsize=16)
    fig.savefig(DEST/"profiles.png",dpi=165);plt.close(fig)
    fig, axes=plt.subplots(2,3,figsize=(15,8),layout="constrained")
    for ax,k,title,y in zip(axes.flat,
            ("pressure_layer_rms_Pa","top_err_mm","bottom_err_mm","max_layer_stress_error_Pa","Q_Pa","alt_Uz_max_mm"),
            ("a   100-layer pressure error","b   Top settlement error","c   Bottom settlement error",
             "d   Stress balance from 0.1 s","e   Vertical stress curvature from 0.1 s","f   Alternating-column displacement"),
            ("RMS error (Pa)","Signed error (mm)","Signed error (mm)","Largest layer error (Pa)","RMS second difference (Pa)","Max amplitude (mm)")):
        for d,l,col in ((ah,"Explicit A",base),(h,"P3",main)):
            if k not in d: continue
            view = d.loc[d.time_s>=.1-1e-7] if k in ("max_layer_stress_error_Pa","Q_Pa") else d
            ax.plot(view.Tv,view[k],color=col,label=l,lw=1.15,ls="--" if l=="Explicit A" else "-")
        if k=="max_layer_stress_error_Pa": ax.axhline(100,color="#a32732",ls=":",label="100 Pa limit")
        if k=="pressure_layer_rms_Pa": ax.set_yscale("log")
        ax.set(title=title,xlabel="Drainage time factor $T_v$",ylabel=y);ax.legend(fontsize=8)
    fig.suptitle("P3 accuracy and stress diagnostics across the full cycle",fontsize=16)
    fig.savefig(DEST/"diagnostics.png",dpi=165);plt.close(fig)
    # Early dynamics use physical time so the ramp and first drained step remain visible.
    fig, ax=plt.subplots(2,2,figsize=(10,6.7),layout="constrained")
    for axis,field,ylab,title in zip(ax.flat,("mean_pressure_Pa","top_settlement_mm","mean_J","speed_RMS_m_s"),
           ("Mean pressure (Pa)","Settlement (mm)","Mean volume ratio J","RMS speed (m/s)"),
           ("a   Mean pore pressure","b   Top material settlement","c   Volume ratio","d   Particle speed")):
        v=h[h.time_s<=.15]; axis.plot(v.time_s,v[field],color=main,lw=1,label="P3")
        if field in ah:
            v=ah[ah.time_s<=.15];axis.plot(v.time_s,v[field],color=base,ls="--",lw=.9,label="Explicit A")
        axis.axvline(.010000228881835938,color=ref,ls=":",lw=1,label="Drainage event")
        axis.set(title=title,xlabel="Simulation time (s)",ylabel=ylab); axis.legend(fontsize=8)
    fig.suptitle("C02 startup at original saved times",fontsize=15)
    fig.savefig(DEST/"startup.png",dpi=150);plt.close(fig)


def time_measurements(inputs):
    rows=[]
    for name,job in (("P3 GPU RTX 3050",JOB),("Explicit A CPU1","upl_bigstep_2tv_CPU1_r1")):
        run = inputs.table(T/"outputs"/job/"Run.csv",sep=";").iloc[0]
        rows.append(dict(scheme=name,steps=int(run.Steps),saves=int(run.PartFiles),loop_s=float(run.TSimul),
                         wall_s=float(run.TTotal),updates_per_loop_second=float(run.Steps/run.TSimul)))
    return rows


def write_json(path, payload):
    def scalar(x):
        if isinstance(x,np.generic):return x.item()
        raise TypeError(f"Unserializable {type(x)}")
    with path.open("x",encoding="utf-8") as f:
        json.dump(payload,f,ensure_ascii=False,indent=2,allow_nan=False,default=scalar)


def main():
    require(all(not p.exists() for p in (DEST,CHECK,LAYERS)), "Existing analysis outputs protected")
    inputs = Inputs()
    frame,q,n,rho,z0,order,z = read_data(inputs)
    layers,variance = collapse_layers(q,n,rho,z0,order)
    h,ah,c,refs,error = histories(inputs,frame,layers,variance,z)
    old_targets = inputs.table(FIG/"full_validation_upl_CPU1_r1_profile_summary.csv").set_index("target_Tv")
    old_profiles = inputs.table(FIG/"full_validation_upl_CPU1_r1_comparison_profiles.csv")
    upw = inputs.table(FIG/"full_validation_release_k1em4_GPU_history.csv")
    targets = target_rows(h, ah, c, old_targets)
    intervals_df = intervals(h)
    timing = time_measurements(inputs)
    short_targets = inputs.table(T/"figures/upl_tpi_p3_window_review_r1.targets.csv")
    short_targets = short_targets[short_targets.series=="BP3"]
    require(len(short_targets)==2 and np.allclose(short_targets.B_P_layer_RMS_error_Pa,
            targets.iloc[:2].P3_layer_RMS_Pa,rtol=1e-12,atol=1e-9), "Old two common target RMS changed")
    pc = h[h.stress_guard_applies]; late = h[h.Tv>=1]
    require(len(late)>1 and np.isfinite(late.pressure_layer_rms_Pa).all(),"Late reference unavailable")
    actual_hit = np.count_nonzero((pc.max_layer_stress_error_Pa>100)|(pc.top_gap_Pa>100))
    thresholds = targets[["pressure_pass","top_pass","bottom_pass"]].all()
    late_inc = float(late.pressure_increment_at_nearest_A_Pa.max())
    summary = dict(stage=TAG,analysis_complete=True,full_native_method_verified=True,
        physical_acceptance=bool(not actual_hit and thresholds.all() and late_inc<=5),
        samples=len(h),material_ID_count=len(order),layers=100,native_end_s=h.time_s.iloc[-1],legacy_Tv_end=h.Tv.iloc[-1],
        pressure_noninferiority_all_ten=thresholds.pressure_pass,top_noninferiority_all_ten=thresholds.top_pass,
        bottom_absolute_and_noninferiority_all_ten=thresholds.bottom_pass,all_ten_combined=targets.all_targets_here_pass.all(),
        pressure_error_increment_all_late_max_Pa=late_inc,all_late_nearest_A_within_5Pa=late_inc<=5,
        max_abs_late_A_clock_gap_s=float(late.P3_minus_A_time_s.abs().max()),
        declared_target_budgets=targets.to_dict(orient="records"),stress_guard_frames=len(pc),
        stress_failed_frames=int(pc.stress_guard_failed.sum()),top_gap_failed_frames=int(pc.top_gap_guard_failed.sum()),
        post_01_max_layer_error_Pa=float(pc.max_layer_stress_error_Pa.max()),
        post_01_max_topgap_Pa=float(pc.top_gap_Pa.max()),violating_layers=list(map(int,np.flatnonzero((error[h.stress_guard_applies]>100).any(axis=0)))),
        post_01_max_Q_Pa=float(pc.Q_Pa.max()),late_max_Q_Pa=float(late.Q_Pa.max()),
        intervals=intervals_df.to_dict(orient="records"),max_alternating_Uz_mm=float(h.alt_Uz_max_mm.max()),
        late_frames=len(late),late_mean_pressure_monotonic_decreasing=bool(np.all(np.diff(late.mean_pressure_Pa)<0)),
        late_bottom_pressure_monotonic_decreasing=bool(np.all(np.diff(late.bottom_pressure_Pa)<0)),
        max_late_pressure_layer_rms_Pa=float(late.pressure_layer_rms_Pa.max()),
        late_first=late.iloc[0].to_dict(),final=h.iloc[-1].to_dict(),
        retained_A_final=ah.iloc[-1].to_dict(),upw_final=upw.iloc[-1].to_dict(),
        observed_timing=timing,reference_constants=c,solver_invocations=0,reader_invocations=0)
    # A failure reaching the endpoint has an open upper bracket.
    summary["intervals"]=[{k:(None if pd.isna(v) else v) for k,v in r.items()} for r in summary["intervals"]]
    DEST.mkdir()
    profiles=csv_outputs(h,ah,layers,refs,z,targets,old_profiles,upw,c)
    intervals_df.to_csv(DEST/"stress_intervals.csv",index=False)
    plots(h,ah,upw,profiles,targets)
    for path in list(inputs.stats):
        inputs.pin(path)
    summary["inputs"]=[dict(path=str(k),bytes=v[0],mtime_ns=v[1]) for k,v in inputs.stats.items()]
    summary["products"]=[str(p) for p in sorted(DEST.iterdir())]+[str(LAYERS)]
    write_json(CHECK,summary)
    print(json.dumps(dict(samples=N,physical_acceptance=summary["physical_acceptance"],final_P_RMS_Pa=h.pressure_layer_rms_Pa.iloc[-1],
                          stress_failed_frames=summary["stress_failed_frames"],out=str(DEST))))


if __name__ == "__main__":
    main()
