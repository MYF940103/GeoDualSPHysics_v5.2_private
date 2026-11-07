"""One admitted Ck2 combined CPU/GPU run; never retries, decodes or queues."""
import csv,ctypes,datetime,json,re,shutil,subprocess,sys,time
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];L=T/'logs'
def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2);f.write('\n')
def identity(q):return dict(pid=q.pid,created_epoch=q.create_time(),exe=q.exe(),argv=q.cmdline(),parent_pid=q.ppid())
K=ctypes.WinDLL('kernel32',use_last_error=True)
K.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];K.OpenProcess.restype=w.HANDLE
K.CloseHandle.argtypes=[w.HANDLE]
K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];K.GetExitCodeProcess.restype=w.BOOL
def exitcode(handle):
    c=w.DWORD();need(K.GetExitCodeProcess(handle,ctypes.byref(c)),'Native exit unavailable');return c.value
need(len(sys.argv)==2 and sys.argv[1] in ('CPU','GPU'),'Use CPU or GPU')
backend=sys.argv[1];tag='upl_ck2_release_short_'+backend+'_r1';out=T/'outputs'/tag
paths={k:L/(tag+s) for k,s in dict(start='.start.json',call='.call.json',run='.run.json',log='.log',san='.sanitizer.log').items()}
need(not out.exists() and not any(p.exists() for p in paths.values()),'Existing/partial run protected')
frozen=[];result=dict(stage=tag+'.run',tag=tag,passed=False,actual_exit=None,actual_Win32_exit=None,native_review_pending=True,physical_acceptance=False,automatic_next_solver=False,SHA_scans=0);handle=None
def bind(e):
    a=stat(e['path']);need(a['bytes']==e['bytes'] and a['mtime_ns']==e['mtime_ns'],'Consumed file changed: '+e['path']);frozen.append(a);return a
try:
    admission=L/'upl_ck2_release_short_r1.admission.json';a=read(admission);bind(stat(admission));need(a['passed'] and tag in a['allowed_jobs'],'Reviewed admission required')
    for e in a['inputs']+a['prerequisites']:bind(e)
    bp=L/('upl_c08_variablek_'+('ReleaseCPU' if backend=='CPU' else 'Release')+'_r1.build.json');b=read(bp)
    need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0,'Release build failed')
    program=bind(b['program']);capture=bind(b['source_capture']);archive=bind(read(capture['path'])['archive']);exe=Path(program['path'])
    seed=T/'outputs/upl_ck2_release_short_r1_seed/CaseLianSaturatedColumnCollapse_ck2_release_short_r1';seedfiles=[bind(stat(str(seed)+s)) for s in ('.xml','.bi4','_Normals.nbi4')]
    runtime=T/'outputs'/('upl_prestress_check_release_CPU_r1_runtime' if backend=='CPU' else 'upl_prestress_check_GPU_r1_runtime')
    for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
        src=bind(stat(runtime/name));dst=exe.parent/name
        if not dst.exists():shutil.copy2(src['path'],dst)
        need(stat(dst)['bytes']==src['bytes'] and stat(dst)['mtime_ns']==src['mtime_ns'],'Runtime copy differs');bind(stat(dst))
    bind(stat(__file__));need(not any((q.info['name'] or '').lower().startswith('dualsphysics') for q in psutil.process_iter(['name'])),'Another solver is active; do not duplicate')
    target=[str(exe),*(['-cpu','-ompthreads:8'] if backend=='CPU' else ['-gpu:0']),'-stable','-mdbc_freeslip',str(seed),str(out),'-dirdataout','data','-svres','-nsteps:800']
    if backend=='GPU':
        san=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/compute-sanitizer/compute-sanitizer.exe');bind(stat(san))
        argv=[str(san),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(paths['san']),*target]
    else:argv=target
    owner=identity(psutil.Process());wall=time.monotonic();started=datetime.datetime.now(datetime.timezone.utc).isoformat();errors=[];child=None
    with paths['log'].open('xb') as f:
        p=subprocess.Popen(argv,cwd=T.parent,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        tool=identity(psutil.Process(p.pid));need(tool['parent_pid']==owner['pid'] and tool['argv'][1:]==argv[1:],'Actual tool/owner identity differs')
        if backend=='CPU':child=tool
        save(paths['start'],dict(stage=tag+'.start',owner=owner,tool=tool,solver=child,target_argv=target,program=program,consumed=frozen,admission=stat(admission),direct_owner_no_scheduler=True))
        print(json.dumps(dict(tag=tag,actual_tool_PID=p.pid)),flush=True)
        if backend=='GPU':
            while p.poll() is None:
                if handle is None:
                    try:children=psutil.Process(p.pid).children(recursive=True)
                    except psutil.NoSuchProcess:children=[]
                    for q in children:
                        try:
                            if q.name().lower()!=exe.name.lower() or not Path(q.exe()).samefile(exe):continue
                            candidate=K.OpenProcess(0x101000,False,q.pid);need(candidate,'Unable to retain solver exit handle');handle=candidate;child=identity(q)
                            need(child['argv'][1:]==target[1:] and child['created_epoch']>=tool['created_epoch'],'Actual GPU solver identity differs');print(json.dumps(dict(actual_solver=child)),flush=True);break
                        except psutil.NoSuchProcess:continue
                        except Exception as e:errors.append(str(e))
                time.sleep(.005)
        rc=p.wait();toolrc=exitcode(int(p._handle));solverrc=exitcode(handle) if backend=='GPU' and handle else toolrc if backend=='CPU' else None
    save(paths['call'],dict(stage=tag+'.call',owner=owner,tool=tool,solver=child,target_argv=target,argv=argv,program=program,actual_Popen_wait_exit=rc,actual_tool_Win32_exit=toolrc,actual_solver_Win32_exit=solverrc,typed_returncode_captured_first=type(rc) is int,ownership_errors=errors,started_utc=started,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_s=time.monotonic()-wall,log=stat(paths['log'])))
    result.update(actual_exit=solverrc,actual_Win32_exit=solverrc,actual_tool_exit=toolrc,solver=child,start_record=stat(paths['start']),actual_call=stat(paths['call']),elapsed_s=time.monotonic()-wall,program=program,source_build=stat(bp),source_capture=capture,source_archive=archive,seed=seedfiles,admission=stat(admission))
    need(child is not None and rc==toolrc==solverrc==0 and not errors,'Actual solver/tool/ownership failed; preserve evidence, no retry')
    if backend=='GPU':
        text=paths['san'].read_text(encoding='utf-8');need('ERROR SUMMARY: 0 errors' in text and 'LEAK SUMMARY: 0 bytes leaked in 0 allocations' in text,'Actual memcheck failed');result.update(memcheck_zero_errors_and_leaks=True,sanitizer_log=stat(paths['san']))
    text=(out/'Run.out').read_text(encoding='utf-8-sig');need('Finished execution (code=0).' in text and re.search(r'Excluded particles[.]+:\s*0(?:\s|$)',text),'Normal completion/no-exclusion failed')
    with (out/'Run.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f,delimiter=';'))
    need(len(rows)==1,'One actual Run summary required');r=rows[0];frames=int(r['PartFiles'])
    need(int(r['Steps'])==800 and r['Np']=='7060' and r['Nbound']==r['Nfixed']=='2060' and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'Actual steps/registry/exclusions differ')
    parts=sorted((out/'data').glob('Part_*.bi4'));need(frames>1 and [q.name for q in parts]==['Part_%04d.bi4'%i for i in range(frames)],'Actual native sequence differs')
    released=[s for s in text.splitlines() if 'GravityPreload: phase=released' in s];need(len(released)==1 and 'completed_step=380 retired=260;' in released[0] and 'damping=OFF Shepard=OFF FreeSeepage=ON.' in released[0],'Actual event differs')
    if backend=='GPU':need('Device selected: 0 "NVIDIA GeForce RTX 3050"' in text,'Actual local GPU differs')
    result.update(passed=True,actual_steps=800,saved_frames=frames,summary=r,event_markers=released,Run_out=stat(out/'Run.out'),Run_csv=stat(out/'Run.csv'),native_file_names=[q.name for q in parts])
except Exception as e:result.update(passed=False,first_failure=str(e))
finally:
    if handle:K.CloseHandle(handle)
    try:result['consumed_stats_unchanged']=bool(frozen) and all(stat(e['path'])==e for e in frozen)
    except Exception:result['consumed_stats_unchanged']=False
    if not result['consumed_stats_unchanged']:result['passed']=False;result.setdefault('first_failure','Consumed file changed')
    result['consumed']=frozen;save(paths['run'],result)
print(json.dumps(dict(tag=tag,passed=result['passed'],actual_exit=result['actual_exit'],first_failure=result.get('first_failure'))),flush=True)
raise SystemExit(0 if result['passed'] else 1)
