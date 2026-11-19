"""Launch one fresh local Cryer GPU implementation check; preserve each exit and log."""
import argparse
import csv
import ctypes
from ctypes import wintypes
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET

T = Path(__file__).resolve().parents[1]
CASES = {"debug2":2,"default128":128,"b64":64,"drain4097":4097}


def stat(path):
    s=path.stat()
    return dict(path=str(path),bytes=s.st_size,mtime_ns=s.st_mtime_ns)


def write(path, value):
    with path.open("x",encoding="utf-8") as f:
        json.dump(value, f, indent=2)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("profile",choices=CASES)
    ap.add_argument("program",type=Path)
    ap.add_argument("--revision",type=int,default=1)
    args=ap.parse_args()
    debug=args.profile=="debug2"
    default=args.profile=="default128"
    exe=args.program.resolve(strict=True)
    n=CASES[args.profile]
    tag=f"cryer_p3_gpu_{args.profile}_r{args.revision}"
    output=T/"outputs"/tag
    record=T/"logs"/tag
    if output.exists() or any(record.parent.glob(tag+".*")):
        raise FileExistsError(f"Existing output or ownership record for {tag}")
    conf="Debug" if debug else "Release"
    build=exe.parent.parent
    if exe.parent.name!="out" or build.parent!=T/"outputs" or not re.fullmatch(rf"cryer_p3_gpu_r\d+_{conf}",build.name):
        raise ValueError("Wrong private Cryer GPU build")
    receipt=T/"logs"/(build.name+".build.json")
    if not json.loads(receipt.read_text(encoding="utf-8-sig"))["passed"]:
        raise ValueError("GPU build did not pass")
    seed=T/"outputs"/("upl_cryer_freebody_short_r1_seed" if default else "cryer_p3_local_seed_r1")/"upl_cryer_freebody_short_r1"
    xml=ET.parse(seed.with_suffix(".xml"))
    params={e.get("key"):e.get("value") for e in xml.iter("parameter")}
    dt=2**(-20 if default else -19)
    assert float(params["DtIni"])==float(params["DtFixed"])==dt and float(params["TimeOut"])==2**-13
    assert float(params["TimeMax"])>=n*dt
    before=[stat(p) for p in (exe,receipt,seed.with_suffix(".xml"),seed.with_suffix(".bi4"))]
    argsolver=[str(exe),"-gpu","-stable",str(seed),str(output),"-dirdataout","data","-svres",f"-nsteps:{n}"]
    argv=argsolver
    mem=record.with_suffix(".memcheck.log")
    if debug:
        sanitizer=Path(os.environ["CUDA_PATH"])/"compute-sanitizer/compute-sanitizer.exe"
        if not sanitizer.is_file():
            sanitizer=Path(shutil.which("compute-sanitizer")).parent.parent/"compute-sanitizer/compute-sanitizer.exe"
        argv=[str(sanitizer.resolve(strict=True)),"--tool","memcheck","--error-exitcode","88","--log-file",str(mem),*argsolver]
    env={k:v for k,v in os.environ.items() if not k.upper().startswith("UPL_TPI_")}
    if not default:
        env.update(UPL_TPI_GPU_R1="B",UPL_TPI_P3_ROWS_R1="3",UPL_TPI_M0_DT_R1="EQ40_RH1")
    info=dict(tag=tag,profile=args.profile,dt=dt,n=n,owner_pid=os.getpid(),args=argv,inputs=before,
              tpi_environment={k:v for k,v in env.items() if k.startswith("UPL_TPI_")})
    start=time.time()
    with record.with_suffix(".console.log").open("xb") as console:
        proc=subprocess.Popen(argv,cwd=exe.parent,env=env,stdout=console,stderr=subprocess.STDOUT)
        handle=wintypes.HANDLE(int(proc._handle))
        timestamps=[wintypes.FILETIME() for _ in range(4)]
        kernel=ctypes.WinDLL("kernel32",use_last_error=True)
        if not kernel.GetProcessTimes(handle,*[ctypes.byref(t) for t in timestamps]):
            raise ctypes.WinError(ctypes.get_last_error())
        info.update(pid=proc.pid,created_filetime=(timestamps[0].dwHighDateTime<<32)+timestamps[0].dwLowDateTime)
        write(record.with_suffix(".start.json"),info)
        result=proc.wait()
        native=wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle,ctypes.byref(native)):
            raise ctypes.WinError(ctypes.get_last_error())
    info.update(popen_exit=result,win32_exit=native.value,wall_s=time.time()-start,passed=False)
    try:
        if result or native.value:
            raise RuntimeError("process rejected; see original console")
        if debug and "ERROR SUMMARY: 0 errors" not in mem.read_text(errors="replace"):
            raise ValueError("missing zero-error GPU memcheck")
        with (output/"Run.csv").open(encoding="utf-8-sig",newline="") as f:
            row,=csv.DictReader(f,delimiter=";")
        cadence=round(2**-13/dt)
        frames=1+n//cadence+int(n%cadence!=0)
        if (int(row["Steps"]),int(row["PartFiles"]),int(row["PartsOut"]),int(row["Np"]))!=(n,frames,0,37181):
            raise ValueError("solver summary differs from plan")
        if len(list((output/"data").glob("Part_*.bi4")))!=frames:
            raise ValueError("native sequence count differs")
        assert before==[stat(Path(p["path"])) for p in before]
        info.update(passed=True,device=row["Hardware"],loop_s=float(row["TSimul"]),frames=frames)
    except Exception as exc:
        info["error"]=str(exc)
        raise
    finally:
        write(record.with_suffix(".run.json"),info)
    print(json.dumps(info,indent=2))


if __name__=="__main__":
    main()
