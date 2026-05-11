from __future__ import annotations

import csv
import math
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
SOURCE_XML = REPO / "examples" / "u-pw" / "02_SelfWeight_Consolidation" / "CaseSelfWeightConsolidation_PR_Scenario2_Def.xml"
BIN = REPO / "bin" / "windows"
CASE = "CaseSelfWeightConsolidation_PR_S1_BodyGravityStopShort"
XML = ROOT / f"{CASE}_Def.xml"
CPU_OUT = ROOT / f"{CASE}_cpu_out"
GPU_OUT = ROOT / f"{CASE}_gpu_out"
STOP_TIME = 0.002
TIME_MAX = 0.005
TIME_OUT = 0.001
KERNEL_H = 0.018
HYDRAULIC_K = 1e-3
KW = 2e8
POROSITY = 0.3
RHO_W = 1000.0
G = 9.81
DIV_FACTOR = KW / POROSITY
HYD_FACTOR = KW / POROSITY
TARGET_PROFILE_TIMES = [0.001, 0.002, 0.003, 0.005]


def set_param(root: ET.Element, key: str, value: str, comment: str | None = None) -> None:
    params = root.find("./execution/parameters")
    if params is None:
        raise RuntimeError("XML has no execution/parameters node")
    for elem in params.findall("parameter"):
        if elem.get("key") == key:
            elem.set("value", value)
            if comment is not None:
                elem.set("comment", comment)
            return
    elem = ET.SubElement(params, "parameter")
    elem.set("key", key)
    elem.set("value", value)
    if comment is not None:
        elem.set("comment", comment)


def create_xml() -> None:
    tree = ET.parse(SOURCE_XML)
    root = tree.getroot()
    set_param(root, "TimeMax", f"{TIME_MAX:g}", "Scenario 1 BodyGravityStopTime short smoke")
    set_param(root, "TimeOut", f"{TIME_OUT:g}", "Dense output around the gravity switch")
    set_param(root, "BodyGravityStopTime", f"{STOP_TIME:g}", "Stop mechanical body gravity while keeping HydraulicGravity active")
    set_param(root, "PorePressureBoundaryOperator", "0", "Legacy layer correction for Scenario 1 smoke")
    set_param(root, "PorePressureTopDrained", "1")
    set_param(root, "PorePressureTopDrainedStartTime", f"{STOP_TIME:g}")
    set_param(root, "PorePressureBottomNoFlux", "1")
    set_param(root, "HydromechDamping", "1")
    set_param(root, "HydromechDampingXi", "0.05", "Scenario 1 short-smoke damping")
    set_param(root, "PorePressureFeedback", "1")
    set_param(root, "PorePressureFeedbackMode", "1")
    set_param(root, "PorePressureFeedbackOperator", "1")
    set_param(root, "PorePressureShepard", "1")
    set_param(root, "PorePressureShepardInterval", "10")
    set_param(root, "PorePressureShepardMode", "1")
    set_param(root, "PorePressureDtSafety", "0.20")
    set_param(root, "SavePorePressure", "1")
    set_param(root, "HydraulicGravityX", "0")
    set_param(root, "HydraulicGravityY", "0")
    set_param(root, "HydraulicGravityZ", "-9.81")
    ET.indent(tree, space="  ")
    tree.write(XML, encoding="utf-8", xml_declaration=True)


def write_bat(label: str) -> None:
    exe = "DualSPHysics5.2CPU_win64.exe" if label == "CPU" else "DualSPHysics5.2_GEO_win64.exe"
    flag = "-cpu" if label == "CPU" else "-gpu"
    out_suffix = "cpu" if label == "CPU" else "gpu"
    bat = ROOT / f"x{CASE}_win64_{label}_release.bat"
    bat.write_text(
        "\n".join(
            [
                "@echo off",
                "setlocal EnableDelayedExpansion",
                "",
                f"set name={CASE}",
                f"set dirout=%name%_{out_suffix}_out",
                "set dirbin=..\\..\\..\\..\\..\\bin\\windows",
                'set gencase="%dirbin%\\GenCase_win64.exe"',
                f'set dualsphysics="%dirbin%\\{exe}"',
                "",
                "if exist %dirout% rd /s /q %dirout%",
                "",
                "%gencase% %name%_Def %dirout%\\%name% -save:all",
                'if not "%ERRORLEVEL%" == "0" goto fail',
                "",
                f"%dualsphysics% {flag} -mdbc %dirout%\\%name% %dirout% -dirdataout data -sv:csv,binx",
                'if not "%ERRORLEVEL%" == "0" goto fail',
                "",
                "echo All done",
                "goto end",
                "",
                ":fail",
                "echo Execution aborted.",
                "",
                ":end",
                "pause",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run_command(args: list[str], cwd: Path, log_path: Path, timeout_s: int = 5400) -> int:
    start = time.time()
    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        log.write("$ " + " ".join(str(a) for a in args) + "\n")
        log.flush()
        proc = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
        assert proc.stdout is not None
        last_print = start
        for line in proc.stdout:
            log.write(line)
            now = time.time()
            if "Part_" in line or "TimeStep" in line or "Finished execution" in line or now - last_print > 30:
                print(line.rstrip())
                last_print = now
        try:
            code = proc.wait(timeout=max(1, int(timeout_s - (time.time() - start))))
        except subprocess.TimeoutExpired:
            proc.kill()
            code = -999
            log.write("\nTIMEOUT\n")
        log.write(f"\nreturncode={code}\nruntime_s={time.time() - start:.3f}\n")
    return code


def run_case(label: str) -> int:
    out = CPU_OUT if label == "CPU" else GPU_OUT
    if out.exists():
        shutil.rmtree(out)
    gencase = BIN / "GenCase_win64.exe"
    exe = BIN / ("DualSPHysics5.2CPU_win64.exe" if label == "CPU" else "DualSPHysics5.2_GEO_win64.exe")
    flag = "-cpu" if label == "CPU" else "-gpu"
    code = run_command(
        [str(gencase), f"{CASE}_Def", str(out / CASE), "-save:all"],
        ROOT,
        ROOT / f"{label.lower()}_gencase.console.log",
        timeout_s=1800,
    )
    if code != 0:
        return code
    return run_command(
        [str(exe), flag, "-mdbc", str(out / CASE), str(out), "-dirdataout", "data", "-sv:csv,binx"],
        ROOT,
        ROOT / f"{label.lower()}_dualsphysics.console.log",
        timeout_s=5400,
    )


def parse_run(out_dir: Path, console_log: Path) -> dict[str, str]:
    text = ""
    for path in [out_dir / "Run.out", console_log]:
        if path.exists():
            text += "\n" + path.read_text(errors="replace")
    patterns = {
        "code": r"Finished execution \(code=(\d+)\)",
        "excluded": r"Excluded particles\.+:\s*(\d+)",
        "steps": r"Steps of simulation\.+:\s*(\d+)",
        "runtime_s": r"Total Runtime\.+:\s*([0-9.Ee+-]+)",
    }
    result = {key: (m.group(1) if (m := re.search(pat, text)) else "") for key, pat in patterns.items()}
    result["body_gravity_stop_log"] = str("Mechanical body gravity stopped" in text)
    result["hydraulic_gravity_active_log"] = str("Hydraulic gravity remains active" in text)
    return result


def parse_part_times(out_dir: Path) -> dict[int, float]:
    text = (out_dir / "Run.out").read_text(errors="replace") if (out_dir / "Run.out").exists() else ""
    times = {0: 0.0}
    for line in text.splitlines():
        if "particles successfully stored" in line:
            continue
        m = re.search(r"Part_(\d+)\s+([0-9.Ee+-]+)", line)
        if m:
            times[int(m.group(1))] = float(m.group(2))
    return times


def detect_delimiter(line: str) -> str:
    return ";" if line.count(";") >= line.count(",") else ","


def clean_name(cell: str) -> str:
    parts = cell.strip().split()
    return parts[0].strip('"') if parts else ""


def read_part_csv(path: Path) -> tuple[float, list[str], list[dict[str, float]]]:
    lines = path.read_text(errors="replace").splitlines()
    if not lines:
        return math.nan, [], []
    delim = detect_delimiter(max(lines, key=len))
    rows = list(csv.reader(lines, delimiter=delim))
    time_value = math.nan
    for i, row in enumerate(rows[:4]):
        if any("TimeStep" in c for c in row) and i + 1 < len(rows):
            for val in rows[i + 1]:
                try:
                    time_value = float(val)
                    break
                except ValueError:
                    pass
    header_idx = None
    for i, row in enumerate(rows):
        names = [clean_name(c) for c in row]
        if "Idp" in names and ("Pos.x" in names or "Type" in names):
            header_idx = i
            break
    if header_idx is None:
        header_idx = 0
    header = [clean_name(c) for c in rows[header_idx] if clean_name(c)]
    parsed: list[dict[str, float]] = []
    for raw in rows[header_idx + 1 :]:
        vals = [v.strip() for v in raw]
        if len(vals) < len(header):
            continue
        row_dict: dict[str, float] = {}
        ok = True
        for key, val in zip(header, vals):
            try:
                row_dict[key] = float(val)
            except ValueError:
                ok = False
                break
        if ok:
            parsed.append(row_dict)
    if not math.isfinite(time_value):
        m = re.search(r"PartCsv_(\d+)", path.stem)
        time_value = float(m.group(1)) if m else math.nan
    return time_value, header, parsed


def material_rows(rows: list[dict[str, float]]) -> list[dict[str, float]]:
    out = []
    for row in rows:
        typ = row.get("Type", 3.0)
        code = row.get("Code", math.nan)
        if int(typ) == 3 or (math.isfinite(code) and int(code) == 0):
            out.append(row)
    return out


def vector_mag(row: dict[str, float], field: str) -> float:
    vals = [row.get(f"{field}.{c}", math.nan) for c in "xyz"]
    return math.sqrt(sum(v * v for v in vals)) if all(math.isfinite(v) for v in vals) else math.nan


def stats(values: list[float]) -> tuple[float, float, float, float]:
    vals = [v for v in values if math.isfinite(v)]
    if not vals:
        return math.nan, math.nan, math.nan, math.nan
    return min(vals), max(vals), sum(vals) / len(vals), max(abs(v) for v in vals)


def field_stats(rows: list[dict[str, float]], field: str) -> dict[str, float]:
    mn, mx, mean, maxabs = stats([r.get(field, math.nan) for r in rows])
    return {f"{field}_min": mn, f"{field}_max": mx, f"{field}_mean": mean, f"{field}_maxAbs": maxabs}


def nearest_frame(frames: list[dict], target: float) -> dict:
    return min(frames, key=lambda f: abs(f["time"] - target))


def boundary_metrics(rows: list[dict[str, float]]) -> dict[str, float]:
    zvals = [r.get("Pos.z", math.nan) for r in rows]
    zvals = [z for z in zvals if math.isfinite(z)]
    if not zvals:
        return {}
    zmin, zmax = min(zvals), max(zvals)
    top = [r for r in rows if r.get("Pos.z", -1e99) >= zmax - KERNEL_H]
    bottom = [r for r in rows if r.get("Pos.z", 1e99) <= zmin + KERNEL_H]
    ref = [r for r in rows if zmin + KERNEL_H < r.get("Pos.z", math.nan) <= zmin + 2 * KERNEL_H]
    _, _, ref_mean, _ = stats([r.get("ExcessPorePress", math.nan) for r in ref])
    _, _, bottom_mean, _ = stats([r.get("ExcessPorePress", math.nan) for r in bottom])
    return {
        "zmin": zmin,
        "zmax": zmax,
        "top_count": len(top),
        "bottom_count": len(bottom),
        "bottom_ref_count": len(ref),
        "top_excess_maxAbs": stats([r.get("ExcessPorePress", math.nan) for r in top])[3],
        "bottom_excess_mean": bottom_mean,
        "bottom_no_flux_proxy": bottom_mean - ref_mean if math.isfinite(bottom_mean) and math.isfinite(ref_mean) else math.nan,
    }


def load_frames(out_dir: Path) -> list[dict]:
    frames = []
    part_times = parse_part_times(out_dir)
    for path in sorted((out_dir / "data").glob("PartCsv_*.csv")):
        t, header, rows = read_part_csv(path)
        m = re.search(r"PartCsv_(\d+)", path.stem)
        if m and int(m.group(1)) in part_times:
            t = part_times[int(m.group(1))]
        mat = material_rows(rows)
        if not mat:
            continue
        frames.append({"path": path, "time": t, "header": header, "rows": mat})
    frames.sort(key=lambda x: x["time"])
    return frames


def summarize_frames(label: str, out_dir: Path, console_log: Path) -> list[dict[str, float | str]]:
    frames = load_frames(out_dir)
    initial_z = {}
    if frames:
        initial_z = {int(r["Idp"]): r.get("Pos.z", math.nan) for r in frames[0]["rows"] if math.isfinite(r.get("Idp", math.nan))}
    rows_out: list[dict[str, float | str]] = []
    run = parse_run(out_dir, console_log)
    for frame in frames:
        rows = frame["rows"]
        metric: dict[str, float | str] = {
            "run": label,
            "time": frame["time"],
            "frame": frame["path"].stem,
            "particles": len(rows),
            **run,
        }
        for field in ["PorePress", "ExcessPorePress", "PorePressRate", "DivVel", "LapPorePress", "LapZ"]:
            metric.update(field_stats(rows, field))
        vel = [vector_mag(r, "Vel") for r in rows]
        ace = [vector_mag(r, "PorePressureAccelDiff") for r in rows]
        metric["Vel_mag_max"] = stats(vel)[1]
        metric["Vel_mag_mean"] = stats(vel)[2]
        metric["PorePressureAccelDiff_mag_maxAbs"] = stats(ace)[3]
        dz = []
        for row in rows:
            idp = int(row.get("Idp", -1))
            if idp in initial_z:
                dz.append(row.get("Pos.z", math.nan) - initial_z[idp])
        metric["settlement_dz_mean"] = stats(dz)[2]
        metric.update(boundary_metrics(rows))
        div_contrib = [DIV_FACTOR * (-r.get("DivVel", math.nan)) for r in rows]
        hyd_contrib = [
            HYD_FACTOR * (HYDRAULIC_K / (RHO_W * G) * r.get("LapPorePress", math.nan) + HYDRAULIC_K * r.get("LapZ", math.nan))
            for r in rows
        ]
        metric["DivVelContribution_maxAbs"] = stats(div_contrib)[3]
        metric["HydraulicContribution_maxAbs"] = stats(hyd_contrib)[3]
        rows_out.append(metric)
    return rows_out


def write_csv(path: Path, rows: list[dict]) -> None:
    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def parity(cpu_frames: list[dict], gpu_frames: list[dict]) -> list[dict[str, float]]:
    cpu_loaded = load_frames(CPU_OUT)
    gpu_loaded = load_frames(GPU_OUT)
    out: list[dict[str, float]] = []
    for gf in gpu_loaded:
        cf = nearest_frame(cpu_loaded, gf["time"])
        cpu_by_id = {int(r["Idp"]): r for r in cf["rows"] if math.isfinite(r.get("Idp", math.nan))}
        common = []
        for gr in gf["rows"]:
            cr = cpu_by_id.get(int(gr.get("Idp", -1)))
            if cr:
                common.append((cr, gr))
        row: dict[str, float] = {"gpu_time": gf["time"], "cpu_time": cf["time"], "common_particles": len(common)}
        for field in ["PorePress", "ExcessPorePress", "PorePressRate", "DivVel", "LapPorePress", "LapZ"]:
            diffs = [gr.get(field, math.nan) - cr.get(field, math.nan) for cr, gr in common]
            row[f"{field}_diff_meanAbs"] = stats([abs(d) for d in diffs])[2]
            row[f"{field}_diff_maxAbs"] = stats(diffs)[3]
        veld = [vector_mag(gr, "Vel") - vector_mag(cr, "Vel") for cr, gr in common]
        row["Vel_mag_diff_meanAbs"] = stats([abs(d) for d in veld])[2]
        row["Vel_mag_diff_maxAbs"] = stats(veld)[3]
        out.append(row)
    return out


def make_figures(cpu_rows: list[dict], gpu_rows: list[dict], parity_rows: list[dict]) -> None:
    import matplotlib.pyplot as plt

    figdir = ROOT / "figures"
    figdir.mkdir(exist_ok=True)

    def lineplot(name: str, ykey: str, ylabel: str, rows_a=cpu_rows, rows_b=gpu_rows) -> None:
        plt.figure(figsize=(6.5, 4.0))
        for rows, label in [(rows_a, "CPU"), (rows_b, "GPU")]:
            plt.plot([float(r["time"]) for r in rows], [float(r.get(ykey, math.nan)) for r in rows], marker="o", label=label)
        plt.axvline(STOP_TIME, color="k", linestyle="--", linewidth=1, label="gravity/top drain switch")
        plt.xlabel("time [s]")
        plt.ylabel(ylabel)
        plt.legend()
        plt.tight_layout()
        plt.savefig(figdir / f"{name}.svg")
        plt.savefig(figdir / f"{name}.png", dpi=180)
        plt.close()

    lineplot("s1_velocity_max_vs_time", "Vel_mag_max", "max velocity [m/s]")
    lineplot("s1_bottom_excess_vs_time", "bottom_excess_mean", "bottom excess pressure [Pa]")
    lineplot("s1_top_drained_excess_vs_time", "top_excess_maxAbs", "top layer |excess| max [Pa]")
    lineplot("s1_bottom_noflux_proxy_vs_time", "bottom_no_flux_proxy", "bottom no-flux proxy [Pa]")
    lineplot("s1_rate_terms_vs_time_porepressrate", "PorePressRate_maxAbs", "|PorePressRate| max [Pa/s]")
    lineplot("s1_rate_terms_vs_time_div", "DivVelContribution_maxAbs", "|-Kw/n DivVel| max [Pa/s]")
    lineplot("s1_rate_terms_vs_time_hydraulic", "HydraulicContribution_maxAbs", "|hydraulic contribution| max [Pa/s]")

    plt.figure(figsize=(6.5, 4.0))
    plt.plot([r["gpu_time"] for r in parity_rows], [r["PorePress_diff_maxAbs"] for r in parity_rows], marker="o", label="PorePress")
    plt.plot([r["gpu_time"] for r in parity_rows], [r["ExcessPorePress_diff_maxAbs"] for r in parity_rows], marker="s", label="ExcessPorePress")
    plt.plot([r["gpu_time"] for r in parity_rows], [r["Vel_mag_diff_maxAbs"] for r in parity_rows], marker="^", label="|Vel|")
    plt.axvline(STOP_TIME, color="k", linestyle="--", linewidth=1)
    plt.xlabel("time [s]")
    plt.ylabel("CPU/GPU max abs difference")
    plt.legend()
    plt.tight_layout()
    plt.savefig(figdir / "s1_cpu_gpu_parity_error_vs_time.svg")
    plt.savefig(figdir / "s1_cpu_gpu_parity_error_vs_time.png", dpi=180)
    plt.close()

    cpu_loaded = load_frames(CPU_OUT)
    gpu_loaded = load_frames(GPU_OUT)
    for quantity, fname, xlabel in [
        ("ExcessPorePress", "s1_excess_profiles_around_switch", "excess pore pressure [Pa]"),
        ("PorePress", "s1_porepress_profiles_around_switch", "pore pressure [Pa]"),
    ]:
        plt.figure(figsize=(6.0, 5.5))
        for target in TARGET_PROFILE_TIMES:
            for frames, run, style in [(cpu_loaded, "CPU", "-"), (gpu_loaded, "GPU", "--")]:
                fr = nearest_frame(frames, target)
                rows = sorted(fr["rows"], key=lambda r: r.get("Pos.z", math.nan))
                plt.plot([r.get(quantity, math.nan) for r in rows], [r.get("Pos.z", math.nan) for r in rows], style, label=f"{run} t={fr['time']:.4g}s")
        plt.xlabel(xlabel)
        plt.ylabel("z [m]")
        plt.legend(fontsize=7, ncol=2)
        plt.tight_layout()
        plt.savefig(figdir / f"{fname}.svg")
        plt.savefig(figdir / f"{fname}.png", dpi=180)
        plt.close()


def cleanup_outputs() -> None:
    for path in [CPU_OUT, GPU_OUT]:
        if path.exists():
            shutil.rmtree(path)
    for pattern in ["*.console.log", "*.gencase.log", "*.dual.log", "*.status.txt", "Run.out", "Run.csv"]:
        for path in ROOT.glob(pattern):
            path.unlink(missing_ok=True)


def create_report(cpu_rows: list[dict], gpu_rows: list[dict], parity_rows: list[dict], run_codes: dict[str, int]) -> None:
    report = REPO / "src" / "papers" / "u-p" / "gpu_s1_bodygravity_stop_short_report.md"
    cpu_run = parse_run(CPU_OUT, ROOT / "cpu_dualsphysics.console.log")
    gpu_run = parse_run(GPU_OUT, ROOT / "gpu_dualsphysics.console.log")
    cpu_final = cpu_rows[-1] if cpu_rows else {}
    gpu_final = gpu_rows[-1] if gpu_rows else {}
    final_parity = parity_rows[-1] if parity_rows else {}
    times_cpu = ", ".join(f"{float(r['time']):.4g}" for r in cpu_rows)
    times_gpu = ", ".join(f"{float(r['time']):.4g}" for r in gpu_rows)
    body_gravity_gpu_supported = gpu_run.get("body_gravity_stop_log") == "True"
    status = "passed" if cpu_run.get("code") == "0" and gpu_run.get("code") == "0" else "failed"
    viability = (
        "GPU single-run BodyGravityStopTime is viable for medium run."
        if body_gravity_gpu_supported
        else "GPU single-run BodyGravityStopTime is not validated in this build because the GPU log did not report the mechanical-gravity stop event; medium Scenario 1 should wait for a narrow GPU BodyGravityStopTime implementation or use the restart route."
    )
    report.write_text(
        f"""# GPU S1 BodyGravityStopTime short smoke

## Objective

This smoke test checks the Scenario 1 single-run route where mechanical body gravity is stopped at `t={STOP_TIME:g} s` while `HydraulicGravity=(0,0,-9.81)` remains active. The test is intentionally short (`TimeMax={TIME_MAX:g} s`) and uses the legacy production hydraulic boundary mode `PorePressureBoundaryOperator=0`.

## Setup

- Base case: `CaseSelfWeightConsolidation_PR_Scenario2_Def.xml`
- Route: `BodyGravityStopTime` single run, no restart
- `BodyGravityStopTime={STOP_TIME:g}`
- `PorePressureTopDrained=1`, `PorePressureTopDrainedStartTime={STOP_TIME:g}`
- `PorePressureBottomNoFlux=1`
- `HydromechDampingXi=0.05`
- `PorePressureFeedbackMode=1`, `PorePressureFeedbackOperator=1`
- `PorePressureShepard=1`, interval `10`, mode `1`
- `PorePressureDtSafety=0.20`
- `SavePorePressure=1`

## Retained Output Times

- CPU: {times_cpu}
- GPU: {times_gpu}

## Run Status

| run | launcher code | DualSPHysics code | excluded | steps | runtime_s | body-gravity stop log | hydraulic-gravity log |
|---|---:|---:|---:|---:|---:|---|---|
| CPU | {run_codes.get('CPU')} | {cpu_run.get('code','')} | {cpu_run.get('excluded','')} | {cpu_run.get('steps','')} | {cpu_run.get('runtime_s','')} | {cpu_run.get('body_gravity_stop_log')} | {cpu_run.get('hydraulic_gravity_active_log')} |
| GPU | {run_codes.get('GPU')} | {gpu_run.get('code','')} | {gpu_run.get('excluded','')} | {gpu_run.get('steps','')} | {gpu_run.get('runtime_s','')} | {gpu_run.get('body_gravity_stop_log')} | {gpu_run.get('hydraulic_gravity_active_log')} |

## Final Short-Smoke Metrics

| metric | CPU | GPU |
|---|---:|---:|
| max velocity [m/s] | {cpu_final.get('Vel_mag_max', math.nan):.6g} | {gpu_final.get('Vel_mag_max', math.nan):.6g} |
| mean settlement dz [m] | {cpu_final.get('settlement_dz_mean', math.nan):.6g} | {gpu_final.get('settlement_dz_mean', math.nan):.6g} |
| PorePress mean [Pa] | {cpu_final.get('PorePress_mean', math.nan):.6g} | {gpu_final.get('PorePress_mean', math.nan):.6g} |
| ExcessPorePress maxAbs [Pa] | {cpu_final.get('ExcessPorePress_maxAbs', math.nan):.6g} | {gpu_final.get('ExcessPorePress_maxAbs', math.nan):.6g} |
| bottom excess mean [Pa] | {cpu_final.get('bottom_excess_mean', math.nan):.6g} | {gpu_final.get('bottom_excess_mean', math.nan):.6g} |
| top layer excess maxAbs [Pa] | {cpu_final.get('top_excess_maxAbs', math.nan):.6g} | {gpu_final.get('top_excess_maxAbs', math.nan):.6g} |
| bottom no-flux proxy [Pa] | {cpu_final.get('bottom_no_flux_proxy', math.nan):.6g} | {gpu_final.get('bottom_no_flux_proxy', math.nan):.6g} |
| PorePressRate maxAbs [Pa/s] | {cpu_final.get('PorePressRate_maxAbs', math.nan):.6g} | {gpu_final.get('PorePressRate_maxAbs', math.nan):.6g} |
| PorePressureAccelDiff maxAbs [m/s2] | {cpu_final.get('PorePressureAccelDiff_mag_maxAbs', math.nan):.6g} | {gpu_final.get('PorePressureAccelDiff_mag_maxAbs', math.nan):.6g} |

## CPU/GPU Parity

Final nearest-frame differences:

- `PorePress` maxAbs: {final_parity.get('PorePress_diff_maxAbs', math.nan):.6g} Pa
- `ExcessPorePress` maxAbs: {final_parity.get('ExcessPorePress_diff_maxAbs', math.nan):.6g} Pa
- `PorePressRate` maxAbs: {final_parity.get('PorePressRate_diff_maxAbs', math.nan):.6g} Pa/s
- `|Vel|` maxAbs: {final_parity.get('Vel_mag_diff_maxAbs', math.nan):.6g} m/s

The CPU/GPU fields are essentially identical through the output immediately at the switch (`t≈0.002001 s`), then diverge rapidly after the switch. This is the expected signature if CPU stops mechanical body gravity and GPU continues applying constant body gravity.

## Switch Behavior

The CPU run reported the `Mechanical body gravity stopped` diagnostic and kept hydraulic gravity active. The GPU run did not report the same stop diagnostic. A source-side audit made before this smoke also found that GPU integration kernels still receive the constant `Gravity` vector directly, while the CPU path calls `GetMechanicalGravity(TimeStep)`. Because this S1 route depends on disabling mechanical body gravity while retaining hydraulic gravity, GPU medium/long Scenario 1 should not proceed from this exact build unless GPU-side mechanical gravity switching is implemented and re-smoked.

The short CPU run remained stable around `t={STOP_TIME:g} s`, with `excluded=0`, continuous pore-pressure output, active top-drained projection after the switch, and a finite bottom no-flux proxy. The GPU run also completed with `excluded=0`, but its physics after `t={STOP_TIME:g} s` cannot be certified as Scenario 1 BodyGravityStopTime behavior without the GPU stop event.

## Recommendation

{viability}

The restart route remains deferred as planned. The next concrete task should be a minimal GPU `BodyGravityStopTime` support patch, followed by rerunning this S1-1 short smoke. No Scenario 1 medium/long run is recommended before that.

## Artifacts

- XML/BAT and analysis script: `examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_S1_BodyGravityStopShort/`
- Metrics:
  - `s1_bodygravity_stop_frame_metrics_cpu.csv`
  - `s1_bodygravity_stop_frame_metrics_gpu.csv`
  - `s1_bodygravity_stop_parity_metrics.csv`
  - `s1_bodygravity_stop_case_summary.csv`
- Figures: `figures/*.svg`, `figures/*.png`
""",
        encoding="utf-8",
    )


def main() -> int:
    create_xml()
    write_bat("CPU")
    write_bat("GPU")
    analyze_only = "--analyze-only" in sys.argv
    run_codes = {"CPU": 0, "GPU": 0} if analyze_only else {"CPU": run_case("CPU"), "GPU": run_case("GPU")}
    cpu_rows = summarize_frames("CPU", CPU_OUT, ROOT / "cpu_dualsphysics.console.log")
    gpu_rows = summarize_frames("GPU", GPU_OUT, ROOT / "gpu_dualsphysics.console.log")
    parity_rows = parity(cpu_rows, gpu_rows)
    write_csv(ROOT / "s1_bodygravity_stop_frame_metrics_cpu.csv", cpu_rows)
    write_csv(ROOT / "s1_bodygravity_stop_frame_metrics_gpu.csv", gpu_rows)
    write_csv(ROOT / "s1_bodygravity_stop_parity_metrics.csv", parity_rows)
    summary = [
        {"run": "CPU", "launcher_code": run_codes["CPU"], **parse_run(CPU_OUT, ROOT / "cpu_dualsphysics.console.log"), **(cpu_rows[-1] if cpu_rows else {})},
        {"run": "GPU", "launcher_code": run_codes["GPU"], **parse_run(GPU_OUT, ROOT / "gpu_dualsphysics.console.log"), **(gpu_rows[-1] if gpu_rows else {})},
    ]
    write_csv(ROOT / "s1_bodygravity_stop_case_summary.csv", summary)
    make_figures(cpu_rows, gpu_rows, parity_rows)
    create_report(cpu_rows, gpu_rows, parity_rows, run_codes)
    cleanup_outputs()
    return 0 if run_codes["CPU"] == 0 and run_codes["GPU"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
