"""Seal the bounded canonical CPU entry review, not a physical-model release.

No compiler, program, solver, Git operation, or retained-output modification.
The post-test documentation update is explicitly separate from tested code.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

T = Path(__file__).resolve().parents[1]
L = T / "logs"
OUT = L / "upl_cpu_public_stage_r1.check.json"


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def entry(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def verify(rows):
    for row in rows:
        need(entry(row["path"]) == row, "Changed sealed file: " + row["path"])


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def main():
    need(not OUT.exists(), "Final stage record retained; do not overwrite")
    freeze = load(L / "upl_cpu_public_build_r3.json")
    need(freeze["msbuild_exit_codes"] == {"DebugCPU": 0, "ReleaseCPU": 0}
         and len(freeze["source"]) == 7, "Authoritative full CPU Rebuild required")
    build_doc = None
    for row in freeze["source"]:
        verify([row["snapshot"]])
        if Path(row["original"]["path"]).suffix in (".cpp", ".h"):
            verify([row["original"]])
        else:
            need(build_doc is None, "More than one build document")
            build_doc = row
    verify(freeze["programs"])
    verify(freeze["inputs"])
    verify(freeze["logs"])
    verify([row["snapshot"] for row in freeze["prior_programs"]])
    independent_path = L / "upl_cpu_public_independent_r1.check.json"
    independent = load(independent_path)
    need(independent["passed"] and independent["identity_mismatches"] == 0
         and len(independent["jobs"]) == 9 and len(independent["half_recomputed"]) == 3
         and len(independent["rejections"]) == 11
         and independent["default_OFF_native_frame_pairs"] == 140,
         "Complete independent canonical/off/rejection review required")
    verify(independent["input_receipts"])
    plan = load(L / "upl_cpu_public_r1.inputs.json")
    checks = [independent_path, L / "upl_cpu_public_build_r3.json",
              L / "upl_cpu_public_off_r2.check.json", L / "upl_cpu_public_OFF_r1.exact.check.json"]
    for job in plan["jobs"]:
        for kind in ("solver", "review"):
            path = L / ("upl_cpu_public_" + job["label"] + "_r1." + kind + ".check.json")
            check = load(path)
            need(check["passed"], "Canonical job not passed: " + job["label"])
            verify(check["files"])
            checks.append(path)
    for pair in ("periodic_constant", "wall_constant", "wall_evolving"):
        path = L / ("upl_cpu_public_" + pair + "_r1.half.check.json")
        half = load(path)
        need(half["passed"], "Independent original half bound failed")
        verify(half["files"])
        checks.append(path)
    for row in independent["rejections"]:
        path = L / ("upl_cpu_public_reject_r1_" + row["label"] + ".run.json")
        negative = load(path)
        need(negative["passed"] and negative["exit_code"] != 0
             and negative["native_PART_count"] == 0 and negative["target_guard_reached"],
             "Invalid XML did not reach its target guard")
        verify(negative["files"])
        verify([negative["log"]])
        checks.append(path)
    part_path = L / "upl_cpu_public_part_r1.check.json"
    part = load(part_path)
    need(part["passed"] and part["canonical_rejections"] == 3
         and part["false_scalar_copy_verified"]
         and part["real_OFF_loader_positive_control_passed"]
         and not part["coupled_restart_acceptance"], "Three genuine PART guards required")
    verify(part["files"])
    checks.append(part_path)
    comparison_path = L / "upl_cpu_public_compare_r1.check.json"
    comparison = load(comparison_path)
    need(comparison["passed"]
         and not comparison["preregistered_full_raw26_equivalence_gate_passed"]
         and comparison["audited_evolved_samples1_to256_all26_equivalence_passed"]
         and not comparison["any_raw_field_masked"]
         and not comparison["thresholds_relaxed"],
         "Offline comparison must preserve the failed complete raw-bit gate explicitly")
    verify(comparison["inputs"])
    verify(comparison["outputs"])
    checks.append(comparison_path)
    doc = entry(build_doc["original"]["path"])
    status = T.parent.parent / "validation" / "upl_current_status.json"
    # Do not re-label a historical document hash as a tested binary input.
    # All six code files and seven immutable build snapshots were checked above.
    result = {
        "passed": True,
        "utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Bounded canonical CPU XML wiring, output, default-OFF and rejection review only",
        "physical_acceptance": False,
        "formal_or_general_upl_release": False,
        "tested_code_files": 6,
        "tested_code_unchanged_since_full_Rebuild_r3": True,
        "source_snapshots": [row["snapshot"] for row in freeze["source"]],
        "documentation_at_build": build_doc["snapshot"],
        "documentation_after_build_reviewed": True,
        "documentation_after_build": doc,
        "documentation_note": "Post-test status prose only; not represented as a new compiled source input",
        "checks": [entry(path) for path in checks],
        "canonical_jobs": independent["jobs"],
        "canonical_native_frames": independent["total_canonical_native_frames"],
        "dynamic_soil_records": independent["actual_dynamic_soil_records"],
        "half_recomputed": independent["half_recomputed"],
        "invalid_XML_guards": 11,
        "genuine_PART_rejections": 3,
        "default_OFF_exact_frame_pairs": 140,
        "complete_private_raw26_equivalence_passed": False,
        "private_initial_and_wall_flux_gates_inherited": False,
        "raw_comparison_note": "The strict full-257-frame private raw-bit comparison is not met: initial PosDiv refresh and periodic signed zeros differ. Retain its false result; no blanket 26-field equivalence or inherited wall-flux acceptance. See the separate actual-time/native-ID comparison receipt. Canonical native/half/safety gates above stand independently.",
        "next": "Private GPU state lifecycle first; public GPU rejection stays until its separate complete model tests pass",
        "limitations": "Fresh CPU 2D, zero gravity, weak elastic periodic/opposing static FreeSlip planes only. No new gravity/load/drainage, general wall, plasticity, conservative-interface, asymptotic stability, exact restart, GPU or formal physical acceptance.",
        "raw_BI4_and_executable_cloud_backup_claimed": False,
        "recipe": entry(__file__),
        "stage_note": entry(T / "notes" / "upl_cpu_public_stage_r1.md"),
        "current_status": entry(status),
    }
    with OUT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print("SEALED limited canonical CPU stage, not full physical acceptance: " + str(OUT))


if __name__ == "__main__":
    main()
