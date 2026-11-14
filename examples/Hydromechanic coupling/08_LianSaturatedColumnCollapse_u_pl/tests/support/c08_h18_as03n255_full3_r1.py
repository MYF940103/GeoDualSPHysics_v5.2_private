"""One fresh original AS0.3/n2.55 psi0 three-second diagnostic; never auto-native/next."""
import argparse,csv,os,re,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import c08_h18_as03_n255_r1 as validated
previous,matrix=validated,validated.matrix
base=matrix.base;T,C,L=matrix.T,matrix.C,matrix.L
need,read,stat,bind,save,invoke=matrix.need,matrix.read,matrix.stat,matrix.bind,matrix.save,matrix.invoke
TAG='c08_h18_as03n255_full3_r1';NOTE=T/'notes'/(TAG+'.md');DECISION=T/'notes/c08_h18_as03n255_decision_r1.md'
CONFIG=T/'configs'/(TAG+'_Def.xml');PREP=L/(TAG+'.prepare.json');ADMISSION=L/(TAG+'.admission.json')
PLAN=T/'configs/c08_h18_release_full3_r2.steps.csv';CONTROL_RUN=L/(validated.TAG+'.run.json')
CONTROL_AD=L/(validated.TAG+'.admission.json');NATIVE=L/'c08_h18_as03_n255_native_r1.check.json';REVIEW=L/'c08_h18_as03n255_review_r1.check.json';ADAPTER=L/'c08_h18_as03n255_review_r1.adapter.json'
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8' # Exact current root identity supplied during author review; never adopt a caller thread.
REVIEWS=[L/(q+'.check.json') for q in ('c08_h18_n255_review_r1','c08_h18_storage_rhs_r2','c08_h18_step_balance_r1','c08_h18_quadratic_r1')]
KEYS=('program','source_build','source_capture','source_archive','source_pre_file','source_run','source_native')
META=dict(group='psi0',Kernel=2,AS_coefficient=.3,AS_exponent=2.55,planned_global_end=2600000,planned_new_updates=600000,expected_saved_frames=301,planned_TimeOut=.01,only_numerical_input_difference='TimeMax 10.90 -> 13.0',diagnostic_only=True,physical_acceptance=False,other_psi_held=True,native_auto_authorized=False,automatic_next_job=False)


def schedule(preload):
    rows=matrix.table(PLAN);need(len(rows)==301 and list(rows[0])==['part','completed_step','saved_step','time_s','dt_s'],'Original full301 plan required');scalar=preload['preload_actual_end_s'];prior=2000000
    for i,q in enumerate(rows):
        step=2600000 if i==300 else 2000001+2000*i
        need(int(q['part'])==i and int(q['completed_step'])==step and int(q['saved_step'])==step-1 and float(q['dt_s'])==5e-6,'Original full301 step/index/dt differs')
        for _ in range(prior,step):scalar+=5e-6
        need(abs(float(q['time_s'])-scalar)<=1e-14,'Full301 scalar clock differs');prior=step
    need(rows[:90]==matrix.table(matrix.PLAN)[:90] and rows[90]['completed_step']!='2180000','Only actual common steps, never a fabricated full91 prefix');return rows


def original_context():
    original,oldad,oldconfig,build,program,material,runtime,window,preload,consumed=validated.original_context() # Exactly once per phase; no prior owner executes and no helper/global PLAN changes.
    control=read(CONTROL_RUN);prior=read(CONTROL_AD);native=read(NATIVE);review=read(REVIEW);adapter=read(ADAPTER)
    need(control['stage']==validated.TAG and control['passed'] and control['solver_completed'] and control['actual_exit']==control['actual_Win32_exit']==0 and control['actual_steps']==2180000 and control['saved_frames']==91 and control['consumed_stats_unchanged'] and control['AS_coefficient']==.3 and control['AS_exponent']==2.55,'Genuine completed AS03/n2.55 window required')
    for key in KEYS:need(bind(control[key])==bind(original[key]),'AS03 must retain original program/source/schema2 PRE closure: '+key)
    call=read(bind(control['actual_call'])['path']);need(call['actual_solver_Win32_exit']==call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and not call['ownership_errors'],'Actual AS03 owned solver exits differ')
    config=Path(bind(prior['input_xml'])['path']);validated.check_input(config,oldconfig);actual=validated.check_input(bind(control['input_xml'])['path'],original['input_xml']['path'],True)
    need(prior['passed'] and prior['allowed_job']==validated.TAG and prior['AS_coefficient']==.3 and prior['AS_exponent']==2.55 and native['passed'] and native['consumed_stats_unchanged'] and native['reader_invocations']==1,'Passed actual AS03 admission/native read required')
    done=read(bind(native['native_completion'])['path']);meta=read(bind(native['metadata'])['path']);reader=read(bind(native['reader_build'])['path']);nc=read(bind(native['actual_call'])['path'])
    need(done['passed'] and done['stage']=='c08_h18_wend_native_r1.receiver' and done['samples']==91 and done['completed_steps']==2180000 and done['typed_arrays']==22 and done['actual_native_IDs_per_frame']==6805 and done['soil_IDs']==5000 and done['actual_fixed_IDs']==1805 and done['source_handoff_schema']==2 and not done['native_rewritten'] and meta['passed'] and meta['receiver_material_CSV_keys']==17 and matrix.f32(meta['AS_coefficient_float_reference'])==matrix.f32(.3) and matrix.f32(meta['AS_exponent_float_reference'])==matrix.f32(2.55),'Exact full91 native AS03 profile required')
    need(reader['passed'] and reader['consumed_stats_unchanged'] and nc['actual_Popen_wait_exit']==nc['actual_Win32_exit']==0 and nc['ownership_failure'] is None and Path(nc['program']).samefile(bind(reader['program'])['path']),'Actual AS255 reader program/exit differs')
    values=matrix.actual_material(actual);matrix.match_material(values,material);values.update(ArtificialStressCoef='0.3',ArtificialStressExp='2.55');profile=matrix.table(bind(control['native_profile'])['path']);need(len(profile)==17 and len({q['key'] for q in profile})==17 and {q['key'] for q in profile}==set(values) and all(q['value']==values[q['key']] if q['key']=='group' else matrix.f32(q['value'])==matrix.f32(values[q['key']]) for q in profile),'All17 actual XML/profile keys must agree')
    need(review['analysis_complete'] and review['consumed_stats_unchanged'] and not review['physical_acceptance'] and not review['winner_selected'] and review['exact_matching_option_rows']==91 and any(q['tag']==validated.TAG and q['actual_samples']==91 for q in review['receiver_summaries']) and adapter['adapter_complete'] and adapter['stats_unchanged'] and adapter['analysis_check']==stat(REVIEW),'Completed independent AS03/AS05 analysis required; no physical acceptance inferred')
    consumed.extend(stat(q) for q in (CONTROL_RUN,CONTROL_AD,NATIVE,REVIEW,ADAPTER,config));consumed.extend(bind(control[q]) for q in ('actual_call','input_xml','native_profile'));consumed.extend(bind(native[q]) for q in ('native_completion','metadata','reader_build','actual_call'));consumed.append(bind(reader['program']))
    for i,path in enumerate(REVIEWS):
        q=read(path);need(q['consumed_stats_unchanged'] and not q['physical_acceptance'] and (q['analysis_complete'] if i==0 else q['passed']),'Retained original diagnostic review required')
    schedule(preload);consumed.extend(stat(q) for q in (Path(__file__),NOTE,DECISION,PLAN,*REVIEWS,T/'notes/c08_h18_rhs_decision_r1.md',T/'notes/c08_h18_step_geometry_r1.md'))
    matrix.verify(consumed);return control,prior,config,build,program,material,runtime,window,preload,consumed


def check_input(path,control_config,generated=False):
    actual=ET.parse(path).getroot();expected=ET.parse(control_config).getroot();nodes=expected.findall("execution/parameters/parameter[@key='TimeMax']")
    need(len(nodes)==1 and float(nodes[0].get('value'))==10.9,'One original n255 endpoint required');nodes[0].set('value','13.0')
    sections=('execution/special','execution/parameters','execution/constants','execution/particles') if generated else (None,)
    need(all(matrix.signature(actual if key is None else actual.find(key))==matrix.signature(expected if key is None else expected.find(key)) for key in sections),'Only TimeMax 10.90 -> 13.0 may differ from original n255')
    pars={q.get('key'):q.get('value') for q in actual.findall('execution/parameters/parameter')};need(len(pars)==len(actual.findall('execution/parameters/parameter')),'Duplicate parameter')
    need(all(matrix.f32(pars[k])==matrix.f32(v) for k,v in dict(Kernel=2,ArtificialStressCoef=.3,ArtificialStressExp=2.55,DtFixed=5e-6,TimeMax=13.,TimeOut=.01).items()),'Explicit full3 numerical profile differs');return actual


def prepare():
    need(os.environ.get('CODEX_THREAD_ID')==THREAD,'Only exact current root may prepare');need(not CONFIG.exists() and not (T/'outputs'/TAG).exists() and not any(L.glob(TAG+'.*')),'Existing preparation/output protected')
    control,prior,config,build,program,material,runtime,window,preload,consumed=original_context()
    raw=config.read_bytes();pattern=rb'(<parameter\s+key="TimeMax"\s+value=")10\.90(")';hits=list(re.finditer(pattern,raw));need(len(hits)==1,'One exact original endpoint line required');hit=hits[0];replacement=hit[1]+b'13.0'+hit[2];changed=raw[:hit.start()]+replacement+raw[hit.end():]
    need(changed.count(replacement)==1 and changed.replace(replacement,hit[0],1)==raw,'Inverse endpoint replacement must recover all original XML bytes')
    with CONFIG.open('xb') as handle:handle.write(changed)
    check_input(CONFIG,config);matrix.verify(consumed)
    save(PREP,dict(stage=TAG+'.prepare',prepared_only=True,exact_inverse_original_XML_bytes=True,control_run=stat(CONTROL_RUN),control_configuration=stat(config),configuration=stat(CONFIG),owner=stat(Path(__file__)),note=stat(NOTE),physical_decision=stat(DECISION),planned_steps=stat(PLAN),**{k:control[k] for k in KEYS},**META,consumed=consumed,consumed_stats_unchanged=True,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,VTK_invocations=0,SHA_scans=0))


def context():
    control,prior,config,build,program,material,runtime,window,preload,consumed=original_context();prepared=read(PREP);admission=read(ADMISSION)
    need(prepared['stage']==TAG+'.prepare' and prepared['prepared_only'] and prepared['exact_inverse_original_XML_bytes'] and prepared['consumed_stats_unchanged'] and prepared['configuration']==stat(CONFIG) and prepared['control_configuration']==stat(config) and prepared['control_run']==stat(CONTROL_RUN),'Exact fresh full3 preparation required');check_input(CONFIG,config)
    need(admission['passed'] and admission['allowed_job']==TAG and admission['root_full_read'] is True and admission['full3_diagnostic_admission'] is True and admission['prepared']==stat(PREP) and admission['input_xml']==stat(CONFIG) and admission['control_run']==stat(CONTROL_RUN) and admission['terminal_queue_once'] is True,'Separate root full-read diagnostic admission required')
    for record in (prepared,admission):
        need(record['owner']==stat(Path(__file__)) and record['note']==stat(NOTE) and record['physical_decision']==stat(DECISION) and record['planned_steps']==stat(PLAN) and all(record[k]==v for k,v in META.items()),'Exact owner/note/new physical decision/full301 plan/profile required')
        for key in KEYS:need(bind(record[key])==bind(control[key]),'Original true program/source/schema2 PRE closure differs: '+key)
    need(admission['root_thread_id']==os.environ.get('CODEX_THREAD_ID')==THREAD and matrix.notifier_path() is not None,'Exact admitted current root/notifier required')
    consumed.extend(stat(q) for q in (PREP,ADMISSION,CONFIG));consumed.extend(bind(q) for q in prepared['consumed']);matrix.verify(consumed);matrix.old.old.idle(True)
    return control,program,material,runtime,preload,consumed


def output_checks(out,preload):
    observed=previous.summary(out/'Run.csv');text=(out/'Run.out').read_text(encoding='utf-8-sig');parts=sorted((out/'data').glob('Part_*.bi4'))
    need(int(observed['Steps'])==2600000 and int(observed['PartFiles'])==301 and int(observed['Np'])==7060 and int(observed['Nfixed'])==int(observed['Nbound'])==2060 and all(int(observed[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')) and 'Gpu_' in observed['Hardware'] and float(observed['H'])==.072 and float(observed['Dp'])==.04,'Actual full301 GPU/no-loss registry differs')
    need('Kernel="Wendland"' in text and 'Finished execution (code=0).' in text and '[Simulation INTERRUPTED' not in text and 'No Penetration=True' in text and 'Dynamic NoPen: '+base.POLICY in text and text.count('GravityPreload: phase=released ')==1 and text.count('GravityPreload: validated native right-wall range=[1805,2060), count=255.')==1 and 'retired=255; damping=OFF Shepard=OFF FreeSeepage=ON.' in text,'Actual kernel/completion/release/NoPen differs')
    for key,value in (('ArtificialStressCoef',.3),('ArtificialStressExp',2.55)):
        hits=re.findall(r'^\s*'+key+r'[:=]\s*([0-9.eE+-]+)\s*$',text,re.M);need(len(hits)==1 and matrix.f32(hits[0])==matrix.f32(value),'Actual explicit AS differs')
    imported=re.findall(r'GravityPreload: state imported file=.*? actual=([0-9.eE+-]+) completed_step=(\d+);',text)
    need(len(imported)==1 and int(imported[0][1])==2000000 and float(imported[0][0])==preload['preload_actual_end_s'] and [q.name for q in parts]==['Part_%04d.bi4'%i for i in range(301)],'Actual original PRE/full301 PART sequence differs')
    return dict(actual_steps=2600000,saved_frames=301,summary=observed,actual_source_time_from_loader=float(imported[0][0]),Run_csv=stat(out/'Run.csv'),Run_out=stat(out/'Run.out'),PART_head=stat(out/'data/Part_Head.ibi4'),PARTs=[stat(q) for q in parts])


def notify_once(run_path):
    attempt=L/(TAG+'.queue_attempt.json');reply=L/(TAG+'.queue_result.json');need(not attempt.exists() and not reply.exists() and os.environ.get('CODEX_THREAD_ID')==THREAD,'One exact current-root terminal queue only; never retry/rearm')
    program=matrix.notifier_path();message=('The single original AS0.3/n2.55 psi0 fresh3s DIAGNOSTIC is terminal: '+str(run_path)+'. Read original owned start/call/status/admissions, actual exits, first actual error/last raw console/partials, bound physical decision and unchanged original program/source/schema2 PRE/input/full301plan. Endpoint10.90->13.0 only; same5us/600000new/2600000completed, no PRE or old0.9 rerun. Full301/native22-field/6805-ID and pressure/stress/motion/geometry review require separate root admission; no auto decoder/VTK/next/otherpsi/half/formal job or physical acceptance. Compare old0.9 only at actual common steps: original final2180000 versus full3Part90=2180001; old91 is not a3s reference. Never reconstruct unsaved arrays/time. Queue once45s; uncertain delivery never resend/rearm/watch.')
    argv=[str(program) if program else 'codex','queue','--thread',THREAD,'--message',message];save(attempt,dict(stage=TAG,run=stat(run_path),thread=THREAD,program=stat(program) if program else None,arguments=argv,attempts=1,timeout_s=45,do_not_resend=True));result=dict(stage=TAG,attempts=1,do_not_resend=True)
    try:
        need(program is not None,'Current notifier unavailable');done=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW);result.update(actual_exit=done.returncode,status='queued' if done.returncode==0 else 'queue_failed',stdout=done.stdout,stderr=done.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(reply,result)


def run():
    out=T/'outputs'/TAG;run_path=L/(TAG+'.run.json');need(not out.exists() and not any(q.name not in {PREP.name,ADMISSION.name} for q in L.glob(TAG+'.*')),'Existing job/partial protected; external launcher prefix must differ')
    claim=L/(TAG+'.claim.json');save(claim,dict(stage=TAG,owner_pid=os.getpid(),owner_created_epoch=psutil.Process().create_time(),single_attempt=True));consumed=[];phase='preflight';result=dict(stage=TAG,**META,solver_completed=False,passed=False,native_review_pending=True,native_full301_requires_separate_admission=True,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,VTK_invocations=0,SHA_scans=0)
    try:
        control,program,material,runtime,preload,consumed=context();consumed.append(stat(claim));out.mkdir();prefix=out/TAG;gen=next(q for q in runtime if Path(q['path']).name=='GenCase_win64.exe')
        phase='GenCase';result['GenCase_invocations']=1;result['GenCase_call']=invoke(TAG+'.gencase',[gen['path'],str(CONFIG.with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml');actual=check_input(seed,control['input_xml']['path'],True);seeds=[stat(Path(str(prefix)+q)) for q in ('.xml','.bi4','_Normals.nbi4')];consumed.extend(seeds)
        profile=out/'native_profile.csv';values=matrix.actual_material(actual);matrix.match_material(values,material);pars={q.get('key'):q.get('value') for q in actual.findall('execution/parameters/parameter')};values.update(ArtificialStressCoef=pars['ArtificialStressCoef'],ArtificialStressExp=pars['ArtificialStressExp'])
        with profile.open('x',encoding='utf-8',newline='') as handle:writer=csv.writer(handle);writer.writerow(('key','value'));writer.writerows(values.items())
        consumed.append(stat(profile));matrix.verify(consumed);argv=[str(program),'-gpu:0','-stable','-mdbc_freeslip:1',str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:2600000'];need(argv[1:4]==control['argv'][1:4] and argv[6:-1]==control['argv'][6:-1] and control['argv'][-1]=='-nsteps:2180000','Only labels and endpoint may change in original solver argv');owner=L/(TAG+'.owner_admission.json');closure={k:control[k] for k in KEYS}
        save(owner,dict(stage=TAG,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(ADMISSION),**closure,**META,runtime=runtime,input_xml=stat(seed),seed=seeds,planned_steps=stat(PLAN),physical_decision=stat(DECISION),control_run=stat(CONTROL_RUN),argv=argv,solver_argv=argv,consumed=consumed));consumed.append(stat(owner))
        result.update(**closure,runtime=runtime,input_xml=stat(seed),seed=seeds,planned_steps=stat(PLAN),physical_decision=stat(DECISION),native_profile=stat(profile),owner_admission=stat(owner),argv=argv,control_run=stat(CONTROL_RUN),kernel=2,kernel_name='Wendland',geometry_profile='bedroles',keep_bed_overlap=False,hdp=1.8,fixed_dt_s=5e-6)
        matrix.old.old.idle(True);phase='solver';result['solver_invocations']=1;result['actual_call']=base.owned(TAG,argv,program,False,stat(owner));phase='runtime_review';result.update(output_checks(out,preload));matrix.verify(consumed);result.update(passed=True,solver_completed=True)
    except Exception as error:result.update(first_failure=str(error),failed_stage=phase)
    call_path=L/(TAG+'.call.json')
    if call_path.exists():
        actual=read(call_path);result.update(actual_call=stat(call_path),actual_exit=actual['actual_solver_Win32_exit'],actual_Win32_exit=actual['actual_solver_Win32_exit'],actual_tool_exit=actual['actual_Popen_wait_exit'],ownership_errors=actual['ownership_errors'])
    gen_call=L/(TAG+'.gencase.call.json')
    if gen_call.exists():result['GenCase_call']=stat(gen_call)
    if (out/'Run.out').exists():
        text=(out/'Run.out').read_text(encoding='utf-8-sig',errors='replace');hit=re.search(r'^Text: (.+)$',text,re.M);parts=sorted((out/'data').glob('Part_*.bi4'));result.update(Run_out=stat(out/'Run.out'),first_engine_exception_text=hit[1] if hit else None,reported_wall_rejection_lines=[q for q in text.splitlines() if q.startswith('DynamicPoreWall rejected:')],observed_saved_files=len(parts),PARTs=[stat(q) for q in parts])
    for label,raw in (('solver',L/(TAG+'.solver.log')),('GenCase',L/(TAG+'.gencase.log'))):
        if raw.exists():
            with raw.open('rb') as handle:first=handle.read(65536).decode('utf-8','replace');handle.seek(max(0,raw.stat().st_size-65536));lines=handle.read().splitlines()
            error=re.search(r'^(?:Text:|Exception|Error(?:\s|:)).*$',first,re.M);result[label+'_console']=dict(raw=stat(raw),first_actual_error_line=error[0] if error else None,last_raw_line=lines[-1].decode('utf-8','replace') if lines else None)
    unchanged=False
    try:unchanged=all(stat(q['path'])==q for q in consumed)
    except Exception as error:result['terminal_stat_error']=str(error)
    if not unchanged:result['passed']=False
    result.update(consumed=consumed,consumed_stats_unchanged=unchanged,last_original_console_line=base.last_part(out),unsaved_state_reconstructed=False,unsaved_failure_time_reconstructed=False,native_invocation_authorized_by_this_owner=False);save(run_path,result);base.publish(TAG,out,None,None,'completed_pending_explicit_native_review' if result['solver_completed'] else 'failed_preserved_no_next_job')
    if result['GenCase_invocations'] or call_path.exists():notify_once(run_path)
    return 0 if result['passed'] else (result.get('actual_exit') or 1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','run'));parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args();need(args.execution_authorized and os.environ.get('CODEX_THREAD_ID')==THREAD,'Author-only until exact current root full-read and separate action authorization')
    prepare() if args.action=='prepare' else exit(run())
