"""Actual C08 psi0 finite Kw PRE, 1 ms M0 hold, matched AS and plane contact during release."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import c08_m0_release_mature_gpu_r1 as mature
import c08_m0_release_gpu_r1 as rel
import c08_m0_gpu_coupled_r1 as gpu
from c08_m0_coupled_deformed_r1 import SEED

T=gpu.T
TAG="c08_m0_coupled_baseline_gpu_r1"
BUILD=T/"outputs"/(TAG+"_build")
EXE=BUILD/"C08Collapse.exe"
STAGE=T/"outputs"/(TAG+"_seed")
CAPS={"short":2000208,"w30":2060200}
ONCE=gpu.once


def edit(name,code):
    text=mature.edit(name,code)
    if name=="JSph":
        text=ONCE(text,"!GravityPreloadReleased && !IsGravityPreloadHandoff()","!GravityPreloadReleased && IsGravityPreloadHandoff()")
        text=ONCE(text,"!NoPenetration && !ArtificialStress && !SoilHourglassXi",
             "NoPenetration && ArtificialStress && ArtificialStressCoef==.3f && ArtificialStressExp==2.55f && !SoilHourglassXi")
        return ONCE(text,"cfg->NstepsBreak==2006200","cfg->NstepsBreak==2060200")
    text=ONCE(text,'GravityPreloadStateFile=std::getenv("C08_MATURE_PRE");','// Use the exact schema2 PRE from the receiver XML.')
    # The published NoPen projection is conditional on an actual handoff. Retain statefile throughout.
    text=ONCE(text,"  GravityPreloadStateFile.clear();","  // Keep the original source contract and release-only plane policy.")
    return ONCE(text,"Nstep<2000208 || (Nstep+1-2000200)%100==0",
       "Nstep<2000002 || Nstep==2000198 || Nstep==2000199 || (Nstep>=2000200 && (Nstep<2000208 || (Nstep+1-2000200)%2000==0))")


def prepare():
    xml=T/"configs"/(TAG+".xml")
    assert not xml.exists()
    root=ET.parse(T/"configs/c08_m0_coupled_deformed_r1.xml")
    root.find("execution/parameters/parameter[@key='TimeOut']").set("value","0.01")
    pre=root.find("execution/special/gravitypreload")
    assert pre.get("statefile")==str(mature.hold.PRE)
    root.write(xml,encoding="utf-8",xml_declaration=True)
    STAGE.mkdir()
    shutil.copy2(xml,STAGE/(SEED.name+".xml"))
    for suffix in (".bi4","_Normals.nbi4"):
        shutil.copy2(SEED/(SEED.name+suffix),STAGE/(SEED.name+suffix))


def run(beta,window):
    if window=="w30":
        check=json.loads((T/"logs"/(TAG+"_short.check.json")).read_text())
        assert check["step"]==2000208 and check["actual_AS_plane_transition_checked"]
    name=TAG+"_"+window+("_b004" if beta else "_b0")
    output=T/"outputs"/name
    log=T/"logs"/(name+".console.log")
    assert not output.exists() and not log.exists()
    args=[str(EXE),"-gpu","-stable","-mdbc_freeslip:1",str(STAGE/SEED.name),str(output),
          "-dirdataout","data","-svres","-nsteps:"+str(CAPS[window])]
    env=dict(os.environ,C08_PRIVATE_BETA="0.04" if beta else "0")
    with log.open("xb") as out:
        proc=subprocess.run(args,cwd=T.parent,env=env,stdout=out,stderr=subprocess.STDOUT)
    (T/"logs"/(name+".call.json")).write_text(json.dumps(dict(command=args,PRE=str(mature.hold.PRE),
        cap=CAPS[window],returncode=proc.returncode,beta=beta),indent=2))
    proc.check_returncode()


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=("build","prepare","sequence",*CAPS))
    parser.add_argument("--beta",choices=("0","0.04"),default="0")
    args=parser.parse_args()
    if args.action=="build":
        rel.ROOT,rel.EXE,rel.edit=BUILD,EXE,edit;rel.build()
    elif args.action=="prepare":prepare()
    elif args.action=="sequence":
        # Serial by construction. Each branch can have its own physical rejection.
        for window in CAPS:
            failed=[]
            for beta in (0.,.04):
                print(f"Starting {window}, beta={beta:g}",flush=True)
                try:run(beta,window)
                except subprocess.CalledProcessError as err:
                    failed.append((beta,err.returncode))
                    if window=="short":
                        raise SystemExit(f"Receiver implementation failed; inspect {beta:g} first: {err.returncode}")
            if failed:
                raise SystemExit(f"{window} rejected; preserve each original call and final saved PART: {failed}")
            subprocess.run([sys.executable,"-B",str(T/"support/c08_m0_coupled_baseline_gpu_review_r1.py"),window],check=True)
        subprocess.run([sys.executable,"-B",str(T/"support/c08_m0_coupled_baseline_gpu_physics_r1.py")],check=True)
    else:run(float(args.beta),args.action)
