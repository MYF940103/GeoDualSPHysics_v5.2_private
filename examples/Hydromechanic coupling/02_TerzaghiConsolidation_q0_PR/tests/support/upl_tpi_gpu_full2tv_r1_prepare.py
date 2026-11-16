"""Prepare only one C02 GPU full-2Tv time-window guard; no tool/program invocation."""
from __future__ import annotations
import argparse
import difflib
from pathlib import Path
import upl_tpi_cpu_build_r2 as b

T, L = b.T, b.L
TAG = "upl_tpi_gpu_full2tv_r1"
NOTE = T / "notes" / (TAG + ".md")
BASE = L / "upl_tpi_gpu_r2.prepare.json"
BASE_BUILD = L / "upl_tpi_gpu_Release_r3.build.json"
OUT = T / "outputs" / (TAG + "_source")
CHECK = L / (TAG + ".prepare.json")
NAME = "JSphGpuSingle.cpp"
BEFORE = "TimeMax<=.15"
AFTER = "(TimeMax<=.15 || (TimeMax==72.88428690075874 && NstepsBreak==11661219))"


class Admission:
    def __init__(self, path):
        self.entry = b.stat(path); self.data = b.read(path)
        b.need(self.data.get("stage") == TAG + ".prepare_admission" and self.data.get("passed") is True and
               self.data.get("prepare_only") is True, "Independent full-read prepare-only admission required")
        self.frozen = {str(Path(x["path"]).resolve()): x for x in self.data["inputs"]}; self.used = {}
        b.need(len(self.frozen) == len(self.data["inputs"]), "Duplicate frozen input")
    def pin(self, path):
        key = str(Path(path).resolve()); b.need(key in self.frozen, "Unadmitted input: " + key)
        self.used[key] = b.same(self.frozen[key]); return self.used[key]
    def finish(self):
        b.same(self.entry)
        for x in self.used.values(): b.same(x)
        return list(self.used.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution-authorized", action="store_true"); parser.add_argument("--admission", type=Path, required=True)
    args = parser.parse_args(); b.need(args.execution_authorized, "Root prepare-only execution required")
    b.need(not OUT.exists() and not CHECK.exists(), "Existing preparation/partial/failure is protected")
    ad = Admission(args.admission)
    result = dict(stage=TAG + ".prepare", passed=False, root_admission=ad.entry, solver_invocations=0,
                  build_invocations=0, native_invocations=0, SHA_scans=0, public_source_changed=False,
                  physical_acceptance=False, automatic_follow_up=False)
    try:
        for path in (Path(__file__), NOTE, Path(b.__file__), BASE, BASE_BUILD): ad.pin(path)
        base, build = b.read(BASE), b.read(BASE_BUILD)
        b.need(base.get("passed") is True and len(base["files"]) == 269 and build.get("passed") is True and
               build.get("configuration") == "Release" and build.get("object_count") == 111 and
               Path(build.get("source_prepare", build.get("prepared"))["path"]).resolve() == BASE.resolve(),
               "Actual complete r2 source and passed Release r3 build required")
        originals = {}
        for entry in base["files"]:
            ad.pin(entry["path"]); b.same(entry); path = Path(entry["path"])
            b.need(path.parent.resolve() == Path(base["source_root"]).resolve() and path.name not in originals,
                   "Original269 source must have unique flat ownership")
            originals[path.name] = path.read_bytes()
        b.need(len(originals) == 269 and NAME in originals and "upl_tpi_gpu_r1.h" in originals and "upl_tpi_gpu_r1.cuh" in originals,
               "Exact frozen GPU source/helper membership required")
        old = originals[NAME]; before = BEFORE.encode("ascii"); after = AFTER.encode("ascii")
        b.need(old.count(before) == 1 and old.count(after) == 0, "The one original bounded Init time guard is not unique")
        changed = old.replace(before, after, 1)
        ad.finish(); OUT.mkdir(); files = []
        for name, raw in originals.items():
            target = OUT / name; data = changed if name == NAME else raw
            with target.open("xb") as f: f.write(data)
            b.need(target.read_bytes() == data, "New source byte-copy differs: " + name); files.append(b.stat(target))
        difference = OUT / "source_diff.json"
        b.write_new(difference, dict(stage=TAG + ".source_diff", passed=True, only_changed_source=NAME,
            before=BEFORE, after=AFTER, occurrences=1,
            unified_diff="".join(difflib.unified_diff(old.decode("utf-8").splitlines(True), changed.decode("utf-8").splitlines(True),
                                                     fromfile="r2/"+NAME, tofile="full2tv/"+NAME)),
            other268_files_byte_identical=True, helper_h_and_cuh_byte_identical=True,
            class_or_header_ABI_changed=False, old_kernel_external_signatures_changed=False,
            physics_math_kernel_or_threshold_changed=False, no_new_XML_or_BAT=True,
            full_clock_and_runner_not_prepared_here=True, physical_acceptance=False))
        result.update(passed=True, source_root=str(OUT), files=files, source_count=269,
            changed_sources=[b.stat(OUT / NAME)], recompile_sources=[b.stat(OUT / NAME)], changed_headers=[],
            source_diff=b.stat(difference), base_prepare=ad.pin(BASE), base_build=ad.pin(BASE_BUILD),
            base_source_entries=base["files"], other268_files_byte_identical=True,
            helper_h_and_cuh_byte_identical=True, class_or_header_ABI_changed=False,
            old_kernel_external_signatures_changed=False, consumed=ad.finish())
    except Exception as exc:
        result.update(failure=str(exc), partial_outputs_preserved=True)
        raise
    finally:
        b.write_new(CHECK, result)


if __name__ == "__main__":
    main()
