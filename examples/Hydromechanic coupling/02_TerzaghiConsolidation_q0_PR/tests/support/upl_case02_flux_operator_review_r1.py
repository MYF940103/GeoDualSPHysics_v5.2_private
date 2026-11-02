"""Offline raw comparison of two measured case02 operator projections; no physical admission."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

T = Path(__file__).resolve().parents[1]
DEPENDENCIES = {
    "support/upl_case02_operator_review_r1.py": "b7ce64ac74ce3d8baa8ad03b98b604cc709a754e68554c204458ebdf5ffb2c42",
    "notes/upl_case02_operator_review_r1.json": "9749fd208fb59b3780aa4b173000eea6c9bde3c40ab7ea3760a59db9c3a6b544",
}
for leaf, sha in DEPENDENCIES.items():
    if hashlib.sha256((T/leaf).read_bytes()).hexdigest() != sha:
        raise RuntimeError("Immutable pure-function dependency changed: "+leaf)
from upl_case02_operator_review_r1 import (Bindings, entry, load, need, csv_rows, responses,
                                          projected, measured_matrix, spectrum, np, scipy)


def ownership(record, mode):
    need(record["passed"] is True and record["mode"] == mode and type(record["exit_code"]) is int
         and record["exit_code"] == 0 and record["failure"] is None, "Owned operator did not pass")
    for key in ("direct_native_call", "typed_LASTEXITCODE_captured_immediately", "owned_call_exited", "bindings_unchanged"):
        need(record[key] is True, "Owned-call evidence missing: "+key)
    need(record["physical_steps"] == 0 and not record["solver_trajectory_started"]
         and not record["physical_acceptance"], "Not a zero-step manufactured operator")


def current(mode, bindings):
    path = T/f"logs/upl_case02_flux_operator_{mode}_r1.run.json"
    record = load(path); ownership(record, mode); bindings.add(entry(path))
    for key in ("bindings", "files", "program", "log", "completion"):
        bindings.tree(record[key])  # Current candidate originals and snapshots really are current.
    refs = [ref for ref in record["bindings"] if ref["path"].endswith(".helper.json")]
    need(len(refs) == 1, "Expected one current operator helper")
    helper = load(refs[0]["path"])
    need(helper["passed"] is True and helper["kind"] == "operator" and helper["configuration"] == record["configuration"]
         and helper["CPU_non_main_objects"] == 85 and helper["link_object_count"] == 86
         and helper["exact_link_closure_verified"] is True and len(helper["source_snapshot"]) == 265,
         "Current operator/helper closure differs")
    for key in ("source_build", "author_files", "source_snapshot", "documentation_snapshot", "objects",
                "helper_object", "tools", "libraries", "runtime", "canonical_programs_before", "canonical_runtime_before"):
        if key in helper:
            bindings.tree(helper[key])
    args = record["arguments"]
    need(len(args) == 5 and args[0] == "--"+mode and args[1] == "--input" and args[3] == "--out", "Current operator argv differs")
    folder = Path(args[4])
    need(Path(record["completion"]["path"]).resolve() == (folder/"completion.json").resolve(), "Current output attribution differs")
    return record, load(folder/"completion.json"), folder, helper, {"run": entry(path), "helper": refs[0], "flat_bindings_verified": len(record["bindings"]), "files_verified": len(record["files"])}


def retained(review, bindings):
    proof = next(q for q in review["proofs"] if q["run"]["path"].endswith("_matrix_r1.run.json"))
    bindings.add(proof["run"]); bindings.add(proof["helper"])
    record, helper = load(proof["run"]["path"]), load(proof["helper"]["path"])
    ownership(record, "matrix")
    for key in ("files", "program", "log", "completion"):
        bindings.tree(record[key])
    bindings.tree(helper["author_files"])
    bindings.tree(helper["source_build"])  # Bind receipt bytes, not its former current originals.
    for pair in helper["source_snapshot"]:
        bindings.add(pair["snapshot"])  # Deliberately NEVER bind pair.original for the old build.
    need(len(helper["source_snapshot"]) == 265 and helper["kind"] == "operator" and helper["passed"] is True,
         "Retained operator source-snapshot proof differs")
    args = record["arguments"]
    need(len(args) == 5 and args[0] == "--matrix" and args[1] == "--input" and args[3] == "--out", "Retained argv differs")
    xml = next(q for q in record["bindings"] if Path(q["path"]).resolve() == Path(args[2]).resolve())
    bindings.add(xml)
    return record, load(record["completion"]["path"]), Path(args[4]), helper, proof


def native_mask(bindings):
    """Actual sealed old Part0 typed export, not a nominal geometry-only FS guess."""
    path = T/"logs/upl_case02_smoke_r1.native.check.json"
    qc_path = T/"logs/upl_case02_smoke_r1.qc.json"
    qc = load(qc_path); bindings.add(entry(qc_path))
    need(qc["passed"] is True and qc["mode"] == "smoke" and qc["physical_acceptance"] is False,
         "Retained independent smoke QC missing")
    native_ref = next(ref for ref in qc["inputs"] if Path(ref["path"]).resolve() == path.resolve())
    bindings.add(native_ref); check = load(path)
    need(check["passed"] is True and check["job"] == "smoke" and check["source_solver_exit_verified"] is True,
         "Retained initial native proof missing")
    bindings.add(check["completion"])
    selected = {Path(ref["path"]).name: ref for ref in check["files"]}
    for name in ("physical.bin", "native_ids.csv", "columns.csv"):
        bindings.add(selected[name])
    columns = csv_rows(selected["columns.csv"]["path"])
    need(len(columns) == 26 and columns[17]["name"] == "FSType", "Not the original case02 private26 FS field")
    ids = csv_rows(selected["native_ids.csv"]["path"])
    need(len(ids) == 1000 and [int(r["id"]) for r in ids] == list(range(40, 1040)), "Initial mask ID ordering differs")
    blob = Path(selected["physical.bin"]["path"]).read_bytes()
    need(struct.unpack("<III", blob[:12]) == (1000, 26, 3), "Initial mask physical schema differs")
    frame = np.dtype([("time", "<f8"), ("x", "<f8", (1000, 26))])
    need(len(blob) == 12+3*frame.itemsize, "Initial mask export length differs")
    first = np.frombuffer(blob, dtype=frame, count=3, offset=12)[0]
    need(first["time"] == 0 and np.isfinite(first["x"]).all(), "Not finite actual Part0")
    z = np.array([float(r["z0"]) for r in ids])
    need(np.array_equal(z, first["x"][:, 2]), "Part0/ID material z differs")
    layer = np.rint(z/.01-.5).astype(int)
    active = np.isin(first["x"][:, 17], (2., 3.))
    layers = sorted(set(layer[active].tolist()))
    need(layers == [99] and int(active.sum()) == 10, "Declared actual top99 mask differs")
    return layers, {"native_check": entry(path), "source": "sealed actual Part0 private26 FSType column17",
                    "active_native_ids": [int(ids[i]["id"]) for i in np.flatnonzero(active)],
                    "active_layers": layers, "active_count": int(active.sum())}


def probe(record, complete, folder, mode, B):
    for key in ("passed", "zero_source_strict_zero", "soil_inputs_force_unchanged", "frozen_C_and_classification_exact", "NoAce_scratch_restored_byte_exact"):
        need(complete[key] is True, "Native operator assertion failed: "+key)
    need(complete["actual_time_s"] == 0 and complete["completed_physical_steps"] == 0
         and complete["native_count"] == 1000 and complete["fixed_count"] == 40
         and complete["physical_acceptance"] is False, "Operator component scope differs")
    calls, summary = responses(folder, mode, complete, B)
    Q, QB, central = projected(calls, folder, mode == "smoke", complete)
    need(complete["basis_columns"] == central["basis_columns"] and complete["periodic_owner_checks"] > 0,
         "Basis/owner counters differ")
    summary.update(central)
    if mode == "smoke":
        need(complete["matrix_rows"] == 0 and complete["matrix_columns"] == 0, "Smoke claims full matrix")
        return None, summary
    need(complete["matrix_rows"] == 300 and complete["matrix_columns"] == 300, "Matrix dimensions differ")
    A, detail = measured_matrix(folder, Q); summary.update(detail)
    return A, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--csv-prefix", type=Path, required=True)
    args = parser.parse_args()
    targets = [args.out, Path(str(args.csv_prefix)+"_eigen.csv"), Path(str(args.csv_prefix)+"_mode.csv")]
    need(not any(p.exists() for p in targets), "Fresh flux review outputs required")
    bindings = Bindings()
    for leaf in (*DEPENDENCIES.keys(), "support/upl_case02_flux_operator_review_r1.py", "notes/upl_case02_flux_operator_review_r1.json"):
        bindings.add(entry(T/leaf))
    old_path = T/"logs/upl_case02_operator_review_r1.check.json"
    old_ref = entry(old_path)
    need(old_ref["sha256"] == "f60b28eea71f44bf39c30c470e7740d2010b6ae447b2e69b148bc9bb9eb28ba2", "Retained sealed review changed")
    bindings.add(old_ref); old_review = load(old_path)
    need(old_review["passed"] is True and old_review["physical_acceptance"] is False, "Retained review not passed/limited")
    bindings.tree(old_review["files"]); bindings.tree(old_review["author_files"])
    bindings.add(old_review["independent_frozen_diagnostic"])
    nominal = load(old_review["independent_frozen_diagnostic"]["path"])
    bindings.tree(nominal["files"])  # No old nominal current_formula_sources originals are rebound.
    p = nominal["parameters"]
    old_record, old_done, old_folder, old_helper, old_proof = retained(old_review, bindings)
    old_A, old_numbers = probe(old_record, old_done, old_folder, "matrix", p["B"])
    new_proofs, new_numbers, new_A, new_record = [], {}, None, None
    for mode in ("smoke", "matrix"):
        record, done, folder, helper, proof = current(mode, bindings)
        need(entry(record["arguments"][2])["sha256"] == entry(old_record["arguments"][2])["sha256"],
             "New/retained operator runtime XML differs")
        A, numbers = probe(record, done, folder, mode, p["B"])
        new_proofs.append(proof); new_numbers[mode] = numbers
        if mode == "matrix":
            new_A, new_record = A, record
    layers, mask_proof = native_mask(bindings)
    omitted = [200+i for i in layers]
    keep = np.ones(300, dtype=bool); keep[omitted] = False
    delta = new_A-old_A
    bits = new_A.view("uint64") != old_A.view("uint64")
    row_report = [{"row": i, "family": ("az", "Rsigma_zz", "pdot")[i//100], "layer": i%100,
                   "actual_initial_FS_pdot_row": i in omitted, "bit_differences": int(bits[i].sum()),
                   "numeric_differences": int(np.count_nonzero(delta[i])), "max_abs_difference": float(max(abs(delta[i])))} for i in range(300)]
    spectra, eigen_rows, mode_rows = [], [], []
    for name, A in (("flux_candidate_measured_projection", new_A), ("retained_pre_flux_measured_projection", old_A)):
        summary, values, modes = spectrum(name, A, p["dt"], p["dp"])
        spectra.append(summary); eigen_rows.extend(values); mode_rows.extend(modes)
    fit_comparison = [{"field": f["field"], "retained_CSV_fit_growth_s-1": f["CSV_fit_growth_s-1"],
                       "retained_CSV_fit_omega_rad_s": f["CSV_fit_omega_rad_s"],
                       "fit_minus_candidate_formal_growth_s-1": f["CSV_fit_growth_s-1"]-spectra[0]["formal_midpoint_growth_s-1"],
                       "fit_minus_candidate_abs_frequency_rad_s": f["CSV_fit_omega_rad_s"]-abs(spectra[0]["imag_rad_s"])}
                      for f in old_review["CSV_fit_comparison_display_clock_only"]]
    bindings.unchanged()
    headers = [["variant", "rank_real_then_imag", "real_s-1", "imag_rad_s"],
               ["variant", "layer", "nominal_z_m", "v_real", "v_imag", "sigma_real", "sigma_imag", "p_real", "p_imag"]]
    import csv
    for target, header, rows in zip(targets[1:], headers, (eigen_rows, mode_rows)):
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream); writer.writerow(header); writer.writerows(rows)
    result = {"stage": "upl_case02_flux_operator_review_r1", "passed": True, "physical_acceptance": False,
              "native_program_started": False, "new_owned_proofs": new_proofs, "retained_control_review": old_ref,
              "retained_control_proof": old_proof, "new_probe_recomputation": new_numbers,
              "retained_probe_recomputation": old_numbers, "actual_initial_FS_mask": mask_proof,
              "non_top_pdot_row_count": int(keep.sum()), "non_top_pdot_rows_bit_exact": bool(not bits[keep].any()),
              "non_top_pdot_rows_numeric_exact": bool(not np.any(delta[keep])),
              "non_top_pdot_bit_differences": int(bits[keep].sum()),
              "non_top_pdot_max_abs_difference": float(np.max(abs(delta[keep]))),
              "all300_rows_raw_comparison_not_a_new_gate": row_report, "spectral_diagnostics": spectra,
              "candidate_minus_retained_max_real_s-1": spectra[0]["max_real_s-1"]-spectra[1]["max_real_s-1"],
              "retained_nominal_model_spectrum_descriptive": nominal["spectral_diagnostics"],
              "retained_failed_run_fit_comparison_display_clocks_only": fit_comparison,
              "retained_source_snapshots_verified": len(old_helper["source_snapshot"]),
              "retained_source_current_originals_rehashed": False,
              "unique_consumed_files_verified_before_after": len(bindings.seen),
              "files": [entry(p) for p in targets[1:]], "versions": {"numpy": np.__version__, "scipy": scipy.__version__},
              "limitations": ["No call to old owned() or mutation/monkeypatch of imported module globals.",
                              "Old source originals are expected to have changed; only retained source snapshots/metadata and old actual output files are verified.",
                              "Current flat run/helper source265 originals and snapshots are actually rehashed; no same-source claim across candidates.",
                              "Same immutable measured-fixture finite amplitudes and projection, not a full C++ Jacobian or trajectory.",
                              "All299 non-top-pdot row equality is a raw report, never a new pass threshold; negative/nonpositive eigenvalues are not physical admission.",
                              "No new q_n proof,half/drain/affine/constitutive/long-time/public/GPU acceptance; no nominal matrix is claimed as modified CPP truth.",
                              "Retained CSV fits keep display/nominal time caveat. Original failed trajectory remains failed."]}
    targets[0].parent.mkdir(parents=True, exist_ok=True)
    with targets[0].open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write("\n")
    print(json.dumps({"passed": True, "physical_acceptance": False, "out": str(targets[0])}))


if __name__ == "__main__":
    main()
