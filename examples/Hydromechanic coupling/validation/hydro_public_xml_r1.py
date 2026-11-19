"""Compare the previous and current public XML readers on real, bounded CPU/GPU runs."""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import numpy as np

HYDRO = Path(__file__).resolve().parent.parent
BIN = HYDRO.parents[1] / "bin/windows"
TAG = "hydro_public_xml_r1"
sys.path.insert(0, str(HYDRO/"02_TerzaghiConsolidation_q0_PR/tests/support"))
from upl_tpi_partial_bi4_r1 import _Cursor, _numeric, _values

# Generated case name, directory relative to the case root and expected load mode.
CASES = {
    "unloaded": ("01", "CaseSelfWeightConsolidation_Scenario2_FreshPR_out", 0),
    "vertical": ("02", "CaseTerzaghiConsolidation_q0_PR_full_k1em4_out", 1),
    "band": ("02", "tests/outputs/hg_release_continue_r2_spr15_c_input", 5),
    "confinement": ("04", "tests/outputs/upl_cryer_freebody_short_r1_seed", 2),
    "lian": ("05", "CaseLianFlexibleStrip2D_PR_release_out", 4),
    "yao": ("06", "tests/outputs/spr_yao_grid10_r1_faces_off_input", 3),
}
KEYS = ["HydroMechTopLoadMode","HydroMechTopLoadQ0","HydroMechTopLoadRampTime"]
RETIRED_LOAD = dict(zip(("retired_mode","retired_q0","retired_ramptime"),KEYS))
STEPS = 6


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def case_dir(code):
    folder, = HYDRO.glob(code+"_*")
    return folder


def input_case(case):
    if case=="dry":
        root=HYDRO.parent/"Elastoplastic_basic/10_StaticDrySoilColumn"
        return root,root/"CaseStaticDrySoilColumn2D_Feng2021_dp002_CPU_out",0
    code,seedpath,mode=CASES[case]
    root=case_dir(code)
    return root,root/seedpath,mode


def write(path, obj):
    with path.open("x", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)


def tag_value(raw, name, default=None):
    match = re.search(rb"<"+name.encode()+rb'\s+value="([^"]*)"',raw)
    return match[1].decode() if match else default


def prepared(case, group, parent):
    _, seed_dir, mode = input_case(case)
    seed, = [p for p in seed_dir.glob("*.xml") if p.with_suffix(".bi4").is_file()]
    folder = parent/"seed"
    folder.mkdir(parents=True)
    for p in (seed.with_suffix(".bi4"),seed.with_name(seed.stem+"_Normals.nbi4")):
        if p.exists():
            shutil.copy2(p,folder/p.name)
    raw = seed.read_bytes()
    if case=="dry":
        need(b"<hydromechanics" not in raw and b"<externalload" not in raw,"Expected dry unmodified source")
        (folder/seed.name).write_bytes(raw)
        return folder/seed.stem,None
    dt = float(re.search(rb'<parameter key="DtFixed" value="([^"]+)"',raw)[1])
    # Exercise ramp, full force and opening within six updates on both sides.
    for key, value in ((KEYS[2], 2*dt), ("HydroMechDrainageStartTime", 3*dt)):
        if mode:
            raw = re.sub(rb'(<'+key.encode()+rb'\s+value=")[^"]*(")', lambda m: m[1]+str(value).encode()+m[2], raw)
    raw = re.sub(rb'(<parameter key="TimeOut" value=")[^"]*(")',lambda m:m[1]+str(2*dt).encode()+m[2],raw)
    # Old inputs can contain literal '<' in a comment attribute understood by TinyXML.
    # Preserve those bytes, special load regions, and every other input parameter.
    values = [tag_value(raw,key,default) for key,default in zip(KEYS,("0","0","0"))]
    if group not in ("old","legacy"):
        for key in [*KEYS,"HydroMechDynamicSeepage"]:
            if key==RETIRED_LOAD.get(group) or (key==KEYS[0] and group=="mixedload"):
                continue
            raw = re.sub(rb'(?m)^\s*<'+key.encode()+rb'\s+value="[^"]*"[^\r\n]*?/>',b"",raw)
        model = "2" if group=="tpi" else ("1" if case=="confinement" else "0")
        if group=="bad_model":
            model="3"
        option = f'<HydroMechModel value="{model}"/>'
        if group=="default_model":
            option=""
        if group in ("retired_dynamic","retired_dynamic0"):
            option=f'<HydroMechDynamicSeepage value="{int(group=="retired_dynamic")}"/>'
        if group=="retired_integrator":
            option='<HydroMechPressureIntegrator value="1"/>'
        if group=="mixedmodel":
            option += '<HydroMechDynamicSeepage value="0"/>'
        load = f'<externalload mode="{values[0]}" q0="{values[1]}" ramptime="{values[2]}"/>'
        if group in RETIRED_LOAD or (group=="default_model" and not mode):
            load=""
        if group in ("negative_q0","negative_ramp"):
            attribute="q0" if group=="negative_q0" else "ramptime"
            load=re.sub(attribute+r'="[^"]+"',attribute+'="-1"',load)
        if group=="badattribute":
            load = load.replace("ramptime=","ramptim=")
        if group=="duplicate":
            load += load
        if group=="hydrooff":
            raw=raw.replace(b'<HydroMech value="1"', b'<HydroMech value="0"')
        if group=="duplicate_model":
            option += option
        need(raw.count(b'</hydromechanics>')==1,"Missing canonical hydro block")
        raw=raw.replace(b'</hydromechanics>',option.encode()+b'\n            </hydromechanics>\n            '+load.encode())
    (folder/seed.name).write_bytes(raw)
    return folder/seed.stem,dt


def read_part(path):
    data=path.read_bytes()
    need(data[:58].rstrip(b" ")==b"#FileJBD JPartDataBi4" and data[58:64]==b"\n\0\0\0\0\0", "BI4 header")
    cur=_Cursor(data,64)
    def item(name,nchildren):
        desc=cur.block(cur.uint())
        need(desc.string()=="\nITEM\n" and desc.string()==name,"Wrong node")
        desc.boolean();desc.boolean();desc.string();desc.string()
        n=desc.uint()
        need(desc.uint()==nchildren,"Wrong number of child nodes")
        values,types=_values(cur.block(desc.uint()))
        desc.finish("Item")
        return n,values
    nr,root=item("JPartDataBi4",1)
    need(nr==0,"Nonempty root")
    nf,meta=item(path.stem.upper(),0)
    fields={}
    for _ in range(nf):
        desc=cur.block(cur.uint())
        need(desc.string()=="\nARRAY","Array header")
        name=desc.string()
        desc.boolean()
        type_id,count,size=desc.integer(),desc.uint(),desc.uint()
        desc.finish("Array")
        arr,info=_numeric(cur,type_id,count)
        need(name not in fields and count==meta["Npok"] and size==info["data_bytes"] and np.isfinite(arr).all(), name)
        fields[name]=arr
    cur.finish("File")
    need(meta["Nout"]==0 and len(fields["Idp"])==root["CaseNp"] and
         np.array_equal(np.sort(fields["Idp"]),np.arange(root["CaseNp"])), "Incomplete or duplicate native IDs")
    return root,meta,fields


def compare(folder, baseline, mode, dt):
    files=sorted((folder/"data").glob("Part_*.bi4"))
    ref=sorted((baseline/"data").glob("Part_*.bi4"))
    need(len(files)>=3 and [p.name for p in files]==[p.name for p in ref],"Saved schedule mismatch")
    rows=[]
    for path,old in zip(files,ref):
        root,meta,fields=read_part(path)
        _,prev,orig=read_part(old)
        need(fields.keys()==orig.keys() and {"Idp","PorePress","FSType","Sigma_kk","HydroMechLoadAce"}<=fields.keys(),"Native output schema")
        for key in ("Cpart","Step","TimeStep","SymplecticDtPre","dterror"):
            need(meta[key].tobytes()==prev[key].tobytes(),"Clock mismatch "+key)
        orders=[np.argsort(q["Idp"]) for q in (fields,orig)]
        for key,a in fields.items():
            z=orig[key]
            need(a.dtype==z.dtype and a.shape==z.shape and a[orders[0]].tobytes()==z[orders[1]].tobytes(),f"{path.name} differs in {key}")
        ace=fields["HydroMechLoadAce"].astype(float)
        active=np.any(ace!=0.,axis=1)
        rows.append(dict(part=int(meta["Cpart"]),time_s=float(meta["TimeStep"]),native_step=int(meta["Step"]),
                         ids=len(ace),fields=len(fields),loaded_count=int(active.sum()),
                         load_massref_sum=(ace.sum(axis=0)*float(root["MassFluid"])).tolist(),
                         load_max_m_s2=float(np.linalg.norm(ace,axis=1).max()),
                         fs23_count=int(np.isin(fields["FSType"],(2,3)).sum())))
    need(math.isclose(rows[-1]["time_s"],STEPS*dt,rel_tol=1e-12) and
         rows[-1]["native_step"]==STEPS-1, "Final update")
    need((rows[-1]["loaded_count"]>0)==bool(mode),"Final actual load")
    return rows


def surface_review(args):
    """Read the successful modern outputs and check projection after the prescribed opening."""
    checks={}
    for case in CASES:
        code,_,mode=CASES[case]
        folder=case_dir(code)/"tests/outputs"/f"{args.tag}_{args.backend}_{case}_modern"
        record=json.loads((folder/"review.json").read_text(encoding="utf-8"))
        dt=record["dt"]
        rows=[]
        for path in sorted((folder/"data").glob("Part_*.bi4")):
            root,m,a=read_part(path)
            pos=a.get("Posd",a.get("Pos"))
            soil=a["Idp"]>=root["CaseNfixed"]
            mask=soil & np.isin(a["FSType"],(2,3))
            if mode==4:
                mask &= np.abs(pos[:,0])>1.25
            elif mode==3:
                mask &= np.abs(pos[:,0])>3.
            after=float(m["TimeStep"])>(3*dt if mode else 0.)
            pmax=float(np.max(np.abs(a["PorePress"][mask]),initial=0.))
            if after:
                need(np.any(mask) and pmax==0.,"Saved active drainage mismatch "+case)
            ace=a["HydroMechLoadAce"].astype(float)
            force=ace*float(root["MassFluid"])
            row=dict(completed_step=int(m["Step"])+1 if m["TimeStep"] else 0,
                     time_s=float(m["TimeStep"]),after_open=after,receiver_count=int(mask.sum()),
                     receiver_p_absmax_Pa=pmax,loaded_count=int(np.any(ace,axis=1).sum()),
                     reference_mass_force_z=float(np.sum(force[:,2])))
            if mode==2:
                norm=np.linalg.norm(pos[soil],axis=1)
                row["reference_mass_inward_radial_N"]=float(-np.sum(np.sum(force[soil]*pos[soil],axis=1)[norm>0]/norm[norm>0]))
            rows.append(row)
        need(len(rows)>=3 and rows[-1]["after_open"],case+" lacks post-opening sample")
        checks[case]=rows
    write(HYDRO/"validation"/f"{args.tag}_{args.backend}_surface.json",
          dict(passed=True,backend=args.backend,short_source_ramp_steps=2,short_drained_open_step=3,
               load_observation="reference particle mass times saved acceleration; radial sum for Cryer",cases=checks))


def run(args,case,group):
    root,_,mode=input_case(case)
    label=f"{args.tag}_{args.backend}_{case}"
    base=root/"tests/outputs"
    folder=base/(label+"_"+group)
    closed=folder/"exit.json"
    if closed.exists():
        prior_exit=json.loads(closed.read_text(encoding="utf-8"))
        seed_xml,=(folder/"seed").glob("*.xml")
        seed=seed_xml.with_suffix("")
        dt=None if case=="dry" else float(re.search(rb'<parameter key="DtFixed" value="([^"]+)"',seed_xml.read_bytes())[1])
    else:
        need(not folder.exists(),"Unclosed outputs require separate investigation "+str(folder))
        seed,dt=prepared(case,group,folder)
    env=os.environ.copy()
    env["PATH"]=str(BIN)+os.pathsep+env["PATH"]
    exe=args.old if group=="old" else args.new
    cmd=[str(exe),"-"+args.backend,"-stable",str(seed),str(folder),"-dirdataout","data","-svres","-nsteps:"+str(STEPS)]
    if args.backend=="cpu":
        cmd.insert(2,"-ompthreads:"+str(args.cpu_threads))
    if closed.exists():
        need(prior_exit["command"]==cmd and prior_exit["case"]==case and prior_exit["profile"]==group,
             "Closed process binding differs")
        rc=prior_exit["exit"]
    else:
        with (folder/"console.log").open("xb") as console:
            result=subprocess.run(cmd,env=env,cwd=BIN,stdout=console,stderr=subprocess.STDOUT,check=False)
        rc=result.returncode
        write(closed,dict(case=case,profile=group,exit=rc,command=cmd))
    rejects={"tpi":"TPI", "mixedmodel":"cannot be combined","mixedload":"cannot be combined",
             "duplicate":"Duplicate externalload","badattribute":"ramptim","duplicate_model":"Duplicate HydroMechModel",
             "hydrooff":"requires HydroMech=1","retired_dynamic":"HydroMechDynamicSeepage",
             "retired_dynamic0":"HydroMechDynamicSeepage","retired_integrator":"HydroMechPressureIntegrator",**RETIRED_LOAD}
    if args.phase=="single":
        rejects.update(mixedmodel="HydroMechDynamicSeepage",mixedload=KEYS[0],duplicate_model="HydroMechModel",
                       duplicate="externalload",hydrooff="HydroMech",bad_model="HydroMechModel",
                       negative_q0="q0",negative_ramp="ramptime")
    evidence=dict(case=case,profile=group,exit=rc,command=cmd,dt=dt)
    if group in rejects:
        text=(folder/"console.log").read_text(errors="replace")
        diagnostic=re.search(r"(?m)^Text: (.+)$",text)
        need(rc!=0 and diagnostic and rejects[group].lower() in diagnostic[1].lower()
             and not any((folder/"data").glob("Part_*.bi4")),text[-800:])
        evidence["error"]=text[text.rfind("*** Exception"):].split("Finished execution")[0].strip()
    else:
        need(rc==0,f"Solver exit {rc}: "+(folder/"console.log").read_text(errors="replace")[-1400:])
        with (folder/"Run.csv").open(encoding="utf-8-sig",newline="") as stream:
            summary,=csv.DictReader(stream,delimiter=";")
        need(int(summary["Steps"])==STEPS and int(summary["PartsOut"])==0, "Run summary")
        evidence["steps"]=STEPS
        if case=="dry":
            states=[]
            for path in sorted((folder/"data").glob("Part_*.bi4")):
                _,meta,arrays=read_part(path)
                need({"Sigma_kk","Sigma_ij","Kplastic"}.issubset(arrays) and
                     not {"PorePress","HydroMechLoadAce","PorePress0"}.intersection(arrays),"Unexpected dry fields")
                states.append(dict(time_s=float(meta["TimeStep"]),saved_step=int(meta["Step"]),ids=len(arrays["Idp"]),
                                   fields=list(arrays)))
            need(len(states)>=2 and states[-1]["saved_step"]==STEPS-1 and states[-1]["time_s"]>0,"Dry final update")
            evidence["dry_native"]=states
        elif args.phase=="single":
            expected_model=1 if case=="confinement" else 0
            log=(folder/"Run.out").read_text(errors="replace")
            need(f"HydroMechModel={expected_model} " in log, "Wrong configured hydromechanics model")
            evidence["configured_model"]=expected_model
        if group!="old" and case!="dry":
            ref=base/f"{args.control_tag or args.tag}_{args.backend}_{case}_old"
            prior=json.loads((ref/"review.json").read_text(encoding="utf-8"))
            need(prior["case"]==case and prior["exit"]==0 and prior["steps"]==STEPS and prior["dt"]==dt,
                 "Closed original same-input baseline required")
            evidence["reference"]=str(ref)
            evidence["exact_native_pairs"]=compare(folder,ref,mode,dt)
    write(folder/"review.json",evidence)
    return evidence


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("phase",choices=["baseline","candidate","surface","single"])
    ap.add_argument("--backend",choices=["cpu","gpu"],default="cpu")
    ap.add_argument("--cases",nargs="+",choices=list(CASES),default=list(CASES))
    ap.add_argument("--tag",default=TAG,help="fresh short label for an independently built runtime")
    ap.add_argument("--control-tag",help="reuse a completed baseline from another label")
    ap.add_argument("--cpu-threads",type=int,default=1)
    ap.add_argument("--old",type=Path)
    ap.add_argument("--new",type=Path)
    args=ap.parse_args()
    need(re.fullmatch(r"[a-z][a-z0-9_]+",args.tag) and 1<=args.cpu_threads<=64,"Invalid run label or thread count")
    if args.phase=="surface":
        surface_review(args)
        sys.exit(0)
    if args.phase=="single":
        need(args.control_tag and re.fullmatch(r"[a-z][a-z0-9_]+",args.control_tag) and args.control_tag!=args.tag,
             "Single-schema verification uses a different retained baseline")
    program = args.old if args.phase=="baseline" else args.new
    need(program is not None and program.is_file(),"Existing original or rebuilt matching executable required")
    program=program.resolve()
    if args.phase=="baseline": args.old=program
    else: args.new=program
    groups={"baseline":["old"],"candidate":["modern","legacy"],"single":["modern"]}
    pairs=[(case,grp) for case in args.cases for grp in groups[args.phase]]
    if args.phase=="single" and "unloaded" in args.cases:
        pairs.append(("unloaded","default_model"))
        pairs.append(("dry","no_hydro_block"))
    if args.phase in ("candidate","single") and "lian" in args.cases:
        pairs.extend(("lian",grp) for grp in ("tpi","mixedmodel","mixedload","duplicate","badattribute","duplicate_model","hydrooff"))
        if args.phase=="single":
            pairs.extend(("lian",grp) for grp in ("retired_dynamic","retired_dynamic0","retired_integrator",
                                                  *RETIRED_LOAD,"bad_model","negative_q0","negative_ramp"))
    records=[]
    for case,group in pairs:
        p=input_case(case)[0]/"tests/outputs"/f"{args.tag}_{args.backend}_{case}_{group}"/"review.json"
        existing=json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
        if existing:
            need(existing["command"][0]==str(program) and existing["case"]==case and existing["profile"]==group, "Saved receipt differs")
            if args.backend=="cpu":
                need(("-ompthreads:"+str(args.cpu_threads)) in existing["command"],"Saved OpenMP settings differ")
        records.append(existing or run(args,case,group))
        print(case,group,"passed",flush=True)
    if set(args.cases)!=set(CASES):
        sys.exit(0)
    write(HYDRO/"validation"/f"{args.tag}_{args.backend}_{args.phase}.json",dict(passed=True,
          program=str(program),bytes=program.stat().st_size,mtime_ns=program.stat().st_mtime_ns,
          steps_per_valid_run=STEPS,short_ramp_dt=2,short_drain_start_dt=3,records=records))
