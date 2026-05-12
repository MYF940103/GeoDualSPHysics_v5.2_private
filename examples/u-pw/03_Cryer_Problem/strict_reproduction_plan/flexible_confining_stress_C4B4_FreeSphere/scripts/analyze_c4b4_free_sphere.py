#!/usr/bin/env python3
"""Analyze C4-B4 flexible confining stress free-sphere smoke outputs."""

from __future__ import annotations

import csv
import math
import re
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("no_load", "CaseFlexConf_C4B4_FreeSphere_NoLoad"),
    ("ramp", "CaseFlexConf_C4B4_FreeSphere_Ramp"),
]
RADIUS = 0.05
SURFACE_FRAC = 0.85
INTERIOR_FRAC = 0.50


DIAG_RE = re.compile(
    r"FlexibleConfiningStress CPU diagnostics: step=(?P<step>[-+0-9.eE]+), "
    r"TimeStep=(?P<time>[-+0-9.eE]+), p0_eff=(?P<p0>[-+0-9.eE]+) Pa, "
    r"targets=(?P<targets>\d+), net_force=\((?P<fx>[-+0-9.eE]+),(?P<fy>[-+0-9.eE]+),(?P<fz>[-+0-9.eE]+)\) N, "
    r"total_abs_force=(?P<fabs>[-+0-9.eE]+) N, max_accel=(?P<amax>[-+0-9.eE]+) m/s2, "
    r"com_accel=(?P<acom>[-+0-9.eE]+) m/s2, symmetry_residual=(?P<sym>[-+0-9.eE]+)"
)


def fnum(value: str | None, default: float = math.nan) -> float:
    if value is None:
        return default
    try:
        return float(str(value).strip().rstrip("."))
    except ValueError:
        return default


def read_runout(case_name: str) -> tuple[list[dict[str, float]], dict[str, str]]:
    runout = ROOT / f"{case_name}_cpu_out" / "Run.out"
    diagnostics: list[dict[str, float]] = []
    meta = {"runout_exists": str(runout.exists()), "code": "unknown", "excluded": "unknown"}
    if not runout.exists():
        return diagnostics, meta
    text = runout.read_text(errors="ignore")
    meta["code"] = "0" if "Finished execution" in text or "Execution finished" in text else "unknown"
    m = re.search(r"Excluded particles\.*:\s*(\d+)", text)
    if not m:
        m = re.search(r"Particles out:\s*(\d+)", text)
    if m:
        meta["excluded"] = m.group(1)
    m = re.search(r"Total steps\.*:\s*(\d+)", text)
    if not m:
        m = re.search(r"Steps of simulation\.*:\s*(\d+)", text)
    if m:
        meta["steps"] = m.group(1)
    m = re.search(r"Total Runtime\.*:\s*([-+0-9.eE]+)", text)
    if m:
        meta["runtime_sec"] = m.group(1)
    for match in DIAG_RE.finditer(text):
        row = {k: fnum(v) for k, v in match.groupdict().items() if k != "targets"}
        row["targets"] = float(match.group("targets"))
        diagnostics.append(row)
    return diagnostics, meta


def read_part_times(case_name: str) -> dict[int, float]:
    runout = ROOT / f"{case_name}_cpu_out" / "Run.out"
    times: dict[int, float] = {0: 0.0}
    if not runout.exists():
        return times
    text = runout.read_text(errors="ignore")
    for match in re.finditer(r"Part_(?P<idx>\d{4})\s+(?P<time>[-+0-9.eE]*\.[-+0-9.eE]+)\s+\d+", text):
        times[int(match.group("idx"))] = fnum(match.group("time"))
    return times


def split_line(line: str) -> list[str]:
    if ";" in line:
        return [v.strip() for v in line.strip().split(";")]
    return [v.strip() for v in line.strip().split(",")]


def find_col(headers: list[str], candidates: tuple[str, ...]) -> int | None:
    lower = [h.strip().lower() for h in headers]
    for cand in candidates:
        cand_l = cand.lower()
        for i, header in enumerate(lower):
            if header == cand_l or header.endswith(cand_l):
                return i
    return None


def read_partcsv_metrics(case_name: str) -> list[dict[str, float]]:
    data_dir = ROOT / f"{case_name}_cpu_out" / "data"
    rows: list[dict[str, float]] = []
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
            "x": find_col(headers, ("Pos.x", "posx", "Pos_x", "x")),
            "y": find_col(headers, ("Pos.y", "posy", "Pos_y", "y")),
            "z": find_col(headers, ("Pos.z", "posz", "Pos_z", "z")),
            "p": find_col(headers, ("PorePress",)),
            "ex": find_col(headers, ("ExcessPorePress",)),
            "rate": find_col(headers, ("PorePressRate",)),
            "kplastic": find_col(headers, ("Kplastic",)),
        }
        count = 0
        pore_vals: list[float] = []
        excess_vals: list[float] = []
        rate_vals: list[float] = []
        kplastic_vals: list[float] = []
        center_p = math.nan
        center_ex = math.nan
        center_r = math.inf
        for line in lines[header_idx + 1:]:
            if not line.strip() or line.startswith("#"):
                continue
            vals = split_line(line)
            count += 1
            p = fnum(vals[idx["p"]]) if idx["p"] is not None and idx["p"] < len(vals) else math.nan
            ex = fnum(vals[idx["ex"]]) if idx["ex"] is not None and idx["ex"] < len(vals) else math.nan
            rate = fnum(vals[idx["rate"]]) if idx["rate"] is not None and idx["rate"] < len(vals) else math.nan
            kp = fnum(vals[idx["kplastic"]], 0.0) if idx["kplastic"] is not None and idx["kplastic"] < len(vals) else 0.0
            if math.isfinite(p):
                pore_vals.append(p)
            if math.isfinite(ex):
                excess_vals.append(ex)
            if math.isfinite(rate):
                rate_vals.append(rate)
            if math.isfinite(kp):
                kplastic_vals.append(abs(kp))
            if idx["x"] is not None and idx["y"] is not None and idx["z"] is not None:
                try:
                    x = float(vals[idx["x"]]); y = float(vals[idx["y"]]); z = float(vals[idx["z"]])
                except (ValueError, IndexError):
                    continue
                r = math.sqrt(x*x + y*y + z*z)
                if r < center_r:
                    center_r = r
                    center_p = p
                    center_ex = ex
        rows.append({
            "frame_index": float(iframe),
            "frame_file": path.name,
            "particle_count_csv": float(count),
            "PorePress_max": max(pore_vals) if pore_vals else math.nan,
            "PorePress_mean": sum(pore_vals) / len(pore_vals) if pore_vals else math.nan,
            "ExcessPorePress_max": max(excess_vals) if excess_vals else math.nan,
            "ExcessPorePress_mean": sum(excess_vals) / len(excess_vals) if excess_vals else math.nan,
            "ExcessPorePress_maxAbs": max((abs(v) for v in excess_vals), default=math.nan),
            "PorePressRate_maxAbs": max((abs(v) for v in rate_vals), default=math.nan),
            "center_PorePress": center_p,
            "center_ExcessPorePress": center_ex,
            "center_radius": center_r,
            "Kplastic_maxAbs": max(kplastic_vals) if kplastic_vals else 0.0,
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


def read_vtk_radial_metrics(case_name: str) -> list[dict[str, float]]:
    vtk_dir = ROOT / f"{case_name}_cpu_vtk_particles"
    paths = sorted(vtk_dir.glob("PartFluid_*.vtk"))
    if not paths:
        return []
    initial_points = read_vtk_vectors(paths[0].read_bytes(), b"POINTS", 3)
    if not initial_points:
        return []
    initial_r = [math.sqrt(p[0]*p[0] + p[1]*p[1] + p[2]*p[2]) for p in initial_points]
    rows: list[dict[str, float]] = []
    for iframe, path in enumerate(paths):
        blob = path.read_bytes()
        points = read_vtk_vectors(blob, b"POINTS", 3)
        velocities = read_vtk_vectors(blob, b"Vel", 3)
        if not points or not velocities or len(points) != len(velocities):
            continue
        vmag: list[float] = []
        radial_v: list[float] = []
        radial_v_surface: list[float] = []
        radial_v_interior: list[float] = []
        tang_surface: list[float] = []
        disp_surface: list[float] = []
        disp_interior: list[float] = []
        for p, v, r0 in zip(points, velocities, initial_r):
            x, y, z = p
            vx, vy, vz = v
            r = math.sqrt(x*x + y*y + z*z)
            vm = math.sqrt(vx*vx + vy*vy + vz*vz)
            vmag.append(vm)
            rv = (x*vx + y*vy + z*vz) / r if r > 0 else 0.0
            radial_v.append(rv)
            if r0 > SURFACE_FRAC * RADIUS:
                radial_v_surface.append(rv)
                tang_surface.append(math.sqrt(max(vm*vm - rv*rv, 0.0)))
                disp_surface.append(r - r0)
            if r0 < INTERIOR_FRAC * RADIUS:
                radial_v_interior.append(rv)
                disp_interior.append(r - r0)
        rows.append({
            "frame_index": float(iframe),
            "frame_file": path.name,
            "particle_count_vtk": float(len(points)),
            "vel_max": max(vmag) if vmag else 0.0,
            "vel_mean": sum(vmag) / len(vmag) if vmag else 0.0,
            "radial_vel_mean": sum(radial_v) / len(radial_v) if radial_v else 0.0,
            "surface_radial_vel_mean": sum(radial_v_surface) / len(radial_v_surface) if radial_v_surface else 0.0,
            "surface_radial_vel_min": min(radial_v_surface) if radial_v_surface else 0.0,
            "surface_radial_vel_max": max(radial_v_surface) if radial_v_surface else 0.0,
            "interior_radial_vel_mean": sum(radial_v_interior) / len(radial_v_interior) if radial_v_interior else 0.0,
            "surface_radial_disp_mean": sum(disp_surface) / len(disp_surface) if disp_surface else 0.0,
            "interior_radial_disp_mean": sum(disp_interior) / len(disp_interior) if disp_interior else 0.0,
            "surface_tangential_vel_mean": sum(tang_surface) / len(tang_surface) if tang_surface else 0.0,
            "surface_particle_count": float(len(radial_v_surface)),
            "interior_particle_count": float(len(radial_v_interior)),
        })
    return rows


def merge_by_frame(left: list[dict[str, float]], right: list[dict[str, float]]) -> list[dict[str, float]]:
    by_frame = {int(r["frame_index"]): dict(r) for r in left}
    for row in right:
        item = by_frame.setdefault(int(row["frame_index"]), {})
        item.update(row)
    return [by_frame[k] for k in sorted(by_frame)]


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def plot(rows: list[dict[str, object]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    fig_dir = ROOT / "figures"
    fig_dir.mkdir(exist_ok=True)

    def lineplot(name: str, ykey: str, ylabel: str, cases: set[str] | None = None) -> None:
        plt.figure(figsize=(6, 4))
        labels = sorted(cases or {str(r["case"]) for r in rows})
        for label in labels:
            sub = [r for r in rows if r.get("case") == label and str(r.get(ykey, "")) != ""]
            if not sub:
                continue
            x = [float(r.get("time", r["frame_index"])) for r in sub]
            y = [float(r[ykey]) for r in sub]
            plt.plot(x, y, marker="o", label=label)
        plt.xlabel("time [s]")
        plt.ylabel(ylabel)
        plt.title(name.replace("_", " "))
        plt.legend()
        plt.tight_layout()
        plt.savefig(fig_dir / f"{name}.png", dpi=180)
        plt.savefig(fig_dir / f"{name}.svg")
        plt.close()

    lineplot("c4b4_p0_eff_ramp", "p0_eff", "effective p0 [Pa]", {"ramp"})
    lineplot("c4b4_velocity_max", "vel_max", "max velocity [m/s]")
    lineplot("c4b4_surface_radial_velocity", "surface_radial_vel_mean", "surface radial velocity mean [m/s]")
    lineplot("c4b4_surface_radial_displacement", "surface_radial_disp_mean", "surface radial displacement mean [m]")
    lineplot("c4b4_com_acceleration", "com_accel", "COM acceleration estimate [m/s2]", {"ramp"})
    lineplot("c4b4_symmetry_residual", "symmetry_residual", "force symmetry residual", {"ramp"})
    lineplot("c4b4_center_excess_pore_pressure", "center_ExcessPorePress", "center excess pressure [Pa]")
    lineplot("c4b4_mean_excess_pore_pressure", "ExcessPorePress_mean", "mean excess pressure [Pa]")

    # Final radial profile proxy: radial velocity vs initial-radius group for ramp.
    ramp_rows = [r for r in rows if r.get("case") == "ramp"]
    if ramp_rows:
        plt.figure(figsize=(6, 4))
        plt.axhline(0, color="0.4", linewidth=0.8)
        x = [float(r.get("time", r["frame_index"])) for r in ramp_rows]
        plt.plot(x, [float(r.get("surface_radial_vel_mean", 0.0)) for r in ramp_rows], marker="o", label="surface")
        plt.plot(x, [float(r.get("interior_radial_vel_mean", 0.0)) for r in ramp_rows], marker="o", label="interior")
        plt.xlabel("time [s]")
        plt.ylabel("radial velocity mean [m/s]")
        plt.title("C4-B4 surface vs interior radial response")
        plt.legend()
        plt.tight_layout()
        plt.savefig(fig_dir / "c4b4_surface_vs_interior_radial_velocity.png", dpi=180)
        plt.savefig(fig_dir / "c4b4_surface_vs_interior_radial_velocity.svg")
        plt.close()


def main() -> None:
    force_rows: list[dict[str, object]] = []
    radial_rows: list[dict[str, object]] = []
    pore_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    merged_rows: list[dict[str, object]] = []

    for label, case_name in CASES:
        diagnostics, meta = read_runout(case_name)
        part_times = read_part_times(case_name)
        vtk_rows = read_vtk_radial_metrics(case_name)
        csv_rows = read_partcsv_metrics(case_name)
        for row in vtk_rows:
            row["time"] = part_times.get(int(row["frame_index"]), row["frame_index"])
        for row in csv_rows:
            row["time"] = part_times.get(int(row["frame_index"]), row["frame_index"])
        merged = merge_by_frame(vtk_rows, csv_rows)

        by_frame_diag = {int(r["step"]): r for r in diagnostics}
        for row in merged:
            row["case"] = label
            diag = by_frame_diag.get(int(row.get("frame_index", -1)))
            if diag:
                row.update({
                    "p0_eff": diag["p0"],
                    "targets": diag["targets"],
                    "net_fx": diag["fx"],
                    "net_fy": diag["fy"],
                    "net_fz": diag["fz"],
                    "total_abs_force": diag["fabs"],
                    "max_conf_accel": diag["amax"],
                    "com_accel": diag["acom"],
                    "symmetry_residual": diag["sym"],
                })
            merged_rows.append(row)

        for row in diagnostics:
            net_mag = math.sqrt(row["fx"]**2 + row["fy"]**2 + row["fz"]**2)
            total_abs = row["fabs"]
            force_rows.append({
                "case": label,
                "step": row["step"],
                "time": row["time"],
                "p0_eff": row["p0"],
                "targets": row["targets"],
                "net_fx": row["fx"],
                "net_fy": row["fy"],
                "net_fz": row["fz"],
                "net_force_mag": net_mag,
                "total_abs_force": total_abs,
                "net_force_mag_over_abs_force": net_mag / total_abs if total_abs else math.nan,
                "max_conf_accel": row["amax"],
                "com_accel": row["acom"],
                "symmetry_residual": row["sym"],
            })
        for row in vtk_rows:
            radial_rows.append({"case": label, **row})
        for row in csv_rows:
            pore_rows.append({"case": label, **row})

        final = merged[-1] if merged else {}
        final_diag = diagnostics[-1] if diagnostics else {}
        summary_rows.append({
            "case": label,
            "runout_exists": meta.get("runout_exists", ""),
            "code": meta.get("code", ""),
            "excluded": meta.get("excluded", ""),
            "steps": meta.get("steps", ""),
            "runtime_sec": meta.get("runtime_sec", ""),
            "frames": len(merged),
            "diagnostic_rows": len(diagnostics),
            "final_p0_eff": final_diag.get("p0", 0.0),
            "target_particles": final_diag.get("targets", 0.0),
            "final_net_force_mag": math.sqrt(
                final_diag.get("fx", 0.0)**2 + final_diag.get("fy", 0.0)**2 + final_diag.get("fz", 0.0)**2
            ) if final_diag else 0.0,
            "final_net_force_mag_over_abs_force": (
                math.sqrt(final_diag.get("fx", 0.0)**2 + final_diag.get("fy", 0.0)**2 + final_diag.get("fz", 0.0)**2)
                / final_diag.get("fabs", math.nan)
            ) if final_diag and final_diag.get("fabs", 0.0) else 0.0,
            "final_max_conf_accel": final_diag.get("amax", 0.0),
            "final_symmetry_residual": final_diag.get("sym", 0.0),
            "final_com_accel": final_diag.get("acom", 0.0),
            "final_vel_max": final.get("vel_max", 0.0),
            "final_surface_radial_vel_mean": final.get("surface_radial_vel_mean", 0.0),
            "final_surface_radial_disp_mean": final.get("surface_radial_disp_mean", 0.0),
            "final_center_excess": final.get("center_ExcessPorePress", math.nan),
            "final_mean_excess": final.get("ExcessPorePress_mean", math.nan),
            "final_kplastic_max_abs": final.get("Kplastic_maxAbs", 0.0),
        })

    force_fields = [
        "case", "step", "time", "p0_eff", "targets", "net_fx", "net_fy", "net_fz",
        "net_force_mag", "total_abs_force", "net_force_mag_over_abs_force",
        "max_conf_accel", "com_accel", "symmetry_residual",
    ]
    radial_fields = [
        "case", "frame_index", "frame_file", "particle_count_vtk", "vel_max", "vel_mean",
        "time", "radial_vel_mean", "surface_radial_vel_mean", "surface_radial_vel_min",
        "surface_radial_vel_max", "interior_radial_vel_mean", "surface_radial_disp_mean",
        "interior_radial_disp_mean", "surface_tangential_vel_mean",
        "surface_particle_count", "interior_particle_count",
    ]
    pore_fields = [
        "case", "frame_index", "time", "frame_file", "particle_count_csv", "PorePress_max",
        "PorePress_mean", "ExcessPorePress_max", "ExcessPorePress_mean",
        "ExcessPorePress_maxAbs", "PorePressRate_maxAbs", "center_PorePress",
        "center_ExcessPorePress", "center_radius", "Kplastic_maxAbs",
    ]
    summary_fields = [
        "case", "runout_exists", "code", "excluded", "steps", "runtime_sec",
        "frames", "diagnostic_rows",
        "final_p0_eff", "target_particles", "final_net_force_mag",
        "final_net_force_mag_over_abs_force", "final_max_conf_accel",
        "final_symmetry_residual", "final_com_accel", "final_vel_max",
        "final_surface_radial_vel_mean", "final_surface_radial_disp_mean",
        "final_center_excess", "final_mean_excess", "final_kplastic_max_abs",
    ]
    write_csv(ROOT / "c4b4_free_sphere_force_diagnostics.csv", force_rows, force_fields)
    write_csv(ROOT / "c4b4_free_sphere_radial_metrics.csv", radial_rows, radial_fields)
    write_csv(ROOT / "c4b4_free_sphere_porepressure_metrics.csv", pore_rows, pore_fields)
    write_csv(ROOT / "c4b4_free_sphere_case_summary.csv", summary_rows, summary_fields)
    plot(merged_rows)


if __name__ == "__main__":
    main()
