"""Screen the genuine 3-D P1 Darcy matrix before using it in a pressure iteration."""
import argparse
import json
import os
import time
from pathlib import Path

# One thread suffices for the sparse eigensolve; set this before BLAS is imported.
for name in ("MKL_NUM_THREADS","OPENBLAS_NUM_THREADS","OMP_NUM_THREADS"):
    os.environ[name]="1"
import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import eigsh

from cryer_shell_equilibrium import R, TESTS, need, write


TAG = "cryer_tet_darcy_spectrum_r1"


def edge_stats(K):
    off=sparse.triu(K,k=1,format="coo")
    d=K.diagonal()
    data=off.data
    scaled=data/np.sqrt(d[off.row]*d[off.col])
    return dict(geometric_unique_off_diagonal=len(data),exact_zero=int(np.sum(data==0)),
        positive=int(np.sum(data>0)),negative=int(np.sum(data<0)),
        robust_positive=int(np.sum(scaled>1.e-14)),robust_negative=int(np.sum(scaled < -1.e-14)),
        absolute_positive_over_all=float(np.maximum(data,0).sum()/abs(data).sum()),
        positive_normalized_max=float(scaled.max()),negative_normalized_min=float(scaled.min()))


def assemble(cache):
    with np.load(cache) as z:
        t=z["tets"];v=z["Ve"];G=z["Ve_gradN"];x=z["x0"]
        fs=z["native_surface"];shell=z["material_shell"];ids=z["native_ids"]
    n=len(x)
    need(len(fs)==5153 and len(ids)==37173 and np.array_equal(ids,np.arange(8,37181))
         and np.array_equal(fs,np.flatnonzero(shell==20)),"Original material and drain IDs")
    interior=np.setdiff1d(np.arange(n),fs)
    Ke=np.einsum("eiq,ejq->eij",G,G)/v[:,None,None]
    rows=np.broadcast_to(t[:,:,None],Ke.shape);cols=np.broadcast_to(t[:,None,:],Ke.shape)
    K=sparse.coo_matrix((Ke.ravel(),(rows.ravel(),cols.ravel())),shape=(n,n)).tocsr()
    return t,v,G,x,fs,shell,ids,interior,K


def main(cache):
    start=time.perf_counter()
    regions=TESTS/"figures"/(TAG+"_radial.csv"); modes=TESTS/"figures"/(TAG+"_high_mode.csv")
    report=TESTS/"logs"/(TAG+".check.json")
    need(not any(f.exists() for f in (regions,modes,report)),"Preserve original analysis")
    t,v,G,x,fs,shell,ids,interior,K=assemble(cache)
    n=len(x)
    # Both orders were assembled independently with identical element memberships.
    asym=K-K.T; asymmetry=float(np.abs(asym.data).max(initial=0.))
    d=K.diagonal()
    need(asymmetry<1e-12 and np.all(d>0),"Symmetric energy and positive diagonal")
    full_components=connected_components(K,directed=False,return_labels=False)
    A=K[interior][:,interior].tocsr()
    open_components=connected_components(A,directed=False,return_labels=False)
    row_def=float(np.max(abs(K@np.ones(n))/d))
    need(full_components==open_components==1 and row_def<1e-12,"Connected pressure graph and closed constant kernel")
    invd=1/np.sqrt(A.diagonal())
    B=A.multiply(invd[:,None]).multiply(invd[None,:]).tocsr()
    F=float(np.max(np.asarray(abs(B).sum(axis=1))))
    rng=np.random.default_rng(20261120)
    seed=rng.standard_normal(len(interior))
    t_assembled=time.perf_counter()-start
    # Rayleigh quotient of *any* vector gives an independent lower bound on lambda_max.
    high,vec=eigsh(B,k=1,which="LA",v0=seed,tol=1e-11,maxiter=3000)
    w=vec[:,0]; w/=np.linalg.norm(w)
    bw=B@w; lam=float(w@bw); err=float(np.linalg.norm(bw-lam*w))
    low,vl=eigsh(B,k=1,which="SA",v0=seed,tol=1e-8,maxiter=4000)
    ll=float(low[0]);errlow=float(np.linalg.norm(B@vl[:,0]-ll*vl[:,0]))
    need(err<1e-7 and errlow<1e-7 and ll>errlow,"Numerical checks of both spectral endpoints")
    jac=w.copy(); sequence=[]
    for _ in range(3):
        jac=jac-B@jac
        sequence.append(float(np.linalg.norm(jac)))
    need(abs(sequence[-1]-abs(1-lam)**3)<1e-7,"Direct three unrelaxed diagonal sweeps")
    pressure=invd*w; top=np.argsort(abs(w))[-8:][::-1]
    highrows=[dict(native_id=int(ids[interior[j]]),shell=int(shell[interior[j]]),
                   normalized_vector_entry=w[j],pressure_mode_unit_max=pressure[j]/np.max(abs(pressure))) for j in top]
    U=sparse.coo_matrix((np.sqrt(A.diagonal()),(np.arange(len(interior)),shell[interior]-1)),
                        shape=(len(interior),19)).tocsr()
    norm=np.sqrt(np.asarray(U.power(2).sum(axis=0)).ravel())
    U=U.multiply(1/norm)
    reduced=np.linalg.eigvalsh((U.T@B@U).toarray())
    radial_projection=float(np.linalg.norm(U.T@w)**2)
    need(radial_projection<=1+1e-12 and reduced[-1]<=lam+1e-8,"Radial-subspace inclusion")
    # Unit pressure immediately before a Dirichlet surface is switched to zero.
    # This homogeneous iteration is only a hydraulic step-response sketch.
    z=np.ones(len(interior)); sweeps=[z.copy()]
    for _ in range(3):
        z=z-(A@z)/A.diagonal()
        sweeps.append(z.copy())
    quad=1-np.sum(x*x,axis=1)/R**2
    Vnode=np.bincount(t.ravel(),weights=np.repeat(v/4,4),minlength=n)
    expected=6/R**2*Vnode[interior];op=A@quad[interior]
    rows=[]
    for j in range(1,20):
        inside=shell[interior]==j
        row=dict(shell=j,r0_over_a=j/20,nodes=int(inside.sum()),
            high_mode_norm2_fraction=float(w[inside]@w[inside]),
            quadratic_integral_ratio=float(op[inside].sum()/expected[inside].sum()),
            local_quadratic_error_RMS_to_source=float(np.sqrt(np.mean((op[inside]/expected[inside]-1)**2))))
        for k,z in enumerate(sweeps[1:],1):
            row.update({f"iteration{k}_mean":z[inside].mean(),f"iteration{k}_min":z[inside].min(),
                        f"iteration{k}_max":z[inside].max()})
        rows.append(row)
    # Check a random full-field energy against an independent direct element gradient.
    h=rng.normal(size=n)
    grad=np.einsum("en,end->ed",h[t],G)
    ene=float(h@(K@h));exact=float(np.sum(np.sum(grad**2,axis=1)/v))
    need(abs(ene-exact)<1e-10*exact,"Independent positive energy assembly")
    write(regions,rows);write(modes,highrows)
    summary=dict(nodes=n,open_unknowns=len(interior),prescribed=len(fs),tetrahedra=len(t),
        closed_nnz=int(K.nnz),open_nnz=int(A.nnz),closed_unique_edges=edge_stats(K),open_unique_edges=edge_stats(A),
        closed_connected=full_components,open_connected=open_components,closed_constant_relative_defect=row_def,
        symmetry_max=asymmetry,checked_energy=ene,independent_energy=exact,
        normalized_K_min=ll,normalized_K_min_eigen_residual=errlow,normalized_K_max_Rayleigh=lam,
        max_eigen_residual=err,max_eigenvalue_upper_bound_from_element_cauchy=4.,
        max_eigenvalue_gershgorin=F,dominant_Jacobi_eigenvalue=1-lam,
        direct_three_sweep_normalized_mode_norms=sequence,
        open_radial_restriction_min=float(reduced[0]),open_radial_restriction_max=float(reduced[-1]),
        largest_mode_squared_radial_projection=radial_projection,
        normalized_high_mode_participation=1/float(np.sum(w**4)),
        first_open_sweeps=[dict(round=k,above_unit=int(np.sum(z>1+1e-12)),below_zero=int(np.sum(z < -1e-12)),
                                maximum=z.max(),minimum=z.min()) for k,z in enumerate(sweeps[1:],1)],
        quadratic_all_weak_integral_ratio=float(op.sum()/expected.sum()),
        assembly_wall_s=t_assembled,analysis_wall_s=time.perf_counter()-start,
        scope="Pure positive Darcy stiffness with zero drain values and the consistent diagonal. Multiplying by positive k/gamma does not change this normalized screen. A homogeneous Jacobi step is not a full P3 pressure round with solid/storage or time-history feedback.")
    with report.open("x",encoding="utf8") as f: json.dump(summary,f,indent=2,allow_nan=False)
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache",type=Path)
    main(parser.parse_args().cache)
