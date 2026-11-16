"""Root-admitted build OR raw22 compare; never run/restart a physical solver."""
from __future__ import annotations
import argparse
from pathlib import Path
import os
import re
import shutil
import upl_tpi_cpu_build_r2 as b
import upl_tpi_cpu_native_r1 as native

T, L, S = b.T, b.L, b.S
TAG = "upl_tpi_raw22_compare_r1"
CPP, NOTE = T/"support"/(TAG+".cpp"), T/"notes"/(TAG+".md")
RAW = T/"support/upl_hg_raw_compare_r1.cpp"
NEUTRAL = T/"support/upl_cpu_public_native_r1.cpp"
BASE = L/"upl_tpi_cpu_native_r1.build.json"
COMPILE, LINK = L/"upl_tpi_cpu_native_r1.compile.call.json", L/"upl_tpi_cpu_native_r1.link.call.json"
ROOT, BUILT = T/"outputs"/(TAG+"_build"), L/(TAG+".build.json")
PROGRAM = ROOT/(TAG+".exe")


class Admission:
    def __init__(self, action, path):
        self.entry, self.data = b.stat(path), b.read(path)
        b.need(self.data.get("stage") == TAG+"."+action+"_admission" and self.data.get("passed") is True
               and self.data.get("action_only") is True, "Independent exact-action root admission required")
        self.frozen = {str(Path(e["path"]).resolve()): e for e in self.data["inputs"]}
        b.need(len(self.frozen) == len(self.data["inputs"]), "Duplicate frozen input paths")
        for p in (Path(__file__), CPP, NOTE, RAW, NEUTRAL, Path(b.__file__), Path(native.__file__)):
            self.pin(p)

    def pin(self, path):
        key = str(Path(path).resolve())
        b.need(key in self.frozen, "Consumed input absent from root admission: "+key)
        return b.same(self.frozen[key])

    def finish(self):
        for entry in self.frozen.values():
            b.same(entry)
        b.same(self.entry)


def build(ad):
    b.need(not ROOT.exists() and not BUILT.exists(), "Existing comparator build/failure is protected")
    for p in (BASE, COMPILE, LINK, b.VCVARS):
        ad.pin(p)
    base, cc, lc = b.read(BASE), b.read(COMPILE), b.read(LINK)
    b.need(base.get("passed") is True and cc.get("passed") is True and lc.get("passed") is True,
           "The genuinely successful native_r1 compile/link recipe is required")
    old_object = Path(base["object"]["path"]).resolve()
    original_cpp = T/"support/upl_tpi_cpu_native_r1.cpp"
    ad.pin(original_cpp)
    for p in (cc["program"]["path"], lc["program"]["path"], base["compiler_dependencies"]["path"]):
        ad.pin(p)
    dependencies = base["original_dependencies"]
    for entry in dependencies:
        ad.pin(entry["path"])
    headers = []
    frozen_headers = (T/"outputs/upl_spr_av_ReleaseCPU_r1_source").resolve()
    for name in b.read(base["compiler_dependencies"]["path"])["Data"]["Includes"]:
        p = Path(name).resolve()
        if p.is_relative_to(frozen_headers):
            headers.append(ad.pin(p))
    b.need(headers, "Actual frozen native recipe headers were not identified")
    ROOT.mkdir()
    result = dict(stage=TAG+".build", passed=False, root_admission=ad.entry, calls=[],
                  solver_invocations=0, comparator_invocations=0, old_reader_invocations=0,
                  old_reader_loader_or_program_changed=False, SHA_scans=0, physical_acceptance=False)
    try:
        # Reuse only the original helper's environment capture; never its build/read/review entry.
        env, batch = native.environment(TAG, ROOT, result["calls"])
        obj, dep = ROOT/"compare.obj", ROOT/"dependencies.json"
        args, skip = [], False
        for value in cc["arguments"]:
            if skip:
                skip = False
            elif value.lower() == "/sourcedependencies":
                skip = True
            elif value.lower().startswith(("/fo", "/fd")) or (not value.startswith("/") and Path(value).resolve() == original_cpp.resolve()):
                continue
            else:
                args.append(value)
        args += ["/Fo"+str(obj), "/Fd"+str(ROOT/"compare.pdb"), "/sourceDependencies", str(dep), str(CPP)]
        call, _ = b.invoke(TAG+".compile", [cc["program"]["path"], *args], S/"VS", env)
        result["calls"].append(call)
        included = {Path(p).resolve() for p in b.read(dep)["Data"]["Includes"]}
        b.need(NEUTRAL.resolve() in included and all(not p.is_relative_to((S/"source").resolve()) for p in included),
               "Comparator did not consume neutral loader or read live source headers")
        args = []
        for value in lc["arguments"]:
            if not value.startswith("/") and value.lower().endswith(".obj") and Path(value).resolve() == old_object:
                args.append(str(obj))
            elif value.lower().startswith("/out:"):
                args.append("/OUT:"+str(PROGRAM))
            elif value.lower().startswith(("/pdb:", "/implib:", "/ltcgout:", "/ilk:", "/pgd:")):
                prefix = value.split(":", 1)[0]
                suffix = {"/pdb": ".pdb", "/implib": ".lib", "/ltcgout": ".iobj", "/ilk": ".ilk", "/pgd": ".pgd"}[prefix.lower()]
                args.append(prefix+":"+str(ROOT/("compare"+suffix)))
            else:
                args.append(value)
        call, _ = b.invoke(TAG+".link", [lc["program"]["path"], *args], S/"VS", env)
        result["calls"].append(call)
        runtime = []
        for entry in base["runtime"]:
            source = entry["destination"]["path"]
            ad.pin(source)
            target = ROOT/Path(source).name
            shutil.copy2(source, target)
            runtime.append(dict(source=b.stat(source), destination=b.stat(target)))
        ad.finish()
        result.update(passed=True, program=b.stat(PROGRAM), object=b.stat(obj), compiler_dependencies=b.stat(dep),
                      runtime=runtime, original_dependencies=dependencies, frozen_headers=headers,
                      reused_real_native_recipe=ad.pin(BASE), environment_batch=batch)
    except Exception as exc:
        result["failure"] = str(exc)
        raise
    finally:
        b.write_new(BUILT, result)


def compare(ad):
    job = ad.data["comparison"]
    label = job["label"]
    b.need(re.fullmatch(r"[A-Za-z0-9_]+", label), "Explicit safe comparison label required")
    tag = TAG+"_"+label
    target, check = T/"outputs"/tag, L/(tag+".compare.json")
    b.need(not target.exists() and not check.exists(), "Existing comparison/partial is protected")
    for p in (BUILT, PROGRAM):
        ad.pin(p)
    built = b.read(BUILT)
    b.need(built.get("passed") is True and Path(built["program"]["path"]).resolve() == PROGRAM.resolve(), "Reviewed genuine comparator build required")
    for entry in built["runtime"]:
        ad.pin(entry["destination"]["path"])
    for key in ("old_native_receipt", "new_native_review", "old_plan", "new_plan"):
        ad.pin(job[key]["path"])
    old_proof, new_proof = b.read(job["old_native_receipt"]["path"]), b.read(job["new_native_review"]["path"])
    b.need(old_proof.get("passed") is True and new_proof.get("passed") is True
           and new_proof.get("job", {}).get("scheme") == "A", "Existing old native and new default-A native qualifications required")
    old, fresh = Path(job["old_data"]).resolve(), Path(job["new_data"]).resolve()
    b.need(old != fresh and Path(new_proof["job"]["data"]).resolve() == fresh, "New default-A raw-data association differs")
    counts = [job[k] for k in ("old_frames", "new_frames", "shared_frames")]
    b.need(all(isinstance(n, int) and not isinstance(n, bool) and n > 0 for n in counts)
           and counts[2] <= min(counts[:2]), "Explicit actual original/shared counts required")
    if label == "CPU_A_startup015_r1":
        b.need(counts == [1682, 344, 343], "Current actual CPU full/startup common prefix is1682/344/343")
    # Pin only raw files actually opened plus an existing native head, not all1682 old PART payloads.
    for directory in (old, fresh):
        for part in range(counts[2]):
            ad.pin(directory/("Part_%04d.bi4" % part))
        head = directory/"Part_Head.ibi4"
        if head.exists():
            ad.pin(head)
    native.no_active_reader(PROGRAM, old)
    native.no_active_reader(PROGRAM, fresh)
    result = dict(stage=TAG+".compare", passed=False, root_admission=ad.entry, comparison=job,
                  solver_invocations=0, old_reader_invocations=0, full_native_exports_created=False,
                  compare_attempts=1, SHA_scans=0, physical_acceptance=False)
    callpath = L/(tag+".call.json")
    try:
        b.invoke(tag, [str(PROGRAM), "--compare", str(old), str(fresh), job["old_plan"]["path"], job["new_plan"]["path"],
                       *map(str, counts), str(target)], S/"VS", os.environ.copy())
        done = b.read(target/"completion.json")
        b.need(done.get("passed") is True and done.get("complete") is True and done.get("frames_compared") == counts[2]
               and done.get("arrays_per_frame") == 22 and done.get("native_IDs_per_frame") == 1040
               and done.get("native_array_different_bytes") == done.get("clock_different_bytes") == 0,
               "Actual native22/clock28 raw comparison failed")
        ad.finish()
        result.update(passed=True, completion=b.stat(target/"completion.json"), arrays=b.stat(target/"arrays.csv"))
    except Exception as exc:
        result["failure"] = str(exc)
        if (target/"completion.json").exists():
            result["actual_comparison_summary"] = b.read(target/"completion.json")
        raise
    finally:
        if callpath.exists():
            result["actual_compare_call"] = b.stat(callpath)
        b.write_new(check, result)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("build", "compare"))
    p.add_argument("--execution-authorized", action="store_true")
    p.add_argument("--admission", required=True, type=Path)
    args = p.parse_args()
    b.need(args.execution_authorized, "Root full-read and one exact action required")
    ad = Admission(args.action, args.admission)
    {"build": build, "compare": compare}[args.action](ad)


if __name__ == "__main__":
    main()
