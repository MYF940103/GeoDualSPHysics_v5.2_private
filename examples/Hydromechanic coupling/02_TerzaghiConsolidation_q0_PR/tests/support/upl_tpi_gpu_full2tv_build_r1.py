"""One-host-only Release build for a prepared C02 full-2Tv window; never run it."""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import upl_tpi_cpu_build_r2 as b
import upl_tpi_gpu_build_r1 as g

T, L, S = b.T, b.L, b.S
TAG = "upl_tpi_gpu_full2tv_build_r1"
BUILD_TAG = "upl_tpi_gpu_full2tv_Release_r1"
NOTE = T / "notes" / (TAG + ".md")
PREP = L / "upl_tpi_gpu_full2tv_r1.prepare.json"
BASE = L / "upl_tpi_gpu_Release_r3.build.json"
CL_CALL = L / "upl_tpi_gpu_Release_r3.JSphGpuSingle.call.json"
LINK_CALL = L / "upl_tpi_gpu_Release_r3.link.call.json"
OUT = T / "outputs" / BUILD_TAG
INT = Path(tempfile.gettempdir()) / TAG / "Release/int"
CHECK = L / (BUILD_TAG + ".build.json")
NAME = "JSphGpuSingle.cpp"
BEFORE = "TimeMax<=.15"
AFTER = "(TimeMax<=.15 || (TimeMax==72.88428690075874 && NstepsBreak==11661219))"


class Admission:
    def __init__(self, path):
        self.entry = b.stat(path); self.data = b.read(path)
        b.need(self.data.get("stage") == TAG + ".build_admission" and self.data.get("passed") is True and
               self.data.get("build_only") is True and self.data.get("configuration") == "Release",
               "Independent one-host Release build-only admission required")
        self.frozen = {str(Path(x["path"]).resolve()): x for x in self.data["inputs"]}; self.used = {}
        b.need(len(self.frozen) == len(self.data["inputs"]), "Duplicate frozen input")
    def pin(self, path):
        key = str(Path(path).resolve()); b.need(key in self.frozen, "Unadmitted input: " + key)
        self.used[key] = b.same(self.frozen[key]); return self.used[key]
    def finish(self):
        b.same(self.entry)
        for x in self.used.values(): b.same(x)
        return list(self.used.values())


def context(ad):
    for p in (Path(__file__), NOTE, Path(b.__file__), Path(g.__file__), g.VCVARS, PREP, BASE, CL_CALL, LINK_CALL): ad.pin(p)
    prep, base, cl, link = [b.read(p) for p in (PREP, BASE, CL_CALL, LINK_CALL)]
    b.need(prep.get("passed") is True and prep.get("stage") == "upl_tpi_gpu_full2tv_r1.prepare" and
           prep.get("source_count") == len(prep["files"]) == 269 and prep.get("other268_files_byte_identical") is True and
           prep.get("helper_h_and_cuh_byte_identical") is True and prep.get("class_or_header_ABI_changed") is False and
           prep.get("old_kernel_external_signatures_changed") is False and
           [Path(x["path"]).name for x in prep["changed_sources"]] == [NAME] and not prep["changed_headers"],
           "Exact passed window-only one-TU preparation required")
    b.need(base.get("passed") is True and base.get("configuration") == "Release" and base.get("object_count") == 111 and
           base.get("consumed_stats_unchanged") is True and
           all(x.get("passed") is True and x.get("actual_Popen_wait_exit") == x.get("actual_Win32_exit") == 0 for x in (cl, link)),
           "Actual passed Release r3 build and compile/link recipe required")
    for e in (prep["base_prepare"], prep["base_build"], prep["source_diff"], base["program"]): ad.pin(e["path"]); b.same(e)
    b.need(Path(prep["base_build"]["path"]).resolve() == BASE.resolve() and
           Path(prep["base_prepare"]["path"]).resolve() == Path(base["source_prepare"]["path"]).resolve(),
           "Preparation and adopted Release source ancestry differ")
    source = Path(prep["source_root"]).resolve()
    b.need(source == (T / "outputs/upl_tpi_gpu_full2tv_r1_source").resolve(), "Unexpected new source root")
    for e in prep["files"]: ad.pin(e["path"]); b.same(e)
    for e in prep["base_source_entries"]: ad.pin(e["path"]); b.same(e)
    old_single = next(x for x in prep["base_source_entries"] if Path(x["path"]).name == NAME)
    old_bytes = Path(old_single["path"]).read_bytes()
    b.need(old_bytes.count(BEFORE.encode()) == 1 and (source / NAME).read_bytes() == old_bytes.replace(BEFORE.encode(), AFTER.encode(), 1),
           "Actual host delta is not exactly the admitted one window guard")
    objects = {Path(e["path"]).name.lower(): e for e in base["objects"]}
    b.need(len(objects) == len(base["objects"]) == 111 and "jsphgpusingle.obj" in objects, "Adopted111 object closure differs")
    for e in objects.values(): ad.pin(e["path"]); b.same(e)
    # Retained /Zi objects still refer to their original compiler PDBs.
    for p in {Path(base["private_no_space_IntDir"]) / "vc143.pdb", Path(base["old_compiler_pdb"]["path"])}: ad.pin(p)
    old_args = link["arguments"]
    linked = [x for x in old_args if x.lower().endswith(".obj")]
    b.need(len(linked) == 111 and [str(Path(x).resolve()) for x in linked] == [e["path"] for e in base["objects"]],
           "Actual Release r3 linker object order differs from its sealed111 list")
    b.need(Path(cl["program"]["path"]).name.lower() == "cl.exe" and Path(link["program"]["path"]).name.lower() == "link.exe",
           "Actual host compiler and linker required")
    for e in (cl["program"], link["program"]): ad.pin(e["path"]); b.same(e)
    libraries = [x["first_existing_candidate"] for x in base["actual_library_search"]]
    for e in libraries: ad.pin(e["path"]); b.same(e)
    runtime = [e["destination"] for e in base["runtime"]]
    for e in runtime: ad.pin(e["path"]); b.same(e)
    cmd = Path(os.environ.get("COMSPEC", "C:/Windows/System32/cmd.exe")); ad.pin(cmd)
    ad.finish(); OUT.mkdir(); INT.mkdir(parents=True); (OUT / "out").mkdir()
    return dict(tag=BUILD_TAG, root=OUT, out=OUT / "out", intdir=INT, source_root=source, configuration="Release",
                tools={"cmd": b.stat(cmd), "cl": cl["program"], "link": link["program"]},
                old_objects=objects, link_args=old_args, libraries=libraries, runtime_sources=runtime,
                compile_call=cl, original_compile=ad.pin(CL_CALL), original_link=ad.pin(LINK_CALL), prepared=ad.pin(PREP))


def compile_one(ad, ctx, env, calls):
    obj, dep = INT / "JSphGpuSingle.obj", INT / "JSphGpuSingle.cpp.sourceDependencies.json"
    args, counts, skip = [], {"source": 0, "fo": 0, "fd": 0, "deps": 0}, False
    for arg in ctx["compile_call"]["arguments"]:
        if skip: skip = False; continue
        lower = arg.lower()
        if lower == "/sourcedependencies": counts["deps"] += 1; skip = True
        elif Path(arg).name == NAME: args.append(str(ctx["source_root"] / NAME)); counts["source"] += 1
        elif lower.startswith("/fo"): args.append("/Fo" + str(obj)); counts["fo"] += 1
        elif lower.startswith("/fd"): args.append("/Fd" + str(INT / "vc143.pdb")); counts["fd"] += 1
        else: args.append(arg)
    b.need(all(x == 1 for x in counts.values()), "Exact single source/Fo/Fd/dependency redirect required")
    args += ["/sourceDependencies", str(dep)]
    ad.finish(); g.invoke(b, BUILD_TAG + ".JSphGpuSingle", [ctx["tools"]["cl"]["path"], *args], S / "VS", env, calls)
    b.need(obj.exists() and dep.exists(), "Actual new host object/dependency record missing")
    included = [Path(x).resolve() for x in b.read(dep)["Data"]["Includes"]]
    old_source = Path(next(x for x in b.read(BASE)["source_files"] if Path(x["path"]).name == NAME)["path"]).parent
    b.need(all(not x.is_relative_to((S / "source").resolve()) and not x.is_relative_to(old_source.resolve()) for x in included),
           "New host compilation consumed live or old-private source headers")
    return b.stat(obj), b.stat(dep)


def link_one(ad, ctx, obj, env, calls):
    name = "DualSPHysics5.2_GEO_win64"
    targets = {"/out:": ctx["out"] / (name + ".exe"), "/pdb:": ctx["out"] / (name + ".pdb"),
               "/implib:": ctx["out"] / (name + ".lib"), "/ltcgout:": INT / (name + ".iobj"), "/ilk:": INT / (name + ".ilk")}
    counts = {x: 0 for x in targets}; args, all_objects, retained = [], [], []
    for arg in ctx["link_args"]:
        lower = arg.lower(); option = next((x for x in targets if lower.startswith(x)), None)
        if option: args.append(arg[:len(option)] + str(targets[option])); counts[option] += 1
        elif lower.endswith(".obj"):
            old = ctx["old_objects"][Path(arg).name.lower()]; chosen = obj if Path(arg).name.lower() == "jsphgpusingle.obj" else old
            args.append(chosen["path"]); all_objects.append(chosen)
            if chosen is old: retained.append(old)
        else: args.append(arg)
    b.need(all(x == 1 for x in counts.values()) and len(all_objects) == 111 and len(retained) == 110,
           "Exact111 link ordering/one replacement/new output redirects differ")
    ad.finish(); g.invoke(b, BUILD_TAG + ".link", [ctx["tools"]["link"]["path"], *args], S / "VS", env, calls)
    program = targets["/out:"]; b.need(program.is_file(), "Actual private program missing")
    identity = b.stat(program)
    with program.open("rb") as f:
        h = hashlib.sha256()
        for chunk in iter(lambda: f.read(1024*1024), b""): h.update(chunk)
    identity["sha256"] = h.hexdigest()
    return identity, all_objects, retained


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--execution-authorized", action="store_true"); p.add_argument("--admission", required=True, type=Path)
    a = p.parse_args(); b.need(a.execution_authorized, "One independent build-only admission required")
    b.need(not OUT.exists() and not INT.exists() and not CHECK.exists(), "Original build/partial/failure is protected")
    ad = ctx = None; calls = []
    result = dict(stage=TAG, passed=False, configuration="Release", compile_invocations=0, link_invocations=0,
                  program_help_invocations=0, solver_invocations=0, native_invocations=0, VTK_invocations=0,
                  physical_acceptance=False, public_source_changed=False, canonical_programs_changed=False,
                  old_source_object_or_BI4_SHA_scans=0, new_CUDA_compile_invocations=0, following_action_launched=False)
    try:
        ad = Admission(a.admission); ctx = context(ad)
        result.update(root_admission=ad.entry, source_prepare=ctx["prepared"], prepared=ctx["prepared"],
                      base_build=ad.pin(BASE), original_compile=ctx["original_compile"], original_link=ctx["original_link"],
                      private_no_space_IntDir=str(INT), private_output_root=str(OUT))
        env, result["environment"] = g.environment(b, ctx, calls)
        result["actual_library_search"] = g.validate_library_search(b, ctx, env)
        obj, deps = compile_one(ad, ctx, env, calls)
        program, objects, retained = link_one(ad, ctx, obj, env, calls)
        runtime = []
        for e in ctx["runtime_sources"]:
            dest = ctx["out"] / Path(e["path"]).name; b.need(not dest.exists(), "Runtime destination already exists")
            shutil.copy2(e["path"], dest); runtime.append(dict(source=e, destination=b.stat(dest)))
        result.update(passed=True, program=program, objects=objects, retained_objects=retained, runtime=runtime,
                      object_count=111, replacement_object_count=1, retained_effective_object_count=110,
                      compiler_dependencies=deps, new_program_identity_SHA256_count=1,
                      class_layout_and_kernel_external_ABI_unchanged=True, adopted_CUDA_object_unchanged=True)
    except Exception as exc:
        result["failure"] = str(exc); raise
    finally:
        result["calls"] = calls
        actual = [b.read(x["path"]) for x in calls]
        result["compile_invocations"] = sum(Path(x["program"]["path"]).name.lower() == "cl.exe" and isinstance(x.get("child"), dict) for x in actual)
        result["link_invocations"] = sum(Path(x["program"]["path"]).name.lower() == "link.exe" and isinstance(x.get("child"), dict) for x in actual)
        if ad is not None:
            try: result["consumed"] = ad.finish(); result["consumed_stats_unchanged"] = True
            except Exception as exc: result.update(passed=False, consumed_stats_unchanged=False, final_stat_failure=str(exc))
        if ctx is not None: result["outputs"] = [b.stat(x) for root in (OUT, INT) for x in root.rglob("*") if x.is_file()]
        b.write_new(CHECK, result)


if __name__ == "__main__":
    main()
