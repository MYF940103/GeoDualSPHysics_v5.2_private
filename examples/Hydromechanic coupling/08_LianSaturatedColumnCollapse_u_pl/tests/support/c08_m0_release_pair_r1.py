"""Compare paired C08 pressure equations at matching saved times with actual material IDs."""
import argparse
import csv
import json

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from c08_m0_release_short_review_r1 import read
from c08_m0_release_mature_review_r1 import soils
from c08_m0_release_mature_gpu_r1 import gpu, TAG
from c08_m0_beta_compare import equal, require

TESTS=gpu.T


def pair(window):
    labels=[TAG+"_"+window+"_"+s for s in ("b0","b004")]
    checks=[json.loads((TESTS/"logs"/(s+".review.json")).read_text()) for s in labels]
    tables=[]
    for s in labels:
        with (TESTS/"figures"/(s+".csv")).open(newline="") as file:
            tables.append(list(csv.DictReader(file)))
    require(checks[0]["saved_frames"]==checks[1]["saved_frames"]==len(tables[0])==len(tables[1]),"Window length")
    result=[]
    first_negative=first_difference=None
    for i,(a,b) in enumerate(zip(*tables),1):
        fields=[];parts=[]
        for s in labels:
            _,part=read(TESTS/"outputs"/s/"data",i)
            fields.append(soils(part["arrays"]))
            parts.append(part)
        x,y=fields
        require(a["step"]==b["step"] and a["t_s"]==b["t_s"] and equal(x["Idp"],y["Idp"]), "Paired material and native time")
        step=int(a["step"])
        neg_source=int(b["previous_negative_sources"])
        if neg_source and first_negative is None:first_negative=step
        dp=y["PorePress"].astype(float)-x["PorePress"]
        dx=np.linalg.norm(y["Posd"]-x["Posd"],axis=1)*1000
        six=[y[k].astype(float)-x[k] for k in ("SigmaState_kk","SigmaState_ij")]
        differs=[k for k in x if not equal(x[k],y[k])]
        if differs and first_difference is None:first_difference=step
        result.append(dict(step=step,t_s=float(a["t_s"]),tau_s=float(a["elapsed_from_release_s"]),
            beta0_pmin_Pa=float(a["minimum_total_Pa"]),beta04_pmin_Pa=float(b["minimum_total_Pa"]),
            beta0_negative=int(a["negative_total"]),beta04_negative=int(b["negative_total"]),
            beta0_speed_m_s=float(a["maximum_speed_m_s"]),beta04_speed_m_s=float(b["maximum_speed_m_s"]),
            beta0_spacing_dp=float(a["minimum_spacing_dp"]),beta04_spacing_dp=float(b["minimum_spacing_dp"]),
            beta0_front_x_m=float(a["front_x_m"]),beta04_front_x_m=float(b["front_x_m"]),
            beta0_max_kappa=float(a["max_kappa"]),beta04_max_kappa=float(b["max_kappa"]),
            negative_source=neg_source,pressure_RMS_Pa=float(np.sqrt(np.mean(dp**2))),
            pressure_max_abs_Pa=float(np.abs(dp).max()),material_max_displacement_mm=float(dx.max()),
            six_stress_max_abs_Pa=max(float(np.abs(d).max()) for d in six),different_fields=" ".join(differs)))
    stem=TAG+"_"+window+"_pair"
    table=TESTS/"figures"/(stem+".csv")
    png=table.with_suffix(".png")
    summary=TESTS/"logs"/(stem+".review.json")
    require(not any(p.exists() for p in (table,png,summary)),"Existing pair result")
    with table.open("x",newline="") as f:
        w=csv.DictWriter(f,fieldnames=result[0]);w.writeheader();w.writerows(result)
    plot_pair(result,png)
    output=dict(window=window,paired_frames=len(result),first_negative_source_saved_step=first_negative,first_difference_saved_step=first_difference,
        final=result[-1],full_window_max={k:max(r[k] for r in result) for k in ("pressure_RMS_Pa","pressure_max_abs_Pa","material_max_displacement_mm","six_stress_max_abs_Pa")},
        scope="Diagnostic paired integration; no formal material case or paper acceptance.")
    summary.write_text(json.dumps(output,indent=2))
    print(summary)


def plot_pair(result,png):
    visible=[r for r in result if float(r["tau_s"])>=0.]
    fig,axes=plt.subplots(2,2,figsize=(10.2,6.7),constrained_layout=True)
    t=np.array([float(r["tau_s"])*1000 for r in visible])
    for ax,(key,scale,ylabel) in zip(axes.flat,[("pmin_Pa",.001,"Minimum total pore pressure (kPa)"),
            ("negative",1,"Soil particles with negative pressure"),("speed_m_s",1,"Maximum speed (m/s)"),("spacing_dp",1,"Minimum nearest-neighbor distance / dp")]):
        for prefix,style,color,legend in (("beta0","-","#175e93","β = 0"),("beta04","--","#c15315","β = 0.04")):
            ax.plot(t,[float(r[prefix+"_"+key])*scale for r in visible],style,color=color,label=legend,linewidth=1.7)
        if key=="spacing_dp" and all(abs(float(r[p+"_spacing_dp"])-1.)<.002 for r in visible for p in ("beta0","beta04")):
            ax.set_ylim(.998,1.0005)
        ax.set(xlabel="Time since wall removal (ms)",ylabel=ylabel)
        ax.grid(alpha=.23)
    axes[0,0].legend()
    fig.suptitle("C08 ψ = 0° · same 10 s PRE and 1 ms M0 hold · AS and NoPen off")
    fig.savefig(png,dpi=155)
    plt.close(fig)


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("window",choices=("short","w03"))
    pair(ap.parse_args().window)
