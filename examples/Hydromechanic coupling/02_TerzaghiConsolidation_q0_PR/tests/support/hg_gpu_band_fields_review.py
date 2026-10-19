"""Read all 21 native BI4 frames; compare GPU Debug/Release to CPU Release."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest().upper()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="hg_gpu_band_fields_r1")
    args = parser.parse_args()
    require(args.tag.replace("_", "").isalnum(), "Simple tag required")
    tests = Path(__file__).resolve().parent.parent
    result_path = tests / "logs" / (args.tag + ".check.json")
    figure = tests / "figures" / (args.tag + ".png")
    require(not result_path.exists() and not figure.exists(), "Refusing retained analysis artifacts")
    verified = {}

    def verify(items):
        for item in items:
            path, digest = item["path"], item["sha256"]
            require(path not in verified or verified[path] == digest, "Conflicting evidence binding")
            if path not in verified:
                require(sha(path) == digest, "Bound artifact changed: " + path)
                verified[path] = digest

    stage_path = tests / "logs/hg_gpu_band_r1.check.json"
    stage = read(stage_path)
    require(stage["passed"] and stage["inputs_unchanged"], "Mode5 stage failed")
    verify(stage["evidence"])
    require(sha(stage["stage_start"]) == stage["stage_start_sha256"], "Stage start hash mismatch")
    build_path = tests / "logs/hg_gpu_band_fields_r1.build.json"
    build = read(build_path)
    verify(build["inputs"])
    require(build["built"] and sha(build["executable"]) == build["executable_sha256"], "Reader build/executable mismatch")
    names = ("cpu_release", "gpu_release", "gpu_debug")
    datasets, records = {}, {}
    for name in names:
        path = tests / "logs" / ("hg_gpu_band_r1_" + name + ".run.json")
        record = read(path)
        require(record["completed"] and record["solver"]["exit_code"] == 0 and record["solver"]["owned_process_absent"], "Unfinished owned solver: " + name)
        require(record["inspector"]["exit_code"] == 0 and record["metrics"]["passed"], "Prior PART inspection failed")
        require(record["summary"]["Steps"] == "20" and record["summary"]["PartFiles"] == "21", "Incomplete trajectory")
        verify(record["inputs"])
        verify(record["outputs"])
        data = tests / "outputs" / ("hg_gpu_band_r1_" + name) / "data"
        require(all(str(p) in verified for p in data.glob("Part_*.bi4")), "Unbound native output")
        process = subprocess.run([build["executable"], str(data)], capture_output=True, text=True)
        require(process.returncode == 0, "BI4 reader failed: " + process.stderr)
        frames = json.loads(process.stdout)
        require(len(frames) == 21, "Missing emitted frames")
        time = np.array([frame["time_s"] for frame in frames])
        values = np.array([frame["rows"] for frame in frames], dtype=np.float64)
        require(values.shape == (21, 1040, 12) and np.isfinite(values).all(), "Invalid decoded field shape/values")
        require(np.array_equal(values[:, :, 0], np.broadcast_to(np.arange(1040), (21, 1040))), "Native ID alignment failed")
        require(np.array_equal(time, np.array([p["actual_time_s"] for p in record["metrics"]["parts"]])), "Independent actual time differs from prior reader")
        datasets[name] = values
        records[name] = dict(run_manifest=str(path), sha256=sha(path), time_s=time.tolist(),
                             position_types=sorted(set(frame["position_type"] for frame in frames)),
                             reader_exit_code=process.returncode, reader_stderr=process.stderr)
    base = datasets["cpu_release"]
    native = np.arange(1040)
    soil = native[40:]
    z0 = base[0, :, 3]
    top = soil[np.isclose(z0[soil], z0[soil].max(), rtol=0, atol=1e-9)]
    bottom = soil[np.isclose(z0[soil], z0[soil].min(), rtol=0, atol=1e-9)]
    require(len(top) == len(bottom) == 10, "Material layers do not have ten native points")
    summaries = {}
    for name in names[1:]:
        candidate = datasets[name]
        require(records[name]["time_s"] == records["cpu_release"]["time_s"], "Backend actual times differ")
        require(np.array_equal(candidate[0], base[0]), "Initial physical fields differ")
        require(np.array_equal(candidate[:, :, 5], base[:, :, 5]), "Pressure reference differs")
        pd = candidate[:, soil, 4] - base[:, soil, 4]
        pa = candidate[:, :, 4] - base[:, :, 4]
        sd = candidate[:, soil, 6:12] - base[:, soil, 6:12]
        sa = candidate[:, :, 6:12] - base[:, :, 6:12]
        settlement = 1000 * ((candidate[0, :, 3] - candidate[:, :, 3]) - (base[0, :, 3] - base[:, :, 3]))
        history = []
        for k, time in enumerate(records[name]["time_s"]):
            history.append(dict(part=k, time_s=time, pressure_rms_pa=float(np.sqrt(np.mean(pd[k] ** 2))),
                                pressure_max_pa=float(abs(pd[k]).max()), stress_rms_pa=float(np.sqrt(np.mean(sd[k] ** 2))),
                                stress_max_pa=float(abs(sd[k]).max()), top_mean_settlement_delta_mm=float(settlement[k, top].mean()),
                                bottom_mean_settlement_delta_mm=float(settlement[k, bottom].mean()),
                                top_max_particle_settlement_delta_mm=float(abs(settlement[k, top]).max()),
                                bottom_max_particle_settlement_delta_mm=float(abs(settlement[k, bottom]).max())))
        summaries[name] = dict(history=history, pressure_worst_frame_rms_pa=max(h["pressure_rms_pa"] for h in history),
                               pressure_max_pa=float(abs(pd).max()), pressure_space_time_rms_pa=float(np.sqrt(np.mean(pd ** 2))),
                               stress_worst_frame_rms_pa=max(h["stress_rms_pa"] for h in history), stress_max_pa=float(abs(sd).max()),
                               stress_space_time_rms_pa=float(np.sqrt(np.mean(sd ** 2))),
                               all_native_pressure_max_pa=float(abs(pa).max()), all_native_stress_max_pa=float(abs(sa).max()),
                               top_max_mean_settlement_delta_mm=max(abs(h["top_mean_settlement_delta_mm"]) for h in history),
                               bottom_max_mean_settlement_delta_mm=max(abs(h["bottom_mean_settlement_delta_mm"]) for h in history),
                               top_max_particle_settlement_delta_mm=float(abs(settlement[:, top]).max()),
                               bottom_max_particle_settlement_delta_mm=float(abs(settlement[:, bottom]).max()),
                               pressure_rms_under_5pa=all(h["pressure_rms_pa"] < 5 for h in history),
                               top_mean_settlement_under_005mm=all(abs(h["top_mean_settlement_delta_mm"]) < .005 for h in history))
    # Publish numeric findings first; the figure remains a separate viewed artifact.
    result = dict(comparison_complete=True, physical_acceptance=False, full_cycle_admitted=False,
                  runs=records, comparisons=summaries, native_count=1040, soil_count=1000, parts=21,
                  top_native_ids=top.tolist(), bottom_native_ids=bottom.tolist(), input_output_hashes_verified=len(verified),
                  evidence=[dict(path=p, sha256=h) for p, h in verified.items()],
                  script_sha256=sha(__file__), reader_build_manifest=str(build_path), reader_build_sha256=sha(build_path),
                  definitions=dict(pressure="PorePress difference over 1000 native soil IDs; identical PorePress0 verified",
                                   stress="Persistent double SigmaState_kk/ij, RMS over all 1000 x 6 components, max absolute component",
                                   settlement="Downward displacement z(initial)-z(t), mm, same initial top/bottom ten native soil IDs; compare layer means and max individual difference"),
                  limitations=["Only 20 steps / 0.0002 s: 5 Pa and .005 mm are short-window difference references, not physical acceptance.",
                               "Positions are used at their emitted precision; zero settlement difference does not prove internal double-position bit equality.",
                               "No HG or SPR long-term GPU validation is established here; no speed comparison is inferred from these short runs.",
                               "CPU does not emit HydroMechLoadAce; this compares the coupled fields, not independent CPU total external-force output."])
    result_path.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf8")
    print(json.dumps({name: {k: v for k, v in data.items() if k != "history"} for name, data in summaries.items()}, indent=2))
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8))
    colors = {"gpu_release": "#2263A6", "gpu_debug": "#D47422"}
    for name, data in summaries.items():
        h = data["history"]; time = np.array([r["time_s"] for r in h]) * 1e6
        for ax, metric in zip(axes[:2], ("pressure", "stress")):
            ax.plot(time, [r[metric + "_rms_pa"] for r in h], color=colors[name], label=name.replace("_", " ").title(), marker="o", markersize=3)
            ax.plot(time, [r[metric + "_max_pa"] for r in h], color=colors[name], linestyle="--", linewidth=1)
        axes[2].plot(time, [r["top_mean_settlement_delta_mm"] for r in h], color=colors[name], marker="o", markersize=3, label=name.replace("_", " ").title())
        axes[2].plot(time, [r["bottom_mean_settlement_delta_mm"] for r in h], color=colors[name], linestyle="--", linewidth=1)
    for ax, title, ylabel in zip(axes, ("Pore-pressure difference", "Double-stress difference", "Material settlement difference"), ("Difference magnitude (Pa)", "Difference magnitude (Pa)", "Signed GPU - CPU difference (mm)")):
        ax.set(title=title, xlabel="Actual time (microseconds)", ylabel=ylabel, xlim=(0, 200))
        ax.grid(True, color="#dedede", linewidth=.6); ax.set_axisbelow(True); ax.ticklabel_format(axis="y", style="sci", scilimits=(-2, 2))
    for ax in axes[:2]:
        ax.set_ylim(bottom=0); ax.text(.04, .97, "Solid: RMS; dashed: maximum", transform=ax.transAxes, va="top", fontsize=9)
    axes[2].text(.04, .97, "Solid: top mean; dashed: bottom mean\nTen initial material IDs per layer", transform=axes[2].transAxes, va="top", fontsize=9)
    axes[0].legend(frameon=False, loc="center left", fontsize=9)
    fig.suptitle("Mode-5 GPU fields versus CPU Release - 21 native-ID-matched frames", fontsize=14)
    fig.text(.5, .035, "Short window only (0.0002 s); reference limits: pressure RMS 5 Pa, top settlement 0.005 mm.\nStress uses double state; settlement is limited by emitted position precision. No full-cycle acceptance.", ha="center", fontsize=10)
    fig.tight_layout(rect=(0, .13, 1, .95), w_pad=2)
    fig.savefig(figure, dpi=180, facecolor="white"); plt.close(fig)
    print("Figure:", figure)


if __name__ == "__main__":
    main()
