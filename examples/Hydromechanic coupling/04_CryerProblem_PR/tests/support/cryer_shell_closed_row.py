"""Restore the initial physical closed-surface Taylor flux correction in both radial matrices."""
import os
for key in ("MKL_NUM_THREADS","OPENBLAS_NUM_THREADS","OMP_NUM_THREADS"):
    os.environ[key]="1"
import json
import numpy as np
from scipy.sparse import coo_matrix
from cryer_coupled_shell_modes import T,Graph,LAM,MU
from cryer_p3_peak_shells import ordered


def main():
    out=T/"figures/cryer_shell_closed_rows_r1.npz"
    receipt=T/"logs/cryer_shell_closed_rows_r1.check.json"
    if any(p.exists() for p in [out,receipt]):raise FileExistsError(out)
    mesh=np.load(T/"outputs/cryer_tet_reference_r1.npz")
    x=mesh["x0"];t=mesh["tets"];g=mesh["Ve_gradN"];faces=mesh["faces"];av=mesh["face_area_out"]
    ve=mesh["Ve"];mass=mesh["native_mass_kg"];s=mesh["native_surface"];n=len(x);nt=len(t)
    name="CaseCryer_TPI_P3_nu030_peak_r1_GPU_out"
    initial=ordered(T.parent/name/name/"data",0,["FSNormal","FSType","Posd"])
    np.testing.assert_array_equal(x,initial["Posd"])
    np.testing.assert_array_equal(s,np.flatnonzero(np.isin(initial["FSType"],(2,3))))
    normal=initial["FSNormal"].astype(float)[s];length=np.linalg.norm(normal,axis=1)
    if np.min(length)<=0:raise ValueError("True initial FS normal required")
    normal/=length[:,None]
    orig=Graph();orig.assemble()
    B=orig.eye;U=orig.vec;gp=orig.grad(B)
    factor=(orig.lx[s]*normal).sum(axis=1)
    dual=np.bincount(t.ravel(),weights=np.repeat(ve/4,4),minlength=n)
    rows={}
    for label,weights in (("original",np.full(len(s),1/len(s))),("paired",dual[s]/dual[s].sum())):
        w=weights[:,None]*factor[:,None]*normal
        rows[label+"_lap"]=sum(w[:,a]@gp[a][s] for a in range(3))
        rows[label+"_vel"]=np.einsum("na,nai->i",w,U[s])
        if label=="original":
            for key,node in (("Ku",orig.Au),("P",orig.Ap),("F",orig.load)):
                rows[label+"_"+key]=np.einsum("na,nai->i",w,node[s])
        else:
            # w.applied_acceleration = (w/m).applied_force. Pair-force virtual work
            # applies to arbitrary, non-radial tests; express this particular test by a single nodal field.
            virtual=np.zeros_like(x)
            virtual[s]=w/mass[s,None]
            recv=coo_matrix((np.full(4*nt,.25),(t.ravel(),np.repeat(np.arange(nt),4))),shape=(n,nt)).tocsr()
            G=[]
            for a in range(3):
                elem=coo_matrix((g[:,:,a].ravel(),(np.repeat(np.arange(nt),4),t.ravel())),shape=(nt,n)).tocsr()
                G.append((recv@elem).multiply((1/dual)[:,None]).tocsr())
            vg=np.stack([op@virtual for op in G],axis=2)
            virtual_stress=MU*(vg+vg.transpose(0,2,1))+LAM*np.trace(vg,axis1=1,axis2=2)[:,None,None]*np.eye(3)
            Ku=np.zeros(20)
            for a in range(3):
                for b in range(3):
                    Ku-=(dual*virtual_stress[:,a,b])@(G[b]@U[:,a,:])
            rows[label+"_Ku"]=Ku
            rows[label+"_P"]=(dual*np.trace(vg,axis1=1,axis2=2))@B
            rows[label+"_F"]=np.array([-np.sum(virtual[faces].mean(axis=1)*av)])
    checks={}
    radius=.0025*np.arange(1,21)
    for label in ("original","paired"):
        lp=rows[label+"_lap"];P=rows[label+"_P"];F=rows[label+"_F"][0];K=rows[label+"_Ku"]
        eqp=float(abs(P.sum()+F)/abs(F));eqs=float(abs(K@radius/(3*LAM+2*MU)-F)/abs(F))
        gap=float(abs(lp.sum())/np.max(abs(lp)))
        if max(eqp,eqs,gap)>3e-11:raise ValueError("Closed normal correction lacks matching uniform equilibrium")
        checks[label]=dict(constant_pressure_Darcy_relative=gap,uniform_p_q_force_relative=eqp,hydrostatic_elastic_q_relative=eqs)
    cos=np.sum(orig.radial[s]*normal,axis=1)
    checks["native_normal_cos_radial_minmax"]=[float(cos.min()),float(cos.max())]
    checks["surface_count"]=len(s)
    checks["policy"]="Only the prescribed actual FS normal component is subtracted from the Darcy Taylor correction. All surface rows stay active in the closed state."
    np.savez(out,**rows)
    receipt.write_text(json.dumps(checks,indent=2)+"\n")
    print(checks)


if __name__=="__main__":main()
