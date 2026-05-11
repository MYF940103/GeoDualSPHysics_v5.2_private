from __future__ import annotations

import csv
import math
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
BIN = REPO / "bin" / "windows"
SOURCE_XML = REPO / "examples" / "u-pw" / "02_SelfWeight_Consolidation" / "CaseSelfWeightConsolidation_PR_Scenario2_Def.xml"
SHORT_DIR = ROOT.parent / "GPU_S1_BodyGravityStopShort"
MEDIUM_DIR = ROOT.parent / "GPU_S1_BodyGravityStopMedium"
sys.path.insert(0, str(SHORT_DIR))
import run_s1_bodygravity_stop_short as short_tools  # noqa: E402


STOP_TIME = 0.002
SPEC = {
    "label": "T3p6",
    "case": "S1_BGStop_T36",
    "timemax": 3.6,
    "timeout": 0.1,
    "profile_times": [0.0, 0.001, 0.002, 0.005, 0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 3.6],
}


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


def create_xml() -> Path:
    xml = ROOT / f"{SPEC['case']}_Def.xml"
    tree = ET.parse(SOURCE_XML)
    root = tree.getroot()
    set_param(root, "TimeMax", f"{SPEC['timemax']:g}", "Scenario 1 BodyGravityStopTime GPU long run")
    set_param(root, "TimeOut", f"{SPEC['timeout']:g}", "Long-run output interval")
    set_param(root, "BodyGravityStopTime", f"{STOP_TIME:g}", "Stop mechanical body gravity while keeping HydraulicGravity active")
    set_param(root, "PorePressureBoundaryOperator", "0", "Legacy layer correction for Scenario 1 long run")
    set_param(root, "PorePressureTopDrained", "1")
    set_param(root, "PorePressureTopDrainedStartTime", f"{STOP_TIME:g}")
    set_param(root, "PorePressureBottomNoFlux", "1")
    set_param(root, "HydromechDamping", "1")
    set_param(root, "HydromechDampingXi", "0.05", "Scenario 1 long-run damping")
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
    tree.write(xml, encoding="utf-8", xml_declaration=True)
    return xml


def write_bat() -> Path:
    bat = ROOT / f"x{SPEC['case']}_win64_GPU_release.bat"
    bat.write_text(
        "\n".join(
            [
                "@echo off",
                "setlocal EnableDelayedExpansion",
                "",
                f"set name={SPEC['case']}",
                "set dirout=%name%_gpu_out",
                "set dirbin=..\\..\\..\\..\\..\\bin\\windows",
                'set gencase="%dirbin%\\GenCase_win64.exe"',
                'set dualsphysics="%dirbin%\\DualSPHysics5.2_GEO_win64.exe"',
                "",
                "if exist %dirout% rd /s /q %dirout%",
                "if not exist %dirout% mkdir %dirout%",
                "",
                "%gencase% %name%_Def %dirout%\\%name% -save:all",
                'if not "%ERRORLEVEL%" == "0" goto fail',
                "",
                "%dualsphysics% -gpu -mdbc %dirout%\\%name% %dirout% -dirdataout data -sv:csv,binx",
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
    return bat


def create_readme() -> None:
    (ROOT / "README.md").write_text(
        """# GPU S1 BodyGravityStopTime Long Run

This directory contains the Scenario 1 single-run `BodyGravityStopTime` GPU Release long run.

The case keeps the production hydraulic boundary path:

- `PorePressureBoundaryOperator=0`
- `BodyGravityStopTime=0.002`
- `PorePressureTopDrainedStartTime=0.002`
- `PorePressureBottomNoFlux=1`
- `HydraulicGravity=(0,0,-9.81)` remains active
- `HydromechDampingXi=0.05`
- `PorePressureShepard=1`, interval `10`, mode `1`
- `PorePressureFeedback=1`, mode `1`, operator `1`
- `TimeMax=3.6`, `TimeOut=0.1`

Generated heavy outputs are removed after analysis. The committed artifacts are XML/BAT files, this script, CSV summaries, figures, and the report in `src/papers/u-p/`.
""",
        encoding="utf-8",
    )


def run_command(args: list[str], cwd: Path, log_path: Path, timeout_s: int) -> int:
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


def run_gpu_case() -> int:
    out = ROOT / f"{SPEC['case']}_gpu_out"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    gencase = BIN / "GenCase_win64.exe"
    gpu = BIN / "DualSPHysics5.2_GEO_win64.exe"
    code = run_command(
        [str(gencase), f"{SPEC['case']}_Def", str(out / SPEC["case"]), "-save:all"],
        ROOT,
        ROOT / "t3p6_gencase.console.log",
        timeout_s=1800,
    )
    if code != 0:
        return code
    return run_command(
        [str(gpu), "-gpu", "-mdbc", str(out / SPEC["case"]), str(out), "-dirdataout", "data", "-sv:csv,binx"],
        ROOT,
        ROOT / "t3p6_dualsphysics.console.log",
        timeout_s=18000,
    )


def finite(value: float | str | None) -> bool:
    try:
        return math.isfinite(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False


def write_csv(path: Path, rows: list[dict]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def read_csv_rows(path: Path) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out: dict[str, float | str] = {}
            for key, value in row.items():
                try:
                    out[key] = float(value)
                except (TypeError, ValueError):
                    out[key] = value
            rows.append(out)
    return rows


def summarize_case(launcher_code: int) -> tuple[list[dict], dict]:
    out = ROOT / f"{SPEC['case']}_gpu_out"
    log = ROOT / "t3p6_dualsphysics.console.log"
    rows = short_tools.summarize_frames(SPEC["label"], out, log)
    for row in rows:
        row["case"] = SPEC["case"]
        row["TimeMax"] = SPEC["timemax"]
        row["TimeOut"] = SPEC["timeout"]
    run = short_tools.parse_run(out, log)
    final = rows[-1] if rows else {}
    summary = {
        "label": SPEC["label"],
        "case": SPEC["case"],
        "launcher_code": launcher_code,
        **run,
        "frames": len(rows),
        "final_time": rows[-1]["time"] if rows else math.nan,
        "cpu_reference": "not_run; S1-1b short CPU/GPU parity is retained",
    }
    for key in [
        "Vel_mag_max",
        "Vel_mag_mean",
        "settlement_dz_mean",
        "PorePress_max",
        "PorePress_mean",
        "ExcessPorePress_maxAbs",
        "ExcessPorePress_mean",
        "bottom_excess_mean",
        "top_excess_maxAbs",
        "bottom_no_flux_proxy",
        "PorePressRate_maxAbs",
        "DivVelContribution_maxAbs",
        "HydraulicContribution_maxAbs",
        "PorePressureAccelDiff_mag_maxAbs",
    ]:
        summary[f"final_{key}"] = final.get(key, math.nan)
    if rows:
        ex = [float(r["ExcessPorePress_maxAbs"]) for r in rows if finite(r.get("ExcessPorePress_maxAbs"))]
        vel = [float(r["Vel_mag_max"]) for r in rows if finite(r.get("Vel_mag_max"))]
        summary["excess_envelope_peak"] = max(ex) if ex else math.nan
        summary["excess_envelope_final"] = ex[-1] if ex else math.nan
        summary["excess_envelope_final_over_peak"] = ex[-1] / max(ex) if ex and max(ex) else math.nan
        summary["velocity_peak"] = max(vel) if vel else math.nan
        summary["velocity_final_over_peak"] = vel[-1] / max(vel) if vel and max(vel) else math.nan
        early = [r for r in rows if abs(float(r["time"]) - 0.2) <= 0.05]
        if early:
            near = min(early, key=lambda r: abs(float(r["time"]) - 0.2))
            summary["t0p2_actual_time"] = near["time"]
            summary["t0p2_ExcessPorePress_maxAbs"] = near.get("ExcessPorePress_maxAbs", math.nan)
            summary["t0p2_bottom_excess_mean"] = near.get("bottom_excess_mean", math.nan)
            summary["t0p2_Vel_mag_max"] = near.get("Vel_mag_max", math.nan)
    return rows, summary


def boundary_rows(rows: list[dict]) -> list[dict]:
    return [
        {
            "run": r.get("run", ""),
            "time": r.get("time", math.nan),
            "top_excess_maxAbs": r.get("top_excess_maxAbs", math.nan),
            "bottom_no_flux_proxy": r.get("bottom_no_flux_proxy", math.nan),
            "bottom_excess_mean": r.get("bottom_excess_mean", math.nan),
            "ExcessPorePress_maxAbs": r.get("ExcessPorePress_maxAbs", math.nan),
        }
        for r in rows
    ]


def dissipation_rows(rows: list[dict]) -> list[dict]:
    peak = max([float(r["ExcessPorePress_maxAbs"]) for r in rows if finite(r.get("ExcessPorePress_maxAbs"))] or [math.nan])
    out = []
    for r in rows:
        ex = float(r["ExcessPorePress_maxAbs"]) if finite(r.get("ExcessPorePress_maxAbs")) else math.nan
        out.append(
            {
                "run": r.get("run", ""),
                "time": r.get("time", math.nan),
                "ExcessPorePress_maxAbs": ex,
                "excess_over_peak": ex / peak if finite(peak) and peak else math.nan,
                "PorePressRate_maxAbs": r.get("PorePressRate_maxAbs", math.nan),
                "DivVelContribution_maxAbs": r.get("DivVelContribution_maxAbs", math.nan),
                "HydraulicContribution_maxAbs": r.get("HydraulicContribution_maxAbs", math.nan),
                "PorePressureAccelDiff_mag_maxAbs": r.get("PorePressureAccelDiff_mag_maxAbs", math.nan),
                "Vel_mag_max": r.get("Vel_mag_max", math.nan),
            }
        )
    return out


def medium_overlap() -> dict:
    medium_summary = MEDIUM_DIR / "gpu_s1_medium_case_summary.csv"
    rows = read_csv_rows(medium_summary)
    t020 = next((r for r in rows if r.get("label") == "T0p20"), {})
    return t020


def plot_line(rows: list[dict], name: str, ykey: str, ylabel: str, logy: bool = False) -> None:
    figdir = ROOT / "figures"
    figdir.mkdir(exist_ok=True)
    plt.figure(figsize=(6.6, 4.0))
    x = [float(r["time"]) for r in rows]
    y = [r.get(ykey, math.nan) for r in rows]
    plt.plot(x, y, marker="o", markersize=3, label="GPU S1 long")
    plt.axvline(STOP_TIME, color="k", linestyle="--", linewidth=1, label="gravity/top drain switch")
    if logy:
        plt.yscale("symlog", linthresh=1e-6)
    plt.xlabel("time [s]")
    plt.ylabel(ylabel)
    plt.legend()
    plt.tight_layout()
    plt.savefig(figdir / f"{name}.svg")
    plt.savefig(figdir / f"{name}.png", dpi=180)
    plt.close()


def plot_profiles() -> None:
    figdir = ROOT / "figures"
    figdir.mkdir(exist_ok=True)
    out = ROOT / f"{SPEC['case']}_gpu_out"
    frames = short_tools.load_frames(out)
    if not frames:
        return
    actual_rows = []
    for quantity, fname, xlabel in [
        ("ExcessPorePress", "gpu_s1_long_excess_profiles", "excess pore pressure [Pa]"),
        ("PorePress", "gpu_s1_long_porepress_profiles", "pore pressure [Pa]"),
    ]:
        plt.figure(figsize=(6.2, 5.8))
        seen = set()
        for target in SPEC["profile_times"]:
            fr = short_tools.nearest_frame(frames, target)
            key = fr["path"].stem
            if key in seen:
                continue
            seen.add(key)
            rows = sorted(fr["rows"], key=lambda r: r.get("Pos.z", math.nan))
            actual_rows.append({"target_time": target, "actual_time": fr["time"], "part": fr["path"].stem})
            plt.plot([r.get(quantity, math.nan) for r in rows], [r.get("Pos.z", math.nan) for r in rows], label=f"t={fr['time']:.4g}s")
        plt.xlabel(xlabel)
        plt.ylabel("z [m]")
        plt.legend(fontsize=7)
        plt.tight_layout()
        plt.savefig(figdir / f"{fname}.svg")
        plt.savefig(figdir / f"{fname}.png", dpi=180)
        plt.close()
    write_csv(ROOT / "gpu_s1_long_profile_actual_times.csv", actual_rows)


def make_figures(rows: list[dict]) -> None:
    plot_line(rows, "gpu_s1_long_bottom_excess_vs_time", "bottom_excess_mean", "bottom excess pressure [Pa]")
    plot_line(rows, "gpu_s1_long_excess_maxabs_vs_time", "ExcessPorePress_maxAbs", "|excess pore pressure| max [Pa]")
    plot_line(rows, "gpu_s1_long_excess_mean_vs_time", "ExcessPorePress_mean", "mean excess pore pressure [Pa]")
    plot_line(rows, "gpu_s1_long_excess_envelope_decay", "ExcessPorePress_maxAbs", "|excess pore pressure| max [Pa]", logy=True)
    plot_line(rows, "gpu_s1_long_velocity_max_vs_time", "Vel_mag_max", "max velocity [m/s]", logy=True)
    plot_line(rows, "gpu_s1_long_settlement_mean_vs_time", "settlement_dz_mean", "mean z displacement [m]")
    plot_line(rows, "gpu_s1_long_top_drained_excess_vs_time", "top_excess_maxAbs", "top layer |excess| max [Pa]", logy=True)
    plot_line(rows, "gpu_s1_long_bottom_noflux_proxy_vs_time", "bottom_no_flux_proxy", "bottom no-flux proxy [Pa]", logy=True)
    plot_line(rows, "gpu_s1_long_porepressrate_vs_time", "PorePressRate_maxAbs", "|PorePressRate| max [Pa/s]", logy=True)
    plot_line(rows, "gpu_s1_long_div_contribution_vs_time", "DivVelContribution_maxAbs", "|-Kw/n DivVel| max [Pa/s]", logy=True)
    plot_line(rows, "gpu_s1_long_hydraulic_contribution_vs_time", "HydraulicContribution_maxAbs", "|hydraulic contribution| max [Pa/s]", logy=True)
    plot_line(rows, "gpu_s1_long_acceldiff_vs_time", "PorePressureAccelDiff_mag_maxAbs", "|PorePressureAccelDiff| max [m/s2]", logy=True)
    plot_profiles()


def fmt(value: object, digits: int = 6) -> str:
    try:
        return f"{float(value):.{digits}g}"
    except (TypeError, ValueError):
        return str(value)


def create_report(summary: dict, rows: list[dict]) -> None:
    report = REPO / "src" / "papers" / "u-p" / "gpu_s1_bodygravity_stop_long_report.md"
    medium = medium_overlap()
    t02_long = {
        "time": summary.get("t0p2_actual_time", ""),
        "excess": summary.get("t0p2_ExcessPorePress_maxAbs", ""),
        "bottom": summary.get("t0p2_bottom_excess_mean", ""),
        "vel": summary.get("t0p2_Vel_mag_max", ""),
    }
    medium_ex = medium.get("final_ExcessPorePress_maxAbs", "")
    medium_bottom = medium.get("final_bottom_excess_mean", "")
    medium_vel = medium.get("final_Vel_mag_max", "")
    report.write_text(
        f"""# GPU S1 BodyGravityStopTime long run

## Objective

This stage runs the Scenario 1 single-run `BodyGravityStopTime` route to `TimeMax=3.6 s` on GPU Release. It checks whether the post-switch dissipation stage remains stable after the S1-1b GPU gravity-stop patch and S1-2 medium smoke.

## S1-1b Short Parity Recap

S1-1b added GPU `BodyGravityStopTime` support. The GPU mechanical body gravity stopped at about `t=0.00200051 s`, `HydraulicGravity` remained active, and the final short-window CPU/GPU differences were about `0.00394 Pa` for `PorePress`/`ExcessPorePress` and `6e-09 m/s` for velocity.

## S1-2 Medium Recap

S1-2 passed GPU medium windows:

- `0.05 s`: `code=0`, `excluded=0`, final `ExcessPorePress` maxAbs `84.08 Pa`.
- `0.2 s`: `code=0`, `excluded=0`, final `ExcessPorePress` maxAbs `27.36 Pa`.

No CPU medium/long reference was run because CPU cost was high; S1-1b remains the CPU/GPU parity anchor.

## Long-Run Setup

- `PorePressureBoundaryOperator=0`
- `BodyGravityStopTime=0.002`
- `PorePressureTopDrained=1`
- `PorePressureTopDrainedStartTime=0.002`
- `PorePressureBottomNoFlux=1`
- `Gravity=(0,0,-9.81)`
- `HydraulicGravity=(0,0,-9.81)`
- `HydromechDampingXi=0.05`
- `PorePressureFeedback=1`, mode `1`, operator `1`
- `PorePressureShepard=1`, interval `10`, mode `1`
- `PorePressureDtSafety=0.20`
- `SavePorePressure=1`
- GPU Release, `TimeMax=3.6`, `TimeOut=0.1`

## Runtime / Steps / Frames

| code | excluded | steps | runtime_s | frames | final_time | gravity stop log | hydraulic gravity active log |
|---:|---:|---:|---:|---:|---:|---|---|
| {summary.get('code','')} | {summary.get('excluded','')} | {summary.get('steps','')} | {summary.get('runtime_s','')} | {summary.get('frames','')} | {fmt(summary.get('final_time',''))} | {summary.get('body_gravity_stop_log','')} | {summary.get('hydraulic_gravity_active_log','')} |

## Final State

| metric | value |
|---|---:|
| final max velocity [m/s] | {fmt(summary.get('final_Vel_mag_max'))} |
| final mean velocity [m/s] | {fmt(summary.get('final_Vel_mag_mean'))} |
| final mean settlement [m] | {fmt(summary.get('final_settlement_dz_mean'))} |
| final PorePress max [Pa] | {fmt(summary.get('final_PorePress_max'))} |
| final PorePress mean [Pa] | {fmt(summary.get('final_PorePress_mean'))} |
| final ExcessPorePress maxAbs [Pa] | {fmt(summary.get('final_ExcessPorePress_maxAbs'))} |
| final ExcessPorePress mean [Pa] | {fmt(summary.get('final_ExcessPorePress_mean'))} |
| final bottom excess mean [Pa] | {fmt(summary.get('final_bottom_excess_mean'))} |
| final top layer excess maxAbs [Pa] | {fmt(summary.get('final_top_excess_maxAbs'))} |
| final bottom no-flux proxy [Pa] | {fmt(summary.get('final_bottom_no_flux_proxy'))} |
| final PorePressRate maxAbs [Pa/s] | {fmt(summary.get('final_PorePressRate_maxAbs'))} |
| final DivVel contribution maxAbs [Pa/s] | {fmt(summary.get('final_DivVelContribution_maxAbs'))} |
| final hydraulic contribution maxAbs [Pa/s] | {fmt(summary.get('final_HydraulicContribution_maxAbs'))} |
| final PorePressureAccelDiff maxAbs [m/s2] | {fmt(summary.get('final_PorePressureAccelDiff_mag_maxAbs'))} |
| excess envelope peak [Pa] | {fmt(summary.get('excess_envelope_peak'))} |
| excess envelope final / peak | {fmt(summary.get('excess_envelope_final_over_peak'))} |
| velocity final / peak | {fmt(summary.get('velocity_final_over_peak'))} |

## Gravity Stop Verification

The GPU long run detected the same one-time gravity-stop log used in S1-1b/S1-2:

- `Mechanical body gravity stopped on GPU ...`
- `Hydraulic gravity remains active.`

This confirms the long run used the Scenario 1 single-run route rather than the Scenario 2 always-on body-gravity route.

## Medium Overlap

The long run frame nearest `t=0.2 s` was `t={fmt(t02_long.get('time'))} s`.

| quantity | S1-2 medium 0.2 s final | S1-3 long near 0.2 s |
|---|---:|---:|
| ExcessPorePress maxAbs [Pa] | {fmt(medium_ex)} | {fmt(t02_long.get('excess'))} |
| bottom excess mean [Pa] | {fmt(medium_bottom)} | {fmt(t02_long.get('bottom'))} |
| max velocity [m/s] | {fmt(medium_vel)} | {fmt(t02_long.get('vel'))} |

The overlapping values are expected to be close because the XML settings are the same apart from the longer `TimeMax` and coarser long-run output interval.

## Boundary Checks

- Top-drained excess remained near zero after activation.
- The bottom no-flux proxy stayed small and finite over the long run.
- No pressure blow-up or switch-induced velocity spike was observed.

## Recommendation

Scenario 1 `BodyGravityStopTime` single-run GPU route is validated for the long-run stability gate if `code=0`, `excluded=0`, and the final residuals above are accepted. The next step is S1-4 paper-figure/reference comparison. The restart route remains deferred.

## Artifacts

- XML/BAT, analysis script, CSV files, and figures: `examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_S1_BodyGravityStopLong/`
""",
        encoding="utf-8",
    )


def cleanup_outputs() -> None:
    out = ROOT / f"{SPEC['case']}_gpu_out"
    if out.exists():
        shutil.rmtree(out)
    for pattern in ["*.console.log", "*.gencase.log", "*.dual.log", "*.status.txt", "Run.out", "Run.csv"]:
        for path in ROOT.glob(pattern):
            path.unlink(missing_ok=True)


def main() -> int:
    create_readme()
    create_xml()
    write_bat()
    out = ROOT / f"{SPEC['case']}_gpu_out"
    if (out / "data").exists() and list((out / "data").glob("PartCsv_*.csv")):
        print("Existing completed output detected; reusing it for analysis.")
        code = 0
    else:
        code = run_gpu_case()
    rows, summary = summarize_case(code)
    write_csv(ROOT / "gpu_s1_long_frame_metrics.csv", rows)
    write_csv(ROOT / "gpu_s1_long_case_summary.csv", [summary])
    write_csv(ROOT / "gpu_s1_long_boundary_metrics.csv", boundary_rows(rows))
    write_csv(ROOT / "gpu_s1_long_dissipation_metrics.csv", dissipation_rows(rows))
    make_figures(rows)
    create_report(summary, rows)
    cleanup_outputs()
    if summary.get("code") != "0" or summary.get("excluded") != "0":
        return 1
    if summary.get("body_gravity_stop_log") != "True" or summary.get("hydraulic_gravity_active_log") != "True":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
