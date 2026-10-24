"""Missing axis-NoPen pairs only; retain completed standard pulse evidence unchanged."""
from decimal import Decimal
from pathlib import Path
import json
import subprocess
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from spr_planes_run import TESTS,REPO,bound


def difference(a,b):
    assert np.array_equal(a.id,b.id) and np.allclose(a.time_s,b.time_s,atol=1e-12,rtol=0)
    n=int(a.step.eq(0).sum());assert len(a)==201*n
    p=(a.pressure.to_numpy()-b.pressure.to_numpy()).reshape(201,n)
    pressure=float(np.sqrt(np.mean(p*p,axis=1)).max());displacement=float(np.hypot(a.x.to_numpy()-b.x.to_numpy(),a.z.to_numpy()-b.z.to_numpy()).max()*1000)
    return dict(pressure_rms_max_pa=pressure,material_displacement_max_mm=displacement,passed=pressure<=.5 and displacement<=1e-5)


def main():
    tag='spr_gpu_nopen_pulse_r2';receipt=TESTS/'logs'/(tag+'.check.json');assert not receipt.exists()
    build=TESTS/'logs/spr_gpu_pulse_Release_op1.build.json';b=json.loads(build.read_text(encoding='utf-8-sig'));exe=Path(b['executable']);assert bound(exe)['sha256']==b['executable_sha256']
    result=dict(passed=False,inputs=[bound(__file__),bound(build),bound(exe)],runs=[],half=[],cpu_gpu=[])
    try:
        for nopen in (True,):
            for geometry in (('corner2',) if nopen else ('corner2','wedge2')):
                for mode in ((2,3) if nopen else (1,2,3)):
                    histories=[]
                    for phase,dt,stride in [('c','.000001',10),('h','.0000005',20)]:
                        oldtag='spr_pulse_nopen_r1' if nopen else 'spr_pulse_r1';oldname=f'{oldtag}_{geometry}_s{mode}_{phase}'
                        name=f'{tag}_{"np" if nopen else "std"}_{geometry}_s{mode}_{phase}'
                        definition=TESTS/'configs'/(name+'_Def.xml');generated=TESTS/'outputs'/(name+'_input');out=TESTS/'outputs'/name
                        assert not any(x.exists() for x in (definition,generated,out))
                        root=ET.parse(TESTS/'configs'/(oldname+'_Def.xml')).getroot()
                        if nopen:
                            initial=root.find('casedef/initials')
                            if initial is None:initial=ET.SubElement(root.find('casedef'),'initials')
                            ET.SubElement(initial,'move',mkfluid='0',x='-.003',y='0',z='-.003',comment='Same initial near-wall position as retained CPU pulse; not a new physical correction')
                        ET.indent(root,space='  ')
                        with definition.open('x',encoding='utf8') as stream:stream.write('<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root,encoding='unicode')+'\n')
                        prefix=generated/name;generated.mkdir();log=TESTS/'logs'/(name+'.log')
                        with (TESTS/'logs'/(name+'.gencase.log')).open('xb') as stream:
                            subprocess.run([str(REPO/'bin/windows/GenCase_win64.exe'),str(definition.with_suffix('')),str(prefix),'-save:all'],stdout=stream,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
                        command=[str(exe),str(int(Decimal('.002')/Decimal(dt))),str(stride),'-gpu','-stable',str(prefix),str(out),'-dirdataout','data','-sv:none']
                        with log.open('xb') as stream:child=subprocess.run(command,cwd=exe.parent,stdout=stream,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
                        assert child.returncode==0,(name,'runtime failure')
                        done=json.loads((out/'pulse_complete.json').read_text());assert done['completed'] and done['max_fixed_dt_minus_mechanical_limit_s']<=0
                        a=pd.read_csv(out/'pulse.csv',float_precision='round_trip').sort_values(['step','id']).reset_index(drop=True)
                        cpu=pd.read_csv(TESTS/'outputs'/oldname/'pulse.csv',float_precision='round_trip').sort_values(['step','id']).reset_index(drop=True)
                        assert np.isfinite(a.to_numpy()).all() and a.rho.gt(0).all() and a.kplastic.eq(0).all()
                        assert a.z.gt(0).all() and (a.x.gt(0).all() if geometry=='corner2' else (np.cos(np.pi/6)*a.x+.5*a.z).gt(0).all())
                        energy=pd.read_csv(out/'energy.csv');ratio=float(energy.total_J_m.max()/energy.total_J_m.iloc[0]);assert ratio<=1.1
                        cross=difference(a,cpu);cross.update(name=name);result['cpu_gpu'].append(cross);assert cross['passed'],cross
                        result['runs'].append(dict(name=name,no_pen=nopen,slip=mode,exit_code=0,owned_exited=True,completion=done,energy_ratio_max=ratio,definition=bound(definition),
                            cpu_reference=bound(TESTS/'outputs'/oldname/'pulse.csv'),outputs=[bound(p) for p in out.iterdir() if p.is_file()]+[bound(log)]))
                        histories.append(a);print(name,'CPU/GPU',cross['pressure_rms_max_pa'],cross['material_displacement_max_mm'],flush=True)
                    pair=difference(*histories);pair.update(no_pen=nopen,geometry=geometry,slip=mode);result['half'].append(pair);assert pair['passed'],pair
                    print('HALF',pair,flush=True)
        result['passed']=True
    finally:
        with receipt.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)


if __name__=='__main__':main()
