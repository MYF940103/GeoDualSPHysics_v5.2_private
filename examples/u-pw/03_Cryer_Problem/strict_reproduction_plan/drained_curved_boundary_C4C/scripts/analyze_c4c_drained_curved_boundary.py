#!/usr/bin/env python3
"""Analyze C4-C drained curved pore-pressure boundary smoke outputs."""

from __future__ import annotations

import csv
import math
import re
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RADIUS = 0.05
SURFACE_FRAC = 0.85
INTERIOR_FRAC = 0.50
CASES = [
    ("zero", "CaseC4C_CurvedDrained_Zero"),
    ("diffusion", "CaseC4C_CurvedDrained_Diffusion"),
    ("compression", "CaseC4C_CurvedDrained_Compression"),
]


CURVED_RE = re.compile(
    r"CPU curved drained pore-pressure boundary: active=(?P<active>\w+), "
    r"center=\((?P<cx>[-+0-9.eE]+),(?P<cy>[-+0-9.eE]+),(?P<cz>[-+0-9.eE]+)\), "
    r"radius=(?P<radius>[-+0-9.eE]+), shell_thickness=(?P<thick>[-+0-9.eE]+), "
    r"target_mk=(?P<target>[-+0-9]+), value=(?P<value>[-+0-9.eE]+) Pa, "
    r"value_type=(?P<vtype>\w+), affected=(?P<affected>\d+), skipped=(?P<skipped>\d+), "
    r"radius_range=\[(?P<rmin>[-+0-9.eE]+),(?P<rmax>[-+0-9.eE]+)\], "
    r"boundary_residual_max=(?P<resid>[-+0-9.eE]+) Pa"
)

CONF_RE = re.compile(
    r"FlexibleConfiningStress CPU diagnostics: step=(?P<step>[-+0-9.eE]+), "
    r"TimeStep=(?P<time>[-+0-9.eE]+), p0_eff=(?P<p0>[-+0-9.eE]+) Pa, "
    r"targets=(?P<targets>\d+), net_force=\((?P<fx>[-+0-9.eE]+),(?P<fy>[-+0-9.eE]+),(?P<fz>[-+0-9.eE]+)\) N, "
    r"total_abs_force=(?P<fabs>[-+0-9.eE]+) N, max_accel=(?P<amax>[-+0-9.eE]+) m/s2, "
    r"com_accel=(?P<acom>[-+0-9.eE]+) m/s2, symmetry_residual=(?P<sym>[-+0-9.eE]+)"
)


def fnum(value: object, default: float = math.nan) -> float:
    try:
        return float(str(value).strip().rstrip("."))
    except Exception:
        return default


def split_line(line: str) -> list[str]:
    sep = ";" if ";" in line else ","
    return [v.strip() for v in line.strip().split(sep)]


def find_col(headers: list[str], candidates: tuple[str, ...]) -> int | None:
    lower = [h.lower().split()[0] if h.strip() else "" for h in headers]
    for cand in candidates:
        cl = cand.lower()
        for i, header in enumerate(lower):
            if header == cl:
                return i
            if len(cl) > 1 and (header.endswith("." + cl) or header.endswith("_" + cl)):
                return i
    return None


def read_runout(case_name: str) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]], dict[int, float]]:
    runout = ROOT / f"{case_name}_cpu_out" / "Run.out"
    meta: dict[str, object] = {"runout_exists": runout.exists(), "code": "unknown", "excluded": "unknown"}
    curved: list[dict[str, object]] = []
    conf: list[dict[str, object]] = []
    times: dict[int, float] = {0: 0.0}
    if not runout.exists():
        return meta, curved, conf, times
    text = runout.read_text(errors="ignore")
    meta["code"] = 0 if ("Finished execution" in text or "Execution finished" in text) else "unknown"
    m = re.search(r"Excluded particles\.*:\s*(\d+)", text)
    if not m:
        m = re.search(r"Particles out:\s*(\d+)", text)
    if m:
        meta["excluded"] = int(m.group(1))
    m = re.search(r"Steps of simulation\.*:\s*(\d+)", text)
    if m:
        meta["steps"] = int(m.group(1))
    m = re.search(r"Total Runtime\.*:\s*([-+0-9.eE]+)", text)
    if m:
        meta["runtime_sec"] = fnum(m.group(1))
    for match in re.finditer(r"Part_(?P<idx>\d{4})\s+(?P<time>[-+0-9.eE]*\.[-+0-9.eE]+)\s+\d+", text):
        times[int(match.group("idx"))] = fnum(match.group("time"))
    for i, match in enumerate(CURVED_RE.finditer(text)):
        row = {k: fnum(v) for k, v in match.groupdict().items() if k not in ("active", "vtype")}
        row["active"] = match.group("active")
        row["value_type"] = match.group("vtype")
        row["diag_index"] = i
        curved.append(row)
    for match in CONF_RE.finditer(text):
        row = {k: fnum(v) for k, v in match.groupdict().items() if k != "targets"}
        row["targets"] = int(match.group("targets"))
        conf.append(row)
    return meta, curved, conf, times


def read_partcsv(case_name: str, times: dict[int, float]) -> list[dict[str, object]]:
    data_dir = ROOT / f"{case_name}_cpu_out" / "data"
    rows: list[dict[str, object]] = []
    for iframe, path in enumerate(sorted(data_dir.glob("PartCsv_*.csv"))):
        lines = path.read_text(errors="ignore").splitlines()
        header_idx = None
        for i, line in enumerate(lines):
            if "PorePress" in line or "Kplastic" in line or "Pos" in line:
                header_idx = i
                break
        if header_idx is None:
            continue
        headers = split_line(lines[header_idx])
        idx = {
            "x": find_col(headers, ("Pos.x", "posx", "x")),
            "y": find_col(headers, ("Pos.y", "posy", "y")),
            "z": find_col(headers, ("Pos.z", "posz", "z")),
            "p": find_col(headers, ("PorePress",)),
            "ex": find_col(headers, ("ExcessPorePress",)),
            "rate": find_col(headers, ("PorePressRate",)),
            "lap": find_col(headers, ("LapPorePress",)),
            "lapz": find_col(headers, ("LapZ",)),
            "div": find_col(headers, ("DivVel",)),
            "kp": find_col(headers, ("Kplastic",)),
        }
        vals_by_key = {key: [] for key in ("p", "ex", "rate", "lap", "lapz", "div", "kp")}
        center_ex = math.nan
        center_p = math.nan
        center_r = math.inf
        surf_ex: list[float] = []
        interior_ex: list[float] = []
        count = 0
        for line in lines[header_idx + 1:]:
            if not line.strip() or line.startswith("#"):
                continue
            vals = split_line(line)
            count += 1
            rowvals: dict[str, float] = {}
            for key in vals_by_key:
                col = idx[key]
                value = fnum(vals[col]) if col is not None and col < len(vals) else math.nan
                rowvals[key] = value
                if math.isfinite(value):
                    vals_by_key[key].append(abs(value) if key == "kp" else value)
            if idx["x"] is not None and idx["y"] is not None and idx["z"] is not None:
                x = fnum(vals[idx["x"]]); y = fnum(vals[idx["y"]]); z = fnum(vals[idx["z"]])
                r = math.sqrt(x*x + y*y + z*z)
                ex = rowvals["ex"]
                if r < center_r:
                    center_r = r
                    center_p = rowvals["p"]
                    center_ex = ex
                if math.isfinite(ex) and r > SURFACE_FRAC * RADIUS:
                    surf_ex.append(ex)
                if math.isfinite(ex) and r < INTERIOR_FRAC * RADIUS:
                    interior_ex.append(ex)
        rows.append({
            "frame_index": iframe,
            "time": times.get(iframe, float(iframe)),
            "frame_file": path.name,
            "particle_count_csv": count,
            "PorePress_max": max(vals_by_key["p"]) if vals_by_key["p"] else math.nan,
            "PorePress_mean": sum(vals_by_key["p"]) / len(vals_by_key["p"]) if vals_by_key["p"] else math.nan,
            "ExcessPorePress_max": max(vals_by_key["ex"]) if vals_by_key["ex"] else math.nan,
            "ExcessPorePress_mean": sum(vals_by_key["ex"]) / len(vals_by_key["ex"]) if vals_by_key["ex"] else math.nan,
            "ExcessPorePress_maxAbs": max((abs(v) for v in vals_by_key["ex"]), default=math.nan),
            "surface_ExcessPorePress_mean": sum(surf_ex) / len(surf_ex) if surf_ex else math.nan,
            "surface_ExcessPorePress_maxAbs": max((abs(v) for v in surf_ex), default=math.nan),
            "interior_ExcessPorePress_mean": sum(interior_ex) / len(interior_ex) if interior_ex else math.nan,
            "PorePressRate_maxAbs": max((abs(v) for v in vals_by_key["rate"]), default=math.nan),
            "LapPorePress_maxAbs": max((abs(v) for v in vals_by_key["lap"]), default=math.nan),
            "LapZ_maxAbs": max((abs(v) for v in vals_by_key["lapz"]), default=math.nan),
            "DivVel_maxAbs": max((abs(v) for v in vals_by_key["div"]), default=math.nan),
            "center_PorePress": center_p,
            "center_ExcessPorePress": center_ex,
            "center_radius": center_r,
            "Kplastic_maxAbs": max(vals_by_key["kp"]) if vals_by_key["kp"] else 0.0,
        })
    return rows


def read_vtk_vectors(blob: bytes, field_name: bytes, components: int) -> list[tuple[float, ...]] | None:
    if field_name == b"POINTS":
        match = re.search(rb"POINTS\s+(\d+)\s+float\s*\n", blob)
    else:
        pattern = rb"\n" + re.escape(field_name) + rb"\s+" + str(components).encode() + rb"\s+(\d+)\s+float\s*\n"
        match = re.search(pattern, blob)
    if not match:
        return None
    count = int(match.group(1))
    start = match.end()
    nvalues = count * components
    nbytes = nvalues * 4
    if start + nbytes > len(blob):
        return None
    values = struct.unpack(f">{nvalues}f", blob[start:start + nbytes])
    return [tuple(values[i:i + components]) for i in range(0, nvalues, components)]


def read_vtk(case_name: str, times: dict[int, float]) -> list[dict[str, object]]:
    vtk_dir = ROOT / f"{case_name}_cpu_vtk_particles"
    paths = sorted(vtk_dir.glob("PartFluid_*.vtk"))
    if not paths:
        return []
    initial = read_vtk_vectors(paths[0].read_bytes(), b"POINTS", 3)
    if not initial:
        return []
    initial_r = [math.sqrt(x*x + y*y + z*z) for x, y, z in initial]
    rows: list[dict[str, object]] = []
    for iframe, path in enumerate(paths):
        blob = path.read_bytes()
        points = read_vtk_vectors(blob, b"POINTS", 3)
        vel = read_vtk_vectors(blob, b"Vel", 3)
        if not points or not vel:
            continue
        vmag: list[float] = []
        surf_rv: list[float] = []
        surf_disp: list[float] = []
        for p, v, r0 in zip(points, vel, initial_r):
            x, y, z = p
            vx, vy, vz = v
            r = math.sqrt(x*x + y*y + z*z)
            vm = math.sqrt(vx*vx + vy*vy + vz*vz)
            vmag.append(vm)
            rv = (x*vx + y*vy + z*vz) / r if r > 0 else 0.0
            if r0 > SURFACE_FRAC * RADIUS:
                surf_rv.append(rv)
                surf_disp.append(r - r0)
        rows.append({
            "frame_index": iframe,
            "time": times.get(iframe, float(iframe)),
            "frame_file": path.name,
            "particle_count_vtk": len(points),
            "vel_max": max(vmag) if vmag else 0.0,
            "vel_mean": sum(vmag) / len(vmag) if vmag else 0.0,
            "surface_radial_vel_mean": sum(surf_rv) / len(surf_rv) if surf_rv else 0.0,
            "surface_radial_disp_mean": sum(surf_disp) / len(surf_disp) if surf_disp else 0.0,
        })
    return rows


def merge_rows(*rowsets: list[dict[str, object]]) -> list[dict[str, object]]:
    merged: dict[int, dict[str, object]] = {}
    for rows in rowsets:
        for row in rows:
            item = merged.setdefault(int(row["frame_index"]), {})
            item.update(row)
    return [merged[k] for k in sorted(merged)]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def plot(all_rows: list[dict[str, object]], residual_rows: list[dict[str, object]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    fig_dir = ROOT / "figures"
    fig_dir.mkdir(exist_ok=True)

    def lineplot(name: str, ykey: str, ylabel: str) -> None:
        plt.figure(figsize=(6, 4))
        for case in sorted({str(r["case"]) for r in all_rows}):
            sub = [r for r in all_rows if r["case"] == case and str(r.get(ykey, "")) != ""]
            if not sub:
                continue
            plt.plot([float(r["time"]) for r in sub], [float(r[ykey]) for r in sub], marker="o", label=case)
        plt.xlabel("time [s]")
        plt.ylabel(ylabel)
        plt.title(name.replace("_", " "))
        plt.legend()
        plt.tight_layout()
        plt.savefig(fig_dir / f"{name}.png", dpi=180)
        plt.savefig(fig_dir / f"{name}.svg")
        plt.close()

    lineplot("c4c_boundary_excess_residual_proxy", "surface_ExcessPorePress_maxAbs", "surface |excess| max [Pa]")
    lineplot("c4c_center_excess_pressure", "center_ExcessPorePress", "center excess pressure [Pa]")
    lineplot("c4c_mean_excess_pressure", "ExcessPorePress_mean", "mean excess pressure [Pa]")
    lineplot("c4c_excess_pressure_maxabs", "ExcessPorePress_maxAbs", "|excess| max [Pa]")
    lineplot("c4c_porepress_rate_maxabs", "PorePressRate_maxAbs", "|PorePressRate| max [Pa/s]")
    lineplot("c4c_lapporepress_maxabs", "LapPorePress_maxAbs", "|LapPorePress| max")
    lineplot("c4c_velocity_max", "vel_max", "max velocity [m/s]")
    lineplot("c4c_kplastic_maxabs", "Kplastic_maxAbs", "|Kplastic| max")
    lineplot("c4c_surface_radial_velocity", "surface_radial_vel_mean", "surface radial velocity mean [m/s]")

    if residual_rows:
        plt.figure(figsize=(6, 4))
        for case in sorted({str(r["case"]) for r in residual_rows}):
            sub = [r for r in residual_rows if r["case"] == case]
            plt.plot(range(len(sub)), [float(r["boundary_residual_max"]) for r in sub], marker="o", label=case)
        plt.xlabel("operator diagnostic index")
        plt.ylabel("boundary residual max [Pa]")
        plt.title("C4-C curved drained operator residual")
        plt.legend()
        plt.tight_layout()
        plt.savefig(fig_dir / "c4c_operator_boundary_residual.png", dpi=180)
        plt.savefig(fig_dir / "c4c_operator_boundary_residual.svg")
        plt.close()


def main() -> None:
    all_rows: list[dict[str, object]] = []
    residual_rows: list[dict[str, object]] = []
    conf_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for label, case_name in CASES:
        meta, curved, conf, times = read_runout(case_name)
        csv_rows = read_partcsv(case_name, times)
        vtk_rows = read_vtk(case_name, times)
        merged = merge_rows(csv_rows, vtk_rows)
        for row in merged:
            row["case"] = label
            all_rows.append(row)
        for row in curved:
            row["case"] = label
            row["boundary_residual_max"] = row.get("resid", "")
            residual_rows.append(row)
        for row in conf:
            row["case"] = label
            conf_rows.append(row)
        final = merged[-1] if merged else {}
        final_curve = curved[-1] if curved else {}
        final_conf = conf[-1] if conf else {}
        summary_rows.append({
            "case": label,
            "code": meta.get("code", ""),
            "excluded": meta.get("excluded", ""),
            "steps": meta.get("steps", ""),
            "runtime_sec": meta.get("runtime_sec", ""),
            "frames": len(merged),
            "curved_diag_rows": len(curved),
            "final_affected": final_curve.get("affected", ""),
            "final_boundary_residual_max": final_curve.get("resid", ""),
            "final_p0_eff": final_conf.get("p0", 0.0),
            "final_vel_max": final.get("vel_max", ""),
            "final_center_excess": final.get("center_ExcessPorePress", ""),
            "final_mean_excess": final.get("ExcessPorePress_mean", ""),
            "final_surface_excess_maxAbs": final.get("surface_ExcessPorePress_maxAbs", ""),
            "final_porepressrate_maxAbs": final.get("PorePressRate_maxAbs", ""),
            "final_lapporepress_maxAbs": final.get("LapPorePress_maxAbs", ""),
            "final_kplastic_maxAbs": final.get("Kplastic_maxAbs", ""),
        })

    common_fields = [
        "case", "frame_index", "time", "frame_file", "particle_count_csv",
        "PorePress_max", "PorePress_mean", "ExcessPorePress_max",
        "ExcessPorePress_mean", "ExcessPorePress_maxAbs",
        "surface_ExcessPorePress_mean", "surface_ExcessPorePress_maxAbs",
        "interior_ExcessPorePress_mean", "PorePressRate_maxAbs",
        "LapPorePress_maxAbs", "LapZ_maxAbs", "DivVel_maxAbs",
        "center_PorePress", "center_ExcessPorePress", "center_radius",
        "Kplastic_maxAbs", "vel_max", "vel_mean", "surface_radial_vel_mean",
        "surface_radial_disp_mean",
    ]
    residual_fields = [
        "case", "diag_index", "active", "radius", "thick", "target", "value",
        "value_type", "affected", "skipped", "rmin", "rmax", "boundary_residual_max",
    ]
    conf_fields = [
        "case", "step", "time", "p0", "targets", "fx", "fy", "fz", "fabs",
        "amax", "acom", "sym",
    ]
    summary_fields = [
        "case", "code", "excluded", "steps", "runtime_sec", "frames",
        "curved_diag_rows", "final_affected", "final_boundary_residual_max",
        "final_p0_eff", "final_vel_max", "final_center_excess",
        "final_mean_excess", "final_surface_excess_maxAbs",
        "final_porepressrate_maxAbs", "final_lapporepress_maxAbs",
        "final_kplastic_maxAbs",
    ]
    write_csv(ROOT / "c4c_drained_boundary_case_summary.csv", summary_rows, summary_fields)
    write_csv(ROOT / "c4c_drained_boundary_residual_metrics.csv", residual_rows, residual_fields)
    write_csv(ROOT / "c4c_pressure_diffusion_metrics.csv", [r for r in all_rows if r["case"] in ("zero", "diffusion")], common_fields)
    write_csv(ROOT / "c4c_compression_drainage_metrics.csv", [r for r in all_rows if r["case"] == "compression"], common_fields)
    write_csv(ROOT / "c4c_confining_stress_diagnostics.csv", conf_rows, conf_fields)
    plot(all_rows, residual_rows)


if __name__ == "__main__":
    main()
