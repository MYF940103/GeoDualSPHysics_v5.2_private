"""Compare already saved CPU/GPU startup fields on the same material IDs and clocks."""
import json

import numpy as np

from tpi_r_public_compatibility import TESTS, check, read_with_history


def load_json(path):
    return json.loads(path.read_text(encoding="utf8"))


def material_values(arrays, fixed, total):
    order = np.argsort(arrays["Idp"])
    check(np.array_equal(arrays["Idp"][order], np.arange(total)), "Native material ID set")
    return {name: v[order[fixed:]] for name, v in arrays.items()}


def rms(values):
    return float(np.sqrt(np.mean(values ** 2)))


def history_error(left, right, time, run_codes):
    if left is None or right is None:
        check(left is None and right is None, "Pressure history presence")
        return None
    for h, code in zip((left, right), run_codes):
        check(h["values"]["RunCode"] == code and h["values"]["SavedTime"] == time,
              "Pressure history ownership or time")
    check({k: v for k, v in left["values"].items() if k != "RunCode"} ==
          {k: v for k, v in right["values"].items() if k != "RunCode"}, "Pressure history schema and clocks")
    a, b = left["arrays"], right["arrays"]
    ia, ib = np.argsort(a["Idp"]), np.argsort(b["Idp"])
    check(np.array_equal(a["Idp"][ia], b["Idp"][ib]), "Pressure history IDs")
    return rms(a["PorePressPrev"][ia].astype(float) - b["PorePressPrev"][ib])


def review(index, model, case, fixed, soil, expected_counts):
    base = [TESTS / "outputs" / f"tpi_r_public_compat_{b}_r1" for b in ("cpu", "gpu")]
    programs = []
    paths = [folder / f"{index}_default" for folder in base]
    for backend, path in zip(("cpu", "gpu"), paths):
        checked = load_json(TESTS / "logs" / f"tpi_r_public_compat_{backend}_r1.check.json")
        check(checked["passed"] and checked["backend"] == backend, "Reviewed backend")
        log = (path / "result/Run.out").read_text(encoding="utf8", errors="replace")
        check("Finished execution (code=0)." in log, "Solver completion")
        call_file = path / "call.json"
        if call_file.exists():
            call = load_json(call_file)
            check(call["exit"] == 0 and call["args"][0] == checked["executable"], "Original program call")
        programs.append(dict(path=checked["executable"], prior_review=f"tpi_r_public_compat_{backend}_r1.check.json",
                             separate_call_present=call_file.exists()))
    seeds = [next((folder / "seed").glob("*.xml")) for folder in paths]
    check(seeds[0].name == seeds[1].name and seeds[0].read_bytes() == seeds[1].read_bytes(), "Same input XML")
    files = [sorted((folder / "result/data").glob("Part_????.bi4")) for folder in paths]
    check(list(map(len, files)) == expected_counts, "Recorded frame counts")
    frames = []
    for left, right in zip(*files):
        check(left.name == right.name, "Matched PART")
        ra, ma, a, ha = read_with_history(left)
        rb, mb, b, hb = read_with_history(right)
        check(all(ra[k] == rb[k] for k in ("CaseName", "CaseNfixed", "CaseNfluid")) and
              (ra["CaseNfixed"], ra["CaseNfluid"]) == (fixed, soil), "Particle set")
        check(all(ma[k] == mb[k] for k in ("Cpart", "Step", "TimeStep", "SymplecticDtPre")) and
              ma["Nout"] == mb["Nout"] == 0, "Actual step or clock")
        check(a.keys() == b.keys() and len(a) == (15 if model == 0 else 22), "Complete production fields")
        a = material_values(a, fixed, fixed + soil)
        b = material_values(b, fixed, fixed + soil)
        diff = {}
        for name in a:
            check(a[name].shape == b[name].shape and a[name].dtype == b[name].dtype, "Array type " + name)
            d = a[name].astype(float) - b[name].astype(float)
            check(np.isfinite(d).all(), "Finite native fields " + name)
            diff[name] = float(np.max(np.abs(d)))
        pos = "Posd" if "Posd" in a else "Pos"
        xyz = a[pos].astype(float) - b[pos].astype(float)
        if not frames:
            check(not np.any(xyz), "Same initial material locations")
        p = a["PorePress"].astype(float) - b["PorePress"].astype(float)
        check(ma["dterror"] <= 1e-14 and mb["dterror"] <= 1e-14, "Signed time-step safety")
        frames.append(dict(part=int(ma["Cpart"]), step=int(ma["Step"]), time_s=float(ma["TimeStep"]),
                           pressure_RMS_Pa=rms(p), max_displacement_diff_mm=float(1000*np.linalg.norm(xyz, axis=1).max()),
                           effective_stress_max_diff_Pa=max(diff["SigmaState_kk"], diff["SigmaState_ij"]),
                           previous_pressure_RMS_Pa=history_error(ha, hb, ma["TimeStep"], (ra["RunCode"], rb["RunCode"])),
                           cpu_dterror_s=float(ma["dterror"]), gpu_dterror_s=float(mb["dterror"]), material_max_abs_diff=diff))
    pmax = max(row["pressure_RMS_Pa"] for row in frames)
    umax = max(row["max_displacement_diff_mm"] for row in frames)
    smax = max(row["effective_stress_max_diff_Pa"] for row in frames)
    return dict(model=model, case=case, same_xml=seeds[0].name, soil_count=soil, fixed_count=fixed,
                programs=programs, saved_frame_counts=expected_counts, shared=len(frames),
                max_pressure_RMS_Pa=pmax, max_displacement_diff_mm=umax, max_stress_diff_Pa=smax,
                startup_pressure_displacement_pass=pmax <= 5. and umax <= .005, frames=frames)


if __name__ == "__main__":
    cases = [(0, 0, "C02", 40, 1000, [4, 4]), (1, 1, "C04", 8, 37173, [4, 4]),
             (2, 2, "C04", 8, 37173, [5, 5]), (3, 2, "C02", 40, 1000, [3, 106])]
    results = [review(*case) for case in cases]
    result = dict(scope="Matched real startup PARTs only", pressure_limit_Pa=5., displacement_limit_mm=.005,
                  passed=all(item["startup_pressure_displacement_pass"] for item in results), profiles=results)
    out = TESTS / "logs/tpi_public_backend_startup_r1.json"
    encoded = json.dumps(result, indent=2, allow_nan=False)
    with out.open("x", encoding="utf8") as stream:
        stream.write(encoded + "\n")
    for item in results:
        print(item["model"], item["case"], item["shared"], item["max_pressure_RMS_Pa"],
              item["max_displacement_diff_mm"], item["max_stress_diff_Pa"])
    if not result["passed"]:
        raise SystemExit(1)
