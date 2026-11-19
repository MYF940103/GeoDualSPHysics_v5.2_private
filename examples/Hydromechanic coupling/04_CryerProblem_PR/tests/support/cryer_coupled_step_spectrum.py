"""Frozen three-dimensional, no-AV linearization of the failed private Cryer step and Schur alternatives."""
import argparse
import gc
import json
import os
import time
from pathlib import Path
for name in ("MKL_NUM_THREADS","OPENBLAS_NUM_THREADS","OMP_NUM_THREADS"):
    os.environ[name]="1"
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import eigsh
from cryer_tet_mechanics import TetMechanics
from c04_p3_pressure_component import CryerSPHPressure,GAMMA,K,RHOW
from cryer_coupled_shell_modes import DT,DAMP,RHO,MU,LAM
from cryer_shell_equilibrium import TESTS,need,write

TAG="cryer_coupled_step_spectrum_r1"
BETA=GAMMA/K
ZIMP=np.sqrt(RHO*(LAM+2*MU))


class Step:
    def __init__(self,cache):
        self.m=m=TetMechanics(cache)
        m.lam=LAM;m.mu=MU
        self.h=h=CryerSPHPressure.load()
        invM=1/m.mass
        self.G=sum(D.multiply(invM[None,:]).tocsr()@H for D,H in zip(m.D,m.HT)).tocsr()
        self.N=sum(H.multiply((invM*h.normal_lx[:,j])[:,None]) for j,H in enumerate(m.HT)).tocsr()
        self.L0=sparse.diags(h.S0)@(sparse.identity(m.n,format="csr")-h.E)
        self.live=None

    def setup(self,opened,kind,dt=DT,theta_on=True,inertia_on=True):
        h=self.h;m=self.m
        self.dt=dt;self.open=opened;self.kind=kind;self.theta_on=theta_on;self.inertia_on=inertia_on
        self.live=np.flatnonzero(~h.fs) if opened else np.arange(m.n)
        self.NG=self.G if opened else self.G+self.N
        self.sync=kind!="lagged"
        base=self.L0.copy()
        if self.sync and theta_on:base=base+(dt*BETA)*self.G
        if inertia_on:base=base-(RHOW*(1-DAMP*dt if self.sync else 1))*self.NG
        if kind in ("lagged","sync_original"):den=h.S0.copy()
        elif kind=="sync_diagonal":den=base.diagonal()
        elif kind=="sync_abs_closed":
            closed=self.L0+(dt*BETA)*self.G-RHOW*(1-DAMP*dt)*(self.G+self.N)
            den=np.asarray(abs(closed).sum(axis=1)).ravel()
            del closed
        else:raise ValueError(kind)
        need(np.all(den>0),"Pressure splitting has positive actual denominator")
        self.den=den
        self.T=(sparse.identity(m.n,format="csr")-base.multiply((1/den)[:,None])).tocsr()

    def action(self,flat):
        m,h=self.m,self.h
        z=flat.reshape((11,m.n));v=z[:3].T/ZIMP
        s=z[3:9].T;p=z[9].copy();pr=z[10]
        if self.open:p[h.fs]=0
        g=1.5*p-.5*pr
        if self.open:g[h.fs]=0
        pf=lambda q:m.pressure_force(q)/m.mass[:,None]
        ef=lambda ss:m.internal_stress(ss)/m.mass[:,None]
        dt=self.dt
        vh=v+.5*dt*(ef(s)+pf(p)-DAMP*v)
        sh=s+.5*dt*m.elastic_stress(m.strain(v))
        se=s+dt*m.elastic_stress(m.strain(vh))
        # vbar contains the prediction-independent contribution of the half-stage corrector.
        vbar=v+dt*(ef(sh)-DAMP*vh)
        if not self.sync:vbar+=dt*pf(g)
        a0=ef(se)-DAMP*vbar
        div=m.divergence(a0)
        if not self.open:div+=np.einsum("ij,ij->i",h.normal_lx,a0)
        rhs=RHOW*div
        if self.theta_on:rhs-=BETA*m.divergence(vbar)
        r=rhs/self.den
        for k in range(3):
            g=self.T@g+r
            if self.open:g[h.fs]=0.
        ve=vbar+dt*pf(g) if self.sync else vbar
        return np.vstack((ve.T*ZIMP,se.T,g,p)).ravel()


def growth(step,n,seed):
    """Direct homogeneous finite-window amplification, plus a Ritz residual using Arnoldi."""
    dim=len(seed);Q=np.zeros((n+1,dim));h=np.zeros((n+1,n))
    Q[0]=seed/np.linalg.norm(seed)
    for j in range(n):
        x=step.action(Q[j])
        for _ in range(2):
            d=Q[:j+1]@x;x-=Q[:j+1].T@d;h[:j+1,j]+=d
        h[j+1,j]=np.linalg.norm(x)
        need(h[j+1,j]>1e-13,"Useful Krylov direction");Q[j+1]=x/h[j+1,j]
    ev,vec=np.linalg.eig(h[:-1])
    k=np.argmax(abs(ev));ritz=ev[k]
    residual=abs(h[-1,-1]*vec[-1,k])/np.linalg.norm(vec[:,k])
    curve=[];z=np.zeros(n);z[0]=1.
    # For k <= n these norms are actual full operator powers (Arnoldi identity).
    for j in range(1,n+1):
        r=h@z;curve.append(float(np.linalg.norm(r)));z=r[:-1]
    return dict(krylov_order=n,ritz_abs=float(abs(ritz)),ritz_real=float(ritz.real),ritz_imag=float(ritz.imag),
        Ritz_residual=float(residual),actual_input_norm=1.,norm8=curve[7],norm16=curve[15],
        norm_final=curve[-1],actual_last_step_ratio=curve[-1]/curve[-2])


def geom_screen(step):
    m,h=step.m,step.h
    # invS0*B M^-1 B^T W is similar to a symmetric positive matrix.
    w=np.sqrt(m.volume/h.S0)
    Gsym=step.G.multiply((w/m.volume)[None,:]).multiply((m.volume/w/h.S0)[:,None]).tocsr()
    asym=Gsym-Gsym.T;need(abs(asym.data).max(initial=0)<1e-10,"Symmetric pressure acceleration eigenproblem")
    ret=[]
    for name,I in (("closed",np.arange(m.n)),("open",np.flatnonzero(~h.fs))):
        A=Gsym[I][:,I].tocsr()
        vals,v=eigsh(A,k=1,which="LA",tol=1e-9)
        ray=float(v[:,0]@(A@v[:,0]))
        ret.append(dict(boundary=name,largest_G_over_S0=ray,eigen_residual=float(np.linalg.norm(A@v[:,0]-ray*v[:,0])),
            rho_G=RHOW*ray,dt_beta_G=DT*BETA*ray,individual_dt_for_unit_theta_s=1/(BETA*ray),
            largest_diagonal_direction_lower=float(A.diagonal().max())))
    return ret


def main(cache,phase,order):
    start=time.perf_counter();step=Step(cache)
    if phase=="geometry":
        out=TESTS/"logs"/(TAG+"_geometry.json")
        need(not out.exists(),"Keep initial spectrum")
        rows=geom_screen(step)
        with out.open("x",encoding="utf8") as f:json.dump(dict(dt_s=DT,beta=BETA,rho=RHOW,rows=rows),f,indent=2)
        print(rows,flush=True);return
    label,opened=(phase.split("_",1)[0],phase.endswith("_open"))
    # Full-state perturbation in pressure/history and mechanical fields, balanced by elastic impedance.
    seed=np.random.default_rng(20261120).normal(size=(11,step.m.n))
    if opened:seed[-2:,step.h.fs]=0.
    if label=="base":
        variants=[("lagged",DT,True,True),("lagged",DT,False,True),("lagged",DT,True,False),
                  ("lagged",DT/2,True,True)]
    elif label=="sync":
        variants=[(x,DT,True,True) for x in ("sync_original","sync_diagonal","sync_abs_closed")]
    else:raise ValueError(label)
    dest=TESTS/"figures"/(TAG+"_"+phase+".csv")
    need(not dest.exists(),"Preserve existing steps")
    results=[]
    for kind,dt,theta,inertia in variants:
        step.setup(opened,kind,dt,theta,inertia)
        g=growth(step,order,seed.ravel())
        row=dict(case=kind,drain=opened,dt=dt,theta_feedback=theta,acceleration_pressure_feedback=inertia,
            denominator_min=step.den.min(),denominator_max=step.den.max(),**g)
        results.append(row);print(json.dumps(row),flush=True);gc.collect()
    write(dest,results);print(f"{time.perf_counter()-start:.2f}s",flush=True)


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("cache",type=Path)
    ap.add_argument("phase",choices=["geometry","base_open","base_closed","sync_open","sync_closed"])
    ap.add_argument("--order",type=int,default=28)
    a=ap.parse_args();main(a.cache,a.phase,a.order)
