"""Own one admitted CPU8 gravity preload and one terminal notification; never decode/restart."""
import argparse,csv,ctypes,datetime,json,os,re,shutil,subprocess,time,xml.etree.ElementTree as ET
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_prestress_extended_CPU_r1';STEPS=2000000
OUT=T/'outputs'/TAG;RUNTIME=T/'outputs'/(TAG+'_runtime');SEED=T/'outputs/upl_prestress_gravity_r1_seed/CaseLianSaturatedColumnCollapse_prestress_gravity_r1'
ADMISSION=L/'upl_prestress_extended_r1.admission.json';THREAD='01a07683-bc64-7463-8db7-9ee6243967d8'
CODEX=Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1021.22027-win32-x64/bin/windows-x86_64/codex.exe')
P={k:L/(TAG+s) for k,s in dict(start='.start.json',call='.call.json',run='.run.json',status='.status.json',tmp='.status.tmp',log='.log',attempt='.queue_attempt.json',queue='.queue_result.json').items()}
K=ctypes.WinDLL('kernel32',use_last_error=True);K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];K.GetExitCodeProcess.restype=w.BOOL;K.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];K.WaitForSingleObject.restype=w.DWORD
def need(b,s):
    if not b:raise RuntimeError(s)
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def check(e):
    s=stat(e['path']);need((s['bytes'],s['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Frozen input changed: '+e['path']);return s
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,d,atomic=False):
    q=P['tmp'] if atomic else p
    with q.open('w' if atomic else 'x',encoding='utf-8',newline='\n') as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
    if atomic:os.replace(q,p)
def identity(q):return dict(pid=q.pid,created_epoch=q.create_time(),exe=q.exe(),argv=q.cmdline(),parent_pid=q.ppid())
def last_part():
    p=OUT/'Run.out'
    if not p.exists():return None
    with p.open('rb') as f:f.seek(max(0,p.stat().st_size-65536));lines=f.read().splitlines(keepends=True)
    for line in reversed(lines):
        m=re.match(rb'^Part_(\d+)\s+([0-9.eE+-]+)\s+(\d+)\s+',line)
        if m and line.endswith(b'\n'):return dict(raw_complete_line=line.decode('utf-8','replace'),part=int(m[1]),last_console_reported_time_text=m[2].decode('ascii'),last_console_reported_steps=int(m[3]),reported_step_fraction_capped=min(int(m[3])/STEPS,1.),not_decoded_native_clock=True)
    return None
def status(child,solver,owner,state):
    wait=K.WaitForSingleObject(int(child._handle),0);need(wait in (0,258),'Owned process handle observation failed');live=wait==258
    if live:
        try:need(psutil.Process(child.pid).create_time()==solver['created_epoch'],'Owned PID creation changed')
        except psutil.NoSuchProcess:need(K.WaitForSingleObject(int(child._handle),0)==0,'Owned process identity unavailable while handle remains live');live=False
    save(P['status'],dict(stage=TAG+'.status',utc=utc(),owner=owner,solver=solver,owned_solver_alive=live,state=state,last_console_report=last_part(),progress_is_console_lower_observation_not_exact_native_time=True,physical_acceptance=False),True)
def context():
    a=read(ADMISSION);need(a['passed'] is True and a['allowed_job']==TAG and re.fullmatch('[0-9a-f]{40}',a['source_commit']),'Separate root admission required')
    expected=T/'outputs/upl_prestress_ReleaseCPU_r1/DualSPHysics5.2CPU_win64.exe';need(Path(a['program']['path']).samefile(expected),'Admitted ReleaseCPU differs')
    names={'DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'};need({Path(e['path']).name for e in a['runtime']}==names and len(a['runtime'])==4,'Exactly four frozen runtime sources required')
    frozen=[*a['inputs'],a['program'],*a['runtime'],stat(ADMISSION),stat(__file__),stat(T/'notes/upl_prestress_extended_r1.json'),stat(T/'support/xCaseLianSaturatedColumnCollapse_prestress_r1_win64_CPU.bat')]
    for suffix in ('.xml','.bi4','_Normals.nbi4'):need(any(Path(e['path']).samefile(str(SEED)+suffix) for e in a['inputs']),'Prepared seed not bound by admission: '+suffix)
    for e in frozen:check(e)
    root=ET.parse(str(SEED)+'.xml').getroot()
    def value(key,parameter=False):
        n=root.findall('.//parameter[@key="'+key+'"]') if parameter else root.findall('.//'+key);need(len(n)==1,'Unique input key required: '+key);return n[0].get('value')
    for key,v in (('DtIni',2.5e-6),('DtFixed',2.5e-6),('TimeMax',5.),('TimeOut',.01),('SoilDamping',1),('SoilDampingCoef',.02),('SoilHourglassXi',0)):need(float(value(key,True))==v,'Admitted physical input differs: '+key)
    need(value('HydroMechInitMode').lower() in ('constantz','2'),'Hydrostatic pressure-only initialization required')
    for key,v in (('HydroMechInitZ',2),('PoreShepardRegularization',1),('PoreShepardInterval',40),('MaterialReturn',1),('HydroMechFreeSeepage',1),('HydroMechDrainage',0)):need(float(value(key))==v,'Admitted physical input differs: '+key)
    active=[q.info for q in psutil.process_iter(['pid','name','cmdline']) if (q.info['name'] or '').lower().startswith('dualsphysics') and 'cpu' in (q.info['name'] or '').lower()];need(not active,'Another CPU solver is active; no process is killed')
    need(CODEX.is_file(),'The fixed one-shot notification CLI is unavailable');RUNTIME.mkdir();OUT.mkdir()
    copies=[]
    for e in [a['program'],*a['runtime']]:
        dst=RUNTIME/Path(e['path']).name;shutil.copy2(e['path'],dst);s=stat(dst);need((s['bytes'],s['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Runtime copy differs');copies.append(s)
    return a,frozen+copies,RUNTIME/expected.name
def output_checks():
    text=(OUT/'Run.out').read_text(encoding='utf-8-sig');need('Finished execution (code=0).' in text and re.search(r'Excluded particles[.]+:\s*0(?:\s|$)',text),'Normal termination/no-exclusion check failed')
    for marker in ('OpenMP(Threads:8)','HydroMechInitMode="ConstantZ"','PoreShepardRegularization="Enabled"','PoreShepardInterval: 40','SoilDamping="BuiFukagawa2013"','SoilDampingCoef=0.02'):need(marker in text,'Actual startup marker missing: '+marker)
    with (OUT/'Run.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f,delimiter=';'))
    need(len(rows)==1,'One actual Run.csv summary required');r=rows[0];n=int(r['Steps']);count=int(r['PartFiles'])
    need(STEPS<=n<=STEPS+1 and r['Np']=='7060' and r['Nbound']==r['Nfixed']=='2060' and r['Hardware']=='CPU' and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'Actual step/ID/exclusion summary differs')
    files=sorted((OUT/'data').glob('Part_*.bi4'));need(count>1 and [p.name for p in files]==['Part_%04d.bi4'%i for i in range(count)] and all(p.stat().st_size>0 for p in files),'Actual PART sequence is incomplete')
    return dict(actual_steps=n,saved_frames=count,physical_time_Run_csv_rounded_text=r['PhysicalTime'],simulation_loop_seconds_reported=r['TSimul'],last_console_report=last_part(),Run_csv=stat(OUT/'Run.csv'),Run_out=stat(OUT/'Run.out'),native_file_names=[p.name for p in files],normal_finish_and_no_exclusion_Run_checks=True)
def queue_once(result):
    event='run_passed_pending_native_review' if result['passed'] else 'run_failed_or_ownership_check_failed'
    message=('同线程已授权C08重力预加载继续：'+TAG+'，事件='+event+'。先读原始start/call/run/status，核PID创建时间/exe/argv/parent/句柄退出及admission冻结输入。成功也只表示待native/物理审查，不是5秒平衡。仅run通过后，先检查是否已有或活动decode，再至多一次运行现有upl_prestress_native_run_r1.py extended CPU；核实际clock、22arrays、P0、FS、ledger、kappa及全部原安全门，审查压力/应力/速度/能量收敛。失败保留真实rc、最后console报告行和首因，不虚构未保存停止时刻、不重跑。继续原任务中状态连续撤墙等开发，但不得据本通知自动启动新solver/restart/额外half，也不得直接赋sigma初场。通知仅一次45秒，超时可能已送达，禁止重发。')
    argv=[str(CODEX),'queue','--thread',THREAD,'--message',message];save(P['attempt'],dict(stage=TAG+'.queue_attempt',utc=utc(),thread=THREAD,argv=argv,run=stat(P['run']),attempts=1,timeout_s=45,do_not_resend=True))
    env=os.environ.copy();env['CODEX_THREAD_ID']=THREAD;out=dict(stage=TAG+'.queue_result',thread=THREAD,attempts=1,do_not_resend=True)
    try:
        q=subprocess.run(argv,cwd=T.parent,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,env=env,creationflags=subprocess.CREATE_NO_WINDOW);out.update(status='queued' if q.returncode==0 else 'queue_failed',actual_exit=q.returncode,stdout=q.stdout,stderr=q.stderr)
    except subprocess.TimeoutExpired as e:out.update(status='queue_delivery_uncertain',error=str(e),stdout=e.stdout.decode('utf-8','replace') if isinstance(e.stdout,bytes) else e.stdout,stderr=e.stderr.decode('utf-8','replace') if isinstance(e.stderr,bytes) else e.stderr)
    except Exception as e:out.update(status='queue_failed',error=str(e))
    out['ended_utc']=utc();save(P['queue'],out)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');args=p.parse_args();need(args.execution_authorized,'Explicit execution invocation required')
    need(not any(p.exists() for p in [OUT,RUNTIME,*P.values()]),'Existing output/runtime/receipt protected')
    result=dict(stage=TAG+'.run',tag=TAG,passed=False,actual_exit=None,BAT_executed=False,threads=8,native_review_pending=True,physical_acceptance=False,native_decoder_invoked=False,automatic_next_solver=False,SHA_scans=0);frozen=[];child=None;errors=[];started=utc();wall=time.monotonic()
    try:
        admission,frozen,exe=context();program=stat(exe);owner=identity(psutil.Process());argv=[str(exe),'-cpu','-ompthreads:8','-stable','-mdbc_freeslip',str(SEED),str(OUT),'-dirdataout','data','-svres','-nsteps:2000000']
        with P['log'].open('xb') as stream:
            child=subprocess.Popen(argv,cwd=T.parent,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);solver=dict(pid=child.pid)
            try:
                solver=identity(psutil.Process(child.pid));need(Path(solver['exe']).samefile(exe) and solver['argv'][1:]==argv[1:] and solver['parent_pid']==owner['pid'],'Actual child executable/argv/parent differs')
                save(P['start'],dict(stage=TAG+'.start',utc=utc(),owner=owner,solver=solver,program=program,argv=argv,working_directory=str(T.parent),admission=stat(ADMISSION),source_commit=admission['source_commit'],consumed=frozen,direct_owner_no_scheduler=True,BAT_executed=False,physical_acceptance=False));status(child,solver,owner,'running')
            except Exception as e:errors.append('Ownership/start/status: '+str(e));print(json.dumps(dict(owned_child_pid=child.pid,observation_failure=str(e),no_process_killed=True)),flush=True)
            result.update(owner=owner,solver=solver,program=program)
            print(json.dumps(dict(solver_started=solver,argv=argv)),flush=True)
            while True:
                try:rc=child.wait(timeout=30);result['actual_exit']=rc;break
                except subprocess.TimeoutExpired:
                    try:status(child,solver,owner,'running')
                    except Exception as e:errors.append('Status: '+str(e));print(json.dumps(dict(status_failure=str(e),owned_child_pid=child.pid)),flush=True)
            code=w.DWORD();got=bool(K.GetExitCodeProcess(int(child._handle),ctypes.byref(code)));result['actual_Win32_exit']=code.value if got else None
            save(P['call'],dict(stage=TAG+'.run_call',started_utc=started,ended_utc=utc(),argv=argv,working_directory=str(T.parent),program=program,solver=solver,actual_Popen_wait_exit=rc,actual_Win32_exit=result['actual_Win32_exit'],typed_returncode_captured_first=type(rc) is int,elapsed_s=time.monotonic()-wall,BAT_executed=False,log=stat(P['log']),ownership_or_status_errors=errors))
        result.update(owner=owner,solver=solver,actual_call=stat(P['call']),source_commit=admission['source_commit'],admission=stat(ADMISSION),program=program,elapsed_s=time.monotonic()-wall)
        need(got and rc==code.value==0 and not errors,'Owned exit or ownership/status check failed');result.update(output_checks())
        result.update(passed=True)
    except Exception as e:
        result.update(failure=str(e),last_console_report=last_part());print(json.dumps(dict(failure=str(e))),flush=True)
        if child is not None and result['actual_exit'] is None:
            # A bookkeeping exception never abandons or kills the child: retain its original handle until exit.
            while True:
                try:result['actual_exit']=child.wait(timeout=30);break
                except subprocess.TimeoutExpired:
                    try:status(child,solver,owner,'running_after_owner_observation_failure')
                    except Exception:pass
            code=w.DWORD();got=bool(K.GetExitCodeProcess(int(child._handle),ctypes.byref(code)));result['actual_Win32_exit']=code.value if got else None
        if child is not None and not P['call'].exists():save(P['call'],dict(stage=TAG+'.run_call',started_utc=started,ended_utc=utc(),argv=argv,program=program,solver=solver,actual_Popen_wait_exit=result['actual_exit'],actual_Win32_exit=result.get('actual_Win32_exit'),owner_exception=result['failure'],BAT_executed=False))
    result['consumed']=frozen
    try:
        for e in frozen:check(e)
        result['consumed_stats_unchanged']=bool(frozen)
    except Exception as e:result.update(passed=False,consumed_stats_unchanged=False,failure=(result.get('failure','')+'; '+str(e)))
    result['last_console_report']=last_part()
    if child is not None and type(result['actual_exit']) is int:
        try:status(child,solver,owner,'terminal_passed_pending_native' if result['passed'] else 'terminal_failure')
        except Exception as e:result.update(passed=False,failure=result.get('failure','')+'; terminal status: '+str(e));print(json.dumps(dict(terminal_status_failure=str(e))),flush=True)
    save(P['run'],result)
    if child is not None and type(result['actual_exit']) is int:
        queue_once(result)
    print(json.dumps(dict(passed=result['passed'],run=str(P['run']),actual_exit=result['actual_exit'],native_review_pending=True)),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
