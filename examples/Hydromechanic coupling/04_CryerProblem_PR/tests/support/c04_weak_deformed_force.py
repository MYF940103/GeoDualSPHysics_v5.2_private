"""One immutable final state, direct P1 weak forces with fixed and updated geometry."""
import json
from c04_p3_pressure_component import T, np
from cryer_tet_mechanics import TetMechanics

TAG="c04_weak_updated_force_r1"
GEOM=T/"outputs/cryer_tet_reference_r1.npz"
STATE=T/"outputs/cryer_weak_peak_r1/state_36864.npz"


def rms(x):
    return float(np.sqrt(np.mean(x*x)))


def scatter(t,v,n):
    return np.stack([np.bincount(t.ravel(),weights=v[:,:,d].ravel(),minlength=n) for d in range(3)],axis=1)


def recover(x,fr,elem,faces,s,p,sigma,areaSign):
    n=len(x)
    X=x[elem]
    E=X[:,1:]-X[:,:1]
    signed=np.linalg.det(E)
    if np.any(np.sign(signed)!=np.sign(fr)):
        raise ValueError("Element orientation changed in the saved coordinates")
    ve=abs(signed)/6
    grad=np.empty((len(elem),4,3))
    grad[:,1:]=np.linalg.inv(E).transpose(0,2,1)
    grad[:,0]=-grad[:,1:].sum(axis=1)
    G=grad*ve[:,None,None]
    fs=scatter(elem,-np.einsum("tij,tkj->tki",sigma[elem].mean(axis=1),G),n)
    fp=scatter(elem,p[elem].mean(axis=1)[:,None,None]*G,n)
    XF=x[faces]
    area=.5*areaSign[:,None]*np.cross(XF[:,1]-XF[:,0],XF[:,2]-XF[:,0])
    q=10000.
    fl=scatter(faces,np.broadcast_to((-q*area/3)[:,None,:],(len(faces),3,3)),n)
    volume=np.bincount(elem.ravel(),weights=np.repeat(ve/4,4),minlength=n)
    total=fs+fp+fl
    smean=np.average(s,axis=0,weights=volume)
    pmean=np.average(p,weights=volume)
    modes=[]
    for k,(a,b) in enumerate(((0,0),(1,1),(2,2),(0,1),(1,2),(0,2))):
        test=np.zeros_like(x)
        test[:,a]=x[:,b] if a==b else x[:,b]/2
        if a!=b:test[:,b]=x[:,a]/2
        actual=np.sum(total*test)
        expected=volume.sum()*(-smean[k]+(pmean-q if a==b else 0.))
        modes.append(dict(affine_virtual_strain=("xx","yy","zz","xy","yz","xz")[k],actual_work_J=float(actual),
                          tensor_and_face_work_J=float(expected),error_J=float(actual-expected)))
    lines=dict(volume_m3=float(volume.sum()),area_m2=float(np.linalg.norm(area,axis=1).sum()),
               quadrature_mean_p_Pa=float(pmean),sigma6_mean_Pa=smean.tolist(),
               total_net_N=total.sum(axis=0).tolist(),total_torque_Nm=np.cross(x,total).sum(axis=0).tolist(),
               six_work=modes,registered_reference_gradients=G)
    return [fs,fp,fl,total],lines


def main():
    out=T/"logs"/(TAG+".json")
    if out.exists():raise FileExistsError(out)
    m=TetMechanics(GEOM)
    with np.load(STATE) as z:
        u=z["u"];s=z["stress"];p=z["p"];v=z["v"]; step=int(z["step"])
        assert step==36864 and np.array_equal(z["ids"],m.ids)
    with np.load(GEOM) as z:
        t=z["tets"];f=z["faces"];A=z["face_area_out"]; G0=z["Ve_gradN"]
    xe=m.x[t];fr=np.linalg.det(xe[:,1:]-xe[:,:1])
    f0=m.x[f]
    sign=np.sign(np.einsum("ij,ij->i",np.cross(f0[:,1]-f0[:,0],f0[:,2]-f0[:,0]),A))
    sigma=np.empty((m.n,3,3))
    for k,(i,j) in enumerate(((0,0),(1,1),(2,2),(0,1),(1,2),(0,2))): sigma[:,i,j]=sigma[:,j,i]=s[:,k]
    F0,l0=recover(m.x,fr,t,f,s,p,sigma,sign)
    F1,l1=recover(m.x+u,fr,t,f,s,p,sigma,sign)
    assert np.max(abs(l0.pop("registered_reference_gradients")-G0))<1.e-15
    l1.pop("registered_reference_gradients")
    force_ref=[m.internal_stress(s),m.pressure_force(p),m.surface_force(10000)]
    orig=[np.max(abs(old-n)) for old,n in zip(F0,force_ref)]; assert max(orig)<1.e-10
    ctr=m.shells==1; surf=m.shells==20
    delta={}
    for label,r,c in zip(("effective_stress","pore_pressure","external_traction","sum"),F0,F1):
        d=c-r; norms=np.linalg.norm(d,axis=1);j=int(np.argmax(norms))
        delta[label]=dict(diff_vector_RMS_N=float(np.sqrt(np.mean(norms**2))),relative_L2=float(np.linalg.norm(d)/np.linalg.norm(r)),
                          diff_max_N=float(norms[j]),max_native_id=int(m.ids[j]),diff_net_N=d.sum(axis=0).tolist(),
                          diff_component_RMS_m_s2=rms(d/m.mass[:,None]),diff_component_max_m_s2=float(abs(d/m.mass[:,None]).max()),
                          center18_diff_component_RMS_m_s2=rms(d[ctr]/m.mass[ctr,None]),
                          surface_diff_component_RMS_m_s2=rms(d[surf]/m.mass[surf,None]),delta_actual_v_power_W=float(np.sum(d*v)))
    obj=dict(step=step,tau_s=.0625,whole_native_material_nodes=m.n,tetrahedra=len(t),true_faces=len(f),
             fixed_direct_vs_original_scattered_force_max_N=orig,fixed=l0,deformed=l1,difference=delta,
             scope="Same native material IDs, positions/displacement, spatial effective Cauchy stress tensor, pore pressure and scalar load. Both actual deformed tet measures and inverse shape gradients are recomputed. This frozen-state form uses current follower normal pressure on the deformed triangles; it is not an evolving updated-Lagrangian constitutive or pressure trajectory.")
    with out.open("x") as fobj:json.dump(obj,fobj,indent=2,allow_nan=False)
    print(out)


if __name__=="__main__":main()

