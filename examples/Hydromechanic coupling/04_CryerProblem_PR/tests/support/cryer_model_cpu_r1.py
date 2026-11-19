"""Two-update native regressions for the private unified Cryer model selector."""
import argparse
import csv
import filecmp
import os
from pathlib import Path
import re
import shutil
import struct
import sys

import numpy as np

sys.dont_write_bytecode = True
import cryer_xml_cpu_checks_r1 as legacy
from cryer_p3_verify_r1 import audit, EXPECTED_TYPES, read
from upl_tpi_cryer_cpu_build_r1 import invoke, need, read as load, stat, write_new

OUT, LOG = legacy.OUT, legacy.LOG
TAG = "cryer_model_cpu_r1"
PROGRAM = OUT/(TAG+"_DebugCPU")/"out/DualSPHysics5.2CPU_win64_debug.exe"
NATIVE_CLOCK = ("TimeStep", "SymplecticDtPre", "dterror")
MODE = "HydroMechModel"
DYN = "HydroMechDynamicSeepage"
INT = "HydroMechPressureIntegrator"
SELECTORS = {
    "refstatic": [], "missing": [], "zero": [(MODE,0)], "one": [(MODE,1)], "two": [(MODE,2)],
    "olddynamic": [(DYN,1)], "oldboth": [(DYN,1),(INT,1)],
    "invalid": [(MODE,3)], "duplicate": [(MODE,1),(MODE,1)],
    "mixedflag": [(DYN,1),(MODE,1)], "mixedintegrator": [(INT,0),(MODE,0)],
    "couplingoff": [(MODE,1)], "wrongnode": [(MODE,2)], "restart": [(MODE,2)],
}
ERRORS = dict(invalid="requires 0, 1 or 2", duplicate="Duplicate HydroMechModel",
              mixedflag="cannot be combined", mixedintegrator="cannot be combined",
              couplingoff="requires HydroMech=1", wrongnode="inside special/hydromechanics",
              restart="requires a fresh start")
VALID_MODE = dict(refstatic=0, missing=0, zero=0, one=1, two=2, olddynamic=1, oldboth=2)


def make_seed(folder, profile, original):
    """Preserve the generated XML/BI4 pair, changing only the selector elements."""
    raw = original.with_suffix(".xml").read_bytes()
    line = re.compile(rb'(?m)^(?P<indent>[ \t]*)<HydroMechDynamicSeepage\s+value="1"[^>]*?/>[ \t]*(?P<nl>\r?\n)')
    found = list(line.finditer(raw))
    need(len(found)==1, "Expected one old dynamic selector")
    match, = found
    selectors = b"".join(match["indent"]+f'<{name} value="{value}" />'.encode()+match["nl"]
                         for name,value in SELECTORS[profile])
    raw = raw[:match.start()] + (b"" if profile=="wrongnode" else selectors) + raw[match.end():]
    if profile=="wrongnode":
        tag = b"            </soils>"
        need(raw.count(tag)==1, "Expected one soils element")
        raw = raw.replace(tag,selectors+tag)
    if profile=="couplingoff":
        flag=b'<HydroMech value="1"'
        need(raw.count(flag)==1,"Expected one coupling switch")
        raw=raw.replace(flag,b'<HydroMech value="0"')
    folder.mkdir()
    seed = folder/original.name
    seed.with_suffix(".xml").write_bytes(raw)
    shutil.copy2(original.with_suffix(".bi4"), seed.with_suffix(".bi4"))
    return seed


def read_static(path):
    """Read the original u-pw sphere's 15 arrays; dynamic saves also contain PosDiv and six J fields."""
    from upl_tpi_partial_bi4_r1 import _Cursor, _numeric, _values
    data=path.read_bytes()
    need(data[:58].rstrip(b" ")==b"#FileJBD JPartDataBi4" and data[58:64]==b"\n\0\0\0\0\0","Static BI4 header")
    cursor=_Cursor(data,64)
    def node(name,arrays,children):
        desc=cursor.block(cursor.uint())
        need(desc.string()=="\nITEM\n" and desc.string()==name,"Static BI4 item")
        desc.boolean();desc.boolean();desc.string();desc.string()
        need((desc.uint(),desc.uint())==(arrays,children),"Static item shape")
        values,types=_values(cursor.block(desc.uint()))
        desc.finish("Static BI4 item")
        return dict(values=values,types=types)
    root=node("JPartDataBi4",0,1)
    fields={k:t for k,t in EXPECTED_TYPES.items() if not k.startswith("Poro") and k!="PosDiv"}
    part=node(path.stem.upper(),len(fields),0)
    meta_types={"Cpart":8,"Npok":8,"Nout":8,"Step":8,**dict.fromkeys(NATIVE_CLOCK,12)}
    need(all(part["types"].get(k)==v for k,v in meta_types.items()),"Static native metadata types")
    need(part["values"]["Cpart"]==int(path.stem.split("_")[-1]),"Static PART ordinal")
    arrays,types={},{}
    for _ in fields:
        desc=cursor.block(cursor.uint())
        need(desc.string()=="\nARRAY","Static BI4 array header")
        name=desc.string()
        hidden=desc.boolean()
        type_id,count,size=desc.integer(),desc.uint(),desc.uint()
        desc.finish("Static BI4 array")
        need(name in fields and name not in arrays and count==part["values"]["Npok"]==37181,"Static array identity")
        values,info=_numeric(cursor,type_id,count)
        need(info["data_bytes"]==size and info["type_name"]==fields[name],"Static field size or type")
        info["hidden"]=hidden
        arrays[name],types[name]=values,info
    cursor.finish("Static BI4 file")
    need(root["values"]["CaseNfixed"]==8 and root["values"]["CaseNfluid"]==37173,"Static sphere population")
    return dict(root=root,part=part,arrays=arrays,types=types)


def verify_native(output, reference, model, dt):
    """Compare every native field of both real solvers in material-ID order."""
    paths=sorted((output/"data").glob("Part_*.bi4"))
    controls=sorted((reference/"data").glob("Part_*.bi4"))
    names=["Part_0000.bi4","Part_0001.bi4"]
    need([p.name for p in paths]==[p.name for p in controls]==names,"Actual two-save schedule")
    if model:
        audit(output/"data",[0,2],dt,reference/"data",exact=True)
    fields={}
    for part,(path,control) in enumerate(zip(paths,controls)):
        reader=read if model else read_static
        cur,old = reader(path),reader(control)
        meta,expected = cur["part"]["values"],old["part"]["values"]
        need((meta["TimeStep"],meta["Step"],meta["Npok"],meta["Nout"])==
             (2*dt if part else 0.,part,37181,0),"Actual time/step/count")
        for key in NATIVE_CLOCK:
            need(struct.pack("<d",meta[key])==struct.pack("<d",expected[key]),f"Clock differs: {key}")
        need(bool(meta.get(DYN,False))==bool(model),"Native model metadata")
        need(meta["dterror"]<=1e-14,"Native signed time-step error")
        fields={k:v["type_name"] for k,v in cur["types"].items()}
        need(fields=={k:v["type_name"] for k,v in old["types"].items()},"Native array type/coverage")
        if model:
            need(fields==EXPECTED_TYPES,"Dynamic particle fields")
        else:
            need("PorePress" in fields and "PoroVolumeRatio" not in fields,"Static particle fields")
        orders = [np.argsort(b["arrays"]["Idp"]) for b in (cur,old)]
        for b,order in zip((cur,old),orders):
            need(np.array_equal(b["arrays"]["Idp"][order],np.arange(37181)),"All native IDs")
        for field in fields:
            a,b = [data["arrays"][field][index] for data,index in zip((cur,old),orders)]
            need(np.all(np.isfinite(a)) and a.tobytes()==b.tobytes(),f"Part {part}: {field}")
    return fields


def run(profile):
    tag=TAG+"_"+profile
    output=OUT/tag
    valid=profile in VALID_MODE
    model=VALID_MODE.get(profile,1)
    dynamic_b=model==2 or profile=="restart"
    seed0=(legacy.prior.SEED if dynamic_b else OUT/(legacy.prior.INPUT_NAME+"_seed"))/legacy.prior.INPUT_NAME
    need(not output.exists() and not (LOG/(tag+".call.json")).exists(),"Preserve existing solver evidence")
    seed=make_seed(OUT/(tag+"_seed"),profile,seed0)
    output.mkdir()
    program=legacy.ROW_PROGRAM if profile=="refstatic" else PROGRAM
    command=[str(program),"-cpu","-ompthreads:8","-stable",str(seed),str(output),"-dirdataout","data","-svres","-nsteps:2"]
    if profile=="restart":
        real=OUT/"cryer_xml_cpu_refB_r1/data"
        need((real/"Part_0001.bi4").is_file(),"Missing genuine restart PART")
        command.extend(["-partbegin:1",str(real)])
    env={k:v for k,v in os.environ.items() if not k.upper().startswith("UPL_TPI")}
    try:
        invoke(tag,command,output,env)
    except RuntimeError:
        if valid:
            raise
    call=load(LOG/(tag+".call.json"))
    code=call["actual_Popen_wait_exit"]
    need(code==call["actual_Win32_exit"],"Solver exit observations differ")
    console=(LOG/(tag+".log")).read_text(encoding="utf-8-sig",errors="replace")
    if not valid:
        msg=next((line for line in console.splitlines() if ERRORS[profile] in line),"")
        need(code==1 and msg and not any((output/"data").glob("Part_*.bi4")),"Expected failure before first PART")
        return dict(profile=profile,exit=code,rejection=msg.strip(),saved=0)
    need(code==0,"Actual solver exit")
    if profile!="refstatic":
        need(f"HydroMechModel={model}" in console,"Selected model log")
    with (output/"Run.csv").open(encoding="utf-8-sig",newline="") as stream:
        row,=csv.DictReader(stream,delimiter=";")
    need(tuple(int(row[key]) for key in ("Steps","PartFiles","PartsOut","Np","Nfixed"))==(2,2,0,37181,8),
         "Solver summary")
    if profile=="refstatic":
        return dict(profile=profile,reference_program=stat(program),exit=code,saved=2)
    reference=OUT/({0:TAG+"_refstatic",1:"cryer_xml_cpu_refA_r1",2:"cryer_xml_cpu_refB_r1"}[model])
    fields=verify_native(output,reference,model,2.**(-19 if dynamic_b else -20))
    sidecars=[]
    if dynamic_b:
        for name in ("UplTpiP3CpuR1.csv","UplTpiP3CpuR1.summary.json","UplTpiP3DtR1.csv","UplTpiP3DtR1.summary.json"):
            need(filecmp.cmp(output/name,reference/name,shallow=False),"Pressure or step ledger differs: "+name)
            sidecars.append(name)
        stats=load(output/"UplTpiP3CpuR1.summary.json")
        need((stats["commits"],stats["endpoint_calls"],stats["endpoint_writes"])==(2,6,6),"Three pressure rounds per update")
    else:
        need(not list(output.glob("UplTpi*")),"Explicit branch entered TPI")
    return dict(profile=profile,model=model,exit=code,saved=2,steps=2,ids=37181,excluded=0,
                reference=str(reference),field_types_exact=fields,clock_fields_bit_exact=NATIVE_CLOCK,
                exact_pressure_and_dt_ledgers=sidecars)


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action",choices=["build","suite",*SELECTORS])
    action=cli.parse_args().action
    if action=="build":
        legacy.SOURCE,legacy.BUILD,legacy.PROGRAM=OUT/(TAG+"_source"),TAG+"_DebugCPU",PROGRAM
        legacy.build()
    else:
        for profile in (SELECTORS if action=="suite" else [action]):
            receipt=LOG/(TAG+"_"+profile+".check.json")
            if receipt.is_file():
                need(load(receipt)["passed"],"Saved check failed")
                continue
            record=run(profile)
            write_new(receipt,dict(passed=True,**record))
            print(profile,record["exit"],flush=True)
