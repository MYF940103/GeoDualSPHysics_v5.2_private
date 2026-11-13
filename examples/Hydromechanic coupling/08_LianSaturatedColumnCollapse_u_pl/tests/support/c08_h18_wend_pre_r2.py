"""Use the current installed notifier; reuse the reviewed r1 numerical owner."""
import argparse
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
import c08_h18_wend_pre_r1 as owner

T,L=owner.T,owner.L
NOTE=T/'notes/c08_h18_wend_pre_r2.md'
original_context=owner.build_context
original_queue=owner.queue_once
original_note=owner.NOTE

def notifier_path():
    found=shutil.which('codex')
    if found and Path(found).is_file():return Path(found).resolve()
    installed=list((Path.home()/'.vscode/extensions').glob('openai.chatgpt-*/bin/windows-x86_64/codex.exe'))
    return max(installed,key=lambda p:p.stat().st_mtime_ns) if installed else None

notifier=notifier_path()
owner.need(notifier is not None,'Current installed codex command is unavailable; no solver started')
owner.CODEX=notifier
owner.NOTE=NOTE

def paths(group):
    owner.need(group=='psi0','Only the separately admitted psi0 source is allowed')
    tag='c08_h18_wend_psi0_pre_r2'
    return tag,T/'outputs'/tag,T/'configs'/(tag+'_Def.xml'),T/'configs'/(tag+'_GPU.bat'),L/(tag+'.prepare.json'),L/(tag+'.admission.json'),L/(tag+'.run.json')

def context():
    b,program,before,runtime=original_context()
    before += [owner.stat(Path(__file__)),owner.stat(original_note)]
    return b,program,before,runtime

owner.paths=paths
owner.build_context=context

def queue_once(tag,rp,group):
    current=notifier_path()
    if current is not None:owner.CODEX=current
    # Original code records one attempt/error, even if no executable remains.
    return original_queue(tag,rp,group)

owner.queue_once=queue_once

def prepare(group):
    tag,out,config,bat,prep,ad,rp=paths(group)
    owner.need(not any(p.exists() for p in (out,config,bat,prep)),'Existing r2 preparation or output is protected')
    b,program,before,runtime=context()
    tree=owner.input_tree(group)
    with config.open('xb') as f:f.write(ET.tostring(tree,encoding='utf-8',xml_declaration=True)+b'\n')
    owner.check_input(config,group)
    old=T/'configs/c08_h18_wend_psi0_pre_r1_Def.xml'
    owner.need(owner.signature(ET.parse(old).getroot())==owner.signature(tree),'r2 must retain the exact reviewed Wendland input')
    before.append(owner.stat(old))
    body='@echo off\r\nsetlocal\r\nset "PYTHON=D:\\anaconda3\\python.exe"\r\nif not exist "%PYTHON%" set "PYTHON=python"\r\n"%PYTHON%" -X utf8 -B "%~dp0..\\support\\c08_h18_wend_pre_r2.py" run --group psi0 --execution-authorized --notify\r\nset "EC=%ERRORLEVEL%"\r\nif not "%~1"=="--unattended" pause\r\nexit /b %EC%\r\n'
    with bat.open('xb') as f:f.write(body.encode('ascii'))
    owner.verify(before)
    owner.save(prep,dict(stage=tag+'.prepare',passed=True,group=group,GenCase_invocations=0,solver_invocations=0,reader_invocations=0,physical_acceptance=False,input_xml=owner.stat(config),test_BAT=owner.stat(bat),program=owner.stat(program),source_build=owner.stat(owner.BUILD),source_capture=b['source_capture'],source_archive=b['source_archive'],material=owner.material(group),kernel=2,kernel_name='Wendland',outputs=[owner.stat(config),owner.stat(bat)],consumed=before,consumed_stats_unchanged=True,notifier_program_at_preparation=owner.stat(owner.CODEX),old_r1_physical_solver_invocations=0))
    print('WENDLAND_R2_PREPARED',tag,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','run'))
    parser.add_argument('--group',choices=('psi0',),required=True)
    parser.add_argument('--execution-authorized',action='store_true')
    parser.add_argument('--notify',action='store_true')
    a=parser.parse_args()
    owner.need(a.execution_authorized and not(a.action=='prepare' and a.notify),'Root review and explicit single action required')
    if a.action=='prepare':prepare(a.group)
    else:raise SystemExit(0 if owner.run(a.group,a.notify) else 1)
