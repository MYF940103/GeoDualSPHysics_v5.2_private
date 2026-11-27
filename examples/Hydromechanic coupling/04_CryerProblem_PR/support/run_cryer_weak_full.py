"""Root XML/BAT entry for the sealed Cryer weak-full GPU experiment."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np

CASE = Path(__file__).resolve().parents[1]
STEM = "CaseCryerWeakFull_nu030_1Tv"
XML = CASE / (STEM + "_Def.xml")
PACKAGE = CASE / "support/weak_full_r1"
MANIFEST_SHA = "f8ed7f15912bd32f16a9f27425fd28f703190faf194935f5ab7f021ed2fd9bf2"
OUTPUT = CASE / (STEM + "_GPU_out")
SMOKE = CASE / "tests/outputs/cryer_weak_full_formal_smoke_r1"


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path, data):
    with path.open("x", encoding="utf8") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")


def utc():
    return datetime.now(timezone.utc).isoformat()


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def preflight(verify_payload=True):
    """Bind the editable XML to the actual frozen operators, clock and material mesh."""
    root = ET.parse(XML).getroot()
    for path, tags in (
        ("casedef/constantsdef", {"gravity", "rhop0", "hdp"}),
        ("execution/special", {"timeout", "soils", "hydromechanics", "drainage", "externalload", "weakfull"}),
        ("execution/special/soils", {"ModulusE", "PRvs"}),
        ("execution/special/hydromechanics", {"HydroMechModel", "PoreWaterRho", "Porosity", "HydraulicConductivity"}),
    ):
        section = root.find(path)
        need(section is not None and {e.tag for e in section} == tags,
             f"Unsupported or missing fixed-profile fields in {path}; rebuild the matching package for a changed model")
    values = {}
    for key, path, attr in (
        ("rho", "casedef/constantsdef/rhop0", "value"),
        ("hdp", "casedef/constantsdef/hdp", "value"),
        ("radius", "casedef/geometry/predefinition/newvarcte[@radius]", "radius"),
        ("dp", "casedef/geometry/predefinition/newvarcte[@Dp]", "Dp"),
        ("E", "execution/special/soils/ModulusE", "value"),
        ("nu", "execution/special/soils/PRvs", "value"),
        ("model", "execution/special/hydromechanics/HydroMechModel", "value"),
        ("water_rho", "execution/special/hydromechanics/PoreWaterRho", "value"),
        ("porosity", "execution/special/hydromechanics/Porosity", "value"),
        ("conductivity", "execution/special/hydromechanics/HydraulicConductivity", "value"),
        ("q0", "execution/special/externalload", "q0"),
        ("ramp_s", "execution/special/externalload", "ramptime"),
        ("drain_s", "execution/special/drainage", "start"),
    ):
        element = root.find(path)
        need(element is not None and attr in element.attrib, f"Missing XML field: {path}/@{attr}")
        values[key] = float(element.get(attr))
    expected = dict(rho=2100., hdp=1.8, radius=.05, dp=.0025, E=2e6, nu=.3, model=2.,
                    water_rho=1000., porosity=.3, conductivity=1e-5, q0=10000.,
                    ramp_s=.00390625, drain_s=.0078125)
    parameters = {e.get("key"): float(e.get("value")) for e in root.findall("execution/parameters/parameter")}
    need(len(parameters) == len(root.findall("execution/parameters/parameter")), "Repeated XML parameter key")
    parameter_profile = dict(StepAlgorithm=2., Kernel=2., Visco=.1, SoilDamping=1.,
        SoilDampingCoef=.00004, DtIni=2.**-19, DtFixed=2.**-19,
        TimeMax=.9187412261962890625, TimeOut=.004554642857142857)
    differences = [f"{k}: XML={values.get(k)!r}, frozen={v!r}" for k,v in expected.items() if values.get(k) != v]
    differences += [f"{k}: XML={parameters.get(k)!r}, frozen={parameter_profile.get(k)!r}"
                    for k in sorted(set(parameters) | set(parameter_profile)) if parameters.get(k) != parameter_profile.get(k)]
    need(not differences, "XML requires a newly generated matching weak package:\n" + "\n".join(differences))
    gravity = root.find("casedef/constantsdef/gravity")
    need(gravity is not None and all(float(gravity.get(k)) == 0. for k in ("x", "y", "z")), "Frozen case has zero body gravity")
    need(root.find("casedef/geometry/definition").get("dp") == "#Dp", "Reference spacing must use the declared Dp")
    need(root.find("execution/special/externalload").get("mode") == "2", "Frozen load is surface confinement")
    drain = root.find("execution/special/drainage")
    need(drain.get("mode") == "drained" and drain.get("clock") == "fixedStep", "Frozen drainage uses the fixed-step clock")
    profile = root.find("execution/special/weakfull")
    wanted = dict(package="support/weak_full_r1", formulation="FixedReferenceP1NativeMass", pressure_rounds="3",
                  material_count="37173", scheduled_states="265", checkpoint_states="4")
    need(profile is not None and all(profile.get(k) == v for k,v in wanted.items()), "Weak runtime/profile differs from the sealed package")
    intervals = [(float(e.get("time")), float(e.get("timeout"))) for e in root.findall("execution/special/timeout/tout")]
    need(intervals == [(0., 64*parameters["DtFixed"]), (values["drain_s"], parameters["TimeOut"])], "XML output intervals differ from the original schedule")

    manifest_path = PACKAGE / "manifest.json"
    need(sha(manifest_path) == MANIFEST_SHA, "Frozen package manifest changed")
    manifest = read_json(manifest_path)
    for entry in manifest["files"]:
        path = PACKAGE / entry["name"]
        need(path.stat().st_size == entry["bytes"]
             and (not verify_payload or sha(path) == entry["sha256"]), f"Frozen package changed: {entry['name']}")
    inputs = PACKAGE / "inputs"
    with (inputs/"operators.bin").open("rb") as stream:
        actual = struct.unpack("<4d", stream.read(32))
    nu, n0 = f32(values["nu"]), f32(values["porosity"])
    h = f32(values["dp"] * values["hdp"])
    damping = f32(f32(parameters["SoilDampingCoef"])*math.sqrt(values["E"]/(((values["rho"]-n0*values["water_rho"])/(1-n0))*h*h)))
    derived = (parameters["DtFixed"], values["E"]/(2*(1+nu)), values["E"]*nu/((1+nu)*(1-2*nu)), damping)
    need(actual == derived, f"XML dt/material/damping do not reproduce the packed operator header: {actual} vs {derived}")
    with np.load(inputs/"reference_mesh.npz") as mesh:
        radius = np.linalg.norm(mesh["x0"], axis=1)
        need(np.array_equal(mesh["native_ids"], np.arange(8, 37181))
             and abs(radius.max()-values["radius"]) < 1e-14
             and np.max(abs(radius/values["dp"]-mesh["material_shell"])) < 1e-10
             and np.all(mesh["native_mass_kg"] == f32(values["rho"]*values["dp"]**3)), "XML geometry/native masses differ from the frozen mesh")
    steps = [int(line) for line in (inputs/"steps.txt").read_text().splitlines()]
    with (inputs/"reference.csv").open(newline="") as stream:
        reference = list(csv.DictReader(stream))
    need(len(steps) == 265 and steps[0] == 0 and steps[-1] == 481685
         and steps == [int(r["step"]) for r in reference if int(r["scheduled"])]
         and all(float(r["time_s"]) == int(r["step"])*parameters["DtFixed"] for r in reference)
         and steps[-1]*parameters["DtFixed"] == parameters["TimeMax"], "Packed timetable differs from the XML clock")
    need(read_json(inputs/"open_completed.json")["closed_pass"]
         and read_json(inputs/"cryer_weak_3d_peak_r1_gates.json")["peak_bounds_pass"], "Missing original closed-state/peak qualification")
    return dict(xml=str(XML), xml_sha256=sha(XML), package=MANIFEST_SHA, physical_profile=values,
                parameters=parameters, operator_dt_mu_lambda_damping=list(actual), planned_steps=steps[-1], planned_frames=269)


def solve(smoke, contract):
    output = SMOKE if smoke else OUTPUT
    mode = "smoke" if smoke else "full"
    need(not output.exists(), f"Preserve existing output: {output}. Use --postprocess to inspect a completed run.")
    output.parent.mkdir(parents=True, exist_ok=True)
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,uuid,driver_version,memory.total", "--format=csv"],
                         text=True, encoding="utf8", errors="replace", capture_output=True, check=True).stdout.splitlines()
    argv = [str(PACKAGE/"weak_full.exe"), mode, str(output)]
    receipt = dict(mode=mode, argv=argv, cwd=str(PACKAGE), started_utc=utc(), gpu_inventory=gpu,
                   cuda_visible_devices=os.environ.get("CUDA_VISIBLE_DEVICES"), contract=contract)
    started = time.perf_counter()
    process = subprocess.Popen(argv, cwd=PACKAGE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf8", errors="replace")
    receipt["child_pid"] = process.pid
    lines = []
    for line in process.stdout:
        print(line, end="", flush=True)
        lines.append(line)
    code = process.wait()
    receipt.update(exit_code=code, finished_utc=utc(), elapsed_seconds=time.perf_counter()-started)
    if output.exists():
        save_json(output/"launch.json", receipt)
        (output/"solver.console.log").write_text("".join(lines), encoding="utf8")
        shutil.copy2(XML, output/XML.name)
    need(code == 0, f"Weak solver exit {code}; preserve partial output and actual_clock.csv in {output}")
    raw = sorted([*output.glob("state_*.bin"), output/"complete.txt", output/"actual_clock.csv"], key=lambda p: p.name)
    seal = dict(mode=mode, package=MANIFEST_SHA, gpu_inventory=gpu,
                cuda_visible_devices=os.environ.get("CUDA_VISIBLE_DEVICES"), utc_finished=receipt["finished_utc"],
                elapsed_seconds=receipt["elapsed_seconds"],
                files=[dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in raw])
    save_json(output/"server_run.json", seal)
    return output


def postprocess(smoke):
    output = SMOKE if smoke else OUTPUT
    destination = output/"review"
    spec = importlib.util.spec_from_file_location("frozen_cryer_weak_review", PACKAGE/"cryer_weak_full_review.py")
    reviewer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reviewer)
    if destination.exists():
        need((destination/"review.json").is_file(), f"Preserve partial review: {destination}; inspect its first error")
        result = read_json(destination/"review.json")
        need(result["mode"] == ("smoke" if smoke else "full") and result["frames"] == (2 if smoke else 269), "Existing review is not this complete trajectory")
        # Fresh reviews hash every payload. Resume derived output using the retained
        # seal and unchanged native sizes/timestamps, without hashing 1.2 GB again.
        seal = read_json(output/"server_run.json")
        mode = "smoke" if smoke else "full"
        reviewed_ns = (destination/"review.json").stat().st_mtime_ns
        need(seal["package"] == MANIFEST_SHA and seal["mode"] == mode
             and (output/"complete.txt").read_text().strip() == mode
             and (output/"server_run.json").stat().st_mtime_ns <= reviewed_ns,
             "Existing return seal is newer than or incompatible with the review")
        need({p.name for p in output.glob("state_*.bin")} ==
             {row["name"] for row in seal["files"] if row["name"].startswith("state_")}, "Native frame set changed after review")
        for row in seal["files"]:
            p = output/row["name"]
            stat = p.stat()
            need(stat.st_size == row["bytes"] and stat.st_mtime_ns <= reviewed_ns, f"Returned state changed after review: {p.name}")
    else:
        reviewer.review(PACKAGE, output, destination, smoke)
    if not smoke:
        plotter = CASE/"support/plot_cryer_weak_full.py"
        need(plotter.is_file(), f"Native review is complete; formal plotting entry is not ready: {plotter}. Run --postprocess later.")
        subprocess.run([sys.executable, "-B", "-X", "utf8", str(plotter), "--output", str(output)], cwd=CASE, check=True)
    print(f"Completed {'smoke' if smoke else 'full'} review: {destination}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="Four original GPU updates from the qualified opening/peak checkpoints")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check-only", action="store_true", help="Read XML and verify the frozen package; no GPU launch or output")
    action.add_argument("--solver-only", action="store_true", help="Run and seal native data, leaving postprocessing for later")
    action.add_argument("--postprocess", action="store_true", help="Review an existing sealed run without rerunning the solver")
    args = parser.parse_args()
    contract = preflight(verify_payload=not args.postprocess)
    if args.check_only:
        print(json.dumps(contract, indent=2))
        return
    if not args.postprocess:
        solve(args.smoke, contract)
    if not args.solver_only:
        postprocess(args.smoke)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr, flush=True)
        raise SystemExit(1)
