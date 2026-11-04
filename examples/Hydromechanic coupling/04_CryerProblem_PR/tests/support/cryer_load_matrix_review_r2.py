"""Plot sealed Cryer load-correction diagnostics; no decoder or solver calls."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"
T = Path(__file__).resolve().parents[1]
PINS = {
    "logs/cryer_load_pair_r1.check.json": "77f8b1478da58e6e8c54a86c22c023da958c6bf1a248b3a0219d288bb7a44ed9",
    "logs/cryer_radial_patch_r1.check.json": "d8639db2c1f4598515f8b2cb76861fae0231ac8030dafd33f765d237b748a290",
    "figures/cryer_radial_patch_r1_metrics.csv": "4b49e044f3e70f4e21d721ec414ab38b82a93c4ca08cd71d8da30cd2a787c739",
}
VARIANTS = ("A_current_raw", "B_load_only_receiver_C", "C_receiver_C_coupled_extension", "D_pair_adjoint_extension")
LABELS = ("A raw", "B load-only C", "C matched\nreceiver C", "D pair adjoint")


def entry(path):
    return dict(path=str(path.resolve()), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def write_csv(path, data):
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]))
        writer.writeheader(); writer.writerows(data)


def main():
    import psutil
    psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-prefix", required=True)
    args = parser.parse_args()
    assert args.output_prefix.replace("_", "").isalnum(), "Use a simple fresh label"
    products = {n: T/"figures"/(args.output_prefix+"."+n) for n in ("schemes.csv", "patch.csv", "history.csv", "png")}
    check = T/"logs"/(args.output_prefix+".check.json")
    assert not any(p.exists() for p in [*products.values(), check]), "Retained outputs protected"
    inputs = []
    for name, expected in PINS.items():
        e = entry(T/name); assert e["sha256"] == expected, name
        inputs.append(e)
    pair = json.loads((T/"logs/cryer_load_pair_r1.check.json").read_text(encoding="utf-8-sig"))
    patch = json.loads((T/"logs/cryer_radial_patch_r1.check.json").read_text(encoding="utf-8-sig"))
    assert pair["analysis_checks_passed"] is True and patch["analysis_checks_passed"] is True
    assert pair["solver_executed"] is False and patch["solver_executed"] is False
    scheme_rows = []
    cases = pair["frozen_pair_screen"]["density_cases"]
    for density, case in cases.items():
        for field, variants in case["fields"].items():
            for name in VARIANTS:
                total, load = variants[name]["total"], variants[name]["external_load"]
                scheme_rows.append(dict(density_case=density, manufactured_field=field, variant=name,
                    total_component_RMS_m_s2=total["component_rms_m_s2"], total_vector_RMS_m_s2=total["vector_rms_m_s2"],
                    total_vector_max_m_s2=total["vector_max_m_s2"], net_force_over_qA=total["net_force_over_qA"],
                    torque_over_qV=total["torque_over_qV"], load_radial_over_qA=load["radial_force_over_qA"],
                    load_work_over_3q_nativeV=load["isotropic_compressive_work_over_3q_nativeV"],
                    load_work_over_3q_geometricV=load["isotropic_compressive_work_over_3qV"]))
    with (T/"figures/cryer_radial_patch_r1_metrics.csv").open(encoding="utf-8-sig", newline="") as stream:
        patch_rows = list(csv.DictReader(stream))
    assert len(scheme_rows) == 24 and len(patch_rows) == 60
    history = []
    for r in pair["native_history"]:
        center, whole = r["center"], r["whole"]
        history.append(dict(part=r["part"], actual_time_s=r["actual_time_s"],
            fixed_center_ID_count=center["count"], center_pressure_Pa=center["pressure_mean_pa"],
            center_total_compression_Pa=center["total_mean_compression_pa"],
            center_total_radial_compression_Pa=center["total_radial_compression_pa"],
            center_total_tangent_compression_Pa=center["total_tangent_compression_pa"],
            whole_total_compression_Pa=whole["total_mean_compression_pa"],
            imposed_q_Pa=center["total_mean_compression_pa"]-center["total_mean_minus_q_pa"]))
    assert len(history) == 8 and all(r["fixed_center_ID_count"] == 12 for r in history)
    for name, data in (("schemes.csv", scheme_rows), ("patch.csv", patch_rows), ("history.csv", history)):
        write_csv(products[name], data)
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    uniform = cases["initial_uniform_rho"]["fields"]["uniform_drained"]
    x = np.arange(4)
    values = [uniform[v]["total"]["component_rms_m_s2"] for v in VARIANTS]
    ax = axes[0, 0]
    ax.bar(x, values, color=["C0", "C3", "C1", "C2"])
    ax.set_yscale("symlog", linthresh=1e-10)
    ax.set(xticks=x, xticklabels=LABELS, ylabel="Residual acceleration component RMS (m/s2)",
           title="Uniform drained compression: load-only correction breaks balance")
    for i, value in enumerate(values): ax.annotate("0" if value == 0 else "%.3g" % value, (i, value), xytext=(0, 6), textcoords="offset points", ha="center")
    ax.grid(True, axis="y", alpha=.3)
    ax = axes[0, 1]
    for offset, key, label in ((-.18, "isotropic_compressive_work_over_3q_nativeV", "Native quadrature volume"),
                               (.18, "isotropic_compressive_work_over_3qV", "Nominal sphere volume")):
        ax.bar(x+offset, [uniform[v]["external_load"][key] for v in VARIANTS], width=.36, label=label)
    ax.axhline(1., color="k", ls=":", lw=1)
    ax.set(xticks=x, xticklabels=LABELS, ylabel="External load moment / (3 q V)",
           title="Affine radial work: keep native and geometric volumes distinct")
    ax.legend(fontsize=8); ax.grid(True, axis="y", alpha=.3)
    ax = axes[1, 0]
    regions, labels = ("whole", "center", "true_surface"), ("Whole sphere", "18 center IDs", "Tracked surface IDs")
    for i, name in enumerate((VARIANTS[0], VARIANTS[2], VARIANTS[3])):
        rr = [next(r for r in patch_rows if float(r["p_over_q"]) == .6 and r["variant"] == name and r["region"] == region)
              for region in regions]
        ax.bar(np.arange(3)+(i-1)*.24, [float(r["vector_rms_m_s2"]) for r in rr], width=.24, label=LABELS[VARIANTS.index(name)])
    ax.set(xticks=np.arange(3), xticklabels=labels, ylabel="Residual acceleration vector RMS (m/s2)",
           title="Nonuniform radial equilibrium, pressure scale = 0.6 q")
    ax.legend(fontsize=8); ax.grid(True, axis="y", alpha=.3)
    ax = axes[1, 1]
    for key, label in (("center_total_compression_Pa", "Fixed center total compression"),
                       ("whole_total_compression_Pa", "Whole mean total compression")):
        ax.plot([r["actual_time_s"] for r in history], [r[key]/1000 for r in history], "o--", label=label)
    ax.axhline(history[-1]["imposed_q_Pa"]/1000, color="k", ls=":", label="Imposed q")
    ax.set(xlabel="Actual saved time (s)", ylabel="Total compression (kPa)",
           title="8 legacy snapshots / 12 center IDs; not the newer symC trajectory")
    ax.legend(fontsize=8); ax.grid(True, alpha=.3)
    fig.suptitle("Cryer load-matrix review: retained frozen algebra and static-patch evidence\n"
                 "A raw; B load only; C all terms with receiver C; D matched pair adjoint. No new trajectory.", fontsize=11)
    fig.savefig(products["png"], dpi=160); plt.close(fig)
    for e in inputs: assert entry(Path(e["path"])) == e
    result = dict(stage=args.output_prefix, passed=True, inputs=inputs, files=[entry(p) for p in products.values()],
                  rows=dict(schemes=len(scheme_rows), patch=len(patch_rows), history=len(history)),
                  source=entry(Path(__file__)), solver_decoder_build_or_production_edit=False,
                  new_operator_or_physical_accuracy_acceptance=False,
                  input_hashes_rechecked_after_analysis=True)
    with check.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps(dict(passed=True, receipt=str(check), rows=result["rows"])))


if __name__ == "__main__":
    main()
