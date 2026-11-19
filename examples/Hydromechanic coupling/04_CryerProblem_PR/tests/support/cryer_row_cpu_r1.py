"""Build the private Cryer CPU P3 solver with the common pressure row and check real saves."""
import argparse
import csv
import difflib
import hashlib
import os
from pathlib import Path
import shutil
import struct
import sys

sys.dont_write_bytecode = True
import upl_tpi_cryer_p3_cpu_r1 as prior
import upl_tpi_cryer_cpu_build_r1 as tools

TEST, OUT, LOG = prior.TEST, prior.OUT, prior.LOG
COMMON = TEST / "support/TpiPressureRow.h"
DRIVER = "upl_tpi_cpu_r1.h"
REFERENCE = {"A128": OUT / "upl_cryer_freebody_smoke128_CPU_r1", "B64": OUT / prior.B64}


def digest(file):
    with file.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def build():
    # Inputs and all common Cryer XYZ force, boundary and history driver code
    # are copied from the retained, HG0-qualified three-round implementation.
    shutil.copytree(prior.SRC, SOURCE)
    path = SOURCE / "source" / DRIVER
    old = prior.source_text(path)
    data = prior.once(old, '#include "DualSphDef.h"',
                      '#include "DualSphDef.h"\n#include "TpiPressureRow.h"')
    data = prior.once(data, "inline double Alpha(){return RequestedScheme()==B_Tpi?.5:0.;}\n", "")
    data = prior.once(data, prior.section(data, "// The mechanical half", "struct Core{"), "")
    data = prior.once(data,
        "    s.predicted[k]=(Alpha()==0.?double(pn[a]):Predict(double(pn[a]),double(s.previous[k]),.5));s.half[k]=float(s.predicted[k]);s.q[k]=s.half[k];",
        '    Need(tpi_pressure::Predict(tpi_pressure::Predictor::Linear,pn[a],s.previous[k],s.predicted[k]),\n'
        '      "Invalid or overflowing linear pressure prediction");\n'
        '    s.half[k]=tpi_pressure::WritePressure(s.predicted[k]);s.q[k]=s.half[k];')
    data = prior.once(data, "return float(state.predicted[id]);", "return tpi_pressure::WritePressure(state.predicted[id]);")
    data = prior.once(data,
        "    s.coreFieldChecks+=7;s.raw[k]=float(SolveBeta0(bool(s.drained[k]),double(s.q[k]),s.S[k],s.R[k]));",
        '    s.coreFieldChecks+=7;\n'
        '    Need(tpi_pressure::Endpoint(bool(s.drained[k]),s.q[k],s.S[k],s.R[k],s.raw[k]),\n'
        '      "Invalid or overflowing beta0 endpoint row");')
    path.write_text(data, encoding="utf-8")
    patch = SOURCE / ("cryer_row_cpu_"+REVISION+".patch")
    with patch.open("x", encoding="utf-8", newline="\n") as stream:
        stream.writelines(difflib.unified_diff(old.splitlines(keepends=True), data.splitlines(keepends=True),
            fromfile="a/source/"+DRIVER, tofile="b/source/"+DRIVER))
    header = SOURCE / "source" / COMMON.name
    shutil.copy2(COMMON, header)
    # Reuse the private VS2022 solution, library staging, actual MSBuild command
    # and object/dependency checks. Only the source/build destinations change.
    prior.SRC = SOURCE
    prior.BUILD = BUILD
    prior.build()
    intdir = Path(os.environ["LOCALAPPDATA"]) / "Temp" / BUILD / "int"
    for tu in ("JSphCpu", "JSphCpuSingle"):
        deps = tools.read(intdir / (tu + ".dependencies.json"))["Data"]["Includes"]
        tools.need(header.resolve() in {Path(name).resolve() for name in deps}, "Common row omitted by " + tu)
    tools.write_new(LOG / (BUILD + ".row.json"), dict(passed=True, program_sha256=digest(PROGRAM),
        shared_header_sha256=digest(header), input_driver_sha256=digest(OUT / "upl_tpi_cryer_p3_cpu_r1_source/source" / DRIVER),
        integrated_driver_sha256=digest(path), dependency_verified=["JSphCpu.cpp","JSphCpuSingle.cpp"]))


def run(label):
    steps = 128 if label=="A128" else 64
    tag = "cryer_row_cpu_" + label + "_" + REVISION
    output = OUT / tag
    output.mkdir()
    seed = OUT / (prior.INPUT_NAME + "_seed") if label=="A128" else prior.SEED
    prefix = seed / prior.INPUT_NAME
    env = {k:v for k,v in os.environ.items() if not k.upper().startswith("UPL_TPI")}
    flags = {} if label=="A128" else dict(UPL_TPI_CPU_R1="B",UPL_TPI_P3_ROWS_R1="3",UPL_TPI_M0_DT_R1="EQ40_RH1")
    env.update(flags)
    cmd = [str(PROGRAM), "-cpu", "-ompthreads:8", "-stable", str(prefix), str(output),
           "-dirdataout", "data", "-svres", "-nsteps:"+str(steps)]
    tools.write_new(LOG / (tag + ".input.json"), dict(solver_sha256=digest(PROGRAM), command=cmd,
        private_selectors={k:v for k,v in env.items() if k.upper().startswith("UPL_TPI")},
        inputs={ext:digest(prefix.with_suffix(ext)) for ext in (".xml",".bi4")}))
    tools.invoke(tag, cmd, output, env)
    compare(label)


def compare(label):
    from cryer_p3_verify_r1 import audit, EXPECTED_TYPES, read
    steps, dt = (128, 2.**-20) if label=="A128" else (64, 2.**-19)
    tag = "cryer_row_cpu_" + label + "_" + REVISION
    output = OUT / tag
    call = tools.read(LOG / (tag + ".call.json"))
    tools.need(call["passed"] and call["actual_Popen_wait_exit"]==call["actual_Win32_exit"]==0,
               "Direct CPU solver failed")
    prefix = Path(call["arguments"][3])
    with (output/"Run.csv").open(encoding="utf-8-sig", newline="") as src:
        result, = csv.DictReader(src, delimiter=";")
    tools.need((int(result["Steps"]),int(result["PartFiles"]),int(result["PartsOut"]),
                int(result["Np"]),int(result["Nfixed"]))==(steps,2,0,37181,8), "CPU completion/IDs/exclusions")
    reference = REFERENCE[label]
    history = audit(output/"data", [0,steps], dt, reference/"data", exact=True)
    # Snapshot validation checks numerical times. Compare IEEE-754 bytes as
    # well, including the sign bit of the initial zero on both solvers.
    for i in range(2):
        name = "Part_%04d.bi4" % i
        new, old = [read(folder/"data"/name)["part"]["values"] for folder in (output,reference)]
        for key in ("TimeStep", "SymplecticDtPre", "dterror"):
            tools.need(struct.pack("<d",new[key])==struct.pack("<d",old[key]), "Native clock differs in "+key)
    sidecars = {}
    if label=="B64":
        for name in ("UplTpiP3CpuR1.csv", "UplTpiP3CpuR1.summary.json", "UplTpiP3DtR1.csv", "UplTpiP3DtR1.summary.json"):
            sidecars[name] = digest(output/name)
            tools.need(sidecars[name]==digest(reference/name), "CPU P3 records differ in "+name)
        summary = tools.read(output/"UplTpiP3CpuR1.summary.json")
        tools.need(summary["commits"]==64 and summary["endpoint_calls"]==summary["endpoint_writes"]==192
                   and summary["core_field_bit_checks"]==7*37173*192, "Actual three-round counts")
    else:
        tools.need(not list(output.glob("UplTpi*")), "Original-default path created TPI evidence")
    tools.write_new(LOG / (tag + ".compare.json"), dict(passed=True, label=label, actual_call=tools.stat(LOG/(tag+".call.json")),
        solver_sha256=digest(PROGRAM), input_sha256={ext:digest(prefix.with_suffix(ext)) for ext in (".xml",".bi4")},
        output=str(output), reference=str(reference), dt_s=dt,
        loop_seconds=float(result["TSimul"]), excluded=int(result["PartsOut"]),
        fields_exact_by_id=sorted(EXPECTED_TYPES), saved_states=history,
        time_and_dt_and_signed_dterror_bits_match=True, matching_sidecar_sha256=sidecars))


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action", choices=["build","A128","B64","compare-A128","compare-B64"])
    cli.add_argument("--revision", type=int, default=1, help="New output revision for an independent repeat")
    args=cli.parse_args()
    if args.revision<1:
        cli.error("revision must be positive")
    REVISION = "r"+str(args.revision)
    SOURCE = OUT / ("cryer_row_cpu_"+REVISION+"_source")
    BUILD = "cryer_row_cpu_"+REVISION+"_DebugCPU"
    PROGRAM = OUT / BUILD / "out/DualSPHysics5.2CPU_win64_debug.exe"
    if args.action=="build":
        build()
    elif args.action.startswith("compare-"):
        compare(args.action.split("-")[1])
    else:
        run(args.action)
