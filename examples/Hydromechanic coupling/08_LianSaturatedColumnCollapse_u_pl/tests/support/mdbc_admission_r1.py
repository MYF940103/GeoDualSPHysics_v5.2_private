"""One explicitly selected short solver OR offline reader job. No chain, watcher, retry or formal edits."""
import csv,datetime,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
import psutil
sys.path.insert(0,str(Path(__file__).parent))
from upl_material_release_native_r2_run import T,L,need,read,stat,save,identity,exitcode
TAG='mdbc_admission_r1';PLAN=T/'notes'/('mdbc_admission_r1.json')
def bind(e,consumed):
    actual=stat(e['path']);need((actual['bytes'],actual['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Consumed stat changed: '+e['path']);consumed[actual['path']]=actual;return actual

def invoke(tag,argv,consumed):
    paths={k:L/(tag+s)for k,s in [('start','.start.json'),('call','.call.json'),('log','.log')]};need(not any(p.exists()for p in paths.values()),'Existing original process records protected')
    owner=identity(psutil.Process());errors=[];child={};started=datetime.datetime.now(datetime.timezone.utc).isoformat();wall=time.monotonic()
    with paths['log'].open('xb')as f:
        p=subprocess.Popen(argv,cwd=T.parent,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            child=identity(psutil.Process(p.pid));need(child['parent_pid']==owner['pid']and Path(child['exe']).samefile(argv[0])and child['argv'][1:]==argv[1:],'Actual direct child identity differs')
        except Exception as e:errors.append(str(e))
        save(paths['start'],dict(owner=owner,child=child,argv=argv,consumed=list(consumed.values()),direct_owner_no_scheduler=True));print(json.dumps(dict(tag=tag,actual_child=child)),flush=True)
        rc=p.wait();actual=exitcode(int(p._handle))
    save(paths['call'],dict(owner=owner,child=child,argv=argv,actual_Popen_wait_exit=rc,actual_Win32_exit=actual,typed_exit_captured_first=type(rc)is int,ownership_errors=errors,started_utc=started,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_s=time.monotonic()-wall,log=stat(paths['log'])))
    need(not errors and type(rc)is int and rc==actual,'Actual direct ownership/exit capture failed');return rc,paths

def spec(profile,backend,variant):
    need(profile in ('column_dbc','source','periodic','cryer_static','cryer_dynamic')and backend in ('CPU','GPU')and variant in ('old','new'),'Undeclared selected job')
    need(variant=='new'or profile.startswith('cryer_'),'Old source/periodic controls are retained, never rerun');need(profile!='column_dbc'or(backend=='CPU'and variant=='new'),'One CPU negative admission only')
    plan=read(PLAN);cfg='DebugCPU'if backend=='CPU'else'Release'if profile=='source'else'Debug';build=L/(('mdbc_partition_'+cfg+'_r1'if variant=='new'else'upl_material_release_'+cfg+'_r3')+'.build.json')
    key=profile+'_'+backend if profile in ('source','periodic')else profile;config=Path(plan['configs'][key]);control=None
    if profile in ('source','periodic'):
        control=plan[profile+'_control'][backend];old=read(L/(control+'.run.json'));need(old['passed']and old['actual_exit']==old['actual_Win32_exit']==0,'Closed actual old solver control required');seed=[Path(e['path'])for e in old['seed']]
    else:
        base=Path(plan['column_seed']if profile=='column_dbc'else plan['cryer_seed'][profile]);seed=[Path(str(base)+suffix)for suffix in(('.xml','.bi4','_Normals.nbi4')if profile=='column_dbc'else('.xml','.bi4'))]
    steps=800 if profile=='source'else 256 if profile=='periodic'else 2;frames=22 if profile=='source'else 5 if profile=='periodic'else 3;xml=config.read_text(encoding='utf-8');dt=float(re.search(r'<parameter\s+key="DtFixed"\s+value="([^"]+)"',xml)[1]);return plan,cfg,build,config,seed,steps,frames,dt,control

def run(profile,backend,variant):
    tag=TAG+'_'+profile+'_'+backend+'_'+variant;out=T/'outputs'/tag;seedout=T/'outputs'/(tag+'_seed');record=L/(tag+'.run.json');need(not any(p.exists()for p in(out,seedout,record)),'Existing/partial selected job protected')
    c={};result=dict(stage=tag,passed=False,solver_invocations=0,native_decoder_invocations=0,physical_acceptance=False,SHA_scans=0)
    try:
        plan,cfg,bp,config,original,steps,frames,dt,control=spec(profile,backend,variant)
        for p in(PLAN,Path(__file__),bp,config,*original):bind(stat(p),c)
        build=read(bp);need(build['passed']and build['actual_typed_exit_code']==build['actual_Win32_exit']==0 and build['source_stats_unchanged']and build['canonical_and_package_stats_unchanged'],'Matching frozen same-configuration build required');program=bind(build['program'],c);bind(build['source_capture'],c);exe=Path(program['path']);need(exe.parent.name==('mdbc_partition_'+cfg+'_r1'if variant=='new'else'upl_material_release_'+cfg+'_r3'),'Exact isolated program directory differs')
        if control:
            old=read(L/(control+'.run.json'));bind(stat(L/(control+'.run.json')),c);need(Path(old['source_build']['path']).name=='upl_material_release_'+cfg+'_r3.build.json','Historical control is another compiler configuration');d=read(L/(control+'.native.check.json'));need(d['passed']and d['original_native_guards_passed']and d['consumed_stats_unchanged'],'Historical all-native safety control not closed');bind(stat(L/(control+'.native.check.json')),c)
        if profile=='column_dbc':need('<mdbcslip'not in config.read_text(encoding='utf-8'),'Old per-MK slip guard would preempt new Hydro-wall negative')
        runtime=T/'outputs'/('upl_prestress_check_'+backend+'_r1_runtime')
        for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
            src=bind(stat(runtime/name),c);dst=exe.parent/name
            if not dst.exists():need(variant=='new','Retained old program runtime is incomplete; never mutate it');shutil.copy2(src['path'],dst)
            now=stat(dst);need((now['bytes'],now['mtime_ns'])==(src['bytes'],src['mtime_ns']),'Actual runtime differs');bind(now,c)
        active=[q.info for q in psutil.process_iter(['exe','cmdline']) if q.info['exe'] and (os.path.normcase(str(Path(q.info['exe']).resolve()))==os.path.normcase(str(exe.resolve())) or any(os.path.normcase(str(Path(a).resolve()))==os.path.normcase(str(out.resolve()))for a in(q.info['cmdline']or[])[1:]if Path(a).is_absolute()))]
        need(not active,'Selected isolated program or output is already owned by an active process; no process is stopped')
        seedout.mkdir();prefix=seedout/original[0].stem;shutil.copy2(config,str(prefix)+'.xml')
        for suffix,p in zip(('.bi4','_Normals.nbi4'),original[1:]):shutil.copy2(p,str(prefix)+suffix)
        seed=[stat(str(prefix)+suffix)for suffix in(('.xml','.bi4','_Normals.nbi4')if len(original)==3 else('.xml','.bi4'))]
        for e in seed:bind(e,c)
        argv=[str(exe),*(['-cpu','-ompthreads:8']if backend=='CPU'else['-gpu:0']),'-stable',*(['-dbc']if profile=='column_dbc'else['-mdbc_freeslip']if profile=='source'else[]),str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:'+str(steps)]
        result.update(profile=profile,backend=backend,variant=variant,configuration=cfg,program=program,source_build=stat(bp),config=stat(config),seed=seed,old_control_tag=control,planned_steps=steps,planned_frames=frames,dt_s=dt,output=str(out));result['solver_invocations']=1;rc,paths=invoke(tag,argv,c);result.update(actual_exit=rc,actual_Win32_exit=rc,start_record=stat(paths['start']),actual_call=stat(paths['call']))
        log=paths['log'].read_text(encoding='utf-8-sig',errors='replace');runout=out/'Run.out';text=runout.read_text(encoding='utf-8-sig',errors='replace')if runout.exists()else log
        if profile=='column_dbc':
            expected=plan['negative_expected_first_error'];need(rc==1 and expected in text and not any(s in text for s in('mdbcslip requires','mdbcslip is only','SoilBoundaryDerivativeSPR requires')),'Negative did not reach the new Hydro-wall first cause');need(not list((out/'data').glob('Part_*.bi4')),'Negative admission unexpectedly reached native saves');result.update(passed=True,expected_rejection_verified=True,first_cause=expected)
        else:
            need(rc==0 and'Finished execution (code=0).'in text,'Actual selected solver did not finish normally')
            with(out/'Run.csv').open(encoding='utf-8-sig',newline='')as f:rows=list(csv.DictReader(f,delimiter=';'))
            need(len(rows)==1,'One actual summary required');r=rows[0];need(int(r['Steps'])==steps and int(r['PartFiles'])==frames and all(int(r[k])==0 for k in('PartsOut','PartsOutRhop','PartsOutVel')),'Actual bounded summary/safety failed');parts=sorted((out/'data').glob('Part_*.bi4'));need([p.name for p in parts]==['Part_%04d.bi4'%i for i in range(frames)],'Native sequence differs')
            if variant=='new'and profile=='cryer_dynamic':need('Dynamic free body:'in text,'Actual admitted dynamic free-body log missing')
            if variant=='new'and profile=='cryer_static':need('Hydromechanical no-wall body:'in text and'cDBC disabled.'in text,'Actual admitted static no-wall body log missing')
            result.update(passed=True,actual_steps=steps,saved_frames=frames,summary=r,Run_out=stat(runout),Run_csv=stat(out/'Run.csv'),native_review_pending=True,noWall_log_verified=variant=='new'and profile.startswith('cryer_'),periodic_NoWall_branch_observation='Npb0 plus final Boundary=DBC; no separate native NoWall metadata'if profile=='periodic'else None)
    except Exception as e:result['first_failure']=str(e)
    result['consumed_stats_unchanged']=bool(c)and all(stat(e['path'])==e for e in c.values());result['passed']=result['passed']and result['consumed_stats_unchanged'];result['consumed']=list(c.values());save(record,result);print(json.dumps(dict(tag=tag,passed=result['passed'],first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed']else 1

def decode(tag):
    need(tag.startswith(TAG+'_')and'..'not in tag and'/'not in tag and'\\'not in tag,'Exact selected native tag required');record=L/(tag+'.run.json');r=read(record);need(r['passed']and r.get('actual_exit')==0 and r['consumed_stats_unchanged'],'Closed positive original run required');out=T/'outputs'/(tag+'_native');cp=L/(tag+'.native.check.json');need(not out.exists()and not cp.exists(),'Existing/partial decode protected')
    c={};bpath=L/'mdbc_admission_native_r2.build.json';b=read(bpath);need(b['passed']and b['consumed_stats_unchanged']and not b['JSph_objects_linked'],'Closed generic BI4 utility reader required')
    for p in(record,bpath,Path(__file__)):bind(stat(p),c)
    for e in r['consumed']:bind(e,c)
    for e in(b['program'],b['source']):bind(e,c)
    data=Path(r['output'])/'data'
    for p in sorted(data.glob('Part_*.bi4')):bind(stat(p),c)
    exe=Path(b['program']['path']);need(not any((q.info['name']or'').lower()==exe.name.lower()and q.info.get('exe')and Path(q.info['exe']).samefile(exe)for q in psutil.process_iter(['name','exe'])),'This reader is already active')
    argv=[str(exe),r['profile'],str(data),repr(r['dt_s']),str(r['saved_frames']),str(r['actual_steps']),str(out),'AUTHORIZED'];rc,paths=invoke(tag+'.native',argv,c);d=read(out/'completion.json')if(out/'completion.json').exists()else{};passed=rc==0 and d.get('passed')and d.get('samples')==r['saved_frames']and d.get('completed_steps')==r['actual_steps']and d.get('profile')==r['profile'];unchanged=all(stat(e['path'])==e for e in c.values())
    save(cp,dict(passed=bool(passed and unchanged),source_run=stat(record),reader_build=stat(bpath),actual_exit=rc,actual_Win32_exit=rc,actual_call=stat(paths['call']),native_completion=stat(out/'completion.json')if d else None,actual_completion=d,files=[stat(p)for p in sorted(out.iterdir())if p.is_file()]if out.exists()else[],consumed=list(c.values()),consumed_stats_unchanged=unchanged,original_native_guards_passed=bool(passed),physical_acceptance=False,SHA_scans=0));print('NATIVE_CHECK',cp,bool(passed and unchanged),flush=True);return 0 if passed and unchanged else 1

if __name__=='__main__':
    need(sys.argv[-1:] == ['--execution-authorized'],'Explicit execution authorization required')
    if len(sys.argv)==6 and sys.argv[1]=='run':raise SystemExit(run(*sys.argv[2:5]))
    if len(sys.argv)==4 and sys.argv[1]=='decode':raise SystemExit(decode(sys.argv[2]))
    raise RuntimeError('Use run PROFILE CPU|GPU old|new --execution-authorized OR decode TAG --execution-authorized')
