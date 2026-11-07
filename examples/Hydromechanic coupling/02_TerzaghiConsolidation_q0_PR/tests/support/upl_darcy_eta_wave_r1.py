"""Isolated Darcy-Eta A/B helper. One explicit action; no production edit or chaining."""
import argparse,ctypes,datetime,json,os,shutil,subprocess,time
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];R=T.parents[3];S=R/'src';L=T/'logs';TAG='upl_darcy_eta_wave_r1'
T08=T.parents[1]/'08_LianSaturatedColumnCollapse_u_pl/tests'
BUILD=T08/'logs/mdbc_partition_DebugCPU_r1.build.json'
CAPTURE=T08/'outputs/mdbc_partition_source_r1/source.json'
OUT=T/'outputs'/(TAG+'_build');RECEIPT=L/(TAG+'.build.json')
CPP=T/'support'/(TAG+'.cpp');NOTE=T/'notes'/(TAG+'.md')
SEED=T/'outputs/upl_p3_spatial_seed_r1_n32_c/CaseUplSpatial_n32_c'
K=ctypes.WinDLL('kernel32',use_last_error=True)
K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
K.GetProcessTimes.argtypes=[w.HANDLE,ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME)]
K.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]
def stat(p):
    p=Path(p).resolve();q=p.stat();return dict(path=str(p),bytes=q.st_size,mtime_ns=q.st_mtime_ns)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,v):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(v,f,indent=2);f.write('\n')
def verify(rows):
    for e in rows:assert stat(e['path'])==e,'Frozen binding changed: '+e['path']
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def argv_windows(line):
    shell=ctypes.WinDLL('shell32');shell.CommandLineToArgvW.argtypes=[w.LPCWSTR,ctypes.POINTER(ctypes.c_int)];shell.CommandLineToArgvW.restype=ctypes.POINTER(w.LPWSTR)
    n=ctypes.c_int();p=shell.CommandLineToArgvW('dummy '+line,ctypes.byref(n));assert p
    ans=[p[i] for i in range(1,n.value)];K.LocalFree.argtypes=[ctypes.c_void_p];K.LocalFree(p);return ans
def launch(tag,program,args,env=None):
    program=Path(program).resolve();start=L/(tag+'.start.json');call=L/(tag+'.call.json');log=L/(tag+'.log')
    assert not any(p.exists() for p in (start,call,log)),'Retained launch protected'
    exact=os.path.normcase(os.path.abspath(program));outputs={os.path.normcase(os.path.abspath(str(a))) for a in args if str(T/'outputs') in str(a)}
    for proc in psutil.process_iter(['pid','exe','cmdline']):
        try:
            e=proc.info['exe'];a=proc.info['cmdline'] or []
            assert not ((e and os.path.normcase(os.path.abspath(e))==exact) or any(os.path.normcase(os.path.abspath(x)) in outputs for x in a)),'Same isolated program/output is active'
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    owner=psutil.Process();started=utc();wall=time.monotonic();rc=wx=None;child=None;failure=None
    try:
        with log.open('xb') as f:
            p=subprocess.Popen([str(program),*map(str,args)],cwd=S/'VS',env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
            c,e,k,u=w.FILETIME(),w.FILETIME(),w.FILETIME(),w.FILETIME();assert K.GetProcessTimes(int(p._handle),ctypes.byref(c),ctypes.byref(e),ctypes.byref(k),ctypes.byref(u))
            size=w.DWORD(32768);buf=ctypes.create_unicode_buffer(size.value);assert K.QueryFullProcessImageNameW(int(p._handle),0,buf,ctypes.byref(size))
            child=dict(pid=p.pid,created_epoch=((c.dwHighDateTime<<32)|c.dwLowDateTime)/1e7-11644473600,exe=buf.value,argv=[str(program),*map(str,args)],argv_source='direct_owned_Popen_arguments')
            save(start,dict(stage=tag,owner=dict(pid=owner.pid,created_epoch=owner.create_time()),child=child,program=stat(program)))
            print('START',tag,p.pid,flush=True);rc=p.wait();code=w.DWORD();assert K.GetExitCodeProcess(int(p._handle),ctypes.byref(code));wx=code.value
    except BaseException as ex:failure=repr(ex)
    d=dict(stage=tag,program=stat(program),arguments=list(map(str,args)),child=child,actual_Popen_wait_exit=rc,actual_Win32_exit=wx,started_utc=started,ended_utc=utc(),elapsed_s=time.monotonic()-wall,invocation_failure=failure,log=stat(log) if log.exists() else None)
    save(call,d);assert rc==wx==0 and failure is None,'Actual tool/helper failure; preserve evidence: '+tag
    return stat(call)
def build():
    assert not OUT.exists() and not RECEIPT.exists(),'Fresh build required'
    b=read(BUILD);assert b['passed'] and b['non_main_objects']==86 and len(b['project_objects'])==87
    objs=b['project_objects'];verify(objs)
    source=[x for x in read(CAPTURE)['files'] if Path(x['path']).is_relative_to(S/'source')];verify(source)
    inter=Path(objs[0]['path']).parent;tlog=inter/'DualSPHysics.tlog';cllog=tlog/'CL.command.1.tlog';lklog=tlog/'link.command.1.tlog'
    lines=cllog.read_text(encoding='utf-16').splitlines();command=next(lines[i+1] for i,x in enumerate(lines[:-1]) if x.startswith('^') and Path(x[1:]).name.lower()=='jsphcpu.cpp')
    original_compile=argv_windows(command);assert Path(original_compile[-1]).name.lower()=='jsphcpu.cpp'
    original_link=argv_windows(' '.join(x for x in lklog.read_text(encoding='utf-16').splitlines() if not x.startswith('^')))
    seedfiles=[SEED.with_suffix(ext) for ext in ('.xml','.bi4')]
    bindings=[stat(p) for p in [BUILD,CAPTURE,cllog,lklog,CPP,NOTE,Path(__file__),*seedfiles]]+source+objs
    OUT.mkdir();private=OUT/'JSphCpu_eta0.cpp';raw=(S/'source/JSphCpu.cpp').read_bytes();old=b'/(rr2+double(Eta2))';assert raw.count(old)==1
    private.write_bytes(raw.replace(old,b'/rr2'));assert private.read_bytes().replace(b'/rr2;',old+b';',1)==raw,'Private source must differ only in one denominator'
    setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert setup.returncode==0;env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));assert env['VCTOOLSVERSION']=='14.36.32532'
    cl=shutil.which('cl.exe',path=env['PATH']);link=shutil.which('link.exe',path=env['PATH']);assert cl and link
    tools=[];passed=False
    def compile_args(src,obj,helper):
        a=[x for x in original_compile[:-1] if not x.lower().startswith(('/fo','/fd'))]
        a+=['/Fo'+str(obj),'/Fd'+str(OUT/'private_compile.pdb'),'/I'+str(S/'source'),'/sourceDependencies',str(obj.with_suffix('.dependencies.json'))]
        if helper is not None:a+=['/std:c++17','/DUPL_DARCY_BARE='+str(helper)]
        return a+[str(src)]
    try:
        tools.append(launch(TAG+'_compile_darcy',cl,compile_args(private,OUT/'JSphCpu_eta0.obj',None),env))
        for kind,bare in [('baseline',0),('candidate',1)]:
            obj=OUT/(kind+'.obj');exe=OUT/(kind+'.exe');tools.append(launch(TAG+'_compile_'+kind,cl,compile_args(CPP,obj,bare),env));args=[]
            for x in original_link:
                low=x.lower()
                if low.startswith('/out:'):x='/OUT:'+str(exe)
                elif low.startswith('/pdb:'):x='/PDB:'+str(OUT/(kind+'.pdb'))
                elif low.startswith('/implib:'):x='/IMPLIB:'+str(OUT/(kind+'.lib'))
                elif low.startswith('/ltcgout:'):x='/LTCGOUT:'+str(OUT/(kind+'.iobj'))
                elif low.endswith('.obj'):
                    name=Path(x).name.lower()
                    if name=='main.obj':x=str(obj)
                    elif name=='jsphcpu.obj' and bare:x=str(OUT/'JSphCpu_eta0.obj')
                args.append(x)
            tools.append(launch(TAG+'_link_'+kind,link,args,env))
        runtime=[]
        for p in Path(b['program']['path']).parent.iterdir():
            if p.suffix.lower()=='.dll' or p.name=='DsphConfig.xml':
                before=stat(p);dest=OUT/p.name;shutil.copy2(p,dest);assert p.read_bytes()==dest.read_bytes();runtime.append(dict(original=before,copy=stat(dest)))
        bindings += [stat(p) for p in sorted(OUT.glob('*.dependencies.json'))];verify(bindings);passed=True
    finally:
        save(RECEIPT,dict(stage=TAG,passed=passed,configuration='DebugCPU',original_build=stat(BUILD),original_compile=original_compile,original_link=original_link,consumed=bindings,tools=tools,private_source=stat(private),programs={k:stat(OUT/(k+'.exe')) for k in ('baseline','candidate') if (OUT/(k+'.exe')).exists()},runtime=runtime if passed else [],SHA_scans=0,production_edits=0,solver_started=False,physical_acceptance=False))
def run(kind):
    b=read(RECEIPT);assert b['passed'];verify(b['consumed']);verify([b['private_source']]);verify([x['copy'] for x in b['runtime']]);verify(list(b['programs'].values()))
    out=T/'outputs'/(TAG+'_'+kind);check=L/(TAG+'_'+kind+'.check.json');assert not out.exists() and not check.exists()
    if kind=='limits':
        args=['--limits',str(out)];program=b['programs']['baseline']['path']
    else:
        if kind=='candidate':assert read(L/(TAG+'_baseline.check.json'))['passed'],'Review complete baseline before candidate'
        args=['--job','32','512','0','-cpu','-ompthreads:1','-stable',str(SEED),str(out),'-dirdataout','data'];program=b['programs'][kind]['path']
    receipt=launch(TAG+'_'+kind,program,args);done=read(out/('completion.json' if kind=='limits' else 'complete.json'));assert done['passed']
    if kind!='limits':assert done['actual_ComputeStep_Sym'] and done['Nx']==32 and done['native_ids']==512 and done['samples']==257 and done['steps']==512 and done['actual_end_s']==2**-15 and done['darcy_bare']==(kind=='candidate') and done['global_eta2']>0
    verify(b['consumed']);save(check,dict(stage=TAG+'_'+kind,passed=True,actual_run=receipt,build=stat(RECEIPT),completion=stat(out/('completion.json' if kind=='limits' else 'complete.json')),files=[stat(p) for p in sorted(out.iterdir()) if p.is_file()],coupled_integrated=(kind!='limits'),half_performed=False,physical_acceptance=False))
def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','limits','baseline','candidate']);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();assert a.execution_authorized,'Root review and explicit authorization required'
    build() if a.action=='build' else run(a.action)
if __name__=='__main__':main()
