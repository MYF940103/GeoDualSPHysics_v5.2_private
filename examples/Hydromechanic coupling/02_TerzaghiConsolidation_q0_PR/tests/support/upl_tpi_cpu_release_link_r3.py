"""One independently admitted link-only recovery of the failed P1 Release r2.

Do not compile either successful r2 TU, rewrite its failure, run help/solver,
decode native data, or follow a successful link with another action.
"""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import upl_tpi_cpu_build_r2 as b

T, L, S, R = b.T, b.L, b.S, b.R
TAG = "upl_tpi_cpu_release_link_r3"
SCRIPT = Path(__file__).resolve()
NOTE = T / "notes" / (TAG + ".md")
OLD = L / "upl_tpi_cpu_ReleaseCPU_r2.build.json"
FAILED_LINK = L / "upl_tpi_cpu_ReleaseCPU_r2.link.call.json"
CL_CALLS = [L / ("upl_tpi_cpu_ReleaseCPU_r2." + name + ".call.json")
            for name in ("JSphCpu", "JSphCpuSingle")]
PREP = L / "upl_tpi_cpu_r1.prepare.json"
BASE = L / "upl_spr_av_ReleaseCPU_r1.build.json"
OLD_ROOT = T / "outputs/upl_tpi_cpu_ReleaseCPU_r2"
ROOT = T / "outputs" / TAG
CHECK = L / (TAG + ".build.json")
EXE = ROOT / "out/DualSPHysics5.2CPU_win64.exe"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-authorized", action="store_true")
    parser.add_argument("--admission", required=True, type=Path)
    args = parser.parse_args()
    b.need(args.execution_authorized, "Independent root link-only admission required")
    b.need(not ROOT.exists() and not CHECK.exists(), "Existing recovery/failure output is protected")
    admission_entry = b.stat(args.admission)
    admission = b.read(args.admission)
    b.need(admission.get("stage") == TAG + ".admission" and admission.get("passed") is True
           and admission.get("link_only") is True, "Exact reviewed root link-only admission required")
    frozen = {str(Path(x["path"]).resolve()): x for x in admission["inputs"]}

    def pin(path):
        key = str(Path(path).resolve())
        b.need(key in frozen, "Consumed input absent from root link admission: " + key)
        return b.same(frozen[key])

    def unchanged():
        for entry in frozen.values():
            b.same(entry)
        b.same(admission_entry)

    for p in (SCRIPT, NOTE, Path(b.__file__), OLD, FAILED_LINK, PREP, BASE, b.VCVARS, *CL_CALLS):
        pin(p)
    old, failed, prep, base = b.read(OLD), b.read(FAILED_LINK), b.read(PREP), b.read(BASE)
    b.need(old.get("passed") is False and old.get("configuration") == "ReleaseCPU"
           and failed.get("passed") is False
           and failed.get("actual_Popen_wait_exit") == failed.get("actual_Win32_exit") == 1104,
           "The retained r2 failure must remain the actual LNK1104 link failure")
    pin(failed["log"]["path"])
    failed_text = Path(failed["log"]["path"]).read_text(encoding="mbcs", errors="replace")
    b.need("LNK1104" in failed_text and "libcpmt.lib" in failed_text.lower(),
           "Original actual link failure was not the recorded missing implicit C++ CRT library")
    b.need(prep.get("passed") is True and prep.get("class_or_header_ABI_changed") is False
           and base.get("passed") is True and base.get("object_count") == 86,
           "Original unchanged-ABI source preparation and A object recipe required")
    source = Path(prep["source_root"]).resolve()
    for entry in prep["files"]:
        pin(entry["path"])
    pin(prep["source_diff"]["path"])
    b.need(len(prep["files"]) == 266, "Original frozen source closure differs")
    successful_compile = []
    new_objects = []
    dependencies = []
    for path, leaf in zip(CL_CALLS, ("JSphCpu.cpp", "JSphCpuSingle.cpp")):
        call = b.read(path)
        b.need(call.get("passed") is True
               and call.get("actual_Popen_wait_exit") == call.get("actual_Win32_exit") == 0
               and Path(call["child"]["exe"]).resolve() == Path(call["program"]["path"]).resolve()
               and Path(call["arguments"][-1]).resolve() == source / leaf,
               "Both original r2 TU compilations must have genuine successful exits")
        pin(call["program"]["path"])
        pin(call["log"]["path"])
        obj = OLD_ROOT / "int" / (Path(leaf).stem + ".obj")
        dep = OLD_ROOT / "int" / (leaf + ".dependencies.json")
        pin(obj)
        pin(dep)
        wanted_fo = "/fo" + str(obj).lower()
        b.need(any(str(x).lower() == wanted_fo for x in call["arguments"]),
               "The retained object was not the actual successful compiler output")
        data = b.read(dep)["Data"]
        includes = {Path(x).resolve() for x in data["Includes"]}
        b.need(Path(data["Source"]).resolve() == source / leaf
               and source / "upl_tpi_cpu_r1.h" in includes
               and source / "JSphCpu.h" in includes and source / "JSph.h" in includes
               and all(not x.is_relative_to((S / "source").resolve()) for x in includes),
               "Retained compile dependency proof missed the prepared header/source or used live headers")
        new_objects.append(obj.resolve())
        successful_compile.append(pin(path))
        dependencies.append(pin(dep))
    # Preserve these exact object paths/order from the actual failed invocation.
    original_args = failed["arguments"]
    objects = [Path(x).resolve() for x in original_args if str(x).lower().endswith(".obj") and not str(x).startswith("/")]
    base_objects = {Path(x["path"]).resolve() for x in base["objects"]}
    expected_names = {x.lower() for x in base["expected_object_basenames"]}
    b.need(len(objects) == len(set(objects)) == 86 and {p.name.lower() for p in objects} == expected_names
           and set(new_objects).issubset(objects)
           and len([p for p in objects if p in base_objects]) == 84
           and all(p in base_objects or p in new_objects for p in objects),
           "Failed r2 link did not use exactly the reviewed 84 A plus two successful private objects")
    object_bindings = [pin(p) for p in objects]
    libraries = [pin(x["path"]) for x in base["libraries"]]
    runtime = [pin(x["copy"]["path"]) for x in base["runtime"]]
    linker = Path(failed["program"]["path"]).resolve()
    pin(linker)
    canonical_before = [b.stat(p) for p in (R / "bin/windows").glob("DualSPHysics*.exe")]
    unchanged()
    ROOT.mkdir()
    (ROOT / "out").mkdir()
    (ROOT / "int").mkdir()
    result = dict(stage=TAG, passed=False, configuration="ReleaseCPU", root_admission=admission_entry,
                  failed_r2_preserved=pin(OLD), original_failed_link=pin(FAILED_LINK),
                  successful_original_CL_calls=successful_compile, original_dependencies=dependencies,
                  original_source_preparation=pin(PREP), original_A_build=pin(BASE),
                  actual_CPU_build_helper=pin(Path(b.__file__)),
                  compile_invocations=0, link_invocations=0, program_help_invocations=0,
                  solver_invocations=0, native_invocations=0, physical_acceptance=False,
                  following_action_launched=False, objects=object_bindings, calls=[],
                  legacy_source_object_or_BI4_SHA_scans=0)
    try:
        batch = ROOT / "load_environment.cmd"
        with batch.open("xb") as f:
            f.write(("@echo off\r\ncall \"" + str(b.VCVARS) +
                     "\" x64 -vcvars_ver=14.36 >nul\r\n"
                     "if errorlevel 1 exit /b %errorlevel%\r\nset\r\n").encode("mbcs"))
        call, raw = b.invoke(TAG + ".environment", [os.environ.get("COMSPEC", "C:/Windows/System32/cmd.exe"),
                             "/d", "/s", "/c", batch.name], ROOT, os.environ.copy(), True)
        result["calls"].append(call)
        env = {k.upper(): v for k, v in os.environ.items()}
        env.update((k.upper(), v) for k, v in (line.split("=", 1) for line in raw.decode("mbcs").splitlines()
                   if "=" in line and not line.startswith("=")))
        env.pop("CL", None)
        env.pop("_CL_", None)
        b.need(env.get("VCTOOLSVERSION") == "14.36.32532", "Retained v143 compiler/linker toolset changed")
        vcvars_lib = env.get("LIB", "")
        b.need(bool(vcvars_lib), "Actual vcvars LIB is missing; never replace it with the incomplete A list")
        vcvars_dirs = [Path(x).resolve() for x in vcvars_lib.split(";") if x]
        crt = next((p / "libcpmt.lib" for p in vcvars_dirs if (p / "libcpmt.lib").is_file()), None)
        b.need(crt is not None, "The genuine retained vcvars LIB does not expose libcpmt.lib")
        pin(crt)
        # Keep every original vcvars search directory first, then append the A
        # explicit-library directories. Do not drop implicit CRT/SDK libraries.
        search = list(dict.fromkeys([str(p) for p in vcvars_dirs] +
                                   [str(Path(x["path"]).parent) for x in libraries]))
        env["LIB"] = ";".join(search)
        result.update(environment_batch=b.stat(batch), VCTOOLSVERSION=env["VCTOOLSVERSION"],
                      actual_vcvars_LIB_dirs=[str(p) for p in vcvars_dirs], effective_LIB_dirs=search,
                      actual_vcvars_LIB_preserved=True, first_existing_libcpmt_search_candidate=pin(crt),
                      libcpmt_candidate_is_search_evidence_not_linker_read_trace=True)
        redirects = {"/out": EXE, "/pdb": ROOT / "out/candidate.pdb",
                     "/implib": ROOT / "out/candidate.lib", "/ltcgout": ROOT / "int/candidate.iobj",
                     "/ilk": ROOT / "int/candidate.ilk", "/pgd": ROOT / "int/candidate.pgd"}
        new_args = []
        for arg in original_args:
            prefix = arg.split(":", 1)[0].lower()
            new_args.append(arg.split(":", 1)[0] + ":" + str(redirects[prefix])
                            if prefix in redirects and ":" in arg else arg)
        b.need([Path(x).resolve() for x in new_args if str(x).lower().endswith(".obj") and not str(x).startswith("/")] == objects,
               "Link-only recovery changed an object path or object ordering")
        result["linker"] = pin(linker)
        result["link_attempts"] = 1
        result["original_direct_link_call_path"] = str(L / (TAG + ".link.call.json"))
        call, _ = b.invoke(TAG + ".link", [str(linker), *new_args], S / "VS", env)
        result["calls"].append(call)
        result["link_invocations"] = 1
        copies = []
        for item in runtime:
            dest = EXE.parent / Path(item["path"]).name
            shutil.copy2(item["path"], dest)
            copies.append(dict(source=item, destination=b.stat(dest)))
        unchanged()
        for item in canonical_before:
            b.same(item)
        program = b.stat(EXE)
        program["sha256"] = hashlib.sha256(EXE.read_bytes()).hexdigest()
        result.update(passed=True, program=program, runtime=copies, original_object_paths_and_stats_unchanged=True,
                      original_failed_r2_and_source_stats_unchanged=True, canonical_programs_stats_unchanged=True,
                      new_program_identity_SHA256_count=1, linker_identity_uses_frozen_stat=True,
                      outputs=[b.stat(p) for p in ROOT.rglob("*") if p.is_file()])
    except Exception as exc:
        result["failure"] = str(exc)
        # Preserve the failed original direct call in this receipt too, without
        # turning a real link failure into an apparent zero-invocation outcome.
        for suffix in ("environment", "link"):
            path = L / (TAG + "." + suffix + ".call.json")
            if path.exists():
                entry = b.stat(path)
                if entry not in result["calls"]:
                    result["calls"].append(entry)
                if suffix == "link" and "child" in b.read(path):
                    result["link_invocations"] = 1
        raise
    finally:
        b.write_new(CHECK, result)
    print(str(CHECK))


if __name__ == "__main__":
    main()
