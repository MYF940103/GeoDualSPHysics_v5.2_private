"""Fresh Release GPU short diagnostic; run, native and review are separate actions."""
from pathlib import Path
import argparse
import csv
import datetime
import json
import os
import re
import subprocess

import psutil

T = Path(__file__).resolve().parents[1]
SRC, LOGS = T.parents[3] / "src", T / "logs"
TAG = "upl_gpu_stabilizers_release_short_r1"
OUT, NATIVE = T / "outputs" / TAG, T / "outputs" / (TAG + "_native")
COMMIT = "295261305527e1d8b2fb76a3eb8d650bf3275a2b"
N, STEPS, DT = 150, 1632, 6.250143051147461e-6
FIELDS = "x y z vx vy vz PorePress PorePress0 J theta sigma_xx sigma_xy sigma_xz sigma_yy sigma_yz sigma_zz Kplastic FSType FSNormal_x FSNormal_y FSNormal_z ExcessPorePress LoadAce_x LoadAce_y LoadAce_z legacy_Rhop".split()
LEAVES = "original15.bin physical.bin clock.bin common_j_theta.bin soil_n.bin native_ids.csv fixed_ids.csv history.csv ledger.csv fixed_samples.csv last_poro.csv columns.csv completion.json".split()


def need(ok, why):
    if not ok:
        raise RuntimeError(why)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def observe(path):
    path = Path(path).resolve()
    s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def record(suffix):
    return LOGS / (TAG + suffix)


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def stable(entries):
    return all(observe(e["path"]) == e for e in entries)


def context():
    build_path = LOGS / "upl_gpu_stabilizers_Release_r1.build.json"
    build = read(build_path)
    need(build["stage"] == "upl_gpu_stabilizers_Release_r1" and build["passed"] and
         build["configuration"] == "Release" and build["exit_code"] == 0 and build["object_count"] == 111 and
         build["source_and_consumed_stats_unchanged"] and not build["changed_paths"] and
         build["root_verified_checkpoint"] == COMMIT,
         "Actual isolated Release GPU build must pass")
    exe = T / "outputs/upl_gpu_stabilizers_Release_r1/gpu/DualSPHysics5.2_GEO_win64.exe"
    need(Path(build["program"]["path"]).resolve() == exe.resolve(), "Unexpected Release program")
    need(all(observe(exe)[k] == build["program"][k] for k in ("path", "bytes", "mtime_ns")),
         "Release program metadata differs from its sealed build")
    prep_path = LOGS / "upl_gpu_stabilizers_short_r1.prepare.json"
    prep = read(prep_path)
    need(prep["passed"] and prep["samples"] == N and prep["steps"] == STEPS and prep["dt_s"] == DT,
         "Retained same-physics short preparation differs")
    reader_build_path = LOGS / "upl_gpu_stabilizers_native_Debug_r1.build.json"
    reader_build = read(reader_build_path)
    need(reader_build["passed"], "Retained Debug native reader build did not pass")
    cpu_path = LOGS / "upl_bigstep_full_r1.native.json"
    cpu = read(cpu_path)
    need(cpu["passed"], "Retained CPU full native receipt did not pass")
    cpu_dir = Path(cpu["directory"])
    done = read(cpu_dir / "completion.json")
    need(done["passed"] and done["samples"] == 1682 and done["backend"] == "CPU_public" and
         done["native_total_arrays"] == 22, "Retained CPU full native completion differs")
    sealed = [v["copy"] for v in prep["input_copies"]] + [prep["clock_prefix"], reader_build["program"]] + build["runtime"]
    for e in sealed:
        need(observe(e["path"])["bytes"] == e["bytes"] and
             ("mtime_ns" not in e or observe(e["path"])["mtime_ns"] == e["mtime_ns"]),
             "Selected sealed input/runtime metadata differs")
    selected = [build_path, exe, prep_path, Path(prep["clock_prefix"]["path"]), reader_build_path,
                Path(reader_build["program"]["path"]), cpu_path, cpu_dir / "completion.json", Path(__file__),
                T / "notes" / (TAG + ".json")]
    selected += [Path(v["copy"]["path"]) for v in prep["input_copies"]]
    selected += [Path(v["path"]) for v in build["runtime"]]
    selected += [cpu_dir / leaf for leaf in ("physical.bin", "clock.bin", "native_ids.csv", "fixed_ids.csv", "columns.csv")]
    return dict(build=build, build_path=build_path, program=exe, prepare=prep, prepare_path=prep_path,
                reader_build=reader_build, reader=Path(reader_build["program"]["path"]), cpu=cpu,
                cpu_path=cpu_path, cpu_dir=cpu_dir, inputs=[observe(p) for p in dict.fromkeys(selected)])


def no_solver():
    for p in psutil.process_iter(["pid", "name", "exe"]):
        try:
            if (p.info["name"] or "").lower().startswith("dualsphysics"):
                need(False, "A solver is already active: PID " + str(p.pid))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def invoke(program, args, label, extra):
    log, start, call = record(label + ".log"), record(label + ".start.json"), record(label + ".call.json")
    need(not any(p.exists() for p in (log, start, call)), "Existing process attempt is protected")
    began = now()
    with log.open("xb") as stream:
        child = subprocess.Popen([str(program), *args], cwd=SRC, stdout=stream, stderr=subprocess.STDOUT)
        p = psutil.Process(child.pid)
        identity = dict(pid=child.pid, creation_time=p.create_time(), parent_pid=p.ppid(),
                        executable=p.exe(), command=p.cmdline())
        identity_matches = (identity["parent_pid"] == os.getpid() and Path(identity["executable"]).resolve() == Path(program).resolve()
                            and identity["command"][1:] == args)
        start_data = dict(stage=TAG + label + ".start", program=observe(program), arguments=args,
                          working_directory=str(SRC), owner=dict(pid=os.getpid(), creation_time=psutil.Process().create_time()),
                          child=identity, actual_identity_matches_requested=identity_matches,
                          started_utc=began, source_commit=COMMIT, physical_acceptance=False, **extra)
        save(start, start_data)
        print(json.dumps(dict(event="started", action=label, child=identity)), flush=True)
        code = child.wait()
    # Seal the actual typed wait result before any output or numerical checks.
    save(call, dict(stage=TAG + label + ".call", program=observe(program), arguments=args,
                    working_directory=str(SRC), child=identity, started_utc=began, ended_utc=now(),
                    exit_code=code, exit_type=type(code).__name__, direct_process_exit_captured=True,
                    actual_identity_matches_requested=identity_matches,
                    start=observe(start), log=observe(log), physical_acceptance=False))
    need(type(code) is int and code == 0 and identity_matches, "Owned process failed; preserve its real call and partial outputs")
    return observe(start), observe(call)


def run(c, authorized):
    need(authorized, "Run requires --execution-authorized")
    protected = [OUT, NATIVE, *[record(s) for s in (".log", ".start.json", ".call.json", ".run.json",
                 ".native.log", ".native.start.json", ".native.call.json", ".native.json", ".cross.json")],
                 T / "figures" / (TAG + ".csv"), T / "figures" / (TAG + ".png")]
    need(not any(p.exists() for p in protected), "Fresh run/output/analysis paths required")
    no_solver()
    args = ["-gpu", "-stable", "-mdbc_freeslip", c["prepare"]["input_prefix"], str(OUT),
            "-dirdataout", "data", "-svres", "-nsteps:1632"]
    start, call = invoke(c["program"], args, "", dict(build=observe(c["build_path"]),
        sealed_program=c["build"]["program"], input_prepare=observe(c["prepare_path"]), inputs=c["inputs"],
        no_fresh_SHA_performed=True, native_decoder_invoked=False, automatic_follow_up=False))
    result = dict(stage=TAG + ".run", passed=False, start=start, call=call, source_commit=COMMIT,
                  build=observe(c["build_path"]), program=observe(c["program"]), inputs=c["inputs"],
                  physical_acceptance=False, native_decoder_invoked=False, automatic_follow_up=False)
    try:
        text = (OUT / "Run.out").read_text(encoding="utf-8", errors="replace")
        need('RunMode="Stable - Pos-Cell - Single-GPU"' in text and "Finished execution (code=0)." in text,
             "Actual GPU normal termination not recorded")
        need(re.search(r"Steps of simulation\.+:\s*1632\b", text), "Wrong completed-step count")
        need("forcecalls=3264 predictorupdates=1632 correctorupdates=1632 ratecalls=3264" in text and
             "ratecalculations=1633 endpoint_rate_reuses=1631" in text, "HG phase/cache counts differ")
        safety = re.search(r"max\(dt/tau\)=([\deE+.-]+) spinbound=([\deE+.-]+)", text)
        need(safety and 0 < float(safety[1]) <= .2 and 0 <= float(safety[2]) <= .01,
             "Original HG dt/tau or spin guard differs")
        parts = sorted((OUT / "data").glob("Part_*.bi4"))
        need([p.name for p in parts] == ["Part_%04d.bi4" % i for i in range(N)], "Missing/extra native frame")
        with (OUT / "Run.csv").open(newline="", encoding="utf-8-sig") as stream:
            run_rows = list(csv.DictReader(stream, delimiter=";"))
        need(len(run_rows) == 1 and int(run_rows[0]["Steps"]) == STEPS and int(run_rows[0]["PartFiles"]) == N and
             int(run_rows[0]["PartsOut"]) == 0 and "Single-GPU" in run_rows[0]["RunMode"], "Run.csv summary differs")
        need(stable(c["inputs"]), "Bound input/program metadata changed during run")
        result.update(passed=True, steps=STEPS, native_frames=N, HG_calls=[3264, 1632, 1632, 3264],
                      HG_calculation_reuse=[1633, 1631], max_dt_tau=float(safety[1]), spinbound=float(safety[2]),
                      simulation_runtime_s=float(re.search(r"Simulation Runtime\.+:\s*([\deE+.-]+)", text)[1]),
                      TSimul_s=float(run_rows[0]["TSimul"]), actual_device_from_Run_csv=run_rows[0]["Hardware"],
                      files=[observe(p) for p in parts], run_out=observe(OUT / "Run.out"), run_csv=observe(OUT / "Run.csv"),
                      bindings_metadata_unchanged=True)
        print(json.dumps(dict(event="run_passed_pending_native", TSimul_s=result["TSimul_s"],
                              actual_device=result["actual_device_from_Run_csv"])), flush=True)
    except Exception as error:
        result["reason"] = str(error)
        raise
    finally:
        save(record(".run.json"), result)


def completed_run(c):
    r = read(record(".run.json"))
    need(r["passed"] and r["steps"] == STEPS and r["native_frames"] == N and
         r["program"] == observe(c["program"]) and stable(r["inputs"]) and stable(r["files"]),
         "Completed run or bound metadata differs")
    need(stable([r["run_out"], r["run_csv"]]), "Completed Run.out/Run.csv metadata differs")
    need(read(r["call"]["path"])["exit_code"] == 0, "Missing actual solver exit0")
    return r


def native(c):
    r = completed_run(c)
    need(not NATIVE.exists() and not record(".native.json").exists(), "Native decode attempt is protected")
    no_solver()
    args = ["--read", "GPU", str(OUT / "data"), c["prepare"]["clock_prefix"]["path"],
            "gpu_stabilizers_short", str(NATIVE)]
    start, call = invoke(c["reader"], args, ".native", dict(source_run=observe(record(".run.json")),
        reader_build=observe(LOGS / "upl_gpu_stabilizers_native_Debug_r1.build.json"), inputs=c["inputs"]))
    done = read(NATIVE / "completion.json")
    checks = dict(stage="upl_gpu_stabilizers_native_r1", backend="GPU_public", window="gpu_stabilizers_short",
                  samples=N, total_native_count=1040, native_total_arrays=22, planned_completed_steps=STEPS,
                  post_open_frames=32, post_open_drained_particle_checks=320, noninitial_signed_dterror_intervals=149,
                  soil_ledger_checks=150000, fixed_public_zero_marker_checks=6000, all_native_J_theta_rows=156000)
    need(done["passed"] and all(done[k] == v for k, v in checks.items()) and done["no_exclusions"] and
         done["scalar_clock_plan_verified"] and done["actual_end_s"] == c["prepare"]["actual_end_s"],
         "Original native completion/coverage guards did not pass")
    need(stable(c["inputs"]) and stable(r["files"]), "Bound metadata changed during decode")
    save(record(".native.json"), dict(stage=TAG + ".native", passed=True, start=start, call=call,
        source_run=observe(record(".run.json")), completion=done, directory=str(NATIVE),
        files=[observe(NATIVE / leaf) for leaf in LEAVES], original_native_guards_passed=True,
        source_commit=COMMIT, bindings_metadata_unchanged=True, no_fresh_SHA_performed=True, physical_acceptance=False))


def review(c):
    os.environ["OPENBLAS_NUM_THREADS"] = os.environ["MKL_NUM_THREADS"] = "1"
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    r, nr = completed_run(c), read(record(".native.json"))
    need(nr["passed"] and nr["original_native_guards_passed"] and stable(nr["files"]) and
         nr["source_run"] == observe(record(".run.json")), "Native metadata changed")
    need(read(nr["call"]["path"])["exit_code"] == 0, "Missing actual reader exit0")
    csv_path, png_path = [T / "figures" / (TAG + ext) for ext in (".csv", ".png")]
    need(not any(p.exists() for p in (csv_path, png_path, record(".cross.json"))), "Retained review protected")
    def physical(directory, samples):
        path = directory / "physical.bin"
        need(tuple(np.fromfile(path, dtype="<u4", count=3)) == (1000, 26, samples) and
             path.stat().st_size == 12 + samples * 208008, "Common26 binary schema differs")
        dt = np.dtype([("t", "<f8"), ("q", "<f8", (1000, 26))])
        return np.memmap(path, mode="r", offset=12, dtype=dt, shape=(samples,))[:N]
    def clock(directory, samples):
        path = directory / "clock.bin"
        need(tuple(np.fromfile(path, dtype="<u4", count=2)) == (samples, 28) and
             path.stat().st_size == 8 + samples * 28, "Actual signed clock schema differs")
        dt = np.dtype([("t", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("error", "<f8")])
        return np.memmap(path, mode="r", offset=8, dtype=dt, shape=(samples,))[:N]
    cpu, gpu = physical(c["cpu_dir"], 1682), physical(NATIVE, N)
    cc, gc = clock(c["cpu_dir"], 1682), clock(NATIVE, N)
    for directory in (c["cpu_dir"], NATIVE):
        with (directory / "columns.csv").open(newline="") as stream:
            need([v["name"] for v in csv.DictReader(stream)] == FIELDS, "Column21/schema identity differs")
    for leaf, count in (("native_ids.csv", 1000), ("fixed_ids.csv", 40)):
        rows = [list(csv.DictReader((d / leaf).open(newline=""))) for d in (c["cpu_dir"], NATIVE)]
        need(rows[0] == rows[1] and len(rows[0]) == count, "Original material/fixed ID coordinates differ")
    need(cpu["q"][0].tobytes() == gpu["q"][0].tobytes(), "Initial common26 fields differ")
    need(np.isfinite(cpu["q"]).all() and np.isfinite(gpu["q"]).all(), "Nonfinite comparison input")
    gap = np.abs(cpu["t"] - gpu["t"])
    need(np.all(gap <= 1e-14) and np.array_equal(cc["t"], cpu["t"]) and np.array_equal(gc["t"], gpu["t"]) and
         np.array_equal(cc["step"], gc["step"]) and np.all(cc["dt"] == DT) and np.all(gc["dt"] == DT),
         "Actual clock/Step/locked-dt comparison failed")
    x0 = cpu["q"][0, :, :3]
    top, bottom = x0[:, 2] == x0[:, 2].max(), x0[:, 2] == x0[:, 2].min()
    need(top.sum() == bottom.sum() == 10, "Fixed original-material top/bottom layers differ")
    rows = []
    v0, drain = float(np.float32(.21)) / 2100., .010000228881835938
    for i in range(N):
        a, b = cpu["q"][i], gpu["q"][i]
        d = b - a
        loads = [np.sum((v0 * (1100. + 1000. * q[:, 8]))[:, None] * q[:, 22:25], axis=0) for q in (a, b)]
        nominal_z = -1000. * min(float(gpu["t"][i]) / drain, 1.)
        row = dict(part=i, time_s=float(gpu["t"][i]), CPU_time_s=float(cpu["t"][i]), time_gap_s=float(gap[i]),
                   saved_step=int(gc["step"][i]), post_open=int(i >= 118),
                   pressure_RMS_Pa=float(np.sqrt(np.mean(d[:, 6] ** 2))),
                   material_XYZ_difference_max_mm=float(1000 * np.linalg.norm(d[:, :3], axis=1).max()),
                   J_max_abs_difference=float(np.abs(d[:, 8]).max()),
                   stored_stress_Frobenius_error_RMS_Pa=float(np.sqrt(np.mean(np.sum(d[:, 10:16] ** 2 * [1, 2, 2, 1, 2, 1], axis=1)))),
                   saved_load_proxy_difference_norm_N_m=float(np.linalg.norm(loads[1] - loads[0])),
                   nominal_saved_time_load_z_N_m=nominal_z)
        for label, q, load, clk in (("CPU", a, loads[0], cc), ("GPU", b, loads[1], gc)):
            row.update({label + "_mean_pressure_Pa": float(q[:, 6].mean()),
                        label + "_top_settlement_mm": float(1000 * (x0[top, 2] - q[top, 2]).mean()),
                        label + "_bottom_settlement_mm": float(1000 * (x0[bottom, 2] - q[bottom, 2]).mean()),
                        label + "_J_mean": float(q[:, 8].mean()),
                        label + "_total_vertical_compression_mean_Pa": float((q[:, 6] - q[:, 15]).mean()),
                        label + "_signed_dterror_s": float(clk["error"][i]),
                        label + "_saved_proxy_minus_saved_time_nominal_z_N_m": float(load[2] - nominal_z)})
            row.update({label + "_saved_load_" + axis + "_N_m": float(load[j]) for j, axis in enumerate("xyz")})
        rows.append(row)
    with csv_path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    fig, axes = plt.subplots(4, 2, figsize=(12, 14), constrained_layout=True)
    t = [v["time_s"] for v in rows]
    def line(ax, key, label=None):
        ax.plot(t, [v[key] for v in rows], label=label or key)
    for label in ("CPU", "GPU"):
        line(axes[0, 0], label + "_mean_pressure_Pa", label)
        line(axes[0, 1], label + "_top_settlement_mm", label + " top")
        line(axes[0, 1], label + "_bottom_settlement_mm", label + " bottom")
        line(axes[2, 0], label + "_J_mean", label)
        line(axes[2, 1], label + "_total_vertical_compression_mean_Pa", label)
        line(axes[3, 1], label + "_signed_dterror_s", label)
    for ax, key, bound in ((axes[1, 0], "pressure_RMS_Pa", 5.), (axes[1, 1], "material_XYZ_difference_max_mm", .005),
                           (axes[3, 0], "saved_load_proxy_difference_norm_N_m", .001)):
        line(ax, key, "observed difference"); ax.axhline(bound, color="r", linestyle="--", label="existing comparison bound")
        ax.set_yscale("symlog", linthresh=bound / 1e6)
    secondary = axes[2, 1].twinx()
    line(secondary, "stored_stress_Frobenius_error_RMS_Pa", "stored stress difference")
    secondary.lines[-1].set(color="tab:red", linestyle=":")
    secondary.set_ylabel("Stress difference RMS (Pa)")
    secondary.legend(loc="lower right", fontsize=7)
    titles = ["Same-node arithmetic mean pore pressure (Pa)", "Fixed material top/bottom settlement (mm)",
              "Per-frame pressure RMS difference (Pa)", "Maximum per-ID XYZ difference (mm)",
              "Same material mean J", "Mean total vertical compression (Pa)",
              "Saved-load proxy backend difference (N/m)", "Original signed necessary-step diagnostic (s)"]
    for ax, title in zip(axes.flat, titles):
        ax.set(title=title, xlabel="Actual saved time (s)"); ax.grid(alpha=.25); ax.legend(fontsize=7)
    fig.suptitle("Release GPU / retained CPU full first150 actual frames — bounded implementation check\nSaved load proxies are not a force-stage load measurement; no full physical acceptance")
    with png_path.open("xb") as stream:
        fig.savefig(stream, format="png", dpi=150)
    plt.close(fig)
    maxima = {k: max(v[k] for v in rows) for k in ("pressure_RMS_Pa", "material_XYZ_difference_max_mm",
              "time_gap_s", "J_max_abs_difference", "stored_stress_Frobenius_error_RMS_Pa", "saved_load_proxy_difference_norm_N_m")}
    passed = maxima["pressure_RMS_Pa"] <= 5 and maxima["material_XYZ_difference_max_mm"] <= .005 and maxima["time_gap_s"] <= 1e-14 and maxima["saved_load_proxy_difference_norm_N_m"] <= .001
    unchanged = stable(c["inputs"]) and stable(r["files"]) and stable(nr["files"])
    save(record(".cross.json"), dict(stage=TAG + ".cross", passed=bool(passed and unchanged), samples=N,
        source_commit=COMMIT, source_native=observe(record(".native.json")), source_CPU_native=observe(c["cpu_path"]),
        maxima=maxima, gates=dict(pressure_RMS_Pa=5, per_material_XYZ_mm=.005, actual_time_s=1e-14, saved_proxy_backend_norm_N_m=.001),
        files=[observe(csv_path), observe(png_path)], bindings_metadata_unchanged=unchanged,
        no_fresh_SHA_performed=True, no_resampling_or_interpolation=True, original_native_arrays=22, all_native_IDs=1040,
        saved_proxy_formula="sum(V0*(rho0-rhow+rhow*Jnew)*retained_LoadAce); compare backend vectors only",
        absolute_saved_proxy_target_errors_recorded=True, nominal_saved_time_target_is_not_force_stage_target=True,
        original_force_stage_load_budget_N_m=.001, actual_force_stage_budget_observed_or_claimed_passed=False,
        post_point1_stress_gate_exercised=False, physical_acceptance=False, controlled_speedup_claimed=False))
    need(passed and unchanged, "Release comparison failed; preserve all observations and figures")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "native", "review"))
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    c = context()
    if args.action == "run":
        run(c, args.execution_authorized)
    elif args.action == "native":
        native(c)
    else:
        review(c)


if __name__ == "__main__":
    main()
