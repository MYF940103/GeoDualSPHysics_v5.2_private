"""Compare the retained +2.5° C08 DDT runs with Lian (2023), Figs. 15 and 16."""
import csv

import matplotlib
matplotlib.use("Agg")
from matplotlib import colors
import matplotlib.pyplot as plt
import numpy as np

from c08_lian_partial_r1 import CASE, CACHE, PDF, REF, FIG16_TICKS, axes_style, panel16
from digitize_lian_collapse_fronts import load_pages
from postprocess_lian_release import RELEASE_IDS, SOIL_IDS, native

CONTROL = CASE / "figures/validation_explicit/psi2p5"
TRIAL = CASE / "tests/figures/c08_ddt3_psi2p5"
OUT = CASE / "figures/validation_explicit/psi2p5_ddt3_comparison"
GROUP_PARTS = {15: (30, 60, 120), 16: (1, 50, 120)}


def records(file):
    with file.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def frames():
    clocks = {setting: {int(r["part"]): r for r in records(path)} for setting, path in
              ((0, CONTROL / "history.csv"), (3, TRIAL / "collapse/history.csv"))}
    # Reuse the particle exports at every paper time for which they already exist.
    off = np.genfromtxt(CONTROL / "fields.csv", delimiter=",", names=True,
                        usecols=("part", "id", "x_m", "z_m", "p_kPa", "excess_kPa"))
    on = np.genfromtxt(TRIAL / "comparison_material.csv", delimiter=",", names=True)
    result = {}
    for part in sorted(set(GROUP_PARTS[15] + GROUP_PARTS[16])):
        a, b = clocks[0][part], clocks[3][part]
        for key in ("time_s", "tau_s", "completed_step"):
            if a[key] != b[key]:
                raise ValueError(f"Saved particle clocks differ at PART {part}")
        off_slice = off[off["part"] == part]
        on_slice = on[(on["DensityDT"] == 3) & (on["nominal_tau_s"] == part / 100)]
        data = {0: {k: off_slice[k] for k in ("id", "x_m", "z_m", "p_kPa", "excess_kPa")}}
        if len(on_slice):
            if np.max(abs(on_slice["actual_tau_s"] - float(b["tau_s"]))) > 1e-10:
                raise ValueError(f"Exported clock differs from the saved history at PART {part}")
            data[3] = {k: on_slice[k] for k in data[0]}
        else:
            if part not in (1, 50):
                raise ValueError(f"Missing expected paired particle export for PART {part}")
            raw = CASE / f"tests/outputs/c08_ddt3_psi2p5_r1/data/Part_{part:04d}.bi4"
            meta, vals = native(raw)
            if (meta["TimeStep"] != float(b["time_s"]) or meta["Step"] + 1 != int(b["completed_step"])
                    or not np.array_equal(vals["Idp"], RELEASE_IDS)):
                raise ValueError(f"Native identity or clock differs in {raw}")
            soil = vals["Idp"] >= SOIL_IDS[0]
            pos = vals["Posd"][soil]
            data[3] = dict(id=vals["Idp"][soil], x_m=pos[:, 0], z_m=pos[:, 2],
                           p_kPa=vals["PorePress"][soil].astype("f8") * .001,
                           excess_kPa=vals["ExcessPorePress"][soil].astype("f8") * .001)
        for setting, frame in data.items():
            if not np.array_equal(frame["id"], SOIL_IDS) or not all(np.isfinite(arr).all() for arr in frame.values()):
                raise ValueError(f"Invalid {setting=} soil field at PART {part}")
            history = clocks[setting][part]
            for col, hmin, hmax in (("p_kPa", "p_min_kPa", "p_max_kPa"),
                                    ("excess_kPa", "excess_min_kPa", "excess_max_kPa")):
                np.testing.assert_allclose([frame[col].min(), frame[col].max()],
                                           [float(history[hmin]), float(history[hmax])], rtol=1e-10, atol=1e-10)
            np.testing.assert_allclose(frame["x_m"].max(), float(history["front_x_m"]), rtol=1e-10)
            result[setting, part] = (frame, history)
    return result


def make_figure(number, particles, samples, page, fronts):
    fig15 = number == 15
    title = "Material excess pressure" if fig15 else "Total pore-water pressure"
    headings = (("Lian · published excess pressure",) if fig15 else ("Lian (a) · stabilized", "Lian (b) · non-stabilized"))
    headings += ("C08 · DDT off", "C08 · DDT3")
    fig, axes = plt.subplots(3, len(headings), figsize=(4 * len(headings), 6.4))
    fig.subplots_adjust(left=.06, right=.989, top=.84, bottom=.215, wspace=.15, hspace=.23)
    fig.suptitle(f"{title} in the dilative soil column", x=.06, y=.98, ha="left", fontsize=17, fontweight="bold")
    fig.text(.06, .914, f"ψ = +2.5°     |     Lian et al. (2023), Fig. {number} and C08 at matched release times",
             color="#45505b", fontsize=10)
    hi = 10 if fig15 else 20
    field = "excess_kPa" if fig15 else "p_kPa"
    palette = colors.ListedColormap((samples["f15_palette"] if fig15 else page[937, 446:612]) / 255.)
    norm = colors.Normalize(-10, hi, clip=True)
    outrows = []
    for i, part in enumerate(GROUP_PARTS[number]):
        tau = part / 100
        axes_row = axes[i]
        if fig15:
            key = f"f15_t{int(round(tau * 10))}"
            axes_row[0].imshow(samples[key], extent=samples[key + "_extent"], origin="upper", interpolation="nearest")
        else:
            for ax, ticks in zip(axes_row[:2], FIG16_TICKS[tau]):
                raster, extent = panel16(page, ticks)
                ax.imshow(raster, extent=extent, origin="upper", interpolation="nearest")
        for setting, ax in zip((0, 3), axes_row[-2:]):
            frame, history = particles[setting, part]
            pressure = frame[field]
            ax.scatter(frame["x_m"], frame["z_m"], c=pressure, s=2.8, linewidths=0, cmap=palette, norm=norm)
            ref = fronts[tau] if fig15 else None
            front = float(history["front_x_m"])
            lower, upper = np.count_nonzero(pressure < -10), np.count_nonzero(pressure > hi)
            outrows.append(dict(figure=number,DensityDT=setting,field=field,nominal_tau_s=tau,part=part,
                                completed_step=history["completed_step"],time_s=history["time_s"],tau_s=history["tau_s"],
                                front_x_m=front,paper_front_x_m=ref["front_x_m"] if ref else "",
                                paper_digitization_m=ref["digitization_m"] if ref else "",
                                native_minus_paper_front_m=front-float(ref["front_x_m"]) if ref else "",
                                soil_count=len(pressure),min_kPa=pressure.min(),p05_kPa=np.percentile(pressure,5),
                                median_kPa=np.median(pressure),p95_kPa=np.percentile(pressure,95),max_kPa=pressure.max(),
                                color_min_kPa=-10,color_max_kPa=hi,below_count=lower,above_count=upper,
                                below_pct=100*lower/len(pressure),above_pct=100*upper/len(pressure)))
        for j, ax in enumerate(axes_row):
            axes_style(ax, f"{tau:g} s\nz (m)" if j == 0 else "", i == 2)
            if i == 0:
                ax.set_title(headings[j], fontsize=11, loc="left", fontweight="bold")
    cb = fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=palette), cax=fig.add_axes([.32,.117,.36,.016]),
                      orientation="horizontal", ticks=np.arange(-10,hi + 1,10))
    cb.set_label(f"{title} (kPa)")
    note = ("C08 uses each particle’s initial pressure as its reference. The paper attributes excess pressure to dilation."
            if fig15 else "C08 uses native total pore-water pressure. Paper colors reproduce the printed panels.")
    fig.text(.06,.012,note,fontsize=9,color="#45505b")
    fig.savefig(OUT / f"lian_fig{number}_ddt.png", dpi=170)
    plt.close(fig)
    return outrows


def main():
    particles = frames()
    fronts = {float(r["tau_s"]): r for r in records(CASE/"support/lian_collapse_fronts.csv")
              if r["group"] == "psi2p5"}
    page, _ = load_pages(CACHE, PDF)
    OUT.mkdir(exist_ok=True, parents=True)
    with np.load(REF/"paper_pressure_samples.npz", allow_pickle=False) as samples:
        rows = [row for n in (15,16) for row in make_figure(n,particles,samples,page,fronts)]
    with (OUT/"lian_fig15_16_ddt.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
