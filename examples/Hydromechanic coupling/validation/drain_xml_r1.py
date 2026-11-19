"""Run bounded solver regressions for the public drainage XML and compare native states.

Run old/new and preload_old/preload_new in order on the corresponding archived/new
backend, and negative on the new CPU. The six retained controls already have a seed
and native results. For retro_new, generate the current CaseRetroSlope_u_pw_prestress_Def
with GenCase into C03 tests/outputs/drain_xml_r1_retro_seed/CaseRetroSlope_u_pw_prestress.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np

from hydro_public_xml_r1 import BIN, CASES, HYDRO, case_dir, need, read_part, tag_value, write
from upl_tpi_partial_bi4_r1 import read as read_dynamic_part

TAG = "drain_xml_r1"
KEYS = ("HydroMechDrainage", "HydroMechDrainageStartTime", "HydroMechDrainageFixedGrid",
        "HydroMechFreeSeepage")
EVENTS = ("event_time", "event_fixed")
C08 = ("c08_off", "c08_free")
SUPPLEMENT = EVENTS + C08
NEGATIVE = {
    **{f"old_{i}": (None, key) for i, key in enumerate(KEYS)},
    "mixed": ('<drainage mode="off"/>', KEYS[0]),
    "retired_soils": (None, KEYS[3]),
    "alias_soils": (None, "HydroMechFreeSurfaceDrainage"),
    "alias_hydro": (None, "HydroMechFreeSurfaceDrainageStartTime"),
    "typo": ('<drainage mode="draind"/>', "drainage"),
    "bad_clock": ('<drainage mode="drained" clock="step"/>', "clock"),
    "off_start": ('<drainage mode="off" start="0"/>', "start"),
    "free_clock": ('<drainage mode="freeSeepage" clock="time"/>', "clock"),
    "negative": ('<drainage mode="drained" start="-1"/>', "start"),
    "not_number": ('<drainage mode="drained" start="NaN"/>', "start"),
    "bad_attr": ('<drainage mode="drained" clok="time"/>', "clok"),
    "off_grid": ('<drainage mode="drained" start="0.000004" clock="fixedStep"/>', "grid"),
    "duplicate": ('<drainage mode="off"/><drainage mode="off"/>', "drainage"),
    "wrong_hydro": ('<drainage mode="off"/>', "drainage"),
    "wrong_soils": ('<drainage mode="off"/>', "drainage"),
    "static_free": ('<drainage mode="freeSeepage"/>', "free"),
}


def baseline(profile, backend):
    if profile=="retro":
        root=case_dir("03")
        return root,None,root/"CaseRetroSlope_u_pw_prestress_out"
    if profile in (*C08,"preload"):
        root = case_dir("08")
        seed = root/"tests/outputs"/("upl_preload_handoff_source_GPU_r1_seed" if profile=="preload"
                                     else "upl_c08_free_seepage_start_r1_seed")
        return root, None, seed
    case = "band" if profile in EVENTS or profile in NEGATIVE else profile
    root = case_dir(CASES[case][0])
    reference = root/"tests/outputs"/f"hydro_public_single_r1_{backend}_{case}_modern"
    return root, reference, reference/"seed"


def remove(raw, key):
    return re.sub(rb"<"+key.encode()+rb'\s+value="[^"]*"[^\r\n]*?/>', b"", raw)


def insert(raw, parent, body, sibling=False):
    closing = ("</"+parent+">").encode()
    need(raw.count(closing)==1, "Expected one "+parent)
    extra=b"\n"+body.encode()+b"\n"
    return raw.replace(closing, closing+extra if sibling else extra+closing)


def prepare(profile, seed, directory, old):
    source, = seed.glob("*.xml")
    raw=source.read_bytes()
    dt=float(re.search(rb'<parameter key="DtFixed" value="([^"]+)"',raw)[1])
    values=[tag_value(raw,key,default) for key,default in zip(KEYS,("1","0","0","0"))]
    steps=6
    if profile in (*C08,"preload"):
        # This generated geometry predates the model/load public schema.
        raw=remove(raw.replace(b"HydroMechDynamicSeepage",b"HydroMechModel"),"HydroMechTopLoadMode")
        values=["0","0","0","0" if profile=="c08_off" else "1"]
        steps=64
        if profile=="preload":
            # A fresh two-stage fixture; no previous statefile or accepted 10 s data are touched.
            raw=raw.replace(b'<gravitypreload time="0.00095"',b'<gravitypreload time="0.00002"')
            need(b'<gravitypreload time="0.00002"' in raw and dt==2.5e-6,"Unexpected gravity seed")
            raw=re.sub(rb'(<parameter key="TimeOut" value=")[^"]*',rb'\g<1>0.0000049995',raw)
            steps=12
    elif profile in EVENTS:
        values=["1",str(6*dt),"1" if profile=="event_fixed" else "0","0"]
        # Just below dt guarantees a save at the sixth cumulative step, one ULP below 6*dt.
        raw=re.sub(rb'(<parameter key="TimeOut" value=")[^"]*',lambda m:m[1]+str(dt*.9999).encode(),raw)
        steps=8
    if profile=="retro":
        need((b"HydroMechFreeSurfaceDrainage" if old else b'<drainage mode="drained"') in raw,
             "Retrogressive source does not have expected drainage schema")
        raw=re.sub(rb'(<parameter key="TimeOut" value=")[^"]*',rb'\g<1>0.000002',raw)
    for key in KEYS:
        raw=remove(raw,key)
    if old and profile!="retro":
        raw=insert(raw,"hydromechanics","".join(f'<{key} value="{v}"/>' for key,v in zip(KEYS,values)))
    elif profile in NEGATIVE:
        body, _=NEGATIVE[profile]
        if profile.startswith("old_") or profile in ("mixed","retired_soils"):
            key=KEYS[int(profile[-1])] if profile.startswith("old_") else KEYS[3 if profile=="retired_soils" else 0]
            raw=insert(raw,"soils" if profile=="retired_soils" else "hydromechanics",f'<{key} value="0"/>')
        if profile in ("alias_soils","alias_hydro"):
            raw=insert(raw,"soils" if profile=="alias_soils" else "hydromechanics",
                       f'<{NEGATIVE[profile][1]} value="1"/>')
        if body:
            parent={"wrong_hydro":"hydromechanics","wrong_soils":"soils"}.get(profile)
            raw=insert(raw,parent or "hydromechanics",body,sibling=not parent)
    elif profile not in ("unloaded","retro"):
        if values[0]=="0":
            mode="freeSeepage" if values[3]=="1" else "off"
            body=f'<drainage mode="{mode}"/>'
        else:
            clock="fixedStep" if values[2]=="1" else "time"
            body=f'<drainage mode="drained" start="{values[1]}" clock="{clock}"/>'
        raw=insert(raw,"hydromechanics",body,sibling=True)
    directory.mkdir(parents=True)
    for item in (source.with_suffix(".bi4"),source.with_name(source.stem+"_Normals.nbi4")):
        if item.exists():
            shutil.copy2(item,directory/item.name)
    (directory/source.name).write_bytes(raw)
    return directory/source.stem,steps


def execute(folder, profile, phase, backend, exe, seed):
    receipt=folder/"exit.json"
    if receipt.exists():
        seen=json.loads(receipt.read_text(encoding="utf-8"))
        need(seen["command"][0]==str(exe) and seen["phase"]==phase,"Different existing run")
        return seen
    need(not folder.exists(),"Partial run must be independently checked: "+str(folder))
    stem,steps=prepare(profile,seed,folder/"seed",phase.endswith("old"))
    cmd=[str(exe),"-"+backend]
    if backend=="cpu":
        cmd.append("-ompthreads:1")
    if profile=="retro":
        cmd.append("-mdbc_noslip:nopen")
    cmd.extend(("-stable",str(stem),str(folder),"-dirdataout","data","-svres",f"-nsteps:{steps}"))
    env=os.environ.copy()
    env["PATH"]=str(BIN)+os.pathsep+env["PATH"]
    with (folder/"console.log").open("xb") as stream:
        result=subprocess.run(cmd,cwd=BIN,env=env,stdout=stream,stderr=subprocess.STDOUT)
    summary=dict(command=cmd,phase=phase,exit=result.returncode,steps=steps,
                 exe_bytes=exe.stat().st_size,exe_mtime_ns=exe.stat().st_mtime_ns)
    write(receipt,summary)
    return summary


def compare(folder, reference, profile, steps):
    paths=sorted((folder/"data").glob("Part_*.bi4"))
    need([p.name for p in paths]==sorted(p.name for p in (reference/"data").glob("Part_*.bi4"))
         and len(paths)>=3,"Different schedules or no completed short trajectory")
    rows=[]
    for path in paths:
        source=reference/"data"/path.name
        if profile=="preload":
            data,previous=(read_dynamic_part(p) for p in (path,source))
            root,meta,fields=data["root"]["values"],data["part"]["values"],data["arrays"]
            old,base=previous["part"]["values"],previous["arrays"]
            upd=int(meta["Step"])+1 if meta["TimeStep"] else 0
            phase=int(upd>8)
            need(meta["GravityPreloadPhase"]==old["GravityPreloadPhase"]==phase and
                 meta["GravityPreloadEventCompletedStep"]==old["GravityPreloadEventCompletedStep"]==8 and
                 (not phase or meta["GravityPreloadActualCompletedStep"]==8),"Wrong release step")
            expected=np.arange(7060)
            if phase:
                expected=expected[(expected<1800)|(expected>=2060)]
            need(meta["Nout"]==0 and np.array_equal(np.sort(fields["Idp"]),expected) and
                 all(np.isfinite(a).all() for a in fields.values()),"Wrong released IDs or non-finite field")
        else:
            root,meta,fields=read_part(path)
            _,old,base=read_part(source)
        need(fields.keys()==base.keys(),"Native schema changed")
        for name in ("Cpart","Step","TimeStep","SymplecticDtPre","dterror","HydroMechFreeSeepage"):
            if name=="HydroMechFreeSeepage" and name not in old:
                need(name not in meta,"Unexpected free seepage")
                continue
            need(np.asarray(meta[name]).tobytes()==np.asarray(old[name]).tobytes(),path.name+" "+name)
        ix,iy=(np.argsort(data["Idp"]) for data in (fields,base))
        for name,a in fields.items():
            b=base[name]
            need(a.shape==b.shape and a.dtype==b.dtype and a[ix].tobytes()==b[iy].tobytes(),path.name+" "+name)
        soil=fields["Idp"]>=root["CaseNfixed"]
        pos=fields.get("Posd",fields.get("Pos"))
        mask=soil & np.isin(fields["FSType"],(2,3))
        if profile in ("lian","yao"):
            mask &= np.abs(pos[:,0])>(1.25 if profile=="lian" else 3.)
        p=fields["PorePress"][mask]
        step=int(meta["Step"])+1 if meta["TimeStep"] else 0
        rows.append(dict(step=step,t_s=float(meta["TimeStep"]),ids=len(soil),arrays=len(fields),
                         receivers=len(p),pmin_Pa=float(p.min()) if len(p) else None,
                         pmax_Pa=float(p.max()) if len(p) else None))
        if profile=="preload":
            rows[-1]["gravity_phase"]=phase
            need(len(p)>0 and (not phase or np.all(p<=0)),"Missing released positive pressure projection")
        if profile in CASES:
            if step>(0 if profile=="unloaded" else 3):
                need(len(p)>0 and np.all(p==0),profile+" active drained receivers")
        elif profile in C08:
            need(len(p)>0 and bool(meta.get("HydroMechFreeSeepage",False))==(profile=="c08_free"),"C08 mode")
            if profile=="c08_free":
                need(np.all(p<=0),"Positive free-surface pressure in completed state")
    need(rows[-1]["step"]==steps,"Final update count")
    if profile=="c08_free":
        need(any(row["pmin_Pa"]<0 for row in rows),"Expected a genuinely negative retained surface pressure")
    if profile in EVENTS:
        need([row["step"] for row in rows]==list(range(9)),"Incomplete source-clock event window")
        need(rows[6]["t_s"]<6*1e-5,"Missing cumulative rounding at opening")
        expect=7 if profile=="event_fixed" else 8
        for row in rows[6:]:
            bounds=(row["pmin_Pa"],row["pmax_Pa"])
            need(row["receivers"]>0 and ((bounds==(0.,0.))==(row["step"]>=expect)),"Wrong event step: "+str(row))
    return rows


def run(args,profile):
    root,retained,seed=baseline(profile,args.backend)
    parent=root/"tests/outputs"
    prefix=f"{TAG}_{args.backend}_{profile}"
    folder=parent/(prefix+"_"+args.phase)
    if profile=="retro" and args.phase=="retro_new":
        seed=parent/(TAG+"_retro_seed")  # Independent GenCase output from migrated root input.
    receipt=execute(folder,profile,args.phase,args.backend,args.program,seed)
    if profile in NEGATIVE:
        diag=re.search(r"(?m)^Text: (.+)$",(folder/"console.log").read_text(errors="replace"))
        need(receipt["exit"]!=0 and diag and NEGATIVE[profile][1].lower() in diag[1].lower()
             and not any((folder/"data").glob("Part_*.bi4")),f"{profile} wrong rejection: {diag}")
        return dict(profile=profile,exit=receipt["exit"],diagnostic=diag[1])
    need(receipt["exit"]==0,"Solver failed: "+str(folder/"console.log"))
    with (folder/"Run.csv").open(encoding="utf-8-sig",newline="") as stream:
        row,=csv.DictReader(stream,delimiter=";")
    need(int(row["Steps"])==receipt["steps"] and int(row["PartsOut"])==0,"Incomplete run or exclusions")
    if args.phase.endswith("old"):
        return dict(profile=profile,exit=0,steps=receipt["steps"])
    reference=parent/(prefix+"_old") if profile in SUPPLEMENT else retained
    if profile=="preload":
        reference=parent/(prefix+"_preload_old")
    if profile=="retro":
        reference=parent/(prefix+"_retro_old")
    return dict(profile=profile,reference=reference.name,frames=compare(folder,reference,profile,receipt["steps"]))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=["old","new","negative","preload_old","preload_new","retro_old","retro_new"])
    parser.add_argument("backend",choices=["cpu","gpu"])
    parser.add_argument("program",type=Path)
    args=parser.parse_args()
    args.program=args.program.resolve(strict=True)
    profiles={"old":SUPPLEMENT,"new":(*CASES,*SUPPLEMENT),"negative":NEGATIVE,
              "preload_old":("preload",),"preload_new":("preload",),"retro_old":("retro",),"retro_new":("retro",)}[args.phase]
    reviews=[]
    for entry in profiles:
        reviews.append(run(args,entry))
        print(args.backend,args.phase,entry,"passed",flush=True)
    output=HYDRO/"validation"/f"{TAG}_{args.backend}_{args.phase}.json"
    write(output,dict(backend=args.backend,phase=args.phase,checks=reviews))
