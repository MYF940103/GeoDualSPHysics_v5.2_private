"""Common-clock assessment of center pressure and surface motion with analytical spherical means."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from cryer_shell_equilibrium import TESTS as T, Reference, R, Q, reference_fields
from cryer_coupled_shell_modes import DT


def compare(source,tag,method):
    old=pd.read_csv(T/"figures/cryer_p3_server_peak_actual_r1/physical/native_and_theory.csv")
    actual_surface=pd.read_csv(T/"figures/cryer_true_surface_old_r1.csv")
    old=old.merge(actual_surface[["completed_step","surface_mm"]],on="completed_step",validate="one_to_one")
    x=pd.read_csv(source)
    if method:
        x=x[x.method==method].copy()
    use=x[x.step>=4096].merge(old,on=None,left_on="step",right_on="completed_step",validate="one_to_one",suffixes=("_new","_old"))
    if len(use)==0:
        raise ValueError("Need at least one closed/open comparison state")
    tau=use.step.to_numpy()*DT-.0078125
    assert np.array_equal(tau,use.tau_s_old.to_numpy()) and np.allclose(tau,use.tau_s_new,atol=1e-15,rtol=0)
    ref=Reference(.3,finite=False)
    volume_mean=np.array([reference_fields(ref,t,[.0025] if t==0 else np.array([.0025]))[1] for t in tau])
    theory=R*1000*(Q-volume_mean)/(3*ref.K)
    if "surface_inward_mm_new" in use:
        inward=use.surface_inward_mm_new.to_numpy()
    else:
        inward=use.surface_inward_mm.to_numpy()
    table=pd.DataFrame(dict(step=use.step,tau_s=tau,Tv=use.legacy_Tv,p_center_candidate_Pa=use.center_Pa,
                  p_center_old_Pa=use.center18_Pa,p_center_theory_Pa=use.M0_r18_Pa,
                  surface_candidate_mm=inward,surface_old_mm=use.surface_mm,surface_theory_mm=theory))
    name=T/"figures"/tag
    for y in (name.with_suffix(".csv"),name.with_suffix(".png"),T/"logs"/(tag+".check.json")):
        if y.exists():raise FileExistsError(y)
    table.to_csv(name.with_suffix(".csv"),index=False)
    late=table[table.Tv>=.005]
    def metrics(t,p,s):
        if t.empty:return {}
        err=t[p]-t.p_center_theory_Pa
        su=t[s]-t.surface_theory_mm
        i=np.argmax(t[p].to_numpy())
        return dict(center_rms_Pa=np.sqrt(np.mean(err**2)),surface_rms_mm=np.sqrt(np.mean(su**2)),
            surface_max_abs_mm=max(abs(su)),surface_bias_final_mm=su.iloc[-1],peak_sample_Pa=t[p].iloc[i],
            sample_tau_s=t.tau_s.iloc[i],surface_at_sample_peak_mm=t[s].iloc[i],surface_ref_at_sample_peak_mm=t.surface_theory_mm.iloc[i])
    report={s:metrics(late,p,d) for s,p,d in [("candidate","p_center_candidate_Pa","surface_candidate_mm"),
                    ("observed_original","p_center_old_Pa","surface_old_mm")]}
    report["scope"]="M0 r/a=.05 central reference and analytical surface u=R*(mean(p)-q)/(3*K). Closed state at tau=0, positive displacement inward."
    report["matched_count"]=len(table);report["mandel_count"]=len(late)
    (T/"logs"/(tag+".check.json")).write_text(json.dumps(report,allow_nan=False,indent=2)+"\n")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(1,3,figsize=(13,3.6),layout="constrained")
    for ax,opt in zip(axs,("start","peak","surface")):
        field=("surface","mm") if opt=="surface" else ("p_center","Pa")
        scale=1 if opt=="surface" else .001
        for key,color,style,label in [("theory","#202020","--","M0 theory"),("old","#b85e26","-","Original 3D P3"),("candidate","#196a91","-","Weak flux (20 shells)" if method else "Weak flux (3D)")]:
            ax.plot(tau*1000,table["_".join([field[0],key,field[1]])]*scale,color=color,linestyle=style,lw=1.6,label=label)
        ax.set(xlabel="Time since drainage opens (ms)",ylabel="Surface inward motion (mm)" if opt=="surface" else "Pressure at r/a=0.05 (kPa)")
        if opt=="start":ax.set_xlim(0,min(2.,max(tau)*1000))
        ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.savefig(name.with_suffix(".png"),dpi=160);plt.close(fig)
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    a=argparse.ArgumentParser(description=__doc__);a.add_argument("source",type=Path);a.add_argument("tag")
    a.add_argument("--method",default=None)
    v=a.parse_args();compare(v.source,v.tag,v.method)
