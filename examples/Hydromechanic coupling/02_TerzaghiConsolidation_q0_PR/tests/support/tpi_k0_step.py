"""Link the CPU/GPU step regression against the current canonical Release object list."""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import subprocess


def write_receipt(stdout, tlog, result):
    # The four deliberately rejected locked steps are printed by the production exception handler.
    lines = stdout.splitlines()
    data = [line for line in lines if line.startswith(("tpi,", "0,", "1,"))]
    rows = list(csv.DictReader(data))
    if len(rows) != 8 or any(not row["cpu_step_s"] or not row["gpu_step_s"] for row in rows):
        raise ValueError("Missing numerical fixture rows")
    rejections = [line for line in lines if line.startswith("*** Exception")]
    if (len(rejections) != 4 or sum("JSphCpuSingle::DtVariable" in line for line in rejections) != 2
        or sum("JSphGpuSingle::DtVariable" in line for line in rejections) != 2
        or sum("current step or DtMin exceeds" in line for line in lines) != 4):
        raise ValueError("Unexpected locked-step rejection count or cause")
    with result.open("x", encoding="utf-8") as output:
        json.dump({"backend":"CPU and GPU linked from canonical GPU Release", "object_list":str(tlog),
                   "material_J":[.88, 1., 1.1, 1.22], "excluded_J":[0.,0.], "relative_tolerance":2e-12,
                   "locked_step_rejections":len(rejections), "rows":rows, "passed":True}, output, indent=2)
    print(result)


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True, help="new output folder")
    parser.add_argument("--result", type=Path, required=True, help="new JSON receipt")
    args = parser.parse_args()
    work, result = args.work.resolve(), args.result.resolve()
    if result.exists():
        raise FileExistsError(result)
    work.mkdir(parents=True, exist_ok=False)
    support = Path(__file__).resolve().parent
    repo = support.parents[4]
    src, vs = repo / "src" / "source", repo / "src" / "VS"
    tlog = vs / "Intermediate" / "DualSPHysics_Release_x64" / "DualSPHysics.tlog" / "link.command.1.tlog"
    lines = tlog.read_text(encoding="utf-16").splitlines()
    objects = [Path(p) for p in lines[0].removeprefix("^").split("|")]
    if sum(p.name.lower() == "main.obj" for p in objects) != 1:
        raise ValueError("Canonical Release object list has no unique main")
    required = ["jsphcpu.obj", "jsphgpu.obj", "jsphgpu_ker.cu.obj"]
    for suffix in required:
        path, = [p for p in objects if p.name.lower() == suffix]
        source = src / {"jsphcpu.obj":"JSphCpu.cpp","jsphgpu.obj":"JSphGpu.cpp",
                        "jsphgpu_ker.cu.obj":"JSphGpu_ker.cu"}[suffix]
        if path.stat().st_mtime_ns < source.stat().st_mtime_ns:
            raise ValueError(f"Rebuild Release before testing {source.name}")
    cuda = Path(os.environ["CUDA_PATH_V11_7"])
    obj, exe = work / "step.obj", work / "step.exe"
    subprocess.run(["cl", "/nologo", "/c", "/EHsc", "/O2", "/MT", "/openmp",
                    "/D_WITHGPU", "/DWIN32", "/D_CONSOLE", "/I"+str(src),
                    "/I"+str(cuda/"include"), str(support/"tpi_k0_step.cpp"), "/Fo"+str(obj)],
                   cwd=work, check=True)
    libraries = re.findall(r'(?<![\w.])[\w]+\.LIB\b', lines[1].upper().split("/MANIFEST")[0])
    options = ["/NOLOGO", "/LTCG", "/SUBSYSTEM:CONSOLE", "/OPT:REF", "/MACHINE:X64",
               "/LIBPATH:"+str(cuda/"lib"/"x64"), "/LIBPATH:"+str(repo/"src"/"lib"/"vs2022"),
               "/OUT:"+str(exe), str(obj)]
    options.extend(str(p) for p in objects if p.name.lower() != "main.obj")
    options.extend(libraries)
    response = work/"link.rsp"
    response.write_text("\n".join('"'+s+'"' for s in options), encoding="ascii")
    subprocess.run(["link", "@"+str(response)], cwd=work, check=True)
    env = os.environ.copy()
    env["PATH"] = str(repo/"bin"/"windows")+os.pathsep+str(cuda/"bin")+os.pathsep+env["PATH"]
    proc = subprocess.run([str(exe)], cwd=work, env=env, capture_output=True, text=True)
    (work/"stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (work/"stderr.txt").write_text(proc.stderr, encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"fixture exit {proc.returncode}: {proc.stdout} {proc.stderr}")
    write_receipt(proc.stdout, tlog, result)


if __name__ == "__main__":
    run()
