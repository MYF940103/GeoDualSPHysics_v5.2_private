"""Fresh-layout offline export only; preserve the sealed compare_r1 analysis and every raw file."""
import csv, hashlib, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
T=Path(__file__).resolve().parents[1]
def entry(p):
    p=Path(p).resolve();h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1048576),b""):h.update(b)
    return dict(path=str(p),bytes=p.stat().st_size,sha256=h.hexdigest())
def need(v,m):
    if not v:raise RuntimeError(m)
check=T/"logs/upl_cpu_public_compare_r1.check.json"
old=json.loads(check.read_text(encoding="utf-8"))
need(old["passed"] and not old["complete_private_raw26_equivalence_passed"],"Preserve actual false strict raw gate")
frozen={str(Path(x["path"]).resolve()).casefold():x for x in old["inputs"]+old["outputs"]}
used=[entry(__file__),entry(check)]
def verify(p):
    a=entry(p);need(frozen.get(a["path"].casefold())==a,"Changed frozen analysis source: "+str(p));used.append(a)
history=T/"figures/upl_cpu_public_compare_r1_history.csv";verify(history)
data=list(csv.DictReader(history.open(newline="",encoding="utf-8")))
names=("periodic_constant","wall_constant","wall_evolving")
labels=("Periodic constant k","Wall constant k","Wall evolving k(J)")
colors=("#2474b5","#328657","#c65a39")
rows={(n,t):[r for r in data if r["group"]==n and r["tag"]==t] for n in names for t in ("c","h")}
def col(n,t,k):return np.array([float(r[k]) for r in rows[n,t]])
times=col(names[0],"h","time_s");need(len(times)==257,"Incomplete published history")
x=times*1e6
effect={};native=1024
for tag in ("c","h"):
    states=[]
    for kind in ("wall_constant","wall_evolving"):
        p=T/("outputs/upl_cpu_public_review_r1_"+kind+"_"+tag)/"physical.bin";verify(p)
        raw=np.memmap(p,dtype="<f8",mode="r",offset=12,shape=(257,1+native*26))
        need(np.array_equal(raw[:,0],times),"Actual effect times differ")
        states.append(raw[:,1:].reshape(257,native,26))
    effect[tag]=np.sqrt(np.mean((states[0][:,:,6]-states[1][:,:,6])**2,axis=1))
    need(abs(float(effect[tag].max())-old["variable_k_effect"][tag]["max_pressure_RMS_Pa"])<=1e-15,"Changed sealed effect calculation")
png=T/"figures/upl_cpu_public_compare_layout_r3.png"
csvpath=T/"figures/upl_cpu_public_compare_layout_r3_effect.csv"
receipt=T/"logs/upl_cpu_public_compare_plot_r3.check.json"
need(not any(p.exists() for p in (png,csvpath,receipt)),"Fresh layout outputs required")
threshold=old["resolved_effect_threshold_Pa"]
with csvpath.open("x",newline="",encoding="utf-8") as out:
    w=csv.writer(out);w.writerow(["actual_time_s","model1_minus_model0_coarse_pressure_RMS_Pa","model1_minus_model0_half_pressure_RMS_Pa","model1_own_coarse_half_pressure_RMS_Pa","predeclared_resolved_effect_threshold_Pa"])
    w.writerows(zip(times,effect["c"],effect["h"],col("wall_evolving","h","own_half_pressure_RMS_Pa"),np.full(257,threshold)))
fig,axes=plt.subplots(2,3,figsize=(13.4,8.0),constrained_layout=True)
for name,label,color in zip(names,labels,colors):
    for tag in ("c","h"):
        style=dict(color=color,lw=1.6 if tag=="h" else .8,ls="-" if tag=="h" else ":")
        for ax,key in zip(axes[0],("pressure_mode_over_Pstar","max_abs_J_minus1","max_abs_n_minus_n0")):
            ax.plot(x,col(name,tag,key),**style,label=label if tag=="h" else None)
    h=np.column_stack([col(name,"h",k) for k in ("own_half_p_RMS_over_Pstar","own_half_v_vector_RMS_over_A","own_half_u_vector_RMS_over_Ustar")])
    axes[1,2].plot(x,1e6*h.max(axis=1),color=color,label=label)
axes[0,0].plot(x,col("wall_constant","h","constant_reference_pressure_mode_over_Pstar"),"k--",lw=1.2,label="Constant-k linear reference only")
axes[0,0].set_ylabel("Pressure cosine mode / P*");axes[0,0].legend(fontsize=7)
axes[0,1].set_ylabel("Maximum |J - 1|");axes[0,2].set_ylabel("Maximum |n - n0|")
lo=col("wall_evolving","h","min_k_over_k0");hi=col("wall_evolving","h","max_k_over_k0")
axes[1,0].fill_between(x,lo,hi,color=colors[2],alpha=.22,label="Evolving wall spatial min/max")
axes[1,0].plot(x,lo,color=colors[2],lw=1);axes[1,0].plot(x,hi,color=colors[2],lw=1)
axes[1,0].axhline(1,color="k",ls="--",lw=1,label="Constant k / k0")
axes[1,0].set_ylabel("Hydraulic conductivity / k0");axes[1,0].legend(fontsize=7)
axes[1,1].plot(x,effect["c"],color=colors[2],label="Model1 - model0 coarse RMS")
axes[1,1].plot(x,col("wall_evolving","h","own_half_pressure_RMS_Pa"),color=colors[0],label="Model1 own coarse/half RMS")
axes[1,1].axhline(threshold,color="k",ls="--",lw=1,label="Predeclared resolved-effect threshold")
axes[1,1].set_ylabel("Pressure comparison RMS [Pa]");axes[1,1].legend(fontsize=7)
axes[1,2].set_ylabel("Max normalized p/v/u half RMS [ppm]");axes[1,2].set_ylim(0,1.0)
axes[1,2].legend(fontsize=7,loc="lower right")
axes[1,2].text(.02,.98,"Original half limit:100 ppm (off-scale)\nAbsolute 5 Pa / 0.005 mm also checked",transform=axes[1,2].transAxes,va="top",fontsize=7,bbox=dict(facecolor="white",edgecolor="none",alpha=.92))
for ax in axes.flat:
    ax.set_xlabel("Actual time [microseconds]");ax.grid(alpha=.22);ax.ticklabel_format(axis="y",style="sci",scilimits=(-3,3))
fig.suptitle("Limited public CPU dynamic seepage: native saved-field review\nSolid:half dt; dotted:coarse dt. Full raw257 private equivalence FAILS at initial diagnostics; evolved256 all26 bits exact.",fontsize=11)
fig.savefig(png,dpi=180);plt.close(fig)
for a in used:need(entry(a["path"])==a,"Layout input changed")
result=dict(passed=True,scope="Layout-only scientific export and matching effect CSV; sealed raw257 failure remains false",inputs=used,outputs=[entry(png),entry(csvpath)],
    complete_private_raw26_equivalence_passed=False,raw_data_modified=False,numerical_thresholds_changed=False,solver_invoked=False,physical_acceptance=False)
with receipt.open("x",encoding="utf-8") as out:json.dump(result,out,indent=2);out.write("\n")
print("PASSED fresh scientific layout; original compare_r1 outputs retained")



