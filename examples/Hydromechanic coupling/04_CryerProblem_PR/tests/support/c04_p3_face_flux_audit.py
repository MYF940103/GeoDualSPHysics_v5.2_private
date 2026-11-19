"""Independently verify element pair budgets, face data, closure, and actual-cloud pressure modes."""
import json
from scipy.sparse.linalg import eigs
from c04_p3_face_flux import FaceFluxPressure, TetMechanics, T, np, RHOW
from c04_p3_coupled_spectrum import Coupled, CryerSPHPressure

TAG="c04_p3_face_flux_r1"
GEOM=T/"outputs/cryer_tet_reference_r1.npz"


def metric(z):
    return dict(rms=float(np.sqrt(np.mean(abs(z)**2))),max=float(np.max(abs(z))))


def spectrum(op,v0):
    val,V=eigs(op,k=1,which="LM",v0=v0,ncv=64,tol=2.e-9,maxiter=200)
    lam=val[0];v=V[:,0]
    applied=op@v.real+1j*(op@v.imag)
    roots=np.roots([1,-1.5*lam**3,.5*lam**3])
    return dict(real=float(lam.real),imag=float(lam.imag),residual=float(np.linalg.norm(applied-lam*v)/np.linalg.norm(v)),
                three_round=float(abs(lam)**3),conditional_temporal_root=float(max(abs(roots))),
                note="one dominant-Ritz search; no nonnormal upper bound or whole-step stability proof")


def main():
    path=T/"logs"/(TAG+".json")
    if path.exists(): raise FileExistsError(path)
    mesh=TetMechanics(GEOM)
    model=FaceFluxPressure(mesh,GEOM)
    original=CryerSPHPressure.load()
    with np.load(GEOM) as z:
        t=z["tets"];ve=z["Ve"];G=z["Ve_gradN"];f=z["faces"];area=z["face_area_out"]
    x=mesh.x
    idx=~model.fs
    n=mesh.n
    ones=np.ones(n)
    zvec=np.zeros((n,3))
    rng=np.random.default_rng(20261120)
    q=rng.normal(size=n)*100.
    a=rng.normal(size=(n,3))
    r=model.total_flux(q,a)
    g=np.zeros_like(r); summed_abs_flux=0.
    for start in range(0,len(t),5000):
        sl=slice(start,start+5000);tt=t[sl];GG=G[sl];volume=ve[sl]
        ac=a[tt].mean(axis=1)
        for i in range(4):
            for j in range(i):
                keij=np.einsum("ik,ik->i",GG[:,i],GG[:,j])/volume
                fl=-keij*(q[tt[:,j]]-q[tt[:,i]]+RHOW*np.einsum("ik,ik->i",ac,x[tt[:,j]]-x[tt[:,i]]))
                np.add.at(g,tt[:,i],fl)
                np.add.at(g,tt[:,j],-fl)
                summed_abs_flux+=np.abs(fl).sum()
    report=dict(material_ids=n,tetrahedra=len(t),boundary_triangles=len(f),true_drained=len(mesh.surface),
        units="total_flux[p,a] in Pa m; positive sign is integrated divergence of grad(p)+rho*a, i.e. negative times Darcy outward discharge gamma/k.",
        element_all_six_pairs_random_independent_vs_sparse_residual_Pa_m=metric(g-r),
        random_signed_scalar_total_Pa_m=float(g.sum()),relative_pair_drift=float(abs(g.sum())/summed_abs_flux),
        integrated_constant_pressure_residual_Pa_m=metric(model.total_flux(ones,zvec)),
        force_and_volume=dict(area_m2=float(np.linalg.norm(area,axis=1).sum()),
            volume_geometry_m3=float(mesh.volume.sum()),volume_native_m3=float(mesh.native_volume.sum()),
            b_plus_surfaceforce1_N_per_Pa=metric(model.b+mesh.unit_surface_force),
            b_net_N_per_Pa=metric(model.b.sum(axis=0)),b_torque_Nm_per_Pa=metric(np.cross(x,model.b).sum(axis=0)),
            bTMinvb_m3_per_Pa_s2=model.closed_response,isolated_closed_pressure_sum=float(model.ell.sum())))
    # With p linear, grad p fixed; choosing a=-grad p/rho must give zero pair
    # total flux, including true exterior. For a=0, the exact natural face flux closes each row.
    checks=[]
    for axis in np.eye(3):
        p=x@axis
        ac=np.broadcast_to(-axis/RHOW,x.shape)
        h=np.zeros(n)
        for i in range(3): np.add.at(h,f[:,i],(area@axis)/3)
        checks.append(dict(combined_constant_acceleration_zero_flux_Pa_m=metric(model.total_flux(p,ac)),
                           applied_true_affine_face_row_residual_Pa_m=metric(model.total_flux(p,zvec)+h)))
    report["affine_moments"]=checks
    # p=|x|^2 gives analytical div(grad p)=6. On each flat facet x dot n is constant.
    p=(x*x).sum(axis=1)
    a_flux=2*np.einsum("ij,ij->i",area,x[f].mean(axis=1))
    h=np.zeros(n)
    for i in range(3): np.add.at(h,f[:,i],a_flux/3)
    curv=(model.total_flux(p,zvec)+h)/mesh.volume
    report["quadratic_manufactured"]=dict(true_planar_flux_m3=float(h.sum()),sphere_analytical_flux_m3=float(8*np.pi*.05**3),
        true_planar_flux_relative_to_sphere=float(h.sum()/(8*np.pi*.05**3)-1),
        global_weighted_laplacian=float(mesh.volume@curv/mesh.volume.sum()),
        boundary_point_error=metric(curv[~idx]-6),interior_point_error=metric(curv[idx]-6),
        near_center_first18_error=metric(curv[mesh.shells==1]-6))
    load=mesh.surface_force(10000)/mesh.mass[:,None]
    ca=model.volume_multiplier(load,0*ones)
    corr=load+model.pressure_acceleration(ca*ones)
    netvolrate=float(model.b.ravel()@corr.ravel())
    zg=np.zeros(n);qi=zg;generated=[]
    # Compatibility must hold at each physical force time, including the first
    # acceleration. With updated load the algebraic closed mean is projected first.
    prev=q.copy()
    final=q.copy()
    vol=mesh.volume
    for j in range(3):
        final=model.sweep(final,zg,load,False)
        generated.append(dict(round=j+1,mean_Pa=float(final.mean()),condition_bTa_m3_s2=model.volume_rate(load+model.pressure_acceleration(final))))
    first=ca*ones
    uniform=[]
    for j in range(3):
        first=model.sweep(first,zg,load,False)
        uniform.append(metric(first-10000))
    report["true_uniform_closed_load"]=dict(mean_pressure_recovered_Pa=float(ca),after_first_projection_acceleration_error_m_s2=metric(corr),
        bTa_m3_s2=netvolrate,projected_sudden_load_uniform_three_rounds_error_Pa=uniform,
        arbitrary_random_initial_pressure_plus_load_check=generated,
        compatibility_note="If theta already has nonzero geometric integral, frozen pressure rows cannot close it. At each physical velocity/acceleration substage use the same b to correct the new velocity with pressure (b.T v =0); endpoint acceleration projection alone cannot repair old velocity drift.")
    for opened in (False,True):
        op=model.fixed_endpoint_operator(opened)
        old=Coupled(original,mesh,opened)
        v0=np.random.default_rng(972).normal(size=op.shape[0])
        modes={}
        for field,y0 in (("random",v0),("shell_alternating",np.where(mesh.shells%2,1.,-1.)[old.active]),
                         ("surface_or_outer_first_free",(mesh.shells[old.active]==max(mesh.shells[old.active])).astype(float))):
            y=y0
            ys=[]
            for j in range(3):
                y=op@y
                ys.append(float(np.linalg.norm(y)/np.linalg.norm(y0)))
            modes[field]=ys
        # For numerical face-opening response only, starting with uniform p and
        # clamping the exterior; actual body velocity and strain fixed to zero.
        q0=10000*ones
        if opened:q0[model.fs]=0
        init=[]
        for j in range(3):
            q0=model.sweep(q0,zg,load,opened)
            init.append(dict(min_Pa=float(min(q0[idx])),max_Pa=float(max(q0[idx])),weighted_mean_Pa=float(vol@q0/vol.sum())))
        report["open" if opened else "closed"]=dict(cond_mode3=modes,uniform_load_transition=init,
            matched_weak_operator=spectrum(op,v0),original_mixed_operator=spectrum(old.op,np.ones(old.n)))
    with path.open("x") as out:json.dump(report,out,indent=2,allow_nan=False)
    print(path,flush=True)


if __name__=="__main__":
    main()
