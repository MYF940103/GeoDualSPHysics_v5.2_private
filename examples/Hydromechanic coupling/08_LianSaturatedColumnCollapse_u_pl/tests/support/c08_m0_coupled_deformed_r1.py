"""Two bounded CPU trajectories from one measured, already released finite-Kw C08 state."""
import argparse
import json
import os
import shutil
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

import numpy as np
import c08_m0_coupled_r1 as base
from c08_m0_release_short_r1 import release_modify

T=base.T
TAG="c08_m0_coupled_deformed_r1"
SEED=T/"outputs/c08_h18_as03n255_full3_r1"
STAGE=T/"outputs"/(TAG+"_seed")
BUILD=T/"outputs"/(TAG+"_build_r2")
PART=SEED/"data/Part_0038.bi4"
CAP=2076009
sys.path.insert(0,str(T.parents[1]/"04_CryerProblem_PR/tests/support"))
from cryer_live_history_review import _Cursor,read_item


def modify(name,original):
    text=release_modify(name,original)
    if name=="JSph":
        text=base.once(text,"GravityPreloadTime==.0002","GravityPreloadTime==10.")
        text=base.once(text,"!GravityPreloadReleased && !IsGravityPreloadHandoff()","!GravityPreloadReleased && IsGravityPreloadHandoff()")
        text=base.once(text,"!NoPenetration && !ArtificialStress && !SoilHourglassXi",
            "NoPenetration && ArtificialStress && ArtificialStressCoef==.3f && ArtificialStressExp==2.55f && !SoilHourglassXi")
        return base.once(text,"cfg->NstepsBreak==48","cfg->NstepsBreak==2076009")
    if name!="JSphCpuSingle":
        return text
    text='#include <fstream>\n#include "JDsFixedDt.h"\n'+text
    at="  if(HydroMechTpi)InitTpiPressure();\n  RunGaugeSystem(TimeStep,true);"
    injected=(T/"support/c08_m0_coupled_deformed_state_r1.inc").read_text()
    return base.once(text,at,"  InitTpiPressure();RunGravityPreloadRelease();\n"+injected+"\n  RunGaugeSystem(TimeStep,true);")


FIELDS=("Idp","Posd","Vel","Rhop","SigmaState_kk","SigmaState_ij","Kplastic","PorePress","PorePress0",
        "PoroVolumeRatio","PoroThetaLastStage","FSType","FSNormal","PosDiv")


def released(path,history=False):
    c=_Cursor(path.read_bytes(),64);tree=read_item(c,0,history);c.finish("complete released actual PART")
    part,=tree["children"]
    assert part["name"]==path.stem.upper()
    a=part["arrays"];m=part["values"];ids=np.sort(a["Idp"])
    assert len(a)==22 and np.array_equal(ids,np.r_[0:1805,2060:7060]) and m["Nout"]==0
    for k in a:
        assert np.isfinite(a[k]).all(),k
    assert m["GravityPreloadPhase"]==1 and m["GravityPreloadTargetIdCount"]==255
    assert m["DynamicArtificialStressActive"] and m["DynamicArtificialStressCoef"]==np.float32(.3)
    assert m["DynamicArtificialStressExp"]==np.float32(2.55) and m["DynamicNoPenetrationActive"]
    assert m["DynamicNoPenetrationPolicy"]=="FixedPlaneStageProjectionReleaseOnly" and not m["DynamicNoPenetrationReactionClosed"]
    return m,a,part["children"]


def prepare():
    m,a,ch=released(PART)
    assert m["Step"]+1==2076001 and not ch and m["MaterialLawVersion"]==2 and m["dtmin"]==m["dtmax"]==5e-6
    STAGE.mkdir()
    root=ET.parse(SEED/(SEED.name+".xml"))
    hydro=root.find("execution/special/hydromechanics")
    hydro.find("HydroMechDynamicSeepage").tag="HydroMechModel";hydro.find("HydroMechModel").set("value","2")
    for tag,value in (("HydroMechTopLoadMode","0"),("HydroMechDrainage","0"),("HydroMechFreeSeepage","1")):
        e=hydro.find(tag);assert e.get("value")==value;hydro.remove(e)
    ET.SubElement(root.find("execution/special"),"drainage",mode="freeSeepage")
    root.find("execution/parameters/parameter[@key='TimeOut']").set("value","0.000001")
    xml=T/"configs"/(TAG+".xml");assert not xml.exists()
    root.write(xml,encoding="utf-8",xml_declaration=True)
    shutil.copy2(xml,STAGE/(SEED.name+".xml"))
    for end in (".bi4","_Normals.nbi4"):
        shutil.copy2(SEED/(SEED.name+end),STAGE/(SEED.name+end))
    records=np.empty(6805,dtype=[(k,a[k].dtype,a[k].shape[1:]) for k in FIELDS])
    order=np.argsort(a["Idp"])
    for k in FIELDS:
        records[k]=a[k][order]
        assert records[k].tobytes()==a[k][order].tobytes()
    header=struct.pack("<IIdd",6805,int(m["Step"])+1,m["TimeStep"],m["GravityPreloadActualTime"])
    (STAGE/"private_native_rows.bin").write_bytes(header+records.tobytes())


def run(beta):
    name=TAG+("_b0" if beta=="0" else "_b004")
    dest=T/"outputs"/name
    console=T/"logs"/(name+".console.log")
    if dest.exists() or console.exists():raise FileExistsError(dest)
    env=dict(os.environ,C08_PRIVATE_BETA=beta,C08_RELEASED_NATIVE_ROWS=str(STAGE/"private_native_rows.bin"))
    args=[str(BUILD/"C08Pressure.exe"),"-cpu","-ompthreads:1","-stable","-mdbc_freeslip:1",str(STAGE/SEED.name),
          str(dest),"-dirdataout","data","-svres","-nsteps:"+str(CAP)]
    with console.open("xb") as log:
        p=subprocess.run(args,cwd=T.parent,env=env,stdout=log,stderr=subprocess.STDOUT)
    (T/"logs"/(name+".call.json")).write_text(json.dumps(dict(command=args,source=str(PART),beta=beta,returncode=p.returncode),indent=2))
    p.check_returncode()


if __name__=="__main__":
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("action",choices=("build","prepare","b0","b004"))
    act=ap.parse_args().action
    if act=="build":
        base.BUILD=BUILD;base.EXE=BUILD/"C08Pressure.exe";base.modify=modify;base.build()
    elif act=="prepare":prepare()
    else:run("0" if act=="b0" else "0.04")
