"""Independent read-only Darcy33/receipt/CSV audit. Never import the pair implementation or run tools."""
import csv
import hashlib
import json
import math
from pathlib import Path
import struct

import numpy as np

T = Path(__file__).resolve().parent.parent
N, C, DP, LX, LZ, A = 512, 33, 2.**-8, 2.**-3, 2.**-4, 2.**-9
K, G, KW, RHO0, RHOW, N0 = 89478488., 134217728., 67108864., 2048., 1000., .25
M, V0, H, EPS = K+4*G/3, DP**2, float(np.float32(1.8*DP)), np.finfo(float).eps
CU = math.sqrt((M+KW/N0)/RHO0)
PSTAR, USTAR = KW/N0*A/CU, A/(CU*2*math.pi/LX)
CACHE, BUILDS, CHECKS = {}, {}, []
BINDINGS = 0


def require(ok, message):
    if not bool(ok):
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"),
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def entry(path):
    p = Path(path).resolve()
    digest = hashlib.sha256()
    with p.open("rb") as stream:
        for block in iter(lambda: stream.read(2**20), b""):
            digest.update(block)
    return {"path": str(p), "bytes": p.stat().st_size, "sha256": digest.hexdigest()}


def verify(value):
    global BINDINGS
    if isinstance(value, list):
        for item in value:
            verify(item)
    elif isinstance(value, dict):
        if {"path", "bytes", "sha256"} <= value.keys():
            BINDINGS += 1
            p = Path(value["path"]).resolve()
            wanted = {"path": str(p), "bytes": value["bytes"], "sha256": value["sha256"].lower()}
            key = str(p).casefold()
            if key not in CACHE:
                CACHE[key] = entry(p)
            require(CACHE[key] == wanted, f"Changed/conflicting binding: {p}")
        else:
            for item in value.values():
                verify(item)


def owned(binding):
    verify(binding)
    q = read(binding["path"])
    require(q.get("owned_call_exited") is True and q["exit_code"] == 0, "Owned exit0 missing")
    verify(q["program"]); verify(q["log"])
    if q.get("target_program"):
        verify(q["target_program"])
    if q.get("memcheck_executed"):
        raw = Path(q["log"]["path"]).read_bytes()
        text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
        require(q["memcheck_zero_errors_and_leaks"] and "ERROR SUMMARY: 0 errors" in text and
                "LEAK SUMMARY: 0 bytes leaked in 0 allocations" in text, "Actual memcheck log failed")
    return q


def helper(binding):
    verify(binding)
    if binding["path"] in BUILDS:
        return BUILDS[binding["path"]]
    h = read(binding["path"])
    require(h["fixture"] == "DarcyActual" and h["exact_link_closure_verified"] and
            h["link_object_count"] == 111 and h["GPU_object_substitutions"] == 110, "Helper identity")
    for key in ("inputs", "author_files", "tools", "libraries", "objects", "runtime", "program",
                "transitive_project_include_files", "source_build"):
        verify(h[key])
    g = read(h["source_build"]["path"])
    for key in ("inputs", "objects", "source_freeze", "project_call", "baseline", "isolated_GPU_program", "runtime"):
        verify(g[key])
    s = read(g["source_freeze"]["path"]); verify(s["source"]); verify(s["five_targets"])
    require(len(s["source"]) == 265 and len(s["five_targets"]) == 5 and len(g["objects"]) == 110,
            "Current source/object closure")
    b = read(g["baseline"]["path"]); verify(b["canonical_GPU"]); verify(b["other_source"])
    owned(h["compile_call"]); link = owned(h["link_call"])
    actual = {str(Path(x).resolve()).casefold() for x in link["arguments"] if x.lower().endswith(".obj")}
    expected = {str(Path(x["path"]).resolve()).casefold() for x in g["objects"]}
    expected.add(str(Path(h["program"]["path"]).parent/"helper.obj").casefold())
    require(len(actual) == 111 and actual == expected, "Actual link is not current110+helper")
    BUILDS[binding["path"]] = h
    return h


def table(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    return {key: np.array([float(r[key]) for r in rows]) for key in rows[0]}


def close(actual, expected, label, factor=128.):
    actual, expected = np.asarray(actual), np.asarray(expected)
    require(actual.shape == expected.shape and np.isfinite(actual).all() and
            np.all(np.abs(actual-expected) <= factor*EPS*np.maximum(np.abs(expected), np.finfo(float).tiny)),
            f"Independent roundoff-level comparison failed: {label}")


def load(name):
    cp = T/"logs"/f"upl_gpu_darcy_actual_{name}_r1.check.json"
    check = read(cp); CHECKS.append(entry(cp)); verify(entry(cp))
    require(check["passed"] and not check["physical_acceptance"] and not check["new_CPU_solver_run"], "Native check")
    verify(check)
    h = helper(check["helper"]); reader = owned(check["call"])
    source = read(check["source_run"]["path"]); verify(source)
    require(source["owned_solver_exit0"] and source["solver_completed_before_analysis"], "Solver ownership")
    original = owned(source["call"]); selected = source["selected_input"]
    cpu, retained = check["backend"] == "CPU", name.startswith("retained_")
    smoke = name == "Smoke"; samples = 3 if smoke else 257
    dt = 2.**(-25 if name.endswith("_h") else -24); cadence = dt if smoke else 2.**-23
    times = np.arange(samples)*cadence
    require(selected["dt"] == dt and selected["samples"] == samples and
            selected["end"] == times[-1] and selected["cadence"] == cadence and
            selected["bi4"]["sha256"] == "364c4421a8b539d0e8e5eb67e00c547657c9c65f48cd7e83168a4ad32cd5a8fa",
            "Seed and actual saved-clock contract")
    if retained:
        require(source["retained_run_reused"] and source["new_solver_run"] is False and
                check["retained_native_re_read"], "Adoption is not a new solve")
        old = read(source["old_source_run"]["path"]); verify(old["files"])
        require(old["call"] == source["call"], "Original owned call changed")
    else:
        finish = read(source["actual_completion"]["path"])
        require(finish["passed"] and finish["actual_production_Run"] and finish["private_complete_dynamic_rate"] and
                finish["private_feedback"] and finish["predictor_histories_released"] and
                not finish["public_GPU_dynamic_mode"] and not finish["physical_fields_rewritten_by_fixture"] and
                finish["completed_steps"] == selected["steps"] and finish["actual_end_s"] == times[-1], "Actual Run finish")
        require(original["actual_GPU_Run_invoked"], "New owned GPU invocation missing")
        if smoke:
            require(original["memcheck_zero_errors_and_leaks"], "Successful actual two-step memcheck required")
    if cpu:
        require(original["arguments"][0:2] == ["-cpu", "-ompthreads:1"] and
                original["program"]["sha256"] == "234b60bd33cd65514f574b1f8df0fda4afc9a873eb8f125e2236d3470d7b28f8",
                "Historical CPU1-thread control identity; no timing inference")
    folder = Path(check["completion"]["path"]).parent
    args = reader["target_arguments"]
    expected_args = ["--read", check["model"], check["backend"], args[3], format(dt, ".17g"),
                     selected["xml"]["path"], str(folder)]
    require(args[:4] == expected_args[:4] and float(args[4]) == dt and args[5:7] == expected_args[5:7] and
            args[7:] == (["--smoke"] if smoke else []) and reader["target_program"] == h["program"], "Reader argv")
    rawdir = Path(args[3]); require(len(list(rawdir.glob("Part_*.bi4"))) == samples, "Raw native frame count")
    d = read(folder/"completion.json")
    kh = 0. if check["model"] == "k0" else float(np.float32(1e-4))
    require(d["passed"] and d["common_columns"] == 33 and d["samples"] == samples and d["native_count"] == N and
            d["native_J_arrays"] == (6 if cpu else 3) and d["native_PosDiv_observed"] is cpu and
            d["public_dynamic_metadata"] is cpu and d["GPU_V_rho_k_derived_not_native_arrays"] is not cpu and
            d["runtime_XML_exact_model_material_and_clock_checked"] and not d["physical_acceptance"], "Typed native/derived attribution")
    path = folder/"physical.bin"
    with path.open("rb") as stream:
        require(struct.unpack("<III", stream.read(12)) == (N, C, samples), "Common33 header")
    require(path.stat().st_size == 12+samples*(1+N*C)*8, "Common33 exact length")
    raw = np.fromfile(path, dtype="<f8", offset=12).reshape(samples, 1+N*C)
    require(np.isfinite(raw).all() and np.array_equal(raw[:, 0], times), "Every binary field/time finite/exact")
    q = raw[:, 1:].reshape(samples, N, C); hist = table(folder/"history.csv"); ids = table(folder/"native_ids.csv")
    require(np.array_equal(ids["id"], np.arange(N)) and np.array_equal(ids["row"], np.arange(N)), "Native ID alignment")
    x0 = np.column_stack([ids[k] for k in ("x0", "y0", "z0")])
    require(np.array_equal(q[0, :, :3], x0) and np.array_equal(q[:, :, 25:28], q[:, :, :3]-x0), "Material reference")
    steps = np.rint(times/dt).astype(int)-1; steps[0] = 0
    require(all(np.isfinite(v).all() for v in hist.values()) and np.array_equal(hist["part"], np.arange(samples)) and
            np.array_equal(hist["time_s"], times) and np.array_equal(hist["saved_step"], steps) and
            (hist["dt_s"] == dt).all() and (hist["dterror_s"] <= 1e-14).all(), "All saved-clock/signed safety")
    j, n = q[:, :, 8], q[:, :, 29]; nr = 1.-.75/j; volume = V0*j; rho = RHOW+(RHO0-RHOW)/j
    require((j > .75).all() and (abs(j-1) <= 1e-4).all() and (n > 0).all() and (n < 1).all() and
            (abs((1-n)*j-.75) <= 5e-13).all(), "J/n saturated domain")
    for actual, ref in ((n, nr), (q[:, :, 30], volume), (q[:, :, 31], rho)):
        require((abs(actual-ref) <= 5e-13*abs(ref)).all(), "All-node ledger")
    require((q[:, :, 32] == kh).all() and (q[:, :, 16] == 0).all() and (q[:, :, 7] == 0).all() and
            (q[:, :, 21:24] == 0).all() and ((q[:, :, 24] >= 700) & (q[:, :, 24] <= 3000)).all(), "Original elastic/load/p0/passive domain")
    require(np.array_equal(q[:, :, 28], (q[:, :, 6].astype("f4")-q[:, :, 7].astype("f4")).astype("f4").astype("f8")), "Float excess")
    diag, shear = q[:, :, [10, 13, 15]], q[:, :, [11, 12, 14]]
    trace = diag.sum(axis=2); devnorm = ((diag-trace[:, :, None]/3)**2).sum(axis=2)+2*(shear**2).sum(axis=2)
    energy = (volume*(.5*rho*(q[:, :, 3:6]**2).sum(axis=2)+devnorm/(4*G)+trace**2/(18*K)+n*q[:, :, 6]**2/(2*KW))).sum(axis=1)
    er = energy/energy[0]; cfl = np.sqrt((M+KW/nr)/rho)*dt/H; diffusion = KW/nr*kh/(RHOW*9.80665)*dt/H**2
    require(energy[0] > 0 and (er <= 1.1).all() and (cfl <= .01).all() and (diffusion <= .01).all(), "Original energy/necessary scales")
    if kh:
        margin = rho*(KW/nr)/(M+KW/nr)-RHOW
        require((margin > 64*EPS*np.maximum(rho, RHOW)).all(), "Necessary positive-k domain")
    require(np.max(abs(hist["energy_ratio"]-er)) <= 64*EPS*N*max(1., er.max()), "Energy sum telemetry roundoff")
    if cpu:
        posdiv = table(folder/"cpu_posdiv.csv")
        require(np.array_equal(posdiv["part"], np.repeat(np.arange(samples), N)) and
                np.array_equal(posdiv["id"], np.tile(np.arange(N), samples)) and
                np.isfinite(posdiv["actual_native_PosDiv"]).all(), "Actual native CPU PosDiv sidecar")
    else:
        require(not (folder/"cpu_posdiv.csv").exists(), "No invented GPU PosDiv")
    if not retained:
        live = rawdir.parent/"live_final.csv"
        require(entry(live)["sha256"] == entry(folder/"last_poro.csv")["sha256"], "Native final/live equality")
    return {"name": name, "q": q, "energy": er, "folder": folder, "samples": samples, "retained": retained,
            "backend": check["backend"], "metrics": {"max_energy": float(er.max()), "max_CFL": float(cfl.max()),
            "max_diffusion": float(diffusion.max()), "J_native_arrays": d["native_J_arrays"]}}


def pair(kind, a, b):
    summary = read(T/"figures"/f"upl_gpu_darcy_actual_{kind}_r1.json"); verify(summary["inputs"]); verify(summary["files"])
    require(summary["passed"] and summary["samples"] == 257 and summary["common_columns"] == C and
            summary["pressure_RMS_limit_Pa"] == 5 and summary["max_material_displacement_limit_mm"] == .005 and
            summary["all_actual_times_and_native_IDs_matched"] and not summary["physical_acceptance"], "Pair contract")
    x, y = a["q"], b["q"]; delta = x-y; v2 = (delta[:, :, 3:6]**2).sum(axis=2); u2 = (delta[:, :, 25:28]**2).sum(axis=2)
    pr, vr, ur = np.sqrt((delta[:, :, 6]**2).mean(axis=1)), np.sqrt(v2.mean(axis=1)), np.sqrt(u2.mean(axis=1))
    du = 1000*np.sqrt(u2).max(axis=1)
    ss = delta[:, :, [10, 13, 15]]; st = delta[:, :, [11, 12, 14]]
    columns = {"part": np.arange(257), "time_s": np.arange(257)*2.**-23, "pressure_RMS_Pa": pr,
        "pressure_RMS_over_Pstar": pr/PSTAR, "velocity_vector_RMS_m_s": vr, "velocity_RMS_over_A": vr/A,
        "material_u_vector_RMS_m": ur, "material_u_RMS_over_Ustar": ur/USTAR, "max_material_u_difference_mm": du,
        "max_abs_J_difference": abs(delta[:, :, 8]).max(axis=1),
        "stress_Frobenius_RMS_Pa": np.sqrt((ss**2).sum(axis=2).mean(axis=1)+2*(st**2).sum(axis=2).mean(axis=1)),
        "max_stress_component_difference_Pa": abs(delta[:, :, 10:16]).max(axis=(1, 2)),
        "passive_Rhop_RMS_kg_m3": np.sqrt((delta[:, :, 24]**2).mean(axis=1)),
        "max_passive_Rhop_difference_kg_m3": abs(delta[:, :, 24]).max(axis=1), "energy_ratio_a": a["energy"], "energy_ratio_b": b["energy"]}
    for label, z in (("a", x), ("b", y)):
        for suffix, values in (("pressure_RMS_Pa", z[:, :, 6]**2), ("velocity_vector_RMS_m_s", (z[:, :, 3:6]**2).sum(axis=2)),
                               ("material_u_vector_RMS_m", (z[:, :, 25:28]**2).sum(axis=2))):
            columns[f"actual_{suffix}_{label}"] = np.sqrt(values.mean(axis=1))
    measured = table(T/"figures"/f"upl_gpu_darcy_actual_{kind}_r1.csv")
    require(measured.keys() == columns.keys(), "Full pair CSV column coverage")
    for key, value in columns.items():
        close(measured[key], value, f"{kind}/{key}")
        if key not in ("part", "time_s"):
            close(summary["maxima"][key], value.max(), f"{kind}/maximum/{key}")
    half = kind in ("k0_half", "GPU_half")
    require((pr <= 5).all() and (du <= .005).all() and summary["normalized_half_gates_applied"] is half, "Original absolute pair gates")
    if half:
        require((pr/PSTAR <= 1e-4).all() and (vr/A <= 1e-4).all() and (ur/USTAR <= 1e-4).all() and
                summary["normalized_half_limit"] == 1e-4, "Independent half normalized gates")
    bd, nd = x.view("u8") != y.view("u8"), x != y
    for i, field in enumerate(summary["per_column_exactness_descriptive_not_half_gate"]):
        require(field["column"] == i and field["different_bit_patterns"] == int(bd[:, :, i].sum()) and
                field["different_numeric_values"] == int(nd[:, :, i].sum()) and
                field["initial_different_bit_patterns"] == int(bd[0, :, i].sum()) and
                field["initial_different_numeric_values"] == int(nd[0, :, i].sum()), "All33 mismatch counts")
        close(field["maximum_abs_numeric_difference"], abs(delta[:, :, i]).max(), "All33 maximum difference")
    require(summary["all_33_values_bitwise_equal_descriptive"] == bool(not bd.any()) and
            summary["all_33_values_numerically_equal_descriptive"] == bool(not nd.any()), "Descriptive equality truth")
    return {"pair": kind, "pressure_RMS_max_Pa": float(pr.max()), "displacement_max_mm": float(du.max()),
            "normalized_half": half, "all33_bitwise_equal": bool(not bd.any()), "all257_CSV_columns_recomputed": len(columns)}


def main():
    names = ["Smoke", "GPU_k0_c", "GPU_k0_h", "GPU_constant_c", "GPU_constant_h",
             "retained_GPU_legacy_k0_c", "retained_GPU_legacy_k0_h", "retained_CPU_constant_c", "retained_CPU_constant_h"]
    runs = {name: load(name) for name in names}
    plans = {"k0_bridge_c": ("GPU_k0_c", "retained_GPU_legacy_k0_c"), "k0_bridge_h": ("GPU_k0_h", "retained_GPU_legacy_k0_h"),
             "k0_half": ("GPU_k0_c", "GPU_k0_h"), "GPU_half": ("GPU_constant_c", "GPU_constant_h"),
             "cross_c": ("retained_CPU_constant_c", "GPU_constant_c"), "cross_h": ("retained_CPU_constant_h", "GPU_constant_h")}
    pairs = [pair(key, runs[left], runs[right]) for key, (left, right) in plans.items()]
    for old in CACHE.values():
        require(entry(old["path"]) == old, "Artifact changed during audit")
    result = {"passed": True, "stage": "upl_gpu_darcy_actual_audit_r1", "checks": CHECKS,
        "binding_verifications": BINDINGS, "unique_files_hashed_before_and_after": len(CACHE), "binding_mismatches": 0,
        "new_GPU_solver_jobs": 5, "new_CPU_solver_jobs": 0, "retained_original_raw_re_reads": 4,
        "typed33_saved_frame_instances": sum(x["samples"] for x in runs.values()),
        "typed33_native_node_records": sum(x["samples"] for x in runs.values())*N,
        "all33_fields_finite_and_all_node_ledgers_recomputed": True, "all257_pair_CSV_metrics_and33_mismatch_counts_recomputed": True,
        "runs": [{k: v for k, v in x.items() if k not in ("q", "energy", "folder")} for x in runs.values()], "pairs": pairs,
        "schema_scope": "CPU6 native J-derived Double arrays and observed native PosDiv sidecar versus GPU3 native Double J/n/theta with explicitly derived V/rho/k; no PosDiv fabrication.",
        "density_scope": "Original CPU1-thread controls retain rational passive-Rhop corrector; GPU active legacy corrector is additive. Neither is the J-derived mixture inertia. This is not a CPU rerun or timing benchmark.",
        "proof_scope": "Original BI4 type/storage/metadata guards derive from frozen actual reader source and owned exit0 calls bound to raw hashes; this audit independently decodes all saved common33 binaries, not a new BI4 parser.",
        "limitations": ["Necessary saved acoustic/diffusion/RH screens, not independently traced every force stage or sufficient stability.",
                        "Half agreement is not0ULP; bit equality is separately descriptive.", "No general physical/public GPU/wall/variable-k/restart/full-cycle acceptance.",
                        "Raw BI4/exe/physical.bin protected local and hash-bound, not cloud backup."],
        "program_or_solver_rerun": False, "production_changed": False, "physical_acceptance": False}
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
