"""Offline G3 twenty-step field review; no solver and no physical acceptance."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


TESTS = Path(__file__).resolve().parent.parent
BACKENDS = ("cpu_release", "gpu_release", "gpu_debug")
COMPONENTS = ("SigmaState_kk.x", "SigmaState_kk.y", "SigmaState_kk.z",
              "SigmaState_ij.x", "SigmaState_ij.y", "SigmaState_ij.z")


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def comparison(candidate, reference, times, top, bottom):
    """Every saved native ID is included; soil statistics use IDs 40..1039."""
    require(np.array_equal(candidate[0], reference[0]), "Unequal initial physical fields")
    require(np.array_equal(candidate[:, :, 5], reference[:, :, 5]), "Unequal PorePress0")
    delta = candidate - reference
    settlement = 1000 * ((candidate[0, :, 3] - candidate[:, :, 3])
                         - (reference[0, :, 3] - reference[:, :, 3]))
    history = []
    for k, time in enumerate(times):
        h = dict(part=k, time_s=float(time))
        for prefix, ids in (("soil", slice(40, None)), ("all_native", slice(None))):
            p, stress = delta[k, ids, 4], delta[k, ids, 6:12]
            h[prefix + "_pressure_rms_pa"] = float(np.sqrt(np.mean(p * p)))
            h[prefix + "_pressure_max_pa"] = float(np.max(np.abs(p)))
            h[prefix + "_stress_rms_pa"] = float(np.sqrt(np.mean(stress * stress)))
            h[prefix + "_stress_max_pa"] = float(np.max(np.abs(stress)))
            h[prefix + "_stress_component_rms_pa"] = np.sqrt(np.mean(stress * stress, axis=0)).tolist()
            h[prefix + "_stress_component_max_pa"] = np.max(np.abs(stress), axis=0).tolist()
        for label, ids in (("top", top), ("bottom", bottom)):
            h[label + "_mean_settlement_delta_mm"] = float(settlement[k, ids].mean())
            h[label + "_max_particle_settlement_delta_mm"] = float(np.abs(settlement[k, ids]).max())
        history.append(h)
    summary = {key: max(abs(h[key]) for h in history)
               for key in history[0] if key not in ("part", "time_s") and not isinstance(history[0][key], list)}
    for key in history[0]:
        if isinstance(history[0][key], list):
            summary[key] = np.max([h[key] for h in history], axis=0).tolist()
    return dict(history=history, maximum_over_frames=summary,
                reference_flags=dict(pressure_rms_under_5pa=summary["soil_pressure_rms_pa"] < 5,
                                     top_mean_settlement_under_005mm=summary["top_mean_settlement_delta_mm"] < .005))


def make_figure(figure, cross, activation):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    colors = dict(cpu_release="#34805B", gpu_release="#2263A6", gpu_debug="#D47422")
    markers = dict(cpu_release="s", gpu_release="o", gpu_debug="^")
    for row, group in enumerate((cross, activation)):
        for name, result in group.items():
            history = result["history"]
            time = np.array([h["time_s"] for h in history]) * 1e6
            style = dict(color=colors[name], marker=markers[name], markersize=3, linewidth=1.2)
            label = name.replace("_", " ").title()
            for column, metric in enumerate(("pressure", "stress")):
                axes[row, column].plot(time, [h["soil_" + metric + "_rms_pa"] for h in history], label=label, **style)
                axes[row, column].plot(time, [h["soil_" + metric + "_max_pa"] for h in history], color=colors[name], linestyle="--", linewidth=1)
            axes[row, 2].plot(time, [h["top_mean_settlement_delta_mm"] for h in history], label=label, **style)
            axes[row, 2].plot(time, [h["bottom_mean_settlement_delta_mm"] for h in history], color=colors[name], linestyle="--", linewidth=1)
        for column, title in enumerate(("Pressure", "Six-component double stress", "Material settlement")):
            ax = axes[row, column]
            scope = "HG on: GPU - CPU Release" if row == 0 else "Same backend: HG on - off"
            ax.set(title=scope + "\n" + title, xlabel="Actual time (microseconds)", xlim=(0, 200),
                   ylabel="Difference magnitude (Pa)" if column < 2 else "Signed difference (mm)")
            ax.grid(True, color="#dedede", linewidth=.6)
            ax.set_axisbelow(True)
            ax.ticklabel_format(axis="y", style="sci", scilimits=(-2, 2), useOffset=False)
            if column < 2:
                ax.set_ylim(bottom=0)
                text = "Solid: RMS; dashed: maximum\n1000 native soil particles"
            else:
                text = "Solid: top mean; dashed: bottom mean\nTen fixed initial material IDs per layer"
                if all(h["top_mean_settlement_delta_mm"] == h["bottom_mean_settlement_delta_mm"] == 0
                       for result in group.values() for h in result["history"]):
                    text += "\nAll saved-position differences are zero"
            ax.text(.025, .97, text, transform=ax.transAxes, va="top", fontsize=8.5)
        axes[row, 0].legend(frameon=False, loc="center left", fontsize=8.5)
    fig.suptitle("G3 HG short trajectory - 21 native-ID-matched frames", fontsize=14)
    fig.text(.5, .025, "Only 20 steps / 0.0002 s; no physical or full-cycle acceptance. Pressure RMS 5 Pa and top settlement 0.005 mm are comparison references.\n"
             "No stress tolerance is inferred. Settlement uses saved position precision; CPU HG-off is the retained G2 run (different build).", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, .09, 1, .95), h_pad=2.3, w_pad=2)
    with figure.open("xb") as stream:
        fig.savefig(stream, format="png", dpi=180, facecolor="white")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="hg_gpu_g3_fields_r1")
    args = parser.parse_args()
    require(args.tag.replace("_", "").isalnum(), "Simple artifact tag required")
    result_path = TESTS / "logs" / (args.tag + ".check.json")
    figure = TESTS / "figures" / (args.tag + ".png")
    require(not result_path.exists() and not figure.exists(), "Refusing retained artifacts")
    verified = {}

    def verify(items):
        for item in items:
            path, expected = str(Path(item["path"])), item["sha256"].upper()
            require(path not in verified or verified[path] == expected, "Conflicting hash: " + path)
            if path not in verified:
                require(sha(path) == expected, "Bound artifact changed: " + path)
                verified[path] = expected

    def bind(path):
        verify([dict(path=str(path), sha256=sha(path))])
        return read(path)

    stage = bind(TESTS / "logs/hg_gpu_g3_short_r1.check.json")
    require(stage["passed"] and stage["inputs_unchanged"] and
            stage["status"] == "g3_off_exact_and_on_lifecycle_passed_pending_field_review", "Short stage has not passed")
    verify(stage["evidence"])
    verify([dict(path=stage["stage_start"], sha256=stage["stage_start_sha256"])])
    start = read(stage["stage_start"])
    require(len(start["plans"]) == 5 and start["steps"] == 20 and start["parts"] == 21, "Wrong short-stage scope")
    verify(start["inputs"])
    verify(start["generated_inputs"])
    # Old CPU-off evidence is retained, not reinterpreted as the current executable build.
    old_stage = bind(TESTS / "logs/hg_gpu_band_r1.check.json")
    require(old_stage["passed"] and old_stage["inputs_unchanged"], "Retained G2 stage failed")
    verify(old_stage["evidence"])
    verify([dict(path=old_stage["stage_start"], sha256=old_stage["stage_start_sha256"])])
    limits_path = TESTS / "logs/hg_bd_spr15_half_r1_half.check.json"
    limits = bind(limits_path)
    require(limits["passed"] and limits["thresholds"]["material_pressure_rms_pa"] == 5 and
            limits["thresholds"]["top_material_settlement_difference_mm"] == .005, "Original reference limits changed")
    build_path = TESTS / "logs/hg_gpu_band_fields_r1.build.json"
    build = bind(build_path)
    require(build["built"], "Reader build failed")
    verify(build["inputs"])
    verify([dict(path=build["executable"], sha256=build["executable_sha256"])])
    bind(Path(__file__).resolve()) if False else verify([dict(path=__file__, sha256=sha(__file__))])
    plans = {("on_" if p["hourglass"] else "off_") + p["stage"]: p for p in start["plans"]}
    require(set(plans) == {"off_gpu_debug", "off_gpu_release", "on_gpu_debug", "on_gpu_release", "on_cpu_release"}, "Unexpected or duplicate plans")
    require({str(Path(p["record"])) for p in plans.values()} == set(stage["runs"]), "Stage/run membership differs")
    plans["off_cpu_release"] = dict(record=str(TESTS / "logs/hg_gpu_band_r1_cpu_release.run.json"),
                                    output=str(TESTS / "outputs/hg_gpu_band_r1_cpu_release"), hourglass=False, stage="cpu_release")
    values, records = {}, {}
    for name, plan in plans.items():
        require(str(Path(plan["record"])) in verified, "Run is not bound to completed stage")
        run = read(plan["record"])
        require(run["completed"] and run["stage"] == plan["stage"], "Run stage failed or differs")
        for role in ("solver", "inspector"):
            require(run[role]["exit_code"] == 0 and run[role]["owned_process_absent"], "Unfinished owned " + role)
        if name != "off_cpu_release":
            require(run["hourglass"] == plan["hourglass"] and run["stage_start_sha256"] == stage["stage_start_sha256"], "Run binding differs")
        summary = run["summary"].get("run", run["summary"])
        require(summary["Steps"] == "20" and summary["PartFiles"] == "21" and summary["Np"] == "1040" and summary["PartsOut"] == "0", "Incomplete native trajectory")
        metrics = run["metrics"]
        require(metrics["passed"] and metrics["parts_checked"] == 21 and metrics["native_id_set"] == "0..1039", "Native inspection failed")
        verify(run["inputs"])
        verify(run["outputs"])
        data = Path(plan["output"]) / "data"
        parts = sorted(data.glob("Part_*.bi4"))
        require(len(parts) == 21 and all(str(p) in verified for p in parts), "Missing/unbound raw PART")
        process = subprocess.run([build["executable"], str(data)], capture_output=True)
        require(process.returncode == 0, "Real BI4 reader failed: " + process.stderr.decode(errors="replace"))
        frames = json.loads(process.stdout)
        field = np.array([frame["rows"] for frame in frames], dtype=np.float64)
        time = np.array([frame["time_s"] for frame in frames])
        require(field.shape == (21, 1040, 12) and np.isfinite(field).all(), "Invalid full-field shape/value")
        require([frame["part"] for frame in frames] == list(range(21)), "Missing/duplicate frame")
        require(np.array_equal(field[:, :, 0], np.broadcast_to(np.arange(1040), (21, 1040))), "Native-ID bijection failed")
        require(np.array_equal(time, [p["actual_time_s"] for p in metrics["parts"]]) and
                np.max(np.abs(time - np.arange(21) * 1e-5)) < 1e-12, "Actual-time alignment failed")
        for k, part in enumerate(metrics["parts"]):
            require(part["native_count"] == 1040 and part["soil_count"] == 1000 and part["all_numeric_fields_finite"] and
                    part["saved_step"] == max(0, k - 1), "Original PART scope changed")
        values[name] = field
        records[name] = dict(run_manifest=plan["record"], run_sha256=sha(plan["record"]), time_s=time.tolist(),
                             position_types=sorted({f["position_type"] for f in frames}), raw_parts=[dict(path=str(p), sha256=verified[str(p)]) for p in parts],
                             reader_exit_code=process.returncode, reader_stdout_sha256=hashlib.sha256(process.stdout).hexdigest().upper(),
                             reader_stderr=process.stderr.decode(errors="replace"), source_summary=run["summary"])
    reference = values["on_cpu_release"]
    soil = np.arange(40, 1040)
    z0 = reference[0, :, 3]
    top = soil[np.isclose(z0[soil], z0[soil].max(), rtol=0, atol=1e-9)]
    bottom = soil[np.isclose(z0[soil], z0[soil].min(), rtol=0, atol=1e-9)]
    require(len(top) == len(bottom) == 10, "Wrong initial material-layer population")
    times = records["on_cpu_release"]["time_s"]
    for name, field in values.items():
        require(records[name]["time_s"] == times, "Different actual backend/activation times")
        require(np.array_equal(field[0], reference[0]), "Initial fields differ: " + name)
        settlement = (field[0, :, 3] - field[:, :, 3]) * 1000
        records[name]["top_material_settlement_mm"] = settlement[:, top].mean(axis=1).tolist()
        records[name]["bottom_material_settlement_mm"] = settlement[:, bottom].mean(axis=1).tolist()
        records[name]["saved_float_position_top_ulp_mm"] = float(np.max(np.abs(np.spacing(field[0, top, 3].astype(np.float32))))) * 1000
    cross = {b: comparison(values["on_" + b], reference, times, top, bottom) for b in BACKENDS[1:]}
    activation = {b: comparison(values["on_" + b], values["off_" + b], times, top, bottom) for b in BACKENDS}
    # Compare XML trees ignoring whitespace/comment text: only the declared Xi parameter may differ.
    def tree(node):
        return (node.tag, tuple(sorted(node.attrib.items())), (node.text or "").strip(), tuple(tree(child) for child in node))
    off_xml = ET.parse(TESTS / "configs/hg_gpu_band_r1_seed.xml").getroot()
    on_xml = ET.parse(TESTS / "configs/hg_gpu_g3_short_r1_on_seed.xml").getroot()
    xi_nodes = [(parent, child) for parent in on_xml.iter() for child in parent if child.get("key") == "SoilHourglassXi"]
    require(len(xi_nodes) == 1 and float(xi_nodes[0][1].get("value")) == .1, "Expected single Xi=.1 edit")
    xi_nodes[0][0].remove(xi_nodes[0][1])
    require(tree(off_xml) == tree(on_xml), "HG activation XML contains another change")
    # Rehash the actual evidence after all six read-only decodes before publishing anything.
    require(all(sha(p) == h for p, h in verified.items()), "Evidence changed during offline review")
    make_figure(figure, cross, activation)
    result = dict(passed=True, status="g3_short_fields_compared_pending_visual_review", comparison_complete=True,
                  physical_acceptance=False, full_cycle_admitted=False, figures_reviewed=False,
                  utc=datetime.now(timezone.utc).isoformat(), runs=records, cross_backend_hg_on=cross, same_backend_hg_activation=activation,
                  parts=21, native_count=1040, soil_count=1000, top_native_ids=top.tolist(), bottom_native_ids=bottom.tolist(),
                  stress_components=COMPONENTS, input_output_hashes_verified=len(verified), evidence=[dict(path=p, sha256=h) for p, h in verified.items()],
                  figure=dict(path=str(figure), sha256=sha(figure)),
                  reference_limits=dict(source=str(limits_path), pressure_rms_pa=5, top_mean_settlement_mm=.005,
                                        purpose="Existing half-step limits shown as short-window discrepancy references; this is not a half-step or physical-accuracy test", stress_tolerance=None),
                  definitions=dict(pressure="PorePress difference, Pa; PorePress0 verified identical; soil and all-native RMS/max reported",
                                   stress="Persistent double SigmaState_kk/ij; joint six-component and individual-component RMS/max; no stress acceptance tolerance invented",
                                   settlement="Downward z(initial)-z(actual t), mm; same ten initial top/bottom native IDs, no moving spatial re-selection",
                                   maxima="Maximum absolute metric over the 21 saved frames; signed settlement histories retained",
                                   activation="On minus off within each backend; CPU off is retained G2 (different build), not a new current-build control"),
                  limitations=["Twenty steps only; not full-cycle, timestep-convergence, restart, speed or physical acceptance.",
                               "5 Pa/.005 mm flags do not establish accuracy; activation differences are intentional model changes, not CPU/GPU numerical error.",
                               "Saved float positions quantize settlement; ULP is representational spacing, not an uncertainty estimate. Zero output difference does not prove internal position equality.",
                               "PART does not contain HG history/rates; lifecycle/operator checks do not become an independent every-step history audit here.",
                               "CPU does not emit HydroMechLoadAce; this is a field comparison, not an independent CPU external-force reconstruction.",
                               "Current G3 inputs and immutable reader objects are rehashed; old G2 executable/source provenance remains historical, not revalidated against overwritten live binaries."])
    with result_path.open("x", encoding="utf8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(check=str(result_path), figure=str(figure),
                          cross_backend={k: v["maximum_over_frames"] for k, v in cross.items()},
                          activation={k: v["maximum_over_frames"] for k, v in activation.items()}), indent=2))


if __name__ == "__main__":
    main()
