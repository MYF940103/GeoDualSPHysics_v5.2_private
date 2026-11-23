"""Build the offline Windows x64 Cryer native-mass weak GPU full-cycle package."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

import numpy as np
from cryer_pair_window import Driver, DT, DAMP, MU, LAM, T, TetMechanics, CryerSPHPressure, viscosity_matrix, validate
from cryer_weak_window import configure
from cryer_shell_equilibrium import Q, R, Reference, reference_fields

TAG="cryer_weak_full_server_r1"
BASE=T/"outputs"
WEAK=BASE/"cryer_weak_window_build_r1"
DLL=WEAK/"cryer_weak_window.dll"
MESH=BASE/"cryer_tet_reference_r1.npz"
PARTS=(("p",1),("previous",1),("u",3),("v",3),("stress",6),("J",1))
INPUT_HASH={
    "cryer_weak_window.dll":"d89fa09263e9ed3af7e15d5e8eedf07b967809e64762a8fa19b2173bfcb14c9c",
    "state_4096.npz":"557e003c76971eebb47aa43e5c93636a8b0ad3382bb8074ac41921f2080fe315",
    "state_4097.npz":"9381fa61afaf747cab7a87980af196f2a9f4c5251b0aebe226777f4e7ddbdea3",
    "state_4160.npz":"0beeab24bf92646df42adbc65a184d02e66749ba5cc2df0fccb8964c4d3c0a26",
    "state_36864.npz":"8ab328159720d142763c575db69ae1ac17444a2ecb8672d649c2008ff29486d4"}

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream,"sha256").hexdigest()

def write_json(path, data):
    with path.open("x",encoding="utf8") as stream:
        json.dump(data,stream,indent=2,allow_nan=False)

def write_input(stream,*values):
    for value in values:
        a=np.asarray(value)
        if isinstance(value,int):a=np.array(value,dtype="<i4")
        if a.dtype not in (np.dtype("float64"),np.dtype("int32"),np.dtype("uint8")):
            raise ValueError(f"Unsupported binary type {a.dtype}")
        a.tofile(stream)

def require(check,message):
    if not check:raise ValueError(message)

def operators(inputs):
    m=TetMechanics(MESH)
    h=CryerSPHPressure.load()
    require(np.array_equal(m.ids,h.ids),"Mesh/hydraulic ID mismatch")
    g=Driver(DLL)
    with (inputs/"operators.bin").open("xb") as stream:
        native=g.call
        def capture(name,*args):
            native(name,*args)
            if name=="init":write_input(stream,*args[1:])
            elif name=="setCsr" and args[0]!=3:write_input(stream,*args[1:])
            elif name in ("uploadWeak","setGeometry"):write_input(stream,*args)
        g.call=capture
        g.call("init",m.n,DT,MU,LAM,DAMP)
        try:
            g.upload(0,m.D);g.upload(1,m.HT)
            for k in (2,3):g.upload(k,[h.E])
            g.upload(4,[viscosity_matrix(m)])
            g.call("setGeometry",*[np.ascontiguousarray(a) for a in
                   (m.x,m.mass,m.unit_surface_force,1/h.S0,h.normal_lx,h.fs.astype(np.uint8))])
            g.call("start")
            fixtures=validate(g,m,h)
            fixtures.update(configure(g,m,h))
            for step in (4096,4097,4160,36864):
                source=BASE/("cryer_weak_peak_r1" if step==36864 else "cryer_weak_open_r1")/f"state_{step}.npz"
                require(digest(source)==INPUT_HASH[source.name],"Original checkpoint SHA mismatch")
                with np.load(source) as z:
                    require(Path(z["program"].item()).resolve()==DLL.resolve() and int(z["step"])==step and
                            np.array_equal(z["ids"],m.ids),"Original program path, step or ID mismatch")
                    fields=[np.ascontiguousarray(z[key]) for key,_ in PARTS]
                with (inputs/f"state_{step}.bin").open("xb") as f:write_input(f,*fields)
            # Last fields are exactly the archived 36864 checkpoint. Compute three
            # fresh steps through the original Python driver as an independent host oracle.
            g.call("restore",36864,*fields)
            g.call("advanceWeak",3)
            outputs=[np.empty_like(f) for f in fields]
            g.call("readState",outputs[0],*outputs[2:]);g.call("readPrevious",outputs[1])
            with (inputs/"state_36867.bin").open("xb") as f:write_input(f,*outputs)
        finally:g.call("releaseWeak")
    with np.load(MESH) as z:
        keys=("native_ids","x0","faces","tets","Ve","native_mass_kg","native_volume_m3","native_surface","material_shell")
        np.savez_compressed(inputs/"reference_mesh.npz",**{k:z[k] for k in keys})
    return fixtures

def time_plan(inputs):
    source=T.parent/"support/CaseCryer_TPI_P3_nu030_full_r1_schedule.csv"
    with source.open() as stream: rows=list(csv.DictReader(stream))
    steps=[int(r["completed_steps"]) for r in rows]
    ref=Reference(.3,finite=False)
    all_steps=sorted(set(steps)|{4097,4160,25984,36864,36867})
    require(len(steps)==265 and steps[-1]==481685,"Unexpected endpoint")
    (inputs/"steps.txt").write_text("".join(f"{i}\n" for i in steps),encoding="ascii")
    with (inputs/"reference.csv").open("x",newline="") as stream:
        w=csv.writer(stream);w.writerow(["step","time_s","tau_s","legacy_Tv","scheduled","target_Tv","M0_center18_Pa","M0_surface_inward_mm"])
        for step in all_steps:
            tau=(step-4096)*DT;tv=tau*ref.legacy_cv/R**2
            j=steps.index(step) if step in steps else -1
            target=(j-64)/200 if j>=64 else None
            if target is not None:
                require(-1e-14<=tv-target<DT*ref.legacy_cv/R**2,"Target is not the first dyadic step")
            if tau>=0:
                m=reference_fields(ref,tau,np.array([.0025]))[1]
                p=float(ref.pressure([tau])[0]);u=1000*R*(Q-m)/(3*ref.K)
            else:p=u=None
            w.writerow([step,step*DT,tau,tv,int(j>=0),target,p,u])
    return digest(source)

def package(build, destination):
    require(digest(DLL)==INPUT_HASH[DLL.name],"Original weak DLL SHA mismatch")
    native=build/"weak_full.exe"
    require(native.exists(),"Compile cryer_weak_full_host.cpp with MSVC v143 and the original DLL import library")
    zip_path=destination/(TAG+".zip")
    require(not zip_path.exists() and not zip_path.with_suffix(".zip.sha256").exists(),"Preserve previous ZIP")
    folder=build/"package";folder.mkdir()
    inputs=folder/"inputs";inputs.mkdir()
    shutil.copy2(native,folder/native.name);shutil.copy2(DLL,folder/DLL.name)
    cl=Path(shutil.which("cl.exe")).resolve()
    redist=cl.parents[6]/"Redist"/"MSVC"/cl.parents[3].name/"x64/Microsoft.VC143.CRT"
    for name in ("msvcp140.dll","vcruntime140.dll","vcruntime140_1.dll"):
        shutil.copy2(redist/name,folder/name)
    fixtures=operators(inputs);schedule_sha=time_plan(inputs)
    for kind in ("open","peak"):
        old=BASE/("cryer_weak_"+kind+"_r1")
        for name in ("history.csv","completed.json"):
            shutil.copy2(old/name,inputs/(kind+"_"+name))
    gate="cryer_weak_3d_peak_r1_gates.json"
    shutil.copy2(T/"logs"/gate,inputs/gate)
    require(json.loads((inputs/gate).read_text())["peak_bounds_pass"] and
            json.loads((inputs/"open_completed.json").read_text())["closed_pass"],"Missing source qualification")
    source=T/"support"
    for name in ("cryer_weak_full_server.ps1","cryer_weak_full_review.py"):shutil.copy2(source/name,folder/name)
    for label,mode in (("RUN_FULL","full"),("CHECK_GPU","smoke")):
        (folder/(label+".bat")).write_bytes(('@echo off\r\ncd /d "%~dp0"\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0cryer_weak_full_server.ps1" '+mode+'\r\nset "runrc=%errorlevel%"\r\npause\r\nexit /b %runrc%\r\n').encode("ascii"))
    (folder/"README.txt").write_text(
        "Cryer 3-D, nu=0.30, fixed material reference, native nodal masses, scalar constant k, M0.\n"
        "Research GPU component. No GeoDualSPHysics production executable or XML switch is involved.\n"
        "Extract the complete ZIP in a fresh Windows x64 directory on the RTX A6000 with its NVIDIA driver.\n"
        "CHECK_GPU.bat tests the first drainage step and three updates from the stored 36864 checkpoint.\n"
        "RUN_FULL.bat runs from the initial state, compares four retained six-field checkpoints bit for bit,\n"
        "then restores the retained step 36864 to continue to the 1 Tv endpoint (481685).\n"
        "One GPU only. Keep at least 2 GB free after extraction. No Python, VS, network or CUDA toolkit is required for the run.\n"
        "Output: cryer_weak_full_out. Return that entire directory, including server_run.json and actual_clock.csv.\n"
        "Return partial output and console error if a run stops. An existing output directory is preserved.\n"
        "On the analysis workstation run: py -3.11 cryer_weak_full_review.py cryer_weak_full_out NEW_REVIEW_DIR\n"
        "The reviewer needs Python >=3.11 with NumPy and Matplotlib. It uses inputs/ beside the reviewer, checks hashes,\n"
        "writes CSVs, figures and a JSON report with pressures, geometry, drainage, and surface settlement.\n"
        "Each state file contains 15*37173 little-endian binary64 values: p(N), previous p(N), u(N,3), v(N,3),\n"
        "stress(N,6: xx, yy, zz, xy, yz, xz), J(N). Units Pa, m, m/s. IDs and x0 are in inputs/reference_mesh.npz.\n"
        "Current coordinates are x0+u. Current J is nodal, while signed tet determinant ratios are computed separately.\n"
        "All 265 scheduled steps and four supplemental steps have full fields. Original dense peak history is also supplied.\n"
        "Opening at step 4096, tD=0.0078125 s; dt=2^-19 s. Interval after opening = 0.005 legacy Tv, first attained step.\n"
        "The smoke path executes four actual GPU updates. A full local 3050 run is estimated at 94 min with replay; measure server time.\n",
        encoding="ascii")
    inventory=[dict(name=p.relative_to(folder).as_posix(),bytes=p.stat().st_size,sha256=digest(p))
               for p in sorted(folder.rglob("*")) if p.is_file()]
    git=subprocess.run(["git","rev-parse","HEAD"],cwd=T.parents[2],capture_output=True,text=True,check=True)
    refs=[MESH,BASE/"c04_p3_pressure_component_r1.npz",BASE/"cryer_tet_step_reference_r1.npz",
          source/"cryer_pair_window.cu",source/"cryer_weak_window.cu",source/"cryer_pair_window.py",
          source/"cryer_weak_window.py",source/"cryer_weak_full_host.cpp",source/"cryer_weak_full_pack.py"]
    write_json(folder/"manifest.json",dict(method="Cryer original fixed-reference weak 3D native mass, nu=0.30",
               git_head=git.stdout.strip(),reference_input_sha256={p.name:digest(p) for p in refs},
               retained_files_sha256=INPUT_HASH,original_schedule_sha256=schedule_sha,
               host_compiler=cl.parents[3].name,host_options="/EHsc /std:c++17 /O2 /MT",component_fixtures=fixtures,files=inventory))
    with zipfile.ZipFile(zip_path,"x",zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for path in sorted(folder.rglob("*")):
            if path.is_file():z.write(path,path.relative_to(folder))
    with zipfile.ZipFile(zip_path) as z:require(z.testzip() is None,"ZIP CRC failure")
    zip_path.with_suffix(".zip.sha256").write_text(digest(zip_path)+"  "+zip_path.name+"\n",encoding="ascii")
    print(zip_path,zip_path.stat().st_size,flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--build",type=Path,default=BASE/"cryer_weak_full_build_r1")
    p.add_argument("--destination",type=Path,default=BASE)
    a=p.parse_args();package(a.build,a.destination)
