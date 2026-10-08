"""Native BI4 comparison for the formal k=1e-4, 2Tv double-state case.

Called by the formal BAT after successful completion. No solver is launched.
  py -3 support/compare_double_q0.py --preflight
  py -3 support/compare_double_q0.py --generated
  py -3 support/compare_double_q0.py
  py -3 support/compare_double_q0.py --selfcheck

Chart contract: two static line/small-multiple figures compare 402 actual saved
times and 100 fixed initial soil layers. The question is whether replacing the
high/low state changes pressure and settlement; no improvement is assumed.
Old blue solid/open circles, new orange dashed/crosses, neutral gray classical
reference. All times and IDs must match; no interpolation or VTK float pressure.
Selfcheck compares the SAME baseline twice and is not a migration experiment.
Final PNG/PDF/CSV/JSON/Markdown files are exclusive-create, never overwritten.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import run_double_q0 as guard

CASE, BASELINE, CURRENT, PREFIX = guard.CASE, guard.BASELINE, guard.CURRENT, guard.PREFIX
LOG = CASE / "tests/logs/pore_double_2tv"
READER = CASE / "tests/outputs/pore_double_vel0/reader/export_state.exe"
READER_BUILD = CASE / "tests/logs/pore_double_vel0/reader.build.json"
NATIVE_BASELINE = CASE / "tests/outputs/pore_double_2tv/baseline_native"
TIME_TOL = 1e-9
FRAME_COUNT, PARTICLE_COUNT, SOIL_COUNT, STEP_COUNT = 402, 1040, 1000, 7288429
TOP_IDS = np.arange(139, 1040, 100)
SOIL_IDS = np.arange(40, 1040)
COLORS = ("#3274A1", "#E1812C")
GRAY = "#777777"
COLUMNS = ("part,id,time_s,x_m,y_m,z_m,pressure_pa,reference_pa,stored_pressure_pa,"
           "residual_pa,velx_m_s,vely_m_s,velz_m_s,rhop_kg_m3,sigma_xx_pa,"
           "sigma_yy_pa,sigma_zz_pa,sigma_xy_pa,sigma_yz_pa,sigma_xz_pa,fstype").split(",")
COL = {name: index for index, name in enumerate(COLUMNS)}
SUFFIXES = ("history.png", "history.pdf", "profiles.png", "profiles.pdf", "history.csv",
            "profiles.csv", "comparison.json", "comparison.md")
CAVEATS = [
    "This is a representation-migration comparison, not proof of greater physical accuracy.",
    "Classical Terzaghi is a small-strain, ideal instantaneous-load physical reference; "
    "the numerical case has finite Kw, a 0.01 s load/drainage transition and moving particles. "
    "It is not an exact reference for this discrete SPH problem.",
    "Prior strict short-run pressure screening (0.01 Pa RMS / 0.1 Pa maximum) was not fully "
    "passed. A completed 2Tv run or a visually overlapping curve does not waive that gate.",
    "Historical and current executable builds differ; recorded core-source provenance is "
    "checked at launch, but this historical comparison is not a controlled timing benchmark.",
    "The saved initial positions may be float3. Fixed initial IDs and their common saved "
    "origin are used for settlement; every frame's native position type is recorded.",
    "Arithmetic particle mean uses the same 1000 soil IDs at every frame; it is not a "
    "current-volume-weighted continuum average. U=1-mean(excess)/q0 is reported only after drainage starts.",
    "Profiles use the same fixed initial-layer ID sets and z0/H, not changing current-z bins. "
    "Requested Tv values select the nearest shared saved frame; neither time nor pressure is interpolated.",
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return guard.sha(Path(path))


def new_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def new_csv(path, rows):
    require(bool(rows), f"No rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: ("" if isinstance(value, float) and not math.isfinite(value) else value)
                             for key, value in row.items()})


def file_record(path):
    return dict(path=str(Path(path).resolve()), bytes=Path(path).stat().st_size, sha256=sha(path))


def verify_reader():
    require(READER.is_file() and READER_BUILD.is_file(), "Validated native reader or build record is missing")
    record = json.loads(READER_BUILD.read_text(encoding="utf-8-sig"))
    require(Path(record["executable"]).resolve() == READER.resolve(), "Reader build record points elsewhere")
    require(sha(READER) == record["executable_sha256"].upper(), "Native reader SHA differs from its verified build")
    return dict(executable=file_record(READER), build_record=file_record(READER_BUILD))


def inventory(data):
    parts = sorted(p for p in data.iterdir() if re.fullmatch(r"Part(?:_p\d+)?_\d+\.bi4", p.name))
    require(parts, f"No native PART files: {data}")
    files = parts + [data / "Part_Head.ibi4"]
    require(all(p.is_file() for p in files), "Native PART header is missing")
    return [file_record(p) for p in files]


def export_native(run, output, reader_record):
    """Cache is trusted only when source, reader and exported CSV hashes agree."""
    source = inventory(run / "data")
    record_path = output / "export_provenance.json"
    if output.exists():
        require(record_path.is_file() and (output / "complete.txt").is_file(),
                f"Incomplete/unattributed native cache; not overwriting it: {output}")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        require(record["source_files"] == source and record["reader"] == reader_record,
                f"Native cache source/reader mismatch: {output}")
        for item in record["exported_files"]:
            require(file_record(item["path"]) == item, f"Native CSV changed: {item['path']}")
        return record
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [str(READER), "--dir", str(run / "data"), "--out", str(output)]
    print(f"Export native state: {run.name}", flush=True)
    result = subprocess.run(command, capture_output=True, text=True, errors="replace")
    # The exporter exclusively creates its directory; retain its log even on failure.
    if output.exists():
        with (output / "reader.log").open("x", encoding="utf-8") as stream:
            stream.write(result.stdout + result.stderr)
    require(result.returncode == 0 and (output / "complete.txt").is_file(),
            f"Native export failed ({result.returncode}): {result.stderr}")
    require(inventory(run / "data") == source, "Native input changed during export")
    record = dict(source_files=source, reader=reader_record, command=command,
                  exported_files=[file_record(output / name) for name in ("frames.csv", "state.csv", "complete.txt")])
    new_json(record_path, record)
    return record


def log_number(text, key):
    match = re.search(r"^\s*" + re.escape(key) + r"\s*[.:=]+\s*([+\-\d.eE]+)", text, re.M)
    require(match is not None, f"Missing completion field: {key}")
    return float(match.group(1))


def model_and_completion(run):
    text = (run / "Run.out").read_text(encoding="utf-8-sig", errors="strict")
    require("Finished execution (code=0)." in text and not re.search(r"Finished execution \(code=[1-9]", text),
            f"Run not successfully completed: {run}")
    for key, expected in (("Excluded particles", 0), ("DTs adjusted to DtMin", 0),
                          ("Steps of simulation", STEP_COUNT), ("PART files", FRAME_COUNT)):
        require(log_number(text, key) == expected, f"{run.name}: unexpected {key}")
    xml = run / (run.name[:-4] + ".xml")
    tree = ET.parse(xml)
    def value(path):
        element = tree.find(path)
        require(element is not None and "value" in element.attrib, f"Missing XML value: {path}")
        result = float(element.get("value"))
        require(math.isfinite(result), f"Nonfinite XML value: {path}")
        return result
    special = "./execution/special/"
    hydro = special + "hydromechanics/"
    model = {name: value(path) for name, path in {
        "E": special + "soils/ModulusE", "nu": special + "soils/PRvs",
        "k": hydro + "HydraulicConductivity", "n": hydro + "Porosity",
        "Kw": hydro + "PoreWaterBulkModulus", "rho_w": hydro + "PoreWaterRho",
        "q0": hydro + "HydroMechTopLoadQ0", "tL": hydro + "HydroMechTopLoadRampTime",
        "tD": hydro + "HydroMechDrainageStartTime",
        "H": "./execution/uservars/varnum[@name='sizefz']", "dp": "./execution/constants/dp",
        "dt": "./execution/parameters/parameter[@key='DtFixed']",
        "dt_ini": "./execution/parameters/parameter[@key='DtIni']",
        "time_max": "./execution/parameters/parameter[@key='TimeMax']",
        "time_out": "./execution/parameters/parameter[@key='TimeOut']",
    }.items()}
    for name, expected in {"k": 1e-4, "H": 1, "dp": .01, "q0": 1e4, "tD": .01,
                           "tL": .01, "dt": 1e-5, "dt_ini": 1e-6,
                           "time_max": 72.8842857142858}.items():
        require(model[name] == expected, f"Unexpected formal {name}: {model[name]}")
    gravity = tree.find("./execution/constants/gravity")
    require(gravity is not None and all(float(gravity.get(axis)) == 0 for axis in "xyz"),
            "Reference assumes the formal zero-gravity external-load case")
    require(0 < model["nu"] < .5 and model["E"] > 0 and model["rho_w"] > 0, "Invalid elastic/water constants")
    model["g_ref"] = 9.81
    model["M"] = model["E"] * (1 - model["nu"]) / ((1 + model["nu"]) * (1 - 2 * model["nu"]))
    model["cv"] = model["k"] * model["M"] / (model["rho_w"] * model["g_ref"])
    return model, dict(folder=str(run), xml=file_record(xml), run_log=file_record(run / "Run.out"),
                       runtime_s=log_number(text, "Simulation Runtime"), steps=STEP_COUNT,
                       excluded_particles=0, adjusted_to_dtmin=0)


def validate_rows(data, frame_times, expected_particles=PARTICLE_COUNT):
    require(data.shape == (len(frame_times), expected_particles, len(COLUMNS)), "Native state shape differs")
    require(np.isfinite(data).all(), "Non-finite/missing native state values")
    require(np.array_equal(data[:, :, COL["id"]], np.broadcast_to(np.arange(expected_particles), data.shape[:2])),
            "Missing/duplicate/unexpected particle IDs (must be complete ordered IDs)")
    require(np.array_equal(data[:, :, COL["part"]], np.broadcast_to(np.arange(len(frame_times))[:, None], data.shape[:2])),
            "Native PART indices differ between state and frame metadata")
    require(np.array_equal(data[:, :, COL["time_s"]], np.broadcast_to(frame_times[:, None], data.shape[:2])),
            "Native row time differs from frame metadata")
    require(np.array_equal(data[:, :, COL["pressure_pa"]],
                           data[:, :, COL["stored_pressure_pa"]] + data[:, :, COL["residual_pa"]]),
            "Native pressure is not the exact stored high plus residual reconstruction")
    require(np.all(data[:, :, COL["rhop_kg_m3"]] > 0), "Nonpositive particle density")


def read_native(path, kind):
    with (path / "frames.csv").open(encoding="utf-8", newline="") as stream:
        frames = list(csv.DictReader(stream))
    require(len(frames) == FRAME_COUNT, f"Expected {FRAME_COUNT} native frames: {path}")
    times = np.array([float(row["time_s"]) for row in frames])
    require(np.isfinite(times).all() and times[0] == 0 and np.all(np.diff(times) > 0), "Native times invalid/nonincreasing")
    for index, row in enumerate(frames):
        require(int(row["part"]) == index and int(row["particle_count"]) == PARTICLE_COUNT,
                f"Native frame indices/counts differ at {path}: {index}")
        require([int(row[name]) for name in ("case_nfixed", "case_nmoving", "case_nfloat", "case_nfluid")]
                == [40, 0, 0, SOIL_COUNT], "Native case particle header differs")
        schema = tuple(row[name] for name in ("pressure_type", "reference_type", "residual_type"))
        expected = ("float", "float", "float") if kind == "high_low" else ("double", "double", "absent")
        require(schema == expected, f"Unexpected {kind} pressure schema at PART {index}: {schema}")
        require(row["pos_type"] in ("float3", "double3"), "Unsupported native position type")
    with (path / "state.csv").open(encoding="utf-8") as stream:
        require(stream.readline().strip().split(",") == COLUMNS, "Native state column schema changed")
        raw = np.loadtxt(stream, delimiter=",", dtype=np.float64, ndmin=2)
    require(raw.shape == (FRAME_COUNT * PARTICLE_COUNT, len(COLUMNS)), "Native state row count differs")
    data = raw.reshape(FRAME_COUNT, PARTICLE_COUNT, len(COLUMNS))
    validate_rows(data, times)
    if kind == "double":
        require(np.count_nonzero(data[:, :, COL["residual_pa"]]) == 0, "Double state has a nonzero residual")
    return dict(times=times, data=data, frames=frames, native=str(path))


def degree_theory(tv):
    tv = np.asarray(tv, dtype=np.float64)
    odd = np.arange(1, 480, 2, dtype=np.float64)
    result = 1 - np.sum(8 / (math.pi ** 2 * odd[:, None] ** 2)
                        * np.exp(-math.pi ** 2 * odd[:, None] ** 2 * tv[None, :] / 4), axis=0)
    result[tv == 0] = 0
    return result


def pressure_theory(z, tv, model):
    z = np.asarray(z, dtype=np.float64)
    indices = np.arange(240)
    modes = (2 * indices + 1) * math.pi / 2
    return model["q0"] * np.sum((2 * (-1.) ** indices / modes * np.exp(-modes ** 2 * tv))[:, None]
                                 * np.cos(modes[:, None] * z[None, :] / model["H"]), axis=0)


def pair_checks(old, new, model):
    require(np.max(np.abs(old["times"] - new["times"])) <= TIME_TOL,
            "Actual native saved times differ by more than 1e-9 s; no interpolation is allowed")
    a, b = old["data"], new["data"]
    require(np.array_equal(a[:, :, COL["reference_pa"]], b[:, :, COL["reference_pa"]]),
            "Pore-pressure references differ; cannot compare excess pressures")
    require(np.array_equal(np.broadcast_to(a[0, :, COL["reference_pa"]], a.shape[:2]), a[:, :, COL["reference_pa"]]),
            "Reference pressure changed during the baseline run")
    physical_columns = list(range(3,8)) + list(range(10,len(COLUMNS)))
    require(np.array_equal(a[0][:, physical_columns], b[0][:, physical_columns]),
            "Initial positions/pressures/references/velocity/stress/density/FSType differ by ID")
    initial = a[0, SOIL_IDS, COL["z_m"]]
    layer_z, layer_id = np.unique(initial, return_inverse=True)
    require(len(layer_z) == 100 and np.array_equal(np.bincount(layer_id), np.full(100, 10)),
            "Formal soil IDs are not 100 initial layers with 10 particles per layer")
    require(np.array_equal(SOIL_IDS[layer_id == 99], TOP_IDS), "Fixed initial top IDs differ")
    require(new["times"][-1] >= model["time_max"] and new["times"][-1] <= model["time_max"] + model["dt"] + TIME_TOL,
            "Native final time did not reach TimeMax within one fixed step")
    return layer_z, layer_id


def analyze(old, new, model):
    layer_z, layer_id = pair_checks(old, new, model)
    a, b = old["data"], new["data"]
    times = old["times"]
    tv = model["cv"] * np.maximum(0, times - model["tD"]) / model["H"] ** 2
    drained = times >= model["tD"]
    u_theory = degree_theory(tv)
    u_theory[~drained] = np.nan
    excess_a = a[:, SOIL_IDS, COL["pressure_pa"]] - a[:, SOIL_IDS, COL["reference_pa"]]
    excess_b = b[:, SOIL_IDS, COL["pressure_pa"]] - b[:, SOIL_IDS, COL["reference_pa"]]
    mean_a, mean_b = excess_a.mean(axis=1), excess_b.mean(axis=1)
    initial_top = a[0, TOP_IDS, COL["z_m"]]
    settle_a = (initial_top[None, :] - a[:, TOP_IDS, COL["z_m"]]).mean(axis=1) * 1000
    settle_b = (initial_top[None, :] - b[:, TOP_IDS, COL["z_m"]]).mean(axis=1) * 1000
    delta = excess_b - excess_a
    history = []
    for part in range(FRAME_COUNT):
        row = dict(part=part, time_old_s=float(times[part]), time_new_s=float(new["times"][part]),
                   time_difference_s=float(new["times"][part]-times[part]), tv=float(tv[part]), n_soil=SOIL_COUNT,
                   old_mean_excess_pa=float(mean_a[part]), new_mean_excess_pa=float(mean_b[part]),
                   mean_difference_pa=float(mean_b[part]-mean_a[part]),
                   old_u=float(1-mean_a[part]/model["q0"]) if drained[part] else math.nan,
                   new_u=float(1-mean_b[part]/model["q0"]) if drained[part] else math.nan,
                   old_settlement_mm=float(settle_a[part]), new_settlement_mm=float(settle_b[part]),
                   settlement_difference_mm=float(settle_b[part]-settle_a[part]),
                   particle_difference_rms_pa=float(np.sqrt(np.mean(delta[part] ** 2))),
                   particle_difference_max_pa=float(np.max(np.abs(delta[part]))),
                   classical_mean_excess_pa=float(model["q0"]*(1-u_theory[part])),
                   classical_u=float(u_theory[part]),
                   classical_settlement_mm=float(model["q0"]*model["H"]/model["M"]*u_theory[part]*1000))
        history.append(row)
    profiles, selected = [], []
    for target in (.5, 1., 2.):
        part = int(np.argmin(abs(tv-target)))
        target_record = dict(requested_tv=target, part=part, actual_tv=float(tv[part]),
                             old_time_s=float(times[part]), new_time_s=float(new["times"][part]))
        selected.append(target_record)
        classical = pressure_theory(layer_z, tv[part], model)
        for layer in range(100):
            mask = layer_id == layer
            rows = SOIL_IDS[mask]
            profiles.append(dict(**target_record, initial_layer=layer, z0_m=float(layer_z[layer]),
                                 z0_over_h=float(layer_z[layer]/model["H"]), n_particles=int(mask.sum()),
                                 particle_ids=" ".join(map(str, rows)),
                                 old_current_z_mean_m=float(a[part, rows, COL["z_m"]].mean()),
                                 new_current_z_mean_m=float(b[part, rows, COL["z_m"]].mean()),
                                 old_excess_pa=float(excess_a[part, mask].mean()),
                                 new_excess_pa=float(excess_b[part, mask].mean()),
                                 difference_pa=float(delta[part, mask].mean()),
                                 classical_excess_pa=float(classical[layer])))
    window_metrics = {}
    for label, mask in (("all_saved_times", np.ones(FRAME_COUNT, dtype=bool)), ("tv_ge_1", tv >= 1)):
        require(np.any(mask), f"No frames in {label}")
        window_metrics[label] = dict(frames=int(mask.sum()),
            max_abs_mean_difference_pa=float(np.max(np.abs(mean_b[mask]-mean_a[mask]))),
            particle_difference_rms_pa=float(np.sqrt(np.mean(delta[mask]**2))),
            max_abs_particle_difference_pa=float(np.max(np.abs(delta[mask]))),
            max_abs_settlement_difference_mm=float(np.max(np.abs(settle_b[mask]-settle_a[mask]))))
    spot_part = FRAME_COUNT - 1
    # Independent scalar fsum path checks the principal reported aggregates.
    scalar_old = math.fsum(float(x) for x in excess_a[spot_part]) / SOIL_COUNT
    scalar_new = math.fsum(float(x) for x in excess_b[spot_part]) / SOIL_COUNT
    scalar_settle = math.fsum(float(initial_top[i]-b[spot_part, pid, COL["z_m"]]) for i,pid in enumerate(TOP_IDS)) / len(TOP_IDS)*1000
    require(abs(scalar_old-mean_a[-1]) < 1e-9 and abs(scalar_new-mean_b[-1]) < 1e-9,
            "Independent mean-pressure check failed")
    require(abs(scalar_settle-settle_b[-1]) < 1e-11, "Independent fixed-top settlement check failed")
    return history, profiles, dict(windows=window_metrics, selected_profiles=selected,
        last_frame=history[-1], fixed_top_ids=TOP_IDS.tolist(), soil_ids=[40,1039],
        initial_layer_particle_counts=[10]*100,
        max_actual_time_mismatch_s=float(np.max(abs(times-new["times"]))),
        initial_position_pressure_reference_equal=True, all_reference_values_equal=True,
        scalar_final_mean_old_pa=scalar_old, scalar_final_mean_new_pa=scalar_new,
        scalar_final_settlement_new_mm=scalar_settle)


def draw_figures(history, profiles, model, prefix, selfcheck):
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10, "axes.titlesize":11,
                         "axes.labelsize":10, "figure.facecolor":"white", "axes.facecolor":"white",
                         "text.color":"#262626", "axes.labelcolor":"#262626", "axes.spines.top":False,
                         "axes.spines.right":False, "grid.color":"#E5E5E5", "grid.linewidth":.6})
    labels = ("Same baseline A (high + residual)", "Same baseline B (high + residual)") if selfcheck else (
        "Baseline (float high + residual)", "Current (double state)")
    x = np.array([r["tv"] for r in history])
    def series(ax, key_a, key_b, theory, factor=1, late=False):
        mask = x >= 1 if late else np.ones(len(x), dtype=bool)
        for index, key in enumerate((key_a, key_b)):
            y = np.array([r[key] for r in history])*factor
            ax.plot(x[mask], y[mask], color=COLORS[index], ls=("-", "--")[index], lw=1.6,
                    marker=("o", "x")[index], markersize=3.4, markevery=max(1,int(mask.sum()/14)),
                    markerfacecolor="none", label=labels[index])
        if theory:
            y = np.array([r[theory] for r in history])*factor
            ax.plot(x[mask], y[mask], color=GRAY, ls=":", lw=1.6, label="Classical Terzaghi reference")
        ax.grid(True)
        ax.set_xlabel(r"$T_v=c_v(t-t_D)/H^2$ (saved times; no interpolation)")
    fig, axes = plt.subplots(2,2,figsize=(13.6,9.5))
    series(axes[0,0],"old_mean_excess_pa","new_mean_excess_pa","classical_mean_excess_pa",.001)
    axes[0,0].set(title="Mean excess pore pressure", ylabel="Soil-particle mean excess pressure (kPa)")
    series(axes[0,1],"old_mean_excess_pa","new_mean_excess_pa","classical_mean_excess_pa",.001,True)
    axes[0,1].set(title=r"Late mean excess pressure ($T_v\geq1$; focused view)", ylabel="Soil-particle mean excess pressure (kPa)")
    series(axes[1,0],"old_u","new_u","classical_u")
    axes[1,0].set(title="Pressure-based consolidation degree", ylabel=r"$U=1-\overline{p-p_0}/q_0$")
    series(axes[1,1],"old_settlement_mm","new_settlement_mm","classical_settlement_mm")
    axes[1,1].set(title="Settlement of fixed initial top IDs", ylabel="Mean downward displacement (mm)")
    # A future negative pressure/U/settlement is evidence, not a plotting error.
    for ax in (axes[0,0],axes[1,0],axes[1,1]):
        finite_values = np.concatenate([line.get_ydata()[np.isfinite(line.get_ydata())] for line in ax.lines])
        if np.all(finite_values >= 0): ax.set_ylim(bottom=0)
    title = "Tool self-check: the same completed baseline compared twice" if selfcheck else "2Tv consolidation: high/low and double pore-pressure states"
    fig.suptitle(title, x=.07, ha="left", y=.982, fontsize=15)
    fig.text(.07,.944,r"$k=10^{-4}$ m/s | 1000 fixed soil IDs | 402 native BI4 frames | fixed initial top: 10 IDs",fontsize=10)
    handles, names = axes[0,0].get_legend_handles_labels()
    fig.legend(handles,names,loc="upper left",bbox_to_anchor=(.062,.928),ncol=3,frameon=False,fontsize=9)
    note = "SELF-CHECK ONLY: overlapping curves are expected; this is not evidence of a migration improvement.\n" if selfcheck else "This full-run comparison does not waive the previously unpassed strict short-run pressure gates.\n"
    pressure_note = "Pressure: the same high + residual baseline twice." if selfcheck else "Pressure: old high + residual versus native double."
    fig.text(.07,.018,note+"Gray: ideal small-strain Terzaghi physical reference, not an exact solution of the finite-Kw moving-particle SPH case.\n"
             +pressure_note+" Settlement uses the common saved initial origin; layer IDs never change.",fontsize=9,color="#4D4D4D")
    fig.subplots_adjust(left=.075,right=.98,top=.84,bottom=.135,wspace=.28,hspace=.34)
    save_figure(fig,prefix,"history")
    fig, axes = plt.subplots(1,3,figsize=(13.6,6.3),sharey=True)
    for ax,target in zip(axes,(.5,1.,2.)):
        rows = [r for r in profiles if r["requested_tv"] == target]
        z = np.array([r["z0_over_h"] for r in rows])
        for index,key in enumerate(("old_excess_pa","new_excess_pa")):
            ax.plot(np.array([r[key] for r in rows])/model["q0"],z,color=COLORS[index],
                    ls=("-","--")[index],lw=1.6,marker=("o","x")[index],markersize=3.4,
                    markevery=8,markerfacecolor="none",label=labels[index])
        ax.plot(np.array([r["classical_excess_pa"] for r in rows])/model["q0"],z,color=GRAY,ls=":",lw=1.6,
                label="Classical Terzaghi reference")
        ax.set_title(f"Requested Tv={target:g}; saved Tv={rows[0]['actual_tv']:.6f}\n"
                     f"PART {rows[0]['part']}; t={rows[0]['old_time_s']:.8f} s",fontsize=10)
        ax.set_xlabel(r"Layer mean excess pressure / $q_0$")
        ax.grid(True)
        ax.set_ylim(0,1)
        finite_values = np.concatenate([line.get_xdata()[np.isfinite(line.get_xdata())] for line in ax.lines])
        if np.all(finite_values >= 0): ax.set_xlim(left=0)
    axes[0].set_ylabel(r"Fixed initial layer coordinate $z_0/H$ (bottom 0, drained top 1)")
    fig.suptitle("Tool self-check: fixed initial-layer pore-pressure profiles" if selfcheck else
                 "Pore-pressure profiles on the same fixed initial layers",x=.07,ha="left",y=.98,fontsize=15)
    fig.text(.07,.925,"100 initial layers, 10 identical particle IDs per layer | actual saved times; no interpolation",fontsize=10)
    handles,names=axes[0].get_legend_handles_labels()
    fig.legend(handles,names,loc="upper left",bbox_to_anchor=(.062,.906),ncol=3,frameon=False,fontsize=9)
    fig.text(.07,.025,("SELF-CHECK ONLY: both numerical series are the same baseline.\n" if selfcheck else
                      "No improvement claim is implied by this representation comparison.\n")+
             "Each panel uses its own pressure-axis scale. Gray is a classical physical reference at the actual saved Tv and initial z0.\n"
             "Profiles are Lagrangian initial-layer averages, not current-z bins; current layer heights are retained in the accompanying CSV.",
             fontsize=9,color="#4D4D4D")
    fig.subplots_adjust(left=.075,right=.985,top=.77,bottom=.18,wspace=.25)
    save_figure(fig,prefix,"profiles")


def save_figure(fig, prefix, stem):
    for extension in ("png","pdf"):
        target = Path(str(prefix)+"_"+stem+"."+extension)
        # Passing the exclusively opened stream also protects against a race.
        with target.open("xb") as stream:
            fig.savefig(stream,format=extension,dpi=180)
    plt.close(fig)


def guard_selftests():
    """Small in-memory negative fixtures; no production or saved data is altered."""
    fixture=np.zeros((2,2,len(COLUMNS)),dtype=np.float64)
    fixture[:,:,COL["id"]]=[0,1]
    fixture[:,:,COL["part"]]=[[0],[1]]
    fixture[:,:,COL["time_s"]]=[[0],[1]]
    fixture[:,:,COL["rhop_kg_m3"]]=2100
    validate_rows(fixture,np.array([0.,1.]),2)
    passed=[]
    for name,field,value in (("duplicate_id","id",0), ("nonfinite_pressure","pressure_pa",math.nan),
                             ("wrong_row_time","time_s",2), ("wrong_part_index","part",3),
                             ("wrong_reconstruction","pressure_pa",1), ("nonpositive_density","rhop_kg_m3",0)):
        bad=fixture.copy()
        bad[1,1,COL[field]]=value
        try:
            validate_rows(bad,np.array([0.,1.]),2)
        except ValueError:
            passed.append(name)
        else:
            raise AssertionError(f"Negative fixture was accepted: {name}")
    return passed


def prior_screening():
    path=CASE/"tests/logs/pore_double_vel0/analysis.json"
    require(path.is_file(), "Prior short-run screening record is missing; cannot silently omit it")
    record=json.loads(path.read_text(encoding="utf-8-sig"))
    found=[]
    def walk(item):
        if isinstance(item,dict):
            if "previous_pressure_screening_pass" in item:
                found.append(dict(label=item.get("label"),passed=item["previous_pressure_screening_pass"]))
            for value in item.values(): walk(value)
        elif isinstance(item,list):
            for value in item: walk(value)
    walk(record)
    require(found and any(not x["passed"] for x in found), "Prior strict-gate evidence changed; review comparison caveats")
    return dict(source=file_record(path), recorded_checks=found, fully_passed=False,
                threshold_rms_pa=.01,threshold_max_pa=.1)


def write_report(path, report, selfcheck):
    final=report["metrics"]["last_frame"]
    metrics=report["metrics"]["windows"]["all_saved_times"]
    title="Same-baseline tool self-check (not a migration result)" if selfcheck else "Formal 2Tv high/low versus double-state comparison"
    lines=[f"# {title}","", "Assessment: "+("tool self-check passed; no physical improvement conclusion" if selfcheck else
        "completed comparison with caveats; overall migration acceptance remains open"),"",
        f"Compared {FRAME_COUNT} complete native BI4 frames, {SOIL_COUNT} fixed soil IDs and {STEP_COUNT} logged steps per run.",
        f"Final actual time: {final['time_old_s']:.17g} / {final['time_new_s']:.17g} s; Tv={final['tv']:.12g}.","",
        ("| Quantity | Same baseline A / high+residual | Same baseline B / high+residual |" if selfcheck else
         "| Quantity | Baseline / high+residual | Current / double state |"), "|---|---:|---:|",
        f"| Final mean excess (Pa) | {final['old_mean_excess_pa']:.12g} | {final['new_mean_excess_pa']:.12g} |",
        f"| Final pressure-based U | {final['old_u']:.12g} | {final['new_u']:.12g} |",
        f"| Fixed-top settlement (mm) | {final['old_settlement_mm']:.12g} | {final['new_settlement_mm']:.12g} |","",
        f"All-frame maximum absolute particle pressure difference: {metrics['max_abs_particle_difference_pa']:.12g} Pa.",
        f"All-frame particle pressure RMS difference: {metrics['particle_difference_rms_pa']:.12g} Pa.",
        f"Maximum fixed-top settlement difference: {metrics['max_abs_settlement_difference_mm']:.12g} mm.","",
        "The full-run differences are descriptive. They do not establish improved physical accuracy, remove the late plateau, "
        "or satisfy the unresolved strict short-run pressure gates by themselves.","",
        "## Validation", "", "- Successful completion, zero exclusions and zero DtMin adjustments checked in both Run.out files.",
        "- Native input, reader executable, CSV and generated XML hashes recorded; source/reader-mismatched caches rejected.",
        "- Every frame has all IDs 0..1039, finite saved fields, native types and consistent row/frame times.",
        "- Comparisons use actual native times within 1e-9 s, no interpolation, equal reference pressures and identical initial state.",
        "- Final mean pressure and fixed-top settlement independently recomputed with scalar math.fsum.",
        "- PNG/PDF render files generated; visual inspection by the operator is still required after the formal run.","",
        "## Caveats",""]
    lines += ["- "+item for item in CAVEATS]
    lines += ["", "## Sources", "", f"- Baseline: `{report['runs'][0]['folder']}`",
              f"- Compared run: `{report['runs'][1]['folder']}`",f"- Native reader: `{READER}`",
              f"- Reproducible script: `{Path(__file__).resolve()}`", "",
              "Detailed per-frame data types, SHA-256 records, all target times, particle-layer membership and numerical differences "
              "are retained in the adjacent JSON and CSV files.",""]
    with path.open("x",encoding="utf-8") as stream: stream.write("\n".join(lines))


def postprocess(selfcheck=False, selfcheck_tag=""):
    started=time.perf_counter()
    figure_dir=CASE/"tests/figures/pore_double_2tv/selfcheck" if selfcheck else CASE/"figures"
    log_dir=LOG/"selfcheck" if selfcheck else LOG
    tag=("_"+selfcheck_tag) if selfcheck_tag else ""
    prefix=figure_dir/(PREFIX+"_selfcheck"+tag if selfcheck else PREFIX)
    qa_path=log_dir/("comparison_qa"+tag+".json")
    targets=[Path(str(prefix)+"_"+suffix) for suffix in SUFFIXES]+[qa_path]
    require(not any(path.exists() for path in targets), "Comparison artifact already exists; refusing every overwrite")
    figure_dir.mkdir(parents=True,exist_ok=True)
    log_dir.mkdir(parents=True,exist_ok=True)
    manifest=None
    if not selfcheck:
        manifest=guard.validate_manifest()
        require(guard.GENERATED_RECORD.is_file(), "Missing pre-solver generated-input record")
        generated=json.loads(guard.GENERATED_RECORD.read_text(encoding="utf-8"))
        require(generated["launch_manifest_sha256"]==sha(guard.MANIFEST), "Generated-input record belongs to another launch")
        for item in generated["generated_files"]:
            require(sha(item["path"])==item["sha256"], f"Generated input changed: {item['path']}")
    compared=BASELINE if selfcheck else CURRENT
    model,old_run=model_and_completion(BASELINE)
    new_model,new_run=model_and_completion(compared)
    require(model==new_model, "Reference-model parameters differ")
    guard.compare_xml(Path(old_run["xml"]["path"]),Path(new_run["xml"]["path"]),generated=True)
    reader=verify_reader()
    old_export=export_native(BASELINE,NATIVE_BASELINE,reader)
    if selfcheck:
        new_export=old_export
        new_native=NATIVE_BASELINE
    else:
        new_native=CURRENT/"native"
        new_export=export_native(CURRENT,new_native,reader)
    print("Read and validate all native frames (positions and pressure without float VTK conversion).",flush=True)
    old=read_native(NATIVE_BASELINE,"high_low")
    new=read_native(new_native,"high_low" if selfcheck else "double")
    history,profiles,metrics=analyze(old,new,model)
    negatives=guard_selftests()
    if selfcheck:
        require(np.array_equal(old["data"],new["data"]), "Same-baseline self-check states differ")
        require(all(value==0 for key,value in metrics["windows"]["all_saved_times"].items() if key!="frames"),
                "Same-baseline self-check metrics are nonzero")
    report=dict(mode="same_baseline_selfcheck_not_migration" if selfcheck else "completed_formal_comparison",
        generated_utc=datetime.now(timezone.utc).isoformat(),script=file_record(Path(__file__)),
        model=model,runs=[old_run,new_run],native_exports=[old_export,new_export],reader=reader,
        actual_time_tolerance_s=TIME_TOL,interpolation=False,metrics=metrics,
        native_frame_types={"old":old["frames"],"new":new["frames"]},
        prior_short_screening=prior_screening(),caveats=CAVEATS,
        chart_contract=dict(question="Does replacing high/low pore state change matched pressure and settlement?",
            takeaway="No improvement assumed; actual differences reported only after validation",
            family="line trends and initial-layer profiles",static_renderer="Matplotlib Agg PNG/PDF",
            time_points=FRAME_COUNT,profile_layers=100,palette_policy="hard two-root cap",
            old_color=COLORS[0],new_color=COLORS[1],reference_color=GRAY,
            non_color="old solid/open circles; new dashed/crosses; reference dotted",
            final_context="case figures" if not selfcheck else "tests figures selfcheck"),
        launch_manifest=file_record(guard.MANIFEST) if not selfcheck else None,
        baseline_provenance=manifest.get("baseline_provenance") if manifest else None,
        validation=dict(native_data_checks="passed",negative_fixtures_rejected=negatives,
                        actual_migration_test=not selfcheck,formal_visual_qa="operator review pending",
                        strict_short_gates_fully_passed=False))
    new_csv(Path(str(prefix)+"_history.csv"),history)
    new_csv(Path(str(prefix)+"_profiles.csv"),profiles)
    draw_figures(history,profiles,model,prefix,selfcheck)
    new_json(Path(str(prefix)+"_comparison.json"),report)
    write_report(Path(str(prefix)+"_comparison.md"),report,selfcheck)
    new_json(qa_path,dict(status="passed_with_caveats",mode=report["mode"],
        elapsed_s=time.perf_counter()-started,frames_per_run=FRAME_COUNT,rows_per_run=FRAME_COUNT*PARTICLE_COUNT,
        max_time_mismatch_s=metrics["max_actual_time_mismatch_s"],metrics=metrics,
        negative_fixtures_rejected=negatives,artifacts=[file_record(path) for path in targets[:-1]],
        visual_qa="Requires inspection of both final PNGs; generation is not visual QA",
        strict_short_gates_fully_passed=False))
    print(f"{'SELF-CHECK' if selfcheck else 'COMPARISON'} passed with caveats: {prefix}",flush=True)
    print(f"Elapsed {time.perf_counter()-started:.2f} s; final mean old/new "
          f"{history[-1]['old_mean_excess_pa']:.12g}/{history[-1]['new_mean_excess_pa']:.12g} Pa.",flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument("--preflight",action="store_true")
    group.add_argument("--generated",action="store_true")
    group.add_argument("--selfcheck",action="store_true")
    parser.add_argument("--selfcheck-tag",default="",help="Optional unique self-check filename tag; never changes formal output paths")
    args=parser.parse_args()
    require(not args.selfcheck_tag or (args.selfcheck and re.fullmatch(r"[a-z0-9_]+",args.selfcheck_tag)),
            "--selfcheck-tag requires --selfcheck and only lowercase letters/digits/underscores")
    if args.preflight: guard.preflight()
    elif args.generated: guard.generated_check()
    else: postprocess(args.selfcheck,args.selfcheck_tag)


if __name__=="__main__":
    try:
        main()
    except (ValueError,OSError,KeyError,AssertionError) as error:
        print(f"COMPARISON ERROR: {error}",file=sys.stderr,flush=True)
        sys.exit(1)
