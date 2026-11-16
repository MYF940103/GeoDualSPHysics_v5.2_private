"""One offline actual-GPU A/B/C startup review; no solver/reader/build/hash."""
from __future__ import annotations
import argparse
import csv
import json
import math
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
TAG = "upl_tpi_gpu_startup_review_r1"
NOTE = T / "notes" / (TAG + ".md")
BASE_XML = T / "configs/upl_bigstep_c625_r1.xml"
DEFINITIONS = (T / "support/upl_bigstep_full_review_r1.py", T / "support/gpu_coupled_compare.py")
CHECK = T / "logs" / (TAG + ".check.json")
F = T / "figures"
PRODUCTS = {n: F / (TAG + "." + n) for n in
            ("history.csv", "profiles.csv", "modes.csv", "cross.csv", "metrics.json",
             "history.png", "profiles.png", "modes.png")}
N, SOIL, FIXED, STEPS, POST = 344, 1000, 40, 24000, 226
DT, END, EVENT = 6.250143051147461e-6, .1500034332275618, 1600
FIELDS = "x y z vx vy vz PorePress PorePress0 J theta sigma_xx sigma_xy sigma_xz sigma_yy sigma_yz sigma_zz Kplastic FSType FSNormal_x FSNormal_y FSNormal_z ExcessPorePress LoadAce_x LoadAce_y LoadAce_z legacy_Rhop".split()
COMPONENTS = ("xx", "xy", "xz", "yy", "yz", "zz")
SCHEMES = ("A", "B", "C")
LABELS = {"A": "A finite Kw", "B": "B TPI alpha=.5, M0", "C": "C PPE-t alpha=0, M0"}
COLORS = {"A": "tab:blue", "B": "tab:orange", "C": "tab:green"}
PROFILES = (0., .01, .025, .075, .15)


def need(ok, message):
    if not bool(ok):
        raise ValueError(message)


def stat(path):
    p = Path(path).resolve()
    s = p.stat()
    return dict(path=str(p), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def write_json(path, value):
    with path.open("x", encoding="utf8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def write_csv(path, rows):
    need(bool(rows), "An empty scientific table must not be published")
    with path.open("x", encoding="utf8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def save_png(fig, path):
    with path.open("xb") as stream:
        fig.savefig(stream, format="png", dpi=165)


class Admission:
    def __init__(self, path):
        self.entry = stat(path)
        self.data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        need(self.data.get("stage") == TAG + ".admission" and self.data.get("passed") is True
             and self.data.get("offline_only") is True, "Root full-read offline-only admission required")
        self.frozen = {str(Path(e["path"]).resolve()): e for e in self.data["inputs"]}
        need(len(self.frozen) == len(self.data["inputs"]), "Duplicated root-frozen input path")
        self.used = {}
        for p in (Path(__file__), NOTE, BASE_XML, *DEFINITIONS):
            self.pin(p)

    def pin(self, path):
        p = str(Path(path).resolve())
        need(p in self.frozen, "Consumed file absent from root admission: " + p)
        entry = self.frozen[p]
        expected = {k: entry[k] for k in ("path", "bytes", "mtime_ns")}
        need(stat(p) == expected, "Root-frozen input stat changed: " + p)
        self.used[p] = expected
        return Path(p)

    def read(self, path):
        return json.loads(self.pin(path).read_text(encoding="utf-8-sig"))

    def table(self, path):
        with self.pin(path).open(encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def finish(self):
        for entry in self.used.values():
            need(stat(entry["path"]) == entry, "Consumed input changed during offline analysis")
        need(stat(self.entry["path"]) == self.entry, "Root admission changed")


def bin_array(ad, path, header, dtype, np):
    path = ad.pin(path)
    size = 4 * len(header)
    with path.open("rb") as f:
        need(struct.unpack("<" + "I" * len(header), f.read(size)) == header,
             "Original native export header differs: " + path.name)
    need(path.stat().st_size == size + N * dtype.itemsize, "Native binary size/stride differs: " + path.name)
    return np.memmap(path, dtype=dtype, mode="r", offset=size, shape=(N,))


def load(ad, scheme, np, result):
    tag = "upl_tpi_gpu_Release_" + scheme + "_startup015_r1"
    review_path = T / "logs" / (tag + ".native_review_r4.json")
    result["scheme_status"][scheme] = dict(tag=tag, native_review_exists=review_path.exists(), qualified=False)
    need(review_path.exists(), scheme + " has no completed native_review; no startup science is admitted")
    review = ad.read(review_path)
    status = result["scheme_status"][scheme]
    status.update(native_review_passed=review.get("passed"), observed_failure=review.get("failure"))
    need(review.get("passed") is True and review.get("stage") == "upl_tpi_gpu_native_r4.review"
         and review.get("original_native_guards_not_relaxed") is True,
         scheme + " native review failed; preserve its actual failure and do not omit it")
    job = review["job"]
    need((job["tag"], job["scheme"], job["window"], job["configuration"]) ==
         (tag, scheme, "startup015", "Release"), "Exact scheme/window/configuration association differs")
    directory = T / "outputs" / (tag + "_native_r4")
    need(Path(job["native_output"]).resolve() == directory.resolve(), "Native output ownership differs")
    runtime_directory = T / "outputs" / tag
    need(Path(job["output_directory"]).resolve() == runtime_directory.resolve(), "Original Run.csv output ownership differs")
    with ad.pin(runtime_directory/"Run.csv").open(encoding="utf-8-sig", newline="") as f:
        runtime_rows = list(csv.DictReader(f, delimiter=";"))
    need(len(runtime_rows) == 1, "Run.csv must contain exactly one original completed GPU row")
    run = runtime_rows[0]
    need(int(run["Steps"]) == STEPS and int(run["PartFiles"]) == N and int(run["Np"]) == 1040
         and int(run["Nbound"]) == int(run["Nfixed"]) == FIXED and int(run["PartsOut"]) == 0
         and "gpu" in run["Hardware"].lower() and "Stable - Pos-Cell - Single-GPU" in run["RunMode"],
         "Original Run.csv 24000-step/344-frame/actualGPU native identity differs")
    tsimul, ttotal, tseg = [float(run[key]) for key in ("TSimul", "TTotal", "TSeg")]
    need(all(math.isfinite(t) and t > 0 for t in (tsimul, ttotal, tseg)), "Original runtime summary is nonfinite or nonpositive")
    timing = dict(TSimul_s=tsimul, TTotal_s=ttotal, TSeg_original_display=tseg,
                  original_TSimul_token=run["TSimul"], original_TTotal_token=run["TTotal"],
                  actual_steps=STEPS, native_frames=N, observed_steps_per_TSimul_s=STEPS/tsimul,
                  hardware=run["Hardware"], original_RunMode=run["RunMode"],
                  rounded_PhysicalTime_display_not_used_as_clock=run["PhysicalTime"],
                  controlled_benchmark=False, observed_nonisolated_instrumented_runtime=True)
    done = ad.read(directory / "completion.json")
    required = dict(passed=True, stage="upl_tpi_gpu_native_r1", backend="GPU_P1_private", window="startup015",
                    samples=N, total_native_count=1040, native_count=SOIL, fixed_count=FIXED,
                    native_total_arrays=22, physical_columns=26,
                    physical_schema="case02_common26_col21_ExcessPorePress_NOT_wave26",
                    actual_end_s=END, planned_completed_steps=STEPS, noninitial_signed_dterror_intervals=N-1,
                    soil_ledger_checks=N*SOIL, fixed_public_zero_marker_checks=N*FIXED,
                    all_native_J_theta_rows=N*1040, post_open_frames=POST,
                    post_open_drained_particle_checks=POST*10, post_open_completed_step_threshold=EVENT,
                    all_exported_physical_fields_finite=True, no_exclusions=True)
    for key, value in required.items():
        need(done.get(key) == value, "Original native completion differs: " + scheme + "/" + key)
    columns = ad.table(directory / "columns.csv")
    need(columns == [dict(column=str(i), name=n) for i, n in enumerate(FIELDS)], "Exact case02 common26 layout differs")
    ids = ad.table(directory / "native_ids.csv")
    need(len(ids) == SOIL and [int(r["row"]) for r in ids] == list(range(SOIL))
         and [int(r["id"]) for r in ids] == list(range(40, 1040)), "All original soil IDs/order differ")
    x0 = np.array([[float(r[a]) for a in ("x0", "y0", "z0")] for r in ids])
    layer = np.rint(x0[:, 2]/.01-.5).astype(int)
    column = np.rint(x0[:, 0]/.01-.5).astype(int)
    need(np.all((layer >= 0) & (layer < 100)) and np.all((column >= 0) & (column < 10))
         and np.array_equal(np.sort(10*layer+column), np.arange(SOIL))
         and np.all(x0[:, 1] == 0), "Original 100-by-10 material lattice differs")
    need(np.max(abs(x0[:, 0]-(column+.5)*.01)) <= 64*np.finfo(float).eps
         and np.max(abs(x0[:, 2]-(layer+.5)*.01)) <= 64*np.finfo(float).eps,
         "Native original coordinates differ from the retained decimal lattice")
    order = np.argsort(10*layer+column)
    physical = bin_array(ad, directory/"physical.bin", (SOIL, 26, N),
                         np.dtype([("t", "<f8"), ("q", "<f8", (SOIL, 26))]), np)
    n = bin_array(ad, directory/"soil_n.bin", (SOIL, 1, N),
                  np.dtype([("t", "<f8"), ("n", "<f8", (SOIL,))]), np)
    clock = bin_array(ad, directory/"clock.bin", (N, 28),
                      np.dtype([("t", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("signed", "<f8")]), np)
    history = ad.table(directory/"history.csv")
    plan = ad.table(job["plan"]["path"])
    need(len(history) == len(plan) == N and int(plan[-1]["completed_steps"]) == STEPS, "344 actual planned/native rows required")
    scalar = [0.]
    for _ in range(STEPS):
        scalar.append(scalar[-1] + DT)
    need(scalar[-1] == END, "Declared original scalar clock endpoint differs")
    completed = np.array([int(p["completed_steps"]) for p in plan], dtype=np.int64)
    actual = np.array([scalar[int(k)] for k in completed], dtype="<f8")
    for i, (p, h) in enumerate(zip(plan, history)):
        need(int(p["part"]) == int(h["part"]) == i and float(p["time_s"]) == actual[i]
             and float(h["time_s"]) == actual[i] and int(h["completed_step"]) == completed[i]
             and int(h["saved_step"]) == (completed[i]-1 if completed[i] else 0), "Actual saved history/plan identity differs")
    need(physical["t"].tobytes() == n["t"].tobytes() == clock["t"].tobytes() == actual.tobytes(), "Native time payloads differ")
    need(np.all(clock["dt"] == DT) and np.array_equal(clock["step"], np.maximum(completed-1, 0)), "Native locked dt/zero-based Step differs")
    need(np.all(np.isfinite(clock["signed"])) and np.all(clock["signed"][1:] <= 1e-14)
         and np.all(clock["signed"][1:] != -np.finfo(float).max), "Original signed nonempty necessary-step interval guard failed")
    need(completed[117] == EVENT and completed[118] == EVENT+1 and int(np.sum(completed > EVENT)) == POST,
         "Original event is pre-open and later receiver coverage differs")
    need(np.isfinite(physical["q"]).all() and np.isfinite(n["n"]).all(), "Original finite exports changed")
    rho = np.empty((N, SOIL))
    count = 0
    with ad.pin(directory/"ledger.csv").open(encoding="utf8", newline="") as f:
        for row in csv.DictReader(f):
            part, slot = divmod(count, SOIL)
            need(part < N and int(row["part"]) == part and int(row["id"]) == slot+40
                 and float(row["time_s"]) == actual[part]
                 and float(row["J"]) == physical["q"][part, slot, 8]
                 and float(row["n_native"]) == n["n"][part, slot], "Original native ledger ownership/time/J/n differs")
            rho[part, slot] = float(row["rho_native_kg_m3"])
            count += 1
    need(count == N*SOIL and np.isfinite(rho).all() and np.all(rho > 0), "Native density ledger coverage differs")
    status.update(qualified=True, samples=N, native_IDs=1040, original_arrays=22,
                  original_native_review=stat(review_path), HG_guards=review["HG_original_guards"],
                  pressure_lifecycle_sidecar=review["sidecar"], same_scheme_CPU_GPU_review=review["same_scheme_CPU_GPU"] if scheme != "A" else None,
                  signed_dterror_not_absolute_valued=True,
                  observed_runtime=timing)
    return dict(scheme=scheme, p=physical, n=n, clock=clock, x0=x0, order=order, completed=completed,
                history=history, rho=rho, z0=x0[order, 2].reshape(100, 10).mean(axis=1), timing=timing)


def references(ad, times, z0, np):
    xml = ET.parse(ad.pin(BASE_XML)).getroot()
    val = lambda name: float(next(xml.iter(name)).get("value"))
    E, nu, k, water, Kw, n0, q0, tD = [val(n) for n in ("ModulusE", "PRvs", "HydraulicConductivity",
        "PoreWaterRho", "PoreWaterBulkModulus", "Porosity", "HydroMechTopLoadQ0", "HydroMechDrainageStartTime")]
    need((E, nu, k, water, Kw, n0, q0, tD) == (2e6, .3, 1e-4, 1000., 2e8, .3, 10000., .010000228881835938),
         "Existing XML physical reference values changed")
    H, g = 1., 9.81
    M = E*(1-nu)/((1+nu)*(1-2*nu))
    Cv, B = k*M/(water*g), 1/(1+n0*M/Kw)
    lam = (np.arange(512)+.5)*np.pi
    coef = 2*(-1.)**np.arange(512)/lam
    cos = np.cos(lam[:, None]*z0[None, :]/H)
    sin = np.sin(lam[:, None]*z0[None, :]/H)
    valid = times >= tD
    refs = {}
    for name, capacity in (("M0", 1.), ("finite_Kw", B)):
        P, settle = np.full((N, 100), np.nan), np.full((N, 100), np.nan)
        decay = np.exp(-capacity*Cv*lam[None, :]**2*(times[valid, None]-tD)/H**2)
        P[valid] = capacity*q0*((decay*coef)@cos)
        settle[valid] = 1000*q0/M*(z0[None, :]-H*capacity*((decay*coef/lam)@sin))
        refs[name] = dict(P=P, settle=settle)
    return refs, dict(E_Pa=E, nu=nu, k_m_s=k, rho_w_kg_m3=water, Kw_Pa=Kw, n0=n0,
                      q0_Pa=q0, H_m=H, tD_s=tD, g_reference_m_s2=g, M_Pa=M, Cv_M0_m2_s=Cv,
                      B_finite_Kw=B, Cv_finite_Kw_m2_s=B*Cv, modes=512)


def describe(d, refs, constants, np):
    scheme, order = d["scheme"], d["order"]
    times, completed = d["clock"]["t"], d["completed"]
    sign = np.where(np.arange(10) % 2, -1., 1.)
    rows, layers = [], []
    arrays = {key: [] for key in ("P", "settle", "total", "J", "n", "rho", "aUz", "aT")}
    refname = "finite_Kw" if scheme == "A" else "M0"
    ref = refs[refname]
    failures = []
    for part, q in enumerate(d["p"]["q"]):
        P = q[order, 6].reshape(100, 10)
        settle = -1000*(q[order, 2]-d["x0"][order, 2]).reshape(100, 10)
        total = q[:, 10:16].copy()
        total[:, [0, 3, 5]] -= q[:, 6, None]
        tg = total[order].reshape(100, 10, 6)
        J = q[order, 8].reshape(100, 10)
        n, rho = d["n"]["n"][part, order].reshape(100, 10), d["rho"][part, order].reshape(100, 10)
        uz = -settle
        aUz = ((uz-uz.mean(axis=1, keepdims=True))*sign).mean(axis=1)
        aT = ((tg-tg.mean(axis=1, keepdims=True))*sign[None, :, None]).mean(axis=1)
        vertical = tg[:, :, 5].mean(axis=1)
        stress = float(np.max(abs(vertical+constants["q0_Pa"])))
        gap = float(abs(vertical[-1]-vertical[-2]))
        post = bool(times[part] >= .1-1e-7)
        if post and (stress > 100. or gap > 100.):
            failures.append(dict(scheme=scheme, part=part, time_s=float(times[part]), completed_step=int(completed[part]),
                                 max_layer_total_error_Pa=stress, worst_layer=int(np.argmax(abs(vertical+constants["q0_Pa"]))),
                                 top_pair_total_gap_Pa=gap, original_limit_Pa=100.))
        row = dict(scheme=scheme, part=part, time_s=float(times[part]), completed_steps=int(completed[part]),
                   legacy_Tv_since_drain=constants["Cv_M0_m2_s"]*(float(times[part])-constants["tD_s"]),
                   pressure_mean_Pa=float(P.mean()), pressure_J_weighted_mean_Pa=float(np.sum(q[:, 6]*q[:, 8])/np.sum(q[:, 8])),
                   pressure_RMS_Pa=float(np.sqrt(np.mean(P**2))), pressure_min_Pa=float(P.min()), pressure_max_Pa=float(P.max()),
                   top10_pressure_Pa=float(P[-1].mean()), bottom10_pressure_Pa=float(P[0].mean()),
                   top10_settlement_mm=float(settle[-1].mean()), bottom10_settlement_mm=float(settle[0].mean()),
                   speed_XYZ_RMS_m_s=float(np.sqrt(np.mean(np.sum(q[:, 3:6]**2, axis=1)))),
                   total_compression_zz_mean_Pa=float(-total[:, 5].mean()), max_layer_total_error_Pa=stress,
                   top_pair_total_gap_Pa=gap, Q_total_zz_second_difference_RMS_Pa=float(np.sqrt(np.mean(np.diff(vertical, n=2)**2))),
                   original_post_01_guard_applies=post, original_stress_guard_passed=(not post or stress <= 100.),
                   original_top_gap_guard_passed=(not post or gap <= 100.),
                   A_pi_Uz_RMS_over100layers_mm=float(np.sqrt(np.mean(aUz**2))), A_pi_Uz_abs_max_mm=float(np.max(abs(aUz))),
                   A_pi_total_sigma_RMS_over100layers_6components_Pa=float(np.sqrt(np.mean(aT**2))),
                   J_min=float(J.min()), J_mean=float(J.mean()), J_max=float(J.max()),
                   n_min=float(n.min()), n_mean=float(n.mean()), n_max=float(n.max()),
                   rho_native_min_kg_m3=float(rho.min()), rho_native_mean_kg_m3=float(rho.mean()), rho_native_max_kg_m3=float(rho.max()),
                   **{"total_sigma_"+c+"_mean_Pa": float(total[:, j].mean()) for j, c in enumerate(COMPONENTS)},
                   appropriate_companion=refname, companion_same_node_mean_P_Pa=None,
                   companion_material_top_settlement_mm=None, companion_material_bottom_settlement_mm=None,
                   native_minus_qualified_companion_P_profile_RMS_Pa=None,
                   native_minus_qualified_companion_top_settlement_mm=None)
        old = d["history"][part]
        for key, oldkey in (("pressure_mean_Pa", "pressure_mean_Pa"), ("top10_settlement_mm", "top10_settlement_mean_mm"),
                            ("bottom10_settlement_mm", "bottom10_settlement_mean_mm"),
                            ("rho_native_mean_kg_m3", "native_current_rho_mean_kg_m3")):
            need(math.isclose(row[key], float(old[oldkey]), rel_tol=2e-12, abs_tol=2e-9),
                 "Condensed definition differs from original native history: "+scheme+"/"+key)
        if np.isfinite(ref["P"][part]).all():
            row.update(companion_same_node_mean_P_Pa=float(ref["P"][part].mean()),
                       companion_material_top_settlement_mm=float(ref["settle"][part, -1]),
                       companion_material_bottom_settlement_mm=float(ref["settle"][part, 0]),
                       native_minus_qualified_companion_P_profile_RMS_Pa=float(np.sqrt(np.mean((P.mean(axis=1)-ref["P"][part])**2))),
                       native_minus_qualified_companion_top_settlement_mm=float(settle[-1].mean()-ref["settle"][part, -1]))
        rows.append(row)
        for key, values in (("P", P), ("settle", settle), ("total", tg), ("J", J), ("n", n), ("rho", rho), ("aUz", aUz), ("aT", aT)):
            arrays[key].append(values)
        for level in range(100):
            layers.append(dict(scheme=scheme, part=part, time_s=float(times[part]), initial_layer=level, z0_m=float(d["z0"][level]),
                               A_pi_Uz_signed_mm=float(aUz[level]), A_pi_total_sigma_zz_signed_Pa=float(aT[level, 5])))
    need(any(r["original_post_01_guard_applies"] for r in rows), "No observed original post-.1s safety coverage")
    d["arrays"] = {key: np.array(value) for key, value in arrays.items()}
    d["rows"] = rows
    return rows, layers, failures


def figures(data, refs, times, selections, np):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    panels = (("pressure_mean_Pa", "Same original IDs: mean pressure (Pa)"),
              ("top10_settlement_mm", "Initial top10 material settlement (mm)"),
              ("bottom10_settlement_mm", "Initial bottom10 material settlement (mm)"),
              ("total_compression_zz_mean_Pa", "Mean total vertical compression (Pa)"),
              ("max_layer_total_error_Pa", "Original max layer stress / top gap (Pa)"),
              ("Q_total_zz_second_difference_RMS_Pa", "Total-stress second-difference Q (Pa)"),
              ("J_mean", "J, native mean and min/max"), ("n_mean", "Native porosity mean and min/max"),
              ("rho_native_mean_kg_m3", "Native mixture density (kg/m3)"), ("speed_XYZ_RMS_m_s", "XYZ velocity RMS (m/s)"))
    fig, axes = plt.subplots(5, 2, figsize=(14, 18), constrained_layout=True)
    for ax, (field, label) in zip(axes.flat, panels):
        for scheme in SCHEMES:
            rr = data[scheme]["rows"]
            ax.plot(times, [r[field] for r in rr], color=COLORS[scheme], label=LABELS[scheme], lw=1.1)
            bounds = {"J_mean": ("J_min", "J_max"), "n_mean": ("n_min", "n_max"),
                      "rho_native_mean_kg_m3": ("rho_native_min_kg_m3", "rho_native_max_kg_m3")}.get(field)
            if bounds:
                ax.fill_between(times, [r[bounds[0]] for r in rr], [r[bounds[1]] for r in rr], color=COLORS[scheme], alpha=.09)
            if field == "max_layer_total_error_Pa":
                ax.plot(times, [r["top_pair_total_gap_Pa"] for r in rr], color=COLORS[scheme], ls=":", lw=.9)
        if field in ("pressure_mean_Pa", "top10_settlement_mm", "bottom10_settlement_mm"):
            refkey = {"pressure_mean_Pa": "companion_same_node_mean_P_Pa", "top10_settlement_mm": "companion_material_top_settlement_mm", "bottom10_settlement_mm": "companion_material_bottom_settlement_mm"}[field]
            for scheme, title, style in (("A", "Finite-Kw quasi-static companion", "--"), ("B", "M0 quasi-static companion", "-.")):
                ax.plot(times, [r[refkey] for r in data[scheme]["rows"]], color="black", ls=style, lw=1., label=title)
        if field == "max_layer_total_error_Pa":
            ax.plot([.1, times[-1]], [100, 100], "k--", label="Original post-.1s 100 Pa limit")
        ax.axvline(.010000228881835938, color="grey", lw=.7)
        ax.set(xlabel="Actual scalar saved time (s)", ylabel=label)
        ax.grid(True, alpha=.35); ax.legend(fontsize=7)
    fig.suptitle("Complete .15 s startup: finite-Kw A versus M0 B/C; qualified companions are not exact dynamic truth")
    save_png(fig, PRODUCTS["history.png"]); plt.close(fig)
    fig, axes = plt.subplots(3, len(selections), figsize=(22, 12), constrained_layout=True)
    for c, (target, part) in enumerate(selections):
        for scheme in SCHEMES:
            a, z = data[scheme]["arrays"], data[scheme]["z0"]
            values = (a["P"][part].mean(axis=1), a["settle"][part].mean(axis=1), -a["total"][part, :, :, 5].mean(axis=1))
            for row, value in enumerate(values):
                axes[row, c].plot(value, z, color=COLORS[scheme], label=LABELS[scheme])
        for name, style in (("finite_Kw", "--"), ("M0", "-.")):
            if np.isfinite(refs[name]["P"][part]).all():
                axes[0, c].plot(refs[name]["P"][part], data["A"]["z0"], color="black", ls=style, label=name+" companion")
                axes[1, c].plot(refs[name]["settle"][part], data["A"]["z0"], color="black", ls=style, label=name+" companion")
        axes[0, c].set_title("target %.5g s\nactual %.12g s; part %d" % (target, times[part], part), fontsize=8)
        for row, title in enumerate(("Pressure (Pa)", "Material settlement (mm)", "Total compression zz (Pa)")):
            axes[row, c].set(xlabel=title, ylabel="Original material z0 (m)"); axes[row, c].grid(True, alpha=.35)
    legend_column = max(c for c, (_, part) in enumerate(selections) if np.isfinite(refs["M0"]["P"][part]).all())
    axes[0, legend_column].legend(fontsize=7); axes[1, legend_column].legend(fontsize=7)
    fig.suptitle("Fixed original 100 material layers; exact common saved frames, no spatial/time fit or smoothing")
    save_png(fig, PRODUCTS["profiles.png"]); plt.close(fig)
    fig, axes = plt.subplots(3, 3, figsize=(17, 12), constrained_layout=True)
    for c, scheme in enumerate(SCHEMES):
        d = data[scheme]
        for r, (key, component, title) in enumerate((("aUz", None, "Signed alternating X-column Uz (mm)"), ("aT", 5, "Signed alternating total sigma zz (Pa)"))):
            values = d["arrays"][key] if component is None else d["arrays"][key][:, :, component]
            span = float(np.max(abs(values))) or 1.  # A zero field gets a finite display scale only.
            mesh = axes[r, c].pcolormesh(times, d["z0"], values.T, shading="nearest", cmap="coolwarm", vmin=-span, vmax=span)
            fig.colorbar(mesh, ax=axes[r, c], label=title)
            axes[r, c].set(xlabel="Actual saved time (s)", ylabel="Original material z0 (m)", title=LABELS[scheme]+"; own symmetric range")
        axes[2, c].plot(times, [v["A_pi_Uz_RMS_over100layers_mm"] for v in d["rows"]], label="RMS of all100 signed layer modes")
        axes[2, c].plot(times, [v["A_pi_Uz_abs_max_mm"] for v in d["rows"]], label="Max absolute layer mode")
        axes[2, c].set(xlabel="Actual saved time (s)", ylabel="Alternating Uz amplitude (mm)"); axes[2, c].grid(True); axes[2, c].legend(fontsize=7)
    fig.suptitle("All100 layer modes and every startup frame; per-panel ranges declared, no filtering/clipping")
    save_png(fig, PRODUCTS["modes.png"]); plt.close(fig)


def science(ad, result):
    import numpy as np
    data = {scheme: load(ad, scheme, np, result) for scheme in SCHEMES}
    a = data["A"]
    for scheme in ("B", "C"):
        d = data[scheme]
        need(d["clock"]["t"].tobytes() == a["clock"]["t"].tobytes()
             and d["completed"].tobytes() == a["completed"].tobytes()
             and d["x0"].tobytes() == a["x0"].tobytes(), "Actual common clocks/steps/original IDs/material geometry differ")
    times = a["clock"]["t"]
    refs, constants = references(ad, times, a["z0"], np)
    history, modes, failures = [], [], []
    for scheme in SCHEMES:
        h, m, failed = describe(data[scheme], refs, constants, np)
        history += h; modes += m; failures += failed
    failures.sort(key=lambda r: (r["time_s"], r["scheme"]))
    selections = [(target, int(np.argmin(abs(times-target)))) for target in PROFILES]
    profiles = []
    for scheme in SCHEMES:
        d, refname = data[scheme], "finite_Kw" if scheme == "A" else "M0"
        aa = d["arrays"]
        for target, part in selections:
            for level in range(100):
                profiles.append(dict(scheme=scheme, target_time_s=target, actual_part=part, actual_time_s=float(times[part]),
                    signed_target_gap_s=float(times[part]-target), initial_layer=level, z0_m=float(d["z0"][level]),
                    pressure_mean_Pa=float(aa["P"][part, level].mean()), pressure_min_Pa=float(aa["P"][part, level].min()), pressure_max_Pa=float(aa["P"][part, level].max()),
                    material_settlement_mean_mm=float(aa["settle"][part, level].mean()), total_compression_zz_mean_Pa=float(-aa["total"][part, level, :, 5].mean()),
                    J_mean=float(aa["J"][part, level].mean()), n_native_mean=float(aa["n"][part, level].mean()), rho_native_mean_kg_m3=float(aa["rho"][part, level].mean()),
                    appropriate_companion=refname, companion_P_Pa=float(refs[refname]["P"][part, level]) if np.isfinite(refs[refname]["P"][part, level]) else None,
                    companion_settlement_mm=float(refs[refname]["settle"][part, level]) if np.isfinite(refs[refname]["settle"][part, level]) else None))
    cross = []
    for left, right in (("A", "B"), ("A", "C"), ("B", "C")):
        for part in range(N):
            d, e = data[left], data[right]
            q, r = d["p"]["q"][part], e["p"]["q"][part]
            # Minimum image in the retained x-periodic cell; all other XYZ differences are direct.
            disp = q[:, :3]-r[:, :3]
            disp[:, 0] -= .1*np.floor(disp[:, 0]/.1+.5)
            x, y = d["rows"][part], e["rows"][part]
            cross.append(dict(pair=left+"_minus_"+right, part=part, time_s=float(times[part]),
                              pressure_same_ID_RMS_difference_Pa=float(np.sqrt(np.mean((q[:, 6]-r[:, 6])**2))),
                              material_XYZ_max_difference_mm=float(1000*np.max(np.sqrt(np.sum(disp**2, axis=1)))),
                              top10_settlement_difference_mm=x["top10_settlement_mm"]-y["top10_settlement_mm"],
                              bottom10_settlement_difference_mm=x["bottom10_settlement_mm"]-y["bottom10_settlement_mm"],
                              total_compression_mean_difference_Pa=x["total_compression_zz_mean_Pa"]-y["total_compression_zz_mean_Pa"],
                              Q_difference_Pa=x["Q_total_zz_second_difference_RMS_Pa"]-y["Q_total_zz_second_difference_RMS_Pa"],
                              descriptive_only_no_half_or_5Pa_equivalence_gate=True))
    metrics = dict(stage=TAG, analysis_complete=True, physical_acceptance=False, schemes={}, cross={},
                   original_post_01s_safety=dict(start_time_s=.1-1e-7, max_layer_total_error_Pa=100., top_pair_gap_Pa=100.,
                                               failures=failures, all_schemes_passed=not failures),
                   constants=constants, appropriate_reference={"A": "finite_Kw", "B": "M0", "C": "M0"},
                   companion_limits="Unfitted H1 quasi-static companions; no exact finite-ramp/band/inertia/J-n startup truth or accuracy acceptance",
                   PorePressRate_is_legacy_scaled_endpoint_residual_not_actual_BC_dpdt=True,
                   actual_common_clock_ID_layer_alignment=True, interpolation_or_header_rewrite=False,
                   new_half_or_full_run_admitted=False, SHA_scans=0)
    for scheme in SCHEMES:
        rr = data[scheme]["rows"]
        post = [r for r in rr if r["original_post_01_guard_applies"]]
        metrics["schemes"][scheme] = dict(final=rr[-1], observed_runtime=data[scheme]["timing"],
            all_startup_pressure_min_Pa=min(r["pressure_min_Pa"] for r in rr),
            all_startup_pressure_max_Pa=max(r["pressure_max_Pa"] for r in rr),
            all_startup_A_pi_Uz_abs_max_mm=max(r["A_pi_Uz_abs_max_mm"] for r in rr),
            post_01_max_layer_total_error_Pa=max(r["max_layer_total_error_Pa"] for r in post),
            post_01_max_top_pair_gap_Pa=max(r["top_pair_total_gap_Pa"] for r in post), post_01_saved_frames=len(post),
            guard_first_failure=next((r for r in failures if r["scheme"] == scheme), None))
    for pair in ("A_minus_B", "A_minus_C", "B_minus_C"):
        rr = [r for r in cross if r["pair"] == pair]
        metrics["cross"][pair] = {key: max(rr, key=lambda r: abs(r[key])) for key in
            ("pressure_same_ID_RMS_difference_Pa", "material_XYZ_max_difference_mm", "top10_settlement_difference_mm", "bottom10_settlement_difference_mm")}
    ad.finish()
    for name, rows in (("history.csv", history), ("profiles.csv", profiles), ("modes.csv", modes), ("cross.csv", cross)):
        write_csv(PRODUCTS[name], rows)
    write_json(PRODUCTS["metrics.json"], metrics)
    figures(data, refs, times, selections, np)
    ad.finish()
    result.update(passed=not failures, analysis_complete=True, metrics=stat(PRODUCTS["metrics.json"]),
                  actual_frames_per_scheme=N, original_native_IDs_per_scheme=1040, material_layers=100,
                  rows=dict(history=len(history), profiles=len(profiles), modes=len(modes), cross=len(cross)),
                  first_original_guard_failure=failures[0] if failures else None,
                  original_guard_failure_count=len(failures), no_failed_C_hidden_or_excluded=True,
                  files=[stat(p) for p in PRODUCTS.values()], constants=constants)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--execution-authorized", action="store_true")
    p.add_argument("--admission", required=True, type=Path)
    args = p.parse_args()
    need(args.execution_authorized, "Root full-read and one offline-only execution required")
    need(not CHECK.exists() and all(not x.exists() for x in PRODUCTS.values()), "Existing/partial scientific outputs are protected; never overwrite")
    ad = Admission(args.admission)
    result = dict(stage=TAG, passed=False, analysis_complete=False, root_admission=ad.entry, scheme_status={},
                  solver_invocations=0, native_invocations=0, build_invocations=0, old_analysis_invocations=0,
                  SHA_scans=0, physical_acceptance=False, automatic_follow_up=False,
                  cross_model_5Pa_or_half_equivalence_gate=False, pressure_clipping_filtering_or_fit=False)
    try:
        science(ad, result)
    except Exception as exc:
        result.update(first_failure=str(exc), partial_outputs_preserved=True)
        raise
    finally:
        result["consumed"] = list(ad.used.values())
        write_json(CHECK, result)
    print(str(CHECK))
    return 0 if result["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
