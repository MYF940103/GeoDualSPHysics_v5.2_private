#!/usr/bin/env python3
"""Summarize C4-B3 flexible confining stress smoke outputs.

The script is intentionally tolerant of DualSPHysics CSV header variants. It
parses the runtime diagnostics printed by the CPU implementation and, when
available, PartCsv velocity fields.
"""

from __future__ import annotations

import csv
import math
import re
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("no_load", "CaseFlexConf_C4B3_NoLoad"),
    ("sign", "CaseFlexConf_C4B3_Sign"),
    ("ramp", "CaseFlexConf_C4B3_Ramp"),
]


DIAG_RE = re.compile(
    r"FlexibleConfiningStress CPU diagnostics: step=(?P<step>[-+0-9.eE]+), "
    r"TimeStep=(?P<time>[-+0-9.eE]+), p0_eff=(?P<p0>[-+0-9.eE]+) Pa, "
    r"targets=(?P<targets>\d+), net_force=\((?P<fx>[-+0-9.eE]+),(?P<fy>[-+0-9.eE]+),(?P<fz>[-+0-9.eE]+)\) N, "
    r"total_abs_force=(?P<fabs>[-+0-9.eE]+) N, max_accel=(?P<amax>[-+0-9.eE]+) m/s2, "
    r"com_accel=(?P<acom>[-+0-9.eE]+) m/s2, symmetry_residual=(?P<sym>[-+0-9.eE]+)"
)


def read_runout(case_name: str) -> tuple[list[dict[str, float]], dict[str, str]]:
    runout = ROOT / f"{case_name}_cpu_out" / "Run.out"
    diagnostics: list[dict[str, float]] = []
    meta = {
        "runout_exists": str(runout.exists()),
        "code": "unknown",
        "excluded": "unknown",
    }
    if not runout.exists():
        return diagnostics, meta
    text = runout.read_text(errors="ignore")
    meta["code"] = "0" if "Finished execution" in text or "Execution finished" in text else "unknown"
    m = re.search(r"Excluded particles\.*:\s*(\d+)", text)
    if not m:
        m = re.search(r"Particles out:\s*(\d+)", text)
    if m:
        meta["excluded"] = m.group(1)
    for match in DIAG_RE.finditer(text):
        row = {k: float(v.rstrip(".")) for k, v in match.groupdict().items() if k != "targets"}
        row["targets"] = float(match.group("targets"))
        diagnostics.append(row)
    return diagnostics, meta


def split_csv_line(line: str) -> list[str]:
    if ";" in line:
        return [v.strip() for v in line.strip().split(";")]
    return [v.strip() for v in line.strip().split(",")]


def find_col(headers: list[str], candidates: tuple[str, ...]) -> int | None:
    lower = [h.strip().lower() for h in headers]
    for cand in candidates:
        cand_l = cand.lower()
        for i, h in enumerate(lower):
            if h == cand_l or h.endswith(cand_l):
                return i
    return None


def partcsv_velocity_metrics(case_name: str) -> list[dict[str, float]]:
    data_dir = ROOT / f"{case_name}_cpu_out" / "data"
    rows: list[dict[str, float]] = []
    for path in sorted(data_dir.glob("PartCsv_*.csv")):
        lines = path.read_text(errors="ignore").splitlines()
        header_idx = None
        for i, line in enumerate(lines):
            if "Vel" in line or "vel" in line:
                header_idx = i
                break
        if header_idx is None:
            continue
        headers = split_csv_line(lines[header_idx])
        ix = find_col(headers, ("Vel_x", "velx", "Vel.x", "Vel:0"))
        iy = find_col(headers, ("Vel_y", "vely", "Vel.y", "Vel:1"))
        iz = find_col(headers, ("Vel_z", "velz", "Vel.z", "Vel:2"))
        if ix is None or iy is None or iz is None:
            continue
        vmax = 0.0
        vmean = 0.0
        count = 0
        for line in lines[header_idx + 1 :]:
            if not line.strip() or line.startswith("#"):
                continue
            vals = split_csv_line(line)
            try:
                vx, vy, vz = float(vals[ix]), float(vals[iy]), float(vals[iz])
            except (ValueError, IndexError):
                continue
            vm = math.sqrt(vx * vx + vy * vy + vz * vz)
            vmax = max(vmax, vm)
            vmean += vm
            count += 1
        rows.append({
            "frame_file": path.name,
            "vel_max": vmax,
            "vel_mean": vmean / count if count else 0.0,
            "particle_count": float(count),
        })
    return rows


def read_vtk_binary_vectors(blob: bytes, field_name: bytes, components: int) -> list[tuple[float, ...]] | None:
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


def vtk_velocity_metrics(case_name: str) -> list[dict[str, float]]:
    vtk_dir = ROOT / f"{case_name}_cpu_vtk_particles"
    rows: list[dict[str, float]] = []
    for path in sorted(vtk_dir.glob("PartFluid_*.vtk")):
        blob = path.read_bytes()
        points = read_vtk_binary_vectors(blob, b"POINTS", 3)
        velocities = read_vtk_binary_vectors(blob, b"Vel", 3)
        if not points or not velocities or len(points) != len(velocities):
            continue
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        cz = sum(p[2] for p in points) / len(points)
        radii = [math.sqrt((p[0] - cx) ** 2 + (p[1] - cy) ** 2 + (p[2] - cz) ** 2) for p in points]
        rmax = max(radii) if radii else 0.0
        surface_cut = 0.82 * rmax
        vmax = 0.0
        vmean = 0.0
        radial_mean = 0.0
        radial_surface_mean = 0.0
        radial_surface_min = 0.0
        radial_surface_max = 0.0
        radial_count = 0
        surface_count = 0
        for p, v, radius in zip(points, velocities, radii):
            vx, vy, vz = v
            vm = math.sqrt(vx * vx + vy * vy + vz * vz)
            vmax = max(vmax, vm)
            vmean += vm
            if radius > 0:
                rv = ((p[0] - cx) * vx + (p[1] - cy) * vy + (p[2] - cz) * vz) / radius
                radial_mean += rv
                radial_count += 1
                if radius >= surface_cut:
                    radial_surface_mean += rv
                    radial_surface_min = min(radial_surface_min, rv) if surface_count else rv
                    radial_surface_max = max(radial_surface_max, rv) if surface_count else rv
                    surface_count += 1
        count = len(velocities)
        rows.append({
            "frame_file": path.name,
            "vel_max": vmax,
            "vel_mean": vmean / count if count else 0.0,
            "particle_count": float(count),
            "radial_vel_mean": radial_mean / radial_count if radial_count else 0.0,
            "radial_vel_surface_mean": radial_surface_mean / surface_count if surface_count else 0.0,
            "radial_vel_surface_min": radial_surface_min,
            "radial_vel_surface_max": radial_surface_max,
            "surface_particle_count": float(surface_count),
        })
    return rows


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def maybe_plot(diag_rows: list[dict[str, object]], vel_rows: list[dict[str, object]]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    fig_dir = ROOT / "figures"
    fig_dir.mkdir(exist_ok=True)
    for case in sorted({r["case"] for r in diag_rows}):
        sub = [r for r in diag_rows if r["case"] == case]
        if not sub:
            continue
        t = [float(r["time"]) for r in sub]
        p0 = [float(r["p0_eff"]) for r in sub]
        fx = [float(r["net_fx"]) for r in sub]
        fy = [float(r["net_fy"]) for r in sub]
        fz = [float(r["net_fz"]) for r in sub]
        plt.figure(figsize=(6, 4))
        plt.plot(t, p0, marker="o")
        plt.xlabel("time [s]")
        plt.ylabel("effective p0 [Pa]")
        plt.title(f"{case}: confining stress ramp")
        plt.tight_layout()
        plt.savefig(fig_dir / f"{case}_p0_ramp.png", dpi=180)
        plt.savefig(fig_dir / f"{case}_p0_ramp.svg")
        plt.close()
        plt.figure(figsize=(6, 4))
        plt.plot(t, fx, marker="o", label="Fx")
        plt.plot(t, fy, marker="o", label="Fy")
        plt.plot(t, fz, marker="o", label="Fz")
        plt.xlabel("time [s]")
        plt.ylabel("net force [N]")
        plt.title(f"{case}: net confining force")
        plt.legend()
        plt.tight_layout()
        plt.savefig(fig_dir / f"{case}_net_force.png", dpi=180)
        plt.savefig(fig_dir / f"{case}_net_force.svg")
        plt.close()
    if vel_rows:
        plt.figure(figsize=(6, 4))
        for case in sorted({r["case"] for r in vel_rows}):
            sub = [r for r in vel_rows if r["case"] == case]
            x = list(range(len(sub)))
            y = [float(r["vel_max"]) for r in sub]
            plt.plot(x, y, marker="o", label=case)
        plt.xlabel("frame index")
        plt.ylabel("velocity max [m/s]")
        plt.title("C4-B3 velocity smoke")
        plt.legend()
        plt.tight_layout()
        plt.savefig(fig_dir / "c4b3_velocity_max.png", dpi=180)
        plt.savefig(fig_dir / "c4b3_velocity_max.svg")
        plt.close()
        plt.figure(figsize=(6, 4))
        for case in sorted({r["case"] for r in vel_rows}):
            sub = [r for r in vel_rows if r["case"] == case]
            x = list(range(len(sub)))
            y = [float(r.get("radial_vel_surface_mean", 0.0)) for r in sub]
            plt.plot(x, y, marker="o", label=case)
        plt.axhline(0.0, color="0.4", linewidth=0.8)
        plt.xlabel("frame index")
        plt.ylabel("surface radial velocity mean [m/s]")
        plt.title("C4-B3 surface radial velocity sign")
        plt.legend()
        plt.tight_layout()
        plt.savefig(fig_dir / "c4b3_surface_radial_velocity.png", dpi=180)
        plt.savefig(fig_dir / "c4b3_surface_radial_velocity.svg")
        plt.close()


def main() -> None:
    diag_rows: list[dict[str, object]] = []
    vel_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    for label, case_name in CASES:
        diagnostics, meta = read_runout(case_name)
        velocities = vtk_velocity_metrics(case_name)
        if not velocities:
            velocities = partcsv_velocity_metrics(case_name)
        for row in diagnostics:
            diag_rows.append({
                "case": label,
                "step": row["step"],
                "time": row["time"],
                "p0_eff": row["p0"],
                "targets": row["targets"],
                "net_fx": row["fx"],
                "net_fy": row["fy"],
                "net_fz": row["fz"],
                "total_abs_force": row["fabs"],
                "max_accel": row["amax"],
                "com_accel": row["acom"],
                "symmetry_residual": row["sym"],
            })
        for i, row in enumerate(velocities):
            vel_rows.append({"case": label, "frame_index": i, **row})
        final_diag = diagnostics[-1] if diagnostics else {}
        final_vel = velocities[-1] if velocities else {}
        summary_rows.append({
            "case": label,
            "runout_exists": meta["runout_exists"],
            "code": meta["code"],
            "excluded": meta["excluded"],
            "diagnostic_rows": len(diagnostics),
            "final_p0_eff": final_diag.get("p0", 0.0),
            "final_symmetry_residual": final_diag.get("sym", 0.0),
            "final_com_accel": final_diag.get("acom", 0.0),
            "final_max_conf_accel": final_diag.get("amax", 0.0),
            "final_vel_max": final_vel.get("vel_max", 0.0),
            "final_vel_mean": final_vel.get("vel_mean", 0.0),
            "final_radial_vel_surface_mean": final_vel.get("radial_vel_surface_mean", 0.0),
            "final_radial_vel_surface_min": final_vel.get("radial_vel_surface_min", 0.0),
            "final_radial_vel_surface_max": final_vel.get("radial_vel_surface_max", 0.0),
        })
    write_csv(ROOT / "c4b3_confining_force_diagnostics.csv", diag_rows, [
        "case", "step", "time", "p0_eff", "targets", "net_fx", "net_fy", "net_fz",
        "total_abs_force", "max_accel", "com_accel", "symmetry_residual",
    ])
    write_csv(ROOT / "c4b3_sign_smoke_metrics.csv", vel_rows, [
        "case", "frame_index", "frame_file", "vel_max", "vel_mean", "particle_count",
        "radial_vel_mean", "radial_vel_surface_mean", "radial_vel_surface_min",
        "radial_vel_surface_max", "surface_particle_count",
    ])
    write_csv(ROOT / "c4b3_flexible_confining_stress_summary.csv", summary_rows, [
        "case", "runout_exists", "code", "excluded", "diagnostic_rows",
        "final_p0_eff", "final_symmetry_residual", "final_com_accel",
        "final_max_conf_accel", "final_vel_max", "final_vel_mean",
        "final_radial_vel_surface_mean", "final_radial_vel_surface_min",
        "final_radial_vel_surface_max",
    ])
    maybe_plot(diag_rows, vel_rows)


if __name__ == "__main__":
    main()
