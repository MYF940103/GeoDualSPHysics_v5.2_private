"""High-k explicit C02 startup diagnosis. Prepare never invokes a solver."""
import argparse
import csv
import json
import math
import shutil
import socket
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from c02_tpi_cost_r1 import CASE, PLAN, ROOT, TESTS, need, setup_xml, xml_path
from c02_tpi_cost_review_r1 import DOUBLE_FIELDS, FIELDS, N0, VEC3, check_hg, read_native, write_report


TAG = "c02_kw_startup_r1"
DT = {"kw10": 1e-6, "kw125": 1.25e-6}
END = .00025
CADENCE = .00001
STEM = PLAN["seed_name"]
SEED = TESTS / PLAN["seed_directory"]


def input_bytes(lane):
    root, _, _ = setup_xml("kw25")
    need(ET.tostring(root.getroot(), encoding="utf-8", xml_declaration=True) == xml_path("kw25").read_bytes(),
         "Reference kw25 input has changed")
    params = root.find("execution/parameters")
    for key, val in (("DtFixed", DT[lane]), ("DtIni", DT[lane]), ("TimeMax", END), ("TimeOut", CADENCE)):
        params.find(f"parameter[@key='{key}']").set("value", str(val))
    # The requested .01-ms save is snapped to its same integer step in both lanes.
    # A quarter-step lead avoids rounding to the next step at nominal targets.
    schedule = root.find("execution/special/timeout")
    schedule.clear()
    schedule.set("active", "true")
    ET.SubElement(schedule, "tout", time="0", timeout="1")
    for i in range(1, 26):
        ET.SubElement(schedule, "tout", time=repr(i*CADENCE-DT[lane]/4), timeout="1")
    ET.indent(root, space="  ")
    return ET.tostring(root.getroot(), encoding="utf-8", xml_declaration=True)


def config(lane):
    return TESTS/"configs"/f"{TAG}_{lane}.xml"


def directory(lane, backend):
    return TESTS/"outputs"/f"{TAG}_{lane}_{backend}"


def spectrum():
    weights = TESTS/"outputs/upl_tpi_case02_step_spectrum_r2/neighbors.csv"
    with weights.open() as stream:
        cells = list(csv.DictReader(stream))
    need(len(cells)==36 and len({(r["ix"], r["iz"]) for r in cells})==36, "C02 Wendland stencil changed")
    r=np.array([(float(v["dx_m"]),float(v["dz_m"])) for v in cells])
    w=np.array([float(v["a_positive_m_inv2"]) for v in cells])
    need(np.all(w>0) and abs(w.sum()-17023.705616385403)<1e-7, "Positive Laplacian weights")
    shape=np.array([float(v["shape_cubed"]) for v in cells])
    D=float(np.float32(2e8))*float(np.float32(.001))/(N0*9806.65)
    rows=[]
    for idir in ((0,1),(1,0),(1,1)):
        theta=r@np.asarray(idir)*(math.pi/.01)
        first=((shape*np.sin(theta))[:,None]*r).sum(axis=0)/(shape*r[:,0]**2).sum()
        need(np.max(np.abs(first))<1e-11, "First-gradient cancellation")
        ell=float(w@(1.-np.cos(theta)))
        for dt in (1.,1.25,1.5,2.,2.5,4.):
            z=D*ell*dt*1e-6
            rows.append(dict(qx_Nyquist=idir[0],qz_Nyquist=idir[1],D_m2_s=D,ell_m_minus2=ell,
                decay_eigenvalue_s_minus1=-D*ell,RK2_limit_us=2e6/(D*ell),dt_us=dt,
                RK2_amplification=1.-z+.5*z*z))
    return rows


def prepare():
    for lane in DT:
        data=input_bytes(lane); dest=config(lane)
        if dest.exists():need(dest.read_bytes()==data, "Prepared short XML differs")
        else:
            with dest.open("xb") as f:f.write(data)
    rows=spectrum()
    out=TESTS/"figures"/(TAG+"_spectrum.csv")
    if out.exists():
        with out.open() as f:
            old=list(csv.DictReader(f))
        need(old==[{k:str(v) for k,v in r.items()} for r in rows],"Existing spectrum differs")
    else:
        with out.open("x",newline="") as f:
            cw=csv.DictWriter(f,fieldnames=rows[0]);cw.writeheader();cw.writerows(rows)
    print("Prepared", list(DT), "and", len(rows), "interior algebra rows")


def run(lane,backend,exe_override):
    infile=config(lane)
    need(infile.read_bytes()==input_bytes(lane),"Prepared input identity")
    exe=(exe_override or ROOT/"bin/windows"/("DualSPHysics5.2_GEO_win64.exe" if backend=="gpu" else "DualSPHysics5.2CPU_win64.exe")).resolve(strict=True)
    out=directory(lane,backend);out.mkdir()
    seed=out/"seed";seed.mkdir()
    for suffix in (".bi4","_Normals.nbi4"):
        src=SEED/(STEM+suffix); dest=seed/src.name
        shutil.copyfile(src,dest)
        need(src.read_bytes()==dest.read_bytes(),"Seed/normal copy changed")
    shutil.copyfile(infile,seed/(STEM+".xml"))
    n=round(END/DT[lane])
    cmd=[str(exe)]+(["-gpu"] if backend=="gpu" else ["-cpu","-ompthreads:1"])
    cmd+=["-stable","-mdbc_freeslip",str(seed/STEM),str(out/"result"),"-dirdataout","data","-svres",f"-nsteps:{n}"]
    info=dict(case=lane,backend=backend,program=str(exe),program_size=exe.stat().st_size,program_mtime=exe.stat().st_mtime_ns,
              host=socket.gethostname(),input=str(infile),seed=str(SEED),argv=cmd)
    write_report(out/"start.json",info)
    wall=time.perf_counter()
    with (out/"console.log").open("xb") as log:
        p=subprocess.Popen(cmd,cwd=CASE,stdout=log,stderr=subprocess.STDOUT)
        rc=p.wait()
    write_report(out/"exit.json",dict(info,pid=p.pid,exit=rc,wall_s=time.perf_counter()-wall,
                 program_unchanged=(exe.stat().st_size,exe.stat().st_mtime_ns)==(info["program_size"],info["program_mtime"])))
    return rc


def review(lane,backend):
    out=directory(lane,backend);res=out/"result";dt=DT[lane];n=round(END/dt);stride=round(CADENCE/dt)
    start=json.loads((out/"start.json").read_text());ex=json.loads((out/"exit.json").read_text())
    need(ex["exit"]==0 and ex["program_unchanged"] and all(ex[k]==v for k,v in start.items()),"Run failed or binding changed; preserve partials")
    need((out/"seed"/(STEM+".xml")).read_bytes()==input_bytes(lane), "Actual XML")
    for suffix in (".bi4","_Normals.nbi4"):
        need((out/"seed"/(STEM+suffix)).read_bytes()==(SEED/(STEM+suffix)).read_bytes(),"Actual geometry")
    text=(res/"Run.out").read_text(encoding="utf8",errors="replace")
    need("HydroMechModel=1 (explicit u-pl)" in text and "Finished execution (code=0)" in text,"Actual finite-Kw exit")
    with (res/"Run.csv").open(encoding="utf-8-sig") as f: rr,=csv.DictReader(f,delimiter=";")
    files=sorted((res/"data").glob("Part_????.bi4"))
    need(int(rr["Steps"])==n and int(rr["PartsOut"])==0 and len(files)==int(rr["PartFiles"])==26,"Actual output count")
    hg=check_hg(text,n);rows=[];clocks=[0.]
    for _ in range(n):clocks.append(clocks[-1]+dt)
    for part,file in enumerate(files):
        head,m,a,h=read_native(file,part,1,1.)
        st=part*stride;t=clocks[st];ii=np.argsort(a["Idp"]);a={k:v[ii] for k,v in a.items()}
        need(h is None and m["Step"]==max(0,st-1) and m["TimeStep"]==t and m["Cpart"]==part and m["Nout"]==0,"Native time/step/part")
        need(set(a)==FIELDS and np.array_equal(a["Idp"],np.arange(1040)),"22 fields and native IDs")
        for k,v in a.items():
            dtype="uint32" if k in ("Idp","FSType") else "float64" if k in DOUBLE_FIELDS else "float32"
            need(v.dtype.name==dtype and v.shape==((1040,3) if k in VEC3 else (1040,)) and np.isfinite(v).all(),"Native array "+k)
        need(m["SymplecticDtPre"]==dt and m["dtmin"]==m["dtmax"]==(dt if st else 0.) and np.isfinite(m["dterror"]) and m["dterror"]<=1.e-14,"Native signed step limit")
        if not st:
            initial=a["Posd"].copy();layers=np.rint(initial[40:,2]/.01-.5).astype(int)
            need(np.all(np.bincount(layers,minlength=100)==10) and not np.any(a["Vel"]) and not np.any(a["PorePress"]), "Initial lattice/rest")
        x=a["Posd"];j=a["PoroVolumeRatio"][40:];por=1-(1.-N0)/j
        need(np.array_equal(x[:40],initial[:40]) and not np.any(a["Vel"][:40]) and not np.any(x[40:,1]) and np.min(x[40:,2])>0,"Geometry")
        need(not np.any(a["Kplastic"]) and not np.any(a["PorePress0"]) and np.array_equal(a["PorePress"],a["ExcessPorePress"]),"Elastic and pressure reference")
        need(np.all(a["Rhop"]>=700) and np.all(a["Rhop"]<=3000) and np.all(j>1.-N0) and np.all(a["Rhop"][:40]==2100) and not np.any(a["PoroThetaLastStage"][:40]),"Density/volume")
        for k,ref in (("PoroPorosity",por),("PoroCurrentVolume",head["MassFluid"]/2100*j),("PoroMixtureDensity",1000+1100/j),("PoroHydraulicConductivity",float(np.float32(.001)))):
            need(not np.any(a[k][:40]) and np.allclose(a[k][40:],ref,rtol=5e-13,atol=0),"Ledger "+k)
        for block in ("kk","ij"):
            need(np.array_equal(a["SigmaState_"+block].astype("float32"),a["Sigma_"+block]),"Stress writeback")
        need(np.array_equal(np.isin(a["FSType"][40:],(2,3)),layers==99) and a["FSType"].max()<=4,"10 eventual drainage receivers")
        hydraulic=head["H"]**2*np.min(por)*9806.65/(2e8*float(np.float32(.001)))
        need(dt<=hydraulic+1e-14 and t<.01,"Closed pre-ramp hydraulic bound")
        p=a["PorePress"][40:];vv=np.linalg.norm(a["Vel"][40:],axis=1)
        load=((a["PoroMixtureDensity"][40:]*a["PoroCurrentVolume"][40:])[:,None]*a["HydroMechLoadAce"][40:]).sum(axis=0)
        rows.append(dict(completed=st,time_s=t,pressure_min_Pa=float(p.min()),pressure_max_Pa=float(p.max()),
            pressure_rms_Pa=float(np.sqrt(np.mean(p.astype(float)**2))),peak_speed_m_s=float(vv.max()),
            force_z_N_m=float(load[2]),min_hydraulic_s=float(hydraulic),signed_dterror_s=float(m["dterror"]),
            dz_max_mm=float(np.abs(x[40:,2]-initial[40:,2]).max()*1000)))
    write_report(TESTS/"logs"/f"{TAG}_{lane}_{backend}.json",dict(steps=n,frames=len(files),case=lane,backend=backend,
        elapsed_loop_s=float(rr["TSimul"]),hg=hg,rows=rows,scope="closed ramp startup only; no drained accuracy/cost acceptance"))


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("action",choices=("prepare","run","review"))
    cli.add_argument("--lane",choices=DT);cli.add_argument("--backend",choices=("cpu","gpu"));cli.add_argument("--exe",type=Path)
    args=cli.parse_args()
    if args.action=="prepare":prepare()
    elif not args.lane or not args.backend:cli.error("run and review require --lane and --backend")
    elif args.action=="run":raise SystemExit(run(args.lane,args.backend,args.exe))
    else:review(args.lane,args.backend)
