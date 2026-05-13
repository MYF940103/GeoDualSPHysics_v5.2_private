#!/usr/bin/env python3
"""T4n2 restart/equilibrium audit for the reduced triaxial specimen."""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIGDIR = ROOT / "figures"
FIGDIR.mkdir(exist_ok=True)

CASES = {
    "stageA": "CaseT4n2_StageA_AllSurface_FeedbackOff",
    "stageB_restart": "CaseT4n2_StageB_Restart_Lateral_FeedbackOff",
    "fresh_lateral": "CaseT4n2_Fresh_Lateral_FeedbackOff",
    "stageC_feedback": "CaseT4n2_StageC_Restart_Lateral_FeedbackDelayed",
}

RADIUS = 0.03
HEIGHT = 0.10
CAP_EXCL = 0.015
EDGE_EXCL = 0.015
T4N_INSTANT_SWITCH_FINAL_Q = 46.29


def fnum(row: dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def normalize_headers(headers: list[str]) -> list[str]:
    return [h.strip() for h in headers if h.strip()]


def read_part(path: Path) -> list[dict[str, float]]:
    with path.open(newline="") as f:
        reader = csv.reader(f, delimiter=";")
        raw_headers = next(reader)
        headers = normalize_headers(raw_headers)
        rows = []
        for raw in reader:
            vals = raw[: len(headers)]
            if len(vals) < len(headers):
                continue
            d: dict[str, float] = {}
            for h, v in zip(headers, vals):
                if h == "Idp":
                    d[h] = int(float(v))
                else:
                    d[h] = float(v)
            rows.append(d)
        return rows


def part_files(case: str) -> list[Path]:
    data = ROOT / f"{case}_out" / "data"
    return sorted(data.glob("PartCsv_*.csv"))


def part_index(path: Path) -> int:
    return int(path.stem.split("_")[-1])


def classify(row: dict[str, float]) -> str:
    x = row["Pos.x [m]"]
    y = row["Pos.y [m]"]
    z = row["Pos.z [m]"]
    r = math.hypot(x, y)
    cap_zone = z <= CAP_EXCL or z >= HEIGHT - CAP_EXCL
    radial_edge = r >= RADIUS - EDGE_EXCL
    if cap_zone and radial_edge:
        return "edge"
    if z <= CAP_EXCL:
        return "bottom_cap"
    if z >= HEIGHT - CAP_EXCL:
        return "top_cap"
    if radial_edge:
        return "lateral"
    return "interior"


def q_proxy(row: dict[str, float]) -> float:
    sxx = row["Sigma_kk.x"]
    syy = row["Sigma_kk.y"]
    szz = row["Sigma_kk.z"]
    sxy = row["Sigma_ij.x"]
    syz = row["Sigma_ij.y"]
    sxz = row["Sigma_ij.z"]
    j2_like = 0.5 * ((sxx - syy) ** 2 + (syy - szz) ** 2 + (szz - sxx) ** 2)
    j2_like += 3.0 * (sxy * sxy + syz * syz + sxz * sxz)
    return math.sqrt(max(0.0, j2_like))


def p_eff(row: dict[str, float]) -> float:
    return -(row["Sigma_kk.x"] + row["Sigma_kk.y"] + row["Sigma_kk.z"]) / 3.0


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def maxabs(values: list[float]) -> float:
    return max((abs(v) for v in values), default=0.0)


def frame_metrics(case_key: str, case: str) -> list[dict[str, float | str]]:
    rows_out: list[dict[str, float | str]] = []
    for pf in part_files(case):
        rows = read_part(pf)
        idx = part_index(pf)
        vel = [math.sqrt(r["Vel.x [m/s]"] ** 2 + r["Vel.y [m/s]"] ** 2 + r["Vel.z [m/s]"] ** 2) for r in rows]
        pp = [r["PorePress"] for r in rows]
        ppr = [r.get("PorePressRate", 0.0) for r in rows]
        divv = [r.get("DivVel", 0.0) for r in rows]
        qv = [q_proxy(r) for r in rows]
        pv = [p_eff(r) for r in rows]
        kp = [r.get("Kplastic", 0.0) for r in rows]
        cls = {c: [] for c in ("interior", "lateral", "top_cap", "bottom_cap", "edge")}
        for r in rows:
            cls[classify(r)].append(r)
        region_q = {f"q_{c}": mean([q_proxy(r) for r in rs]) for c, rs in cls.items()}
        region_p = {f"p_eff_{c}": mean([p_eff(r) for r in rs]) for c, rs in cls.items()}
        rows_out.append(
            {
                "case": case,
                "case_key": case_key,
                "part": idx,
                "n": len(rows),
                "velocity_max": max(vel, default=0.0),
                "divvel_maxabs": maxabs(divv),
                "divvel_mean": mean(divv),
                "porepressrate_maxabs": maxabs(ppr),
                "porepress_mean": mean(pp),
                "porepress_min": min(pp, default=0.0),
                "porepress_max": max(pp, default=0.0),
                "negative_pressure_count": sum(1 for v in pp if v < 0.0),
                "p_eff_mean": mean(pv),
                "q_mean": mean(qv),
                "kplastic_max": max(kp, default=0.0),
                **region_q,
                **region_p,
            }
        )
    return rows_out


def parse_run(case: str) -> dict[str, float | str]:
    out = ROOT / f"{case}_out" / "Run.out"
    text = out.read_text(errors="ignore") if out.exists() else ""
    def grab(pattern: str, default: float = 0.0) -> float:
        m = re.search(pattern, text)
        return float(m.group(1)) if m else default
    return {
        "case": case,
        "code": grab(r"Finished execution \(code=(\d+)\)"),
        "excluded": grab(r"Excluded particles\.+:\s+(\d+)"),
        "dtmin_adjustments": grab(r"DTs adjusted to DtMin\.+:\s+(\d+)"),
        "steps": grab(r"Steps of simulation\.+:\s+(\d+)"),
        "restart_soil_restored": "Restart soil state restored" in text,
        "restart_porepress_restored": "Restart pore-pressure state restored" in text,
        "initialstress_ignored_on_restart": "InitialStressMode=1 is ignored on restart" in text,
    }


def parse_diagnostics(case: str) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    out = ROOT / f"{case}_out" / "Run.out"
    text = out.read_text(errors="ignore") if out.exists() else ""
    conf_rows: list[dict[str, object]] = []
    fb_rows: list[dict[str, object]] = []
    conf_re = re.compile(
        r"FlexibleConfiningStress CPU diagnostics: step=(?P<step>\d+), TimeStep=(?P<time>[-+0-9.eE]+), "
        r"p0_eff=(?P<p0>[-+0-9.eE]+) Pa, targets=(?P<targets>\d+), legacy_targets=(?P<legacy>\d+), "
        r".*?max_accel=(?P<maxacc>[-+0-9.eE]+) m/s2, com_accel=(?P<com>[-+0-9.eE]+) m/s2, "
        r"symmetry_residual=(?P<sym>[-+0-9.eE]+), lateral_selector_active=(?P<lat>\d+)"
    )
    fb_re = re.compile(
        r"PorePressureFeedback diagnostics: step=(?P<step>\d+), TimeStep=(?P<time>[-+0-9.eE]+), "
        r"factor=(?P<factor>[-+0-9.eE]+), applied=(?P<applied>\d+), class_skipped=(?P<skipped>\d+), "
        r"raw_max=(?P<rawmax>[-+0-9.eE]+), raw_mean=(?P<rawmean>[-+0-9.eE]+), "
        r"used_max=(?P<usedmax>[-+0-9.eE]+), used_mean=(?P<usedmean>[-+0-9.eE]+), "
        r"pre_accel_max=(?P<premax>[-+0-9.eE]+), used_to_reference_ratio_max=(?P<ratio>[-+0-9.eE]+), "
        r"confining_ref=(?P<confref>[-+0-9.eE]+), limited=(?P<limited>\d+), relaxed=(?P<relaxed>\d+), cap_min=(?P<capmin>[-+0-9.eE]+)"
    )
    for m in conf_re.finditer(text):
        conf_rows.append(
            {
                "case": case,
                "step": int(m.group("step")),
                "time": float(m.group("time")),
                "p0_eff": float(m.group("p0")),
                "targets": int(m.group("targets")),
                "legacy_targets": int(m.group("legacy")),
                "max_confining_accel": float(m.group("maxacc")),
                "com_accel": float(m.group("com")),
                "symmetry_residual": float(m.group("sym")),
                "lateral_selector_active": int(m.group("lat")),
            }
        )
    for m in fb_re.finditer(text):
        fb_rows.append(
            {
                "case": case,
                "step": int(m.group("step")),
                "time": float(m.group("time")),
                "feedback_factor": float(m.group("factor")),
                "applied": int(m.group("applied")),
                "class_skipped": int(m.group("skipped")),
                "raw_max": float(m.group("rawmax")),
                "raw_mean": float(m.group("rawmean")),
                "used_max": float(m.group("usedmax")),
                "used_mean": float(m.group("usedmean")),
                "pre_accel_max": float(m.group("premax")),
                "used_to_reference_ratio_max": float(m.group("ratio")),
                "confining_ref": float(m.group("confref")),
                "limited": int(m.group("limited")),
                "relaxed": int(m.group("relaxed")),
                "cap_min": float(m.group("capmin")),
            }
        )
    return conf_rows, fb_rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("")
        return
    keys: list[str] = []
    for row in rows:
        for k in row:
            if k not in keys:
                keys.append(k)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, keys)
        writer.writeheader()
        writer.writerows(rows)


def continuity(stage_a_case: str, stage_b_case: str) -> list[dict[str, object]]:
    a = read_part(ROOT / f"{stage_a_case}_out" / "data" / "PartCsv_0023.csv")
    b = read_part(ROOT / f"{stage_b_case}_out" / "data" / "PartCsv_0023.csv")
    amap = {int(r["Idp"]): r for r in a}
    bmap = {int(r["Idp"]): r for r in b}
    keys = [
        "Pos.x [m]",
        "Pos.y [m]",
        "Pos.z [m]",
        "Vel.x [m/s]",
        "Vel.y [m/s]",
        "Vel.z [m/s]",
        "Rhop [kg/m^3]",
        "Sigma_kk.x",
        "Sigma_kk.y",
        "Sigma_kk.z",
        "Sigma_ij.x",
        "Sigma_ij.y",
        "Sigma_ij.z",
        "Kplastic",
        "PorePress",
    ]
    out = []
    ids = sorted(set(amap) & set(bmap))
    for key in keys:
        diffs = [bmap[i][key] - amap[i][key] for i in ids]
        out.append({"field": key, "count": len(ids), "max_abs_diff": maxabs(diffs), "mean_abs_diff": mean([abs(v) for v in diffs])})
    out.append({"field": "p_eff_mean", "count": len(ids), "max_abs_diff": abs(mean([p_eff(bmap[i]) for i in ids]) - mean([p_eff(amap[i]) for i in ids])), "mean_abs_diff": ""})
    out.append({"field": "q_mean", "count": len(ids), "max_abs_diff": abs(mean([q_proxy(bmap[i]) for i in ids]) - mean([q_proxy(amap[i]) for i in ids])), "mean_abs_diff": ""})
    return out


def make_figures(all_metrics: list[dict[str, object]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    by_case: dict[str, list[dict[str, object]]] = {}
    for row in all_metrics:
        by_case.setdefault(str(row["case"]), []).append(row)
    for rows in by_case.values():
        rows.sort(key=lambda r: float(r["part"]))

    def plot_metric(metric: str, ylabel: str, stem: str) -> None:
        plt.figure(figsize=(7, 4))
        for case, rows in by_case.items():
            x = [float(r["part"]) for r in rows]
            y = [float(r[metric]) for r in rows]
            plt.plot(x, y, marker="o", markersize=2, label=case.replace("CaseT4n2_", ""))
        plt.xlabel("PART index")
        plt.ylabel(ylabel)
        plt.legend(fontsize=7)
        plt.tight_layout()
        for ext in ("png", "svg"):
            plt.savefig(FIGDIR / f"{stem}.{ext}")
        plt.close()

    plot_metric("p_eff_mean", "p' proxy [Pa]", "t4n2_p_eff_vs_part")
    plot_metric("q_mean", "q proxy [Pa]", "t4n2_q_vs_part")
    plot_metric("velocity_max", "max velocity [m/s]", "t4n2_velocity_max_vs_part")
    plot_metric("divvel_maxabs", "max |DivVel| [1/s]", "t4n2_divvel_maxabs_vs_part")
    plot_metric("porepressrate_maxabs", "max |PorePressRate| [Pa/s]", "t4n2_porepressrate_maxabs_vs_part")
    plot_metric("porepress_mean", "mean pore pressure [Pa]", "t4n2_porepress_mean_vs_part")
    plot_metric("negative_pressure_count", "negative-pressure particles", "t4n2_negative_pressure_count_vs_part")


def main() -> None:
    all_metrics: list[dict[str, object]] = []
    for key, case in CASES.items():
        all_metrics.extend(frame_metrics(key, case))
    write_csv(ROOT / "t4n2_stageA_equilibrium_metrics.csv", [r for r in all_metrics if r["case_key"] == "stageA"])
    write_csv(ROOT / "t4n2_stageB_switch_metrics.csv", [r for r in all_metrics if r["case_key"] == "stageB_restart"])
    write_csv(ROOT / "t4n2_feedback_gate_metrics.csv", [r for r in all_metrics if r["case_key"] == "stageC_feedback"])
    write_csv(ROOT / "t4n2_restart_vs_fresh_comparison.csv", [r for r in all_metrics if r["case_key"] in ("stageB_restart", "fresh_lateral")])
    write_csv(ROOT / "t4n2_restart_state_continuity.csv", continuity(CASES["stageA"], CASES["stageB_restart"]))

    summaries = []
    conf_diag: list[dict[str, object]] = []
    fb_diag: list[dict[str, object]] = []
    for key, case in CASES.items():
        crows, frows = parse_diagnostics(case)
        conf_diag.extend(crows)
        fb_diag.extend(frows)
        rows = [r for r in all_metrics if r["case_key"] == key]
        final = rows[-1] if rows else {}
        first = rows[0] if rows else {}
        run = parse_run(case)
        summaries.append(
            {
                **run,
                "case_key": key,
                "frames": len(rows),
                "first_part": first.get("part", ""),
                "final_part": final.get("part", ""),
                "final_p_eff_mean": final.get("p_eff_mean", ""),
                "final_q_mean": final.get("q_mean", ""),
                "final_porepress_mean": final.get("porepress_mean", ""),
                "final_porepress_min": final.get("porepress_min", ""),
                "final_negative_pressure_count": final.get("negative_pressure_count", ""),
                "porepressrate_maxabs_all": max((float(r["porepressrate_maxabs"]) for r in rows), default=0.0),
                "velocity_max_all": max((float(r["velocity_max"]) for r in rows), default=0.0),
                "divvel_maxabs_all": max((float(r["divvel_maxabs"]) for r in rows), default=0.0),
                "kplastic_max_all": max((float(r["kplastic_max"]) for r in rows), default=0.0),
                "q_change_from_first": float(final.get("q_mean", 0.0)) - float(first.get("q_mean", 0.0)) if rows else "",
                "stageB_final_q_vs_t4n_instant_switch": (float(final.get("q_mean", 0.0)) - T4N_INSTANT_SWITCH_FINAL_Q) if key == "stageB_restart" and rows else "",
            }
        )
    write_csv(ROOT / "t4n2_case_summary.csv", summaries)
    write_csv(ROOT / "t4n2_selector_stage_metrics.csv", conf_diag)
    write_csv(ROOT / "t4n2_feedback_diagnostics.csv", fb_diag)
    make_figures(all_metrics)


if __name__ == "__main__":
    main()
