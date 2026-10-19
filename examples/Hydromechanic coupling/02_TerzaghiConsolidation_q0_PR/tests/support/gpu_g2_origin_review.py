"""Offline G2 origin review; no production writes or solver execution."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def require(ok, why):
    if not ok:
        raise RuntimeError(why)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest().upper()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def binding(entries):
    result = {}
    for item in entries:
        path = str(Path(item["path"]).resolve())
        require(path not in result or result[path] == item["sha256"], "Conflicting hash: " + path)
        result[path] = item["sha256"]
    return result


def verify_hashes(entries):
    for path, digest in entries.items():
        require(sha(path) == digest, "Retained artifact changed: " + path)


def rows(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        data = list(csv.DictReader(stream))
    require(len(data) == 5200, "Expected five phases of 1040 native IDs")
    result = {key: np.array([float(row[key]) for row in data]) for key in data[0]}
    require(all(np.isfinite(value).all() for value in result.values()), "Nonfinite source CSV")
    # Every emitted physical float is rounded back to binary32 before arithmetic
    # or bit comparison; phase/fraction/native ID/z are not downcast.
    for key in result:
        if key.startswith(("cpu_", "gpu_")) and not key.endswith("_exact"):
            result[key] = result[key].astype(np.float32)
    for phase, fraction in enumerate((0., .5, 1., 1.5, 0.)):
        selected = result["phase"] == phase
        require(selected.sum() == 1040, "Phase coverage")
        require(np.array_equal(result["id"][selected], np.arange(1040)), "Native IDs must be unique and ordered 0..1039")
        require(np.all(result["fraction"][selected] == fraction), "Fraction mismatch")
        require(np.all(result["code"][selected][:40] == 0) and np.all(result["code"][selected][40:] == 6144), "Retained native fixed/fluid types changed")
    return result


def inspect(tests, configuration):
    name = "hg_gpu_load_origin_" + configuration + "_r1"
    log = tests / "logs"
    output = tests / "outputs" / (name + "_run")
    paths = [log / (name + suffix) for suffix in (".check.json", ".start.json", ".build.json")]
    check, start, build = map(read_json, paths)
    require(check["status"] == "origin_and_spatial_force_passed_not_physical_acceptance" and check["exit_code"] == 0, "Origin process did not succeed")
    require(check["configuration"] == configuration and build["configuration"] == configuration, "Build configuration mismatch")
    require(check["executable"] == start["executable"] == build["executable"], "Executable binding mismatch")
    cb, sb, bb = binding(check["inputs"]), binding(start["inputs"]), binding(build["inputs"])
    require(cb == sb and all(cb.get(p) == h for p, h in bb.items()), "Historical build/start/check input hashes disagree")
    require(cb.get(str(paths[2].resolve())) == sha(paths[2]), "Build manifest binding mismatch")
    require(cb.get(str(Path(build["executable"]).resolve())) == build["executable_sha256"], "Executable hash binding mismatch")
    # These are completed historical runs. The parent may now legitimately edit
    # production guards/rebuild objects; retain their original binding, not a
    # forged current-source hash. Immutable tests/exe/runtime/numeric files must match.
    immutable = {p: h for p, h in cb.items() if Path(p).is_relative_to(tests.parent)}
    verify_hashes(immutable)
    out_hashes = binding(check["outputs"])
    verify_hashes(out_hashes)
    for filename in ("origin_compare.csv", "complete.json"):
        require(str((output / filename).resolve()) in out_hashes, "Unbound numeric output: " + filename)
    complete = read_json(output / "complete.json")
    require(check["metrics"] == complete and complete["integrated_steps"] == 0 and not complete["g2_accepted"], "Completion scope/binding mismatch")
    cmd = "Get-CimInstance Win32_Process -Filter 'ProcessId=" + str(check["pid"]) + "' | Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress"
    probe = subprocess.run(["powershell.exe", "-NoProfile", "-Command", cmd], check=True, capture_output=True, text=True)
    current = json.loads(probe.stdout) if probe.stdout.strip() else None
    require(current is None or current.get("ExecutablePath", "").lower() != check["executable"].lower(), "Owned fixture remains active")
    data = rows(output / "origin_compare.csv")
    seed = next(Path(p) for p in cb if p.endswith("full_k1em4.xml"))
    xml = ET.parse(seed)
    mass = float(np.float32(xml.find(".//massfluid").attrib["value"]))
    require(mass == float(np.float32(xml.find(".//massbound").attrib["value"])), "All-native force norm requires equal masses")
    support = float(np.float32(2 * float(xml.find(".//h").attrib["value"])))
    zmax = float(np.max(data["z"][data["id"] >= 40]))
    require(np.array_equal(data["in_band"].astype(bool), data["z"] > zmax - support), "Saved band flag differs from strict geometric selection")
    original_limit = 64 * float(np.finfo(np.float32).eps)
    require(complete["original_64eps_limit"] == original_limit and complete["spatial_force_limit_N_m"] == .001, "Recorded thresholds changed")
    mismatch = {}
    for backend in ("cpu", "gpu"):
        same = data[backend + "_mode2_raw"].view(np.uint32) == data[backend + "_mode5_raw"].view(np.uint32)
        mismatch[backend] = int(np.count_nonzero(~same))
        require(np.array_equal(same.astype(int), data[backend + "_origin_exact"]), "CSV exact flag differs from independently recovered float32 bits")
    require(not any(mismatch.values()), "Same-backend origin differs")
    phases = []
    for k in range(5):
        selected = data["phase"] == k
        d = {key: values[selected].astype(np.float64) for key, values in data.items()}
        band = d["in_band"].astype(bool)
        cpu, gpu = d["cpu_mode5_raw"], d["gpu_mode5_raw"]
        diff = np.abs(gpu - cpu)
        vector = np.column_stack([d["gpu_a" + axis] - d["cpu_a" + axis] for axis in "xyz"])
        values = {
            "cpu_flex_l1_force_N_m": mass * math.fsum(abs(cpu)),
            "gpu_flex_l1_force_N_m": mass * math.fsum(abs(gpu)),
            "cpu_gpu_flex_l1_difference_N_m": mass * math.fsum(diff),
            "cpu_band_raw_force_N_m": mass * math.fsum(cpu[band]),
            "gpu_band_raw_force_N_m": mass * math.fsum(gpu[band]),
            "cpu_applied_force_N_m": mass * math.fsum(d["cpu_mode5_load"]),
            "gpu_applied_force_N_m": mass * math.fsum(d["gpu_mode5_load"]),
            "all_native_spatial_vector_L1_force_difference_N_m": mass * math.fsum(np.linalg.norm(vector, axis=1)),
        }
        for key, value in values.items():
            require(abs(value - complete["phases"][k][key]) <= 1e-9, "Independent recomputation mismatch: " + key)
        require(values["all_native_spatial_vector_L1_force_difference_N_m"] < .001, "Spatial force gate failed")
        target = -1000. * min(1., d["fraction"][0])
        require(abs(values["cpu_applied_force_N_m"] - target) < .001 and abs(values["gpu_applied_force_N_m"] - target) < .001, "Applied force target failed")
        scaled = diff / np.maximum(1., abs(cpu))
        load_scaled = abs(d["gpu_mode5_load"] - d["cpu_mode5_load"]) / np.maximum(1., abs(d["cpu_mode5_load"]))
        ace_scaled = np.abs(vector) / np.maximum(1., np.column_stack([abs(d["cpu_a" + axis]) for axis in "xyz"]))
        values.update(phase=k, fraction=float(d["fraction"][0]), band_count=int(band.sum()),
                      raw_64eps_failure_count=int(np.count_nonzero(scaled > original_limit)),
                      load_64eps_failure_count=int(np.count_nonzero(load_scaled > original_limit)),
                      ace_64eps_failure_native_count=int(np.count_nonzero(np.any(ace_scaled > original_limit, axis=1))),
                      raw_max_scaled=float(scaled.max()), raw_max_absolute=float(diff.max()),
                      force_target_N_m=target, signed_total_difference_N_m=values["gpu_applied_force_N_m"] - values["cpu_applied_force_N_m"])
        phases.append(values)
    require(max(p["raw_max_scaled"] for p in phases) > original_limit, "The retained raw rejection unexpectedly disappeared")
    evidence = [{"path": str(p), "sha256": sha(p)} for p in paths + [output / "origin_compare.csv", output / "complete.json", seed]]
    return data, dict(configuration=configuration, rows=5200, native_ids_per_phase=1040, soil_ids_per_phase=1000,
                      same_backend_float32_mismatches=mismatch, mass_from_float32_seed=mass, support_m=support,
                      phases=phases, immutable_current_hashes_verified=len(immutable) + len(out_hashes),
                      historical_build_binding_entries=len(bb), historical_production_not_rehashed=True,
                      owned_process_absent=True, exit_code=0, evidence=evidence)


def plot(datasets, reports, output):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 9.6))
    colors = {"cpu": "#2263A6", "gpu": "#D47422"}
    for row, (data, report) in enumerate(zip(datasets, reports)):
        phase = data["phase"] == 2
        band = phase & data["in_band"].astype(bool)
        require(band.sum() == 40, "Plot must retain all 40 top-band native points")
        levels = np.unique(np.round(data["z"][band], 9))
        require(len(levels) == 4, "Expected four loading layers")
        profile, residual = axes[row]
        for backend, marker in (("cpu", "o"), ("gpu", "x")):
            x = -data[backend + "_mode5_load"][band].astype(float)
            z = data["z"][band]
            profile.scatter(x, z, color=colors[backend], marker=marker, s=23, alpha=.65, label=backend.upper() + " (40 points)")
            means, lows, highs = [], [], []
            for level in levels:
                sample = x[np.isclose(z, level, rtol=0, atol=1e-9)]
                require(len(sample) == 10, "Layer does not contain all ten native points")
                means.append(sample.mean()); lows.append(sample.min()); highs.append(sample.max())
            profile.plot(means, levels, color=colors[backend], linestyle="-" if backend == "cpu" else "--", linewidth=1.1)
            profile.hlines(levels, lows, highs, color=colors[backend], linewidth=2)
        profile.set(title=report["configuration"] + ": top-band allocation", xlabel="Downward load acceleration (m/s²)", ylabel="Initial material height z (m)", ylim=(.959, 1.001), xlim=(-8, 375))
        profile.set_yticks(levels)
        profile.legend(loc="center right", frameon=False, fontsize=9)
        profile.text(.04, .73, "Dots: all particles; lines: layer means\nHorizontal segments: min–max (not CI)", transform=profile.transAxes, fontsize=8.7)
        # Near-zero selection is explicit, fixed in units, and not an acceptance
        # filter: all 1040 native particles remain in every numerical force gate.
        near = phase & (data["id"] >= 40) & (np.abs(data["cpu_mode5_raw"]) < 1.) & (np.abs(data["gpu_mode5_raw"]) < 1.)
        for backend, marker in (("cpu", "o"), ("gpu", "x")):
            residual.scatter(data[backend + "_mode5_raw"][near].astype(float) * 1e6, data["z"][near], s=6, marker=marker, alpha=.4, color=colors[backend], label=backend.upper())
        residual.axvline(0, color="#555555", linewidth=.8)
        residual.set(title=report["configuration"] + ": near-zero raw residuals", xlabel="Raw vertical acceleration (10⁻⁶ m/s²)", ylabel="Initial material height z (m)", ylim=(0, 1), xlim=(-115, 115))
        residual.text(.03, .97, f"{int(near.sum())}/1000 soil points; both |raw| < 1 m/s²\nFull height shown; end truncation layers excluded", transform=residual.transAxes, va="top", fontsize=8.6)
        residual.legend(loc="lower right", frameon=False)
        report["plot_near_zero_soil_count"] = int(near.sum())
        for ax in (profile, residual):
            ax.grid(True, color="#e1e1e1", linewidth=.6, alpha=.75)
            ax.set_axisbelow(True)
    fig.suptitle("G2 raw-load origin diagnostic — fixed initial geometry, q/q₀ = 1", fontsize=15, y=.975)
    fig.text(.5, .028, "Mode 2 and mode 5 raw values match bit-for-bit within each backend. Original CPU/GPU 64ε checks still fail.\nNo time integration, mode-5 lifecycle acceptance or full-cycle physical acceptance is established here.", ha="center", fontsize=10, color="#343434")
    fig.tight_layout(rect=(0, .075, 1, .95), h_pad=2.8, w_pad=3)
    fig.savefig(output, dpi=180, facecolor="white")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="gpu_g2_origin_r1")
    args = parser.parse_args()
    require(args.tag.replace("_", "").replace("-", "").isalnum(), "Simple shallow tag required")
    tests = Path(__file__).resolve().parent.parent
    check_path, figure = tests / "logs" / (args.tag + ".check.json"), tests / "figures" / (args.tag + ".png")
    require(not check_path.exists() and not figure.exists(), "Refusing existing analysis artifacts")
    old = tests / "logs" / "hg_gpu_load_Debug_r1.check.json"
    old_record = read_json(old)
    require(old_record["status"] == "failed", "Original r1 failure must remain retained")
    verify_hashes(binding(old_record["outputs"]))
    datasets, reports = [], []
    for configuration in ("Debug", "Release"):
        data, report = inspect(tests, configuration)
        datasets.append(data); reports.append(report)
    plot(datasets, reports, figure)
    result = dict(offline_review_passed=True, origin_verified=True, spatial_force_verified=True,
                  original_64eps_limit=64 * float(np.finfo(np.float32).eps), original_64eps_passed=False,
                  g2_accepted=False, physical_accuracy_accepted=False, integrated_steps=0, configurations=reports,
                  original_failure={"path": str(old), "sha256": sha(old)},
                  figure={"path": str(figure), "sha256": sha(figure), "visual_inspection_pending": True},
                  script={"path": str(Path(__file__).resolve()), "sha256": sha(__file__)},
                  definitions={"spatial_L1": "sum over all 1040 native IDs of mass * Euclidean norm(a_GPU-a_CPU)",
                               "near_zero_plot_only": "Both backend |raw|<1 m/s², native soil only; numerical gates do not use this filter",
                               "profile_range": "Observed per-layer minimum/maximum, not uncertainty or confidence intervals"},
                  limitations=["Historical production source/object hashes are preserved through build/start/check agreement, not asserted equal to the legally evolving current source tree.",
                               "Immutable fixture CPP/executable/runtime/inputs/numeric outputs are rehashed.",
                               "Same-backend origin evidence does not isolate the individual PosCell, fast-math or summation contributions.",
                               "This zero-step diagnostic does not accept long-term G2 physics or mode-5 input/pool lifecycle."])
    with check_path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"check": str(check_path), "figure": str(figure), "review_passed": True}))


if __name__ == "__main__":
    main()
