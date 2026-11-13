"""Three Wendland psi0 configurations, one explicitly admitted .90s job per run."""
import argparse,csv,json,os,re,shutil,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import c08_h18_plastic_matrix_r1 as old

base=old.base
T,C,L=base.T,base.C,base.L
need,read,stat,bind,save,invoke=base.need,base.read,base.stat,base.bind,base.save,base.invoke
verify,f32,table,signature=old.verify,old.f32,old.table,old.signature
TAG='c08_h18_wend_matrix_r1';NOTE=T/'notes'/(TAG+'.md');MANIFEST=T/'configs'/(TAG+'.jobs.json')
SOURCE_TAG='c08_h18_wend_psi0_pre_r2';SOURCE=T/'outputs'/SOURCE_TAG;PRE=SOURCE/'data/Part_1000.bi4';SOURCE_RUN=L/(SOURCE_TAG+'.run.json')
BUILD=L/'c08_preload_schema2_Release_r1.build.json';RUNTIME=T/'outputs/c08_preload_schema2_Release_r1'
NATIVE_BUILD=L/'c08_h18_wend_native_r1.build.json';NATIVE=T/'outputs/c08_h18_wend_native_r1_build/C08H18WendNative_win64.exe'
PLAN=T/'configs/c08_h18_release_w09_r2.steps.csv';SOURCE_PLAN=T/'configs/c08_h18_pre_r2.steps.csv'
JOBS=[('c08_h18_wend_psi0_a03_w09_r1',.3),('c08_h18_wend_psi0_a05_w09_r1',.5),('c08_h18_wend_psi0_a07_w09_r1',.7)]
DT=.000005;EVENT=2000000;END=2180000;SAMPLES=91;THREAD=old.THREAD
MATERIAL_KEYS={'Kernel',*old.MATERIAL_KEYS}


def notifier_path():
    found=shutil.which('codex')
    if found and Path(found).is_file():return Path(found).resolve()
    installed=list((Path.home()/'.vscode/extensions').glob('openai.chatgpt-*/bin/windows-x86_64/codex.exe'))
    return max(installed,key=lambda p:p.stat().st_mtime_ns) if installed else None


def schedule():
    rows=table(PLAN);source=table(SOURCE_PLAN);keys=['part','completed_step','saved_step','time_s','dt_s']
    need(len(rows)==91 and len(source)==1001 and list(rows[0])==list(source[0])==keys,'Original complete91/source1001 scalar plans required')
    scalar=0.;previous=0
    for i,q in enumerate(source):
        step=int(q['completed_step']);need(int(q['part'])==i and float(q['dt_s'])==DT and (step==int(q['saved_step'])==0 if i==0 else step>previous and int(q['saved_step'])==step-1),'Original source plan record differs')
        for _ in range(previous,step):scalar+=DT
        need(abs(float(q['time_s'])-scalar)<=1e-14,'Original source plan scalar replay differs');previous=step
    need(previous==EVENT,'Original source event differs');source_time=scalar
    for i,q in enumerate(rows):
        step=int(q['completed_step']);need(int(q['part'])==i and float(q['dt_s'])==DT and int(q['saved_step'])==step-1 and step>previous,'Original receiver plan record differs')
        for _ in range(previous,step):scalar+=DT
        need(abs(float(q['time_s'])-scalar)<=1e-14,'Original receiver plan scalar replay differs');previous=step
    need(int(rows[0]['completed_step'])==EVENT+1 and previous==END,'Actual first-post/end clock plan differs')
    return dict(duration_s=.9,end_completed_step=END,samples=SAMPLES,first_actual_time_s=float(rows[0]['time_s']),actual_end_s=scalar),dict(preload_actual_end_s=source_time),rows


def expected(coefficient):
    # Reuse only the frozen numerical tree constructor; no old source is read.
    x=old.expected(coefficient,'psi0');g=x.find('execution/special/gravitypreload');g.set('statefile',str(PRE.resolve()));g.set('elastic_source','false');g.set('keep_bed_overlap','false');g.set('comment','Import only the qualified same-material Wendland schema2 PRE; original histories retained')
    pars={q.get('key'):q for q in x.findall('execution/parameters/parameter')};need('Kernel' in pars,'Original receiver Kernel parameter missing');pars['Kernel'].set('value','2');pars['Kernel'].set('comment','Wendland H1.8; weights/gradients differ from the retained Cubic source')
    pars['DtFixed'].set('comment','Fixed5us; original coupled necessary-step checks remain');x.find('casedef/constantsdef/hdp').set('comment','Same H/dp=1.8 and support2H as this Wendland source')
    return x


def check_input(path,coefficient,generated=False):
    actual=ET.parse(path).getroot();want=expected(coefficient)
    if generated:
        need(all(signature(actual.find(q))==signature(want.find(q)) for q in ('execution/special','execution/parameters')),'Actual generated physical sections differ')
        ct=actual.find('execution/constants');need(float(ct.find('h').get('value'))==.072 and float(ct.find('dp').get('value'))==.04,'Actual generated H/dp differs')
        particles=actual.find('execution/particles');need([particles.get(k) for k in ('np','nb','nbf')]==['7060','2060','2060'] and [(q.get('mkbound'),q.get('begin'),q.get('count')) for q in particles.findall('fixed')]==[('0','0','255'),('1','255','1550'),('2','1805','255')] and [(q.get('begin'),q.get('count')) for q in particles.findall('fluid')]==[('2060','5000')],'Actual bed-last original ID registry differs')
    else:need(signature(actual)==signature(want),'Undeclared receiver configuration change')
    pars={q.get('key'):q.get('value') for q in actual.findall('execution/parameters/parameter')};need(len(pars)==len(actual.findall('execution/parameters/parameter')),'Duplicate receiver parameter')
    for key,value in dict(Kernel=2,DtIni=DT,DtFixed=DT,TimeMax=10.9,TimeOut=.01,DPCtes=3,SavePosDouble=1,NoPenetration=1,ArtificialStress=1,ArtificialStressCoef=coefficient,ArtificialStressExp=3.825,PartsOutMax=0).items():need(f32(pars[key])==f32(value),'Actual receiver parameter differs: '+key)
    g=actual.find('execution/special/gravitypreload');need(Path(g.get('statefile')).samefile(PRE) and g.get('elastic_source')==g.get('keep_bed_overlap')=='false' and float(g.get('time'))==10 and g.get('release_mkbound')=='2','Actual source/phase/retirement differs')
    return actual


def actual_material(root):
    p={q.get('key'):q.get('value') for q in root.findall('execution/parameters/parameter')};result={'Kernel':p['Kernel'],**old.entries(root,'psi0')};need(set(result)==MATERIAL_KEYS and f32(result['Kernel'])==f32(2),'Actual fifteen-key Wendland material required');return result


def match_material(left,right):
    need(set(left)==set(right)==MATERIAL_KEYS,'Actual source/target material key coverage differs')
    for key,value in left.items():need(value==right[key] if key in ('group','fresh_trigger_active') else f32(value)==f32(right[key]),'Same-material source/target mismatch: '+key)


def build_context():
    # This helper binds the actual frozen schema2 binary/source and copied runtime.
    b,program,before,runtime=old.pre.build_context();need(program.parent==RUNTIME and b['configuration']=='Release','Only the frozen schema2 Release program allowed')
    before += [stat(q) for q in (Path(__file__),NOTE,Path(old.__file__),Path(old.old.__file__),old.ROOT)]
    return b,program,before,runtime


def prepare():
    need(not MANIFEST.exists(),'Existing preparation protected');w,p,rows=schedule();b,program,before,runtime=build_context();jobs=[]
    for tag,_ in JOBS:need(not (T/'outputs'/tag).exists() and not (T/'configs'/(tag+'_Def.xml')).exists() and not (T/'configs'/('x'+tag+'_win64_GPU.bat')).exists(),'Existing prepared/partial job protected')
    for tag,coefficient in JOBS:
        config=T/'configs'/(tag+'_Def.xml');bat=T/'configs'/('x'+tag+'_win64_GPU.bat')
        with config.open('xb') as f:f.write(ET.tostring(expected(coefficient),encoding='utf-8',xml_declaration=True)+b'\n')
        check_input(config,coefficient)
        body='@echo off\r\nsetlocal\r\nset "PYTHON=D:\\anaconda3\\python.exe"\r\nif not exist "%PYTHON%" set "PYTHON=python"\r\n"%PYTHON%" -X utf8 -B "%~dp0..\\support\\c08_h18_wend_matrix_r1.py" run --job '+tag+' --execution-authorized --notify\r\nset "EC=%ERRORLEVEL%"\r\nif not "%~1"=="--unattended" pause\r\nexit /b %EC%\r\n'
        with bat.open('xb') as f:f.write(body.encode('ascii'))
        jobs.append(dict(tag=tag,group='psi0',Kernel=2,AS_coefficient=coefficient,AS_exponent=3.825,configuration=stat(config),BAT=stat(bat),plan=stat(PLAN),end_completed_step=END,samples=SAMPLES,output=str(T/'outputs'/tag)))
    before += [stat(PLAN),stat(SOURCE_PLAN)];verify(before)
    save(MANIFEST,dict(stage=TAG+'.prepare',prepared_only=True,kernel=2,kernel_name='Wendland',hdp=1.8,fixed_dt_s=DT,geometry_profile='bedroles',keep_bed_overlap=False,source_run=stat(SOURCE_RUN),source_pre=stat(PRE),source_qualification_not_claimed=True,program=stat(program),source_build=stat(BUILD),jobs=jobs,source_plan=stat(SOURCE_PLAN),receiver_plan=stat(PLAN),consumed=before,consumed_stats_unchanged=True,GenCase_invocations=0,solver_invocations=0,native_invocations=0,automatic_next_job=False,physical_acceptance=False));print('WENDLAND_MATRIX_PREPARED',MANIFEST,flush=True)


def context(tag,notify):
    a=read(L/(tag+'.admission.json'));m=read(MANIFEST);w,p,rows=schedule();coefficient=dict(JOBS)[tag];row=next(q for q in m['jobs'] if q['tag']==tag);b,program,before,runtime=build_context()
    need(a['passed'] and a['allowed_job']==tag and a['group']=='psi0' and a['kernel']==2 and a['kernel_name']=='Wendland' and a['matrix_manifest']==stat(MANIFEST) and a['input_xml']==row['configuration'] and a['planned_steps']==stat(PLAN) and a['planned_global_end']==END and a['expected_saved_frames']==SAMPLES and f32(a['AS_coefficient'])==f32(coefficient) and f32(a['AS_exponent'])==f32(3.825) and a['source_review_allows_AS_screen'] and a['native_auto_authorized'] is False,'Exact independently reviewed single Wendland job admission required')
    need(m['prepared_only'] and m['kernel']==2 and m['source_pre']==stat(PRE) and m['source_run']==stat(SOURCE_RUN) and m['receiver_plan']==stat(PLAN) and m['source_plan']==stat(SOURCE_PLAN) and len(m['jobs'])==3 and m['consumed_stats_unchanged'] and row['group']=='psi0' and row['Kernel']==2 and row['AS_coefficient']==coefficient and row['AS_exponent']==3.825 and row['samples']==SAMPLES and row['end_completed_step']==END and row['plan']==stat(PLAN) and Path(row['output'])==T/'outputs'/tag,'Prepared single job/clock differs');check_input(bind(row['configuration'])['path'],coefficient)
    for key,value in dict(program=stat(program),source_build=stat(BUILD),source_capture=b['source_capture'],source_archive=b['source_archive']).items():need(bind(a[key])==value,'Root physical program/source binding differs: '+key)
    need(Path(bind(a['source_run'])['path']).samefile(SOURCE_RUN),'Only the actual completed Wendland psi0 source allowed');sr=read(SOURCE_RUN)
    need(sr['passed'] and sr['solver_completed'] and sr['actual_exit']==sr['actual_Win32_exit']==0 and sr['group']=='psi0' and sr['kernel']==2 and sr['elastic_source'] is False and sr['material']==dict(coh=5000.,dlt=0.,DilationDecay=0.) and sr['actual_steps']==EVENT and sr['saved_frames']==1001 and sr['consumed_stats_unchanged'] and sr['source_pre_file']==stat(PRE) and sr['program']==stat(program) and sr['source_build']==stat(BUILD) and sr['source_capture']==b['source_capture'] and sr['source_archive']==b['source_archive'],'Complete own-material/kernel2 source required; old failed Cubic sources forbidden')
    source_call=read(bind(sr['actual_call'])['path']);need(source_call['actual_solver_Win32_exit']==source_call['actual_Popen_wait_exit']==source_call['actual_Win32_exit']==0 and not source_call['ownership_errors'] and source_call['arguments']==sr['argv'] and Path(source_call['actual_solver']['exe']).samefile(program),'Actual completed source owned exits/program/argv differ')
    sd=read(bind(a['source_native'])['path']);sc=read(bind(a['source_native_call'])['path']);nb=read(bind(a['native_build'])['path']);need(Path(a['native_build']['path']).samefile(NATIVE_BUILD),'Explicit Wendland native build required')
    need(sd['passed'] and sd['stage']=='c08_h18_wend_native_r1.source' and sd['group']=='psi0' and sd['same_material_plastic_PRE'] and sd['expected_handoff_schema']==2 and sd['source_group_certificate_checked'] and sd['source_yield_uses_actual_kappa'] and sd['declared_Kernel_XML_CSV']==2 and sd['source_event_contract_kernel_checked'] and sd['source_material_CSV_keys']==15 and sd['geometry_profile']=='bedroles' and sd['release_target_ID_begin']==1805 and sd['release_target_ID_count']==255 and sd['keep_bed_overlap'] is False and sd['certified_PRE'] and not sd['partial'] and sd['samples']==1001 and sd['completed_steps']==EVENT and sd['actual_end_s']==p['preload_actual_end_s'] and not sd['runtime_success_claimed'] and not sd['physical_acceptance'],'Actual full Wendland schema2 native qualification required')
    need(nb['passed'] and nb['consumed_stats_unchanged'] and nb['declared_Kernel_XML_CSV']==2 and nb['source_material_CSV_keys']==15 and nb['receiver_material_CSV_keys']==17 and nb['program']==stat(NATIVE) and nb['physical_source_archive']==b['source_archive'] and nb['actual_link_objects']==7 and len(nb['objects'])==6 and not nb['JSph_objects_linked'],'Closed passed Wendland reader build required')
    need(sc['actual_Popen_wait_exit']==sc['actual_Win32_exit']==0 and sc['ownership_failure'] is None and Path(sc['program'])==NATIVE and len(sc['arguments'])==6 and sc['arguments'][:2]==['--source','full'] and Path(sc['arguments'][2])==SOURCE/'data' and Path(sc['arguments'][3])==Path(a['source_material_profile']['path']) and Path(sc['arguments'][4])==SOURCE_PLAN and Path(sc['arguments'][5])==Path(a['source_native']['path']).parent,'Actual unique full source native invocation differs')
    source_material_rows=table(bind(a['source_material_profile'])['path']);need(len(source_material_rows)==15 and all(list(q)==['key','value'] for q in source_material_rows),'Actual source15-key CSV required');source_material={q['key']:q['value'] for q in source_material_rows};match_material(source_material,actual_material(ET.parse(bind(sr['input_xml'])['path']).getroot()))
    thread=os.environ.get('CODEX_THREAD_ID');need(not notify or (a['root_thread_id']==thread==THREAD and notifier_path() is not None),'Only actual admitted root thread may queue once')
    before += [stat(q) for q in (MANIFEST,PLAN,SOURCE_PLAN,L/(tag+'.admission.json'),SOURCE_RUN,PRE,PRE.parent/'Part_Head.ibi4',NATIVE_BUILD)]+[bind(q) for q in m['consumed']]+[bind(row[k]) for k in ('configuration','BAT')]+[bind(a[k]) for k in ('source_native','source_native_call','source_material_profile','source_physical_review')]+[bind(sr[k]) for k in ('actual_call','input_xml')]+[bind(nb[k]) for k in ('program','source','core_derivation')]+[bind(q) for q in nb['calls']]
    verify(before);old.old.idle(True)
    return a,row,coefficient,b,program,before,runtime,thread,w,p,source_material


def write_profile(path,root,coefficient,source_material):
    result=actual_material(root);match_material(result,source_material);pars={q.get('key'):q.get('value') for q in root.findall('execution/parameters/parameter')};result.update(ArtificialStressCoef=pars['ArtificialStressCoef'],ArtificialStressExp=pars['ArtificialStressExp']);need(len(result)==17 and f32(result['ArtificialStressCoef'])==f32(coefficient) and f32(result['ArtificialStressExp'])==f32(3.825),'Actual receiver17-key profile differs')
    with path.open('x',encoding='utf-8',newline='') as f:w=csv.writer(f);w.writerow(('key','value'));w.writerows(result.items())


def notify_once(tag,rp):
    attempt=L/(tag+'.queue_attempt.json');reply=L/(tag+'.queue_result.json');need(not attempt.exists() and not reply.exists(),'Terminal queue already attempted; never resend')
    program=notifier_path();message=('The single admitted Wendland C08 psi0 .90s AS window is terminal: '+str(rp)+'. Read original run/start/call/status/root and owner admissions, true exits, program/source/PRE/input/plan bindings. Kernel2 H1.8/5us, same full Wendland schema2 psi0 PRE with actual kappa retained, contiguous bed-last retire255/keepfalse, NoPen FixedPlaneStageProjectionReleaseOnly/ReactionClosed=false, total-AS coefficient as recorded at exponent3.825, original AV.1/CompletedOnly. One91-frame window only; no next epsilon/psi/formal/native/VTK run is automatic. Require the actual loader contract2 and first-post+1 clock; P0 bit inheritance and kappa histories are original native checks. Updated first-frame sigma/J cannot prove pre-update bit equality with PRE; report actual changes without fabricating an initial receiver save. Existing loader/unit and old schema1 regression are implementation evidence only. After safe genuine completion root independently authorizes a unique Wendland17-key receiver read and physical pressure/NN/kappa/J/motion review. Exit0/normal safety is not physics or parameter selection. Preserve failure/partials/last actual console, no invented unsaved time, duplicate solver or overwrite. This owner queues once with45s timeout; uncertain delivery never resends/rearms.')
    argv=[str(program) if program is not None else 'codex','queue','--thread',THREAD,'--message',message];save(attempt,dict(stage=tag,utc=base.utc(),thread=THREAD,run=stat(rp),program=stat(program) if program is not None else None,arguments=argv,attempts=1,timeout_s=45,do_not_resend=True));result=dict(stage=tag,attempts=1,do_not_resend=True)
    try:
        need(program is not None,'No current notifier executable; terminal run remains preserved')
        q=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW);result.update(actual_exit=q.returncode,status='queued' if q.returncode==0 else 'queue_failed',stdout=q.stdout,stderr=q.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(reply,result)


def run(tag,notify):
    out=T/'outputs'/tag;rp=L/(tag+'.run.json');ad=L/(tag+'.admission.json');need(not out.exists() and not any(q.name!=ad.name for q in L.glob(tag+'.*')),'Existing job/owner/output protected; no retry');claim=L/(tag+'.claim.json');save(claim,dict(stage=tag,owner_pid=os.getpid(),owner_created_epoch=psutil.Process().create_time(),single_attempt=True));before=[];stage='preflight';result=dict(stage=tag,passed=False,solver_completed=False,group='psi0',kernel=2,kernel_name='Wendland',geometry_profile='bedroles',keep_bed_overlap=False,same_material_plastic_PRE=True,expected_source_handoff_schema=2,physical_acceptance=False,native_review_pending=True,automatic_next_job=False,selection_made=False,formal_jobs_started=0,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,PartVTK_invocations=0,SHA_scans=0)
    try:
        a,row,coefficient,b,program,before,runtime,thread,w,p,source_material=context(tag,notify);before.append(stat(claim));out.mkdir();prefix=out/tag;stage='GenCase';result['GenCase_invocations']=1;result['GenCase_call']=invoke(tag+'.gencase',[str(RUNTIME/'GenCase_win64.exe'),str(Path(row['configuration']['path']).with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml');actual=check_input(seed,coefficient,True);seeds=[stat(Path(str(prefix)+q)) for q in ('.xml','.bi4','_Normals.nbi4')];before+=seeds;profile=out/'native_profile.csv';write_profile(profile,actual,coefficient,source_material);before.append(stat(profile));verify(before)
        argv=[str(program),'-gpu:0','-stable','-mdbc_freeslip:1',str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:'+str(END)];ownerad=L/(tag+'.owner_admission.json');save(ownerad,dict(stage=tag,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(ad),matrix_manifest=stat(MANIFEST),program=stat(program),source_build=stat(BUILD),source_capture=b['source_capture'],source_archive=b['source_archive'],runtime=runtime,source_pre_file=stat(PRE),source_run=a['source_run'],source_native=a['source_native'],source_native_call=a['source_native_call'],source_material_profile=a['source_material_profile'],source_physical_review=a['source_physical_review'],input_xml=stat(seed),seed=seeds,planned_steps=stat(PLAN),planned_new_updates=180000,planned_global_end=END,expected_saved_frames=SAMPLES,Kernel=2,AS_coefficient=coefficient,AS_exponent=3.825,group='psi0',same_material_plastic_PRE=True,argv=argv,solver_argv=argv,consumed=before));before.append(stat(ownerad))
        result.update(program=stat(program),source_build=stat(BUILD),source_capture=b['source_capture'],source_archive=b['source_archive'],runtime=runtime,source_pre_file=stat(PRE),source_run=a['source_run'],source_native=a['source_native'],input_xml=stat(seed),seed=seeds,planned_steps=stat(PLAN),native_profile=stat(profile),owner_admission=stat(ownerad),argv=argv,AS_coefficient=coefficient,AS_exponent=3.825,hdp=1.8,fixed_dt_s=DT)
        stage='solver';result['solver_invocations']=1;result['actual_call']=base.owned(tag,argv,program,False,stat(ownerad));result.update(solver_returned_zero=True,actual_exit=0,actual_Win32_exit=0);stage='solver_output_review';result.update(old.old.output_checks(out,coefficient,w,p));text=(out/'Run.out').read_text(encoding='utf-8-sig')
        need('Wendland' in result['summary']['Configuration'] and '[Simulation INTERRUPTED' not in text and 'GravityPreload: source material law=unified2; certified same-material plastic schema/contract2; native stress/kappa/J/p history retained.' in text,'Actual kernel/completion/schema2 loader differs');verify(before);result.update(passed=True,solver_completed=True,first_saved_completed_step=EVENT+1,first_saved_time_s=w['first_actual_time_s'],source_continuity_scope='Actual contract2 import; first saved state is after one updated step, not a pre-update bit proof',native_argv=[str(NATIVE),'--receiver','window','psi0',str(out/'data'),str(PRE),str(PLAN),str(profile),str(out/'native_r1')],native_invocation_authorized_by_this_owner=False,consumed_stats_unchanged=True)
    except Exception as error:
        result.update(first_failure=str(error),failed_stage=stage);cp=L/(tag+'.call.json')
        if cp.exists():
            call=read(cp);result.update(actual_call=stat(cp),actual_exit=call['actual_solver_Win32_exit'],actual_Win32_exit=call['actual_solver_Win32_exit'],actual_tool_exit=call['actual_Popen_wait_exit'],ownership_errors=call['ownership_errors'])
        raw=out/'Run.out'
        if raw.exists():
            text=raw.read_text(encoding='utf-8-sig',errors='replace');hit=re.search(r'^Text: (.+)$',text,re.M);result.update(Run_out=stat(raw),first_engine_exception_text=hit[1] if hit else None)
    result.update(consumed=before,last_original_console_line=base.last_part(out),unsaved_failure_time_reconstructed=False);save(rp,result);base.publish(tag,out,None,None,'completed_pending_explicit_native_review' if result['passed'] else 'failed_preserved_no_next_job')
    if notify and (L/(tag+'.call.json')).exists():notify_once(tag,rp)
    print(json.dumps(dict(passed=result['passed'],run=str(rp),solver_completed=result['solver_completed'],first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','run'));parser.add_argument('--job',choices=[q[0] for q in JOBS]);parser.add_argument('--execution-authorized',action='store_true');parser.add_argument('--notify',action='store_true');args=parser.parse_args();need(args.execution_authorized and (args.action=='run' or not args.notify),'Root full-read and explicit action required');need((args.action=='run')==bool(args.job),'Run selects exactly one psi0 job; prepare writes only three inputs and manifest');prepare() if args.action=='prepare' else exit(run(args.job,args.notify))
