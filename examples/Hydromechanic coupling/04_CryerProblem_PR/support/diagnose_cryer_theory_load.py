from pathlib import Path
import argparse
import csv
import json
import math
import os
import re
import sys
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "support"))

import postprocess_cryer as cryer


DEFAULT_CASES = [
    ROOT / "refinement" / "sweep_corrected_20260621" / "r0000_d0_full_tout0250",
    ROOT / "refinement" / "sweep_corrected_20260621" / "k1e5_tv008_toutTv001",
]


def read_run_scalar(runout, key, default=None):
    if not runout.exists():
        return default
    pattern = re.compile(rf"\b{re.escape(key)}=([0-9.Ee+-]+)")
    for line in runout.read_text(errors="ignore").splitlines():
        match = pattern.search(line)
        if match:
            return float(match.group(1))
    return default


def read_part_times(runout):
    times = {0: 0.0}
    if not runout.exists():
        return times
    pattern = re.compile(r"^Part_(\d+)\s+([0-9.Ee+-]+)\s+\d+")
    for line in runout.read_text(errors="ignore").splitlines():
        match = pattern.match(line.strip())
        if match:
            times[int(match.group(1))] = float(match.group(2))
    return times


def case_runout_path(case_dir):
    direct = case_dir / "Run.out"
    if direct.exists():
        return direct
    return case_dir / "out" / "Run.out"


def case_vtk_path(case_dir, part):
    direct = case_dir / "particles" / f"PartFluid_{part:04d}.vtk"
    if direct.exists():
        return direct
    return case_dir / "out" / "particles" / f"PartFluid_{part:04d}.vtk"


def case_label(case_dir):
    if case_dir.name in ("stage1", "stage2") and case_dir.parent.name:
        return f"{case_dir.parent.name}_{case_dir.name}"
    return case_dir.name


def find_xml(case_dir):
    direct_out_xml = case_dir / f"{case_dir.name}.xml"
    if direct_out_xml.exists():
        return direct_out_xml
    out_xml = case_dir / "out" / f"{case_dir.name}.xml"
    if out_xml.exists():
        return out_xml
    direct_xml = case_dir / f"{case_dir.name}_Def.xml"
    if direct_xml.exists():
        return direct_xml
    matches = sorted(case_dir.glob("*_Def.xml"))
    if matches:
        return matches[0]
    matches = sorted(case_dir.glob("*.xml"))
    return matches[0] if matches else None


def xml_float(root, tag, default):
    node = root.find(f".//{tag}")
    if node is None:
        return default
    value = node.get("value")
    if value is None:
        return default
    return float(value)


def read_case_parameters(case_dir):
    xml_path = find_xml(case_dir)
    values = {
        "E": 2.0e6,
        "nu": 0.3,
        "rho_w": 1000.0,
        "kw": 2.0e8,
        "porosity": 0.3,
        "khyd": 1.0e-4,
        "q0": 10000.0,
        "rhop0": 2100.0,
    }
    if xml_path:
        root = ET.parse(xml_path).getroot()
        values["E"] = xml_float(root, "ModulusE", values["E"])
        values["nu"] = xml_float(root, "PRvs", values["nu"])
        values["rho_w"] = xml_float(root, "PoreWaterRho", values["rho_w"])
        values["kw"] = xml_float(root, "PoreWaterBulkModulus", values["kw"])
        values["porosity"] = xml_float(root, "Porosity", values["porosity"])
        values["khyd"] = xml_float(root, "HydraulicConductivity", values["khyd"])
        values["q0"] = xml_float(root, "HydroMechTopLoadQ0", values["q0"])
        values["rhop0"] = xml_float(root, "rhop0", values["rhop0"])
    runout = case_runout_path(case_dir)
    values["dp"] = read_run_scalar(runout, "Dp", 0.003)
    values["radius"] = 0.05
    values["mass_fluid"] = read_run_scalar(runout, "MassFluid", values["rhop0"] * values["dp"] ** 3)
    values["kernel_h"] = read_run_scalar(runout, "KernelH", 1.8 * values["dp"])
    values["kernel_size"] = read_run_scalar(runout, "KernelSize", 2.0 * values["kernel_h"])
    values["xml"] = str(xml_path) if xml_path else ""
    return values


def theory_metrics(values):
    e = values["E"]
    nu = values["nu"]
    khyd = values["khyd"]
    rho_w = values["rho_w"]
    g = 9.81
    radius = values["radius"]
    kw = values["kw"]
    por = values["porosity"]
    kbulk = e / (3.0 * (1.0 - 2.0 * nu))
    gshear = e / (2.0 * (1.0 + nu))
    m_constrained = kbulk + 4.0 * gshear / 3.0
    kw_over_n = kw / por
    storage_eff = 1.0 / (1.0 / m_constrained + por / kw)
    cv_m = khyd * m_constrained / (rho_w * g)
    cv_storage = khyd * storage_eff / (rho_w * g)
    cv_water = khyd * kw_over_n / (rho_w * g)
    return {
        "E": e,
        "nu": nu,
        "K_bulk": kbulk,
        "G_shear": gshear,
        "M_constrained": m_constrained,
        "Kw": kw,
        "porosity": por,
        "Kw_over_n": kw_over_n,
        "storage_eff_modulus": storage_eff,
        "khyd": khyd,
        "cv_using_M": cv_m,
        "cv_using_storage_eff": cv_storage,
        "cv_using_Kw_over_n_only": cv_water,
        "cv_storage_over_M": cv_storage / cv_m if cv_m else 0.0,
        "cv_Kw_over_n_over_M": cv_water / cv_m if cv_m else 0.0,
        "time_for_Tv_1_using_M": radius * radius / cv_m if cv_m else 0.0,
        "time_for_Tv_1_using_storage_eff": radius * radius / cv_storage if cv_storage else 0.0,
        "time_for_Tv_1_using_Kw_over_n_only": radius * radius / cv_water if cv_water else 0.0,
    }


def load_summary(case_dir):
    path = case_dir / "analysis" / f"{case_dir.name}_summary.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def closest_part(times, target_time):
    return min(times.keys(), key=lambda idx: abs(times[idx] - target_time))


def selected_parts(case_dir):
    times = read_part_times(case_runout_path(case_dir))
    summary = load_summary(case_dir)
    parts = {1}
    if summary.get("peak_num_time") is not None:
        parts.add(closest_part(times, float(summary["peak_num_time"])))
    parts.add(max(times.keys()))
    return sorted(idx for idx in parts if idx > 0), times


def radial_stats(rows, params, nbins=24):
    radius = params["radius"]
    area = 4.0 * math.pi * radius * radius
    mass = params["mass_fluid"]
    kernel_size = params["kernel_size"]
    result = {
        "count": 0,
        "nonzero_count": 0,
        "signed_inward_force": 0.0,
        "positive_inward_force": 0.0,
        "outward_force": 0.0,
        "net_force_x": 0.0,
        "net_force_y": 0.0,
        "net_force_z": 0.0,
        "mean_loadace_mag": 0.0,
        "mean_signed_inward_acc": 0.0,
        "core_inward_force": 0.0,
        "boundary_inward_force": 0.0,
        "outer_10pct_inward_force": 0.0,
    }
    bins = []
    for i in range(nbins):
        r0 = radius * i / nbins
        r1 = radius * (i + 1) / nbins
        bins.append({
            "bin": i,
            "r0": r0,
            "r1": r1,
            "r_mid": 0.5 * (r0 + r1),
            "count": 0,
            "nonzero_count": 0,
            "mean_signed_inward_acc": 0.0,
            "mean_loadace_mag": 0.0,
            "signed_inward_force": 0.0,
            "positive_inward_force": 0.0,
            "outward_force": 0.0,
        })

    mag_sum = 0.0
    inward_acc_sum = 0.0
    for row in rows:
        if "loadace_x" not in row:
            continue
        r = row["r"]
        if r <= 0.0:
            continue
        ax = row["loadace_x"]
        ay = row["loadace_y"]
        az = row["loadace_z"]
        mag = row["loadace_mag"]
        erx, ery, erz = row["x"] / r, row["y"] / r, row["z"] / r
        ar_out = ax * erx + ay * ery + az * erz
        inward_acc = -ar_out
        signed_force = mass * inward_acc
        positive_force = max(0.0, signed_force)
        outward_force = max(0.0, -signed_force)

        result["count"] += 1
        if mag > 1.0e-14:
            result["nonzero_count"] += 1
        result["signed_inward_force"] += signed_force
        result["positive_inward_force"] += positive_force
        result["outward_force"] += outward_force
        result["net_force_x"] += mass * ax
        result["net_force_y"] += mass * ay
        result["net_force_z"] += mass * az
        mag_sum += mag
        inward_acc_sum += inward_acc
        if r < radius - kernel_size:
            result["core_inward_force"] += positive_force
        else:
            result["boundary_inward_force"] += positive_force
        if r >= 0.9 * radius:
            result["outer_10pct_inward_force"] += positive_force

        ibin = min(nbins - 1, max(0, int(r / radius * nbins)))
        b = bins[ibin]
        b["count"] += 1
        if mag > 1.0e-14:
            b["nonzero_count"] += 1
        b["mean_signed_inward_acc"] += inward_acc
        b["mean_loadace_mag"] += mag
        b["signed_inward_force"] += signed_force
        b["positive_inward_force"] += positive_force
        b["outward_force"] += outward_force

    if result["count"]:
        result["mean_loadace_mag"] = mag_sum / result["count"]
        result["mean_signed_inward_acc"] = inward_acc_sum / result["count"]
    for b in bins:
        if b["count"]:
            b["mean_signed_inward_acc"] /= b["count"]
            b["mean_loadace_mag"] /= b["count"]
    net = math.sqrt(result["net_force_x"] ** 2 + result["net_force_y"] ** 2 + result["net_force_z"] ** 2)
    result["net_force_mag"] = net
    result["area"] = area
    result["equiv_pressure_signed"] = result["signed_inward_force"] / area
    result["equiv_pressure_positive"] = result["positive_inward_force"] / area
    result["net_force_ratio_to_positive_inward"] = net / result["positive_inward_force"] if result["positive_inward_force"] else 0.0
    result["core_inward_force_fraction"] = result["core_inward_force"] / result["positive_inward_force"] if result["positive_inward_force"] else 0.0
    result["boundary_inward_force_fraction"] = result["boundary_inward_force"] / result["positive_inward_force"] if result["positive_inward_force"] else 0.0
    result["outer_10pct_inward_force_fraction"] = result["outer_10pct_inward_force"] / result["positive_inward_force"] if result["positive_inward_force"] else 0.0
    return result, bins


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def plot_bins(figdir, tag, profiles):
    plt.figure(figsize=(7.2, 4.8), dpi=220)
    for label, bins in profiles:
        total = sum(b["positive_inward_force"] for b in bins)
        xs = [b["r_mid"] / 0.05 for b in bins]
        ys = [b["positive_inward_force"] / total if total else 0.0 for b in bins]
        plt.plot(xs, ys, "o-", ms=3, lw=1.0, label=label)
    plt.xlabel("r/R")
    plt.ylabel("fraction of inward radial load")
    plt.grid(True, alpha=0.25)
    plt.legend(loc="best", fontsize=8)
    plt.tight_layout()
    out = figdir / f"{tag}_radial_load_fraction.png"
    plt.savefig(out)
    plt.close()
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", type=Path, default=None)
    parser.add_argument("--figdir", type=Path, default=ROOT / "figures")
    parser.add_argument("--outtag", default="cryer_theory_load_diagnostics")
    args = parser.parse_args()

    cases = args.case or DEFAULT_CASES
    args.figdir.mkdir(parents=True, exist_ok=True)

    theory_rows = []
    summary_rows = []
    all_details = {}
    profiles = []
    for case_dir in cases:
        case_dir = case_dir.resolve()
        label_name = case_label(case_dir)
        params = read_case_parameters(case_dir)
        tmetrics = theory_metrics(params)
        theory_rows.append({"case": label_name, **tmetrics})

        parts, times = selected_parts(case_dir)
        details = {"parameters": params, "theory": tmetrics, "parts": {}}
        for part in parts:
            vtk = case_vtk_path(case_dir, part)
            if not vtk.exists():
                continue
            rows = cryer.read_part_vtk(vtk)
            stats, bins = radial_stats(rows, params)
            time = times.get(part, 0.0)
            tv = tmetrics["cv_using_M"] * time / (params["radius"] ** 2) if params["radius"] else 0.0
            label = f"{label_name} Part_{part:04d} Tv={tv:.4g}"
            profiles.append((label, bins))
            part_summary = {
                "case": label_name,
                "part": part,
                "time": time,
                "tv_using_M": tv,
                "q0": params["q0"],
                "equiv_pressure_signed_over_q0": stats["equiv_pressure_signed"] / params["q0"] if params["q0"] else 0.0,
                "equiv_pressure_positive_over_q0": stats["equiv_pressure_positive"] / params["q0"] if params["q0"] else 0.0,
                "nonzero_fraction": stats["nonzero_count"] / stats["count"] if stats["count"] else 0.0,
                "net_force_ratio": stats["net_force_ratio_to_positive_inward"],
                "core_inward_force_fraction": stats["core_inward_force_fraction"],
                "boundary_inward_force_fraction": stats["boundary_inward_force_fraction"],
                "outer_10pct_inward_force_fraction": stats["outer_10pct_inward_force_fraction"],
                "mean_signed_inward_acc": stats["mean_signed_inward_acc"],
                "mean_loadace_mag": stats["mean_loadace_mag"],
            }
            summary_rows.append(part_summary)
            details["parts"][f"Part_{part:04d}"] = {
                "summary": part_summary,
                "stats": stats,
                "bins": bins,
            }
            bin_rows = []
            for b in bins:
                bin_rows.append({
                    "case": case_dir.name,
                    "part": part,
                    "time": time,
                    "tv_using_M": tv,
                    "r_mid_over_R": b["r_mid"] / params["radius"],
                    **b,
                })
            write_csv(args.figdir / f"{args.outtag}_{label_name}_part{part:04d}_radial_bins.csv", bin_rows)
        all_details[label_name] = details

    write_csv(args.figdir / f"{args.outtag}_theory_parameters.csv", theory_rows)
    write_csv(args.figdir / f"{args.outtag}_load_summary.csv", summary_rows)
    plot_path = plot_bins(args.figdir, args.outtag, profiles)
    json_path = args.figdir / f"{args.outtag}.json"
    json_path.write_text(json.dumps({
        "theory_parameters": theory_rows,
        "load_summary": summary_rows,
        "details": all_details,
        "radial_load_fraction_plot": str(plot_path),
    }, indent=2), encoding="utf-8")

    print(json.dumps({
        "theory_parameters_csv": str(args.figdir / f"{args.outtag}_theory_parameters.csv"),
        "load_summary_csv": str(args.figdir / f"{args.outtag}_load_summary.csv"),
        "json": str(json_path),
        "plot": str(plot_path),
        "load_summary": summary_rows,
    }, indent=2))


if __name__ == "__main__":
    main()
