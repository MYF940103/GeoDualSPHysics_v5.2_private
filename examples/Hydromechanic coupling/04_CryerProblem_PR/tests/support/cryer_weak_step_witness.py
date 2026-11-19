"""Cross-test the mode produced by the real lagged operator using the synchronised operators."""
import argparse
from pathlib import Path
from cryer_coupled_step_spectrum import Step,DT,TESTS,need,write,np,RHOW,BETA,DAMP
from cryer_weak_step_spectrum import Weak


def witness(cache,opened):
    o=Step(cache)
    o.setup(opened,"lagged")
    w=Weak(cache)
    w.setup(opened)
    seed=np.random.default_rng(20261120).normal(size=(11,w.m.n))
    if opened:seed[-2:,w.surface]=0
    z=seed.ravel()/np.linalg.norm(seed)
    for _ in range(28):
        z=o.action(z)
        z/=np.linalg.norm(z)
    # All three operators receive exactly the same perturbation, including p_{n-1}.
    result=[]
    for name in ("actual_lagged","original_sph_sync","weak_sync"):
        op=w if name=="weak_sync" else o
        if name=="original_sph_sync":o.setup(opened,"sync_abs_closed")
        cur=z.copy()
        log_norm=0.
        peak=1.
        ns=20 if name=="actual_lagged" else 128
        for j in range(1,ns+1):
            x=op.action(cur);gain=np.linalg.norm(x)
            x/=gain
            cos=float(x@cur)
            log_norm+=np.log(gain)
            amp=np.exp(log_norm)
            peak=max(amp,peak)
            if j in (1,2,4,8,16,20,32,64,128):
                result.append(dict(opened=opened,scheme=name,nstep=j,amp=amp,maximum_through_step=peak,
                                   last_step_gain=gain,last_step_signed_cosine=cos))
            cur=x
    tag="cryer_weak_step_witness_r1_"+("open" if opened else "closed")
    dest=TESTS/"figures"/(tag+".csv")
    need(not dest.exists(),"Preserve witness")
    write(dest,result)
    for r in result:
        if r["nstep"] in (1,20,128):print(r)
    if opened:
        # On physical interior test rows the discrete boundary trace is identically zero.
        # Dirichlet Schur block reduces to K + (beta*dt-rho*(1-d*dt)) B^T B in conjugate units.
        i=np.flatnonzero(~w.surface)
        wg=w.BP.multiply(w.m.volume[:,None]).tocsr()
        gauss=(w.FP+wg)[i]
        L=w.L[i][:,i].tocsr()
        analytic=(w.K+(DT*BETA-RHOW*(1-DAMP*DT))*wg)[i][:,i]
        difference=L-analytic
        a=(L-L.T)
        scale=max(abs(L.data))
        # D is computed on the whole closed matrix; its row bounds every remaining row.
        rr=np.asarray(abs(L).sum(axis=1)).ravel()/w.den[i]
        extra=dict(live=len(i),positive_schur_coefficient=DT*BETA-RHOW*(1-DAMP*DT),
                   interior_FplusWB_max=float(abs(gauss.data).max(initial=0)),
                   relative_L_to_K_plus_gram=float(abs(difference.data).max(initial=0)/scale),
                   relative_asymmetry=float(abs(a.data).max(initial=0)/scale),
                   maximal_Gershgorin_eigenvalue_bound=float(rr.max()))
        write(TESTS/"figures"/(tag+"_schur.csv"),[extra]);print(extra)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("cache",type=Path);p.add_argument("boundary",choices=["open","closed"])
    a=p.parse_args();witness(a.cache,a.boundary=="open")
