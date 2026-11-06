"""Own exactly one root-admitted Release short case; never decode or launch a next case."""
import csv,ctypes,datetime,json,re,shutil,subprocess,sys,time,xml.etree.ElementTree as ET
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];L=T/'logs';A=L/'upl_gravity_release_short_r1.admission.json'
def need(b,s):
    if not b:raise RuntimeError(s)
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,d):
    with p.open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def identity(q):return dict(pid=q.pid,created_epoch=q.create_time(),exe=q.exe(),argv=q.cmdline(),parent_pid=q.ppid())
def admission_entry(e):
    m=re.fullmatch(r'(.{19})(?:\.(\d{1,9}))?(?:Z|\+00:00)?',e['LastWriteTimeUtc']);need(m is not None,'UTC admission timestamp required')
    ns=int(datetime.datetime.strptime(m[1].replace(' ','T'),'%Y-%m-%dT%H:%M:%S').replace(tzinfo=datetime.timezone.utc).timestamp())*10**9+int((m[2] or '').ljust(9,'0'))
    return dict(path=e['Path'],bytes=e['Length'],mtime_ns=ns)
def main():
    need(len(sys.argv)==3 and sys.argv[1] in ('off','on') and sys.argv[2] in ('CPU','GPU'),'Usage: script off|on CPU|GPU')
    mode,backend=sys.argv[1:];tag='upl_gravity_release_'+mode+'_'+backend+'_r1';out=T/'outputs'/tag;paths={k:L/(tag+s) for k,s in dict(start='.start.json',call='.call.json',run='.run.json',log='.log').items()}
    need(not out.exists() and not any(p.exists() for p in paths.values()),'Existing output/partial receipt protected')
    frozen=[];result=dict(stage=tag+'.run',tag=tag,passed=False,actual_exit=None,actual_Win32_exit=None,native_review_pending=True,physical_acceptance=False,native_decoder_invoked=False,automatic_next_solver=False,BAT_executed=False,SHA_scans=0)
    def bind(e):
        s=stat(e['path']);need((s['bytes'],s['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Frozen file changed: '+e['path']);frozen.append(s);return s
    def load(p):bind(stat(p));return read(p)
    try:
        a=load(A);need(a['passed'] is True and tag in a['allowed_jobs'],'Separate root admission required')
        for e in a['inputs']:bind(admission_entry(e))
        for conf in ('DebugCPU','Debug','ReleaseCPU','Release'):
            b=load(L/('upl_gravity_release_'+conf+'_r1.build.json'));need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0,'Current build gate failed')
        build=L/('upl_gravity_release_'+('ReleaseCPU' if backend=='CPU' else 'Release')+'_r1.build.json');b=read(build);program=bind(b['program']);capture=bind(b['source_capture']);archive=bind(read(capture['path'])['archive']);exe=Path(program['path'])
        for kind in ('CPU','GPU'):
            gate=load(L/('upl_wall_retire_'+kind+'_r1.check.json'));need(gate['passed'] is True,'Retirement component gate failed')
        old='upl_prestress_check_'+('release_CPU' if backend=='CPU' else 'GPU')+'_r1';r=load(L/(old+'.run.json'));n=load(L/(old+'_native_r1.check.json'))
        need(r['passed'] and r['actual_exit']==0 and r['actual_steps']==400 and r['saved_frames']==11 and r['consumed_stats_unchanged'] and n['passed'] and n['original_native_guards_passed'] and n['consumed_stats_unchanged'],'Retained same-backend control not closed');bind(n['native_completion'])
        seed=T/('outputs/upl_prestress_check_r1_seed/CaseLianSaturatedColumnCollapse_prestress_check_r1' if mode=='off' else 'outputs/upl_gravity_release_on_r1_seed/CaseLianSaturatedColumnCollapse_releasecheck_r1');seedfiles=[bind(stat(str(seed)+s)) for s in ('.xml','.bi4','_Normals.nbi4')]
        root=ET.parse(str(seed)+'.xml').getroot();params={p.get('key'):p.get('value') for p in root.findall('.//parameter')};event=root.findall('.//gravitypreload');steps=400 if mode=='off' else 800
        need(all(float(params[k])==v for k,v in (('DtIni',2.5e-6),('DtFixed',2.5e-6),('TimeMax',.001 if mode=='off' else .002),('TimeOut',.0001))),'Prepared clock input differs')
        need(not event if mode=='off' else len(event)==1 and float(event[0].get('time'))==.00095 and event[0].get('release_mkbound')=='2' and float(params['PartsOutMax'])==0,'Prepared event input differs')
        for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
            source=bind(stat(T/'outputs'/(old+'_runtime')/name));dst=exe.parent/name
            if not dst.exists():shutil.copy2(source['path'],dst)
            s=stat(dst);need((s['bytes'],s['mtime_ns'])==(source['bytes'],source['mtime_ns']),'Shared runtime differs');bind(s)
        bind(stat(__file__));bind(stat(T/'notes/upl_gravity_release_short_r1.json'))
        need(not any((q.info['name'] or '').lower().startswith('dualsphysics') for q in psutil.process_iter(['name'])),'Another solver is active; no process is killed')
        argv=[str(exe),*(['-cpu','-ompthreads:8'] if backend=='CPU' else ['-gpu:0']),'-stable','-mdbc_freeslip',str(seed),str(out),'-dirdataout','data','-svres','-nsteps:'+str(steps)];owner=identity(psutil.Process());started=utc();wall=time.monotonic();errors=[]
        result.update(program=program,source_build=stat(build),source_capture=capture,source_archive=archive,seed=seedfiles,admission=stat(A),owner=owner)
        with paths['log'].open('xb') as f:
            p=subprocess.Popen(argv,cwd=T.parent,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);solver=dict(pid=p.pid)
            try:
                solver=identity(psutil.Process(p.pid));need(Path(solver['exe']).samefile(exe) and solver['argv'][1:]==argv[1:] and solver['parent_pid']==owner['pid'],'Actual child identity differs')
                save(paths['start'],dict(stage=tag+'.start',utc=utc(),owner=owner,solver=solver,program=program,argv=argv,working_directory=str(T.parent),consumed=frozen,admission=stat(A),direct_owner_no_scheduler=True,BAT_executed=False))
            except Exception as e:errors.append(str(e))
            print(json.dumps(dict(tag=tag,solver=solver,ownership_errors=errors)),flush=True);rc=p.wait();code=w.DWORD();K=ctypes.WinDLL('kernel32',use_last_error=True);K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];got=bool(K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)));win=code.value if got else None
            save(paths['call'],dict(stage=tag+'.run_call',actual_Popen_wait_exit=rc,actual_Win32_exit=win,typed_returncode_captured_first=type(rc) is int,program=program,argv=argv,working_directory=str(T.parent),solver=solver,started_utc=started,ended_utc=utc(),elapsed_s=time.monotonic()-wall,ownership_errors=errors,log=stat(paths['log']),BAT_executed=False))
        result.update(actual_exit=rc,actual_Win32_exit=win,solver=solver,start_record=stat(paths['start']) if paths['start'].exists() else None,actual_call=stat(paths['call']),elapsed_s=time.monotonic()-wall);need(got and rc==win==0 and not errors,'Owned exit/identity check failed')
        text=(out/'Run.out').read_text(encoding='utf-8-sig');need('Finished execution (code=0).' in text and re.search(r'Excluded particles[.]+:\s*0(?:\s|$)',text),'Normal finish/no-exclusion check failed')
        with (out/'Run.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f,delimiter=';'))
        need(len(rows)==1,'One Run.csv summary required');r=rows[0];count=int(r['PartFiles']);need(int(r['Steps'])==steps and r['Np']=='7060' and r['Nbound']==r['Nfixed']=='2060' and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'Actual steps/original counts/exclusions differ')
        files=sorted((out/'data').glob('Part_*.bi4'));need(count>1 and [p.name for p in files]==['Part_%04d.bi4'%i for i in range(count)] and all(p.stat().st_size>0 for p in files),'Actual PART membership incomplete')
        markers=[s for s in text.splitlines() if 'GravityPreload:' in s];released=[s for s in markers if 'phase=released' in s]
        need(not markers if mode=='off' else len(released)==1 and re.search(r'completed_step=380 retired=260;',released[0]) is not None and 'damping=OFF Shepard=OFF FreeSeepage=ON.' in released[0],'Actual event marker differs')
        result.update(passed=True,actual_steps=int(r['Steps']),saved_frames=count,summary=r,event_markers=markers,release_completed_step=380 if mode=='on' else None,retired=260 if mode=='on' else 0,Run_out=stat(out/'Run.out'),Run_csv=stat(out/'Run.csv'),native_file_names=[p.name for p in files],native_ID_count_not_yet_checked=True)
    except Exception as e:result.update(passed=False,failure=str(e))
    try:
        result['consumed_stats_unchanged']=bool(frozen) and all(stat(e['path'])==e for e in frozen);need(result['consumed_stats_unchanged'],'Consumed metadata changed')
    except Exception as e:result.update(passed=False,consumed_stats_unchanged=False,metadata_failure=str(e))
    result['consumed']=frozen;save(paths['run'],result);print(json.dumps(dict(tag=tag,passed=result['passed'],actual_exit=result['actual_exit'],run=str(paths['run']))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
