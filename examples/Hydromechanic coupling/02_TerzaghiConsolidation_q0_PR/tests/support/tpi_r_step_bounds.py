"""Probe the actual hydraulic and mechanical bounds on the same C02 initial state."""
import argparse
import json
import math
from pathlib import Path
import re
import shutil
import subprocess

from c02_tpi_cost_r1 import CASE, PLAN, TESTS, setup_xml


def probe(exe, backend, root, name, dt, factor, resume):
    folder=root/name
    seed=folder/"seed"
    stem=PLAN["seed_name"]
    tree,_,_=setup_xml("tpi100")
    tree.find("execution/special/hydromechanics/HydroMechTpiR").set("value",str(factor))
    for key in ("DtIni","DtFixed"):
        tree.find(f"execution/parameters/parameter[@key='{key}']").set("value",str(dt))
    if name=="wave":
        tree.find("execution/parameters/parameter[@key='SoilHourglassXi']").set("value","0")
    result=folder/"result"
    argv=[str(exe),*(["-cpu","-ompthreads:1"] if backend=="cpu" else ["-gpu"]),"-stable","-mdbc_freeslip",
          str(seed/stem),str(result),"-dirdataout","data","-svres","-nsteps:1"]
    if folder.exists():
        assert resume
        old=json.loads((folder/"exit.json").read_text())
        assert old["argv"]==argv and old["dt_s"]==dt and old["R"]==factor
        rc=old["exit"]
    else:
        seed.mkdir(parents=True)
        for ext in (".bi4", "_Normals.nbi4"):
            shutil.copyfile(TESTS/PLAN["seed_directory"]/(stem+ext),seed/(stem+ext))
        tree.write(seed/(stem+".xml"),encoding="utf-8",xml_declaration=True)
        with (folder/"console.log").open("xb") as log:
            rc=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,cwd=CASE).returncode
    text=(folder/"console.log").read_text(errors="replace")
    record=dict(exit=rc,argv=argv,dt_s=dt,R=factor,parts=len(list((result/"data").glob("Part_*.bi4"))))
    # Read the actual substage diagnostics before attributing a rejected step.
    match=re.search(r"(?:Dynamic|GPU porosity) current step or DtMin exceeds its necessary bound:[^\r\n]+",text)
    if match:
        record["reason"]=match[0]
        record["bounds"]={k:float(v) for k,v in re.findall(r"(current|bound|force|wave_visc|pore|k_gradient)=([\d.eE+\-]+)",match[0])}
    if "HG dt exceeds 0.2 frozen stiffness time scale." in text:
        record["reason"]="HG dt exceeds 0.2 frozen stiffness time scale."
    if not (folder/"exit.json").exists():
        (folder/"exit.json").write_text(json.dumps(record,indent=2))
    if name=="admitted":
        assert rc==0 and record["parts"]==2 and "Finished execution (code=0)" in text,record
    elif name=="mechanical":
        assert rc==1 and record["parts"]==1 and record["reason"]=="HG dt exceeds 0.2 frozen stiffness time scale.",record
    else:
        assert rc==1 and record["parts"]<=1 and match,record
        b=record["bounds"]
        assert b["current"]>b["bound"] and b["current"]==dt,record
        expected=b["pore"] if name=="hydraulic" else min(b["force"],b["wave_visc"])
        assert b["bound"]==expected and (name=="hydraulic" or b["pore"]>b["bound"]),record
    return record


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("exe",type=Path)
    p.add_argument("backend",choices=("cpu","gpu"))
    p.add_argument("tag")
    p.add_argument("--resume",action="store_true",help="Review retained probe exits and run only missing probes.")
    args=p.parse_args()
    assert args.tag.isidentifier()
    exe=args.exe.resolve(strict=True)
    root=TESTS/"outputs"/args.tag
    root.mkdir(exist_ok=args.resume)
    records={n:probe(exe,args.backend,root,n,d,r,args.resume) for n,d,r in (
        ("hydraulic",1e-5,1.),("admitted",1e-5,2.25),("mechanical",1e-3,512.),("wave",1e-3,512.))}
    raw=records["hydraulic"]["bounds"]["pore"]
    assert math.isclose(records["wave"]["bounds"]["pore"],512*raw,rel_tol=1e-8)
    with (TESTS/"logs"/(args.tag+".check.json")).open("x") as f:
        json.dump(dict(passed=True,initial_required_R=1e-5/raw,records=records),f,indent=2)
