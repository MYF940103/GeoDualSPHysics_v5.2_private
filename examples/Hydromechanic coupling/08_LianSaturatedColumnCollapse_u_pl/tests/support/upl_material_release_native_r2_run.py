"""One explicit new-program Symplectic regression job; no decode, chain, retry or watcher."""
import csv,ctypes,datetime,json,re,shutil,subprocess,sys,time,xml.etree.ElementTree as ET
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_material_release_native_r1'
MODES=('source','alias0','receive_old','receive_new','fluid','plastic')
def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def identity(q):return dict(pid=q.pid,created_epoch=q.create_time(),exe=q.exe(),argv=q.cmdline(),parent_pid=q.ppid())
K=ctypes.WinDLL('kernel32',use_last_error=True);K.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];K.OpenProcess.restype=w.HANDLE;K.CloseHandle.argtypes=[w.HANDLE];K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];K.GetExitCodeProcess.restype=w.BOOL
def exitcode(h):
    v=w.DWORD();need(K.GetExitCodeProcess(h,ctypes.byref(v)),'Actual process exit unavailable');return v.value
def main():
    need(len(sys.argv)==4 and sys.argv[1] in MODES and sys.argv[2] in ('CPU','GPU') and sys.argv[3]=='--execution-authorized','Use source|alias0|receive_old|receive_new|fluid|plastic CPU|GPU --execution-authorized')
    mode,backend=sys.argv[1:3];sanitize=backend=='GPU' and mode=='source';tag=TAG+'_'+mode+'_'+backend;out=T/'outputs'/tag;seedroot=T/'outputs'/(tag+'_seed');steps=4 if mode=='fluid' else 256 if mode=='plastic' else 800
    paths={k:L/(tag+s) for k,s in dict(start='.start.json',call='.call.json',run='.run.json',log='.log',san='.sanitizer.log').items()}
    need(not out.exists() and not seedroot.exists() and not any(p.exists() for p in paths.values()),'Existing or partial job protected; inspect it, never retry this tag')
    frozen=[];handle=None;result=dict(stage=tag+'.run',tag=tag,mode=mode,backend=backend,passed=False,actual_exit=None,actual_Win32_exit=None,solver_invocations=0,native_decoder_invoked=False,automatic_next_solver=False,watcher_created=False,BAT_executed=False,SHA_scans=0,physical_acceptance=False)
    def bind(e):
        a=stat(e['path']);need((a['bytes'],a['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Consumed file changed: '+e['path']);frozen.append(a);return a
    def load(p):bind(stat(p));return read(p)
    def newnative(m,b):
        q=L/(TAG+'_'+m+'_'+b+'.native.check.json');d=load(q);need(d['passed'] and d['original_native_guards_passed'] and d['consumed_stats_unchanged'],'Prior new-program native gate not passed: '+str(q));bind(d['native_completion']);return d
    try:
        bp=L/('upl_material_release_'+('DebugCPU' if backend=='CPU' else 'Debug')+'_r3.build.json');build=load(bp)
        need(build['passed'] and build['actual_typed_exit_code']==build['actual_Win32_exit']==0 and build['source_stats_unchanged'] and build['canonical_and_package_stats_unchanged'],'Matching isolated new Debug-r3 build required')
        program=bind(build['program']);capture=bind(build['source_capture']);archive=bind(read(capture['path'])['archive']);exe=Path(program['path'])
        need(Path(capture['path']).parent.name=='upl_material_release_source_r3' and Path(capture['path']).name=='source.json' and Path(archive['path']).parent.name=='upl_material_release_source_r3','Matching frozen r3 source capture/archive required')
        need(exe.parent.name=='upl_material_release_'+('DebugCPU' if backend=='CPU' else 'Debug')+'_r3','Wrong new program path')
        config=T/'configs'/(tag+'.xml');bind(stat(config));tree=ET.parse(config);root=tree.getroot();soils=root.find('./execution/special/soils');need(soils is not None,'Actual soils XML missing')
        need(soils.find('MaterialReturn').get('value')==('0' if mode=='alias0' else '1'),'Actual deprecated XML alias differs')
        pre=None;pretime=None
        if mode in ('source','alias0','receive_old','receive_new'):
            oldrun=load(L/('upl_preload_handoff_source_'+backend+'_r1.run.json'));need(oldrun['passed'] and oldrun['actual_exit']==oldrun['actual_Win32_exit']==0,'Closed historical r2 source needed')
            oldcheck=load(L/('upl_preload_handoff_source_'+backend+'_r1_native_r1.check.json'));need(oldcheck['passed'] and oldcheck['original_native_guards_passed'] and oldcheck['qualified_elastic_PRE_verified'],'Closed old native source needed')
            original=[bind(e) for e in oldrun['seed']];need(len(original)==3,'Historical XML/BI4/normal seed binding required')
            if mode!='source':newnative('source',backend)
            if mode=='receive_old':pre=Path(bind(oldcheck['certified_pre_file'])['path']);pretime=oldcheck['actual_completion']['source_PRE_actual_time_s']
            elif mode=='receive_new':
                d=newnative('source',backend);need(d['actual_completion']['source_material_law_version']==2,'New PRE must be Version2');pre=Path(bind(d['certified_pre_file'])['path']);pretime=d['actual_completion']['source_PRE_actual_time_s']
            event=root.find('./execution/special/gravitypreload');need(event is not None,'Actual PRE event missing')
            if pre is None:need(event.get('elastic_source')=='true' and not event.get('statefile'),'Source qualification scope differs')
            else:need(Path(event.get('statefile','')).samefile(pre) and not event.get('elastic_source'),'Actual receiver config points to another PRE');result.update(source_pre_file=stat(pre),source_pre_time_s=pretime)
        else:
            newnative('source',backend);base=T/'outputs/upl_material_periodic_shear_r1_seed/CaseLianMaterialPeriodicShear_r1';original=[bind(stat(str(base)+s)) for s in ('.xml','.bi4')]
            if mode=='plastic' and backend=='GPU':newnative('plastic','CPU')
        seedroot.mkdir();seed=seedroot/Path(original[0]['path']).stem;shutil.copy2(config,str(seed)+'.xml')
        for suffix,e in zip(('.bi4','_Normals.nbi4'),original[1:]):shutil.copy2(e['path'],str(seed)+suffix)
        seedfiles=[bind(stat(str(seed)+s)) for s in ('.xml','.bi4')+(('_Normals.nbi4',) if len(original)==3 else ())]
        runtime=T/'outputs'/('upl_prestress_check_CPU_r1_runtime' if backend=='CPU' else 'upl_prestress_check_GPU_r1_runtime');runtimefiles=[]
        for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
            src=bind(stat(runtime/name));dst=exe.parent/name
            if not dst.exists():shutil.copy2(src['path'],dst)
            actual=stat(dst);need((actual['bytes'],actual['mtime_ns'])==(src['bytes'],src['mtime_ns']),'Runtime copy SMT differs');bind(actual);runtimefiles.append(actual)
        bind(stat(__file__));need(not any((p.info['name'] or '').lower().startswith('dualsphysics') for p in psutil.process_iter(['name'])),'Another actual solver is active; no process is stopped')
        target=[str(exe),*(['-cpu','-ompthreads:8'] if backend=='CPU' else ['-gpu:0']),'-stable',*(['-mdbc_freeslip'] if len(original)==3 else []),str(seed),str(out),'-dirdataout','data','-svres','-nsteps:'+str(steps)]
        argv=target
        if sanitize:
            san=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/compute-sanitizer/compute-sanitizer.exe');bind(stat(san));argv=[str(san),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(paths['san']),*target]
        owner=identity(psutil.Process());started=utc();wall=time.monotonic();errors=[];tool={};child=None;result.update(program=program,source_build=stat(bp),source_capture=capture,source_archive=archive,config=stat(config),seed=seedfiles,base_seed=original,runtime=runtimefiles,initial_completed_step=380 if pre else 0)
        with paths['log'].open('xb') as stream:
            p=subprocess.Popen(argv,cwd=T.parent,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);result['solver_invocations']=1
            try:
                tool=identity(psutil.Process(p.pid));need(tool['argv'][1:]==argv[1:] and tool['parent_pid']==owner['pid'],'Actual owned tool identity differs')
                if not sanitize:child=tool;need(Path(child['exe']).samefile(exe),'Actual direct program differs')
            except Exception as e:errors.append(str(e))
            save(paths['start'],dict(stage=tag+'.start',owner=owner,tool=tool,solver=child,target_argv=target,program=program,working_directory=str(T.parent),consumed=frozen,direct_owner_no_scheduler=True))
            print(json.dumps(dict(tag=tag,actual_tool_PID=p.pid,solver=child)),flush=True)
            while sanitize and p.poll() is None:
                if handle is None:
                    try:
                        for q in psutil.Process(p.pid).children(recursive=True):
                            try:
                                if q.name().lower()!=exe.name.lower() or not Path(q.exe()).samefile(exe):continue
                                child=identity(q);handle=K.OpenProcess(0x101000,False,q.pid);need(handle,'Actual solver handle unavailable');need(child['argv'][1:]==target[1:] and child['parent_pid']==p.pid,'Actual GPU child identity differs');print(json.dumps(dict(actual_solver=child)),flush=True);break
                            except psutil.NoSuchProcess:continue
                    except psutil.NoSuchProcess:pass
                    except Exception as e:errors.append(str(e))
                time.sleep(.005)
            rc=p.wait();toolrc=solverrc=None
            try:toolrc=exitcode(int(p._handle));solverrc=toolrc if not sanitize else exitcode(handle) if handle else None
            except Exception as e:errors.append(str(e))
        save(paths['call'],dict(stage=tag+'.call',owner=owner,tool=tool,solver=child,argv=argv,target_argv=target,program=program,actual_Popen_wait_exit=rc,actual_tool_Win32_exit=toolrc,actual_solver_Win32_exit=solverrc,typed_returncode_captured_first=type(rc) is int,ownership_errors=errors,started_utc=started,ended_utc=utc(),elapsed_s=time.monotonic()-wall,log=stat(paths['log'])))
        result.update(actual_exit=solverrc,actual_Win32_exit=solverrc,actual_tool_exit=toolrc,memcheck_invoked=sanitize,solver=child,start_record=stat(paths['start']),actual_call=stat(paths['call']),elapsed_s=time.monotonic()-wall);need(child is not None and rc==toolrc==solverrc==0 and not errors,'Actual owned exit/identity failed; retain evidence')
        if sanitize:
            text=paths['san'].read_text();need('ERROR SUMMARY: 0 errors' in text and 'LEAK SUMMARY: 0 bytes leaked in 0 allocations' in text,'Actual memcheck failed');result.update(memcheck_zero_errors_and_leaks=True,sanitizer_log=stat(paths['san']))
        text=(out/'Run.out').read_text(encoding='utf-8-sig');need('Finished execution (code=0).' in text and re.search(r'Excluded particles[.]+:\s*0(?:\s|$)',text),'Normal completion/no-exclusion failed')
        need('MaterialReturn is deprecated: values 0 and 1 both use the unified DP return' in text,'Explicit unified-alias migration warning missing')
        with (out/'Run.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f,delimiter=';'))
        need(len(rows)==1,'One actual summary row required');r=rows[0];frames=int(r['PartFiles']);n=7060 if len(original)==3 else 1024;nb=2060 if len(original)==3 else 0
        need(int(r['Steps'])==steps and int(r['Np'])==n and int(r['Nbound'])==int(r['Nfixed'])==nb and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'Actual updates/registry/exclusion summary differs')
        parts=sorted((out/'data').glob('Part_*.bi4'));need(frames>=2 and [q.name for q in parts]==['Part_%04d.bi4'%i for i in range(frames)],'Actual PART sequence differs')
        markers=[s for s in text.splitlines() if 'GravityPreload:' in s]
        if len(original)==3:
            releases=[s for s in markers if 'phase=released' in s];imports=[s for s in markers if 'state imported file=' in s];need(len(releases)==1 and 'completed_step=380 retired=260;' in releases[0] and 'damping=OFF Shepard=OFF FreeSeepage=ON.' in releases[0] and len(imports)==bool(pre),'Actual one-shot release/import differs')
            if pre:
                for line in [imports[0],releases[0]]:
                    m=re.search(r'actual=([^ ]+) completed_step=(\d+)',line);need(m and float(m[1])==pretime and int(m[2])==380,'Imported source actual clock/global count differs')
        result.update(passed=True,actual_steps=steps,new_updates_from_completed_counters=steps-(380 if pre else 0),saved_frames=frames,summary=r,event_markers=markers,Run_out=stat(out/'Run.out'),Run_csv=stat(out/'Run.csv'),native_file_names=[p.name for p in parts],native_review_pending=True)
    except Exception as e:result.update(passed=False,first_failure=str(e))
    finally:
        if handle:K.CloseHandle(handle)
        try:result['consumed_stats_unchanged']=bool(frozen) and all(stat(e['path'])==e for e in frozen)
        except Exception:result['consumed_stats_unchanged']=False
        if not result['consumed_stats_unchanged']:result['passed']=False;result.setdefault('first_failure','Consumed binding changed')
        result['consumed']=frozen;save(paths['run'],result)
    print(json.dumps(dict(tag=tag,passed=result['passed'],actual_exit=result['actual_exit'],first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
