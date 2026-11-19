"""Time-continuous shell response to opening drainage at uniform undrained equilibrium."""
import os
for env_key in ("OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","OMP_NUM_THREADS"):
    os.environ[env_key]="1"
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.linalg import eig, expm, solve
from scipy.optimize import minimize_scalar

from cryer_coupled_shell_modes import T, DP, R, LAM, MU, RHO, RHOW, HYD, DAMP, N0, LONG


def check(test, message):
    if not test:
        raise ValueError(message)


class Evolution:
    """Pressure stored at 19 free shells; the shell at r=R is prescribed drained."""
    def __init__(self, blocks, storage):
        keep=slice(0,19)
        k=blocks["K"]; pforce=blocks["P"][:,keep]
        d=blocks["D"][keep]; dk=blocks["DK"][keep]
        da=blocks["DP"][keep,keep]; lap=blocks["La"][keep,keep]
        a=HYD*(lap+RHOW*da)
        b=HYD*RHOW*dk
        c=-(1+HYD*RHOW*DAMP)*d
        # Shift the constant held compressive load into the exactly drained final state.
        # Use physical u,v before applying a diagonal unit conversion for exponentiation.
        bulk=LAM+2*MU/3
        r=DP*np.arange(1,21)
        u_end=-r/(3*bulk)
        check(np.max(abs(k@u_end+blocks["F"][:,0]))<1.e-10, "Static skeleton traction")
        check(np.max(abs(dk@u_end+blocks["DF"][keep,0]))<3.e-7,"Static acceleration in Darcy")
        p_closed=1/(1+bulk*storage)
        u_closed=-r*storage*p_closed/3
        I=np.eye(20)
        z=np.zeros_like(I)
        if storage==0:
            pressure_map=-solve(a,np.column_stack((b,c)))
            generator=np.block([[z,I],[k,-DAMP*I]])+np.vstack((z,pforce@pressure_map[:,:20]))@np.hstack((I,z))
            generator[20:,20:]+=pforce@pressure_map[:,20:]
            state=np.r_[u_closed-u_end,np.zeros(20)]
            self.algebraic_residual=float(np.max(np.abs(a@pressure_map+np.c_[b,c])/np.maximum(1.,np.max(abs(np.c_[b,c]),axis=0))))
            check(self.algebraic_residual<1.e-12,"M0 elimination")
        else:
            generator=np.block([[z,I,np.zeros((20,19))],
                                [k,-DAMP*I,pforce],
                                [b/storage,c/storage,a/storage]])
            state=np.r_[u_closed-u_end,np.zeros(20),np.full(19,p_closed)]
            pressure_map=np.hstack((np.zeros((19,40)),np.eye(19)))
            self.algebraic_residual=None
        units=np.r_[np.full(20,R/LONG),np.full(20,1000*R/LONG),np.ones(len(state)-40)]
        self.mat=generator*units[None,:]/units[:,None]
        self.y0=state/units
        self.obs=pressure_map*units[None,:]
        self.poles,vec=eig(self.mat)
        self.spectral_abscissa=float(self.poles.real.max())
        self.vec_cond=float(np.linalg.cond(vec))
        self.residues=(self.obs@vec)*solve(vec,self.y0)[None,:]
        self.initial_closed_pressure=p_closed

    def pressure(self,t,all_shells=False):
        t=np.atleast_1d(t)
        obs=self.residues if all_shells else self.residues[0]
        series=obs@np.exp(self.poles[:,None]*t[None,:])
        check(np.max(abs(series.imag))<1.e-6*max(1,np.max(abs(series.real))),"Complex-pair cancellation")
        return series.real

    def crosscheck(self,times):
        direct=np.stack([self.obs@expm(self.mat*t)@self.y0 for t in times],axis=1)
        residual=float(np.max(abs(direct-self.pressure(times,all_shells=True))))
        check(residual<5.e-6,"Complex eigensystem versus independent matrix exponential")
        return residual


def main():
    import argparse
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("tag")
    ap.add_argument("blocks",type=Path)
    args=ap.parse_args()
    targets=[T/folder/(args.tag+suffix) for folder,suffix in [
        ("figures","_history.csv"),("figures","_peak.csv"),("logs",".check.json"),("figures",".png")]]
    check(not any(path.exists() for path in targets),"Existing result")
    ref=pd.read_csv(T/"figures/cryer_p3_server_peak_actual_r1/physical/matched_center_diagnosis.csv")
    post=ref[ref.tau_s>=0]
    check(len(post)==513 and len(post[post.legacy_Tv>=.005])==475,"Actual-clock ledger")
    times=post.tau_s.to_numpy()
    blocks=np.load(args.blocks)
    q=10000.
    histories=[];summary=[];checks={}
    for name,capacity,ref_col,ref_peak,ref_time in [
        ("M0",0,"B_M0_Pa",12478.53263299281,.04192258568544373),
        ("finite_Kw",N0/2e8,"A_finite_Kw_Pa",12439.176,.04205180291164746)]:
        ev=Evolution(blocks,capacity)
        if ev.spectral_abscissa>1.e-6:
            checks[name]={"stable":False,"max_real_eigenvalue_per_s":ev.spectral_abscissa}
            continue
        independent=ev.crosscheck(np.array([0,.004638671875,.02,.0419921875,.0625]))
        p=q*ev.pressure(times)
        raw=post.B_pressure_Pa if name=="M0" else post.A_pressure_Pa
        for part,t,press,theory,native in zip(post.part,times,p,post[ref_col],raw):
            histories.append(dict(model=name,retained_part=int(part),tau_s=t,continuous_shell_pressure_Pa=press,
                                  quasistatic_reference_Pa=theory,observed_SPH_Pa=native,at_preopen_native=(t==0)))
        win=post.legacy_Tv.to_numpy()>=.005
        # Resolve every oscillatory mode within the physical peak window before polishing the maximum.
        dt=min(3.e-6,2*np.pi/max(1.,np.max(abs(ev.poles.imag)))/24)
        grid=np.linspace(times[win][0],times[-1],int(np.ceil((times[-1]-times[win][0])/dt))+1)
        yp=q*ev.pressure(grid)
        idx=int(np.argmax(yp))
        loc=np.flatnonzero((yp[1:-1]>=yp[:-2])&(yp[1:-1]>yp[2:]))+1
        if 0<idx<len(yp)-1:
            fit=minimize_scalar(lambda t:-q*ev.pressure(t)[0],bounds=(grid[idx-1],grid[idx+1]),
                                method="bounded",options={"xatol":1.e-14})
            peak_tau,peak=fit.x,-fit.fun
        else:
            peak_tau,peak=grid[idx],yp[idx]
        pos=np.flatnonzero(win)[int(np.argmax(p[win]))]
        summary.append(dict(model=name,sampled_peak_Pa=p[pos],sampled_peak_tau_s=times[pos],
                            continuous_peak_Pa=peak,continuous_peak_tau_s=peak_tau,
                            reference_peak_Pa=ref_peak,reference_peak_tau_s=ref_time,
                            amplitude_diff_pct=100*(peak/ref_peak-1),phase_diff_pct=100*(peak_tau/ref_time-1),
                            matched_reference_RMS_Pa=float(np.sqrt(np.mean((p[win]-post[ref_col].to_numpy()[win])**2))),
                            closed_center_Pa=q*ev.initial_closed_pressure,opening_center_limit_Pa=p[0],
                            local_maxima_in_window=len(loc),modal_peak_grid_max_spacing_s=dt))
        checks[name]=dict(stable=True,static_pressure_limit=0.,max_real_eigenvalue_per_s=ev.spectral_abscissa,
                          eigenbasis_condition=ev.vec_cond,eigen_expm_abs_pressure_per_Pa=independent,
                          M0_elimination_error=ev.algebraic_residual)
    if histories:
        pd.DataFrame(histories).to_csv(targets[0],index=False)
        pd.DataFrame(summary).to_csv(targets[1],index=False)
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(1,2,figsize=(10,3.7),layout="constrained")
        for name,tab in pd.DataFrame(histories).groupby("model",sort=False):
            axes[0].plot(tab.tau_s*1000,tab.continuous_shell_pressure_Pa/1000,label=name+" shell response")
            axes[1].plot(tab.tau_s*1000,tab.continuous_shell_pressure_Pa-tab.quasistatic_reference_Pa,label=name)
        axes[0].plot(times*1000,post.B_M0_Pa/1000,"k--",label="M0 continuum reference")
        axes[0].set_ylabel("Pressure at r/a=0.05 (kPa)")
        axes[1].set_ylabel("Shell model minus matched reference (Pa)")
        for ax in axes:
            ax.grid(alpha=.22);ax.legend(fontsize=8);ax.set_xlabel("Time after drainage opens (ms)")
        axes[1].set_xlim(times[win][0]*1000,62.5)
        diff=pd.DataFrame(histories)
        dv=diff[diff.tau_s>=times[win][0]]
        error=dv.continuous_shell_pressure_Pa-dv.quasistatic_reference_Pa
        axes[1].set_ylim(error.min()-10,error.max()+10)
        fig.savefig(targets[3],dpi=160);plt.close(fig)
    targets[2].write_text(json.dumps(dict(source_blocks=str(args.blocks),models=checks,
        published_quasistatic_references="actual r/a=.05, ideal uniform undrained state at opening",
        native_t0_is_preopen=True, model_t0_is_right_hand_limit=True, time_integrator="continuous matrix exponential",
        removed_angular_response=True, real_P3_update=False,solver_runs=0,summary=summary),indent=2)+"\n",encoding="utf8")
    print(json.dumps({"models":checks,"summary":summary}))


if __name__=="__main__":
    main()
