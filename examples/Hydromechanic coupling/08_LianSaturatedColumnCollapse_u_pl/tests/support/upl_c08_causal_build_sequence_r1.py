"""Own three already reviewed isolated builds, then one same-thread completion notice; no solver."""
import ctypes,datetime,json,os,subprocess,sys,time
from pathlib import Path
from ctypes import wintypes as w
import psutil

T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_c08_causal_build_sequence_r1'
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8'
CLI=Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1021.22027-win32-x64/bin/windows-x86_64/codex.exe')
BUILDER=T/'support/upl_c08_causal_build_r1.py';CAP=T/'outputs/upl_c08_causal_source_r1/source.json'
def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,d):
 with p.open('x',encoding='utf8') as f:json.dump(d,f,ensure_ascii=False,indent=2)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

if __name__=='__main__':
 if sys.argv[1:]!=['--execution-authorized','--notify']:raise SystemExit('Reviewed explicit build sequence and one terminal notice only')
 if os.environ.get('CODEX_THREAD_ID')!=THREAD or not CLI.is_file():raise SystemExit('Verified same-thread completion mechanism required')
 if any((L/(TAG+s)).exists() for s in ('.start.json','.run.json','.queue_attempt.json','.queue_result.json')):raise SystemExit('Prior owner or partial records protected')
 source=read(CAP);frozen=[stat(BUILDER),stat(__file__),stat(T/'notes/upl_c08_causal_build_sequence_r1.md'),stat(CAP),source['archive'],source['production_diff']]
 owner=psutil.Process();identity=dict(pid=owner.pid,created_epoch=owner.create_time(),exe=owner.exe(),argv=owner.cmdline(),parent_pid=owner.ppid())
 save(L/(TAG+'.start.json'),dict(stage=TAG,owner=identity,started_utc=now(),frozen=frozen,solver_invocations=0))
 result=dict(stage=TAG,passed=False,owner=identity,calls=[],build_receipts=[],frozen=frozen,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,physical_acceptance=False,SHA_scans=0)
 try:
  for conf in ('DebugCPU','Debug','Release'):
   argv=[sys.executable,'-X','utf8','-B',str(BUILDER),conf,'--execution-authorized'];log=L/(TAG+'_'+conf+'.log');begin=time.monotonic()
   with log.open('xb') as f:
    p=subprocess.Popen(argv,cwd=T.parent,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    child=psutil.Process(p.pid);ci=dict(pid=p.pid,created_epoch=child.create_time(),exe=child.exe(),argv=child.cmdline(),parent_pid=child.ppid());rc=p.wait()
    call=dict(configuration=conf,child=ci,argv=argv,actual_Popen_wait_exit=rc,actual_Win32_exit=None,elapsed_s=time.monotonic()-begin,log=stat(log));result['calls'].append(call)
    k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];v=w.DWORD()
    if not k.GetExitCodeProcess(int(p._handle),ctypes.byref(v)):raise RuntimeError('Build helper native exit unavailable')
   call['actual_Win32_exit']=v.value
   receipt=L/('upl_c08_causal_'+conf+'_r1.build.json')
   if receipt.is_file():result['build_receipts'].append(stat(receipt))
   if rc or v.value:raise RuntimeError(conf+' helper failed; preserve the real call and build log')
   b=read(receipt)
   if not(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and b['canonical_runtime_PRE_unchanged']):raise RuntimeError(conf+' isolated build check failed')
   if any(stat(e['path'])!=e for e in frozen):raise RuntimeError('Frozen build sequence input changed')
  result['passed']=True
 except Exception as e:result['first_failure']=str(e)
 result['ended_utc']=now();run=L/(TAG+'.run.json');save(run,result)
 message=('Authorized same-thread C08 causal-observer build continuation, not a physical observation. Event='+('three_builds_passed_pending_implementation_review' if result['passed'] else 'build_failed_preserved_pending_diagnosis')+'. Read '+str(run)+' and its original start plus all three immutable build calls/receipts. This owner ran builds only: no program/help, solver, native or VTK. Verify actual CPU Debug/GPU Debug/Release exits, dual macros and frozen source/runtime_r5/r6/PRE protection. The full n3 r6 3s review is complete but clumping/early arrest remains unresolved; other psi stay locked. Continue the already authorized output-only causal observer toward Debug smoke/native/memcheck and only then a separately reviewed .90s Release observation, without changing physics/thresholds or duplicate solvers. A completed build is not physical acceptance. Preserve any failure, no old-owner restart, recursive rearm or connectivity test. This owner queues exactly once, timeout may already have delivered; never resend.')
 argv=[str(CLI),'queue','--thread',THREAD,'--message',message];attempt=L/(TAG+'.queue_attempt.json')
 save(attempt,dict(stage=TAG,thread=THREAD,argv=argv,run=stat(run),attempts=1,timeout_s=45,do_not_resend=True))
 reply=dict(stage=TAG,attempts=1,do_not_resend=True)
 try:
  q=subprocess.run(argv,cwd=T.parent,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
  reply.update(status='queued' if q.returncode==0 else 'queue_failed',actual_exit=q.returncode,stdout=q.stdout,stderr=q.stderr)
 except subprocess.TimeoutExpired as e:reply.update(status='delivery_uncertain',error=str(e))
 except Exception as e:reply.update(status='queue_failed',error=str(e))
 save(L/(TAG+'.queue_result.json'),reply);print(json.dumps(dict(passed=result['passed'],run=str(run),first_failure=result.get('first_failure'))),flush=True)
 raise SystemExit(0 if result['passed'] else 1)
