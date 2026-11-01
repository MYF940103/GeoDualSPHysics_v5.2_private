"""Prepare, or explicitly execute ONE canonical CPU public-input rejection.

No batch mode, GenCase, compiler, private harness, PART fabrication or retry.
Preparation preserves the sealed BI4 and changes only the declared XML controls.
"""
import argparse
import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


T = Path(__file__).resolve().parents[1]
LOGS = T / "logs"
PREFIX = "upl_cpu_public_reject_r1"
PLAN = LOGS / "upl_cpu_public_r1.inputs.json"
FREEZE = LOGS / "upl_cpu_public_build_r3.json"
OFF = LOGS / "upl_cpu_public_off_r2.check.json"
DEBUG = LOGS / "upl_cpu_public_debug_wall_evolving_smoke_r1.review.check.json"
BUILD = LOGS / "upl_cpu_public_reader_ReleaseCPU_r2.build.json"
PREPARED = LOGS / (PREFIX + ".inputs.json")
NOTE = T / "notes" / (PREFIX + ".json")
EXPERIMENTAL = ("HydroMechDynamicSeepage is experimental: fresh CPU 2-D, zero gravity, "
                "InitMode=None and positive constant DtFixed only.")
FEEDBACK = ("Porosity feedback requires no-wall elastic CPU fixtures without acceleration "
            "input/load/drainage/HG/damping/viscosity/DDT/artificial stress/SPR/Shepard; "
            "k/gravity require the private dynamic-rate fixture.")
CASES = {
    "hydro_off": ("periodic_constant_c", "hydro", "HydroMech", "0", EXPERIMENTAL),
    "model_invalid": ("periodic_constant_c", "hydro", "HydroMechConductivityModel", "2",
        "HydroMechConductivityModel must be 0=constant or 1=void-ratio exponential."),
    "model_missing_ck": ("wall_evolving_c", "remove_hydro", "HydroMechConductivityCk", None,
        "Void-ratio exponential conductivity requires explicit finite HydroMechConductivityCk>0."),
    "model_master_off": ("wall_evolving_c", "hydro", "HydroMechDynamicSeepage", "0",
        "Evolving conductivity requires HydroMechDynamicSeepage=1."),
    "gravity": ("periodic_constant_c", "gravity", "z", "-9.80665", EXPERIMENTAL),
    "fixed_zero": ("periodic_constant_c", "parameter", "DtFixed", "0", EXPERIMENTAL),
    "pore_safety_overflow": ("periodic_constant_c", "hydro", "PoreDtSafety", "1e100",
        "Experimental dynamic seepage requires finite positive PoreDtSafety and CFLnumber."),
    "periodic_crossinc": ("periodic_constant_c", "crossinc", None, None,
        "Experimental dynamic seepage requires axis-aligned rectangular periodic translations in the 2-D plane."),
    "wall_noslip": ("wall_evolving_c", "parameter", "SlipMode", "2",
        "Dynamic wall fixture requires finite stationary FreeSlip wall normals."),
    "drainage": ("wall_evolving_c", "hydro", "HydroMechDrainage", "1", FEEDBACK),
    "spr_conflict": ("wall_evolving_c", "parameter", "SoilBoundaryDerivativeSPR", "1", FEEDBACK),
}


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def entry(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def new_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def verify_tree(value):
    """Verify actual sealed entries, not a status boolean alone."""
    seen = set()
    def visit(item):
        if isinstance(item, dict):
            if {"path", "bytes", "sha256"}.issubset(item):
                key = (item["path"], item["bytes"], item["sha256"].lower())
                if key not in seen:
                    actual = entry(item["path"])
                    require((actual["bytes"], actual["sha256"]) == key[1:],
                            "Sealed identity changed: " + item["path"])
                    seen.add(key)
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)
    visit(value)
    return len(seen)


def prerequisites(for_run=False):
    freeze, off, plan = load(FREEZE), load(OFF), load(PLAN)
    require(freeze["status"] == "DebugCPU_ReleaseCPU_passed_prebuild_source_snapshot_held_for_tests"
            and len(freeze["source"]) == 7 and
            freeze["msbuild_exit_codes"] == {"DebugCPU": 0, "ReleaseCPU": 0},
            "Authoritative seven-file full Rebuild r3 required")
    require(off.get("passed") and off["actual_native_frame_pairs"] == 140 and
            off["all_bits_0ULP"] and off["clock_step_dterror_exact"] and off["exclusions"] == 0,
            "Current default-OFF 140-pair exact regression required")
    require(plan["status"] == "runtime_inputs_prepared_not_solved" and len(plan["jobs"]) == 9
            and plan["all_copied_BI4_byte_identical"], "Nine sealed valid runtime inputs required")
    bindings = [entry(FREEZE), entry(OFF), entry(PLAN), entry(__file__), entry(NOTE)]
    # A prebuild original was intentionally replaced by this Rebuild. Its sealed
    # snapshot, not that historical canonical path, is the preserved old binary.
    verify_tree({key: freeze[key] for key in ("source", "programs", "inputs", "logs")})
    verify_tree([row["snapshot"] for row in freeze["prior_programs"]])
    for obj in (off, plan):
        verify_tree(obj)
    for group in off["groups"]:
        require(load(group["check"]["path"]).get("passed"), "A default-OFF group did not pass")
    build = None
    if for_run:
        debug, build = load(DEBUG), load(BUILD)
        require(debug.get("passed") and debug.get("job") == "debug_wall_evolving_smoke",
                "Successful canonical Debug native review required before rejection execution")
        completion = load(debug["completion"]["path"])
        require(completion.get("passed") and completion.get("samples") == 3,
                "Actual canonical Debug three-frame native review required")
        require(build["status"] == "built_not_run" and build["configuration"] == "ReleaseCPU"
                and build["compile_exit"] == 0 and build["link_exit"] == 0,
                "Already isolated Release canonical program/reader build required")
        require(build["source_freeze"] == entry(FREEZE), "Isolated Release build is not public r3")
        expected = T / "outputs" / "upl_cpu_public_program_ReleaseCPU_r2" / "DualSPHysics5.2CPU_win64.exe"
        require(Path(build["canonical_program"]["path"]).resolve() == expected.resolve(),
                "Only the already isolated canonical CPU Release executable is allowed")
        verify_tree(debug)
        verify_tree(build)
        bindings += [entry(DEBUG), entry(BUILD)]
    return plan, build, bindings


def one(root, path):
    nodes = root.findall(path)
    require(len(nodes) == 1, "Expected exactly one XML node: " + path)
    return nodes[0]


def semantic(root):
    rows = {}
    def visit(node, path):
        rows[path] = [dict(sorted(node.attrib.items())), (node.text or "").strip()]
        counts = {}
        totals = {}
        for child in node:
            totals[child.tag] = totals.get(child.tag, 0) + 1
        for child in node:
            counts[child.tag] = counts.get(child.tag, 0) + 1
            suffix = ("[@key='" + child.get("key") + "']" if child.get("key") else
                      ("[" + str(counts[child.tag]) + "]" if totals[child.tag] > 1 else ""))
            visit(child, path + "/" + child.tag + suffix)
    visit(root, "/" + root.tag)
    return rows


def mutate(root, spec):
    _, kind, key, value, _ = spec
    hydro = one(root, "./execution/special/hydromechanics")
    params = one(root, "./execution/parameters")
    if kind in ("hydro", "remove_hydro"):
        node = one(hydro, "./" + key)
        if kind == "remove_hydro":
            hydro.remove(node)
        else:
            require(node.get("value") != value, "Mutation would be vacuous")
            node.set("value", value)
    elif kind == "parameter":
        node = one(params, "./parameter[@key='" + key + "']")
        require(node.get("value") != value, "Mutation would be vacuous")
        node.set("value", value)
    elif kind == "gravity":
        one(root, "./execution/constants/gravity").set(key, value)
    elif kind == "crossinc":
        params.remove(one(params, "./parameter[@key='XZPeriodic']"))
        require(not params.findall("./parameter[@key='XPeriodicIncZ']") and
                not params.findall("./parameter[@key='ZPeriodicIncX']"), "Unexpected pre-existing cross-inc")
        ET.SubElement(params, "parameter", key="XPeriodicIncZ", value="0.001")
        ET.SubElement(params, "parameter", key="ZPeriodicIncX", value="0")
    else:
        raise RuntimeError("Undeclared mutation")


def prepare():
    plan, _, bindings = prerequisites()
    paths = [PREPARED]
    for label in CASES:
        paths += [T / "outputs" / (PREFIX + "_" + label + "_seed"),
                  T / "outputs" / (PREFIX + "_" + label + "_out")]
    # Check every possible output in advance; no in-place update/retry.
    for label in CASES:
        paths += [LOGS / (PREFIX + "_" + label + s) for s in (".log", ".started.json", ".run.json")]
    require(not any(p.exists() for p in paths), "A rejection artifact already exists; retain it")
    jobs = {j["label"]: j for j in plan["jobs"]}
    cases = []
    for label, spec in CASES.items():
        base = jobs[spec[0]]
        source = Path(base["runtime"]["path"])
        original = ET.parse(source).getroot()
        changed = copy.deepcopy(original)
        before = semantic(original)
        mutate(changed, spec)
        after = semantic(changed)
        delta = [{"path": p, "before": before.get(p), "after": after.get(p)}
                 for p in sorted(before.keys() | after.keys()) if before.get(p) != after.get(p)]
        require(len(delta) == (3 if spec[1] == "crossinc" else 1), "Unexpected logical XML changes")
        require(ET.tostring(one(original, "./casedef")) == ET.tostring(one(changed, "./casedef")),
                "Generation geometry/material casedef changed")
        folder = T / "outputs" / (PREFIX + "_" + label + "_seed")
        folder.mkdir()
        xml = folder / source.name
        ET.indent(changed, space="    ")
        with xml.open("xb") as stream:
            stream.write(ET.tostring(changed, encoding="utf-8", xml_declaration=True))
        bi4 = folder / Path(base["copied_geometry"]["path"]).name
        shutil.copyfile(base["copied_geometry"]["path"], bi4)
        require(entry(bi4)["sha256"] == base["copied_geometry"]["sha256"], "Copied geometry changed")
        cases.append({"label": label, "base": spec[0], "source_xml": base["runtime"],
            "source_bi4": base["copied_geometry"], "xml": entry(xml), "bi4": entry(bi4),
            "xml_semantic_delta": delta, "expected_exact_message": spec[4],
            "input_prefix": str(xml.with_suffix("")),
            "output": str(T / "outputs" / (PREFIX + "_" + label + "_out"))})
    verify_tree(bindings)
    new_json(PREPARED, {"status": "eleven_rejection_inputs_prepared_not_executed", "cases": cases,
        "bindings": bindings, "BI4_byte_identical": True, "solver_executed": False,
        "pending_PART_cases": ["ON_old_OFF_PART", "OFF_ON_J_PART", "OFF_false_metadata_PART"],
        "physical_acceptance": False})
    print("PREPARED 11 only; no solver executed: " + str(PREPARED))


def run_one(label, authorized):
    require(authorized, "--execution-authorized is required; one root-selected owned call only")
    _, build, bindings = prerequisites(for_run=True)
    prepared = load(PREPARED)
    require(prepared["status"] == "eleven_rejection_inputs_prepared_not_executed" and
            len(prepared["cases"]) == 11, "Prepared eleven-case manifest required")
    verify_tree(prepared)
    selected = [case for case in prepared["cases"] if case["label"] == label]
    require(len(selected) == 1, "Select one declared rejection label")
    case = selected[0]
    require(case["expected_exact_message"] == CASES[label][4], "Expected rejection changed")
    log = LOGS / (PREFIX + "_" + label + ".log")
    started = LOGS / (PREFIX + "_" + label + ".started.json")
    receipt = LOGS / (PREFIX + "_" + label + ".run.json")
    output = Path(case["output"])
    require(not any(p.exists() for p in (log, started, receipt, output)),
            "Owned rejection call/output already exists; no retry or overwrite")
    program = Path(build["canonical_program"]["path"])
    argv = [str(program), "-cpu", "-ompthreads:1", "-stable", case["input_prefix"],
            str(output), "-dirdataout", "data", "-svres"]
    clock = time.monotonic()
    start_utc = datetime.now(timezone.utc).isoformat()
    # Launch exactly once, not a batch. Never terminate any old/foreign process.
    with log.open("xb") as stream:
        proc = subprocess.Popen(argv, cwd=str(program.parent), stdout=stream,
                                stderr=subprocess.STDOUT, shell=False)
        new_json(started, {"status": "owned_call_started_not_completed", "pid": proc.pid,
            "started_utc": start_utc, "argv": argv, "program": entry(program),
            "prepared": entry(PREPARED), "bindings": bindings, "physical_acceptance": False})
        code = proc.wait()
    files = [entry(p) for p in sorted(output.rglob("*")) if p.is_file()] if output.exists() else []
    native = [row for row in files if re.fullmatch(r"Part_\d+\.bi4", Path(row["path"]).name, re.I)]
    text = log.read_bytes().decode("utf-8", errors="replace")
    exact = case["expected_exact_message"] in text
    parser_rejection = (label == "pore_safety_overflow" and not exact and
        "Error reading xml - Value of 'value' invalid." in text and
        "It is not a valid real number." in text)
    identity_error = None
    try:
        verify_tree(bindings)
        verify_tree(prepared)
        verify_tree(build)
    except Exception as error:
        identity_error = str(error)
    passed = code != 0 and exact and not native and identity_error is None
    new_json(receipt, {"passed": passed, "label": label, "scope": "Single canonical invalid-input rejection only",
        "pid": proc.pid, "owned_call_exited": True, "exit_code": code, "started_utc": start_utc,
        "ended_utc": datetime.now(timezone.utc).isoformat(), "elapsed_s": time.monotonic() - clock,
        "argv": argv, "program": entry(program), "prepared": entry(PREPARED),
        "input": [case["xml"], case["bi4"]], "bindings": bindings, "log": entry(log), "files": files,
        "expected_exact_message": case["expected_exact_message"], "expected_message_present": exact,
        "target_guard_reached": exact, "parser_rejection_target_guard_not_reached": parser_rejection,
        "native_PART_count": len(native), "native_PART_saved": bool(native), "identity_error": identity_error,
        "physical_acceptance": False, "PART_restart_coverage": False})
    require(passed, "Rejection failed its exact target/exit/no-native-PART/identity gate; preserve all evidence")
    print("PASSED ONE canonical rejection: " + label)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--run-one", choices=tuple(CASES))
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        require(not args.execution_authorized, "Preparation cannot execute a program")
        prepare()
    else:
        run_one(args.run_one, args.execution_authorized)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("HELD: " + str(exc), file=sys.stderr)
        sys.exit(1)
