"""Prepare only the fresh epsilon.25/n3 Def and self-locating BAT; never launch a program."""
import argparse,json,xml.etree.ElementTree as ET
from pathlib import Path

T=Path(__file__).resolve().parents[1];C=T.parent;TAG='upl_c08_as025_window_GPU_r1'
ROOT=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r6_Def.xml'
PRE=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4'
OWNER=T/'support/upl_c08_as025_window_r1.py';NOTE=T/'notes/upl_c08_as025_window_r1.md'
CONFIG=T/'configs'/(TAG+'_Def.xml');BAT=T/'configs'/('x'+TAG+'_win64_GPU.bat')

def need(value,message):
    if not value:raise RuntimeError(message)
def stat(path):
    path=Path(path).resolve();s=path.stat();return dict(path=str(path),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def signature(n):return n.tag,tuple(sorted((k,v) for k,v in n.attrib.items() if k!='comment' and not k.endswith('_comment'))),(n.text or '').strip(),tuple(signature(q) for q in n)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--prepare-only',action='store_true');a=ap.parse_args();need(a.prepare_only,'Root full-read before explicit prepare-only action')
    need(all(p.is_file() for p in (ROOT,PRE,OWNER,NOTE)),'Retained root/PRE and reviewed author files required')
    need(not CONFIG.exists() and not BAT.exists() and not (T/'outputs'/TAG).exists(),'Existing configuration/BAT/output protected')
    need(not any(p.name!=TAG+'.admission.json' for p in (T/'logs').glob(TAG+'.*')),'Existing actual job/partial evidence protected')
    original=ROOT.read_bytes().decode('utf-8-sig');text=original
    def replace(old,new):
        nonlocal text
        need(text.count(old)==1,'Unique retained template anchor required: '+old);text=text.replace(old,new,1)
    state=str(PRE.resolve()).replace('&','&amp;').replace('"','&quot;')
    replace('<!-- r6 psi0-only diagnostic: CompletedOnly free-seepage, AS epsilon0.2 exponent3; same frozen r5 solver and original certified GPU PRE. Full3s remains unreviewed; other groups stay locked. -->','<!-- Bounded psi0 diagnostic: AS epsilon0.25 exponent3, CompletedOnly, original certified GPU PRE; only0.30s after release, not physical acceptance. -->')
    replace('statefile="__GRAVITY_PRELOAD_STATE__"','statefile="'+state+'"')
    replace('comment="Launcher substitutes this backend certified PRE path; loader verifies complete state and contract"','comment="Original certified r2GPU PRE; loader verifies full state/contract, no source recomputation"')
    replace('<parameter key="ArtificialStressCoef" value="0.2" comment="Explicit existing Bui artificial-stress coefficient" />','<parameter key="ArtificialStressCoef" value="0.25" comment="Single coefficient0.25 diagnostic from0.2; exponent3/hdp1.2/CompletedOnly unchanged; not an accepted repair" />')
    replace('<parameter key="ArtificialStressExp" value="3" comment="Single exponent3 diagnostic; epsilon0.2 and CompletedOnly policy unchanged" />','<parameter key="ArtificialStressExp" value="3" comment="Retained exponent3; only AS coefficient0.2 to0.25 changes released physics" />')
    replace('<parameter key="TimeMax" value="13.0" comment="10 s actual gravity preload plus 3 s after release; no PART restart" units_comment="seconds" />','<parameter key="TimeMax" value="10.30" comment="Bounded0.30s after imported PRE; owner caps global4120000, no source recomputation" units_comment="seconds" />')
    want=ET.fromstring(original);want.find('execution/special/gravitypreload').set('statefile',str(PRE.resolve()))
    for key,value in (('ArtificialStressCoef','0.25'),('ArtificialStressExp','3'),('TimeMax','10.30'),('TimeOut','0.01')):
        nodes=want.findall("execution/parameters/parameter[@key='"+key+"']");need(len(nodes)==1,'Unique original parameter required');nodes[0].set('value',value)
    need(signature(ET.fromstring(text))==signature(want),'Prepared full Def changed outside the declared source/coefficient/end scope')
    bat='\r\n'.join(('@echo off','setlocal','set "PYTHON=D:\\anaconda3\\python.exe"','if not exist "%PYTHON%" set "PYTHON=python"','"%PYTHON%" -X utf8 -B "%~dp0..\\support\\upl_c08_as025_window_r1.py" --execution-authorized --notify','set "EC=%ERRORLEVEL%"','if not "%~1"=="--unattended" pause','exit /b %EC%',''))
    with CONFIG.open('xb') as f:f.write(text.encode('utf-8'))
    with BAT.open('xb') as f:f.write(bat.encode('ascii'))
    need(ROOT.read_bytes().decode('utf-8-sig')==original,'Retained root changed during preparation')
    print(json.dumps(dict(prepared_only=True,configuration=stat(CONFIG),BAT=stat(BAT),owner=stat(OWNER),note=stat(NOTE),admission_written=False,GenCase_invocations=0,solver_invocations=0,build_invocations=0,native_invocations=0)),flush=True)
    return 0
if __name__=='__main__':raise SystemExit(main())
