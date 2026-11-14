"""Offline fixed-state scientific review; no solver/native/build invocation or time advance."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np

T=Path(__file__).resolve().parents[1]
TAG="c08_tpi_state_review_r1"
CHECK=T/"logs"/(TAG+".check.json")
BASE=T/"outputs/c08_tpi_state_r1"
PARTS=(38,76)
LEGS=("baseline","proposal_after_original_BC")
FOCUS=(4953,4954,6767,6865)
PAIRS=((4953,4954),(6767,6865))
KEYS="x_m z_m p_actual_Pa P0_Pa J n V_m2 k_m_s theta_s_1 FS neighbors fixed_donors true_Dirichlet S_LP_1_per_m_s Rgamma_Pa_per_m_s conditional_raw_defined actual_rate_Pa_s float_error_Pa_s float_budget_Pa_s expanded_error_Pa_s expanded_budget_Pa_s AS_eig_min AS_eig_mid AS_eig_max".split()
EPS=np.finfo("f8").eps

def need(ok,message):
    if not ok:raise RuntimeError(message)
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def bind(e):
    need(stat(e["path"])==e,"Consumed stat changed: "+e["path"]);return e
def bits(a,b,dtype="<f8"):
    a,b=np.asarray(a,dtype=dtype),np.asarray(b,dtype=dtype)
    return a.shape==b.shape and a.tobytes()==b.tobytes()
def close(a,b):return abs(a-b)<=64*EPS*5000*(abs(a)+abs(b))+64*np.finfo("f8").smallest_subnormal
def csvread(p):
    with p.open(encoding="utf-8-sig",newline="") as f:return list(csv.DictReader(f))
def csvwrite(p,rows):
    with p.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def change(old,new):return None if old==0 else 100*(new-old)/abs(old)

def figures(prefix,a,raw,states,pairs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    colors=("#226AA7","#D76B24");x=np.arange(2);width=.34
    fig,ax=plt.subplots(2,2,figsize=(12,8),layout="constrained")
    for col,metric,title,unit in ((0,"Rgamma_RMS","Unscaled residual RMS",r"Pa m$^{-1}$ s$^{-1}$"),(1,"Rgamma_abs_max","Largest absolute unscaled residual",r"Pa m$^{-1}$ s$^{-1}$")):
        for leg,label in enumerate(("Original pressure","One row + original FS policy")):
            v=[float(states[(p,LEGS[leg])][metric]) for p in PARTS]
            bars=ax[0,col].bar(x+(leg-.5)*width,v,width,color=colors[leg],label=label)
            ax[0,col].bar_label(bars,fmt="%.3g",fontsize=8,padding=2)
        ax[0,col].set(title=title,ylabel=unit,xticks=x,xticklabels=["Part 38","Part 76"]);ax[0,col].margins(y=.2)
    labels=[str(p)+"\n"+str(i)+"/"+str(j) for p in PARTS for i,j in PAIRS];xp=np.arange(4)
    for leg,label in enumerate(("Original pressure","One row + original FS policy")):
        v=[float(pairs[(p,LEGS[leg],i,j)]["rddot_m_s2"]) for p in PARTS for i,j in PAIRS]
        ax[1,0].bar(xp+(leg-.5)*width,v,width,color=colors[leg],label=label)
    ax[1,0].axhline(0,color="k",lw=.7);ax[1,0].set(title="Two fixed pairs: instantaneous r double-dot",ylabel=r"m s$^{-2}$",xticks=xp,xticklabels=labels)
    for pi,p in enumerate(PARTS):
        dp=a[pi,1,:,KEYS.index("p_actual_Pa")]-a[pi,0,:,KEYS.index("p_actual_Pa")]
        ax[1,1].scatter(a[pi,0,:,KEYS.index("p_actual_Pa")]/1000,dp,s=5,alpha=.6,color=colors[pi],edgecolors="none",label="Part "+str(p),rasterized=True)
    ax[1,1].axhline(0,color="k",lw=.7);ax[1,1].set(title="Actual post-policy pressure change: every soil ID",xlabel="Original native pressure [kPa]",ylabel="Post-policy minus original [Pa]")
    ax[1,1].legend(loc="best",fontsize=8)
    for item in ax.flat:item.grid(axis="y",alpha=.22)
    handles,labels0=ax[0,0].get_legend_handles_labels();fig.legend(handles,labels0,loc="outside lower center",ncol=2,fontsize=9)
    fig.suptitle("C08: one conditional fixed-state pressure row, not a TPI trajectory or repair acceptance",fontsize=12)
    p1=Path(str(prefix)+"_summary.png");fig.savefig(p1,dpi=180);plt.close(fig)
    fig,ax=plt.subplots(2,2,figsize=(12,7),layout="constrained")
    rmax=float(np.max(np.abs(a[:,0,:,KEYS.index("Rgamma_Pa_per_m_s")])));dpall=a[:,1,:,KEYS.index("p_actual_Pa")]-a[:,0,:,KEYS.index("p_actual_Pa")]
    dmax=float(np.max(np.abs(dpall)));scales=(max(rmax,np.finfo("f8").tiny),max(dmax,np.finfo("f8").tiny))
    for pi,p in enumerate(PARTS):
        xx,zz=a[pi,0,:,0],a[pi,0,:,1]
        for c,values in enumerate((a[pi,0,:,KEYS.index("Rgamma_Pa_per_m_s")],dpall[pi])):
            artist=ax[pi,c].scatter(xx,zz,c=values,s=5,cmap="coolwarm",norm=Normalize(-scales[c],scales[c]),edgecolors="none",rasterized=True)
            title="Original R_gamma" if c==0 else "After original FS policy: delta pressure"
            ax[pi,c].set(title="Part "+str(p)+": "+title,xlabel="Actual x [m]",ylabel="Actual z [m]",aspect="equal")
            fig.colorbar(artist,ax=ax[pi,c],shrink=.87,label=r"R_gamma [Pa m$^{-1}$ s$^{-1}$]" if c==0 else "Pressure change [Pa]")
    fig.suptitle("All 5000 original soil positions; unsmoothed scatter, no geometry or time advance",fontsize=12)
    p2=Path(str(prefix)+"_spatial.png");fig.savefig(p2,dpi=180);plt.close(fig);return [p1,p2]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--execution-authorized",action="store_true")
    need(p.parse_args().execution_authorized,"Separate root offline review admission required")
    prefix=T/"figures"/TAG
    destinations=[CHECK]+[Path(str(prefix)+s) for s in ("_states.csv","_pairs.csv","_focus.csv","_summary.png","_spatial.png")]
    need(not any(q.exists() for q in destinations),"Existing complete/partial scientific review protected")
    cp=T/"logs/c08_tpi_state_r1.check.json";check=read(cp)
    need(check["passed"] and check["consumed_stats_unchanged"] and check["component_invocations"]==1 and check["physical_steps"]==0,"Passed unique component required")
    call=read(bind(check["actual_call"])["path"]);done=read(bind(check["completion"])["path"])
    need(call["actual_Popen_wait_exit"]==call["actual_Win32_exit"]==0 and call["ownership_failure"] is None and done["passed"],"Actual completed component call required")
    need(done["actual_force_calls"]==done["actual_Darcy_calls"]==4 and done["proposal_force_calls"]==2 and done["baseline_native_bits_rows"]==10000
         and done["soil_rows"]==20000 and done["focus_rows"]==16 and done["pair_rows"]==8 and done["summary_rows"]==4
         and done["admitted_state_proposals"]==2 and done["both_states_S_LP_and_raw_admissible"]
         and done["physical_steps"]==done["material_return_calls"]==0,"Actual bounded4-force/2-state coverage differs")
    files={Path(e["path"]).name:e for e in check["files"]};used=[stat(Path(__file__)),stat(T/"notes/c08_tpi_state_review_r1.md"),stat(cp),bind(check["actual_call"]),bind(check["completion"])]
    for leaf in ("soil.csv","summary.csv","focus.csv","pairs.csv"):
        need(Path(files[leaf]["path"]).resolve()==(BASE/leaf).resolve(),"Actual component CSV path differs");used.append(bind(files[leaf]))
    states={(int(r["part"]),r["leg"]):r for r in csvread(BASE/"summary.csv")};pairlist=csvread(BASE/"pairs.csv");focuslist=csvread(BASE/"focus.csv")
    need(set(states)=={(p,l) for p in PARTS for l in LEGS} and len(pairlist)==8 and len(focuslist)==16,"Summary/focus/pair scope differs")
    need({(int(r["part"]),r["leg"],int(r["native_id"])) for r in focuslist}=={(p,l,i) for p in PARTS for l in LEGS for i in FOCUS},"Focus ID/leg coverage differs")
    pairs={(int(r["part"]),r["leg"],int(r["id_i"]),int(r["id_j"])):r for r in pairlist}
    need(len(pairs)==8 and set(pairs)=={(p,l,i,j) for p in PARTS for l in LEGS for i,j in PAIRS},"Pair coverage differs")
    a=np.full((2,2,5000,len(KEYS)),np.nan);raw=np.full((2,5000),np.nan);seen=np.zeros((2,2,5000),bool);count=0
    with (BASE/"soil.csv").open(encoding="utf-8-sig",newline="") as f:
        for row in csv.DictReader(f):
            part,leg,native=int(row["part"]),row["leg"],int(row["native_id"])
            need(part in PARTS and leg in LEGS and 2060<=native<7060,"Soil part/leg/ID outside scope")
            pi,li,j=PARTS.index(part),LEGS.index(leg),native-2060;need(not seen[pi,li,j],"Duplicate soil ID/leg")
            need(float(row["time_s"])==float(states[(part,leg)]["time_s"]) and int(row["completed_step"])==int(states[(part,leg)]["completed_step"]),"Soil actual time/step differs")
            a[pi,li,j]=[float(row[k]) for k in KEYS];seen[pi,li,j]=True;count+=1
            if li==0:need(row["p_conditional_raw_Pa"]!="","Admitted baseline raw proposal missing");raw[pi,j]=float(row["p_conditional_raw_Pa"])
            else:need(row["p_conditional_raw_Pa"]=="" and row["conditional_raw_defined"]=="0","Trial leg must not pretend a second proposal")
    need(count==20000 and np.all(seen) and np.all(np.isfinite(a)) and np.all(np.isfinite(raw)),"Incomplete/nonfinite scientific fields")
    def field(pi,li,key):return a[pi,li,:,KEYS.index(key)]
    result=[];capIds={}
    for pi,part in enumerate(PARTS):
        old,new=states[(part,LEGS[0])],states[(part,LEGS[1])]
        need(old["proposal_allowed"]=="1" and old["nonpositive_S_rows"]==old["raw_overflow_rows"]=="0","Baseline first-proposal admission differs")
        p0,p1=field(pi,0,"p_actual_Pa"),field(pi,1,"p_actual_Pa");S=field(pi,0,"S_LP_1_per_m_s");R=field(pi,0,"Rgamma_Pa_per_m_s")
        need(np.all(a[pi,:,:,KEYS.index("S_LP_1_per_m_s")]>0.) and np.all(field(pi,0,"conditional_raw_defined")==1),"Actual admitted finite positive-S rows differ")
        need(np.all(a[pi,:,:,KEYS.index("true_Dirichlet")]==0.),"C08 HydroDrainageOFF cannot be relabelled Dirichlet")
        need(bits(raw[pi],(p0+R/S).astype("<f4"),"<f4"),"Baseline actual float raw proposal arithmetic differs")
        fs=np.isin(field(pi,0,"FS"),(2.,3.));cap=fs&(raw[pi]>0);expected=raw[pi].astype("<f4");expected[cap]=0
        need(bits(p1,expected,"<f4") and int(new["positive_FS_cap_changes"])==int(np.count_nonzero(cap)),"Original positive-FS cap/post-policy proposal differs")
        negative=raw[pi]<0.;need(bits(p1[negative],raw[pi,negative],"<f4"),"Completed policy changed negative raw pressure")
        need(bits(field(pi,0,"FS"),field(pi,1,"FS")) and bits(a[pi,0,:,:2],a[pi,1,:,:2]),"Pressure-only proposal changed saved FS/positions")
        capIds[str(part)]=[int(j+2060) for j in np.flatnonzero(cap)]
        for li,leg in enumerate(LEGS):
            sr=states[(part,leg)];rr=field(pi,li,"Rgamma_Pa_per_m_s");rate=field(pi,li,"actual_rate_Pa_s")
            need(close(float(np.sqrt(np.mean(rr*rr))),float(sr["Rgamma_RMS"])) and close(float(np.max(np.abs(rr))),float(sr["Rgamma_abs_max"]))
                 and close(float(np.sqrt(np.mean(rate*rate))),float(sr["actual_rate_RMS_Pa_s"])),"Original component norm summary differs")
            need(np.all(field(pi,li,"float_error_Pa_s")<=field(pi,li,"float_budget_Pa_s")) and np.all(field(pi,li,"expanded_error_Pa_s")<=field(pi,li,"expanded_budget_Pa_s")),"Original arithmetic budgets failed")
        dp=p1-p0
        proposalS=field(pi,1,"S_LP_1_per_m_s")
        result.append(dict(part=part,time_s=float(old["time_s"]),S_min=float(S.min()),S_median=float(np.median(S)),S_max=float(S.max()),proposal_S_min=float(proposalS.min()),proposal_S_median=float(np.median(proposalS)),proposal_S_max=float(proposalS.max()),
            true_Dirichlet_count=0,FS_count=int(fs.sum()),positive_FS_cap_count=int(cap.sum()),negative_raw_unchanged_by_policy_count=int(negative.sum()),
            Rgamma_RMS_old=float(old["Rgamma_RMS"]),Rgamma_RMS_new=float(new["Rgamma_RMS"]),Rgamma_RMS_change_percent=change(float(old["Rgamma_RMS"]),float(new["Rgamma_RMS"])),
            Rgamma_max_old=float(old["Rgamma_abs_max"]),Rgamma_max_new=float(new["Rgamma_abs_max"]),rate_RMS_old_Pa_s=float(old["actual_rate_RMS_Pa_s"]),rate_RMS_new_Pa_s=float(new["actual_rate_RMS_Pa_s"]),
            pressure_change_min_Pa=float(dp.min()),pressure_change_RMS_Pa=float(np.sqrt(np.mean(dp*dp))),pressure_change_max_Pa=float(dp.max())))
    focusout=[]
    for row in focuslist:
        pi,li,j=PARTS.index(int(row["part"])),LEGS.index(row["leg"]),int(row["native_id"])-2060
        for fk,sk in (("p_actual_Pa","p_actual_Pa"),("S_LP","S_LP_1_per_m_s"),("Rgamma","Rgamma_Pa_per_m_s"),("actual_rate_Pa_s","actual_rate_Pa_s"),("AS_eig_min","AS_eig_min"),("AS_eig_mid","AS_eig_mid"),("AS_eig_max","AS_eig_max")):
            need(float(row[fk])==a[pi,li,j,KEYS.index(sk)],"Focus row differs from full soil CSV")
    for pi,part in enumerate(PARTS):
        for native in FOCUS:
            j=native-2060;r=dict(part=part,native_id=native,pressure_old_Pa=field(pi,0,"p_actual_Pa")[j],pressure_new_Pa=field(pi,1,"p_actual_Pa")[j])
            for key in ("AS_eig_min","AS_eig_mid","AS_eig_max"):
                r[key+"_old"]=field(pi,0,key)[j];r[key+"_new"]=field(pi,1,key)[j];r[key+"_change"]=r[key+"_new"]-r[key+"_old"]
            focusout.append(r)
    pairout=[]
    for part in PARTS:
        for i,j in PAIRS:
            old,new=pairs[(part,LEGS[0],i,j)],pairs[(part,LEGS[1],i,j)]
            need(float(old["r_m"])==float(new["r_m"]) and float(old["rdot_m_s"])==float(new["rdot_m_s"]),"Frozen pair geometry/velocity changed")
            for row in (old,new):need(close(float(row["rddot_m_s2"]),float(row["relative_all_neighbor_a_radial_m_s2"])+float(row["tangential_curvature_m_s2"])),"Pair curvature identity differs")
            pairout.append(dict(part=part,id_i=i,id_j=j,distance_m=float(old["r_m"]),rdot_m_s=float(old["rdot_m_s"]),rddot_old_m_s2=float(old["rddot_m_s2"]),rddot_new_m_s2=float(new["rddot_m_s2"]),rddot_change_m_s2=float(new["rddot_m_s2"])-float(old["rddot_m_s2"])))
    for e in used:bind(e)
    csvpaths=[Path(str(prefix)+s) for s in ("_states.csv","_pairs.csv","_focus.csv")]
    for path,rows in zip(csvpaths,(result,pairout,focusout)):csvwrite(path,rows)
    png=figures(prefix,a,raw,states,pairs)
    report=dict(stage=TAG,passed=True,soil_rows=count,states=result,pairs=pairout,positive_FS_cap_native_IDs=capIds,baseline_bits_reused=10000,
        actual_force_calls_reused=4,S_LP_positive_is_not_full_operator_or_trajectory_acceptance=True,pressure_proposal_history_is_not_available=True,
        trial_proposal_allowed_default_is_not_a_second_iteration_proof=True,negative_preservation_scope="raw proposed negative pressure versus after-original-completed-policy pressure; not baseline versus proposal",
        norm_recalculation_budget="64*eps*5000*(abs(original)+abs(recalculated)) plus denormal term; arithmetic only",consumed=used,consumed_stats_unchanged=True,
        outputs=[stat(q) for q in csvpaths+png],unsmoothed_actual_scatter=True,solver_invocations=0,native_invocations=0,SHA_scans=0,physical_acceptance=False,clumping_repair_or_time_trajectory_claimed=False)
    with CHECK.open("x",encoding="utf-8",newline="\n") as f:json.dump(report,f,ensure_ascii=False,indent=2,allow_nan=False);f.write("\n")
    print(str(CHECK))

if __name__=="__main__":main()
