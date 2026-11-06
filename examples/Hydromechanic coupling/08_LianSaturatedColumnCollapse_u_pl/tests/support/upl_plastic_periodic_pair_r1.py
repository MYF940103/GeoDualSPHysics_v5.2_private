"""Offline paired native exports only; no BI4 decoder, solver or numerical acceptance gate."""
import csv,json,struct
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from upl_c08_fsmask_r1 import SCHEMA,TYPES,need
N,LENGTH,DT=1024,1.28,2.**-19
def js(p):return json.loads(Path(p).read_text(encoding="utf-8"))
def stat(p):
    p=Path(p).resolve();s=p.stat();return {"path":str(p),"bytes":s.st_size,"mtime_ns":s.st_mtime_ns}
def table(p):
    with Path(p).open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f))
def write(p,rows):
    with p.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def bound(e):
    a=stat(e["path"]);need(a["bytes"]==e["bytes"] and a["mtime_ns"]==e["mtime_ns"],"Closed export/receipt changed: "+e["path"]);return a
def load(tests,backend):
    tag="upl_material_periodic_shear_"+backend+"_r1";d=tests/"outputs"/(tag+"_native_r1");p=tests/"logs"/(tag+"_native_r1.check.json");r=js(p)
    need(r["passed"] and r["original_native_guards_passed"] and r["consumed_stats_unchanged"],"Native receipt not closed: "+backend)
    consumed=[stat(p)]+[bound(r[k]) for k in ("source_run_check","source_run_call","source_build","reader_call","native_completion")]+[bound(e) for e in r["files"]]
    need(js(r["source_run_check"]["path"])["passed"] and js(r["source_run_call"]["path"])["actual_solver_Win32_exit"]==0 and js(r["reader_call"]["path"])["actual_Popen_wait_exit"]==0,"Actual solver/reader exit not closed")
    done=js(d/"completion.json");need(done["passed"] and done["stage"]=="upl_plastic_periodic_native_r1" and done["input_run_tag"]==tag and done["samples"]==5 and done["total_native_IDs"]==N and done["fixed_IDs"]==0 and done["typed_arrays"]==22,"Native profile scope differs")
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
    x0=np.array([[float(r[k]) for k in ("x0","y0","z0")] for r in ids]);row=np.array([int(r["z_velocity_row"]) for r in ids]);need(np.array_equal(x0,frames[0]["Posd"]) and np.array_equal(np.bincount(row,minlength=32),np.full(32,32)),"Initial material row map differs")
    clocks=table(d/"clocks.csv");history=table(d/"history.csv");need(len(clocks)==len(history)==5,"Five clock/history records required")
    scalar=0.;previous=0
    for i,(c,h) in enumerate(zip(clocks,history)):
        for _ in range(previous,32*i):scalar+=DT
        previous=32*i;need(int(c["completed_step"])==32*i and int(c["saved_step"])==(32*i-1 if i else 0) and int(h["part"])==i and struct.pack("<d",times[i])==struct.pack("<d",scalar)==struct.pack("<d",float(c["time_s"]))==struct.pack("<d",float(h["time_s"])),"Actual saved clock/step differs")
    return {"frames":frames,"times":times,"x0":x0,"row":row,"clocks":clocks,"history":history,"done":done,"consumed":consumed}
def frob(x):return np.sqrt(np.sum(x[:,:3]**2,axis=1)+2*np.sum(x[:,3:]**2,axis=1))
def stress(a):return np.column_stack((a["SigmaState_kk"]-a["PorePress"][:,None],a["SigmaState_ij"]))
def image(x):
    a=x.copy();a[:,(0,2)]-=LENGTH*np.round(a[:,(0,2)]/LENGTH);return a
def run():
    tests=Path(__file__).resolve().parents[1];prefix=tests/"figures/upl_plastic_periodic_pair_r1";paths={k:Path(str(prefix)+s) for k,s in {"metrics":"_metrics.csv","row":"_row_profile.csv","maxima":"_ID_maxima.csv","png":".png","check":".check.json"}.items()}
    need(not any(p.exists() for p in paths.values()),"Existing pair artifacts protected");data={b:load(tests,b) for b in ("CPU","GPU")};a,b=data["CPU"],data["GPU"]
    need(np.array_equal(a["x0"],b["x0"]) and np.array_equal(a["row"],b["row"]) and all(struct.pack("<d",x)==struct.pack("<d",y) for x,y in zip(a["times"],b["times"])),"Same-input initial IDs/coordinates/actual times do not match")
    metrics=[];maxima=[];initial_different=[name for name,_,_ in SCHEMA if a["frames"][0][name].tobytes()!=b["frames"][0][name].tobytes()]
    for part,(fa,fb) in enumerate(zip(a["frames"],b["frames"])):
        r={"part":part,"time_s":a["times"][part],"completed_step":32*part,"CPU_signed_dterror_s":float(a["clocks"][part]["signed_dterror_s"]),"GPU_signed_dterror_s":float(b["clocks"][part]["signed_dterror_s"])}
        differences=[("p","Pa",fb["PorePress"].astype(float)-fa["PorePress"],None),("material_XYZ","mm",1000*image(image(fb["Posd"]-b["x0"])-image(fa["Posd"]-a["x0"])),None),("velocity_XYZ","m_s",fb["Vel"].astype(float)-fa["Vel"],None),("total_sigma","Pa",stress(fb)-stress(fa),frob)]
        for field,key,unit in (("Kplastic","kappa","1"),("PoroVolumeRatio","J","1"),("PoroPorosity","n","1"),("PoroMixtureDensity","rho_mix","kg_m3"),("PoroHydraulicConductivity","k","m_s")):differences.append((key,unit,fb[field].astype(float)-fa[field].astype(float),None))
        for key,unit,delta,norm in differences:
            magnitude=np.abs(delta) if delta.ndim==1 else (norm(delta) if norm else np.linalg.norm(delta,axis=1));r[key+"_difference_RMS_"+unit]=float(np.sqrt(np.mean(magnitude**2)));r[key+"_difference_max_"+unit]=float(magnitude.max());q=int(magnitude.argmax());values=np.atleast_1d(delta[q]).tolist()
            maximum={"part":part,"time_s":a["times"][part],"metric":key,"unit":unit,"RMS":r[key+"_difference_RMS_"+unit],"max_magnitude":float(magnitude[q]),"native_ID_at_max":q}
            for j in range(6):maximum["GPU_minus_CPU_component_"+str(j)]=float(values[j]) if j<len(values) else 0.
            maxima.append(maximum)
        for backend,f in (("CPU",fa),("GPU",fb)):
            r[backend+"_p_RMS_Pa"]=float(np.sqrt(np.mean(f["PorePress"].astype(float)**2)));r[backend+"_kappa_max"]=float(f["Kplastic"].max());r[backend+"_kappa_nonzero_IDs"]=int(np.count_nonzero(f["Kplastic"]));r[backend+"_total_sigma_RMS_Pa"]=float(np.sqrt(np.mean(frob(stress(f))**2)));h=data[backend]["history"][part]
            r[backend+"_history_p_RMS_roundoff_Pa"]=r[backend+"_p_RMS_Pa"]-float(h["p_RMS_Pa"]);r[backend+"_history_total_sigma_RMS_roundoff_Pa"]=r[backend+"_total_sigma_RMS_Pa"]-float(h["total_sigma_Frobenius_RMS_Pa"]);r[backend+"_FS23_count"]=int(np.count_nonzero(np.isin(f["FSType"],(2,3))))
        metrics.append(r)
    profile=[]
    for row in range(32):
        pick=a["row"]==row;r={"initial_z_row":row,"native_IDs":int(pick.sum()),"initial_z_m":float(a["x0"][pick,2].mean())}
        for backend in ("CPU","GPU"):
            x=data[backend]["frames"][-1]["Kplastic"][pick].astype(float)
            for name,v in (("mean",x.mean()),("min",x.min()),("max",x.max()),("std",x.std())):r[backend+"_kappa_"+name]=float(v)
        r["matched_ID_kappa_max_abs_difference"]=float(np.abs(b["frames"][-1]["Kplastic"][pick].astype(float)-a["frames"][-1]["Kplastic"][pick].astype(float)).max());profile.append(r)
    write(paths["metrics"],metrics);write(paths["row"],profile);write(paths["maxima"],maxima)
    fig,axes=plt.subplots(2,2,figsize=(11.8,8.1));time=np.array(a["times"])*1e6;blue,orange="#1565a8","#da7b16"
    for ax,key,scale,title,ylabel in ((axes[0,0],"kappa_max",1.,"Plastic history grows after yield",r"maximum $\kappa$"),(axes[0,1],"p_RMS_Pa",1.,"Pore pressure (all native owners)","pressure RMS (Pa)"),(axes[1,0],"total_sigma_RMS_Pa",.001,"Total stress (Frobenius RMS)","total stress RMS (kPa)")):
        ax.plot(time,[r["CPU_"+key]*scale for r in metrics],color=blue,lw=2,label="CPU");ax.plot(time,[r["GPU_"+key]*scale for r in metrics],color=orange,marker="o",mfc="none",mec=orange,ms=7,ls="none",label="GPU");ax.set(title=title,xlabel="actual saved time (µs)",ylabel=ylabel);ax.grid(alpha=.22)
    ax=axes[1,1];z=[r["initial_z_m"] for r in profile];ax.plot(z,[r["CPU_kappa_mean"] for r in profile],color=blue,lw=1.6);ax.plot(z,[r["GPU_kappa_mean"] for r in profile],color=orange,marker="o",mfc="none",mec=orange,ms=5,ls="none");ax.set(title="Final plastic history by initial z row",xlabel="initial material z (m)",ylabel=r"row mean $\kappa$");ax.grid(alpha=.22)
    axes[0,0].legend(frameon=False);axes[0,1].text(.03,.96,"max matched-ID Δp RMS = %.6g Pa"%max(r["p_difference_RMS_Pa"] for r in metrics),transform=axes[0,1].transAxes,va="top",fontsize=9);axes[1,0].text(.03,.96,"max matched-ID Δσ RMS = %.6g Pa"%max(r["total_sigma_difference_RMS_Pa"] for r in metrics),transform=axes[1,0].transAxes,va="top",fontsize=9)
    fig.suptitle("Constant-strength periodic plastic shear — CPU / GPU, 128 updates",fontsize=14);fig.text(.5,.015,"Five actual saved states; differences are descriptive. No half-step, theory or physical-acceptance claim.\nLines connect CPU samples / raw row means; GPU shows hollow markers. No fitting or smoothing.",ha="center",fontsize=9);fig.tight_layout(rect=(0,.065,1,.95));fig.savefig(paths["png"],dpi=200);plt.close(fig)
    consumed=[e for d in data.values() for e in d["consumed"]];need(all(stat(e["path"])["bytes"]==e["bytes"] and stat(e["path"])["mtime_ns"]==e["mtime_ns"] for e in consumed),"Closed consumed artifacts changed")
    review={"stage":"upl_plastic_periodic_pair_r1","offline_analysis_completed":True,"original_CPU_GPU_native_gates_passed":True,"actual_matched_frames":5,"native_IDs_per_frame":N,"typed_arrays_per_frame":22,"metrics_rows":5,"profile_rows":32,"matched_ID_maxima_rows":len(maxima),"initial_different_array_names_descriptive":initial_different,"maxima_over_five_saved_states":{k:max(r[k] for r in metrics) for k in metrics[0] if "difference_" in k},"input_receipts_and_exports":consumed,"output_artifacts":[stat(p) for k,p in paths.items() if k!="check"],"figure_visual_QA_pending":True,"new_numerical_gate":False,"source_build_solver_decoder_Git_SHA_actions":0,"physical_acceptance":False}
    with paths["check"].open("x",encoding="utf-8") as f:json.dump(review,f,indent=2,allow_nan=False);f.write("\n")
    print(json.dumps({"offline_analysis_completed":True,"maxima":review["maxima_over_five_saved_states"],"initial_different_arrays":initial_different}),flush=True)
if __name__=="__main__":run()
