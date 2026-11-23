"""Assess a completed conservative 3D Cryer peak diagnostic at the server's actual steps."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from cryer_weak_comparison import compare
from cryer_coupled_shell_modes import T, DT
from cryer_shell_equilibrium import reference_fields, Reference, R
from cryer_p3_verify_r1 import need


TAG="cryer_weak_3d_peak_r1"


def main():
    pre=T/"outputs/cryer_weak_open_r1"
    ext=T/"outputs/cryer_weak_peak_r1"
    for folder,count in ((pre,4160),(ext,36864)):
        seal=json.loads((folder/"completed.json").read_text())
        need(seal["steps"]==count and seal["material_ids"]==37173,"Wrong run or partial data")
    need(json.loads((pre/"completed.json").read_text())["closed_pass"],"Failed source qualification")
    def joined(name,key):
        a,b=[pd.read_csv(root/name,float_precision="round_trip") for root in [pre,ext]]
        overlap=a[a.step==4160].reset_index(drop=True)
        right=b[b.step==4160].reset_index(drop=True)
        need(np.array_equal(overlap.to_numpy(),right.to_numpy()),"Restart seam "+name)
        out=pd.concat((a,b[b.step>4160]),ignore_index=True)
        need(not out.duplicated(key).any(),"Unexpected duplicate state")
        return out
    hist=joined("history.csv","step")
    shell=joined("shells.csv",["step","material_shell"])
    need(np.array_equal(hist.time_s.to_numpy(),hist.step.to_numpy()*DT),"Actual binary clock")
    need(np.all(hist.loc[hist.step>4096,"surface_absmax_Pa"]==0),"Drainage")
    need(np.array_equal(shell.groupby("step")["count"].sum().to_numpy(),np.full(len(hist),37173)),"All materials")
    common=hist[hist.step%64==0]
    need(np.array_equal(common.step,np.arange(577)*64),"Expected 577 shared clocks")
    dest=T/"figures"/(TAG+"_history.csv")
    if dest.exists():raise FileExistsError(dest)
    hist.to_csv(dest,index=False)
    compare(dest,TAG,None)
    r=Reference(.3,finite=False)
    ppeak=hist[hist.tau_s>=.005*.05**2/r.legacy_cv].center_Pa.idxmax()
    peak=hist.loc[ppeak]
    ref_tau=.04192258568544373;ref_p=12478.53263299281
    ideal_t=float(peak.tau_s)
    e1=100*(peak.center_Pa/ref_p-1);e2=100*(ideal_t/ref_tau-1)
    points=[4097,4160,8192,int(peak.step),36864]
    save=[]
    for step in points:
        t=shell[shell.step==step].copy()
        radii=t.material_shell.to_numpy()*.0025
        theory=reference_fields(r,(step-4096)*DT,radii)[0]
        t["p_theory_Pa"]=theory
        t["mean_minus_theory_Pa"]=t.p_mean_Pa-theory
        save.append(t)
    pd.concat(save).to_csv(T/"figures"/(TAG+"_profile.csv"),index=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,3,figsize=(12.4,3.8),layout="constrained")
    for ax,t,title in zip(axes,(save[1],save[3],save[4]),("First shared open frame","Sampled center peak","End of peak window")):
        rad=t.material_shell.to_numpy()/20
        p=t.p_mean_Pa.to_numpy()/1000;sd=t.p_std_Pa.to_numpy()/1000
        ax.plot(rad,t.p_theory_Pa/1000,"k--",label="Analytical at saved time")
        ax.plot(rad,p,"o",ms=3,color="#196a91",label="Material shell mean")
        ax.fill_between(rad,p-sd,p+sd,color="#7ab7cd",alpha=.3,label="Angular spread ±1 SD")
        ax.set(xlabel="Material radius r/a",ylabel="Pore pressure (kPa)",title=title)
        ax.legend(fontsize=7);ax.grid(alpha=.2)
    fig.savefig(T/"figures"/(TAG+"_profiles.png"),dpi=160);plt.close(fig)
    check=dict(actual_steps=36864,actual_end_s=36864*DT,shared_with_original=577,n_nodes=37173,
               active_drained=5153,strict_amplitude_pct=1.,strict_timing_pct=2.,
               peak_frame_step=int(peak.step),center_peak_Pa=peak.center_Pa,peak_tau_s=ideal_t,
               matched_ref_Pa=float(r.pressure(ideal_t)[0]),continuous_theory_peak_Pa=ref_p,
               continuous_theory_peak_tau_s=ref_tau,amplitude_error_pct=e1,timing_error_pct=e2,
               peak_bounds_pass=bool(abs(e1)<=1 and abs(e2)<=2),
               scope="Fixed reference particle geometry, constant conductivity and initial native masses. Three weak residual rounds with velocity correction, full 3D AV. This is a research implementation, no production integration.")
    dest=T/"logs"/(TAG+"_gates.json")
    with dest.open("x") as f:json.dump(check,f,indent=2,allow_nan=False)
    print(json.dumps(check,indent=2))


if __name__=="__main__":main()
