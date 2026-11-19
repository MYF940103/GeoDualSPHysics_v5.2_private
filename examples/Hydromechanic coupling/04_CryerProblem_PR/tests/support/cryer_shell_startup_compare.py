"""Actual-clock and continuous startup peaks, with observed SPH samples kept separate."""
import os
for key in ("OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","OMP_NUM_THREADS"):
    os.environ[key]="1"
import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar

from cryer_shell_step_response import Evolution, T, N0


def continuous_peak(ev,end,interval):
    # The real fast modes can decay before one native save. Include time zero,
    # logarithmically spaced times near the release and a regular oscillation-resolving grid.
    tt=np.unique(np.r_[0,np.geomspace(1e-11,end,2401),np.linspace(0,end,int(np.ceil(end/interval))+1)])
    pp=ev.pressure(tt)*10000
    cands=[(float(tt[0]),float(pp[0])),(float(tt[-1]),float(pp[-1]))]
    extrema=np.flatnonzero((pp[1:-1]>=pp[:-2])&(pp[1:-1]>pp[2:]))+1
    for i in extrema:
        result=minimize_scalar(lambda tau:-ev.pressure(tau)[0]*10000,bounds=(tt[i-1],tt[i+1]),
                               method="bounded",options={"xatol":1.e-15})
        cands.append((float(result.x),float(-result.fun)))
    return max(cands,key=lambda pair:pair[1])


def main():
    fig=T/"figures"
    target=fig/"cryer_shell_candidate_startup_r1.csv"
    if target.exists(): raise FileExistsError(target)
    rows=[]
    for label,block,history in [
        ("original","cryer_coupled_shell_modes_r1_blocks","cryer_shell_step_old_r1"),
        ("paired_sph","cryer_shell_tet_pair_r1_sph","cryer_shell_step_tet_sph_r1"),
        ("paired_p1","cryer_shell_tet_pair_r1_p1","cryer_shell_step_tet_p1_r1")]:
        clocks=pd.read_csv(fig/(history+"_history.csv"))
        b=np.load(fig/(block+".npz"))
        for name,capacity in (("M0",0),("finite_Kw",N0/2e8)):
            group=clocks[clocks.model==name]
            # Include 0+ for the mathematical maximum; use the 37 genuinely open
            # samples strictly preceding the first original Mandel-window frame.
            end=.004638671875
            obs=group[(group.tau_s>0)&(group.tau_s<end)]
            if len(obs)!=37 or obs.iloc[0].tau_s!=2**-13:
                raise ValueError("Opening clocks")
            saved=obs.continuous_shell_pressure_Pa.idxmax()
            native=obs.observed_SPH_Pa.idxmax()
            ev=Evolution(b,capacity)
            t1,p1=continuous_peak(ev,end,2.e-7)
            t2,p2=continuous_peak(ev,end,1.e-7)
            if abs(t1-t2)>1.e-9 or abs(p1-p2)>1.e-6:
                raise ValueError("Startup peak localization changed upon grid refinement")
            rows.append(dict(candidate=label,model=name,open_clock_count=len(obs),first_tau_s=obs.iloc[0].tau_s,
                component_first_saved_Pa=obs.iloc[0].continuous_shell_pressure_Pa,
                component_sampled_max_Pa=obs.loc[saved].continuous_shell_pressure_Pa,
                component_sampled_max_tau_s=obs.loc[saved].tau_s,
                component_continuous_max_Pa=p2,component_continuous_max_tau_s=t2,
                max_refine_delta_Pa=abs(p1-p2),max_refine_delta_tau_s=abs(t1-t2),
                original_physical_native_first_Pa=obs.iloc[0].observed_SPH_Pa,
                original_physical_native_saved_max_Pa=obs.loc[native].observed_SPH_Pa,
                original_physical_native_saved_max_tau_s=obs.loc[native].tau_s,
                continuum_startup_end_s=end))
    out=pd.DataFrame(rows)
    out.to_csv(target,index=False)
    print(out[["candidate","model","component_first_saved_Pa","component_sampled_max_Pa",
               "component_continuous_max_Pa","component_continuous_max_tau_s","original_physical_native_first_Pa"]].to_string(index=False))


if __name__=="__main__":
    main()
