"""Regression of the optional TPI hydraulic factor against sealed public-program results."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np

TESTS=Path(__file__).resolve().parents[1]
CASES=TESTS.parents[1]
SPHERE=CASES/"04_CryerProblem_PR/tests"
sys.path.insert(0,str(SPHERE/"support"))
from public_tpi_regression import read_with_history


def check(ok,message):
    if not ok:raise ValueError(message)


def check_factor_record(log, mode):
    values=re.findall(r"^\s*HydroMechTpiR=(\S+)\s*$",log,re.M)
    check(values==(["1"] if mode==2 else []),"Effective factor record")


def compare(before,after,mode):
    original=sorted((before/"data").glob("Part_*.bi4"))
    simulated=sorted((after/"data").glob("Part_*.bi4"))
    check(original and [p.name for p in original]==[p.name for p in simulated],"Complete saved time set")
    checked=history_count=0
    for old,new in zip(original,simulated):
        root,meta,a,h=read_with_history(old)
        root2,m,b,h2=read_with_history(new)
        for k in ("Step","Cpart","TimeStep","SymplecticDtPre","dterror"):
            check(np.asarray(meta[k]).tobytes()==np.asarray(m[k]).tobytes(),"Actual clock "+k)
        check(m["Nout"]==0 and m["Npok"]==meta["Npok"],"Particle count")
        ia=np.argsort(a["Idp"]);ib=np.argsort(b["Idp"])
        check(a.keys()==b.keys(),"Native schema")
        for name,v in a.items():
            check(v.dtype==b[name].dtype and v[ia].tobytes()==b[name][ib].tobytes(),f"{new}: changed {name}")
            checked+=1
        check(("HydroMechTpiR" not in m) and ("HydroMechTpiR" not in root2),"Default schema changed")
        check((h is None)==(h2 is None),"History existence")
        if h is not None:
            check(mode==2 and h["values"]["RunCode"]==root["RunCode"] and h2["values"]["RunCode"]==root2["RunCode"],"History run identity")
            for field,x in h["values"].items():
                if field!="RunCode":check(x==h2["values"][field],"History "+field)
            i1=np.argsort(h["arrays"]["Idp"]);i2=np.argsort(h2["arrays"]["Idp"])
            for field,x in h["arrays"].items():
                check(x[i1].tobytes()==h2["arrays"][field][i2].tobytes(),"History array "+field)
            history_count+=len(i1)
    return dict(frames=len(original),native_fields_per_frame=len(a),exact_field_checks=checked,history_owner_checks=history_count)


def test(exe,backend,tag,resume):
    runroot=TESTS/"outputs"/tag
    runroot.mkdir(exist_ok=resume)
    exe_id={"path":str(exe),"size":exe.stat().st_size,"mtime_ns":exe.stat().st_mtime_ns}
    identity=runroot/"program.json"
    if resume:
        check(identity.is_file() and json.loads(identity.read_text())==exe_id,"Resume requires the same recorded executable")
    else:
        with identity.open("x") as f:json.dump(exe_id,f,indent=2)
    archive=[
        (0,TESTS/f"outputs/public_tpi_upw_{backend}_final1"),
        (1,SPHERE/f"outputs/public_tpi_upl_{backend}_final1"),
        (2,SPHERE/f"outputs/public_tpi_sphere4hist_{backend}_hist1"),
        (2,TESTS/("outputs/public_tpi_column25_cpu_hist1" if backend=="cpu" else "outputs/public_tpi_column_gpu_hist1"))]
    results=[]
    for index,(mode,old) in enumerate(archive):
        oldrun=json.loads((old/"review.json").read_text())
        check(oldrun["exit"]==0,"Invalid original solver exit")
        if not oldrun["passed"]:
            # The public C02 archive also has a separate accepted density audit against
            # its earlier private solver. Below we compare directly with that public
            # archive, requiring all 22 fields, including Rhop, to match.
            check(mode==2 and old.parent.parent==TESTS and (old/"density_audit.json").is_file(),"Original regression failed")
            density=json.loads((old/"density_audit.json").read_text())
            check(density["passed"] and all(r["density_formula_exact_current_float_and_both_double"] and
                  r["other_raw_fields_and_clock_exact"] and r["all_fixed_Rhop_exact"] for r in density["frames"]),"Original C02 density audit")
        seed=old/"seed"
        xml,=seed.glob("*.xml")
        for suffix,value in ([("default",None),("explicit1","1")] if mode==2 else [("default",None)]):
            name=f"{index}_{suffix}"
            dest=runroot/name
            newseed=dest/"seed"
            newxml=newseed/xml.name
            argv=oldrun["args"].copy()
            argv[0]=str(exe)
            argv[argv.index(str(xml.with_suffix("")))]=str(newxml.with_suffix(""))
            result=dest/"result";argv[argv.index(str(old/"result"))]=str(result)
            if dest.exists():
                check(resume and json.loads((dest/"call.json").read_text())==dict(args=argv,exit=0) and
                      (dest/"result/Run.csv").is_file() and
                      "Finished execution (code=0)" in (dest/"console.log").read_text(errors="replace"),"Incomplete prior program output")
                check_factor_record((result/"Run.out").read_text(errors="replace"),mode)
                oldxml,=(dest/"seed").glob("*.xml")
                el=ET.parse(oldxml).find("execution/special/hydromechanics/HydroMechTpiR")
                check((el.get("value") if el is not None else None)==value,"Different factor in prior output")
                results.append(dict(profile=old.name,setting=suffix,adopted_existing=True,**compare(old/"result",dest/"result",mode)))
                continue
            dest.mkdir()
            shutil.copytree(seed,newseed)
            if value is not None:
                tree=ET.parse(newxml); hydro=tree.find("execution/special/hydromechanics")
                ET.SubElement(hydro,"HydroMechTpiR",value=value)
                tree.write(newxml,encoding="utf-8",xml_declaration=True)
            with (dest/"console.log").open("xb") as out:
                rc=subprocess.run(argv,cwd=dest,stdout=out,stderr=subprocess.STDOUT).returncode
            (dest/"call.json").write_text(json.dumps(dict(args=argv,exit=rc),indent=2))
            check(rc==0,"Exit "+str(rc)+" "+name)
            text=(result/"Run.out").read_text(errors="replace")
            check_factor_record(text,mode)
            results.append(dict(profile=old.name,setting=suffix,**compare(old/"result",result,mode)))
    # A bad input must be rejected before any simulation state is saved.
    for key,mode_id,value,expected in [("old_mode",1,"1","requires HydroMechModel=2"),
         ("low",2,"0.5","must be finite and at least 1"),("overflow",2,"1e309","must be finite and at least 1"),
         ("text",2,"oops","valid real number")]:
        mode,old=archive[1 if mode_id==1 else 2]
        folder=runroot/("invalid_"+key)
        existing=folder.exists()
        if not existing:
            folder.mkdir()
            shutil.copytree(old/"seed",folder/"seed")
        orig,=(old/"seed").glob("*.xml")
        new=folder/"seed"/orig.name
        if not existing:
            tree=ET.parse(new); hydro=tree.find("execution/special/hydromechanics")
            ET.SubElement(hydro,"HydroMechTpiR",value=value);tree.write(new,encoding="utf-8")
        args=json.loads((old/"review.json").read_text())["args"]
        args[0]=str(exe);args[args.index(str(orig.with_suffix("")))]=str(new.with_suffix(""))
        out=folder/"result";args[args.index(str(old/"result"))]=str(out)
        log=folder/"console.log"
        if existing:
            check(resume and json.loads((folder/"call.json").read_text())==dict(args=args,exit=1),"Incomplete rejection receipt")
            check(ET.parse(new).find("execution/special/hydromechanics/HydroMechTpiR").get("value")==value,"Wrong rejected input")
            rc=1
        else:
            with log.open("xb") as stream:rc=subprocess.run(args,cwd=folder,stdout=stream,stderr=subprocess.STDOUT).returncode
            (folder/"call.json").write_text(json.dumps(dict(args=args,exit=rc),indent=2))
        logtext=log.read_text(errors="replace")
        check(rc==1 and expected in logtext and not list((out/"data").glob("Part_*.bi4")),f"Invalid-input handling: {key}")
        results.append(dict(profile=key,rejected=True,diagnostic=expected))
    target=TESTS/"logs"/(tag+".check.json")
    with target.open("x") as f:json.dump(dict(passed=True,backend=backend,executable=str(exe),tests=results),f,indent=2)
    print(target)

if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("exe",type=Path);ap.add_argument("backend",choices=("cpu","gpu"));ap.add_argument("tag")
    ap.add_argument("--resume",action="store_true")
    args=ap.parse_args();check(args.tag.isidentifier(),"Invalid output label")
    test(args.exe.resolve(strict=True),args.backend,args.tag,args.resume)

