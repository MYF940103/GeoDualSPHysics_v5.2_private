"""Offline softening pair and retained constant-strength effects; no numerical gate."""
import json,struct
from pathlib import Path
import upl_plastic_periodic_pair_r1 as retained
from upl_plastic_periodic_pair_r1 import np,plt,SCHEMA,TYPES,N,DT,need,js,stat,table,write,bound,frob,stress,image

def load(tests,backend,soft):
    tag=("upl_plastic_softening_" if soft else "upl_material_periodic_shear_")+backend+"_r1"
    stage="upl_plastic_softening_native_r1" if soft else "upl_plastic_periodic_native_r1"
    d=tests/"outputs"/(tag+"_native_r1");p=tests/"logs"/(tag+"_native_r1.check.json");r=js(p)
    need(r["passed"] and r["original_native_guards_passed"] and r["consumed_stats_unchanged"],"Native receipt not closed: "+tag)
    consumed=[stat(p)]+[bound(r[k]) for k in ("source_run_check","source_run_call","source_build","reader_call","native_completion")]+[bound(e) for e in r["files"]]
    need(js(r["source_run_check"]["path"])["passed"] and js(r["source_run_call"]["path"])["actual_solver_Win32_exit"]==0 and js(r["reader_call"]["path"])["actual_Popen_wait_exit"]==0,"Actual solver/reader exit not closed")
    done=js(d/"completion.json");need(done["passed"] and done["stage"]==stage and done["input_run_tag"]==tag and done["samples"]==5 and done["total_native_IDs"]==N and done["fixed_IDs"]==0 and done["typed_arrays"]==22,"Native profile scope differs")
    if soft:need(done["cohesion_peak_Pa"]==5000 and done["cohesion_residual_Pa"]==1000 and done["cohesion_decay"]==5,"Softening descriptive law differs")
    layout=table(d/"typed22_layout.csv");need(len(layout)==22,"22 layout rows required")
    for row,(name,kind,nc) in zip(layout,SCHEMA):need((row["array"],row["type"],int(row["components"]),int(row["bytes_per_particle"]))==(name,kind,nc,TYPES[kind].itemsize*nc),"Typed layout differs")
    need((d/"typed22.bin").stat().st_size==12+5*(8+N*212),"Typed file size differs");frames=[];times=[]
    with (d/"typed22.bin").open("rb") as f:
        need(struct.unpack("<III",f.read(12))==(N,22,5),"Typed header differs")
        for part in range(5):
            times.append(struct.unpack("<d",f.read(8))[0]);a={}
            for name,kind,nc in SCHEMA:
                x=np.fromfile(f,dtype=TYPES[kind],count=N*nc);need(x.size==N*nc and np.isfinite(x).all(),"Incomplete/nonfinite closed typed data");a[name]=x.reshape(N,nc) if nc>1 else x
            need(np.array_equal(a["Idp"],np.arange(N)),"Native ID alignment differs");frames.append(a)
        need(not f.read(1),"Extra typed data")
    ids=table(d/"native_ids.csv");need(len(ids)==N and all(int(v["id"])==i for i,v in enumerate(ids)),"Initial ID table differs")
    x0=np.array([[float(r[k]) for k in ("x0","y0","z0")] for r in ids]);row=np.array([int(r["z_velocity_row"]) for r in ids]);need(np.array_equal(x0,frames[0]["Posd"]) and np.array_equal(np.bincount(row,minlength=32),np.full(32,32)),"Initial row map differs")
    clocks=table(d/"clocks.csv");history=table(d/"history.csv");need(len(clocks)==len(history)==5,"Five clock/history records required");scalar=0.;previous=0
    for i,(c,h) in enumerate(zip(clocks,history)):
        for _ in range(previous,32*i):scalar+=DT
        previous=32*i;need(int(c["completed_step"])==32*i and int(c["saved_step"])==(32*i-1 if i else 0) and int(h["part"])==i and struct.pack("<d",times[i])==struct.pack("<d",scalar)==struct.pack("<d",float(c["time_s"]))==struct.pack("<d",float(h["time_s"])),"Actual clock/step differs")
    return dict(frames=frames,times=times,x0=x0,row=row,clocks=clocks,history=history,done=done,consumed=consumed,soft=soft)

def effective(a):return np.column_stack((a["SigmaState_kk"],a["SigmaState_ij"]))
def cohesion(a,soft):return 1000.+4000.*np.exp(-5.*a["Kplastic"].astype(float)) if soft else np.full(N,5000.)
def rms(a):return float(np.sqrt(np.mean(a*a)))

def run():
    tests=Path(__file__).resolve().parents[1];prefix=tests/"figures/upl_plastic_softening_pair_r1"
    paths={k:Path(str(prefix)+s) for k,s in {"history":"_history.csv","differences":"_differences.csv","row":"_row_profile.csv","png":".png","check":".check.json"}.items()}
    need(not any(p.exists() for p in paths.values()),"Existing softening artifacts protected")
    helpers=[stat(Path(__file__)),stat(Path(retained.__file__)),stat(tests/"support/upl_c08_fsmask_r1.py")]
    data={label:load(tests,backend,soft) for label,backend,soft in (("CPU_soft","CPU",True),("GPU_soft","GPU",True),("CPU_constant","CPU",False),("GPU_constant","GPU",False))};base=data["CPU_soft"]
    for d in data.values():need(np.array_equal(base["x0"],d["x0"]) and np.array_equal(base["row"],d["row"]) and all(struct.pack("<d",x)==struct.pack("<d",y) for x,y in zip(base["times"],d["times"])),"Actual initial IDs/coordinates/rows/times do not match")
    series=[]
    for label,d in data.items():
        for part,a in enumerate(d["frames"]):
            c=cohesion(a,d["soft"]);u=image(a["Posd"]-d["x0"]);h=d["history"][part]
            row=dict(dataset=label,part=part,time_s=d["times"][part],completed_step=32*part,signed_dterror_s=float(d["clocks"][part]["signed_dterror_s"]),p_mean_Pa=float(a["PorePress"].astype(float).mean()),p_RMS_Pa=rms(a["PorePress"].astype(float)),kappa_max=float(a["Kplastic"].max()),kappa_RMS=rms(a["Kplastic"].astype(float)),kappa_nonzero_IDs=int(np.count_nonzero(a["Kplastic"])),cohesion_min_from_saved_kappa_Pa=float(c.min()),cohesion_max_from_saved_kappa_Pa=float(c.max()),material_XYZ_RMS_mm=rms(np.linalg.norm(u,axis=1))*1000,material_XYZ_max_mm=float(np.linalg.norm(u,axis=1).max())*1000,sigma_eff_Frobenius_RMS_Pa=rms(frob(effective(a))),sigma_total_Frobenius_RMS_Pa=rms(frob(stress(a))),J_min=float(a["PoroVolumeRatio"].min()),J_max=float(a["PoroVolumeRatio"].max()),n_min=float(a["PoroPorosity"].min()),n_max=float(a["PoroPorosity"].max()),rho_mix_min_kg_m3=float(a["PoroMixtureDensity"].min()),rho_mix_max_kg_m3=float(a["PoroMixtureDensity"].max()),k_min_m_s=float(a["PoroHydraulicConductivity"].min()),k_max_m_s=float(a["PoroHydraulicConductivity"].max()),FS23_count=int(np.count_nonzero(np.isin(a["FSType"],(2,3)))))
            row["history_p_RMS_roundoff_Pa"]=row["p_RMS_Pa"]-float(h["p_RMS_Pa"]);row["history_sigma_eff_RMS_roundoff_Pa"]=row["sigma_eff_Frobenius_RMS_Pa"]-float(h["sigma_eff_Frobenius_RMS_Pa"])
            row["history_cohesion_min_roundoff_Pa"]=row["cohesion_min_from_saved_kappa_Pa"]-(float(h["cohesion_min_from_saved_kappa_Pa"]) if d["soft"] else 5000.);row["history_cohesion_max_roundoff_Pa"]=row["cohesion_max_from_saved_kappa_Pa"]-(float(h["cohesion_max_from_saved_kappa_Pa"]) if d["soft"] else 5000.);series.append(row)
    differences=[];initial_aux={};pairs=(("soft_GPU_minus_CPU","GPU_soft","CPU_soft"),("CPU_soft_minus_constant","CPU_soft","CPU_constant"),("GPU_soft_minus_constant","GPU_soft","GPU_constant"))
    for name,left,right in pairs:
        a,b=data[left],data[right];initial_aux[name]=[k for k,_,_ in SCHEMA if a["frames"][0][k].tobytes()!=b["frames"][0][k].tobytes()]
        for part,(fa,fb) in enumerate(zip(a["frames"],b["frames"])):
            r=dict(comparison=name,left_dataset=left,right_dataset=right,part=part,time_s=a["times"][part],completed_step=32*part)
            delta=[("p","Pa",fa["PorePress"].astype(float)-fb["PorePress"],None),("material_XYZ","mm",1000*image(image(fa["Posd"]-a["x0"])-image(fb["Posd"]-b["x0"])),None),("sigma_eff","Pa",effective(fa)-effective(fb),frob),("sigma_total","Pa",stress(fa)-stress(fb),frob)]
            for field,key,unit in (("Kplastic","kappa","1"),("PoroVolumeRatio","J","1"),("PoroPorosity","n","1"),("PoroMixtureDensity","rho_mix","kg_m3"),("PoroHydraulicConductivity","k","m_s")):delta.append((key,unit,fa[field].astype(float)-fb[field].astype(float),None))
            for key,unit,x,norm in delta:
                magnitude=np.abs(x) if x.ndim==1 else (norm(x) if norm else np.linalg.norm(x,axis=1));r[key+"_difference_RMS_"+unit]=rms(magnitude);r[key+"_difference_max_"+unit]=float(magnitude.max());r[key+"_native_ID_at_max"]=int(magnitude.argmax())
            differences.append(r)
    profile=[]
    for row in range(32):
        pick=base["row"]==row;r=dict(initial_z_row=row,native_IDs=int(pick.sum()),initial_z_m=float(base["x0"][pick,2].mean()))
        for label,d in data.items():
            a=d["frames"][-1];k=a["Kplastic"][pick].astype(float);c=cohesion(a,d["soft"])[pick]
            for key,v in (("kappa_mean",k.mean()),("kappa_min",k.min()),("kappa_max",k.max()),("cohesion_min_Pa",c.min()),("cohesion_max_Pa",c.max())):r[label+"_"+key]=float(v)
        profile.append(r)
    write(paths["history"],series);write(paths["differences"],differences);write(paths["row"],profile)
    fig,axes=plt.subplots(2,3,figsize=(13.4,8.1));styles={"CPU_soft":dict(color="#1565a8",lw=1.8),"GPU_soft":dict(color="#da7b16",marker="o",mfc="none",ls="none",ms=6),"CPU_constant":dict(color="#555555",ls="--",lw=1.3),"GPU_constant":dict(color="#777777",marker="x",ls="none",ms=5)};time=np.array(base["times"])*1e6
    for ax,key,scale,title,ylabel in ((axes[0,0],"kappa_max",1.,"Saved plastic history",r"maximum $\kappa$"),(axes[0,1],"cohesion_min_from_saved_kappa_Pa",1.,"Derived strength from saved history","minimum cohesion (Pa)"),(axes[0,2],"p_RMS_Pa",1.,"Pore pressure","native pressure RMS (Pa)"),(axes[1,0],"sigma_eff_Frobenius_RMS_Pa",.001,"Effective stress","Frobenius RMS (kPa)")):
        for label in data:ax.plot(time,[r[key]*scale for r in series if r["dataset"]==label],label=label.replace("_"," "),**styles[label])
        ax.set(title=title,xlabel=r"actual saved time ($\mu$s)",ylabel=ylabel);ax.grid(alpha=.22)
    ax=axes[1,1]
    for backend,color,marker in (("CPU","#1565a8","o"),("GPU","#da7b16","s")):
        r=[v for v in differences if v["comparison"]==backend+"_soft_minus_constant"];ax.plot(time,[v["sigma_eff_difference_RMS_Pa"] for v in r],color=color,marker=marker,mfc="none",label=backend)
    ax.set(title="Softening effect at matched material IDs",xlabel=r"actual saved time ($\mu$s)",ylabel=r"RMS $\|\sigma'_{soft}-\sigma'_{constant}\|_F$ (Pa)");ax.grid(alpha=.22);ax.legend(frameon=False)
    ax=axes[1,2]
    for label in data:ax.plot([r["initial_z_m"] for r in profile],[r[label+"_kappa_mean"] for r in profile],**styles[label])
    ax.set(title="Final plastic history by original z row",xlabel="initial material z (m)",ylabel=r"row mean $\kappa$");ax.grid(alpha=.22)
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc="upper center",bbox_to_anchor=(.5,.94),ncol=4,frameon=False);fig.suptitle("Periodic cohesion softening: CPU / GPU and retained constant-strength controls",fontsize=14)
    fig.text(.5,.015,"Five actual saved states / 1024 original IDs; descriptive differences, no new numerical or physical gate.\nCohesion uses saved float kappa, not the continuous return-root residual. Lines connect raw samples / row means; no fitting or smoothing.",ha="center",fontsize=9);fig.tight_layout(rect=(0,.065,1,.89));fig.savefig(paths["png"],dpi=200);plt.close(fig)
    consumed=helpers+[e for d in data.values() for e in d["consumed"]];need(all(stat(e["path"])["bytes"]==e["bytes"] and stat(e["path"])["mtime_ns"]==e["mtime_ns"] for e in consumed),"Closed consumed artifacts changed")
    maxima={name:{k:max(r[k] for r in differences if r["comparison"]==name) for k in differences[0] if "difference_" in k} for name,_,_ in pairs}
    review=dict(stage="upl_plastic_softening_pair_r1",offline_analysis_completed=True,original_all_four_native_gates_passed=True,matched_actual_frames=5,native_IDs_per_frame=N,typed_arrays_per_frame=22,history_rows=len(series),difference_rows=len(differences),profile_rows=len(profile),initial_different_array_names_descriptive=initial_aux,maxima_by_comparison=maxima,input_receipts_and_exports=consumed,output_artifacts=[stat(p) for k,p in paths.items() if k!="check"],figure_visual_QA_pending=True,cross_backend_comparison_is_descriptive=True,same_backend_effects_are_softening_minus_retained_constant=True,saved_kappa_strength_is_not_continuous_root_residual=True,new_numerical_gate=False,source_build_solver_decoder_Git_SHA_actions=0,physical_acceptance=False)
    with paths["check"].open("x",encoding="utf-8") as f:json.dump(review,f,indent=2,allow_nan=False);f.write("\n")
    print(json.dumps(dict(offline_analysis_completed=True,maxima=maxima,initial_different_arrays=initial_aux)),flush=True)
if __name__=="__main__":run()
