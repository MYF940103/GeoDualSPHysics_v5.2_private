"""Run the manufactured TPI rows using the VS Release or ReleaseCPU project objects."""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpu-only", action="store_true")
    cpu_only = parser.parse_args().cpu_only
    config = "ReleaseCPU" if cpu_only else "Release"
    tests = Path(__file__).resolve().parents[1]
    repo = tests.parents[3]
    src = repo / "src"
    vs = src / "VS"
    tlog = vs / f"Intermediate/DualSPHysics_{config}_x64/DualSPHysics.tlog"
    lines = (tlog / "link.command.1.tlog").read_text(encoding="utf-16").splitlines()
    assert lines[0].startswith("^")
    objects = [Path(s) for s in lines[0][1:].split("|")]
    active_sources = [("jsphcpu_porepressure.obj", "JSphCpu_porepressure.cpp")]
    if not cpu_only:
        active_sources.append(("jsphgpu_ker.cu.obj", "JSphGpu_ker.cu"))
    for name, source in active_sources:
        match, = [p for p in objects if p.name.lower() == name]
        if match.stat().st_mtime_ns < (src / "source" / source).stat().st_mtime_ns:
            raise RuntimeError(f"Rebuild the {config} project before testing {source}")

    work = Path(tempfile.mkdtemp(prefix="tpi_rows_", dir=tests / "outputs"))
    cl = shutil.which("cl.exe")
    link = shutil.which("link.exe")
    assert cl and link, "Run inside the VS x64 developer shell"
    flags = (tlog / "CL.command.1.tlog").read_text(encoding="utf-16").splitlines()
    main_flags = next(flags[i+1] for i in range(len(flags)-1) if flags[i].endswith("\\MAIN.CPP"))
    includes = re.findall(r'/I"([^"]+)"', main_flags, flags=re.I)
    obj = work / "rows.obj"
    binary = work / "rows.exe"
    fixture = Path(__file__).with_suffix(".cpp")
    subprocess.run([cl, "/c", "/nologo", "/O2", "/MT", "/EHsc", "/fp:precise", "/openmp",
                    *([] if cpu_only else ["/D_WITHGPU"]), "/DWIN32", "/D_CONSOLE", "/I"+str(src / "source"),
                    *["/I"+s for s in includes], "/Fo"+str(obj), str(fixture)], check=True)
    # Link against the genuine project object set, substituting only main.
    libs = re.findall(r'(?:/LIBPATH:(?:"[^"]+"|\S+)|(?<!\S)[^"\s]+\.LIB)(?=\s)', lines[1], flags=re.I)
    args = ["/nologo", "/MACHINE:X64", "/SUBSYSTEM:CONSOLE", "/OPT:REF", "/LTCG", f'/OUT:"{binary}"', *libs]
    args += [f'"{obj if p.name.lower()=="main.obj" else p}"' for p in objects]
    rsp = work / "link.rsp"
    rsp.write_text("\n".join(args), encoding="utf-16")
    subprocess.run([link, "@"+str(rsp)], cwd=vs, check=True)
    env = {**os.environ, "PATH": str(repo / "bin/windows")+os.pathsep+os.environ["PATH"]}
    proc = subprocess.run([binary], cwd=work, env=env, capture_output=True, text=True)
    (work / "stdout.txt").write_text(proc.stdout, encoding="utf-8")
    (work / "stderr.txt").write_text(proc.stderr, encoding="utf-8")
    proc.check_returncode()
    data = list(csv.DictReader(io.StringIO(proc.stdout[proc.stdout.index("field,id,"):])))
    assert len(data) == 30
    result = {"component": "tpi_variable_k_rows", "configuration": config, "passed": True, "rows": len(data),
              "scenarios": list(dict.fromkeys(row["field"] for row in data)),
              "max_cpu_error_Pa": max(abs(float(r["cpu_Pa"])-float(r["reference_Pa"])) for r in data),
              "max_gpu_error_Pa": None if cpu_only else max(abs(float(r["gpu_Pa"])-float(r["reference_Pa"])) for r in data),
              "minimum_omitted_chain_error_Pa": min(abs(float(r["reference_Pa"])-float(r["omit_chain_Pa"]))
                  for r in data if r["field"] in ("affine_p_J","affine_J_acceleration")),
              "max_wrong_k_diagonal_and_residual_error_Pa": max(abs(float(r["reference_Pa"])-float(r["constant_k_row_Pa"]))
                  for r in data if r["field"]=="quadratic_uniform_J1125"),
              "per_row_threshold_Pa": 0.0002, "output": str(work.relative_to(tests))}
    (work / "result.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
