"""Prepare, build and short-test the strict model and load XML on the private Cryer P3 solvers."""
import argparse
import csv
import filecmp
import os
import re
import shutil
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True
import cryer_model_cpu_r1 as cpu
import cryer_xml_gpu_r1 as gpu
from cryer_model_prepare_r1 import MODEL
from cryer_row_gpu_r1 import call, load, need, save
from cryer_xml_prepare_r1 import edit, replace

OUT, LOG = cpu.OUT, cpu.LOG
PUBLIC = OUT.parents[4] / "src/source"
SEED_NAME = "upl_cryer_freebody_short_r1"
REFERENCES = {
    "cpu": ("missing", "zero", "one", "two"),
    "gpu": ("missing", "model0", "model1", "model2"),
}
VALID = ("default", "model0", "model1", "model2")
OLD_DYNAMIC = "HydroMechDynamicSeepage"
OLD_INTEGRATOR = "HydroMechPressureIntegrator"
LOAD_KEYS = ("HydroMechTopLoadMode", "HydroMechTopLoadQ0", "HydroMechTopLoadRampTime")
INVALID = {"legacy": OLD_DYNAMIC, "mixed": OLD_DYNAMIC, "integrator": OLD_INTEGRATOR,
           "legacy_load": LOAD_KEYS[0], "mixed_load": LOAD_KEYS[0], "old_alpha": "PoreTpiAlpha"}


def tag(backend):
    return f"cryer_model_strict_{backend}_r1"


def source_root(backend):
    return OUT / (tag(backend) + "_source")


def block(text, start, end):
    first = text.index(start)
    return text[first:text.index(end, first + len(start))]


def configure(previous, public):
    """Share the active public XML parser while retaining this Cryer binary's three-round entry."""
    read_load = block(public, "void JSph::ReadExternalLoad(", "\n//====")
    initialization = "void JSph::InitSoilParameters("
    previous = replace(previous, initialization, read_load + "\n" + initialization)
    # The frozen Cryer program predates the FreeSeepage operator. Fail closed for this key.
    strict = block(public, "  if(hydroNode)sxml->CheckElementNames(hydroEle,true,", "  //-Soil strength parameters.")
    strict = replace(strict, "HydroMechDrainageFixedGrid HydroMechFreeSeepage ", "HydroMechDrainageFixedGrid ")
    previous = replace(previous, block(previous, "  //-Reject removed experimental controls", "  //-Soil strength parameters."), strict)
    model = block(public, "  const TiXmlElement* model=hydroEle->FirstChildElement", "  HydroMechConductivityModel=sxml")
    model = block(model, "  const TiXmlElement* model=", "  if(modelid==2)Run_Exceptioon")
    env_guard = block(MODEL, "  for(const char* key:", "  if(solidEle->FirstChildElement")
    dispatch = re.sub(r"\bmodel\b", "modelid", MODEL[MODEL.index("  if(model && !HydroMech)"):])
    previous = replace(previous, MODEL, env_guard + model +
        '  if(modelid>2)Run_Exceptioon("HydroMechModel must be 0 (u-pw), 1 (explicit u-pl) or 2 (TPI).");\n' + dispatch)
    next_read = "  //-Pore-water material properties and pore-pressure numerical controls."
    previous = replace(previous, block(previous, "  const string toploadmodestr=", next_read),
                       "  ReadExternalLoad(sxml,solidEle->Parent()->ToElement());\n\n")
    stop = "  //-Input validation."
    previous = replace(previous, block(previous,next_read,stop), block(public,next_read,stop))
    for line in previous.splitlines(keepends=True):
        if line.startswith('    if(HydroMechTopLoadMode!=HMLOAD_None') and 'Run_Exceptioon("HydroMechTopLoad' in line:
            previous = replace(previous, line, "")
    previous = replace(previous, "Evolving conductivity requires HydroMechDynamicSeepage=1.", "Evolving conductivity requires a dynamic HydroMechModel.")
    return previous


def prepare(backend):
    original = OUT / ("cryer_model_" + backend + "_r1_source")
    destination = source_root(backend)
    units = Path("source") if backend == "cpu" else Path()
    public = (PUBLIC/"JSph.cpp").read_text(encoding="latin1")
    public_h = (PUBLIC/"JSph.h").read_text(encoding="latin1")
    signature = next(line for line in public_h.splitlines() if "void ReadExternalLoad(" in line)
    def header(old):
        old = replace(old, "class JXml;", "class JXml;\nclass TiXmlElement;")
        return replace(old, "  void InitSoilParameters(", signature + "\n  void InitSoilParameters(")
    for leaf, fn in (("JSph.cpp",lambda s: configure(s,public)),("JSph.h",header)):
        fn((original/units/leaf).read_text(encoding="latin1"))
    shutil.copytree(original,destination)
    edit(destination/units/"JSph.cpp", lambda s: configure(s,public))
    edit(destination/units/"JSph.h",header)
    print(destination,flush=True)


def build(backend):
    name = tag(backend)
    if backend == "cpu":
        cpu.legacy.SOURCE = source_root(backend)
        cpu.legacy.BUILD = name + "_DebugCPU"
        cpu.legacy.PROGRAM = OUT / cpu.legacy.BUILD / "out/DualSPHysics5.2CPU_win64_debug.exe"
        cpu.legacy.build()
    else:
        gpu.TAG = name
        gpu.build(source_root(backend))


def make_seed(backend, profile, output):
    index = VALID.index(profile) if profile in VALID else 3
    reference = OUT / ("cryer_model_" + backend + "_r1_" + REFERENCES[backend][index])
    source = reference.with_name(reference.name + "_seed") / SEED_NAME
    tree = ET.parse(source.with_suffix(".xml"))
    special = tree.getroot().find("execution/special")
    hydro = special.find("hydromechanics")
    params = [hydro.find(key) for key in LOAD_KEYS]
    need(all(p is not None for p in params), "Expected three original load fields")
    if profile != "legacy_load":
        ET.SubElement(special, "externalload", {
            "mode": params[0].attrib["value"], "q0": params[1].attrib["value"],
            "ramptime": params[2].attrib["value"],
        })
    if profile != "legacy_load" and profile != "mixed_load":
        for p in params:
            hydro.remove(p)
    if profile in ("legacy", "mixed"):
        if profile == "legacy":
            hydro.remove(hydro.find("HydroMechModel"))
        ET.SubElement(hydro, OLD_DYNAMIC, {"value": "1"})
    elif profile == "integrator":
        ET.SubElement(hydro, OLD_INTEGRATOR, {"value": "1"})
    elif profile == "old_alpha":
        ET.SubElement(hydro, "PoreTpiAlpha", {"value": "0.5"})
    directory = output.with_name(output.name + "_seed")
    directory.mkdir()
    prefix = directory / SEED_NAME
    tree.write(prefix.with_suffix(".xml"), encoding="utf-8", xml_declaration=True)
    shutil.copyfile(source.with_suffix(".bi4"), prefix.with_suffix(".bi4"))
    return prefix, reference


def run(backend, profile):
    label = tag(backend) + "_" + profile
    receipt = LOG / (label + ".check.json")
    output = OUT / label
    need(not receipt.exists() and not output.exists(), "Fresh output required: " + label)
    suffix = "_DebugCPU" if backend == "cpu" else "_Release"
    product = load(LOG / (tag(backend) + suffix + ".build.json"))
    need(product["passed"], "Build failed")
    exe = Path(product["program"]["path"])
    need(exe.is_file() and exe.stat().st_size == product["program"]["bytes"],
         "Missing or changed private executable")
    prefix, ref = make_seed(backend, profile, output)
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("UPL_TPI")}
    args = [str(exe), "-" + backend]
    if backend == "cpu":
        args.append("-ompthreads:8")
    args.extend(["-stable", str(prefix), str(output), "-dirdataout", "data", "-svres", "-nsteps:2"])
    console = LOG / (label + ".console.log")
    rec = call(args, exe.parent, env, console)
    rec.update(passed=False, profile=profile)
    try:
        msg = console.read_text(encoding="utf-8-sig", errors="replace")
        need(rec["win32_exit"] == rec["popen_exit"], "Exit observations disagree")
        if profile in INVALID:
            errors = [line.strip() for line in msg.splitlines()
                      if "Error reading xml" in line and INVALID[profile] in line]
            need(rec["popen_exit"] == 1 and errors and not list((output/"data").glob("Part_*.bi4")),
                 "Missing expected rejection of " + INVALID[profile])
            rec.update(saved=0, rejection=errors[-1])
        else:
            model = 0 if profile == "default" else int(profile[-1])
            dt = 2.**(-19 if model == 2 else -20)
            need(rec["popen_exit"] == 0 and f"HydroMechModel={model}" in msg, "Unexpected model/exit")
            with (output/"Run.csv").open(encoding="utf-8-sig", newline="") as f:
                summary, = csv.DictReader(f, delimiter=";")
            need(tuple(int(summary[key]) for key in ("Steps","PartFiles","PartsOut","Np","Nfixed"))
                 == (2,2,0,37181,8), "Unexpected native output schedule")
            fields = cpu.verify_native(output,ref,model,dt)
            ledgers = sorted(p.name for p in ref.glob("UplTpi*"))
            need(sorted(p.name for p in output.glob("UplTpi*")) == ledgers and bool(ledgers) == (model == 2),
                 "Wrong pressure/dt diagnostics")
            for name in ledgers:
                need(filecmp.cmp(output/name,ref/name,shallow=False), "Changed pressure/dt ledger " + name)
            if model == 2:
                stem = "Cpu" if backend == "cpu" else "Gpu"
                p3 = load(output / ("UplTpiP3" + stem + "R1.summary.json"))
                need(p3["commits"] == 2 and p3["endpoint_writes"] == 6, "Expected three rounds per update")
            rec.update(model=model, native_frames=2, matched_ids=37181, exact_arrays=sorted(fields),
                       actual_times_s=[0.,2*dt], exact_clocks=list(cpu.NATIVE_CLOCK),
                       exact_pressure_dt_ledgers=ledgers, previous_runtime_reference=str(ref))
        rec["passed"] = True
    finally:
        save(receipt, rec)
    print(label, "passed", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backend", choices=("cpu","gpu"))
    parser.add_argument("action", choices=("prepare","build","suite",*VALID,*INVALID))
    opts = parser.parse_args()
    if opts.action == "prepare":
        prepare(opts.backend)
    elif opts.action == "build":
        build(opts.backend)
    else:
        for profile in ((*VALID,*INVALID) if opts.action == "suite" else (opts.action,)):
            run(opts.backend,profile)
