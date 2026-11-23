"""Conservative weak Darcy flux and the spatially matched solid on the projected Cryer sphere.

The midpoint and matrix exponential are independent time references for the spatial test.
Each pressure shell has its own unknown. All twenty solid displacement shells stay free.
"""
import json
import numpy as np
import pandas as pd
from scipy.linalg import expm, solve
from scipy.optimize import minimize_scalar
from cryer_coupled_shell_modes import T, DT, HYD, RHOW, DAMP
from cryer_tet_mechanics import TetMechanics


TAG="cryer_weak_flux_shell_r1"


def assemble():
    m=TetMechanics(T/"outputs/cryer_tet_reference_r1.npz")
    U=m.x/np.linalg.norm(m.x,axis=1)[:,None]
    basis=np.eye(20)[m.shells-1]
    w=basis.T@m.volume
    mass=basis.T@m.mass
    with np.load(T/"figures/cryer_shell_tet_pair_r1_p1.npz") as data:
        blocks={k:data[k] for k in data.files}
    G=mass[:,None]*blocks["P"]
    K=-w[:,None]*blocks["La"]
    F=np.zeros((20,20))
    for k in range(3):
        F+=(m.D[k]@basis).T@((m.volume*U[:,k])[:,None]*basis)
    trace=F+G.T
    boundary_error=np.max(abs(trace[:-1]))
    assert boundary_error<1e-14 and np.max(abs(F.sum(axis=0)))<1e-14
    assert np.max(abs(K.sum(axis=0)))<1e-12 and np.max(abs(K-K.T))<1e-12
    assert np.allclose(G.T,w[:,None]*blocks["D"],rtol=0,atol=1e-14)
    P=G/mass[:,None]
    hydraulic=K[:-1,:-1]+RHOW*F[:-1]@P[:,:-1]
    spectrum=np.linalg.eigvalsh(hydraulic)
    assert np.min(spectrum)>0 and np.linalg.norm(hydraulic-hydraulic.T)<1e-10
    return blocks["K"],blocks["F"][:,0],K,G,P,F,mass,w,dict(
        interior_integration_by_parts_abs_m2=boundary_error,
        closed_constant_flux_abs_m2=float(np.max(abs(F.sum(axis=0)))),
        open_pressure_schur_minmax_m=spectrum[[0,-1]].tolist())


class Phase:
    def __init__(self,mechanics,drained):
        Ks,ext,K,G,P,F,mass,w,_=mechanics
        self.drain=drained
        self.n=19 if drained else 20
        l=self.n
        I=np.eye(20)
        Afree=np.column_stack((Ks,-DAMP*I,ext))
        Vmap=np.column_stack((np.zeros_like(I),I,np.zeros(20)))
        self.GT=G.T
        self.F=F
        self.K=K
        self.P=P
        self.Ks=Ks
        self.ext=ext
        fluid=(K[:l,:l]+RHOW*F[:l]@P[:,:l])
        right=-G.T[:l]@Vmap/HYD-RHOW*F[:l]@Afree
        if not drained:
            # Replace the dependent sum of the weak rows by d/dt of sealed total volume.
            b=G@np.ones(20)
            fluid[-1]=b@P
            right[-1]=-b@Afree
        self.pmap=solve(fluid,right)
        self.amap=Afree+P[:,:l]@self.pmap
        self.generator=np.zeros((41,41));self.generator[:20,20:40]=I
        self.generator[20:40]=self.amap
        self.map=expm(DT*self.generator)
        self.mid=solve(np.eye(41)-.5*DT*self.generator,np.eye(41)+.5*DT*self.generator)

    def measure(self,state):
        p=self.pmap@state
        if self.drain:p=np.r_[p,0.]
        a=self.amap@state
        flux=HYD*(self.K@p+RHOW*self.F@a)
        volrate=self.GT@state[20:40]
        return p, a, volrate, flux


def march(method,ops,ref):
    c,o=(Phase(ops,s) for s in (False,True))
    y=np.zeros(41)
    row=[]; profiles=[]; opening=None
    for end in range(36865):
        q=10000*min(max(end-1,0)/2048,1)
        y[-1]=q
        phase=o if end>4096 else c
        if end:
            y=getattr(phase,method)@y
        if end==4096:
            opening=y.copy()
        if end%64!=0 and end not in (4097,4098,4100,4104,4112,4128):continue
        p,a,vr,fl=phase.measure(y)
        eq=vr+fl
        n=phase.n
        row.append(dict(method=method,step=end,tau_s=end*DT-.0078125,
                        source_Pa=q,center_Pa=p[0],surface_inward_mm=-1000*y[19],
                        shell17_Pa=p[16],shell18_Pa=p[17],boundary_Pa=p[-1],max_speed_m_s=max(abs(y[20:40])),
                        unconstrained_balance_m3_s=max(abs(eq[:n])),
                        total_volume_rate_m3_s=sum(vr),outward_relative_flux_m3_s=-eq[-1] if phase.drain else 0.))
        if end in (4096,4097,4160,4096+64*344,36864):
            for j in range(20):
                profiles.append(dict(method=method,step=end,shell=j+1,r_over_a=(j+1)/20,p_Pa=p[j],
                                     inward_mm=-1000*y[j],radial_acc_m_s2=a[j]))
    tab=pd.DataFrame(row)
    post=tab.merge(ref[["completed_step","legacy_Tv","M0_r18_Pa","center18_Pa","shell_inward_mm"]],
                   left_on="step",right_on="completed_step",validate="one_to_one")
    w=post[post.legacy_Tv>=.005]
    peak=w.loc[w.center_Pa.idxmax()]
    pw=tab[tab.step.between(3904,4096)]
    result=dict(sample_peak_Pa=float(peak.center_Pa),sample_peak_tau_s=float(peak.tau_s),
                center_window_RMS_Pa=float(np.mean((w.center_Pa-w.M0_r18_Pa)**2)**.5),
                first_open_center_Pa=float(tab.loc[tab.step==4097,"center_Pa"].iloc[0]),
                open64_center_Pa=float(tab.loc[tab.step==4160,"center_Pa"].iloc[0]),
                closed_p_last4_abs_err_Pa=max(abs(pw.center_Pa-10000)),
                closed_max_speed_last4_m_s=pw.max_speed_m_s.max(),
                max_weak_free_balance_m3_s=tab.unconstrained_balance_m3_s.max(),
                max_boundary_volume_mismatch_m3_s=max(abs(tab.total_volume_rate_m3_s+tab.outward_relative_flux_m3_s)),
                u_at_center_peak_surface_inward_mm=float(peak.surface_inward_mm))
    if method=="map":
        pfull=lambda t: float(o.pmap[0]@(expm(t*o.generator)@opening))
        opt=minimize_scalar(lambda t:-pfull(t),bounds=(peak.tau_s-.0003,peak.tau_s+.0003),method="bounded",
                            options={"xatol":1.e-13})
        result.update(continuous_peak_Pa=-opt.fun,continuous_peak_tau_s=opt.x,
                      amplitude_error_pct=100*(-opt.fun/12478.53263299281-1),
                      phase_error_pct=100*(opt.x/.04192258568544373-1))
    return tab,profiles,result


def main():
    outputs=[T/"figures"/(TAG+s) for s in ("_history.csv","_profiles.csv",".png")]
    check=T/"logs"/(TAG+".check.json")
    if any(x.exists() for x in [*outputs,check]):raise FileExistsError(TAG)
    ref=pd.read_csv(T/"figures/cryer_p3_server_peak_actual_r1/physical/native_and_theory.csv")
    ops=assemble()
    ts=[];profiles=[];report={}
    for method in ("map","mid"):
        t,prof,rep=march(method,ops,ref)
        ts.append(t);profiles.extend(prof);report[method]=rep
    report["time_reference_max_center_difference_Pa"]=float(abs(ts[0].center_Pa-ts[1].center_Pa).max())
    pd.concat(ts).to_csv(outputs[0],index=False)
    pd.DataFrame(profiles).to_csv(outputs[1],index=False)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axs=plt.subplots(1,3,figsize=(13,3.5),layout="constrained")
    t=ts[0];post=t[t.step>=4096];old=ref[ref.completed_step>=4096]
    for ax,mx in zip(axs[:2],[2,62.5]):
        ax.plot(old.tau_s*1000,old.M0_r18_Pa/1000,"k--",label="M0 analytical")
        ax.plot(old.tau_s*1000,old.center18_Pa/1000,color="#be6331",label="Original 3D P3")
        ax.plot(post.tau_s*1000,post.center_Pa/1000,color="#236a99",label="Weak-flux 20 shells")
        ax.set(xlim=(0,mx),xlabel="Time after opening (ms)",ylabel="Pressure at r/a=0.05 (kPa)")
    true_surface=pd.read_csv(T/"figures/cryer_true_surface_old_r1.csv")
    old_surface=old.merge(true_surface[["completed_step","surface_mm"]],on="completed_step",validate="one_to_one")
    axs[2].plot(old_surface.tau_s*1000,old_surface.surface_mm,color="#be6331",label="Original 3D P3")
    axs[2].plot(post.tau_s*1000,post.surface_inward_mm,color="#236a99",label="Weak-flux 20 shells")
    axs[2].set(xlabel="Time after opening (ms)",ylabel="Surface inward motion (mm)")
    for ax in axs:ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.savefig(outputs[2],dpi=160);plt.close(fig)
    report["patch"]=ops[-1]
    report["scope"]="Fixed 20-shell Galerkin reference, all 20 motions free, instantaneous M0 pressure closure and conservative weak Darcy flux. No P3/AV/production or three-dimensional peak claim."
    check.write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
