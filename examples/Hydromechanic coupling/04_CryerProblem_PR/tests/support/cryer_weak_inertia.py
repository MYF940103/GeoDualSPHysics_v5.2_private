"""Keep all physical force/flux matrices fixed; compare only the radial inertial mass."""
import os
for v in ("OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","OMP_NUM_THREADS"):os.environ[v]="1"
import json
import numpy as np
import pandas as pd
from cryer_weak_flux_shell import assemble,Phase,march
from cryer_coupled_shell_modes import RHO,DT,T

TAG="cryer_weak_inertia_r1"


def require(c,msg):
    if not c:raise ValueError(msg)


def relative(a,b):
    return float(np.linalg.norm(a-b)/np.linalg.norm(b))


def dense(ops,method):
    close,o=Phase(ops,False),Phase(ops,True)
    y=np.zeros(41)
    for step in range(1,4097):
        y[-1]=10000.*min((step-1)/2048.,1.)
        y=getattr(close,method)@y
    saved=[]
    for i in range(2433):
        if i:y=getattr(o,method)@y
        p=o.measure(y)[0]
        saved.append((i, i*DT, p[0],p[16],p[17],-1000*y[19]))
    return pd.DataFrame(saved,columns=["open_step","tau_s","center_Pa","p17_Pa","p18_Pa","surface_mm"])


def main():
    base=T/"figures";check=T/"logs"/(TAG+".check.json")
    hc,sc,nc,oc,fc=[base/(TAG+suffix) for suffix in ("_history.csv","_material.csv","_profiles.csv","_startup.csv",".png")]
    if any(f.exists() for f in [check,hc,sc,nc,oc,fc]):raise FileExistsError(TAG)
    ref=pd.read_csv(base/"cryer_p3_server_peak_actual_r1/physical/native_and_theory.csv")
    actual=pd.read_csv(base/"cryer_true_surface_old_r1.csv")
    raw=assemble();Ks,ext,K,G,P,F,old,w,quality=raw
    with np.load(T/"outputs/cryer_tet_reference_r1.npz") as geo:
        s=geo["material_shell"];n=len(s);nodemass=geo["native_mass_kg"];nativevol=geo["native_volume_m3"]
        dual=np.bincount(geo["tets"].ravel(),weights=np.repeat(geo["Ve"]/4,4),minlength=n)
        areas=geo["face_area_out"];xc=geo["x0"][geo["faces"]].mean(axis=1)
    mass2=RHO*w
    require(np.allclose(np.bincount(s,weights=nodemass)[1:],old,rtol=1e-12,atol=1e-16)
            and np.allclose(np.bincount(s,weights=dual)[1:],w,rtol=1e-12,atol=1e-16),"Initial shell masses/volumes")
    # Recover physical stiffness and external force before mapping them back to acceleration.
    FK=old[:,None]*Ks;Fe=old*ext
    Ks2=FK/mass2[:,None];ext2=Fe/mass2;P2=G/mass2[:,None]
    ops2=(Ks2,ext2,K,G,P2,F,mass2,w,quality)
    force_id={"elastic_relative":relative(mass2[:,None]*Ks2,FK),"external_relative":relative(mass2*ext2,Fe),
              "pore_relative":relative(mass2[:,None]*P2,old[:,None]*P),
              "stiffness_self_adjoint":relative(FK,FK.T)}
    require(max(force_id.values())<3e-12,"Physical force matrix invariance")
    # Full geometric and native affine work of all nine x_i n_j entries, not fitted to a pressure curve.
    face_work=xc.T@areas;V=float(dual.sum());V0=float(nativevol.sum())
    ga=relative(face_work,V*np.eye(3));oldgap=relative(V0*np.eye(3),face_work)
    require(ga<3e-12 and .10<oldgap<.12,"Positive volume/work contradiction")
    mats=[]
    for j in range(1,21):
        mask=s==j;eff=nodemass[mask]/dual[mask]
        mats.append(dict(shell=j,ids=int(mask.sum()),geometric_volume_m3=w[j-1],
            native_initial_volume_m3=nativevol[mask].sum(),native_total_mass_kg=old[j-1],
            dual_total_mass_kg=mass2[j-1],native_mass_over_geometric_shell_volume_kg_m3=old[j-1]/w[j-1],
            native_per_point_effective_density_min_kg_m3=eff.min(),native_per_point_effective_density_max_kg_m3=eff.max(),
            candidate_mass_over_geometric_volume_kg_m3=mass2[j-1]/w[j-1],
            native_ledger_density_kg_m3=RHO))
    hist=[];prof=[];den=[];results={};reference=base/"cryer_weak_flux_shell_r1"
    olds=pd.read_csv(str(reference)+"_history.csv");oldprof=pd.read_csv(str(reference)+"_profiles.csv")
    receipt=json.loads((T/"logs/cryer_weak_flux_shell_r1.check.json").read_text())
    for lab,ops in (("native_mass",raw),("geometric_mass",ops2)):
        results[lab]={}
        for method in ("map","mid"):
            if lab=="native_mass":
                tab=olds[olds.method==method].copy();pr=oldprof[oldprof.method==method].copy()
                res=receipt[method].copy()
            else:
                tab,pr,res=march(method,ops,ref);pr=pd.DataFrame(pr)
            tab["inertia"]=lab;pr["inertia"]=lab;hist.append(tab);prof.append(pr)
            e=dense(ops,method);e["method"]=method;e["inertia"]=lab;den.append(e)
            ix=e[(e.open_step>0)&(e.open_step%64==0)&(e.tau_s<.004638671875)]
            dcmp=tab.merge(actual[["completed_step","surface_mm"]],left_on="step",right_on="completed_step")
            wcmp=dcmp[dcmp.tau_s>=.004638671875];diff=wcmp.surface_inward_mm-wcmp.surface_mm
            at=dcmp.loc[dcmp.step==4160].iloc[0];end=dcmp.iloc[-1]
            res.update(opening_saved_64_surface_mm=float(at.surface_inward_mm),opening_saved_64_native_surface_mm=float(at.surface_mm),
                       end_surface_mm=float(end.surface_inward_mm),end_native_surface_mm=float(end.surface_mm),
                       mandel_surface_vs_native_RMS_mm=float(np.sqrt(np.mean(diff**2))),
                       mandel_surface_vs_native_max_mm=float(max(abs(diff))),
                       dense_early_min_Pa=float(e.center_Pa[1:].min()),dense_early_max_Pa=float(e.center_Pa[1:].max()),
                       early_saved_min_Pa=float(ix.center_Pa.min()),early_saved_max_Pa=float(ix.center_Pa.max()),
                       right_limit_Pa=float(e.center_Pa[0]),
                       min_early_radius_pressure_step=int(e.loc[e.center_Pa[1:].idxmin(),"open_step"]),
                       max_early_radius_pressure_step=int(e.loc[e.center_Pa[1:].idxmax(),"open_step"]))
            results[lab][method]=res
    data=pd.concat(hist,ignore_index=True);sm=pd.DataFrame(mats);df=pd.concat(den,ignore_index=True);pf=pd.concat(prof)
    df[["inertia","method","open_step","tau_s","center_Pa","p17_Pa","p18_Pa","surface_mm"]].to_csv(oc,index=False)
    data.to_csv(hc,index=False);sm.to_csv(sc,index=False);pf.to_csv(nc,index=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    f,axes=plt.subplots(2,2,figsize=(11,7),layout="constrained")
    for name,color,label in [("native_mass","#a7551d","Native equal masses"),("geometric_mass","#1c668b","Geometric inertial masses")]:
        e=df[(df.inertia==name)&(df.method=="map")&(df.open_step>0)]
        tab=data[(data.inertia==name)&(data.method=="map")&(data.step>=4096)]
        axes[0,0].plot(e.tau_s*1e6,e.center_Pa/1e3,color=color,label=label)
        tail=tab.tau_s>=.004638671875
        axes[0,1].plot(tab.tau_s[tail]*1e3,tab.center_Pa[tail]/1e3,color=color,label=label)
        axes[1,0].plot(tab.tau_s*1e3,tab.surface_inward_mm,color=color,label=label)
    rr=ref[ref.completed_step>4096];keep=rr.legacy_Tv>=.005
    axes[0,0].scatter(rr.tau_s*1e6,rr.center18_Pa/1e3,s=12,color="black",label="Saved original P3",zorder=3)
    axes[0,0].set(xlim=(0,500),xlabel="Time after opening (µs)",ylabel="Center pressure (kPa)")
    axes[0,1].plot(rr.tau_s[keep]*1e3,rr.M0_r18_Pa[keep]/1e3,":",color="black",label="M0 reference")
    axes[0,1].set(xlabel="Time after opening (ms)",ylabel="Mandel-window center pressure (kPa)")
    aa=actual[actual.completed_step>=4096]
    axes[1,0].plot(aa.tau_s*1e3,aa.surface_mm,":",color="black",label="Saved original surface (5,153 IDs)")
    axes[1,0].set(xlabel="Time after opening (ms)",ylabel="Surface inward motion (mm)")
    axes[1,1].plot(sm.shell,sm.native_mass_over_geometric_shell_volume_kg_m3,"o-",ms=3,color="#a7551d",label="Native mass / shell volume")
    axes[1,1].axhline(RHO,color="#1c668b",label="Geometric mass / shell volume")
    axes[1,1].set(xlabel="Initial shell index",ylabel="Inertia per geometric volume (kg/m³)",xticks=[1,5,10,15,20])
    for a in axes.flat:a.grid(alpha=.2);a.legend(fontsize=8)
    f.savefig(fc,dpi=155);plt.close(f)
    results.update(density_kg_m3=RHO,native_total_mass_kg=float(old.sum()),geometric_total_mass_kg=float(mass2.sum()),
       volume_geo_m3=V,volume_native_m3=V0,affine_geometric_relative=ga,affine_native_ledger_relative=oldgap,
       all_nine_geometric_trace_m3=face_work.tolist(),surface_work_10kPa_unit_affine=-3e4*V,
       old_ledger_dilatation_work_10kPa_unit_affine=-3e4*V0,force_invariance=force_id,
       scope="Cold ramp/hold/drain, instantaneous M0 weak Darcy, frozen 20-shell geometry. Only solid inertial mass changed. Uniform initial physical mixture density and old ledger are not overwritten.",
       solver_runs=0)
    check.write_text(json.dumps(results,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"mass":[old.sum(),mass2.sum()],"affine":oldgap,"new":results["geometric_mass"]["map"]}))


if __name__=="__main__":main()

