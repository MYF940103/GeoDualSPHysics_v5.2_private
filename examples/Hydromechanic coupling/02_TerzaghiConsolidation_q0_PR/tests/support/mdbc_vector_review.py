"""Offline review of exactly 18 explicitly selected fixed-plane fixture runs.

No solver, synthetic rows, threshold fitting or physical/time-integration acceptance.
The independent calculations below use retained CSV values, not completion maxima.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from datetime import datetime, timezone

TESTS = Path(__file__).resolve().parent.parent
GEOMETRIES = ("2d_h", "2d_v", "2d_t", "3d_h", "3d_t", "3d_o")
GEOMETRY_LABELS = ("2D horizontal", "2D vertical", "2D 30 deg", "3D horizontal", "3D 30 deg", "3D oblique")
TRIALS = ("constant_projection_only", "bc_compatible_affine")
EPS = 2.0 ** -23
FLOORS = (20.0, 2000.0, 0.02)  # Pa/s, Pa/s, kg/m3/s; fixed before execution.
EVIDENCE = {}
HASH_CACHE = {}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    path = Path(path).resolve()
    stat = path.stat()
    key = (str(path), stat.st_size, stat.st_mtime_ns)
    if key not in HASH_CACHE:
        checksum = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                checksum.update(block)
        HASH_CACHE[key] = checksum.hexdigest()
    return {"path": str(path), "bytes": stat.st_size, "sha256": HASH_CACHE[key]}


def verify(entry):
    actual = digest(entry["path"])
    require(actual["sha256"].lower() == entry["sha256"].lower(), f"Hash mismatch: {entry['path']}")
    if "bytes" in entry:
        require(actual["bytes"] == entry["bytes"], f"Length mismatch: {entry['path']}")
    EVIDENCE[actual["path"]] = actual
    return actual


def read_json(path):
    actual = digest(path)
    EVIDENCE[actual["path"]] = actual
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def number(row, key):
    value = float(row[key])
    require(math.isfinite(value), f"Nonfinite {key}: {row}")
    return value


def close(actual, expected, message):
    require(math.isclose(actual, expected, rel_tol=2e-12, abs_tol=1e-15), message)


def csv_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    require(rows, f"Empty CSV: {path}")
    return rows


def max_checked(rows, keys):
    return [max(row[key] for row in rows) for key in keys]


def review_run(label):
    run_path = TESTS / "logs" / f"{label}.run.json"
    run = read_json(run_path)
    require(run["label"] == label and run["status"] == "passed_manufactured_fields_only", f"Not a passed fixture run: {label}")
    require(run["exit_code"] == 0 and run["owned_process_absent"] is True and run["inputs_unchanged"] is True, f"Exit/ownership/hash gate: {label}")
    require(run["physical_accuracy_accepted"] is False, "Unexpected physical acceptance claim")
    for key in ("build_manifest", "build_log", "prepare_manifest", "runner", "executable"):
        verify(run[key])
    for entry in run["inputs"] + run["outputs"]:
        verify(entry)
    build = read_json(run["build_manifest"]["path"])
    require(build["status"] == "built_not_run" and build["production_build_confirmed"] is True, "Unconfirmed production-object build")
    require(build["configuration"] == run["configuration"], "Build/run configuration mismatch")
    for entry in build["inputs"] + build["resolved_compile_link_inputs"] + build["runtime"]:
        verify(entry)
    require(build["exe_sha256"].lower() == run["executable"]["sha256"].lower(), "Executable/build mismatch")
    require(build["build_log_sha256"].lower() == run["build_log"]["sha256"].lower(), "Build-log mismatch")
    prepare = read_json(run["prepare_manifest"]["path"])
    matches = [v for v in prepare["variants"] if v["label"] == run["prepared_variant"]]
    require(len(matches) == 1 and matches[0] == run["descriptor"], "Preparation descriptor mismatch")
    desc = matches[0]
    geom, slip, dim = desc["geometry"], int(desc["slip_mode"]), int(desc["dimension"])
    require(geom in GEOMETRIES and slip in (1, 2, 3) and dim == int(geom[0]), "Unsupported geometry/slip")
    nw, nr, ns = (48, 24, 12) if dim == 2 else (768, 192, 48)
    nparticle = 208 if dim == 2 else 3328
    require((desc["native_count"], desc["wall_count"], desc["wall_roi_count"]) == (nparticle, nw, nr), "Unexpected manufactured grid counts")
    output = Path(run["output"]).resolve()
    require(output == (TESTS / "outputs" / label).resolve(), "Output outside the selected shallow run")
    retained = {Path(item["path"]).resolve() for item in run["outputs"]}
    files = [output / name for name in ("vector_complete.json", "vector_rows.csv", "pore_rows.csv", "consumer_rows.csv")]
    require(all(path in retained for path in files), "Required output is not hash-bound by run receipt")
    done = read_json(files[0])
    require(done == run["completion"] and done["passed"] is True, "Completion/run mismatch")
    for key, value in (("dimension", dim), ("slip_mode", slip), ("native_count", nparticle), ("wall_count", nw), ("wall_roi_count", nr), ("soil_roi_count", ns), ("r_wiring_0ulp_native_count", nparticle), ("forced_inactive_branch_trials", int(slip != 1))):
        require(done[key] == value, f"Completion coverage mismatch: {key}")
    for key in ("actual_rotated_native_grid_verified", "r_reference_physical_velocity_restored", "forced_inactive_is_not_physical_activation_test", "no_support_fallback_not_instrumented", "raw_density_analytic_error_is_not_an_acceptance_gate", "constant_projection_is_not_bc_compatible_flow"):
        require(done[key] is True, f"Fixture scope assertion missing: {key}")
    require(done["time_integrated"] is False and done["physical_acceptance"] is False and done["copied_mls_or_neighbor_formula"] is False, "Fixture scope changed")

    vectors = csv_rows(files[1])
    require(len(vectors) == 2 * nw * 3, "Incomplete wall/component/trial rows")
    seen, roi_ids, vector_errors, velocity_rows = set(), {}, {}, []
    for row in vectors:
        trial, native, component = row["trial"], int(row["id"]), int(row["component"])
        key = (trial, native, component)
        require(trial in TRIALS and native in range(nw) and component in range(3) and key not in seen, "Unexpected/duplicate vector key")
        seen.add(key)
        actual, expected = number(row, "actual"), number(row, "expected")
        error = abs(actual - expected)
        tolerance = 32 * EPS * max(0.125, abs(expected))
        relative = error / abs(expected) if abs(expected) > 1e-12 else 0.0
        for name, value in (("error", error), ("tolerance", tolerance), ("relative_nonzero_error", relative)):
            close(number(row, name), value, f"Vector {name} not independently reproduced")
        require(row["roi"] in ("0", "1") and row["active"] in ("0", "1"), "Invalid wall flags")
        if row["roi"] == "1":
            require(row["active"] == "1", "ROI wall inactive")
            roi_ids.setdefault(trial, set()).add(native)
            vector_errors.setdefault((trial, native), []).append(error)
            velocity_rows.append({"error": error, "relative": relative, "ratio": error / tolerance})
    require(all(len(roi_ids.get(trial, set())) == nr for trial in TRIALS) and roi_ids[TRIALS[0]] == roi_ids[TRIALS[1]], "Native ROI wall coverage mismatch")
    require(len(velocity_rows) == 2 * nr * 3 and all(len(values) == 3 for values in vector_errors.values()), "ROI component coverage mismatch")
    max_v, max_vrel, ratio_v = max_checked(velocity_rows, ("error", "relative", "ratio"))
    max_vnorm = max(math.sqrt(sum(e * e for e in values)) for values in vector_errors.values())

    pores, pore_ids, pore_errors = csv_rows(files[2]), set(), []
    for row in pores:
        native = int(row["id"])
        require(native not in pore_ids and native in roi_ids[TRIALS[0]], "Unexpected/duplicate pore ROI ID")
        pore_ids.add(native)
        expected, actual = number(row, "expected"), number(row, "actual")
        error, tolerance = abs(actual - expected), 32 * EPS * max(1.0, abs(expected))
        close(number(row, "error"), error, "Pore error mismatch")
        close(number(row, "tolerance"), tolerance, "Pore threshold mismatch")
        pore_errors.append({"error": error, "ratio": error / tolerance})
    require(pore_ids == roi_ids[TRIALS[0]] and len(pores) == nr, "Scalar/native ROI coverage mismatch")
    max_pore, ratio_pore = max_checked(pore_errors, ("error", "ratio"))

    consumers, consumer_keys, soil_ids = csv_rows(files[3]), set(), set()
    diff_max, diff_ratio, bias_max, bias_ratio = [0.0]*3, [0.0]*3, [0.0]*3, [0.0]*2
    require(len(consumers) == ns * 8, "Incomplete consumer rows")
    for row in consumers:
        native, component = int(row["id"]), int(row["component_0to5_sigma_6_pore_7_rho"])
        require(nw <= native < nparticle and component in range(8) and (native, component) not in consumer_keys, "Unexpected/duplicate consumer key")
        soil_ids.add(native); consumer_keys.add((native, component))
        group = 0 if component < 6 else component - 5
        mls, oracle, exact = (number(row, name) for name in ("mls", "oracle", "analytic"))
        diff, bias = abs(mls - oracle), abs(mls - exact)
        tolerance = FLOORS[group] + 2e-5 * abs(oracle)
        for name, value in (("mls_oracle_error", diff), ("analytic_error", bias), ("comparison_tolerance", tolerance)):
            close(number(row, name), value, f"Consumer {name} mismatch")
        diff_max[group] = max(diff_max[group], diff)
        diff_ratio[group] = max(diff_ratio[group], diff/tolerance)
        bias_max[group] = max(bias_max[group], bias)
        if group < 2:
            bias_ratio[group] = max(bias_ratio[group], bias/(FLOORS[group] + 2e-5*abs(exact)))
    require(len(soil_ids) == ns and all((native, component) in consumer_keys for native in soil_ids for component in range(8)), "Native soil/component coverage mismatch")
    ratios = [ratio_v, ratio_pore] + diff_ratio + bias_ratio
    require(all(value <= 1.0 for value in ratios), f"Independent preset-limit gate failed: {label}: {ratios}")
    for key, value in (("max_velocity_abs_error", max_v), ("max_velocity_relative_nonzero_error", max_vrel), ("max_velocity_vector_error", max_vnorm), ("max_pore_scalar_error_Pa", max_pore)):
        close(float(done[key]), value, f"Completion max disagrees with CSV: {key}")
    for key, values in (("consumer_mls_oracle_max", diff_max), ("consumer_analytic_max", bias_max)):
        require(len(done[key]) == len(values), f"Completion array length: {key}")
        for actual, expected in zip(done[key], values):
            close(float(actual), expected, f"Completion max disagrees with CSV: {key}")
    return {"label": label, "geometry": geom, "slip": slip, "configuration": run["configuration"],
            "build_sha256": run["build_manifest"]["sha256"], "prepare_sha256": run["prepare_manifest"]["sha256"],
            "native_count": nparticle, "wall_count": nw, "wall_roi_count": nr, "soil_roi_count": ns,
            "csv_rows": [len(vectors), len(pores), len(consumers)], "max_velocity_abs_error_m_per_s": max_v,
            "max_velocity_relative_nonzero_error": max_vrel, "max_pore_scalar_error_Pa": max_pore,
            "max_consumer_mls_oracle_errors_S_P_R": diff_max, "max_consumer_analytic_errors_S_P_R": bias_max,
            "preset_limit_ratios_velocity_scalar_S_P_R_Sanalytic_Panalytic": ratios,
            "raw_R_analytic_bias_kg_m3_s_not_a_gate": bias_max[2]}


def plot_results(results, limits_path, raw_path, tag):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    colors, markers = ("#245A81", "#C47A23", "#6F7E3C"), ("o", "s", "^")
    names = ("Vel0 (normal-compatible)", "NoSlip", "FreeSlip")
    titles = ("Vector reflection", "Scalar pore reconstruction", "Stress-rate S: MLS vs oracle", "Pore-rate P: MLS vs oracle", "Density-rate R: MLS vs oracle", "Corrected S: analytic", "Corrected P: analytic")
    lookup = {(r["geometry"], r["slip"]): r for r in results}
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.labelcolor": "#28323A", "text.color": "#28323A"})
    fig, axes = plt.subplots(2, 4, figsize=(17, 8), sharey=True)
    for metric, ax in enumerate(axes.flat[:7]):
        peak = 0.0
        for slip in (1, 2, 3):
            values = [lookup[(geom, slip)]["preset_limit_ratios_velocity_scalar_S_P_R_Sanalytic_Panalytic"][metric] for geom in GEOMETRIES]
            peak = max(peak, max(values))
            ax.scatter([x+(slip-2)*.17 for x in range(6)], values, color=colors[slip-1], marker=markers[slip-1], s=37, zorder=3)
        ax.axhline(1.0, color="#444444", linestyle="--", linewidth=1)
        ax.set_ylim(-.035, 1.08); ax.set_xlim(-.5, 5.5)
        ax.set_xticks(range(6), GEOMETRY_LABELS, rotation=35, ha="right")
        ax.grid(axis="y", color="#E3E6E8", linewidth=.7)
        ax.set_title(titles[metric], fontsize=11)
        ax.text(.03, .82, f"max ratio = {peak:.4g}", transform=ax.transAxes, fontsize=10)
        if metric in (0, 4): ax.set_ylabel("Maximum error / preset local limit")
    axes.flat[7].axis("off")
    handles = [Line2D([], [], color=colors[i], marker=markers[i], linestyle="none", label=names[i]) for i in range(3)]
    axes.flat[7].legend(handles=handles, loc="upper left", frameon=False)
    axes.flat[7].text(0, .59, "Each point is the maximum row ratio\ninside the declared native ROI.\nThe dashed line is the preset limit.\n\nLinear scale; genuine zero stays zero.\nConstant velocity tests reflection only,\nnot a wall-compatible flow.\n\nNo time integration or full-case\nphysical acceptance is implied.", va="top", fontsize=10, linespacing=1.5)
    fig.suptitle("Fixed-plane manufactured fields: independent CSV limits", fontsize=16)
    fig.text(.02, .015, f"{tag} | 6 geometries x 3 slip modes | S: Pa/s; P: Pa/s; R: kg/m3/s before normalization", fontsize=10)
    fig.subplots_adjust(top=.90, bottom=.15, left=.06, right=.99, wspace=.22, hspace=.64)
    fig.savefig(limits_path, dpi=180); plt.close(fig)
    fig, ax = plt.subplots(figsize=(11, 5.4))
    for slip in (1, 2, 3):
        values = [lookup[(geom, slip)]["raw_R_analytic_bias_kg_m3_s_not_a_gate"] for geom in GEOMETRIES]
        positions = [x+(slip-2)*.23 for x in range(6)]
        ax.bar(positions, values, width=.21, color=colors[slip-1], label=names[slip-1], alpha=.85)
        ax.scatter(positions, values, color=colors[slip-1], marker=markers[slip-1], s=25, zorder=3)
    ax.set_ylim(bottom=0); ax.grid(axis="y", color="#E3E6E8", linewidth=.7); ax.set_axisbelow(True)
    ax.set_xticks(range(6), GEOMETRY_LABELS); ax.set_ylabel("Maximum |R - (-rho div(v))| [kg/m3/s]")
    ax.set_title("Raw density-rate analytic bias - diagnostic only, NOT an acceptance gate", fontsize=13)
    ax.legend(frameon=False, loc="upper right")
    fig.text(.06, .035, "R retains the raw kernel moment. The R wiring gate compares the same production operator with MLS vs oracle wall values.\nThis plot does not establish density integration accuracy; all runs are non-integrating manufactured-field tests.", fontsize=10)
    fig.subplots_adjust(left=.11, right=.98, bottom=.19, top=.89)
    fig.savefig(raw_path, dpi=180); plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="Fresh review tag; logs/TAG.check.json and figures/TAG_*.png")
    parser.add_argument("--labels", required=True, nargs=18, metavar="RUN", help="Exactly 18 retained run labels, all six geometries x three SlipMode values")
    args = parser.parse_args()
    require(re.fullmatch(r"[A-Za-z0-9_-]+", args.tag), "Unsafe review tag")
    require(len(set(args.labels)) == 18 and all(re.fullmatch(r"[A-Za-z0-9_-]+", label) for label in args.labels), "Need 18 distinct safe run labels")
    check_path = TESTS / "logs" / f"{args.tag}.check.json"
    limits_path = TESTS / "figures" / f"{args.tag}_limits.png"
    raw_path = TESTS / "figures" / f"{args.tag}_raw_R.png"
    require(not any(path.exists() for path in (check_path, limits_path, raw_path)), "Refusing to overwrite review artifacts")
    # Fail before any output if one label is unfinished/missing. Never fabricate a
    # missing category or use completion strings as replacement measurements.
    require(all((TESTS / "logs" / f"{label}.run.json").is_file() for label in args.labels), "All 18 run receipts must exist before review")
    results = [review_run(label) for label in args.labels]
    require({(r["geometry"], r["slip"]) for r in results} == {(g, s) for g in GEOMETRIES for s in (1, 2, 3)}, "The 18 labels do not cover all geometry/slip combinations exactly once")
    require(len({r["build_sha256"] for r in results}) == 1 and len({r["prepare_sha256"] for r in results}) == 1, "Do not silently mix builds or preparation batches")
    results.sort(key=lambda r: (GEOMETRIES.index(r["geometry"]), r["slip"]))
    verify(digest(__file__))
    # Recheck evidence metadata/hashes immediately before creating deliverables.
    for entry in list(EVIDENCE.values()): verify(entry)
    plot_results(results, limits_path, raw_path, args.tag)
    report = {"status": "passed_independent_csv_manufactured_field_review", "tag": args.tag,
              "created_utc": datetime.now(timezone.utc).isoformat(), "labels": args.labels,
              "all_18_combinations_present": True, "source_hashes_verified": True,
              "independent_csv_limits_passed": True, "results": results,
              "limits": {"velocity": "32*FLT_EPSILON*max(.125,abs(expected_component))", "pore_scalar": "32*FLT_EPSILON*max(1,abs(expected))", "consumer_absolute_floors_S_P_R": FLOORS, "consumer_relative_factor": 2e-5},
              "limitations": ["Raw R analytic bias is diagnostic, not an acceptance gate.", "No-support/MLS-order fallback was not directly instrumented.", "Forced inactive wall is a branch test, not physical activation evidence.", "R 0-ULP wiring, temporary-field restoration and actual-grid checks are hash-bound runtime assertions; the full R proof arrays/positions are not exported for independent CSV recomputation.", "Analytic expected fields are exported by the fixture; this review recomputes errors/limits and coverage, not the MLS implementation.", "No time integration, moving/curved/corner wall acceptance, restart, GPU or full-case physical acceptance."],
              "physical_accuracy_accepted": False, "visual_inspection_performed": False,
              "visual_inspection_required": [str(limits_path), str(raw_path)],
              "evidence": list(EVIDENCE.values()), "figures": [digest(limits_path), digest(raw_path)]}
    with check_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    print(check_path)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"REVIEW FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
