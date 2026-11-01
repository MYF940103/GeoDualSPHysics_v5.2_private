"""Seal the reviewed private time-policy stage, without executing solvers."""
import json
from pathlib import Path

from upl_p3_perm_time_periodic_review_r1 import TESTS, LOGS, entry, read, verify


def main():
    target = LOGS / "upl_p3_perm_time_stage_r1.check.json"
    assert not target.exists(), "Retained stage receipt protected"
    leaves = ["upl_p3_perm_time_off_r1.check.json",
              "upl_p3_perm_time_DebugCPU_r1.check.json",
              "upl_p3_perm_time_ReleaseCPU_r1.check.json",
              "upl_p3_perm_time_periodic_r1_repair.check.json",
              "upl_p3_perm_time_wall_ReleaseCPU_r2.check.json"]
    checks, bindings = {}, []
    for leaf in leaves:
        path = LOGS / leaf
        check = read(path)
        assert check["passed"], leaf
        verify(check.get("files", []))
        for row in check.get("exact_files", []):
            verify([row["retained"], row["current"]])
            assert row["byte_identical"]
        bindings.append(entry(path))
        checks[leaf] = check
    off = checks[leaves[0]]
    assert off["actual_native_frame_pairs"] == 140 and off["all_bits_0ULP"]
    for group in off["groups"]:
        verify([group["check"]])
        saved = read(group["check"]["path"])
        assert saved["passed"]
        verify(saved.get("files", []))
    independent_path = TESTS / "notes" / "upl_p3_perm_time_independent_r1.json"
    independent = read(independent_path)
    assert independent["passed"] and not independent["physical_acceptance"]
    for row in independent["evidence"]:
        now = entry(TESTS / row["path"])
        assert now["bytes"] == row["bytes"] and now["sha256"] == row["sha256"]
    bindings.append(entry(independent_path))
    wall = checks[leaves[-1]]
    assert wall["solver_jobs"] == 2 and wall["native_ids"] == 1024
    assert wall["matched_samples_per_job"] == 257 and wall["columns"] == 26
    verify(wall["receipts"])
    for row in wall["receipts"]:
        owned = read(row["path"])
        assert owned["exit_code"] == 0 and owned["owned_call_exited"]
        verify([owned["program"], owned["build"], owned["log"]])
    verify([wall["half"]])
    half_wall = read(wall["half"]["path"])
    assert half_wall["passed"]
    result = dict(
        passed=True, scope="Private CPU smooth conductivity necessary time guard and exact integration regression",
        source_changes=["src/source/JSphCpu.h", "src/source/JSphCpu.cpp"],
        source_purpose="Reuse same-pass GJ for a padded thread-local maximum speed; add Safety*h/maxuk to DtVariable. No new neighbor pass or rate arithmetic.",
        default_OFF_native_frame_pairs=140, default_OFF_all15_arrays_clock_step_dterror_exact=True,
        configurations=["DebugCPU", "ReleaseCPU"], cache_cases_per_configuration=40,
        actual_DtVariable_cases_per_configuration=64, expected_rejections_per_configuration=32,
        actual_periodic_and_wall_solver_jobs=4, native_records_bitwise_exact=789504,
        native26_field_values_bitwise_exact=20527104,
        periodic_half=checks[leaves[-2]]["independent_half_metrics"], wall_half=half_wall,
        reviewed_checks=bindings,
        retained_wrapper_failures=[
            "Initial default-OFF companion invocation omitted its required build-confirmation flag and exited before build/run; corrected explicit invocation used the unused fresh label.",
            "Periodic r1 completed both actual jobs and the half comparator; empty stdout left no Tee log and prevented only the comparator receipt. Offline NumPy and exact-byte review adopted the completed results without rerunning or fabricating a historical log.",
            "First Wall r2 precheck saw both Raw and corrected seed pairs. No build/program ran. Original unbuilt wrapper/note archived in outputs/upl_p3_perm_time_wrapper_precheck_r1; recipe now selects exactly the same corrected CaseUplWall runtime seeds as the retained control."],
        figures="Existing periodic/wall comparison figures remain applicable because complete numerical CSV/physical results are byte-identical; no duplicate plots produced.",
        gradient_bound_never_dominant_inferred=False, necessary_not_sufficient_stability=True,
        public_XML_or_GPU_or_formal_release=False, physical_acceptance=False,
        raw_binary_ledger_executable_cloud_backup_claimed=False)
    result["files"] = bindings + [entry(__file__), entry(Path(__file__).with_name("upl_p3_perm_time_periodic_review_r1.py"))]
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(passed=True, receipt=str(target), raw_fields_exact=20527104)))


if __name__ == "__main__":
    main()
