"""Replot one existing staged-load difference table with readable labels, no reanalysis."""
import csv,json,os
from pathlib import Path
for key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS"):os.environ[key]="1"
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
T=Path(__file__).resolve().parents[1]
SOURCE=T/"figures/upl_tpi_p1_loadclock_window_review_r1.differences.csv"
OUT=T/"figures/upl_tpi_p1_loadclock_window_review_r1.differences_readable_r2.png"
CHECK=T/"logs/upl_tpi_p1_diff_plot_r2.check.json"
def stat(p):
 s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
assert not OUT.exists()and not CHECK.exists()
before=stat(SOURCE)
with SOURCE.open(encoding="utf-8-sig",newline="")as f:rows=list(csv.DictReader(f))
assert len(rows)==1263 and [int(r["part"])for r in rows]==list(range(1263))
time=[float(r["actual_time_s"])for r in rows]
fields=[("new_minus_old_top10_settlement_mm","Top-material settlement change (mm)"),("new_minus_old_abs_top_settlement_signed_error_mm","Change in absolute top error (mm)"),("native_pressure_RMS_difference_Pa","Pressure RMS difference (Pa)"),("material_XYZ_max_difference_mm","Maximum material displacement difference (mm)"),("new_minus_old_Q_total_zz_second_difference_RMS_Pa","Change in total-stress curvature Q (Pa)"),("new_minus_old_J_mean","Change in mean J")]
fig,axes=plt.subplots(3,2,figsize=(13,10),layout="constrained")
for ax,(key,label)in zip(axes.flat,fields):
 ax.plot(time,[float(r[key])if r[key] else float("nan")for r in rows],lw=1.)
 ax.set(xlabel="Exactly shared actual time (s)",ylabel=label);ax.grid(True,alpha=.3)
fig.suptitle("Staged load clock minus original clock: same step, times and material IDs",fontsize=13)
fig.savefig(OUT,dpi=180);plt.close(fig)
assert stat(SOURCE)==before
with CHECK.open("x",encoding="utf8",newline="\n")as f:json.dump(dict(stage="upl_tpi_p1_diff_plot_r2",passed=True,source=before,script=stat(Path(__file__)),output=stat(OUT),rows=1263,original_plot_and_CSV_preserved=True,no_smoothing_or_clipping=True,solver_invocations=0,native_invocations=0,SHA_scans=0,physical_acceptance=False),f,indent=2);f.write("\n")
print(OUT)
