"""One root-admitted offline full2Tv B science review; no solver/reader/build/hash."""
from __future__ import annotations
import argparse
import csv
import json
import math
import os
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
TAG = "upl_tpi_gpu_full2tv_review_r1"
NOTE = T / "notes" / (TAG + ".md")
BASE_XML = T / "configs/upl_bigstep_c625_r1.xml"
PLAN_NOTE = T.parent.parent / "validation/upl_tpi_three_scheme_plan_r1.md"
DEFINITIONS = (T / "support/upl_tpi_gpu_startup_review_r2.py", T / "support/upl_bigstep_full_review_r1.py",
               T / "support/gpu_coupled_compare.py")
CHECK = T / "logs" / (TAG + ".check.json")
PRODUCTS = {name: T / "figures" / (TAG + "." + name) for name in
            ("history.csv", "layers.csv", "profiles.csv", "profile_times.csv", "cross.csv", "noninferiority.csv",
             "metrics.json", "history.png", "profiles.png", "settlement_profiles.png", "modes.png")}
FULL_TAG = "upl_tpi_gpu_Release_B_full2tv_r1"
B_REVIEW = T / "logs" / (FULL_TAG + ".native_review_full_r1.json")
A_REVIEW = T / "logs/upl_bigstep_full_r1.review.json"
A_NATIVE = T / "logs/upl_bigstep_full_r1.native.json"
A_PLAN = T / "logs/upl_bigstep_full_r1.clock.csv"
A_DIRECTORY = T / "outputs/upl_bigstep_2tv_CPU1_r1_native_r1"
A_LAYERS = T / "figures/upl_bigstep_full_r1.layers.csv"
UPW_CHECK = T / "logs/upl_full_upw_compare_r1.check.json"
UPW_HISTORY = T / "figures/upl_full_upw_compare_r1.history.csv"
UPW_PROFILES = T / "figures/upl_full_upw_compare_r1.profiles.csv"
N, SOIL, FIXED, STEPS, POST = 1682, 1000, 40, 11661219, 1564
DT, END, EVENT = 6.250143051147461e-6, 72.88428689946836, 1600
REQUESTED = (.005, .05, .1, .25, .4, .5, .7, 1., 1.5, 2.)
FIELDS = "x y z vx vy vz PorePress PorePress0 J theta sigma_xx sigma_xy sigma_xz sigma_yy sigma_yz sigma_zz Kplastic FSType FSNormal_x FSNormal_y FSNormal_z ExcessPorePress LoadAce_x LoadAce_y LoadAce_z legacy_Rhop".split()
COMPONENTS = ("xx", "xy", "xz", "yy", "yz", "zz")
LABELS = {"A": "Retained A: finite Kw, CPU1", "B": "New B: TPI alpha=.5, M0, GPU"}
COLORS = {"A": "tab:blue", "B": "tab:orange"}


def need(ok, message):
    if not bool(ok):
        raise ValueError(message)


def stat(path):
    p = Path(path).resolve(); s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def write_json(path, value):
    with path.open("x", encoding="utf8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False); f.write("\n")


def write_csv(path, rows):
    need(bool(rows), "Empty scientific table is not a completed product")
    with path.open("x", encoding="utf8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def save_png(fig, path):
    with path.open("xb") as f:
        fig.savefig(f, format="png", dpi=165)


class Admission:
    def __init__(self, path):
        self.entry = stat(path)
        self.data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        need(self.data.get("stage") == TAG + ".admission" and self.data.get("passed") is True and
             self.data.get("offline_only") is True, "Root full-read offline-only admission required")
        self.frozen = {str(Path(e["path"]).resolve()): e for e in self.data["inputs"]}
        need(len(self.frozen) == len(self.data["inputs"]), "Duplicated admission input path")
        self.used = {}
        for p in (Path(__file__), NOTE, BASE_XML, PLAN_NOTE, *DEFINITIONS): self.pin(p)

    def pin(self, path):
        key = str(Path(path).resolve())
        need(key in self.frozen, "Consumed input absent from admission: " + key)
        expected = {k: self.frozen[key][k] for k in ("path", "bytes", "mtime_ns")}
        need(stat(key) == expected, "Root-frozen input stat changed: " + key)
        self.used[key] = expected
        return Path(key)

    def read(self, path):
        return json.loads(self.pin(path).read_text(encoding="utf-8-sig"))

    def table(self, path):
        with self.pin(path).open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def finish(self):
        for entry in self.used.values(): need(stat(entry["path"]) == entry, "Consumed file changed during offline review")
        need(stat(self.entry["path"]) == self.entry, "Root admission changed")


def binary(ad, path, header, dtype, np):
    path = ad.pin(path); size = 4 * len(header)
    with path.open("rb") as f:
        need(struct.unpack("<" + "I" * len(header), f.read(size)) == header, "Native binary declaration differs: " + path.name)
    need(path.stat().st_size == size + N * dtype.itemsize, "Native record size/count differs: " + path.name)
    return np.memmap(path, dtype=dtype, mode="r", offset=size, shape=(N,))


def timing(ad, directory, scheme):
    with ad.pin(directory / "Run.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    need(len(rows) == 1, "One original Run.csv row required")
    r = rows[0]
    need(int(r["Steps"]) == STEPS and int(r["PartFiles"]) == N and int(r["Np"]) == 1040 and
         int(r["Nfixed"]) == int(r["Nbound"]) == FIXED and int(r["PartsOut"]) == 0, "Actual complete runtime identity differs")
    need(("gpu" in r["Hardware"].lower()) == (scheme == "B"), "Actual backend differs from the declared control")
    loop, total = float(r["TSimul"]), float(r["TTotal"])
    need(all(math.isfinite(x) and x > 0 for x in (loop, total)), "Nonpositive/nonfinite observed runtime")
    return dict(TSimul_s=loop, TTotal_s=total, actual_steps=STEPS, actual_native_frames=N,
                original_TSimul_token=r["TSimul"], original_TTotal_token=r["TTotal"],
                observed_steps_per_TSimul_s=STEPS / loop, hardware=r["Hardware"], RunMode=r["RunMode"],
                rounded_PhysicalTime_not_used_as_clock=r["PhysicalTime"], controlled_benchmark=False,
                cross_backend_runtime_is_not_TPI_speedup=True, nonisolated_and_instrumented=True)


def load(ad, scheme, np, result):
    if scheme == "B":
        review = ad.read(B_REVIEW)
        need(review.get("stage") == "upl_tpi_gpu_full2tv_native_r1.review" and review.get("passed") is True and
             review.get("original_native_guards_not_relaxed") is True and review.get("physical_acceptance") is False,
             "The actual independent full-B native review must pass before science")
        job = review["job"]
        need((job["tag"], job["scheme"], job["window"], job["configuration"]) ==
             (FULL_TAG, "B", "full2tv", "Release"), "Full-B owner/profile association differs")
        directory = T / "outputs" / (FULL_TAG + "_native_full_r1")
        need(Path(job["native_output"]).resolve() == directory.resolve(), "Full-B native directory differs")
        native = ad.read(T / "logs" / (FULL_TAG + ".native_full_r1.json"))
        need(native.get("passed") is True and Path(native["job"]["native_output"]).resolve() == directory.resolve(),
             "Full-B unique native-read receipt does not bind this output")
        prefix = review["same_B_short_actual_prefix"]
        need(prefix.get("actual_shared_old_new_indices") == [[i, i] for i in range(343)] and
             len(prefix["files"]) == 5 and all(x["all_shared_export_record_bytes_equal"] for x in prefix["files"]),
             "The passed native review must retain its real343 same-B shared records")
        plan_path = job["plan"]["path"]
        runtime = Path(job["output_directory"])
        stage, backend, window = "upl_tpi_gpu_full2tv_native_r1", "GPU_full2Tv_private", "full2tv"
        source = dict(review=stat(B_REVIEW), native=stat(T / "logs" / (FULL_TAG + ".native_full_r1.json")),
                      HG_guards=review["HG_original_guards"], pressure_lifecycle=review["sidecar"],
                      inherited_shared343_proof=prefix, new_raw_prefix_comparison_performed=False)
    else:
        review, native = ad.read(A_REVIEW), ad.read(A_NATIVE)
        need(review.get("stage") == "upl_bigstep_full_review_r1.review" and review.get("passed") is True and
             native.get("stage") == "upl_bigstep_full_review_r1.native" and native.get("passed") is True and
             native.get("original_native_guards_passed") is True, "Retained finite-Kw full-A native/descriptive review required")
        directory, plan_path = A_DIRECTORY, A_PLAN
        need(Path(native["directory"]).resolve() == directory.resolve(), "Retained full-A native output association differs")
        run = ad.read(native["source_run"]["path"])
        need(run.get("passed") is True and run.get("backend") == "CPU" and run.get("threads") == 1 and
             run["job"]["SlipMode"] == 3, "Actual CPU1/FreeSlip A control association differs")
        runtime = Path(run["job"]["output_directory"])
        stage, backend, window = "upl_bigstep_native_r1", "CPU_public", "candidate_full2Tv"
        source = dict(review=stat(A_REVIEW), native=stat(A_NATIVE), old_passed_is_descriptive_not_100Pa_acceptance=True)
    done = ad.read(directory / "completion.json")
    required = dict(passed=True, stage=stage, backend=backend, window=window, samples=N,
                    native_count=SOIL, fixed_count=FIXED, total_native_count=1040, native_total_arrays=22,
                    physical_columns=26, physical_schema="case02_common26_col21_ExcessPorePress_NOT_wave26",
                    actual_end_s=END, planned_completed_steps=STEPS, noninitial_signed_dterror_intervals=N-1,
                    soil_ledger_checks=N*SOIL, fixed_public_zero_marker_checks=N*FIXED, all_native_J_theta_rows=N*1040,
                    post_open_frames=POST, post_open_drained_particle_checks=POST*10,
                    post_open_completed_step_threshold=EVENT, no_exclusions=True, all_exported_physical_fields_finite=True)
    for key, value in required.items(): need(done.get(key) == value, "Native completion differs: " + scheme + "/" + key)
    need(ad.table(directory / "columns.csv") == [dict(column=str(i), name=name) for i, name in enumerate(FIELDS)], "Case02 common26 columns differ")
    ids = ad.table(directory / "native_ids.csv")
    need(len(ids) == SOIL and [int(r["row"]) for r in ids] == list(range(SOIL)) and
         [int(r["id"]) for r in ids] == list(range(40, 1040)), "All1000 original material IDs/order differ")
    x0 = np.array([[float(r[c]) for c in ("x0", "y0", "z0")] for r in ids])
    layer, column = np.rint(x0[:, 2]/.01-.5).astype(int), np.rint(x0[:, 0]/.01-.5).astype(int)
    need(np.array_equal(np.sort(10*layer+column), np.arange(SOIL)) and np.all((layer >= 0) & (layer < 100)) and
         np.all((column >= 0) & (column < 10)) and np.all(x0[:, 1] == 0), "Original100-by10 material lattice differs")
    order = np.argsort(10*layer+column)
    physical = binary(ad, directory / "physical.bin", (SOIL, 26, N), np.dtype([("t", "<f8"), ("q", "<f8", (SOIL, 26))]), np)
    n = binary(ad, directory / "soil_n.bin", (SOIL, 1, N), np.dtype([("t", "<f8"), ("n", "<f8", (SOIL,))]), np)
    clock = binary(ad, directory / "clock.bin", (N, 28), np.dtype([("t", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("signed", "<f8")]), np)
    plan, history = ad.table(plan_path), ad.table(directory / "history.csv")
    need(len(plan) == len(history) == N, "All1682 actual plan/history states required")
    completed = np.array([int(r["completed_steps"]) for r in plan], dtype=np.int64)
    actual = np.array([float(r["time_s"]) for r in plan], dtype="<f8")
    # The already passed native phase replayed scalar +=dt; science consumes those actual clocks, not n*dt.
    need(completed[-1] == STEPS and actual[-1] == END and np.all(np.diff(actual) > 0) and
         physical["t"].tobytes() == n["t"].tobytes() == clock["t"].tobytes() == actual.tobytes(), "Actual native time payloads differ")
    need(np.array_equal(clock["step"], np.maximum(completed-1, 0)) and np.all(clock["dt"] == DT), "Saved Step/locked dt differs")
    need(np.isfinite(clock["signed"]).all() and np.all(clock["signed"][1:] <= 1e-14) and
         np.all(clock["signed"][1:] != -np.finfo(float).max), "Original signed nonempty interval guard failed")
    need(completed[117] == 1600 and completed[118] == 1601 and int(np.sum(completed > EVENT)) == POST,
         "Event1600 pre-open/post-open coverage differs")
    for i, (p, h) in enumerate(zip(plan, history)):
        need(int(p["part"]) == int(h["part"]) == i and float(h["time_s"]) == actual[i] and
             int(h["completed_step"]) == completed[i] and int(h["saved_step"]) == int(clock["step"][i]), "Native history actual identity differs")
    need(np.isfinite(physical["q"]).all() and np.isfinite(n["n"]).all(), "Nonfinite original exports")
    rho = np.empty((N, SOIL)); count = 0
    with ad.pin(directory / "ledger.csv").open(encoding="utf8", newline="") as f:
        for r in csv.DictReader(f):
            part, slot = divmod(count, SOIL)
            need(part < N and int(r["part"]) == part and int(r["id"]) == slot+40 and float(r["time_s"]) == actual[part] and
                 float(r["J"]) == physical["q"][part, slot, 8] and float(r["n_native"]) == n["n"][part, slot], "Native rho-ledger ID/time/J/n association differs")
            rho[part, slot] = float(r["rho_native_kg_m3"]); count += 1
    need(count == N*SOIL and np.isfinite(rho).all() and np.all(rho > 0), "All native rho ledger rows required")
    result["scheme_status"][scheme] = dict(qualified=True, native_arrays=22, saved_states=N, source=source,
                                          observed_runtime=timing(ad, runtime, scheme))
    return dict(scheme=scheme, p=physical, n=n, clock=clock, rho=rho, history=history, completed=completed,
                x0=x0, order=order, z0=x0[order, 2].reshape(100, 10).mean(axis=1))


def references(ad, times, z0, np):
    xml = ET.parse(ad.pin(BASE_XML)).getroot(); val = lambda name: float(next(xml.iter(name)).get("value"))
    E, nu, k, water, Kw, n0, q0, tD = [val(name) for name in ("ModulusE", "PRvs", "HydraulicConductivity", "PoreWaterRho",
        "PoreWaterBulkModulus", "Porosity", "HydroMechTopLoadQ0", "HydroMechDrainageStartTime")]
    need((E, nu, k, water, Kw, n0, q0, tD) == (2e6, .3, 1e-4, 1000., 2e8, .3, 10000., .010000228881835938), "Original physical companion constants changed")
    H, g = 1., 9.81; M = E*(1-nu)/((1+nu)*(1-2*nu)); Cv = k*M/(water*g); capacity = 1/(1+n0*M/Kw)
    lam = (np.arange(512)+.5)*np.pi; coef = 2*(-1.)**np.arange(512)/lam
    co, si = np.cos(lam[:, None]*z0[None, :]/H), np.sin(lam[:, None]*z0[None, :]/H)
    valid = times >= tD; refs = {}
    for name, cap in (("M0", 1.), ("finite_Kw", capacity)):
        p, settle, continuum = np.full((N, 100), np.nan), np.full((N, 100), np.nan), np.full(N, np.nan)
        decay = np.exp(-cap*Cv*lam[None, :]**2*(times[valid, None]-tD)/H**2)
        p[valid] = cap*q0*((decay*coef)@co)
        settle[valid] = 1000*q0/M*(z0[None, :]-H*cap*((decay*coef/lam)@si))
        continuum[valid] = cap*q0*np.sum(2*decay/lam[None, :]**2, axis=1)
        refs[name] = dict(P=p, settle=settle, continuum=continuum, capacity=cap)
    return refs, dict(E_Pa=E, nu=nu, M_Pa=M, k_m_s=k, rho_w_kg_m3=water, Kw_Pa=Kw, n0=n0, q0_Pa=q0,
                      H_m=H, tD_s=tD, ramp_time_s=val("HydroMechTopLoadRampTime"), g_reference_m_s2=g,
                      Cv_M0_m2_s=Cv, B_finite_Kw=capacity, Cv_finite_Kw_m2_s=capacity*Cv,
                      S_infinity_continuum_surface_mm=1000*q0*H/M, series_modes=512)


def describe(d, refs, constants, np):
    scheme, order = d["scheme"], d["order"]; refname = "finite_Kw" if scheme == "A" else "M0"; ref = refs[refname]
    sign = np.where(np.arange(10) % 2, -1., 1.); rows, layers, failures = [], [], []
    arrays = {name: [] for name in ("P", "settle", "effective", "total", "J", "n", "rho", "aUz", "aEffective", "aTotal")}
    for part, q in enumerate(d["p"]["q"]):
        P = q[order, 6].reshape(100, 10); settle = -1000*(q[order, 2]-d["x0"][order, 2]).reshape(100, 10)
        effective = q[order, 10:16].reshape(100, 10, 6); total = effective.copy(); total[:, :, [0, 3, 5]] -= P[:, :, None]
        J, n, rho = q[order, 8].reshape(100, 10), d["n"]["n"][part, order].reshape(100, 10), d["rho"][part, order].reshape(100, 10)
        aUz = ((-settle+settle.mean(axis=1, keepdims=True))*sign).mean(axis=1)
        aE = ((effective-effective.mean(axis=1, keepdims=True))*sign[None, :, None]).mean(axis=1)
        aT = ((total-total.mean(axis=1, keepdims=True))*sign[None, :, None]).mean(axis=1)
        vertical = total[:, :, 5].mean(axis=1); stress = float(np.max(abs(vertical+constants["q0_Pa"])))
        gap = float(abs(vertical[-1]-vertical[-2])); time = float(d["clock"]["t"][part]); post = time >= .1-1e-7
        if post and (stress > 100. or gap > 100.): failures.append(dict(scheme=scheme, part=part, time_s=time,
            completed_step=int(d["completed"][part]), max_layer_total_error_Pa=stress, worst_layer=int(np.argmax(abs(vertical+constants["q0_Pa"]))), top_pair_total_gap_Pa=gap, original_limit_Pa=100.))
        row = dict(scheme=scheme, part=part, time_s=time, completed_steps=int(d["completed"][part]),
            legacy_Tv_since_drain=constants["Cv_M0_m2_s"]*(time-constants["tD_s"]),
            applicable_reference_Tv=ref["capacity"]*constants["Cv_M0_m2_s"]*(time-constants["tD_s"]),
            pressure_mean_Pa=float(P.mean()), pressure_J_weighted_mean_Pa=float(np.sum(q[:, 6]*q[:, 8])/np.sum(q[:, 8])),
            pressure_native_point_RMS_Pa=float(np.sqrt(np.mean(P**2))), pressure_min_Pa=float(P.min()), pressure_max_Pa=float(P.max()),
            top10_pressure_Pa=float(P[-1].mean()), bottom10_pressure_Pa=float(P[0].mean()), top10_settlement_mm=float(settle[-1].mean()),
            bottom10_settlement_mm=float(settle[0].mean()), speed_XYZ_RMS_m_s=float(np.sqrt(np.mean(np.sum(q[:, 3:6]**2, axis=1)))),
            effective_compression_zz_mean_Pa=float(-effective[:, :, 5].mean()), total_compression_zz_mean_Pa=float(-total[:, :, 5].mean()),
            max_layer_total_error_Pa=stress, top_pair_total_gap_Pa=gap, Q_total_zz_second_difference_RMS_Pa=float(np.sqrt(np.mean(np.diff(vertical, n=2)**2))),
            original_post_01_guard_applies=post, original_stress_guard_passed=not post or stress <= 100., original_top_gap_guard_passed=not post or gap <= 100.,
            A_pi_Uz_RMS_over100layers_mm=float(np.sqrt(np.mean(aUz**2))), A_pi_Uz_abs_max_mm=float(np.max(abs(aUz))),
            A_pi_effective_sigma_RMS_over100layers_6components_Pa=float(np.sqrt(np.mean(aE**2))),
            A_pi_total_sigma_RMS_over100layers_6components_Pa=float(np.sqrt(np.mean(aT**2))),
            J_min=float(J.min()), J_mean=float(J.mean()), J_max=float(J.max()), n_min=float(n.min()), n_mean=float(n.mean()), n_max=float(n.max()),
            rho_native_min_kg_m3=float(rho.min()), rho_native_mean_kg_m3=float(rho.mean()), rho_native_max_kg_m3=float(rho.max()),
            **{"effective_sigma_"+c+"_mean_Pa": float(effective[:, :, j].mean()) for j, c in enumerate(COMPONENTS)},
            **{"total_sigma_"+c+"_mean_Pa": float(total[:, :, j].mean()) for j, c in enumerate(COMPONENTS)},
            appropriate_companion=refname, companion_same_node_mean_P_Pa=None, companion_continuum_mean_P_Pa=None,
            companion_material_top_settlement_mm=None, companion_material_bottom_settlement_mm=None,
            P_layer_mean_profile_RMS_error_Pa=None, P_native_point_RMS_error_Pa=None, P_native_point_abs_error_max_Pa=None,
            top_settlement_signed_error_mm=None, bottom_settlement_signed_error_mm=None)
        if np.isfinite(ref["P"][part]).all():
            row.update(companion_same_node_mean_P_Pa=float(ref["P"][part].mean()), companion_continuum_mean_P_Pa=float(ref["continuum"][part]),
                companion_material_top_settlement_mm=float(ref["settle"][part, -1]), companion_material_bottom_settlement_mm=float(ref["settle"][part, 0]),
                P_layer_mean_profile_RMS_error_Pa=float(np.sqrt(np.mean((P.mean(axis=1)-ref["P"][part])**2))),
                P_native_point_RMS_error_Pa=float(np.sqrt(np.mean((P-ref["P"][part, :, None])**2))),
                P_native_point_abs_error_max_Pa=float(np.max(abs(P-ref["P"][part, :, None]))),
                top_settlement_signed_error_mm=float(settle[-1].mean()-ref["settle"][part, -1]),
                bottom_settlement_signed_error_mm=float(settle[0].mean()-ref["settle"][part, 0]))
        old = d["history"][part]
        for key, oldkey in (("pressure_mean_Pa", "pressure_mean_Pa"), ("top10_settlement_mm", "top10_settlement_mean_mm"),
                            ("bottom10_settlement_mm", "bottom10_settlement_mean_mm"), ("rho_native_mean_kg_m3", "native_current_rho_mean_kg_m3")):
            need(math.isclose(row[key], float(old[oldkey]), rel_tol=2e-12, abs_tol=2e-9), "Native summary definition changed: " + scheme + "/" + key)
        rows.append(row)
        for key, value in (("P", P), ("settle", settle), ("effective", effective), ("total", total), ("J", J), ("n", n), ("rho", rho), ("aUz", aUz), ("aEffective", aE), ("aTotal", aT)): arrays[key].append(value)
        if scheme == "B":
            for level in range(100):
                layers.append(dict(scheme=scheme, part=part, time_s=time, completed_steps=int(d["completed"][part]), initial_layer=level, z0_m=float(d["z0"][level]),
                    pressure_mean_Pa=float(P[level].mean()), pressure_min_Pa=float(P[level].min()), pressure_max_Pa=float(P[level].max()),
                    pressure_std_across_X_Pa=float(P[level].std()), material_settlement_mean_mm=float(settle[level].mean()), A_pi_Uz_signed_mm=float(aUz[level]),
                    J_min=float(J[level].min()), J_mean=float(J[level].mean()), J_max=float(J[level].max()), n_native_mean=float(n[level].mean()),
                    rho_native_min_kg_m3=float(rho[level].min()), rho_native_mean_kg_m3=float(rho[level].mean()), rho_native_max_kg_m3=float(rho[level].max()),
                    **{"effective_sigma_"+c+"_mean_Pa": float(effective[level, :, j].mean()) for j, c in enumerate(COMPONENTS)},
                    **{"total_sigma_"+c+"_mean_Pa": float(total[level, :, j].mean()) for j, c in enumerate(COMPONENTS)},
                    **{"A_pi_effective_sigma_"+c+"_signed_Pa": float(aE[level, j]) for j, c in enumerate(COMPONENTS)},
                    **{"A_pi_total_sigma_"+c+"_signed_Pa": float(aT[level, j]) for j, c in enumerate(COMPONENTS)}))
    d.update(rows=rows, arrays={key: np.array(value) for key, value in arrays.items()})
    return rows, layers, failures


def upw_context(ad):
    check = ad.read(UPW_CHECK)
    need(check.get("stage") == "upl_full_upw_compare_r1" and check.get("passed") is True and
         check.get("full_physical_acceptance_claimed") is False, "Retained lightweight u-pw comparison receipt required")
    history = [r for r in ad.table(UPW_HISTORY) if r["series"] == "retained_upw_GPU_Vel0_1"]
    profiles = ad.table(UPW_PROFILES)
    need(len(history) == 7290 and len(profiles) == 1000, "Retained u-pw lightweight row coverage differs")
    return dict(history=history, profiles=profiles, qualifiers=check["qualifiers"], clock_qualifier=check["clock_qualifier"])


def retained_A_mode_csv(ad, d, np):
    """Use the already published A-layer CSV for its plotted heatmap, without duplicating it."""
    uz, total = np.empty((N, 100)), np.empty((N, 100, 6)); count = 0
    with ad.pin(A_LAYERS).open(encoding="utf8", newline="") as f:
        for r in csv.DictReader(f):
            part, level = divmod(count, 100)
            need(part < N and int(r["part"]) == part and int(r["initial_layer"]) == level and
                 float(r["time_s"]) == d["clock"]["t"][part] and float(r["z0_m"]) == d["z0"][level],
                 "Retained A all-layer plot CSV ownership/time differs")
            uz[part, level] = float(r["A_pi_Uz_signed_mm"])
            total[part, level] = [float(r["A_pi_total_sigma_"+c+"_Pa"]) for c in COMPONENTS]
            count += 1
    need(count == N*100 and np.isfinite(uz).all() and np.isfinite(total).all(), "Retained A complete mode CSV coverage differs")
    # Same published definition, not a new physical accuracy or bit-equality gate.
    need(np.array_equal(uz, d["arrays"]["aUz"]) and np.array_equal(total, d["arrays"]["aTotal"]),
         "Retained A mode definition differs from its own original native export")
    d["display_modes"] = dict(aUz=uz, aTotal=total)


def selections(data, refs, constants, upw, np):
    times = data["B"]["clock"]["t"]; selection, timing_rows, profiles, budgets = [], [], [], []
    for tv in REQUESTED:
        target = constants["tD_s"] + tv/constants["Cv_M0_m2_s"]
        need(times[0] <= target <= times[-1], "Declared legacyTv target outside actual coverage")
        part = int(np.argmin(abs(times-target))); selection.append((tv, part))
        old = sorted([r for r in upw["profiles"] if float(r["target_Tv"]) == tv], key=lambda r: int(r["initial_layer"]))
        need(len(old) == 100 and [int(r["initial_layer"]) for r in old] == list(range(100)), "Retained u-pw profile layers differ")
        for scheme in ("A", "B"):
            d = data[scheme]; refname = "finite_Kw" if scheme == "A" else "M0"; ref = refs[refname]; a = d["arrays"]
            own_target = constants["tD_s"] + tv/(ref["capacity"]*constants["Cv_M0_m2_s"])
            meta = dict(scheme=scheme, requested_legacy_Tv=tv, target_time_s=target, actual_part=part, actual_time_s=float(times[part]),
                completed_steps=int(d["completed"][part]), signed_target_time_gap_s=float(times[part]-target),
                actual_legacy_Tv=constants["Cv_M0_m2_s"]*(float(times[part])-constants["tD_s"]),
                applicable_reference_Tv=ref["capacity"]*constants["Cv_M0_m2_s"]*(float(times[part])-constants["tD_s"]),
                applicable_same_number_Tv_target_time_s=own_target, applicable_same_number_Tv_target_within_saved_coverage=bool(own_target <= times[-1]),
                signed_legacy_Tv_gap=constants["Cv_M0_m2_s"]*(float(times[part])-constants["tD_s"])-tv,
                appropriate_companion=refname, interpolation_used=False)
            timing_rows.append(meta)
            for level in range(100):
                profiles.append(dict(**meta, initial_layer=level, z0_m=float(d["z0"][level]), pressure_mean_Pa=float(a["P"][part, level].mean()),
                    pressure_min_Pa=float(a["P"][part, level].min()), pressure_max_Pa=float(a["P"][part, level].max()),
                    material_settlement_mean_mm=float(a["settle"][part, level].mean()),
                    effective_compression_zz_mean_Pa=float(-a["effective"][part, level, :, 5].mean()), total_compression_zz_mean_Pa=float(-a["total"][part, level, :, 5].mean()),
                    J_mean=float(a["J"][part, level].mean()), n_native_mean=float(a["n"][part, level].mean()), rho_native_mean_kg_m3=float(a["rho"][part, level].mean()),
                    companion_pressure_Pa=float(ref["P"][part, level]), companion_material_settlement_mm=float(ref["settle"][part, level]),
                    retained_upw_pressure_Pa=float(old[level]["old_pressure_Pa"]), retained_upw_z0_m=float(old[level]["old_z0_m"]),
                    retained_upw_actual_time_s=float(old[level]["old_actual_time_s"]), retained_upw_actual_Tv=float(old[level]["old_actual_Tv"]),
                    signed_current_minus_upw_time_gap_s=float(times[part])-float(old[level]["old_actual_time_s"])))
        a, z = data["A"]["rows"][part], data["B"]["rows"][part]
        EpA, EpB = a["P_layer_mean_profile_RMS_error_Pa"], z["P_layer_mean_profile_RMS_error_Pa"]
        EsA, EsB = abs(a["top_settlement_signed_error_mm"]), abs(z["top_settlement_signed_error_mm"])
        EbA, EbB = abs(a["bottom_settlement_signed_error_mm"]), abs(z["bottom_settlement_signed_error_mm"])
        ppass = EpB <= EpA + .001*constants["q0_Pa"]
        latepass = tv < 1. or EpB <= EpA + 5.
        spass = EsB <= EsA + .001*constants["S_infinity_continuum_surface_mm"]
        bpass = EbB <= .005 and EbB <= EbA + .002
        budgets.append(dict(requested_legacy_Tv=tv, actual_part=part, actual_time_s=float(times[part]),
            A_appropriate_reference="finite_Kw", B_appropriate_reference="M0", A_P_layer_RMS_error_Pa=EpA, B_P_layer_RMS_error_Pa=EpB,
            pressure_error_increment_percentage_points=100*(EpB-EpA)/constants["q0_Pa"], pressure_increment_limit_percentage_points=.10,
            pressure_noninferiority_passed=ppass, late_absolute_P_increment_gate_applies=tv >= 1., late_P_increment_Pa=EpB-EpA,
            late_P_increment_limit_Pa=5., late_P_increment_passed=latepass, A_top_abs_error_mm=EsA, B_top_abs_error_mm=EsB,
            top_error_increment_percentage_points=100*(EsB-EsA)/constants["S_infinity_continuum_surface_mm"], top_increment_limit_percentage_points=.10,
            top_noninferiority_passed=spass, A_bottom_abs_error_mm=EbA, B_bottom_abs_error_mm=EbB, bottom_abs_limit_mm=.005,
            bottom_error_increment_mm=EbB-EbA, bottom_increment_limit_mm=.002, bottom_absolute_and_noninferiority_passed=bpass,
            all_declared_budgets_passed=ppass and latepass and spass and bpass, not_a_half_or_cross_model_equivalence_gate=True))
    return selection, timing_rows, profiles, budgets


def figures(data, selection, upw, np):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fields = (("pressure_mean_Pa", "Mean native pressure (Pa)"), ("top10_settlement_mm", "Initial top10 material settlement (mm)"),
        ("bottom10_settlement_mm", "Initial bottom10 material settlement (mm)"), ("effective_compression_zz_mean_Pa", "Mean effective vertical compression (Pa)"),
        ("total_compression_zz_mean_Pa", "Mean total vertical compression (Pa)"), ("max_layer_total_error_Pa", "Original layer total-stress error / top gap (Pa)"),
        ("Q_total_zz_second_difference_RMS_Pa", "Total-stress second difference Q (Pa)"), ("J_mean", "J mean and native min/max"),
        ("n_mean", "Porosity mean and native min/max"), ("rho_native_mean_kg_m3", "Native mixture density (kg/m3)"),
        ("speed_XYZ_RMS_m_s", "Native XYZ velocity RMS (m/s)"), ("A_pi_Uz_RMS_over100layers_mm", "Alternating-X Uz: layer RMS (mm)"))
    fig, axes = plt.subplots(6, 2, figsize=(15, 21), constrained_layout=True)
    oldnames = dict(pressure_mean_Pa="mean_pressure_pa", top10_settlement_mm="top_settlement_mm", bottom10_settlement_mm="bottom_settlement_mm",
                    max_layer_total_error_Pa="max_layer_total_error_pa", Q_total_zz_second_difference_RMS_Pa="Q_pa")
    for ax, (field, title) in zip(axes.flat, fields):
        for scheme in ("A", "B"):
            rr = data[scheme]["rows"]; times = [r["time_s"] for r in rr]
            ax.plot(times, [r[field] for r in rr], color=COLORS[scheme], lw=1., label=LABELS[scheme])
            bounds = {"J_mean": ("J_min", "J_max"), "n_mean": ("n_min", "n_max"), "rho_native_mean_kg_m3": ("rho_native_min_kg_m3", "rho_native_max_kg_m3")}.get(field)
            if bounds: ax.fill_between(times, [r[bounds[0]] for r in rr], [r[bounds[1]] for r in rr], color=COLORS[scheme], alpha=.09)
            if field == "max_layer_total_error_Pa": ax.plot(times, [r["top_pair_total_gap_Pa"] for r in rr], color=COLORS[scheme], ls=":", lw=.8, label=scheme+" top-pair gap")
            refkey = {"pressure_mean_Pa": "companion_same_node_mean_P_Pa", "top10_settlement_mm": "companion_material_top_settlement_mm", "bottom10_settlement_mm": "companion_material_bottom_settlement_mm"}.get(field)
            if refkey: ax.plot(times, [r[refkey] for r in rr], color="black", ls="--" if scheme == "A" else "-.", lw=.9, label=("finite-Kw" if scheme == "A" else "M0")+" qualified companion")
        if field in oldnames:
            ax.plot([float(r["time_s"]) for r in upw["history"]], [float(r[oldnames[field]]) for r in upw["history"]], color="tab:green", lw=.8, alpha=.8, label="Retained u-pw GPU Vel0 (context)")
        if field == "max_layer_total_error_Pa": ax.plot([.1, END], [100., 100.], "k--", lw=.8, label="Original post-.1s100 Pa limit")
        ax.set(xlabel="Each source's actual saved time (s)", ylabel=title); ax.grid(True, alpha=.3); ax.legend(fontsize=6)
    fig.suptitle("Full2Tv native history: finite-Kw A versus M0 TPI B; startup retained, no time/space fitting")
    save_png(fig, PRODUCTS["history.png"]); plt.close(fig)
    for quantity, output, xlabel in (("P", "profiles.png", "Pressure (Pa)"), ("settle", "settlement_profiles.png", "Material settlement (mm)")):
        fig, axes = plt.subplots(2, 5, figsize=(20, 11), constrained_layout=True)
        for ax, (tv, part) in zip(axes.flat, selection):
            for scheme in ("A", "B"):
                d = data[scheme]; rr = d["rows"][part]
                ax.plot(d["arrays"][quantity][part].mean(axis=1), d["z0"], color=COLORS[scheme], lw=1., marker="o" if scheme == "A" else "x", markevery=8, markersize=3, fillstyle="none", label=LABELS[scheme])
                refkey = "companion_P" if quantity == "P" else "companion_settle"
                ax.plot(d[refkey][part], d["z0"], color="black", ls="--" if scheme == "A" else "-.", lw=.9, label=("finite-Kw" if scheme == "A" else "M0")+" companion at actual time")
            if quantity == "P":
                old = sorted([r for r in upw["profiles"] if float(r["target_Tv"]) == tv], key=lambda r: int(r["initial_layer"]))
                ax.plot([float(r["old_pressure_Pa"]) for r in old], [float(r["old_z0_m"]) for r in old], color="tab:green", lw=.8, marker="+", markevery=10, markersize=3, label="u-pw at its own saved time (context)")
            ax.set(title="Target legacy Tv=%g\nactual t=%.9g s, TvB=%.7g" % (tv, data["B"]["rows"][part]["time_s"], data["B"]["rows"][part]["applicable_reference_Tv"]), xlabel=xlabel, ylabel="Initial material z0 (m)")
            ax.grid(True, alpha=.3)
        axes.flat[-1].legend(fontsize=6)
        fig.suptitle("All ten declared Tv: actual nearest saved states; unfitted H1 references; different A/B physical limits")
        save_png(fig, PRODUCTS[output]); plt.close(fig)
    fig, axes = plt.subplots(3, 2, figsize=(16, 13), constrained_layout=True)
    for col, scheme in enumerate(("A", "B")):
        d = data[scheme]; times = d["clock"]["t"]
        for row, (key, component, title) in enumerate((("aUz", None, "Signed alternating X-column Uz (mm)"), ("aTotal", 5, "Signed alternating total sigma zz (Pa)"))):
            source = d.get("display_modes", d["arrays"])
            values = source[key] if component is None else source[key][:, :, component]
            # Use the same magnitude scale for both schemes, without changing any values.
            span = max(float(np.max(abs((data[k].get("display_modes", data[k]["arrays"])[key] if component is None else
                data[k].get("display_modes", data[k]["arrays"])[key][:, :, component])))) for k in ("A", "B")) or 1.
            mesh = axes[row, col].pcolormesh(times, d["z0"], values.T, shading="nearest", cmap="coolwarm", vmin=-span, vmax=span)
            fig.colorbar(mesh, ax=axes[row, col], label=title)
            axes[row, col].set(title=LABELS[scheme]+"; common A/B symmetric range", xlabel="Actual time (s)", ylabel="Initial material z0 (m)")
        axes[2, col].plot(times, [r["A_pi_Uz_RMS_over100layers_mm"] for r in d["rows"]], label="All100 signed layer modes RMS")
        axes[2, col].plot(times, [r["A_pi_Uz_abs_max_mm"] for r in d["rows"]], label="Max absolute layer mode")
        axes[2, col].set(xlabel="Actual time (s)", ylabel="Alternating Uz amplitude (mm)"); axes[2, col].grid(True); axes[2, col].legend(fontsize=7)
    fig.suptitle("Every saved state and100 fixed original layers; no smoothing, clipping or half/reference chain")
    save_png(fig, PRODUCTS["modes.png"]); plt.close(fig)


def science(ad, result):
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"): os.environ[name] = "1"
    import numpy as np
    data = {scheme: load(ad, scheme, np, result) for scheme in ("A", "B")}
    a, z = data["A"], data["B"]
    need(a["x0"].tobytes() == z["x0"].tobytes() and a["clock"]["t"].tobytes() == z["clock"]["t"].tobytes() and
         a["completed"].tobytes() == z["completed"].tobytes(), "Full A/B actual clock/IDs/material geometry differ")
    refs, constants = references(ad, z["clock"]["t"], z["z0"], np)
    history, layers, failures = [], [], []
    for scheme in ("A", "B"):
        h, m, failed = describe(data[scheme], refs, constants, np); history += h; layers += m; failures += failed
        ref = refs["finite_Kw" if scheme == "A" else "M0"]
        data[scheme].update(companion_P=ref["P"], companion_settle=ref["settle"])
    retained_A_mode_csv(ad, a, np)
    upw = upw_context(ad)
    selection, timing_rows, profiles, budgets = selections(data, refs, constants, upw, np)
    cross = []
    for part in range(N):
        x, y = z["p"]["q"][part], a["p"]["q"][part]; displacement = x[:, :3]-y[:, :3]
        displacement[:, 0] -= .1*np.floor(displacement[:, 0]/.1+.5)
        b_row, a_row = z["rows"][part], a["rows"][part]
        cross.append(dict(pair="B_M0_GPU_minus_A_finiteKw_CPU1", part=part, actual_time_s=float(z["clock"]["t"][part]),
            completed_steps=int(z["completed"][part]), pressure_same_material_ID_RMS_difference_Pa=float(np.sqrt(np.mean((x[:, 6]-y[:, 6])**2))),
            material_XYZ_max_difference_mm=float(1000*np.max(np.linalg.norm(displacement, axis=1))),
            top10_settlement_difference_mm=b_row["top10_settlement_mm"]-a_row["top10_settlement_mm"], bottom10_settlement_difference_mm=b_row["bottom10_settlement_mm"]-a_row["bottom10_settlement_mm"],
            total_compression_mean_difference_Pa=b_row["total_compression_zz_mean_Pa"]-a_row["total_compression_zz_mean_Pa"], Q_difference_Pa=b_row["Q_total_zz_second_difference_RMS_Pa"]-a_row["Q_total_zz_second_difference_RMS_Pa"],
            descriptive_only_no_5Pa_or_half_gate=True))
    # Match every plotted old-u-pw history point in the condensed output without reprocessing its native data.
    for r in upw["history"]:
        out = {key: None for key in history[0]}
        out.update(scheme="retained_upw_GPU_Vel0_context", part=int(r["part"]), time_s=float(r["time_s"]), legacy_Tv_since_drain=float(r["actual_Tv"]),
            pressure_mean_Pa=float(r["mean_pressure_pa"]), top10_settlement_mm=float(r["top_settlement_mm"]), bottom10_settlement_mm=float(r["bottom_settlement_mm"]),
            Q_total_zz_second_difference_RMS_Pa=float(r["Q_pa"]), max_layer_total_error_Pa=float(r["max_layer_total_error_pa"]), top_pair_total_gap_Pa=float(r["top_gap_pa"]))
        history.append(out)
    metrics = dict(stage=TAG, analysis_complete=True, physical_acceptance=False, constants=constants, schemes={},
        declared_Tv_targets=list(REQUESTED), declared_Tv_definition="Legacy H1 M0-Cv scheduling, preserved from accepted full plan; each trajectory/reference also reports its applicable Cv*actual_tau/H^2",
        appropriate_reference={"A": "finite_Kw", "B": "M0"}, reference_limits="Unfitted H1 quasistatic closed-loading/top-drainage companions, not an exact finite-ramp/kernel-band/inertial/current-J startup solution; no height, load or time fit",
        total_stress_definition="Saved six-component sigma is effective skeleton stress; total=saved_sigma-p*I; shears unchanged",
        Q_definition="RMS of98 second differences of100 initial-material-layer mean total sigma_zz; not the alternating-X mode",
        mode_definition="Signed (-1)^initial_X_column projection after subtracting each original-layer mean; all100 layers at all1682 saved times",
        matching_A_heatmap_CSV=stat(A_LAYERS), matching_B_heatmap_CSV=str(PRODUCTS["layers.csv"]),
        post_01_original_stress=dict(start_s=.1-1e-7, max_layer_total_error_limit_Pa=100., top_pair_gap_limit_Pa=100., failures=failures),
        noninferiority=dict(plan=stat(PLAN_NOTE), all_ten_declared_targets_passed=all(r["all_declared_budgets_passed"] for r in budgets), rows=budgets),
        old_upw=dict(passed_lightweight_receipt=stat(UPW_CHECK), qualifiers=upw["qualifiers"], clock_qualifier=upw["clock_qualifier"], raw_native_reprocessed=False),
        pressure_clipping_smoothing_fitting=False, interpolation_or_clock_header_rewrite=False, default_A_native_rerun=False,
        inherited_same_B_short_prefix_not_repeated=True, all22_prefix_bitproof_claimed=False, cross_model_5Pa_or_half_equivalence_gate=False,
        full_exact_restart_claimed=False, new_full_A_C_half_reference_solver_admitted=False, SHA_scans=0)
    for scheme in ("A", "B"):
        rr = data[scheme]["rows"]; post = [r for r in rr if r["original_post_01_guard_applies"]]; late = [r for r in rr if r["legacy_Tv_since_drain"] >= 1.]
        increments = [late[i+1]["pressure_mean_Pa"]-late[i]["pressure_mean_Pa"] for i in range(len(late)-1)]
        metrics["schemes"][scheme] = dict(final=rr[-1], observed_runtime=result["scheme_status"][scheme]["observed_runtime"],
            all_saved_native_pressure_min_Pa=min(r["pressure_min_Pa"] for r in rr), all_saved_native_pressure_max_Pa=max(r["pressure_max_Pa"] for r in rr),
            post_01_saved_frames=len(post), post_01_stress_failure_count=sum(r["scheme"] == scheme for r in failures),
            post_01_max_layer_total_error_Pa=max(r["max_layer_total_error_Pa"] for r in post), post_01_max_top_pair_gap_Pa=max(r["top_pair_total_gap_Pa"] for r in post),
            first_original_stress_failure=next((r for r in failures if r["scheme"] == scheme), None),
            all_saved_alternating_Uz_abs_max_mm=max(r["A_pi_Uz_abs_max_mm"] for r in rr), late_legacy_Tv_ge1_saved_states=len(late),
            late_mean_pressure_increase_count=sum(x > 0 for x in increments), late_max_signed_pressure_increment_Pa=max(increments) if increments else None,
            late_first_mean_pressure_Pa=late[0]["pressure_mean_Pa"] if late else None, late_final_mean_pressure_Pa=late[-1]["pressure_mean_Pa"] if late else None,
            late_max_layer_profile_RMS_error_Pa=max(r["P_layer_mean_profile_RMS_error_Pa"] for r in late) if late else None,
            late_max_abs_bottom_material_error_mm=max(abs(r["bottom_settlement_signed_error_mm"]) for r in late) if late else None,
            plateau_or_no_growth_claim_not_inferred_from_exit=True)
    failures_B = [r for r in failures if r["scheme"] == "B"]
    passed = not failures_B and all(r["all_declared_budgets_passed"] for r in budgets)
    metrics.update(B_original_100Pa_guards_and_planned_noninferiority_passed=passed,
                   preserved_A_100Pa_failure_does_not_exempt_B=True, final_physical_or_public_source_admission_requires_root_review=True)
    ad.finish()
    for name, rows in (("history.csv", history), ("layers.csv", layers), ("profiles.csv", profiles), ("profile_times.csv", timing_rows), ("cross.csv", cross), ("noninferiority.csv", budgets)):
        write_csv(PRODUCTS[name], rows)
    write_json(PRODUCTS["metrics.json"], metrics); figures(data, selection, upw, np); ad.finish()
    result.update(passed=passed, analysis_complete=True, metrics=stat(PRODUCTS["metrics.json"]),
        rows=dict(history=len(history), B_all100_layer_history=len(layers), profiles=len(profiles), profile_times=len(timing_rows), cross=len(cross), noninferiority=len(budgets)),
        original_B_stress_failure_count=len(failures_B), noninferiority_failure_count=sum(not r["all_declared_budgets_passed"] for r in budgets),
        existing_A_stress_failure_count=sum(r["scheme"] == "A" for r in failures), files=[stat(p) for p in PRODUCTS.values()],
        source_admission_or_formal_acceptance=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-authorized", action="store_true"); parser.add_argument("--admission", type=Path, required=True)
    args = parser.parse_args(); need(args.execution_authorized, "Root full-read and one offline-only execution required")
    need(not CHECK.exists() and not any(p.exists() for p in PRODUCTS.values()), "Existing/partial science output protected; never overwrite")
    ad = Admission(args.admission)
    result = dict(stage=TAG, passed=False, analysis_complete=False, root_admission=ad.entry, scheme_status={},
        solver_invocations=0, native_invocations=0, build_invocations=0, old_analysis_invocations=0, SHA_scans=0,
        physical_acceptance=False, automatic_follow_up=False)
    try: science(ad, result)
    except Exception as exc:
        result.update(first_failure=str(exc), partial_outputs_preserved=True); raise
    finally:
        result["consumed"] = list(ad.used.values()); write_json(CHECK, result)
    print(str(CHECK)); return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
