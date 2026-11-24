"""Plot retained no-HG C08 pressure fields against Lian et al. (2023), Figs. 16–17."""
import csv
import hashlib
import json
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib.lines import Line2D
import numpy as np

CASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CASE / "support"))
from digitize_lian_collapse_fronts import connected_body, load_pages
from postprocess_lian_release import DP, SOIL_IDS, native, verify_source_material

OUT = CASE / "tests/figures/c08_lian_partial_r1"
REF = CASE / "figures/validation_explicit/reference"
CACHE = CASE / "tests/figures"
PDF = CASE.parents[2] / "src/papers/PDF/Lian 2023 u-pl.pdf"
# Per-row ticks on the original 180 dpi page: (0 m, 8 m, bed, 2 m) in pixels.
FIG16_TICKS = {
    .01: ((166, 660, 1051, 927), (713, 1207, 1050, 926)),
    .50: ((164, 658.5, 1262, 1138), (712, 1210, 1262, 1137)),
    1.2: ((168, 663.5, 1482, 1358), (714, 1217, 1483, 1357)),
}
GEOMETRY = "#7995a9"
EDGE = "#9b361e"


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def source_record(path):
    return {"path": Path(os.path.relpath(path, CASE)).as_posix(),
            "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def load_run(group, parts, sources):
    folder = CASE / f"CaseLianCollapse_{group}_GPU_out"
    preload = CASE / f"CaseLianCollapse_{group}_pre_GPU_out/data/Part_1000.bi4"
    sources.extend([preload, folder / "Run.out", folder / "provenance.json"])
    pre_meta, pre_state = native(preload)
    verify_source_material(pre_meta, group)
    source_time = pre_meta["TimeStep"]
    frames = {}
    for part in parts:
        file = folder / f"data/Part_{part:04d}.bi4"
        meta, arrays = native(file)
        mask = arrays["Idp"] >= SOIL_IDS[0]
        assert np.array_equal(arrays["Idp"][mask], SOIL_IDS)
        assert meta["GravityPreloadActualTime"] == source_time and meta["Cpart"] == part
        assert np.array_equal(arrays["PorePress0"][mask], pre_state["PorePress0"][SOIL_IDS])
        assert np.array_equal(arrays["ExcessPorePress"][mask],
                              arrays["PorePress"][mask] - arrays["PorePress0"][mask])
        pos = arrays["Posd"][mask]
        time = float(meta["TimeStep"])
        tau = time - source_time
        assert abs(tau - part / 100) <= 5.01e-6
        frames[part] = {"part": part, "time_s": time, "tau_s": tau, "x": pos[:, 0], "z": pos[:, 2],
                        "total": arrays["PorePress"][mask].astype("f8") / 1000,
                        "excess": arrays["ExcessPorePress"][mask].astype("f8") / 1000}
        assert all(np.isfinite(frames[part][k]).all() for k in ("x", "z", "total", "excess"))
        sources.append(file)
    return frames


def panel16(page, ticks):
    x0, x8, bed, z2 = ticks
    left, right, top = int(x0) - 3, int(np.ceil(x8)) + 3, z2 - 4
    crop = page[top:bed + 2, left:right + 1]
    body = connected_body(crop, 16, 55)
    rgba = np.dstack((crop, 255 * body.astype(np.uint8)))
    sx, sz = 8 / (x8 - x0), 2 / (bed - z2)
    extent = ((left - x0 - .5)*sx, (right - x0 + .5)*sx, -1.5*sz, (bed - top + .5)*sz)
    return rgba, extent


def axes_style(ax, label="", bottom=True):
    ax.set(xlim=(-.05, 8.1), ylim=(-.04, 2.16), aspect="equal", yticks=(0, 1, 2),
           xticks=(0, 2, 4, 6, 8))
    ax.tick_params(length=2.3, labelsize=8, labelbottom=bottom)
    ax.spines[["right", "top"]].set_visible(False)
    for side in ("bottom", "left"):
        ax.spines[side].set_color("#8a939b")
    if label:
        ax.set_ylabel(label, fontsize=9)
    if bottom:
        ax.set_xlabel("x (m)", fontsize=8, labelpad=1)


def colorbar(fig, rect, palette, label):
    scalar = plt.cm.ScalarMappable(norm=colors.Normalize(-10, 20, clip=True), cmap=palette)
    bar = fig.colorbar(scalar, cax=fig.add_axes(rect), orientation="horizontal", ticks=[-10, 0, 10, 20])
    bar.ax.tick_params(labelsize=8, length=2)
    bar.set_label(label, fontsize=9, labelpad=2)


def native_pressure(ax, frame, field, cmap):
    ax.scatter(frame["x"], frame["z"], c=frame[field], s=2.5, linewidths=0,
               cmap=cmap, norm=colors.Normalize(-10, 20, clip=True))


def summary(figure, tau, field, frame, reference=None):
    row = dict(figure=figure, group="psim5" if figure == 17 else "psi2p5", nominal_tau_s=tau,
               paper_field=field, native_field="PorePress" if field == "PWP" else "ExcessPorePress",
               native_status="available" if frame is not None else "unavailable",
               display_min_kPa=-10, display_max_kPa=20, part="", time_s="", tau_s="",
               native_front_x_m="", paper_front_x_m="", paper_front_kind="", digitization_scale_m="",
               native_minus_paper_front_m="", n="", min_kPa="", p05_kPa="", median_kPa="", p95_kPa="",
               max_kPa="", below_color_count="", above_color_count="", outside_color_fraction="",
               positive_count="", positive_fraction="")
    if reference:
        row.update(paper_front_x_m=float(reference["front_x_m"]),
                   paper_front_kind=reference["kind"], digitization_scale_m=float(reference["digitization_m"]))
    if frame is None:
        return row
    p = frame["total" if field == "PWP" else "excess"]
    below, above, positive = (int(np.count_nonzero(test)) for test in (p < -10, p > 20, p > 0))
    x = float(frame["x"].max())
    q = np.percentile(p, [0, 5, 50, 95, 100])
    row.update(part=frame["part"], time_s=frame["time_s"], tau_s=frame["tau_s"],
               native_front_x_m=x, n=p.size, min_kPa=q[0], p05_kPa=q[1], median_kPa=q[2],
               p95_kPa=q[3], max_kPa=q[4], below_color_count=below, above_color_count=above,
               outside_color_fraction=(below + above)/p.size, positive_count=positive,
               positive_fraction=positive/p.size)
    if reference and reference["kind"] == "visible":
        row["native_minus_paper_front_m"] = x - row["paper_front_x_m"]
    return row


def figure16(page, frames, rows):
    fig, axes = plt.subplots(3, 3, figsize=(13.7, 6.4))
    fig.subplots_adjust(left=.065, right=.982, bottom=.19, top=.84, hspace=.15, wspace=.14)
    fig.suptitle("Dilative soil   ·   Total pore-water pressure", x=.065, y=.982, ha="left",
                 fontsize=17, fontweight="bold")
    fig.text(.065, .92, "ψ = +2.5°     |     Lian et al. (2023), Fig. 16 and the C08 explicit solution",
             fontsize=10, color="#45505b")
    headings = ("Lian (a)   Stabilized", "Lian (b)   Non-stabilized", "C08   Explicit u–pˡ")
    palette = colors.ListedColormap(page[937, 446:612] / 255.)
    for index, (tau, ticks) in enumerate(FIG16_TICKS.items()):
        current = axes[index]
        for ax, calibration in zip(current[:2], ticks):
            pixels, extent = panel16(page, calibration)
            ax.imshow(pixels, extent=extent, origin="upper", interpolation="nearest")
        frame = frames[int(round(100*tau))]
        native_pressure(current[2], frame, "total", palette)
        rows.append(summary(16, tau, "PWP", frame))
        for col, ax in enumerate(current):
            axes_style(ax, f"{tau:g} s\nz (m)" if col == 0 else "", index == 2)
            if index == 0:
                ax.set_title(headings[col], fontsize=11, loc="left", fontweight="bold")
    colorbar(fig, [.33, .095, .34, .015], palette, "Total pore-water pressure (kPa)")
    fig.text(.065, .018, "Paper columns retain the printed soil colors. C08 uses 5,000 particle centers per frame.",
             fontsize=9, color="#45505b")
    fig.savefig(OUT / "fig16_total.png", dpi=165, facecolor="white")
    plt.close(fig)


def figure17(times, rows, frames, samples, outline, last_tau, destination):
    single = len(times) == 1
    fig = plt.figure(figsize=(13.7, 3.75 if single else 8.55))
    grid = fig.add_gridspec(len(times), 3, left=.065, right=.982, bottom=.31 if single else .16,
                            top=.71 if single else .877, hspace=.19, wspace=.14)
    fig.suptitle("Contractive soil   ·   Geometry and pore-water pressure", x=.065, y=.978,
                 ha="left", fontsize=17, fontweight="bold")
    fig.text(.065, .863 if single else .924,
             f"ψ = −5°     |     Lian et al. (2023), Fig. 17     |     Last saved C08 frame at {last_tau:.6f} s",
             fontsize=10, color="#45505b")
    palette = colors.ListedColormap(samples["f17_palette"] / 255.)
    headings = ("Lian   Published pressure colors", "C08   Material excess pressure", "C08 centers and published outline")
    for index, tau in enumerate(times):
        result = rows[tau]
        bottom = single or index == len(times) - 1
        ax = fig.add_subplot(grid[index, 0])
        key = f"f17_t{int(round(10*tau))}"
        ax.imshow(samples[key], extent=samples[key + "_extent"], origin="upper", interpolation="nearest")
        axes_style(ax, f"{tau:g} s\nz (m)", bottom)
        if index == 0:
            ax.set_title(headings[0], loc="left", fontsize=10, fontweight="bold")
        if result["paper_front_kind"] == "lower_bound":
            ax.axvline(8, color="#555c61", ls=":", lw=.8)
            ax.text(.985, .92, ("Total PWP" if tau == 3 else "Excess pressure") + "  ·  x ≥ 8 m",
                    va="top", ha="right", transform=ax.transAxes, fontsize=8)
        frame = frames.get(int(round(100*tau)))
        if frame is None:
            unavailable = fig.add_subplot(grid[index, 1:])
            unavailable.set_axis_off()
            unavailable.text(.5, .48, "Simulation unavailable", ha="center", va="center",
                             transform=unavailable.transAxes, color="#68727b", fontsize=11)
            continue
        pressure = fig.add_subplot(grid[index, 1])
        geom = fig.add_subplot(grid[index, 2])
        native_pressure(pressure, frame, "excess", palette)
        geom.scatter(frame["x"], frame["z"], s=2.1, linewidths=0, color=GEOMETRY)
        edge = outline[outline["tau_s"] == tau]
        assert len(edge)
        geom.scatter(edge["x_m"], edge["z_m"], s=2.3, linewidths=0, color=EDGE)
        for col, plot in enumerate((pressure, geom), 1):
            axes_style(plot, bottom=single or index == 1)
            if index == 0:
                plot.set_title(headings[col], loc="left", fontsize=10, fontweight="bold")
        geom.text(.982, .82, f'Front difference\n{result["native_minus_paper_front_m"]:+.2f} m',
                  transform=geom.transAxes, ha="right", va="center", fontsize=8, color="#394651")
    y = .17 if single else .085
    colorbar(fig, [.10, y, .29, .018 if single else .013], palette, "Printed pressure scale (kPa)")
    handles = [Line2D([], [], marker="o", ls="none", ms=5, color=color, label=name)
               for color, name in ((GEOMETRY, "C08 soil centers"), (EDGE, "Published visible edge"))]
    fig.legend(handles=handles, bbox_to_anchor=(.53, y + .012), loc="center left", ncol=2,
               fontsize=9, frameon=False, handletextpad=.35)
    fig.text(.065, .025, "C08 excess pressure uses each particle’s initial pressure. "
             "The paper attributes excess pressure to plastic contraction.", fontsize=9, color="#45505b")
    fig.savefig(OUT / destination, dpi=165, facecolor="white")
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    page21 = CACHE / "c08_h18_lian2023_ref-21.png"
    page22 = CACHE / "c08_h18_lian2023_ref-22.png"
    page, _ = load_pages(CACHE, PDF)
    neg_output = CASE / "CaseLianCollapse_psim5_GPU_out"
    saves = sorted((neg_output / "data").glob("Part_*.bi4"))
    if [p.name for p in saves] != [f"Part_{i:04d}.bi4" for i in range(68)]:
        raise ValueError("Expected the retained consecutive partial release ending at PART 0067")
    if "Finished execution (code=1)." not in (neg_output / "Run.out").read_text(errors="replace"):
        raise ValueError("Expected the retained failed −5° release")
    fronts = CASE / "support/lian_collapse_fronts.csv"
    outline_file = CASE / "support/lian_collapse_outline.csv"
    samples_file = REF / "paper_pressure_samples.npz"
    sources = [Path(__file__), Path(sys.modules["postprocess_lian_release"].__file__),
               Path(sys.modules["digitize_lian_collapse_fronts"].__file__),
               Path(sys.modules["upl_tpi_partial_bi4_r1"].__file__), fronts, outline_file, samples_file]
    sources.extend([page21, page22] if page21.exists() and page22.exists() else [PDF])
    neg = load_run("psim5", [20, 50, 67], sources)
    pos = load_run("psi2p5", [1, 50, 120], sources)
    references = {float(r["tau_s"]): r for r in read_rows(fronts) if r["group"] == "psim5"}
    outline = np.genfromtxt(outline_file, delimiter=",", names=True, dtype=None, encoding="utf-8-sig")
    outline = outline[(outline["group"] == "psim5") & (outline["edge_kind"] == "visible")]
    rows = []
    figure16(page, pos, rows)
    times = (.2, .5, 1.6, 3.)
    comparison = {tau: summary(17, tau, "PWP" if tau == 3 else "Excess pl",
                               neg.get(int(round(100*tau))), references[tau]) for tau in times}
    rows.extend(comparison.values())
    with np.load(samples_file, allow_pickle=False) as samples:
        for selected, name in ((times, "fig17_partial.png"), ((.2,), "fig17_t020.png"), ((.5,), "fig17_t050.png")):
            figure17(selected, comparison, neg, samples, outline, neg[67]["tau_s"], name)
    with (OUT / "paper_comparison.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    provenance = dict(paper_doi="10.1016/j.cma.2023.115967", paper_section="4.4, printed pages 21–22",
                      fig16_columns=["Stabilized total pressure, original panel (a)",
                                     "Non-stabilized total pressure, original panel (b)", "C08 native PorePress"],
                      fig16_original_pixel_ticks=FIG16_TICKS,
                      fig16_rgb_filter="Largest 8-connected component with max(RGB)-min(RGB)>=55; original RGB",
                      fig17_reference="Published connected fill, visible edges; clipped late fronts are lower bounds",
                      native_center_spacing_m=DP, fig17_pressure_reference="Fixed initial material PorePress0",
                      fig17_last_saved_part=67, fig17_last_saved_time_s=neg[67]["time_s"],
                      fig17_last_saved_tau_s=neg[67]["tau_s"],
                      source_paths_relative_to="C08 case root", sources=[source_record(p) for p in sources])
    (OUT / "paper_sources.json").write_text(json.dumps(provenance, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
