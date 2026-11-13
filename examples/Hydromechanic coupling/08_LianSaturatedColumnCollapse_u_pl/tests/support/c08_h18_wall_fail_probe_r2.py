"""Prepare/run one separately admitted AS.7 terminal-printf replay; no automatic decoding."""
import argparse,json,os,re,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import c08_h18_wend_matrix_r1 as matrix

base=matrix.base
T,C,L=matrix.T,matrix.C,matrix.L
need,read,stat,bind,save,invoke=matrix.need,matrix.read,matrix.stat,matrix.bind,matrix.save,matrix.invoke
TAG='c08_h18_wall_fail_probe_GPU_r2'
NOTE=T/'notes/c08_h18_wall_fail_probe_r2.md'
CONFIG=T/'configs'/(TAG+'_Def.xml')
PREP=L/(TAG+'.prepare.json')
ADMISSION=L/(TAG+'.admission.json')
BUILD=L/'c08_h18_wall_fail_gpu_r2.build.json'
PROGRAM=T/'outputs/c08_h18_wall_fail_gpu_r2_build/DualSPHysics5.2_GEO_win64.exe'
ORIGINAL='c08_h18_wend_psi0_a07_w09_r1'
ORIGINAL_RUN=L/(ORIGINAL+'.run.json')
ORIGINAL_ADMISSION=L/(ORIGINAL+'.admission.json')
THREAD=matrix.THREAD


def original_context():
    run=read(ORIGINAL_RUN);admission=read(ORIGINAL_ADMISSION)
    need(run['stage']==ORIGINAL and not run['passed'] and not run['solver_completed'] and run['actual_exit']==run['actual_Win32_exit']==1,'Only the genuine failed AS.7 original is the diagnostic reference')
    call=read(bind(run['actual_call'])['path'])
    need(call['actual_solver_Win32_exit']==call['actual_Popen_wait_exit']==call['actual_Win32_exit']==1 and not call['ownership_errors'] and Path(call['actual_solver']['exe']).samefile(bind(run['program'])['path']),'Original failed owner/exits/program differ')
    need(admission['passed'] and admission['allowed_job']==ORIGINAL and admission['group']=='psi0' and admission['kernel']==2 and matrix.f32(admission['AS_coefficient'])==matrix.f32(.7) and matrix.f32(admission['AS_exponent'])==matrix.f32(3.825) and admission['source_review_allows_AS_screen'] and admission['native_auto_authorized'] is False,'Original exact AS.7/root source admission required')
    config=Path(bind(admission['input_xml'])['path']);matrix.check_input(config,.7)
    matrix.check_input(bind(run['input_xml'])['path'],.7,True)
    window,preload,rows=matrix.schedule()
    need(admission['planned_steps']==stat(matrix.PLAN) and admission['planned_global_end']==matrix.END and admission['expected_saved_frames']==matrix.SAMPLES,'Original full91 target/plan must remain unchanged')
    source_run=read(bind(admission['source_run'])['path']);source=read(bind(admission['source_native'])['path'])
    need(source_run['passed'] and source_run['solver_completed'] and source_run['actual_exit']==source_run['actual_Win32_exit']==0 and source_run['actual_steps']==matrix.EVENT and source_run['saved_frames']==1001 and source_run['source_pre_file']==bind(run['source_pre_file'])==stat(matrix.PRE),'Same genuine completed Wendland PRE required; no source replay')
    need(source['passed'] and source['stage']=='c08_h18_wend_native_r1.source' and source['certified_PRE'] and not source['partial'] and source['samples']==1001 and source['completed_steps']==matrix.EVENT and source['actual_end_s']==preload['preload_actual_end_s'],'Reuse the existing complete native source qualification')
    material_rows=matrix.table(bind(admission['source_material_profile'])['path']);material={q['key']:q['value'] for q in material_rows}
    matrix.match_material(material,matrix.actual_material(ET.parse(bind(source_run['input_xml'])['path']).getroot()))
    gen=next(q for q in run['runtime'] if Path(q['path']).name=='GenCase_win64.exe')
    consumed=[stat(q) for q in (ORIGINAL_RUN,ORIGINAL_ADMISSION,matrix.PLAN,matrix.SOURCE_PLAN,Path(__file__),NOTE,Path(matrix.__file__),Path(base.__file__),Path(base.evidence.__file__))]
    consumed.extend(bind(run[key]) for key in ('actual_call','program','source_build','source_capture','source_archive','source_pre_file','input_xml','native_profile'))
    consumed.extend(bind(admission[key]) for key in ('input_xml','source_run','source_native','source_native_call','source_material_profile','source_physical_review'))
    consumed.extend((bind(source_run['input_xml']),bind(gen),stat(matrix.PRE.parent/'Part_Head.ibi4')))
    matrix.verify(consumed)
    return run,admission,config,window,preload,material,gen,consumed


def prepare():
    need(not CONFIG.exists() and not PREP.exists() and not (T/'outputs'/TAG).exists() and not any(L.glob(TAG+'.*')),'Existing complete/partial probe preparation or output is protected')
    original,admission,config,window,preload,material,gen,consumed=original_context()
    with CONFIG.open('xb') as handle:handle.write(config.read_bytes())
    need(matrix.signature(ET.parse(CONFIG).getroot())==matrix.signature(ET.parse(config).getroot()),'Fresh label changed the numerical XML signature')
    matrix.check_input(CONFIG,.7);matrix.verify(consumed)
    save(PREP,dict(stage=TAG+'.prepare',prepared_only=True,diagnostic_only=True,intervention='terminal_rejection_printf_only',original_run=stat(ORIGINAL_RUN),original_admission=stat(ORIGINAL_ADMISSION),original_configuration=stat(config),configuration=stat(CONFIG),planned_steps=stat(matrix.PLAN),planned_global_end=matrix.END,expected_saved_frames=matrix.SAMPLES,source_pre_file=stat(matrix.PRE),AS_coefficient=.7,AS_exponent=3.825,kernel=2,numerical_signature_matches_original=True,consumed=consumed,consumed_stats_unchanged=True,GenCase_invocations=0,solver_invocations=0,reader_invocations=0,PartVTK_invocations=0,SHA_scans=0,physical_acceptance=False))
    print('WALL_FAIL_PROBE_PREPARED',PREP,flush=True)


def context():
    original,previous,config,window,preload,material,gen,consumed=original_context()
    prepared=read(PREP);admission=read(ADMISSION);build=read(BUILD)
    need(prepared['stage']==TAG+'.prepare' and prepared['prepared_only'] and prepared['configuration']==stat(CONFIG) and prepared['original_configuration']==stat(config) and prepared['original_run']==stat(ORIGINAL_RUN) and prepared['planned_steps']==stat(matrix.PLAN) and prepared['numerical_signature_matches_original'] and prepared['consumed_stats_unchanged'],'Exact fresh prepared configuration required')
    need(matrix.signature(ET.parse(CONFIG).getroot())==matrix.signature(ET.parse(config).getroot()),'Prepared numerical XML differs from the actual AS.7 original')
    matrix.check_input(CONFIG,.7)
    need(build['stage']=='c08_h18_wall_fail_gpu_r2.build' and build['passed'] and build['configuration']=='Release' and build['consumed_stats_unchanged'] and build['actual_typed_exit_code']==build['actual_Win32_exit']==0 and build['intervention']=='terminal_rejection_printf_only' and build['terminal_rejection_printf_only'] and build['exact_inverse_original_bytes'] and not build['physical_arithmetic_changed'] and not build['production_source_changed'] and not build['public_interfaces_changed'] and not build['trace_macros_enabled'] and not build['primary_snapshot_added'],'Require the separately reviewed private r2 fail-only printf build')
    need(build['baseline_source_build']==original['source_build'] and build['baseline_source_capture']==original['source_capture'] and build['baseline_source_archive']==original['source_archive'] and build['physical_objects_recompiled']==1 and build['retained_physical_objects']==112 and len(build['retained_project_objects'])==112 and build['actual_link_objects']==113 and len(build['runtime'])==7 and len(build['calls'])==2,'Private build must preserve the actual original source/object provenance')
    need(Path(bind(build['program'])['path'])==PROGRAM and PROGRAM.parent!=Path(original['program']['path']).parent,'Only the new private program is allowed; original executable is protected')
    for key in ('source_capture','source_archive'):
        need(bind(build[key])!=original[key],'Modified private source identity cannot impersonate the frozen baseline')
    need(admission['passed'] and admission['allowed_job']==TAG and admission['diagnostic_only'] and admission['output_only_diagnostic_replay'] and admission['intervention']=='terminal_rejection_printf_only' and admission['prepared']==stat(PREP) and admission['private_build']==stat(BUILD) and admission['input_xml']==stat(CONFIG) and admission['original_run']==stat(ORIGINAL_RUN) and admission['source_pre_file']==stat(matrix.PRE) and admission['planned_steps']==stat(matrix.PLAN) and admission['planned_global_end']==matrix.END and admission['expected_saved_frames']==matrix.SAMPLES and admission['native_auto_authorized'] is False and admission['terminal_queue_once'] is True,'A separate root admission for this exact output-only replay is required')
    for key in ('program','source_capture','source_archive'):
        need(bind(admission[key])==bind(build[key]),'Root private program/source binding differs: '+key)
    need(admission['root_thread_id']==os.environ.get('CODEX_THREAD_ID')==THREAD and matrix.notifier_path() is not None,'Actual admitted root thread/current Codex notifier required before launching')
    consumed.extend(stat(q) for q in (PREP,ADMISSION,BUILD,CONFIG))
    consumed.extend(bind(q) for q in prepared['consumed'])
    consumed.extend(bind(build[key]) for key in ('program','source_capture','source_archive','private_gpu_source','private_wall_include','baseline_source_build','baseline_source_capture','baseline_source_archive'))
    consumed.extend(bind(q) for q in build['runtime']+build['calls'])
    # The separately reviewed build receipt owns object provenance; no old-object
    # enumeration, rehash or repeated source archive scan is performed here.
    matrix.verify(consumed);matrix.old.old.idle(True)
    return admission,build,original,previous,window,preload,material,gen,consumed


def notify_once(run_path):
    attempt=L/(TAG+'.queue_attempt.json');reply=L/(TAG+'.queue_result.json')
    need(not attempt.exists() and not reply.exists(),'Terminal queue was already attempted; never resend or rearm')
    need(os.environ.get('CODEX_THREAD_ID')==THREAD,'Terminal queue must stay on the admitted actual root thread')
    program=matrix.notifier_path()
    message=('The single root-admitted C08 AS.7 terminal-printf diagnostic replay is terminal: '+str(run_path)+'. Read original run/start/call/status/root and owner admissions, actual child/tool exits, last original console and private build/source/PRE/input/full91plan bindings. This is c08_h18_wall_fail_probe_GPU_r1, Kernel2 H1.8/5us, same certified Wendland psi0 PRE, AS.7/n3.825, original AV/NoPen/CompletedOnly and target2180000. Expected wall803 rejection remains a solver failure, not a completed .9s result. Private C08_WALL_FAIL printf text is terminal diagnostic evidence; do not invent its unsaved arrays. Root alone may authorize later existing failed34_as07 native decoding IF genuine same failure/profile and compare retained34 native prefix; nothing is automatic. Unexpected actual0/full completion remains pending review and is not physical acceptance. Preserve all partials and original failures. No rerun, PRE, next physics, half chain, other psi, CPU/GPU control, auto-native/VTK, watcher, resend or rearm. This verified same-thread terminal queue is attempted once with45s timeout; timeout may have delivered.')
    argv=[str(program) if program else 'codex','queue','--thread',THREAD,'--message',message]
    save(attempt,dict(stage=TAG,utc=base.utc(),thread=THREAD,run=stat(run_path),program=stat(program) if program else None,arguments=argv,attempts=1,timeout_s=45,do_not_resend=True))
    result=dict(stage=TAG,attempts=1,do_not_resend=True)
    try:
        need(program is not None,'Current Codex notifier unavailable; terminal evidence remains preserved')
        completed=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        result.update(actual_exit=completed.returncode,status='queued' if completed.returncode==0 else 'queue_failed',stdout=completed.stdout,stderr=completed.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(reply,result)


def run():
    out=T/'outputs'/TAG;run_path=L/(TAG+'.run.json')
    allowed={PREP.name,ADMISSION.name}
    need(not out.exists() and not any(q.name not in allowed for q in L.glob(TAG+'.*')),'Existing probe output/owner/call/partial is protected; no retry')
    claim=L/(TAG+'.claim.json');save(claim,dict(stage=TAG,owner_pid=os.getpid(),owner_created_epoch=psutil.Process().create_time(),single_attempt=True))
    consumed=[];phase='preflight'
    result=dict(stage=TAG,passed=False,solver_completed=False,diagnostic_only=True,intervention='terminal_rejection_printf_only',physical_acceptance=False,native_review_pending=True,trajectory_equivalence_proven=False,automatic_next_job=False,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,PartVTK_invocations=0,SHA_scans=0)
    try:
        admission,build,original,previous,window,preload,material,gen,consumed=context();consumed.append(stat(claim));out.mkdir();prefix=out/TAG
        phase='GenCase';result['GenCase_invocations']=1
        result['GenCase_call']=invoke(TAG+'.gencase',[gen['path'],str(CONFIG.with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml');actual=matrix.check_input(seed,.7,True)
        baseline_xml=ET.parse(bind(original['input_xml'])['path']).getroot()
        need(all(matrix.signature(actual.find(section))==matrix.signature(baseline_xml.find(section)) for section in ('execution/special','execution/parameters')),'Generated diagnostic physics differs from actual original AS.7 XML')
        seeds=[stat(Path(str(prefix)+suffix)) for suffix in ('.xml','.bi4','_Normals.nbi4')];consumed.extend(seeds)
        profile=out/'native_profile.csv';matrix.write_profile(profile,actual,.7,material);consumed.append(stat(profile));matrix.verify(consumed)
        argv=[str(PROGRAM),'-gpu:0','-stable','-mdbc_freeslip:1',str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:'+str(matrix.END)]
        need(argv[1:4]==original['argv'][1:4] and argv[6:]==original['argv'][6:],'Only private executable and fresh input/output labels may differ in solver argv')
        owner=L/(TAG+'.owner_admission.json')
        save(owner,dict(stage=TAG,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(ADMISSION),private_build=stat(BUILD),program=bind(build['program']),source_build=stat(BUILD),source_capture=build['source_capture'],source_archive=build['source_archive'],baseline_source_build=original['source_build'],baseline_source_capture=original['source_capture'],baseline_source_archive=original['source_archive'],runtime=build['runtime'],source_pre_file=stat(matrix.PRE),source_run=previous['source_run'],source_native=previous['source_native'],source_native_call=previous['source_native_call'],source_material_profile=previous['source_material_profile'],source_physical_review=previous['source_physical_review'],input_xml=stat(seed),seed=seeds,planned_steps=stat(matrix.PLAN),planned_new_updates=180000,planned_global_end=matrix.END,expected_saved_frames=matrix.SAMPLES,Kernel=2,AS_coefficient=.7,AS_exponent=3.825,group='psi0',same_material_plastic_PRE=True,argv=argv,solver_argv=argv,consumed=consumed))
        consumed.append(stat(owner))
        result.update(group='psi0',kernel=2,kernel_name='Wendland',geometry_profile='bedroles',keep_bed_overlap=False,same_material_plastic_PRE=True,expected_source_handoff_schema=2,private_build=stat(BUILD),program=bind(build['program']),source_build=stat(BUILD),source_capture=build['source_capture'],source_archive=build['source_archive'],baseline_source_build=original['source_build'],baseline_source_capture=original['source_capture'],baseline_source_archive=original['source_archive'],runtime=build['runtime'],source_pre_file=stat(matrix.PRE),source_run=previous['source_run'],source_native=previous['source_native'],input_xml=stat(seed),seed=seeds,planned_steps=stat(matrix.PLAN),native_profile=stat(profile),owner_admission=stat(owner),argv=argv,AS_coefficient=.7,AS_exponent=3.825,hdp=1.8,fixed_dt_s=matrix.DT)
        phase='solver';result['solver_invocations']=1
        result['actual_call']=base.owned(TAG,argv,PROGRAM,False,stat(owner))
        result.update(actual_exit=0,actual_Win32_exit=0,actual_tool_exit=0,solver_returned_zero=True)
        phase='unexpected_normal_completion_review';result.update(matrix.old.old.output_checks(out,.7,window,preload))
        matrix.verify(consumed);result.update(passed=True,solver_completed=True,unexpected_normal_completion=True,consumed_stats_unchanged=True)
    except Exception as error:
        result.update(first_failure=str(error),failed_stage=phase)
    call_path=L/(TAG+'.call.json');observation_errors=[]
    try:
        if call_path.exists():
            call=read(call_path);result.update(actual_call=stat(call_path),actual_exit=call['actual_solver_Win32_exit'],actual_Win32_exit=call['actual_solver_Win32_exit'],actual_tool_exit=call['actual_Popen_wait_exit'],ownership_errors=call['ownership_errors'])
    except Exception as error:observation_errors.append('Actual call observation: '+str(error))
    try:
        raw=out/'Run.out'
        if raw.exists():
            text=raw.read_text(encoding='utf-8-sig',errors='replace');hit=re.search(r'^Text: (.+)$',text,re.M)
            rejected=re.findall(r'DynamicPoreWall rejected: stage=(\d+) sorted_slot=(\d+) native_id=(\d+) step_start=([0-9.eE+-]+) step=(\d+) B=\(([^)]+)\) normal=\(([^)]+)\)\.',text)
            parts=sorted((out/'data').glob('Part_*.bi4'))
            matches=(len(rejected)==1 and int(rejected[0][0])==0 and int(rejected[0][2])==803 and float(rejected[0][3])==10.332704999693412 and int(rejected[0][4])==2066541 and [q.name for q in parts]==['Part_%04d.bi4'%i for i in range(34)])
            result.update(Run_out=stat(raw),first_engine_exception_text=hit[1] if hit else None,reported_wall_rejection_texts=['stage='+','.join(q) for q in rejected],observed_saved_files=len(parts),PARTs=[stat(q) for q in parts],reported_failure_profile_matches_original=bool(matches),expected_failure_observed=bool(matches and result.get('actual_exit')==result.get('actual_Win32_exit')==result.get('actual_tool_exit')==1 and not result.get('ownership_errors')))
    except Exception as error:observation_errors.append('Terminal Run.out observation: '+str(error))
    try:
        solver_log=L/(TAG+'.solver.log')
        if solver_log.exists():
            lines=solver_log.read_text(encoding='utf-8-sig',errors='replace').splitlines();diagnostics=[q for q in lines if 'C08_WALL_FAIL ' in q]
            result.update(solver_log=stat(solver_log),terminal_diagnostic_lines=diagnostics,terminal_diagnostic_line_count=len(diagnostics))
    except Exception as error:observation_errors.append('Terminal printf observation: '+str(error))
    unchanged=False;last_console=None
    try:unchanged=all(stat(q['path'])==q for q in consumed)
    except Exception as error:observation_errors.append('Terminal stat audit: '+str(error))
    try:last_console=base.last_part(out)
    except Exception as error:observation_errors.append('Last original console observation: '+str(error))
    if observation_errors or not unchanged:result['passed']=False
    result.update(consumed=consumed,consumed_stats_unchanged=unchanged,terminal_observation_errors=observation_errors,last_original_console_line=last_console,unsaved_failure_time_reconstructed=False,unsaved_state_reconstructed=False,original_target_completed_step=matrix.END,original_target_samples=matrix.SAMPLES,native_invocation_authorized_by_this_owner=False)
    save(run_path,result)
    base.publish(TAG,out,None,None,'completed_pending_explicit_native_review' if result['solver_completed'] else 'failed_preserved_no_next_job')
    if call_path.exists():notify_once(run_path)
    print(json.dumps(dict(run=str(run_path),solver_completed=result['solver_completed'],actual_exit=result.get('actual_exit'),physical_acceptance=False)),flush=True)
    return 0 if result['passed'] else (result.get('actual_exit') or 1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','run'));parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    need(args.execution_authorized,'Author-only until root full-read and separate explicit preparation/run authorization')
    prepare() if args.action=='prepare' else exit(run())
