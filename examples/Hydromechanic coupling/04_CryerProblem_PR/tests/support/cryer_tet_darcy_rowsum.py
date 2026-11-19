"""Check a geometry-defined row-sum preconditioner on the original Cryer Darcy operator."""
import argparse
import json
from pathlib import Path

from cryer_tet_darcy_spectrum import TAG as EXACT_DIAG, assemble
from cryer_shell_equilibrium import TESTS,Q,R,need,write
from cryer_peak_paired_manufactured import Reference,radial_state
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh

TAG="cryer_tet_darcy_rowsum_r2"


def main(cache):
    baseline=json.loads((TESTS/"logs"/(EXACT_DIAG+".check.json")).read_text(encoding="utf8"))
    figures=TESTS/"figures"
    out=figures/(TAG+"_cpu_sweeps.csv");modes=figures/(TAG+"_modes.csv")
    figure=figures/(TAG+".png");report=TESTS/"logs"/(TAG+".check.json")
    need(not any(p.exists() for p in (out,modes,figure,report)),"Preserve earlier evidence")
    _,_,_,x,fs,shell,ids,I,K=assemble(cache)
    A=K[I][:,I].tocsr()
    d=A.diagonal()
    need(K.nnz==baseline["closed_nnz"] and A.nnz==baseline["open_nnz"],"Same 3-D operator")
    # Freeze the entire closed-row absolute sum before removing boundary columns.
    s=np.asarray(abs(K).sum(axis=1)).ravel()[I]
    open_sum=np.asarray(abs(A).sum(axis=1)).ravel()
    need(np.all(s>=d) and np.min(s-open_sum)>-1e-12,"Fixed closed-row domination")
    S=1/np.sqrt(s)
    B=A.multiply(S[:,None]).multiply(S[None,:]).tocsr()
    rng=np.random.default_rng(20261120); seed=rng.normal(size=len(I))
    low,vlo=eigsh(B,k=1,which="SA",v0=seed,tol=1e-8,maxiter=4000)
    high,vhi=eigsh(B,k=1,which="LA",v0=seed,tol=1e-11,maxiter=4000)
    ll,hl=float(low[0]),float(high[0])
    need(0<ll<=hl<=1+1e-12,"Symmetric positive and Gershgorin bound")
    witnesses=[]
    for label,v,lam in (("slow",vlo[:,0],ll),("high",vhi[:,0],hl)):
        err=float(np.linalg.norm(B@v-lam*v))
        need(err<1e-7,"Eigen residual of actual normalized matrix")
        for k in range(4):
            witnesses.append(dict(mode=label,round=k,normalized_error_norm=np.linalg.norm(v),
                                  lambda_value=lam,eigen_residual=err))
            need(abs(np.linalg.norm(v)-abs(1-lam)**k)<1e-7,"Direct three independent sweeps")
            v=v-B@v
    U=sparse.coo_matrix((np.sqrt(s),(np.arange(len(I)),shell[I]-1)),shape=(len(I),19)).tocsr()
    U=U.multiply(1/np.sqrt(np.asarray(U.power(2).sum(axis=0)).ravel()))
    rads=np.linalg.eigvalsh((U.T@B@U).toarray())
    metrics=[]
    def observe(name,method,k,z,known=None,b=None):
        row=dict(case=name,preconditioner=method,round=k,min_pressure_Pa=z.min(),max_pressure_Pa=z.max(),
            interior_mean_Pa=z.mean(),center18_mean_Pa=z[shell[I]==1].mean(),
            above_initial_10kPa=int(np.sum(z>Q+1e-8)),below_zero=int(np.sum(z < -1e-8)),
            err_vector_rms_Pa=None,err_max_Pa=None,err_center18_mean_Pa=None,
            residual_diagonal_weighted_norm=None)
        if known is not None:
            row.update(err_vector_rms_Pa=np.sqrt(np.mean((z-known)**2)),err_max_Pa=np.max(abs(z-known)),
                       err_center18_mean_Pa=np.mean((z-known)[shell[I]==1]),
                       residual_diagonal_weighted_norm=float(np.linalg.norm((b-A@z)/np.sqrt(d))))
        metrics.append(row)
    for name,divider in (("diagonal",d),("closed_absolute_row_sum",s)):
        z=np.full(len(I),Q)
        observe("first_open_zero_rhs",name,0,z)
        for k in (1,2,3):
            z=z-(A@z)/divider
            observe("first_open_zero_rhs",name,k,z)
    # Independently constructed two consecutive frozen test systems. Use the measured
    # peak-window step, prescribed reference times and exact known algebraic RHS.
    # They isolate row iteration and carry history; no solver substage is reconstructed.
    ref=Reference(.3,finite=False);ref.cv=ref.H*ref.kappa;ref.decay=ref.xi**2*ref.cv/R**2
    dp=.0025;dt=2.**-19
    targets=[]
    for step in (1,2):
        p,*_=radial_state(ref,dp*np.arange(1,21),step*dt)
        need(abs(p[-1])<1e-7,"Manufactured zero Dirichlet pressure")
        targets.append(p[shell[I]-1])
    for name,divider in (("diagonal",d),("closed_absolute_row_sum",s)):
        prev=np.full(len(I),Q)
        prev2=prev.copy()
        for step,target in enumerate(targets,1):
            b=A@target
            z=prev if step==1 else 2*prev-prev2
            case=f"prescribed_frozen_system_{step}"
            observe(case,name,0,z,target,b)
            for k in (1,2,3):
                z=z+(b-A@z)/divider
                observe(case,name,k,z,target,b)
            prev2,prev=prev,z
    write(modes,witnesses);write(out,metrics)
    summary=dict(nodes=len(x),open_unknowns=len(I),drain_nodes=len(fs),K_entries=K.nnz,
        diagonal_over_absolute_row_percentiles=np.quantile(d/s,[0,.01,.5,.99,1]).tolist(),
        open_absolute_over_closed_absolute_max=float(np.max(open_sum/s)),
        original_row_sum_Gershgorin_lower=float(np.min((d-open_sum+d)/s)),
        SPD_plus_closed_row_sum_Gershgorin_upper=1.,
        normalized_min=ll,normalized_max=hl,
        three_sweep_slowest_norm=(1-ll)**3,three_sweep_highest_norm=(1-hl)**3,
        spectral_interval_pressure_error_action=[1-hl,1-ll],
        radial_normalized_min=float(rads[0]),radial_normalized_max=float(rads[-1]),
        fixed_row_definition="S_i = sum_j |K_ij| over all original nodes, including diagonal and all true fixed surface nodes. A=K_II. CPU update p += (b-Ap)/S.",
        scoped_predictor="Known P1 linear systems b=A p_M0(r,t), t=dt and 2dt. TPI history seed for second test uses 2*previous_estimated-previous2. No force-stage or real projected-P3 RHS; this only checks algebra and error propagation.")
    with report.open("x",encoding="utf8") as f:json.dump(summary,f,indent=2,allow_nan=False)
    plot(figure,baseline,summary,metrics)
    print(json.dumps(summary,indent=2))
    print([m for m in metrics if m["case"]=="first_open_zero_rhs" and m["preconditioner"]=="closed_absolute_row_sum"])


def plot(dest,base,alt,metrics):
    import matplotlib.pyplot as plt
    fig,aa=plt.subplots(1,2,figsize=(10,4),layout="constrained")
    for label,lo,hi,col in (("Original diagonal",base["normalized_K_min"],base["normalized_K_max_Rayleigh"],"#ba5531"),
                             ("Closed absolute row sum",alt["normalized_min"],alt["normalized_max"],"#216895")):
        k=np.arange(4)
        aa[0].plot(k,np.abs(1-hi)**k,"o-",color=col,label=label+" · high")
        aa[0].plot(k,np.abs(1-lo)**k,"--",color=col)
        method="diagonal" if label.startswith("Original") else "closed_absolute_row_sum"
        records=[r for r in metrics if r["case"]=="first_open_zero_rhs" and r["preconditioner"]==method]
        aa[1].plot(k,[r["max_pressure_Pa"]-Q for r in records],"o-",color=col,label=label)
    aa[0].set(yscale="log",ylabel="Normalized mode norm",title="Highest mode (solid) and slowest (dashed)")
    aa[1].set(ylabel="Maximum excess above initial value (Pa)",title="Opening a 10 kPa field, zero RHS")
    for ax in aa:
        ax.set(xlabel="Jacobi sweep",xticks=[0,1,2,3]);ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.savefig(dest,dpi=175);plt.close(fig)


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("cache",type=Path)
    main(ap.parse_args().cache)
