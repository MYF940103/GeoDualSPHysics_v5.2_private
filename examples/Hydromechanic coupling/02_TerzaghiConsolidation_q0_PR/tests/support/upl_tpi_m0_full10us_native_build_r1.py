"""Build one CPU-only Release ABI full10us reader; never invoke a reader/solver."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import shutil
import sys
sys.dont_write_bytecode = True
import upl_tpi_cpu_build_r2 as b
import upl_tpi_gpu_full2tv_native_r1 as common

T, L, S = b.T, b.L, b.S
TAG = "upl_tpi_m0_full10us_native_r1"
SCRIPT = Path(__file__).resolve()
CPP = T / "support" / (TAG + ".cpp")
NOTE = T / "notes" / (TAG + ".md")
OLD_CPP = T / "support/upl_tpi_m0_dt_native_r1.cpp"
BASE = L / "upl_tpi_m0_dt_native_r1.build.json"
COMPILE = L / "upl_tpi_m0_dt_native_r1.compile.call.json"
LINK = L / "upl_tpi_m0_dt_native_r1.link.call.json"
NEUTRAL = T / "support/upl_cpu_public_native_r1.cpp"
BUILDROOT = T / "outputs" / (TAG + "_build")
BUILD = L / (TAG + ".build.json")
PROGRAM = BUILDROOT / (TAG + ".exe")


class Admission:
    def __init__(self, path):
        self.entry, self.data, self.consumed = b.stat(path), b.read(path), {}
        b.need(self.data.get("stage") == TAG + ".build_admission"
               and self.data.get("passed") is True and self.data.get("action_only") is True,
               "An exact independently reviewed build-only admission is required")
        self.frozen = {str(Path(e["path"]).resolve()): e for e in self.data["inputs"]}
        b.need(len(self.frozen) == len(self.data["inputs"]), "Duplicate admitted input")
        for p in (SCRIPT, CPP, NOTE, OLD_CPP, NEUTRAL, Path(b.__file__), Path(common.__file__)):
            self.pin(p)

    def pin(self, path):
        key = str(Path(path).resolve())
        b.need(key in self.frozen, "Consumed input absent from root admission: " + key)
        self.consumed[key] = b.same(self.frozen[key])
        return self.consumed[key]

    def finish(self):
        for e in self.consumed.values():
            b.same(e)
        b.same(self.entry)
        return list(self.consumed.values())


def context(ad):
    b.need(not BUILDROOT.exists() and not BUILD.exists(), "Existing reader artifacts are protected")
    for suffix in ("environment", "compile", "link"):
        for ext in (".call.json", ".log"):
            b.need(not (L / (TAG + "." + suffix + ext)).exists(), "Existing tool evidence is protected")
    for p in (BASE, COMPILE, LINK, b.VCVARS):
        ad.pin(p)
    base, cc, link = b.read(BASE), b.read(COMPILE), b.read(LINK)
    b.need(base.get("passed") is True and base.get("stage") == "upl_tpi_m0_dt_native_r1.build"
           and base.get("solver_invocations") == base.get("reader_invocations") == 0,
           "A genuine successful build-only M0 reader recipe is required")
    for entry in base["calls"]:
        ad.pin(entry["path"]); b.same(entry)
        call = b.read(entry["path"])
        b.need(call.get("passed") is True and call.get("actual_Popen_wait_exit")
               == call.get("actual_Win32_exit") == 0, "Original tool handle exits differ")
    for key in ("program", "object", "compiler_dependencies", "environment_batch"):
        ad.pin(base[key]["path"]); b.same(base[key])
    oldobj = Path(base["object"]["path"]).resolve()
    deps = b.read(base["compiler_dependencies"]["path"])
    b.need(Path(deps["Data"]["Source"]).resolve() == OLD_CPP.resolve(), "Actual original reader source differs")
    includes = {Path(p).resolve() for p in deps["Data"]["Includes"]}
    b.need(NEUTRAL.resolve() in includes and not any(p.is_relative_to((S / "source").resolve()) for p in includes),
           "Original reader did not use its retained neutral loader/header closure")
    for e in base["original_dependencies"]:
        ad.pin(e["path"]); b.same(e)
    for p in includes:
        ad.pin(p)  # Current stat-bound system includes; old JSON proves the actual include names, not their old mtimes.
    for entry in base["runtime"]:
        ad.pin(entry["destination"]["path"]); b.same(entry["destination"])
    for call in (cc, link):
        ad.pin(call["program"]["path"]); b.same(call["program"])
    flags = {x.lower() for x in cc["arguments"]}
    b.need({"/std:c++17", "/o2", "/mt", "/fp:precise"} <= flags
           and not ({"/mtd", "/mdd", "/od"} & flags), "Original CPU-only Release ABI flags differ")
    objects = [Path(x).resolve() for x in link["arguments"] if not x.startswith("/") and x.lower().endswith(".obj")]
    libraries = [Path(x).resolve() for x in link["arguments"] if not x.startswith("/") and x.lower().endswith(".lib")]
    b.need(len(objects) == 86 and objects.count(oldobj) == 1 and len(libraries) == 17,
           "Actual one-reader plus85 retained objects/17 explicit libraries recipe differs")
    for p in objects + libraries:
        if p != oldobj:
            ad.pin(p)
    b.need(len({Path(e["destination"]["path"]).name.lower() for e in base["runtime"]}) == 4,
           "Original four runtime basenames differ")
    ad.finish()
    return base, cc, link, oldobj, includes


def build(ad, result):
    base, cc, link, oldobj, includes = context(ad)
    BUILDROOT.mkdir()
    result["build_started"] = True
    env, batch = common.environment(TAG, BUILDROOT, result["calls"])
    b.need(env.get("WINDOWSSDKVERSION", "").rstrip("\\/") == "10.0.22000.0",
           "Original actual reader SDK22000 differs")
    obj, dep = BUILDROOT / "reader.obj", BUILDROOT / "dependencies.json"
    args, skip, source_count = [], False, 0
    for x in cc["arguments"]:
        if skip:
            skip = False
        elif x.lower() == "/sourcedependencies":
            skip = True
        elif x.lower().startswith(("/fo", "/fd")):
            continue
        elif not x.startswith("/") and Path(x).resolve() == OLD_CPP.resolve():
            source_count += 1
        else:
            args.append(x)
    b.need(source_count == 1 and not skip, "Original single source/dependency argument differs")
    args += ["/Fo" + str(obj), "/Fd" + str(BUILDROOT / "reader.pdb"), "/sourceDependencies", str(dep), str(CPP)]
    call, _ = b.invoke(TAG + ".compile", [cc["program"]["path"], *args], S / "VS", env)
    result["calls"].append(call)
    actual = b.read(dep)["Data"]
    b.need(Path(actual["Source"]).resolve() == CPP.resolve()
           and {Path(p).resolve() for p in actual["Includes"]} == includes,
           "Actual new compiler source or original complete include closure differs")
    args, replaced_obj, replaced_out = [], 0, 0
    for x in link["arguments"]:
        if not x.startswith("/") and x.lower().endswith(".obj") and Path(x).resolve() == oldobj:
            args.append(str(obj)); replaced_obj += 1
        elif x.lower().startswith("/out:"):
            args.append("/OUT:" + str(PROGRAM)); replaced_out += 1
        elif x.lower().startswith(("/pdb:", "/implib:", "/ltcgout:", "/ilk:", "/pgd:")):
            prefix = x.split(":", 1)[0]
            ext = {"/pdb": ".pdb", "/implib": ".lib", "/ltcgout": ".iobj", "/ilk": ".ilk", "/pgd": ".pgd"}[prefix.lower()]
            args.append(prefix + ":" + str(BUILDROOT / ("reader" + ext)))
        else:
            args.append(x)
    b.need(replaced_obj == replaced_out == 1, "Exact isolated reader object/EXE replacement differs")
    if not any(x.lower().startswith("/ilk:") for x in args):
        args.append("/ILK:" + str(BUILDROOT / "reader.ilk"))
    call, _ = b.invoke(TAG + ".link", [link["program"]["path"], *args], S / "VS", env)
    result["calls"].append(call)
    copies = []
    for entry in base["runtime"]:
        source = entry["destination"]
        target = BUILDROOT / Path(source["path"]).name
        b.need(not target.exists(), "Fresh runtime destination already exists")
        shutil.copy2(source["path"], target)
        copies.append(dict(source=b.same(source), destination=b.stat(target)))
    result.update(passed=True, program=b.stat(PROGRAM), source=b.stat(CPP), object=b.stat(obj),
                  compiler_dependencies=b.stat(dep), environment_batch=batch, runtime=copies,
                  retained_nonreader_object_count=85, explicit_library_count=17,
                  actual_complete_include_count=len(includes), original_recipe=ad.pin(BASE),
                  original_compile=ad.pin(COMPILE), original_link=ad.pin(LINK), consumed=ad.finish())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-admission", type=Path, required=True)
    parser.add_argument("--execution-authorized", action="store_true")
    args = parser.parse_args()
    b.need(args.execution_authorized, "Explicit build-only execution authorization required")
    b.need(not BUILD.exists(), "Original build/failure receipt is protected")
    result = dict(stage=TAG + ".build", passed=False, build_started=False, calls=[],
                  configuration="CPU-only Release native utility (/O2 /MT)", private_offline_reader=True,
                  solver_invocations=0, reader_invocations=0, CUDA_compilations=0,
                  old_reader_or_loader_changed=False, physical_acceptance=False, SHA_scans=0)
    try:
        ad = Admission(args.root_admission)
        result["root_admission"] = ad.entry
        build(ad, result)
    except Exception as exc:
        result["failure"] = str(exc)
        raise
    finally:
        b.write_new(BUILD, result)


if __name__ == "__main__":
    main()
