"""Offline POS/NEG dilation pairs; compare backends only within each material option."""
import json,struct
from pathlib import Path
import upl_plastic_softening_pair_r1 as soft
from upl_plastic_softening_pair_r1 import np,plt,SCHEMA,TYPES,N,DT,need,js,stat,table,write,bound,frob,stress,image,effective,rms

def load(tests,backend,option):
    tag={"POS":"upl_plastic_dilative_","NEG":"upl_plastic_contractive_"}[option]+backend+"_r1"
    stage="upl_plastic_dilation_native_r1"
    d=tests/"outputs"/(tag+"_native_r1");p=tests/"logs"/(tag+"_native_r1.check.json");r=js(p)
    need(r["passed"] and r["original_native_guards_passed"] and r["consumed_stats_unchanged"],"Native receipt not closed: "+tag)
    consumed=[stat(p)]+[bound(r[k]) for k in ("source_run_check","source_run_call","source_build","reader_call","native_completion")]+[bound(e) for e in r["files"]]
    need(js(r["source_run_check"]["path"])["passed"] and js(r["source_run_call"]["path"])["actual_solver_Win32_exit"]==0 and js(r["reader_call"]["path"])["actual_Popen_wait_exit"]==0,"Actual solver/reader exit not closed")
    done=js(d/"completion.json");need(done["passed"] and done["stage"]==stage and done["input_run_tag"]==tag and done["samples"]==5 and done["total_native_IDs"]==N and done["fixed_IDs"]==0 and done["typed_arrays"]==22,"Native profile scope differs")
    need(done["material_selector"]==option and done["cohesion_peak_Pa"]==({"POS":5000,"NEG":7500}[option]) and done["cohesion_residual_Pa"]==1000 and done["cohesion_decay"]==5 and done["dilation_decay_float"]==float(np.float32(.2)),"Declared material metadata/law differs")
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
    return dict(frames=frames,times=times,x0=x0,row=row,clocks=clocks,history=history,done=done,consumed=consumed,option=option)

def cohesion(a,d):
    c=d["done"];return c["cohesion_residual_Pa"]+(c["cohesion_peak_Pa"]-c["cohesion_residual_Pa"])*np.exp(-c["cohesion_decay"]*a["Kplastic"].astype(float))
def dilation(a,d):
    c=d["done"];return c["initial_dilation_radians_float"]*np.exp(-c["dilation_decay_float"]*a["Kplastic"].astype(float))

def run():
    tests=Path(__file__).resolve().parents[1];prefix=tests/"figures/upl_plastic_dilation_pair_r1"
    paths={k:Path(str(prefix)+s) for k,s in {"history":"_history.csv","differences":"_differences.csv","arrays":"_arrays.csv","png":".png","check":".check.json"}.items()}
    need(not any(p.exists() for p in paths.values()),"Existing dilation artifacts protected")
    helpers=[stat(Path(__file__)),stat(Path(soft.__file__)),stat(tests/"support/upl_plastic_periodic_pair_r1.py"),stat(tests/"support/upl_c08_fsmask_r1.py")]
    data={option+"_"+backend:load(tests,backend,option) for option in ("POS","NEG") for backend in ("CPU","GPU")};base=data["POS_CPU"]
    for d in data.values():need(np.array_equal(base["x0"],d["x0"]) and np.array_equal(base["row"],d["row"]) and all(struct.pack("<d",x)==struct.pack("<d",y) for x,y in zip(base["times"],d["times"])),"Actual original IDs/coordinates/rows/times differ")
    series=[]
    for label,d in data.items():
        born=d["done"];psi0=born["initial_dilation_radians_float"];peak=born["cohesion_peak_Pa"]
        for part,a in enumerate(d["frames"]):
            c=cohesion(a,d);psi=dilation(a,d);u=image(a["Posd"]-d["x0"]);h=d["history"][part]
            r=dict(dataset=label,option=d["option"],part=part,time_s=d["times"][part],completed_step=32*part,signed_dterror_s=float(d["clocks"][part]["signed_dterror_s"]),cohesion_peak_Pa=peak,psi0_radians_float=psi0,dilation_decay_float=born["dilation_decay_float"],kappa_max=float(a["Kplastic"].max()),kappa_RMS=rms(a["Kplastic"].astype(float)),kappa_nonzero_IDs=int(np.count_nonzero(a["Kplastic"])),p_mean_Pa=float(a["PorePress"].astype(float).mean()),p_RMS_Pa=rms(a["PorePress"].astype(float)),p_min_Pa=float(a["PorePress"].min()),p_max_Pa=float(a["PorePress"].max()),J_min=float(a["PoroVolumeRatio"].min()),J_max=float(a["PoroVolumeRatio"].max()),J_max_abs_departure=float(np.abs(a["PoroVolumeRatio"]-1.).max()),cohesion_min_from_saved_kappa_Pa=float(c.min()),cohesion_max_from_saved_kappa_Pa=float(c.max()),cohesion_max_loss_from_peak_Pa=float(peak-c.min()),psi_min_radians_from_saved_kappa=float(psi.min()),psi_max_radians_from_saved_kappa=float(psi.max()),psi_max_abs_change_degrees=float(np.abs(psi0-psi).max()*180./np.pi),sigma_eff_Frobenius_RMS_Pa=rms(frob(effective(a))),sigma_total_Frobenius_RMS_Pa=rms(frob(stress(a))),material_XYZ_RMS_mm=1000*rms(np.linalg.norm(u,axis=1)),material_XYZ_max_mm=1000*float(np.linalg.norm(u,axis=1).max()),n_min=float(a["PoroPorosity"].min()),n_max=float(a["PoroPorosity"].max()),rho_mix_min_kg_m3=float(a["PoroMixtureDensity"].min()),rho_mix_max_kg_m3=float(a["PoroMixtureDensity"].max()),k_min_m_s=float(a["PoroHydraulicConductivity"].min()),k_max_m_s=float(a["PoroHydraulicConductivity"].max()),FS23_count=int(np.count_nonzero(np.isin(a["FSType"],(2,3)))))
            r["history_p_mean_roundoff_Pa"]=r["p_mean_Pa"]-float(h["p_mean_Pa"]);r["history_cohesion_min_roundoff_Pa"]=r["cohesion_min_from_saved_kappa_Pa"]-float(h["cohesion_min_from_saved_kappa_Pa"]);r["history_psi_min_roundoff_rad"]=r["psi_min_radians_from_saved_kappa"]-float(h["psi_min_radians_from_saved_kappa"]);series.append(r)
    differences=[];arrayrows=[];initial_aux={}
    for option in ("POS","NEG"):
        a,b=data[option+"_GPU"],data[option+"_CPU"];initial_aux[option]=[k for k,_,_ in SCHEMA if a["frames"][0][k].tobytes()!=b["frames"][0][k].tobytes()]
        for part,(fa,fb) in enumerate(zip(a["frames"],b["frames"])):
            r=dict(option=option,comparison="GPU_minus_CPU_within_"+option,part=part,time_s=a["times"][part],completed_step=32*part)
            delta=[("p","Pa",fa["PorePress"].astype(float)-fb["PorePress"],None),("material_XYZ","mm",1000*image(image(fa["Posd"]-a["x0"])-image(fb["Posd"]-b["x0"])),None),("sigma_eff","Pa",effective(fa)-effective(fb),frob),("sigma_total","Pa",stress(fa)-stress(fb),frob),("cohesion","Pa",cohesion(fa,a)-cohesion(fb,b),None),("psi","rad",dilation(fa,a)-dilation(fb,b),None)]
            for field,key,unit in (("Kplastic","kappa","1"),("PoroVolumeRatio","J","1"),("PoroPorosity","n","1"),("PoroMixtureDensity","rho_mix","kg_m3"),("PoroHydraulicConductivity","k","m_s")):delta.append((key,unit,fa[field].astype(float)-fb[field].astype(float),None))
            for key,unit,x,norm in delta:
                magnitude=np.abs(x) if x.ndim==1 else (norm(x) if norm else np.linalg.norm(x,axis=1));r[key+"_difference_RMS_"+unit]=rms(magnitude);r[key+"_difference_max_"+unit]=float(magnitude.max());r[key+"_native_ID_at_max"]=int(magnitude.argmax())
            differences.append(r)
            for name,kind,nc in SCHEMA:
                x,y=fa[name],fb[name];v=x.astype(float)-y.astype(float);magnitude=np.abs(v) if nc==1 else np.linalg.norm(v,axis=1);bits=x.view("u"+str(x.dtype.itemsize))!=y.view("u"+str(y.dtype.itemsize));changed=bits if nc==1 else np.any(bits,axis=1)
                arrayrows.append(dict(option=option,part=part,time_s=a["times"][part],array=name,scalar_type=kind,components=nc,difference_RMS_native_units=rms(magnitude),difference_max_native_units=float(magnitude.max()),native_ID_at_max=int(magnitude.argmax()),different_scalar_bits_count=int(np.count_nonzero(bits)),different_IDs=int(np.count_nonzero(changed))))
    write(paths["history"],series);write(paths["differences"],differences);write(paths["arrays"],arrayrows)
    fig,axes=plt.subplots(2,3,figsize=(13.4,8.1));styles={"POS_CPU":dict(color="#1565a8",lw=1.8),"POS_GPU":dict(color="#1565a8",marker="o",mfc="none",ls="none",ms=6),"NEG_CPU":dict(color="#9a346f",ls="--",lw=1.8),"NEG_GPU":dict(color="#9a346f",marker="s",mfc="none",ls="none",ms=5)};labels={"POS_CPU":"POS CPU (+2.5 deg, cp 5 kPa)","POS_GPU":"POS GPU","NEG_CPU":"NEG CPU (-5 deg, cp 7.5 kPa)","NEG_GPU":"NEG GPU"};time=np.array(base["times"])*1e6
    for ax,key,scale,title,ylabel in ((axes[0,0],"kappa_max",1.,"Saved plastic history",r"maximum $\kappa$"),(axes[0,1],"p_mean_Pa",1.,"Mean pore pressure (ranges/RMS in CSV)","native mean pressure (Pa)"),(axes[0,2],"J_max_abs_departure",1.,"Actual volume ratio departure",r"maximum $|J-1|$"),(axes[1,0],"cohesion_max_loss_from_peak_Pa",1.,"Derived cohesion loss from saved history",r"$c_p-\min c(\kappa)$ (Pa)"),(axes[1,1],"psi_max_abs_change_degrees",1.,"Derived dilation relaxation from saved history",r"maximum $|\psi_0-\psi(\kappa)|$ (degrees)"),(axes[1,2],"sigma_eff_Frobenius_RMS_Pa",.001,"Effective stress","Frobenius RMS (kPa)")):
        for label in data:ax.plot(time,[r[key]*scale for r in series if r["dataset"]==label],label=labels[label],**styles[label])
        ax.set(title=title,xlabel=r"actual saved time ($\mu$s)",ylabel=ylabel);ax.grid(alpha=.22)
    handles,legend=axes[0,0].get_legend_handles_labels();fig.legend(handles,legend,loc="upper center",bbox_to_anchor=(.5,.94),ncol=4,frameon=False);fig.suptitle("Periodic positive / negative dilation: matched CPU / GPU within each material option",fontsize=14)
    fig.text(.5,.015,"Five raw saved states / 1024 original IDs. POS and NEG have different cp and psi0; no cross-option error comparison.\nStrength and dilation use saved float kappa, not the continuous return root. No fitting, smoothing, new physical gate or performance claim.",ha="center",fontsize=9);fig.tight_layout(rect=(0,.065,1,.89));fig.savefig(paths["png"],dpi=200);plt.close(fig)
    consumed=helpers+[e for d in data.values() for e in d["consumed"]];need(all(stat(e["path"])["bytes"]==e["bytes"] and stat(e["path"])["mtime_ns"]==e["mtime_ns"] for e in consumed),"Closed consumed artifacts changed")
    maxima={option:{k:max(r[k] for r in differences if r["option"]==option) for k in differences[0] if "difference_" in k} for option in ("POS","NEG")}
    evidence={label:dict(native_completion=d["done"],native_metadata_verified_by_reader=dict(MaterialReturn_type="DatUint",MaterialReturn=1,DilationDecay_type="DatFloat",DilationDecay=d["done"]["dilation_decay_float"],free_seepage_true_only_key_absent=True),law_parameters_source="Explicit option plus root-reviewed XML and the closed compiled native profile; psi0/strength outputs are derived, not extra native arrays.") for label,d in data.items()}
    review=dict(stage="upl_plastic_dilation_pair_r1",offline_analysis_completed=True,original_all_four_native_gates_passed=True,matched_actual_frames=5,native_IDs_per_frame=N,typed_arrays_per_frame=22,history_rows=len(series),difference_rows=len(differences),array_metric_rows=len(arrayrows),initial_different_array_names_descriptive=initial_aux,maxima_within_options_only=maxima,material_and_born_metadata_evidence=evidence,input_receipts_and_exports=consumed,output_artifacts=[stat(p) for k,p in paths.items() if k!="check"],figure_visual_QA_pending=True,no_cross_option_error_comparison=True,new_numerical_gate=False,source_build_solver_decoder_Git_SHA_actions=0,physical_acceptance=False)
    with paths["check"].open("x",encoding="utf-8") as f:json.dump(review,f,indent=2,allow_nan=False);f.write("\n")
    print(json.dumps(dict(offline_analysis_completed=True,maxima=maxima,initial_different_arrays=initial_aux)),flush=True)
if __name__=="__main__":run()
