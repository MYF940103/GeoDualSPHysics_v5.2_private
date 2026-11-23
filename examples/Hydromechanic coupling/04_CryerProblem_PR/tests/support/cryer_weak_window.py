"""Run the full 3-D fixed-reference conservative flux experiment after CPU/GPU component checks."""
import argparse
import ctypes as ct
from pathlib import Path
import numpy as np
from cryer_pair_window import T, DT, DAMP, execute
from c04_p3_pressure_component import GAMMA, K as CONDUCTIVITY
from cryer_tet_darcy_spectrum import assemble


def configure(driver,m,hydro):
    ptr=ct.c_void_p
    driver.lib.startWeak.argtypes=[]
    driver.lib.advanceWeak.argtypes=[ct.c_int]
    driver.lib.uploadWeak.argtypes=[ct.c_int]+[ptr]*5
    driver.lib.weakFixture.argtypes=[ptr,ptr,ptr,ct.c_int,ptr]
    driver.lib.weakClosedFixture.argtypes=[ptr,ptr,ct.c_double,ptr]
    driver.lib.releaseWeak.argtypes=[]
    stiff=assemble(T/"outputs/cryer_tet_reference_r1.npz")[-1].sorted_indices()
    # Analytic linear response, with the endpoint AV frozen within the three rounds.
    pressure_acc=[H.multiply((1/m.mass)[:,None]).tocsr() for H in m.HT]
    BP=sum(B@P for B,P in zip(m.D,pressure_acc))
    FP=sum(H@P for H,P in zip(m.HT,pressure_acc))
    jac=stiff+1000*(1-DAMP*DT)*FP+(GAMMA/CONDUCTIVITY*DT)*BP.multiply(m.volume[:,None])
    row=np.asarray(abs(jac).sum(axis=1)).ravel()
    assert np.isfinite(row).all() and np.min(row)>0
    driver.call("uploadWeak",stiff.nnz,stiff.indptr,stiff.indices,stiff.data,m.volume,row)
    driver.call("startWeak")
    with np.load(T/"outputs/cryer_tet_step_reference_r1.npz") as f:
        q=np.ascontiguousarray(f["p_Pa"].astype(np.float32).astype(np.float64))
        a=np.ascontiguousarray(f["acceleration_m_s2"].astype(np.float32).astype(np.float64))
        theta=np.ascontiguousarray(f["divergence_v_per_s"].astype(np.float32).astype(np.float64))
    rhs=-stiff@q-1000*sum(H@a[:,j] for j,H in enumerate(m.HT))-(GAMMA/CONDUCTIVITY)*m.volume*theta
    expected=(q+rhs/row).astype(np.float32).astype(np.float64)
    out=np.zeros(m.n)
    report={"coupled_row_min":min(row),"coupled_row_max":max(row)}
    for drain in (False,True):
        driver.call("weakFixture",q,a,theta,int(drain),out)
        if drain:expected[hydro.fs]=0
        diff=float(np.max(abs(out-expected)))
        report["raw_sweep_"+("open" if drain else "closed")+"_max_Pa"]=diff
        if diff>2e-6:raise ArithmeticError(f"Independent weak residual {diff} Pa")
    base=np.ascontiguousarray(m.surface_force(10000)/m.mass[:,None])
    zero=np.zeros(m.n)
    driver.call("weakClosedFixture",zero,base,0.,out)
    uniform=float(np.max(abs(out-10000)))
    report["uniform_preload_recovered_max_error_Pa"]=uniform
    if uniform>2e-6:raise ArithmeticError(f"Uniform-pressure constraint {uniform}")
    b=m.pressure_force(np.ones(m.n))
    pn=m.pressure_force(q)/m.mass[:,None]
    c=-np.sum(b*(a+pn))/np.sum(b*b/m.mass[:,None])
    driver.call("weakClosedFixture",q,a,0.,out)
    expected=(q+c).astype(np.float32).astype(np.float64)
    diff=float(np.max(abs(out-expected)))
    report["nonuniform_multiplier_max_error_Pa"]=diff
    if diff>2e-6:raise ArithmeticError(f"Nonuniform sealed constraint {diff} Pa")
    return report


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dll",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--steps",type=int,choices=(4160,36864),default=4160)
    ap.add_argument("--resume",type=Path)
    a=ap.parse_args()
    if a.steps>4160 and not a.resume:ap.error("Review the actual first opening before extending")
    execute(a.dll,a.out,a.steps,a.resume,weak=configure)
