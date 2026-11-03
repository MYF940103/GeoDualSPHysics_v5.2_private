"""Fresh layout-only redraw; preserve the original offline computation and draft PNG."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import NullFormatter

T = Path(__file__).resolve().parents[1]
frozen = json.loads((T / "logs/upl_lian_eq23_review_r1.check.json").read_text(encoding="utf-8"))
source_e = next(e for e in frozen["inputs"] if Path(e["path"]).name == "upl_lian_eq23_review_r1.py")
with Path(source_e["path"]).open("rb") as stream:
    assert hashlib.file_digest(stream, "sha256").hexdigest() == source_e["sha256"]
spec = importlib.util.spec_from_file_location("sealed_eq23_review", T / "support/upl_lian_eq23_review_r1.py")
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)  # Pure helper definitions only; never main/provenance/operator execution.
check_e = r.adopt(T / "logs/upl_lian_eq23_review_r1.check.json")
check = r.read(check_e)
need = r.need
need(check["passed"] and check["review_completed"], "Completed offline computation required")
for e in check["inputs"]:
    if Path(e["path"]).name == "upl_lian_eq23_review_r1.py":
        r.bind(e)
csv_e = next(e for e in check["files"] if Path(e["path"]).name.endswith("_errors.csv"))
data = r.rows(csv_e)
out = T / "figures/upl_lian_eq23_review_r1_errors_clean.png"
record = T / "logs/upl_lian_eq23_review_r1_plot.check.json"
need(not out.exists() and not record.exists(), "Fresh layout paths required")
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 170})
fig, axes = plt.subplots(2, 3, figsize=(13.5, 8.1), sharex=True)
for ri, region in enumerate(r.REGIONS):
    for fi, field in enumerate(("x2", "xz", "cos2pi_x")):
        ax = axes[ri, fi]
        for vi, variant in enumerate(r.VARIANTS):
            for ci, cloud in enumerate(r.CLOUDS):
                a = sorted((d for d in data if d["region"] == region and d["field"] == field and d["variant"] == variant and d["cloud"] == cloud
                            and d["pressure_storage"] == "double_manufactured_pressure"), key=lambda d: float(d["dp"]))
                if a:
                    ax.plot([float(d["dp"]) for d in a], [float(d["relative_tensor_Frobenius_error"]) for d in a], color=r.COLORS[vi],
                            linestyle="-" if ci == 0 else "--", marker="o" if ci == 0 else "s", ms=4, lw=1.5)
        ax.set_xscale("log"); ax.set_yscale("log"); ax.grid(True, which="both", alpha=.2)
        ax.set_title(region.capitalize() + " · " + {"x2": "$p=x^2$", "xz": "$p=xz$", "cos2pi_x": r"$p=\cos(2\pi x)$"}[field])
        ax.set_xticks([1 / 32, 1 / 24, 1 / 16], ["1/32", "1/24", "1/16"])
        ax.xaxis.set_minor_formatter(NullFormatter())
        if fi == 0: ax.set_ylabel("Relative Hessian Frobenius RMS error")
        if ri == 1: ax.set_xlabel("Particle spacing Δp (unit square)")
handles = [Line2D([], [], color=r.COLORS[i], label=r.LABELS[i], lw=2) for i in range(4)] + [Line2D([], [], color="#444", marker="o", label="Ordered"),
           Line2D([], [], color="#444", marker="s", linestyle="--", label="Fixed jitter ±0.08Δp")]
fig.legend(handles=handles, loc="lower center", ncol=3, bbox_to_anchor=(.5, .015), frameon=False)
fig.suptitle("Literal 2D Eq23 diagnostic: tensor error versus spacing", fontsize=16, y=.98)
fig.text(.5, .925, "Double pressure inputs · h=float(1.8Δp) · full/truncated receiver supports · no accuracy threshold", ha="center")
fig.subplots_adjust(top=.86, bottom=.19, hspace=.34, wspace=.25)
fig.savefig(out, dpi=170); plt.close(fig)
inputs = [check_e, csv_e, r.adopt(__file__), r.adopt(T / "support/upl_lian_eq23_review_r1.py")]
for e in inputs: r.bind(e)
for e in r.BOUND.values(): need(r.same(r.entry(e["path"]), e), "Layout input changed")
with record.open("x", encoding="utf-8") as stream:
    json.dump(dict(stage="upl_lian_eq23_review_r1.layout", passed=True, layout_only=True, original_draft_preserved=True,
        independent_final_rehash_performed=True, inputs=list(r.BOUND.values()), files=[r.entry(out)],
        difference="Suppress automatic minor log tick labels; identical original plotted data and major ticks",
        numeric_analysis_reexecuted=False, solver_build_or_operator_executed=False, physical_acceptance=False), stream, indent=2)
    stream.write("\n")
print(json.dumps(dict(passed=True, figure=str(out), receipt=str(record))))
