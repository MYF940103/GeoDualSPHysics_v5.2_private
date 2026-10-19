"""Reproducible production-merge case-02 run; no overwrite, retry or chaining.

Reuse the hash-verified frozen GenCase particle/normal files. Write a matching
Def and generated runtime XML with every changed setting explicit. The runner
does not change solver physics through CLI or in-memory overrides.
--dry-run reads/checks only; --prepare-only creates inputs but starts no solver.
Normal completion is not physical acceptance. No plotting is claimed here.
"""
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

TESTS = Path(__file__).resolve().parents[1]
CASE, REPO = TESTS.parent, TESTS.parents[3]
BASE = TESTS / "outputs/stress_full_r1_dt1/CaseTCq0_stress_dt1"
TEMPLATE = TESTS / "configs/CaseTCq0_hg_merge_Def.xml"
FREEZE = TESTS / "logs/hg_merge_base.json"
NATIVE_INITIAL = TESTS / "outputs/hg_window_x01/initial_state.csv"
CHANGED_PARAMETERS = {"DtIni", "DtFixed", "TimeMax", "TimeOut", "SoilStressRateGradCorr", "SoilHourglassXi"}


def require(okay, message):
    if not okay:
        raise ValueError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def utc():
    return datetime.now(timezone.utc).isoformat()


def entry(path):
    p = Path(path).resolve()
    return dict(path=str(p), bytes=p.stat().st_size, sha256=sha(p))


def save_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def status(path, value):
    value = dict(value, updated_utc=utc())
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    os.replace(tmp, path)


def signature(node, omit=False):
    if omit and (node.tag == "HydroMechTopLoadMode" or node.tag == "parameter" and node.get("key") in CHANGED_PARAMETERS):
        return None
    attrs = tuple(sorted((k, v) for k, v in node.attrib.items() if k not in {"comment", "units_comment", "_rem"}))
    return node.tag, attrs, (node.text or "").strip(), tuple(s for c in node if (s := signature(c, omit)) is not None)


def replace_value(text, selector, value):
    pattern = rf'(<{selector}\s+value=")[^"]*(")'
    text, count = re.subn(pattern, lambda m: m[1]+str(value)+m[2], text)
    require(count == 1, f"Expected one XML setting: {selector}")
    return text


def render(text, settings):
    text = replace_value(text, "HydroMechTopLoadMode", "TopKernelBand" if settings["top_load_mode"] == 5 else "TopVertical")
    comment = "CPU top kernel-support load band; same resultant as TopVertical (mode 5)" if settings["top_load_mode"] == 5 else "Original vertical load on top free-surface particles (mode 1)"
    text = re.sub(r'(<HydroMechTopLoadMode value="[^"]*" comment=")[^"]*(")', lambda m: m[1]+comment+m[2], text)
    values = dict(DtIni=settings["dt_text"], DtFixed=settings["dt_text"], TimeMax=settings["duration_text"],
                  TimeOut=settings["output_interval_text"], SoilStressRateGradCorr="1", SoilHourglassXi=settings["xi_text"])
    for key, value in values.items():
        if f'key="{key}"' not in text:
            require(key in {"SoilStressRateGradCorr", "SoilHourglassXi"}, f"Missing baseline parameter {key}")
            match = re.search(r'(?m)^([ \t]*)<parameter key="SoilDamping"', text)
            require(match is not None, "Missing standard parameter insertion point")
            comment = "Correct soil stress-rate velocity gradients" if key == "SoilStressRateGradCorr" else "Small-rotation elastic GNOG; 0 disables HG"
            line = f'{match[1]}<parameter key="{key}" value="{value}" comment="{comment}" />\n'
            text = text[:match.start()]+line+text[match.start():]
        text = replace_value(text, f'parameter key="{key}"', value)
    for key, comment in {"DtIni": "Initial time step equal to explicit fixed dt", "DtFixed": "Explicit production-merge fixed time step",
                         "TimeMax": "Requested diagnostic duration; not physical acceptance", "TimeOut": "Diagnostic output interval"}.items():
        text = re.sub(rf'(<parameter key="{key}" value="[^"]*" comment=")[^"]*(")', lambda m: m[1]+comment+m[2], text)
    return text


def settings(args):
    dt, duration = Decimal(args.dt), Decimal(args.duration)
    interval = Decimal(args.output_interval) if args.output_interval else min(duration, Decimal("0.1"))
    require(re.fullmatch(r"[A-Za-z0-9_-]{1,72}", args.name), "Use a short simple run label")
    require(dt in {Decimal("0.00001"), Decimal("0.000005")} and duration.is_finite() and duration > 0,
            "Require dt=1e-5 or 5e-6 and positive finite duration")
    require(interval.is_finite() and interval > 0 and interval/dt == (interval/dt).to_integral_value(),
            "Output interval must be a positive integer multiple of dt")
    require(math.isfinite(args.xi) and args.xi >= 0, "Invalid HG coefficient")
    steps = int((duration/dt).to_integral_value(rounding=ROUND_CEILING))
    require(1 <= steps <= 15000000, "Duration outside retained case-02 runner range")
    return dict(label=args.name, duration_s=float(duration), duration_text=str(duration), dt=float(dt), dt_text=str(dt),
                steps=steps, stride=int(interval/dt), output_interval_s=float(interval), output_interval_text=str(interval),
                xi=args.xi, xi_text=str(args.xi), top_load_mode=args.top_mode, grad_corr=1,
                engine=args.engine, threads=args.threads, save=args.save)


def prepare(s, write):
    frozen = load(FREEZE)
    require(frozen["status"] == "frozen_pre_production_merge" and frozen["source_and_copy_hashes_verified"], "Missing verified pre-merge snapshot")
    source_files = [BASE.with_suffix(".xml"), BASE.with_suffix(".bi4"), BASE.with_name(BASE.name+"_Normals.nbi4")]
    for path in source_files:
        saved = [e for e in frozen["entries"] if Path(e["path"]).resolve() == path.resolve()]
        require(len(saved) == 1 and sha(path) == saved[0]["sha256"].lower(), f"Changed frozen input: {path}")
    original = source_files[0].read_text(encoding="utf-8-sig")
    definition = TEMPLATE.read_text(encoding="utf-8-sig")
    roots = [ET.fromstring(original), ET.fromstring(definition)]
    for section in ("casedef", "execution/special", "execution/parameters"):
        require(signature(roots[0].find(section), True) == signature(roots[1].find(section), True),
                f"Template changed an unapproved baseline setting: {section}")
    particles = roots[0].find("execution/particles")
    fluid = particles.find("fluid")
    require(particles.get("np") == "1040" and particles.get("nb") == "40" and fluid.get("begin") == "40"
            and fluid.get("count") == "1000", "Unexpected frozen native particle metadata")
    for root in roots:
        require(root.find("execution/special/hydromechanics/HydraulicConductivity").get("value") == "1e-4", "Unexpected conductivity")
    runtime_text, def_text = render(original, s), render(definition, s)
    for text in (runtime_text, def_text):
        root = ET.fromstring(text)
        for section in ("casedef", "execution/special", "execution/parameters"):
            require(signature(root.find(section), True) == signature(roots[0].find(section), True), "Unexpected XML change")
    prefix = TESTS/f"outputs/{s['label']}_input/CaseTCq0_{s['label']}"
    definition_path = TESTS/f"configs/CaseTCq0_{s['label']}_Def.xml"
    record_path = TESTS/f"logs/{s['label']}.prepare.json"
    payload = dict(settings=s, prefix=str(prefix), definition=str(definition_path),
                   frozen_source_inputs=[entry(p) for p in source_files], template=entry(TEMPLATE), snapshot=entry(FREEZE),
                   preparation="Retained GenCase particles/normals copied byte-for-byte after unchanged casedef/physics check",
                   approved_changes=sorted(CHANGED_PARAMETERS | {"HydroMechTopLoadMode"}),
                   native_id_range=[0, 1039], soil_id_range=[40, 1039], physical_accuracy_accepted=False)
    if not write:
        return prefix, payload
    if record_path.exists():
        previous = load(record_path)
        require(previous["settings"] == s, "Existing preparation has different settings")
        for item in previous["inputs"]:
            require(sha(item["path"]) == item["sha256"], f"Changed prepared input: {item['path']}")
        return prefix, previous
    require(not prefix.parent.exists() and not definition_path.exists(), "Refusing to overwrite prepared inputs")
    prefix.parent.mkdir()
    with definition_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(def_text)
    with prefix.with_suffix(".xml").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(runtime_text)
    for old, new in ((source_files[1], prefix.with_suffix(".bi4")),
                     (source_files[2], prefix.with_name(prefix.name+"_Normals.nbi4"))):
        shutil.copy2(old, new)
        require(sha(old) == sha(new), "Copied native particle/normal hash mismatch")
    payload["inputs"] = [entry(p) for p in [definition_path, *sorted(prefix.parent.iterdir())]]
    payload["created_utc"] = utc()
    save_new(record_path, payload)
    return prefix, payload


def parse_solver_completion(out, s):
    with (out/"Run.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter=";"))
    require(len(rows) == 1, "Expected one production Run.csv result")
    r = rows[0]
    text = (out/"Run.out").read_text(encoding="utf-8-sig", errors="replace")
    require("[Simulation finished" in text and "Finished execution (code=0)" in text, "Missing production completion marker")
    require(int(r["Np"]) == 1040 and int(r["PartsOut"]) == 0, "Production particle count/loss check failed")
    return dict(mode="formal_cpu_solver", steps=int(r["Steps"]), final_time=float(r["PhysicalTime"]),
                normal_soil=1000, native_state_compared=False, elapsed_seconds=float(r["TSimul"]),
                physical_configuration_overridden=False, physical_accuracy_accepted=False,
                last_saved_snapshot_may_precede_final_time=True)


def runtime_inputs(args):
    default = TESTS/f"outputs/mech_bin_{args.binary_label}/mechanics.exe" if args.engine == "wrapper" else REPO/"bin/windows/DualSPHysics5.2CPU_win64.exe"
    exe = Path(args.exe).resolve() if args.exe else default
    require(exe.is_file(), f"Executable not found: {exe}")
    build_path = Path(args.build_record).resolve() if args.build_record else TESTS/f"logs/mech_bin_{args.binary_label}.build.json" if args.engine == "wrapper" else None
    files = []
    if build_path:
        build = load(build_path)
        for item in build["runtime"]:
            require(sha(item["path"]) == item["sha256"].lower(), f"Changed build runtime: {item['path']}")
        require(any(Path(e["path"]).resolve() == exe.resolve() for e in build["runtime"]), "Executable absent from build manifest")
        files = [entry(build_path)]+[entry(e["path"]) for e in build["runtime"]]
    else:
        files = [entry(exe)]+[entry(p) for p in exe.parent.glob("*.dll")]
    require(NATIVE_INITIAL.is_file(), "Missing retained native initial-state CSV")
    return exe, files


def compare_initial(path):
    frames = [pd.read_csv(p, float_precision="round_trip").sort_values("id") for p in (NATIVE_INITIAL, path)]
    for frame in frames:
        require(np.array_equal(frame.id.to_numpy(), np.arange(1040)), "Wrong initial native ID set")
        require(np.isfinite(frame.to_numpy()).all(), "Nonfinite initial native state")
    types = {"id": "<u4", **{c: "<f8" for c in ("x", "y", "z", "sigma_xx", "sigma_yy", "sigma_zz", "sigma_xy", "sigma_yz", "sigma_xz")},
             **{c: "<f4" for c in ("vx", "vy", "vz", "rho", "pressure", "kplastic")}}
    same = {c: frames[0][c].to_numpy(dtype=d).tobytes() == frames[1][c].to_numpy(dtype=d).tobytes() for c, d in types.items()}
    require(all(same.values()), f"Initial retained native fields differ: {same}")
    return dict(reference=str(NATIVE_INITIAL), reference_sha256=sha(NATIVE_INITIAL), native_ids=1040,
                fields_bitwise_equal=same, stored_field_types=types, porepress0_compared=False,
                limitation="The old initial CSV did not retain PorePress0; whole binary-state equivalence is not claimed.")


def run(args, s, prefix, prepared):
    out, logs = TESTS/f"outputs/{s['label']}", TESTS/"logs"
    paths = {key: logs/f"{s['label']}.{key}" for key in ("run.json", "start.json", "status.json", "stdout.log", "stderr.log")}
    require(not out.exists() and not any(p.exists() for p in paths.values()), "Refusing overwrite, retry or duplicate run")
    exe, runtime = runtime_inputs(args)
    inputs = prepared["inputs"]+[entry(p) for p in (Path(__file__), FREEZE, TEMPLATE, NATIVE_INITIAL, logs/f"{s['label']}.prepare.json")]
    inputs += runtime
    inputs = list({item["path"]: item for item in inputs}.values())
    command = [str(exe)]
    if args.engine == "wrapper":
        command += [str(s["steps"]), str(s["stride"]), str(s["save"])]
    command += ["-cpu", "-stable", f"-ompthreads:{s['threads']}", "-mdbc", str(prefix), str(out), "-dirdataout", "data", "-svres"]
    if args.engine == "solver":
        command += [f"-nsteps:{s['steps']}"]
    command += ["-svextraparts:1"] if s["save"] else ["-sv:none"]
    record = dict(status="running_not_accepted", purpose="production_merge_regression", physical_accuracy_accepted=False,
                  **s, arguments=command[1:], command=command, executable=str(exe), executable_sha256=sha(exe), output=str(out),
                  inputs=inputs, started_utc=utc(), git_head=subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip(),
                  source_project_git_status=subprocess.check_output(["git", "-C", str(REPO), "status", "--short", "--", "src/source", "src/VS"], text=True).splitlines(),
                  hourglass_xi=s["xi"], hourglass_enabled=s["xi"] > 0)
    begin = time.perf_counter(); process = None
    code, failure, complete, hg, initial_check = None, None, None, None, None
    try:
        with paths["stdout.log"].open("xb") as stdout, paths["stderr.log"].open("xb") as stderr:
            process = subprocess.Popen(command, cwd=CASE, stdout=stdout, stderr=stderr, stdin=subprocess.DEVNULL,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            record["pid"] = process.pid
            save_new(paths["start.json"], record)
            while True:
                status(paths["status.json"], dict(status="running_not_accepted", label=s["label"], pid=process.pid,
                       elapsed_seconds=time.perf_counter()-begin, target_seconds=s["duration_s"], physical_accuracy_accepted=False))
                try:
                    code = process.wait(timeout=20)
                    break
                except subprocess.TimeoutExpired:
                    pass
        require(code == 0, f"Solver exit code {code}; inspect stdout/stderr and Run.out")
        if args.engine == "wrapper":
            complete, hg = load(out/"complete.json"), load(out/"hourglass_complete.json")
            require(complete["mode"] == "production_symplectic" and complete["normal_soil"] == 1000
                    and complete["dt"] == s["dt"] and complete["xi"] == s["xi"] and complete["stress_grad_corr"]
                    and complete["top_load_mode"] == s["top_load_mode"] and not complete["physical_configuration_overridden"], "Wrapper configuration/completion mismatch")
            initial_check = compare_initial(out/"initial_state.csv")
            require(hg["hg_rate_calls"] == (2*s["steps"] if s["xi"] else 0), "Incomplete HG endpoint history")
        else:
            complete = parse_solver_completion(out, s)
        require(complete["steps"] == s["steps"] and abs(complete["final_time"]-s["steps"]*s["dt"]) < 1e-6,
                "Requested duration/step count not reached")
    except BaseException as error:
        failure = f"{type(error).__name__}: {error}"
        if process is not None and process.poll() is None:
            process.terminate(); process.wait(timeout=30)
            code = process.returncode
    changed = [e["path"] for e in inputs if not Path(e["path"]).is_file() or sha(e["path"]) != e["sha256"]]
    okay = failure is None and not changed
    record.update(status="completed_pending_physical_acceptance" if okay else "failed_or_incomplete",
                  finished_utc=utc(), elapsed_seconds=time.perf_counter()-begin, exit_code=code, failure=failure,
                  inputs_unchanged=not changed, changed_inputs=changed, completion_valid=okay,
                  completion=complete, hourglass=hg, initial_state_comparison=initial_check,
                  outputs=[entry(p) for p in sorted(out.rglob("*")) if p.is_file()] if out.exists() else [])
    save_new(paths["run.json"], record)
    status(paths["status.json"], dict(status=record["status"], label=s["label"], final_time=complete.get("final_time") if complete else None,
           failure=failure, run_manifest=str(paths["run.json"]), physical_accuracy_accepted=False))
    print(json.dumps(dict(status=record["status"], record=str(paths["run.json"]), failure=failure)))
    return 0 if okay else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--duration", required=True, help="Physical seconds; final step rounds upward")
    parser.add_argument("--dt", default="0.00001")
    parser.add_argument("--output-interval")
    parser.add_argument("--xi", type=float, default=.1)
    parser.add_argument("--top-mode", type=int, choices=(1, 5), default=5)
    parser.add_argument("--engine", choices=("wrapper", "solver"), default="wrapper")
    parser.add_argument("--binary-label", default="hg_m1rel")
    parser.add_argument("--exe")
    parser.add_argument("--build-record")
    parser.add_argument("--threads", type=int, choices=(1, 4), default=1)
    parser.add_argument("--save", type=int, choices=(0, 1), default=1)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--run", action="store_true", help="Launch this run once; no automatic next stage")
    args = parser.parse_args(); s = settings(args)
    runtime_inputs(args)
    compare_initial(NATIVE_INITIAL)  # Check field presence/types before creating inputs or starting a process.
    prefix, prepared = prepare(s, not args.dry_run)
    if args.dry_run or args.prepare_only:
        print(json.dumps(dict(status="checked_not_run" if args.dry_run else "prepared_not_run", **prepared), indent=2))
        return 0
    return run(args, s, prefix, prepared)


if __name__ == "__main__":
    sys.exit(main())
