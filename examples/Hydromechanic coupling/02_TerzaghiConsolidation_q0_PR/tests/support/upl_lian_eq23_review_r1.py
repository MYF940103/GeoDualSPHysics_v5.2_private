"""Offline readout of the sealed Eq23 manufactured diagnostic; no operator execution."""
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

# Limit only this offline Python process; never alter another process or user settings.
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

T = Path(__file__).resolve().parents[1]
NAME, SOURCE = "upl_lian_eq23_review_r1", "upl_lian_eq23_operator_r1"
D = T / "outputs" / SOURCE
PINS = {"logs/upl_lian_eq23_operator_r1.run.json": (18180, "117652e8ed8e47cde712fdb650154796478162d4dbd25437d9e1d8b867f86bf1"),
        "support/upl_lian_eq23_operator_r1.cpp": (16395, "a44bb3693eb985046ee5a4adfea9b4639f990dc87172896f979a1ef087e6d2c0"),
        "notes/upl_lian_eq23_operator_r1.json": (8406, "f99ff237b750178b4322b5d76c0060a1bf4a081c9f27ed184770c0a3349abe4b")}
VARIANTS = ("literal_receiver_C_r2", "receiver_C_Eta2", "pair_C_Eta2", "pair_C_Eta2_tangent_Neumann")
LABELS = ("Literal receiver C, r²", "Receiver C, r²+η²", "Pair C, r²+η²", "Pair C + tangent projection")
COLORS = ("#174a7e", "#dc8a21", "#21825a", "#a05290")
CLOUDS = ("ordered", "fixed_jitter_008dp")
REGIONS = ("interior", "truncated")
FIELDS = ("1", "x", "z", "x2", "xz", "z2", "cos2pi_x")
BOUND = {}


def need(ok, why):
    if not bool(ok):
        raise ValueError(why)


def entry(path):
    path = Path(path).resolve(strict=True)
    with path.open("rb") as stream:
        h = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=h)


def bind(e):
    key = str(Path(e["path"]).resolve()).casefold()
    if key not in BOUND:
        BOUND[key] = entry(e["path"])
    a = BOUND[key]
    need((a["bytes"], a["sha256"]) == (e["bytes"], e["sha256"].lower()), "Consumed input changed: " + e["path"])
    return Path(a["path"])


def adopt(path):
    e = entry(path)
    bind(e)
    return e


def read(e):
    return json.loads(bind(e).read_text(encoding="utf-8-sig"))


def same(a, b):
    return (str(Path(a["path"]).resolve()).casefold(), a["bytes"], a["sha256"]) == (
        str(Path(b["path"]).resolve()).casefold(), b["bytes"], b["sha256"])


def owned(e, stage):
    c = read(e)
    need(c.get("stage") == stage and c.get("direct_native_call") is True and c.get("owned_call_exited") is True and
         c.get("typed_returncode_captured_immediately") is True and type(c.get("exit_code")) is int and
         c["exit_code"] == 0 and c.get("invocation_failure") is None, "Original owned integer exit0 required")
    bind(c["program"])
    if c.get("log"):
        bind(c["log"])
    return c


def rows(e):
    with bind(e).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        need(reader.fieldnames and len(set(reader.fieldnames)) == len(reader.fieldnames), "CSV header invalid")
        return list(reader)


def write_csv(path, data):
    with path.open("x", encoding="utf-8", newline="") as stream:
        w = csv.DictWriter(stream, fieldnames=list(data[0]))
        w.writeheader()
        w.writerows(data)


def provenance():
    pinned = {}
    for name, (size, sha) in PINS.items():
        e = dict(path=str(T / name), bytes=size, sha256=sha)
        bind(e)
        pinned[name] = e
    run = read(pinned["logs/" + SOURCE + ".run.json"])
    build = read(run["source_build"])
    call = owned(run["call"], SOURCE + ".call")
    compile_call = owned(build["compile_call"], SOURCE + ".Compile")
    link_call = owned(build["link_call"], SOURCE + ".Link")
    need(run.get("passed") is True and build.get("passed") is True and build["project_objects_linked"] == 0 and
         same(run["program"], build["program"]) and same(call["program"], run["program"]) and
         call["arguments"] == [str(D)] and same(build["source"], pinned["support/" + SOURCE + ".cpp"]) and
         same(build["note"], pinned["notes/" + SOURCE + ".json"]), "Standalone source/build/run association differs")
    need("/O2" in compile_call["arguments"] and "/fp:precise" in compile_call["arguments"] and
         [a for a in link_call["arguments"] if a.lower().endswith(".obj")] == [build["object"]["path"]],
         "Actual standalone optimized single-object link required")
    for e in [build["program"], build["object"], build["compiler_dependencies"], *build["actual_archived_headers"]]:
        bind(e)
    dependency = read(build["compiler_dependencies"])["Data"]
    archive = T / "outputs/upl_hg_column_ReleaseCPU_r1_source"
    need(all(Path(e["path"]).resolve().parent == archive.resolve() for e in build["actual_archived_headers"]) and
         not any(Path(p).resolve().is_relative_to(T.parents[3] / "src/source") for p in dependency["Includes"]),
         "Archived project include closure required, never current mutable source")
    files = {Path(e["path"]).name: e for e in run["files"]}
    need(set(files) == {"completion.json", "fields.csv", "moments.csv", "periodic_matrix.csv", "periodic_diagnostics.csv"} and
         all(Path(e["path"]).resolve().parent == D.resolve() for e in files.values()) and
         same(run["completion"], files["completion.json"]), "Exact sealed diagnostic output membership required")
    done = read(run["completion"])
    expected = dict(stage=SOURCE, dimension=2, constant_k=True, J=1, manufactured_receivers=3712,
        exact_constant_checks=29696, affine_forward_bound_checks=51968, matched_trace_forward_bound_checks=185600,
        periodic_matrix_nodes=64, periodic_matrices=6, basic_arithmetic_checks_passed=True,
        quadratic_or_smooth_accuracy_threshold_applied=False, Eq23_discrete_accuracy_accepted=False, physical_acceptance=False)
    need(all(done.get(k) == v for k, v in expected.items()), "Original basic coverage/limited claims differ")
    for e in files.values():
        bind(e)
    return run, build, call, compile_call, link_call, done, files


def accuracy(moment_rows, field_rows):
    groups, moment_summary = {}, []
    need(len(moment_rows) == 3712 and len(field_rows) == 600, "Declared CSV counts differ")
    for cloud in CLOUDS:
        for nx in (16, 24, 32):
            cloud_rows = [r for r in moment_rows if r["cloud"] == cloud and int(r["nx"]) == nx]
            need(len(cloud_rows) == nx * nx and sorted(int(r["receiver"]) for r in cloud_rows) == list(range(nx * nx)), "Receiver identity coverage differs")
            for region in REGIONS:
                a = [r for r in cloud_rows if r["region"] == region]
                need(a, "Empty original region")
                groups[(cloud, nx, region)] = a
                inverse = []
                for r in a:
                    x, z = float(r["x"]), float(r["z"])
                    interior = min(x, z, 1 - x, 1 - z) >= float(np.float32(2 * float(r["h"])))
                    need(interior == (region == "interior"), "Actual support classification differs")
                    m = np.asarray([[float(r[k]) for k in ("Mxx", "Mxz")], [float(r[k]) for k in ("Mzx", "Mzz")]])
                    c = np.asarray([[float(r[k]) for k in ("Cxx", "Cxz")], [float(r[k]) for k in ("Czx", "Czz")]])
                    need(np.isfinite(m).all() and np.isfinite(c).all(), "Nonfinite moment/inverse")
                    inverse.append(float(np.linalg.norm(c @ m - np.eye(2), np.inf)))
                moment_summary.append(dict(cloud=cloud, nx=nx, region=region, receivers=len(a),
                    neighbors_min=min(int(r["neighbors"]) for r in a), neighbors_max=max(int(r["neighbors"]) for r in a),
                    condition_inf_max=max(float(r["condition_inf"]) for r in a), independently_recomputed_inverse_residual_inf_max=max(inverse),
                    corrected_affine_residual_inf_max=max(float(r["corrected_affine_residual_inf"]) for r in a)))
    output, unique = [], set()
    for source in field_rows:
        cloud, nx, region, field, variant, storage = (source[k] for k in ("cloud", "nx", "region", "field", "variant", "pressure_storage"))
        nx = int(nx)
        key = cloud, nx, region, field, variant, storage
        need(key not in unique and field in FIELDS and variant in VARIANTS, "Duplicate/unknown field case")
        unique.add(key)
        a = groups[(cloud, nx, region)]
        need(int(source["receivers"]) == len(a) and bool(int(source["affine_forward_bound_applicable"])) == (field in ("x", "z")), "Field-region coverage differs")
        truth = {"x2": (2., 0., 0.), "xz": (0., 1., 0.), "z2": (0., 0., 2.)}.get(field, (0., 0., 0.))
        exact = np.asarray([(-4 * math.pi ** 2 * math.cos(2 * math.pi * float(r["x"])), 0., 0.) if field == "cos2pi_x" else truth for r in a])
        tensor_truth = float(np.sqrt(np.mean(exact[:, 0] ** 2 + 2 * exact[:, 1] ** 2 + exact[:, 2] ** 2)))
        trace_truth = float(np.sqrt(np.mean((exact[:, 0] + exact[:, 2]) ** 2)))
        row = dict(source)
        tensor_error = math.sqrt(sum(float(source[k]) ** 2 * w for k, w in (("Hxx_error_RMS", 1), ("Hxz_error_RMS", 2), ("Hzz_error_RMS", 1))))
        row.update(tensor_Frobenius_error_RMS=tensor_error, analytic_tensor_Frobenius_RMS=tensor_truth,
            relative_tensor_Frobenius_error=tensor_error / tensor_truth if tensor_truth else None,
            analytic_trace_RMS=trace_truth, relative_scalar_expression_error=float(source["scalar_expression_error_RMS"]) / trace_truth if trace_truth else None,
            observed_order_tensor_from_previous_grid=None, observed_order_scalar_from_previous_grid=None)
        need(all(math.isfinite(float(v)) for k, v in source.items() if k not in ("cloud", "pressure_storage", "field", "variant", "region")), "Nonfinite original aggregate")
        if field == "1":
            need(tensor_error == 0 and float(source["scalar_expression_error_RMS"]) == 0, "Original constant field is not exact null")
        output.append(row)
    for r in output:
        nx = int(r["nx"])
        if nx == 16:
            continue
        prev_nx = 16 if nx == 24 else 24
        p = next(p for p in output if all(p[k] == r[k] for k in ("cloud", "region", "field", "variant", "pressure_storage")) and int(p["nx"]) == prev_nx)
        for metric, target in (("tensor_Frobenius_error_RMS", "observed_order_tensor_from_previous_grid"), ("scalar_expression_error_RMS", "observed_order_scalar_from_previous_grid")):
            x, y = float(p[metric]), float(r[metric])
            r[target] = math.log(x / y) / math.log(float(p["dp"]) / float(r["dp"])) if x > 0 and y > 0 else None
    return output, moment_summary


def spectra(matrix_rows, diagnostic_rows):
    need(len(matrix_rows) == 384 and len(diagnostic_rows) == 6, "Six64x64 matrices required")
    result, summaries = [], []
    for cloud in CLOUDS:
        for variant in VARIANTS[:3]:
            rows_ = sorted((r for r in matrix_rows if r["cloud"] == cloud and r["variant"] == variant), key=lambda r: int(r["row"]))
            need([int(r["row"]) for r in rows_] == list(range(64)), "Matrix row identity differs")
            a = np.asarray([[float(r["a" + str(j)]) for j in range(64)] for r in rows_])
            need(np.isfinite(a).all(), "Nonfinite matrix")
            d = next(r for r in diagnostic_rows if r["cloud"] == cloud and r["variant"] == variant)
            s = (a + a.T) / 2
            lam, u = np.linalg.eigh(s)
            eig, vectors = np.linalg.eig(a)
            ix = np.lexsort((eig.imag, eig.real))
            eig, vectors = eig[ix], vectors[:, ix]
            norm2, norm_inf, fro = float(np.linalg.norm(a, 2)), float(np.linalg.norm(a, np.inf)), float(np.linalg.norm(a, "fro"))
            rowmax, colmax = float(np.abs(a @ np.ones(64)).max()), float(np.abs(np.sum(a, axis=0)).max())
            resid_s = np.linalg.norm(s @ u - u * lam, axis=0)
            resid_a = np.linalg.norm(a @ vectors - vectors * eig, axis=0) / np.linalg.norm(vectors, axis=0)
            indicator = 64 * np.finfo(float).eps / (1 - 64 * np.finfo(float).eps) * norm2
            summary = dict(cloud=cloud, variant=variant, n=64, A_norm2=norm2, A_norm_inf=norm_inf,
                A_real_eigen_min=float(eig.real.min()), A_real_eigen_max=float(eig.real.max()), A_imag_eigen_abs_max=float(np.abs(eig.imag).max()),
                symmetric_part_eigen_min=float(lam[0]), symmetric_part_eigen_max=float(lam[-1]),
                symmetric_part_max_positive_over_roundoff_indicator=max(0., float(lam[-1])) / indicator,
                eigen_roundoff_indicator_not_a_physical_gate=indicator, symmetric_part_eigen_residual2_max=float(resid_s.max()),
                A_eigen_residual2_max=float(resid_a.max()), asymmetry_Frobenius_relative=float(np.linalg.norm(a - a.T, "fro") / fro),
                antisymmetry_abs_max=float(np.abs(a - a.T).max()), reconstructed_constant_row_residual_inf=rowmax,
                volume_weighted_column_residual_inf=float(d["V"]) * colmax,
                row_residual_relative=rowmax / norm_inf, column_residual_relative=colmax / norm_inf,
                cpp_row_sum_abs_max=float(d["row_sum_abs_max"]), cpp_volume_weighted_column_sum_abs_max=float(d["volume_weighted_column_sum_abs_max"]),
                cpp_Frobenius_minus_numpy=float(d["Frobenius_norm"]) - fro, matrix_storage_bytes=int(d["matrix_storage_bytes"]),
                source_cumulative_matrix_wall_seconds=float(d["cumulative_matrix_wall_seconds"]))
            summaries.append(summary)
            for i in range(64):
                result.append(dict(summary, sorted_rank=i, A_eigen_real=float(eig[i].real), A_eigen_imag=float(eig[i].imag),
                    symmetric_part_eigenvalue=float(lam[i]), A_eigen_residual2=float(resid_a[i]), symmetric_part_eigen_residual2=float(resid_s[i])))
    return result, summaries


def figures(error_rows, spectrum_rows, matrix_summary, errors_png, spectra_png):
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "savefig.dpi": 170})
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 8.1), sharex=True)
    for ri, region in enumerate(REGIONS):
        for fi, field in enumerate(("x2", "xz", "cos2pi_x")):
            ax = axes[ri, fi]
            for vi, variant in enumerate(VARIANTS):
                for ci, cloud in enumerate(CLOUDS):
                    a = sorted((r for r in error_rows if r["region"] == region and r["field"] == field and r["variant"] == variant and
                                r["cloud"] == cloud and r["pressure_storage"] == "double_manufactured_pressure"), key=lambda r: float(r["dp"]))
                    if a:
                        ax.plot([float(r["dp"]) for r in a], [r["relative_tensor_Frobenius_error"] for r in a],
                                color=COLORS[vi], linestyle="-" if ci == 0 else "--", marker="o" if ci == 0 else "s", ms=4, lw=1.5)
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.grid(True, which="both", alpha=.2)
            ax.set_title(region.capitalize() + " · " + {"x2": "$p=x^2$", "xz": "$p=xz$", "cos2pi_x": r"$p=\cos(2\pi x)$"}[field])
            ax.set_xticks([1 / 32, 1 / 24, 1 / 16], ["1/32", "1/24", "1/16"])
            if fi == 0:
                ax.set_ylabel("Relative Hessian Frobenius RMS error")
            if ri == 1:
                ax.set_xlabel("Particle spacing Δp (unit square)")
    handles = [Line2D([], [], color=COLORS[i], label=LABELS[i], lw=2) for i in range(4)] + [
        Line2D([], [], color="#444444", marker="o", label="Ordered", lw=1.5),
        Line2D([], [], color="#444444", marker="s", linestyle="--", label="Fixed jitter ±0.08Δp", lw=1.5)]
    fig.legend(handles=handles, loc="lower center", ncol=3, bbox_to_anchor=(.5, .015), frameon=False)
    fig.suptitle("Literal 2D Eq23 diagnostic: tensor error versus spacing", fontsize=16, y=.98)
    fig.text(.5, .925, "Double pressure inputs · h=float(1.8Δp) · full/truncated receiver supports · no accuracy threshold", ha="center")
    fig.subplots_adjust(top=.86, bottom=.19, hspace=.34, wspace=.25)
    fig.savefig(errors_png)
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 8.4))
    ax, sx, skew, null = axes.ravel()
    labels, asym, row, col = [], [], [], []
    for ci, cloud in enumerate(CLOUDS):
        for vi, variant in enumerate(VARIANTS[:3]):
            a = [r for r in spectrum_rows if r["cloud"] == cloud and r["variant"] == variant]
            m = next(r for r in matrix_summary if r["cloud"] == cloud and r["variant"] == variant)
            marker, style = ("o", "-") if ci == 0 else ("x", "--")
            ax.scatter([r["A_eigen_real"] / m["A_norm2"] for r in a], [r["A_eigen_imag"] / m["A_norm2"] for r in a],
                       marker=marker, s=18, color=COLORS[vi], alpha=.65)
            sx.plot(range(64), [r["symmetric_part_eigenvalue"] / m["A_norm2"] for r in a], color=COLORS[vi], linestyle=style,
                    label=("Ordered" if ci == 0 else "Jitter") + " · " + LABELS[vi])
            labels.append(("Ordered" if ci == 0 else "Jitter") + "\n" + ("literal", "receiver η", "pair η")[vi])
            asym.append(m["asymmetry_Frobenius_relative"])
            row.append(m["row_residual_relative"])
            col.append(m["column_residual_relative"])
    ax.axvline(0, color="#555555", lw=.7)
    ax.axhline(0, color="#777777", lw=.6)
    ax.set(title="Full nonsymmetric A eigenvalues", xlabel="Re(λ)/‖A‖₂", ylabel="Im(λ)/‖A‖₂")
    sx.axhline(0, color="#555555", lw=.7)
    sx.set(title="Symmetric part S=(A+Aᵀ)/2", xlabel="Sorted eigenvalue index", ylabel="λ(S)/‖A‖₂")
    inset = sx.inset_axes([.10, .52, .37, .36])
    for line in sx.lines[:-1]:
        inset.plot(line.get_xdata()[-2:], line.get_ydata()[-2:], color=line.get_color(), linestyle=line.get_linestyle(), marker=".")
    inset.axhline(0, color="#555555", lw=.5)
    inset.set_title("Largest two", fontsize=8)
    inset.tick_params(labelsize=7)
    x = np.arange(6)
    skew.bar(x, asym, color=[COLORS[i % 3] for i in range(6)])
    skew.set(title="Relative matrix asymmetry", ylabel="‖A−Aᵀ‖F / ‖A‖F", xticks=x, xticklabels=labels)
    null.bar(x - .17, row, .34, label="Coefficient row residual", color="#356f9c")
    null.bar(x + .17, col, .34, label="Column conservation residual", color="#c78531")
    null.set(title="Reconstructed coefficients: null versus conservation", ylabel="Residual / ‖A‖∞", xticks=x, xticklabels=labels)
    for a in (skew, null):
        a.set_yscale("symlog", linthresh=np.finfo(float).eps)
        a.tick_params(axis="x", labelsize=8)
    null.legend(fontsize=8, frameon=False)
    for a in axes.ravel():
        a.grid(True, alpha=.17)
    fig.suptitle("Six 64-node periodic matrices: algebraic diagnostics", fontsize=16, y=.98)
    fig.text(.5, .925, "Full A and S spectra are distinct · exact source constant-input null does not imply column conservation", ha="center")
    fig.legend(*sx.get_legend_handles_labels(), loc="lower center", ncol=3, bbox_to_anchor=(.5, .005), fontsize=9, frameon=False)
    fig.subplots_adjust(top=.86, bottom=.16, hspace=.40, wspace=.29)
    fig.savefig(spectra_png)
    plt.close(fig)


def main():
    started = time.perf_counter()
    targets = [T / "figures" / (NAME + suffix) for suffix in ("_errors.csv", "_spectra.csv", "_errors.png", "_spectra.png")]
    record = T / "logs" / (NAME + ".check.json")
    need(all(not p.exists() for p in targets + [record]), "Fresh review artifacts required")
    result = dict(stage=NAME, passed=False, review_completed=False, created_utc=datetime.now(timezone.utc).isoformat(),
                  solver_build_or_operator_executed=False, Eq23_discrete_accuracy_accepted=False, physical_acceptance=False, failure=None)
    try:
        for p in (__file__, T / "notes" / (NAME + ".json"), sys.executable, np.__file__, matplotlib.__file__):
            adopt(p)
        run, build, call, cc, lc, done, files = provenance()
        error_rows, moments = accuracy(rows(files["moments.csv"]), rows(files["fields.csv"]))
        spectrum_rows, matrices = spectra(rows(files["periodic_matrix.csv"]), rows(files["periodic_diagnostics.csv"]))
        write_csv(targets[0], error_rows)
        write_csv(targets[1], spectrum_rows)
        figures(error_rows, spectrum_rows, matrices, targets[2], targets[3])
        finest = [{k: r[k] for k in ("cloud", "region", "field", "Hxx_mean", "Hxz_mean", "Hzz_mean", "tensor_Frobenius_error_RMS",
                   "relative_tensor_Frobenius_error", "relative_scalar_expression_error", "observed_order_tensor_from_previous_grid")}
                  for r in error_rows if r["variant"] == VARIANTS[0] and r["pressure_storage"] == "double_manufactured_pressure" and
                  int(r["nx"]) == 32 and r["field"] in ("x2", "xz", "z2", "cos2pi_x")]
        affine = [r for r in error_rows if r["field"] in ("x", "z")]
        result.update(passed=True, review_completed=True, field_rows=600, moment_rows=3712, spectrum_rows=384,
            source_run=adopt(T / "logs" / (SOURCE + ".run.json")), source_completion=run["completion"], source_build=run["source_build"],
            original_basic_arithmetic_checks=done, literal_finest_double_pressure=finest, moment_summary=moments, periodic_matrices=matrices,
            affine_double_tensor_RMS_max=max(float(r["tensor_Frobenius_error_RMS"]) for r in affine if r["pressure_storage"] == "double_manufactured_pressure"),
            affine_float_tensor_RMS_max=max(float(r["tensor_Frobenius_error_RMS"]) for r in affine if r["pressure_storage"] == "production_float_pressure"),
            pressure_quantization_max=max(float(r["input_float_quantization_max"]) for r in error_rows),
            original_affine_ratio_max=max(float(r["affine_roundoff_ratio_max"]) for r in error_rows),
            original_tensor_scalar_trace_ratio_max=max(float(r["matched_trace_roundoff_ratio_max"]) for r in error_rows),
            cost=dict(source_program_wall_seconds=done["wall_seconds"], owned_process_wall_seconds=call["wall_seconds"],
                compile_seconds=cc["wall_seconds"], link_seconds=lc["wall_seconds"], input_csv_bytes=sum(e["bytes"] for n, e in files.items() if n.endswith(".csv")),
                six_dense_matrix_double_storage_bytes=sum(m["matrix_storage_bytes"] for m in matrices)),
            software=dict(python=sys.version, numpy=np.__version__, matplotlib=matplotlib.__version__),
            accuracy_gate_added=False, convergence_order_accepted=False, general_Neumann_acceptance=False,
            notes="All variants/storage modes and raw errors remain in CSV. Apparent orders use absolute RMS ratios, changing receiver regions and only three spacings. Eigenvalue roundoff indicator is numerical scale, not a physical threshold; no nonsymmetric stability proof.")
    except Exception as exc:
        result["failure"] = str(exc)
        result["passed"] = False
    try:
        for e in list(BOUND.values()):
            a = entry(e["path"])
            need((a["bytes"], a["sha256"]) == (e["bytes"], e["sha256"]), "Input changed during independent final rehash")
        result["independent_final_rehash_performed"] = True
    except Exception as exc:
        result["independent_final_rehash_performed"] = result["passed"] = False
        result["failure"] = (result["failure"] + "; " if result["failure"] else "") + str(exc)
    result.update(inputs=list(BOUND.values()), files=[entry(p) for p in targets if p.exists()], offline_wall_seconds=time.perf_counter() - started)
    with record.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(dict(passed=result["passed"], receipt=str(record), failure=result["failure"])))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
