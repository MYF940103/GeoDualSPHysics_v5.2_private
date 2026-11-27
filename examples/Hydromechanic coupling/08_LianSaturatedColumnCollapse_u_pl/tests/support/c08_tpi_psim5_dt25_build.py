"""Relink the frozen formal C08 receiver for the isolated −5° timestep retry."""
import difflib
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

CASE = Path(__file__).resolve().parents[2]
ROOT = CASE.parents[2]
OUTPUTS = CASE / "tests/outputs"
ORIGINAL = OUTPUTS / "c08_tpi_formal_build_r1"
ORIGINAL_GPU = OUTPUTS / "c08_m0_coupled_baseline_gpu_r1_build"
BUILD = OUTPUTS / "c08_tpi_psim5_dt25_build_r1"
PROGRAM = BUILD / "C08TpiPsim5Dt25.exe"
RUNTIME_FILES = "ChronoEngine.dll", "dsphchrono.dll", "vcomp140.dll", "DsphConfig.xml"
SOURCE = 2_000_000
SOURCE_DT = 5e-6
DT = 2.5e-6
HOLD = 400
OPEN = SOURCE + HOLD
SAVE_STEPS = 4_000
FILTER_STEPS = 80
CAPS = {"short": OPEN + 8, "full": OPEN + 300 * SAVE_STEPS}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def identity(path):
    return dict(path=str(path), bytes=path.stat().st_size, mtime_ns=path.stat().st_mtime_ns)


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save(path, data):
    with path.open("x", encoding="utf8") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)
        stream.write("\n")


def replace(source, old, new):
    require(source.count(old) == 1, "Frozen source literal missing or ambiguous: " + old)
    return source.replace(old, new, 1)


def host_source(code):
    material = (
        "    const bool c08Material=\n"
        "      (SoilCte.dlt==0.f && SoilCte.coh==5000.f && SoilCte.psiDecay==0.f)\n"
        "      || (SoilCte.dlt==float(TORAD*2.5) && SoilCte.coh==5000.f && SoilCte.psiDecay==.2f)\n"
        "      || (SoilCte.dlt==float(TORAD*(-5.)) && SoilCte.coh==7500.f && SoilCte.psiDecay==.2f);"
    )
    code = replace(code, material,
                   "    const bool c08Material=(SoilCte.dlt==float(TORAD*(-5.)) "
                   "&& SoilCte.coh==7500.f && SoilCte.psiDecay==.2f);")
    code = replace(
        code,
        "      && CaseNfluid==5000 && CaseNfixed==2060 && CaseNp==7060 && FixedDt->GetFixedValue()==5e-6\n"
        "      && (cfg->NstepsBreak==2000208 || cfg->NstepsBreak==2060200 || cfg->NstepsBreak==2240200\n"
        "        || (cfg->NstepsBreak==2600200 && TimeMax==13.001 && TimePart==.01));",
        f"      && CaseNfluid==5000 && CaseNfixed==2060 && CaseNp==7060 && FixedDt->GetFixedValue()=={DT:g}\n"
        f"      && (cfg->NstepsBreak=={CAPS['short']} || cfg->NstepsBreak=={CAPS['full']})\n"
        "      && TimeMax==13.001 && TimePart==.01;",
    )
    # Reconstruct the exact 5 us source contract. The reader still validates
    # every value, source clock and fingerprint written by the source solver.
    code = replace(
        code,
        "<<PoreMdbcInterpolationMode<<' '<<PoreDtSafety<<' '<<CFLnumber<<' '<<FixedDt->GetFixedValue()<<' '",
        f"<<PoreMdbcInterpolationMode<<' '<<PoreDtSafety<<' '<<CFLnumber<<' '<<{SOURCE_DT:g}<<' '",
    )
    code = replace(
        code,
        "    state.Load(file,GetGravityPreloadContract(),CaseNp,CaseNpb,GravityPreloadStep,GravityPreloadTime,\n"
        "      FixedDt->GetFixedValue(),SoilCte.coh,SoilCte.Porosity,RhopZero,SoilCte.PoreWaterRho,",
        f"    state.Load(file,GetGravityPreloadContract(),CaseNp,CaseNpb,{SOURCE},GravityPreloadTime,\n"
        f"      {SOURCE_DT:g},SoilCte.coh,SoilCte.Porosity,RhopZero,SoilCte.PoreWaterRho,",
    )
    code = replace(code, "200-step wall hold", "400-step wall hold")
    return replace(code, "holds the wall for 200 complete steps.", "holds the wall for 400 complete steps.")


def gpu_source(code):
    code = replace(
        code,
        "      const bool filtered=round==2 && PoreShepardRegularization && (Nstep+1)%PoreShepardInterval==0;",
        "      //-Preserve the 0.2 ms filter spacing at half the receiver step.\n"
        "      const bool filtered=round==2 && PoreShepardRegularization && (Nstep+1)%(2*PoreShepardInterval)==0;",
    )
    code = replace(
        code,
        "  if(Nstep!=2000000 || GravityPreloadReleased || Np!=7060 || Npb!=2060 || SymplecticDtPre!=5e-6)\n"
        "    Run_Exceptioon(\"C08 original PRE clock or registry changed.\");\n"
        "  PrepareTpiPressure(PorePressg,Posxyg,true);",
        f"  if(Nstep!={SOURCE} || GravityPreloadReleased || Np!=7060 || Npb!=2060"
        f" || SymplecticDtPre!={SOURCE_DT:g})\n"
        '    Run_Exceptioon("C08 original PRE clock or registry changed.");\n'
        f"  SymplecticDtPre={DT:g}; //-Checked receiver dt; new history starts from equal pressures.\n"
        "  PrepareTpiPressure(PorePressg,Posxyg,true);",
    )
    code = replace(
        code,
        "  GravityPreloadStep=2000200;GravityPreloadTime=TimeStep;\n"
        "  for(unsigned i=0;i<200;i++)GravityPreloadTime+=SymplecticDtPre;\n"
        '  Log->Printf("C08Mature history=cold_actual_p source=%.17g M0_wall_hold=200 release=%.17g",TimeStep,GravityPreloadTime);',
        f"  GravityPreloadStep={OPEN};GravityPreloadTime=TimeStep;\n"
        f"  for(unsigned i=0;i<{HOLD};i++)GravityPreloadTime+=SymplecticDtPre;\n"
        f'  Log->Printf("C08Mature history=cold_actual_p source=%.17g M0_wall_hold={HOLD} '
        f'release=%.17g receiver_dt=%.17g closed_filter_steps={FILTER_STEPS}",TimeStep,GravityPreloadTime,SymplecticDtPre);',
    )
    return replace(
        code,
        "Nstep<2000002 || Nstep==2000198 || Nstep==2000199 || (Nstep>=2000200 && (Nstep<2000208 || (Nstep+1-2000200)%2000==0))",
        f"Nstep<{SOURCE+2} || Nstep=={OPEN-2} || Nstep=={OPEN-1} || "
        f"(Nstep>={OPEN} && (Nstep<{CAPS['short']} || (Nstep+1-{OPEN})%{SAVE_STEPS}==0))",
    )


def original_inputs():
    base = load(ORIGINAL / "build.json")
    receipt = load(ORIGINAL / "static_review.json")
    require(base["executable"] == identity(ORIGINAL / "C08FormalTpi.exe")
            and receipt["linked_objects"] == 113 and receipt["changed_cuda_objects"] == 0,
            "Wrong frozen formal baseline")
    sources = (ORIGINAL / "JSph.cpp", ORIGINAL_GPU / "JSphGpuSingle.cpp")
    require(base["private_source"]["sha256"] == hashlib.sha256(sources[0].read_bytes()).hexdigest(),
            "Formal source differs from its build")
    gpu_build = load(ORIGINAL_GPU / "build.json")
    require(identity(sources[1].with_suffix(".obj")) in base["inputs"]
            and gpu_build["changed"]["JSphGpuSingle"]["changed"] ==
                hashlib.sha256(sources[1].read_bytes()).hexdigest()
            and sources[1].stat().st_mtime_ns <= sources[1].with_suffix(".obj").stat().st_mtime_ns,
            "Frozen GPU host source or object differs")
    return base, sources


def compile_command(compiler, candidate):
    old = load(ORIGINAL / "compile_JSph.json")["command"]
    require(old[-1] == str(ORIGINAL / "JSph.cpp"), "Unexpected original compiler arguments")
    options = [f"/Fo{candidate.with_suffix('.obj')}" if arg.startswith("/Fo") else
               f"/Fd{candidate.with_suffix('.pdb')}" if arg.startswith("/Fd") else arg for arg in old[1:-1]]
    return [compiler, *options, str(candidate)]


def invoke(command, tag):
    with (BUILD / f"{tag}.log").open("xb") as stream:
        status = subprocess.run(command, cwd=ROOT / "src/VS", stdout=stream, stderr=subprocess.STDOUT).returncode
    save(BUILD / f"{tag}.json", dict(command=command, returncode=status))
    require(status == 0, f"{tag} failed ({status}); preserve the saved logs")


def prove_abi(dumpbin, replacements):
    def dump(flag, path):
        return subprocess.check_output([dumpbin, flag, str(path)], cwd=ROOT / "src/VS",
                                       encoding="utf8", errors="replace")

    def symbols(path, cls):
        return {s for s in re.findall(r"SECT[0-9A-F]+[^\n]*?\bExternal\s+\|\s+(\?\S+)",
                                      dump("/symbols", path)) if f"{cls}@@" in s}

    def dependencies(path):
        return sorted(set(re.findall(r"^\s*([a-z0-9_.-]+\.dll)\s*$",
                                     dump("/dependents", path), re.IGNORECASE | re.MULTILINE)))

    counts = {}
    for old, new in replacements.items():
        original = symbols(old, old.stem)
        require(len(original) > 20 and original == symbols(new, old.stem), f"{old.stem} symbols changed")
        counts[old.stem] = len(original)
    imports = dependencies(ORIGINAL / "C08FormalTpi.exe")
    require(imports and imports == dependencies(PROGRAM), "Runtime DLL imports changed")
    return dict(symbol_counts=counts, dlls=imports, symbols_equal=True, dependencies_equal=True)


def build():
    compiler, linker, dumpbin = (shutil.which(exe) for exe in ("cl.exe", "link.exe", "dumpbin.exe"))
    require(compiler and linker and dumpbin, "Run in the VS 2022 MSVC x64 developer shell")
    base, sources = original_inputs()
    lead, *lines = (ORIGINAL / "link.rsp").read_text(encoding="utf8").splitlines()
    objects = [Path(line.strip('"')) for line in lines]
    old_objects = [source.with_suffix(".obj") for source in sources]
    require(len(objects) == len(set(objects)) == 113 and all(objects.count(obj) == 1 for obj in old_objects),
            "Expected exactly two original host objects")
    observed = {Path(row["path"]): row for row in base["inputs"]}
    for obj in objects:
        if obj != old_objects[0]:
            require(identity(obj) == observed.get(obj), f"Original linked object differs: {obj}")
    frozen = [identity(p) for p in (*sources, *objects, ORIGINAL / "link.rsp", ORIGINAL / "C08FormalTpi.exe",
                                     *(ORIGINAL / name for name in RUNTIME_FILES))]
    BUILD.mkdir()
    replacements = {}
    for source, transform in zip(sources, (host_source, gpu_source), strict=True):
        candidate = BUILD / source.name
        original = source.read_text(encoding="utf8")
        changed = transform(original)
        candidate.write_text(changed, encoding="utf8")
        (BUILD / f"{source.stem}.diff").write_text("".join(difflib.unified_diff(
            original.splitlines(True), changed.splitlines(True), str(source), candidate.name
        )), encoding="utf8")
        invoke(compile_command(compiler, candidate), "compile_" + source.stem)
        replacements[source.with_suffix(".obj")] = candidate.with_suffix(".obj")
    for key, suffix in (("OUT", ".exe"), ("PDB", ".pdb"), ("LTCGOUT", ".iobj"), ("IMPLIB", ".lib")):
        lead, count = re.subn("/" + key + r':"[^"]+"',
                             lambda _: f'/{key}:"{PROGRAM.with_suffix(suffix)}"', lead)
        require(count == 1, "Wrong frozen linker switch " + key)
    linked = [replacements.get(obj, obj) for obj in objects]
    response = BUILD / "link.rsp"
    response.write_text("\n".join([lead, *(f'"{obj}"' for obj in linked)]), encoding="utf8")
    invoke([linker, "@" + str(response)], "link")
    abi = prove_abi(dumpbin, replacements)
    for name in RUNTIME_FILES:
        shutil.copy2(ORIGINAL / name, BUILD / name)
    require(all(identity(Path(item["path"])) == item for item in frozen), "Frozen build inputs changed")
    save(BUILD / "build.json", dict(
        executable=identity(PROGRAM), baseline=base["executable"], inputs=frozen, abi=abi,
        linked_objects=len(linked), retained_objects=len(linked) - len(replacements),
        changed_host_objects=2, changed_cuda_objects=0, beta=.04, source_dt=SOURCE_DT,
        receiver_dt=DT, source_completed_steps=SOURCE, warm_steps=HOLD,
        closed_filter_steps=FILTER_STEPS, caps=CAPS, solver_launched=False,
    ))
    print(PROGRAM)


if __name__ == "__main__":
    build()
