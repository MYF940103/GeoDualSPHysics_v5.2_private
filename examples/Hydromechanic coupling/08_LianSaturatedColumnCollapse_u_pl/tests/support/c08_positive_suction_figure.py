"""Show retained toe pressure fields, point histories and the saved-state terms at the peak."""
import csv
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
import numpy as np

from c08_positive_suction_sites import OUT, RUNS, checked, select_materials
from c08_psi25_suction_row import pressure_row
from c08_psi25_tpi_native import SOIL_IDS, TESTS, require


def main():
    gpu_text=(TESTS/"outputs/c08_m0_gpu_coupled_r1_build/JSphGpu.cpp").read_text(encoding="utf8",errors="replace")
    require("gamma=rhow*9.80665" in gpu_text,"Unexpected private TPI row scaling")
    with (OUT/"material_sites.csv").open(encoding="utf8") as f:
        records=list(csv.DictReader(f))
    worst=min((r for r in records if r["policy"]=="beta004"),key=lambda r:float(r["p_kPa"]))
    part=int(worst["part"])
    peak_id=int(worst["id"])
    base_tag=RUNS["beta004"]
    base_rec=json.loads((TESTS/"logs"/(base_tag+".native_review.json")).read_text())
    _,peak,_=checked(TESTS/"outputs"/base_tag/"data"/f"Part_{part:04d}.bi4",base_rec)
    _,matched,adjacent=select_materials(peak,peak_id)
    selected=[peak_id]+matched
    require(len(selected)==3,"Expected the peak point and two matched controls")
    fig,axes=plt.subplots(2,2,figsize=(11,7.2),layout="constrained")
    styles=dict(zip(selected,("black","#c45e07","#5e37ad")))
    markers=dict(zip(selected,("o","s","^")))
    terms=[]
    norm=Normalize(-30,10)
    for col,(label,tag) in enumerate(RUNS.items()):
        rec=json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text())
        _,a,_=checked(TESTS/"outputs"/tag/"data"/f"Part_{part:04d}.bi4",rec)
        xz=a["Posd"][-5000:][:,[0,2]]
        roi=(xz[:,0]>=3.3)&(xz[:,0]<=4.65)&(xz[:,1]<=.8)
        p=a["PorePress"][-5000:]/1000
        ax=axes[0,col]
        sc=ax.scatter(*xz[roi].T,c=p[roi],s=10,cmap="RdBu_r",norm=norm,linewidths=0)
        for rid in selected:
            si=int(np.searchsorted(SOIL_IDS,rid))
            x,z=xz[si]
            ax.scatter(x,z,s=57,facecolors="none",edgecolors=styles[rid],marker=markers[rid],linewidths=1.5)
            i=len(a["Idp"])-len(SOIL_IDS)+si
            values=pressure_row(a,i)
            # Gravity for the bed's normal head and the TPI pressure-row gamma are configured separately.
            values["theta_source"]=-1000*9.80665*a["PoroThetaLastStage"][i]
            terms.append(dict(policy=label,part=part,step=int(worst["step"]),tau_s=float(worst["tau_s"]),
                              id=rid,peak_or_matched="deepest" if rid==peak_id else "matched_low_kappa",
                              among_two_nearest=int(rid in adjacent),**values))
        ax.set(xlim=(3.3,4.65),ylim=(-.025,.8),aspect="equal",xlabel="x (m)",ylabel="z (m)",
               title=f"Positive-only, β = {0.04 if label=='beta004' else 0:g},  t = {float(worst['tau_s']):.2f} s")
        ax.axhline(0,color=".35",lw=.9)
    fig.colorbar(sc,ax=axes[0,:],label="Gauge pore pressure (kPa)",shrink=.80,extend="both")
    for ax,label in zip(axes[1,:],("p_kPa","J")):
        for rid in selected:
            for policy,style in (("beta004","-"),("beta0","--")):
                items=[r for r in records if int(r["id"])==rid and r["policy"]==policy]
                require(len(items)==128,"Missing fixed material samples")
                ax.plot([float(r["tau_s"]) for r in items],[float(r[label]) for r in items],
                        color=styles[rid],ls=style,lw=1.3)
        ax.axvline(float(worst["tau_s"]),color=".5",lw=.7,ls=":")
        ax.grid(alpha=.22)
        ax.set(xlim=(0,1.2),xlabel="Time after wall release (s)",
               ylabel="Gauge pore pressure (kPa)" if label=="p_kPa" else "Material volume ratio J")
    axes[1,0].legend(handles=[Line2D([],[],color=styles[r],marker=markers[r],mfc="none",label=str(r))
                              for r in selected],ncol=3,fontsize=8,loc="lower right")
    axes[1,1].legend(handles=[Line2D([],[],color=".3",ls=style,label=name) for style,name in
                             (("-","β = 0.04"),("--","β = 0"))],fontsize=8)
    out_png=OUT/"toe_fields_histories.png"
    require(not out_png.exists(),"Existing figure")
    with (OUT/"peak_pressure_terms.csv").open("x",encoding="utf8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=terms[0])
        writer.writeheader()
        writer.writerows(terms)
    fig.savefig(out_png,dpi=170)
    plt.close(fig)


if __name__=="__main__":
    main()
