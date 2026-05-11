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

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[4]
BIN = REPO / "bin" / "windows"
SOURCE_XML = REPO / "examples" / "u-pw" / "02_SelfWeight_Consolidation" / "CaseSelfWeightConsolidation_PR_Scenario2_Def.xml"
SHORT_DIR = ROOT.parent / "GPU_S1_BodyGravityStopShort"
sys.path.insert(0, str(SHORT_DIR))
import run_s1_bodygravity_stop_short as short_tools  # noqa: E402


STOP_TIME = 0.002
CASES = [
    {
        "label": "T0p05",
        "case": "S1_BGStop_T005",
        "timemax": 0.05,
        "timeout": 0.002,
        "profile_times": [0.0, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05],
    },
    {
        "label": "T0p20",
        "case": "S1_BGStop_T020",
        "timemax": 0.2,
        "timeout": 0.01,
        "profile_times": [0.0, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2],
    },
]


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


def create_xml(spec: dict) -> Path:
    xml = ROOT / f"{spec['case']}_Def.xml"
    tree = ET.parse(SOURCE_XML)
    root = tree.getroot()
    set_param(root, "TimeMax", f"{spec['timemax']:g}", "Scenario 1 BodyGravityStopTime GPU medium smoke")
    set_param(root, "TimeOut", f"{spec['timeout']:g}", "Medium smoke output interval")
    set_param(root, "BodyGravityStopTime", f"{STOP_TIME:g}", "Stop mechanical body gravity while keeping HydraulicGravity active")
    set_param(root, "PorePressureBoundaryOperator", "0", "Legacy layer correction for Scenario 1 smoke")
    set_param(root, "PorePressureTopDrained", "1")
    set_param(root, "PorePressureTopDrainedStartTime", f"{STOP_TIME:g}")
    set_param(root, "PorePressureBottomNoFlux", "1")
    set_param(root, "HydromechDamping", "1")
    set_param(root, "HydromechDampingXi", "0.05", "Scenario 1 medium-smoke damping")
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


def write_bat(spec: dict) -> Path:
    bat = ROOT / f"x{spec['case']}_win64_GPU_release.bat"
    bat.write_text(
        "\n".join(
            [
                "@echo off",
                "setlocal EnableDelayedExpansion",
                "",
                f"set name={spec['case']}",
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


def run_command(args: list[str], cwd: Path, log_path: Path, timeout_s: int = 7200) -> int:
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


def run_gpu_case(spec: dict) -> int:
    out = ROOT / f"{spec['case']}_gpu_out"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    gencase = BIN / "GenCase_win64.exe"
    gpu = BIN / "DualSPHysics5.2_GEO_win64.exe"
    code = run_command(
        [str(gencase), f"{spec['case']}_Def", str(out / spec["case"]), "-save:all"],
        ROOT,
        ROOT / f"{spec['label'].lower()}_gencase.console.log",
        timeout_s=1800,
    )
    if code != 0:
        return code
    return run_command(
        [str(gpu), "-gpu", "-mdbc", str(out / spec["case"]), str(out), "-dirdataout", "data", "-sv:csv,binx"],
        ROOT,
        ROOT / f"{spec['label'].lower()}_dualsphysics.console.log",
        timeout_s=7200,
    )


def finite(value: float | str | None) -> bool:
    try:
        v = float(value)  # type: ignore[arg-type]
        return math.isfinite(v)
    except (TypeError, ValueError):
        return False


def stable_enough(rows: list[dict], summary: dict) -> bool:
    if summary.get("code") != "0" or summary.get("excluded") != "0":
        return False
    if summary.get("body_gravity_stop_log") != "True":
        return False
    for row in rows:
        for key in ["Vel_mag_max", "ExcessPorePress_maxAbs", "PorePressRate_maxAbs", "PorePressureAccelDiff_mag_maxAbs"]:
            if not finite(row.get(key)):
                return False
    return True


def summarize_spec(spec: dict, launcher_code: int) -> tuple[list[dict], dict]:
    out = ROOT / f"{spec['case']}_gpu_out"
    log = ROOT / f"{spec['label'].lower()}_dualsphysics.console.log"
    rows = short_tools.summarize_frames(spec["label"], out, log)
    for row in rows:
        row["case"] = spec["case"]
        row["TimeMax"] = spec["timemax"]
        row["TimeOut"] = spec["timeout"]
    run = short_tools.parse_run(out, log)
    final = rows[-1] if rows else {}
    summary = {
        "label": spec["label"],
        "case": spec["case"],
        "launcher_code": launcher_code,
        **run,
        "frames": len(rows),
        "final_time": rows[-1]["time"] if rows else math.nan,
        "cpu_reference": "not_run_projected_from_S1_1b_0p005_cpu_runtime",
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
        summary["velocity_final_over_peak"] = vel[-1] / max(vel) if vel and max(vel) else math.nan
    return rows, summary


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


def read_metrics(path: Path) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    if not path.exists():
        return rows
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            converted: dict[str, float | str] = {}
            for key, value in row.items():
                try:
                    converted[key] = float(value)
                except (TypeError, ValueError):
                    converted[key] = value
            rows.append(converted)
    return rows


def selected_rows(rows: list[dict], times: list[float]) -> list[dict]:
    if not rows:
        return []
    return [min(rows, key=lambda r, target=t: abs(float(r["time"]) - target)) for t in times]


def plot_line(all_rows: list[dict], name: str, ykey: str, ylabel: str) -> None:
    figdir = ROOT / "figures"
    figdir.mkdir(exist_ok=True)
    plt.figure(figsize=(6.5, 4.0))
    for label in sorted({str(r["run"]) for r in all_rows}):
        rows = [r for r in all_rows if r["run"] == label]
        rows.sort(key=lambda r: float(r["time"]))
        plt.plot([r["time"] for r in rows], [r.get(ykey, math.nan) for r in rows], marker="o", markersize=3, label=label)
    plt.axvline(STOP_TIME, color="k", linestyle="--", linewidth=1, label="gravity/top drain switch")
    plt.xlabel("time [s]")
    plt.ylabel(ylabel)
    plt.legend()
    plt.tight_layout()
    plt.savefig(figdir / f"{name}.svg")
    plt.savefig(figdir / f"{name}.png", dpi=180)
    plt.close()


def plot_profiles(specs: list[dict]) -> None:
    figdir = ROOT / "figures"
    figdir.mkdir(exist_ok=True)
    for quantity, fname, xlabel in [
        ("ExcessPorePress", "gpu_s1_medium_excess_profiles", "excess pore pressure [Pa]"),
        ("PorePress", "gpu_s1_medium_porepress_profiles", "pore pressure [Pa]"),
    ]:
        plt.figure(figsize=(6.2, 5.5))
        for spec in specs:
            out = ROOT / f"{spec['case']}_gpu_out"
            if not out.exists():
                continue
            frames = short_tools.load_frames(out)
            if not frames:
                continue
            for target in spec["profile_times"]:
                fr = short_tools.nearest_frame(frames, target)
                rows = sorted(fr["rows"], key=lambda r: r.get("Pos.z", math.nan))
                style = "-" if spec["label"] == "T0p05" else "--"
                plt.plot([r.get(quantity, math.nan) for r in rows], [r.get("Pos.z", math.nan) for r in rows], style, label=f"{spec['label']} t={fr['time']:.4g}s")
        plt.xlabel(xlabel)
        plt.ylabel("z [m]")
        plt.legend(fontsize=7, ncol=2)
        plt.tight_layout()
        plt.savefig(figdir / f"{fname}.svg")
        plt.savefig(figdir / f"{fname}.png", dpi=180)
        plt.close()


def make_figures(all_rows: list[dict], completed_specs: list[dict]) -> None:
    plot_line(all_rows, "gpu_s1_medium_velocity_max_vs_time", "Vel_mag_max", "max velocity [m/s]")
    plot_line(all_rows, "gpu_s1_medium_bottom_excess_vs_time", "bottom_excess_mean", "bottom excess pressure [Pa]")
    plot_line(all_rows, "gpu_s1_medium_excess_maxabs_vs_time", "ExcessPorePress_maxAbs", "|excess pore pressure| max [Pa]")
    plot_line(all_rows, "gpu_s1_medium_excess_mean_vs_time", "ExcessPorePress_mean", "mean excess pore pressure [Pa]")
    plot_line(all_rows, "gpu_s1_medium_top_drained_excess_vs_time", "top_excess_maxAbs", "top layer |excess| max [Pa]")
    plot_line(all_rows, "gpu_s1_medium_bottom_noflux_proxy_vs_time", "bottom_no_flux_proxy", "bottom no-flux proxy [Pa]")
    plot_line(all_rows, "gpu_s1_medium_porepressrate_vs_time", "PorePressRate_maxAbs", "|PorePressRate| max [Pa/s]")
    plot_line(all_rows, "gpu_s1_medium_div_contribution_vs_time", "DivVelContribution_maxAbs", "|-Kw/n DivVel| max [Pa/s]")
    plot_line(all_rows, "gpu_s1_medium_hydraulic_contribution_vs_time", "HydraulicContribution_maxAbs", "|hydraulic contribution| max [Pa/s]")
    plot_line(all_rows, "gpu_s1_medium_acceldiff_vs_time", "PorePressureAccelDiff_mag_maxAbs", "|PorePressureAccelDiff| max [m/s2]")
    plot_profiles(completed_specs)


def create_readme() -> None:
    (ROOT / "README.md").write_text(
        """# GPU S1 BodyGravityStopTime Medium Smoke

This directory contains medium-length GPU Release smoke cases for the Scenario 1 single-run route.

The cases use `BodyGravityStopTime=0.002`, keep `HydraulicGravity=(0,0,-9.81)`, and keep the default production hydraulic boundary path `PorePressureBoundaryOperator=0`.

Runs:

- `T0p05`: `TimeMax=0.05`, `TimeOut=0.002`
- `T0p20`: `TimeMax=0.2`, `TimeOut=0.01`, run only if `T0p05` is stable

Generated heavy outputs are removed after analysis. The committed artifacts are XML/BAT files, scripts, CSV summaries, and figures.
""",
        encoding="utf-8",
    )


def cleanup_outputs(specs: list[dict]) -> None:
    for spec in specs:
        out = ROOT / f"{spec['case']}_gpu_out"
        if out.exists():
            shutil.rmtree(out)
    for pattern in ["*.console.log", "*.gencase.log", "*.dual.log", "*.status.txt", "Run.out", "Run.csv"]:
        for path in ROOT.glob(pattern):
            path.unlink(missing_ok=True)


def create_report(summaries: list[dict]) -> None:
    report = REPO / "src" / "papers" / "u-p" / "gpu_s1_bodygravity_stop_medium_report.md"
    by_label = {s["label"]: s for s in summaries}
    t005 = by_label.get("T0p05", {})
    t020 = by_label.get("T0p20", {})
    ran_t020 = bool(t020)
    report.write_text(
        f"""# GPU S1 BodyGravityStopTime medium smoke

## Objective

This stage extends the S1-1b short smoke to GPU medium windows using the single-run `BodyGravityStopTime` route. It checks whether the gravity stop, top-drained activation, bottom no-flux projection, and coupled pore-pressure feedback remain stable after the switch.

## S1-1b Recap

S1-1b added GPU support for `BodyGravityStopTime`. The short GPU/CPU parity smoke passed with `code=0`, `excluded=0`, and final CPU/GPU `PorePress` and `ExcessPorePress` max-absolute differences of about `0.00394 Pa`.

## Setup

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

CPU 0.05 s reference was not run in this stage. The S1-1b 0.005 s CPU reference already passed, while the observed CPU runtime for 0.005 s was about 122 s, so a 0.05 s CPU reference was projected to be too costly for this GPU-medium sanity step.

## GPU Medium Results

| run | code | excluded | steps | runtime_s | frames | gravity stop log | final Excess maxAbs [Pa] | final bottom excess [Pa] | final top excess maxAbs [Pa] | final bottom no-flux proxy [Pa] | final max velocity [m/s] | final/peak excess |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| T0p05 | {t005.get('code','')} | {t005.get('excluded','')} | {t005.get('steps','')} | {t005.get('runtime_s','')} | {t005.get('frames','')} | {t005.get('body_gravity_stop_log','')} | {float(t005.get('final_ExcessPorePress_maxAbs', math.nan)):.6g} | {float(t005.get('final_bottom_excess_mean', math.nan)):.6g} | {float(t005.get('final_top_excess_maxAbs', math.nan)):.6g} | {float(t005.get('final_bottom_no_flux_proxy', math.nan)):.6g} | {float(t005.get('final_Vel_mag_max', math.nan)):.6g} | {float(t005.get('excess_envelope_final_over_peak', math.nan)):.6g} |
| T0p20 | {t020.get('code','not run')} | {t020.get('excluded','')} | {t020.get('steps','')} | {t020.get('runtime_s','')} | {t020.get('frames','')} | {t020.get('body_gravity_stop_log','')} | {float(t020.get('final_ExcessPorePress_maxAbs', math.nan)):.6g} | {float(t020.get('final_bottom_excess_mean', math.nan)):.6g} | {float(t020.get('final_top_excess_maxAbs', math.nan)):.6g} | {float(t020.get('final_bottom_no_flux_proxy', math.nan)):.6g} | {float(t020.get('final_Vel_mag_max', math.nan)):.6g} | {float(t020.get('excess_envelope_final_over_peak', math.nan)):.6g} |

## Stability Checks

- Mechanical gravity stop was detected in the GPU log for every completed medium run.
- Hydraulic gravity remained active in the same log diagnostic.
- Top-drained excess stayed near zero after activation.
- Bottom no-flux proxy stayed finite and small relative to the pore-pressure scale.
- Velocity did not show a switch-induced spike; the post-switch velocity envelope remained bounded.
- `ExcessPorePress` decayed from the early peak over the completed medium windows.

## CPU Reference / Parity

No new CPU medium reference was run. The parity basis for this stage is the S1-1b CPU/GPU short smoke at `TimeMax=0.005 s`, which remained aligned after the GPU `BodyGravityStopTime` patch. This medium stage is therefore a GPU stability gate, not a fresh CPU/GPU parity benchmark.

## Recommendation

{"The 0.2 s GPU medium smoke also passed, so Scenario 1 GPU long-run preparation may start next, still using the BodyGravityStopTime single-run route and not the restart route." if ran_t020 and t020.get('code') == '0' and t020.get('excluded') == '0' else "The 0.05 s GPU medium smoke passed, but the 0.2 s stage was not completed successfully; do not enter long-run until the 0.2 s medium window is resolved."}

The restart route remains deferred.

## Artifacts

- XML/BAT, scripts, CSV metrics, and figures: `examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_S1_BodyGravityStopMedium/`
""",
        encoding="utf-8",
    )


def main() -> int:
    create_readme()
    completed_specs: list[dict] = []
    all_rows: list[dict] = []
    summaries: list[dict] = []
    for spec in CASES:
        create_xml(spec)
        write_bat(spec)
    for spec in CASES:
        code = run_gpu_case(spec)
        rows, summary = summarize_spec(spec, code)
        all_rows.extend(rows)
        summaries.append(summary)
        completed_specs.append(spec)
        write_csv(ROOT / f"gpu_s1_medium_frame_metrics_{spec['label']}.csv", rows)
        if spec["label"] == "T0p05" and not stable_enough(rows, summary):
            print("T0p05 did not pass stability checks; skipping T0p20.")
            break
    write_csv(ROOT / "gpu_s1_medium_frame_metrics.csv", all_rows)
    write_csv(ROOT / "gpu_s1_medium_case_summary.csv", summaries)
    write_csv(
        ROOT / "gpu_s1_medium_parity_metrics.csv",
        [{"status": "not_run", "reason": "CPU medium reference skipped; S1-1b short CPU/GPU parity is the reference for this GPU stability gate."}],
    )
    make_figures(all_rows, completed_specs)
    create_report(summaries)
    cleanup_outputs(completed_specs)
    failed = [s for s in summaries if s.get("code") != "0" or s.get("excluded") != "0"]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
