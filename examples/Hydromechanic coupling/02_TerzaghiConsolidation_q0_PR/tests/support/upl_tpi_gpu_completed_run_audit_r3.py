"""Offline-only, independently admitted review of one preserved GPU checker failure.

This cannot invoke a program, reader, solver, compiler, Git, or another action.
It does not alter the failed run/status or claim native/physical acceptance.
"""
from __future__ import annotations
import argparse
import ast
import csv
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import upl_tpi_gpu_run_r3 as r

c, T, L = r.c, r.T, r.L
TAG = "upl_tpi_gpu_completed_run_audit_r3"
FAILED_TAG = "upl_tpi_gpu_Debug_B_debug2steps_r1"
FAILED_REASON = "Actual GPU normal finish/steps/no-exclusion differs"
FAILURE_KIND = "preserved_r1_postcheck_wrong_mode_and_Hardware_case_only"
MODE = 'RunMode="Stable - Pos-Cell - Single-GPU"'
BAD_MODE = 'RunMode="Stable - Pos-Double - Single-GPU"'
SCRIPT = Path(__file__).resolve()
NOTE = T / "notes" / (TAG + ".md")
OLD_SCRIPT = T / "support/upl_tpi_gpu_run_r1.py"
OLD_NOTE = T / "notes/upl_tpi_gpu_run_r1.md"
REVIEW = L / (FAILED_TAG + ".completed_run_review_r3.json")
PREVIOUS = L / (FAILED_TAG + ".completed_run_review_r2.json")
PREVIOUS_SCRIPT = T / "support/upl_tpi_gpu_completed_run_audit_r2.py"
PREVIOUS_NOTE = T / "notes/upl_tpi_gpu_completed_run_audit_r2.md"
PREVIOUS_FAILURE = "Actual GPU Run.csv metadata differs"


class Admission(c.Admission):
    def __init__(self, path):
        self.entry = c.stat(path)
        self.data = c.read(path)
        c.need(self.data.get("stage") == TAG + ".audit_admission" and
               self.data.get("passed") is True and self.data.get("audit_only") is True and
               self.data.get("tag") == FAILED_TAG,
               "One exact completed-run offline audit admission required")
        self.frozen = {str(Path(x["path"]).resolve()): x for x in self.data["inputs"]}
        self.consumed = {}
        for p in (SCRIPT, NOTE, PREVIOUS_SCRIPT, PREVIOUS_NOTE, PREVIOUS, OLD_SCRIPT, OLD_NOTE, Path(r.__file__), r.NOTE, Path(c.__file__)):
            self.pin(p)


def check_only_two_classifier_patches():
    old = ast.parse(OLD_SCRIPT.read_text(encoding="utf-8-sig"))
    new = ast.parse(Path(r.__file__).read_text(encoding="utf-8-sig"))
    oldfn = next(x for x in old.body if isinstance(x, ast.FunctionDef) and x.name == "check_output")
    newfn = next(x for x in new.body if isinstance(x, ast.FunctionDef) and x.name == "check_output")
    mode_replaced, hardware_replaced = 0, 0
    for node in ast.walk(oldfn):
        if isinstance(node, ast.Constant) and node.value == BAD_MODE:
            node.value = MODE
            mode_replaced += 1
        if (isinstance(node, ast.Compare) and len(node.ops) == len(node.comparators) == 1 and
                isinstance(node.ops[0], ast.In) and isinstance(node.left, ast.Constant) and node.left.value == "GPU"):
            node.left = ast.Constant(value="gpu")
            node.comparators[0] = ast.Call(func=ast.Attribute(value=node.comparators[0], attr="lower", ctx=ast.Load()), args=[], keywords=[])
            hardware_replaced += 1
    c.need(mode_replaced == hardware_replaced == 1 and
           ast.dump(oldfn, include_attributes=False) == ast.dump(newfn, include_attributes=False),
           "Corrected checker must differ from frozen r1 only in actual mode and Hardware case classifiers")


def same_entry(ad, entry):
    ad.pin(entry["path"])
    return c.same(entry)


def stat_fields(entry):
    # Build receipts may carry an already-recorded SHA as extra provenance.
    # Identity/stat equality uses exactly the admitted fields; no re-hash.
    return {key: entry[key] for key in ("path", "bytes", "mtime_ns")}


def previous_failure(ad):
    failed = c.read(PREVIOUS)
    c.need(failed.get("stage") == "upl_tpi_gpu_completed_run_audit_r2.audit" and
           failed.get("passed") is False and failed.get("failure") == PREVIOUS_FAILURE and
           failed.get("solver_invocations") == failed.get("reader_invocations") == failed.get("build_invocations") == 0,
           "Original failed offline audit must remain preserved as diagnostic evidence")
    same_entry(ad, failed["root_admission"])
    return c.stat(PREVIOUS)


def actual_identity(start, call, run, program):
    c.need(call.get("passed") is True and call.get("failure") is None and
           call.get("actual_Popen_wait_exit") == call.get("actual_Win32_exit") ==
           call.get("target_actual_Win32_exit") == 0 and
           run.get("actual_Popen_wait_exit") == run.get("actual_Win32_exit") ==
           run.get("target_actual_Win32_exit") == 0 and
           call.get("target_handle_acquired_before_wait") is True,
           "Original target/tool genuine handle exits were not successful")
    c.need(call["owner"] == start["owner"] and call["child"] == start["tool"] and
           call["target"] == start["target"] == run["target"] and
           start["tool"]["parent"] == start["owner"]["pid"] and
           start["target"]["parent"] == start["tool"]["pid"],
           "Original owner/tool/target identity or parent chain differs")
    for kind, who in (("tool", call["child"]), ("target", call["target"])):
        ticks = call[kind + "_creation_FILETIME_ticks"]
        c.need(abs((ticks - 116444736000000000) / 1e7 - who["created"]) <= 1e-6,
               "Original native creation time differs: " + kind)
    expected_args = ["-gpu", "-stable", "-mdbc_freeslip", str(c.PREFIX),
                     run["output_directory"], "-dirdataout", "data", "-svres", "-tmax:0.14999999", "-nsteps:2"]
    c.need(run["arguments"] == start["arguments"] == call["target_arguments"] == expected_args and
           call["target"]["argv"] == [str(program), *expected_args] and
           Path(call["target"]["exe"]).resolve() == program and
           call.get("tool_is_solver") is False,
           "Original actual GPU target argv/executable/profile differs")
    tool = Path(call["program"]["path"]).resolve()
    expected_tool = ["--tool", "memcheck", "--error-exitcode", "86", "--leak-check", "full",
                     "--target-processes", "all", "--log-file", str(L / (FAILED_TAG + ".memcheck.log")),
                     str(program), *expected_args]
    c.need(tool.name.lower() == "compute-sanitizer.exe" and
           Path(call["child"]["exe"]).resolve() == tool and
           call["arguments"] == expected_tool and call["child"]["argv"] == [str(tool), *expected_tool],
           "Original actual sanitizer program/argv differs")


def review_completed(ad):
    old_failure = previous_failure(ad)
    paths = {x: L / (FAILED_TAG + "." + x + ".json") for x in ("run", "start", "call", "status")}
    for p in paths.values(): ad.pin(p)
    run, start, call, status = (c.read(paths[x]) for x in ("run", "start", "call", "status"))
    c.need(run.get("stage") == "upl_tpi_gpu_run_r1.run" and run.get("passed") is False and
           run.get("failure") == FAILED_REASON and run.get("consumed_stats_unchanged") is True and
           run.get("tag") == FAILED_TAG and
           (run.get("configuration"), run.get("scheme"), run.get("window")) == ("Debug", "B", "debug2steps") and
           status.get("passed") is False and status.get("state") == "failed_preserved" and
           status.get("following_action_launched") is False and
           run.get("native_invocations") == run.get("VTK_invocations") == run.get("build_invocations") == 0,
           "Only the exact sealed wrong-mode postcheck failure is eligible")
    c.need(status["run"] == c.stat(paths["run"]) and run["call"] == c.stat(paths["call"]),
           "Original failure status/call binding changed")
    for key in ("program", "source_build", "prepared", "plan", "root_admission", "memcheck_program"):
        same_entry(ad, run[key])
    for key in ("source_entries", "runtime", "consumed", "outputs_stat_only"):
        for entry in run[key]: same_entry(ad, entry)
    same_entry(ad, call["program"]); same_entry(ad, call["target_program"]); same_entry(ad, call["log"])
    program = Path(run["program"]["path"]).resolve()
    c.need(start["program"] == call["target_program"] == run["program"] and
           start["source_build"] == run["source_build"] and start["plan"] == run["plan"] and
           run["root_admission"] == start["root_admission"] and run["input_prefix"] == start["input_prefix"] == str(c.PREFIX) and
           run["actual_environment"] == start["actual_environment"] == call["actual_environment"] == {"UPL_TPI_GPU_R1": "B"},
           "Original source/input/program/environment bindings differ")
    actual_identity(start, call, run, program)
    built, prepared = c.read(run["source_build"]["path"]), c.read(run["prepared"]["path"])
    bp = built.get("source_prepare", built.get("prepared"))
    c.need(built.get("passed") is True and built.get("configuration") == "Debug" and built.get("object_count") == 111 and
           stat_fields(built["program"]) == stat_fields(run["program"]) and bp == run["prepared"] and
           built.get("consumed_stats_unchanged") is True and prepared.get("passed") is True and
           prepared.get("host_h_API_and_other_268_files_byte_identical") is True,
           "Actual patched Debug build/source preparation binding differs")
    original_ad = c.read(run["root_admission"]["path"])
    c.need(original_ad.get("stage") == "upl_tpi_gpu_run_r1.run_admission" and original_ad.get("passed") is True and
           original_ad.get("one_job_only") is True and original_ad["job"]["tag"] == FAILED_TAG and
           original_ad["job"]["source_build"] == run["source_build"] and
           original_ad["job"]["source_prepare"] == run["prepared"],
           "Original root launch admission binding differs")
    ctx = dict(run, paths={"log": Path(call["log"]["path"]), "memcheck": L / (FAILED_TAG + ".memcheck.log")})
    ad.pin(ctx["paths"]["memcheck"])
    check_only_two_classifier_patches()
    checks = r.check_output(ctx)  # Pure completed-file checks, not context/run_owned/main.
    text = (Path(run["output_directory"]) / "Run.out").read_text(encoding="utf-8-sig")
    c.need(text.count(MODE) == 1 and BAD_MODE not in text,
           "New actual RunMode must be exactly the original Pos-Cell GPU mode")
    ad.pin(r.OLD_GPU); old = c.read(r.OLD_GPU); same_entry(ad, old["run_out"])
    old_text = Path(old["run_out"]["path"]).read_text(encoding="utf-8-sig")
    c.need(old.get("passed") is True and old_text.count(MODE) == 1 and BAD_MODE not in old_text,
           "Retained original GPU backend has a different actual mode")
    for p in (c.ORIGINAL_RUN, c.SEED_XML, c.SEED_BI4, c.SEED_NORMALS): ad.pin(p)
    rows, clock = r.schedule(ET.parse(c.SEED_XML).getroot(), "debug2steps")
    with Path(run["plan"]["path"]).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f); actual_rows = list(reader)
        c.need(reader.fieldnames == c.HEADER, "Original launch-plan schema changed")
    c.need(actual_rows == [{k: str(v) for k, v in row.items()} for row in rows] and clock == run["clock"] == start["clock"],
           "Original scalar-clock two-update launch plan changed")
    terminal = c.terminal_evidence(ctx)
    c.need(all(run.get(k) == v for k, v in terminal.items()) and
           terminal["actual_Run_out_normal_finish"] is True and
           terminal["console_first_actual_error_line"] is None and terminal["Run_out_first_actual_error_line"] is None,
           "Original terminal evidence differs or contains another actual failure")
    return dict(previous_failed_audit=old_failure, program_binding_stat_fields_only=True,
                original_run=c.stat(paths["run"]), original_start=c.stat(paths["start"]),
                original_call=c.stat(paths["call"]), original_status=c.stat(paths["status"]),
                actual_mode=MODE, retained_GPU_actual_mode=MODE, wrong_mode_predicate=BAD_MODE,
                actual_Hardware=checks["actual_device_from_Run_csv"], Hardware_case_insensitive_gpu_classifier=True,
                corrected_checker_AST_diff_is_only_two_classifiers=True, completed_output_checks=checks,
                actual_Popen_wait_exit=0, actual_Win32_exit=0, target_actual_Win32_exit=0,
                terminal_evidence=terminal, plan=run["plan"], original_run_passed=False,
                all_original_postconditions_except_two_metadata_classifiers_passed=True, failure_kind=FAILURE_KIND)


def accept_review(ad, job, run, call):
    """Pure eligibility check; does not execute this audit or mutate the original run."""
    entry = job.get("completed_run_review")
    c.need(isinstance(entry, dict), "Failed run requires its separately passed exact completed-run audit")
    ad.pin(SCRIPT); ad.pin(NOTE); ad.pin(entry["path"]); c.same(entry)
    review = c.read(entry["path"])
    c.need(job["tag"] == FAILED_TAG and Path(entry["path"]).resolve() == REVIEW.resolve() and
           run.get("passed") is False and run.get("failure") == FAILED_REASON and
           run.get("stage") == "upl_tpi_gpu_run_r1.run" and
           (run.get("configuration"), run.get("scheme"), run.get("window")) == ("Debug", "B", "debug2steps") and
           review.get("stage") == TAG + ".audit" and review.get("passed") is True and
           review.get("failure_kind") == FAILURE_KIND and review.get("original_run_passed") is False and
           review.get("all_original_postconditions_except_two_metadata_classifiers_passed") is True and
           review.get("corrected_checker_AST_diff_is_only_two_classifiers") is True and
           review.get("Hardware_case_insensitive_gpu_classifier") is True and
           "gpu" in review.get("actual_Hardware", "").lower() and
           review.get("actual_mode") == review.get("retained_GPU_actual_mode") == MODE and
           review.get("actual_Popen_wait_exit") == review.get("actual_Win32_exit") == review.get("target_actual_Win32_exit") == 0 and
           review["original_run"] == job["run_receipt"] and review["original_call"] == job["call"] and
           review.get("solver_invocations") == review.get("reader_invocations") == review.get("build_invocations") == 0 and
           review.get("physical_acceptance") is False,
           "Completed-run audit does not admit this exact preserved checker failure")
    for key in ("original_run", "original_start", "original_call", "original_status", "previous_failed_audit"):
        ad.pin(review[key]["path"]); c.same(review[key])
    c.need(review["previous_failed_audit"] == c.stat(PREVIOUS) and
           review.get("program_binding_stat_fields_only") is True,
           "Corrected audit must preserve the actual prior failed-audit diagnostic")
    previous_failure(ad)
    status = c.read(review["original_status"]["path"])
    c.need(status.get("passed") is False and status.get("state") == "failed_preserved" and
           status["run"] == job["run_receipt"] and call.get("passed") is True,
           "Original failed record/status must remain preserved")
    checks = review["completed_output_checks"]
    c.need(checks.get("solver_summary_completed") is True and checks.get("reported_steps") == 2 and
           checks.get("reported_native_frames") == 2 and checks.get("actual_memcheck_zero_errors") is True and
           checks.get("actual_r2_device_fixture_marker_count") == 1,
           "Completed-run audit lacks original full Debug completion evidence")
    return checks


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--execution-authorized", action="store_true")
    p.add_argument("--admission", required=True, type=Path)
    args = p.parse_args()
    c.need(args.execution_authorized, "Independent offline-only root admission required")
    c.need(not REVIEW.exists(), "Existing completed-run audit, including failure, is protected")
    ad = Admission(args.admission)
    result = dict(stage=TAG + ".audit", passed=False, root_admission=ad.entry, solver_invocations=0,
                  reader_invocations=0, build_invocations=0, VTK_invocations=0, Git_invocations=0,
                  SHA_scans=0, original_failure_records_changed=False, physical_acceptance=False,
                  native_and_sidecar_review_pending=True, automatic_follow_up=False)
    try:
        result.update(review_completed(ad)); result["consumed"] = ad.finish(); result["passed"] = True
    except Exception as exc:
        result["failure"] = str(exc)
        raise
    finally:
        c.write_new(REVIEW, result)


if __name__ == "__main__":
    main()
