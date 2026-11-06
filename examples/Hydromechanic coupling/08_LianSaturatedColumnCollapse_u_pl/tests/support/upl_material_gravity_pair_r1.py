"""7060-owner cold gravity comparison; old CPU is default MR0, old GPU is MR1."""
import json,struct
from pathlib import Path
import upl_plastic_softening_pair_r1 as helpers
from upl_plastic_softening_pair_r1 import np,plt,SCHEMA,TYPES,need,js,stat,table,write,bound,frob,stress,effective,rms
N,FIXED,DT=7060,2060,2.**-18

def load(tests,tag,kind):
    d=tests/"outputs"/(tag+"_native_r1");receipt=tests/"logs"/(tag+".check.json" if kind!="new" else tag+"_native_r1.check.json");r=js(receipt);need(r["passed"] and r["consumed_stats_unchanged"],"Closed native/control receipt required: "+tag);consumed=[stat(receipt)]
    if kind=="new":
        need(r["original_native_guards_passed"],"Original new native gates failed");consumed += [bound(r[k]) for k in ("source_run_check","source_run_call","source_build","reader_call","native_completion")]+[bound(e) for e in r["files"]]
        need(js(r["source_run_check"]["path"])["passed"] and js(r["source_run_call"]["path"])["actual_solver_Win32_exit"]==0,"New actual solver exit not closed");done=js(d/"completion.json");stage="upl_material_gravity_native_r1"
    elif kind=="cpu_default":
        need(r["original_native_guards_passed"],"Retained default native gates failed");consumed += [bound(r[k]) for k in ("source_build","actual_call","reader_call","native_completion")]+[bound(v["new"]) for v in r["comparisons"].values()]
        need(js(r["actual_call"]["path"])["actual_solver_Win32_exit"]==0,"Retained default solver exit not closed");done=js(d/"completion.json");stage="upl_material_default_native_r1"
    else:
        need(kind=="gpu_mr1","Unknown explicit control schema");consumed += [bound(r[k]) for k in ("actual_call","reader_call")]
        need(js(r["actual_call"]["path"])["actual_target_Win32_exit"]==0 and js(r["actual_call"]["path"])["actual_Popen_wait_exit"]==0,"Retained MR1 solver/tool exit not closed");done=js(d/"completion.json");need(done==r["native_completion"],"Retained embedded completion differs");stage="upl_material_on_native_r1"
    call=js(r["reader_call"]["path"]);need(call["actual_Popen_wait_exit"]==0 and Path(call["arguments"][-1]).samefile(d),"Actual reader exit/directory differs")
    need(done["passed"] and done["stage"]==stage and done["input_run_tag"]==tag and done["samples"]==5 and done["completed_steps"]==128 and done["total_native_IDs"]==N and done["soil_IDs"]==5000 and done["fixed_IDs"]==FIXED and done["typed_arrays"]==22,"7060 native profile scope differs")
    files=[d/n for n in ("typed22.bin","typed22_layout.csv","clocks.csv","native_ids.csv","completion.json")];consumed += [stat(p) for p in files]
    layout=table(d/"typed22_layout.csv");need(len(layout)==22,"22 layout rows required")
    for row,(name,kind,nc) in zip(layout,SCHEMA):need((row["array"],row["type"],int(row["components"]),int(row["bytes_per_particle"]))==(name,kind,nc,TYPES[kind].itemsize*nc),"Typed layout differs")
    raw=(d/"typed22.bin").read_bytes();need(len(raw)==12+5*(8+N*212) and struct.unpack_from("<III",raw)==(N,22,5),"Typed header/size differs");off=12;frames=[];times=[]
    for part in range(5):
        times.append(struct.unpack_from("<d",raw,off)[0]);off+=8;a={}
        for name,kind,nc in SCHEMA:
            x=np.frombuffer(raw,dtype=TYPES[kind],count=N*nc,offset=off);off+=N*nc*TYPES[kind].itemsize;need(np.isfinite(x).all(),"Nonfinite closed typed data");a[name]=x.reshape(N,nc) if nc>1 else x
        need(np.array_equal(a["Idp"],np.arange(N)),"Original ID ordering differs");frames.append(a)
    ids=table(d/"native_ids.csv");need(len(ids)==N and all(int(q["id"])==i and int(q["is_fixed"])==int(i<FIXED) for i,q in enumerate(ids)),"Initial native ID/class map differs");x0=np.array([[float(q[k]) for k in ("x0","y0","z0")] for q in ids]);need(np.array_equal(x0,frames[0]["Posd"]),"Initial coordinate export differs")
    clocks=table(d/"clocks.csv");need(len(clocks)==5,"Five actual clock rows required");scalar=0.;previous=0
    for i,c in enumerate(clocks):
        for _ in range(previous,32*i):scalar+=DT
        previous=32*i;need(int(c["completed_step"])==32*i and int(c["saved_step"])==(32*i-1 if i else 0) and struct.pack("<d",times[i])==struct.pack("<d",scalar)==struct.pack("<d",float(c["time_s"])),"Actual scalar clock/Step differs")
    return dict(frames=frames,times=times,x0=x0,clocks=clocks,done=done,raw=raw,directory=d,consumed=consumed)

def run():
    tests=Path(__file__).resolve().parents[1];prefix=tests/"figures/upl_material_gravity_pair_r1";paths={k:Path(str(prefix)+s) for k,s in {"CSV":"_metrics.csv","PNG":".png","check":".check.json"}.items()};need(not any(p.exists() for p in paths.values()),"Existing gravity artifacts protected")
    source_stats=[stat(Path(__file__)),stat(Path(helpers.__file__)),stat(tests/"support/upl_plastic_periodic_pair_r1.py"),stat(tests/"support/upl_c08_fsmask_r1.py")]
    specs=(("new_CPU","upl_material_gravity_CPU_r1","new"),("new_GPU","upl_material_gravity_GPU_r1","new"),("CPU_default_MR0","upl_material_default_CPU_r1","cpu_default"),("GPU_retained_MR1","upl_material_on_GPU_r1","gpu_mr1"));data={label:load(tests,tag,kind) for label,tag,kind in specs};base=data["new_CPU"]
    for d in data.values():need(np.array_equal(base["x0"],d["x0"]) and all(struct.pack("<d",x)==struct.pack("<d",y) for x,y in zip(base["times"],d["times"])),"Original geometry/actual time matching differs")
    metrics=[];soil=slice(FIXED,N)
    for label,d in data.items():
        for part,a in enumerate(d["frames"]):
            u=a["Posd"][soil]-d["x0"][soil];j=a["PoroVolumeRatio"][soil];kap=a["Kplastic"][soil];fs=a["FSType"][soil]
            metrics.append(dict(dataset=label,part=part,time_s=d["times"][part],completed_step=32*part,soil_IDs=5000,fixed_IDs=2060,signed_dterror_s=float(d["clocks"][part]["signed_dterror_s"]),p_mean_Pa=float(a["PorePress"][soil].astype(float).mean()),p_RMS_Pa=rms(a["PorePress"][soil].astype(float)),material_displacement_RMS_mm=1000*rms(np.linalg.norm(u,axis=1)),material_displacement_max_mm=1000*float(np.linalg.norm(u,axis=1).max()),sigma_eff_Frobenius_RMS_Pa=rms(frob(effective(a)[soil])),sigma_total_Frobenius_RMS_Pa=rms(frob(stress(a)[soil])),J_min=float(j.min()),J_max=float(j.max()),J_max_abs_departure=float(np.abs(j-1).max()),kappa_max=float(kap.max()),kappa_nonzero_IDs=int(np.count_nonzero(kap)),FS23_soil_count=int(np.count_nonzero(np.isin(fs,(2,3))))))
    array_differences=[];file_comparisons={};initial_aux={};pairs=(("new_GPU_minus_CPU","new_GPU","new_CPU"),("new_CPU_vs_default_MR0","new_CPU","CPU_default_MR0"),("new_GPU_vs_retained_MR1","new_GPU","GPU_retained_MR1"))
    for name,left,right in pairs:
        a,b=data[left],data[right];initial_aux[name]=[k for k,_,_ in SCHEMA if a["frames"][0][k].tobytes()!=b["frames"][0][k].tobytes()]
        for part,(fa,fb) in enumerate(zip(a["frames"],b["frames"])):
            for field,kind,nc in SCHEMA:
                x,y=fa[field],fb[field];v=x.astype(float)-y.astype(float);magnitude=np.abs(v) if nc==1 else np.linalg.norm(v,axis=1);bits=x.view("u"+str(x.dtype.itemsize))!=y.view("u"+str(y.dtype.itemsize));changed=bits if nc==1 else np.any(bits,axis=1)
                array_differences.append(dict(comparison=name,part=part,time_s=a["times"][part],array=field,scalar_type=kind,components=nc,native_IDs=N,difference_RMS_native_units=rms(magnitude),difference_max_native_units=float(magnitude.max()),native_ID_at_max=int(magnitude.argmax()),different_scalar_bits_count=int(np.count_nonzero(bits)),different_IDs=int(np.count_nonzero(changed))))
        if name!="new_GPU_minus_CPU":
            r={}
            for leaf in ("typed22.bin","clocks.csv"):
                x=a["raw"] if leaf=="typed22.bin" else (a["directory"]/leaf).read_bytes();y=b["raw"] if leaf=="typed22.bin" else (b["directory"]/leaf).read_bytes();need(len(x)==len(y),"Comparison file size differs");xa=np.frombuffer(x,dtype=np.uint8);ya=np.frombuffer(y,dtype=np.uint8);delta=xa!=ya;r[leaf]=dict(bit_identical=x==y,different_bytes=int(np.count_nonzero(delta)),different_bits=sum(int(v).bit_count() for v in np.bitwise_xor(xa[delta],ya[delta])))
            r["all_new_and_control_soil_kappa_zero"]=all(not np.count_nonzero(f["Kplastic"][soil]) for d in (a,b) for f in d["frames"]);r["comparison_is_observation_not_mandatory_bit_gate"]=True;file_comparisons[name]=r
    write(paths["CSV"],metrics);fig,axes=plt.subplots(2,2,figsize=(11.8,8.1));styles={"new_CPU":dict(color="#1565a8",lw=1.8),"new_GPU":dict(color="#da7b16",marker="o",mfc="none",ls="none",ms=6),"CPU_default_MR0":dict(color="#555555",ls="--",lw=1.2),"GPU_retained_MR1":dict(color="#777777",marker="x",ls="none",ms=5)};time=np.array(base["times"])*1e3
    for ax,key,title,ylabel in ((axes[0,0],"p_RMS_Pa","Cold-start pore pressure","soil pressure RMS (Pa)"),(axes[0,1],"material_displacement_RMS_mm","Original material displacement","soil displacement RMS (mm)"),(axes[1,0],"sigma_eff_Frobenius_RMS_Pa","Effective stress","soil Frobenius RMS (Pa)"),(axes[1,1],"J_max_abs_departure","Actual volume-ratio departure",r"maximum soil $|J-1|$")):
        for label in data:ax.plot(time,[r[key] for r in metrics if r["dataset"]==label],label=label.replace("_"," "),**styles[label])
        ax.set(title=title,xlabel="actual saved time (ms)",ylabel=ylabel);ax.grid(alpha=.22)
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc="upper center",bbox_to_anchor=(.5,.94),ncol=4,frameon=False);fig.suptitle("Cold gravity / free-seepage startup: new softening configuration and retained states",fontsize=13)
    fig.text(.5,.015,"5000 soil + 2060 fixed original IDs / five raw saved times. Old CPU is default MR0; old GPU is explicit MR1.\nKappa is observed, not forced nonzero. This short startup is not equilibrium or nonzero-plastic-wall acceptance; no fitted theory or new bit/physical gate.",ha="center",fontsize=8.5);fig.tight_layout(rect=(0,.065,1,.89));fig.savefig(paths["PNG"],dpi=200);plt.close(fig)
    consumed=source_stats+[e for d in data.values() for e in d["consumed"]];need(all(stat(e["path"])["bytes"]==e["bytes"] and stat(e["path"])["mtime_ns"]==e["mtime_ns"] for e in consumed),"Consumed receipt/export/helper SMT changed")
    review=dict(stage="upl_material_gravity_pair_r1",offline_analysis_completed=True,new_CPU_GPU_original_native_gates_passed=True,native_IDs_per_sample=N,soil_IDs=5000,fixed_IDs=2060,typed_arrays=22,actual_matched_frames=5,metric_rows=len(metrics),array_difference_rows=len(array_differences),same_backend_file_observations=file_comparisons,array_differences=array_differences,initial_different_array_names_descriptive=initial_aux,retained_control_labels=dict(CPU="Default MR0/free, not an old MR1 trajectory",GPU="Accepted explicit MR1/free"),old_GPU_export_provenance="Closed owned reader call and embedded completion identity reused; exports receive current size/mtime observations, not fabricated historical export hashes. Historical mutable live CPP/docs inventories are not revalidated.",input_receipts_exports_and_helpers=consumed,output_artifacts=[stat(p) for k,p in paths.items() if k!="check"],figure_visual_QA_pending=True,new_numerical_gate=False,source_build_solver_decoder_Git_SHA_actions=0,equilibrium_or_nonzero_plastic_wall_acceptance=False,physical_acceptance=False)
    with paths["check"].open("x",encoding="utf-8") as f:json.dump(review,f,indent=2,allow_nan=False);f.write("\n")
    print(json.dumps(dict(offline_analysis_completed=True,same_backend_file_observations=file_comparisons,initial_different_arrays=initial_aux)),flush=True)
if __name__=="__main__":run()
