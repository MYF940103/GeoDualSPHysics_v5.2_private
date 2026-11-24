"""Public C02/C04 changing-conductivity smoke, constant-k regression and backend review.

Run each backend once with its newly built Release program, then run --review.
The baseline seeds and comparison PARTs are the archived public TPI regression.
"""
import argparse
import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np

TESTS = Path(__file__).resolve().parents[1]
SPHERE = TESTS.parents[1] / "04_CryerProblem_PR/tests"
sys.path.insert(0, str(SPHERE / "support"))
from public_tpi_regression import read_with_history

SPECS = {
    "column_archive": (TESTS, 2, None, 25),
    "column_const": (TESTS, 2, None, 2004),
    "column_lim": (TESTS, 2, 1e100, 25),
    "column_var": (TESTS, 2, .5, 2004),
    "column_exp": (TESTS, 1, .5, 2004),
    "sphere_const": (SPHERE, 2, None, 4),
    "sphere_var": (SPHERE, 2, .5, 32),
}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def write(path, obj):
    with path.open("x", encoding="utf8") as stream:
        json.dump(obj, stream, indent=2, allow_nan=False)


def old(case, backend):
    if case == TESTS:
        profile = "public_tpi_column25_cpu_hist1" if backend == "cpu" else "public_tpi_column_gpu_hist1"
    else:
        profile = f"public_tpi_sphere4hist_{backend}_hist1"
    return case / "outputs" / profile


def run_path(case, tag, backend, label):
    return case / "outputs" / f"{tag}_{backend}_{label}"


def run_one(exe, tag, backend, label):
    case, model, ck, steps = SPECS[label]
    base = old(case, backend)
    previous = json.loads((base / "review.json").read_text())
    check(previous["exit"] == 0, str(base))
    dest = run_path(case, tag, backend, label)
    dest.mkdir()
    seed, result = dest / "seed", dest / "result"
    shutil.copytree(base / "seed", seed)
    xml, = seed.glob("*.xml")
    tree = ET.parse(xml)
    hydro = tree.find("./execution/special/hydromechanics")
    if ck is not None:
        for name, value in (("HydroMechModel", model), ("HydroMechConductivityModel", 1),
                            ("HydroMechConductivityCk", ck)):
            el = hydro.find(name)
            if el is None:
                el = ET.SubElement(hydro, name)
            el.set("value", str(value))
            el.attrib.pop("comment", None)
        if label == "sphere_var":
            # Save every eight real updates; preserve the original ramp and drainage clocks.
            pars = tree.find("./execution/parameters")
            dt = float(pars.find("./parameter[@key='DtFixed']").get("value"))
            pars.find("./parameter[@key='TimeOut']").set("value", str(8 * dt))
    if case == TESTS and steps == 2004:
        # Equal physical times and dt for the finite-Kw and TPI comparison.
        # The 10 us archived TPI setting would exceed the explicit coupled-wave bound.
        pars = tree.find("./execution/parameters")
        dt = float(pars.find("./parameter[@key='DtFixed']").get("value")) / 2.
        for key in ("DtFixed", "DtIni"):
            pars.find(f"./parameter[@key='{key}']").set("value", str(dt))
    if ck is not None or (case == TESTS and steps == 2004):
        tree.write(xml, encoding="utf-8", xml_declaration=True)
    args = previous["args"].copy()
    args[0] = str(exe)
    args[args.index(str(base / "seed" / xml.stem))] = str(xml.with_suffix(""))
    args[args.index(str(base / "result"))] = str(result)
    args[-1] = f"-nsteps:{steps}"
    with (dest / "console.log").open("xb") as stream:
        p = subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT, cwd=dest)
    write(dest / "call.json", dict(args=args, exit=p.returncode, program_size=exe.stat().st_size,
                                    program_mtime_ns=exe.stat().st_mtime_ns))
    check(p.returncode == 0, str(dest / "console.log"))
    check("Finished execution (code=0)" in (result / "Run.out").read_text(errors="replace"),
          "Missing solver completion")


def frames(folder):
    return sorted((folder / "result/data").glob("Part_????.bi4"))


def ordered(path):
    root, meta, arrays, hist = read_with_history(path)
    ids = np.argsort(arrays["Idp"])
    total = int(root["CaseNp"])
    check(len(arrays) == 22 and int(meta["Nout"]) == 0 and int(meta["Npok"]) == total and
          np.array_equal(arrays["Idp"][ids], np.arange(total)), str(path))
    ordered_arrays = {k: v[ids] for k, v in arrays.items()}
    check(all(np.isfinite(v).all() for v in ordered_arrays.values()), "Nonfinite saved particle field")
    check(float(meta["dterror"]) <= 1e-14, str(path) + " signed step guard")
    return root, meta, ordered_arrays, hist


def history_exact(ha, hb):
    if ha is None or hb is None:
        return ha is None and hb is None
    a, b = ha["arrays"], hb["arrays"]
    ia, ib = np.argsort(a["Idp"]), np.argsort(b["Idp"])
    return ({k: v for k, v in ha["values"].items() if k != "RunCode"} ==
            {k: v for k, v in hb["values"].items() if k != "RunCode"} and
            a.keys() == b.keys() and all(a[k].dtype == b[k].dtype and a[k].shape == b[k].shape and a[k][ia].tobytes() == b[k][ib].tobytes() for k in a))


def exact(path_a, path_b):
    ra, ma, a, ha = ordered(path_a)
    rb, mb, b, hb = ordered(path_b)
    check(all(ma[k].tobytes() == mb[k].tobytes() for k in
              ("Step", "Cpart", "TimeStep", "SymplecticDtPre", "dterror")), "Clock " + str(path_b))
    check(a.keys() == b.keys(), "Different field sets")
    for name in a:
        check(a[name].shape == b[name].shape and a[name].dtype == b[name].dtype and a[name].tobytes() == b[name].tobytes(),
              f"{path_b} changed {name}")
    check(history_exact(ha, hb), str(path_b) + " changed TPI history")


def assess(case, tag, backend, label):
    folder = run_path(case, tag, backend, label)
    file_list = frames(folder)
    _, model, ck, steps = SPECS[label]
    cfg = ET.parse(next((folder / "seed").glob("*.xml")))
    hydro = cfg.find("./execution/special/hydromechanics")
    param = lambda key: float(np.float32(hydro.find(key).get("value")))
    k0, n0 = param("HydraulicConductivity"), param("Porosity")
    previous = -1.
    kspread = nspread = pk_spread = interior_k_span = 0.
    drained = 0
    interior_joint_pairs = 0
    for i, file in enumerate(file_list):
        root, m, a, h = ordered(file)
        time = float(m["TimeStep"])
        check(time > previous and (h is not None) == bool(model == 2 and i), str(file) + " history/time")
        if h is not None:
            history = h["values"]
            check(history["Scheme"] == "P3_B_alpha_half_beta_zero" and history["Valid"] == 1 and
                  history["CompletedUpdates"] == int(m["Step"]) + 1 and history["RunCode"] == root["RunCode"] and
                  history["PreviousTime"] + history["Dt"] == history["SavedTime"] == time, "TPI history binding")
        cut = int(root["CaseNfixed"])
        j, n, kval, pressure = (a[k][cut:] for k in ("PoroVolumeRatio", "PoroPorosity", "PoroHydraulicConductivity", "PorePress"))
        if i == 0:
            initial_p0 = a["PorePress0"].copy()
        check(np.array_equal(a["PorePress0"].view("u4"), initial_p0.view("u4")) and
              np.array_equal((pressure - initial_p0[cut:]).view("u4"), a["ExcessPorePress"][cut:].view("u4")),
              str(file) + " fixed P0/excess")
        rhow = param("PoreWaterRho")
        expect_rho = rhow + (float(root["Rhop0"]) - rhow) / j
        expect_volume = float(np.float32(root["MassFluid"])) / float(root["Rhop0"]) * j
        check(np.allclose(a["PoroMixtureDensity"][cut:], expect_rho, rtol=1e-14, atol=0) and
              np.array_equal(expect_rho.astype("f4"), a["Rhop"][cut:]) and
              np.allclose(a["PoroCurrentVolume"][cut:], expect_volume, rtol=1e-14, atol=0),
              str(file) + " saturated mass/volume ledger")
        expect_n = 1. - (1. - n0) / j
        expect_k = k0 * np.exp((j - 1.) / ((1. - n0) * ck)) if ck is not None else np.full(len(j), k0)
        check((j > 1. - n0).all() and (kval > 0).all() and np.max(abs(n - expect_n)) < 2e-14 and
              np.max(abs(kval - expect_k)) < 2e-14 * k0, str(file) + " n,k ledger")
        smooth = ~np.isin(a["FSType"][cut:], (2, 3))
        if ck == .5:
            if i == 0:
                dp = float(root["Dp"])
                # Body-fitted sphere and Cartesian column both use true initial Euclidean distances.
                from scipy.spatial import cKDTree
                edges = cKDTree(a["Posd"][cut:]).query_pairs(1.1 * dp, output_type="ndarray")
            left, right = edges.T
            joint = (smooth[left] & smooth[right] &
                     (abs(kval[left] - kval[right]) > k0 * 1e-12) &
                     (abs(pressure[left] - pressure[right]) > 1e-3))
            interior_joint_pairs = max(interior_joint_pairs, int(joint.sum()))
        kspread = max(kspread, float(np.ptp(kval)) / k0)
        interior_k_span = max(interior_k_span, float(np.ptp(kval[smooth])) / k0)
        nspread = max(nspread, float(np.ptp(n)))
        pk_spread = max(pk_spread, float(np.ptp(pressure)))
        if case == TESTS and time > float(cfg.find("./execution/special/drainage").get("start")) + 1e-12:
            check((~smooth).sum() == 10 and np.all(pressure[~smooth] == 0.), "Post-open drainage " + str(file))
            drained += 1
        previous = time
    check(file_list and int(m["Step"]) + 1 == steps, f"Incomplete window {label}")
    if ck == .5:
        check(interior_k_span > 1e-10 and pk_spread > 0.1 and interior_joint_pairs > 0, f"Insufficient changing interior k or pressure in {label}")
    if case == TESTS and steps == 2004:
        check(drained > 0, "No open drainage frames")
    check(len(file_list) > 1, label)
    return dict(saved=len(file_list), steps=steps, final_time_s=time, max_spatial_k_span_over_k0=kspread,
                max_interior_k_span_over_k0=interior_k_span, max_n_span=nspread, joint_k_p_interior_neighbor_pairs=interior_joint_pairs,
                max_p_span_Pa=pk_spread, drained_output_frames=drained)


def compare_folders(first, second, enforce):
    left, right = frames(first), frames(second)
    check(len(left) == len(right), "Different output cadence")
    rows = []
    for x, y in zip(left, right):
        root, ma, a, _ = ordered(x)
        rb, mb, b, _ = ordered(y)
        check(all(ma[k] == mb[k] for k in ("TimeStep", "Step", "Cpart")), "Nonmatching actual step/clock")
        check(a.keys() == b.keys() and all(a[k].shape == b[k].shape and a[k].dtype == b[k].dtype for k in a)
              and root["CaseNfixed"] == rb["CaseNfixed"], "Schema mismatch")
        start = int(root["CaseNfixed"])
        delta = a["PorePress"][start:].astype(float) - b["PorePress"][start:]
        position_delta = a["Posd"][start:] - b["Posd"][start:]
        rows.append((float(np.sqrt(np.mean(delta**2))), float(np.linalg.norm(position_delta, axis=1).max()*1000)))
    pm, um = np.max(rows, axis=0)
    if enforce:
        check(pm <= 5 and um <= .005, f"Cross-backend bound: {pm} Pa, {um} mm")
    return dict(matched_frames=len(rows), max_pressure_RMS_Pa=pm, max_displacement_mm=um,
                end_pressure_RMS_Pa=rows[-1][0], end_displacement_mm=rows[-1][1])


def save_clocks(tag):
    # C02 constant/variable TPI and explicit u-pl use this common actual clock on both backends.
    out = TESTS / "logs" / f"{tag}.clocks.csv"
    files = frames(run_path(TESTS, tag, "cpu", "column_var"))
    check(len(files) == 131, "C02 matched history coverage")
    with out.open("x", newline="", encoding="utf8") as stream:
        writer = csv.writer(stream)
        writer.writerow(("part", "native_step", "completed_updates", "actual_time_s"))
        for i, path in enumerate(files):
            _, m, _, _ = read_with_history(path)
            check(m["Cpart"] == i, "C02 saved clock index")
            writer.writerow((i, int(m["Step"]), int(m["Step"]) + int(i > 0), repr(float(m["TimeStep"]))))


def review(tag):
    results, cross, options = {}, {}, {}
    for label, (case, model, ck, _) in SPECS.items():
        results[label] = {}
        for backend in ("cpu", "gpu"):
            folder = run_path(case, tag, backend, label)
            entry = assess(case, tag, backend, label)
            if label in ("column_archive", "column_lim", "sphere_const"):
                reference = old(case, backend) if ck is None else run_path(case, tag, backend, "column_archive")
                sources, fresh = frames(reference), frames(folder)
                # The GPU archive continues to 1002 updates; the new archived regression ends at 25.
                if label == "column_archive" and backend == "gpu":
                    check(len(sources) == 106 and len(fresh) == 3, "GPU25 archive coverage")
                    sources = sources[:3]
                check(len(sources) == len(fresh) and [x.name for x in sources] == [x.name for x in fresh],
                      "Incomplete comparison coverage")
                pairs = list(zip(sources, fresh))
                for oldf, newf in pairs:
                    exact(oldf, newf)
                entry["bit_exact_controls"] = len(pairs)
            results[label][backend] = entry
        cross[label] = compare_folders(run_path(case, tag, "cpu", label), run_path(case, tag, "gpu", label), True)
    for b in ("cpu", "gpu"):
        for ref in ("column_const", "column_exp"):
            data = compare_folders(run_path(TESTS, tag, b, "column_var"), run_path(TESTS, tag, b, ref), False)
            check(data["max_pressure_RMS_Pa"] > 0., "No variable-k/model effect under load")
            options[f"{b}_varTpi_vs_{ref}"] = data
    save_clocks(tag)
    write(TESTS / "logs" / f"{tag}.check.json", dict(passed=True, outcomes=results, backend=cross, options=options,
          column_clock_file=f"{tag}.clocks.csv", archived_constant_control_updates={"C02": 25, "C04": 4},
          comparison_scope="Cross-backend p/u budgets apply only within a model. Explicit finite-Kw versus TPI zero-storage and constant versus evolving k are descriptive."))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tag", default="tpi_variable_k_r1")
    p.add_argument("--backend", choices=("cpu", "gpu"))
    p.add_argument("--exe", type=Path)
    p.add_argument("--label", choices=SPECS, action="append")
    p.add_argument("--review", action="store_true")
    args = p.parse_args()
    check(args.tag.isidentifier(), "Use a simple test tag")
    if args.review:
        review(args.tag)
    else:
        check(args.backend and args.exe, "Provide backend and executable")
        for name in args.label or SPECS:
            run_one(args.exe.resolve(strict=True), args.tag, args.backend, name)
