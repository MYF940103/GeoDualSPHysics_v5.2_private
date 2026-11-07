"""Explicit local r3 GPU receiver from the untouched server r2 elastic PRE. No restart/chain."""
import argparse,csv,ctypes,datetime,io,json,os,re,subprocess,time,xml.etree.ElementTree as ET
from ctypes import wintypes as w
from pathlib import Path
from xml.sax.saxutils import escape
import psutil
T=Path(__file__).resolve().parents[1];C=T.parent;L=T/'logs';TAG='upl_c08_resume_r1'
SOURCE=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out'
PRE=SOURCE/'data/Part_1000.bi4';RUNTIME=C/'support/runtime_r3';MANIFEST=C/'support/server_manifest_r3.json'
K=ctypes.WinDLL('kernel32',use_last_error=True)
K.GetProcessTimes.argtypes=[w.HANDLE,ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME)]
K.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]
K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,v):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(v,f,indent=2);f.write('\n')
def verify(rows):
    for e in rows:assert stat(e['path'])==e,'Consumed file changed: '+e['path']
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def summary(p):
    text=Path(p).read_text(encoding='utf-8-sig');header=text.splitlines()[0]
    assert re.match(r'^#?RunName[;,]',header),'Unsupported Run.csv header'
    if text.startswith('#'):text=text[1:]
    rows=list(csv.DictReader(io.StringIO(text),delimiter=';' if ';' in header else ','));assert len(rows)==1,'One Run.csv row required';return rows[0]
def source_bindings():
    r=summary(SOURCE/'Run.csv');text=(SOURCE/'Run.out').read_text(encoding='utf-8-sig')
    assert int(r['Steps'])==4000000 and int(r['PartFiles'])==1001 and int(r['PartsOut'])==0 and int(r['Np'])==7060 and int(r['Nbound'])==int(r['Nfixed'])==2060,'Source scheduling/registry differs'
    assert 'Finished execution (code=0).' in text and 'MaterialReturn: 1=ConsistentDev' in text and 'event_completed_step=4000000 release_mkbound=2' in text,'Actual old source summary/log differs'
    assert PRE.is_file() and sorted(p.name for p in (SOURCE/'data').glob('Part_*.bi4'))==['Part_%04d.bi4'%i for i in range(1001)],'Complete original source filename sequence required'
    # Scheduling evidence only. The production native loader independently validates this PRE.
    m=read(MANIFEST);program=RUNTIME/'DualSPHysics5.2_GEO_win64.exe';built=m['programs']['GPU'];verify([built])
    a=stat(program);assert (a['bytes'],a['mtime_ns'])==(built['bytes'],built['mtime_ns']),'runtime_r3 GPU does not match its frozen program stat'
    return [stat(p) for p in (PRE,SOURCE/'Run.csv',SOURCE/'Run.out',SOURCE/'data/Part_Head.ibi4',MANIFEST,Path(__file__),T/'notes'/(TAG+'.md'))]+[stat(p) for p in sorted(RUNTIME.iterdir()) if p.is_file()]+[built,m['builds']['Release'],m['compiled_source_archive']]
def invoke(tag,program,args,bindings):
    start=L/(tag+'.start.json');call=L/(tag+'.call.json');log=L/(tag+'.log');assert not any(p.exists() for p in (start,call,log)),'Retained invocation/partial output protected'
    exact=os.path.normcase(os.path.abspath(program));target={os.path.normcase(os.path.abspath(x)) for x in map(str,args) if str(T/'outputs') in x}
    for q in psutil.process_iter(['exe','cmdline']):
        try:
            e=q.info['exe'];av=q.info['cmdline'] or []
            assert not ((e and os.path.normcase(os.path.abspath(e))==exact) or any(os.path.normcase(os.path.abspath(x)) in target for x in av)),'Same exact program/output already active'
            if '-gpu:0' in args:assert not any(x.lower().startswith('-gpu') for x in av[1:]),'Another GPU solver is active; no process is stopped'
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    verify(bindings);owner=psutil.Process();begin=utc();wall=time.monotonic();rc=wx=None;child=None;failure=None
    try:
        with log.open('xb') as f:
            p=subprocess.Popen([str(program),*map(str,args)],cwd=C,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
            c,e,k,u=w.FILETIME(),w.FILETIME(),w.FILETIME(),w.FILETIME();assert K.GetProcessTimes(int(p._handle),ctypes.byref(c),ctypes.byref(e),ctypes.byref(k),ctypes.byref(u))
            n=w.DWORD(32768);buf=ctypes.create_unicode_buffer(n.value);assert K.QueryFullProcessImageNameW(int(p._handle),0,buf,ctypes.byref(n))
            child=dict(pid=p.pid,created_epoch=((c.dwHighDateTime<<32)|c.dwLowDateTime)/1e7-11644473600,exe=buf.value,argv=[str(program),*map(str,args)],argv_source='exact_direct_owned_Popen')
            save(start,dict(stage=tag,owner=dict(pid=owner.pid,created_epoch=owner.create_time()),child=child,program=stat(program),consumed=bindings));print('START',tag,p.pid,flush=True)
            rc=p.wait();v=w.DWORD();assert K.GetExitCodeProcess(int(p._handle),ctypes.byref(v));wx=v.value
    except BaseException as ex:failure=repr(ex)
    d=dict(stage=tag,child=child,program=stat(program),arguments=list(map(str,args)),actual_Popen_wait_exit=rc,actual_Win32_exit=wx,started_utc=begin,ended_utc=utc(),elapsed_s=time.monotonic()-wall,invocation_failure=failure,log=stat(log) if log.exists() else None)
    save(call,d);assert rc==wx==0 and failure is None,'Actual program failed; preserve source/partial receiver and inspect '+str(call)
    verify(bindings);return stat(call)
def paths(group,mode):
    name=TAG+'_'+group+'_GPU_'+mode
    return name,T/'configs'/(name+'_Def.xml'),T/'outputs'/name,L/(name+'.prepare.json'),L/(name+'.run.json')
def prepare(group,mode):
    name,config,out,receipt,runrecord=paths(group,mode);assert not any(p.exists() for p in (config,out,receipt,runrecord)),'Fresh configuration/seed/output required'
    template=C/('CaseLianSaturatedColumnCollapse_'+group+'_shared_r3_Def.xml');bindings=source_bindings()+[stat(template)];result=dict(stage=name,passed=False,GenCase_invocations=0,solver_invocations=0,native_decoder_invocations=0,source_PRE_certified_by_this_script=False,SHA_scans=0)
    try:
        text=template.read_text(encoding='utf-8');assert text.count('__GRAVITY_PRELOAD_STATE__')==1
        text=text.replace('__GRAVITY_PRELOAD_STATE__',escape(str(PRE.resolve()),{'"':'&quot;'}))
        if mode=='short':
            old='10 s actual gravity preload plus 3 s after release; no PART restart';assert text.count(old)==1
            text=text.replace(old,'Short receiver: stop at global completed4040000; TimeMax13 and all numerical values retained')
        a,b=ET.fromstring(template.read_text(encoding='utf-8')),ET.fromstring(text)
        assert len(list(a.iter()))==len(list(b.iter()))
        for x,y in zip(a.iter(),b.iter()):
            xa={k:v for k,v in x.attrib.items() if 'comment' not in k};ya={k:v for k,v in y.attrib.items() if 'comment' not in k}
            if x.tag=='gravitypreload':xa['statefile']=str(PRE.resolve())
            assert x.tag==y.tag and xa==ya,'Unexpected physical/XML change'
        assert b.find('./execution/special/soils/MaterialReturn') is None,'Only unified r3 template allowed'
        with config.open('x',encoding='utf-8',newline='\r\n') as f:f.write(text)
        bindings.append(stat(config));prefix=out/name;result['GenCase_invocations']=1
        call=invoke(name+'.gencase',RUNTIME/'GenCase_win64.exe',[str(config.with_suffix('')),str(prefix),'-save:all'],bindings)
        seed=[stat(str(prefix)+suffix) for suffix in ('.xml','.bi4','_Normals.nbi4')];verify(bindings)
        result.update(passed=True,config=stat(config),template=stat(template),source_pre_file=stat(PRE),source_summary=summary(SOURCE/'Run.csv'),seed=seed,GenCase_call=call,output=str(out),case_prefix=str(prefix),expected_global_completed_steps=4040000 if mode=='short' else 5200000,expected_new_updates=40000 if mode=='short' else 1200000,planned_TimeMax=13.,dt_s=.0000025,output_interval_s=.01,source_clock_must_be_imported_not_reset=True,consumed=bindings)
    except Exception as ex:result['first_failure']=str(ex)
    save(receipt,result);print(json.dumps(dict(stage=name,prepared=result['passed'],first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
def run(group,mode):
    name,config,out,prepared,record=paths(group,mode);assert not record.exists() and not (out/'Run.out').exists() and not (out/'data').exists(),'Retained/partial solver output is never retried'
    p=read(prepared);assert p['passed'];bindings=p['consumed']+p['seed']+[stat(prepared)];verify(bindings)
    end=4040000 if mode=='short' else 5200000;result=dict(stage=name,passed=False,backend='GPU',window=mode,output=str(out),program=stat(RUNTIME/'DualSPHysics5.2_GEO_win64.exe'),source_build=read(MANIFEST)['builds']['Release'],source_pre_file=stat(PRE),input_xml=p['seed'][0],solver_invocations=0,native_decoder_invocations=0,native_review_pending=True,physical_acceptance=False,SHA_scans=0)
    try:
        result['solver_invocations']=1;call=invoke(name+'.solver',RUNTIME/'DualSPHysics5.2_GEO_win64.exe',['-gpu:0','-stable','-mdbc_freeslip',p['case_prefix'],str(out),'-dirdataout','data','-svres','-nsteps:'+str(end)],bindings)
        text=(out/'Run.out').read_text(encoding='utf-8-sig');r=summary(out/'Run.csv');assert 'Finished execution (code=0).' in text and int(r['Steps'])==end,'Actual receiver did not reach the admitted global endpoint'
        assert int(r['Np'])==7060 and int(r['Nfixed'])==int(r['Nbound'])==2060 and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'Original registry/no-loss summary differs'
        imports=[x for x in text.splitlines() if 'GravityPreload: state imported file=' in x];releases=[x for x in text.splitlines() if 'GravityPreload: phase=released' in x]
        assert len(imports)==len(releases)==1 and 'GravityPreload: source material law=legacy MR1 ElasticV1;' in text,'Actual source law/import/one-shot release differs'
        assert 'retired=260; damping=OFF Shepard=OFF FreeSeepage=ON.' in releases[0],'Release/stage flags differ'
        clocks=[]
        for line in (imports[0],releases[0]):
            m=re.search(r'actual=([^ ]+) completed_step=(\d+)',line);assert m and int(m[2])==4000000;clocks.append(float(m[1]))
        scalar=0.
        for _ in range(4000000):scalar+=.0000025
        assert clocks[0]==clocks[1]==scalar,'Actual imported scalar clock was reset/changed'
        frames=sorted(p.name for p in (out/'data').glob('Part_*.bi4'));assert frames==['Part_%04d.bi4'%i for i in range(int(r['PartFiles']))],'Actual saved frame membership differs'
        verify(bindings);result.update(passed=True,actual_call=call,actual_source_time_from_loader=clocks[0],initial_completed_step=4000000,actual_steps=int(r['Steps']),saved_frames=int(r['PartFiles']),actual_global_completed_steps=int(r['Steps']),actual_new_updates=int(r['Steps'])-4000000,summary=r,actual_import_line=imports[0],actual_release_line=releases[0],Run_out=stat(out/'Run.out'),Run_csv=stat(out/'Run.csv'),source_pre_file=stat(PRE),seed=p['seed'],consumed=bindings)
    except Exception as ex:result['first_failure']=str(ex)
    callpath=L/(name+'.solver.call.json')
    if callpath.exists():
        actual=read(callpath);result.update(actual_exit=actual['actual_Popen_wait_exit'],actual_Win32_exit=actual['actual_Win32_exit'],actual_call=stat(callpath),solver_invocations=int(actual['child'] is not None))
    else:result['solver_invocations']=0
    save(record,result);print(json.dumps(dict(stage=name,run_metadata_passed=result['passed'],first_failure=result.get('first_failure'),native_review_pending=True)),flush=True);return 0 if result['passed'] else 1
def main():
    a=argparse.ArgumentParser();a.add_argument('action',choices=['prepare-short','run-short','prepare-full','run-full']);a.add_argument('--group',choices=['psi0','psi2p5','psim5'],default='psi0');a.add_argument('--execution-authorized',action='store_true');p=a.parse_args();assert p.execution_authorized,'Root full read and explicit execution authorization required'
    operation,mode=p.action.split('-');raise SystemExit(prepare(p.group,mode) if operation=='prepare' else run(p.group,mode))
if __name__=='__main__':main()
