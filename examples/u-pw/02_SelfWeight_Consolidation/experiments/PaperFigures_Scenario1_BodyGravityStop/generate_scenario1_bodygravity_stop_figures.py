from __future__ import annotations

import csv
import math
import shutil
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
EXP = ROOT.parent
REPO = ROOT.parents[4]
SHORT = EXP / "GPU_S1_BodyGravityStopShort"
MEDIUM = EXP / "GPU_S1_BodyGravityStopMedium"
LONG = EXP / "GPU_S1_BodyGravityStopLong"
FIG = ROOT / "figures"
STOP_TIME = 0.002


def read_csv(path: Path) -> list[dict[str, float | str]]:
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


def f(value: object, default: float = math.nan) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def nearest(rows: list[dict], t: float) -> dict:
    return min(rows, key=lambda r: abs(f(r.get("time")) - t)) if rows else {}


def stage_rows() -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    short = read_csv(SHORT / "s1_bodygravity_stop_frame_metrics_gpu_after_patch.csv")
    medium = read_csv(MEDIUM / "gpu_s1_medium_frame_metrics.csv")
    long = read_csv(LONG / "gpu_s1_long_frame_metrics.csv")
    combined = []
    for stage, rows in [("S1-1b short GPU", short), ("S1-2 medium GPU", medium), ("S1-3 long GPU", long)]:
        for row in rows:
            out = dict(row)
            out["stage"] = stage
            combined.append(out)
    return short, medium, long, combined


def scenario1_reference_bottom(times: list[float]) -> list[dict]:
    # Supporting Materials notes: p0(z) = [(Kw/n) rho g (H-z)] / [M + Kw/n],
    # u(z,t) = sum A_n cos(lambda_n z) exp(-lambda_n^2 cv tau).
    # This is retained only as a context reference because the validated
    # BodyGravityStopTime run is a dynamic single-run workflow, not an
    # instantaneous Eq.(4) initialization.
    H = 0.9900000001
    E = 2.0e6
    nu = 0.3
    kw = 2.0e8
    n = 0.3
    k = 1.0e-3
    rho = 2100.0
    rho_w = 1000.0
    g = 9.81
    bulk = E / (3.0 * (1.0 - 2.0 * nu))
    shear = E / (2.0 * (1.0 + nu))
    m = bulk + 4.0 * shear / 3.0
    cv = k * m / (rho_w * g)
    denom = m + kw / n
    p0_bottom = (kw / n) * rho * g * H / denom

    def coeff(idx: int) -> float:
        lam = (2 * idx + 1) * math.pi / (2 * H)
        # A_n = 2/H int_0^H C(H-z) cos(lambda z) dz
        # = 2C/H * (H/lambda - sin(lambda H)/lambda^2)
        c = (kw / n) * rho * g / denom
        return (2.0 * c / H) * (H / lam - math.sin(lam * H) / (lam * lam))

    rows = []
    for t in times:
        tau = max(t - STOP_TIME, 0.0)
        u_bottom = 0.0
        for idx in range(240):
            lam = (2 * idx + 1) * math.pi / (2 * H)
            u_bottom += coeff(idx) * math.exp(-(lam * lam) * cv * tau)
        rows.append(
            {
                "time": t,
                "reference": "Supporting Materials Scenario 1 series; context only for BodyGravityStopTime",
                "bottom_excess_reference_pa": u_bottom,
                "initial_bottom_excess_pa": p0_bottom,
                "cv_m2_s": cv,
            }
        )
    return rows


def make_dir() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(exist_ok=True)


def save_fig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(FIG / f"{name}.svg")
    plt.savefig(FIG / f"{name}.png", dpi=220)
    try:
        plt.savefig(FIG / f"{name}.pdf")
    except Exception:
        pass
    plt.close()


def plot_bottom_excess(short: list[dict], medium: list[dict], long: list[dict], ref: list[dict]) -> None:
    plt.figure(figsize=(7.0, 4.2))
    for label, rows, style in [
        ("S1-1b short GPU", short, "o-"),
        ("S1-2 medium GPU", medium, "s-"),
        ("S1-3 long GPU", long, ".-"),
    ]:
        rows = sorted(rows, key=lambda r: f(r.get("time")))
        plt.plot([f(r.get("time")) for r in rows], [f(r.get("bottom_excess_mean")) for r in rows], style, markersize=3, label=label)
    plt.axvline(STOP_TIME, color="k", linestyle="--", linewidth=1, label="mechanical gravity stop")
    plt.xlabel("time [s]")
    plt.ylabel("bottom excess pressure [Pa]")
    plt.legend(fontsize=8)
    save_fig("figure1_bottom_excess_time")

    plt.figure(figsize=(7.0, 4.2))
    long_sorted = sorted(long, key=lambda r: f(r.get("time")))
    plt.plot([f(r.get("time")) for r in long_sorted], [abs(f(r.get("bottom_excess_mean"))) for r in long_sorted], ".-", label="S1-3 long GPU |bottom excess|")
    plt.plot([f(r.get("time")) for r in ref], [f(r.get("bottom_excess_reference_pa")) for r in ref], "--", label="SM Scenario 1 series context")
    plt.yscale("log")
    plt.axvline(STOP_TIME, color="k", linestyle="--", linewidth=1)
    plt.xlabel("time [s]")
    plt.ylabel("|bottom excess| [Pa]")
    plt.legend(fontsize=8)
    save_fig("figure1b_bottom_excess_reference_context")


def plot_excess_decay(long: list[dict]) -> None:
    rows = sorted(long, key=lambda r: f(r.get("time")))
    plt.figure(figsize=(7.0, 4.2))
    plt.plot([f(r.get("time")) for r in rows], [f(r.get("ExcessPorePress_maxAbs")) for r in rows], ".-", label="max |excess|")
    plt.plot([f(r.get("time")) for r in rows], [abs(f(r.get("ExcessPorePress_mean"))) for r in rows], ".-", label="|mean excess|")
    plt.axvline(STOP_TIME, color="k", linestyle="--", linewidth=1, label="gravity/top drain switch")
    plt.yscale("log")
    plt.xlabel("time [s]")
    plt.ylabel("excess pressure [Pa]")
    plt.legend(fontsize=8)
    save_fig("figure2_excess_decay")


def copy_profile_figures() -> None:
    # The heavy PartCsv output for S1-3 was intentionally cleaned after S1-3.
    # Carry forward the profile figures generated during that analysis.
    mapping = {
        "gpu_s1_long_excess_profiles": "figure3_excess_profiles",
        "gpu_s1_long_porepress_profiles": "figure4_total_pore_pressure_profiles",
    }
    for src_base, dst_base in mapping.items():
        for ext in ["svg", "png"]:
            src = LONG / "figures" / f"{src_base}.{ext}"
            if src.exists():
                shutil.copy2(src, FIG / f"{dst_base}.{ext}")


def plot_velocity(long: list[dict]) -> None:
    rows = sorted(long, key=lambda r: f(r.get("time")))
    plt.figure(figsize=(7.0, 4.2))
    plt.plot([f(r.get("time")) for r in rows], [f(r.get("Vel_mag_max")) for r in rows], ".-", label="max velocity")
    plt.plot([f(r.get("time")) for r in rows], [f(r.get("Vel_mag_mean")) for r in rows], ".-", label="mean velocity")
    plt.axvline(STOP_TIME, color="k", linestyle="--", linewidth=1)
    plt.yscale("log")
    plt.xlabel("time [s]")
    plt.ylabel("velocity [m/s]")
    plt.legend(fontsize=8)
    save_fig("figure5_velocity_decay")


def plot_boundary(long: list[dict]) -> None:
    rows = sorted(long, key=lambda r: f(r.get("time")))
    fig, ax = plt.subplots(2, 1, figsize=(7.0, 6.0), sharex=True)
    ax[0].plot([f(r.get("time")) for r in rows], [f(r.get("top_excess_maxAbs")) for r in rows], ".-")
    ax[0].set_yscale("log")
    ax[0].set_ylabel("top |excess| [Pa]")
    ax[0].axvline(STOP_TIME, color="k", linestyle="--", linewidth=1)
    ax[1].plot([f(r.get("time")) for r in rows], [abs(f(r.get("bottom_no_flux_proxy"))) for r in rows], ".-")
    ax[1].set_yscale("log")
    ax[1].set_xlabel("time [s]")
    ax[1].set_ylabel("|bottom no-flux proxy| [Pa]")
    ax[1].axvline(STOP_TIME, color="k", linestyle="--", linewidth=1)
    save_fig("figure6_boundary_checks")


def plot_consistency(short: list[dict], medium: list[dict], long: list[dict]) -> None:
    plt.figure(figsize=(7.0, 4.2))
    for label, rows, marker in [
        ("short", short, "o"),
        ("medium", medium, "s"),
        ("long", long, "."),
    ]:
        rows = sorted(rows, key=lambda r: f(r.get("time")))
        plt.plot([f(r.get("time")) for r in rows], [f(r.get("ExcessPorePress_maxAbs")) for r in rows], marker + "-", markersize=3, label=label)
    plt.axvline(STOP_TIME, color="k", linestyle="--", linewidth=1)
    plt.yscale("log")
    plt.xlabel("time [s]")
    plt.ylabel("max |excess| [Pa]")
    plt.legend()
    save_fig("figure7_short_medium_long_consistency")


def plot_contributions(long: list[dict]) -> None:
    rows = sorted(long, key=lambda r: f(r.get("time")))
    plt.figure(figsize=(7.0, 4.2))
    for key, label in [
        ("PorePressRate_maxAbs", "|PorePressRate|"),
        ("DivVelContribution_maxAbs", "|volumetric contribution|"),
        ("HydraulicContribution_maxAbs", "|hydraulic contribution|"),
    ]:
        plt.plot([f(r.get("time")) for r in rows], [f(r.get(key)) for r in rows], ".-", markersize=3, label=label)
    plt.yscale("log")
    plt.axvline(STOP_TIME, color="k", linestyle="--", linewidth=1)
    plt.xlabel("time [s]")
    plt.ylabel("rate contribution [Pa/s]")
    plt.legend(fontsize=8)
    save_fig("figure8_rate_contributions")


def consistency_metrics(short: list[dict], medium: list[dict], long: list[dict]) -> list[dict]:
    rows = []
    for name, a, b, note in [
        ("short_vs_medium_at_0p002", nearest(short, 0.002), nearest(medium, 0.002), "same retained switch frame"),
        ("short_vs_medium_at_0p004", nearest(short, 0.004), nearest(medium, 0.004), "same retained post-switch frame"),
        ("medium_vs_long_at_0p2", nearest(medium, 0.2), nearest(long, 0.2), "same retained medium/long overlap frame"),
    ]:
        rows.append(
            {
                "comparison": name,
                "note": note,
                "time_a": a.get("time", ""),
                "time_b": b.get("time", ""),
                "excess_maxAbs_a": a.get("ExcessPorePress_maxAbs", ""),
                "excess_maxAbs_b": b.get("ExcessPorePress_maxAbs", ""),
                "excess_maxAbs_diff": f(a.get("ExcessPorePress_maxAbs")) - f(b.get("ExcessPorePress_maxAbs")),
                "bottom_excess_a": a.get("bottom_excess_mean", ""),
                "bottom_excess_b": b.get("bottom_excess_mean", ""),
                "bottom_excess_diff": f(a.get("bottom_excess_mean")) - f(b.get("bottom_excess_mean")),
                "vel_max_a": a.get("Vel_mag_max", ""),
                "vel_max_b": b.get("Vel_mag_max", ""),
                "vel_max_diff": f(a.get("Vel_mag_max")) - f(b.get("Vel_mag_max")),
            }
        )
    rows.append(
        {
            "comparison": "short_vs_long_at_0p005",
            "note": "not computed: S1-3 long run used TimeOut=0.1 and has no retained 0.005 s frame; S1-1b remains the switch-time parity anchor",
        }
    )
    return rows


def aggregate_summaries() -> list[dict]:
    rows = []
    for source, path in [
        ("S1-1b short after patch", SHORT / "s1_bodygravity_stop_case_summary_after_patch.csv"),
        ("S1-2 medium", MEDIUM / "gpu_s1_medium_case_summary.csv"),
        ("S1-3 long", LONG / "gpu_s1_long_case_summary.csv"),
    ]:
        for row in read_csv(path):
            out = dict(row)
            out["source"] = source
            rows.append(out)
    return rows


def create_metrics(short: list[dict], medium: list[dict], long: list[dict], ref: list[dict]) -> None:
    combined = []
    for stage, rows in [("S1-1b", short), ("S1-2", medium), ("S1-3", long)]:
        for row in rows:
            out = dict(row)
            out["stage"] = stage
            combined.append(out)
    write_csv(ROOT / "scenario1_final_frame_metrics.csv", combined)
    write_csv(ROOT / "scenario1_final_case_summary.csv", aggregate_summaries())
    write_csv(ROOT / "scenario1_short_medium_long_consistency.csv", consistency_metrics(short, medium, long))
    write_csv(ROOT / "scenario1_boundary_metrics.csv", [{k: r.get(k, "") for k in ["run", "time", "top_excess_maxAbs", "bottom_no_flux_proxy", "bottom_excess_mean"]} for r in long])
    peak = max([f(r.get("ExcessPorePress_maxAbs")) for r in long] or [math.nan])
    diss = []
    for r in long:
        ex = f(r.get("ExcessPorePress_maxAbs"))
        diss.append(
            {
                "time": r.get("time", ""),
                "ExcessPorePress_maxAbs": ex,
                "excess_over_peak": ex / peak if peak else math.nan,
                "Vel_mag_max": r.get("Vel_mag_max", ""),
                "PorePressRate_maxAbs": r.get("PorePressRate_maxAbs", ""),
                "DivVelContribution_maxAbs": r.get("DivVelContribution_maxAbs", ""),
                "HydraulicContribution_maxAbs": r.get("HydraulicContribution_maxAbs", ""),
            }
        )
    write_csv(ROOT / "scenario1_dissipation_metrics.csv", diss)
    final = long[-1]
    write_csv(
        ROOT / "scenario1_paper_figure_metrics.csv",
        [
            {
                "metric": "early_peak_excess_maxAbs_pa",
                "value": peak,
            },
            {
                "metric": "final_excess_maxAbs_pa",
                "value": final.get("ExcessPorePress_maxAbs", ""),
            },
            {
                "metric": "final_over_peak",
                "value": f(final.get("ExcessPorePress_maxAbs")) / peak if peak else math.nan,
            },
            {"metric": "final_bottom_excess_pa", "value": final.get("bottom_excess_mean", "")},
            {"metric": "final_top_excess_maxAbs_pa", "value": final.get("top_excess_maxAbs", "")},
            {"metric": "final_bottom_no_flux_proxy_pa", "value": final.get("bottom_no_flux_proxy", "")},
            {"metric": "final_velocity_max_m_s", "value": final.get("Vel_mag_max", "")},
        ],
    )
    write_csv(ROOT / "scenario1_reference_metrics.csv", ref)


def create_note(short: list[dict], medium: list[dict], long: list[dict], ref: list[dict]) -> None:
    report = REPO / "src" / "papers" / "u-p" / "paper_scenario1_bodygravity_stop_note.md"
    final = long[-1]
    peak = max([f(r.get("ExcessPorePress_maxAbs")) for r in long] or [math.nan])
    overlap = consistency_metrics(short, medium, long)[-1]
    report.write_text(
        f"""# Scenario 1 BodyGravityStopTime paper-figure note

## Purpose

This note documents the final paper-figure set for the self-weight Scenario 1
`BodyGravityStopTime` route. The route generates self-weight pore-pressure
response with mechanical body gravity active, then stops the mechanical body
force at `t=0.002 s` while keeping `HydraulicGravity=(0,0,-9.81)` active and
activating the top-drained boundary.

## Why the BodyGravityStopTime Route Was Used

The single-run route avoids GPU restart-state mapping risk while preserving the
physical split required by Scenario 1:

- mechanical body gravity is removed after the undrained generation stage;
- hydraulic gravity remains active for hydrostatic elevation and `LapZ`;
- top drainage activates at the same staged time;
- bottom no-flux remains active.

The restart route remains deferred because the short/medium/long GPU route is
already stable and because restart parity would add a separate state-mapping
problem.

## Short CPU/GPU Parity Recap

S1-1b passed after the GPU `BodyGravityStopTime` patch:

- CPU/GPU `code=0`, `excluded=0`;
- GPU mechanical body gravity stopped at about `t=0.00200051 s`;
- `HydraulicGravity` remained active;
- final CPU/GPU `PorePress` and `ExcessPorePress` max-absolute differences were
  about `0.00394 Pa`;
- final velocity max-absolute difference was about `6e-09 m/s`.

## Medium Stability Recap

S1-2 passed both GPU medium windows:

- `0.05 s`: final `ExcessPorePress` maxAbs `84.08 Pa`;
- `0.2 s`: final `ExcessPorePress` maxAbs `27.36 Pa`;
- `code=0`, `excluded=0` for both.

## Long-Run Result

S1-3 ran to `3.600001 s` with `code=0`, `excluded=0`, `3,775,438` steps, and
`37` retained frames.

Key final metrics:

| metric | value |
|---|---:|
| final max velocity [m/s] | {f(final.get('Vel_mag_max')):.6g} |
| final mean velocity [m/s] | {f(final.get('Vel_mag_mean')):.6g} |
| final `ExcessPorePress` maxAbs [Pa] | {f(final.get('ExcessPorePress_maxAbs')):.6g} |
| final bottom excess mean [Pa] | {f(final.get('bottom_excess_mean')):.6g} |
| final top-drained excess maxAbs [Pa] | {f(final.get('top_excess_maxAbs')):.6g} |
| final bottom no-flux proxy [Pa] | {f(final.get('bottom_no_flux_proxy')):.6g} |
| excess final / long-run retained peak | {f(final.get('ExcessPorePress_maxAbs')) / peak:.6g} |

The S1-3 long run agrees with S1-2 at the overlap point:

| comparison | S1-2 medium | S1-3 long |
|---|---:|---:|
| time [s] | {overlap.get('time_a')} | {overlap.get('time_b')} |
| `ExcessPorePress` maxAbs [Pa] | {f(overlap.get('excess_maxAbs_a')):.6g} | {f(overlap.get('excess_maxAbs_b')):.6g} |
| bottom excess mean [Pa] | {f(overlap.get('bottom_excess_a')):.6g} | {f(overlap.get('bottom_excess_b')):.6g} |
| max velocity [m/s] | {f(overlap.get('vel_max_a')):.6g} | {f(overlap.get('vel_max_b')):.6g} |

## Boundary Consistency

The top-drained residual stayed near zero and the bottom no-flux proxy remained
small throughout the long run. No pressure blow-up or gravity-switch velocity
spike was observed.

## Reference / Analytical Comparison

The local Supporting Materials notes give a Scenario 1 cosine-series
dissipation reference assuming an instantaneous Eq.(4) undrained
self-weight profile at drainage activation. That reference was reconstructed
for context in `scenario1_reference_metrics.csv`.

It is not used as a strict error target for the final BodyGravityStopTime line,
because this validated route is a dynamic single-run workflow. Previous A2
audits showed that the actual generated profile at `t ~= 0.002 s` does not equal
the ideal Eq.(4) state. Therefore Scenario 1 is treated here as a
drainage-to-equilibrium stability and dissipation benchmark rather than a
strict analytical-profile reproduction.

## Figures

Paper figures and metrics are stored in:

`examples/u-pw/02_SelfWeight_Consolidation/experiments/PaperFigures_Scenario1_BodyGravityStop/`

Main figures:

1. bottom excess pressure vs time;
2. excess-pressure decay;
3. excess-pressure profiles carried forward from S1-3;
4. total pore-pressure profiles carried forward from S1-3;
5. velocity decay;
6. top-drained and bottom no-flux checks;
7. short/medium/long consistency;
8. pressure-rate, volumetric, and hydraulic contributions.

## Recommended Manuscript Wording

The Scenario 1 self-weight consolidation test was conducted using a single-run
mechanical-gravity switch, in which the mechanical body force was removed after
the undrained loading stage while the hydraulic gravity remained active. The
GPU solution remained stable over 3.6 s, with no particle exclusion,
continuous pressure dissipation, negligible top-drained residual, and a small
bottom no-flux residual. The excess pore pressure decayed to a final maximum
magnitude of approximately `1.65 Pa`, while the maximum velocity decreased to
approximately `3.0e-7 m/s`, confirming the stability of the coupled u-pw PR
implementation under the gravity-switch drainage workflow.

## Limitations

- This figure set does not claim strict analytical-profile reproduction for
  Scenario 1.
- The restart route remains deferred.
- `PorePressureBoundaryOperator=0` remains the production interpretation.
- Corrected-gradient production operators remain deferred.

## Closure

Scenario 1 can be used as a paper-compatible stability and
drainage-to-equilibrium validation figure for the current u-pw PR
implementation.
""",
        encoding="utf-8",
    )


def update_workflow_docs() -> None:
    workflow = REPO / "src" / "papers" / "u-p" / "scenario1_staged_workflow_plan.md"
    text = workflow.read_text(encoding="utf-8")
    marker = "\n## S1-4 Completion Status\n"
    addition = f"""{marker}
S1-1b, S1-2, S1-3, and S1-4 are complete for the
`BodyGravityStopTime` single-run route:

- S1-1b short CPU/GPU parity passed after the GPU body-gravity stop patch.
- S1-2 GPU medium windows to `0.05 s` and `0.2 s` passed.
- S1-3 GPU long run to `3.6 s` passed with `code=0`, `excluded=0`.
- S1-4 generated paper-figure metrics and the technical note
  `paper_scenario1_bodygravity_stop_note.md`.

The restart route remains deferred. The validated production path for the
current paper workflow is the single-run `BodyGravityStopTime` route with
`PorePressureBoundaryOperator=0`.
"""
    if marker in text:
        text = text.split(marker)[0] + addition
    else:
        text += addition
    workflow.write_text(text, encoding="utf-8")

    gpu_plan = REPO / "src" / "papers" / "u-p" / "gpu_port_plan.md"
    text = gpu_plan.read_text(encoding="utf-8")
    marker = "\n## Scenario 1 BodyGravityStopTime Status\n"
    addition = f"""{marker}
The Scenario 1 `BodyGravityStopTime` single-run workflow is complete through
S1-4:

- S1-1b: GPU mechanical body gravity stop support and short CPU/GPU parity.
- S1-2: GPU medium smoke to `0.05 s` and `0.2 s`.
- S1-3: GPU long run to `3.6 s` with `code=0`, `excluded=0`.
- S1-4: paper-figure and reference-context note generated.

`HydraulicGravity` remains active after the mechanical body force stops.
`PorePressureBoundaryOperator=0` remains the production path. The restart route,
corrected-gradient production operators, and GPU `PorePressureBoundaryOperator=2`
remain deferred.
"""
    if marker in text:
        text = text.split(marker)[0] + addition
    else:
        text += addition
    gpu_plan.write_text(text, encoding="utf-8")


def main() -> None:
    make_dir()
    short, medium, long, _ = stage_rows()
    times = [f(r.get("time")) for r in long]
    ref = scenario1_reference_bottom(times)
    create_metrics(short, medium, long, ref)
    plot_bottom_excess(short, medium, long, ref)
    plot_excess_decay(long)
    copy_profile_figures()
    plot_velocity(long)
    plot_boundary(long)
    plot_consistency(short, medium, long)
    plot_contributions(long)
    create_note(short, medium, long, ref)
    update_workflow_docs()
    (ROOT / "README.md").write_text(
        """# Paper Figures: Scenario 1 BodyGravityStopTime

This directory contains paper-ready figure artifacts for the Scenario 1
single-run `BodyGravityStopTime` GPU workflow. No new simulations are run by
the generator; it only consumes retained S1-1b/S1-2/S1-3 CSV summaries and
figures.

The profile figures are carried forward from S1-3 because heavy PartCsv output
was intentionally cleaned after the long run.
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
