"""Build and exercise the private Cryer CPU XML selector against the real pre-XML solver."""
import argparse
import csv
import os
from pathlib import Path
import shutil
import struct
import sys

sys.dont_write_bytecode = True
import cryer_row_cpu_r1 as row
import upl_tpi_cryer_p3_cpu_r1 as prior
import upl_tpi_cryer_cpu_build_r1 as tools

OUT, LOG = prior.OUT, prior.LOG
SOURCE = OUT / "cryer_xml_cpu_r1_source"
ROW_SOURCE = OUT / "cryer_row_cpu_r1_source"
ROW_PROGRAM = OUT / "cryer_row_cpu_r1_DebugCPU/out/DualSPHysics5.2CPU_win64_debug.exe"
CASES = {"refA":None, "refB":None, "absent":None, "explicit0":"0", "explicit1":"1",
         "invalid":"2", "duplicate":"1", "dynamic_off":"1", "misplaced":"1",
         "restart":"1", "stale_env":None}
ERRORS = {"invalid":"requires 0 (explicit Kw) or 1 (TPI)", "duplicate":"Duplicate HydroMechPressureIntegrator",
          "dynamic_off":"requires HydroMech=1 and HydroMechDynamicSeepage=1",
          "misplaced":"inside special/hydromechanics", "restart":"requires a fresh start",
          "stale_env":"clear the old private environment switches"}
STEPS = 2


def build():
    if not (SOURCE / "VS").exists():
        shutil.copytree(ROW_SOURCE / "VS", SOURCE / "VS")
    prior.SRC, prior.BUILD = SOURCE, BUILD
    prior.build()
    intdir = Path(os.environ["LOCALAPPDATA"]) / "Temp" / BUILD / "int"
    hashes = {}
    for name in ("JSph.cpp", "JSphCpu.cpp", "JSphCpuSingle.cpp"):
        unit = SOURCE/"source"/name
        deps = tools.read(intdir/(unit.stem+".dependencies.json"))["Data"]
        tools.need(Path(deps["Source"]).resolve()==unit.resolve(), "Wrong private translation unit "+name)
        hashes[name]=row.digest(unit)
    tools.write_new(LOG/(BUILD+".source.json"), dict(program_sha256=row.digest(PROGRAM),
        source_root=str(SOURCE), translation_unit_sha256=hashes))


def seed(label, tag):
    folder = prior.SEED if label in ("refB","explicit1") or CASES[label] in ("1","2") else OUT/(prior.INPUT_NAME+"_seed")
    prefix = folder/prior.INPUT_NAME
    if CASES[label] is None:
        return prefix
    target = OUT/(tag+"_seed")
    target.mkdir()
    prefix_out = target/prior.INPUT_NAME
    shutil.copy2(prefix.with_suffix(".bi4"), prefix_out.with_suffix(".bi4"))
    xml = prefix.with_suffix(".xml").read_bytes()
    anchor = b"                <HydroMechDynamicSeepage "
    tools.need(xml.count(anchor)==1 and b"<HydroMechPressureIntegrator" not in xml, "Unexpected seed layout")
    line = ('                <HydroMechPressureIntegrator value="%s" />' % CASES[label]).encode("ascii")
    newline = b"\r\n" if b"\r\n" in xml else b"\n"
    if label=="misplaced":
        anchor = b"            </soils>"
        tools.need(xml.count(anchor)==1,"Unique soils section required")
    xml = xml.replace(anchor, (line+newline)*(2 if label=="duplicate" else 1)+anchor)
    if label=="dynamic_off":
        enabled = anchor+b'value="1"'
        tools.need(xml.count(enabled)==1, "Unique dynamic seepage flag required")
        xml = xml.replace(enabled, anchor+b'value="0"')
    prefix_out.with_suffix(".xml").write_bytes(xml)
    return prefix_out


def run(label):
    tag = "cryer_xml_cpu_"+label+"_"+REV
    output = OUT/tag
    output.mkdir()
    prefix, program = seed(label,tag), ROW_PROGRAM if label.startswith("ref") else PROGRAM
    env = {k:v for k,v in os.environ.items() if not k.upper().startswith("UPL_TPI")}
    if label=="refB":
        env.update(UPL_TPI_CPU_R1="B", UPL_TPI_P3_ROWS_R1="3", UPL_TPI_M0_DT_R1="EQ40_RH1")
    elif label=="stale_env":
        env["UPL_TPI_CPU_R1"]="B"
    cmd = [str(program),"-cpu","-ompthreads:8","-stable",str(prefix),str(output),
           "-dirdataout","data","-svres","-nsteps:"+str(STEPS)]
    if label=="restart":
        reference = OUT/("cryer_xml_cpu_refB_"+REV)/"data"
        tools.need((reference/"Part_0001.bi4").is_file(),"Real retained PART required")
        cmd.extend(["-partbegin:1",str(reference)])
    tools.write_new(LOG/(tag+".input.json"), dict(label=label, program_sha256=row.digest(program),
        command=cmd, input_sha256={ext:row.digest(prefix.with_suffix(ext)) for ext in (".xml",".bi4")},
        private_selectors={k:v for k,v in env.items() if k.upper().startswith("UPL_TPI")}))
    negative = label in ERRORS
    try:
        tools.invoke(tag, cmd, output, env)
    except RuntimeError:
        if not negative:
            raise
    call = tools.read(LOG/(tag+".call.json"))
    if negative:
        console = (LOG/(tag+".log")).read_text(encoding="utf-8-sig", errors="replace")
        message = next((s for s in reversed(console.splitlines()) if "HydroMechPressureIntegrator" in s
                        and ERRORS[label] in s), "")
        tools.need(not call["passed"] and call["actual_Popen_wait_exit"]==call["actual_Win32_exit"]!=0 and
                   message and not list((output/"data").glob("Part_*.bi4")), "Expected selector failure before saved native state")
        tools.write_new(LOG/(tag+".reject.json"), dict(passed=True, label=label, exit=call["actual_Popen_wait_exit"],
            diagnostic=message, native_parts=0))
        return
    with (output/"Run.csv").open(encoding="utf-8-sig",newline="") as stream:
        summary, = csv.DictReader(stream,delimiter=";")
    tools.need(call["passed"] and (int(summary["Steps"]),int(summary["PartFiles"]),int(summary["PartsOut"]),
               int(summary["Np"]),int(summary["Nfixed"]))==(STEPS,2,0,37181,8), "Short CPU run/particles/exclusions")
    from cryer_p3_verify_r1 import audit, EXPECTED_TYPES, read
    use_b = label in ("refB","explicit1")
    dt = 2.**(-19 if use_b else -20)
    ref = None if label.startswith("ref") else OUT/("cryer_xml_cpu_ref"+("B" if use_b else "A")+"_"+REV)
    frames = audit(output/"data",[0,STEPS],dt,(ref/"data") if ref else None,exact=bool(ref))
    if ref:
        for i in range(2):
            file = "Part_%04d.bi4" % i
            new, old = [read(folder/"data"/file)["part"]["values"] for folder in (output,ref)]
            for key in ("TimeStep","SymplecticDtPre","dterror"):
                tools.need(struct.pack("<d",new[key])==struct.pack("<d",old[key]), "Native clock differs: "+key)
    sidecars = {}
    if use_b:
        detail = tools.read(output/"UplTpiP3CpuR1.summary.json")
        tools.need(detail["completed"] and detail["commits"]==STEPS and detail["endpoint_writes"]==3*STEPS,
                   "Explicit B did not actually run all endpoints")
        if ref:
            for name in ("UplTpiP3CpuR1.csv","UplTpiP3CpuR1.summary.json","UplTpiP3DtR1.csv","UplTpiP3DtR1.summary.json"):
                sidecars[name] = row.digest(output/name)
                tools.need(sidecars[name]==row.digest(ref/name), "Pressure/dt evidence differs: "+name)
    else:
        tools.need(not list(output.glob("UplTpi*")), "Default inadvertently ran the private pressure path")
    tools.write_new(LOG/(tag+".native.json"),dict(passed=True, label=label, reference=str(ref) if ref else None,
        fields_exact_by_id=sorted(EXPECTED_TYPES) if ref else None, native_frames=frames,
        matched_time_dt_signed_dterror=bool(ref), matched_sidecar_sha256=sidecars,
        loop_seconds=float(summary["TSimul"]), excluded=0, completed_steps=STEPS, dt_s=dt))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["build",*CASES])
    parser.add_argument("--revision",type=int,default=1,help="fresh build and run output revision")
    args=parser.parse_args()
    if args.revision<1:
        parser.error("revision must be positive")
    REV = "r"+str(args.revision)
    BUILD = "cryer_xml_cpu_"+REV+"_DebugCPU"
    PROGRAM = OUT/BUILD/"out/DualSPHysics5.2CPU_win64_debug.exe"
    if args.action=="build":
        build()
    else:
        run(args.action)
