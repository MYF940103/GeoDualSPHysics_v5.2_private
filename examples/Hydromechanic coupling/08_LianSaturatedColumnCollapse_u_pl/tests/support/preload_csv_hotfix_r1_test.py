"""Read-only real CSV checks and small parser fixtures; no physical solver."""
import csv,io,json,shutil,subprocess,time,zipfile
from pathlib import Path
T=Path(__file__).resolve().parents[1];C=T.parent;TAG='preload_csv_hotfix_r1'
O=T/'outputs'/TAG;CHECK=T/'logs'/(TAG+'.check.json');SCRIPT=C/'support/check_lian_preload_schedule_r1.ps1'
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def invoke(name,args,expected):
    log=O/(name+'.log');start=time.monotonic()
    with log.open('xb') as f:
        p=subprocess.Popen(args,cwd=C,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        rc=p.wait()
    record=dict(name=name,arguments=args,pid=p.pid,actual_exit=rc,expected_exit=expected,elapsed_s=time.monotonic()-start,log=stat(log))
    calls.append(record)
    if rc!=expected:raise RuntimeError('Unexpected parser/BAT result: '+name)
def ps(name,folder,expected,*extra):
    invoke(name,['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(SCRIPT),'-SourceOut',str(folder),*extra],expected)
def fixture(name,text,part=True):
    p=O/name;p.mkdir();(p/'Run.csv').write_text(text,encoding='utf-8')
    if part:
        (p/'data').mkdir();(p/'data/Part_1000.bi4').write_bytes(b'Parser fixture only; not a native PRE file.\n')
    return p
assert not O.exists() and not CHECK.exists(),'Prior tests protected'
source=T/'outputs/upl_prestress10_CPU_r1';gpu=T/'outputs/upl_material_release_native_r1_source_GPU_release'
protected=[stat(p) for p in (SCRIPT,source/'Run.csv',source/'data/Part_1000.bi4',gpu/'Run.csv',gpu/'data/Part_0021.bi4',C/'support/LianCollapse_upl_win64_r2.zip',C/'support/LianCollapse_upl_win64_r3.zip')]
O.mkdir();calls=[];passed=False;failure=None
try:
    # Reproduce the original header/comment bug using a real closed 10-s CSV.
    invoke('original_import_failure',['powershell','-NoProfile','-Command',"Import-Csv -LiteralPath '"+str(source/'Run.csv').replace("'","''")+"' -Delimiter ';' -ErrorAction Stop"],1)
    ps('actual_cpu_10s',source,0)
    ps('actual_gpu_short',gpu,0,'-ExpectedSteps','800','-ExpectedPartFiles','22','-ExpectedPrePart','Part_0021.bi4')
    ps('wrong_step_rejected',source,1,'-ExpectedSteps','3999999')
    text=(source/'Run.csv').read_text(encoding='utf-8-sig');lines=text.splitlines()
    ps('header_without_hash',fixture('without_hash',text.removeprefix('#')),0)
    reader=list(csv.reader(io.StringIO(text),delimiter=';'));s=io.StringIO();writer=csv.writer(s,delimiter=',',lineterminator='\n');writer.writerows(reader)
    ps('comma_header',fixture('comma',s.getvalue()),0)
    ps('missing_pre_rejected',fixture('missing_pre',text,False),1)
    ps('multiple_rows_rejected',fixture('multiple',text+lines[1]+'\n'),1)
    ps('unsupported_header_rejected',fixture('bad_header',text.replace('#RunName;','#Unexpected;',1)),1)
    # Exercise the double-click checker in a disposable package layout only.
    layout=O/'layout';(layout/'support').mkdir(parents=True)
    for p in (SCRIPT,C/'xCheckLianSaturatedColumnCollapse_preload_win64.bat'):
        shutil.copy2(p,layout/('support/'+p.name if p==SCRIPT else p.name))
    q=layout/'CaseLianSaturatedColumnCollapse_shared_preload_r3_GPU_out';(q/'data').mkdir(parents=True)
    (q/'Run.csv').write_text(text,encoding='utf-8');(q/'data/Part_1000.bi4').write_bytes(b'Parser fixture only, not native state.\n')
    invoke('double_click_checker',['cmd.exe','/d','/c',str(layout/'xCheckLianSaturatedColumnCollapse_preload_win64.bat'),'--unattended'],0)
    # Only the known :checksource block may differ from each immutable archive.
    for version in ('r2','r3'):
        leaf='support/run_lian_collapse_shared_'+version+'_win64.bat'
        with zipfile.ZipFile(C/('support/LianCollapse_upl_win64_'+version+'.zip')) as z:
            members=[n for n in z.namelist() if n.replace('\\','/').endswith(leaf)];assert len(members)==1
            old=z.read(members[0]);new=(C/leaf).read_bytes();a=old.index(b'\n:checksource\r\n');b=old.index(b'\n:exists',a)
            na=new.index(b'\n:checksource\r\n');nb=new.index(b'\n:exists',na)
            assert old[:a]==new[:na] and old[b:]==new[nb:],'Launcher changed outside the postcheck block'
    assert all(stat(p['path'])==p for p in protected),'Protected real inputs/archive changed'
    passed=True
except Exception as e:failure=str(e)
record=dict(stage=TAG,passed=passed,first_failure=failure,calls=calls,protected=protected,protected_stats_unchanged=all(stat(p['path'])==p for p in protected),solver_invocations=0,native_PRE_certification=False,fixture_PRE_files_are_deliberately_invalid=True,SHA_scans=0)
CHECK.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=passed,first_failure=failure,cases=len(calls)),indent=2))
if not passed:raise SystemExit(1)
