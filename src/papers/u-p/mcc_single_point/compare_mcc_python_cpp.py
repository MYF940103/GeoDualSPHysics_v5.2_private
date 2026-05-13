"""Compare M2 Python and M3a C++ MCC material-point outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
FIG = ROOT / "figures"

PATHS = {
    "isotropic": ("m2_mcc_isotropic_path.csv", "m3a_cpp_isotropic_path.csv"),
    "drained_like": ("m2_mcc_drained_triaxial_path.csv", "m3a_cpp_drained_triaxial_path.csv"),
    "undrained_like": ("m2_mcc_undrained_path.csv", "m3a_cpp_undrained_path.csv"),
}

COMPARE_COLUMNS = [
    "p",
    "q",
    "pc",
    "e",
    "eps_p_v",
    "eps_p_eq",
    "plastic_multiplier",
    "yield_f",
    "yield_f_normalized",
    "residual",
    "stress_xx",
    "stress_yy",
    "stress_zz",
    "sigmac_xx",
    "sigmac_yy",
    "sigmac_zz",
]


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict]) -> None:
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


def f(row: Dict[str, str], key: str) -> float:
    return float(row[key])


def max_abs_diff(py_rows: List[Dict[str, str]], cpp_rows: List[Dict[str, str]], key: str) -> float:
    return max(abs(f(a, key) - f(b, key)) for a, b in zip(py_rows, cpp_rows))


def max_int_diff(py_rows: List[Dict[str, str]], cpp_rows: List[Dict[str, str]], key: str) -> int:
    return max(abs(int(a[key]) - int(b[key])) for a, b in zip(py_rows, cpp_rows))


def save_plot(name: str, fig) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    svg = FIG / f"{name}.svg"
    png = FIG / f"{name}.png"
    fig.savefig(svg)
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
    fig.savefig(png, dpi=180)
    plt.close(fig)


def plot_path(name: str, py_rows: List[Dict[str, str]], cpp_rows: List[Dict[str, str]]) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([f(r, "p") for r in py_rows], [f(r, "q") for r in py_rows], label="Python", lw=2)
    ax.plot([f(r, "p") for r in cpp_rows], [f(r, "q") for r in cpp_rows], "--", label="C++", lw=1.5)
    ax.set_xlabel("p' (Pa)")
    ax.set_ylabel("q (Pa)")
    ax.set_title(f"Python vs C++ p'-q: {name}")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save_plot(f"m3a_python_cpp_{name}_pq", fig)


def plot_time(name: str, key: str, ylabel: str, py_rows: List[Dict[str, str]], cpp_rows: List[Dict[str, str]]) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([f(r, "step") for r in py_rows], [f(r, key) for r in py_rows], label="Python", lw=2)
    ax.plot([f(r, "step") for r in cpp_rows], [f(r, key) for r in cpp_rows], "--", label="C++", lw=1.5)
    ax.set_xlabel("step")
    ax.set_ylabel(ylabel)
    ax.set_title(f"Python vs C++ {ylabel}: {name}")
    ax.legend()
    ax.grid(True, alpha=0.3)
    save_plot(f"m3a_python_cpp_{name}_{key}", fig)


def main() -> None:
    metrics = []
    summary: Dict[str, object] = {"paths": {}, "passed": True}
    for name, (py_file, cpp_file) in PATHS.items():
        py_rows = read_csv(OUT / py_file)
        cpp_rows = read_csv(OUT / cpp_file)
        if len(py_rows) != len(cpp_rows):
            summary["passed"] = False
            raise RuntimeError(f"Row count mismatch for {name}: Python={len(py_rows)} C++={len(cpp_rows)}")

        path_summary: Dict[str, float | int] = {"rows": len(py_rows)}
        for col in COMPARE_COLUMNS:
            diff = max_abs_diff(py_rows, cpp_rows, col)
            metrics.append({"path": name, "field": col, "max_abs_diff": diff})
            path_summary[f"max_abs_diff_{col}"] = diff
        iter_diff = max_int_diff(py_rows, cpp_rows, "iterations")
        yield_flag_diff = max_int_diff(py_rows, cpp_rows, "yield_flag")
        metrics.append({"path": name, "field": "iterations", "max_abs_diff": iter_diff})
        metrics.append({"path": name, "field": "yield_flag", "max_abs_diff": yield_flag_diff})
        path_summary["max_iteration_diff"] = iter_diff
        path_summary["max_yield_flag_diff"] = yield_flag_diff
        summary["paths"][name] = path_summary

        plot_path(name, py_rows, cpp_rows)
        plot_time(name, "pc", "p_c (Pa)", py_rows, cpp_rows)
        plot_time(name, "yield_f_normalized", "normalized |f|", py_rows, cpp_rows)
        plot_time(name, "iterations", "iterations", py_rows, cpp_rows)

    sign_py = read_csv(OUT / "m2_mcc_sign_regression.csv")
    sign_cpp = read_csv(OUT / "m3a_cpp_sign_regression.csv")
    sign_metrics = []
    for col in ["p_internal", "q_internal", "sigmac_xx_roundtrip", "sigmac_yy_roundtrip", "sigmac_zz_roundtrip"]:
        diff = abs(float(sign_py[0][col]) - float(sign_cpp[0][col]))
        sign_metrics.append({"path": "sign_regression", "field": col, "max_abs_diff": diff})
    metrics.extend(sign_metrics)
    summary["sign_regression"] = {m["field"]: m["max_abs_diff"] for m in sign_metrics}

    write_csv(OUT / "m3a_python_cpp_parity_metrics.csv", metrics)
    (OUT / "m3a_python_cpp_parity_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("M3a Python-C++ parity complete")
    for row in metrics:
        if row["field"] in {"p", "q", "pc", "e", "iterations"}:
            print(f"{row['path']} {row['field']}: max_abs_diff={row['max_abs_diff']}")


if __name__ == "__main__":
    main()
