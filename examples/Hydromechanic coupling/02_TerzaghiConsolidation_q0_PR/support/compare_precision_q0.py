"""Compare completed q0 consolidation runs without overwriting historical figures.

Examples (from the case directory):
  python support/compare_precision_q0.py
  python support/compare_precision_q0.py --partial --output-prefix precision_progress

The existing VTK reader is reused. Snapshot times come from Run.out, not
snapshot_index * TimeOut. A historical comparison cannot isolate a source patch
when other solver changes occurred between the two executable builds.
"""

from pathlib import Path
import argparse
import csv
from decimal import Decimal, InvalidOperation
import hashlib
import importlib.util
import math
import re
import sys
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
PARSER = ROOT / "support" / "postprocess_terzaghi_q0.py"
spec = importlib.util.spec_from_file_location("q0_existing_parser", PARSER)
pp = importlib.util.module_from_spec(spec)
sys.dont_write_bytecode = True
spec.loader.exec_module(pp)
TARGETS = (0.005, 0.05, 0.1, 0.25, 0.5, 0.7, 1.0, 1.5, 2.0)
COLORS = ("#D55E00", "#0072B2")
STYLES = ("--", "-")


def normalized(value):
    try:
        return str(Decimal(value).normalize())
    except InvalidOperation:
        return value.strip()


def signature(element):
    """Compare executable XML settings while ignoring descriptive comments."""
    if element is None:
        return None
    attrs = tuple(sorted((key, normalized(value)) for key, value in element.attrib.items()
                         if "comment" not in key and not key.startswith("_")))
    children = tuple(signature(child) for child in element if not child.tag.startswith("_"))
    return element.tag, attrs, (element.text or "").strip(), children


def xml_value(tree, xpath):
    element = tree.find(xpath)
    if element is None or "value" not in element.attrib:
        raise ValueError(f"Missing required XML value: {xpath}")
    return float(element.attrib["value"])


def log_number(log, key, default=None):
    match = re.search(r"^\s*" + re.escape(key) + r"\s*[.:=]+\s*([+\-\d.eE]+)", log, re.M)
    return float(match.group(1)) if match else default


def read_run(folder, partial):
    folder = folder.resolve()
    if not folder.is_dir():
        raise ValueError(f"Run directory does not exist: {folder}")
    logpath = folder / "Run.out"
    log = logpath.read_text(encoding="utf-8", errors="replace")
    complete = "Finished execution (code=0)." in log
    if not partial and not complete:
        raise ValueError(f"Run is not successfully complete: {logpath}")
    if re.search(r"Finished execution \(code=[1-9]", log):
        raise ValueError(f"Failed execution cannot be compared: {logpath}")
    if log_number(log, "Excluded particles", 0) != 0:
        raise ValueError(f"Particle exclusions invalidate this comparison: {logpath}")
    xmls = [path for path in folder.glob("*.xml")
            if ET.parse(path).find("./execution/particles") is not None]
    if len(xmls) != 1:
        raise ValueError(f"Expected exactly one generated case XML in {folder}; found {len(xmls)}")
    xmlpath = xmls[0]
    tree = ET.parse(xmlpath)
    special = "./execution/special/"
    hydro = special + "hydromechanics/"
    parameters = "./execution/parameters/parameter[@key='{}']"
    model = {
        "E": xml_value(tree, special + "soils/ModulusE"),
        "nu": xml_value(tree, special + "soils/PRvs"),
        "k": xml_value(tree, hydro + "HydraulicConductivity"),
        "n": xml_value(tree, hydro + "Porosity"),
        "Kw": xml_value(tree, hydro + "PoreWaterBulkModulus"),
        "rho_w": xml_value(tree, hydro + "PoreWaterRho"),
        "q0": xml_value(tree, hydro + "HydroMechTopLoadQ0"),
        "tL": xml_value(tree, hydro + "HydroMechTopLoadRampTime"),
        "tD": xml_value(tree, hydro + "HydroMechDrainageStartTime"),
        "H": xml_value(tree, "./execution/uservars/varnum[@name='sizefz']"),
        "dp": xml_value(tree, "./execution/constants/dp"),
        "dt": xml_value(tree, parameters.format("DtFixed")),
        "time_max": xml_value(tree, parameters.format("TimeMax")),
        "time_out": xml_value(tree, parameters.format("TimeOut")),
        "g_ref": 9.81,
    }
    if model["H"] <= 0 or model["q0"] <= 0 or model["dt"] <= 0:
        raise ValueError("This comparison requires positive height, load and fixed time step")
    if not math.isclose(model["tL"], model["tD"], abs_tol=1e-12):
        raise ValueError("The reference implemented here requires tL = drainage start time")
    gravity = tree.find("./execution/constants/gravity")
    if gravity is None or any(float(gravity.attrib[axis]) != 0 for axis in "xyz"):
        raise ValueError("This external-load reference requires zero gravity")
    model["M"] = model["E"] * (1 - model["nu"]) / ((1 + model["nu"]) * (1 - 2 * model["nu"]))
    model["cv"] = model["k"] * model["M"] / (model["rho_w"] * model["g_ref"])
    initial_count = sum(int(el.attrib["count"]) for el in tree.findall("./execution/particles/fluid"))
    if not initial_count:
        raise ValueError(f"No generated soil/fluid particles in {xmlpath}")
    times = {0: 0.0}
    for match in re.finditer(r"^Part_(\d+)\s+([\d.eE+\-]+)\s+\d+\s+\d+\s+", log, re.M):
        times[int(match.group(1))] = float(match.group(2))
    vtk_by_index = {pp.part_index(path): path for path in (folder / "particles").glob("PartFluid_*.vtk")}
    if not vtk_by_index:
        raise ValueError(f"No converted fluid VTK snapshots in {folder / 'particles'}")
    indices = sorted(vtk_by_index)
    if indices != list(range(indices[-1] + 1)):
        raise ValueError(f"Missing/irregular VTK snapshot indices in {folder}")
    missing_times = set(indices) - set(times)
    if missing_times:
        raise ValueError(f"Run.out lacks actual snapshot times: {sorted(missing_times)}")
    if any(times[j] <= times[i] for i, j in zip(indices, indices[1:])):
        raise ValueError(f"Non-monotonic actual snapshot times in {logpath}")
    bi4_indices = {int(re.search(r"Part_(\d+)\.bi4$", path.name).group(1))
                   for path in (folder / "data").glob("Part_[0-9]*.bi4")}
    if not set(indices).issubset(bi4_indices):
        raise ValueError(f"Some converted snapshots have no source BI4 file in {folder}")
    final_tv = model["cv"] * max(0, times[indices[-1]] - model["tD"]) / model["H"] ** 2
    if not partial:
        if len(indices) < 401 or final_tv < 1.999:
            raise ValueError(f"Full 2Tv comparison requires >=401 snapshots and Tv>=1.999; got {len(indices)}, {final_tv}")
        logged_count = log_number(log, "PART files")
        if logged_count is None or int(logged_count) != len(indices) or bi4_indices != set(indices):
            raise ValueError(f"Complete VTK/BI4/PART counts disagree in {folder}")
        total_steps = log_number(log, "Steps of simulation")
        if total_steps is None or total_steps * model["dt"] < model["time_max"] - model["dt"]:
            raise ValueError(f"Completed fixed-step run did not reach configured TimeMax: {folder}")
    chosen = {tv: min(indices, key=lambda idx: abs(times[idx] - (model["tD"] + tv * model["H"] ** 2 / model["cv"])))
              for tv in TARGETS if tv <= final_tv + model["cv"] * model["time_out"] / model["H"] ** 2 * .51}
    pp.DP = model["dp"]
    history, profiles = [], {}
    z0 = None
    for idx in indices:
        rows = pp.read_part_vtk(vtk_by_index[idx])
        if len(rows) != initial_count:
            raise ValueError(f"Particle count changed at {vtk_by_index[idx]}: {len(rows)} vs {initial_count}")
        if not all(math.isfinite(row[key]) for row in rows for key in ("x", "z", "excess", "pore")):
            raise ValueError(f"Non-finite particle state in {vtk_by_index[idx]}")
        if z0 is None:
            z0 = pp.top_layer_z(rows)
        time = times[idx]
        tv = model["cv"] * max(0, time - model["tD"]) / model["H"] ** 2
        mean_p = pp.mean_value(rows, "excess")
        theory_u = pp.degree_theory(tv) if time >= model["tD"] else 0.0
        theory_p = model["q0"] * (1 - theory_u) if time >= model["tD"] else math.nan
        item = {"snapshot": vtk_by_index[idx].name, "index": idx, "time_s": time, "tv": tv,
                "n_particles": len(rows), "mean_excess_pa": mean_p,
                "u_num": 1 - mean_p / model["q0"] if time >= model["tD"] else 0.0,
                "u_theory": theory_u, "mean_theory_pa": theory_p,
                "settlement_mm": (z0 - pp.top_layer_z(rows)) * 1000,
                "settlement_theory_mm": model["q0"] * model["H"] / model["M"] * theory_u * 1000,
                "max_speed_m_s": pp.max_value(rows, "speed")}
        history.append(item)
        for target, selected in chosen.items():
            if selected == idx:
                profiles[target] = (item, pp.layer_average(rows, "excess"))
    run_csv = folder / "Run.csv"
    csv_meta = {}
    if run_csv.exists():
        with run_csv.open(encoding="utf-8-sig", newline="") as stream:
            csv_meta = next(csv.DictReader(stream, delimiter=";"), {})
    return {"folder": folder, "xml": xmlpath, "tree": tree, "log": log, "complete": complete,
            "model": model, "history": history, "profiles": profiles, "csv": csv_meta,
            "initial_count": initial_count, "runtime_s": log_number(log, "Simulation Runtime"),
            "run_log_sha256": hashlib.sha256(logpath.read_bytes()).hexdigest(),
            "xml_sha256": hashlib.sha256(xmlpath.read_bytes()).hexdigest()}


def check_settings(baseline, current):
    for xpath in ("./execution/parameters", "./execution/constants",
                  "./casedef/geometry", "./casedef/constantsdef"):
        if signature(baseline["tree"].find(xpath)) != signature(current["tree"].find(xpath)):
            raise ValueError(f"Generated case settings differ at {xpath}; refusing a misleading comparison")
    # A terminal TimeOut segment only schedules an exact-final snapshot. It does
    # not change the physical equations; every other special setting must match.
    specials = [tuple(signature(child) for child in run["tree"].find("./execution/special")
                      if child.tag != "timeout") for run in (baseline, current)]
    if specials[0] != specials[1]:
        raise ValueError("Generated special settings differ beyond output-only timeout scheduling")
    if baseline["initial_count"] != current["initial_count"]:
        raise ValueError("Initial particle counts differ")
    for name in ("PoreMdbcInterpolationMode", "PoreCompressionSourceMode", "PoreCompressionGradCorr",
                 "SoilStressRateGradCorr", "mDBC-Corrector", "mDBC-FastSingle", "SlipMode", "StepAlgorithm"):
        pattern = r"^\s*" + re.escape(name) + r"\s*[:=]\s*(.+)$"
        old, new = (re.search(pattern, run["log"], re.M) for run in (baseline, current))
        if old and new and old.group(1).strip() != new.group(1).strip():
            raise ValueError(f"Logged solver configuration differs: {name}: {old.group(1)} vs {new.group(1)}")


def pressure_theory(z, tv, model):
    """Classical drained-top / impermeable-bottom Terzaghi Fourier solution."""
    z = np.asarray(z)
    result = np.zeros_like(z, dtype=float)
    for n in range(240):
        m = (2 * n + 1) * math.pi / 2
        result += 2 * (-1) ** n / m * np.cos(m * z / model["H"]) * math.exp(-m * m * tv)
    return model["q0"] * result


def target_metrics(run):
    result = []
    for target, (item, profile) in sorted(run["profiles"].items()):
        z, pressure = np.asarray(profile).T
        truth = pressure_theory(z, item["tv"], run["model"])
        result.append(dict(item, target_tv=target, profile_rmse_pa=float(np.sqrt(np.mean((pressure - truth) ** 2))),
                           bottom_excess_pa=float(pressure[0]), top_excess_pa=float(pressure[-1]),
                           mean_error_pa=item["mean_excess_pa"] - item["mean_theory_pa"],
                           u_error=item["u_num"] - item["u_theory"]))
    return result


def save_csv(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def finish_figure(fig, path):
    fig.tight_layout()
    fig.savefig(path.with_suffix(".png"), dpi=240, facecolor="white")
    fig.savefig(path.with_suffix(".pdf"), facecolor="white")
    plt.close(fig)


def make_plots(runs, labels, outdir, prefix, partial):
    plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.facecolor": "white", "figure.facecolor": "white",
                         "lines.linewidth": 1.8, "pdf.fonttype": 42})
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.6))
    fields = ("mean_excess_pa", "mean_excess_pa", "u_num", "settlement_mm")
    titles = ("Mean excess pore pressure", "Late-time dissipation", "Consolidation degree", "Top settlement")
    ylabels = ("Mean excess pressure (Pa)", "Mean excess pressure (Pa)", "$U = 1-\\bar{p}/q_0$", "Settlement (mm)")
    max_tv = min(run["history"][-1]["tv"] for run in runs)
    for run, label, color, style in zip(runs, labels, COLORS, STYLES):
        post = [item for item in run["history"] if item["time_s"] >= run["model"]["tD"]]
        for ax, field in zip(axes.flat, fields):
            ax.plot([row["tv"] for row in post], [row[field] for row in post], color=color,
                    linestyle=style, label=label)
    model = runs[0]["model"]
    tvs = np.linspace(0.00001, max_tv, 700)
    u = np.array([pp.degree_theory(float(tv)) for tv in tvs])
    curves = (model["q0"] * (1 - u), model["q0"] * (1 - u), u,
              model["q0"] * model["H"] / model["M"] * u * 1000)
    for ax, curve, title, ylabel in zip(axes.flat, curves, titles, ylabels):
        ax.plot(tvs, curve, "k:", linewidth=1.8, label="Classical Terzaghi")
        ax.set(xlabel="$T_v=c_v(t-t_D)/H^2$", ylabel=ylabel, title=title, xlim=(0, max(0.01, max_tv)))
        ax.grid(alpha=.2)
        ax.legend(fontsize=8)
    axes[0, 1].set_xlim(1, max(1.01, max_tv))
    late_values = [row["mean_excess_pa"] for run in runs for row in run["history"] if 1 <= row["tv"] <= max_tv]
    if late_values:
        axes[0, 1].set_ylim(0, 1.1 * max(late_values + [float(model["q0"] * (1 - pp.degree_theory(1)))]))
    elif partial:
        axes[0, 1].text(.5, .5, "No shared data beyond Tv=1 yet", ha="center", transform=axes[0, 1].transAxes)
    fig.suptitle("q0 consolidation, k=" + f"{model['k']:g} m/s" + (" - PARTIAL RESULTS" if partial else ""), fontsize=13)
    finish_figure(fig, outdir / f"{prefix}_history")
    fig, axes = plt.subplots(1, 3, figsize=(11.8, 5.5), sharey=True, sharex=True)
    values = [pressure / model["q0"] for run in runs for target in (.5, 1.0, 2.0)
              if target in run["profiles"] for _, pressure in run["profiles"][target][1]]
    xmax = max(.42, 1.05 * max(values)) if values else .42
    for ax, target in zip(axes, (.5, 1.0, 2.0)):
        available = all(target in run["profiles"] for run in runs)
        if not available:
            ax.text(.5, .5, "Not reached", ha="center", transform=ax.transAxes)
        else:
            for run, label, color, style in zip(runs, labels, COLORS, STYLES):
                item, prof = run["profiles"][target]
                z, pressure = np.asarray(prof).T
                ax.plot(pressure / model["q0"], z / model["H"], linestyle=style, color=color,
                        marker="o" if color == COLORS[0] else "s", markevery=8, markersize=3,
                        markerfacecolor="none", label=f"{label} (Tv={item['tv']:.5f})")
            actual = runs[1]["profiles"][target][0]["tv"]
            z = np.linspace(0, model["H"], 200)
            ax.plot(pressure_theory(z, actual, model) / model["q0"], z / model["H"], "k:",
                    label="Classical Terzaghi (current time)")
        ax.set(title=f"Tv approximately {target:g}", xlabel="$p_w/q_0$", xlim=(-.01, xmax), ylim=(0, 1.01))
        ax.grid(alpha=.2)
        if available:
            ax.legend(loc="upper right", fontsize=7)
    axes[0].set_ylabel("$z/H$ (current particle position)")
    fig.suptitle("Pore-pressure profiles - common horizontal scale" + (" - PARTIAL RESULTS" if partial else ""))
    finish_figure(fig, outdir / f"{prefix}_profiles")


def write_report(path, runs, labels, partial):
    lines = ["# q0 pore-pressure precision comparison", "", "Status: " + ("PARTIAL / not a final acceptance" if partial else "completed 2Tv runs"), ""]
    if runs[0]["folder"] == runs[1]["folder"]:
        lines += ["SELF-CHECK: both inputs are the same historical result; this is not a precision-patch result.", ""]
    model = runs[0]["model"]
    lines += [f"Generated XML physical and numerical settings match (output-only timeout segments are excluded). k={model['k']:g} m/s, dp={model['dp']:g} m, dt={model['dt']:g} s, H={model['H']:g} m, q0={model['q0']:g} Pa.",
              f"E={model['E']:g} Pa, nu={model['nu']:g}, n={model['n']:g}, Kw={model['Kw']:g} Pa. M={model['M']:.12g} Pa, cv={model['cv']:.12g} m2/s.",
              "Tv=cv*(t-tD)/H^2, with tD=tL. g_ref=9.81 m/s2 is the conductivity-to-pressure conversion reference; simulation gravity is zero.", "",
              "| Quantity | Baseline | Current |", "|---|---:|---:|"]
    finals = [run["history"][-1] for run in runs]
    for key in ("time_s", "tv", "n_particles", "mean_excess_pa", "mean_theory_pa", "u_num", "u_theory", "settlement_mm", "settlement_theory_mm", "max_speed_m_s"):
        lines.append(f"| {key} | {finals[0][key]:.10g} | {finals[1][key]:.10g} |")
    lines += ["", "Final values refer to each last saved snapshot, not to an invented snapshot at exact Tv=2.",
              "Run.out supplies actual times (printed to six decimal places); Part_0000 is time zero. The solver can stop slightly after its last scheduled PART output.", ""]
    for run, label in zip(runs, labels):
        final = run["history"][-1]
        late = [row for row in run["history"] if row["tv"] >= 1]
        slope = float(np.polyfit([row["tv"] for row in late], [row["mean_excess_pa"] for row in late], 1)[0]) if len(late) > 1 else math.nan
        targets = target_metrics(run)
        terminal = targets[-1] if targets else None
        lines += [f"## {label}", "", f"Input: `{run['folder']}`", f"Generated XML: `{run['xml'].name}`",
                  f"Run.csv version: `{run['csv'].get('Rcode-VersionInfo', 'unavailable')}`; date: `{run['csv'].get('DateTime', 'unavailable')}`.",
                  f"Hardware/run mode: `{run['csv'].get('Hardware', 'unavailable')}` / `{run['csv'].get('RunMode', 'unavailable')}`.",
                  f"Snapshots: {len(run['history'])}; particles per snapshot: {run['initial_count']} (verified all snapshots).",
                  f"Simulation runtime: {run['runtime_s']} s; solver physical end time: {run['csv'].get('PhysicalTime', 'not complete')} s.",
                  f"Final U error: {final['u_num'] - final['u_theory']:.10g}; mean-pressure error: {final['mean_excess_pa'] - final['mean_theory_pa']:.10g} Pa.",
                  f"Least-squares mean-pressure slope over available Tv>=1: {slope:.10g} Pa/Tv."]
        if terminal:
            lines.append(f"Last target Tv={terminal['target_tv']:g}, actual Tv={terminal['tv']:.10g}: profile RMSE={terminal['profile_rmse_pa']:.10g} Pa; bottom pressure={terminal['bottom_excess_pa']:.10g} Pa.")
        lines += [f"Run.out SHA256: `{run['run_log_sha256']}`", f"Generated XML SHA256: `{run['xml_sha256']}`", ""]
    lines += ["## Interpretation limits", "",
              "A comparison with a historical executable does not isolate the precision patch. The retained July result predates subsequent u-pw source changes, including pore-pressure mDBC handling. Identical XML and a shared version banner do not prove identical solver source. A same-source unpatched control is needed before assigning the whole improvement to compensated accumulation.",
              "Simulation times are reported for traceability, not as a speedup: compiler/build, hardware load, OpenMP scheduling and executable revisions may differ.",
              "The analytic curve is classical incompressible-water, small-strain Terzaghi theory with an ideal initial q0 field at drainage opening. The numerical model has finite Kw, a load ramp and moving particles. It is a physical accuracy reference rather than an exact solution of every discrete equation.",
              f"Finite-water storage indicator n*M/Kw={model['n'] * model['M'] / model['Kw']:.10g}; no finite-Kw correction has been silently substituted into the historical reference.",
              "Mean pressure uses the same arithmetic mean of the soil particles as the historical analysis. Profiles are averaged in dp-wide current-z layers; settlement follows the mean top layer. No initial high-pressure snapshot is fabricated before the first saved post-load output.", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=ROOT / "CaseTerzaghiConsolidation_q0_PR_full_k1em4_out")
    parser.add_argument("--current", type=Path, default=ROOT / "CaseTerzaghiConsolidation_q0_PR_full_k1em4_precision_out")
    parser.add_argument("--output-prefix", default="precision_q0_k1em4")
    parser.add_argument("--partial", action="store_true", help="Write clearly marked interim results only under tests/figures")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.output_prefix):
        raise ValueError("Output prefix must contain only letters, digits, underscores or hyphens")
    if not args.output_prefix.startswith("precision_"):
        raise ValueError("Output prefix must start with precision_ to protect historical figures")
    outdir = ROOT / "tests" / "figures" if args.partial else ROOT / "figures"
    suffixes = ("history.png", "history.pdf", "profiles.png", "profiles.pdf", "history.csv", "targets.csv", "report.md")
    existing = [outdir / f"{args.output_prefix}_{suffix}" for suffix in suffixes
                if (outdir / f"{args.output_prefix}_{suffix}").exists()]
    if existing:
        raise ValueError(f"Comparison outputs already exist; choose a new --output-prefix. First existing file: {existing[0]}")
    runs = [read_run(path if path.is_absolute() else ROOT / path, args.partial) for path in (args.baseline, args.current)]
    check_settings(*runs)
    selfcheck = runs[0]["folder"] == runs[1]["folder"]
    labels = ("Historical u-pw", "Current precision run") if not selfcheck else ("Historical input A", "Same historical input B")
    outdir.mkdir(parents=True, exist_ok=True)
    history = [dict(dataset=label, source=str(run["folder"]), **item) for run, label in zip(runs, labels) for item in run["history"]]
    targets = [dict(dataset=label, source=str(run["folder"]), **item) for run, label in zip(runs, labels) for item in target_metrics(run)]
    save_csv(outdir / f"{args.output_prefix}_history.csv", history)
    if targets:
        save_csv(outdir / f"{args.output_prefix}_targets.csv", targets)
    make_plots(runs, labels, outdir, args.output_prefix, args.partial)
    write_report(outdir / f"{args.output_prefix}_report.md", runs, labels, args.partial)
    print(f"Comparison outputs: {outdir / args.output_prefix}")
    for run, label in zip(runs, labels):
        last = run["history"][-1]
        print(f"{label}: snapshots={len(run['history'])}, Tv={last['tv']:.10g}, U={last['u_num']:.10g}, mean excess={last['mean_excess_pa']:.10g} Pa")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, ET.ParseError) as exc:
        print(f"Comparison refused: {exc}", file=sys.stderr)
        sys.exit(1)
