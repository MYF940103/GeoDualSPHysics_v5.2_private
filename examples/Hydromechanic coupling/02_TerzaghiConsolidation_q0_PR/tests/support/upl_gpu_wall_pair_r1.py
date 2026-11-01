"""Offline wall33 Half/Cross/Effect/Reference, one explicit action, fresh outputs only.

No solver, BI4 parser, input mutation, interpolation, smoothing or stage admission.
The immutable typed-export utility and constant-k reference are hash-bound imports.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

N, FIXED, TOTAL, C = 1024, 256, 1280, 33
DC, DH, CAD, END = 2.0**-25, 2.0**-26, 2.0**-23, 2.0**-15
DP, WIDTH, LZ, LX, AMP = 2.0**-9, 2.0**-4, 2.0**-4, 2.0**-3, 2.0**-9
N0, RHO0, RW, KW, BULK, SHEAR = .25, 2048., 1000., 67108864., 89478488., 134217728.
V0, H, K0, CK = DP*DP, float(np.float32(1.8*DP)), float(np.float32(1e-4)), 2.0**-13
SUPPORT = Path(__file__).resolve().parent
DEPENDENCIES = {
    "upl_gpu_perm_pair_r1.py": "4d246d45c054d647a10993474f13595c2720fbdc36d05f4c1e1c21956502b0f5",
    "upl_cpu_public_compare_r1.py": "1c6451a327ccce28e7194e296fc952322cf1ed97b06fd946b7899bec9e733dac",
}


def need(ok, message):
    if not bool(ok):
        raise ValueError(message)


def entry(path):
    path = Path(path).resolve()
    need(path.is_file(), "Missing input: " + str(path))
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return dict(path=str(path), bytes=path.stat().st_size, sha256=h.hexdigest())


def frozen_module(name):
    path = SUPPORT/name
    need(entry(path)["sha256"] == DEPENDENCIES[name], "Immutable scientific dependency changed: " + name)
    spec = importlib.util.spec_from_file_location("wall_frozen_" + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # The immutable files guard their main; no analysis is launched.
    return module


def load_run(folder, raw_dir, util, inputs):
    folder = folder.resolve()
    paths = {name: folder/name for name in ("completion.json", "physical.bin", "native_ids.csv",
             "fixed_ids.csv", "fixed_samples.csv", "history.csv", "native_hashes.csv")}
    for path in paths.values():
        inputs.append(entry(path))
    done = util.read_json(paths["completion.json"])
    backend, model, window = done["backend"], done["model"], done["window"]
    need(done.get("passed") is True and done.get("physical_acceptance") is False and
         backend in ("CPU", "GPU") and model in ("k0", "constant", "variable"), "Require a passed declared typed native review")
    need(window in ("full", "k0-short") and (window != "k0-short" or model == "k0"), "Pairs do not admit smoke or an undeclared short model")
    samples, cadence, end = (257, CAD, END) if window == "full" else (17, DC, 2.0**-21)
    dt = done["dt_s"]
    need(dt in (DC, DH), "Undeclared actual coarse/half step")
    expected = dict(native_count=N, fixed_count=FIXED, total_native_count=TOTAL, samples=samples,
                    common_columns=C, cadence_s=cadence, actual_end_s=end, native_ledger_checks=N*samples,
                    fixed_sample_checks=FIXED*samples, original_arrays=15, native_J_arrays=6 if backend == "CPU" else 3,
                    conductivity_model=1 if model == "variable" else 0,
                    conductivity_Ck=CK if model == "variable" else 0., conductivity_m_s=0. if model == "k0" else K0)
    for key, value in expected.items():
        need(done.get(key) == value, "Typed reader completion mismatch: " + key)
    need(done.get("GPU_V_rho_k_derived_not_native") is (backend == "GPU") and
         done.get("fixed_sample_n_is_not_wall_material") is True and
         done.get("native_clock_IDs_and_raw_SHA_unchanged") is True,
         "Backend native/derived/fixed-sample attribution differs")
    times = np.arange(samples, dtype=np.float64)*cadence
    path = paths["physical.bin"]
    need(path.stat().st_size == 12+samples*(1+N*C)*8, "Truncated/trailing wall33 export")
    with path.open("rb") as stream:
        need(struct.unpack("<III", stream.read(12)) == (N, C, samples), "Not a1024x33 typed wall export; old26 is not reinterpreted")
    raw = np.fromfile(path, dtype="<f8", offset=12).reshape(samples, 1+N*C)
    need(np.isfinite(raw).all() and np.array_equal(raw[:, 0], times), "Nonfinite or nonmatching actual times; no interpolation")
    q = raw[:, 1:].reshape(samples, N, C)
    ids, fixed, hist = (util.table(paths[name]) for name in ("native_ids.csv", "fixed_ids.csv", "history.csv"))
    need(len(ids) == N and len(fixed) == FIXED and len(hist) == samples, "Incomplete native/fixed/history rows")
    for table, count, first in ((ids, N, FIXED), (fixed, FIXED, 0)):
        need(np.array_equal(util.values(table, "row"), np.arange(count)) and
             np.array_equal(util.values(table, "id"), np.arange(first, first+count)), "ID rows not contiguous/unique in declared order")
    x0 = np.column_stack([util.values(ids, name) for name in ("x0", "y0", "z0")])
    fx = np.column_stack([util.values(fixed, name) for name in ("x0", "y0", "z0")])
    planes = util.values(fixed, "plane_x")
    need(np.array_equal(x0, q[0, :, :3]) and (x0[:, 1] == 0).all() and
         np.array_equal(np.unique(x0[:, 0]), (np.arange(32)+.5)*DP) and
         np.array_equal(np.unique(x0[:, 2]), (np.arange(32)+.5)*DP) and
         len(np.unique(x0, axis=0)) == N, "Initial material tensor coordinates/ID alignment differ")
    expected_wall_x = np.r_[np.arange(-4, 0)+.5, np.arange(32, 36)+.5]*DP
    need(len(np.unique(fx, axis=0)) == FIXED and (fx[:, 1] == 0).all() and
         np.array_equal(np.unique(fx[:, 0]), expected_wall_x) and
         np.array_equal(np.unique(fx[:, 2]), (np.arange(32)+.5)*DP) and
         np.array_equal(planes, np.where(fx[:, 0] < 0, 0., WIDTH)), "Fixed geometry/layers/planes differ")
    band = np.minimum(x0[:, 0], WIDTH-x0[:, 0]) <= 2.*H
    need(band.sum() == 256 and np.array_equal(util.values(ids, "wall_band").astype(bool), band), "Original256-particle material wall band changed")
    for key in hist[0]:
        util.values(hist, key)
    need(np.array_equal(util.values(hist, "part"), np.arange(samples)) and
         np.array_equal(util.values(hist, "time_s"), times) and
         np.array_equal(util.values(hist, "dt_s"), np.full(samples, dt)), "History actual clocks/dt differ")
    steps = np.rint(times/dt).astype(np.int64)-1
    steps[0] = 0
    need(np.array_equal(util.values(hist, "saved_step"), steps) and
         (util.values(hist, "dterror_s") <= 1e-14).all(), "Original native saved-step/signed-dterror guard failed")
    need(np.array_equal(q[:, :, 25:28], q[:, :, :3]-x0), "Material XYZ displacement is not ID-matched actual minus initial")
    j, n = q[:, :, 8], q[:, :, 29]
    rn, rv, rr = 1.-(1.-N0)/j, V0*j, RW+(RHO0-RW)/j
    rk = np.zeros_like(j) if model == "k0" else np.full_like(j, K0)
    if model == "variable":
        rk = K0*np.exp((j-1.)/((1.-N0)*CK))
        rk[j == 1.] = K0
    need((j > 1.-N0).all() and (np.abs(j-1.) <= 1e-4).all() and
         (n > 0).all() and (n < 1).all() and np.isfinite(rk).all() and
         (rk >= 0).all() and (model == "k0" or (rk > 0).all()), "Weak saturated state/current-k domain failed")
    ledger = np.stack([np.abs(n-rn)/rn, np.abs(q[:, :, 30]-rv)/rv,
                       np.abs(q[:, :, 31]-rr)/rr,
                       np.abs(q[:, :, 32]-rk)/np.maximum(rk, np.finfo(float).tiny)])
    need(np.isfinite(ledger).all() and (ledger <= 5e-13).all() and
         (np.abs((1.-n)*j-(1.-N0)) <= 5e-13).all() and
         (model == "variable" or (q[:, :, 32] == (0. if model == "k0" else K0)).all()), "Independent all-row n/V/rho/k ledger failed")
    need((q[:, :, 1] == 0).all() and (q[:, :, 0] > 0).all() and (q[:, :, 0] < WIDTH).all() and
         (q[:, :, 2] > 0).all() and (q[:, :, 2] < LZ).all() and (q[:, :, 7] == 0).all() and
         (q[:, :, 16] == 0).all() and (q[:, :, 21:24] == 0).all() and
         (q[:, :, 24] >= 700).all() and (q[:, :, 24] <= 3000).all(), "Original geometry/elastic/p0/load/passive-density guard failed")
    excess = (q[:, :, 6].astype(np.float32)-q[:, :, 7].astype(np.float32)).astype(np.float32)
    need(np.array_equal(q[:, :, 28], excess.astype(np.float64)) and
         (q[0, :, 6:8] == 0).all() and (q[0, :, 8] == 1).all() and
         (q[0, :, 9] == 0).all() and (q[0, :, 10:16] == 0).all() and
         (q[0, :, 4:6] == 0).all(), "Initial pressure/J/stress/transverse velocity differs")
    # Match the retained C++ operation order, not a new sine sampling procedure.
    expected_v = np.array([float(np.float32(AMP*math.sin(2.*math.pi*x/LX))) for x in x0[:, 0]])
    need(np.array_equal(q[0, :, 3], expected_v), "Initial actual XML sine field differs")
    trace = q[:, :, 10]+q[:, :, 13]+q[:, :, 15]
    dev = ((q[:, :, [10, 13, 15]]-trace[:, :, None]/3.)**2).sum(axis=2)
    dev += 2.*(q[:, :, [11, 12, 14]]**2).sum(axis=2)
    energy = (rv*(.5*rr*(q[:, :, 3:6]**2).sum(axis=2)+dev/(4.*SHEAR)+
                   trace**2/(18.*BULK)+n*q[:, :, 6]**2/(2.*KW))).sum(axis=1)
    need(np.isfinite(energy).all() and energy[0] > 0, "Empty/nonfinite independent energy")
    energy /= energy[0]
    coupled = np.sqrt((BULK+4.*SHEAR/3.+KW/rn)/rr)*dt/H
    diffusion = (KW/rn)*q[:, :, 32]/(RW*9.80665)*dt/(H*H)
    need((energy <= 1.1).all() and np.isfinite(diffusion).all() and
         (coupled <= .01).all() and (diffusion <= .01).all(), "Original independently recomputed energy/wave/diffusion screen failed")
    if model != "k0":
        b = KW/rn
        margin = rr*b/(BULK+4.*SHEAR/3.+b)-RW
        need((margin > 64.*np.finfo(float).eps*np.maximum(rr, RW)).all(), "Original positive-k continuous domain failed")
    need(np.max(np.abs(j-1.)) > 1e-8, "Natural non-smoke J evolution empty")
    span = (rk.max(axis=1)-rk.min(axis=1))/K0
    need(model != "variable" or float(span.max()) >= .005, "Original variable-k activation screen empty")
    gap = float(np.max(np.abs(util.values(hist, "energy_ratio")-energy)))
    need(gap <= 64.*np.finfo(float).eps*N*max(1., float(energy.max())), "Energy telemetry differs beyond original finite summation roundoff")
    markers = util.table(paths["fixed_samples.csv"])
    need(len(markers) == FIXED*samples and np.array_equal(util.values(markers, "part"), np.repeat(np.arange(samples), FIXED)) and
         np.array_equal(util.values(markers, "id"), np.tile(np.arange(FIXED), samples)), "Incomplete fixed-sample history/IDs")
    fixed_xyz = np.column_stack([util.values(markers, key) for key in ("x", "y", "z")])
    fj, fn, ft = (util.values(markers, key) for key in ("J", "n_saved", "theta"))
    util.values(markers, "p")
    need(np.array_equal(fixed_xyz, np.tile(fx, (samples, 1))) and (fj > 1.-N0).all() and (ft == 0).all() and
         ((fn == 0).all() if backend == "CPU" else np.array_equal(fn, 1.-(1.-N0)/fj)), "Fixed raw sample/marker convention differs")
    need(all(r["n_is_CPU_zero_marker_or_GPU_sample_not_wall_material"] == "true" for r in markers), "Fixed sample must not be presented as wall material")
    if backend == "CPU":
        path = folder/"cpu_posdiv.csv"
        inputs.append(entry(path))
        pd = util.table(path)
        need(len(pd) == samples*N and np.array_equal(util.values(pd, "part"), np.repeat(np.arange(samples), N)) and
             np.array_equal(util.values(pd, "id"), np.tile(np.arange(FIXED, TOTAL), samples)), "CPU actual PosDiv sidecar alignment differs")
        util.values(pd, "native_PosDiv")
    else:
        need(not (folder/"cpu_posdiv.csv").exists(), "GPU PosDiv must not be fabricated")
    hashes = util.table(paths["native_hashes.csv"])
    need(len(hashes) == samples and np.array_equal(util.values(hashes, "part"), np.arange(samples)), "Incomplete raw reader hash table")
    for part, record in enumerate(hashes):
        digest = record["sha256_before"].lower()
        need(record["filename"] == f"Part_{part:04}.bi4" and len(digest) == 64 and
             set(digest) <= set("0123456789abcdef") and digest == record["sha256_after"].lower() and
             record["equal"] == "true", "Reader raw SHA before/after evidence differs")
        if raw_dir is not None:
            raw_entry = entry(raw_dir/record["filename"])
            need(raw_entry["sha256"] == digest, "Current original PART differs from reader binding")
            inputs.append(raw_entry)
    if raw_dir is not None:
        need({p.name for p in raw_dir.glob("Part_*.bi4")} == {r["filename"] for r in hashes}, "Extra/missing current original PARTs")
    return dict(q=q, times=times, x0=x0, fixed=fx, planes=planes, band=band, backend=backend, model=model,
                window=window, samples=samples, dt=dt, folder=str(folder), completion=entry(paths["completion.json"]),
                energy=energy, kspan=span, original_raw_hashes_verified=raw_dir is not None,
                fixed_marker=dict(convention="CPU zero marker" if backend == "CPU" else "GPU reconstructed sample",
                                  min_n=float(fn.min()), max_n=float(fn.max()), rows=len(markers)),
                metrics=dict(max_energy_ratio=float(energy.max()), max_energy_telemetry_gap=gap,
                             max_ledger_relative_error=float(ledger.max()), max_abs_J_minus_1=float(np.abs(j-1.).max()),
                             max_saved_coupled_CFL=float(coupled.max()), max_saved_Ddt_h2=float(diffusion.max()),
                             max_k_span_over_k0=float(span.max())))


def compact(run):
    return {key: run[key] for key in ("folder", "backend", "model", "window", "samples", "dt", "completion",
                                    "original_raw_hashes_verified", "fixed_marker", "metrics")}


def own_half(path, variable, util, inputs, analysis):
    inputs.append(entry(path))
    done = util.read_json(path)
    need(done.get("passed") is True and done.get("action") == "Half" and done.get("model") == "variable" and
         done.get("samples") == 257 and done.get("native_count") == N and done.get("common_columns") == C and
         done.get("absolute_gates_passed") is True and done.get("normalized_half_gates_applied") is True and
         done.get("normalized_half_limit") == 1e-4 and done.get("physical_acceptance") is False,
         "Effect requires its already-passed independent full GPU variable half")
    need(all(done[side]["backend"] == "GPU" for side in ("a", "b")) and
         [done[side]["dt"] for side in ("a", "b")] == [DC, DH], "Effect half is not own GPU c/h")
    side = done["a"] if variable["dt"] == DC else done["b"]
    need(side["folder"] == variable["folder"] and side["completion"] == variable["completion"] and
         done["analysis_program"]["sha256"] == analysis["sha256"], "Effect variable side/recipe differs from own half")
    for bound in done["inputs"]+done["files"]:
        util.verify(bound)
        inputs.append(bound)
    csv_files = [record for record in done["files"] if Path(record["path"]).suffix == ".csv"]
    need(len(csv_files) == 1, "Own half needs one full metric CSV")
    rows = util.table(util.verify(csv_files[0]))
    need(len(rows) == 257 and np.array_equal(util.values(rows, "time_s"), variable["times"]), "Own half actual time CSV differs")
    pressure = util.values(rows, "pressure_RMS_Pa")
    need((pressure <= 5).all() and (util.values(rows, "max_material_u_difference_mm") <= .005).all() and
         (util.values(rows, "pressure_RMS_over_Pstar") <= 1e-4).all() and
         (util.values(rows, "velocity_RMS_over_A") <= 1e-4).all() and
         (util.values(rows, "material_u_RMS_over_Ustar") <= 1e-4).all() and
         done["maxima"]["pressure_RMS_Pa"] == float(pressure.max()), "Original full own-half numeric limits do not hold")
    return float(pressure.max())


def rk_reference(times, public):
    # Independent physical [u,v,sigma,p] RK4, old CPU wall Derivative/Advance contract.
    kappa, b = 2.*math.pi/LX, KW/N0
    diffusivity, modulus = b*K0/(RW*9.80665), BULK+4.*SHEAR/3.
    def derivative(y):
        acceleration = kappa*(y[3]-y[2])/RHO0
        return np.array([y[1], acceleration, modulus*kappa*y[1],
                         -b*kappa*y[1]-diffusivity*kappa*kappa*y[3]+diffusivity*RW*kappa*acceleration])
    def advance(y, interval, pieces):
        h = interval/pieces
        for _ in range(pieces):
            a = derivative(y); bb = derivative(y+.5*h*a)
            c = derivative(y+.5*h*bb); d = derivative(y+h*c)
            y = y+h*(a+2*bb+2*c+d)/6.
        return y
    curves = []
    for pieces in (16, 32):
        y = np.array([0., AMP, 0., 0.]); curve = [y.copy()]
        for interval in np.diff(times):
            y = advance(y, float(interval), pieces); curve.append(y.copy())
        curves.append(np.array(curve))
    need(float(np.abs(curves[0][:, 3]-curves[1][:, 3]).max()) <= 1e-8, "Original physical RK16/RK32 pressure self-check failed")
    normalized = curves[0][:, [3, 1, 0]]/np.array([public.PS, AMP, public.US])
    reference = public.reference()  # Exact retained independently scaled4x4 expm, no main run.
    gap = float(np.abs(reference-normalized).max())
    need(gap < 2e-11, "Original expm/RK4 normalized cross-check failed")
    return reference, gap


def reference_metrics(run, refs, public):
    q, phase = run["q"], 2.*math.pi*run["x0"][:, 0]/LX
    out, near = [], []
    for i in range(257):
        p = q[i, :, 6]/public.PS-refs[i, 0]*np.cos(phase)
        v = q[i, :, 3:6].copy()/AMP; v[:, 0] -= refs[i, 1]*np.sin(phase)
        u = q[i, :, 25:28].copy()/public.US; u[:, 0] -= refs[i, 2]*np.sin(phase)
        square = np.column_stack((p*p, (v*v).sum(axis=1), (u*u).sum(axis=1)))
        out.append(np.sqrt(square.mean(axis=0))); near.append(np.sqrt(square[run["band"]].mean(axis=0)))
    out, near = np.array(out), np.array(near)
    mode = 2.*np.mean(q[:, :, 6]*np.cos(phase), axis=1)/public.PS
    need(refs[-1, 0] != 0 and np.isfinite(refs).all(), "Reference endpoint pressure empty/nonfinite")
    endpoint = float(mode[-1]/refs[-1, 0]-1.)
    passed = bool(out.max() <= .01 and near.max() <= .01 and abs(endpoint) <= .01)
    try:
        old_out, old_near, old_endpoint = public.constant_errors(q, refs, True)
        need(passed and np.array_equal(old_out, out) and np.array_equal(old_near, near) and
             old_endpoint == endpoint, "Retained original reference calculation differs")
    except RuntimeError as error:
        need(not passed and str(error) == "Original constant-wall1% full/near/endpoint objective failed",
             "Unexpected retained constant reference failure: " + str(error))
    return out, near, endpoint, passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", required=True, choices=("Half", "Cross", "Effect", "Reference"))
    parser.add_argument("--a", required=True, type=Path); parser.add_argument("--b", type=Path)
    parser.add_argument("--a-data", type=Path); parser.add_argument("--b-data", type=Path)
    parser.add_argument("--half-check", type=Path); parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    need((args.b is None) == (args.action == "Reference"), "Only Reference takes one run; pairs require two")
    need((args.half_check is not None) == (args.action == "Effect"), "Only Effect requires own GPU half")
    need(args.b_data is None or args.b is not None, "B raw directory without a B run")
    files = [Path(str(args.out)+suffix) for suffix in (".json", ".csv", ".png")]
    need(args.out.parent.is_dir() and not any(path.exists() for path in files), "Fresh output prefix required")
    util = frozen_module("upl_gpu_perm_pair_r1.py"); public = frozen_module("upl_cpu_public_compare_r1.py")
    inputs = [entry(__file__), entry(SUPPORT.parent/"notes/upl_gpu_wall_pair_r1.json")]
    inputs += [entry(SUPPORT/name) for name in DEPENDENCIES]
    analysis = inputs[0]
    a = load_run(args.a, args.a_data, util, inputs)
    b = load_run(args.b, args.b_data, util, inputs) if args.b is not None else None
    ps, us = float(public.PS), float(public.US)
    columns = {"part": np.arange(a["samples"]), "time_s": a["times"]}
    report = dict(action=args.action, model=a["model"], a=compact(a), b=compact(b) if b else None,
                  native_count=N, fixed_count=FIXED, samples=a["samples"], common_columns=C,
                  normalizers=dict(Pstar_Pa=ps, Ustar_m=us, A_m_s=AMP, cu0_m_s=float(public.CU)),
                  absolute_gates_applied=args.action in ("Half", "Cross"), normalized_half_gates_applied=args.action == "Half",
                  normalized_half_limit=1e-4 if args.action == "Half" else None,
                  pressure_RMS_limit_Pa=5. if args.action in ("Half", "Cross") else None,
                  max_material_displacement_limit_mm=.005 if args.action in ("Half", "Cross") else None)
    refs = None
    if b is not None:
        need(a["window"] == b["window"] and np.array_equal(a["times"], b["times"]) and
             np.array_equal(a["x0"].view(np.uint64), b["x0"].view(np.uint64)) and
             np.array_equal(a["fixed"].view(np.uint64), b["fixed"].view(np.uint64)) and
             np.array_equal(a["planes"], b["planes"]), "Different actual times or native/fixed material geometry")
        need(np.array_equal(a["q"][0].view(np.uint64), b["q"][0].view(np.uint64)), "Initial all33 bit patterns differ; no initial diagnostic/signed-zero masking")
        if args.action == "Half":
            need(a["backend"] == b["backend"] and a["model"] == b["model"] and
                 (a["dt"], b["dt"]) == (DC, DH), "Half must be independent same-backend/model coarse then half")
        elif args.action == "Cross":
            need({a["backend"], b["backend"]} == {"CPU", "GPU"} and a["model"] == b["model"] and
                 a["dt"] == b["dt"], "Cross requires same-model/dt CPU and GPU, not a half")
        else:
            need(a["backend"] == b["backend"] == "GPU" and a["model"] == "constant" and
                 b["model"] == "variable" and a["window"] == "full" and a["dt"] == b["dt"],
                 "Effect requires same-dt full constantA versus variableB GPU")
        delta = a["q"]-b["q"]
        pressure = np.sqrt((delta[:, :, 6]**2).mean(axis=1))
        velocity = np.sqrt((delta[:, :, 3:6]**2).sum(axis=2).mean(axis=1))
        displacement = np.sqrt((delta[:, :, 25:28]**2).sum(axis=2).mean(axis=1))
        umax = 1000.*np.linalg.norm(delta[:, :, 25:28], axis=2).max(axis=1)
        absolute = bool((pressure <= 5).all() and (umax <= .005).all())
        normalized = bool((pressure/ps <= 1e-4).all() and (velocity/AMP <= 1e-4).all() and (displacement/us <= 1e-4).all())
        columns.update(pressure_RMS_Pa=pressure, pressure_RMS_over_Pstar=pressure/ps,
                       velocity_vector_RMS_m_s=velocity, velocity_RMS_over_A=velocity/AMP,
                       material_u_vector_RMS_m=displacement, material_u_RMS_over_Ustar=displacement/us,
                       max_material_u_difference_mm=umax, max_abs_J_difference=np.abs(delta[:, :, 8]).max(axis=1),
                       stress_Frobenius_RMS_Pa=np.sqrt((delta[:, :, [10, 13, 15]]**2).sum(axis=2).mean(axis=1)+2.*(delta[:, :, [11, 12, 14]]**2).sum(axis=2).mean(axis=1)),
                       passive_Rhop_RMS_kg_m3=np.sqrt((delta[:, :, 24]**2).mean(axis=1)))
        passed = absolute and (normalized if args.action == "Half" else True)
        report.update(initial_all33_bits_exact=True, absolute_gates_passed=absolute if args.action != "Effect" else None,
                      normalized_cross_or_effect_metrics_descriptive_only=args.action != "Half",
                      all33_evolved_bits_exact_descriptive=bool(np.array_equal(a["q"].view(np.uint64), b["q"].view(np.uint64))))
        if args.action == "Effect":
            halfmax = own_half(args.half_check, b, util, inputs, analysis)
            threshold = max(.001, 10.*halfmax)
            passed = bool(float(pressure.max()) > threshold)
            report.update(own_GPU_half=entry(args.half_check), own_GPU_half_pressure_RMS_max_Pa=halfmax,
                          effect_strict_lower_limit_Pa=threshold, resolved_option_effect_passed=passed,
                          option_effect_not_theory_or_half_error=True)
    else:
        need(a["model"] == "constant" and a["window"] == "full" and a["samples"] == 257,
             "Reference is only original constant-k full wall window; variable has no such truth gate")
        refs, gap = rk_reference(a["times"], public)
        errors, near, endpoint, passed = reference_metrics(a, refs, public)
        for j, name in enumerate(("p", "v_XYZ", "u_XYZ")):
            columns["constant_global_"+name+"_RMS_normalized"] = errors[:, j]
            columns["constant_wall_band_"+name+"_RMS_normalized"] = near[:, j]
        report.update(constant_reference_used=True, original_one_percent_objective=True,
                      max_global_normalized_RMS=errors.max(axis=0).tolist(),
                      max_wall_band_normalized_RMS=near.max(axis=0).tolist(),
                      material_band_native_count=int(a["band"].sum()), endpoint_pressure_relative_error=endpoint,
                      expm_vs_physical_RK4_max_normalized_difference=gap,
                      reference_crosscheck_limit=2e-11)
    phase = 2.*math.pi*a["x0"][:, 0]/LX
    for label, run in (("a", a), ("b", b)):
        if run is None:
            continue
        columns["pressure_cosine_mode_over_Pstar_"+label] = 2.*np.mean(run["q"][:, :, 6]*np.cos(phase), axis=1)/ps
        columns["vx_sine_mode_over_A_"+label] = 2.*np.mean(run["q"][:, :, 3]*np.sin(phase), axis=1)/AMP
        columns["ux_sine_mode_over_Ustar_"+label] = 2.*np.mean(run["q"][:, :, 25]*np.sin(phase), axis=1)/us
        columns["energy_ratio_"+label] = run["energy"]
        columns["k_spatial_span_over_k0_"+label] = run["kspan"]
    if refs is not None:
        for j, name in enumerate(("pressure_cosine_mode_over_Pstar", "vx_sine_mode_over_A", "ux_sine_mode_over_Ustar")):
            columns[name+"_reference"] = refs[:, j]
    with files[1].open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream); writer.writerow(columns)
        for i in range(a["samples"]):
            writer.writerow([format(float(value[i]), ".17g") for value in columns.values()])
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.8), constrained_layout=True)
    for axis, name, ylabel in zip(axes.flat[:3], ("pressure_cosine_mode_over_Pstar", "vx_sine_mode_over_A", "ux_sine_mode_over_Ustar"),
                                  ("Pressure cosine mode / P*", "Velocity sine mode / A", "Material-u sine mode / U*")):
        for label, run, style in (("a", a, "-"), ("b", b, "--")):
            if run is not None:
                axis.plot(a["times"]*1e6, columns[name+"_"+label], style,
                          label=f"{label.upper()}: {run['backend']} {run['model']}, dt={run['dt']:.5g}s")
        if refs is not None:
            axis.plot(a["times"]*1e6, columns[name+"_reference"], "k:", label="Constant-k continuum4x4")
        axis.set(ylabel=ylabel)
    axis = axes[1, 1]
    if args.action == "Reference":
        for j, name in enumerate(("p", "v XYZ", "u XYZ")):
            axis.plot(a["times"]*1e6, 100.*errors[:, j], label="Global "+name)
            axis.plot(a["times"]*1e6, 100.*near[:, j], "--", label="Wall-band "+name)
        axis.axhline(1., color="k", linestyle=":", label="Original1% objective")
        axis.set(ylabel="Full XYZ normalized RMS [%]")
    elif args.action == "Effect":
        axis.plot(a["times"]*1e6, pressure, label="Variable-k option pressure RMS effect")
        axis.axhline(report["effect_strict_lower_limit_Pa"], color="k", linestyle=":", label="max(.001Pa,10x own GPUhalf)")
        axis.set(ylabel="Option pressure difference [Pa], not theory error")
    else:
        for value, name in ((pressure/ps, "p RMS / P*"), (velocity/AMP, "v XYZ RMS / A"), (displacement/us, "u XYZ RMS / U*")):
            axis.plot(a["times"]*1e6, value, label=name)
        axis.axhline(1e-4, color="k", linestyle=":", label="Original half limit" if args.action == "Half" else "Half limit reference only, not cross gate")
        axis.set(ylabel="Normalized pair differences")
    for axis in axes.flat:
        axis.set(xlabel="Actual saved time [microseconds]"); axis.grid(alpha=.23); axis.legend(fontsize=7)
    fig.suptitle(f"Private opposing-wall {args.action}: {a['samples']} exact times; no general/full physical admission")
    fig.savefig(files[2], dpi=175); plt.close(fig)
    for bound in inputs:
        need(entry(bound["path"]) == bound, "Bound input changed during offline analysis")
    report.update(passed=bool(passed), analysis_program=analysis,
                  maxima={key: float(np.max(value)) for key, value in columns.items() if key not in ("part", "time_s")},
                  inputs=inputs, files=[entry(files[1]), entry(files[2])], runtime_versions=dict(python=sys.version, numpy=np.__version__, matplotlib=matplotlib.__version__),
                  no_native_fields_or_initial_bits_masked=True, no_smoothing_or_interpolation=True,
                  raw_BI4_reparsed=False, owned_solver_exit_verified_by_this_script=False,
                  endpoint_force_audit_verified_by_this_script=False, passive_density_exactness_required=False,
                  fixed_marker_n_cross_backend_exactness_required=False, physical_acceptance=False,
                  limitations=["Typed33 exports, not a second BI4 reader; root must bind owned solver/build/reader/audit receipts",
                               "GPU soilV/rho/k are derived, CPU values native; fixed sample n/zero markers are separate",
                               "Saved last-stage theta is not endpoint theta; separate complete257 endpoint audit remains required",
                               "Half/Cross/Effect are distinct; only constant Reference applies original1% continuum objectives",
                               "Necessary scales/conditional energy and these weak windows do not admit publicGPU/general walls/restarts/fullcycle"])
    with files[0].open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False); stream.write("\n")
    print(json.dumps(dict(passed=bool(passed), action=args.action, output=str(files[0]))))
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, KeyError, OSError, RuntimeError, struct.error) as error:
        print("HELD offline wall pair/reference; no solver rerun: "+str(error), file=sys.stderr)
        sys.exit(1)
