"""Mechanical and volume handoff audit on two retained Cryer P3 particle states."""
import os
for key in ("OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","OMP_NUM_THREADS"):
    os.environ[key]="1"
import json
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from cryer_tet_weak_force import geometry, internal, external
from cryer_p3_peak_shells import ordered
from cryer_peak_momentum_shadow import apply_symmetric
from cryer_p3_verify_r1 import N0, RHO0
from cryer_shell_equilibrium import TESTS, Q, need


def norm(a):
    return np.linalg.norm(a,axis=1)


def rms(a):
    a=np.asarray(a)
    return float(np.sqrt(np.mean(np.sum(a*a,axis=-1) if a.ndim>1 else a*a)))


def original(st):
    """Raw pair forces and the current-geometry corrected velocity divergence."""
    x=st["Posd"];v=st["Vel"].astype(float);vol=st["PoroCurrentVolume"]
    sk=st["SigmaState_kk"].astype("f4").astype(float);sh=st["SigmaState_ij"].astype("f4").astype(float)
    p=st["PorePress"].astype(float);n=len(p)
    h=float(np.float32(.0045)); pairs=cKDTree(x).query_pairs(2*h,output_type="ndarray")
    f=np.zeros_like(x); ext=np.zeros_like(x);moment=np.zeros((n,3,3));slope=np.zeros_like(moment)
    for start in range(0,len(pairs),65536):
        i,j=pairs[start:start+65536].T
        d=x[i]-x[j]; w=float(np.float32(-2.08891/h**4))/h*(1-norm(d)/(2*h))**3
        g=w[:,None]*d
        gp=g*(vol[i]*vol[j])[:,None]
        load=2*Q*gp
        force=apply_symmetric(sk[i]+sk[j],sh[i]+sh[j],gp)+(2*Q-p[i]-p[j])[:,None]*gp
        dv=v[j]-v[i]
        for b in range(3):
            def bin_pair(ij,ji):
                return np.bincount(i,ij,minlength=n)+np.bincount(j,ji,minlength=n)
            f[:,b]+=bin_pair(force[:,b],-force[:,b]);ext[:,b]+=bin_pair(load[:,b],-load[:,b])
            for a in range(3):
                m=-d[:,a]*g[:,b]
                sv=dv[:,a]*g[:,b]
                moment[:,a,b]+=bin_pair(m*vol[j],m*vol[i]);slope[:,a,b]+=bin_pair(sv*vol[j],sv*vol[i])
    theta=np.einsum("nij,nij->n",slope,np.linalg.inv(moment))
    return f,ext,theta,len(pairs)


def main():
    tag="cryer_tet_handoff_r1"
    figures=TESTS/"figures"
    receipt=TESTS/"logs"/(tag+".check.json")
    outputs=[figures/(tag+s) for s in ("_regions.csv","_shells.csv",".png")]
    need(not any(p.exists() for p in [*outputs,receipt]),"Use fresh audit paths")
    name="CaseCryer_TPI_P3_nu030_peak_r1_GPU_out"
    native=TESTS/"outputs"/name/name/"data"
    cache=np.load(TESTS/"outputs/cryer_tet_reference_r1.npz")
    shell=cache["material_shell"];t=cache["tets"];faces=cache["faces"]
    x0=cache["x0"];v0=cache["native_volume_m3"];n=len(shell)
    need(np.array_equal(cache["native_ids"],np.arange(8,37181)),"Original material IDs")
    vol_ref=cache["Ve"]
    geom_sign=np.sign(np.linalg.det(x0[t[:,1:]]-x0[t[:,:1]]))
    dual0=np.bincount(t.ravel(),np.repeat(vol_ref/4,4),minlength=n)
    hist=pd.read_csv(figures/"cryer_p3_server_peak_actual_r1/physical/native_and_theory.csv",float_precision="round_trip")
    info=[];regions=[];profiles=[]
    for part in (64,65):
        st=ordered(native,part,["Posd","PorePress","PoroCurrentVolume","PoroMixtureDensity","SigmaState_kk",
                  "SigmaState_ij","HydroMechLoadAce","FSType","PoroVolumeRatio","PoroPorosity","PoroThetaLastStage","Vel"])
        x=st["Posd"];vel=st["Vel"].astype(float);volume=st["PoroCurrentVolume"];rho=st["PoroMixtureDensity"]
        mass=volume*rho;p=st["PorePress"].astype(float);J=st["PoroVolumeRatio"];por=st["PoroPorosity"]
        saved=hist.iloc[part]
        need(saved.completed_step==64*part and saved.tau_s==(part-64)*2**-13,"Confirmed native scalar clock")
        need(abs(p[shell==1].mean()-saved.center18_Pa)<1e-8 and np.array_equal(np.flatnonzero(np.isin(st["FSType"],(2,3))),cache["native_surface"]),"P3 center and surface")
        need(int(saved.active_drain_count)==(5153 if part==65 else 0) and (part==64 or np.all(p[shell==20]==0)),"True surface clock/drainage")
        need(np.max(abs(volume-v0*J))<1e-19 and np.max(abs(por-(1-(1-N0)/J)))<1e-14
             and np.max(abs(rho-(1000+(RHO0-1000)/J)))<1e-10,"Retain native volume/porosity/mixture ledger")
        ve,g,av,sign=geometry(x,t,faces)
        need(np.array_equal(sign,geom_sign),"Positive reference-mapped orientation")
        dual=np.bincount(t.ravel(),np.repeat(ve/4,4),minlength=n);jgeom=dual/dual0
        normal=x/np.linalg.norm(x,axis=1)[:,None]
        sk=st["SigmaState_kk"];sh=st["SigmaState_ij"]
        eff=np.zeros((n,3,3))
        for a in range(3):eff[:,a,a]=sk[:,a]
        for j,(a,b) in enumerate(((0,1),(1,2),(0,2))):eff[:,a,b]=eff[:,b,a]=sh[:,j]
        total=eff-p[:,None,None]*np.eye(3)
        # Reference +/- the uniform traction belongs to the original physical outer material faces.
        node_load=external(faces,-Q*np.eye(3),av,n)
        weak=internal(total[t].mean(axis=1),t,g,n)+node_load
        reduced_precision=(eff.astype("f4").astype(float)-p[:,None,None]*np.eye(3))
        weak_f32=internal(reduced_precision[t].mean(axis=1),t,g,n)+node_load
        base,base_load,theta_raw,pairs=original(st)
        current_load=st["HydroMechLoadAce"].astype(float)*mass[:,None]
        face_area=norm(av);fn=av/face_area[:,None]
        traction=np.einsum("nij,nj->ni",total[faces].mean(axis=1),fn)
        mismatch=traction+Q*fn
        face_r=np.sum(mismatch*fn,axis=1)
        face_t=mismatch-face_r[:,None]*fn
        tr_rms=np.sqrt(np.average(norm(mismatch)**2,weights=face_area))
        theta_cell=np.einsum("nac,nac->n",vel[t],g)/ve
        theta_weak=np.bincount(t.ravel(),np.repeat(ve*theta_cell/4,4),minlength=n)/dual
        state_work=-float(np.sum(np.einsum("tij,tai,taj->t",total[t].mean(axis=1),vel[t],g)))
        need(abs(state_work-np.sum((weak-node_load)*vel))<3e-12 and np.linalg.norm(weak.sum(axis=0))<1e-10
             and np.linalg.norm(np.cross(x,weak).sum(axis=0))<1e-11,"Face and independent stress work and balances")
        need(abs(ve.sum()-np.sum(av*x[faces].mean(axis=1))/3)<1e-14,"Transformed volume from oriented surface")
        ag_geom=(weak/mass[:,None]);ag_base=(base/mass[:,None])
        for label,mask in [("center18",shell==1),("inner10",shell<=10),("all",shell>0),("surface",shell==20)]+[(f"shell_{j}",shell==j) for j in range(1,21)]:
            row=dict(part=part,tau_s=saved.tau_s,completed_step=int(saved.completed_step),region=label,ids=int(mask.sum()),
                     native_pressure_mean_Pa=p[mask].mean(),total_minus_prescribed_rms_Pa=rms((total[mask]+Q*np.eye(3)).reshape(-1,9)),
                     speed_rms_m_s=rms(vel[mask]),native_J_minus1_mean=float((J[mask]-1).mean()),
                     geometry_J_minus1_mean=float((jgeom[mask]-1).mean()),geometry_minus_native_J_rms=rms(jgeom[mask]-J[mask]),
                     geometry_minus_native_J_max=float(np.max(abs(jgeom[mask]-J[mask]))),
                     raw_weak_accel_change_rms_m_s2=rms((ag_geom-ag_base)[mask]),
                     raw_weak_theta_change_rms_s_inv=rms((theta_weak-theta_raw)[mask]),
                     weak_native_load_delta_rms_m_s2=rms(((node_load-current_load)/mass[:,None])[mask]))
            for key,f,theta,load in (("original",ag_base,theta_raw,base_load),("candidate",ag_geom,theta_weak,node_load)):
                ri=np.einsum("ij,ij->i",f,-normal)
                row.update({key+"_accel_rms_m_s2":rms(f[mask]),key+"_accel_absmax_m_s2":float(norm(f[mask]).max()),
                            key+"_mean_inward_m_s2":ri[mask].mean(),key+"_tangent_rms_m_s2":rms((f+normal*ri[:,None])[mask]),
                            key+"_div_v_rms_s_inv":rms(theta[mask]),key+"_inward_load_N":float(np.sum(-normal[mask]*load[mask]))})
            if label.startswith("shell_"):profiles.append(dict(row,r_over_a=int(label.split("_")[1])/20))
            else:regions.append(row)
        input_force=[]
        for label,f in (("native_saved_load_with_saved_J_mass",current_load),("raw_reconstructed_load",base_load),("P1_geometric_traction",node_load),("raw_total",base),("P1_total",weak)):
            input_force.append(dict(name=label,net_force_N=f.sum(axis=0).tolist(),net_torque_Nm=np.cross(x,f).sum(axis=0).tolist(),
                               inward_N=float(np.sum(-normal*f)),inward_at_true_surface_N=float(np.sum((-normal*f)[shell==20])),
                               dilatation_work_Nm=float(np.sum(f*x))))
        info.append(dict(part=part,time_s=saved.time_s,completed_step=int(saved.completed_step),tau_s=saved.tau_s,
                    active_receivers=int(saved.active_drain_count),pairs=pairs,total_materials=n,faces=len(faces),
                    applied_surface_area_m2=face_area.sum(),uniform_traction_q_times_area_N=float(Q*face_area.sum()),
                    face_total_traction_residual_rms_Pa=float(tr_rms),face_normal_residual_rms_Pa=float(np.sqrt(np.average(face_r**2,weights=face_area))),
                    face_tangent_residual_rms_Pa=float(np.sqrt(np.average(norm(face_t)**2,weights=face_area))),
                    candidate_saved_double_vs_float_stress_force_rms_m_s2=rms((weak-weak_f32)/mass[:,None]),
                    reconstructed_vs_saved_load_rms_m_s2=rms((base_load-current_load)/mass[:,None]),
                    saved_load_rms_m_s2=rms(current_load/mass[:,None]),net_and_inward_forces=input_force,
                    volume_geom_m3=ve.sum(),volume_native_m3=volume.sum(),native_div_geom_volume_ratio=volume.sum()/ve.sum(),
                    volume_native_ratio_over_initial=float(volume.sum()/v0.sum()),volume_geom_ratio_over_initial=float(ve.sum()/vol_ref.sum()),
                    nodal_init_geometry_over_native_volume_quantiles=np.quantile(dual0/v0,[0,.5,1]).tolist(),
                    candidate_internal_force_velocity_power_W=state_work,
                    native_PoroThetaLastStage_is_previous_substage=True,
                    velocity_current_not_stage_equality_required=True))
    df=pd.DataFrame(regions);layers=pd.DataFrame(profiles)
    df.to_csv(outputs[0],index=False);layers.to_csv(outputs[1],index=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(1,3,figsize=(13,4),layout="constrained")
    for k,part in enumerate((64,65)):
        tab=layers[layers.part==part]
        for col,style,label in [("original","o-","Original pair force"),("candidate","x--","Paired nodal force")]:
            ax[k].plot(tab.r_over_a,tab[col+"_accel_rms_m_s2"],style,ms=4,label=label)
        ax[k].set_yscale("log");ax[k].set_title(f"Part {part}, completed step {part*64}")
        ax[k].set_ylabel("Stress + pressure + load RMS (m/s²)");ax[k].legend(fontsize=8)
        ax[2].plot(tab.r_over_a,100*tab.geometry_minus_native_J_rms,label=f"Part {part}")
    ax[2].set_yscale("log");ax[2].set_ylabel("Geometric minus native J RMS (%)");ax[2].legend(fontsize=8)
    for a in ax:a.set_xlabel("Initial material radius / sphere radius");a.grid(alpha=.2)
    fig.savefig(outputs[2],dpi=150);plt.close(fig)
    receipt.write_text(json.dumps(dict(frames=info,new_sph_runs=0,changed_native_states=0,
                    model="same saved p and all six effective stresses; actual mapped faces, original native inertia; Darcy unchanged and not reevaluated",
                    force_scope="No artificial viscosity, damping, reconstructing or reversing an unsaved integration stage"),
                    indent=2,allow_nan=False)+"\n",encoding="utf8")
    print(df[["part","region","original_accel_rms_m_s2","candidate_accel_rms_m_s2","geometry_minus_native_J_rms"]].to_string(index=False))


if __name__=="__main__":
    main()
