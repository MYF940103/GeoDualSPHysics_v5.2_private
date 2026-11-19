"""Compare the three fixed radial models against identical harmonic and opening references."""
import os
for env_key in ("OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","OMP_NUM_THREADS"):
    os.environ[env_key]="1"
from types import SimpleNamespace
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from cryer_coupled_shell_modes import T, Graph, N0


def main():
    figdir=T/"figures"
    table=pd.read_csv(figdir/"cryer_coupled_shell_modes_r1_shells.csv")
    candidates=[
        ("SPH","cryer_coupled_shell_modes_r1_blocks","cryer_shell_step_old_r1"),
        ("Paired force, SPH Darcy","cryer_shell_tet_pair_r1_sph","cryer_shell_step_tet_sph_r1"),
        ("Paired force, P1 Darcy","cryer_shell_tet_pair_r1_p1","cryer_shell_step_tet_p1_r1")]
    paths=[figdir/("cryer_shell_candidate_comparison_r1"+ext) for ext in [".csv",".png"]]
    if any(p.exists() for p in paths): raise FileExistsError("Archived comparison exists")
    rows=[];fig,ax=plt.subplots(1,3,layout="constrained",figsize=(13,4))
    colors=["#424242","#2365a3","#ba5222"]
    for (name,blocks,step),color in zip(candidates,colors):
        with np.load(figdir/(blocks+".npz")) as raw:
            b=SimpleNamespace(**dict(raw))
        for (m,f),group in table.groupby(["model","frequency_Hz"],sort=False):
            u,p=Graph.harmonic(b,2j*np.pi*f,0 if m=="M0" else N0/2e8)
            p0=(group.continuum_p_real+1j*group.continuum_p_imag).to_numpy()
            u0=(group.continuum_u_real_m_per_Pa+1j*group.continuum_u_imag_m_per_Pa).to_numpy()
            rows.append(dict(discretization=name,storage=m,frequency_Hz=f,amplitude_abs=abs(p[0]),
                reference_amplitude_abs=abs(p0[0]),amplitude_error_pct=100*(abs(p[0]/p0[0])-1),
                phase_error_deg=np.angle(p[0]/p0[0],deg=True),center_complex_difference=abs(p[0]-p0[0]),
                pressure_rms_all_20_shells=np.mean(abs(p-p0)**2)**.5,
                radial_u_rms_all_20_shells_m_per_Pa=np.mean(abs(u-u0)**2)**.5))
        tab=pd.read_csv(figdir/(step+"_history.csv")).query("model=='M0'")
        win=tab[tab.tau_s>=.004638671875]
        if name=="SPH":
            ax[0].plot(win.tau_s*1000,win.quasistatic_reference_Pa/1000,label="Continuum M0",c="black",ls="--")
        ax[0].plot(win.tau_s*1000,win.continuous_shell_pressure_Pa/1000,label=name,c=color)
        ax[1].plot(win.tau_s*1000,win.continuous_shell_pressure_Pa-win.quasistatic_reference_Pa,c=color)
        m=[r for r in rows if r["discretization"]==name and r["storage"]=="M0"]
        ax[2].plot([r["frequency_Hz"] for r in m],[r["amplitude_error_pct"] for r in m],c=color,marker="o")
    out=pd.DataFrame(rows)
    baseline=pd.read_csv(figdir/"cryer_coupled_shell_modes_r1_transfer.csv")
    base=out[out.discretization=="SPH"].merge(baseline,left_on=["storage","frequency_Hz"],right_on=["model","frequency_Hz"],validate="one_to_one")
    if max(abs(base.amplitude_abs-base.center_amplitude))>1e-11:
        raise ValueError("Original harmonic controls")
    ax[0].legend(fontsize=8)
    ax[0].set_ylabel("Center pressure (kPa)");ax[1].set_ylabel("Center minus reference (Pa)")
    for a in ax[:2]:a.set_xlabel("Time after drainage opens (ms)")
    ax[2].set_xscale("log");ax[2].set_xlabel("Traction frequency (Hz)")
    ax[2].set_ylabel("Harmonic amplitude error (%)")
    for a in ax:a.grid(alpha=.22)
    fig.suptitle("Cryer M0, fixed 20-shell basis, first 18 material points at r/a=0.05")
    fig.savefig(paths[1],dpi=165);plt.close(fig)
    out.to_csv(paths[0],index=False)


if __name__=="__main__":
    main()
