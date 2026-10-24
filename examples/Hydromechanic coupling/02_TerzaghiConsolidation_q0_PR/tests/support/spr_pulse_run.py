"""Bounded 2-ms nonzero pulse and half-step test; never runs formal consolidation."""
from pathlib import Path
from decimal import Decimal
import argparse
import json
import subprocess
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from spr_planes_run import xml, bound, TESTS, REPO

TAG="spr_pulse_r1"


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--nopen',action='store_true');args=parser.parse_args()
    tag='spr_pulse_nopen_r1' if args.nopen else TAG
    binary='spr_pulse_nopen_r2rel' if args.nopen else 'spr_pulse_r1rel'
    receipt=TESTS/"logs"/(tag+".check.json");assert not receipt.exists()
    build=TESTS/"logs"/(binary+".build.json");b=json.loads(build.read_text(encoding="utf-8-sig"))
    exe=TESTS/"outputs"/binary/"spr_pulse.exe";assert bound(exe)["sha256"]==b["exe_sha256"]
    result=dict(passed=False,inputs=[bound(__file__),bound(build),bound(exe)],runs=[],half=[])
    try:
        for geometry in (("corner2",) if args.nopen else ("corner2","wedge2")):
            for mode in ((2,3) if args.nopen else (1,2,3)):
                histories=[]
                for v,dt,stride in (("c",".000001",10),("h",".0000005",20)):
                    name=f"{tag}_{geometry}_s{mode}_{v}";definition=TESTS/"configs"/(name+"_Def.xml")
                    generated=TESTS/"outputs"/(name+"_input");out=TESTS/"outputs"/name
                    assert not any(p.exists() for p in (definition,generated,out))
                    root=ET.fromstring(xml(geometry,mode))
                    if args.nopen:root.find("execution/parameters/parameter[@key='NoPenetration']").set('value','1')
                    for key,value in (("DtIni",dt),("DtFixed",dt),("TimeMax",".002")):
                        root.find("execution/parameters/parameter[@key='"+key+"']").set("value",value)
                    ET.indent(root,space="  ")
                    with definition.open("x",encoding="utf8") as stream:stream.write('<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root,encoding="unicode")+'\n')
                    generated.mkdir();prefix=generated/name;log=TESTS/"logs"/(name+".log")
                    with (TESTS/"logs"/(name+".gencase.log")).open("xb") as stream:
                        subprocess.run([str(REPO/"bin/windows/GenCase_win64.exe"),str(definition.with_suffix("")),str(prefix),"-save:all"],stdout=stream,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
                    command=[str(exe),str(int(Decimal('.002')/Decimal(dt))),str(stride),"-cpu","-ompthreads:1",str(prefix),str(out),"-dirdataout","data","-sv:none"]
                    with log.open("xb") as stream:
                        child=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
                    assert child.returncode==0,(name,"runtime failure")
                    done=json.loads((out/"pulse_complete.json").read_text())
                    a=pd.read_csv(out/"pulse.csv",float_precision="round_trip").sort_values(["step","id"])
                    energy=pd.read_csv(out/"energy.csv")
                    n=len(a[a.step.eq(0)]);assert len(a)==201*n and a.id.nunique()==n
                    assert a.select_dtypes('number').apply(np.isfinite).all().all() and a.rho.gt(0).all() and a.kplastic.eq(0).all()
                    assert a.z.gt(0).all() and (a.x.gt(0).all() if geometry=="corner2" else (np.cos(np.pi/6)*a.x+.5*a.z).gt(0).all())
                    ratio=float(energy.total_J_m.max()/energy.total_J_m.iloc[0])
                    record=dict(name=name,completed=done,energy_ratio_max=ratio,energy_gate=ratio<=1.1,definition=bound(definition),outputs=[bound(p) for p in out.iterdir() if p.is_file()])
                    result['runs'].append(record);histories.append(a)
                    print(name,"energy max/initial",ratio,flush=True)
                c,h=histories
                assert np.array_equal(c.id,h.id) and np.allclose(c.time_s,h.time_s,atol=1e-12,rtol=0)
                pressure=(c.pressure.to_numpy()-h.pressure.to_numpy()).reshape(201,n)
                disp=np.sqrt((c.x.to_numpy()-h.x.to_numpy())**2+(c.z.to_numpy()-h.z.to_numpy())**2)*1000
                maximum=float(np.sqrt(np.mean(pressure**2,axis=1)).max());movement=float(disp.max())
                pair=dict(geometry=geometry,slip_mode=mode,pressure_rms_max_pa=maximum,material_displacement_max_mm=movement,passed=maximum<=.5 and movement<=1e-5)
                result['half'].append(pair);print('HALF',pair,flush=True)
        result['passed']=all(x['energy_gate'] for x in result['runs']) and all(x['passed'] for x in result['half'])
    finally:
        with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)


if __name__=='__main__':main()
