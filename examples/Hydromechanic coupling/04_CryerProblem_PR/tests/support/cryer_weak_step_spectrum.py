"""3-D small-strain weak Darcy/traction coupling. Independent three-sweep linearized step."""
import argparse
import json
from pathlib import Path
from cryer_coupled_step_spectrum import (np,sparse,Step,growth,DT,DAMP,BETA,RHOW,ZIMP,LAM,MU,TESTS,need,write)
from cryer_tet_darcy_spectrum import assemble
from cryer_tet_mechanics import TetMechanics

TAG="cryer_weak_step_spectrum_r1"


class Weak:
    def __init__(self,cache):
        self.m=m=TetMechanics(cache)
        m.lam=LAM
        m.mu=MU
        self.surface=np.zeros(m.n,dtype=bool)
        self.surface[m.surface]=True
        self.K=assemble(cache)[-1]
        self.P=[HT.multiply((1/m.mass)[:,None]).tocsr() for HT in m.HT]
        self.BP=sum(D@P for D,P in zip(m.D,self.P)).tocsr()
        self.FP=sum(HT@P for HT,P in zip(m.HT,self.P)).tocsr()
        self.bface=np.column_stack([HT@np.ones(m.n) for HT in m.HT])
        self.volrow=sum(P.T@self.bface[:,j] for j,P in enumerate(self.P))
        self.cnormal=float(self.volrow.sum())
        need(self.cnormal>0 and np.max(abs(self.bface+m.unit_surface_force))<1e-16,"Sealed volume derivative and traction work")

    def setup(self,opened,split="total",constraint=True):
        m=self.m
        self.open=opened
        self.constraint=constraint
        self.L=(self.K+RHOW*(1-DAMP*DT)*self.FP+BETA*DT*self.BP.multiply(m.volume[:,None])).tocsr()
        basis={"total":self.L,"hydraulic":self.K}
        self.den=np.asarray(abs(basis[split]).sum(axis=1)).ravel()
        need(np.all(self.den>0),"Positive denominator")
        self.jac=(sparse.identity(m.n,format="csr")-self.L.multiply((1/self.den)[:,None])).tocsr()

    def pacc(self,p):
        return np.column_stack([P@p for P in self.P])

    def flux_acc(self,a):
        return sum(H@a[:,j] for j,H in enumerate(self.m.HT))

    def terms(self,flat):
        m=self.m
        z=flat.reshape((11,m.n))
        v=z[:3].T/ZIMP
        s=z[3:9].T
        p=z[9].copy()
        if self.open:p[self.surface]=0
        q=1.5*p-.5*z[10]
        if self.open:q[self.surface]=0
        ae=m.internal_stress(s)/m.mass[:,None]
        vh=v+.5*DT*(ae+self.pacc(p)-DAMP*v)
        sh=s+.5*DT*m.elastic_stress(m.strain(v))
        se=s+DT*m.elastic_stress(m.strain(vh))
        vbar=v+DT*(m.internal_stress(sh)/m.mass[:,None]-DAMP*vh)
        a0=m.internal_stress(se)/m.mass[:,None]-DAMP*vbar
        rhs=-RHOW*self.flux_acc(a0)-BETA*m.volume*m.divergence(vbar)
        return p,q,vbar,se,a0,rhs

    def action(self,flat):
        p,q,vbar,se,a0,rhs=self.terms(flat)
        base=rhs/self.den
        sealed_target=-np.einsum("ij,ij->",self.bface,vbar)/DT
        for _ in range(3):
            q=self.jac@q+base
            if self.open:q[self.surface]=0
            elif self.constraint:q+=(sealed_target-self.volrow@q)/self.cnormal
        v=vbar+DT*self.pacc(q)
        # Displacement and linearized volume ratio have passive identity blocks.
        # u1=u0+dt/2(v0+v1), J1=J0+dt B(vh). They feed no force in this fixed-reference diagnostic.
        return np.vstack((v.T*ZIMP,se.T,q,p)).ravel()

    def manufacture(self,seed):
        p,q,vbar,se,a0,rhs=self.terms(seed)
        a=self.m.internal_stress(se)/self.m.mass[:,None]-DAMP*(vbar+DT*self.pacc(q))+self.pacc(q)
        v=vbar+DT*self.pacc(q)
        true=-self.K@q-RHOW*self.flux_acc(a)-BETA*self.m.volume*self.m.divergence(v)
        algebraic=rhs-self.L@q
        free=~self.surface if self.open else np.ones(len(q),dtype=bool)
        relative=np.linalg.norm((true-algebraic)[free])/np.linalg.norm(true[free])
        # Both round residual and offset must follow the unassembled weak form.
        q3=self.action(seed).reshape((11,-1))[9]
        exact_volume=float(np.einsum("ij,ij->",self.bface,vbar+DT*self.pacc(q3)))
        manufactured_right=self.L@q
        fixed=self.jac@q+manufactured_right/self.den-q
        return dict(unassembled_residual_relative=relative,
                    exact_field_fixedpoint_max_Pa=float(max(abs(fixed[free]))),
                    final_net_volume_rate_m3_s=exact_volume,
                    independent_sum_constant_flux=float(sum(self.flux_acc(a))))


def main(cache,opened,order):
    w=Weak(cache)
    rng=np.random.default_rng(20261120)
    seed=rng.normal(size=(11,w.m.n))
    if opened:seed[-2:,w.surface]=0
    seed=seed.ravel()
    tag=TAG+("_open" if opened else "_closed")
    result=TESTS/"figures"/(tag+".csv")
    need(not result.exists(),"Preserve results")
    out=[]
    for split,constraint in ([("hydraulic",True),("total",True)] if opened else
                             [("hydraulic",True),("total",True),("total",False)]):
        w.setup(opened,split,constraint)
        row=dict(open=opened,split=split,enforce_volume=(constraint and not opened),
                 nodes=w.m.n,den_min=w.den.min(),den_max=w.den.max(),**w.manufacture(seed))
        row.update(growth(w,order,seed))
        out.append(row)
        print(json.dumps(row),flush=True)
    write(result,out)


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cache",type=Path)
    ap.add_argument("boundary",choices=["open","closed"])
    ap.add_argument("--order",type=int,default=32)
    a=ap.parse_args()
    main(a.cache,a.boundary=="open",a.order)
