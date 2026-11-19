"""Graph the saved actual three-dimensional disturbance powers and waveform ablations."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIG=Path(__file__).resolve().parents[1]/"figures"


def main():
    target=FIG/"cryer_coupled_step_spectrum_r1.png"
    if target.exists():raise FileExistsError(target)
    fig,axes=plt.subplots(1,2,figsize=(10,4.1),layout="constrained",sharey=True)
    labels={"actual_lagged":"SPH pressure, lagged velocity",
            "original_sph_sync":"SPH pressure, synchronized velocity",
            "weak_sync":"Weak flux, synchronized velocity"}
    for ax,side in zip(axes,("closed","open")):
        data=pd.read_csv(FIG/f"cryer_weak_step_witness_r1_{side}.csv")
        for name,part in data.groupby("scheme",sort=False):
            ax.plot([0,*part.nstep],[1.,*part.amp],marker="o",ms=3,label=labels[name])
        ax.set(xlabel="Additional steps",title=f"{side.capitalize()} drainage boundary",yscale="log",
               xticks=[0,20,40,60,80,100,120],ylim=(1e-4,1e7))
        ax.axhline(1,color=".4",lw=.7,ls=":")
        ax.grid(alpha=.22,which="major")
    axes[0].set_ylabel("Amplitude relative to the same initial perturbation")
    axes[1].legend(fontsize=8)
    fig.savefig(target,dpi=170)
    plt.close(fig)


if __name__=="__main__":main()
