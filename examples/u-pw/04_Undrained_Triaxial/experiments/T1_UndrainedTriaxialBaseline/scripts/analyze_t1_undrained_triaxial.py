#!/usr/bin/env python3
"""Postprocess the T1 reduced undrained triaxial baseline.

The script reads DualSPHysics PartCsv outputs and writes compact CSV metrics
and smoke figures. The stress-path calculation is an engineering diagnostic,
not a paper-quality triaxial reduction.
"""
import argparse
import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def f(row, key, default=math.nan):
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def read_rows(path):
    with path.open(newline="") as fp:
        return [row for row in csv.DictReader(fp, delimiter=";") if row.get("Idp")]


def mean(values):
    vals = [v for v in values if math.isfinite(v)]
    return sum(vals) / len(vals) if vals else math.nan


def pctl(values, pct):
    vals = sorted(v for v in values if math.isfinite(v))
    if not vals:
        return math.nan
    pos = (len(vals) - 1) * pct / 100.0
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return vals[lo]
    return vals[lo] * (hi - pos) + vals[hi] * (pos - lo)


def velocity(row):
    vx = f(row, "Vel.x [m/s]")
    vy = f(row, "Vel.y [m/s]")
    vz = f(row, "Vel.z [m/s]")
    if not (math.isfinite(vx) and math.isfinite(vy) and math.isfinite(vz)):
        return math.nan
    return math.sqrt(vx * vx + vy * vy + vz * vz)


def stress_pq(row):
    sxx = f(row, "Sigma_kk.x")
    syy = f(row, "Sigma_kk.y")
    szz = f(row, "Sigma_kk.z")
    sxy = f(row, "Sigma_ij.x")
    sxz = f(row, "Sigma_ij.y")
    syz = f(row, "Sigma_ij.z")
    if not all(math.isfinite(v) for v in (sxx, syy, szz, sxy, sxz, syz)):
        return math.nan, math.nan
    p_eff = -(sxx + syy + szz) / 3.0
    dev = [sxx + p_eff, syy + p_eff, szz + p_eff]
    j2 = 0.5 * (dev[0] ** 2 + dev[1] ** 2 + dev[2] ** 2) + sxy ** 2 + sxz ** 2 + syz ** 2
    q = math.sqrt(max(0.0, 3.0 * j2))
    return p_eff, q


def write_csv(path, rows, fieldnames=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_run_out(data_dir):
    out = data_dir.parent / "Run.out"
    times = {"0000": 0.0}
    info = {"excluded_particles": math.nan, "steps": math.nan, "runtime_s": math.nan}
    if not out.exists():
        return times, info
    for line in out.read_text(errors="ignore").splitlines():
        text = line.strip()
        if text.startswith("Part_"):
            parts = text.split()
            if len(parts) >= 2 and parts[0].startswith("Part_"):
                frame = parts[0].replace("Part_", "")
                try:
                    times[frame] = 0.0 if "successfully" in text else float(parts[1])
                except ValueError:
                    pass
        elif text.startswith("Excluded particles"):
            try:
                info["excluded_particles"] = int(text.split(":")[-1])
            except ValueError:
                pass
        elif text.startswith("Steps of simulation"):
            try:
                info["steps"] = int(text.split(":")[-1])
            except ValueError:
                pass
        elif text.startswith("Total Runtime"):
            try:
                info["runtime_s"] = float(text.split(":")[-1].split()[0])
            except ValueError:
                pass
    return times, info


def save_plot(figdir, name):
    figdir.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(figdir / f"{name}.svg")
    plt.savefig(figdir / f"{name}.png", dpi=160)
    plt.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="CaseUndrainedTriaxial_PR_T1_Baseline_out/data")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--time-out", type=float, default=0.00025)
    args = ap.parse_args()

    data = Path(args.data)
    outdir = Path(args.outdir)
    figdir = outdir / "figures"
    files = sorted(data.glob("PartCsv_*.csv"))
    if not files:
        raise SystemExit(f"no PartCsv files found in {data}")

    first = read_rows(files[0])
    if not first:
        raise SystemExit("first PartCsv has no rows")
    xs0 = [f(r, "Pos.x [m]") for r in first]
    zs0 = [f(r, "Pos.z [m]") for r in first]
    xmin, xmax = min(xs0), max(xs0)
    zmin, zmax = min(zs0), max(zs0)
    width = xmax - xmin
    height = zmax - zmin
    mid_ids = set()
    top_ids = set()
    for r in first:
        x = f(r, "Pos.x [m]")
        z = f(r, "Pos.z [m]")
        pid = r.get("Idp")
        # T1 is a very short top-loaded smoke, so the diagnostic region is the
        # upper-middle core below the AccInput layer rather than the unloaded
        # geometric center.
        if xmin + 0.25 * width <= x <= xmin + 0.75 * width and zmin + 0.70 * height <= z <= zmin + 0.90 * height:
            mid_ids.add(pid)
        if z >= zmax - max(0.02 * height, 0.0101):
            top_ids.add(pid)

    top0 = mean(f(r, "Pos.z [m]") for r in first if r.get("Idp") in top_ids)
    h0 = height if height > 0 else math.nan

    frame_rows = []
    region_rows = []
    pore_rows = []
    stress_rows = []
    min_pressure = math.inf
    nan_count = 0
    part_times, run_info = parse_run_out(data)

    for idx, path in enumerate(files):
        rows = read_rows(path)
        region = [r for r in rows if r.get("Idp") in mid_ids]
        top = [r for r in rows if r.get("Idp") in top_ids]
        top_mean = mean(f(r, "Pos.z [m]") for r in top)
        axial_disp = top_mean - top0 if math.isfinite(top_mean) and math.isfinite(top0) else math.nan
        axial_strain = -axial_disp / h0 if math.isfinite(axial_disp) and math.isfinite(h0) and h0 > 0 else math.nan

        def collect(sample):
            pp = [f(r, "PorePress") for r in sample]
            ep = [f(r, "ExcessPorePress") for r in sample]
            pr = [f(r, "PorePressRate") for r in sample]
            dv = [f(r, "DivVel") for r in sample]
            kp = [f(r, "Kplastic") for r in sample]
            vel = [velocity(r) for r in sample]
            pq = [stress_pq(r) for r in sample]
            return {
                "count": len(sample),
                "porepress_mean": mean(pp),
                "porepress_min": min([v for v in pp if math.isfinite(v)], default=math.nan),
                "porepress_max": max([v for v in pp if math.isfinite(v)], default=math.nan),
                "excess_mean": mean(ep),
                "excess_p95": pctl(ep, 95),
                "porepressrate_mean": mean(pr),
                "porepressrate_maxabs": max([abs(v) for v in pr if math.isfinite(v)], default=math.nan),
                "divvel_mean": mean(dv),
                "divvel_min": min([v for v in dv if math.isfinite(v)], default=math.nan),
                "divvel_max": max([v for v in dv if math.isfinite(v)], default=math.nan),
                "kplastic_mean": mean(kp),
                "kplastic_max": max([v for v in kp if math.isfinite(v)], default=math.nan),
                "velocity_mean": mean(vel),
                "velocity_max": max([v for v in vel if math.isfinite(v)], default=math.nan),
                "p_eff_mean": mean(p for p, _ in pq),
                "q_mean": mean(q for _, q in pq),
            }

        allm = collect(rows)
        regm = collect(region)
        frame = path.stem.replace("PartCsv_", "")
        t = part_times.get(frame, idx * args.time_out)
        rec = {
            "frame": frame,
            "time_s": t,
            "axial_displacement_m": axial_disp,
            "axial_strain_compression_positive": axial_strain,
            **{f"all_{k}": v for k, v in allm.items()},
            **{f"region_{k}": v for k, v in regm.items()},
        }
        frame_rows.append(rec)
        region_rows.append({"frame": frame, "time_s": t, "axial_strain_compression_positive": axial_strain, **regm})
        pore_rows.append({
            "frame": frame,
            "time_s": t,
            "region_porepress_mean": regm["porepress_mean"],
            "region_excess_mean": regm["excess_mean"],
            "region_porepressrate_mean": regm["porepressrate_mean"],
            "region_porepressrate_maxabs": regm["porepressrate_maxabs"],
            "region_divvel_mean": regm["divvel_mean"],
            "all_porepress_mean": allm["porepress_mean"],
            "all_excess_mean": allm["excess_mean"],
        })
        stress_rows.append({
            "frame": frame,
            "time_s": t,
            "axial_strain_compression_positive": axial_strain,
            "p_eff_mean_region": regm["p_eff_mean"],
            "q_mean_region": regm["q_mean"],
            "p_eff_mean_all": allm["p_eff_mean"],
            "q_mean_all": allm["q_mean"],
        })

        for r in rows:
            for key in ("PorePress", "ExcessPorePress", "PorePressRate", "DivVel", "Kplastic"):
                val = f(r, key)
                if not math.isfinite(val):
                    nan_count += 1
            pp = f(r, "PorePress")
            if math.isfinite(pp):
                min_pressure = min(min_pressure, pp)

    write_csv(outdir / "t1_frame_metrics.csv", frame_rows)
    write_csv(outdir / "t1_measurement_region_metrics.csv", region_rows)
    write_csv(outdir / "t1_pore_pressure_metrics.csv", pore_rows)
    write_csv(outdir / "t1_stress_path_metrics.csv", stress_rows)

    last = frame_rows[-1]
    summary = [{
        "frames": len(files),
        "excluded_particles": run_info["excluded_particles"],
        "steps": run_info["steps"],
        "runtime_s": run_info["runtime_s"],
        "material_rows_last": last["all_count"],
        "measurement_region_count": last["region_count"],
        "top_tracking_count": len(top_ids),
        "final_time_s": last["time_s"],
        "final_axial_displacement_m": last["axial_displacement_m"],
        "final_axial_strain": last["axial_strain_compression_positive"],
        "final_region_excess_mean_pa": last["region_excess_mean"],
        "final_region_porepress_mean_pa": last["region_porepress_mean"],
        "final_region_porepressrate_maxabs_pa_s": last["region_porepressrate_maxabs"],
        "final_region_divvel_mean_1_s": last["region_divvel_mean"],
        "final_kplastic_max": last["all_kplastic_max"],
        "final_velocity_max_m_s": last["all_velocity_max"],
        "min_porepress_all_pa": min_pressure,
        "nan_or_inf_field_count": nan_count,
    }]
    write_csv(outdir / "t1_case_summary.csv", summary)

    times = [r["time_s"] for r in frame_rows]
    plt.figure()
    plt.plot(times, [r["axial_displacement_m"] for r in frame_rows], marker="o")
    plt.xlabel("time [s]")
    plt.ylabel("top displacement [m]")
    save_plot(figdir, "t1_axial_displacement_vs_time")

    plt.figure()
    plt.plot(times, [r["axial_strain_compression_positive"] for r in frame_rows], marker="o")
    plt.xlabel("time [s]")
    plt.ylabel("axial strain, compression positive")
    save_plot(figdir, "t1_axial_strain_vs_time")

    plt.figure()
    plt.plot(times, [r["region_porepress_mean"] for r in frame_rows], marker="o", label="PorePress")
    plt.plot(times, [r["region_excess_mean"] for r in frame_rows], marker="s", label="ExcessPorePress")
    plt.xlabel("time [s]")
    plt.ylabel("pressure [Pa]")
    plt.legend()
    save_plot(figdir, "t1_pore_pressure_vs_time")

    plt.figure()
    plt.plot(times, [r["all_velocity_max"] for r in frame_rows], marker="o")
    plt.xlabel("time [s]")
    plt.ylabel("max velocity [m/s]")
    save_plot(figdir, "t1_velocity_max_vs_time")

    plt.figure()
    plt.plot(times, [r["region_divvel_mean"] for r in frame_rows], marker="o", label="DivVel")
    plt.plot(times, [r["region_porepressrate_mean"] for r in frame_rows], marker="s", label="PorePressRate")
    plt.xlabel("time [s]")
    plt.legend()
    save_plot(figdir, "t1_divvel_porepressrate_vs_time")

    plt.figure()
    plt.plot(times, [r["all_kplastic_max"] for r in frame_rows], marker="o")
    plt.xlabel("time [s]")
    plt.ylabel("Kplastic max")
    save_plot(figdir, "t1_kplastic_max_vs_time")

    plt.figure()
    plt.plot([r["p_eff_mean_region"] for r in stress_rows], [r["q_mean_region"] for r in stress_rows], marker="o")
    plt.xlabel("p' proxy [Pa]")
    plt.ylabel("q proxy [Pa]")
    save_plot(figdir, "t1_pq_path_proxy")

    print("frames,region_count,final_excess_mean,final_kplastic_max,final_velocity_max,nan_or_inf_field_count")
    print(f"{len(files)},{last['region_count']},{last['region_excess_mean']},{last['all_kplastic_max']},{last['all_velocity_max']},{nan_count}")


if __name__ == "__main__":
    main()
