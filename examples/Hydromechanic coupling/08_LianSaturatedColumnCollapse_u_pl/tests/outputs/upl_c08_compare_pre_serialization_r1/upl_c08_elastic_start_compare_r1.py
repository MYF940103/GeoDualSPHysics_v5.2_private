"""Closed C08 startup exports only; descriptive CPU/GPU comparison, no solver/decoder."""
import os
for _key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS"):
    os.environ[_key]="1"
import csv,json,pathlib,struct,ctypes
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
if os.name=="nt":
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(),0x4000)
T=pathlib.Path(__file__).resolve().parents[1]
TAG="upl_c08_elastic_start_compare_r1"
PREFIX=T/"figures"/TAG
CHECK=T/"logs"/(TAG+".check.json")
OBS={}
def need(ok,message):
    if not ok: raise RuntimeError(message)
def stat(path):
    path=pathlib.Path(path);s=path.stat()
    return dict(path=str(path.resolve()),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def observe(entry):
    need(stat(entry["path"])==entry,"Changed consumed SMT: "+entry["path"])
    OBS[entry["path"]]=entry
    return pathlib.Path(entry["path"])
def current(path): return observe(stat(path))
def read_json(path): return json.loads(current(path).read_text(encoding="utf-8"))
def read_csv(path):
    with current(path).open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def write_csv(path,rows):
    with path.open("x",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def load(backend):
    label="upl_c08_elastic_start_"+backend+"_r2_native_r1";out=T/"outputs"/label
    receipt=read_json(T/"logs"/(label+".check.json"))
    need(receipt["stage"]==label and receipt["passed"] and receipt["original_native_guards_passed"] and receipt["consumed_stats_unchanged"],backend+" original native review is not passed")
    need([receipt[k] for k in ("samples","completed_steps","last_saved_step","total_native_IDs","typed_arrays")]==[5,128,127,7060,22],backend+" native scope differs")
    leaves={pathlib.Path(e["path"]).name:e for e in receipt["outputs"]}
    for name in ("typed22.bin","typed22_layout.csv","clocks.csv","native_ids.csv","history.csv","completion.json"):
        need(pathlib.Path(leaves[name]["path"]).resolve()==(out/name).resolve(),"Receipt output path differs")
        observe(leaves[name])
    completion=read_json(out/"completion.json")
    need(completion["stage"]=="upl_c08_elastic_start_native_r1" and completion["passed"] and completion["input_run_tag"]=="upl_c08_elastic_start_"+backend+"_r2" and completion["backend_argument"]==backend,backend+" completion identity differs")
    call=read_json(observe(receipt["reader_call"]))
    need(type(call["exit_code"]) is int and call["exit_code"]==0 and call["actual_Popen_wait"],backend+" reader did not exit0")
    clocks=read_csv(out/"clocks.csv");layout=read_csv(out/"typed22_layout.csv");ids=read_csv(out/"native_ids.csv");history=read_csv(out/"history.csv")
    need(len(clocks)==5 and len(layout)==22 and len(ids)==7060 and len(history)==25,"Export lengths differ")
    need([int(r["id"]) for r in ids]==list(range(7060)) and [r["is_fixed"] for r in ids]==["1"]*2060+["0"]*5000,"Material ID partition differs")
    x0=np.array([[float(r[k]) for k in ("x0","y0","z0")] for r in ids])
    payload=current(out/"typed22.bin").read_bytes()
    need(len(payload)==7483652 and struct.unpack_from("<III",payload)==(7060,22,5),"Original typed payload/header differs")
    offset=12;frames=[]
    for part in range(5):
        time,=struct.unpack_from("<d",payload,offset);offset+=8;r=clocks[part]
        need(struct.pack("<d",time)==struct.pack("<d",float(r["time_s"])) and int(r["part"])==part and int(r["completed_step"])==32*part and int(r["saved_step"])==(32*part-1 if part else 0),"Actual clock/step association differs")
        a={}
        for field in layout:
            count=int(field["components"]);dtype={"uint32":"<u4","float32":"<f4","float64":"<f8"}[field["type"]]
            need(int(field["bytes_per_particle"])==np.dtype(dtype).itemsize*count,"Typed layout width differs")
            v=np.frombuffer(payload,dtype=dtype,count=7060*count,offset=offset).reshape(7060,count);offset+=7060*int(field["bytes_per_particle"])
            a[field["array"]]=v[:,0] if count==1 else v
        need(np.array_equal(a["Idp"],np.arange(7060)),"Typed native IDs differ")
        frames.append(a)
    need(offset==len(payload),"Trailing typed payload")
    hist={(int(r["part"]),r["initial_material_band"]):r for r in history}
    need(len(hist)==25,"Repeated history band")
    return dict(frames=frames,clocks=clocks,x0=x0,history=hist,layout=layout,receipt=current(T/"logs"/(label+".check.json")))
def main():
    outputs=[PREFIX.with_suffix(".csv"),PREFIX.with_name(TAG+".history.csv"),PREFIX.with_suffix(".png")]
    need(not any(p.exists() for p in outputs+[CHECK]),"Fresh comparison outputs required")
    current(__file__);cpu=load("CPU");gpu=load("GPU");soil=slice(2060,7060)
    need(cpu["layout"]==gpu["layout"] and cpu["x0"].tobytes()==gpu["x0"].tobytes(),"Typed schema or initial material coordinates differ")
    need(np.array_equal(cpu["frames"][0]["Posd"],cpu["x0"]) and np.array_equal(gpu["frames"][0]["Posd"],gpu["x0"]),"Initial coordinate association differs")
    metrics=[];bands=[];times=[]
    for part,(c,g) in enumerate(zip(cpu["frames"],gpu["frames"])):
        tc=float(cpu["clocks"][part]["time_s"]);tg=float(gpu["clocks"][part]["time_s"])
        need(struct.pack("<d",tc)==struct.pack("<d",tg),"CPU/GPU actual saved times differ")
        times.append(tc);cp=c["PorePress"][soil].astype(float);gp=g["PorePress"][soil].astype(float);dp=gp-cp
        cu=c["Posd"][soil]-cpu["x0"][soil];gu=g["Posd"][soil]-gpu["x0"][soil]
        du=np.linalg.norm(gu-cu,axis=1)
        # Sigma_ij order is xy,yz,xz; total sigma = effective sigma - p I.
        dd=(g["SigmaState_kk"][soil]-gp[:,None])-(c["SigmaState_kk"][soil]-cp[:,None])
        ds=g["SigmaState_ij"][soil]-c["SigmaState_ij"][soil]
        total2=np.sum(dd*dd,axis=1)+2*np.sum(ds*ds,axis=1)
        row=dict(part=part,time_s=tc,soil_IDs=5000,p_GPU_minus_CPU_RMS_Pa=float(np.sqrt(np.mean(dp*dp))),p_GPU_minus_CPU_maxabs_Pa=float(np.max(np.abs(dp))),XYZ_material_displacement_difference_max_m=float(np.max(du)),sigma_total_difference_Frobenius_RMS_Pa=float(np.sqrt(np.mean(total2))))
        for name,key,unit in (("J","PoroVolumeRatio",""),("n","PoroPorosity",""),("rho","PoroMixtureDensity","_kg_m3"),("k","PoroHydraulicConductivity","_m_s")):
            d=g[key][soil]-c[key][soil];row[name+"_difference_RMS"+unit]=float(np.sqrt(np.mean(d*d)));row[name+"_difference_maxabs"+unit]=float(np.max(np.abs(d)))
        need(all(np.isfinite(x) for x in row.values()),"Nonfinite descriptive difference");metrics.append(row)
        for band in ("all","top_2h","bottom_2h","left_2h","right_2h"):
            ch=cpu["history"][part,band];gh=gpu["history"][part,band]
            need(int(ch["count"])==int(gh["count"]) and float(ch["time_s"])==tc and float(gh["time_s"])==tg,"History material/time association differs")
            bands.append(dict(part=part,time_s=tc,initial_material_band=band,count=int(ch["count"]),CPU_p_mean_Pa=float(ch["p_mean_Pa"]),GPU_p_mean_Pa=float(gh["p_mean_Pa"]),CPU_downward_material_settlement_um=-1e6*float(ch["mean_dz_m"]),GPU_downward_material_settlement_um=-1e6*float(gh["mean_dz_m"])))
    write_csv(outputs[0],metrics);write_csv(outputs[1],bands)
    plt.rcParams.update({"font.size":10,"axes.grid":True,"grid.alpha":.25})
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout="constrained")
    for band,color in (("all","black"),("top_2h","tab:blue"),("bottom_2h","tab:orange")):
        values=[r for r in bands if r["initial_material_band"]==band]
        for backend,marker,style in (("CPU","o","-"),("GPU","x","--")):
            axes[0,0].plot(np.array(times)*1e3,[r[backend+"_p_mean_Pa"] for r in values],style,marker=marker,color=color,markersize=4,label=backend+" "+band)
            axes[0,1].plot(np.array(times)*1e3,[r[backend+"_downward_material_settlement_um"] for r in values],style,marker=marker,color=color,markersize=4,label=backend+" "+band)
    axes[0,0].set(xlabel="Actual saved time [ms]",ylabel="Arithmetic mean pore pressure [Pa]",title="Initial-material band pressure")
    axes[0,1].set(xlabel="Actual saved time [ms]",ylabel="Mean material settlement [um], downward +",title="Initial-material band displacement")
    for ax in axes[0]:ax.legend(ncol=2,fontsize=8)
    c=cpu["frames"][-1];g=gpu["frames"][-1];xyz=c["Posd"][soil];p=c["PorePress"][soil];d=g["PorePress"][soil].astype(float)-p
    v=axes[1,0].scatter(xyz[:,0],xyz[:,2],c=p,s=7,cmap="viridis",linewidths=0)
    fig.colorbar(v,ax=axes[1,0],label="CPU pore pressure [Pa]")
    span=float(np.max(np.abs(d)));span=span if span else 1.
    v=axes[1,1].scatter(xyz[:,0],xyz[:,2],c=d,s=7,cmap="coolwarm",vmin=-span,vmax=span,linewidths=0)
    fig.colorbar(v,ax=axes[1,1],label="GPU - CPU pressure [Pa]")
    axes[1,0].set_title("CPU final native field: all 5000 soil IDs")
    axes[1,1].set_title("ID-paired final difference on CPU native coordinates")
    for ax in axes[1]:ax.set(xlabel="CPU actual x [m]",ylabel="CPU actual z [m]",aspect="equal");ax.grid(False)
    fig.suptitle("C08 elastic gravity startup: 128 updates, 0..0.48828125 ms\nDescriptive CPU/GPU comparison; NoDrain is not an explicit closed-normal-flux condition",fontsize=12)
    with outputs[2].open("xb") as f:fig.savefig(f,format="png",dpi=160)
    plt.close(fig)
    need(all(stat(e["path"])==e for e in OBS.values()),"Consumed SMT changed during comparison")
    with CHECK.open("x",encoding="utf-8") as f:
        json.dump(dict(stage=TAG,passed=True,scope="Offline descriptive comparison only; no cross-backend accuracy gate, fit, interpolation, FSNormal bit gate or physical acceptance.",source_receipts=[cpu["receipt"],gpu["receipt"]],actual_times_s=times,paired_soil_IDs_per_frame=5000,metrics=metrics,consumed=list(OBS.values()),consumed_stats_unchanged=True,outputs=[stat(p) for p in outputs],SHA_scans=0,physical_acceptance=False),f,indent=2);f.write("\n")
if __name__=="__main__":main()
