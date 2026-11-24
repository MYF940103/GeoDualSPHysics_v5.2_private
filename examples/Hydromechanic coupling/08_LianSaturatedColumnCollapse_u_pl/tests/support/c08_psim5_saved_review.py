"""Review the saved DDT0 collapse prefix and compare it with the two complete releases."""
import csv
import json
from pathlib import Path
import sys

import numpy as np

CASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CASE / "support"))
import postprocess_lian_release as post
import compare_lian_release as paper
import matplotlib.pyplot as plt

FIG = CASE / "figures/validation_explicit"
OUT = FIG / "saved_comparison"


def negative_history():
    pre = CASE / "CaseLianCollapse_psim5_pre_GPU_out"
    run = CASE / "CaseLianCollapse_psim5_GPU_out"
    log = (run / "Run.out").read_text(encoding="utf-8", errors="replace")
    provenance = json.loads((run / "provenance.json").read_text(encoding="utf-8-sig"))
    post.require(provenance["state"] == "failed" and provenance["group"] == "psim5"
                 and "Finished execution (code=1)" in log, "Expected the failed original receiver")
    fault = next(line for line in log.splitlines() if line.startswith("DynamicPoreWall rejected:"))
    sources = sorted((run / "data").glob("Part_*.bi4"))
    post.require([p.name for p in sources] == [f"Part_{i:04d}.bi4" for i in range(68)],
                 "Expected only the original 68 consecutive particle snapshots")
    material, ref = post.native(pre / "data/Part_1000.bi4")
    post.verify_source_material(material, "psim5")
    start = float(material["TimeStep"])
    z0 = post.native(pre / "data/Part_0000.bi4")[1]["Posd"][post.SOIL_IDS, 2]
    top = abs(z0 - z0.max()) < post.DP / 4
    bottom = abs(z0 - z0.min()) < post.DP / 4
    prev_kappa = ref["Kplastic"][-5000:]
    clocks = np.cumsum(np.r_[start, np.full(134001, post.DT)])
    rows = []
    extremes = []
    for i, source in enumerate(sources):
        meta, fields = post.native(source)
        prev_kappa = post.check_frame(meta, fields, i, False, ref, prev_kappa, start, "psim5")
        step = int(meta["Step"])
        completed = step + 1
        t = float(meta["TimeStep"])
        post.require(0 < completed - 2_000_000 < len(clocks)
                     and t == clocks[completed - 2_000_000]
                     and (not rows or step > rows[-1]["saved_step"]), f"Original scalar clock at {source.name}")
        row = post.measures(fields, ref, top, bottom, i, t, t - start)[0]
        row.update(saved_step=step, completed_step=completed, signed_dterror_s=float(meta["dterror"]))
        rows.append(row)
        p = fields["PorePress"][-5000:].astype("f8") / 1000
        imin = int(p.argmin())
        x, _, z = fields["Posd"][-5000:][imin]
        extremes.append(dict(part=i, tau_s=t-start, time_s=t, minimum_id=int(post.SOIL_IDS[imin]),
                             x_m=x, z_m=z, p_min_kPa=p[imin], p01_kPa=np.quantile(p,.01),
                             p50_kPa=np.median(p), p99_kPa=np.quantile(p,.99), p_max_kPa=p.max(),
                             soil_below_minus_100kPa=int((p < -100).sum()),
                             soil_below_minus_1000kPa=int((p < -1000).sum()),
                             J_at_min=fields["PoroVolumeRatio"][-5000:][imin],
                             fs_type_at_min=int(fields["FSType"][-5000:][imin])))
    post.require(rows[-1]["completed_step"] == 2134001 and "step=2135793 " in fault,
                 "The saved prefix and reported rejection no longer match this case")
    paper.save_rows(OUT / "negative_pressure_extrema.csv", extremes)
    return rows


def comparison_rows(histories):
    with (CASE / "support/lian_collapse_fronts.csv").open(encoding="utf-8", newline="") as f:
        refs = list(csv.DictReader(f))
    rows = []
    for r in refs:
        group = r["group"]
        target = float(r["tau_s"])
        h = histories[group]
        index = np.argmin(np.abs(h["tau_s"] - target))
        data = h[index]
        available = abs(data["tau_s"] - target) <= 5.01e-6
        front = float(r["front_x_m"])
        rows.append(dict(group=group, figure=r["figure"], requested_tau_s=target,
                         paper_front_m=front, paper_kind=r["kind"], readout_scale_m=r["digitization_m"],
                         status="observed" if available else "beyond_last_save",
                         part=int(data["part"]) if available else "",
                         actual_tau_s=float(data["tau_s"]) if available else "",
                         native_front_m=data["front_x_m"] if available else "",
                         native_minus_paper_m=data["front_x_m"]-front if available and r["kind"]=="visible" else ""))
    return rows


def plot(histories, refs):
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.5), layout="constrained", sharex=True)
    metrics = (("front_x_m", "Material front x (m)"), ("top_settlement_mm", "Top material settlement (mm)"),
               ("p_min_kPa", "Minimum / maximum pore pressure (kPa)"), ("nearest_min_dp", "Minimum spacing / dp"))
    for ax, (key, label) in zip(axes.flat, metrics):
        for group, h in histories.items():
            angle, color = paper.GROUPS[group]
            ax.plot(h["tau_s"], h[key], lw=1.7, color=color, label=angle)
            if key == "p_min_kPa":
                ax.plot(h["tau_s"], h["p_max_kPa"], lw=1.1, ls="--", color=color)
            if group == "psim5":
                ax.plot(h["tau_s"][-1], h[key][-1], "|", ms=10, color=color)
        ax.set(ylabel=label, xlim=(-.025,3.06))
        ax.grid(alpha=.22)
    for r in refs:
        ax = axes[0, 0]
        if r["paper_kind"] == "visible":
            ax.scatter(r["requested_tau_s"],r["paper_front_m"],s=35,marker="s",facecolors="white",
                       edgecolors=paper.GROUPS[r["group"]][1],zorder=4)
        else:
            ax.scatter(r["requested_tau_s"],r["paper_front_m"],s=55,marker="$↑$",
                       color=paper.GROUPS[r["group"]][1],zorder=4)
    axes[0,0].set_ylim(top=8.6)
    axes[0,0].text(.02,.96,"□  Lian visible front     ↑  published lower bound",
                   transform=axes[0,0].transAxes,va="top",fontsize=9)
    axes[0,1].legend(title="Initial dilation", frameon=False)
    axes[1,0].text(.98,.96,"solid: minimum    dashed: maximum",transform=axes[1,0].transAxes,
                   va="top",ha="right",fontsize=9)
    axes[1,0].set_yscale("symlog", linthresh=60)
    ticks = [-1000,-300,-100,-50,0,50,100,200]
    axes[1,0].set_yticks(ticks, labels=[str(v) for v in ticks])
    axes[1,0].set_ylabel("Pore pressure (kPa; symmetric log scale)")
    for ax in axes[1]:
        ax.set_xlabel("Time after wall release (s)")
    fig.suptitle("Explicit u-pl collapse without HG or stress diffusion\n"
                 "−5° ends at the last saved frame (0.670005 s)", fontsize=14)
    fig.savefig(OUT / "comparison.png", dpi=165)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    paper.save_rows(OUT / "negative_saved_history.csv", negative_history())
    histories = {group: paper.read_run(group) for group in ("psi0","psi2p5")}
    histories["psim5"] = np.genfromtxt(OUT / "negative_saved_history.csv", names=True, delimiter=",")
    refs = comparison_rows(histories)
    paper.save_rows(OUT / "paper_fronts.csv", refs)
    summary = []
    traces = []
    for group, history in histories.items():
        stats = paper.summarize(group, history)
        if history["tau_s"][-1] < 1:
            stats["front_advance_last_second_m"] = ""
        stats = {key.replace("final_", "last_saved_"): value for key, value in stats.items()}
        stats.update(status="failed_partial" if group=="psim5" else "completed")
        summary.append(stats)
        traces.extend(dict(group=group, **{k: row[k] for k in history.dtype.names}) for row in history)
    paper.save_rows(OUT / "summary.csv",summary)
    paper.save_rows(OUT / "histories.csv",traces)
    plot(histories, refs)


if __name__ == "__main__":
    main()
