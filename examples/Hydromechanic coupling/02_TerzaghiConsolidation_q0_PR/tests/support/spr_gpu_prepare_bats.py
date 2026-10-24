"""Clickable GPU companion reproductions; no existing XML/BAT/output is changed."""
import json
import xml.etree.ElementTree as ET
from spr_planes_run import TESTS,bound


def main():
    receipt=TESTS/'logs/spr_gpu_reproduction_bats_r1.json';assert not receipt.exists();entries=[]
    definitions=[]
    for geometry in ('corner2','wedge2','edge3'):
        source='spr_planes_r4_rel' if geometry=='wedge2' else 'spr_planes_r3_rel'
        for slip in (1,2,3):definitions.append((f'{source}_{geometry}_s{slip}','spr_gpu_planes_Release_op1/spr_gpu_planes.exe',False))
    for tag in ('spr_gpu_pulse_r1','spr_gpu_nopen_pulse_r2'):
        r=json.loads((TESTS/'logs'/(tag+'.check.json')).read_text())
        for run in r['runs']:definitions.append((run['name'],'spr_gpu_pulse_Release_op1/spr_gpu_pulse.exe',True))
    for name,binary,pulse in definitions:
        definition=TESTS/'configs'/(name+'_Def.xml');assert definition.exists()
        exe=TESTS/'outputs'/binary;assert exe.exists();extra=''
        if pulse:
            dt=float(ET.parse(definition).find("execution/parameters/parameter[@key='DtFixed']").get('value'))
            extra=str(round(.002/dt))+' '+str(round(.00001/dt))+' '
        path=TESTS/'configs'/('x'+name+'_win64_GPU.bat');assert not path.exists()
        manual=name+'_gpu_manual_r1'
        lines=['@echo off','setlocal EnableDelayedExpansion','pushd "%~dp0\\..\\.."','',
            'rem Bounded GPU companion reproduction, not formal consolidation or theory acceptance.',
            'rem Uses the retained verified companion; CSV/JSON only, combined plots are an offline step.',
            'set name='+manual,'set dirout=tests\\outputs\\%name%','set dirinput=tests\\outputs\\%name%_input',
            'set dirbin=../../../bin/windows','set gencase="%dirbin%/GenCase_win64.exe"',
            'set diagnostic="tests/outputs/'+binary+'"','if exist %dirout% goto fail','if exist %dirinput% goto fail',
            '%gencase% tests/configs/'+name+'_Def %dirinput%/%name% -save:all','if not "%ERRORLEVEL%"=="0" goto fail',
            '%diagnostic% '+extra+'-gpu -stable %dirinput%/%name% %dirout% -dirdataout data -sv:none',
            'if not "%ERRORLEVEL%"=="0" goto fail','popd','exit /b 0',':fail',
            'echo Diagnostic refused or failed. Existing results were not removed.','popd','exit /b 1','']
        with path.open('x',encoding='utf8') as stream:stream.write('\n'.join(lines))
        entries.append(dict(bat=bound(path),definition=bound(definition),executable=bound(exe)))
    with receipt.open('x',encoding='utf8') as stream:json.dump(dict(entries=entries,count=len(entries),solver_started=False),stream,indent=2)
    print('Prepared',len(entries),'GPU XML companion BAT entries; no solver started')


if __name__=='__main__':main()
