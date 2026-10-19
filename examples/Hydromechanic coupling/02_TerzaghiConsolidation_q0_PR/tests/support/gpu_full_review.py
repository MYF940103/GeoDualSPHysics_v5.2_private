"""CPU/GPU 2Tv material-coordinate profiles and theory; never launch a solver."""
import argparse
import json
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from gpu_coupled_compare import records, frames, measure
from mdbc_gpu_vector_run import TESTS, bound, read, verify
from settlement_audit import previous, theoretical_settlement

TARGETS = (.1, .2, .4, .5, .7, 1., 1.5, 2.)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gpu", required=True)
    p.add_argument("--cpu", required=True)
    p.add_argument("--tag", required=True)
    args = p.parse_args()
    pair_path = TESTS / "logs" / (args.tag + "_pair.check.json")
    pair = read(pair_path)
    assert pair["passed"] and not pair["half_step_gate_applied"] and not pair["prefix_only"]
    verify([pair["figure"], pair["metrics"]])
    rows, profiles, evidence, completions = [], [], [bound(pair_path), bound(__file__)], {}
    for label, name in (("CPU", args.cpu), ("GPU", args.gpu)):
        run, settings, path, entries = records(name)
        assert settings["save"] == 1 and settings["steps"] == 7288429 and settings["dt"] == 1e-5
        xml = TESTS / "outputs" / (name + "_input") / ("CaseTCq0_" + name + ".xml")
        model = previous.model(ET.parse(xml))
        assert model["k"] == 1e-4
        evidence += entries + [bound(xml)]
        initial, selected = None, {}
        for a in frames(path, settings):
            if initial is None:
                initial = a.copy()
            time = float(a.time_s.iloc[0])
            tv = model["cv"] * max(time - model["tD"], 0) / model["H"] ** 2
            row, safety = measure(a, initial)
            assert all(safety.values())
            row.update(backend=label, tv=tv,
                classical_top_mm=float(theoretical_settlement([initial.z.iloc[99]], time, model)[0]),
                finite_kw_top_mm=float(theoretical_settlement([initial.z.iloc[99]], time, model, finite=True)[0]))
            rows.append(row)
            for target in TARGETS:
                if target not in selected or abs(tv - target) < selected[target][0]:
                    selected[target] = (abs(tv - target), a.copy(), time, tv)
        assert tv >= 2 - 1e-6 and abs(time - 72.88429) < 1e-6
        completions[label] = dict(actual_time_s=time, tv=tv, completion=run["completion"])
        for target, (_, a, time, actual_tv) in selected.items():
            z0 = initial.z.to_numpy().reshape(10, 100).mean(axis=0)
            pressure = a.pressure.to_numpy().reshape(10, 100).mean(axis=0)
            eta = model["n"] * model["M"] / model["Kw"]
            classical = previous.reference.pressure_theory(z0, actual_tv, model)
            finite = previous.reference.pressure_theory(z0, actual_tv / (1 + eta), model) / (1 + eta)
            for i in range(100):
                profiles.append(dict(backend=label, target_tv=target, actual_tv=actual_tv, time_s=time,
                    z0_H=z0[i] / model["H"], pressure_pa=pressure[i], classical_pa=classical[i], finite_kw_pa=finite[i]))
    history, profile = pd.DataFrame(rows), pd.DataFrame(profiles)
    base = TESTS / "figures" / args.tag
    history.to_csv(str(base) + "_history.csv", index=False, mode="x")
    profile.to_csv(str(base) + "_profiles.csv", index=False, mode="x")
    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    for color, target in zip(plt.cm.viridis(np.linspace(.05, .95, len(TARGETS))), TARGETS):
        for label, style in (("CPU", "-"), ("GPU", "--")):
            a = profile[(profile.backend == label) & (profile.target_tv == target)]
            axes[0].plot(a.pressure_pa / model["q0"], a.z0_H, color=color, ls=style,
                         label=f"Tv~{target:g}" if label == "CPU" else None)
            axes[1].plot(a.pressure_pa - a.finite_kw_pa, a.z0_H, color=color, ls=style)
        axes[0].plot(a.classical_pa / model["q0"], a.z0_H, color=color, ls=":", lw=.8)
    axes[0].set(xlabel="Pore pressure / q0", ylabel="Initial material z0/H", title="CPU solid / GPU dashed / classical dotted")
    axes[1].set(xlabel="Numerical - ideal finite-Kw pressure (Pa)", ylabel="Initial material z0/H")
    axes[0].legend(fontsize=8); axes[1].axvline(0, color="gray", lw=.7)
    for ax in axes:
        ax.grid(alpha=.25); ax.set_ylim(0, 1)
    fig.suptitle("k=1e-4: profiles at actual nearest saved times (no interpolation)")
    fig.tight_layout()
    with open(str(base) + "_profiles.png", "xb") as stream:
        fig.savefig(stream, dpi=170)
    plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))
    keys = ("mean_pressure_pa", "top_settlement_mm", "bottom_settlement_mm",
            "max_layer_total_error_pa", "top_gap_pa", "total_stress_Q_pa")
    for label, style in (("CPU", "-"), ("GPU", "--")):
        h = history[(history.backend == label) & (history.time_s >= .1 - 1e-7)]
        for ax, key in zip(axes.flat, keys):
            ax.plot(h.tv, h[key], style, lw=1.4, label=label)
            ax.set(xlabel="Tv from actual time", title=key); ax.grid(alpha=.25)
    axes[0, 1].plot(h.tv, h.classical_top_mm, ":", color="black", label="Classical (material top)")
    axes[0, 1].plot(h.tv, h.finite_kw_top_mm, ":", color="gray", label="Ideal finite Kw")
    axes[0, 0].legend(); axes[0, 1].legend(fontsize=8)
    fig.suptitle("Same-physics CPU/GPU full cycle; bottom bias and Q retained, not hidden")
    fig.tight_layout()
    with open(str(base) + "_history.png", "xb") as stream:
        fig.savefig(stream, dpi=170)
    plt.close(fig)
    # Both backends independently retain their original HG history guards.
    for label, name in (("CPU", args.cpu), ("GPU", args.gpu)):
        hg_path = TESTS / "outputs" / name / "hourglass.csv"
        h = pd.read_csv(hg_path, float_precision="round_trip")
        assert h.dt_over_tau.between(0, .2).all() and h.integrated_max_skew_rad.between(0, .01, inclusive="left").all()
        assert (abs(h.rate_power + 2 * h.rate_form) <= 1e-9 * (1 + abs(h.rate_power) + 2 * h.rate_form)).all()
        assert len(h) + 1 == len(history[history.backend == label])
        evidence.append(bound(hg_path))
    metrics = {}
    for label in ("CPU", "GPU"):
        h = history[history.backend == label]
        a = profile[profile.backend == label]
        metrics[label] = dict(final=h.iloc[-1].to_dict(),
            profile_rmse_by_tv={str(tv): float(np.sqrt(np.mean((s.pressure_pa - s.classical_pa)**2))) for tv, s in a.groupby("target_tv")},
            final_settlement_error_pct=float(100 * (h.iloc[-1].top_settlement_mm / h.iloc[-1].classical_top_mm - 1)))
    evidence += [bound(str(base) + suffix) for suffix in ("_history.csv", "_profiles.csv", "_history.png", "_profiles.png")]
    verify(evidence)
    with (TESTS / "logs" / (args.tag + ".check.json")).open("x", encoding="utf8") as stream:
        json.dump(dict(passed=True, completions=completions, metrics=metrics, evidence=evidence,
            visual_review_pending=True, physical_acceptance=False,
            limitations=["Elastic, small rotation, fixed plane, xi=.1, eta=.04, fresh HG starts only",
                         "Ideal theory omits dynamic load ramp; material-top settlement differs from H-top settlement",
                         "15-s half validation only; no full-cycle half-step trajectory",
                         "Old late-Q trend disclosed; user provisionally accepted 1D accuracy on Oct16"]), stream, indent=2)
    print(json.dumps(dict(passed=True, metrics=metrics), indent=2))


if __name__ == "__main__":
    main()
