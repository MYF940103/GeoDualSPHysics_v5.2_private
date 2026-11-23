"""Review the three actual Cryer opening states without merging different sampling clocks."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from cryer_weak_geovol import T, DT, summarize


TAG = "cryer_voronoi_window_open_r1"


def main():
    folder = T / "outputs" / TAG
    seal = json.loads((folder / "completed.json").read_text())
    if not (seal["closed_pass"] and seal["steps"] == 4160 and seal["material_ids"] == 37173):
        raise ValueError("The closed/opening window is incomplete")
    figures = T / "figures"
    paths = [figures/(TAG+s) for s in (".csv","_shells.csv",".png")]
    check = T/"logs"/(TAG+".check.json")
    if any(path.exists() for path in [*paths,check]):
        raise FileExistsError("Preserve previous opening review")
    previous = pd.read_csv(figures/"cryer_weak_geovol_open_r1.csv",float_precision="round_trip")
    reference = pd.read_csv(figures/"cryer_weak_angular_opening_r1_shells.csv",float_precision="round_trip")
    m0 = reference[reference.model=="original_P3"].set_index(["step","shell"]).sort_index()
    if not m0.index.is_unique or len(m0)!=60:
        raise ValueError("Analytical reference requires 20 shell values per retained step")
    with np.load(T/"outputs/cryer_tet_reference_r1.npz") as z:
        ids, x, shell = z["native_ids"], z["x0"], z["material_shell"]
    baseline = {"P3":None,"weak P1":"cryer_weak_open_r1",
                "geometric mass + AV":"cryer_weak_geovol_open_r1","face flux":TAG}
    summary, profile = [], []
    for step in (4096,4097,4160):
        ref = m0.loc[step]
        for label,source in baseline.items():
            if source is None:
                row = previous[(previous.step==step) & previous.source.str.endswith("P3")].iloc[0].to_dict()
                records = [(s,int(r.n),r.mean_Pa,r.angular_std_Pa) for s,r in ref.iterrows()]
            else:
                with np.load(T/"outputs"/source/f"state_{step}.npz") as z:
                    if not (int(z["step"])==step and np.array_equal(z["ids"],ids)):
                        raise ValueError("Material or step mismatch")
                    p = z["p"]
                    row = summarize(p,z["J"],x+z["u"],ids,x,shell,step,label)
                    records = [(s,int((shell==s).sum()),p[shell==s].mean(),p[shell==s].std())
                               for s in range(1,21)]
            row["source"] = label
            row.pop("legacy_Tv",None)
            if row["time_s"] != step*DT or sum(rec[1] for rec in records)!=len(ids):
                raise ArithmeticError("Incomplete material coverage or unmatched physical time")
            squared = 0.
            for s,n,mean,sd in records:
                theo = ref.loc[s,"M0_Pa"]
                squared += n*(mean-theo)**2
                profile.append(dict(step=step,source=label,shell=s,count=n,r_over_a=ref.loc[s,"r0_over_a"],
                                    mean_Pa=mean,angular_sd_Pa=sd,reference_Pa=theo))
            row["radial_mean_theory_rms_Pa"] = np.sqrt(squared / len(ids))
            row["center_reference_Pa"] = ref.loc[1,"M0_Pa"]
            summary.append(row)
    hist, prof = pd.DataFrame(summary),pd.DataFrame(profile)
    hist.to_csv(paths[0],index=False,mode="x");prof.to_csv(paths[1],index=False,mode="x")
    styles = [("#585d67","o"),("#c07c30","v"),("#7773aa","s"),("#007789","D")]
    fig, axes = plt.subplots(1,3,figsize=(13,4.3),layout="constrained")
    selected = prof[prof.step==4160]
    for (label,_),(color,mk) in zip(baseline.items(),styles):
        group=selected[selected.source==label]
        # Show independent material-shell means and angular scatter, with the original identities.
        axes[0].plot(group.r_over_a,group.mean_Pa/1000,color=color,marker=mk,ms=3,label=label)
        axes[1].plot(group.r_over_a,group.angular_sd_Pa,color=color,marker=mk,ms=3)
        h=hist[hist.source==label]
        axes[2].scatter(np.arange(3),h.surface_inward_mm*1000,color=color,marker=mk,s=35)
    theory=selected[selected.source=="P3"]
    axes[0].plot(theory.r_over_a,theory.reference_Pa/1000,"k--",label="Quasi-static M0")
    axes[0].set(xlabel="Initial radius / sphere radius",ylabel="Shell mean pressure (kPa)",title="64 steps after opening")
    axes[1].set(xlabel="Initial radius / sphere radius",ylabel="Within-shell pressure SD (Pa)",title="Angular pressure variation")
    axes[2].set(xlabel="Actual steps after opening",ylabel="Surface inward motion (µm)",
                title="5,153 surface material points",xticks=range(3),xticklabels=["0","1","64"])
    for ax in axes: ax.grid(alpha=.2)
    fig.legend(*axes[0].get_legend_handles_labels(),loc="outside lower center",ncol=5)
    fig.savefig(paths[2],dpi=170);plt.close(fig)
    report=dict(step=4160,dt_s=DT,scope="3 actual states for the opening. P3 step 4097 is the retained local run.",
                final=hist[hist.step==4160].to_dict(orient="records"),closed_pass=True)
    with check.open("x") as f:
        json.dump(report,f,indent=2,allow_nan=False);f.write("\n")


if __name__=="__main__":
    main()
