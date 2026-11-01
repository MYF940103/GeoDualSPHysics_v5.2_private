"""Offline-only audit of the sealed k0 r2 typed-reader 33-column exports.

--pair CPU_half|GPU_half|cross_c|cross_h --a REVIEWDIR --b REVIEWDIR --out PREFIX
Creates fresh PREFIX.json/.csv/.png. No solver, source/native mutation, smoothing,
time interpolation, missing-field substitution, or second raw-BI4 parser.
The r2 C++ helper differs from retained failed r1 only by k0::Finite qualification;
that ADL compile repair is not a physical-model change.
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


def load(folder, backend, dt):
    folder = folder.resolve()
    files = [folder/name for name in ("completion.json", "physical.bin", "native_ids.csv", "history.csv")]
    if backend == "CPU":
        files.append(folder/"cpu_posdiv.csv")
    else:
        need(not (folder/"cpu_posdiv.csv").exists(), "GPU reader must not fabricate CPU PosDiv")
    inputs = [binding(path) for path in files]
    with files[0].open("r", encoding="utf-8-sig") as stream:
        done = json.load(stream, parse_constant=invalid_json_number)
    need(done.get("passed") is True and done.get("backend") == backend and done.get("smoke") is False,
         "Require passed full-window r2 reader completion for declared backend")
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
         (np.abs((1.-n)*j-(1.-N0)) <= 5e-13).all() and (q[:, :, 32] == 0).all(),
         "Independent all-row J-derived n/V/rho/k0 ledger failed")
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
            "backend": backend, "dt": dt, "folder": str(folder),
            "metrics": {"max_energy_ratio": float(energy_ratio.max()),
                        "max_energy_ratio_telemetry_gap": energy_gap,
                        "max_ledger_relative_error": float(ledger.max()),
                        "max_abs_J_minus_1": float(np.abs(j-1.).max()),
                        "max_saved_coupled_CFL": float(coupled.max()),
                        "min_signed_dterror_s": float(error.min()), "max_signed_dterror_s": float(error.max())}}


def reference(run):
    phase = 2.*math.pi*run["x0"][:, 0]/LX
    wt = CU*(2.*math.pi/LX)*TIMES[:, None]
    p = -PSTAR*np.sin(wt)*np.cos(phase)[None, :]
    v = np.zeros((S, N, 3)); u = np.zeros_like(v)
    v[:, :, 0] = AMP*np.cos(wt)*np.sin(phase)[None, :]
    u[:, :, 0] = USTAR*np.sin(wt)*np.sin(phase)[None, :]
    q = run["q"]
    return {"p": p, "v": v, "u": u,
            "p_rms": np.sqrt(((q[:, :, 6]-p)**2).mean(axis=1)),
            "v_rms": np.sqrt(((q[:, :, 3:6]-v)**2).sum(axis=2).mean(axis=1)),
            "u_rms": np.sqrt(((q[:, :, 25:28]-u)**2).sum(axis=2).mean(axis=1))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", required=True, choices=("CPU_half", "GPU_half", "cross_c", "cross_h"))
    parser.add_argument("--a", required=True, type=Path); parser.add_argument("--b", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path); args = parser.parse_args()
    outputs = [Path(str(args.out)+suffix) for suffix in (".json", ".csv", ".png")]
    need(args.out.parent.is_dir() and not any(p.exists() for p in outputs), "Fresh output prefix in existing directory required")
    analysis_program = binding(Path(__file__))
    plans = {"CPU_half": ("CPU", DC, "CPU", DH), "GPU_half": ("GPU", DC, "GPU", DH),
             "cross_c": ("CPU", DC, "GPU", DC), "cross_h": ("CPU", DH, "GPU", DH)}
    ba, da, bb, db = plans[args.pair]; a, b = load(args.a, ba, da), load(args.b, bb, db)
    need(np.array_equal(a["x0"], b["x0"]), "Different native material points")
    need(np.array_equal(a["q"][0, :, :17], b["q"][0, :, :17]), "Initial physical/J state differs")
    delta = a["q"]-b["q"]
    pressure = np.sqrt((delta[:, :, 6]**2).mean(axis=1))
    velocity = np.sqrt((delta[:, :, 3:6]**2).sum(axis=2).mean(axis=1))
    displacement = np.sqrt((delta[:, :, 25:28]**2).sum(axis=2).mean(axis=1))
    maximum_u = 1000.*np.sqrt((delta[:, :, 25:28]**2).sum(axis=2)).max(axis=1)
    half = args.pair.endswith("_half")
    absolute = bool((pressure <= 5.).all() and (maximum_u <= .005).all())
    normalized = bool((pressure/PSTAR <= 1e-4).all() and (velocity/AMP <= 1e-4).all() and (displacement/USTAR <= 1e-4).all())
    passed = absolute and (normalized if half else True)
    refs = [reference(a), reference(b)]
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
    for label, ref in zip(("a", "b"), refs):
        for field in ("p_rms", "v_rms", "u_rms"):
            columns[f"continuum_{field}_{label}"] = ref[field]
    with outputs[1].open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream); writer.writerow(columns)
        for part in range(S):
            writer.writerow([format(float(value[part]), ".17g") for value in columns.values()])
    zlevels = np.unique(a["x0"][:, 2]); z = zlevels[np.argmin(np.abs(zlevels-LZ/2.))]
    selected = np.flatnonzero(a["x0"][:, 2] == z); selected = selected[np.argsort(a["x0"][selected, 0])]
    need(len(selected) == 32, "Declared material plotting row is not 32 nodes")
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.8), constrained_layout=True)
    x = a["x0"][selected, 0]
    for axis, index, scale, label, refkey in ((axes[0, 0], 6, 1e-3, "Pore pressure [kPa]", "p"),
                                            (axes[0, 1], 3, 1e3, "Horizontal velocity [mm/s]", "v"),
                                            (axes[1, 0], 25, 1e3, "Material horizontal displacement [mm]", "u")):
        for run, color, style, name in ((a, "C0", "-", "A"), (b, "C1", "o", "B")):
            axis.plot(x, scale*run["q"][-1, selected, index], style, color=color, markerfacecolor="none",
                      markersize=4, label=f"{name}: {run['backend']}, dt={run['dt']:.5g}s")
        truth = refs[0][refkey][-1, selected]
        if truth.ndim == 2:
            truth = truth[:, 0]
        axis.plot(x, scale*truth, "k--", linewidth=1.2, label="Weak continuum (diagnostic)")
        axis.set(xlabel="Initial material x [m]", ylabel=label); axis.grid(alpha=.25); axis.legend(fontsize=8)
    left = axes[1, 1]; right = left.twinx()
    l1, = left.plot(TIMES, pressure, color="C0", label="Pair pressure RMS")
    l2, = right.plot(TIMES, maximum_u, color="C1", label="Pair max material-u difference")
    left.set(xlabel="Actual time [s]", ylabel="Pressure RMS difference [Pa]")
    right.set_ylabel("Maximum material-u difference [mm]");left.grid(alpha=.25);left.legend(handles=[l1,l2],fontsize=8)
    fig.suptitle(f"{args.pair}: private k=0 window, final t={END:.8g}s; material z0={z:.8g}m")
    fig.savefig(outputs[2], dpi=160);plt.close(fig)
    inputs = [analysis_program]+a["inputs"]+b["inputs"]
    need(all(binding(Path(item["path"])) == item for item in inputs), "Input changed during offline review")
    summary = {"passed": passed, "pair": args.pair, "native_count": N, "samples": S,
               "common_columns": C, "all_actual_times_and_native_IDs_matched": True,
               "pressure_RMS_limit_Pa": 5., "max_material_displacement_limit_mm": .005,
               "absolute_gates_passed": absolute, "normalized_half_gates_applied": half,
               "normalized_half_limit": 1e-4 if half else None,
               "normalized_cross_metrics_descriptive_only": not half,
               "normalized_metrics_within_half_limits_descriptive_if_cross": normalized,
               "maxima": {key: float(np.max(value)) for key, value in columns.items() if key not in ("part", "time_s")},
               "normalizers": {"Pstar_Pa": PSTAR, "Ustar_m": USTAR, "A_m_s": AMP, "cu0_m_s": CU},
               "a": {key: a[key] for key in ("folder", "backend", "dt", "metrics")},
               "b": {key: b[key] for key in ("folder", "backend", "dt", "metrics")},
               "inputs": inputs, "outputs": [binding(outputs[1]), binding(outputs[2])],
               "raw_BI4_reparsed": False, "owned_solver_exit_verified_by_this_script": False,
               "passive_density_exactness_required": False,
               "continuum_reference": "Linear k0 weak plane wave at initial material x; diagnostic, not a new theory gate",
               "limitations": ["Typed-reader exports are inputs, not independent raw BI4 parsing",
                               "CPU rational versus GPU additive passive density is descriptive only",
                               "Saved theta is last force-stage diagnostic, not endpoint divergence",
                               "Energy/local scales and bounded short agreement do not prove sufficient stability, general conservation or physical release"],
               "physical_acceptance": False}
    with outputs[0].open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2, allow_nan=False);stream.write("\n")
    print(json.dumps({"passed": passed, "pair": args.pair, "max_pressure_RMS_Pa": float(pressure.max()),
                      "max_material_u_difference_mm": float(maximum_u.max()), "output_json": str(outputs[0])}))
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, struct.error) as error:
        print(f"Offline k0 pair rejected: {error}", file=sys.stderr)
        sys.exit(1)
