"""Offline review of measured initial operator projections; never starts native code."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
import numpy as np
import scipy
from scipy.linalg import eig

T = Path(__file__).resolve().parents[1]
FAMILIES = ("vz", "sigma_zz", "p")
CHANNELS = ("az", "Rsigma_zz", "pdot", "theta", "pdot_noAce")
FEPS, DEPS = np.finfo("float32").eps, np.finfo("float64").eps


def need(test, message):
    if not test:
        raise ValueError(message)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))  # preserves distinct K/k keys


def entry(path):
    path = Path(path).resolve()
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            sha.update(block)
    return {"path": str(path), "bytes": path.stat().st_size, "sha256": sha.hexdigest()}


class Bindings:
    def __init__(self):
        self.seen = {}

    def add(self, ref):
        key = str(Path(ref["path"]).resolve()).lower()
        if key in self.seen:
            old = self.seen[key]
            need((old["bytes"], old["sha256"].lower()) == (ref["bytes"], ref["sha256"].lower()), "Conflicting consumed binding: "+key)
        else:
            got = entry(ref["path"])
            need((got["bytes"], got["sha256"]) == (ref["bytes"], ref["sha256"].lower()), "SHA/size mismatch: "+key)
            self.seen[key] = got

    def tree(self, value):
        if isinstance(value, dict):
            if {"path", "bytes", "sha256"} <= value.keys():
                self.add(value)
            else:
                for child in value.values():
                    self.tree(child)
        elif isinstance(value, list):
            for child in value:
                self.tree(child)

    def unchanged(self):
        for old in list(self.seen.values()):
            need(entry(old["path"]) == old, "Input changed during offline review: "+old["path"])


def budget(value):
    mag = np.maximum(1., value)
    return 64.*FEPS*mag + 256.*DEPS*mag  # unchanged producer arithmetic envelope


def roundtrip(got, ref, why):
    got, ref = np.asarray(got), np.asarray(ref)
    error = abs(got-ref)
    bound = 16.*DEPS*np.maximum(np.maximum(abs(got), abs(ref)), np.finfo("float64").tiny)
    need(np.isfinite(got).all() and np.isfinite(ref).all() and np.all(error <= bound), why)
    return float(np.max(error)) if error.size else 0.


def csv_rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def owned(mode, bindings):
    path = T/f"logs/upl_case02_operator_{mode}_r1.run.json"
    record = load(path)
    need(record["passed"] is True and record["exit_code"] == 0 and record["failure"] is None, "Owned component failed")
    for key in ("direct_native_call", "typed_LASTEXITCODE_captured_immediately", "owned_call_exited", "bindings_unchanged"):
        need(record[key] is True, "Missing direct/typed/unchanged evidence: "+key)
    need(record["mode"] == mode and record["physical_steps"] == 0 and not record["solver_trajectory_started"] and not record["physical_acceptance"], "Scope changed")
    for key in ("bindings", "files", "completion", "log", "program"):
        bindings.tree(record[key])
    helpers = [e for e in record["bindings"] if e["path"].endswith(".helper.json")]
    need(len(helpers) == 1, "Expected one bound helper receipt")
    helper = load(helpers[0]["path"])
    need(helper["passed"] is True and helper["kind"] == "operator" and helper["configuration"] == record["configuration"] and helper["CPU_non_main_objects"] == 85 and helper["link_object_count"] == 86 and helper["exact_link_closure_verified"] is True, "Helper/object contract differs")
    need(len(helper["source_snapshot"]) == 265 and len(helper["libraries"]) == 17 and len(helper["runtime"]) == 4 and helper["canonical_program_count"] == 7, "Source/library/runtime/canonical closure differs")
    for key in ("source_build", "author_files", "source_snapshot", "objects", "helper_object", "tools", "libraries", "runtime", "canonical_programs_before", "canonical_runtime_before"):
        bindings.tree(helper[key])
    args = record["arguments"]
    need(len(args) == 5 and args[0] == "--"+mode and args[1] == "--input" and args[3] == "--out", "Component argv differs")
    folder = Path(args[4])
    need(Path(record["completion"]["path"]).resolve() == (folder/"completion.json").resolve(), "Completion/argv path differs")
    bindings.add(entry(path))
    return record, load(folder/"completion.json"), folder, {"run": entry(path), "helper": helpers[0], "bindings": len(record["bindings"]), "output_files": len(record["files"])}


def responses(folder, mode, complete, B):
    count = 17 if mode == "smoke" else 601
    calls = {}
    max_spread, max_decomp_error = 0., 0.
    for row in csv_rows(folder/"responses.csv"):
        call, z = int(row["call"]), int(row["output_layer"])
        need(1 <= call <= count and 0 <= z < 100, "Response call/layer out of range")
        meta = (row["input_family"], int(row["input_layer"]), float(row["input_amplitude"]))
        if call not in calls:
            calls[call] = {"meta": meta, "mean": np.zeros((5, 100)), "seen": set()}
        item = calls[call]
        need(item["meta"] == meta and z not in item["seen"], "Duplicate/inconsistent response layer")
        item["seen"].add(z)
        mean, spread, peak, limit = [np.array([float(row[c+suffix]) for c in CHANNELS]) for suffix in ("_mean", "_column_spread", "_global_peak", "_arithmetic_budget")]
        need(np.isfinite(np.concatenate((mean, spread, peak, limit))).all() and np.all(spread >= 0) and np.all(peak >= 0), "Nonfinite/negative response statistics")
        need(np.array_equal(limit, budget(peak)), "Stored arithmetic budget differs from original formula")
        need(np.all(spread <= limit) and np.all(abs(mean) <= peak+limit), "Original spread/peak envelope failed")
        if "peak" in item:
            need(np.array_equal(item["peak"], peak), "Global peak differs between layers of one call")
        item["peak"], item["mean"][:, z] = peak, mean
        max_spread = max(max_spread, float(np.max(spread/limit)))
        comp = -B*mean[3]
        observed = [float(row[k]) for k in ("compression_from_theta", "pressure_noAce_component", "acceleration_component")]
        max_decomp_error = max(max_decomp_error, roundtrip(observed, [comp, mean[4]-comp, mean[2]-mean[4]], "Response decomposition changed"))
        need(float(row["wave_scale_s"]) > 0 and np.isfinite(float(row["wave_scale_s"])) and float(row["pore_scale_s"]) > 0 and np.isfinite(float(row["pore_scale_s"])), "Invalid recorded scales")
    need(sorted(calls) == list(range(1, count+1)) and all(len(q["seen"]) == 100 for q in calls.values()), "Response coverage incomplete")
    zero = calls[1]
    need(zero["meta"] == ("zero", -1, 0.) and np.all(zero["mean"] == 0) and np.all(zero["peak"] == 0), "Strict-zero source response failed")
    need(complete["actual_force_calls"] == count and complete["explicit_noAce_rate_calls"] == count and complete["response_rows"] == count*100, "Native force/row counters differ")
    roundtrip(max_spread, complete["max_column_spread_over_arithmetic_budget"], "Native spread summary differs")
    return calls, {"actual_force_calls": count, "explicit_noAce_calls": count, "response_rows": count*100, "independent_max_spread_ratio": max_spread, "max_decomposition_roundtrip_abs_error": max_decomp_error}


def projected(calls, folder, smoke, complete):
    amp_v = float(np.float32(.001))
    specs = [("vz", 99, amp_v), ("sigma_zz", 99, 1.), ("p", 99, 1.), ("p", 0, 1.)] if smoke else [(name, z, amp_v if name == "vz" else 1.) for name in FAMILIES for z in range(100)]
    linear = csv_rows(folder/"linearity.csv")
    need(len(linear) == len(specs), "Linearity coverage differs")
    Q, QB = np.empty((5, 100, len(specs))), np.empty((5, 100, len(specs)))
    max_odd = max_half = 0.
    for col, (family, layer, amp) in enumerate(specs):
        first = 2+(4 if smoke else 2)*col
        plus, minus = calls[first], calls[first+1]
        need(plus["meta"] == (family, layer, amp) and minus["meta"] == (family, layer, -amp), "Signed source order/amplitude differs")
        odd = float(np.max(abs(plus["mean"]+minus["mean"])/budget(np.maximum(plus["peak"], minus["peak"]))[:, None]))
        Q[:, :, col] = (plus["mean"]-minus["mean"])/(2*amp)
        QB[:, :, col] = ((budget(plus["peak"])+budget(minus["peak"]))/abs(2*amp))[:, None]
        half = 0.
        if smoke:
            hp, hm = calls[first+2], calls[first+3]
            need(hp["meta"] == (family, layer, amp*.5) and hm["meta"] == (family, layer, -amp*.5), "Half-amplitude source differs")
            derivative = (hp["mean"]-hm["mean"])/amp
            half = float(np.max(abs(Q[:, :, col]-derivative)/budget(np.maximum(abs(Q[:, :, col]), abs(derivative)))))
        need(odd <= 1. and half <= 1., "Original oddness/amplitude envelope failed")
        line = linear[col]
        need(int(line["column"]) == col and (line["input_family"], int(line["input_layer"]), float(line["amplitude"])) == (family, layer, amp), "Linearity source labels differ")
        roundtrip([odd, half], [float(line["max_odd_error_over_arithmetic_budget"]), float(line["max_half_amplitude_derivative_error_over_budget"])], "Stored linearity ratios differ")
        max_odd, max_half = max(max_odd, odd), max(max_half, half)
    roundtrip([max_odd, max_half], [complete["max_oddness_over_arithmetic_budget"], complete["max_half_amplitude_linearity_over_arithmetic_budget"]], "Native oddness/amplitude summaries differ")
    return Q, QB, {"basis_columns": len(specs), "independent_max_odd_ratio": max_odd, "independent_max_half_amplitude_ratio": max_half}


def measured_matrix(folder, Q):
    basis = csv_rows(folder/"basis.csv")
    need(len(basis) == 300, "Basis row count differs")
    for col, row in enumerate(basis):
        exact_amp = float(np.float32(.001)) if col < 100 else 1.
        need(int(row["column"]) == col and row["input_family"] == FAMILIES[col//100] and int(row["input_layer"]) == col%100, "Basis family/layer sorting differs")
        need(float(np.float32(float(row["amplitude"]))) == exact_amp, "Display-limited basis amplitude differs after float recovery")
    rows, theta = csv_rows(folder/"jacobian.csv"), csv_rows(folder/"theta_jacobian.csv")
    need(len(rows) == 300 and len(theta) == 100, "Matrix row counts differ")
    A = np.empty((300, 300))
    TH = np.empty((100, 300))
    for i, row in enumerate(rows):
        need(int(row["row"]) == i and row["output_family"] == CHANNELS[i//100] and int(row["output_layer"]) == i%100, "Jacobian row sorting differs")
        A[i] = [float(row[f"c{j}"]) for j in range(300)]
    for i, row in enumerate(theta):
        need(int(row["output_layer"]) == i, "Theta row sorting differs")
        TH[i] = [float(row[f"c{j}"]) for j in range(300)]
    expected = Q[:3].reshape(300, 300)
    error = roundtrip(A, expected, "Stored Jacobian differs from actual signed responses")
    therror = roundtrip(TH, Q[3], "Stored theta Jacobian differs from signed responses")
    return A, {"jacobian_values": A.size, "theta_values": TH.size, "max_jacobian_reconstruction_abs_error": error, "max_theta_reconstruction_abs_error": therror, "jacobian_reconstruction_bit_differences": int(np.count_nonzero(A.view("uint64") != expected.view("uint64"))), "basis_amplitude_is_display_limited": True}


def premise(got, ref, allowance):
    delta = got-ref
    return {"max_abs_difference": float(np.max(abs(delta))), "relative_Frobenius_difference": float(np.linalg.norm(delta)/max(np.linalg.norm(got), np.linalg.norm(ref), np.finfo("float64").tiny)), "max_difference_over_propagated_probe_envelope": float(np.max(abs(delta)/allowance))}


def spectrum(name, A, dt, dp):
    values, vectors = eig(A)
    need(np.isfinite(values).all(), "Nonfinite measured-projection eigenvalue")
    order = np.lexsort((values.imag, values.real))
    index = order[-1]
    lam, vector = values[index], vectors[:, index]
    denom = np.linalg.norm(A)*np.linalg.norm(vector)+abs(lam)*np.linalg.norm(vector)
    residual = float(np.linalg.norm(A@vector-lam*vector)/max(denom, np.finfo("float64").tiny))
    pressure = vector[200:]
    scale = float(max(abs(pressure)))
    if scale:
        vector = vector*np.exp(-1j*np.angle(pressure[np.argmax(abs(pressure))]))/scale
    else:
        vector = vector/max(abs(vector))
    gain = 1+dt*lam+.5*(dt*lam)**2
    summary = {"variant": name, "max_real_s-1": float(lam.real), "imag_rad_s": float(lam.imag), "top10_pressure_energy_fraction": float(np.sum(abs(pressure[-10:])**2)/np.sum(abs(pressure)**2)) if scale else None, "eigenpair_normwise_residual": residual, "formal_midpoint_growth_s-1": float(np.log(abs(gain))/dt), "formal_midpoint_frequency_rad_s": float(np.angle(gain)/dt)}
    eigen = [[name, rank, float(values[i].real), float(values[i].imag)] for rank, i in enumerate(order)]
    mode = [[name, i, (i+.5)*dp, *[float(q) for q in (vector[i].real, vector[i].imag, vector[100+i].real, vector[100+i].imag, vector[200+i].real, vector[200+i].imag)]] for i in range(100)]
    return summary, eigen, mode


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--out", type=Path, required=True)
    cli.add_argument("--csv-prefix", type=Path, required=True)
    args = cli.parse_args()
    paths = [args.out, Path(str(args.csv_prefix)+"_eigen.csv"), Path(str(args.csv_prefix)+"_mode.csv")]
    need(not any(p.exists() for p in paths), "Refusing to overwrite review outputs")
    bindings = Bindings()
    own = [entry(__file__), entry(T/"notes/upl_case02_operator_review_r1.json")]
    for ref in own:
        bindings.add(ref)
    frozen_path = T/"logs/upl_case02_frozen_matrix_r1.check.json"
    frozen = load(frozen_path)
    bindings.add(entry(frozen_path))
    need(frozen["analysis_completed"] and not frozen["physical_acceptance"] and not frozen["actual_CPP_Jacobian"] and not frozen["failed_trajectory_reclassified_as_passed"], "Nominal diagnostic scope differs")
    bindings.tree(frozen["files"])
    bindings.tree(frozen["current_formula_sources"])
    p = frozen["parameters"]  # Python JSON handles distinct K/k; no PS case folding.
    proofs, summaries, matrix_data = [], {}, None
    for name in ("smoke", "matrix"):
        record, complete, folder, proof = owned(name, bindings)
        xml = ET.parse(record["arguments"][2]).getroot()
        hydro = xml.find("execution/special/hydromechanics")
        n = float(np.float32(float(hydro.find("Porosity").attrib["value"])))
        Kw = float(np.float32(float(hydro.find("PoreWaterBulkModulus").attrib["value"])))
        need(n == p["n0"] and Kw == p["Kw"], "Nominal/measured material differs")
        for key in ("passed", "zero_source_strict_zero", "soil_inputs_force_unchanged", "frozen_C_and_classification_exact", "NoAce_scratch_restored_byte_exact", "wall_state_and_periodic_copies_from_production"):
            need(complete[key] is True, "Bound native assertion failed: "+key)
        need(complete["native_count"] == 1000 and complete["fixed_count"] == 40 and complete["layers"] == 100 and complete["columns_per_layer"] == 10 and complete["actual_time_s"] == 0 and complete["completed_physical_steps"] == 0 and not complete["Run_ComputeStep_SaveData_called"] and not complete["physical_acceptance"], "Component/native scope differs")
        calls, numbers = responses(folder, name, complete, Kw/n)
        Q, QB, central = projected(calls, folder, name == "smoke", complete)
        need(complete["basis_columns"] == central["basis_columns"] and complete["periodic_owner_checks"] > 0, "Native basis/ghost count differs")
        if name == "smoke":
            need(complete["matrix_rows"] == 0 and complete["matrix_columns"] == 0, "Smoke unexpectedly claims a full matrix")
        summaries[name] = {**numbers, **central, "native_asserted_periodic_owner_checks": complete["periodic_owner_checks"]}
        if name == "matrix":
            A, detail = measured_matrix(folder, Q)
            need(complete["matrix_rows"] == 300 and complete["matrix_columns"] == 300, "Native matrix dimensions differ")
            summaries[name].update(detail)
            matrix_data = (A, Q[4], QB)
        proofs.append(proof)
    A, N, QB = matrix_data
    BA = QB[:3].reshape(300, 300)
    premises = {"raw_pressure_equals_negative_stress_H": premise(A[:100, 200:], -A[:100, 100:200], BA[:100, 200:]+BA[:100, 100:200]),
                "noAce_sigma_block_zero": premise(N[:, 100:200], np.zeros((100, 100)), QB[4, :, 100:200]),
                "velocity_pressure_block_unchanged_by_NoAce": premise(A[200:, :100], N[:, :100], BA[200:, :100]+QB[4, :, :100]),
                "acceleration_pressure_equals_negative_sigma_block": premise(A[200:, 200:]-N[:, 200:], -(A[200:, 100:200]-N[:, 100:200]), BA[200:, 200:]+QB[4, :, 200:]+BA[200:, 100:200]+QB[4, :, 100:200])}
    noA, compatible = A.copy(), A.copy()
    noA[200:, :] = N
    compatible[200:, 200:] = (p["rho0"]/p["rhow"]-1.)*A[200:, 100:200]
    spectral, eigen_rows, mode_rows = [], [], []
    for name, matrix in (("actual_measured_projection", A), ("diagnostic_actual_NoAce", noA), ("diagnostic_compatible_pressure_block", compatible)):
        s, er, mr = spectrum(name, matrix, p["dt"], p["dp"])
        spectral.append(s); eigen_rows.extend(er); mode_rows.extend(mr)
    nominal = next(s for s in frozen["spectral_diagnostics"] if s["variant"] == "modeled_current")
    fit_path = next(Path(e["path"]) for e in frozen["files"] if e["path"].endswith("_fit.csv"))
    fit_rows = csv_rows(fit_path)
    need(len(fit_rows) == 72, "Frozen fit CSV coverage differs")
    comparisons = []
    for fit in frozen["independent_CSV_fits"]:
        rows = [r for r in fit_rows if r["field"] == fit["field"]]
        need([int(r["part"]) for r in rows] == list(range(20, 56)), "Frozen fit part window differs")
        observed, fitted = [np.array([float(r[key]) for r in rows]) for key in ("observed", "fitted")]
        R2 = float(1-np.sum((fitted-observed)**2)/np.sum((observed-observed.mean())**2))
        roundtrip(R2, fit["R_squared"], "Frozen CSV/JSON fit quality differs")
        comparisons.append({"field": fit["field"], "CSV_recomputed_R_squared": R2, "CSV_fit_growth_s-1": fit["growth_s-1"], "CSV_fit_omega_rad_s": fit["omega_rad_s"], "fit_minus_actual_formal_midpoint_growth_s-1": fit["growth_s-1"]-spectral[0]["formal_midpoint_growth_s-1"], "fit_minus_actual_semidiscrete_frequency_rad_s": fit["omega_rad_s"]-abs(spectral[0]["imag_rad_s"]), "fit_minus_actual_formal_midpoint_frequency_rad_s": fit["omega_rad_s"]-abs(spectral[0]["formal_midpoint_frequency_rad_s"])})
    bindings.unchanged()
    headers = [["variant", "rank_real_then_imag", "real_s-1", "imag_rad_s"], ["variant", "layer", "nominal_z_m", "v_real", "v_imag", "sigma_real", "sigma_imag", "p_real", "p_imag"]]
    for path, header, rows in zip(paths[1:], headers, (eigen_rows, mode_rows)):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream); writer.writerow(header); writer.writerows(rows)
    result = {"stage": "upl_case02_operator_review_r1", "passed": True, "physical_acceptance": False, "native_program_started": False, "manufactured_projection_not_trajectory_or_full_CPP_Jacobian": True, "failed_short_trajectory_reclassified_as_passed": False, "proofs": proofs, "independent_CSV_checks": summaries, "diagnostic_premises_reported_not_assumed": premises, "spectral_diagnostics": spectral, "actual_minus_nominal_max_real_s-1": spectral[0]["max_real_s-1"]-nominal["max_real_s-1"], "actual_minus_nominal_abs_frequency_rad_s": abs(spectral[0]["imag_rad_s"])-abs(nominal["imag_rad_s"]), "independent_frozen_diagnostic": entry(frozen_path), "CSV_fit_comparison_display_clock_only": comparisons, "unique_file_bindings_rehashed_before_after": len(bindings.seen), "author_files": own, "files": [entry(path) for path in paths[1:]], "versions": {"Python": sys.version, "numpy": np.__version__, "scipy": scipy.__version__}, "limitations": ["Native rollback/C/ghost bits are sealed producer assertions, not independently reconstructible from layer means; no second BI4 parser.", "Global peaks/spreads are exported statistics, not all ten individual responses; only original exported arithmetic envelopes and central-difference consistency are recomputed.", "CSV arithmetic identity replay permits16 DBL_EPS relative roundtrip error only; original spread/oddness/amplitude gates remain exactly <=1 with their unchanged64FLT_EPS+256DBL_EPS envelopes.", "basis.csv amplitude has limited default stream precision; actual responses/linearity amplitudes, not its printed .001, normalize derivatives.", "Eigenvalues concern the finite-amplitude100-layer measured projection, not every particle mode, evolved coefficients or physical/integrator stability.", "NoAce and compatible-pressure replacements are conditional diagnostic counterfactuals, not recommended physical changes.", "Fit times remain diagnostic CSV display labels, not decoded binary TimeStep; no new half/drainage/continuum/public admission."]}
    paths[0].parent.mkdir(parents=True, exist_ok=True)
    with paths[0].open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps({"passed": True, "physical_acceptance": False, "out": str(paths[0])}))


if __name__ == "__main__":
    main()
