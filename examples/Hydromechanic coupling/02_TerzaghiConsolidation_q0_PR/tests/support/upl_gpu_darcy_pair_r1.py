"""Offline-only pairs of strict 33-column constant-k GPU/CPU typed exports.

One explicit --pair with --a/--b review folders and --a-check/--b-check receipts.
Fresh .json/.csv/.png only. No solver/BI4 parser, interpolation, smoothing,
missing-field substitution, native changes or continuum-accuracy gate.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

N, C, S = 512, 33, 257
DC, DH, CAD, END = 2.0**-24, 2.0**-25, 2.0**-23, 2.0**-15
DP, LX, LZ, AMP = 2.0**-8, 2.0**-3, 2.0**-4, 2.0**-9
N0, RHO0, RHOW, KW = .25, 2048., 1000., 67108864.
K, G, V0 = 89478488., 134217728., DP*DP
H = float(np.float32(1.8*DP))
CU = math.sqrt((K+4.*G/3.+KW/N0)/RHO0)
PSTAR, USTAR = (KW/N0)*AMP/CU, AMP/(CU*2.*math.pi/LX)
TIMES = np.arange(S, dtype=np.float64)*CAD
EPS = np.finfo(float).eps
KHYD = float(np.float32(1e-4))
VERIFIED = {}


def need(ok, message):
    if not bool(ok):
        raise ValueError(message)


def invalid_json_number(value):
    raise ValueError(f"Nonfinite/nonstandard JSON number: {value}")


def binding(path):
    path = path.resolve()
    need(path.is_file(), f"Missing evidence: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            digest.update(chunk)
    return {"path": str(path), "bytes": path.stat().st_size,
            "sha256": digest.hexdigest()}


def table(path):
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        need(reader.fieldnames is not None and len(reader.fieldnames) == len(set(reader.fieldnames)),
             f"Missing/duplicate CSV columns: {path}")
    return rows


def values(rows, key):
    result = np.asarray([float(row[key]) for row in rows], dtype=np.float64)
    need(np.isfinite(result).all(), f"Nonfinite CSV column: {key}")
    return result


def read_json(path):
    with path.open("r", encoding="utf-8-sig") as stream:
        result = json.load(stream, parse_constant=invalid_json_number)
    need(isinstance(result, dict), f"Expected JSON object: {path}")
    return result


def verify(entry):
    need(isinstance(entry, dict) and {"path", "bytes", "sha256"} <= entry.keys(),
         "Missing explicit artifact binding")
    path = Path(entry["path"]).resolve()
    expected = {"path": str(path), "bytes": entry["bytes"], "sha256": entry["sha256"].lower()}
    key = str(path).casefold()
    if key not in VERIFIED:
        need(binding(path) == expected, f"Changed bound artifact: {path}")
        VERIFIED[key] = expected
    else:
        need(VERIFIED[key] == expected, f"Conflicting artifact bindings: {path}")
    return path


def owned_call(entry):
    path = verify(entry); call = read_json(path)
    need(call.get("owned_call_exited") is True and call.get("exit_code") == 0 and
         not call.get("launch_error"), f"Owned exit0 missing: {path}")
    verify(call["program"]); verify(call["log"])
    if call.get("target_program"):
        verify(call["target_program"])
    return call


def receipt(check_path, folder, backend, dt, model):
    check_path = check_path.resolve(); check_entry = binding(check_path); verify(check_entry)
    check = read_json(check_path)
    need(check.get("passed") is True and check.get("backend") == backend and
         check.get("model") == model and check.get("common_columns") == C and
         check.get("native_frames") == S and check.get("physical_acceptance") is False and
         check.get("actual_solver_exit_verified_by_wrapper") is True,
         "Require passed matching full native typed-reader check, not a compile-only result")
    required = {str((folder/name).resolve()).casefold()
                for name in ("completion.json", "physical.bin", "native_ids.csv", "history.csv")}
    exported = set()
    for row in check["files"]:
        exported.add(str(verify(row)).casefold())
    need(required <= exported, "Reader exports are not fully bound by the supplied check")
    need(verify(check["completion"]) == folder/"completion.json", "Wrong reader completion binding")
    verify(check["input"])
    reader = owned_call(check["call"]); argv = reader["arguments"]
    need(len(argv) == 7 and argv[:3] == ["--read", model, backend] and
         float(argv[4]) == dt and Path(argv[6]).resolve() == folder,
         "Reader call did not read the declared backend/model/clock into this folder")
    source_path = verify(check["source_run"]); source = read_json(source_path)
    need(source.get("owned_solver_exit0") is True and source.get("backend") == backend and
         source.get("model") == model and source.get("native_frames") == S and
         source.get("solver_completed_before_analysis") is True,
         "Original solve must already be sealed with owned exit0")
    owned_call(source["call"]); verify(source["input"])
    selected = source["selected_input"]
    need(selected["backend"] == backend and selected["model"] == model and
         selected["dt"] == dt and selected["end"] == END and selected["cadence"] == CAD and
         selected["samples"] == S and selected["smoke"] is False,
         "Bound selected runtime differs from this complete pair")
    need(verify(selected["xml"]) == Path(argv[5]).resolve(), "Reader/runtime binding differs")
    verify(selected["bi4"])
    need(selected["bi4"]["bytes"] == 23948 and selected["bi4"]["sha256"] ==
         "364c4421a8b539d0e8e5eb67e00c547657c9c65f48cd7e83168a4ad32cd5a8fa",
         "Initial native geometry is not the retained exact 32x16 seed")
    data = Path(argv[3]).resolve()
    expected = {str((data/f"Part_{part:04}.bi4").resolve()).casefold() for part in range(S)}
    actual = {str(p.resolve()).casefold() for p in data.glob("Part_*.bi4")}
    source_files = {str(verify(row)).casefold() for row in source["files"]}
    need(actual == expected and expected <= source_files,
         "Original raw 257 native PARTs are missing, extra, or not source-receipt bound")
    helper_path = verify(check["helper"]); helper = read_json(helper_path)
    need(helper.get("fixture") == "DarcyActual" and helper.get("exact_link_closure_verified") is True and
         helper.get("link_object_count") == 111 and helper.get("GPU_object_substitutions") == 110 and
         helper["program"]["sha256"] == reader["program"]["sha256"],
         "The supplied typed reader is not the frozen actual Darcy helper")
    verify(helper["program"]); verify(helper["source_build"])
    for row in helper["author_files"]:
        verify(row)
    if source.get("retained_run_reused"):
        need(source.get("new_solver_run") is False, "Retained adoption must not claim a new solve")
        verify(source["old_source_run"])
    compact = [check_entry, check["completion"], check["call"], check["source_run"],
               source["call"], selected["xml"], selected["bi4"], check["helper"], helper["source_build"]]
    return compact, source.get("retained_run_reused") is True


def load(folder, backend, dt, model, check_path):
    folder = folder.resolve()
    proof, retained = receipt(check_path, folder, backend, dt, model)
    khyd = 0. if model == "k0" else KHYD
    files = [folder/name for name in ("completion.json", "physical.bin", "native_ids.csv", "history.csv")]
    if backend == "CPU":
        files.append(folder/"cpu_posdiv.csv")
    else:
        need(not (folder/"cpu_posdiv.csv").exists(), "GPU reader must not fabricate CPU PosDiv")
    inputs = [binding(path) for path in files]+proof
    for item in inputs:
        verify(item)
    with files[0].open("r", encoding="utf-8-sig") as stream:
        done = json.load(stream, parse_constant=invalid_json_number)
    need(done.get("passed") is True and done.get("backend") == backend and done.get("smoke") is False and done.get("model") == model and
         done.get("conductivity_m_s") == khyd and done.get("runtime_XML_exact_model_material_and_clock_checked") is True,
         "Require passed full-window Darcy33 reader completion for declared backend/model")
    for key, expected in {"native_count": N, "fixed_count": 0, "samples": S,
                          "common_columns": C, "dt_s": dt, "cadence_s": CAD,
                          "actual_end_s": END, "native_ledger_checks": N*S,
                          "original_arrays": 15, "native_J_arrays": 6 if backend == "CPU" else 3}.items():
        need(done.get(key) == expected, f"Completion mismatch: {key}")
    need(done.get("native_PosDiv_observed") is (backend == "CPU") and
         done.get("public_dynamic_metadata") is (backend == "CPU") and
         done.get("GPU_V_rho_k_derived_not_native_arrays") is (backend == "GPU"),
         "Backend-specific native/derived schema attribution mismatch")
    for key in ("saved_clock_step_exact", "native_ID_aligned", "no_exclusions"):
        need(done.get(key) is True, f"Reader prerequisite missing: {key}")
    expected_bytes = 12+S*(1+N*C)*8
    need(files[1].stat().st_size == expected_bytes, "Truncated/trailing common binary")
    with files[1].open("rb") as stream:
        need(struct.unpack("<III", stream.read(12)) == (N, C, S), "Wrong 33-column export header")
    raw = np.fromfile(files[1], dtype="<f8", offset=12).reshape(S, 1+N*C)
    need(np.isfinite(raw).all(), "Nonfinite common binary value; no skipped rows")
    need(np.array_equal(raw[:, 0], TIMES), "Nonmatching actual saved times; interpolation forbidden")
    q = raw[:, 1:].reshape(S, N, C)
    ids = table(files[2]); hist = table(files[3])
    need(len(ids) == N and len(hist) == S, "Wrong native-ID/history row count")
    for key in hist[0]:
        values(hist, key)  # No unused telemetry NaN is silently skipped.
    need(np.array_equal(values(ids, "row"), np.arange(N)) and
         np.array_equal(values(ids, "id"), np.arange(N)), "Native rows are not unique contiguous ID order")
    x0 = np.column_stack([values(ids, name) for name in ("x0", "y0", "z0")])
    need(np.array_equal(x0, q[0, :, :3]), "Native-ID material reference differs from initial binary")
    need(np.array_equal(values(hist, "part"), np.arange(S)) and
         np.array_equal(values(hist, "time_s"), TIMES) and
         np.array_equal(values(hist, "dt_s"), np.full(S, dt)), "History clock/part/dt mismatch")
    steps = np.rint(TIMES/dt).astype(np.int64)-1; steps[0] = 0
    need(np.array_equal(values(hist, "saved_step"), steps), "Zero-based native saved step mismatch")
    error = values(hist, "dterror_s")
    need((error <= 1e-14).all(), "Original signed dterror guard failed")
    need(np.array_equal(q[:, :, 25:28], q[:, :, :3]-x0[None, :, :]),
         "Material displacement is not same-ID actual position minus initial position")
    j, n = q[:, :, 8], q[:, :, 29]
    reference_n = 1.-(1.-N0)/j
    reference_v, reference_rho = V0*j, RHOW+(RHO0-RHOW)/j
    need((j > 1.-N0).all() and (np.abs(j-1.) <= 1e-4).all() and
         (n > 0).all() and (n < 1).all(), "Original weak saturated J/n domain failed")
    ledger = np.stack((np.abs(n-reference_n)/reference_n,
                       np.abs(q[:, :, 30]-reference_v)/reference_v,
                       np.abs(q[:, :, 31]-reference_rho)/reference_rho))
    need(np.isfinite(ledger).all() and (ledger <= 5e-13).all() and
         (np.abs((1.-n)*j-(1.-N0)) <= 5e-13).all() and (q[:, :, 32] == khyd).all(),
         "Independent all-row J-derived n/V/rho/constant-k ledger failed")
    need((q[:, :, 16] == 0).all() and (q[:, :, 7] == 0).all() and
         (q[:, :, 21:24] == 0).all() and (q[:, :, 24] >= 700).all() and
         (q[:, :, 24] <= 3000).all(), "Original elastic/no-load/p0/passive-density guard failed")
    excess = (q[:, :, 6].astype(np.float32)-q[:, :, 7].astype(np.float32)).astype(np.float32)
    need(np.array_equal(q[:, :, 28], excess.astype(np.float64)), "Native float excess mismatch")
    need((q[:, :, 1] == 0).all() and (q[:, :, 0] > 0).all() and
         (q[:, :, 0] < LX).all() and (q[:, :, 2] > 0).all() and (q[:, :, 2] < LZ).all(),
         "Weak material window left declared primary geometry")
    need((q[0, :, 8] == 1).all() and (q[0, :, 9] == 0).all() and
         (q[0, :, 6:8] == 0).all() and (q[0, :, 10:16] == 0).all(), "Initial J/theta/p/stress mismatch")
    trace = q[:, :, 10]+q[:, :, 13]+q[:, :, 15]
    dev = ((q[:, :, [10, 13, 15]]-trace[:, :, None]/3.)**2).sum(axis=2)
    dev += 2.*(q[:, :, [11, 12, 14]]**2).sum(axis=2)
    energy = (reference_v*(.5*reference_rho*(q[:, :, 3:6]**2).sum(axis=2)+
               dev/(4.*G)+trace**2/(18.*K)+n*q[:, :, 6]**2/(2.*KW))).sum(axis=1)
    need(np.isfinite(energy).all() and energy[0] > 0, "Empty/nonfinite independent energy")
    energy_ratio = energy/energy[0]
    need((energy_ratio <= 1.1).all(), "Original independently recomputed energy bound failed")
    coupled = np.sqrt((K+4.*G/3.+KW/reference_n)/reference_rho)*dt/H
    need((coupled <= .01).all(), "Original independently recomputed saved coupled-CFL screen failed")
    diffusion = (KW/reference_n)*khyd/(RHOW*9.80665)*dt/(H*H)
    need(np.isfinite(diffusion).all() and (diffusion <= .01).all(),
         "Original independently recomputed saved diffusion screen failed")
    if khyd > 0:
        bcoef = KW/reference_n
        margin = reference_rho*bcoef/(K+4.*G/3.+bcoef)-RHOW
        need((margin > 64.*EPS*np.maximum(reference_rho, RHOW)).all(),
             "Original positive-k continuous-domain necessary guard failed")
    else:
        margin = np.zeros_like(reference_n)  # k0 is not subject to the positive-k domain.

    need(np.max(np.abs(j-1.)) > 1e-8, "Full-window natural J evolution empty")
    history_energy = values(hist, "energy_ratio")
    # A summation-order audit only, not an extra physical stability allowance.
    energy_gap = float(np.max(np.abs(history_energy-energy_ratio)))
    need(energy_gap <= 64.*np.finfo(float).eps*N*max(1., float(np.max(energy_ratio))),
         "Reader energy telemetry disagrees beyond finite summation roundoff")
    if backend == "CPU":
        pv = table(files[4]); need(len(pv) == N*S, "Incomplete observed CPU PosDiv sidecar")
        need(np.array_equal(values(pv, "part"), np.repeat(np.arange(S), N)) and
             np.array_equal(values(pv, "id"), np.tile(np.arange(N), S)), "CPU PosDiv time/ID alignment failed")
        values(pv, "actual_native_PosDiv")
    return {"q": q, "x0": x0, "energy": energy_ratio, "inputs": inputs,
            "backend": backend, "dt": dt, "folder": str(folder), "model": model,
            "retained_native_re_read": retained,
            "metrics": {"max_energy_ratio": float(energy_ratio.max()),
                        "max_energy_ratio_telemetry_gap": energy_gap,
                        "max_ledger_relative_error": float(ledger.max()),
                        "max_abs_J_minus_1": float(np.abs(j-1.).max()),
                        "max_saved_coupled_CFL": float(coupled.max()),
                        "max_saved_Ddt_h2": float(diffusion.max()),
                        "min_positive_k_continuous_margin": float(margin.min()) if khyd > 0 else None,
                        "min_signed_dterror_s": float(error.min()), "max_signed_dterror_s": float(error.max())}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    plans = {
        "k0_bridge_c": ("GPU", DC, "GPU", DC, "k0"),
        "k0_bridge_h": ("GPU", DH, "GPU", DH, "k0"),
        "k0_half": ("GPU", DC, "GPU", DH, "k0"),
        "GPU_half": ("GPU", DC, "GPU", DH, "constant"),
        "cross_c": ("CPU", DC, "GPU", DC, "constant"),
        "cross_h": ("CPU", DH, "GPU", DH, "constant"),
    }
    parser.add_argument("--pair", required=True, choices=tuple(plans))
    for key in ("a", "b", "a-check", "b-check", "out"):
        parser.add_argument("--"+key, required=True, type=Path)
    args = parser.parse_args()
    outputs = [Path(str(args.out)+suffix) for suffix in (".json", ".csv", ".png")]
    need(args.out.parent.is_dir() and not any(p.exists() for p in outputs), "Fresh output prefix required")
    analysis_program = binding(Path(__file__))
    declaration = binding(Path(__file__).parent.parent/"notes"/"upl_gpu_darcy_pair_r1.json")
    verify(analysis_program); verify(declaration)
    ba, da, bb, db, model = plans[args.pair]
    a = load(args.a, ba, da, model, args.a_check)
    b = load(args.b, bb, db, model, args.b_check)
    need(np.array_equal(a["x0"], b["x0"]), "Different native material points")
    need(np.array_equal(a["q"][0, :, :17], b["q"][0, :, :17]), "Initial physical/J state differs")
    if args.pair.startswith("k0_bridge"):
        need(not a["retained_native_re_read"] and b["retained_native_re_read"],
             "Bridge must be new complete-rate GPU A versus original k0 GPU B re-read")
    delta = a["q"]-b["q"]
    pressure = np.sqrt((delta[:, :, 6]**2).mean(axis=1))
    velocity = np.sqrt((delta[:, :, 3:6]**2).sum(axis=2).mean(axis=1))
    displacement = np.sqrt((delta[:, :, 25:28]**2).sum(axis=2).mean(axis=1))
    maximum_u = 1000.*np.sqrt((delta[:, :, 25:28]**2).sum(axis=2)).max(axis=1)
    half = args.pair in ("k0_half", "GPU_half")
    absolute = bool((pressure <= 5.).all() and (maximum_u <= .005).all())
    normalized = bool((pressure/PSTAR <= 1e-4).all() and (velocity/AMP <= 1e-4).all() and
                      (displacement/USTAR <= 1e-4).all())
    passed = absolute and (normalized if half else True)
    stress_rms = np.sqrt((delta[:, :, [10, 13, 15]]**2).sum(axis=2).mean(axis=1)+
                         2.*(delta[:, :, [11, 12, 14]]**2).sum(axis=2).mean(axis=1))
    columns = {"part": np.arange(S), "time_s": TIMES, "pressure_RMS_Pa": pressure,
               "pressure_RMS_over_Pstar": pressure/PSTAR, "velocity_vector_RMS_m_s": velocity,
               "velocity_RMS_over_A": velocity/AMP, "material_u_vector_RMS_m": displacement,
               "material_u_RMS_over_Ustar": displacement/USTAR, "max_material_u_difference_mm": maximum_u,
               "max_abs_J_difference": np.abs(delta[:, :, 8]).max(axis=1),
               "stress_Frobenius_RMS_Pa": stress_rms,
               "max_stress_component_difference_Pa": np.abs(delta[:, :, 10:16]).max(axis=(1, 2)),
               "passive_Rhop_RMS_kg_m3": np.sqrt((delta[:, :, 24]**2).mean(axis=1)),
               "max_passive_Rhop_difference_kg_m3": np.abs(delta[:, :, 24]).max(axis=1),
               "energy_ratio_a": a["energy"], "energy_ratio_b": b["energy"]}
    for name, run in (("a", a), ("b", b)):
        columns["actual_pressure_RMS_Pa_"+name] = np.sqrt((run["q"][:, :, 6]**2).mean(axis=1))
        columns["actual_velocity_vector_RMS_m_s_"+name] = np.sqrt((run["q"][:, :, 3:6]**2).sum(axis=2).mean(axis=1))
        columns["actual_material_u_vector_RMS_m_"+name] = np.sqrt((run["q"][:, :, 25:28]**2).sum(axis=2).mean(axis=1))
    with outputs[1].open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream); writer.writerow(columns)
        for part in range(S):
            writer.writerow([format(float(value[part]), ".17g") for value in columns.values()])
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.5), constrained_layout=True)
    for name, run, color, style in (("a", a, "C0", "-"), ("b", b, "C1", "--")):
        label = f"{name.upper()}: {run['backend']}, dt={run['dt']:.5g}s"
        axes[0, 0].plot(TIMES, columns["actual_pressure_RMS_Pa_"+name], style, color=color, label=label)
        axes[0, 1].plot(TIMES, columns["actual_material_u_vector_RMS_m_"+name]*1000., style, color=color, label=label)
    axes[0, 0].set(ylabel="Actual pressure RMS [Pa]")
    axes[0, 1].set(ylabel="Actual material-u vector RMS [mm]")
    axes[1, 0].plot(TIMES, pressure/5., label="Pressure RMS / 5 Pa")
    axes[1, 0].plot(TIMES, maximum_u/.005, label="Max material-u difference / .005 mm")
    axes[1, 0].axhline(1., color="k", linestyle=":", label="Original absolute bound")
    axes[1, 0].set(ylabel="Pair error / original absolute limit")
    for values_, label in ((pressure/PSTAR, "Pressure RMS / Pstar"), (velocity/AMP, "Velocity RMS / A"),
                           (displacement/USTAR, "Material-u RMS / Ustar")):
        axes[1, 1].plot(TIMES, values_, label=label)
    axes[1, 1].axhline(1e-4, color="k", linestyle=":",
                     label="Original half bound" if half else "Half reference only (not this gate)")
    axes[1, 1].set(ylabel="Normalized pair difference")
    for axis in axes.flat:
        axis.set(xlabel="Actual saved time [s]"); axis.grid(alpha=.25); axis.legend(fontsize=8)
    # A log display does not alter zero CSV samples; exact zeros have no logarithmic ordinate.
    for axis in axes[1]:
        axis.set_yscale("log")
    fig.suptitle(f"{args.pair}: {model}, 257 exact saved times; no continuum-accuracy claim")
    fig.savefig(outputs[2], dpi=160); plt.close(fig)
    names = ("x","y","z","vx","vy","vz","p","p0","J","theta","sxx","sxy","sxz","syy","syz","szz",
             "plastic","FSType","nx","ny","nz","load_ax","load_ay","load_az","passive_Rhop",
             "ux","uy","uz","excess","n","V","mixture_rho","k")
    bits_a, bits_b = a["q"].view(np.uint64), b["q"].view(np.uint64)
    bitdiff, numericdiff = bits_a != bits_b, a["q"] != b["q"]
    fields = [{"column": i, "name": name, "different_bit_patterns": int(bitdiff[:, :, i].sum()),
               "different_numeric_values": int(numericdiff[:, :, i].sum()),
               "maximum_abs_numeric_difference": float(np.abs(delta[:, :, i]).max()),
               "initial_different_bit_patterns": int(bitdiff[0, :, i].sum()),
               "initial_different_numeric_values": int(numericdiff[0, :, i].sum())}
              for i, name in enumerate(names)]
    # Rehash every verified source PART, receipt, input, program and typed export after analysis.
    for entry in VERIFIED.values():
        need(binding(Path(entry["path"])) == entry, "Bound input changed during offline analysis")
    inputs = [analysis_program, declaration]+a["inputs"]+b["inputs"]
    summary = {"passed": passed, "pair": args.pair, "model": model, "native_count": N, "samples": S,
               "common_columns": C, "all_actual_times_and_native_IDs_matched": True,
               "pressure_RMS_limit_Pa": 5., "max_material_displacement_limit_mm": .005,
               "absolute_gates_passed": absolute, "normalized_half_gates_applied": half,
               "normalized_half_limit": 1e-4 if half else None,
               "normalized_nonhalf_metrics_descriptive_only": not half,
               "normalized_metrics_within_half_limits_descriptive_if_nonhalf": normalized,
               "maxima": {key: float(np.max(value)) for key, value in columns.items() if key not in ("part", "time_s")},
               "normalizers": {"Pstar_Pa": PSTAR, "Ustar_m": USTAR, "A_m_s": AMP, "cu0_m_s": CU},
               "a": {key: a[key] for key in ("folder", "backend", "dt", "model", "retained_native_re_read", "metrics")},
               "b": {key: b[key] for key in ("folder", "backend", "dt", "model", "retained_native_re_read", "metrics")},
               "all_33_values_bitwise_equal_descriptive": bool(not bitdiff.any()),
               "all_33_values_numerically_equal_descriptive": bool(not numericdiff.any()),
               "per_column_exactness_descriptive_not_half_gate": fields,
               "inputs": inputs, "files": [binding(outputs[1]), binding(outputs[2])],
               "verified_unique_artifact_bindings": len(VERIFIED),
               "original_raw_native_parts_verified_per_side": S,
               "raw_BI4_reparsed": False, "owned_solver_exit_verified_via_bound_receipts": True,
               "new_solver_invoked": False, "passive_density_exactness_required": False,
               "continuum_or_discrete_theory_reference_used": False,
               "runtime_versions": {"python": sys.version, "numpy": np.__version__, "matplotlib": matplotlib.__version__},
               "limitations": ["New typed-reader33 exports only; no second raw BI4 parser or old26 reinterpretation",
                               "CPU native6 J-derived arrays plus PosDiv versus GPU native3 arrays with derived V/rho/k",
                               "Bit-pattern/numeric differences are descriptive and cannot turn half agreement into 0ULP",
                               "Last-stage theta is not endpoint divergence; necessary scales and energy are not sufficient stability",
                               "No continuum1%, general conservation, public GPU, walls, variable-k, restart or full-cycle admission"],
               "physical_acceptance": False, "full_cycle_accepted": False}
    with outputs[0].open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps({"passed": passed, "pair": args.pair, "max_pressure_RMS_Pa": float(pressure.max()),
                      "max_material_u_difference_mm": float(maximum_u.max()), "output_json": str(outputs[0])}))
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, struct.error) as error:
        print(f"Offline Darcy pair rejected: {error}", file=sys.stderr)
        sys.exit(1)
