"""Offline plot and conditioned arithmetic review; never launches a solver."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import struct

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"
T = Path(__file__).resolve().parents[1]
TAG = "upl_lian_variable_scalar_r1"


def entry(path):
    return dict(path=str(path.resolve()), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def field(name, x, z):
    return {"1": lambda: 1., "x": lambda: x, "z": lambda: z,
            "half_x2": lambda: .5*x*x, "xz": lambda: x*z,
            "half_z2": lambda: .5*z*z, "cos2pi_x": lambda: math.cos(2*math.pi*x),
            "cos2pi_x_plus_z": lambda: math.cos(2*math.pi*(x+z))}[name]()


def main():
    import psutil
    psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-prefix", required=True)
    args = parser.parse_args()
    assert args.output_prefix.replace("_", "").isalnum(), "Use a simple fresh label"
    products = [T/"figures"/(args.output_prefix+s) for s in (".csv", ".png")]
    check = T/"logs"/(args.output_prefix+".review.json")
    assert not any(p.exists() for p in [*products, check]), "Retained products protected"
    receipt = T/"logs"/(TAG+".run.json")
    run = json.loads(receipt.read_text(encoding="utf-8-sig"))
    assert run["passed"] is True and run["program_attempts"] == 1
    for item in run["files"]:
        assert entry(Path(item["path"])) == item
    source = Path(run["output_directory"])
    response, states, weights = (rows(source/n) for n in ("responses.csv", "states.csv", "weights.csv"))
    assert len(response) == 1536 and len(states) == 24*361
    points, pairs = {}, {}
    for r in states:
        points.setdefault((r["geometry"], r["J_law_state"]), {})[int(r["node"])] = r
    for r in weights:
        pairs.setdefault((r["geometry"], r["J_law_state"], r["C_denominator"]), []).append(r)
    cached, maximum, max_abs = {}, 0., 0.
    alpha = run["native_summary"]["alpha"]
    for r in response:
        key = tuple(r[k] for k in ("geometry", "J_law_state", "C_denominator", "pressure_storage", "field"))
        if key not in cached:
            nodes, pp = points[key[:2]], pairs[key[:3]]
            p = {i: field(r["field"], float(q["x"]), float(q["z"])) for i, q in nodes.items()}
            if r["pressure_storage"] == "float_quantized_pressure":
                p = {i: struct.unpack("f", struct.pack("f", v))[0] for i, v in p.items()}
            lp = raw = lx = lz = gpx = gpz = gjx = gjz = scale = 0.
            for q in pp:
                j = int(q["neighbor"])
                v, w, dx, dz, gx, gz, kb = (float(q[n]) for n in ("Vj", "w", "dx", "dz", "gi_x", "gi_z", "kbar"))
                dp = p[180]-p[j]
                lp += w*dp; raw += kb*w*dp; lx += w*dx; lz += w*dz
                gpx += -v*dp*gx; gpz += -v*dp*gz
                delta = float(nodes[j]["J"])-float(nodes[180]["J"])
                gjx += v*delta*gx; gjz += v*delta*gz
                scale += abs(kb*w)*(abs(p[180])+abs(p[j]))
            ki = float(nodes[180]["k"])
            chain = 0. if r["J_law_state"].endswith("OFF") else alpha*ki*gjx*gpx+alpha*ki*gjz*gpz
            defect = gpx*lx+gpz*lz
            cached[key] = (ki*(lp-defect)+chain, raw-ki*defect,
                           128*(len(pp)+4)*2.220446049250313e-16*(scale+abs(ki*defect)+abs(chain)))
        product, pair, budget = cached[key]
        value = pair if r["k_treatment"].startswith("Eq25") else product
        difference = abs(value-float(r["actual_normalized_source"]))
        ratio = difference/budget if budget else 0.
        assert difference == 0. if budget == 0. else ratio <= 1., "Conditioned arithmetic reconstruction differs"
        maximum, max_abs = max(maximum, ratio), max(max_abs, difference)
    selected = [r for r in response if r["J_law_state"] == "affine_J_law_ON" and
                r["pressure_storage"] == "double_pressure" and
                r["field"] in ("x", "z", "cos2pi_x", "cos2pi_x_plus_z")]
    assert len(selected) == 96
    with products[0].open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(selected[0])); writer.writeheader(); writer.writerows(selected)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FixedLocator, ScalarFormatter
    fig, axes = plt.subplots(2, 4, figsize=(16, 7), constrained_layout=True)
    names = ("x", "z", "cos2pi_x", "cos2pi_x_plus_z")
    for row, cloud in enumerate(("ordered", "fixed_jitter_008dp")):
        for col, name in enumerate(names):
            ax = axes[row, col]
            for branch, color in (("receiver_C_r2", "C0"), ("production_pair_C_Eta2", "C1")):
                for method, style in (("production_product_rule_pattern", "-o"), ("Eq25_pressure_weight_pattern_gamma1", "--s")):
                    rr = sorted((r for r in selected if (r["cloud"], r["field"], r["C_denominator"], r["k_treatment"]) ==
                                (cloud, name, branch, method)), key=lambda r: int(r["dp_denominator"]))
                    y = [100*float(r["relative_continuum_error_if_nonzero"]) for r in rr]
                    ax.plot([int(r["dp_denominator"]) for r in rr], [v if v > 0 else math.nan for v in y], style,
                            color=color, ms=4, label=("pair C / Eta" if branch.startswith("production") else "receiver C / r2")+
                            (": pair-k" if method.startswith("Eq25") else ": product rule"))
            ax.set_xscale("log", base=2); ax.set_yscale("log")
            ax.xaxis.set_major_locator(FixedLocator([16, 32, 64])); ax.xaxis.set_major_formatter(ScalarFormatter())
            ax.xaxis.set_minor_locator(FixedLocator([])); ax.set(xlabel="1 / dp", ylabel="Relative error (%)",
                                                             title=cloud+" / "+name)
            ax.grid(True, alpha=.3)
    axes[0, 0].legend(fontsize=7)
    fig.suptitle("Smooth k(J), pressure only: same-state 2x2 comparison; zero errors omitted on log axis\n"
                 "Roundoff-limited affine products are not a physical convergence claim; no wall/acceleration tested", fontsize=10)
    fig.savefig(products[1], dpi=160); plt.close(fig)
    result = dict(stage=args.output_prefix+".review", passed=True, source_run=entry(receipt),
                  source_files=run["files"], rows_recomputed=len(response),
                  conditioned_reconstruction_max_difference=max_abs, conditioned_roundoff_ratio_max=maximum,
                  selected_rows=len(selected), files=[entry(p) for p in products],
                  operator_reconstruction_uses_exported_weights_and_states=True,
                  independent_C_kernel_or_native_parser_claim=False, physical_acceptance=False,
                  solver_or_build_invoked=False, script=entry(Path(__file__)))
    with check.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps(dict(passed=True, check=str(check), max_difference=max_abs, max_ratio=maximum)))


if __name__ == "__main__":
    main()
