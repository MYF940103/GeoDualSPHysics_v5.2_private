"""Separate exact sources of the finite-storage pressure pulse and check the drained pressure subspace."""
import json
import numpy as np
import pandas as pd
from scipy.linalg import expm

from cryer_shell_ramp_open import T, Q, DT, TR, HYD, RHOW, N0, Phase, march

TAG="cryer_shell_opening_channels_r1"


def prepare(B,C,name,strict):
    # Both discretizations approach the same material domain yet use different force and scalar projections.
    BC={k:B[k].copy() for k in B};CC={k:C[k].copy() for k in C}
    if strict:
        for accel,block,affine in [("DK","K","Ku"),("DP","P","P"),("DF","F","F")]:
            BC[accel]=B["D"]@B[block]
            CC[name+"_"+affine]=C[name+"_vel"]@B[block]
    return BC,CC


def channels(B,C,name,strict,ref):
    B,C=prepare(B,C,name,strict)
    M=N0/2e8
    c=Phase(B,C,name,M,True);o=Phase(B,C,name,M,False)
    # Independent exact affine map for q held at source n. No uniform preload substituted.
    n=len(c.f);aug=np.eye(n+2)
    aug[:n,:n]=c.E;aug[:n,n]=c.g;aug[n,n+1]=DT/TR
    ramp=(np.linalg.matrix_power(aug,2048)@np.r_[np.zeros(n),0.,1.])[:n]
    y=c.direct(ramp,1.,0.,TR); ps=c.pressure(y,1)[-1];y0=y[:-1]
    # Per-unit-q state derivatives. Remove column of drained surface pressure only.
    raw=np.zeros((len(y0),4));raw[:,0]=(c.a@y+c.f)[:-1]
    raw[20:40,1]=-B["P"][:,-1]*ps/o.units[20:40]
    raw[40:,2]=-HYD*B["La"][:-1,-1]*ps/M
    raw[40:,3]=-HYD*RHOW*B["DP"][:-1,-1]*ps/M
    b0=o.a@y0+o.f
    residual=np.max(abs(b0-raw.sum(axis=1)))/max(1,np.max(abs(b0)))
    if residual>3e-11:raise ValueError("Opening split")
    H=np.zeros((len(y0)+4,len(y0)+4));H[:len(y0),:len(y0)]=o.a;H[:len(y0),len(y0):]=raw
    hist=[]
    for step in [1,2,4,8,16,32,60,63,64,128,192,2048,21600,23000]:
        # Each column is additive Duhamel propagation under the identical full operator.
        effect=expm(step*DT*H)[:len(y0),len(y0):]
        truth=Q*o.pressure(o.direct(y0,1,0.,step*DT),1)
        for j in [0,16,17,18]:
            contrib=Q*(o.o[j]@effect)
            pstart=Q*o.pressure(y0,1.)[j]
            err=abs(pstart+np.sum(contrib)-truth[j])
            if err>1e-4:raise ValueError("Duhamel reconstruction")
            hist.append(dict(operator=name,acceleration_space=("strict_radial" if strict else "all_material_vectors"),
                step_after_open=step,tau_s=step*DT,shell=j+1,preopen_Pa=pstart,
                inherited_closed_derivative_Pa=contrib[0],removed_boundary_pressure_force_Pa=contrib[1],
                removed_boundary_Darcy_pressure_Pa=contrib[2],removed_boundary_Darcy_acceleration_Pa=contrib[3],
                unchanged_external_traction_increment_Pa=0.,total_Pa=truth[j],reconstruction_abs_Pa=err))
    # The strict Galerkin constraint is a separate diagnostic for unresolved angular accelerations.
    sub=Phase(B,C,name,0.,True)
    _,summary=march(name,"finite_Kw","source_n_held",c,o,ref) if strict else (None,None)
    return hist,dict(source_split_relative=residual,closed_M0_max_real_per_s=sub.stats["spectral_abscissa_per_s"],
                     finite_Kw_strict_radial_summary=summary)


def subspace(B,V,m):
    # Scalar mass matrix is diagonal; deleting the outer pressure DOF commutes with its inverse.
    # Restricting pressure does not impose radial/clamped displacement at the freely moving surface.
    free=np.eye(20)[:,:19];Mv=np.diag(V)
    inv_error=np.max(abs(np.linalg.inv(free.T@Mv@free)-free.T@np.linalg.inv(Mv)@free))
    MP=m[:,None]*B["P"];DtV=(V[:,None]*B["D"]).T
    grad_work=np.linalg.norm((MP-DtV)@free)/np.linalg.norm(MP@free)
    # Actual angular acceleration divergence before projection versus strict mass-projected acceleration.
    gram=V[:,None]*(B["DP"]-B["D"]@B["P"]);G=free.T@gram@free
    norm=np.linalg.norm(V[:,None]*B["DP"])
    return dict(restricted_pressure_mass_inverse_abs=inv_error,
         restricted_pressure_virtual_work_relative=grad_work,
         angular_pressure_force_gram_asym_relative=np.linalg.norm(G-G.T)/norm,
         angular_gram_symmetric_eigen_minmax=[float(a) for a in np.linalg.eigvalsh((G+G.T)/2)[[0,-1]]],
         angular_gram_vs_full_norm=np.linalg.norm(G)/norm,
         boundary_pressure_force_radial_accel_per_Pa_by_shell=B["P"][:,-1].tolist(),
         traction_radial_accel_per_Pa_by_shell=B["F"][:,0].tolist(),
         unconstrained_external_displacement_dofs=20,pressure_free_dofs=19)


def main():
    dest=T/"figures"/(TAG+".csv");rec=T/"logs"/(TAG+".check.json")
    if dest.exists() or rec.exists():raise FileExistsError(dest)
    mesh=np.load(T/"outputs/cryer_tet_reference_r1.npz");s=mesh["material_shell"]-1
    m=np.bincount(s,weights=mesh["native_mass_kg"])
    dual=np.bincount(mesh["tets"].ravel(),weights=np.repeat(mesh["Ve"]/4,4),minlength=len(s))
    refs=pd.read_csv(T/"figures/cryer_p3_server_peak_actual_r1/physical/matched_center_diagnosis.csv")
    cfg={"original":"cryer_coupled_shell_modes_r1_blocks","paired":"cryer_shell_tet_pair_r1_sph"}
    C=np.load(T/"figures/cryer_shell_closed_rows_r1.npz")
    results={};table=[]
    for name,tag in cfg.items():
        B=np.load(T/"figures"/(tag+".npz"))
        V=np.bincount(s,weights=mesh["native_volume_m3"] if name=="original" else dual)
        results[name]=dict(pressure_subspace=subspace(B,V,m))
        if name=="paired":
            info=results[name]["pressure_subspace"]
            if info["restricted_pressure_virtual_work_relative"]>3e-12 or info["angular_pressure_force_gram_asym_relative"]>1e-11 or info["angular_gram_symmetric_eigen_minmax"][0]<-1e-11:
                raise ValueError("Restricted compatible virtual work or positive angular complement")
        for strict in [False,True]:
            rows,res=channels(B,C,name,strict,refs)
            results[name]["strict" if strict else "actual_angular"]=res
            table.extend(rows)
    df=pd.DataFrame(table);df.to_csv(dest,index=False)
    results["physical_solver_runs"]=0
    results["maximum_reconstruction_error_Pa"]=float(df.reconstruction_abs_Pa.max())
    rec.write_text(json.dumps(results,indent=2,allow_nan=False)+"\n")
    print(df[(df.step_after_open==64)&(df.shell==1)].to_string(index=False))


if __name__=="__main__":main()
