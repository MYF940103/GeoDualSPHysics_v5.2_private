from pathlib import Path
import argparse
import csv
import importlib.util
import math
import xml.etree.ElementTree as ET

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent.parent
FIGDIR = ROOT / "figures"
POSTPROCESS = Path(__file__).resolve().parent / "postprocess_terzaghi_q0.py"

spec = importlib.util.spec_from_file_location("terzaghi_q0", POSTPROCESS)
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)

CASES = [
    ("1e-3", "k1em3"),
    ("5e-4", "k5em4"),
    ("1e-4", "k1em4"),
]

SUPPLEMENT_TV005 = {}

TARGET_TV = [0.005, 0.05, 0.1, 0.25, 0.4, 0.5, 0.7, 1.0, 1.5, 2.0]


def cv_for_k(k_text):
    return float(k_text) * pp.M_CONSTRAINED / (pp.RHO_W * pp.G_REF)


def tv_from_time(time, cv, tl):
    return cv * max(0.0, time - tl) / (pp.H * pp.H)


def time_from_tv(tv, cv, tl):
    return tl + tv * pp.H * pp.H / cv


def output_interval_for_cv(cv):
    return max(0.0025, (pp.H * pp.H / cv) / 250.0)


def case_time_out(tag, cv):
    xml_path = ROOT / f"CaseTerzaghiConsolidation_q0_PR_full_{tag}_Def.xml"
    if not xml_path.exists():
        xml_path = ROOT / "tests" / "configs" / "formal_validation" / f"CaseTerzaghiConsolidation_q0_PR_full_{tag}_Def.xml"
    if not xml_path.exists():
        return output_interval_for_cv(cv)
    tree = ET.parse(xml_path)
    for param in tree.findall(".//parameter"):
        if param.attrib.get("key") == "TimeOut":
            return float(param.attrib["value"])
    return output_interval_for_cv(cv)


def case_ramp_time(tag):
    xml_path = ROOT / f"CaseTerzaghiConsolidation_q0_PR_full_{tag}_Def.xml"
    if not xml_path.exists():
        xml_path = ROOT / "tests" / "configs" / "formal_validation" / f"CaseTerzaghiConsolidation_q0_PR_full_{tag}_Def.xml"
    if not xml_path.exists():
        return pp.TL
    tree = ET.parse(xml_path)
    elem = tree.find(".//HydroMechTopLoadRampTime")
    if elem is None:
        return pp.TL
    return float(elem.attrib["value"])


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


def max_value(rows, key):
    vals = [row[key] for row in rows if key in row]
    return max(vals) if vals else 0.0


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


def invalid_summary(k_text, tag, series, reason):
    counts = [len(item["rows"]) for item in series]
    return {
        "k": k_text,
        "tag": tag,
        "valid": False,
        "reason": reason,
        "series": series,
        "initial_particles": counts[0] if counts else 0,
        "min_particles": min(counts) if counts else 0,
        "n_snapshots": len(series),
        "final_time": series[-1]["time"] if series else 0.0,
        "final_tv": 0.0,
        "final_u_num": math.nan,
        "final_u_theory": math.nan,
        "u_rmse": math.nan,
        "settlement_mm": math.nan,
        "settlement_theory_mm": math.nan,
        "max_speed": math.nan,
        "target_rows": [],
        "cv": cv_for_k(k_text),
        "tl": pp.TL,
    }


def summarize_case(k_text, tag):
    folder = ROOT / f"CaseTerzaghiConsolidation_q0_PR_full_{tag}_out" / "particles"
    if not folder.exists():
        folder = ROOT / "tests" / "outputs" / "formal_validation" / f"CaseTerzaghiConsolidation_q0_PR_full_{tag}_out" / "particles"
    if not folder.exists():
        return None
    cv = cv_for_k(k_text)
    tl = case_ramp_time(tag)
    tout = case_time_out(tag, cv)
    series = load_series(folder, tout)
    counts = [len(item["rows"]) for item in series]
    if len(series) < 2:
        return invalid_summary(k_text, tag, series, "less than two saved fluid snapshots")
    if counts[0] <= 0:
        return invalid_summary(k_text, tag, series, "initial snapshot has no fluid particles")
    if min(counts[1:]) < 0.9 * counts[0]:
        return invalid_summary(k_text, tag, series, "fluid particles were excluded during the run")
    z0_top = pp.top_layer_z(series[0]["rows"])
    final = series[-1]
    supplement = {}
    supp_folder = SUPPLEMENT_TV005.get(tag)
    if supp_folder and supp_folder.exists():
        supp_series = load_series(supp_folder, time_from_tv(0.005, cv, tl))
        if len(supp_series) > 1:
            supplement[0.005] = supp_series[1]
    post = [item for item in series if item["time"] >= tl]
    u_rmse = math.sqrt(sum((degree_num(item, tl) - pp.degree_theory(tv_from_time(item["time"], cv, tl))) ** 2 for item in post) / len(post))
    target_rows = []
    final_tv = tv_from_time(series[-1]["time"], cv, tl)
    target_tv_tol = 0.51 * cv * tout / (pp.H * pp.H)
    for tv in TARGET_TV:
        if tv > final_tv + target_tv_tol:
            continue
        item = supplement.get(tv)
        if item is None:
            item = pp.nearest_snapshot(series, time_from_tv(tv, cv, tl))
        prof = pp.layer_average(item["rows"], "excess")
        actual_tv = tv_from_time(item["time"], cv, tl)
        rms = math.sqrt(sum((p - terzaghi_excess(z, max(0.0, item["time"] - tl), cv)) ** 2 for z, p in prof) / len(prof)) / 1000.0
        bottom_kpa, bottom_grad_kpa_m = bottom_layer_stats(item["rows"])
        target_rows.append({
            "k": k_text,
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
            "max_speed": max_value(item["rows"], "speed"),
        })
    return {
        "k": k_text,
        "tag": tag,
        "valid": True,
        "reason": "ok",
        "series": series,
        "initial_particles": counts[0],
        "min_particles": min(counts),
        "n_snapshots": len(series),
        "z0_top": z0_top,
        "final_time": final["time"],
        "final_tv": tv_from_time(final["time"], cv, tl),
        "final_u_num": degree_num(final, tl),
        "final_u_theory": pp.degree_theory(tv_from_time(final["time"], cv, tl)),
        "u_rmse": u_rmse,
        "settlement_mm": (z0_top - pp.top_layer_z(final["rows"])) * 1000.0,
        "settlement_theory_mm": pp.H * pp.Q0 * pp.MV * pp.degree_theory(tv_from_time(final["time"], cv, tl)) * 1000.0,
        "max_speed": max(max_value(item["rows"], "speed") for item in series),
        "target_rows": target_rows,
        "cv": cv,
        "tl": tl,
        "supplement": supplement,
    }


def write_csv(summaries, prefix):
    summary_path = FIGDIR / f"{prefix}_summary.csv"
    with summary_path.open("w", newline="") as f:
        fields = ["k", "valid", "reason", "n_snapshots", "initial_particles", "min_particles", "final_time", "final_tv", "final_u_num", "final_u_theory", "u_rmse", "settlement_mm", "settlement_theory_mm", "max_speed"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in summaries:
            writer.writerow({key: row[key] for key in fields})

    targets_path = FIGDIR / f"{prefix}_targets.csv"
    fields = ["k", "target_tv", "snapshot", "time_s", "actual_tv", "u_num", "u_theory", "profile_rms_kpa", "top_excess_kpa", "bottom_excess_kpa", "bottom_grad_kpa_per_m", "side_center_rms_kpa", "max_speed"]
    with targets_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in summaries:
            for target in row["target_rows"]:
                writer.writerow(target)
    return summary_path, targets_path


def series_with_supplement(row):
    items = [{"source": "formal", "item": item} for item in row["series"]]
    for tv, item in row.get("supplement", {}).items():
        items.append({"source": f"supplement_Tv{tv:g}", "item": item})
    items.sort(key=lambda x: (x["item"]["time"], x["source"]))
    return items


def write_plot_data_csv(summaries, prefix):
    history_path = FIGDIR / f"{prefix}_history_data.csv"
    history_fields = [
        "k", "source", "snapshot", "time_s", "tv",
        "u_num", "u_theory", "mean_excess_kpa",
        "settlement_mm", "settlement_theory_mm", "max_speed",
    ]
    with history_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=history_fields)
        writer.writeheader()
        for row in summaries:
            if not row["valid"]:
                continue
            for entry in series_with_supplement(row):
                item = entry["item"]
                tv = tv_from_time(item["time"], row["cv"], row["tl"])
                writer.writerow({
                    "k": row["k"],
                    "source": entry["source"],
                    "snapshot": item["name"],
                    "time_s": item["time"],
                    "tv": tv,
                    "u_num": degree_num(item, row["tl"]),
                    "u_theory": pp.degree_theory(tv) if item["time"] >= row["tl"] else 0.0,
                    "mean_excess_kpa": mean(item["rows"], "excess") / 1000.0,
                    "settlement_mm": (row["z0_top"] - pp.top_layer_z(item["rows"])) * 1000.0,
                    "settlement_theory_mm": pp.H * pp.Q0 * pp.MV * pp.degree_theory(tv) * 1000.0 if item["time"] >= row["tl"] else 0.0,
                    "max_speed": max_value(item["rows"], "speed"),
                })

    profiles_path = FIGDIR / f"{prefix}_profiles_data.csv"
    profile_fields = [
        "k", "target_tv", "actual_tv", "source", "snapshot",
        "z_m", "z_over_h", "pore_sph_pa", "pore_sph_norm",
        "pore_theory_pa", "pore_theory_norm",
    ]
    with profiles_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=profile_fields)
        writer.writeheader()
        for row in summaries:
            if not row["valid"]:
                continue
            target_tv_tol = 0.51 * row["cv"] * case_time_out(row["tag"], row["cv"]) / (pp.H * pp.H)
            target_tvs = [tv for tv in TARGET_TV if tv <= row["final_tv"] + target_tv_tol]
            for tv in target_tvs:
                source = "formal"
                item = row.get("supplement", {}).get(tv)
                if item is None:
                    item = pp.nearest_snapshot(row["series"], time_from_tv(tv, row["cv"], row["tl"]))
                else:
                    source = f"supplement_Tv{tv:g}"
                t_rel = max(0.0, item["time"] - row["tl"])
                actual_tv = tv_from_time(item["time"], row["cv"], row["tl"])
                for z, p in pp.layer_average(item["rows"], "excess"):
                    pth = terzaghi_excess(z, t_rel, row["cv"])
                    writer.writerow({
                        "k": row["k"],
                        "target_tv": tv,
                        "actual_tv": actual_tv,
                        "source": source,
                        "snapshot": item["name"],
                        "z_m": z,
                        "z_over_h": z / pp.H,
                        "pore_sph_pa": p,
                        "pore_sph_norm": p / pp.Q0,
                        "pore_theory_pa": pth,
                        "pore_theory_norm": pth / pp.Q0,
                    })
    return history_path, profiles_path


def tv_label(tv):
    return f"Tv{tv:g}".replace(".", "p").replace("-", "m")


def write_wide_data_csv(summaries, prefix):
    written = []
    target_metrics = [
        "actual_tv", "time_s", "u_num", "u_theory", "profile_rms_kpa",
        "top_excess_kpa", "bottom_excess_kpa", "bottom_grad_kpa_per_m",
        "side_center_rms_kpa", "max_speed",
    ]
    for row in summaries:
        if not row["valid"]:
            continue
        ktag = row["tag"]
        target_tvs = [target["target_tv"] for target in row["target_rows"]]

        targets_path = FIGDIR / f"{prefix}_targets_wide_{ktag}.csv"
        target_fields = ["k", "metric"] + [tv_label(tv) for tv in target_tvs]
        with targets_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=target_fields)
            writer.writeheader()
            by_tv = {target["target_tv"]: target for target in row["target_rows"]}
            for metric in target_metrics:
                out = {"k": row["k"], "metric": metric}
                for tv in target_tvs:
                    out[tv_label(tv)] = by_tv[tv][metric]
                writer.writerow(out)
        written.append(targets_path)

        profile_entries = []
        target_tv_tol = 0.51 * row["cv"] * case_time_out(row["tag"], row["cv"]) / (pp.H * pp.H)
        for tv in [t for t in TARGET_TV if t <= row["final_tv"] + target_tv_tol]:
            item = row.get("supplement", {}).get(tv)
            if item is None:
                item = pp.nearest_snapshot(row["series"], time_from_tv(tv, row["cv"], row["tl"]))
            t_rel = max(0.0, item["time"] - row["tl"])
            actual_tv = tv_from_time(item["time"], row["cv"], row["tl"])
            profile_entries.append((tv, actual_tv, item["name"], pp.layer_average(item["rows"], "excess"), t_rel))

        profiles_path = FIGDIR / f"{prefix}_profiles_wide_{ktag}.csv"
        profile_fields = ["z_m", "z_over_h"]
        for tv, _, _, _, _ in profile_entries:
            lab = tv_label(tv)
            profile_fields.extend([
                f"sph_norm_{lab}", f"theory_norm_{lab}",
                f"sph_kpa_{lab}", f"theory_kpa_{lab}",
            ])
        profile_fields.extend([f"actual_tv_{tv_label(tv)}" for tv, _, _, _, _ in profile_entries])
        profile_fields.extend([f"snapshot_{tv_label(tv)}" for tv, _, _, _, _ in profile_entries])
        with profiles_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=profile_fields)
            writer.writeheader()
            if profile_entries:
                nrows = len(profile_entries[0][3])
                for i in range(nrows):
                    z = profile_entries[0][3][i][0]
                    out = {"z_m": z, "z_over_h": z / pp.H}
                    for tv, actual_tv, snapshot, prof, t_rel in profile_entries:
                        lab = tv_label(tv)
                        p = prof[i][1]
                        pth = terzaghi_excess(prof[i][0], t_rel, row["cv"])
                        out[f"sph_norm_{lab}"] = p / pp.Q0
                        out[f"theory_norm_{lab}"] = pth / pp.Q0
                        out[f"sph_kpa_{lab}"] = p / 1000.0
                        out[f"theory_kpa_{lab}"] = pth / 1000.0
                        out[f"actual_tv_{lab}"] = actual_tv
                        out[f"snapshot_{lab}"] = snapshot
                    writer.writerow(out)
        written.append(profiles_path)
    return written


def plot_summary(summaries, prefix):
    summaries = [row for row in summaries if row["valid"]]
    if not summaries:
        return None
    tvmax = max(row["final_tv"] for row in summaries)
    fig, axes = plt.subplots(3, 1, figsize=(9.5, 9.5), sharex=True)
    for row in summaries:
        series = row["series"]
        times = [item["time"] for item in series]
        tvs = [tv_from_time(t, row["cv"], row["tl"]) for t in times]
        u_num = [degree_num(item, row["tl"]) for item in series]
        settlement = [(row["z0_top"] - pp.top_layer_z(item["rows"])) * 1000.0 for item in series]
        mean_excess = [mean(item["rows"], "excess") / 1000.0 for item in series]
        axes[0].plot(tvs, u_num, label=f"k={row['k']}")
        axes[1].plot(tvs, mean_excess, label=f"k={row['k']}")
        axes[2].plot(tvs, settlement, label=f"k={row['k']}")
    ngrid = max(200, int(math.ceil(tvmax * 200)))
    tvgrid = [tvmax * i / ngrid for i in range(ngrid + 1)]
    axes[0].plot(tvgrid, [pp.degree_theory(tv) for tv in tvgrid], "k--", label="Terzaghi")
    axes[1].set_ylabel("Mean excess p (kPa)")
    axes[0].set_ylabel("Degree U")
    axes[2].set_ylabel("Settlement (mm)")
    axes[2].set_xlabel("Tv")
    for ax in axes:
        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    path = FIGDIR / f"{prefix}_history.png"
    fig.savefig(path, dpi=180)
    plt.close(fig)
    return path


def plot_profiles(summaries, prefix):
    zgrid = [i * pp.H / 200.0 for i in range(201)]
    for row in summaries:
        if not row["valid"]:
            continue
        fig, ax = plt.subplots(figsize=(6.8, 6.2))
        target_tv_tol = 0.51 * row["cv"] * case_time_out(row["tag"], row["cv"]) / (pp.H * pp.H)
        target_tvs = [tv for tv in TARGET_TV if tv <= row["final_tv"] + target_tv_tol]
        colors = plt.cm.viridis([i / max(1, len(target_tvs) - 1) for i in range(len(target_tvs))])
        for color, tv in zip(colors, target_tvs):
            item = row.get("supplement", {}).get(tv)
            if item is None:
                item = pp.nearest_snapshot(row["series"], time_from_tv(tv, row["cv"], row["tl"]))
            prof = pp.layer_average(item["rows"], "excess")
            t_rel = max(0.0, item["time"] - row["tl"])
            actual_tv = tv_from_time(item["time"], row["cv"], row["tl"])
            label = f"Tv={actual_tv:.3g}"
            ax.plot([terzaghi_excess(z, t_rel, row["cv"]) / pp.Q0 for z in zgrid], [z / pp.H for z in zgrid], color=color, lw=1.4, label=f"{label} analytical")
            ax.plot([p / pp.Q0 for _, p in prof], [z / pp.H for z, _ in prof], "o", color=color, ms=3.0, mfc="none", label=f"{label} SPH")
        ax.set_xlabel("Normalized pore pressure $p_w/q_0$")
        ax.set_ylabel("$z/H$")
        ax.set_xlim(-0.02, 1.05)
        ax.set_ylim(0.0, 1.02)
        ax.set_title(f"q0 full validation normalized profiles, k={row['k']}")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=7, frameon=True)
        fig.tight_layout()
        path = FIGDIR / f"{prefix}_profiles_{row['tag']}.png"
        fig.savefig(path, dpi=180)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tags", nargs="+", help="Only summarize selected case tags, for example: k1em4")
    parser.add_argument("--output-prefix", default="full_validation_q0", help="Prefix for generated CSV and PNG files")
    args = parser.parse_args()

    FIGDIR.mkdir(parents=True, exist_ok=True)
    summaries = []
    for k_text, tag in CASES:
        if args.tags and tag not in args.tags:
            continue
        row = summarize_case(k_text, tag)
        if row is not None:
            summaries.append(row)
    if not summaries:
        raise RuntimeError("No completed full-validation cases found.")
    summary_path, targets_path = write_csv(summaries, args.output_prefix)
    history_data_path, profiles_data_path = write_plot_data_csv(summaries, args.output_prefix)
    wide_data_paths = write_wide_data_csv(summaries, args.output_prefix)
    history_path = plot_summary(summaries, args.output_prefix)
    plot_profiles(summaries, args.output_prefix)
    print("Full q0 validation summary")
    print("k       valid final_Tv  U_num    U_theory U_RMSE   sett_mm max_speed reason")
    for row in summaries:
        print(f"{row['k']:<7} {str(row['valid']):<5} {row['final_tv']:>8.4f} {row['final_u_num']:>8.5f} {row['final_u_theory']:>8.5f} {row['u_rmse']:>8.5f} {row['settlement_mm']:>8.3f} {row['max_speed']:>9.3e} {row['reason']}")
    print(f"Saved {summary_path}")
    print(f"Saved {targets_path}")
    print(f"Saved {history_data_path}")
    print(f"Saved {profiles_data_path}")
    for path in wide_data_paths:
        print(f"Saved {path}")
    if history_path:
        print(f"Saved {history_path}")
    else:
        print("No valid cases available for history/profile plots.")


if __name__ == "__main__":
    main()
