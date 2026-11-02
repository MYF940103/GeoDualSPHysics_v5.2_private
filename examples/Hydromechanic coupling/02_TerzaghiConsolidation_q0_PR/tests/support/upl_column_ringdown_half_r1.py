"""Offline dyadic GPU half check. Reuse the established column definitions, never a solver."""
import csv, hashlib, importlib.util, json, struct
from pathlib import Path
import numpy as np

T = Path(__file__).resolve().parents[1]
parent = T / "support/upl_gpu_column_pair_r1.py"
parent_source = parent.read_bytes()
if hashlib.sha256(parent_source).hexdigest() != "1da9023466c34f3ab77287eb77ccec270b60d2e07389a48e1ea4466cf3bdea28":
    raise ValueError("Retained neutral comparison helpers changed before import")
spec = importlib.util.spec_from_file_location("retained_column_pair", parent)
base = importlib.util.module_from_spec(spec)
exec(compile(parent_source, str(parent), "exec"), base.__dict__)  # Only the pinned bytes; retained main stays guarded.
need, bind, adopt, readjson, entry = base.require, base.bind, base.adopt, base.readjson, base.entry
N, S = 1277, 1000
SCHEMA = "case02_common26_col21_ExcessPorePress_NOT_wave26"
STEPS = np.array(sorted(set(range(0, 65537, 64)) | set(range(5120, 5377))), dtype=np.int64)

def mapped(e, header, dtype):
    p = bind(e)
    with p.open("rb") as f:
        need(struct.unpack("<" + "I" * len(header), f.read(4 * len(header))) == header, "Binary header differs")
    dtype = np.dtype(dtype)
    need(p.stat().st_size == 4 * len(header) + N * dtype.itemsize, "Binary payload length differs")
    return np.memmap(p, mode="r", offset=4 * len(header), dtype=dtype, shape=(N,))

def dataset(window):
    ce = adopt(T / ("logs/upl_column_ringdown_GPU_" + window + "_r1.native.json"))
    c = readjson(ce["path"])
    need(c["passed"] and c["physical_acceptance"] is False, "Native owner rejected")
    q = readjson(bind(c["completion"]))
    dt = 2.0 ** (-20 if window == "half" else -19)
    need(q["passed"] and q["backend"] == "GPU_public" and q["window"] == "ringdown125" and q["preset"] == window, "Wrong native preset/backend")
    need((q["samples"], q["native_count"], q["fixed_count"], q["total_native_count"], q["physical_columns"]) == (N, S, 40, 1040, 26), "Wrong native identity")
    need(q["physical_schema"] == SCHEMA and q["dt_s"] == dt and q["actual_end_s"] == 0.125, "Wrong schema/clock/end")
    need(q["public_schema"] and q["public_master_on"] and q["native_total_arrays"] == 22 and q["PART_typed_public_metadata_verified"] and q["no_exclusions"] and q["physical_acceptance"] is False, "Native typed/safety contract rejected")
    for e in c["inputs"] + c["files"]:
        bind(e)
    r = readjson(bind(c["source_run"]))
    need(r["passed"] and r["backend"] == "GPU" and r["window"] == window and r["physical_acceptance"] is False, "Source Run rejected")
    for e in r["inputs"] + r["files"]:
        bind(e)
    call = base.owned(r["call"])
    need(not call.get("invocation_failure"), "Solver invocation failed")
    reader_call = base.owned(c["reader_call"])
    h = readjson(bind(c["reader_helper"]))
    need(h["passed"] and h["exact_link_closure_verified"] and h["program"]["sha256"] == reader_call["program"]["sha256"], "Reader build/program rejected")
    bind(h["program"])
    b = readjson(bind(r["source_build"]))
    need(b["passed"] and b["isolated_GPU_program"]["sha256"] == call["program"]["sha256"], "Current project-main/build differs")
    files = {Path(e["path"]).name: e for e in c["files"]}
    need(len(files) == 13 and all(Path(e["path"]).parent == Path(c["paths"]["native_dir"]) for e in files.values()), "Native leaf scope differs")
    p = mapped(files["physical.bin"], (S, 26, N), [("time", "<f8"), ("q", "<f8", (S, 26))])
    clock = mapped(files["clock.bin"], (N, 28), [("time", "<f8"), ("step", "<u4"), ("dt", "<f8"), ("error", "<f8")])
    ids = np.genfromtxt(bind(files["native_ids.csv"]), delimiter=",", names=True, encoding="utf-8")
    need(np.array_equal(ids["id"], np.arange(40, 1040)) and np.array_equal(ids["row"], np.arange(S)), "Material ID order differs")
    x0 = np.column_stack([ids[k] for k in ("x0", "y0", "z0")]).astype("<f8")
    with bind(files["columns.csv"]).open(encoding="utf-8-sig", newline="") as f:
        cols = list(csv.DictReader(f))
    need([v["name"] for v in cols] == base.F and [int(v["column"]) for v in cols] == list(range(26)), "Column order differs")
    factor = 2 if window == "half" else 1
    done = np.where(np.arange(N) == 0, 0, clock["step"].astype(np.int64) + 1)
    need(np.array_equal(done, factor * STEPS) and np.all(clock["dt"] == dt), "Declared saved-step table differs")
    need(np.array_equal(clock["time"].view("<u8"), (STEPS * 2.0 ** -19).view("<u8")) and np.array_equal(p["time"].view("<u8"), clock["time"].view("<u8")), "Actual dyadic time bits differ")
    need(np.isfinite(clock["error"]).all() and np.all(clock["error"][1:] <= 1e-14) and np.all(clock["error"][1:] != -np.finfo(float).max), "Signed necessary-step guard rejected")
    need(np.array_equal(p["q"][0, :, :3].view("<u8"), x0.view("<u8")), "Initial material coordinates differ")
    return dict(check=ce, run=c["source_run"], build=r["source_build"], p=p, clock=clock, x0=x0)

def main():
    check = T / "logs/upl_column_ringdown_half_r1.check.json"
    metrics = T / "figures/upl_column_ringdown_half_r1.csv"
    need(not check.exists() and not metrics.exists(), "Retained result protected")
    result = dict(stage="upl_column_ringdown_half_r1", passed=False, physical_acceptance=False, solver_or_decoder_invoked=False, failure=None)
    try:
        adopt(__file__); adopt(T / "notes/upl_column_ringdown_half_r1.json"); adopt(parent)
        a, b = dataset("coarse"), dataset("half")
        need(a["build"] == b["build"] and np.array_equal(a["x0"].view("<u8"), b["x0"].view("<u8")), "Initial material/current build differs")
        gap = float(np.max(np.abs(a["clock"]["time"] - b["clock"]["time"])))
        pmax, umax = 0.0, 0.0
        field_max, field_rms = np.zeros(26), np.zeros(26)
        with metrics.open("x", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["part", "coarse_actual_time_s", "half_actual_time_s", "pressure_RMS_Pa", "material_XYZ_displacement_difference_max_mm", "velocity_XYZ_RMS_m_s", "stress6_RMS_Pa", "J_max_abs", "saved_theta_max_abs_s_inv"])
            for part in range(N):
                av, bv = np.asarray(a["p"]["q"][part]), np.asarray(b["p"]["q"][part])
                need(np.isfinite(av).all() and np.isfinite(bv).all(), "Nonfinite native state")
                d = av - bv; rms = np.sqrt(np.mean(d * d, axis=0)); ma = np.max(np.abs(d), axis=0)
                field_max = np.maximum(field_max, ma); field_rms = np.maximum(field_rms, rms)
                du = (av[:, :3] - a["x0"]) - (bv[:, :3] - b["x0"])
                p = float(rms[6]); u = float(1000 * np.max(np.linalg.norm(du, axis=1)))
                pmax, umax = max(pmax, p), max(umax, u)
                w.writerow([part, float(a["clock"]["time"][part]), float(b["clock"]["time"][part]), p, u, float(np.sqrt(np.mean(np.sum(d[:, 3:6] ** 2, axis=1)))), float(np.sqrt(np.mean(np.sum(d[:, 10:16] ** 2, axis=1)))), float(ma[8]), float(ma[9])])
        gates = dict(pressure_RMS_all_times_le_5Pa=pmax <= 5.0, material_XYZ_difference_all_times_le_0_005mm=umax <= 0.005, actual_time_difference_le_1e_minus14_s=gap <= 1e-14)
        for e in base.TRACKED.values():
            need(entry(e["path"]) == e, "Input changed during offline check")
        result.update(passed=all(gates.values()), gates=gates, samples=N, native_count=S, rows=N, native_checks=[a["check"], b["check"]], source_runs=[a["run"], b["run"]], source_build=a["build"], max_pressure_RMS_Pa=pmax, max_material_XYZ_displacement_difference_mm=umax, max_actual_time_difference_s=gap, max_field_RMS={k: float(v) for k, v in zip(base.F, field_rms)}, max_field_abs={k: float(v) for k, v in zip(base.F, field_max)}, all26_differences_descriptive_not_all26_gates=True, full_cycle_half_acceptance=False)
    except Exception as exc:
        result["failure"] = str(exc)
    result.update(inputs=list(base.TRACKED.values()), files=[entry(metrics)] if metrics.exists() else [])
    with check.open("x", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, allow_nan=False); f.write("\n")
    print(json.dumps({"passed": result["passed"], "check": str(check)}))
    return 0 if result["passed"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
