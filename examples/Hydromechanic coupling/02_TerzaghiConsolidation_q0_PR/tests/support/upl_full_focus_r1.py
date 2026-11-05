"""Show late accuracy and stress differences without changing full-history evidence."""
import csv
import hashlib
import json
import os
from pathlib import Path

for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"
T = Path(__file__).resolve().parents[1]
NAME = "upl_full_focus_r1"


def entry(path):
    with path.open("rb") as stream:
        sha = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(path=str(path.resolve()), bytes=path.stat().st_size, sha256=sha)


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(path, data):
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]))
        writer.writeheader(); writer.writerows(data)


def main():
    import psutil
    psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    products = {s: T/"figures"/(NAME+"."+s) for s in ("history.csv", "final_stress.csv", "png")}
    check = T/"logs"/(NAME+".check.json")
    assert not any(p.exists() for p in [*products.values(), check]), "Retained products protected"
    rp = T/"logs/upl_bigstep_full_r1.review.json"
    assert entry(rp)["sha256"] == "5613343b5675bc6e6378ccd7c446b68f84c3fd2b72a5f548e69203259adf5bfc"
    review = json.loads(rp.read_text(encoding="utf-8-sig"))
    cp = T/"logs/upl_full_upw_compare_r1.check.json"
    comparison = json.loads(cp.read_text(encoding="utf-8-sig"))
    assert review["passed"] and comparison["passed"] and comparison["source_full_review"] == entry(rp)
    inputs = [entry(rp), entry(cp), *review["files"], *comparison["files"]]
    old = T.parent/"figures/full_validation_release_k1em4_GPU_history.csv"
    assert entry(old)["sha256"] == "78da4b0b43efcb4f69135d9082763ca1e7d951b94a6681ef1727687e883749fd"
    inputs.append(entry(old))
    for e in inputs: assert entry(Path(e["path"])) == e
    full_files = {Path(e["path"]).name: Path(e["path"]) for e in review["files"]}
    compare_files = {Path(e["path"]).name: Path(e["path"]) for e in comparison["files"]}
    h = rows(compare_files["upl_full_upw_compare_r1.history.csv"])
    theory = {float(r["time_s"]): r for r in rows(full_files["upl_bigstep_full_r1.theory.csv"])}
    old_rows = rows(old); output = []
    for r in h:
        current = r["series"].startswith("current")
        t = float(r["time_s"]); tv = float(r["actual_Tv"])
        a, b = float(r["top_settlement_mm"]), float(r["bottom_settlement_mm"])
        ref = theory.get(t) if current else None
        old_ref = None if current else old_rows[int(r["part"])]
        classical_a = float(ref["H1_classical_material_top_settlement_mm"]) if ref else float(old_ref["classical_top_mm"]) if old_ref else None
        classical_b = float(ref["H1_classical_material_bottom_settlement_mm"]) if ref else float(old_ref["classical_bottom_mm"]) if old_ref else None
        output.append(dict(series=r["series"], part=int(r["part"]), time_s=t, actual_Tv=tv,
            mean_pressure_Pa=float(r["mean_pressure_pa"]), top_settlement_mm=a, bottom_settlement_mm=b,
            H1_classical_top_error_um=1000*(a-classical_a) if classical_a is not None else None,
            H1_classical_bottom_error_um=1000*(b-classical_b) if classical_b is not None else None,
            H1_finite_top_error_um=1000*(a-float(ref["H1_finite_Kw_material_top_settlement_mm"])) if ref else None,
            H1_finite_same_node_mean_pressure_Pa=float(ref["H1_finite_Kw_same_node_mean_P_Pa"]) if ref else None,
            Q_Pa=float(r["Q_pa"]), max_layer_total_error_Pa=float(r["max_layer_total_error_pa"]),
            top_gap_Pa=float(r["top_gap_pa"]), in_late_Tv_window=int(tv>=1), in_post_point1_window=int(t>=.1-1e-7)))
    assert len(output) == 8972
    last = []
    with full_files["upl_bigstep_full_r1.layers.csv"].open(encoding="utf-8", newline="") as stream:
        for r in csv.DictReader(stream):
            if int(r["part"]) == 1681:
                total = float(r["total_sigma_zz_mean_Pa"])
                last.append(dict(initial_layer=int(r["initial_layer"]), z0_m=float(r["z0_m"]),
                    time_s=float(r["time_s"]), total_sigma_zz_Pa=total, signed_total_stress_residual_Pa=total+10000))
    assert len(last) == 100
    write(products["history.csv"], output); write(products["final_stress.csv"], last)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), constrained_layout=True)
    for series, label in (("current_upl_CPU1_FreeSlip3", "u-pl CPU / FreeSlip"), ("retained_upw_GPU_Vel0_1", "u-pw GPU / Vel0")):
        rr = [r for r in output if r["series"] == series]
        late = [r for r in rr if r["in_late_Tv_window"]]
        post = [r for r in rr if r["in_post_point1_window"]]
        axes[0, 0].plot([r["actual_Tv"] for r in late], [r["mean_pressure_Pa"] for r in late], label=label)
        axes[0, 1].plot([r["actual_Tv"] for r in late], [r["H1_classical_top_error_um"] for r in late], label=label)
        axes[0, 2].plot([r["actual_Tv"] for r in late], [r["H1_classical_bottom_error_um"] for r in late], label=label)
        axes[1, 0].plot([r["time_s"] for r in post], [r["Q_Pa"] for r in post], label=label)
        axes[1, 1].plot([r["time_s"] for r in post], [r["max_layer_total_error_Pa"] for r in post], label=label)
        if series.startswith("current"):
            axes[0, 0].plot([r["actual_Tv"] for r in late], [r["H1_finite_same_node_mean_pressure_Pa"] for r in late], "k:", label="H1 finite Kw / same IDs")
            axes[0, 1].plot([r["actual_Tv"] for r in late], [r["H1_finite_top_error_um"] for r in late], "--", color=".4", label="u-pl vs H1 finite Kw")
    labels = (("Mean pressure (Pa)", "Late dissipation", "Each source's actual Tv"),
        ("Top settlement minus reference (um)", "Own-time H1 classical reference", "Each source's actual Tv"),
        ("Bottom settlement minus reference (um)", "Own-time H1 classical reference", "Each source's actual Tv"),
        ("Q = RMS layer stress second difference (Pa)", "Post-0.1s spatial stress variation", "Actual saved time (s)"),
        ("Maximum layer total-stress error (Pa)", "Old 100Pa criterion shown for comparison", "Actual saved time (s)"))
    for ax, (ylabel, title, xlabel) in zip(axes.flat, labels):
        ax.set(ylabel=ylabel, xlabel=xlabel, title=title); ax.grid(True); ax.legend(fontsize=7)
    axes[1, 1].axhline(100, color="C3", ls=":", label="Old 100Pa criterion"); axes[1, 1].legend(fontsize=7)
    ax = axes[1, 2]
    ax.plot([r["signed_total_stress_residual_Pa"] for r in last], [r["z0_m"] for r in last], "o-", ms=2)
    for x in (-100, 100): ax.axvline(x, color="C3", ls=":", lw=1)
    ax.set(xlabel="sigma_total_zz + q0 (Pa)", ylabel="Original material z0 (m)", title="u-pl final layer stress residual"); ax.grid(True)
    fig.suptitle("Full-history evidence retained separately; explicit late/post-0.1s views\n"
                 "Different formulation/wall/backend/step. No interpolation, fitted reference, or relaxed criterion.", fontsize=11)
    fig.savefig(products["png"], dpi=160); plt.close(fig)
    for e in inputs: assert entry(Path(e["path"])) == e
    result = dict(stage=NAME, passed=True, inputs=inputs, files=[entry(p) for p in products.values()],
                  rows=dict(history=len(output), final_stress=len(last)), script=entry(Path(__file__)),
                  views_are_explicit_subsets_not_replacements_for_full_history=True,
                  solver_or_decoder_invoked=False, old_100Pa_criterion_relaxed=False, physical_acceptance=False)
    with check.open("x", encoding="utf-8") as stream: json.dump(result, stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps(dict(passed=True, receipt=str(check))))


if __name__ == "__main__":
    main()
