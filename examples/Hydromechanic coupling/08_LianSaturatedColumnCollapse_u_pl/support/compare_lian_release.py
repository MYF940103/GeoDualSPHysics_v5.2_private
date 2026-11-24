"""Compare C08 native material fronts with the printed Lian et al. (2023) panels."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from plot_lian_release_fields import plot_group


ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures" / "validation_explicit"
GROUPS = {"psi0": ("0°", "#2366a2"), "psi2p5": ("+2.5°", "#b2570a"), "psim5": ("−5°", "#168173")}
SAMPLES = {"psi0": (0.3, 0.6, 1.2), "psi2p5": (0.3, 0.6, 1.2), "psim5": (0.2, 0.5, 1.6, 3.0)}


def save_rows(path, rows):
    with path.with_suffix(".tmp").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    path.with_suffix(".tmp").replace(path)


def read_run(group):
    path = FIGURES / group / "history.csv"
    history = np.genfromtxt(path, names=True, delimiter=",", encoding="utf-8-sig")
    if (history.shape != (301,) or not np.array_equal(history["part"], np.arange(301))
            or int(history[-1]["completed_step"]) != 2600000
            or np.any(np.diff(history["tau_s"]) <= 0) or abs(history[-1]["tau_s"] - 3) > 1e-8):
        raise ValueError(f"Incomplete release history in {path}")
    return history


def compare(group, history, references):
    paper = sorted((r for r in references if r["group"] == group), key=lambda r: float(r["tau_s"]))
    if tuple(float(r["tau_s"]) for r in paper) != SAMPLES[group]:
        raise ValueError(f"Missing or repeated published panel for {group}")
    comparisons = []
    for ref in paper:
        target = float(ref["tau_s"])
        state = history[np.argmin(np.abs(history["tau_s"] - target))]
        if abs(state["tau_s"] - target) > 5.01e-6:
            raise ValueError(f"{group} has no saved frame at {target} s within one update")
        x = float(ref["front_x_m"])
        lower_bound = ref["kind"] == "lower_bound"
        if ref["kind"] not in {"lower_bound", "visible"}:
            raise ValueError(f"Unknown reference kind {ref['kind']}")
        comparisons.append(dict(group=group, figure=ref["figure"], requested_tau_s=target,
            part=int(state["part"]), actual_time_s=state["time_s"], actual_tau_s=state["tau_s"],
            sph_front_x_m=state["front_x_m"], published_extent_m=x, published_kind=ref["kind"],
            paper_digitization_scale_m=ref["digitization_m"], half_particle_spacing_m=0.02,
            sph_minus_visible_m="" if lower_bound else state["front_x_m"] - x,
            upper_bound_sph_minus_paper_m=state["front_x_m"] - x if lower_bound else "",
            top_settlement_mm=state["top_settlement_mm"], p_min_kPa=state["p_min_kPa"],
            p_max_kPa=state["p_max_kPa"], nearest_min_dp=state["nearest_min_dp"]))
    return comparisons


def front_panel(ax, group, history, comparisons):
    angle, color = GROUPS[group]
    ax.plot(history["tau_s"], history["front_x_m"], color=color, lw=1.7, label="SPH material front")
    for kind, marker, label in (("visible", "s", "Lian visible extent"), ("lower_bound", "^", "Lian panel limit (≥)")):
        subset = [r for r in comparisons if r["published_kind"] == kind]
        if not subset:
            continue
        t = [r["requested_tau_s"] for r in subset]
        x = [r["published_extent_m"] for r in subset]
        ax.scatter(t, x, marker=marker, facecolors="white", edgecolors="black", s=36,
                   label=label, zorder=4, clip_on=False)
        for time, front, r in zip(t, x, subset):
            if kind == "lower_bound":
                ax.annotate("", (time, front+0.25), (time, front+0.04),
                            arrowprops=dict(arrowstyle="->", color="#333333"))
            else:
                ax.errorbar(time, front, yerr=float(r["paper_digitization_scale_m"]), color="black",
                            lw=1, capsize=3)
        if kind == "lower_bound":
            ax.set_ylim(top=max(ax.get_ylim()[1], max(x)+0.4))
    ax.set(xlabel="Time since wall release (s)", ylabel="Front position x (m)", title=f"ψ = {angle}")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8, frameon=False)


def summarize(group, h):
    end = h[-1]
    tail = h[np.argmin(abs(h["tau_s"]-2))]
    return dict(group=group, frames=len(h), actual_end_s=end["time_s"], elapsed_s=end["tau_s"],
        final_front_x_m=end["front_x_m"], final_runout_m=end["runout_m"],
        front_advance_last_second_m=end["front_x_m"]-tail["front_x_m"],
        final_top_settlement_mm=end["top_settlement_mm"], final_rms_speed_m_s=end["speed_rms_m_s"],
        min_p_kPa=h["p_min_kPa"].min(), min_p_tau_s=h["tau_s"][h["p_min_kPa"].argmin()],
        max_p_kPa=h["p_max_kPa"].max(), max_p_tau_s=h["tau_s"][h["p_max_kPa"].argmax()],
        max_speed_m_s=h["speed_max_m_s"].max(), max_kappa=h["kappa_max"].max(),
        min_nn_in_dp=h["nearest_min_dp"].min(), final_nn_in_dp=end["nearest_min_dp"],
        max_soil_with_nearest_under_half_dp=int(h["nearest_below_half_dp"].max()),
        final_soil_with_nearest_under_half_dp=int(end["nearest_below_half_dp"]),
        min_J=h["J_min"].min(), max_J=h["J_max"].max())


def plot_all(groups, histories, matches):
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.0), constrained_layout=True, sharex=True)
    for ax, group in zip(axes, groups):
        front_panel(ax, group, histories[group], matches[group])
    fig.savefig(FIGURES/"paper_fronts.png", dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(10.8, 7.1), constrained_layout=True, sharex=True)
    panels = (("top_settlement_mm", "Top material settlement (mm)"), ("p_mean_kPa", "Mean pore pressure (kPa)"),
              ("speed_rms_m_s", "RMS material speed (m/s)"), ("nearest_below_half_dp", "Soil particles with nearest spacing < 0.5 dp"))
    for ax, (field, label) in zip(axes.flat, panels):
        for group in groups:
            angle, color = GROUPS[group]
            ax.plot(histories[group]["tau_s"], histories[group][field], color=color, label=f"ψ = {angle}", lw=1.4)
        ax.set_ylabel(label, fontsize=9)
        ax.grid(alpha=0.2)
    for ax in axes[-1]:
        ax.set_xlabel("Time since wall release (s)")
    axes[0, 0].legend(fontsize=8, frameon=False)
    fig.savefig(FIGURES/"material_histories.png", dpi=180)
    plt.close(fig)
    save_rows(FIGURES/"material_histories.csv",
              [dict(group=g, actual_tau_s=row["tau_s"], **{field: row[field] for field, _ in panels})
               for g in groups for row in histories[g]])


def write_report(rows, comparisons):
    lines = [
        "# 饱和土柱塌陷三组显式 u-pl 验证",
        "",
        "三组在本组重力预载后撤去右墙，各计算 3 s。下表使用固定材料 ID 和实际保存时钟。"
        "顶层沉降相对于本组撤墙前的状态，向下为正。末秒前缘推进量为 2 s 附近保存帧至末帧的位移。",
        "",
        "| 初始剪胀角 | 末帧前缘 x (m) | 末秒前缘推进 (m) | 末帧顶层沉降 (mm) | 全程孔压范围 (kPa) | 最小近邻距离 / dp |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        angle = GROUPS[row["group"]][0]
        lines.append(f"| {angle} | {row['final_front_x_m']:.3f} | {row['front_advance_last_second_m']:+.4f} | "
                     f"{row['final_top_settlement_mm']:.2f} | {row['min_p_kPa']:.2f} 至 {row['max_p_kPa']:.2f} | "
                     f"{row['min_nn_in_dp']:.3f} |")
    lines.extend(["", "## 与 Lian 等数值结果的几何对比", "",
        "模拟前缘为最右土粒中心，论文读数为图中连续土体的可见边缘。"
        "两种几何表示的尺度差约为半个粒子间距 0.02 m。表中差值保留原坐标。"
        "论文中负角组有两幅图在 8 m 处截断，差值只能给出上界。",
        "", "| 初始剪胀角 | 图号 | 撤墙后时刻 (s) | 模拟前缘 (m) | 论文图读数 (m) | 模拟减论文 (m) |",
        "|---|---:|---:|---:|---:|---:|"])
    for group, matches in comparisons.items():
        for item in matches:
            bounded = item["published_kind"] == "lower_bound"
            delta = item["upper_bound_sph_minus_paper_m"] if bounded else item["sph_minus_visible_m"]
            lines.append(f"| {GROUPS[group][0]} | {item['figure']} | {item['requested_tau_s']:.1f} | "
                         f"{item['sph_front_x_m']:.3f} | {'≥' if bounded else ''}{item['published_extent_m']:.3f} | "
                         f"{'≤' if bounded else ''}{delta:+.3f} |")
    lines.extend(["", "三组使用本组实际材料历史。负角组峰值黏聚力为 7.5 kPa，另外两组为 5 kPa。"
        "组间差异包含黏聚力与剪胀规律的共同影响。图中保留团聚和孔压尖峰；"
        "逐帧极值、极值时刻、运动速度和塑性应变见配套 CSV。",
        "", "[三组前缘图](paper_fronts.png) · [材料历史](material_histories.png) · "
        "[汇总数据](release_summary.csv) · [前缘读图说明](reference/README.md)"])
    (FIGURES/"README.md").write_text("\n".join(lines)+"\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    what = parser.add_mutually_exclusive_group(required=True)
    what.add_argument("--group", choices=list(GROUPS))
    what.add_argument("--all", action="store_true")
    args = parser.parse_args()
    with (ROOT/"support/lian_collapse_fronts.csv").open(encoding="utf-8-sig", newline="") as stream:
        refs = list(csv.DictReader(stream))
    groups = list(GROUPS) if args.all else [args.group]
    histories = {g: read_run(g) for g in groups}
    comparisons = {g: compare(g, histories[g], refs) for g in groups}
    for g in groups:
        dest = FIGURES / g
        fig, ax = plt.subplots(figsize=(6.2, 3.8), constrained_layout=True)
        front_panel(ax, g, histories[g], comparisons[g])
        fig.savefig(dest/"paper_front.png", dpi=180)
        plt.close(fig)
        save_rows(dest/"paper_front.csv", comparisons[g])
        save_rows(dest/"release_summary.csv", [summarize(g, histories[g])])
        plot_group(g, dest)
    if args.all:
        plot_all(groups, histories, comparisons)
        save_rows(FIGURES/"paper_fronts.csv", [row for g in groups for row in comparisons[g]])
        summaries = [summarize(g, histories[g]) for g in groups]
        save_rows(FIGURES/"release_summary.csv", summaries)
        write_report(summaries, comparisons)


if __name__ == "__main__":
    main()
