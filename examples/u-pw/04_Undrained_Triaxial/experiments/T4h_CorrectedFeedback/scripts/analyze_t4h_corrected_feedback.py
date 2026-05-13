#!/usr/bin/env python3
"""T4h corrected pressure-gradient feedback audit."""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

R = 0.03
H = 0.10
DP = 0.01
KERNEL_H = 0.018
KERNEL_SIZE = 2.0 * KERNEL_H
RHO0 = 2100.0
MASS = RHO0 * DP**3

CASES = [
    {"case": "CaseT4h_ConfOnly_Op1InteriorBaseline", "label": "op1 interior", "operator": 1, "mode": "excess", "class_filter": "interior", "stabilized": "off"},
    {"case": "CaseT4h_ConfOnly_Op2LSQInterior", "label": "op2 LSQ interior", "operator": 2, "mode": "excess", "class_filter": "interior", "stabilized": "off"},
    {"case": "CaseT4h_ConfOnly_Op2LSQInteriorStabilized", "label": "op2 LSQ stabilized", "operator": 2, "mode": "excess", "class_filter": "interior", "stabilized": "relax+cap"},
]


def fnum(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(str(value).strip().rstrip("."))
    except Exception:
        return default


def write_table(path: Path, rows, fieldnames=None):
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_partcsv(path: Path):
    with path.open(newline="") as f:
        reader = csv.reader(f, delimiter=";")
        header = [h.strip() for h in next(reader) if h.strip()]
        rows = []
        for raw in reader:
            if not raw:
                continue
            vals = [v.strip() for v in raw[: len(header)]]
            if len(vals) != len(header):
                continue
            rows.append({key: fnum(value) for key, value in zip(header, vals)})
        return rows


def arr(rows, key):
    return np.array([row.get(key, 0.0) for row in rows], dtype=float)


def stats(values):
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return {"mean": np.nan, "std": np.nan, "min": np.nan, "max": np.nan, "maxabs": np.nan}
    return {
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "maxabs": float(np.max(np.abs(values))),
    }


def cylinder_class(x, y, z):
    s = z
    r = np.sqrt(x * x + y * y)
    cap = 0.015
    edge = 0.015
    out = np.zeros_like(r, dtype=int)
    outside = (s < -cap) | (s > H + cap) | (r > R + edge)
    lateral = (np.abs(r - R) <= edge) & (s > cap) & (s < H - cap) & ~outside
    top = (s >= H - cap) & (s <= H + cap) & ~outside
    bottom = (s >= -cap) & (s <= cap) & ~outside
    edge_ring = ((np.abs(r - R) <= edge) & (top | bottom)) & ~outside
    interior = ~(outside | lateral | top | bottom | edge_ring)
    out[interior] = 1
    out[lateral] = 2
    out[top] = 3
    out[bottom] = 4
    out[edge_ring] = 5
    out[outside] = 6
    return out


def parse_run_out(path: Path):
    text = path.read_text(errors="ignore")
    times = {0: 0.0}
    for line in text.splitlines():
        match = re.match(r"^\s*Part_(\d{4})\s+([0-9.Ee+\-]+)\s+\d+\s+\d+\s+", line)
        if match:
            times[int(match.group(1))] = fnum(match.group(2))

    def one(pattern, default=0.0):
        match = re.search(pattern, text)
        return fnum(match.group(1), default) if match else default

    status = {
        "code": 0 if "Finished execution (code=0)" in text else 1,
        "excluded": one(r"Excluded particles\.+:\s+([0-9]+)"),
        "steps": one(r"Steps of simulation\.+:\s+([0-9]+)"),
        "part_files": one(r"PART files\.+:\s+([0-9]+)"),
        "dtmin_adjusted": one(r"DTs adjusted to DtMin\.+:\s+([0-9]+)"),
        "runtime_sec": one(r"Total Runtime\.+:\s+([0-9.Ee+\-]+)"),
    }

    conf_rows = []
    re_conf = re.compile(
        r"FlexibleConfiningStress CPU diagnostics: step=(?P<step>\d+), TimeStep=(?P<time>[-+0-9.Ee]+), p0_eff=(?P<p0_eff>[-+0-9.Ee]+) Pa, targets=(?P<targets>\d+), legacy_targets=(?P<legacy_targets>\d+), net_force=\((?P<net_fx>[-+0-9.Ee]+),(?P<net_fy>[-+0-9.Ee]+),(?P<net_fz>[-+0-9.Ee]+)\) N, total_abs_force=(?P<total_abs_force>[-+0-9.Ee]+) N, max_accel=(?P<conf_max_accel>[-+0-9.Ee]+) m/s2, com_accel=(?P<com_accel>[-+0-9.Ee]+) m/s2, symmetry_residual=(?P<symmetry_residual>[-+0-9.Ee]+)"
    )
    re_ext = re.compile(
        r"FlexibleConfiningStress extended diagnostics: step=(?P<step>\d+), fi_min=(?P<fi_min>[-+0-9.Ee]+), fi_max=(?P<fi_max>[-+0-9.Ee]+), fi_mean=(?P<fi_mean>[-+0-9.Ee]+), fi_threshold=(?P<fi_threshold>[-+0-9.Ee]+), fi_selected=(?P<fi_selected>\d+), class_interior=(?P<class_interior>\d+), class_lateral=(?P<class_lateral>\d+), class_top=(?P<class_top>\d+), class_bottom=(?P<class_bottom>\d+), class_edge=(?P<class_edge>\d+), class_outside=(?P<class_outside>\d+), lateral_fi_selected=(?P<lateral_fi_selected>\d+), cap_fi_selected=(?P<cap_fi_selected>\d+), lateral_inward_radial_accel_mean=(?P<lat_accel_mean>[-+0-9.Ee]+), lateral_inward_radial_accel_max=(?P<lat_accel_max>[-+0-9.Ee]+), cap_abs_axial_accel_mean=(?P<cap_axial_mean>[-+0-9.Ee]+), cap_abs_axial_accel_max=(?P<cap_axial_max>[-+0-9.Ee]+)"
    )
    by_step = {}
    for match in re_conf.finditer(text):
        data = {key: fnum(value) for key, value in match.groupdict().items()}
        by_step[int(data["step"])] = data
    for match in re_ext.finditer(text):
        step = int(match.group("step"))
        by_step.setdefault(step, {"step": step, "time": np.nan})
        by_step[step].update({key: fnum(value) for key, value in match.groupdict().items()})
    conf_rows = [by_step[k] for k in sorted(by_step)]

    fb_rows = []
    re_fb = re.compile(
        r"PorePressureFeedback diagnostics: step=(?P<step>\d+), TimeStep=(?P<time>[-+0-9.Ee]+), factor=(?P<factor>[-+0-9.Ee]+), applied=(?P<applied>\d+), class_skipped=(?P<class_skipped>\d+), raw_max=(?P<raw_max>[-+0-9.Ee]+), raw_mean=(?P<raw_mean>[-+0-9.Ee]+), used_max=(?P<used_max>[-+0-9.Ee]+), used_mean=(?P<used_mean>[-+0-9.Ee]+), pre_accel_max=(?P<pre_accel_max>[-+0-9.Ee]+), used_to_reference_ratio_max=(?P<ratio_max>[-+0-9.Ee]+), confining_ref=(?P<confining_ref>[-+0-9.Ee]+), limited=(?P<limited>\d+), relaxed=(?P<relaxed>\d+), cap_min=(?P<cap_min>[-+0-9.Ee]+)"
    )
    re_fb_class = re.compile(
        r"PorePressureFeedback class diagnostics: step=(?P<step>\d+), lateral_used_max=(?P<lateral_used_max>[-+0-9.Ee]+), cap_edge_used_max=(?P<cap_edge_used_max>[-+0-9.Ee]+), interior_used_max=(?P<interior_used_max>[-+0-9.Ee]+)"
    )
    re_fb_lsq = re.compile(
        r"PorePressureFeedback LSQ diagnostics: step=(?P<step>\d+), solved=(?P<lsq_solved>\d+), fallback=(?P<lsq_fallback>\d+), cond_min=(?P<lsq_cond_min>[-+0-9.Ee]+), cond_mean=(?P<lsq_cond_mean>[-+0-9.Ee]+), cond_max=(?P<lsq_cond_max>[-+0-9.Ee]+)"
    )
    by_fb = {}
    for match in re_fb.finditer(text):
        data = {key: fnum(value) for key, value in match.groupdict().items()}
        by_fb[int(data["step"])] = data
    for match in re_fb_class.finditer(text):
        step = int(match.group("step"))
        by_fb.setdefault(step, {"step": step, "time": np.nan})
        by_fb[step].update({key: fnum(value) for key, value in match.groupdict().items()})
    for match in re_fb_lsq.finditer(text):
        step = int(match.group("step"))
        by_fb.setdefault(step, {"step": step, "time": np.nan})
        by_fb[step].update({key: fnum(value) for key, value in match.groupdict().items()})
    fb_rows = [by_fb[k] for k in sorted(by_fb)]
    return times, status, conf_rows, fb_rows


def region_masks(rows):
    x, y, z = arr(rows, "Pos.x [m]"), arr(rows, "Pos.y [m]"), arr(rows, "Pos.z [m]")
    r = np.sqrt(x * x + y * y)
    return {
        "all": np.ones(len(rows), dtype=bool),
        "center_core": (r <= 0.015) & (z >= 0.025) & (z <= 0.075),
        "interior_class": cylinder_class(x, y, z) == 1,
        "lateral_class": cylinder_class(x, y, z) == 2,
        "cap_edge_class": np.isin(cylinder_class(x, y, z), [3, 4, 5]),
    }


def analyse_case(meta):
    case = meta["case"]
    out = ROOT / f"{case}_out"
    data_dir = out / "data"
    times, status, conf_rows, fb_rows = parse_run_out(out / "Run.out")
    frames = []
    regions = []
    for csv_path in sorted(data_dir.glob("PartCsv_*.csv")):
        part = int(csv_path.stem.split("_")[-1])
        rows = read_partcsv(csv_path)
        masks = region_masks(rows)
        p = arr(rows, "PorePress")
        ex = arr(rows, "ExcessPorePress")
        pr = arr(rows, "PorePressRate")
        div = arr(rows, "DivVel")
        vx, vy, vz = arr(rows, "Vel.x [m/s]"), arr(rows, "Vel.y [m/s]"), arr(rows, "Vel.z [m/s]")
        vel = np.sqrt(vx * vx + vy * vy + vz * vz)
        kp = arr(rows, "Kplastic")
        frames.append({
            **meta,
            "time": times.get(part, np.nan),
            "part": part,
            "porepress_mean": stats(p)["mean"],
            "porepress_min": stats(p)["min"],
            "porepress_max": stats(p)["max"],
            "excess_mean": stats(ex)["mean"],
            "porepressrate_mean": stats(pr)["mean"],
            "porepressrate_maxabs": stats(pr)["maxabs"],
            "divvel_mean": stats(div)["mean"],
            "divvel_maxabs": stats(div)["maxabs"],
            "velocity_max": stats(vel)["max"],
            "kplastic_max": stats(kp)["max"],
            "negative_pressure_count": int(np.sum(p < 0.0)),
        })
        for region, mask in masks.items():
            regions.append({
                **meta,
                "time": times.get(part, np.nan),
                "part": part,
                "region": region,
                "count": int(mask.sum()),
                "porepress_mean": stats(p[mask])["mean"],
                "porepress_min": stats(p[mask])["min"],
                "porepress_max": stats(p[mask])["max"],
                "porepressrate_mean": stats(pr[mask])["mean"],
                "porepressrate_maxabs": stats(pr[mask])["maxabs"],
                "divvel_mean": stats(div[mask])["mean"],
                "divvel_maxabs": stats(div[mask])["maxabs"],
                "velocity_max": stats(vel[mask])["max"],
            })
    for row in conf_rows:
        row.update(meta)
    for row in fb_rows:
        row.update(meta)
    return status, frames, regions, conf_rows, fb_rows


def wendland_fac(rr2):
    rad = math.sqrt(rr2)
    if rad <= 0.0 or rad > KERNEL_SIZE:
        return 0.0
    qq = rad / KERNEL_H
    wqq1 = 1.0 - 0.5 * qq
    bwen = -2.08891 / (KERNEL_H**4)
    return bwen * qq * wqq1**3 / rad


def wendland_wab(rr2):
    rad = math.sqrt(rr2)
    if rad > KERNEL_SIZE:
        return 0.0
    qq = rad / KERNEL_H
    awen = 0.41778 / (KERNEL_H**3)
    wqq = qq + qq + 1.0
    wqq1 = 1.0 - 0.5 * qq
    return awen * wqq * (wqq1**4)


def feedback_accel(pos, rho, pressure, operator):
    n = len(pressure)
    acc = np.zeros((n, 3), dtype=float)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            dr = pos[i] - pos[j]
            rr2 = float(np.dot(dr, dr))
            if rr2 <= KERNEL_SIZE * KERNEL_SIZE and rr2 > 1e-12:
                fac = wendland_fac(rr2)
                grad = fac * dr
                if operator == 2:
                    continue
                if operator == 1:
                    coef = -MASS * (pressure[j] - pressure[i]) / (rho[i] * rho[j])
                else:
                    coef = -MASS * (pressure[i] + pressure[j]) / (rho[i] * rho[j])
                acc[i] += coef * grad
    if operator == 2:
        vol = MASS / rho
        for i in range(n):
            amat = np.zeros((3, 3), dtype=float)
            bvec = np.zeros(3, dtype=float)
            for j in range(n):
                if i == j:
                    continue
                dx = pos[j] - pos[i]
                rr2 = float(np.dot(dx, dx))
                if rr2 <= KERNEL_SIZE * KERNEL_SIZE and rr2 > 1e-12:
                    w = vol[j] * wendland_wab(rr2)
                    dp = pressure[j] - pressure[i]
                    amat += w * np.outer(dx, dx)
                    bvec += w * dp * dx
            try:
                grad = np.linalg.solve(amat, bvec)
                acc[i] = -grad / rho[i]
            except np.linalg.LinAlgError:
                acc[i] = 0.0
    return acc


def manufactured_tests():
    rows = read_partcsv(ROOT / "CaseT4h_ConfOnly_Op1InteriorBaseline_out" / "data" / "PartCsv_0000.csv")
    pos = np.column_stack([arr(rows, "Pos.x [m]"), arr(rows, "Pos.y [m]"), arr(rows, "Pos.z [m]")])
    rho = arr(rows, "Rhop [kg/m^3]")
    cls = cylinder_class(pos[:, 0], pos[:, 1], pos[:, 2])
    radius = np.sqrt(pos[:, 0] ** 2 + pos[:, 1] ** 2)
    fields = {
        "uniform_1000": np.full(len(rows), 1000.0),
        "linear_x_1000PaPerM": 1000.0 * pos[:, 0],
        "radial_linear": 1000.0 * radius / R,
        "center_bump": 1000.0 * np.exp(-(radius / 0.015) ** 2),
    }
    out = []
    for field, pressure in fields.items():
        for op in [1, 2]:
            acc = feedback_accel(pos, rho, pressure, op)
            mag = np.linalg.norm(acc, axis=1)
            net = np.sum(acc * MASS, axis=0)
            if field.startswith("linear_x"):
                expected = np.array([-1000.0 / RHO0, 0.0, 0.0])
                err = acc - expected
                sign_metric = float(np.nanmean(acc[:, 0]))
            elif field == "radial_linear":
                radial = np.column_stack([np.divide(pos[:, 0], radius, out=np.zeros_like(radius), where=radius > 0), np.divide(pos[:, 1], radius, out=np.zeros_like(radius), where=radius > 0), np.zeros_like(radius)])
                sign_metric = float(np.nanmean(np.sum(acc * radial, axis=1)))
                err = np.zeros_like(acc)
            elif field == "center_bump":
                radial = np.column_stack([np.divide(pos[:, 0], radius, out=np.zeros_like(radius), where=radius > 0), np.divide(pos[:, 1], radius, out=np.zeros_like(radius), where=radius > 0), np.zeros_like(radius)])
                sign_metric = float(np.nanmean(np.sum(acc * radial, axis=1)))
                err = np.zeros_like(acc)
            else:
                err = acc
                sign_metric = float(np.nanmax(mag))
            for name, mask in {
                "all": np.ones(len(rows), dtype=bool),
                "interior": cls == 1,
                "lateral": cls == 2,
                "cap_edge": np.isin(cls, [3, 4, 5]),
            }.items():
                out.append({
                    "field": field,
                    "operator": op,
                    "region": name,
                    "count": int(mask.sum()),
                    "accel_max": stats(mag[mask])["max"],
                    "accel_mean": stats(mag[mask])["mean"],
                    "error_maxabs": stats(np.linalg.norm(err[mask], axis=1))["maxabs"],
                    "error_mean": stats(np.linalg.norm(err[mask], axis=1))["mean"],
                    "net_fx": float(net[0]),
                    "net_fy": float(net[1]),
                    "net_fz": float(net[2]),
                    "sign_metric": sign_metric,
                })
    write_table(ROOT / "t4h_manufactured_feedback_metrics.csv", out)
    return out


def plot_lines(rows, ykey, title, fname, ylabel=None, filter_region=None):
    plt.figure(figsize=(7.2, 4.6))
    for meta in CASES:
        cr = [r for r in rows if r["case"] == meta["case"]]
        if filter_region:
            cr = [r for r in cr if r.get("region") == filter_region]
        if not cr:
            continue
        plt.plot([r["time"] for r in cr], [r.get(ykey, np.nan) for r in cr], marker="o", linewidth=1.4, label=meta["label"])
    plt.title(title)
    plt.xlabel("time [s]")
    plt.ylabel(ylabel or ykey)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=8)
    plt.tight_layout()
    for ext in ("png", "svg"):
        plt.savefig(FIG / f"{fname}.{ext}")
    plt.close()


def main():
    manufactured = manufactured_tests()
    statuses, all_frames, all_regions, all_conf, all_fb = [], [], [], [], []
    for meta in CASES:
        status, frames, regions, conf_rows, fb_rows = analyse_case(meta)
        final = frames[-1] if frames else {}
        center = [r for r in regions if r["case"] == meta["case"] and r["region"] == "center_core"]
        reversal = next((r["time"] for r in center if r["porepress_mean"] < 0.0), np.nan)
        statuses.append({
            **meta,
            **status,
            "frame_count": len(frames),
            "max_porepressrate": max((r["porepressrate_maxabs"] for r in frames), default=np.nan),
            "max_velocity": max((r["velocity_max"] for r in frames), default=np.nan),
            "final_porepress_mean": final.get("porepress_mean", np.nan),
            "final_porepress_min": final.get("porepress_min", np.nan),
            "negative_pressure_count_final": final.get("negative_pressure_count", np.nan),
            "center_reversal_time": reversal,
            "kplastic_max": max((r["kplastic_max"] for r in frames), default=np.nan),
        })
        all_frames.extend(frames)
        all_regions.extend(regions)
        all_conf.extend(conf_rows)
        all_fb.extend(fb_rows)

    lsq_rows = [r for r in all_fb if r.get("lsq_solved") is not None or r.get("lsq_fallback") is not None]
    write_table(ROOT / "t4h_case_summary.csv", statuses)
    write_table(ROOT / "t4h_feedback_acceleration_metrics.csv", all_fb)
    write_table(ROOT / "t4h_lsq_condition_metrics.csv", lsq_rows)
    write_table(ROOT / "t4h_reversal_metrics.csv", [{"case": s["case"], "label": s["label"], "center_reversal_time": s["center_reversal_time"], "negative_pressure_count_final": s["negative_pressure_count_final"], "final_porepress_min": s["final_porepress_min"]} for s in statuses])
    write_table(ROOT / "t4h_porepressrate_metrics.csv", [{"case": s["case"], "label": s["label"], "max_porepressrate": s["max_porepressrate"], "max_velocity": s["max_velocity"], "dtmin_adjusted": s["dtmin_adjusted"], "excluded": s["excluded"]} for s in statuses])
    write_table(ROOT / "t4h_operator_comparison_metrics.csv", statuses)
    write_table(ROOT / "t4h_confinement_diagnostics.csv", all_conf)
    write_table(ROOT / "t4h_measurement_region_metrics.csv", all_regions)

    plot_lines(all_frames, "porepressrate_maxabs", "PorePressRate maxAbs", "t4h_porepressrate_maxabs", "PorePressRate maxAbs [Pa/s]")
    plot_lines(all_frames, "velocity_max", "Velocity max", "t4h_velocity_max", "velocity max [m/s]")
    plot_lines(all_regions, "porepress_mean", "Center-core pore pressure", "t4h_center_porepress", "PorePress [Pa]", "center_core")
    plot_lines(all_regions, "porepressrate_maxabs", "Center-core PorePressRate", "t4h_center_porepressrate", "PorePressRate [Pa/s]", "center_core")
    plot_lines(all_fb, "used_max", "Feedback acceleration used max", "t4h_feedback_used_max", "acceleration [m/s2]")
    plot_lines(all_fb, "interior_used_max", "Feedback acceleration by class: interior", "t4h_feedback_interior_class", "acceleration [m/s2]")
    plot_lines(all_conf, "cap_axial_max", "Cap leakage diagnostic", "t4h_cap_leakage", "cap axial accel [m/s2]")
    plot_lines(all_conf, "lat_accel_mean", "Lateral confinement acceleration", "t4h_lateral_acceleration", "inward radial accel [m/s2]")
    plot_lines(all_fb, "lsq_cond_max", "LSQ condition proxy max", "t4h_lsq_condition", "condition proxy")

    plt.figure(figsize=(7.2, 4.6))
    labels = [s["label"] for s in statuses]
    values = [s["max_porepressrate"] for s in statuses]
    plt.bar(labels, values)
    plt.yscale("log")
    plt.xticks(rotation=35, ha="right")
    plt.ylabel("max |PorePressRate| [Pa/s]")
    plt.title("Feedback variant stability")
    plt.tight_layout()
    for ext in ("png", "svg"):
        plt.savefig(FIG / f"t4h_variant_porepressrate_bar.{ext}")
    plt.close()

    man = [r for r in manufactured if r["region"] == "all"]
    plt.figure(figsize=(7.2, 4.6))
    x = np.arange(len(man))
    plt.bar(x, [r["accel_max"] for r in man])
    plt.yscale("log")
    plt.xticks(x, [f"{r['field']} op{r['operator']}" for r in man], rotation=45, ha="right", fontsize=8)
    plt.ylabel("max acceleration [m/s2]")
    plt.title("Manufactured feedback acceleration")
    plt.tight_layout()
    for ext in ("png", "svg"):
        plt.savefig(FIG / f"t4h_manufactured_feedback_accel.{ext}")
    plt.close()


if __name__ == "__main__":
    main()
