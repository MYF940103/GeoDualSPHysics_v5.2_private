"""Reproducible, non-overwriting Release regression for the TPI removal.

Reads existing generated cases/checkpoints; writes only beneath this directory.
Compare identical backends/integrators across versions, not CPU against GPU.
The optional pair_verlet scenario is a failing diagnostic, not an accepted
regression case: both pre-cleanup and new solvers lose particles with this setup.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
CASES = REPO / "examples/Hydromechanic coupling/01_SelfWeightConsolidation_PR/tests/outputs"
PAIR_DIR = CASES / "CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out"
SCENARIOS = {
    "pair_symplectic": (PAIR_DIR / "CaseSWSc2_MLSDirect_Tv2", CASES / "CaseSWSt1_MLSDirect_GPU_out/data", 56, "-symplectic"),
    "pair_verlet": (PAIR_DIR / "CaseSWSc2_MLSDirect_Tv2", CASES / "CaseSWSt1_MLSDirect_GPU_out/data", 56, "-verlet:40"),
    "density_symplectic": (CASES / "CaseSWSc2_PR_Dens_p300_out/CaseSWSc2_PR_Dens_p300", PAIR_DIR / "data", 300, "-symplectic"),
}
VERSIONS = {
    "previous_release": ROOT / "previous_release",
    "precleanup_rebuilt": ROOT / "precleanup_rebuilt",
    "new_release": REPO / "bin/windows",
}
EXES = {"cpu": "DualSPHysics5.2CPU_win64.exe", "gpu": "DualSPHysics5.2_GEO_win64.exe"}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_one(version, backend, scenario):
    prefix, restart, part, integrator = SCENARIOS[scenario]
    executable = VERSIONS[version] / EXES[backend]
    converter = REPO / "bin/windows/PartVTK_win64.exe"
    inputs = [prefix.with_suffix(".xml"), prefix.with_suffix(".bi4"),
              prefix.with_name(prefix.name + "_Normals.nbi4"),
              restart / ("Part_%04d.bi4" % part), restart / ("PartExtra_%04d.bi4" % part)]
    optional_head = restart / "Part_Head.ibi4"
    if optional_head.exists():
        inputs.append(optional_head)
    for path in [executable, converter] + inputs:
        if not path.is_file():
            raise FileNotFoundError(path)
    hashes = {str(path): sha256(path) for path in inputs}
    out = ROOT / "runs" / (version + "__" + backend + "__" + scenario)
    if out.exists():
        raise FileExistsError("Refusing to overwrite regression output: " + str(out))
    out.mkdir(parents=True)
    command = [str(executable), "-" + backend, "-mdbc", "-stable", integrator]
    if backend == "cpu":
        command += ["-ompthreads:1"]
    command += ["-partbegin:%d:0" % part, str(restart), "-tmax:0.002", "-tout:0.0002",
                "-nsteps:2000", "-nortimes:1", "-sv:binx", "-dirdataout", "data", "-svres",
                str(prefix), str(out)]
    record = {"version": version, "backend": backend, "scenario": scenario,
              "command": command, "cwd": str(REPO / "src"),
              "executable_sha256": sha256(executable), "input_sha256": hashes,
              "converter_sha256": sha256(converter)}
    print("RUN " + out.name, flush=True)
    started = time.monotonic()
    with (out / "stdout.txt").open("wb") as log:
        result = subprocess.run(command, cwd=REPO / "src", stdout=log, stderr=subprocess.STDOUT, timeout=180)
    record["wall_seconds"] = time.monotonic() - started
    record["process_exit_code"] = result.returncode
    log_text = (out / "Run.out").read_bytes().decode("gb18030", errors="replace") if (out / "Run.out").exists() else ""
    for key, pattern in {
        "steps": r"Steps of simulation\.+:\s*(\d+)",
        "excluded_particles": r"Excluded particles\.+:\s*(\d+)",
        "dt_min_adjustments": r"DTs adjusted to DtMin\.+:\s*(\d+)",
    }.items():
        match = re.search(pattern, log_text)
        record[key] = int(match.group(1)) if match else None
    record["inputs_unchanged"] = all(sha256(path) == hashes[str(path)] for path in inputs)
    record["solver_passed"] = (result.returncode == 0 and record["steps"] == 2000
                               and record["excluded_particles"] == 0 and record["inputs_unchanged"])
    (out / "run_metadata.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    if not record["solver_passed"]:
        raise RuntimeError("Solver regression failed; inspect " + str(out))
    vtk_dir = out / "vtk"
    vtk_dir.mkdir()
    convert_command = [str(converter), "-dirin", str(out / "data"), "-savevtk", str(vtk_dir / "PartAll"),
                       "-onlytype:+all", "-vars:-all,+idp,+vel,+rhop,+sigma_kk,+sigma_ij,+porepress,+porepress0,+excessporepress,+fstype"]
    record["conversion_command"] = convert_command
    with (out / "conversion_stdout.txt").open("wb") as log:
        converted = subprocess.run(convert_command, cwd=REPO / "src", stdout=log, stderr=subprocess.STDOUT, timeout=120)
    record["conversion_exit_code"] = converted.returncode
    record["vtk_count"] = len(list(vtk_dir.glob("*.vtk")))
    record["passed"] = converted.returncode == 0 and record["vtk_count"] >= 10
    (out / "run_metadata.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print("DONE " + out.name + " " + json.dumps({key: record[key] for key in ["process_exit_code", "steps", "excluded_particles", "vtk_count", "wall_seconds", "passed"]}), flush=True)
    if not record["passed"]:
        raise RuntimeError("Particle conversion failed; inspect " + str(out))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", nargs="+", choices=VERSIONS, default=list(VERSIONS))
    parser.add_argument("--backend", nargs="+", choices=EXES, default=list(EXES))
    parser.add_argument("--scenario", nargs="+", choices=SCENARIOS,
                        default=["pair_symplectic", "density_symplectic"])
    args = parser.parse_args()
    for backend in args.backend:
        for version in args.version:
            for scenario in args.scenario:
                run_one(version, backend, scenario)


if __name__ == "__main__":
    main()
