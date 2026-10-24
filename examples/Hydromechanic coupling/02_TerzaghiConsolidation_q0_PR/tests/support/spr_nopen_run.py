"""Observe reference NoPen under pure tangential and inward normal motion."""
from pathlib import Path
import json
import argparse
import subprocess
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
from mdbc_plane_prepare import render
from spr_planes_run import TESTS,REPO,bound

TAG="spr_nopen_reference_r1"


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--spr-on',action='store_true');args=parser.parse_args()
    tag='spr_nopen_on_r1' if args.spr_on else TAG
    receipt=TESTS/"logs"/(tag+".check.json");assert not receipt.exists()
    exe=TESTS/"outputs"/('spr_nopen_r2rel' if args.spr_on else 'spr_nopen_r1rel')/"spr_nopen.exe"
    result=dict(completed=False,inputs=[bound(__file__),bound(exe)],runs=[],tangent_tolerance_m_s=1e-7)
    try:
        for geometry in ("2d_h","2d_t"):
            for mode in (2,3):
                name=f"{tag}_{geometry}_s{mode}";definition=TESTS/"configs"/(name+"_Def.xml")
                generated=TESTS/"outputs"/(name+"_input");out=TESTS/"outputs"/name
                assert not any(p.exists() for p in (definition,generated,out))
                root=ET.fromstring(render(geometry,mode)[0])
                for key,value in (("NoPenetration","1"),("SoilBoundaryDerivativeSPR","1" if args.spr_on else "0")):
                    root.find("execution/parameters/parameter[@key='"+key+"']").set("value",value)
                ET.indent(root,space="  ");definition.write_text('<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root,encoding="unicode")+'\n',encoding="utf8")
                generated.mkdir();prefix=generated/name
                with (TESTS/"logs"/(name+".gencase.log")).open("xb") as stream:
                    subprocess.run([str(REPO/"bin/windows/GenCase_win64.exe"),str(definition.with_suffix("")),str(prefix),"-save:all"],stdout=stream,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
                with (TESTS/"logs"/(name+".log")).open("xb") as stream:
                    process=subprocess.run([str(exe),"-cpu","-ompthreads:1",str(prefix),str(out),"-dirdataout","data","-sv:none"],stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=60)
                if args.spr_on and geometry=='2d_t':
                    assert process.returncode!=0 and 'inclined NoPen is not rotation-consistent' in (TESTS/'logs'/(name+'.log')).read_text(encoding='utf8',errors='replace')
                    result['runs'].append(dict(geometry=geometry,slip_mode=mode,expected_inclined_rejection=True));print(name,'expected axis-scope rejection',flush=True);continue
                assert process.returncode==0
                item=json.loads((out/"nopen_complete.json").read_text())
                item.update(geometry=geometry,slip_mode=mode,tangent_invariance_passed=item["max_pure_tangent_normal_shift_m_s"]<=1e-7,
                            definition=bound(definition),outputs=[bound(p) for p in out.iterdir() if p.is_file()])
                result['runs'].append(item);print(name,{k:item[k] for k in ('max_pure_tangent_normal_shift_m_s','pure_tangent_active_count','max_inward_normal_shift_m_s','tangent_invariance_passed')},flush=True)
                if args.spr_on:
                    a=pd.read_csv(TESTS/'outputs'/f'{TAG}_{geometry}_s{mode}'/'nopen.csv',float_precision='round_trip')
                    b=pd.read_csv(out/'nopen.csv',float_precision='round_trip')
                    assert a.to_numpy(dtype='<f8').tobytes()==b.to_numpy(dtype='<f8').tobytes()
                    item['original_nopen_shift_0ulp']=True
        result['completed']=True
    finally:
        with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)


if __name__=='__main__':main()
