"""One separately admitted Release AS.7 window with the experimental centroid wall retry."""
import argparse,json,os,re,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import c08_h18_wall_fail_probe_r1 as previous

matrix,base=previous.matrix,previous.base
T,C,L=previous.T,previous.C,previous.L
need,read,stat,bind,save,invoke=previous.need,previous.read,previous.stat,previous.bind,previous.save,previous.invoke
TAG='c08_h18_centroid_a07_GPU_r1'
NOTE=T/'notes/c08_h18_centroid_a07_r1.md'
CONFIG=T/'configs'/(TAG+'_Def.xml')
PREP=L/(TAG+'.prepare.json');ADMISSION=L/(TAG+'.admission.json')
BUILD=L/'c08_h18_centroid_Release_r1.build.json'
PROGRAM=T/'outputs/c08_h18_centroid_Release_r1/DualSPHysics5.2_GEO_win64.exe'
INTERVENTION='dynamic_wall_centroid_retry_once'
THREAD=matrix.THREAD


def original_context():
    original,admission,config,window,preload,material,gen,consumed=previous.original_context()
    consumed.extend(stat(q) for q in (Path(__file__),NOTE,Path(previous.__file__)))
    return original,admission,config,window,preload,material,gen,consumed


def prepare():
    need(not CONFIG.exists() and not PREP.exists() and not (T/'outputs'/TAG).exists() and not any(L.glob(TAG+'.*')),'Existing candidate preparation/output is protected; no retry')
    original,admission,config,window,preload,material,gen,consumed=original_context()
    with CONFIG.open('xb') as handle:handle.write(config.read_bytes())
    need(matrix.signature(ET.parse(CONFIG).getroot())==matrix.signature(ET.parse(config).getroot()),'Candidate label must retain the actual original AS.7 numerical XML')
    matrix.check_input(CONFIG,.7);matrix.verify(consumed)
    save(PREP,dict(stage=TAG+'.prepare',prepared_only=True,intervention=INTERVENTION,physical_closure_change=True,experimental_pending_physical_acceptance=True,original_run=stat(previous.ORIGINAL_RUN),original_admission=stat(previous.ORIGINAL_ADMISSION),original_configuration=stat(config),configuration=stat(CONFIG),planned_steps=stat(matrix.PLAN),planned_global_end=matrix.END,expected_saved_frames=matrix.SAMPLES,source_pre_file=stat(matrix.PRE),AS_coefficient=.7,AS_exponent=3.825,kernel=2,numerical_input_signature_matches_original=True,consumed=consumed,consumed_stats_unchanged=True,GenCase_invocations=0,solver_invocations=0,reader_invocations=0,PartVTK_invocations=0,SHA_scans=0,physical_acceptance=False))
    print('CENTROID_AS07_PREPARED',PREP,flush=True)


def debug_qualification(entry,release,consumed):
    """Consume root's actual aggregate; never launch or substitute component tests."""
    sealed=bind(entry);qualification=read(sealed['path']);consumed.append(sealed)
    need(qualification['stage']=='c08_h18_centroid_debug_regression_r1' and qualification['passed'] and qualification['intervention']==INTERVENTION and qualification['source_stats_unchanged'] and qualification['consumed_stats_unchanged'] and qualification['CPU_Debug_smoke_passed'] and qualification['GPU_Debug_smoke_passed'] and qualification['GPU_Debug_memcheck_zero_errors_and_leaks'],'Actual accepted CPU/GPU Debug smoke and GPU memcheck aggregate required before Release')
    need(bind(qualification['source_capture'])==bind(release['source_capture']) and bind(qualification['source_archive'])==bind(release['source_archive']),'Debug acceptance must cover the exact Release candidate source snapshot')
    consumed.extend((bind(qualification['source_capture']),bind(qualification['source_archive'])))
    for key,configuration in (('cpu_build','DebugCPU'),('gpu_build','Debug')):
        build_entry=bind(qualification[key]);build=read(build_entry['path']);consumed.append(build_entry)
        need(build['stage']=='c08_h18_centroid_'+configuration+'_r1.build' and build['passed'] and build['configuration']==configuration and build['intervention']==INTERVENTION and build['actual_typed_exit_code']==build['actual_Win32_exit']==0 and build['source_stats_unchanged'] and build['consumed_stats_unchanged'] and build['source_capture']==release['source_capture'] and build['source_archive']==release['source_archive'],'Accepted actual candidate Debug build/source differs: '+configuration)
        consumed.append(bind(build['program']))
    for key in ('cpu_smoke','gpu_smoke','gpu_memcheck'):
        evidence=bind(qualification[key]);observed=read(evidence['path']);consumed.append(evidence)
        need(observed.get('passed') is True and observed.get('consumed_stats_unchanged') is True,'Actual root-reviewed smoke/memcheck evidence must be passed and sealed: '+key)
    need(not qualification.get('physical_acceptance',False),'Debug implementation acceptance is not collapse physical acceptance')
    return qualification


def context():
    original,prior,config,window,preload,material,gen,consumed=original_context()
    prepared=read(PREP);admission=read(ADMISSION);build=read(BUILD)
    need(prepared['stage']==TAG+'.prepare' and prepared['prepared_only'] and prepared['intervention']==INTERVENTION and prepared['physical_closure_change'] and prepared['configuration']==stat(CONFIG) and prepared['original_configuration']==stat(config) and prepared['original_run']==stat(previous.ORIGINAL_RUN) and prepared['planned_steps']==stat(matrix.PLAN) and prepared['numerical_input_signature_matches_original'] and prepared['consumed_stats_unchanged'],'Exact fresh candidate preparation required')
    need(matrix.signature(ET.parse(CONFIG).getroot())==matrix.signature(ET.parse(config).getroot()),'Original AS.7 input physics must be retained; closure changes only through candidate source')
    matrix.check_input(CONFIG,.7)
    need(build['stage']=='c08_h18_centroid_Release_r1.build' and build['passed'] and build['configuration']=='Release' and build['intervention']==INTERVENTION and build['actual_typed_exit_code']==build['actual_Win32_exit']==0 and build['source_stats_unchanged'] and build['consumed_stats_unchanged'] and len(build['project_objects'])==113 and len(build['runtime'])==7,'A passed isolated authoritative Release candidate build is required')
    need(build['baseline_source_build']==original['source_build'] and build['baseline_source_capture']==original['source_capture'] and build['baseline_source_archive']==original['source_archive'] and len(build['source_differences'])==2,'Candidate must retain the separately reviewed two-file CPU/GPU centroid intervention provenance')
    need(Path(bind(build['program'])['path'])==PROGRAM and PROGRAM.parent!=Path(original['program']['path']).parent,'Only the isolated Release candidate executable is allowed')
    for key in ('source_capture','source_archive'):
        need(bind(build[key])!=original[key],'Changed physical closure source cannot impersonate the original snapshot')
    need(admission['passed'] and admission['allowed_job']==TAG and admission['intervention']==INTERVENTION and admission['physical_intervention_authorized'] and admission['experimental_pending_physical_acceptance'] and admission['prepared']==stat(PREP) and admission['candidate_build']==stat(BUILD) and admission['input_xml']==stat(CONFIG) and admission['original_run']==stat(previous.ORIGINAL_RUN) and admission['source_pre_file']==stat(matrix.PRE) and admission['planned_steps']==stat(matrix.PLAN) and admission['planned_global_end']==matrix.END and admission['expected_saved_frames']==matrix.SAMPLES and admission['native_auto_authorized'] is False and admission['terminal_queue_once'] is True,'Distinct root admission for this experimental physical closure change is required')
    for key in ('program','source_capture','source_archive'):
        need(bind(admission[key])==bind(build[key]),'Root candidate program/source binding differs: '+key)
    qualification=debug_qualification(admission['debug_regression'],build,consumed)
    need(admission['root_thread_id']==os.environ.get('CODEX_THREAD_ID')==THREAD and matrix.notifier_path() is not None,'Actual admitted root thread/current Codex notifier required before launch')
    consumed.extend(stat(q) for q in (PREP,ADMISSION,BUILD,CONFIG))
    consumed.extend(bind(q) for q in prepared['consumed'])
    consumed.extend(bind(build[key]) for key in ('program','source_capture','source_archive','baseline_source_build','baseline_source_capture','baseline_source_archive','actual_call'))
    consumed.extend(bind(q) for q in build['runtime'])
    matrix.verify(consumed);matrix.old.old.idle(True)
    return admission,build,original,prior,window,preload,material,gen,qualification,consumed


def notify_once(run_path):
    attempt=L/(TAG+'.queue_attempt.json');reply=L/(TAG+'.queue_result.json')
    need(not attempt.exists() and not reply.exists(),'Terminal queue already attempted; never resend or rearm')
    need(os.environ.get('CODEX_THREAD_ID')==THREAD,'Terminal queue must remain on the actual admitted root thread')
    program=matrix.notifier_path()
    message=('The single root-admitted centroid-wall AS.7 candidate window is terminal: '+str(run_path)+'. Read original run/start/call/status/root and owner admissions, actual child/tool exits, last original console, candidate build/source/Debug smoke+memcheck/PRE/input/full91plan bindings. This is c08_h18_centroid_a07_GPU_r1, a physical dynamic-wall centroid retry intervention, not an output-only replay. It retains original Wendland H1.8/5us/AS.7n3.825/PRE/AV/NoPen/CompletedOnly and target2180000. Exit0/full91 or later failure is runtime evidence only; native decoding and physical pressure/spacing/J/kappa/motion review need independent root admission. No automatic native/VTK, second solver, PRE, half/control/other-psi run, acceptance, watcher, resend or rearm. Preserve all old tags and partials. This verified same-thread terminal queue is attempted once with45s timeout; timeout may have delivered.')
    argv=[str(program) if program else 'codex','queue','--thread',THREAD,'--message',message]
    save(attempt,dict(stage=TAG,utc=base.utc(),thread=THREAD,run=stat(run_path),program=stat(program) if program else None,arguments=argv,attempts=1,timeout_s=45,do_not_resend=True))
    result=dict(stage=TAG,attempts=1,do_not_resend=True)
    try:
        need(program is not None,'Current Codex notifier unavailable; preserve terminal evidence without retry')
        completed=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        result.update(actual_exit=completed.returncode,status='queued' if completed.returncode==0 else 'queue_failed',stdout=completed.stdout,stderr=completed.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(reply,result)


def run():
    out=T/'outputs'/TAG;run_path=L/(TAG+'.run.json');allowed={PREP.name,ADMISSION.name}
    need(not out.exists() and not any(q.name not in allowed for q in L.glob(TAG+'.*')),'Existing candidate output/owner/call/partial is protected; external launch logs require a different prefix')
    claim=L/(TAG+'.claim.json');save(claim,dict(stage=TAG,owner_pid=os.getpid(),owner_created_epoch=psutil.Process().create_time(),single_attempt=True))
    consumed=[];phase='preflight'
    result=dict(stage=TAG,passed=False,solver_completed=False,intervention=INTERVENTION,physical_closure_change=True,experimental_pending_physical_acceptance=True,physical_acceptance=False,native_review_pending=True,automatic_next_job=False,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,PartVTK_invocations=0,SHA_scans=0)
    try:
        admission,build,original,prior,window,preload,material,gen,qualification,consumed=context();consumed.append(stat(claim));out.mkdir();prefix=out/TAG
        phase='GenCase';result['GenCase_invocations']=1
        result['GenCase_call']=invoke(TAG+'.gencase',[gen['path'],str(CONFIG.with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml');actual=matrix.check_input(seed,.7,True);baseline_xml=ET.parse(bind(original['input_xml'])['path']).getroot()
        need(all(matrix.signature(actual.find(section))==matrix.signature(baseline_xml.find(section)) for section in ('execution/special','execution/parameters')),'Generated AS.7 numerical sections differ from the actual original input')
        seeds=[stat(Path(str(prefix)+suffix)) for suffix in ('.xml','.bi4','_Normals.nbi4')];consumed.extend(seeds)
        profile=out/'native_profile.csv';matrix.write_profile(profile,actual,.7,material);consumed.append(stat(profile));matrix.verify(consumed)
        argv=[str(PROGRAM),'-gpu:0','-stable','-mdbc_freeslip:1',str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:'+str(matrix.END)]
        need(argv[1:4]==original['argv'][1:4] and argv[6:]==original['argv'][6:],'Only candidate executable and fresh input/output labels may differ in solver argv')
        owner=L/(TAG+'.owner_admission.json')
        closure=dict(candidate_build=stat(BUILD),program=bind(build['program']),source_build=stat(BUILD),source_capture=build['source_capture'],source_archive=build['source_archive'],baseline_source_build=original['source_build'],baseline_source_capture=original['source_capture'],baseline_source_archive=original['source_archive'],runtime=build['runtime'],debug_regression=admission['debug_regression'],intervention=INTERVENTION,physical_closure_change=True,experimental_pending_physical_acceptance=True)
        save(owner,dict(stage=TAG,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(ADMISSION),**closure,source_pre_file=stat(matrix.PRE),source_run=prior['source_run'],source_native=prior['source_native'],source_native_call=prior['source_native_call'],source_material_profile=prior['source_material_profile'],source_physical_review=prior['source_physical_review'],input_xml=stat(seed),seed=seeds,planned_steps=stat(matrix.PLAN),planned_new_updates=180000,planned_global_end=matrix.END,expected_saved_frames=matrix.SAMPLES,Kernel=2,AS_coefficient=.7,AS_exponent=3.825,group='psi0',same_material_plastic_PRE=True,argv=argv,solver_argv=argv,consumed=consumed))
        consumed.append(stat(owner))
        result.update(**closure,group='psi0',kernel=2,kernel_name='Wendland',geometry_profile='bedroles',keep_bed_overlap=False,same_material_plastic_PRE=True,expected_source_handoff_schema=2,source_pre_file=stat(matrix.PRE),source_run=prior['source_run'],source_native=prior['source_native'],input_xml=stat(seed),seed=seeds,planned_steps=stat(matrix.PLAN),native_profile=stat(profile),owner_admission=stat(owner),argv=argv,AS_coefficient=.7,AS_exponent=3.825,hdp=1.8,fixed_dt_s=matrix.DT)
        phase='solver';result['solver_invocations']=1
        result['actual_call']=base.owned(TAG,argv,PROGRAM,False,stat(owner))
        result.update(actual_exit=0,actual_Win32_exit=0,actual_tool_exit=0,solver_returned_zero=True)
        phase='completed_runtime_review';result.update(matrix.old.old.output_checks(out,.7,window,preload))
        matrix.verify(consumed);result.update(passed=True,solver_completed=True,consumed_stats_unchanged=True)
    except Exception as error:result.update(first_failure=str(error),failed_stage=phase)
    observation_errors=[];call_path=L/(TAG+'.call.json')
    try:
        if call_path.exists():
            call=read(call_path);result.update(actual_call=stat(call_path),actual_exit=call['actual_solver_Win32_exit'],actual_Win32_exit=call['actual_solver_Win32_exit'],actual_tool_exit=call['actual_Popen_wait_exit'],ownership_errors=call['ownership_errors'])
    except Exception as error:observation_errors.append('Actual call observation: '+str(error))
    try:
        raw=out/'Run.out'
        if raw.exists():
            text=raw.read_text(encoding='utf-8-sig',errors='replace');hit=re.search(r'^Text: (.+)$',text,re.M);parts=sorted((out/'data').glob('Part_*.bi4'))
            result.update(Run_out=stat(raw),first_engine_exception_text=hit[1] if hit else None,reported_wall_rejection_lines=[line for line in text.splitlines() if line.startswith('DynamicPoreWall rejected:')],observed_saved_files=len(parts),PARTs=[stat(q) for q in parts])
    except Exception as error:observation_errors.append('Terminal Run.out observation: '+str(error))
    unchanged=False;last_console=None
    try:unchanged=all(stat(q['path'])==q for q in consumed)
    except Exception as error:observation_errors.append('Terminal stat audit: '+str(error))
    try:last_console=base.last_part(out)
    except Exception as error:observation_errors.append('Last original console observation: '+str(error))
    if observation_errors or not unchanged:result['passed']=False
    result.update(consumed=consumed,consumed_stats_unchanged=unchanged,terminal_observation_errors=observation_errors,last_original_console_line=last_console,unsaved_failure_time_reconstructed=False,unsaved_state_reconstructed=False,original_target_completed_step=matrix.END,original_target_samples=matrix.SAMPLES,native_invocation_authorized_by_this_owner=False)
    save(run_path,result);base.publish(TAG,out,None,None,'completed_pending_explicit_native_review' if result['solver_completed'] else 'failed_preserved_no_next_job')
    if call_path.exists():notify_once(run_path)
    print(json.dumps(dict(run=str(run_path),solver_completed=result['solver_completed'],actual_exit=result.get('actual_exit'),physical_acceptance=False)),flush=True)
    return 0 if result['passed'] else (result.get('actual_exit') or 1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','run'));parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    need(args.execution_authorized,'Author-only until root full-read and separately authorized preparation or Release run')
    prepare() if args.action=='prepare' else exit(run())
