"""Offline review of the closed C08 nearest-fit and CPU cutoff components."""
from pathlib import Path
import csv
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

base = Path(__file__).resolve().parents[1]
out = base / "outputs/upl_c08_nearest_CPU_r1"
rows = list(csv.DictReader((out / "walls.csv").open(encoding="utf-8")))
done = json.loads((out / "completion.json").read_text(encoding="utf-8"))
cutoff = json.loads((base / "logs/upl_inactive_cutoff_CPU_r1.check.json").read_text(encoding="utf-8"))
assert done["passed"] and cutoff["passed"] and len(rows) == 2060
assert {int(r["native_id"]) for r in rows} == set(range(2060))
near = [r for r in rows if r["physical_near"] == "1"]
retry = [r for r in near if r["retry"] == "1"]
primary = [r for r in near if r["retry"] == "0"]
assert (len(near), len(retry), len(primary)) == (410, 10, 400)
assert all(r["actual_state_called"] == "0" for r in rows if r["physical_near"] == "0")
assert all(r["primary_control_compared"] == r["primary_p_float_bytes_equal"] ==
           r["primary_geometry_reference_derived_errors_equal"] == "1" for r in primary)
assert all(abs(float(r["fit_raw_det"])) >= 1e-3 for r in near)
assert all(float(r["p_error"]) <= float(r["p_budget"]) and
           float(r["J_error"]) <= float(r["J_budget"]) for r in near)

stem = base / "figures/upl_wall_support_review_r1"
check = base / "logs/upl_wall_support_review_r1.check.json"
columns = ["native_id", "mk", "primary_raw_det", "fit_raw_det", "fit_condition",
           "nearest_source_id", "fit_shift_norm", "p_B_reference", "p_B_actual",
           "J_actual", "p_error", "J_error", "p_budget", "J_budget"]
with stem.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(retry)

x = np.arange(10)
fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), constrained_layout=True)
ax = axes[0]
ax.scatter(x, [abs(float(r["primary_raw_det"])) for r in retry],
           marker="x", s=55, label="Original mirror fit")
ax.scatter(x, [abs(float(r["fit_raw_det"])) for r in retry],
           marker="o", s=35, facecolors="none", edgecolors="tab:orange", label="One nearest-source fit")
ax.axhline(1e-3, color="black", ls="--", lw=1, label="Unchanged determinant gate")
ax.set_yscale("symlog", linthresh=1e-5)
ax.set_ylim(0, 0.4)
ax.set_ylabel("Absolute raw MLS determinant (zero retained)")
ax.set_title("The 10 originally rejected wall samples")
ax.legend(fontsize=8, loc="center left", bbox_to_anchor=(0, 0.25))
ax = axes[1]
ax.bar(x, [float(r["p_error"]) for r in retry], color="tab:orange", label="Error at original boundary position")
ax.axhline(max(float(r["p_error"]) for r in primary), color="tab:blue", ls="--", lw=1,
           label="Maximum among 400 unchanged primary samples")
ax.set_ylabel("Absolute prescribed-pressure error [Pa]")
ax.set_title("No particle, mirror position or threshold changed")
ax.set_ylim(0, 0.0025)
ax.text(0.03, 0.93, "410/410 reconstructed; 400 primary pressure values exact\n"
        f"Maximum J error: {max(float(r['J_error']) for r in near):.3g}\n"
        f"Maximum fit-centre shift: {max(float(r['fit_shift_norm']) for r in retry):.3g} m",
        transform=ax.transAxes, va="top", fontsize=9)
ax.legend(fontsize=8, loc="lower left")
for ax in axes:
    ax.set_xticks(x, [r["native_id"] for r in retry], rotation=45)
    ax.set_xlabel("Original wall material ID")
    ax.grid(alpha=0.2)
fig.suptitle("Case08 zero-step field reconstruction; not a gravity or collapse validation", fontsize=11)
fig.savefig(stem.with_suffix(".png"), dpi=180)
plt.close(fig)

result = {
    "stage": "upl_wall_support_review_r1", "passed": True,
    "state_wall_rows": len(rows), "near_reconstructed": len(near),
    "one_nearest_retries": len(retry), "unchanged_primary_pressure_values": len(primary),
    "max_pressure_error_Pa": max(float(r["p_error"]) for r in near),
    "max_J_error": max(float(r["J_error"]) for r in near),
    "retry_det_range": [min(abs(float(r["fit_raw_det"])) for r in retry), max(abs(float(r["fit_raw_det"])) for r in retry)],
    "retry_condition_range": [min(float(r["fit_condition"]) for r in retry), max(float(r["fit_condition"]) for r in retry)],
    "max_fit_shift_m": max(float(r["fit_shift_norm"]) for r in retry),
    "CPU_cutoff_check": "tests/logs/upl_inactive_cutoff_CPU_r1.check.json",
    "figure_and_csv": ["tests/figures/" + stem.with_suffix(s).name for s in [".png", ".csv"]],
    "original_geometry_source_or_output_modified": False,
    "new_solver_decoder_build_or_SHA": False,
    "limits": "Prescribed affine pressure/J only; no nonlinear corner accuracy, force/flux, gravity, plasticity or physical acceptance. Old baseline has no raw J export.",
    "physical_acceptance": False,
}
check.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2))
