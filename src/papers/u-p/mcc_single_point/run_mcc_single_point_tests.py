"""Run standalone Modified Cam Clay single-point diagnostic paths."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from mcc_single_point import (
    MCCParams,
    from_sigmac_negative_compression,
    invariants,
    log_p,
    make_initial_state,
    principal_diag,
    record_step,
    to_sigmac_negative_compression,
    trace,
    update_state,
    yield_function,
)


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
FIG = ROOT / "figures"


def write_csv(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    keys: List[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def read_col(rows: Iterable[Dict], key: str) -> List[float]:
    return [float(r[key]) for r in rows]


def save_plot(name: str, fig) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    svg_path = FIG / f"{name}.svg"
    fig.savefig(svg_path)
    # Matplotlib writes multi-line path data with trailing spaces.  Strip them
    # so repository whitespace checks stay useful.
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
        encoding="utf-8",
    )
    fig.savefig(FIG / f"{name}.png", dpi=180)
    plt.close(fig)


def default_params() -> MCCParams:
    return MCCParams(
        m=1.20,
        lam=0.20,
        kappa=0.04,
        e0=0.80,
        pc0=160.0,
        young=5000.0,
        poisson=0.30,
        tension_cutoff=1.0e-5,
        return_tolerance=1.0e-8,
        return_max_iter=45,
    )


def sign_regression(params: MCCParams) -> List[Dict]:
    sigmac = principal_diag(-50.0, -50.0, -50.0)
    internal = from_sigmac_negative_compression(sigmac)
    p, q, _ = invariants(internal)
    sigmac_back = to_sigmac_negative_compression(internal)
    return [
        {
            "test": "hydrostatic_compression",
            "sigmac_xx_input": sigmac[0][0],
            "sigmac_yy_input": sigmac[1][1],
            "sigmac_zz_input": sigmac[2][2],
            "p_internal": p,
            "q_internal": q,
            "sigmac_xx_roundtrip": sigmac_back[0][0],
            "sigmac_yy_roundtrip": sigmac_back[1][1],
            "sigmac_zz_roundtrip": sigmac_back[2][2],
            "passed": int(p > 0.0 and abs(q) < 1.0e-12 and sigmac_back[0][0] < 0.0),
            "m": params.m,
            "lambda": params.lam,
            "kappa": params.kappa,
            "e0": params.e0,
            "pc0": params.pc0,
        }
    ]


def run_path(path: str, increments: List, params: MCCParams, p0: float = 100.0) -> List[Dict]:
    state = make_initial_state(p0, params)
    rows: List[Dict] = []
    rows.append(record_step(0, path, principal_diag(0.0, 0.0, 0.0), state, params))
    p_initial, _, _ = invariants(state.stress)
    for step, strain_inc in enumerate(increments, start=1):
        state = update_state(state, strain_inc, params)
        p, _, _ = invariants(state.stress)
        pore_proxy = p_initial - p if path.startswith("undrained") else 0.0
        rows.append(record_step(step, path, strain_inc, state, params, pore_proxy))
    return rows


def isotropic_path(params: MCCParams) -> List[Dict]:
    increments = []
    for _ in range(90):
        increments.append(principal_diag(1.5e-4, 1.5e-4, 1.5e-4))
    for _ in range(45):
        increments.append(principal_diag(-1.0e-4, -1.0e-4, -1.0e-4))
    for _ in range(45):
        increments.append(principal_diag(1.0e-4, 1.0e-4, 1.0e-4))
    return run_path("isotropic_compression_swelling", increments, params)


def drained_like_path(params: MCCParams) -> List[Dict]:
    increments = []
    for _ in range(140):
        # Simplified drained-like strain-controlled triaxial compression:
        # axial compression with zero lateral strain. This is not a strict
        # constant-confining-stress material driver.
        increments.append(principal_diag(3.0e-4, 0.0, 0.0))
    return run_path("drained_like_triaxial_strain_control", increments, params)


def undrained_like_path(params: MCCParams) -> List[Dict]:
    increments = []
    for _ in range(140):
        # Zero volumetric strain deviatoric compression.
        increments.append(principal_diag(3.0e-4, -1.5e-4, -1.5e-4))
    return run_path("undrained_like_zero_volumetric_strain", increments, params)


def yield_consistency_rows(paths: Dict[str, List[Dict]], params: MCCParams) -> List[Dict]:
    rows = []
    for name, data in paths.items():
        plastic = [r for r in data if int(r["yield_flag"]) == 1]
        max_abs_f = max((abs(float(r["yield_f"])) for r in plastic), default=0.0)
        max_norm_f = max((float(r["yield_f_normalized"]) for r in plastic), default=0.0)
        max_res = max((abs(float(r["residual"])) for r in plastic), default=0.0)
        max_iter = max((int(r["iterations"]) for r in plastic), default=0)
        final = data[-1]
        rows.append(
            {
                "path": name,
                "steps": len(data) - 1,
                "plastic_steps": len(plastic),
                "max_abs_yield_f_plastic": max_abs_f,
                "max_normalized_yield_f_plastic": max_norm_f,
                "max_abs_return_residual_plastic": max_res,
                "max_iterations": max_iter,
                "final_p": final["p"],
                "final_q": final["q"],
                "final_pc": final["pc"],
                "final_e": final["e"],
                "final_eps_p_v": final["eps_p_v"],
                "final_eps_p_eq": final["eps_p_eq"],
                "tolerance": params.return_tolerance,
            }
        )
    return rows


def return_iteration_rows(paths: Dict[str, List[Dict]]) -> List[Dict]:
    rows = []
    for name, data in paths.items():
        for r in data:
            rows.append(
                {
                    "path": name,
                    "step": r["step"],
                    "yield_flag": r["yield_flag"],
                    "return_status": r["return_status"],
                    "iterations": r["iterations"],
                    "residual": r["residual"],
                    "yield_f": r["yield_f"],
                    "plastic_multiplier": r["plastic_multiplier"],
                }
            )
    return rows


def summary_rows(paths: Dict[str, List[Dict]], sign_rows: List[Dict], params: MCCParams) -> List[Dict]:
    rows = []
    for name, data in paths.items():
        final = data[-1]
        plastic = [r for r in data if int(r["yield_flag"]) == 1]
        failed = [r for r in data if "failure" in str(r["return_status"]) or "tension" in str(r["return_status"])]
        rows.append(
            {
                "case": name,
                "steps": len(data) - 1,
                "plastic_steps": len(plastic),
                "failed_steps": len(failed),
                "final_p": final["p"],
                "final_q": final["q"],
                "final_pc": final["pc"],
                "final_e": final["e"],
                "final_eps_p_v": final["eps_p_v"],
                "final_eps_p_eq": final["eps_p_eq"],
                "max_iterations": max((int(r["iterations"]) for r in data), default=0),
                "max_abs_yield_f": max(abs(float(r["yield_f"])) for r in data),
                "max_normalized_yield_f": max(float(r["yield_f_normalized"]) for r in data),
                "max_abs_residual": max(abs(float(r["residual"])) for r in data),
                "M": params.m,
                "lambda": params.lam,
                "kappa": params.kappa,
                "e0": params.e0,
                "pc0": params.pc0,
                "E": params.young,
                "nu": params.poisson,
            }
        )
    rows.append(
        {
            "case": "stress_sign_regression",
            "steps": 1,
            "plastic_steps": 0,
            "failed_steps": 0 if sign_rows[0]["passed"] else 1,
            "final_p": sign_rows[0]["p_internal"],
            "final_q": sign_rows[0]["q_internal"],
            "final_pc": params.pc0,
            "final_e": params.e0,
            "final_eps_p_v": 0.0,
            "final_eps_p_eq": 0.0,
            "max_iterations": 0,
            "max_abs_yield_f": abs(yield_function(sign_rows[0]["p_internal"], sign_rows[0]["q_internal"], params.pc0, params)),
            "max_normalized_yield_f": abs(yield_function(sign_rows[0]["p_internal"], sign_rows[0]["q_internal"], params.pc0, params))
            / max(params.m * params.m * sign_rows[0]["p_internal"] * params.pc0, 1.0),
            "max_abs_residual": 0.0,
            "M": params.m,
            "lambda": params.lam,
            "kappa": params.kappa,
            "e0": params.e0,
            "pc0": params.pc0,
            "E": params.young,
            "nu": params.poisson,
        }
    )
    return rows


def make_figures(paths: Dict[str, List[Dict]], consistency: List[Dict]) -> None:
    iso = paths["isotropic"]
    drained = paths["drained_like"]
    undrained = paths["undrained_like"]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([log_p(float(r["p"])) for r in iso], read_col(iso, "e"), lw=1.8)
    ax.set_xlabel("log(p')")
    ax.set_ylabel("void ratio e")
    ax.set_title("MCC isotropic compression / swelling")
    ax.grid(True, alpha=0.3)
    save_plot("m2_isotropic_e_logp", fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(read_col(drained, "p"), read_col(drained, "q"), label="drained-like")
    ax.plot(read_col(undrained, "p"), read_col(undrained, "q"), label="undrained-like")
    ax.set_xlabel("p' (Pa)")
    ax.set_ylabel("q (Pa)")
    ax.set_title("MCC p'-q paths")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save_plot("m2_pq_paths", fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(read_col(drained, "step"), read_col(drained, "pc"), label="drained-like")
    ax.plot(read_col(undrained, "step"), read_col(undrained, "pc"), label="undrained-like")
    ax.plot(read_col(iso, "step"), read_col(iso, "pc"), label="isotropic")
    ax.set_xlabel("step")
    ax.set_ylabel("p_c (Pa)")
    ax.set_title("MCC hardening")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save_plot("m2_pc_evolution", fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    for name, data in paths.items():
        ax.semilogy(read_col(data, "step"), [max(float(r["yield_f_normalized"]), 1.0e-18) for r in data], label=name)
    ax.set_xlabel("step")
    ax.set_ylabel("normalized |yield f|")
    ax.set_title("Yield function normalized residual/history")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save_plot("m2_yield_residual", fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    for name, data in paths.items():
        ax.plot(read_col(data, "step"), read_col(data, "plastic_multiplier"), label=name)
    ax.set_xlabel("step")
    ax.set_ylabel("plastic multiplier")
    ax.set_title("Plastic multiplier per step")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save_plot("m2_plastic_multiplier", fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    for name, data in paths.items():
        ax.plot(read_col(data, "step"), read_col(data, "iterations"), label=name)
    ax.set_xlabel("step")
    ax.set_ylabel("Newton iterations")
    ax.set_title("Return mapping iterations")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save_plot("m2_iteration_count", fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.axis("off")
    sign_text = [
        "Sigmac input: (-50, -50, -50) Pa",
        "Internal p': +50 Pa",
        "Round trip: compression remains negative in Sigmac",
    ]
    ax.text(0.02, 0.7, "\n".join(sign_text), fontsize=11, va="top")
    ax.set_title("Stress sign regression")
    save_plot("m2_stress_sign_regression", fig)

    fig, ax = plt.subplots(figsize=(6, 4))
    names = [str(r["path"]) for r in consistency]
    vals = [float(r["max_normalized_yield_f_plastic"]) for r in consistency]
    ax.bar(names, vals)
    ax.set_yscale("log")
    ax.set_ylabel("max normalized |f| on plastic steps")
    ax.set_title("Yield consistency by path")
    ax.tick_params(axis="x", rotation=25)
    ax.grid(True, axis="y", alpha=0.3)
    save_plot("m2_yield_consistency_summary", fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)

    params = default_params()
    params.validate()
    (OUT / "m2_mcc_default_parameters.json").write_text(
        json.dumps(
            {
                "M": params.m,
                "lambda": params.lam,
                "kappa": params.kappa,
                "e0": params.e0,
                "pc0": params.pc0,
                "E": params.young,
                "nu": params.poisson,
                "tension_cutoff": params.tension_cutoff,
                "return_tolerance": params.return_tolerance,
                "return_max_iter": params.return_max_iter,
                "elastic_predictor": "linear isotropic E/nu",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    sign = sign_regression(params)
    iso = isotropic_path(params)
    drained = drained_like_path(params)
    undrained = undrained_like_path(params)
    paths = {"isotropic": iso, "drained_like": drained, "undrained_like": undrained}

    consistency = yield_consistency_rows(paths, params)
    iterations = return_iteration_rows(paths)
    summary = summary_rows(paths, sign, params)

    write_csv(OUT / "m2_mcc_sign_regression.csv", sign)
    write_csv(OUT / "m2_mcc_isotropic_path.csv", iso)
    write_csv(OUT / "m2_mcc_drained_triaxial_path.csv", drained)
    write_csv(OUT / "m2_mcc_undrained_path.csv", undrained)
    write_csv(OUT / "m2_mcc_yield_consistency.csv", consistency)
    write_csv(OUT / "m2_mcc_return_iterations.csv", iterations)
    write_csv(OUT / "m2_mcc_test_summary.csv", summary)

    make_figures(paths, consistency)

    print("M2 MCC single-point tests complete")
    for row in summary:
        print(
            f"{row['case']}: failed={row['failed_steps']} final_p={float(row['final_p']):.6g} "
            f"final_q={float(row['final_q']):.6g} final_pc={float(row['final_pc']):.6g}"
        )


if __name__ == "__main__":
    main()
