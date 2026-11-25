"""Run the one-factor C08 TPI surface-pressure comparison after the original pair is reviewed."""
import argparse
import difflib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from c08_m0_gpu_coupled_r1 import BUILD as CUDA_SOURCE, CUDA, SRC, once, sha
from c08_psi25_tpi_build import OUT as CONTROL_BUILD, RUNTIME
from c08_psi25_tpi_run import CAP, CASE, PRE, SEED, TESTS, expected_xml, identity, now, record

TAG = "c08_psi25_tpi_surface_zero_r1"
BUILD = TESTS/"outputs"/(TAG+"_build_r2")
PROGRAM = BUILD/"C08Psi25SurfaceZero.exe"
LOG = TESTS/"logs"
CONTROL = "c08_psi25_tpi_paper_b004_r1"
PAIR = "c08_psi25_tpi_paper_pair_r1"


def load(path):
    return json.loads(path.read_text(encoding="utf8"))


def invoke(args, log, cwd=CASE, env=None):
    with log.open("xb") as stdout:
        return subprocess.run(args, cwd=cwd, env=env, stdout=stdout, stderr=subprocess.STDOUT).returncode


def build():
    source = CUDA_SOURCE/"JSphGpu_ker.cu"
    original_cuda = load(CUDA_SOURCE/"build.json")
    control = load(CONTROL_BUILD/"build.json")
    exe = Path(control["exe"])
    header = CUDA_SOURCE/"JSphGpu_ker.h"
    pressure_row = TESTS/"support/c08_m0_pressure_row.cuh"
    for path, expected in ((source, original_cuda["sources"][source.name]["private"]),
                           (header, original_cuda["sources"][header.name]["private"]),
                           (pressure_row, original_cuda["gpu_row"]), (exe, control["sha256"])):
        if sha(path) != expected:
            raise ValueError(f"Frozen control input differs: {path}")
    build_inputs = [(p, identity(p)) for p in (source, header, pressure_row, exe)]
    before = source.read_text(encoding="utf8")
    start = before.index("__global__ void KerApplyFreeSurfacePorePressure(")
    end = before.index("\nvoid ApplyFreeSurfacePorePressure(", start)
    after = before[:start] + once(before[start:end], "isfinite(porepress[p]) && porepress[p]>0",
                                  "isfinite(porepress[p])") + before[end:]
    old_link = (CONTROL_BUILD/"link.rsp").read_text(encoding="utf8").splitlines()
    objects = [Path(line.strip('"')) for line in old_link[1:]]
    original_obj = CUDA_SOURCE/"JSphGpu_ker.cu.obj"
    if len(objects) != 113 or objects.count(original_obj) != 1:
        raise ValueError("The original GPU translation unit is not uniquely bound")
    if any(p.stat().st_mtime_ns > exe.stat().st_mtime_ns for p in objects):
        raise ValueError("A control linker input is newer than the sealed control")
    cl, link = shutil.which("cl.exe"), shutil.which("link.exe")
    if not cl or not link:
        raise RuntimeError("The MSVC x64 developer environment is required")

    BUILD.mkdir()
    private = BUILD/source.name
    private.write_text(after, encoding="utf8")
    # The frozen header tree does not include the InOut kernel text compiled in this unit.
    inout = BUILD/"JSphGpu_InOut_iker.cu"
    inout.write_bytes(subprocess.check_output(
        ["git", "show", control["header_commit"]+":src/source/"+inout.name], cwd=SRC))
    (BUILD/"changes.diff").write_text("".join(difflib.unified_diff(
        before.splitlines(True), after.splitlines(True), "control/"+source.name, "candidate/"+source.name)),
        encoding="utf8")
    obj = BUILD/original_obj.name
    include = (CUDA_SOURCE, TESTS/"support", CONTROL_BUILD/"src/source", CUDA/"include")
    compile_cmd = [str(CUDA/"bin/nvcc.exe"), "-gencode=arch=compute_86,code=sm_86",
        "-gencode=arch=compute_86,code=compute_86", "--use-local-env", "-ccbin", str(Path(cl).parent),
        "-x", "cu", *["-I"+str(p) for p in include], "-maxrregcount=0", "--machine", "64", "--compile",
        "-cudart", "static", "-use_fast_math", "-Xcompiler", "/wd4267", "-Wno-deprecated-gpu-targets",
        "-D_WITHGPU", "-DWIN32", "-D_CONSOLE", "-D_VC80_UPGRADE=0x0710", "-D_MBCS",
        "-Xcompiler", "/EHsc /W3 /nologo /O2 /FS /MT", "-o", str(obj), str(private)]
    rc = invoke(compile_cmd, BUILD/"nvcc.log", SRC/"VS")
    record(BUILD/"compile.json", dict(command=compile_cmd, exit_code=rc))
    if rc:
        raise RuntimeError(f"NVCC exit {rc}; see {BUILD/'nvcc.log'}")

    objects[objects.index(original_obj)] = obj
    head = old_link[0]
    for key, suffix in (("OUT",".exe"), ("PDB",".pdb"), ("LTCGOUT",".iobj"), ("IMPLIB",".lib")):
        head, count = re.subn("/"+key+r':"[^"]+"',
                             lambda _: '/'+key+':"'+str(PROGRAM.with_suffix(suffix))+'"', head)
        if count != 1:
            raise ValueError(f"Unexpected link parameter {key}")
    rsp = BUILD/"link.rsp"
    rsp.write_text("\n".join([head, *['"'+str(p)+'"' for p in objects]]), encoding="utf8")
    link_cmd = [link, "@"+str(rsp)]
    rc = invoke(link_cmd, BUILD/"link.log", SRC/"VS")
    record(BUILD/"link.json", dict(command=link_cmd, exit_code=rc))
    if rc:
        raise RuntimeError(f"Link exit {rc}; see {BUILD/'link.log'}")
    for name in RUNTIME:
        shutil.copy2(CONTROL_BUILD/name, BUILD/name)
    if any(identity(p) != saved for p, saved in build_inputs):
        raise ValueError("An input changed while building the candidate")
    record(BUILD/"build.json", dict(built_utc=now(), program=str(PROGRAM),
        executable=identity(PROGRAM), program_sha256=sha(PROGRAM), input_files=[v for _,v in build_inputs],
        original_link=str(CONTROL_BUILD/"link.rsp"), headers=control["header_commit"],
        changed_cuda_source=identity(private), source_sha256=sha(private),
        inline_cuda=identity(inout), inline_cuda_sha256=sha(inout),
        unchanged_objects=112, changed_cuda_objects=1, surface_zero="completed_substep_all_finite_FS2_or_FS3"))


def await_pair():
    terminal = LOG/(PAIR+".terminal.json")
    deadline = time.monotonic()+2*3600
    while not terminal.exists():
        if time.monotonic() > deadline:
            raise TimeoutError(f"No original pair completion record at {terminal}")
        time.sleep(25)
    # The terminal file is written once. An incomplete in-progress JSON isn't a terminal finding.
    for _ in range(10):
        try:
            seal = load(terminal)
            break
        except json.JSONDecodeError:
            time.sleep(1)
    else:
        raise ValueError(f"Unreadable original pair completion record at {terminal}")
    if seal["exit_code"] or any(seal["results"][x] != dict(stage="reviewed", exit_code=0)
                               for x in ("b0", "b004", "figures")):
        raise ValueError("Original beta pair needs review before the surface-boundary test")
    for label in ("b0","b004"):
        receipt = load(LOG/f"c08_psi25_tpi_paper_{label}_r1.native_review.json")
        if receipt["passed"] is not True or receipt["frames"] != 132:
            raise ValueError(f"Incomplete original beta={label} native review")
    return terminal


def script(name, log, *args):
    rc = invoke([sys.executable, "-B", "-X", "utf8", str(TESTS/"support"/name), *args], log)
    if rc:
        raise RuntimeError(f"{name} exit {rc}; see {log}")


def await_build():
    ready = BUILD/"build.json"
    deadline = time.monotonic()+1800
    while not ready.is_file():
        for step in ("compile","link"):
            receipt = BUILD/(step+".json")
            if receipt.is_file():
                try:
                    rc = load(receipt)["exit_code"]
                except json.JSONDecodeError:
                    continue
                if rc:
                    raise RuntimeError(f"Candidate {step} exit {rc}; see {receipt}")
        if time.monotonic() > deadline:
            raise TimeoutError(f"No completed candidate build at {ready}")
        time.sleep(15)


def solve(pair):
    build_file = BUILD/"build.json"
    proof = load(build_file)
    info = load(SEED.parent/"inputs.json")
    if (identity(PROGRAM)!=proof["executable"] or identity(PRE)!=info["source"]
            or any(identity(Path(i["path"]))!=i for i in info["inputs"])
            or SEED.with_suffix(".xml").read_bytes()!=expected_xml()):
        raise ValueError("The candidate executable or identical receiver inputs changed")
    ctrl = load(LOG/(CONTROL+".call.json"))
    old = ctrl["command"]
    if ctrl["returncode"] != 0 or old[4] != str(SEED) or old[-1] != "-nsteps:"+str(CAP["paper"]):
        raise ValueError("Wrong original beta=.04 receiver call")
    folder = TESTS/"outputs"/TAG
    cmd = [str(PROGRAM), *old[1:5], str(folder), *old[6:]]
    start = dict(tag=TAG, cap=CAP["paper"], beta=.04, command=cmd, PRE=str(PRE), exe=proof["executable"],
           source=info["source"], build=str(build_file), pair=identity(pair),
           surface_zero=True, start_utc=now(), owner_pid=os.getpid())
    folder.mkdir()
    with (LOG/(TAG+".console.log")).open("xb") as stream:
        with subprocess.Popen(cmd, cwd=CASE, stdout=stream, stderr=subprocess.STDOUT,
                              env=dict(os.environ, C08_PRIVATE_BETA="0.04")) as child:
            record(LOG/(TAG+".start.json"), dict(start, solver_pid=child.pid))
            rc = child.wait()
    record(LOG/(TAG+".call.json"), dict(start, solver_pid=child.pid, returncode=rc, end_utc=now()))
    if rc:
        raise RuntimeError(f"GPU solver exit {rc}; see {folder/'Run.out'}")
    return folder


def run(codex, thread):
    if codex and (not codex.is_file() or not thread or thread != os.environ.get("CODEX_THREAD_ID")):
        raise ValueError("Use the current thread for the single completion notification")
    record(LOG/(TAG+".owner.json"), dict(pid=os.getpid(), start_utc=now(), thread=thread,
                                       build=str(BUILD/"build.json"), dependency=PAIR))
    stage = "original_pair"
    try:
        pair = await_pair()
        stage = "build"
        await_build()
        stage = "solver"
        folder = solve(pair)
        stage = "native"
        script("c08_psi25_tpi_native.py", LOG/(TAG+".native.log"), TAG, "--window", "paper",
               "--beta", "0.04", "--prefix", CONTROL, "--surface-zero")
        stage = "figures"
        runs = ("--run", "TPI beta=0.04 (positive clamp)", str(TESTS/"outputs"/CONTROL),
                "--run", "TPI beta=0.04 (surface p=0)", str(folder))
        script("c08_psi25_tpi_shape.py", LOG/(TAG+".shape.log"), "--tag", "paper_surface_zero_r1", *runs)
        script("c08_psi25_tpi_fields.py", LOG/(TAG+".fields.log"), "--tag", "paper_surface_zero_r1", *runs)
        script("c08_psi25_tpi_mobilization.py", LOG/(TAG+".mobilization.log"),
               "--run", "positive_clamp", str(TESTS/"outputs"/CONTROL), "--run", "surface_zero", str(folder),
               "--output", str(TESTS/"figures"/(TAG+"_mobilization.csv")))
        result = dict(stage="pending_physical_review", exit_code=0)
    except (OSError, ValueError, RuntimeError) as error:
        result = dict(stage=stage, exit_code=1, error=str(error))
    terminal = LOG/(TAG+".terminal.json")
    record(terminal, dict(**result, ended_utc=now()))
    if codex:
        record(LOG/(TAG+".queue_attempt.json"), dict(thread=thread, terminal=str(terminal), time_utc=now()))
        message = (f"C08 +2.5 degree TPI beta=.04 surface p=0 control is terminal: {terminal}. "
                   "Read actual call, native and figure receipts. Report same-time comparison with positive-only beta=.04 "
                   "and Lian. Retain failures and partials. Repair derived outputs only if needed, never rerun solver "
                   "or resend/rearm this completion owner.")
        try:
            queue = subprocess.run([str(codex), "queue", "--thread", thread, "--message", message],
                                   timeout=45, capture_output=True)
            notification = dict(exit_code=queue.returncode)
        except (OSError, subprocess.TimeoutExpired) as error:
            notification = dict(status="delivery_unknown", error=str(error))
        record(LOG/(TAG+".queue_result.json"), notification)
    return result["exit_code"]


if __name__ == "__main__":
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("action", choices=("build","run"))
    args.add_argument("--codex", type=Path)
    args.add_argument("--thread")
    opts = args.parse_args()
    if opts.action == "build":
        build()
    else:
        sys.exit(run(opts.codex, opts.thread))
