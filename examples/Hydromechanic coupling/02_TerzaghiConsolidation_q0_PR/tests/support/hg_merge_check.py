"""Offline production-merge regression and optional matched-time half-dt gate.

Never runs a solver or overwrites evidence. Same-scheme merge requires zero ULP
and identical final binary bytes; no tolerance is substituted if it fails.
Example: --candidate NEW --reference hg_soft_x01 --half NEW_HALF --seconds .1 --tag REVIEW
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
import numpy as np
import pandas as pd
import traction_gate as gate
import hourglass_check as hg
from settlement_audit import previous, theoretical_settlement

TESTS = Path(__file__).resolve().parents[1]
FIELDS = ["x", "y", "z", "vx", "vy", "vz", "rho", "pressure",
          *["sigma_"+s for s in ("xx", "yy", "zz", "xy", "yz", "xz")], "kplastic"]
F32 = {"vx", "vy", "vz", "rho", "pressure", "pressure0", "kplastic"}
BIN_DTYPE = np.dtype([("id", "<u4"), *[(k, "<f8") for k in ("x", "y", "z")],
    *[(k, "<f4") for k in ("vx", "vy", "vz", "rho", "pressure", "pressure0")],
    *[(k, "<f8") for k in FIELDS if k.startswith("sigma_")], ("kplastic", "<f4")])


def label(value):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise argparse.ArgumentTypeError("Use a shallow alphanumeric label")
    return value


def differences(a, b, fields=FIELDS):
    gate.require(a.index.equals(b.index), "Cannot compare different native IDs")
    result = {}
    for key in fields:
        dtype = np.dtype("<f4" if key in F32 else "<f8")
        x, y = (np.asarray(frame[key], dtype=dtype) for frame in (a, b))
        utype = np.dtype("<u4" if key in F32 else "<u8")
        xb, yb = x.view(utype), y.view(utype)
        sign = np.array(1 << (dtype.itemsize*8-1), dtype=utype)
        xo, yo = (np.where(v & sign, ~v, v ^ sign) for v in (xb, yb))
        delta = x.astype(float)-y.astype(float)
        result[key] = {"different_bits": int(np.count_nonzero(xb != yb)),
            "max_ulp": int(np.max(np.maximum(xo, yo)-np.minimum(xo, yo))),
            "max_abs": float(np.max(abs(delta))), "rms": float(np.sqrt(np.mean(delta*delta)))}
    return {"zero_ulp": all(v["different_bits"] == 0 for v in result.values()), "fields": result}


def verify_binary(path, frame):
    data = np.fromfile(path, dtype=BIN_DTYPE)
    gate.require(BIN_DTYPE.itemsize == 104 and path.stat().st_size == 104*1040
                 and np.array_equal(data["id"], np.arange(1040)), str(path)+": binary layout/IDs")
    decoded = pd.DataFrame.from_records(data).set_index("id")
    gate.require(differences(decoded, frame)["zero_ulp"], str(path)+": binary and CSV differ")
    gate.finite(decoded, str(path))
    return decoded


def xml_data(run):
    choices = []
    for entry in run["inputs"]:
        path = Path(entry["path"])
        if path.suffix.lower() == ".xml":
            tree = ET.parse(path)
            if tree.find("./execution/particles") is not None:
                choices.append((path, tree))
    gate.require(len(choices) == 1, "Expected one executed GenCase XML")
    path, tree = choices[0]
    model = previous.model(tree)
    excluded = {"DtIni", "DtFixed", "TimeMax", "TimeOut", "SoilStressRateGradCorr",
                "SoilHourglassXi", "SavePosDouble", "HydroMechTopLoadMode", "timeout"}
    def canonical(node):
        if node is None:
            return None
        if node.tag in excluded or node.get("key") in excluded:
            return None
        attrs = {}
        for k, v in node.attrib.items():
            if "comment" in k or k.startswith("_"):
                continue
            try: attrs[k] = float(v)
            except ValueError: attrs[k] = v
        return [node.tag, attrs, [v for child in node if (v := canonical(child)) is not None]]
    signature = {name: canonical(tree.find("./execution/"+name))
                 for name in ("special", "parameters", "constants", "particles", "motion")}
    controls = {e.get("key"): e.get("value") for e in tree.findall("./execution/parameters/parameter")
                if e.get("key") in excluded}
    controls["HydroMechTopLoadMode"] = tree.find("./execution/special/hydromechanics/HydroMechTopLoadMode").get("value")
    return model, signature, {"path": str(path), "sha256": gate.sha(path),
        "explicit_configuration_exclusions": sorted(excluded), "controls": controls}


def new_completion(name, run, seconds):
    c, h = run["completion"], run["hourglass"]
    gate.require(run["status"] == "completed_pending_physical_acceptance" and run["exit_code"] == 0
                 and run["completion_valid"], name+": production run incomplete")
    gate.require(c["mode"] == "production_symplectic" and c["initial_time"] == 0
                 and c["snapshot_part"] == 0 and c["normal_soil"] == 1000
                 and c["native_step_calls"] == c["steps"] == run["steps"]
                 and c["stride"] == run["stride"] and c["dt"] == run["dt"]
                 and c["top_load_mode"] == run["top_load_mode"] and run["grad_corr"] == 1
                 and abs(c["final_time"]-seconds) < 1e-7
                 and c["steps"] == round(seconds/c["dt"]) and c["stress_grad_corr"]
                 and not c["physical_configuration_overridden"], name+": production configuration/endpoint")
    gate.require(c["max_fixed_dt_minus_mechanical_limit_s"] <= 0 and c["pore_dt_limit_s"] >= c["dt"],
                 name+": mechanical or pore dt limit")
    gate.require(h == gate.load(TESTS/f"outputs/{name}/hourglass_complete.json")
                 and h["xi"] == c["xi"] == run["hourglass_xi"] and h["steps"] == c["steps"], name+": HG identity")
    gate.require(all(np.isfinite(v) for v in h.values() if isinstance(v, (int, float))), name+": nonfinite HG statistics")
    n = c["steps"] if h["xi"] > 0 else 0
    gate.require(h["hg_force_calls"] == h["hg_updates"] == h["hg_rate_calls"] == 2*n
                 and h["predictor_updates"] == h["corrector_updates"] == h["predictor_rate_calls"] == h["endpoint_rate_calls"] == n,
                 name+": HG phase counts")
    gate.require(h["history_integrator"] == "production_endpoint_trapezoidal_r2"
                 and h["last_rate_phase"] == h["csv_rate_phase"] == "corrected_endpoint", name+": HG integrator")
    if n:
        gate.require(h["first_pair_count"] > 0 and 0 <= h["integrated_max_skew_rad"] < .01
                     and 0 <= h["max_dt_over_hg_tau"] <= .2 and h["min_natural_dt_limit_s"] >= c["dt"],
                     name+": HG scope/time-scale guard")
    else:
        gate.require(h["xi_zero_bypasses_hg_allocation"], name+": off still allocates HG")
    return {"completed": True, "xi": h["xi"], "dt": c["dt"], "save": c["save_parts"],
            "physical_accuracy_accepted": False}


def read_run(name, seconds):
    run = gate.load(TESTS/f"logs/{name}.run.json")
    evidence = gate.evidence(name, run)
    native = run["completion"]["mode"] == "production_symplectic"
    if native:
        completion = new_completion(name, run, seconds)
    elif seconds <= 1:
        xi = run["hourglass_xi"]
        role = "base" if xi is None else "off" if xi == 0 else "half" if run["dt"] == 5e-6 else "x4"
        completion = hg.completed(role, name, run, seconds, xi_b=xi or .1)
    else:
        completion = gate.completed(name, run, seconds, run["dt"])
    out = TESTS/"outputs"/name
    recorded = {str(Path(e["path"]).resolve()) for e in run["outputs"]}
    required = ["initial_state.csv", "final_state.csv", "final_state.bin", "state.csv", "complete.json"]
    if native: required += ["initial_state.bin", "initial_state.json", "final_state.json", "hourglass_complete.json"]
    xi = run["completion"]["xi"] if native else (run["hourglass_xi"] or 0)
    if xi:
        required += ["hourglass_final.csv", "hourglass_complete.json"]
        gate.require(run["hourglass"] == gate.load(out/"hourglass_complete.json"), name+": embedded HG metadata differs")
    gate.require(all(str((out/p).resolve()) in recorded for p in required), name+": inspected artifact missing from manifest")
    initial, final = (gate.state(out/f"{stem}_state.csv") for stem in ("initial", "final"))
    binary = verify_binary(out/"final_state.bin", final)
    if native:
        verify_binary(out/"initial_state.bin", initial)
        for stem, n in (("initial", 0), ("final", run["steps"])):
            meta = gate.load(out/f"{stem}_state.json")
            gate.require(meta["completed_steps"] == n and meta["native_count"] == 1040
                         and meta["soil_count"] == 1000 and meta["binary_record_bytes"] == 104, name+": state metadata")
    raw = pd.read_csv(out/"state.csv", float_precision="round_trip")
    gate.finite(raw, name)
    n, stride, dt = run["steps"], run["stride"], run["dt"]
    expected = sorted({0, n, *range(stride, n, stride)}) if native else sorted({0, n-1, *range(0, n, stride)})
    gate.require(raw.stage.eq("full_step" if native else "predictor").all()
                 and not raw.duplicated(["step", "id"]).any()
                 and sorted(raw.step.unique()) == expected and len(raw) == len(expected)*1000,
                 name+": sampled timeline incomplete/duplicated")
    frames, metrics = [], []
    model, signature, xml = xml_data(run)
    if native:
        c, controls = run["completion"], xml["controls"]
        mode = {"TopKernelBand": 5, "5": 5, "TopVertical": 1, "1": 1}.get(controls["HydroMechTopLoadMode"])
        gate.require(float(controls["DtIni"]) == float(controls["DtFixed"]) == c["dt"]
                     and float(controls["SoilHourglassXi"]) == c["xi"]
                     and int(controls["SoilStressRateGradCorr"]) == 1 and mode == c["top_load_mode"],
                     name+": excluded XML controls do not match actual recorded runtime")
    for step, rows in raw.groupby("step", sort=True):
        gate.require(rows.time_s.nunique() == 1, name+": mixed frame times")
        time = float(rows.time_s.iloc[0])
        gate.require(abs(time-step*dt) < 1e-7, name+": wrong actual time")
        a = rows.set_index("id").sort_index()[FIELDS]
        frames.append((time, a));metrics.append(gate.geometry(a, initial, time))
    if not native:
        time = run["completion"]["final_time"]
        frames.append((time, final.loc[gate.SOIL, FIELDS]));metrics.append(gate.geometry(final, initial, time))
    gate.require(differences(frames[-1][1], final.loc[gate.SOIL, FIELDS])["zero_ulp"], name+": final sample differs from final state")
    for m in metrics:
        m["tv"] = model["cv"]*max(m["time_s"]-model["tD"], 0)/model["H"]**2
        topz = initial.loc[gate.SOIL[(gate.SOIL-40)%100 == 99], "z"].to_numpy()
        m["classical_top_settlement_mm"] = float(theoretical_settlement(topz, m["time_s"], model).mean())
        m["ideal_finite_kw_top_settlement_mm"] = float(theoretical_settlement(topz, m["time_s"], model, finite=True).mean())
    rate = hg.endpoint_rate(name, final, run["hourglass"]) if xi else None
    if rate is not None: gate.require(rate["rate_check_passed"], name+": independent endpoint rate mismatch")
    return dict(name=name, run=run, evidence=evidence, completion_check=completion, native=native,
        initial=initial, final=final, binary=binary, frames=frames, metrics=metrics,
        model=model, signature=signature, xml=xml, xi=xi, endpoint_rate=rate)


def match_frames(a, b):
    pairs = []
    for time, frame in a["frames"]:
        found = [(t, f) for t, f in b["frames"] if abs(t-time) < 1e-7]
        gate.require(len(found) == 1, "No unique actual-time match at "+str(time))
        t, other = found[0]
        pairs.append((time, t, frame, other))
    return pairs


def summary(data):
    m = pd.DataFrame(data["metrics"]);post = m[m.time_s >= .1-1e-7]
    return {"native_run": data["native"], "evidence": data["evidence"], "completion_check": data["completion_check"],
        "xml": data["xml"], "model": data["model"], "endpoint_rate": data["endpoint_rate"],
        "matched_native_ids": 1040, "metrics": data["metrics"],
        "sampled_max_dx_mm": float(m.max_dx_mm.max()), "sampled_max_layer_z_span_mm": float(m.max_layer_z_span_mm.max()),
        "post_0_1s_max_layer_total_stress_error_pa": float(post.max_layer_total_stress_error_pa.max()) if len(post) else None,
        "post_0_1s_max_top_pair_gap_pa": float(post.top_pair_gap_pa.max()) if len(post) else None,
        "solver_elapsed_seconds": data["run"]["elapsed_seconds"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("candidate", "reference", "tag"): parser.add_argument("--"+arg, type=label, required=True)
    parser.add_argument("--half", type=label);parser.add_argument("--seconds", type=float, default=.1)
    args = parser.parse_args()
    gate.require(0 < args.seconds <= 15, "This checker covers at most 15 s, never 2Tv acceptance")
    names = [args.candidate, args.reference]+([args.half] if args.half else [])
    gate.require(len(set(names)) == len(names), "Use distinct run labels")
    record = TESTS/f"logs/{args.tag}.check.json"
    gate.require(not record.exists(), "Refusing overwrite of review")
    pending = [n for n in names if not (TESTS/f"logs/{n}.run.json").exists()]
    if pending:
        print(json.dumps({"status": "pending", "waiting_for": pending, "solver_launched": False}));return 2
    report = {"checked_utc": datetime.now(timezone.utc).isoformat(), "labels": names, "seconds": args.seconds,
        "thresholds": {"same_scheme_max_ulp": 0, "same_scheme_binary_byte_equal": True, "geometry_mm": .5,
            "post_0_1s_layer_stress_and_top_gap_pa": 100, "short_half_mean_pressure_pa": 50,
            "window_half_material_pressure_rms_pa": 5, "half_top_settlement_mm": .005},
        "scripts": {str(Path(p)): gate.sha(p) for p in (__file__, gate.__file__, hg.__file__,
            sys.modules[theoretical_settlement.__module__].__file__, previous.__file__, previous.reference.__file__)},
        "physical_accuracy_accepted": False, "full_cycle_accepted": False, "solver_launched": False,
        "limits": ["Same-scheme mismatch is reported, never relaxed to a numerical tolerance.",
            "Full-step physical states are compared to legacy predictor states at the same actual time; stale boundary diagnostic columns are excluded.",
            "Old initial_state.csv contains no pressure0 field or binary state; initial consensus covers its 15 native physical columns only. Final binaries compare pressure0 as well.",
            "Legacy predictor sampling follows force-stage boundary updates; production full-step sampling precedes the next force stage. Top-layer differences require phase diagnosis, not an automatic claim that the merger changed physics.",
            "Legacy mechanics.Execute restores initial density and performs an extra initial RunCellDivide(true); the new wrapper retains the production Run initialization sequence. Never change production initialization merely to match a diagnostic fixture.",
            "Geometry/stress maxima cover saved samples, not every integration stage.",
            "Finite-Kw settlement reference assumes ideal quasi-static undrained loading, unlike the actual dynamic ramp.",
            "Small-rotation and frozen-operator dt guards do not prove coupled stability or full-cycle accuracy.",
            "Single-run elapsed-time ratio is descriptive, not a controlled efficiency benchmark."]}
    try:
        data = {n: read_run(n, args.seconds) for n in names}
        a, b = data[args.candidate], data[args.reference]
        gate.require(a["native"], "Candidate must use the production step")
        gate.require(a["xi"] == b["xi"] and a["run"]["dt"] == b["run"]["dt"]
                     and a["run"]["threads"] == b["run"]["threads"], "Merge comparison scheme/dt/threads mismatch")
        gate.require(a["signature"] == b["signature"], "Physical XML differs outside explicit controls")
        if not b["native"]:
            gate.require(b["run"]["variant"] == "normalized" and a["run"]["completion"]["top_load_mode"] == 5,
                         "Legacy normalized load is not matched by production mode5")
        report["results"] = {n: summary(d) for n, d in data.items()}
        failures = []
        for n, d in data.items():
            initial = differences(a["initial"], d["initial"])
            report["results"][n]["initial_state_vs_candidate"] = initial
            if not initial["zero_ulp"]: failures.append(n+": initial native state differs")
            m = report["results"][n]
            geom = max(m["sampled_max_dx_mm"], m["sampled_max_layer_z_span_mm"])
            if geom > .5 or (args.seconds > 1 and geom >= .5):
                failures.append(n+": geometry exceeds 0.5 mm")
            for field in ("post_0_1s_max_layer_total_stress_error_pa", "post_0_1s_max_top_pair_gap_pa"):
                if m[field] is not None and m[field] > 100: failures.append(n+": "+field+" exceeds 100 Pa")
        merge = differences(a["binary"], b["binary"], FIELDS+["pressure0"])
        merge["final_binary_byte_equal"] = (TESTS/f"outputs/{args.candidate}/final_state.bin").read_bytes() == (TESTS/f"outputs/{args.reference}/final_state.bin").read_bytes()
        merge["matched_frames"] = []
        for time, other, x, y in match_frames(a, b):
            diff = differences(x, y)
            top = (x.index.to_numpy()-40)%100 == 99
            merge["matched_frames"].append({"candidate_time_s": time, "reference_time_s": other, **diff,
                "non_top_layers_0_to_98": differences(x.loc[~top], y.loc[~top]),
                "top_material_layer_99": differences(x.loc[top], y.loc[top])})
        merge["all_sampled_physical_fields_zero_ulp"] = all(r["zero_ulp"] for r in merge["matched_frames"])
        if a["xi"]:
            paths = [TESTS/f"outputs/{n}/hourglass_final.csv" for n in names[:2]]
            frames = [pd.read_csv(p, float_precision="round_trip").set_index("id").sort_index() for p in paths]
            merge["hourglass_history"] = differences(*frames, fields=list(frames[0].columns))
            if not merge["hourglass_history"]["zero_ulp"]: failures.append("Merge HG history/rate is not zero ULP")
        merge["final_state_hard_regression_passed"] = merge["zero_ulp"] and merge["final_binary_byte_equal"]
        if not merge["final_state_hard_regression_passed"]:
            failures.append("Merge final native state is not bitwise identical")
        if not merge["all_sampled_physical_fields_zero_ulp"]:
            failures.append("Sampled states differ: zero-ULP history requirement unmet; inspect stage and layer partitions")
        merge["descriptive_wall_time_speedup"] = b["run"]["elapsed_seconds"]/a["run"]["elapsed_seconds"]
        report["merge_regression"] = merge
        if args.half:
            h = data[args.half]
            gate.require(h["native"] and h["xi"] == a["xi"] and h["signature"] == a["signature"]
                         and h["run"]["dt"]*2 == a["run"]["dt"]
                         and h["evidence"]["exe_sha256"] == a["evidence"]["exe_sha256"], "Half-dt scheme/binary mismatch")
            rows = []
            for time, other, x, y in match_frames(a, h):
                p = x.pressure.to_numpy()-y.pressure.to_numpy()
                mx, my = gate.geometry(x, a["initial"], time), gate.geometry(y, h["initial"], other)
                rows.append({"coarse_time_s": time, "fine_time_s": other,
                    "material_pressure_rms_pa": float(np.sqrt(np.mean(p*p))),
                    "mean_pressure_abs_difference_pa": float(abs(p.mean())),
                    "top_settlement_abs_difference_mm": abs(mx["top_settlement_mm"]-my["top_settlement_mm"])})
            half = {"matched_frames": rows, "max_material_pressure_rms_pa": max(r["material_pressure_rms_pa"] for r in rows),
                "max_mean_pressure_abs_difference_pa": max(r["mean_pressure_abs_difference_pa"] for r in rows),
                "max_top_settlement_abs_difference_mm": max(r["top_settlement_abs_difference_mm"] for r in rows)}
            ds = half["max_top_settlement_abs_difference_mm"]
            if ds > .005 or (args.seconds > 1 and ds >= .005): failures.append("Half-dt settlement does not meet 0.005-mm limit")
            if args.seconds > 1 and half["max_material_pressure_rms_pa"] >= 5: failures.append("Window half-dt material pressure RMS is not <5 Pa")
            if args.seconds <= 1 and half["max_mean_pressure_abs_difference_pa"] > 50: failures.append("Short half-dt mean pressure exceeds 50 Pa")
            report["half_dt"] = half
        report["run_completion_verified"] = True;report["reasons"] = failures
        report["merge_and_requested_checks_passed"] = not failures
        report["full_15s_half_dt_gate_passed"] = bool(not failures and args.half and args.seconds == 15)
        report["status"] = "merge_checks_passed_not_full_cycle_acceptance" if not failures else "merge_or_window_checks_rejected"
    except (OSError, ValueError, KeyError, TypeError, AssertionError) as error:
        report.update(status="evidence_or_configuration_rejected", reasons=[str(error)],
                      merge_and_requested_checks_passed=False, full_15s_half_dt_gate_passed=False)
    with record.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False);stream.write("\n")
    print(json.dumps({"status": report["status"], "reasons": report["reasons"], "record": str(record)}, indent=2))
    return 0 if report["merge_and_requested_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
