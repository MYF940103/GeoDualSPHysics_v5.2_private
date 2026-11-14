"""Author-only two fixed release-AV jobs; each needs separate root admission, never auto-native/next."""
import argparse,csv,os,re,struct,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import c08_h18_as03n255_full3_r1 as retained

m,base=retained.matrix,retained.base
T,C,L=m.T,m.C,m.L
need,read,stat,bind,save=m.need,m.read,m.stat,m.bind,m.save
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8'
NOTE=T/'notes/c08_h18_av20_run_r1.md'
JOBS={'smoke':dict(tag='c08_h18_av20_smoke_CPU_r1',configuration='DebugCPU',backend='CPU',end=2000400,samples=2,time=10.002,tout=.002,queue=False),
      'window':dict(tag='c08_h18_av20_window_GPU_r1',configuration='Release',backend='GPU',end=2180000,samples=91,time=10.9,tout=.01,queue=True)}


def paths(job):
    tag=job['tag'];return T/'configs'/(tag+'_Def.xml'),L/(tag+'.prepare.json'),L/(tag+'.admission.json'),T/'outputs'/tag


def plan(job):return T/'configs/c08_h18_av20_smoke_CPU_r1.steps.csv' if job['backend']=='CPU' else m.PLAN


def schedule(job,preload):
    rows=m.table(plan(job));need(len(rows)==job['samples'] and list(rows[0])==['part','completed_step','saved_step','time_s','dt_s'],'Exact original clock columns/count required');scalar=preload['preload_actual_end_s'];prior=2000000
    for i,q in enumerate(rows):
        step=(2000001 if i==0 else 2000400) if job['backend']=='CPU' else (2180000 if i==90 else 2000001+2000*i)
        need(int(q['part'])==i and int(q['completed_step'])==step and int(q['saved_step'])==step-1 and float(q['dt_s'])==5e-6,'Exact clock step/index/dt required')
        for _ in range(prior,step):scalar+=5e-6
        need(abs(float(q['time_s'])-scalar)<=1e-14,'Actual sequential scalar clock differs');prior=step
    need(prior==job['end'],'Actual forced endpoint differs');return rows


def input_check(path,control,job,generated=False):
    actual=ET.parse(path).getroot();expected=ET.parse(control).getroot()
    for key,value in (('TimeMax',job['time']),('TimeOut',job['tout'])):
        nodes=expected.findall("execution/parameters/parameter[@key='"+key+"']");need(len(nodes)==1,'One original time parameter required')
        if job['backend']=='CPU':nodes[0].set('value',str(value))
    sections=('execution/special','execution/parameters','execution/constants','execution/particles') if generated else (None,)
    need(all(m.signature(actual if k is None else actual.find(k))==m.signature(expected if k is None else expected.find(k)) for k in sections),'Only admitted duration/cadence may differ from original AS03 input')
    p={q.get('key'):q.get('value') for q in actual.findall('execution/parameters/parameter')}
    need(len(p)==len(actual.findall('execution/parameters/parameter')) and all(m.f32(p[k])==m.f32(v) for k,v in dict(Kernel=2,Visco=.1,DtFixed=5e-6,ArtificialStressCoef=.3,ArtificialStressExp=2.55,TimeMax=job['time'],TimeOut=job['tout']).items()),'XML retains exact certified AV.1/AS03/material context');return actual


def originals_and_build(job):
    control,ad,config,oldbuild,oldprogram,material,oldruntime,window,preload,consumed=retained.original_context()
    build=L/('c08_h18_av20_'+job['configuration']+'_r2.build.json');b=read(build);program=Path(bind(b['program'])['path']);capture=read(bind(b['source_capture'])['path']);baseline=read(bind(b['baseline_source_build'])['path'])
    need(b['passed'] and b['consumed_stats_unchanged'] and b['configuration']==job['configuration'] and b['allowed_runtime_backend']==job['backend'],'Exact private backend build required; GPU binary CPU path is not admitted')
    need(b['base_original_source_capture']==control['source_capture'] and b['base_original_source_archive']==control['source_archive'] and baseline['passed'] and baseline['consumed_stats_unchanged'] and bind(b['base_program'])==bind(baseline['program']) and baseline['source_capture']==control['source_capture'] and baseline['source_archive']==control['source_archive'],'Private/base/source-PRE origins must remain distinct and genuinely bound')
    need(capture['reverse_reconstruction_original_bytes_exact'] and capture['all_other_archive_member_bytes_exact'] and capture['only_release_AV_override_and_actual_metadata_changed'] and capture['released_AV_literal']=='.2f' and capture['preload_input_AV_literal']=='.1f' and not capture['trace_macros_enabled'],'Only reviewed release AV.2 plus actual output metadata intervention allowed')
    config_new,prep,admission,out=paths(job);input_check(config_new,config,job);schedule(job,preload)
    consumed.extend(stat(q) for q in (Path(__file__),NOTE,build,config_new,plan(job)));consumed.extend(bind(b[k]) for k in ('program','source_capture','source_archive','base_program','baseline_source_build','base_original_source_capture','base_original_source_archive'));runtime=[bind(q) for q in b['runtime']];consumed+=runtime
    gen=next(bind(q) for q in oldruntime if Path(q['path']).name=='GenCase_win64.exe');consumed.append(gen);m.verify(consumed)
    closure=dict(program=stat(program),source_build=stat(build),source_capture=b['source_capture'],source_archive=b['source_archive'],base_program=b['base_program'],base_source_build=b['baseline_source_build'],base_original_source_capture=control['source_capture'],base_original_source_archive=control['source_archive'],**{k:control[k] for k in ('source_pre_file','source_run','source_native')})
    return control,config,material,preload,closure,runtime,gen,consumed


def prepare(job):
    config,prep,admission,out=paths(job);need(os.environ.get('CODEX_THREAD_ID')==THREAD and config.is_file() and not out.exists() and not any(L.glob(job['tag']+'.*')),'Only actual root may prepare reviewed authored files; old evidence protected')
    control,oldconfig,material,preload,closure,runtime,gen,consumed=originals_and_build(job)
    save(prep,dict(stage=job['tag']+'.prepare',prepared_only=True,job=job,configuration=stat(config),control_configuration=stat(oldconfig),control_run=stat(retained.CONTROL_RUN),owner=stat(Path(__file__)),note=stat(NOTE),planned_steps=stat(plan(job)),**closure,runtime=runtime,GenCase_program=gen,consumed=consumed,consumed_stats_unchanged=True,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,physical_acceptance=False))


def context(job):
    config,prep,admission,out=paths(job);control,oldconfig,material,preload,closure,runtime,gen,consumed=originals_and_build(job);p,a=read(prep),read(admission)
    need(p['prepared_only'] and p['consumed_stats_unchanged'] and p['job']==job and p['configuration']==stat(config) and p['control_configuration']==stat(oldconfig) and p['control_run']==stat(retained.CONTROL_RUN),'Exact independently prepared job required')
    need(a['passed'] and a['allowed_job']==job['tag'] and a['root_full_read'] is True and a['prepared']==stat(prep) and a['input_xml']==stat(config) and a['job']==job and a['terminal_queue_once']==job['queue'] and a['root_thread_id']==os.environ.get('CODEX_THREAD_ID')==THREAD,'Separate current-root admission required')
    for q in (p,a):
        need(q['owner']==stat(Path(__file__)) and q['note']==stat(NOTE) and q['planned_steps']==stat(plan(job)) and all(q[k]==v for k,v in closure.items()),'Actual private program/source and original PRE closure differ')
    if job['backend']=='GPU':
        smoke=JOBS['smoke'];runpath=L/(smoke['tag']+'.run.json');r=read(runpath);native=read(bind(a['cpu_smoke_native'])['path']);d=read(bind(native['native_completion'])['path']);v=read(bind(native['metadata'])['path'])
        need(a['cpu_smoke_reviewed'] is True and a['cpu_smoke_run']==stat(runpath) and r['passed'] and r['solver_completed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==2000400 and r['saved_frames']==2 and native['passed'] and native['consumed_stats_unchanged'] and native['reader_invocations']==1,'GPU held until actual CPU smoke and separately admitted native review')
        need(d['passed'] and d['samples']==2 and d['completed_steps']==2000400 and d['typed_arrays']==22 and d['actual_native_IDs_per_frame']==6805 and d['backend_argument']=='CPU' and v['passed'] and v['stage']=='c08_h18_av20_native_r1.metadata' and v['AV_policy']=='ReleaseOnly' and v['AV_override_active_expected'] and v['AV_override_headers']==2 and v['AV_coefficient_float_reference']==struct.unpack('<f',struct.pack('<f',.2))[0] and v['backend_argument']=='CPU','All2 CPU headers must prove real typed release AV.2')
        consumed.append(stat(runpath));consumed.append(bind(a['cpu_smoke_native']));consumed.extend(bind(native[k]) for k in ('actual_call','native_completion','metadata','reader_build'))
    if job['queue']:need(m.notifier_path() is not None,'Current root notifier unavailable before long launch')
    consumed.extend(stat(q) for q in (prep,admission));consumed.extend(bind(q) for q in p['consumed']);consumed.append(bind(a['physical_decision']));m.verify(consumed);m.old.old.idle(True)
    return control,material,preload,closure,runtime,gen,consumed


def output_checks(job,out,preload):
    q=retained.previous.summary(out/'Run.csv');text=(out/'Run.out').read_text(encoding='utf-8-sig');parts=sorted((out/'data').glob('Part_*.bi4'))
    need(int(q['Steps'])==job['end'] and int(q['PartFiles'])==job['samples'] and int(q['Np'])==7060 and int(q['Nbound'])==int(q['Nfixed'])==2060 and all(int(q[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')) and float(q['H'])==.072 and float(q['Dp'])==.04 and bool('Gpu_' in q['Hardware'])==(job['backend']=='GPU'),'Actual no-loss run/backend/geometry/end differs')
    need('Kernel="Wendland"' in text and 'Finished execution (code=0).' in text and '[Simulation INTERRUPTED' not in text and 'Dynamic NoPen: '+base.POLICY in text and text.count('GravityPreload: phase=released ')==1 and text.count('GravityPreload: validated native right-wall range=[1805,2060), count=255.')==1 and 'retired=255; damping=OFF Shepard=OFF FreeSeepage=ON.' in text,'Actual completed release/safety context differs')
    imported=re.findall(r'GravityPreload: state imported file=.*? actual=([0-9.eE+-]+) completed_step=(\d+);',text)
    need(len(imported)==1 and int(imported[0][1])==2000000 and float(imported[0][0])==preload['preload_actual_end_s'] and [p.name for p in parts]==['Part_%04d.bi4'%i for i in range(job['samples'])],'Actual original PRE and complete save sequence required')
    return dict(actual_steps=job['end'],saved_frames=job['samples'],summary=q,Run_csv=stat(out/'Run.csv'),Run_out=stat(out/'Run.out'),PART_head=stat(out/'data/Part_Head.ibi4'),PARTs=[stat(p) for p in parts])


def notify_once(job,runpath):
    tag=job['tag'];attempt=L/(tag+'.queue_attempt.json');reply=L/(tag+'.queue_result.json');need(job['queue'] and not attempt.exists() and not reply.exists() and os.environ.get('CODEX_THREAD_ID')==THREAD,'One terminal GPU queue to the actual root only')
    program=m.notifier_path();message=('The single admitted C08 release-only AV0.2 GPU .90s window is terminal: '+str(runpath)+'. Read actual start/call/status/owner+root admission/exits/private build/source and original schema2 PRE/input/full91plan first. XML certified Visco.1 remains unchanged; actual AV must be proven by new typed Policy ReleaseOnly/OverrideActive true/Coef float.2 on all91 headers, not startup Configuration. CPU Debug two-frame smoke/native was prior admission only, not GPU bit truth or physical acceptance. Preserve original22/6805/P0/J/kappa/ledger/FS/plane/clock/signed guards. No auto reader/VTK/otherpsi/half/PRE/nextsolver. Check existing/active readers before separately admitting AV20 native window once. Failed/completed-solver analysis remains preserved; never rerun, invent unsaved time, resend/rearm or add watcher. One current-root45s terminal queue attempt only.')
    argv=[str(program) if program else 'codex','queue','--thread',THREAD,'--message',message];save(attempt,dict(stage=tag,run=stat(runpath),thread=THREAD,arguments=argv,attempts=1,timeout_s=45,do_not_resend=True));result=dict(stage=tag,attempts=1,do_not_resend=True)
    try:
        need(program is not None,'Current notifier unavailable');q=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW);result.update(actual_exit=q.returncode,status='queued' if q.returncode==0 else 'queue_failed',stdout=q.stdout,stderr=q.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(reply,result)


def run(job):
    config,prep,admission,out=paths(job);tag=job['tag'];runpath=L/(tag+'.run.json');need(not out.exists() and not any(q.name not in {prep.name,admission.name} for q in L.glob(tag+'.*')),'Existing complete/partial protected; external launcher prefix must differ');claim=L/(tag+'.claim.json');save(claim,dict(stage=tag,owner_pid=os.getpid(),owner_created_epoch=psutil.Process().create_time(),single_attempt=True));consumed=[];phase='preflight';result=dict(stage=tag,job=job,passed=False,solver_completed=False,physical_acceptance=False,native_review_pending=True,actual_AV_typed_confirmation_pending=True,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,VTK_invocations=0,SHA_scans=0,automatic_next_job=False)
    try:
        control,material,preload,closure,runtime,gen,consumed=context(job);consumed.append(stat(claim));out.mkdir();prefix=out/tag;phase='GenCase';result['GenCase_invocations']=1;result['GenCase_call']=m.invoke(tag+'.gencase',[gen['path'],str(config.with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml');actual=input_check(seed,control['input_xml']['path'],job,True);seeds=[stat(Path(str(prefix)+s)) for s in ('.xml','.bi4','_Normals.nbi4')];consumed+=seeds
        values=m.actual_material(actual);m.match_material(values,material);pars={q.get('key'):q.get('value') for q in actual.findall('execution/parameters/parameter')};values.update(ArtificialStressCoef=pars['ArtificialStressCoef'],ArtificialStressExp=pars['ArtificialStressExp']);profile=out/'native_profile.csv'
        with profile.open('x',encoding='utf-8',newline='') as f:writer=csv.writer(f);writer.writerow(('key','value'));writer.writerows(values.items())
        consumed.append(stat(profile));program=Path(closure['program']['path']);argv=[str(program),*(['-cpu','-ompthreads:1'] if job['backend']=='CPU' else ['-gpu:0']),'-stable','-mdbc_freeslip:1',str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:'+str(job['end'])];owner=L/(tag+'.owner_admission.json');m.verify(consumed)
        save(owner,dict(stage=tag,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(admission),job=job,**closure,runtime=runtime,input_xml=stat(seed),seed=seeds,planned_steps=stat(plan(job)),native_profile=stat(profile),argv=argv,solver_argv=argv,consumed=consumed));consumed.append(stat(owner));result.update(job=job,**closure,runtime=runtime,input_xml=stat(seed),seed=seeds,planned_steps=stat(plan(job)),native_profile=stat(profile),owner_admission=stat(owner),argv=argv,group='psi0',kernel=2,geometry_profile='bedroles',keep_bed_overlap=False,hdp=1.8,fixed_dt_s=5e-6,AS_coefficient=.3,AS_exponent=2.55,certified_input_AV=.1,expected_release_AV=.2)
        m.old.old.idle(True);phase='solver';result['solver_invocations']=1;result['actual_call']=base.owned(tag,argv,program,False,stat(owner));result['solver_completed']=True;phase='runtime_review';result.update(output_checks(job,out,preload));m.verify(consumed);result.update(passed=True)
    except Exception as error:result.update(first_failure=str(error),failed_stage=phase)
    callpath=L/(tag+'.call.json')
    if callpath.exists():q=read(callpath);result.update(actual_call=stat(callpath),actual_exit=q['actual_solver_Win32_exit'],actual_Win32_exit=q['actual_solver_Win32_exit'],actual_tool_exit=q['actual_Popen_wait_exit'],ownership_errors=q['ownership_errors'])
    if (out/'Run.out').exists():
        text=(out/'Run.out').read_text(encoding='utf-8-sig',errors='replace');error=re.search(r'^Text: (.+)$',text,re.M);result.update(Run_out=stat(out/'Run.out'),first_engine_exception_text=error[1] if error else None,observed_saved_files=len(list((out/'data').glob('Part_*.bi4'))))
    unchanged=False
    try:unchanged=all(stat(q['path'])==q for q in consumed)
    except Exception as error:result['terminal_stat_error']=str(error)
    if not unchanged:result['passed']=False
    result.update(consumed=consumed,consumed_stats_unchanged=unchanged,last_original_console_line=base.last_part(out),unsaved_state_reconstructed=False,unsaved_failure_time_reconstructed=False);save(runpath,result);base.publish(tag,out,None,None,('completed_pending_independent_native' if result['passed'] else 'completed_solver_runtime_review_failed') if result['solver_completed'] else 'failed_preserved_no_next_job')
    if job['queue'] and (result['GenCase_invocations'] or callpath.exists()):notify_once(job,runpath)
    return 0 if result['passed'] else (result.get('actual_exit') or 1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','run'));parser.add_argument('--job',choices=tuple(JOBS),required=True);parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args();need(args.execution_authorized and os.environ.get('CODEX_THREAD_ID')==THREAD,'Author-only until separate current-root preparation/run authorization');job=JOBS[args.job]
    prepare(job) if args.action=='prepare' else exit(run(job))
