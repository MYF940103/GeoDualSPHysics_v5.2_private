"""Offline Cryer P3 accuracy using fixed material points and actual native clocks."""
import argparse
import csv
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

from cryer_p3_verify_r1 import audit, need, TESTS, T_D
from cryer_p3_radial_r1 import RadialPressure
sys.path.insert(0,str(TESTS.parent/"support"))
from plot_cryer_formal_four_nu_r1 import Reference


def compare(rows, control, stage, ref=None):
    frame=pd.DataFrame(rows)
    tau=frame.tau_s.to_numpy()
    if ref is None:
        ref=Reference(.3,finite=False)
    ref.cv=ref.H*ref.kappa
    ref.decay=ref.xi**2*ref.cv/.05**2
    tv=tau*ref.legacy_cv/.05**2
    truth=ref.pressure(tau,radius=.0025)
    frame["legacy_Tv"]=tv
    frame["M0_r18_Pa"]=truth
    frame["native_minus_M0_Pa"]=frame.center18_Pa-truth
    mask=(tv>=.005)&(tau<=.0625)
    need(np.count_nonzero(mask)>=12,"not enough actual Mandel samples")
    peak=minimize_scalar(lambda t:-ref.pressure(t,radius=.0025)[0],
                         bounds=(.005*.05**2/ref.legacy_cv, .0625),method="bounded",options={"xatol":1e-14})
    need(peak.success and .04<peak.x<.05, "analytical peak search failed")
    model=frame.loc[mask].iloc[frame.loc[mask,"center18_Pa"].argmax()]
    theory_sample=frame.loc[mask].iloc[np.argmax(truth[mask])]
    amplitude=100*(model.center18_Pa/(-peak.fun)-1)
    phase=model.tau_s-peak.x
    gaps=np.diff(tau[mask])
    max_gap=float(gaps.max())
    rms=np.sqrt(np.mean(frame.loc[mask,"native_minus_M0_Pa"]**2))
    baseline=control[control.series=="current_upl_GPU"].iloc[0]
    phase_limit=max(.02*peak.x,.5*max_gap)
    criteria=dict(sampling=max_gap<=.01*peak.x,
                  peak_within_one_percent=abs(amplitude)<=1.,
                  no_worse_than_A_plus_0p10pp=abs(amplitude)<=abs(baseline.native_peak_amplitude_error_percent_of_reference_peak)+.10,
                  peak_time=abs(phase)<=phase_limit)
    return frame,dict(stage=stage,center_material_ids=18,reference="M0, nominal radius .05 m, material r0=.0025 m",
        peak_window_start_Tv=.005,peak_window_end_tau_s=.0625,window_rows=int(mask.sum()),
        theoretical_peak_Pa=-peak.fun,theoretical_tau_s=peak.x,
        native_peak_Pa=model.center18_Pa,native_peak_tau_s=model.tau_s,
        sampled_theory_peak_Pa=theory_sample.M0_r18_Pa,sampled_theory_tau_s=theory_sample.tau_s,
        amplitude_error_pct=amplitude,phase_error_s=phase,phase_error_pct=100*phase/peak.x,
        sampling_max_s=max_gap,phase_limit_s=phase_limit,window_RMS_Pa=rms,
        original_A_amplitude_error_pct=baseline.native_peak_amplitude_error_percent_of_reference_peak,
        criteria={k:bool(v) for k,v in criteria.items()},peak_physical_criteria_met=stage=="peak" and all(criteria.values()))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output",type=Path,help="Returned original solver output")
    ap.add_argument("schedule",type=Path,help="Packaged peak/full schedule CSV")
    ap.add_argument("destination",type=Path,help="Fresh figure/data directory")
    args=ap.parse_args()
    with args.schedule.open(newline="") as f: schedule=list(csv.DictReader(f))
    count=len(schedule)
    need(count in (577,265),"unsupported output profile")
    stage="peak" if count==577 else "full"
    steps=[int(r["completed_steps"]) for r in schedule]
    dt=2**-19
    need(steps[64]==4096 and steps[-1]==(36864 if stage=="peak" else 481685),"invalid schedule")
    need(all(int(r["part"])==n and float(r["time_s"])==steps[n]*dt for n,r in enumerate(schedule)),"clock plan")
    output=args.output.resolve()
    need(not args.destination.exists(),"preserve previous analysis")
    metrics=pd.read_csv(TESTS/"figures/upl_cryer_freebody_peak_review_r1_metrics.csv")
    ref=Reference(.3,finite=False)
    radial=RadialPressure(ref.legacy_cv/.05**2)
    history=audit(output/"data",steps,dt,p3_sidecars=True,radial=radial)
    frame,result=compare(history,metrics,stage,ref)
    out=args.destination
    out.mkdir(parents=True,exist_ok=False)
    frame.to_csv(out/"native_and_theory.csv",index=False)
    result["radial_pressure"]=radial.write(out/"radial_pressure.csv",out/"radial_pressure.png")
    old=pd.read_csv(TESTS/"figures/upl_cryer_freebody_peak_review_r1_history.csv")
    old=old[old.series=="current_upl_GPU"]
    fig,(ax,closed)=plt.subplots(1,2,figsize=(11,4.4),gridspec_kw={"width_ratios":[1.6,1]},layout="constrained")
    after=frame.legacy_Tv>0
    ax.plot(frame.legacy_Tv[after],frame.M0_r18_Pa[after]/1e3,color="#1e405e",label="M0 analytical")
    ax.scatter(frame.legacy_Tv[after],frame.center18_Pa[after]/1e3,s=8,facecolors="none",edgecolors="#c64c1c",label="P3, fixed 18 particles")
    afterA=old.legacy_Tv>0
    ax.plot(old.legacy_Tv[afterA],old.finite_Kw_fixed_radius_reference_Pa[afterA]/1e3,color="0.4",linestyle="--",label="Finite-Kw analytical")
    ax.scatter(old.legacy_Tv[afterA],old.native_fixed18_pressure_Pa[afterA]/1e3,s=5,marker="+",color="#3c846f",label="Retained finite-Kw A")
    ax.set(xscale="log",xlabel="Time factor after drainage, Tv",ylabel="Pore pressure (kPa)")
    ax.set_xlim(right=5 if stage=="full" else .09)
    closed.plot(frame.time_s*1000,frame.center18_Pa/1e3,color="#ba461c",label="P3")
    closed.axvline(T_D*1000,linestyle=":",color="black",label="Drain opens after this step")
    closed.set(xlim=(0,12),xlabel="Time since loading began (ms)",ylabel="Pore pressure (kPa)")
    for a in (ax,closed):
        a.grid(alpha=.25)
        a.legend(fontsize=8)
    fig.savefig(out/"cryer_center18.png",dpi=200)
    plt.close(fig)
    (out/"physical_review.json").write_text(json.dumps(result,indent=2,allow_nan=False),encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
