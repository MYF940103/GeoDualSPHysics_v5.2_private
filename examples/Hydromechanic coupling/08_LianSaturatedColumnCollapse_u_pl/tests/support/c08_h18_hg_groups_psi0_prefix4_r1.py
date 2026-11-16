"""One separately admitted groups-guard psi0 four-save implementation regression."""
import argparse
import csv
import os
from pathlib import Path
import psutil
import c08_h18_wend_matrix_r1 as m
import c08_h18_hg_wall_host_jobs_r2 as host

T,C,L=m.T,m.C,m.L
TAG='c08_h18_hg_groups_psi0_prefix4_r1'
SCRIPT=Path(__file__).resolve()
NOTE=T/'notes'/(TAG+'.md')
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8'
BUILD=L/'c08_h18_hg_groups_build_r1.build.json'
BUILD_REVIEW=L/'c08_h18_hg_groups_build_r1.root_review_r1.json'
MATERIAL_CHECK=L/'c08_h18_hg_material_groups_probe_r1.check.json'
ORIGINAL_SCRIPT=T/'support/c08_h18_wall_c_retry_prefix4_GPU_r1.py'
OLDTAG='c08_h18_wall_c_retry_prefix4_GPU_r1'
OLDRUN=L/(OLDTAG+'.run.json')
OLDPREP=L/(OLDTAG+'.prepare.json')
OLDREVIEW=L/(OLDTAG+'.check.json')
OLDOUT=T/'outputs'/OLDTAG
READER_BUILD=L/'c08_h18_hg_opt4_native_r1.build.json'
OUT=T/'outputs'/TAG
PLAN=T/'configs'/(TAG+'.steps.csv')
PREP=L/(TAG+'.prepare.json')
RUN=L/(TAG+'.run.json')
CALL=L/(TAG+'.call.json')
START=L/(TAG+'.start.json')
SEAL=L/(TAG+'.solver_completed.json')
STATUS=L/(TAG+'.status.json')
NATIVE_CHECK=L/(TAG+'.native.check.json')
REVIEW=L/(TAG+'.check.json')
ENVIRONMENT='C08_HG_OPT_H18'
STEPS=(2000001,2002001,2004001,2006001)
DT=.000005


def take(path,consumed):
    consumed.append(m.stat(path));return m.read(path)


def bound(ref,consumed):
    consumed.append(m.bind(ref));return Path(ref['path'])


def good_call(path,consumed):
    q=take(path,consumed)
    m.need(q['actual_Popen_wait_exit']==q['actual_Win32_exit']==0 and q['ownership_failure'] is None
           and q['child'] and q['child']['creation_filetime_100ns']>0,'Actual owned tool exits must be zero')
    return q


def prerequisites(consumed):
    b=take(BUILD,consumed);br=take(BUILD_REVIEW,consumed)
    m.need(b['passed'] and b['consumed_stats_unchanged'] and b['configuration']=='Release'
           and b['actual_link_objects']==114 and b['retained_objects_count']==113
           and b['recompiled_host_objects']==1 and b['physical_CUDA_objects_recompiled']==0
           and b['material_guard_only'] and not b['material_law_or_HG_Node_source_changed']
           and b['C_quality_CUDA_object_retained'] and b['host_capture_object_retained']
           and b['retained_opt_HG_objects']==2 and b['exact_inverse_original_host_bytes']
           and not b['public_source_changed'] and not b['class_or_CTE_ABI_changed']
           and br['passed'] and br['build']==m.stat(BUILD)
           and br['source_capture']==b['source_capture'] and br['source_diff']==b['source_diff']
           and br['actual_calls']==b['calls'] and br['actual_CL_link_exits_zero']
           and br['one_host_TU_only'] and br['retained_objects']==113
           and br['C_quality_CUDA_retained'] and br['material_algorithms_unchanged']
           and br['XML_float_angle_storage_matches'] and br['original_psi0_tuple_logically_admitted']
           and br['exact_groups']==['psi0','psi2p5','psim5']
           and br['CPU_exact_material_probe']==m.stat(MATERIAL_CHECK),
           'Reviewed one-host-TU exact-groups guard candidate required')
    for key in ('program','source_capture','source_archive','source_diff','replacement_host_object'):
        bound(b[key],consumed)
    m.need(len(b['calls'])==2,'Exactly one actual CL and link call required')
    for entry,leaf in zip(b['calls'],('cl.exe','link.exe')):
        call=good_call(bound(entry,consumed),consumed)
        m.need(Path(call['program']).name.lower()==leaf and call['child']['argv']==[call['program']]+call['arguments']
               and call['child']['parent_pid']==call['owner']['pid'],'Actual compiler/link identity differs')
    pc=take(MATERIAL_CHECK,consumed);done=pc['completion']
    m.need(pc['passed'] and pc['consumed_stats_unchanged'] and pc['material_probe_invocations']==1
           and pc['solver_invocations']==pc['native_reader_invocations']==pc['GPU_actions']==pc['HGproducer_calls']==0
           and done['passed'] and done['points']==21 and done['groups']==3
           and done['EvaluateMaterial_calls']==21 and done['invalid_ReturnMaterial_calls']==3
           and done['invalid_noncommit_sentinels']==3 and done['independent_manufactured_oracle']
           and done['original_tolerances_unchanged'] and done['GPU_calls']==done['HGproducer_calls']==0,
           'Existing independent CPU21 material probe must pass; this is not a GPU material qualification')
    pb=take(bound(pc['build'],consumed),consumed)
    m.need(pb['passed'],'Actual material probe build failed');bound(pb['program'],consumed)
    good_call(bound(pc['actual_call'],consumed),consumed)
    completions=[bound(q,consumed) for q in pc['outputs'] if Path(q['path']).name=='completion.json']
    m.need(len(completions)==1 and take(completions[0],consumed)==done,'Actual CPU21 completion binding differs')
    for entry in b['runtime']:bound(entry,consumed)
    m.need(len(b['runtime'])==9,'Original isolated nine-file runtime closure required')
    return b


def admission(phase,consumed):
    path=L/(TAG+'.root_'+phase+'_admission.json');q=take(path,consumed)
    m.need(q['authorized'] and q['allowed_stage']==TAG and q['phase']==phase
           and q['execution_script']==m.stat(SCRIPT) and q['note']==m.stat(NOTE)
           and q['source_build']==m.stat(BUILD) and q['build_review']==m.stat(BUILD_REVIEW)
           and q['material_probe']==m.stat(MATERIAL_CHECK) and q['retained_run']==m.stat(OLDRUN)
           and q['retained_review']==m.stat(OLDREVIEW)
           and q['root_thread_id']==os.environ.get('CODEX_THREAD_ID')==THREAD
           and not q['automatic_next_job'] and not q['automatic_native'] and not q['watcher'],
           'Separate exact current-root phase admission required')
    if phase!='prepare':m.need(q['preparation']==m.stat(PREP),'Prepared job binding differs')
    return m.stat(path)


def retained(consumed):
    r=take(OLDRUN,consumed);p=take(OLDPREP,consumed);q=take(OLDREVIEW,consumed)
    m.need(r['passed'] and r['solver_completed'] and r['consumed_stats_unchanged']
           and r['actual_exit']==r['actual_Win32_exit']==0 and r['ownership_failure'] is None
           and r['solver_identity_matches'] and r['saved_frames']==4
           and r['new_updates']==6001 and r['global_nsteps_limit']==STEPS[-1]
           and q['passed'] and q['all22_native_four_records_byte_equal']
           and q['clock_layout_signed_rows_byte_equal'] and q['HG_eight60column_rows_byte_equal']
           and q['policy_equal'] and q['all_original_native_guards']
           and q['plastic_saved_stage_present'] and q['normal_short_no_fault_capture']
           and p['passed'] and p['prepared_only'],'Completed immediate original four-frame plastic control required')
    good_call(bound(r['actual_call'],consumed),consumed)
    bound(p['source_pre_file'],consumed);source=take(bound(p['source_native'],consumed),consumed)
    m.need(source['passed'] and source['certified_PRE'] and source['expected_handoff_schema']==2
           and source['same_material_plastic_PRE'] and source['group']=='psi0'
           and source['completed_steps']==2000000 and source['actual_end_s']==9.9999999997060076,
           'Original certified psi0 PRE must be adopted without a new preload')
    for key in ('input_xml','planned_steps','native_profile','source_run'):bound(p[key],consumed)
    for entry in p['seed']:bound(entry,consumed)
    for leaf in ('native_r1/typed22.bin','native_r1/typed22_layout.csv','native_r1/clocks.csv',
                 'native_r1/completion.json','C08OptPlasticHG.csv','C08OptPlasticHGPolicy.json'):
        refs=[entry for entry in q['consumed'] if Path(entry['path']).resolve()==(OLDOUT/leaf).resolve()]
        expected_refs=2 if leaf=='native_r1/completion.json' else 1
        m.need(len(refs)==expected_refs and all(q==refs[0] for q in refs),
               'Exact sealed immediate comparison identity/count required: '+leaf)
        bound(refs[0],consumed)
    # The real run stores actual ownership; its preparation stores adopted source/profile fields.
    # A local value merge reads both sealed schemas without altering either imported module.
    context=dict(p);context.update(r)
    return context,p


def prepare():
    m.need(not OUT.exists() and not PLAN.exists() and not PREP.exists(),'Existing complete/partial preparation protected')
    consumed=[m.stat(SCRIPT),m.stat(NOTE),m.stat(ORIGINAL_SCRIPT)]
    try:
        ad=admission('prepare',consumed);b=prerequisites(consumed);old,oldprep=retained(consumed)
        m.need(old['fixed_dt_s']==DT and old['environment_override']=={ENVIRONMENT:'1'}
               and old['actual_source_time_s']==9.9999999997060076,'Retained dt/environment/source clock differs')
        rows=m.table(old['planned_steps']['path'])
        m.need(len(rows)==4 and [int(q['completed_step']) for q in rows]==list(STEPS)
               and all(int(q['saved_step'])==int(q['completed_step'])-1 and float(q['dt_s'])==DT for q in rows),
               'The original four real saved steps must be used unchanged')
        m.need(len(m.table(old['native_profile']['path']))==17 and len(old['seed'])==3,
               'Original seventeen-key material profile and generated triple required')
        host.summary(OLDOUT/'Run.csv')
        m.verify(consumed);OUT.mkdir()
        seeds=[host.copy_exact(q['path'],OUT/Path(q['path']).name) for q in old['seed']]
        profile=host.copy_exact(old['native_profile']['path'],OUT/'native_profile.csv')
        plan=host.copy_exact(old['planned_steps']['path'],PLAN)
        input_xml=next(q for q in seeds if Path(q['path']).suffix=='.xml')
        seed=Path(input_xml['path']).with_suffix('')
        argv=[b['program']['path'],'-gpu:0','-stable','-mdbc_freeslip:1',str(seed),str(OUT),'-dirdataout','data','-svres','-nsteps:2006001']
        m.verify(consumed)
        m.save(PREP,dict(stage=TAG+'.prepare',passed=True,prepared_only=True,configuration='Release',profile='prefix4',
            program=b['program'],source_build=m.stat(BUILD),source_capture=b['source_capture'],source_archive=b['source_archive'],
            root_build_review=m.stat(BUILD_REVIEW),material_probe=m.stat(MATERIAL_CHECK),
            retained_C_quality_CUDA_object=next(q for q in b['retained_objects'] if Path(q['path']).name.lower()=='jsphgpu_ker.cu.obj'),
            candidate_is_numerical_change=False,material_guard_only=True,output_only=False,
            retained_objects=113,actual_link_objects=114,private_HG_Node_material_recompiled=False,
            source_pre_file=old['source_pre_file'],source_native=old['source_native'],source_run=old['source_run'],
            retained_run=m.stat(OLDRUN),retained_review=m.stat(OLDREVIEW),seed=seeds,input_xml=input_xml,
            native_profile=profile,planned_steps=plan,planned_rows=rows,runtime=b['runtime'],
            actual_source_time_s=old['actual_source_time_s'],planned_actual_end_s=float(rows[-1]['time_s']),
            fixed_dt_s=DT,global_nsteps_limit=STEPS[-1],new_updates=6001,expected_saved_frames=4,
            HG_history_cold_zero=True,environment_override={ENVIRONMENT:'1'},argv=argv,cwd=str(C),output=str(OUT),
            execution_script=m.stat(SCRIPT),note=m.stat(NOTE),root_admission=ad,consumed=consumed,
            consumed_stats_unchanged=True,seed_and_profile_and_plan_byte_copied=True,GenCase_invocations=0,
            solver_invocations=0,reader_invocations=0,VTK_invocations=0,SHA_scans=0,physical_acceptance=False,
            automatic_native=False,automatic_next_job=False,watcher=False,terminal_queue_once=False))
    except Exception as error:
        if not PREP.exists():m.save(PREP,dict(stage=TAG+'.prepare',passed=False,first_failure=str(error),consumed=consumed,partial_preserved=True,automatic_retry=False))
        raise


def prepared(consumed):
    p=take(PREP,consumed)
    m.need(p['passed'] and p['prepared_only'] and p['consumed_stats_unchanged']
           and p['execution_script']==m.stat(SCRIPT) and p['note']==m.stat(NOTE)
           and p['source_build']==m.stat(BUILD) and p['material_probe']==m.stat(MATERIAL_CHECK)
           and p['new_updates']==6001 and p['expected_saved_frames']==4 and p['global_nsteps_limit']==STEPS[-1],
           'Exact passed prepared four-frame candidate required')
    for key in ('program','source_capture','source_archive','source_pre_file','source_native','source_run',
                'input_xml','native_profile','planned_steps'):bound(p[key],consumed)
    for entry in p['seed']+p['runtime']:bound(entry,consumed)
    return p


def run():
    m.need(all(not q.exists() for q in (RUN,CALL,START,SEAL,STATUS,L/(TAG+'.log'))),'Existing solver owner/attempt/result protected')
    consumed=[m.stat(SCRIPT),m.stat(NOTE),m.stat(ORIGINAL_SCRIPT)];result=dict(stage=TAG,passed=False,solver_completed=False,solver_invocations=0,
        solver_launch_attempts=0,physical_acceptance=False,native_review_pending=True,candidate_is_numerical_change=False,material_guard_only=True,
        output_only=False,automatic_native=False,automatic_next_job=False,watcher=False,terminal_queue_once=False,SHA_scans=0)
    p=None;call=None
    try:
        ad=admission('run',consumed);b=prerequisites(consumed);p=prepared(consumed)
        m.need(p['program']==b['program'] and not (OUT/'data').exists() and not (OUT/'Run.out').exists(),
               'Fresh prepared output and current candidate program required')
        for proc in psutil.process_iter(['exe','cmdline']):
            try:
                m.need(not(proc.info['exe'] and Path(proc.info['exe']).name.lower().startswith('dualsphysics')
                       and any(q.lower().startswith('-gpu') for q in (proc.info['cmdline'] or [])[1:])),
                       'An actual GPU physical target is active; nothing stopped or changed')
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        proc=psutil.Process();owner=dict(pid=proc.pid,created_epoch=proc.create_time(),exe=proc.exe(),argv=proc.cmdline(),parent_pid=proc.ppid())
        env=dict(os.environ)
        for key in list(env):
            if key.upper()==ENVIRONMENT:env.pop(key)
        env[ENVIRONMENT]='1';m.verify(consumed)
        m.save(START,dict(stage=TAG+'.start',owner=owner,program=p['program'],source_build=m.stat(BUILD),
            preparation=m.stat(PREP),root_admission=ad,argv=p['argv'],cwd=p['cwd'],source_pre_file=p['source_pre_file'],
            input_xml=p['input_xml'],planned_steps=p['planned_steps'],environment_override={ENVIRONMENT:'1'},consumed=consumed))
        result.update(owner=owner,program=p['program'],source_build=m.stat(BUILD),source_capture=p['source_capture'],
            source_archive=p['source_archive'],preparation=m.stat(PREP),root_admission=ad,source_pre_file=p['source_pre_file'],
            input_xml=p['input_xml'],planned_steps=p['planned_steps'],argv=p['argv'],output=str(OUT),new_updates=6001,
            expected_saved_frames=4,global_nsteps_limit=STEPS[-1],fixed_dt_s=DT,solver_launch_attempts=1)
        result['actual_call']=m.invoke(TAG,p['argv'],C,env=env)
    except Exception as error:result['first_failure']=str(error)
    if CALL.exists():
        result['actual_call']=m.stat(CALL);call=m.read(CALL);child=call.get('child')
        matches=bool(p and child and child['exe']==p['program']['path'] and child['argv']==p['argv']
            and child['creation_filetime_100ns']>0 and child['parent_pid']==result['owner']['pid']
            and call['owner']['pid']==result['owner']['pid']
            and abs(call['owner']['created_epoch']-result['owner']['created_epoch'])<=5e-6)
        result.update(actual_exit=call.get('actual_Popen_wait_exit'),actual_Win32_exit=call.get('actual_Win32_exit'),
            ownership_failure=call.get('ownership_failure'),solver_identity=child,solver_identity_matches=matches,
            solver_invocations=1 if child else None)
    try:
        m.need(call and result['actual_exit']==result['actual_Win32_exit']==0 and result['ownership_failure'] is None
               and result['solver_identity_matches'],'Actual owned solver normal exit unproved')
        text=(OUT/'Run.out').read_text(encoding='utf-8-sig')
        m.need('Finished execution (code=0).' in text and '[Simulation INTERRUPTED' not in text
               and 'certified same-material plastic schema/contract2' in text,'Normal same-material schema2 completion required')
        m.save(SEAL,dict(stage=TAG+'.solver_completed',solver_completed=True,actual_call=m.stat(CALL),original_start=m.stat(START),
            owner=result['owner'],program=p['program'],source_build=m.stat(BUILD),source_pre_file=p['source_pre_file'],
            input_xml=p['input_xml'],planned_steps=p['planned_steps'],native_review_pending=True,no_solver_retry=True,physical_acceptance=False))
        result.update(solver_completed=True,solver_completion=m.stat(SEAL))
        summary=host.summary(OUT/'Run.csv');parts=sorted((OUT/'data').glob('Part_*.bi4'))
        m.need(int(summary['Steps'])==STEPS[-1] and int(summary['PartFiles'])==4 and summary['PartsOut']=='0'
               and summary['PartsOutRhop']=='0' and summary['PartsOutVel']=='0'
               and abs(float(summary['PhysicalTime'])-p['planned_actual_end_s'])<=.00000051
               and [q.name for q in parts]==['Part_%04d.bi4'%i for i in range(4)],'Original short summary/real four-file extent differs')
        m.need(not (OUT/'WallFaultCaptureHostR1').exists(),'Normal short must not create a fault capture')
        m.verify(consumed)
        result.update(passed=True,consumed_stats_unchanged=True,saved_frames=4,actual_steps=STEPS[-1],summary=summary,
            PARTs=[m.stat(q) for q in parts],Run_out=m.stat(OUT/'Run.out'),Run_csv=m.stat(OUT/'Run.csv'),normal_short_no_fault_capture=True)
    except Exception as error:
        result.setdefault('first_failure',str(error));result['survivor_observations']=host.observe_survivors(call)
    if (OUT/'Run.out').exists():
        text=(OUT/'Run.out').read_text(encoding='utf-8-sig',errors='replace')
        parts=[q for q in text.splitlines() if q.startswith('Part_')];result['last_original_console_PART_line']=parts[-1] if parts else None
        exceptions=[q for q in text.splitlines() if q.startswith('*** Exception') or q.startswith('Text:')]
        result['first_engine_exception_text']=exceptions[:2]
    result['consumed']=consumed;m.save(RUN,result)
    m.save(STATUS,dict(stage=TAG,status='completed_pending_unique_native_review' if result['passed'] else 'failed_preserved',
        run=m.stat(RUN),physical_acceptance=False,automatic_native=False,automatic_next_job=False,watcher=False))
    m.need(result['passed'],result.get('first_failure','Solver run failed; preserve partial evidence'))


def native():
    callpath=L/(TAG+'.native.call.json');nativeout=OUT/'native_r1'
    m.need(not nativeout.exists() and not callpath.exists() and not NATIVE_CHECK.exists()
           and not (L/(TAG+'.native.log')).exists(),'Existing reader owner/partial/completion protected; no second decode')
    consumed=[m.stat(SCRIPT),m.stat(NOTE),m.stat(ORIGINAL_SCRIPT)];result=dict(stage=TAG+'.native',passed=False,reader_invocations=0,solver_invocations=0,physical_acceptance=False,SHA_scans=0)
    try:
        ad=admission('native',consumed);prerequisites(consumed);p=prepared(consumed);r=take(RUN,consumed)
        m.need(r['passed'] and r['solver_completed'] and r['saved_frames']==4 and r['actual_steps']==STEPS[-1]
               and r['program']==p['program'] and r['normal_short_no_fault_capture'],'Completed own normal short solver required')
        good_call(bound(r['actual_call'],consumed),consumed)
        for entry in r['PARTs']:bound(entry,consumed)
        b=take(READER_BUILD,consumed)
        m.need(b['passed'] and b['consumed_stats_unchanged'] and b['profiles']==['short4']
               and b['samples']==4 and b['end']==STEPS[-1] and b['typed_arrays']==22 and b['active_IDs']==6805
               and b['source_and_receiver_numeric_cores_byte_identical'],'Existing unchanged original short4 reader required')
        program=bound(b['program'],consumed)
        for proc in psutil.process_iter(['exe']):
            try:m.need(not proc.info['exe'] or Path(proc.info['exe']).resolve()!=program.resolve(),'This reader is already active')
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        argv=[str(program),'--receiver','short4','psi0',str(OUT/'data'),p['source_pre_file']['path'],
              p['planned_steps']['path'],p['native_profile']['path'],str(nativeout)]
        m.verify(consumed);entry=m.invoke(TAG+'.native',argv,C);result['reader_invocations']=1
        good_call(bound(entry,consumed),consumed);done=take(nativeout/'completion.json',consumed)
        m.need(done['passed'] and done['samples']==4 and done['completed_steps']==STEPS[-1]
               and done['typed_arrays']==22 and done['actual_native_IDs_per_frame']==6805
               and done['ledger_checks']==20000 and done['P0_bits_checks']==27220
               and done['fixed_marker_checks']==7220 and done['nonempty_signed_intervals']==4
               and done['max_scalar_clock_error_s']<=1e-14 and done['max_signed_dterror_s']<=1e-14
               and not done['native_rewritten'],'All original native safety, ledger and signed clocks must pass')
        m.verify(consumed)
        result.update(passed=True,actual_call=entry,native_completion=m.stat(nativeout/'completion.json'),root_admission=ad,
            reader_build=m.stat(READER_BUILD),program=b['program'],consumed_stats_unchanged=True,all_original_native_guards=True)
    except Exception as error:
        result['first_failure']=str(error)
        if callpath.exists():result.update(actual_call=m.stat(callpath),reader_invocations=1)
    result['consumed']=consumed;m.save(NATIVE_CHECK,result)
    m.need(result['passed'],result.get('first_failure','Native review failed; do not decode again'))


def review():
    m.need(not REVIEW.exists(),'Existing complete/partial exact regression protected')
    consumed=[m.stat(SCRIPT),m.stat(NOTE),m.stat(ORIGINAL_SCRIPT)];result=dict(stage=TAG+'.review',passed=False,physical_acceptance=False,
        candidate_is_numerical_change=False,material_guard_only=True,output_only=False,solver_invocations=0,reader_invocations=0,SHA_scans=0,automatic_next_job=False)
    try:
        ad=admission('review',consumed);prerequisites(consumed);prepared(consumed);retained(consumed)
        run=take(RUN,consumed);nr=take(NATIVE_CHECK,consumed)
        m.need(run['passed'] and run['solver_completed'] and nr['passed'] and nr['reader_invocations']==1
               and nr['all_original_native_guards'] and not (OUT/'WallFaultCaptureHostR1').exists(),
               'One completed own solver/native and no short fault capture required')
        good_call(bound(nr['actual_call'],consumed),consumed)
        done=take(bound(nr['native_completion'],consumed),consumed)
        m.need(done['passed'] and done['samples']==4 and done['typed_arrays']==22
               and done['actual_native_IDs_per_frame']==6805 and not done['native_rewritten'],
               'Actual completed unique native receipt binding must remain unchanged')
        equal=[]
        for leaf in ('native_r1/typed22.bin','native_r1/typed22_layout.csv','native_r1/clocks.csv',
                     'C08OptPlasticHG.csv','C08OptPlasticHGPolicy.json'):
            a,b=OUT/leaf,OLDOUT/leaf;consumed.extend((m.stat(a),m.stat(b)))
            m.need(a.read_bytes()==b.read_bytes(),'Original full-byte regression differs: '+leaf);equal.append(leaf)
        with (OUT/'C08OptPlasticHG.csv').open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f);m.need(len(reader.fieldnames)==60,'Original HG60-column schema required');rows=list(reader)
        m.need(len(rows)==8 and any(int(q['smooth'])>0 or int(q['tension'])>0 for q in rows),
               'All eight actual HG rows must include a genuine plastic saved stage')
        m.verify(consumed)
        result.update(passed=True,root_admission=ad,actual_native_call=nr['actual_call'],native_completion=nr['native_completion'],
            native_check=m.stat(NATIVE_CHECK),solver_run=m.stat(RUN),retained_run=m.stat(OLDRUN),
            all22_native_four_records_byte_equal=True,clock_layout_signed_rows_byte_equal=True,
            HG_eight60column_rows_byte_equal=True,policy_equal=True,plastic_saved_stage_present=True,
            all_original_native_guards=True,normal_short_no_fault_capture=True,compared_files=equal,
            short_integration_does_not_qualify_other_group_dispatch=True,not_full3_or_paper_acceptance=True,consumed_stats_unchanged=True)
    except Exception as error:result['first_failure']=str(error)
    result['consumed']=consumed;m.save(REVIEW,result)
    m.need(result['passed'],result.get('first_failure','Exact regression failed; no gate relaxation or automatic next run'))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('prepare','run','native','review'))
    parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    m.need(args.execution_authorized,'Separate current-root review and phase admission required')
    {'prepare':prepare,'run':run,'native':native,'review':review}[args.phase]()

