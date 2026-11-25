"""Fresh positive-dilatancy receivers. No preload solve. Each tag is consumed once."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

TESTS = Path(__file__).resolve().parents[1]
CASE = TESTS.parent
STEM = "CaseLianCollapse_psi2p5"
ORIGINAL = CASE / (STEM + "_GPU_out") / STEM
PRE = CASE / (STEM + "_pre_GPU_out") / "data/Part_1000.bi4"
SEED = TESTS / "outputs/c08_psi25_tpi_seed_r1" / STEM
EXE = TESTS / "outputs/c08_psi25_tpi_build_r2/C08Psi25Tpi.exe"
CAP = {"short": 2000208, "paper": 2240200}


def now():
    return datetime.now(timezone.utc).isoformat()


def record(path, data):
    with path.open("x", encoding="utf8") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)


def identity(path):
    info = path.stat()
    return dict(path=str(path), bytes=info.st_size, mtime_ns=info.st_mtime_ns)


def expected_xml():
    doc = ET.parse(ORIGINAL.with_suffix(".xml"))
    special = doc.find("execution/special")
    model = special.find("hydromechanics/HydroMechModel")
    wall = special.find("gravitypreload")
    material = special.find("soils")
    declared = {name: float(material.find(name).get("value")) for name in ("coh", "dlt", "DilationDecay")}
    if (declared != dict(coh=5000., dlt=2.5, DilationDecay=.2) or model.get("value") != "1"
            or (ORIGINAL.parent / wall.get("statefile")).resolve() != PRE
            or not PRE.is_file() or special.find("drainage").get("mode") != "freeSeepage"):
        raise ValueError("Saved receiver geometry/material/handoff definition differs")
    if json.loads((PRE.parent.parent / "provenance.json").read_text())["state"] != "completed":
        raise ValueError("No completed DDT0 preload")
    model.set("value", "2")
    model.set("comment", "Three-round TPI in the positive-dilatancy receiver")
    wall.set("statefile", str(PRE))
    return ET.tostring(doc.getroot(), encoding="utf-8", xml_declaration=True)


def prepare():
    xml = expected_xml()
    SEED.parent.mkdir()
    SEED.with_suffix(".xml").write_bytes(xml)
    for suffix in (".bi4", "_Normals.nbi4"):
        shutil.copy2(str(ORIGINAL) + suffix, str(SEED) + suffix)
    record(SEED.parent / "inputs.json", dict(source=identity(PRE), baseline=identity(ORIGINAL.with_suffix(".xml")),
           inputs=[identity(p) for p in SEED.parent.iterdir()], prepared_utc=now()))


def run(window, beta):
    label = "b0" if beta == "0" else "b004"
    tag = f"c08_psi25_tpi_{window}_{label}_r1"
    start, console, call = [TESTS / "logs" / (tag + end) for end in (".start.json", ".console.log", ".call.json")]
    directory = TESTS / "outputs" / tag
    inputs = json.loads((SEED.parent / "inputs.json").read_text())
    items = inputs["inputs"] + [inputs["source"]]
    if any(identity(Path(saved["path"])) != saved for saved in items) or SEED.with_suffix(".xml").read_bytes()!=expected_xml():
        raise ValueError("Prepared input changed")
    if window == "paper":
        for other in ("b0", "b004"):
            short = TESTS / "logs" / f"c08_psi25_tpi_short_{other}_r1.native_review.json"
            check = json.loads(short.read_text())
            if check.get("passed") is not True:
                raise ValueError(f"Review short result first: {short}")
    if directory.exists() or any(p.exists() for p in (start, console, call)):
        raise FileExistsError(f"Inspect retained run {tag}")
    args = [str(EXE), "-gpu", "-stable", "-mdbc_freeslip:1", str(SEED), str(directory),
            "-dirdataout", "data", "-svres", "-nsteps:" + str(CAP[window])]
    info = dict(tag=tag, cap=CAP[window], beta=float(beta), command=args, PRE=str(PRE), exe=identity(EXE),
                source=inputs["source"], start_utc=now(), owner_pid=os.getpid())
    directory.mkdir()
    env = dict(os.environ, C08_PRIVATE_BETA=beta)
    with console.open("xb") as stdout:
        child = subprocess.Popen(args, cwd=CASE, env=env, stdout=stdout, stderr=subprocess.STDOUT)
        info["solver_pid"] = child.pid
        record(start, info)
        rc = child.wait()
    record(call, dict(**info, returncode=rc, end_utc=now()))
    if rc:
        raise SystemExit(rc)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("window", choices=("prepare", *CAP))
    parser.add_argument("--beta", choices=("0", "0.04"))
    opts = parser.parse_args()
    if opts.window == "prepare":
        prepare()
    elif opts.beta is None:
        parser.error("Select --beta 0 or 0.04")
    else:
        run(opts.window, opts.beta)
