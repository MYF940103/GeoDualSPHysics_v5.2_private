from pathlib import Path
import argparse
import csv
import importlib.util
import math
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
POSTPROCESS = ROOT / "support" / "postprocess_terzaghi_q0.py"

spec = importlib.util.spec_from_file_location("terzaghi_q0", POSTPROCESS)
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)

TARGET_TV = [0.005, 0.05, 0.1, 0.25, 0.4, 0.5]


def cv_for_k(k_text):
    return float(k_text) * pp.M_CONSTRAINED / (pp.RHO_W * pp.G_REF)


def tv_from_time(time, cv, tl):
    return cv * max(0.0, time - tl) / (pp.H * pp.H)


def time_from_tv(tv, cv, tl):
    return tl + tv * pp.H * pp.H / cv


def read_xml_value(xml_path, tag, default):
    tree = ET.parse(xml_path)
    elem = tree.find(f".//{tag}")
    if elem is None:
        return default
    return float(elem.attrib["value"])


def read_timeout(xml_path):
    tree = ET.parse(xml_path)
    for param in tree.findall(".//parameter"):
        if param.attrib.get("key") == "TimeOut":
            return float(param.attrib["value"])
    raise RuntimeError(f"TimeOut not found in {xml_path}")


def load_series(folder, tout):
    data = []
    for path in sorted(folder.glob("PartFluid_*.vtk")):
        idx = pp.part_index(path)
        rows = pp.read_part_vtk(path)
        data.append({"name": path.name, "index": idx, "time": idx * tout, "rows": rows})
    if not data:
        raise RuntimeError(f"No PartFluid VTK files found in {folder}")
    return data


def terzaghi_excess(z, t_rel, cv, nterms=240):
    value = 0.0
    for n in range(nterms):
        lam = (2 * n + 1) * math.pi / (2.0 * pp.H)
        an = 2.0 * pp.Q0 * math.sin(lam * pp.H) / (pp.H * lam)
        value += an * math.cos(lam * z) * math.exp(-lam * lam * cv * t_rel)
    return value


def mean(rows, key):
    vals = [row[key] for row in rows if key in row]
    return sum(vals) / len(vals) if vals else 0.0


def top_rows(rows):
    zmax = max(row["z"] for row in rows)
    return [row for row in rows if row["z"] >= zmax - 0.55 * pp.DP]


def bottom_layer_stats(rows):
    prof = pp.layer_average(rows, "excess")
    if len(prof) < 2:
        return 0.0, 0.0
    z0, p0 = prof[0]
    z1, p1 = prof[1]
    return p0 / 1000.0, (p1 - p0) / max(1e-12, z1 - z0) / 1000.0


def layer_dict(rows, key, selector=None):
    bins = {}
    for row in rows:
        if key not in row:
            continue
        if selector is not None and not selector(row):
            continue
        iz = int(math.floor(row["z"] / pp.DP + 0.5 + 1e-6))
        bins.setdefault(iz, []).append(row)
    out = {}
    for iz, vals in bins.items():
        out[iz] = (
            sum(row["z"] for row in vals) / len(vals),
            sum(row[key] for row in vals) / len(vals),
        )
    return out


def side_center_rms(rows):
    xmin = min(row["x"] for row in rows)
    xmax = max(row["x"] for row in rows)
    xmid = 0.5 * (xmin + xmax)
    left = layer_dict(rows, "excess", lambda r: r["x"] <= xmin + 0.55 * pp.DP)
    right = layer_dict(rows, "excess", lambda r: r["x"] >= xmax - 0.55 * pp.DP)
    center = layer_dict(rows, "excess", lambda r: abs(r["x"] - xmid) <= 0.55 * pp.DP)
    diffs = []
    for iz, (_, pc) in center.items():
        vals = []
        if iz in left:
            vals.append(left[iz][1])
        if iz in right:
            vals.append(right[iz][1])
        if vals:
            diffs.append((sum(vals) / len(vals) - pc) ** 2)
    return math.sqrt(sum(diffs) / len(diffs)) / 1000.0 if diffs else 0.0


def degree_num(item, tl):
    if item["time"] < tl:
        return 0.0
    return 1.0 - mean(item["rows"], "excess") / pp.Q0


def summarize(args):
    out_dir = Path(args.output).resolve()
    vtk_dir = out_dir / "particles"
    xml_path = Path(args.xml).resolve()
    fig_dir = Path(args.figures).resolve()
    fig_dir.mkdir(parents=True, exist_ok=True)

    cv = cv_for_k(args.k)
    tl = read_xml_value(xml_path, "HydroMechTopLoadRampTime", pp.TL)
    tout = read_timeout(xml_path)
    series = load_series(vtk_dir, tout)
    final_tv = tv_from_time(series[-1]["time"], cv, tl)
    tv_tol = 0.51 * cv * tout / (pp.H * pp.H)
    target_rows = []

    for tv in TARGET_TV:
        if tv > final_tv + tv_tol:
            continue
        item = pp.nearest_snapshot(series, time_from_tv(tv, cv, tl))
        prof = pp.layer_average(item["rows"], "excess")
        actual_tv = tv_from_time(item["time"], cv, tl)
        rms = math.sqrt(sum((p - terzaghi_excess(z, max(0.0, item["time"] - tl), cv)) ** 2 for z, p in prof) / len(prof)) / 1000.0
        bottom_kpa, bottom_grad_kpa_m = bottom_layer_stats(item["rows"])
        target_rows.append({
            "label": args.label,
            "k": args.k,
            "target_tv": tv,
            "snapshot": item["name"],
            "time_s": item["time"],
            "actual_tv": actual_tv,
            "u_num": degree_num(item, tl),
            "u_theory": pp.degree_theory(actual_tv),
            "profile_rms_kpa": rms,
            "top_excess_kpa": mean(top_rows(item["rows"]), "excess") / 1000.0,
            "bottom_excess_kpa": bottom_kpa,
            "bottom_grad_kpa_per_m": bottom_grad_kpa_m,
            "side_center_rms_kpa": side_center_rms(item["rows"]),
            "max_speed": max(row.get("speed", 0.0) for row in item["rows"]),
        })

    post = [item for item in series if item["time"] >= tl]
    u_rmse = math.sqrt(sum((degree_num(item, tl) - pp.degree_theory(tv_from_time(item["time"], cv, tl))) ** 2 for item in post) / len(post))
    summary = {
        "label": args.label,
        "k": args.k,
        "snapshots": len(series),
        "final_tv": final_tv,
        "final_u_num": degree_num(series[-1], tl),
        "final_u_theory": pp.degree_theory(final_tv),
        "u_rmse": u_rmse,
        "max_speed": max(max(row.get("speed", 0.0) for row in item["rows"]) for item in series),
        "initial_particles": len(series[0]["rows"]),
        "min_particles": min(len(item["rows"]) for item in series),
    }

    targets_path = fig_dir / f"{args.label}_targets.csv"
    summary_path = fig_dir / f"{args.label}_summary.csv"
    with targets_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(target_rows[0].keys()))
        writer.writeheader()
        writer.writerows(target_rows)
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)

    tv025 = next((row for row in target_rows if abs(row["target_tv"] - 0.25) < 1e-12), None)
    if tv025:
        print(f"{args.label}: Tv0.25 RMS={tv025['profile_rms_kpa']:.6f} kPa, U={tv025['u_num']:.6f}, speed={tv025['max_speed']:.6e}")
    print(f"summary: final_Tv={summary['final_tv']:.6f}, U_RMSE={summary['u_rmse']:.6f}, max_speed={summary['max_speed']:.6e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--k", default="1e-4")
    parser.add_argument("--xml", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--figures", default=str(ROOT / "tests" / "figures"))
    summarize(parser.parse_args())


if __name__ == "__main__":
    main()
