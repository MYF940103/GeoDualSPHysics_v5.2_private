"""Four aligned CPU 2-D short runs. Formal case files are read-only."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET

TESTS=Path(__file__).resolve().parents[1]
CASE=TESTS.parent
REPO=CASE.parents[2]
TAG="spr_yao_short_r1"
VARIANTS=("auto_off","faces_off","faces_on","faces_half")


def bound(path):
    path=Path(path).resolve()
    with path.open('rb') as stream:return dict(path=str(path),sha256=hashlib.file_digest(stream,'sha256').hexdigest().upper())


def render(variant):
    root=ET.parse(CASE/'CaseYao2DConsolidation_PR_Def.xml').getroot()
    parameters=root.find('execution/parameters')
    def parameter(key,value):
        item=parameters.find("parameter[@key='"+key+"']")
        if item is None:item=ET.SubElement(parameters,'parameter',key=key,comment='Independent CPU SPR boundary short test')
        item.set('value',value)
    dt='.00001' if variant=='faces_half' else '.00002'
    for key,value in [('SavePosDouble','1'),('SoilStressRateGradCorr','1'),('SoilBoundaryDerivativeSPR','1' if variant in ('faces_on','faces_half') else '0'),('SoilHourglassXi','0'),('NoPenetration','0'),('DtIni',dt),('DtFixed',dt),('TimeMax','.02'),('TimeOut','.001')]:parameter(key,value)
    hydro=root.find('execution/special/hydromechanics')
    for key,value in [('PoreCompressionSourceMode','PairDivergence'),('PoreCompressionGradCorr','1')]:
        item=hydro.find(key)
        if item is None:item=ET.SubElement(hydro,key,comment='Aligned corrected-gradient control for the SPR comparison')
        item.set('value',value)
    if variant!='auto_off':
        main=root.find('casedef/geometry/commands/mainlist');boxes=main.findall('drawbox');assert len(boxes)==3
        for i,box in enumerate(boxes):main.insert(list(main).index(box),ET.Element('setmkbound',mk=str(i)))
        initialize=ET.Element('initialize')
        for mk,point,normal in [('0',(0,0,0),(0,0,1)),('1',(-10,0,0),(1,0,0)),('2',(10,0,0),(-1,0,0))]:
            plane=ET.SubElement(initialize,'boundnormal_plane',mkbound=mk)
            ET.SubElement(plane,'point',**dict(zip('xyz',map(str,point))));ET.SubElement(plane,'normal',**dict(zip('xyz',map(str,normal))))
            ET.SubElement(plane,'maxdisth',v='0',comment='All native wall layers; outer unused layers also have defined normals')
            ET.SubElement(plane,'clear',v='true')
        root.find('execution/special').insert(0,initialize)
    ET.indent(root,space='    ')
    return '<?xml version="1.0" encoding="UTF-8" ?>\n'+ET.tostring(root,encoding='unicode')+'\n'


def batch(name):
    return '\n'.join(['@echo off','setlocal EnableDelayedExpansion','pushd "%~dp0\\..\\.."','',
      'rem Independent short CPU test: preserve formal files and retained outputs.',
      'rem Native BI4 output only; four-way comparison is performed by tests/scripts/spr_yao_review.py.',
      'set name='+name,'set dirout=tests\\outputs\\%name%','set diroutdata=%dirout%\\data',
      'set dirbin=../../../bin/windows','set gencase="%dirbin%/GenCase_win64.exe"',
      'set dualsphysicscpu="%dirbin%/DualSPHysics5.2CPU_win64.exe"','if exist %dirout% goto fail',
      '%gencase% tests/configs/%name%_Def %dirout%/%name% -save:all','if not "%ERRORLEVEL%"=="0" goto fail',
      '%dualsphysicscpu% -cpu -ompthreads:8 %dirout%/%name% %dirout% -dirdataout data -svres -svextraparts:1',
      'if not "%ERRORLEVEL%"=="0" goto fail','popd','exit /b 0',':fail',
      'echo Test refused or failed. Retained outputs were not deleted.','popd','exit /b 1',''])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--run',action='store_true');args=parser.parse_args()
    state=TESTS/'logs'/(TAG+'.status.json')
    if args.prepare:
        assert not state.exists()
        for variant in VARIANTS:
            name=TAG+'_'+variant
            for path,text in [(TESTS/'configs'/(name+'_Def.xml'),render(variant)),(TESTS/'configs'/('x'+name+'_win64_CPU.bat'),batch(name))]:
                with path.open('x',encoding='utf8') as stream:stream.write(text)
        print('Prepared four XML/BAT pairs; no solver started');return
    assert args.run and not state.exists()
    inputs=[bound(__file__),bound(CASE/'CaseYao2DConsolidation_PR_Def.xml')]
    inputs += [bound(REPO/'src/source'/x) for x in ('JSphCpu.cpp','JSphCpu.h','JSphCpuSingle.cpp')]
    inputs += [bound(REPO/'bin/windows'/x) for x in ('DualSPHysics5.2CPU_win64.exe','GenCase_win64.exe')]
    for variant in VARIANTS:
        name=TAG+'_'+variant
        inputs += [bound(TESTS/'configs'/(name+'_Def.xml')),bound(TESTS/'configs'/('x'+name+'_win64_CPU.bat'))]
        assert not (TESTS/'outputs'/name).exists()
    record=dict(status='running',started_utc=datetime.now(timezone.utc).isoformat(),inputs=inputs,runs=[])
    def save():state.write_text(json.dumps(record,indent=2),encoding='utf8')
    save()
    try:
        for variant in VARIANTS:
            name=TAG+'_'+variant;record['active_variant']=variant;save();log=TESTS/'logs'/(name+'.log')
            with log.open('xb') as stream:
                child=subprocess.Popen([os.environ['ComSpec'],'/d','/c',str(TESTS/'configs'/('x'+name+'_win64_CPU.bat'))],cwd=CASE,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                record['owned_wrapper_pid']=child.pid;save();code=child.wait()
            assert code==0,(name,'solver/BAT failure')
            out=TESTS/'outputs'/name
            record['runs'].append(dict(variant=variant,exit_code=code,owned_exited=True,log=bound(log),outputs=[bound(p) for p in out.rglob('*') if p.is_file()]))
            save();print(name+' completed',flush=True)
        for item in inputs:assert bound(item['path'])['sha256']==item['sha256']
        record.update(status='completed_pending_review',finished_utc=datetime.now(timezone.utc).isoformat())
    except Exception as error:
        record.update(status='rejected_or_interrupted',error=repr(error));raise
    finally:save()


if __name__=='__main__':main()
