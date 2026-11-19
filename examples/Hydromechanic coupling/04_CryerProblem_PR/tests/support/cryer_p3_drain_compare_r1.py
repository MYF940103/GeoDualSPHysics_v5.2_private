"""Compare already-audited finite-Kw and P3 histories at their actual saved times."""
import argparse
from pathlib import Path
import json
import numpy as np
import pandas as pd

T = Path(__file__).resolve().parents[1]
F = T / "figures"
OLD = F / "upl_cryer_freebody_peak_review_r1_history.csv"
SHORT = F / "cryer_p3_gpu_b64_r1.csv"
FULL = F / "cryer_p3_gpu_drain4097_r1.csv"
TAG = "cryer_p3_drain_AB_r1"
RAMP, DRAIN = 2.**-8, 2.**-7
DT_A, DT_B = 2.**-20, 2.**-19
INITIAL_IDS=T/"outputs/upl_tpi_cryer_cpu_DebugCPU_B_startup128_r1_native_r2/native_ids.csv"

FIELDS_A = dict(center_pressure_Pa="center_Pa",pressure_arithmetic_mean_Pa="mean_Pa",
    shell_inward_initial_V_mm="shell_inward_mm",total_mean_compression_initial_V_Pa="total_compression_Pa",
    surface_pressure_absmax_Pa="surface_p_absmax_Pa",activeDrainCount="active_drain",
    saved_J_load_proxy_inward_N="inward_force_proxy_N",pressure_min_Pa="pmin_Pa",pressure_max_Pa="pmax_Pa")
FIELDS_B = dict(center18_Pa="center_Pa",mean_pressure_Pa="mean_Pa",shell_inward_mm="shell_inward_mm",
    mean_total_compression_Pa="total_compression_Pa",surface_p_absmax_Pa="surface_p_absmax_Pa",
    active_drain_count="active_drain",surface_count="surface_FS23",
    pressure_min_Pa="pmin_Pa",pressure_max_Pa="pmax_Pa")


def traction(t):
    # JSphGpu::ConfigCtes: evaluate the original source clock in every phase.
    return 10000.*np.clip(t/RAMP,0.,1.)


def closed_uniform_state():
    # Closed, drained skeleton bulk Kd (hydrostatic loading); incompressible
    # grains, alpha=1. Starting material shell is identical in both methods.
    kd=2e6/(3*(1.-2.*.3))
    bfluid=2e8/.3
    ids=pd.read_csv(INITIAL_IDS,float_precision="round_trip")
    shell=ids.loc[ids.shell_r0_ge_a_minus_2h.eq(1)]
    if len(shell)!=17646 or len(ids)!=37181:
        raise ValueError("Initial shell does not match the fixed Cryer sphere")
    radius=np.average(shell.r0_m,weights=shell.initial_native_volume_m3)
    return dict(finite_Kw_pressure_Pa=10000.*bfluid/(kd+bfluid),
        finite_Kw_shell_mm=1000.*radius*10000./(3*(kd+bfluid)),M0_limit_pressure_Pa=10000.,M0_limit_shell_mm=0.)


def build_table(short=False):
    source=SHORT if short else FULL
    b=pd.read_csv(source,float_precision="round_trip")
    old=pd.read_csv(OLD,float_precision="round_trip")
    a=old.loc[old.series.eq("current_upl_GPU")].copy()
    if len(a)!=577 or not (a.dt_s==DT_A).all() or not (a.center_count==18).all():
        raise ValueError("Unexpected retained finite-Kw u-pl sphere")
    a["surface_FS23"]=a.FS2_count+a.FS3_count
    a["source_q_Pa"]=traction(np.maximum(a.completed_step-1,0)*DT_A)
    b["source_q_Pa"]=traction(np.maximum(b.completed_step-1,0)*DT_B)
    expected=np.array([0,64] if short else [*range(0,4097,64),4097])
    if not np.array_equal(b.completed_step,expected) or not np.array_equal(b.time_s,expected*DT_B):
        raise ValueError("Incomplete observed B clock")
    if a.time_s.duplicated().any() or not np.array_equal(a.time_s,a.completed_step*DT_A):
        raise ValueError("Retained A clock is ambiguous")
    if not (b.loc[b.time_s<=DRAIN,"active_drain_count"]==0).all():
        raise ValueError("Unexpected early drainage")
    if not short and not (b.active_drain_count.iloc[-1]==b.surface_count.iloc[-1]>0 and b.surface_p_absmax_Pa.iloc[-1]==0):
        raise ValueError("First open B state has incomplete true FS2/3 drainage")
    if not short:
        first_a_open=a.loc[a.time_s>DRAIN].iloc[0]
        if not (first_a_open.activeDrainCount==first_a_open.surface_FS23>0 and first_a_open.surface_pressure_absmax_Pa==0):
            raise ValueError("First observed A open state differs")
        a=a.loc[(a.time_s<=b.time_s.max())|a.time_s.eq(first_a_open.time_s)]
    else:
        a=a.loc[a.time_s<=b.time_s.max()]
    def columns(fr, mapping, group):
        selected=fr[["time_s",*mapping]].rename(columns=mapping).copy()
        return selected.rename(columns={k:group+"_"+k for k in selected if k!="time_s"})
    cols_a={**FIELDS_A,"surface_FS23":"surface_FS23","source_q_Pa":"source_q_Pa","completed_step":"completed_step"}
    cols_b={**FIELDS_B,"source_q_Pa":"source_q_Pa","completed_step":"completed_step"}
    if "saved_J_inward_load_proxy_N" in b:cols_b["saved_J_inward_load_proxy_N"]="inward_force_proxy_N"
    combined=columns(b,cols_b,"B").merge(columns(a,cols_a,"A"),on="time_s",how="outer",sort=True,
        validate="one_to_one",indicator="match")
    combined["match"]=combined["match"].map(dict(both="exact_AB",left_only="B_only",right_only="A_only"))
    combined.insert(1,"tau_s",combined.time_s-DRAIN)
    combined.insert(2,"phase",np.select([combined.time_s.eq(0),combined.time_s.lt(RAMP),combined.time_s.eq(RAMP),
        combined.time_s.lt(DRAIN),combined.time_s.eq(DRAIN)],["initial","ramp","ramp_end","hold","drain_pre_open"],"open"))
    combined.insert(3,"scheduled_q_at_saved_t_Pa",traction(combined.time_s.to_numpy()))
    # On an open frame with verified Dirichlet zero, the interior mean is
    # recoverable directly from the total stored sum; no previous-state
    # surface pressure or fictitious post-opening A sample is substituted.
    for group in ("A","B"):
        active=combined[group+"_active_drain"]
        verified_zero=(active>0)&(combined[group+"_surface_p_absmax_Pa"]==0)
        interior=combined[group+"_mean_Pa"]*37173/(37173-active)
        combined[group+"_post_open_non_Dirichlet_soil_mean_Pa"]=interior.where(verified_zero)
    # Express the uniform closed state only during the hold. The free-body
    # transient and the post-opening response have their own dynamics.
    hold=(combined.time_s>=RAMP)&(combined.time_s<=DRAIN)
    for metric,value in closed_uniform_state().items():
        combined["uniform_closed_"+metric]=np.where(hold,value,np.nan)
    for metric in ("center_Pa","mean_Pa","shell_inward_mm","total_compression_Pa","surface_p_absmax_Pa",
                   "active_drain","surface_FS23","inward_force_proxy_N"):
        if "B_"+metric in combined:
            combined["B_minus_A_"+metric]=combined["B_"+metric]-combined["A_"+metric]
    counts=combined.match.value_counts().to_dict()
    if counts.get("exact_AB",0)!=(2 if short else 65):
        raise ValueError("Exact A/B time intersection differs")
    if not short and (counts.get("B_only",0)!=1 or counts.get("A_only",0)!=1):
        raise ValueError("Unexpected nonmatching states")
    return combined


def plot(data,outfile):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    colors={"A":"#246799","B":"#b64d28"}
    fig,(p,u)=plt.subplots(1,2,figsize=(12.8,5.3),layout="constrained")
    fig.suptitle("Cryer sphere   |   Ramp, closed hold and first saved drainage response",fontsize=15)
    closed=data.time_s<=DRAIN
    shape={"center_Pa":"o","mean_Pa":"^"}
    x=data.time_s*1000
    for axis in (p,u):
        axis.axvline(RAMP*1000,c="#777777",lw=.8,ls="--")
        axis.axvline(DRAIN*1000,c="#777777",lw=.8,ls="--")
        axis.grid(True,color="#dadde0",linewidth=.65)
        axis.set_axisbelow(True)
        axis.set_xlabel("Time since loading began (ms)")
        axis.set_xlim(-.12,8.20)
        axis.set_xticks([0,1,2,3,4,5,6,7,8])
    for g,c in colors.items():
        for metric,marker in shape.items():
            values=data[g+"_"+metric]/1000
            p.plot(x[closed],values[closed],color=c,ls="-" if metric=="center_Pa" else "--",lw=1.6,
                marker=marker,ms=3.8,markevery=5,mfc=c if metric=="center_Pa" else "white")
            ix=~closed & values.notna()
            p.scatter(x[ix],values[ix],s=35,marker=marker,edgecolors=c,facecolors=c if metric=="center_Pa" else "white",zorder=5)
        inward=data[g+"_shell_inward_mm"]*1000
        u.plot(x[closed],inward[closed],color=c,lw=1.8,marker="o",ms=3.7,markevery=5)
        ix=~closed & inward.notna()
        u.scatter(x[ix],inward[ix],s=47,marker="D",color=c,zorder=5)
    p.plot(x[closed],data.scheduled_q_at_saved_t_Pa[closed]/1000,":",color="#383838",lw=1.2)
    p.set_title("Pore pressure and prescribed load")
    p.set_ylabel("Pressure (kPa)")
    p.legend(handles=[Line2D([],[],c=colors["A"],lw=2,label="A  finite $K_w$"),Line2D([],[],c=colors["B"],lw=2,label="B  P3"),
        Line2D([],[],c="#444444",marker="o",label="Fixed center 18"),Line2D([],[],c="#444444",ls="--",marker="^",mfc="white",label="All soil mean"),
        Line2D([],[],c="#444444",ls=":",label="Scheduled traction")],loc="lower right",ncol=2,fontsize=8.1)
    u.set_title("Material shell displacement")
    u.set_ylabel("Mean inward displacement (µm)")
    u.legend(handles=[Line2D([],[],c=c,lw=2,label=l) for c,l in ((colors["A"],"A  finite $K_w$"),(colors["B"],"B  P3"))]+
        [Line2D([],[],c="#444444",ls="none",marker="D",label="First saved open state")],loc="best",fontsize=8)
    for t,label in ((RAMP,"Ramp ends"),(DRAIN,"Drain opens")):
        if t>data.time_s.max():continue
        p.annotate(label,xy=(t*1000,.98),xycoords=("data","axes fraction"),xytext=(-3,0),
                   textcoords="offset points",ha="right",va="top",fontsize=8,color="#424242",
                   bbox=dict(facecolor="white",alpha=.85,edgecolor="none",pad=1))
    if (data.time_s>DRAIN).any():
        fs_a=int(data.loc[data.match.eq("A_only"),"A_active_drain"].iloc[0])
        fs_b=int(data.loc[data.match.eq("B_only"),"B_active_drain"].iloc[0])
        fig.supxlabel(f"First open saves after drainage     A  122.0703 µs ({fs_a:,} drained)     |     B  1.9073 µs ({fs_b:,} drained)",fontsize=9)
    else:
        fig.suptitle("Cryer startup rendering check   |   Two observed closed states")
        for axis in (p,u):
            axis.set_xticks([0,.04,.08,.12]);axis.set_xlim(-.006,.13)
    fig.savefig(outfile,dpi=180,format="png")
    plt.close(fig)


def summarize(data):
    centers=("center_Pa","mean_Pa","shell_inward_mm","total_compression_Pa")
    out={}
    for name,selected in (("ramp",(data.time_s>0)&(data.time_s<=RAMP)),
            ("closed_hold",(data.time_s>=RAMP)&(data.time_s<=DRAIN))):
        states=data.loc[selected & data.match.eq("exact_AB")]
        section={}
        for col in centers:
            delta=states["B_minus_A_"+col]
            idx=delta.abs().idxmax()
            section[col]=dict(rms_B_minus_A=float(np.sqrt(np.mean(delta**2))),
                maximum_absolute_B_minus_A=float(abs(delta.loc[idx])),time_of_max_s=float(states.time_s.loc[idx]))
        out[name]=dict(actual_time_pairs=len(states),comparison=section)
    return out


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-short",action="store_true")
    args=parser.parse_args()
    data=build_table(args.check_short)
    if args.check_short:
        from io import BytesIO
        check=BytesIO()
        plot(data,check)
        if not check.getvalue().startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Actual short input failed the in-memory chart render")
        print(data[["time_s","match","A_center_Pa","B_center_Pa","B_minus_A_center_Pa"]].to_string(index=False))
    else:
        dest_csv=F/(TAG+".csv"); dest_png=F/(TAG+".png")
        receipt=T/"logs"/(TAG+".check.json")
        if dest_csv.exists() or dest_png.exists() or receipt.exists():raise FileExistsError("Existing comparison output")
        plot(data,dest_png)
        data.to_csv(dest_csv,index=False,float_format="%.17g",mode="x")
        result={"rows":len(data),"counts":data.match.value_counts().to_dict(),"window_differences":summarize(data),
            "uniform_closed_targets":closed_uniform_state(),"B_source":str(FULL),"A_source":str(OLD),
            "A_series":"current_upl_GPU","native_reads_or_solver_runs":0,"numerical_interpolation":False,
            "post_open_steps_have_distinct_clocks":True,"table":str(dest_csv),"plot":str(dest_png)}
        with receipt.open("x",encoding="utf8") as fh:
            json.dump(result,fh,indent=2,allow_nan=False);fh.write("\n")
        print(json.dumps(result))
