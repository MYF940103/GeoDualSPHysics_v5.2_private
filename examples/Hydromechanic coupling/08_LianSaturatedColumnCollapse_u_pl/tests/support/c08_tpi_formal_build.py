"""Build the three-material C08 TPI receiver from the sealed positive-pressure-cap program."""
import difflib
import json
from pathlib import Path
import re
import shutil
import subprocess

from c08_m0_gpu_coupled_r1 import CUDA, SRC, once
from c08_psi25_tpi_build import OUT as CONTROL, RUNTIME, digest
from c08_psi25_tpi_run import TESTS, identity, now, record


BUILD = TESTS / "outputs/c08_tpi_formal_build_r1"
PROGRAM = BUILD / "C08FormalTpi.exe"
MODES = {
    "psi0": (0.0, 5000.0, 0.0),
    "psi2p5": (2.5, 5000.0, 0.2),
    "psim5": (-5.0, 7500.0, 0.2),
}
CONTROL_CAPS = [2000208, 2060200, 2240200]
FULL_CAP = 2600200


def require(valid, message):
    if not valid:
        raise ValueError(message)


def formal_host(code):
    guard = "    const bool c08Probe=HydroMechTpi && gravitycontainer && !Cpu && !WithMpi"
    code = once(code, guard,
                "    const bool c08Material=\n"
                "      (SoilCte.dlt==0.f && SoilCte.coh==5000.f && SoilCte.psiDecay==0.f)\n"
                "      || (SoilCte.dlt==float(TORAD*2.5) && SoilCte.coh==5000.f && SoilCte.psiDecay==.2f)\n"
                "      || (SoilCte.dlt==float(TORAD*(-5.)) && SoilCte.coh==7500.f && SoilCte.psiDecay==.2f);\n"
                + guard)
    code = once(code,
                "      && HydroMechConductivityModel==1 && HydroMechConductivityCk==2. && SoilCte.dlt==float(TORAD*2.5)\n"
                "      && SoilCte.psiDecay==.2f && SoilCte.coh==5000.f && SoilCte.coh_r==1000.f && SoilCte.n_coh==5.f",
                "      && HydroMechConductivityModel==1 && HydroMechConductivityCk==2.\n"
                "      && c08Material && SoilCte.coh_r==1000.f && SoilCte.n_coh==5.f")
    code = once(code,
                "      && CaseNfluid==5000 && CaseNfixed==2060 && CaseNp==7060 && FixedDt->GetFixedValue()==5e-6\n"
                "      && (cfg->NstepsBreak==2000208 || cfg->NstepsBreak==2060200 || cfg->NstepsBreak==2240200);",
                "      && Dp==.04 && KernelH==float(.072)\n"
                "      && CaseNfluid==5000 && CaseNfixed==2060 && CaseNp==7060 && FixedDt->GetFixedValue()==5e-6\n"
                "      && (cfg->NstepsBreak==2000208 || cfg->NstepsBreak==2060200 || cfg->NstepsBreak==2240200\n"
                "        || (cfg->NstepsBreak==2600200 && TimeMax==13.001 && TimePart==.01));")
    code = once(code,
                "Private C08 check requires its bounded same-material PRE plus 200-step M0 hold and bounded release.",
                "C08 TPI requires an admitted material, its exact same-material PRE, 200-step wall hold and an admitted release window.")
    code = once(code, "TPI u-pl M0, alpha=0.5, beta=0, 3 endpoint corrections, Rh=1",
                "TPI u-pl M0, alpha=0.5, 3 endpoint corrections, Rh=1")
    entry = '    Log->Printf("  HydroMechModel=%u (%s)",model,modelname[model]);'
    return once(code, entry, entry + '\n    if(model==2)Log->Printf("  C08PrivateTpiBeta=%.8g",C08Beta());')


def invoke(command, stage):
    with (BUILD / f"{stage}.log").open("xb") as stream:
        exit_code = subprocess.run(command, cwd=SRC / "VS", stdout=stream,
                                   stderr=subprocess.STDOUT, check=False).returncode
    record(BUILD / f"{stage}.json", dict(command=command, returncode=exit_code, ended_utc=now()))
    require(exit_code == 0, f"Build failed during {stage}, inspect its saved log")


def compare_abi(dumpbin, original_obj, candidate_obj, original_program):
    def dump(flag, path):
        return subprocess.check_output([dumpbin, flag, str(path)], cwd=SRC / "VS",
                                       stderr=subprocess.STDOUT).decode("utf8", errors="replace")

    def definitions(path):
        return {s for s in re.findall(r"SECT[0-9A-F]+[^\n]*?\bExternal\s+\|\s+(\?\S+)",
                                      dump("/symbols", path)) if "JSph@@" in s}

    def dependencies(path):
        return sorted(set(re.findall(r"^\s*([a-z0-9_.-]+\.dll)\s*$",
                                     dump("/dependents", path), re.IGNORECASE | re.MULTILINE)))

    methods = definitions(original_obj)
    dlls = dependencies(original_program)
    require(len(methods) >= 100 and methods == definitions(candidate_obj), "Defined JSph ABI symbols changed")
    require(dlls and dlls == dependencies(PROGRAM), "Runtime DLL import names changed")
    return dict(defined_jsph_symbols=len(methods), symbols_equal=True, dlls=dlls, dependencies_equal=True)


def build():
    compiler, linker, dumpbin = (shutil.which(exe) for exe in ("cl.exe", "link.exe", "dumpbin.exe"))
    require(compiler and linker and dumpbin, "Use the MSVC x64 developer shell")
    control_receipt = CONTROL / "build.json"
    control = json.loads(control_receipt.read_text(encoding="utf8"))
    original_program = Path(control["exe"])
    original_source = CONTROL / "JSph.cpp"
    original_obj = CONTROL / "JSph.obj"
    original_response = CONTROL / "link.rsp"
    require(control["caps"] == CONTROL_CAPS and digest(original_program) == control["sha256"]
            and digest(original_source) == control["private_source_sha256"],
            "Sealed private positive-pressure-cap control changed")
    header_tree = CONTROL / "src/source"
    require(all((header_tree / name).is_file() for name in ("JSph.h", "JGravityPreloadState.h")),
            "Frozen control headers are missing")
    lead, *listed = original_response.read_text(encoding="utf8").splitlines()
    linked = [Path(line.strip('"')) for line in listed]
    require(len(linked) == len(set(linked)) == 113 and linked.count(original_obj) == 1
            and all(obj.stat().st_mtime_ns <= original_program.stat().st_mtime_ns for obj in linked),
            "Control linked objects are missing or newer than the sealed program")
    retained = [identity(path) for path in (control_receipt, original_program, original_response,
                                           original_source, *linked, *(CONTROL / name for name in RUNTIME))]
    original = original_source.read_text(encoding="utf8")
    transformed = formal_host(original)
    BUILD.mkdir()
    candidate = BUILD / original_source.name
    candidate.write_text(transformed, encoding="utf8")
    (BUILD / "changes.diff").write_text("".join(difflib.unified_diff(
        original.splitlines(True), transformed.splitlines(True), "control/JSph.cpp", "formal/JSph.cpp")),
        encoding="utf8")
    obj = candidate.with_suffix(".obj")
    flags = ["/c", "/nologo", "/W3", "/O2", "/Zi", "/D_WITHGPU", "/DWIN32", "/D_CONSOLE",
             "/D_VC80_UPGRADE=0x0710", "/D_MBCS", "/Gm-", "/EHsc", "/MT", "/GS", "/fp:precise",
             "/Zc:wchar_t", "/Zc:forScope", "/Zc:inline", "/openmp", "/external:W3", "/Gd", "/TP", "/FC"]
    invoke([compiler, *flags, "/I"+str(header_tree), "/I"+str(CUDA / "include"),
            "/Fo"+str(obj), "/Fd"+str(BUILD / "JSph.pdb"), str(candidate)], "compile_JSph")
    objects = [obj if prior == original_obj else prior for prior in linked]
    require([(a, b) for a, b in zip(linked, objects, strict=True) if a != b] == [(original_obj, obj)],
            "Only the new host admission object may replace a retained object")
    for key, suffix in (("OUT", ".exe"), ("PDB", ".pdb"), ("LTCGOUT", ".iobj"), ("IMPLIB", ".lib")):
        lead, count = re.subn("/" + key + r':"[^"]+"',
                             lambda _: '/' + key + ':"' + str(PROGRAM.with_suffix(suffix)) + '"', lead)
        require(count == 1, "Unexpected linker output switch " + key)
    response = BUILD / "link.rsp"
    response.write_text("\n".join([lead, *['"' + str(path) + '"' for path in objects]]), encoding="utf8")
    invoke([linker, "@"+str(response)], "link")
    for name in RUNTIME:
        shutil.copy2(CONTROL / name, BUILD / name)
    abi = compare_abi(dumpbin, original_obj, obj, original_program)
    require(all(identity(Path(meta["path"])) == meta for meta in retained), "Frozen input changed during build")
    record(BUILD / "static_review.json", dict(abi, linked_objects=113, unchanged_objects=112,
           replacements=[[str(original_obj), str(obj)]], changed_cuda_objects=0))
    record(BUILD / "build.json",
           dict(built_utc=now(), program=str(PROGRAM), executable=identity(PROGRAM), sha256=digest(PROGRAM),
                inputs=retained, private_source=dict(identity(candidate), sha256=digest(candidate)),
                private_link_response=identity(response), header_commit=control["header_commit"],
                header_tree=str(header_tree), unchanged_objects=112, changed_host_objects=1,
                changed_cuda_objects=0, material_contract=MODES, receiver_caps=[*CONTROL_CAPS, FULL_CAP],
                source_completed_steps=2000000, closed_wall_steps=200, step_s=5e-6, time_max_s=13.001,
                spacing_m=.04, smoothing_length_m=.072, boundary_pressure="positive-only cap",
                solver_launched=False))
    print(PROGRAM, flush=True)


if __name__ == "__main__":
    build()
