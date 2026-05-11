from __future__ import annotations

import csv
import math
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[5]
EXPDIR = Path(__file__).resolve().parent
CPU_B1 = EXPDIR.parent / "CPU_B1_BoundaryOperator"
BIN = ROOT / "bin/windows"
GENCASE = BIN / "GenCase_win64.exe"
CPU_EXE = BIN / "DualSPHysics5.2CPU_win64.exe"
GPU_EXE = BIN / "DualSPHysics5.2_GEO_win64.exe"

FIELDS = "+idp,+vel,+rhop,+type,+mk,+PorePress,+ExcessPorePress,+PorePressRate,+DivVel,+LapPorePress,+LapZ,+PorePressureAccelDiff"
KERNEL_H = 0.018

CASES = [
    {
        "label": "hydrostatic_mode1_gpu",
        "source": CPU_B1 / "CaseB1_hydrostatic_mode1_Def.xml",
        "run_cpu": False,
        "run_gpu": True,
    },
    {
        "label": "diffusion_mode1_parity",
        "source": CPU_B1 / "CaseB1_diffusion_profile_mode1_Def.xml",
        "run_cpu": True,
        "run_gpu": True,
    },
    {
        "label": "selfweight_mode1_parity",
        "source": CPU_B1 / "CaseB1_selfweight_short_mode1_Def.xml",
        "run_cpu": True,
        "run_gpu": True,
    },
    {
        "label": "selfweight_mode0_gpu",
        "source": CPU_B1 / "CaseB1_selfweight_short_mode0_Def.xml",
        "run_cpu": False,
        "run_gpu": True,
    },
    {
        "label": "selfweight_mode1_medium_gpu",
        "source": CPU_B1 / "CaseB1_selfweight_short_mode1_Def.xml",
        "run_cpu": False,
        "run_gpu": True,
        "time_max": "0.05",
        "time_out": "0.005",
    },
]


def set_param(root: ET.Element, key: str, value: str) -> None:
    params = root.find("./execution/parameters")
    if params is None:
        raise RuntimeError("Missing execution/parameters")
    for p in params.findall("parameter"):
        if p.get("key") == key:
            p.set("value", str(value))
            return
    p = ET.SubElement(params, "parameter")
    p.set("key", key)
    p.set("value", str(value))


def prepare_xml(case: dict) -> str:
    src = Path(case["source"])
    name = f"CaseB4_{case['label']}"
    tree = ET.parse(src)
    root = tree.getroot()
    set_param(root, "PorePressureBoundaryOperator", "1" if "mode1" in case["label"] else "0")
    if "time_max" in case:
        set_param(root, "TimeMax", case["time_max"])
    if "time_out" in case:
        set_param(root, "TimeOut", case["time_out"])
    out = EXPDIR / f"{name}_Def.xml"
    tree.write(out, encoding="utf-8", xml_declaration=True)
    return name


def run_cmd(cmd: list[str], cwd: Path) -> tuple[int, str]:
    print("RUN:", " ".join(str(c) for c in cmd), flush=True)
    proc = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(proc.stdout, flush=True)
    return proc.returncode, proc.stdout


def run_case(name: str, backend: str) -> Path:
    outdir = EXPDIR / f"{name}_{backend}_out"
    if outdir.exists():
        shutil.rmtree(outdir)
    code, _ = run_cmd([str(GENCASE), f"{name}_Def", str(outdir / name), "-save:all"], EXPDIR)
    if code:
        raise RuntimeError(f"GenCase failed for {name} {backend}")
    exe = CPU_EXE if backend == "cpu" else GPU_EXE
    flag = "-cpu" if backend == "cpu" else "-gpu"
    code, _ = run_cmd([str(exe), flag, "-mdbc", str(outdir / name), str(outdir), "-dirdataout", "data", "-sv:csv,binx"], EXPDIR)
    if code:
        raise RuntimeError(f"DualSPHysics failed for {name} {backend}")
    return outdir


def parse_run(outdir: Path) -> dict[str, str]:
    text = (outdir / "Run.out").read_text(errors="replace") if (outdir / "Run.out").exists() else ""
    pats = {
        "code": r"Finished execution \(code=(\d+)\)",
        "excluded": r"Excluded particles\.+:\s*(\d+)",
        "steps": r"Steps of simulation\.+:\s*(\d+)",
        "runtime_s": r"Total Runtime\.+:\s*([0-9.Ee+-]+)",
    }
    return {k: (m.group(1) if (m := re.search(p, text)) else "") for k, p in pats.items()}


def clean_header(header: list[str]) -> list[str]:
    return [h.strip().split()[0] for h in header if h.strip()]


def read_part(path: Path) -> tuple[list[str], list[dict[str, float]]]:
    with path.open(newline="", errors="ignore") as f:
        reader = csv.reader(f, delimiter=";")
        header = clean_header(next(reader))
        rows = []
        for raw in reader:
            vals = [v.strip() for v in raw if v.strip()]
            if len(vals) != len(header):
                continue
            row = {}
            for key, val in zip(header, vals):
                try:
                    row[key] = float(val)
                except ValueError:
                    row[key] = math.nan
            rows.append(row)
    return header, rows


def final_material(outdir: Path) -> tuple[list[str], list[dict[str, float]], Path]:
    parts = sorted((outdir / "data").glob("PartCsv_*.csv"))
    if not parts:
        return [], [], Path()
    part = parts[-1]
    header, rows = read_part(part)
    return header, [r for r in rows if int(r.get("Type", -1)) == 3], part


def stats(vals: list[float]) -> tuple[float, float, float, float]:
    clean = [v for v in vals if math.isfinite(v)]
    if not clean:
        return math.nan, math.nan, math.nan, math.nan
    return min(clean), max(clean), sum(clean) / len(clean), max(abs(v) for v in clean)


def vecmag(row: dict[str, float], field: str) -> float:
    x = row.get(f"{field}.x", math.nan)
    y = row.get(f"{field}.y", math.nan)
    z = row.get(f"{field}.z", math.nan)
    if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
        return math.nan
    return math.sqrt(x * x + y * y + z * z)


def summarize(outdir: Path, label: str, backend: str) -> dict[str, str]:
    run = parse_run(outdir)
    header, rows, part = final_material(outdir)
    zvals = [r.get("Pos.z", math.nan) for r in rows if math.isfinite(r.get("Pos.z", math.nan))]
    zmin, zmax = (min(zvals), max(zvals)) if zvals else (math.nan, math.nan)
    top = [r for r in rows if r.get("Pos.z", -1e99) >= zmax - KERNEL_H]
    bottom = [r for r in rows if r.get("Pos.z", 1e99) <= zmin + KERNEL_H]
    ref = [r for r in rows if zmin + KERNEL_H < r.get("Pos.z", math.nan) <= zmin + 2 * KERNEL_H]
    _, _, ref_ex, _ = stats([r.get("ExcessPorePress", math.nan) for r in ref])
    bottom_proxy = [abs(r.get("ExcessPorePress", math.nan) - ref_ex) for r in bottom if math.isfinite(ref_ex)]
    out = {
        "label": label,
        "backend": backend,
        **run,
        "frame": part.stem,
        "n": str(len(rows)),
        "top_excess_maxAbs": f"{stats([r.get('ExcessPorePress', math.nan) for r in top])[3]:.9g}",
        "bottom_no_flux_proxy": f"{stats(bottom_proxy)[3]:.9g}",
    }
    for field in ("PorePress", "ExcessPorePress", "PorePressRate", "DivVel", "LapPorePress", "LapZ"):
        mn, mx, mean, ma = stats([r.get(field, math.nan) for r in rows])
        out[f"{field}_min"] = f"{mn:.9g}"
        out[f"{field}_max"] = f"{mx:.9g}"
        out[f"{field}_mean"] = f"{mean:.9g}"
        out[f"{field}_maxAbs"] = f"{ma:.9g}"
    out["Vel_maxAbs"] = f"{stats([vecmag(r, 'Vel') for r in rows])[3]:.9g}"
    out["PorePressureAccelDiff_maxAbs"] = f"{stats([vecmag(r, 'PorePressureAccelDiff') for r in rows])[3]:.9g}"
    return out


def by_id(rows: list[dict[str, float]]) -> dict[int, dict[str, float]]:
    return {int(r["Idp"]): r for r in rows if math.isfinite(r.get("Idp", math.nan))}


def compare_rows(label: str, rows_a: list[dict[str, float]], rows_b: list[dict[str, float]], tag_a: str, tag_b: str) -> dict[str, str]:
    a = by_id(rows_a)
    b = by_id(rows_b)
    ids = sorted(set(a) & set(b))
    result = {"label": label, "a": tag_a, "b": tag_b, "matched": str(len(ids))}
    for field in ("PorePress", "ExcessPorePress", "PorePressRate", "DivVel", "LapPorePress", "LapZ"):
        diffs = [abs(a[i].get(field, math.nan) - b[i].get(field, math.nan)) for i in ids]
        _, _, mean, ma = stats(diffs)
        result[f"{field}_diff_meanAbs"] = f"{mean:.9g}"
        result[f"{field}_diff_maxAbs"] = f"{ma:.9g}"
    diffs = [abs(vecmag(a[i], "PorePressureAccelDiff") - vecmag(b[i], "PorePressureAccelDiff")) for i in ids]
    _, _, mean, ma = stats(diffs)
    result["PorePressureAccelDiff_mag_diff_meanAbs"] = f"{mean:.9g}"
    result["PorePressureAccelDiff_mag_diff_maxAbs"] = f"{ma:.9g}"
    return result


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    keys = sorted({k for row in rows for k in row})
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def plot_pressure(results: dict[str, tuple[list[str], list[dict[str, float]]]]) -> None:
    figdir = EXPDIR / "figures"
    figdir.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(9, 4), sharey=True)
    targets = [
        ("diffusion_mode1_parity_cpu", "CPU mode=1", "#1f77b4", "-"),
        ("diffusion_mode1_parity_gpu", "GPU mode=1", "#d62728", "--"),
        ("selfweight_mode1_parity_gpu", "SW GPU mode=1", "#2ca02c", "-"),
        ("selfweight_mode0_gpu_gpu", "SW GPU mode=0", "#777777", ":"),
    ]
    for ax, field in zip(axes, ["ExcessPorePress", "PorePressRate"]):
        for key, label, color, style in targets:
            if key not in results:
                continue
            _, rows = results[key]
            pts = sorted([(r.get(field, math.nan), r.get("Pos.z", math.nan)) for r in rows])
            xs = [p[0] for p in pts if math.isfinite(p[0]) and math.isfinite(p[1])]
            ys = [p[1] for p in pts if math.isfinite(p[0]) and math.isfinite(p[1])]
            ax.plot(xs, ys, style, lw=1.6, color=color, label=label)
        ax.set_xlabel(field)
        ax.grid(True, alpha=0.25)
    axes[0].set_ylabel("z [m]")
    axes[0].legend(fontsize=8)
    fig.tight_layout()
    for ext in ("svg", "png"):
        fig.savefig(figdir / f"gpu_b4_boundary_operator_parity.{ext}", dpi=180)


def cleanup_outputs() -> None:
    for outdir in EXPDIR.glob("CaseB4_*_out"):
        shutil.rmtree(outdir, ignore_errors=True)


def main() -> None:
    summaries: list[dict[str, str]] = []
    comparisons: list[dict[str, str]] = []
    material: dict[str, tuple[list[str], list[dict[str, float]]]] = {}
    for cfg in CASES:
        name = prepare_xml(cfg)
        if cfg.get("run_cpu"):
            out = run_case(name, "cpu")
            summaries.append(summarize(out, cfg["label"], "cpu"))
            header, rows, _ = final_material(out)
            material[f"{cfg['label']}_cpu"] = (header, rows)
        if cfg.get("run_gpu"):
            out = run_case(name, "gpu")
            summaries.append(summarize(out, cfg["label"], "gpu"))
            header, rows, _ = final_material(out)
            material[f"{cfg['label']}_gpu"] = (header, rows)

    for label in ("diffusion_mode1_parity", "selfweight_mode1_parity"):
        ca, ga = material.get(f"{label}_cpu"), material.get(f"{label}_gpu")
        if ca and ga:
            comparisons.append(compare_rows(label, ca[1], ga[1], "cpu", "gpu"))
    if "selfweight_mode1_parity_gpu" in material and "selfweight_mode0_gpu_gpu" in material:
        comparisons.append(compare_rows("selfweight_gpu_mode1_vs_mode0", material["selfweight_mode1_parity_gpu"][1], material["selfweight_mode0_gpu_gpu"][1], "mode1", "mode0"))

    write_csv(EXPDIR / "gpu_b4_boundary_operator_summary.csv", summaries)
    write_csv(EXPDIR / "gpu_b4_boundary_operator_comparison.csv", comparisons)
    plot_pressure(material)
    cleanup_outputs()
    print("B4 completed. Heavy outputs cleaned.")


if __name__ == "__main__":
    main()

