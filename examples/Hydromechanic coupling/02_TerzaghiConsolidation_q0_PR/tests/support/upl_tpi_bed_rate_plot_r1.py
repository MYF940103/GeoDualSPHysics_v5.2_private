"""Plot near-bed admissible manufactured fields and the saved terminal stress decomposition."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

figures=Path(__file__).resolve().parents[1]/"figures"
output=figures/"upl_tpi_bed_rate_r1.png"
if output.exists():raise RuntimeError("Use the existing scientific figure")
rates=pd.read_csv(figures/"upl_tpi_bed_rate_r1_manufactured.csv")
cells=pd.read_csv(figures/"upl_tpi_bed_cell_r1.csv")
rates=rates[(rates.part==1652)&(rates.field=="quadratic_normal")&(rates.layer<4)]
cells=cells[cells.time_s>=.1]
fig,(ax0,ax1)=plt.subplots(1,2,figsize=(11,4.1),layout="constrained")
old=rates[rates.operator=="original"]
ax0.plot(old.layer,old.mean_exact_s1,"k-",label="Analytical derivative")
for mode,marker,label in (("original","s","Recorded wall operator"),
                          ("plane_quadratic","o","Wall-constrained quadratic fit")):
    r=rates[rates.operator==mode]
    ax0.plot(r.layer,r.mean_rate_s1,marker=marker,mfc="none",ms=8,ls="none",label=label)
ax0.set(xticks=range(4),xlabel="Initial material layer (0 = first soil layer)",
        ylabel=r"Normal velocity gradient ($s^{-1}$)",title=r"Quadratic field $v_z=z^2$ on terminal geometry")
for col,lab in (("original_total_error_Pa","Measured point total-stress error"),
                ("M_log_cell_minus_target_effective_Pa","Stress from cell geometry minus reference"),
                ("M_log_native_J_minus_cell_Pa","Native point J minus geometry (stress units)"),
                ("reference_minus_native_pressure_Pa","Reference minus native pressure")):
    ax1.plot(cells.time_s,cells[col],label=lab)
ax1.axhline(-100,color="k",ls=":",label="Original lower stress limit")
ax1.set(xlabel="Actual saved time (s)",ylabel="Signed stress difference (Pa)",
        title="Bottom material point and its finite cell")
for ax in (ax0,ax1):
    ax.legend(fontsize=8);ax.grid(alpha=.25)
fig.savefig(output,dpi=165)
plt.close(fig)
