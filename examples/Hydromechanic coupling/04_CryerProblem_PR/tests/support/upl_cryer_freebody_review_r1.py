"""Offline completed Cryer startup review; never invokes a solver or decoder."""
from pathlib import Path
import csv
import json
import os
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
C = T.parent
TAG, RUN = "upl_cryer_freebody_review_r1", "upl_cryer_freebody_short_GPU_r1"
N, FIXED, SOIL, TOTAL, DT, DRAIN = 69, 8, 37173, 37181, 2.**-20, 2.**-7
LIMITS = dict(pressure_target_rms_Pa=100., total_stress_target_six_rms_Pa=100., speed_max_m_s=1e-5,
              isotropic_vector_residual_rms_mm=1e-5, shell_target_error_rms_mm=1e-5)


def need(ok, why):
    if not ok:
        raise RuntimeError(why)


def rows(path):
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def stat(path):
    s = path.stat()
    return dict(path=str(path.resolve()), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def write(path, data):
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0])); writer.writeheader(); writer.writerows(data)


def main():
    os.environ["OPENBLAS_NUM_THREADS"] = os.environ["MKL_NUM_THREADS"] = "1"
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    native = T / "outputs" / (RUN + "_native")
    oldpath = C / "figures/formal_validation/cryer_formal_four_nu_r1_nu030_summary.csv"
    xmlpath = T / "configs/upl_cryer_freebody_short_r1_Def.xml"
    contractpath = T / "notes/upl_cryer_comparison_contract_r1.json"
    leaves = ("completion.json", "summary.csv", "center18.csv", "native_ids.csv", "columns.csv", "common26.bin", "clock.bin")
    sources = [native / leaf for leaf in leaves] + [oldpath, xmlpath, contractpath, Path(__file__), T / "notes" / (TAG + ".json")]
    before = [stat(p) for p in sources]
    outputs = {name: T / "figures" / (TAG + "_" + name) for name in ("history.csv", "center18.csv", "closed.csv", "history.png", "closed.png")}
    check = T / "logs" / (TAG + ".check.json")
    need(not any(p.exists() for p in [*outputs.values(), check]), "Fresh review outputs required; no overwrite/retry")
    done = json.loads((native / "completion.json").read_text(encoding="utf-8"))
    expected = dict(stage="upl_cryer_public_native_r1", passed=True, declared_backend="GPU", window="short_8704",
                    samples=N, completed_steps=8704, dt_s=DT, actual_end_s=.00830078125, total_native_ids=TOTAL,
                    soil_ids=SOIL, fixed_ids=FIXED, center_material_ids=18, native_typed_arrays=22,
                    soil_ledger_checks=SOIL*N, fixed_marker_checks=FIXED*N, post_open_frames=4, noninitial_signed_dterror_intervals=68)
    need(all(done[k] == v for k, v in expected.items()) and done["post_open_FS23_zero_pressure_checks"] > 0,
         "Completed69-frame original native guards are required")
    data, center, old = rows(native / "summary.csv"), rows(native / "center18.csv"), rows(oldpath)
    need(len(data) == N and len(center) == N*18 and np.isfinite([[float(v) for v in r.values()] for r in data]).all(), "Incomplete/nonfinite summary or center histories")
    time = np.array([float(r["time_s"]) for r in data])
    need(np.array_equal(time, np.arange(N)*128*DT) and [int(r["part"]) for r in data] == list(range(N)), "Actual saved times/parts differ")
    ctype = np.dtype([("time", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("error", "<f8")])
    clockpath = native / "clock.bin"
    need(tuple(np.fromfile(clockpath, dtype="<u4", count=2)) == (N, 28) and clockpath.stat().st_size == 8+N*28, "Clock binary schema differs")
    clock = np.memmap(clockpath, mode="r", offset=8, dtype=ctype, shape=(N,))
    need(np.array_equal(clock["time"], time) and np.all(clock["dt"] == DT) and np.all(np.isfinite(clock["error"])) and
         np.all(clock["error"] <= 1e-14) and np.array_equal(clock["step"], np.maximum(np.arange(N)*128-1, 0)), "Original signed clocks/Step guard failed")
    ids = np.loadtxt(native / "native_ids.csv", delimiter=",", skiprows=1)
    need(ids.shape == (TOTAL, 9) and np.array_equal(ids[:, 0], np.arange(TOTAL)) and np.all(ids[:FIXED, 1] == 0) and np.all(ids[FIXED:, 1] == 1), "Original fixed/soil ID layout differs")
    contract = json.loads(contractpath.read_text(encoding="utf-8"))["observation"]["fixed_initial_material_IDs"]
    selected = ids[ids[:, 7] == 1, 0].astype(int).tolist()
    need(selected == contract, "The exact original center18 IDs differ")
    for i in range(N):
        selected_rows = [r for r in center if int(r["part"]) == i]
        need([int(r["id"]) for r in selected_rows] == contract and all(float(r["time_s"]) == time[i] and
             np.array_equal([float(r[k]) for k in ("x0", "y0", "z0")], ids[int(r["id"]), 2:5]) for r in selected_rows), "Individual center IDs/initial coordinates/actual clocks differ")
    dtype = np.dtype([("time", "<f8"), ("q", "<f8", (TOTAL, 26))])
    path = native / "common26.bin"
    need(tuple(np.fromfile(path, dtype="<u4", count=3)) == (TOTAL, 26, N) and path.stat().st_size == 12+N*dtype.itemsize, "All-ID common26 binary schema differs")
    fields = [r["name"] for r in rows(native / "columns.csv")]
    need(fields[10:16] == "sigma_xx sigma_xy sigma_xz sigma_yy sigma_yz sigma_zz".split() and fields[21] == "ExcessPorePress", "Native stress/excess-pressure columns differ")
    mapped = np.memmap(path, mode="r", offset=12, dtype=dtype, shape=(N,))
    need(np.array_equal(mapped[0]["q"][:, :3], ids[:, 2:5]), "Initial native coordinates differ from ID ledger")
    root = ET.parse(xmlpath).getroot()
    value = lambda name: float(root.find(".//"+name).attrib["value"])
    E, nu, Kw, q0, n0 = value("ModulusE"), value("PRvs"), value("PoreWaterBulkModulus"), value("HydroMechTopLoadQ0"), float(np.float32(value("Porosity")))
    need(value("HydroMechDrainageStartTime") == DRAIN and value("HydroMechTopLoadRampTime") == 2.**-8 and
         float(data[0]["n_min"]) == n0 and float(data[0]["n_max"]) == n0, "Reference inputs differ")
    K, Mf = E/(3*(1-2*nu)), Kw/n0
    pstar, effective, alpha = Mf*q0/(K+Mf), -K*q0/(K+Mf), -q0/(3*(K+Mf))
    x0, r0, w = ids[FIXED:, 2:5], ids[FIXED:, 5], ids[FIXED:, 6].copy()
    need(np.all(w > 0), "Positive initial native-volume weights required")
    w /= w.sum(); shell = ids[FIXED:, 8] == 1; sw = w[shell]/w[shell].sum()
    closed = []
    for i in (61, 62, 63, 64):
        q = mapped[i]["q"][FIXED:]; need(mapped[i]["time"] == time[i] and np.isfinite(q).all(), "Closed native state invalid")
        u, p = q[:, :3]-x0, q[:, 6]
        total = q[:, 10:16].copy(); total[:, [0, 3, 5]] -= p[:, None]; total[:, [0, 3, 5]] += q0
        efferror = q[:, 10:16].copy(); efferror[:, [0, 3, 5]] -= effective
        beta = np.sum(w*np.sum(u*x0, axis=1))/np.sum(w*r0*r0)
        inward = 1000*(r0-np.linalg.norm(q[:, :3], axis=1))
        row = dict(part=i, time_s=float(time[i]), pressure_target_rms_Pa=float(np.sqrt(w@((p-pstar)**2))),
                   total_stress_target_six_rms_Pa=float(np.sqrt(w@np.mean(total**2, axis=1))), speed_max_m_s=float(np.linalg.norm(q[:, 3:6], axis=1).max()),
                   isotropic_vector_residual_rms_mm=float(1000*np.sqrt(w@np.sum((u-beta*x0)**2, axis=1))),
                   shell_target_error_rms_mm=float(np.sqrt(sw@((inward[shell]+1000*alpha*r0[shell])**2))),
                   isotropic_target_vector_error_rms_mm=float(1000*np.sqrt(w@np.sum((u-alpha*x0)**2, axis=1))),
                   isotropic_fit_scalar=float(beta), unfitted_isotropic_target=alpha, conditional_pressure_target_Pa=pstar,
                   pressure_initial_V_mean_Pa=float(w@p), effective_mean_compression_initial_V_Pa=float(-w@q[:, [10, 13, 15]].mean(axis=1)),
                   effective_stress_target_six_rms_Pa=float(np.sqrt(w@np.mean(efferror**2, axis=1))),
                   conditional_effective_diagonal_target_Pa=effective, conditional_shell_mean_inward_target_mm=float(-1000*alpha*(sw@r0[shell])))
        row["all_five_original_diagnostics_passed"] = all(row[k] <= limit for k, limit in LIMITS.items()); closed.append(row)
    lookup = {float(r["time_s"]): r for r in old}; need(len(lookup) == len(old), "Old summary has duplicate times")
    matched = [i for i, t in enumerate(time) if float(t) in lookup]
    need(matched == list(range(65)) and all(int(lookup[float(time[i])]["part"]) == i for i in matched), "Actual old exact-time overlap is not the expected65 pre-open rows")
    old_fields = ("center_pressure_pa", "pressure_mean_pa", "shell_inward_mm", "total_mean_compression_pa", "speed_max_m_s")
    for i, row in enumerate(data):
        prior = lookup.get(float(time[i])); row["old_exact_time_match"] = prior is not None
        row.update({"old_formal_"+k: prior[k] if prior else "" for k in old_fields})
    write(outputs["history.csv"], data); write(outputs["center18.csv"], center); write(outputs["closed.csv"], closed)
    fig, axes = plt.subplots(4, 2, figsize=(12, 13), constrained_layout=True)
    def line(ax, key, label=None): ax.plot(time, [float(r[key]) for r in data], label=label or key)
    line(axes[0, 0], "center_pressure_Pa", "u-pl fixed18"); line(axes[0, 0], "pressure_initial_V_mean_Pa", "u-pl initial-V mean")
    axes[0, 0].plot(time[matched], [float(lookup[float(time[i])]["center_pressure_pa"]) for i in matched], "--", label="old u-pw fixed18, exact times only")
    for id in contract: axes[0, 0].plot(time, [float(r["PorePress"]) for r in center if int(r["id"]) == id], color="grey", alpha=.15, linewidth=.6)
    for key in ("shell_inward_initial_V_mm", "material_inward_initial_V_mm"): line(axes[0, 1], key)
    axes[0, 1].plot(time[matched], [float(lookup[float(time[i])]["shell_inward_mm"]) for i in matched], "--", label="old u-pw shell, exact times only")
    for key in ("J_min", "J_initial_V_mean", "J_max"): line(axes[1, 0], key)
    for key in ("n_min", "n_initial_V_mean", "n_max"): line(axes[1, 1], key)
    other = axes[1, 1].twinx(); line(other, "rho_native_initial_V_mean_kg_m3", "native mixture rho"); other.set_ylabel("rho (kg/m³)")
    for key in ("effective_mean_compression_initial_V_Pa", "total_mean_compression_initial_V_Pa"): line(axes[2, 0], key)
    for key in ("saved_J_load_proxy_inward_N", "saved_J_load_proxy_net_x_N", "saved_J_load_proxy_net_y_N", "saved_J_load_proxy_net_z_N"): line(axes[2, 1], key)
    for key in ("FS2_count", "FS3_count", "activeDrainCount"): line(axes[3, 0], key)
    other = axes[3, 0].twinx(); line(other, "surface_pressure_absmax_Pa", "actual surface max |P|"); other.set_ylabel("Surface |P| (Pa)")
    line(axes[3, 1], "speed_max_m_s", "actual max speed"); axes[3, 1].set_yscale("symlog", linthresh=1e-7)
    titles = ("Pressure (Pa), all18 points retained", "Fixed initial shell/material inward motion (mm)", "Same-J state", "Native n and mixture rho", "Effective/total mean compression (Pa)", "Saved-J load proxies (N), not force-stage budgets", "Actual FS2/3 and drained receivers", "Startup maximum speed (m/s)")
    for ax, title in zip(axes.flat, titles): ax.set(title=title, xlabel="Actual time (s)"); ax.axvline(DRAIN, color="k", linestyle=":"); ax.grid(alpha=.2); ax.legend(fontsize=6)
    fig.suptitle("3-D u-pl startup — old u-pw is a whole-framework descriptive control, historical program gap retained\nFour post-open frames are not a Mandel-peak or full physical acceptance")
    with outputs["history.png"].open("xb") as stream: fig.savefig(stream, format="png", dpi=150)
    plt.close(fig); fig, axes = plt.subplots(3, 2, figsize=(11, 9), constrained_layout=True)
    for ax, (key, limit) in zip(axes.flat, LIMITS.items()):
        ax.plot([r["part"] for r in closed], [r[key] for r in closed], "o-"); ax.axhline(limit, color="r", linestyle="--"); ax.set(title=key, xlabel="Actual closed Part"); ax.set_yscale("symlog", linthresh=limit/1e4); ax.grid(alpha=.2)
    axes[2, 1].plot([r["part"] for r in closed], [r["isotropic_target_vector_error_rms_mm"] for r in closed], "o-"); axes[2, 1].set(title="Unfitted u=alpha*x0 vector error (mm), descriptive", xlabel="Actual closed Part"); axes[2, 1].grid(alpha=.2)
    fig.suptitle("Parts61–64 only: original five conditional closed-loading diagnostics\nFinite Kw, actual float n0; no ramp/post-open theory claim, no fitted radius/time/load")
    with outputs["closed.png"].open("xb") as stream: fig.savefig(stream, format="png", dpi=150)
    plt.close(fig)
    need([stat(p) for p in sources] == before, "Consumed sealed input metadata changed")
    result = dict(stage=TAG, passed=True, offline_analysis_completed=True, sources=before, files=[stat(p) for p in outputs.values()],
                  samples=N, exact_old_time_rows=len(matched), exact_old_parts=matched, old_control_program_identity_unknown=True,
                  same_model_5Pa_equivalence_claimed=False, closed_original_limits=LIMITS, closed=closed,
                  all_five_closed_diagnostics_passed=all(r["all_five_original_diagnostics_passed"] for r in closed),
                  conditional_reference=dict(E_XML=E, nu_XML=nu, Kw=Kw, n_actual_float=n0, K=K, Mf=Mf, p=pstar, effective_diagonal=effective, alpha=alpha),
                  no_interpolation_or_time_radius_load_fit=True, fresh_hashes_performed=0, bindings_metadata_unchanged=True,
                  solver_or_decoder_invoked=False, force_stage_load_budget_claimed=False, physical_acceptance=False, automatic_next_action=False)
    with check.open("x", encoding="utf-8") as stream: json.dump(result, stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps(dict(analysis_completed=True, all_five_closed_diagnostics_passed=result["all_five_closed_diagnostics_passed"], check=str(check))))


if __name__ == "__main__":
    main()
