"""Build the sealed C08 finer-grid receiver without starting a simulation."""
import difflib
import json
from pathlib import Path
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

from c08_m0_coupled_baseline_gpu_r1 import BUILD as SINGLE
from c08_m0_gpu_coupled_r1 import BUILD as GPU, CUDA, SRC, once
from c08_psi25_tpi_build import OUT as CONTROL, RUNTIME, digest
from c08_psi25_tpi_run import PRE, TESTS, identity, now, record


BUILD = TESTS / "outputs/c08_dp03125_tpi_build_r1"
PROGRAM = BUILD / "C08Dp03125Tpi.exe"
SEED = TESTS / "outputs/c08_dp03125_pre_seed_r4/seed.json"
DP, H, DT = .03125, .05625, 5e-6
FIXED_PARTS = [[0, 0, 325], [1, 325, 1970], [2, 2295, 325]]
NFIXED, NMATERIAL = 2620, 8192
TOTAL = NFIXED + NMATERIAL
RELEASE_MK, RIGHT_FIRST, RIGHT_COUNT = FIXED_PARTS[-1]
CAPS = [2000208, 2060200, 2240200]


def require(valid, message):
    if not valid:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding="utf8"))


def verify_seed():
    verified = read_json(SEED)
    require((verified["spacing"], verified["fixed"], verified["material"], verified["fixed_parts"])
            == (DP, NFIXED, NMATERIAL, FIXED_PARTS), "Unexpected finer seed receipt")
    require(all(identity(Path(item["path"])) == item for item in verified["files"]),
            "Finer seed changed since generation")
    source = ET.parse(SEED.parent / "c08_dp03125_pre.xml")
    particles = source.find("execution/particles")
    fixed_parts = [[int(e.get(k)) for k in ("mkbound", "begin", "count")]
                   for e in particles.findall("fixed")]
    fluid, = particles.findall("fluid")
    require(tuple(int(particles.get(k)) for k in ("np", "nb", "nbf")) == (TOTAL, NFIXED, NFIXED)
            and fixed_parts == FIXED_PARTS
            and (int(fluid.get("begin")), int(fluid.get("count"))) == (NFIXED, NMATERIAL),
            "GenCase XML does not match the reviewed wall and material ranges")
    constants = source.find("execution/constants")
    require((float(constants.find("dp").get("value")), float(constants.find("h").get("value")))
            == (DP, H), "GenCase XML does not match reviewed physical scales")
    return verified["files"]


def finer_host(name, code):
    if name == "JSph":
        code = once(code,
                    "      && CaseNfluid==5000 && CaseNfixed==2060 && CaseNp==7060 && FixedDt->GetFixedValue()==5e-6",
                    f"      && Dp=={DP} && KernelH==float({H})\n"
                    f"      && CaseNfluid=={NMATERIAL} && CaseNfixed=={NFIXED} && CaseNp=={TOTAL}\n"
                    f"      && FixedDt->GetFixedValue()=={DT:g}")
        return once(code,
                    "GravityPreloadKeepBedOverlap || GravityPreloadIdBegin!=1805 || removed!=255",
                    f"GravityPreloadKeepBedOverlap || GravityPreloadIdBegin!={RIGHT_FIRST} || removed!={RIGHT_COUNT}")
    if name == "JSphGpuSingle":
        return once(code,
                    "  if(Nstep!=2000000 || GravityPreloadReleased || Np!=7060 || Npb!=2060 || SymplecticDtPre!=5e-6)",
                    f"  if(Nstep!=2000000 || GravityPreloadReleased || Np!={TOTAL} || Npb!={NFIXED}\n"
                    f"    || GravityPreloadMkBound!={RELEASE_MK} || GravityPreloadIdBegin!={RIGHT_FIRST}\n"
                    f"    || GravityPreloadIdCount!={RIGHT_COUNT} || SymplecticDtPre!={DT:g})")
    raise ValueError(name)


def invoke(command, kind):
    with (BUILD / f"{kind}.log").open("xb") as stdout:
        status = subprocess.run(command, cwd=SRC / "VS", stdout=stdout,
                                stderr=subprocess.STDOUT, check=False).returncode
    record(BUILD / f"{kind}.json", dict(command=command, returncode=status, ended_utc=now()))
    require(status == 0, f"Build failed at {kind}")


def build():
    refined_inputs = verify_seed()
    compiler, linker = shutil.which("cl.exe"), shutil.which("link.exe")
    require(compiler and linker, "Use the MSVC x64 developer shell")
    control_receipt = CONTROL / "build.json"
    single_receipt = SINGLE / "build.json"
    control = read_json(control_receipt)
    single = read_json(single_receipt)
    parent = Path(control["exe"])
    sources = {"JSph": CONTROL / "JSph.cpp", "JSphGpuSingle": SINGLE / "JSphGpuSingle.cpp"}
    require(control["caps"] == CAPS and digest(parent) == control["sha256"]
            and digest(sources["JSph"]) == control["private_source_sha256"]
            and digest(sources["JSphGpuSingle"]) == single["changed"]["JSphGpuSingle"]["changed"],
            "Sealed control program or matching host source changed")
    original_response = CONTROL / "link.rsp"
    lead, *listed = original_response.read_text(encoding="utf8").splitlines()
    original_objects = [Path(line.strip('"')) for line in listed]
    old_host = [path.with_suffix(".obj") for path in sources.values()]
    require(len(original_objects) == len(set(original_objects)) == 113
            and all(original_objects.count(path) == 1 for path in old_host)
            and all(path.stat().st_mtime_ns <= parent.stat().st_mtime_ns
                    for path in original_objects), "Original linked objects missing or modified")
    received = [*refined_inputs, identity(SEED)]
    received += [identity(path) for path in (PRE, parent, original_response, control_receipt,
                                            single_receipt, GPU / "JSphGpu_ker.h", *sources.values(),
                                            *(CONTROL / name for name in RUNTIME), *original_objects)]
    header_tree = CONTROL / "src/source"
    require(all((header_tree / name).is_file() for name in
                ("JSph.h", "JSphGpu.h", "JSphGpuSingle.h", "JGravityPreloadState.h")),
            "Frozen control header tree is missing")

    BUILD.mkdir()
    flags = ["/c", "/nologo", "/W3", "/O2", "/Zi", "/D_WITHGPU", "/DWIN32", "/D_CONSOLE",
             "/D_VC80_UPGRADE=0x0710", "/D_MBCS", "/Gm-", "/EHsc", "/MT", "/GS", "/fp:precise",
             "/Zc:wchar_t", "/Zc:forScope", "/Zc:inline", "/openmp", "/external:W3", "/Gd", "/TP", "/FC"]
    includes = [GPU, TESTS / "support", header_tree, CUDA / "include"]
    differences = []
    candidates = []
    objects = original_objects.copy()
    for name, source in sources.items():
        original = source.read_text(encoding="utf8")
        transformed = finer_host(name, original)
        candidate = BUILD / source.name
        candidate.write_text(transformed, encoding="utf8")
        candidates.append(candidate)
        differences.extend(difflib.unified_diff(
            original.splitlines(True), transformed.splitlines(True),
            f"control/{source.name}", f"finer/{source.name}"))
    (BUILD / "changes.diff").write_text("".join(differences), encoding="utf8")
    for older, candidate in zip(old_host, candidates, strict=True):
        obj = candidate.with_suffix(".obj")
        cmd = [compiler, *flags, *["/I"+str(path) for path in includes], "/Fo"+str(obj),
               "/Fd"+str(candidate.with_suffix(".pdb")), str(candidate)]
        invoke(cmd, "compile_"+candidate.stem)
        objects[objects.index(older)] = obj
    require([after for before, after in zip(original_objects, objects, strict=True)
             if before != after] == sorted([path.with_suffix(".obj") for path in candidates],
                                          key=objects.index), "Unexpected object substitution")
    for key, suffix in (("OUT", ".exe"), ("PDB", ".pdb"), ("LTCGOUT", ".iobj"), ("IMPLIB", ".lib")):
        lead, count = re.subn("/"+key+r':"[^"]+"', lambda _: '/'+key+':"'+
                             str(PROGRAM.with_suffix(suffix))+'"', lead)
        require(count == 1, "Unexpected linker output switch "+key)
    response = BUILD / "link.rsp"
    response.write_text("\n".join([lead, *['"'+str(path)+'"' for path in objects]]), encoding="utf8")
    invoke([linker, "@"+str(response)], "link")
    for name in RUNTIME:
        shutil.copy2(CONTROL / name, BUILD / name)
    require(all(identity(Path(item["path"])) == item for item in received),
            "An original input changed during construction")
    record(BUILD / "build.json",
           dict(built_utc=now(), program=str(PROGRAM), executable=identity(PROGRAM),
                sha256=digest(PROGRAM), seed=identity(SEED), inputs=received,
                private_sources=[dict(**identity(path), sha256=digest(path)) for path in candidates],
                private_link_response=identity(response), header_commit=control["header_commit"],
                header_tree=str(header_tree), unchanged_objects=111, changed_host_objects=2,
                changed_cuda_objects=0, fixed_parts=FIXED_PARTS, receiver_caps=CAPS, closed_wall_steps=200,
                source_completed_steps=2000000, spacing_m=DP, smoothing_length_m=H, step_s=DT,
                material=NMATERIAL, fixed=NFIXED, total=TOTAL, right_range=[RIGHT_FIRST, NFIXED],
                boundary_pressure="positive-only cap", solver_launched=False))
    print(PROGRAM, flush=True)


if __name__ == "__main__":
    build()
