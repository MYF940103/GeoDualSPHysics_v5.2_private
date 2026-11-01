"""Read-only independent audit of the sealed public CPU nine-job/11-reject stage.

No subprocesses, native programs, compiler, source edits or Git operations.
Writes only one new analysis check JSON; never replaces retained evidence.
"""
import csv
import hashlib
import json
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

T = Path(__file__).resolve().parents[1]
L = T / "logs"
TAG = "upl_cpu_public_independent_r1"
CHECK = L / (TAG + ".check.json")
NOTE = T / "notes" / (TAG + ".md")
JOBS = ("debug_wall_evolving_smoke", "periodic_constant_c", "periodic_constant_h",
        "wall_constant_c", "wall_constant_h", "wall_evolving_c", "wall_evolving_h",
        "OFF_default", "OFF_explicit")
PAIRS = ("periodic_constant", "wall_constant", "wall_evolving")
N0, RHO0, RHOW, KW = .25, 2048., 1000., 67108864.
K, G, A, CK = 89478488., 134217728., 2.**-9, 2.**-13
K0 = float(np.float32(.0001))
M = K + 4*G/3
CU = np.sqrt((M+KW/N0)/RHO0)
PSTAR, USTAR = (KW/N0)*A/CU, A/(CU*2*np.pi/(1/8))
SCHEMA = (("Idp", "<u4", 1), ("Posd", "<f8", 3), ("Vel", "<f4", 3),
          ("Sigma_kk", "<f4", 3), ("Sigma_ij", "<f4", 3), ("FSNormal", "<f4", 3),
          ("HydroMechLoadAce", "<f4", 3), ("Rhop", "<f4", 1), ("Kplastic", "<f4", 1),
          ("PorePress", "<f4", 1), ("PorePress0", "<f4", 1), ("ExcessPorePress", "<f4", 1),
          ("SigmaState_kk", "<f8", 3), ("SigmaState_ij", "<f8", 3), ("FSType", "<u4", 1))
BINDINGS, HASHED = {}, {}


def need(ok, text):
    if not ok:
        raise RuntimeError(text)


def bound(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def verify(value):
    if isinstance(value, dict):
        if {"path", "bytes", "sha256"} <= value.keys():
            key = (value["path"], value["bytes"], value["sha256"].lower())
            if key not in HASHED:
                got = bound(value["path"])
                need((got["bytes"], got["sha256"]) == key[1:], "Frozen binding changed: " + key[0])
                HASHED[key] = got
        for child in value.values():
            verify(child)
    elif isinstance(value, list):
        for child in value:
            verify(child)


def read(path, verify_contents=True):
    path = Path(path).resolve()
    BINDINGS[str(path)] = bound(path)
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if verify_contents:
        verify(value)
    return value


def close(got, expected, text):
    need(np.all(np.isfinite(got)) and np.allclose(got, expected, rtol=5e-13, atol=0), text)


def raw15(path, n, samples):
    data = Path(path).read_bytes()
    need(struct.unpack("<III", data[:12]) == (n, 15, samples), "Original15 header differs")
    offset, times, frames = 12, [], []
    for part in range(samples):
        times.append(struct.unpack_from("<d", data, offset)[0]); offset += 8
        frame = {}
        for name, dtype, width in SCHEMA:
            values = np.frombuffer(data, dtype=dtype, count=n*width, offset=offset)
            offset += values.nbytes
            need(np.isfinite(values).all(), "Nonfinite original15: " + name)
            frame[name] = values.reshape(n, width) if width > 1 else values
        need(np.array_equal(frame["Idp"], np.arange(n)), "Original15 native ID order differs")
        need(np.array_equal(frame["Sigma_kk"], frame["SigmaState_kk"].astype("<f4")) and
             np.array_equal(frame["Sigma_ij"], frame["SigmaState_ij"].astype("<f4")),
             "Float stress does not round from actual double stress")
        need(np.array_equal(frame["ExcessPorePress"], frame["PorePress"]-frame["PorePress0"]),
             "Actual float excess differs")
        frames.append(frame)
    need(offset == len(data), "Unreviewed/truncated original15 bytes")
    return np.array(times), frames


def physical(path, n, samples):
    data = Path(path).read_bytes()
    need(struct.unpack("<III", data[:12]) == (n, 26, samples), "Physical header differs")
    values = np.frombuffer(data, dtype="<f8", offset=12).reshape(samples, 1+n*26)
    need(np.isfinite(values).all(), "Nonfinite actual 26 fields")
    return values[:, 0], values[:, 1:].reshape(samples, n, 26)


def audit_job(label, plan, program_by_config):
    spec = next(job for job in plan["jobs"] if job["label"] == label)
    solved = read(L / ("upl_cpu_public_"+label+"_r1.solver.check.json"))
    reviewed = read(L / ("upl_cpu_public_"+label+"_r1.review.check.json"))
    need(solved["passed"] and reviewed["passed"] and solved["native_frames"] == spec["samples"],
         "A canonical job has not completed its own native review")
    solver_call = read(solved["call"]["path"])
    reader_call = read(reviewed["reader_call"]["path"])
    for call in (solver_call, reader_call):
        need(call["owned_call_exited"] and call["exit_code"] == 0, "Owned call did not exit zero")
    need(solver_call["program"] == program_by_config[spec["configuration"]], "Wrong canonical CPU program")
    need("-cpu" in solver_call["arguments"] and not any(a.startswith("-gpu") for a in solver_call["arguments"]),
         "Canonical job is not explicit CPU")
    complete = read(reviewed["completion"]["path"])
    need(complete["passed"] and complete["samples"] == spec["samples"] and
         complete["native_count"] == spec["native"] and complete["fixed_count"] == spec["fixed"] and
         complete["no_exclusions"] and complete["saved_clock_step_exact"], "Native completion identity differs")
    folder = Path(reviewed["completion"]["path"]).parent
    times, frames = raw15(folder/"original15.bin", spec["native"]+spec["fixed"], spec["samples"])
    wanted = np.arange(spec["samples"])*spec["cadence"]
    need(np.array_equal(times, wanted), "Original15 saved clocks differ")
    with (folder/"history.csv").open(newline="", encoding="utf-8") as stream:
        history = list(csv.DictReader(stream))
    need(len(history) == spec["samples"], "Incomplete saved history")
    for part, row in enumerate(history):
        step = round(wanted[part]/spec["dt"])-1 if part else 0
        need(int(row["part"]) == part and float(row["time_s"]) == wanted[part] and
             int(row["native_step"]) == step and float(row["dt_s"]) == spec["dt"], "Native actual time/step mismatch")
        error = float(row["dterror_s"])
        need(np.isfinite(error) and error <= 1e-14, "Original signed dterror guard failed")
    soil_ids = np.genfromtxt(folder/"native_ids.csv", delimiter=",", names=True)
    need(np.array_equal(soil_ids["native_id"], np.arange(spec["fixed"], spec["fixed"]+spec["native"])),
         "Native material ID ledger differs")
    result = {"job": label, "frames": spec["samples"], "soil": spec["native"], "fixed": spec["fixed"],
              "dt": spec["dt"], "actual_end_s": float(times[-1]), "owned_solver_exit": 0,
              "signed_dterror_min": min(float(r["dterror_s"]) for r in history),
              "signed_dterror_max": max(float(r["dterror_s"]) for r in history)}
    if not spec["dynamic"]:
        need(not (folder/"physical.bin").exists() and complete["derived_arrays"] == 0 and complete["model_metadata_absent"],
             "OFF native output acquired dynamic state/metadata")
        return result, None
    tp, x = physical(folder/"physical.bin", spec["native"], spec["samples"])
    need(np.array_equal(times, tp), "Original15/physical clock mismatch")
    # Independently decode the actual original15 typed layout and compare all common fields.
    for part, f in enumerate(frames):
        sl = slice(spec["fixed"], None)
        for columns, name in ((slice(0, 3), "Posd"), (slice(3, 6), "Vel"), (6, "PorePress"),
                (7, "PorePress0"), (16, "Kplastic"), (17, "FSType"), (slice(18, 21), "FSNormal"),
                (slice(22, 25), "HydroMechLoadAce"), (25, "Rhop")):
            need(np.array_equal(x[part, :, columns], f[name][sl]), "Original15/26 native field mismatch: "+name)
        sigma = np.column_stack((f["SigmaState_kk"][sl, 0], f["SigmaState_ij"][sl, 0], f["SigmaState_ij"][sl, 2],
                                 f["SigmaState_kk"][sl, 1], f["SigmaState_ij"][sl, 1], f["SigmaState_kk"][sl, 2]))
        need(np.array_equal(x[part, :, 10:16], sigma), "Six stress component ordering differs")
    j = x[:, :, 8]; n = 1-(1-N0)/j; rho = RHOW+(RHO0-RHOW)/j
    dp = 1/512 if spec["fixed"] else 1/256
    volume = dp*dp*j
    k = K0*np.exp((j-1)/((1-N0)*CK)) if spec["model"] else np.full_like(j, K0)
    need((j > 1-N0).all() and np.max(abs(j-1)) <= 1e-4 and (n > 0).all() and (n < 1).all(), "Weak saturated J domain failed")
    need(np.max(abs((1-n)*j-(1-N0))) <= 5e-13, "Solid-volume ledger identity failed")
    span = np.max(np.ptp(k, axis=1)/K0); change = np.max(abs(k/K0-1))
    close(float(np.min(k)), complete["min_k"], "J-derived minimum k differs")
    close(float(np.max(k)), complete["max_k"], "J-derived maximum k differs")
    close(float(span), complete["max_k_span_over_initial_k0"], "J-derived spatial k span differs")
    close(float(change), complete["max_k_change_over_initial_k0"], "J-derived k evolution differs")
    need(complete["ledger_native_checks"] == spec["native"]*spec["samples"] and
         complete["fixed_marker_checks"] == spec["fixed"]*spec["samples"] and
         complete["max_ledger_relative_error"] <= 5e-13, "Native reader derived-array coverage failed")
    sig = x[:, :, 10:16]; tr = sig[:, :, 0]+sig[:, :, 3]+sig[:, :, 5]; mean = tr/3
    dev = sum((sig[:, :, q]-mean)**2 for q in (0, 3, 5))+2*sum(sig[:, :, q]**2 for q in (1, 2, 4))
    energy = np.sum(volume*(.5*rho*np.sum(x[:, :, 3:6]**2, axis=2)+dev/(4*G)+tr*tr/(18*K)+n*x[:, :, 6]**2/(2*KW)), axis=1)
    er = energy/energy[0]
    need(np.isfinite(er).all() and np.max(er) <= 1.1, "Independent full-field energy guard failed")
    close(er, np.array([float(r["energy_ratio"]) for r in history]), "Independent energy/history differs")
    close(float(np.max(er)), complete["max_energy_ratio"], "Independent maximum energy differs")
    h = float(np.float32(1.8*dp)); b = KW/n; d = b*k/(RHOW*9.80665)
    cfl = np.sqrt((M+b)/rho)*spec["dt"]/h; diff = d*spec["dt"]/(h*h)
    need(np.max(cfl) <= .01 and np.max(diff) <= .01 and
         (rho*b/(M+b)-RHOW > 64*np.finfo(float).eps*np.maximum(rho, RHOW)).all(), "Independent necessary current-state scale/domain failed")
    close(float(np.max(cfl)), complete["max_coupled_CFL"], "Current J-derived wave scale differs")
    close(float(np.max(diff)), complete["max_Ddt_h2"], "Current J-derived diffusion scale differs")
    result.update({"soil_records": int(j.size), "fixed_markers_checked_by_native_reader": complete["fixed_marker_checks"],
        "max_energy_ratio": float(np.max(er)), "end_energy_ratio": float(er[-1]), "max_abs_J_minus_1": float(np.max(abs(j-1))),
        "min_n": float(n.min()), "max_n": float(n.max()), "min_rho": float(rho.min()), "max_rho": float(rho.max()),
        "min_k": float(k.min()), "max_k": float(k.max()), "max_k_span_over_k0": float(span), "max_k_change_over_k0": float(change),
        "max_coupled_CFL": float(cfl.max()), "max_Ddt_h2": float(diff.max()),
        "derived_saved_array_relative_error_checked_by_native_reader": complete["max_ledger_relative_error"]})
    return result, (folder, times, x)


def main():
    need(not CHECK.exists(), "Independent result retained; no overwrite")
    freeze_path = L/"upl_cpu_public_build_r3.json"
    freeze = read(freeze_path, False)
    need(len(freeze["source"]) == 7 and freeze["msbuild_exit_codes"] == {"DebugCPU": 0, "ReleaseCPU": 0}, "Full Rebuild r3 required")
    for key in ("source", "programs", "inputs", "logs"):
        verify(freeze[key])
    verify([r["snapshot"] for r in freeze["prior_programs"]])
    off = read(L/"upl_cpu_public_off_r2.check.json")
    need(off["passed"] and off["actual_native_frame_pairs"] == 140 and off["all_bits_0ULP"] and off["clock_step_dterror_exact"] and off["exclusions"] == 0, "Default OFF140 gate required")
    for group in off["groups"]:
        need(read(group["check"]["path"])["passed"], "A default OFF group failed")
    plan = read(L/"upl_cpu_public_r1.inputs.json")
    need(tuple(j["label"] for j in plan["jobs"]) == JOBS, "Undeclared public matrix")
    programs = {}
    for cfg in ("DebugCPU", "ReleaseCPU"):
        build = read(L/("upl_cpu_public_reader_"+cfg+"_r2.build.json"))
        need(build["status"] == "built_not_run" and build["compile_exit"] == build["link_exit"] == 0 and
             build["source_freeze"] == bound(freeze_path), "Wrong isolated program/reader build")
        programs[cfg] = build["canonical_program"]
    jobs, fields = [], {}
    for label in JOBS:
        row, field = audit_job(label, plan, programs)
        jobs.append(row); fields[label] = field
    half = []
    for pair in PAIRS:
        receipt = read(L/("upl_cpu_public_"+pair+"_r1.half.check.json"))
        reference = read(receipt["completion"]["path"])
        need(receipt["passed"] and reference["passed"], "A half check failed")
        left, right = fields[pair+"_c"], fields[pair+"_h"]
        need(np.array_equal(left[1], right[1]) and np.array_equal(left[2][0].view("<u8"), right[2][0].view("<u8")), "Half clocks/initial26 differ")
        for name in ("native_ids.csv", "fixed_ids.csv"):
            need((left[0]/name).read_bytes() == (right[0]/name).read_bytes(), "Half material identity differs")
        c, h = left[2], right[2]
        pr = np.sqrt(np.mean((c[:, :, 6]-h[:, :, 6])**2, axis=1))
        vr = np.sqrt(np.mean(np.sum((c[:, :, 3:6]-h[:, :, 3:6])**2, axis=2), axis=1))/A
        ur = np.sqrt(np.mean(np.sum((c[:, :, :3]-h[:, :, :3])**2, axis=2), axis=1))/USTAR
        um = 1000*np.max(np.linalg.norm(c[:, :, :3]-h[:, :, :3], axis=2))
        values = {"max_pressure_RMS_Pa": float(pr.max()), "max_material_displacement_mm": float(um),
                  "max_pressure_RMS_over_Pstar": float(pr.max()/PSTAR), "max_velocity_vector_RMS_over_A": float(vr.max()),
                  "max_displacement_vector_RMS_over_Ustar": float(ur.max()), "max_J_difference": float(np.max(abs(c[:, :, 8]-h[:, :, 8])))}
        need(pr.max() <= 5 and um <= .005 and pr.max()/PSTAR <= 1e-4 and vr.max() <= 1e-4 and ur.max() <= 1e-4, "Original absolute/normalized half bounds failed")
        for key, value in values.items():
            close(value, reference[key], "Independent half metric differs: "+pair+"/"+key)
        half.append({"pair": pair, "samples": len(left[1]), "soil": c.shape[1], **values})
    exact = read(L/"upl_cpu_public_OFF_r1.exact.check.json")
    need(exact["passed"] and exact["samples"] == 9 and len(exact["equal_files"]) == 4, "Canonical OFF exact gate required")
    for equal in exact["equal_files"]:
        need(Path(equal["left"]["path"]).read_bytes() == Path(equal["right"]["path"]).read_bytes(), "Absent/explicit OFF bytes differ")
    prepared = read(L/"upl_cpu_public_reject_r1.inputs.json")
    need(len(prepared["cases"]) == 11, "Exactly eleven invalid inputs required")
    rejected = []
    for case in prepared["cases"]:
        r = read(L/("upl_cpu_public_reject_r1_"+case["label"]+".run.json"))
        text = Path(r["log"]["path"]).read_bytes().decode("utf-8", errors="replace")
        need(r["passed"] and r["owned_call_exited"] and r["exit_code"] != 0 and
             case["expected_exact_message"] in text and r["target_guard_reached"] and
             not r["parser_rejection_target_guard_not_reached"] and not r["identity_error"], "Invalid input did not reach its exact target guard")
        native = [p for p in Path(case["output"]).rglob("Part_*.bi4") if p.stem[5:].isdigit()]
        need(not native and r["native_PART_count"] == 0, "Invalid input saved a native PART")
        need(r["program"] == programs["ReleaseCPU"], "Invalid-input executable differs")
        rejected.append({"label": case["label"], "owned_pid": r["pid"], "exit_code": r["exit_code"], "exact_guard": True, "native_PART_count": 0})
    for path in (Path(__file__), NOTE, Path(sys.executable)):
        BINDINGS[str(path.resolve())] = bound(path)
    # Second pass catches a source/result changing during the independent read.
    for row in list(HASHED.values()) + list(BINDINGS.values()):
        need(bound(row["path"]) == row, "Audit input changed while reading")
    result = {"passed": True, "utc": datetime.now(timezone.utc).isoformat(), "scope": "Completed nine canonical CPU jobs, three independent half pairs, eleven invalid-input guards and default-OFF140 only",
        "physical_acceptance": False, "formal_or_general_upl_acceptance": False, "source_freeze": bound(freeze_path),
        "source_snapshots_equal_current_worktree": True, "source_files": 7, "numpy_version": np.__version__,
        "unique_verified_identity_bindings": len(HASHED), "identity_mismatches": 0, "input_receipts": list(BINDINGS.values()),
        "jobs": jobs, "half_recomputed": half, "rejections": rejected,
        "total_canonical_native_frames": sum(j["frames"] for j in jobs),
        "actual_dynamic_soil_records": sum(j.get("soil_records", 0) for j in jobs),
        "default_OFF_native_frame_pairs": 140, "absent_vs_explicit_OFF_files_byte_exact": 4,
        "pending_restart_invalid_cases": 3,
        "limitations": ["Independent Python decodes the frozen reader original15/26 analysis binaries, not native BI4 directly. Native BI4 typed arrays, six saved derived arrays and metadata rely on the frozen canonical reader, its verified output identities and complete node/frame coverage; Python independently recalculates J-derived summaries, energy and scales.",
            "Theta is last force-stage state, not a newly synchronized endpoint rate. Cached gradient-k stage maximum is not independently present in native output; production necessary-stage guard and prior private component coverage remain prerequisites.",
            "dterror is finite signed requested-bound telemetry <=1e-14, not an absolute clock error. Actual clocks/steps are checked separately.",
            "No new wall flux/reaction or private-control equivalence claim here; those are separate retained/root comparison stages.",
            "Finite-window weak-field agreement and necessary local limits do not establish asymptotic spectral stability, conservation, general boundaries, GPU, PART restart or formal physical validation."]}
    with CHECK.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps({"passed": True, "check": str(CHECK), "verified_bindings": len(HASHED), "jobs": len(jobs), "half_pairs": len(half), "invalid_guards": len(rejected), "frames": result["total_canonical_native_frames"], "dynamic_soil_records": result["actual_dynamic_soil_records"], "halfs": half}, indent=2))


if __name__ == "__main__":
    main()
