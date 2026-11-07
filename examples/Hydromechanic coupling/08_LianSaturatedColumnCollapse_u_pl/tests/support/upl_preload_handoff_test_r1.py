"""One separately admitted source or receive continuity run. Never decodes or chains jobs."""
import csv,ctypes,datetime,json,re,shutil,subprocess,sys,time,xml.etree.ElementTree as ET
from ctypes import wintypes as w
from pathlib import Path
from xml.sax.saxutils import quoteattr
import psutil
T=Path(__file__).resolve().parents[1];L=T/'logs';A=L/'upl_preload_handoff_test_r1.admission.json'
def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def identity(q):return dict(pid=q.pid,created_epoch=q.create_time(),exe=q.exe(),argv=q.cmdline(),parent_pid=q.ppid())
K=ctypes.WinDLL('kernel32',use_last_error=True)
K.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];K.OpenProcess.restype=w.HANDLE
K.CloseHandle.argtypes=[w.HANDLE];K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];K.GetExitCodeProcess.restype=w.BOOL
def exitcode(handle):
    value=w.DWORD();need(K.GetExitCodeProcess(handle,ctypes.byref(value)),'Actual native exit unavailable');return value.value
def main():
    need(len(sys.argv)==3 and sys.argv[1] in ('source','receive') and sys.argv[2] in ('CPU','GPU'),'Use source|receive CPU|GPU')
    mode,backend=sys.argv[1:];tag='upl_preload_handoff_'+mode+'_'+backend+'_r1';out=T/'outputs'/tag;seedroot=T/'outputs'/(tag+'_seed')
    paths={k:L/(tag+s) for k,s in dict(start='.start.json',call='.call.json',run='.run.json',log='.log',san='.sanitizer.log').items()}
    need(not out.exists() and not seedroot.exists() and not any(p.exists() for p in paths.values()),'Existing output/seed/partial receipt protected')
    frozen=[];handle=None;result=dict(stage=tag+'.run',tag=tag,mode=mode,backend=backend,passed=False,actual_exit=None,actual_Win32_exit=None,native_review_pending=True,native_decoder_invoked=False,automatic_next_solver=False,BAT_executed=False,SHA_scans=0,physical_acceptance=False)
    def bind(e):
        s=stat(e['path']);need((s['bytes'],s['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Consumed file changed: '+e['path']);frozen.append(s);return s
    def load(p):bind(stat(p));return read(p)
    try:
        a=load(A);need(a['passed'] is True and tag in a['allowed_jobs'],'Separate root admission required')
        for e in a['inputs']+a['prerequisites']:bind(e)
        bp=L/('upl_preload_handoff_'+('ReleaseCPU' if backend=='CPU' else 'Release')+'_r2.build.json');b=load(bp)
        need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and b['canonical_stats_unchanged'],'Matching new Release build is not closed')
        program=bind(b['program']);capture=bind(b['source_capture']);archive=bind(read(capture['path'])['archive']);exe=Path(program['path'])
        pre=None;pretime=None
        if mode=='receive':
            source='upl_preload_handoff_source_'+backend+'_r1';sr=load(L/(source+'.run.json'));nc=load(L/(source+'_native_r1.check.json'))
            need(sr['passed'] and sr['actual_exit']==sr['actual_Win32_exit']==0 and sr['actual_steps']==800 and sr['consumed_stats_unchanged'],'Same-backend source run is not closed')
            need(Path(sr['program']['path']).samefile(exe) and Path(sr['source_build']['path']).samefile(bp),'Source/receive must use the same closed new program/build')
            need(nc['passed'] and nc['original_native_guards_passed'] and nc['consumed_stats_unchanged'] and nc['qualified_elastic_PRE_verified'] is True,'Qualified source native review required')
            need(bind(nc['source_run'])==stat(L/(source+'.run.json')),'Native review belongs to another source run')
            call=read(bind(nc['reader_call'])['path']);need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0,'Actual source reader exits are not zero')
            d=read(bind(nc['native_completion'])['path'])
            need(d['input_run_tag']==source and d['completed_steps']==800 and d['qualified_PRE_read_by_current_helper'] is True and d['event_completed_step']==380,'Actual qualified source PRE completion differs')
            pre=Path(bind(nc['certified_pre_file'])['path']);wanted=T/'outputs'/source/'data'/('Part_%04d.bi4'%int(d['genuine_pre_event_part']))
            need(pre.samefile(wanted),'Certified PRE is not the original source PART')
            pretime=float(d['genuine_pre_event_time_s'])
            result.update(source_run=stat(L/(source+'.run.json')),source_native=stat(L/(source+'_native_r1.check.json')),source_pre_file=stat(pre),source_pre_time_s=pretime)
        original=T/'outputs/upl_ck2_release_short_r1_seed/CaseLianSaturatedColumnCollapse_ck2_release_short_r1'
        originals=[bind(stat(str(original)+s)) for s in ('.xml','.bi4','_Normals.nbi4')]
        text=Path(originals[0]['path']).read_bytes().decode('utf-8');root=ET.fromstring(text);events=root.findall('.//gravitypreload');params={p.get('key'):p.get('value') for p in root.findall('.//parameter')}
        need(len(events)==1 and events[0].get('time')=='0.00095' and events[0].get('release_mkbound')=='2' and not any(k in events[0].attrib for k in ('elastic_source','statefile')),'Original prepared event differs')
        need(all(float(params[k])==v for k,v in (('DtIni',2.5e-6),('DtFixed',2.5e-6),('TimeMax',.002),('TimeOut',.0001),('PartsOutMax',0))),'Original unchanged clock/loss control differs')
        attribute='elastic_source="true"' if mode=='source' else 'statefile='+quoteattr(str(pre))
        derived,n=re.subn(r'<gravitypreload\b[^>]*/>',lambda m:m[0][:-2]+attribute+' />',text);need(n==1,'Exactly one literal event tag required')
        check=ET.fromstring(derived);check.find('.//gravitypreload').attrib.pop('elastic_source' if mode=='source' else 'statefile')
        need(ET.tostring(check)==ET.tostring(root),'Derivation changed another input field')
        seedroot.mkdir();seed=seedroot/original.name;Path(str(seed)+'.xml').write_bytes(derived.encode('utf-8'))
        for suffix,e in zip(('.bi4','_Normals.nbi4'),originals[1:]):shutil.copy2(e['path'],str(seed)+suffix)
        seedfiles=[bind(stat(str(seed)+s)) for s in ('.xml','.bi4','_Normals.nbi4')]
        runtime=T/'outputs'/('upl_prestress_check_release_CPU_r1_runtime' if backend=='CPU' else 'upl_prestress_check_GPU_r1_runtime')
        for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
            e=bind(stat(runtime/name));dst=exe.parent/name
            if not dst.exists():shutil.copy2(e['path'],dst)
            bind(dict(e,path=str(dst.resolve())))
        bind(stat(__file__));bind(stat(T/'notes/upl_preload_handoff_test_r1.json'))
        need(not any((q.info['name'] or '').lower().startswith('dualsphysics') for q in psutil.process_iter(['name'])),'Another solver is active; no process is killed')
        target=[str(exe),*(['-cpu','-ompthreads:8'] if backend=='CPU' else ['-gpu:0']),'-stable','-mdbc_freeslip',str(seed),str(out),'-dirdataout','data','-svres','-nsteps:800']
        argv=target
        if backend=='GPU':
            san=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/compute-sanitizer/compute-sanitizer.exe');bind(stat(san));argv=[str(san),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(paths['san']),*target]
        owner=identity(psutil.Process());started=utc();wall=time.monotonic();errors=[];tool={};child=None
        result.update(program=program,source_build=stat(bp),source_capture=capture,source_archive=archive,seed=seedfiles,base_seed=originals,admission=stat(A),initial_completed_step=380 if mode=='receive' else 0,input_change=attribute)
        with paths['log'].open('xb') as stream:
            p=subprocess.Popen(argv,cwd=T.parent,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                tool=identity(psutil.Process(p.pid));need(tool['argv'][1:]==argv[1:] and tool['parent_pid']==owner['pid'],'Actual owned tool identity differs')
                if backend=='CPU':child=tool;need(Path(child['exe']).samefile(exe),'Actual CPU program differs')
            except Exception as e:errors.append(str(e))
            try:save(paths['start'],dict(stage=tag+'.start',owner=owner,tool=tool,solver=child,target_argv=target,program=program,working_directory=str(T.parent),consumed=frozen,admission=stat(A),direct_owner_no_scheduler=True,BAT_executed=False))
            except Exception as e:errors.append('Start receipt: '+str(e))
            print(json.dumps(dict(tag=tag,actual_tool_PID=p.pid,solver=child)),flush=True)
            while backend=='GPU' and p.poll() is None:
                if handle is None:
                    try:
                        for q in psutil.Process(p.pid).children(recursive=True):
                            try:
                                if q.name().lower()!=exe.name.lower() or not Path(q.exe()).samefile(exe):continue
                                child=identity(q);handle=K.OpenProcess(0x101000,False,q.pid);need(handle,'Could not retain actual solver handle')
                                need(child['argv'][1:]==target[1:] and child['parent_pid']==p.pid,'Actual GPU child identity differs');print(json.dumps(dict(actual_solver=child)),flush=True);break
                            except psutil.NoSuchProcess:continue
                    except psutil.NoSuchProcess:pass
                    except Exception as e:errors.append(str(e))
                time.sleep(.005)
            rc=p.wait();toolrc=solverrc=None
            try:
                toolrc=exitcode(int(p._handle));solverrc=toolrc if backend=='CPU' else exitcode(handle) if handle else None
            except Exception as e:errors.append(str(e))
        save(paths['call'],dict(stage=tag+'.call',owner=owner,tool=tool,solver=child,argv=argv,target_argv=target,working_directory=str(T.parent),program=program,actual_Popen_wait_exit=rc,actual_tool_Win32_exit=toolrc,actual_solver_Win32_exit=solverrc,typed_returncode_captured_first=type(rc) is int,ownership_errors=errors,started_utc=started,ended_utc=utc(),elapsed_s=time.monotonic()-wall,log=stat(paths['log']),BAT_executed=False))
        result.update(actual_exit=solverrc,actual_Win32_exit=solverrc,actual_tool_exit=toolrc,solver=child,start_record=stat(paths['start']) if paths['start'].exists() else None,actual_call=stat(paths['call']),elapsed_s=time.monotonic()-wall)
        need(child is not None and rc==toolrc==solverrc==0 and not errors,'Actual owned exits/identity failed; no retry')
        if backend=='GPU':
            santext=paths['san'].read_text(encoding='utf-8');need('ERROR SUMMARY: 0 errors' in santext and 'LEAK SUMMARY: 0 bytes leaked in 0 allocations' in santext,'Actual memcheck failed');result.update(memcheck_zero_errors_and_leaks=True,sanitizer_log=stat(paths['san']))
        text=(out/'Run.out').read_text(encoding='utf-8-sig');need('Finished execution (code=0).' in text and re.search(r'Excluded particles[.]+:\s*0(?:\s|$)',text),'Normal completion/no-exclusion failed')
        with (out/'Run.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f,delimiter=';'))
        need(len(rows)==1,'One actual Run summary required');r=rows[0];frames=int(r['PartFiles'])
        need(int(r['Steps'])==800 and r['Np']=='7060' and r['Nbound']==r['Nfixed']=='2060' and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'Actual global completed step/registry/exclusions differ')
        files=sorted((out/'data').glob('Part_*.bi4'));need(frames>0 and [q.name for q in files]==['Part_%04d.bi4'%i for i in range(frames)] and all(q.stat().st_size>0 for q in files),'Actual native membership differs')
        markers=[s for s in text.splitlines() if 'GravityPreload:' in s];released=[s for s in markers if 'phase=released' in s];imports=[s for s in markers if 'state imported file=' in s]
        need(len(released)==1 and 'completed_step=380 retired=260;' in released[0] and 'damping=OFF Shepard=OFF FreeSeepage=ON.' in released[0],'Actual one-shot release differs')
        need(len(imports)==(mode=='receive'),'Actual import marker count differs')
        if mode=='receive':
            match=re.search(r'actual=([^ ]+) completed_step=(\d+)',imports[0]);need(match is not None and float(match[1])==pretime and int(match[2])==380,'Imported actual clock/completed count differs')
            match=re.search(r'actual=([^ ]+) completed_step=(\d+)',released[0]);need(match is not None and float(match[1])==pretime and int(match[2])==380,'Release did not occur at the actual source PRE clock')
        result.update(passed=True,actual_steps=800,new_updates_from_completed_counters=420 if mode=='receive' else 800,saved_frames=frames,summary=r,event_markers=markers,Run_out=stat(out/'Run.out'),Run_csv=stat(out/'Run.csv'),native_file_names=[q.name for q in files],native_first_time_and_IDs_pending=True)
    except Exception as e:result.update(passed=False,first_failure=str(e))
    finally:
        if handle:K.CloseHandle(handle)
        try:result['consumed_stats_unchanged']=bool(frozen) and all(stat(e['path'])==e for e in frozen)
        except Exception:result['consumed_stats_unchanged']=False
        if not result['consumed_stats_unchanged']:result['passed']=False;result.setdefault('first_failure','Consumed stat changed')
        result['consumed']=frozen;save(paths['run'],result)
    print(json.dumps(dict(tag=tag,passed=result['passed'],actual_exit=result['actual_exit'],first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
