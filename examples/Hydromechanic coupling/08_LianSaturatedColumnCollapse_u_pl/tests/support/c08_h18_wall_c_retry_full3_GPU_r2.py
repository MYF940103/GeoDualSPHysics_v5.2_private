"""One separately admitted C-quality retry psi0 full3 direct owner; no reader/next job."""
import argparse
import math
import os
import re
import subprocess
from pathlib import Path
import psutil
import c08_h18_wend_matrix_r1 as m
import c08_h18_wall_c_retry_prefix4_GPU_r1 as short
import c08_h18_hg_opt_full3_r1 as oldowner
import c08_h18_hg_wall_host_jobs_r2 as host

T,C,L=m.T,m.C,m.L
TAG='c08_h18_wall_c_retry_full3_GPU_r2'
SCRIPT=Path(__file__).resolve();NOTE=T/'notes'/(TAG+'.md')
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8'
OUT=T/'outputs'/TAG;PLAN=T/'configs'/(TAG+'.steps.csv')
PREP=L/(TAG+'.prepare.json');RUN=L/(TAG+'.run.json');START=L/(TAG+'.start.json')
CALL=L/(TAG+'.call.json');SEAL=L/(TAG+'.solver_completed.json');STATUS=L/(TAG+'.status.json')
QUEUE=L/(TAG+'.queue_attempt.json');REPLY=L/(TAG+'.queue_result.json')
BUILD=short.BUILD;BUILD_REVIEW=short.BUILD_REVIEW;COMP_REVIEW=short.COMP_REVIEW
CONTROL='c08_h18_as03n255_full3_r1'
CRUN=L/(CONTROL+'.run.json');CPREP=L/(CONTROL+'.prepare.json')
CNATIVE=L/'c08_h18_as03n255_full3_native_r1.check.json'
CREVIEW=L/'c08_h18_as03n255_full3_review_r1.check.json'
CODEX=oldowner.CODEX;CODEX_STAT=oldowner.CODEX_STAT
ENVIRONMENT='C08_HG_OPT_H18'
DT=.000005;PRESTEP=2000000;END=2600000;FRAMES=301
JOB=dict(steps=tuple(2000001+2000*part for part in range(300))+(END,),updates=600000,frames=FRAMES)


def admission(phase,consumed):
    path=L/(TAG+'.root_'+phase+'_admission.json');q=short.take(path,consumed)
    m.need(q['authorized'] and q['allowed_stage']==TAG and q['phase']==phase
           and q['execution_script']==m.stat(SCRIPT) and q['note']==m.stat(NOTE)
           and q['source_build']==m.stat(BUILD) and q['build_review']==m.stat(BUILD_REVIEW)
           and q['component_review']==m.stat(COMP_REVIEW) and q['new_prefix4_review']==m.stat(short.REVIEW)
           and q['root_thread_id']==os.environ.get('CODEX_THREAD_ID')==THREAD
           and q['single_full3_only'] and q['terminal_queue_once'] and not q['watcher']
           and not q['automatic_native'] and not q['automatic_next_job'] and q['codex']==CODEX_STAT,
           'Separate exact current-root prepare/run and one terminal queue admission required')
    if phase=='run':m.need(q['preparation']==m.stat(PREP),'Prepared full3 binding differs')
    short.bound(q['codex'],consumed);short.bound(q['physical_decision'],consumed)
    return q,m.stat(path)


def prerequisites(consumed):
    # Reuse the reviewed narrow candidate/object/component checks, not an old
    # build label and not a repeated113-object/276-source or SHA scan.
    consumed.extend((m.stat(short.SCRIPT),m.stat(short.NOTE),m.stat(Path(oldowner.__file__)),m.stat(Path(host.__file__))))
    b=short.prerequisites(consumed)
    r=short.take(short.RUN,consumed);q=short.take(short.REVIEW,consumed)
    m.need(r['passed'] and r['solver_completed'] and r['consumed_stats_unchanged']
           and r['actual_exit']==r['actual_Win32_exit']==0 and r['ownership_failure'] is None
           and r['solver_identity_matches'] and r['program']==b['program'] and r['source_build']==m.stat(BUILD)
           and r['saved_frames']==4 and r['actual_steps']==2006001 and r['new_updates']==6001
           and q['passed'] and q['solver_run']==m.stat(short.RUN) and q['native_check']==m.stat(short.NATIVE_CHECK)
           and q['consumed_stats_unchanged'] and q['candidate_is_numerical_change'] and not q['output_only']
           and q['all22_native_four_records_byte_equal'] and q['clock_layout_signed_rows_byte_equal']
           and q['HG_eight60column_rows_byte_equal'] and q['policy_equal'] and q['plastic_saved_stage_present']
           and q['all_original_native_guards'] and q['normal_short_no_fault_capture'],
           'The new candidate must pass its own strict real-plastic four-frame integration first')
    short.good_call(short.bound(r['actual_call'],consumed),consumed)
    nr=short.take(short.bound(q['native_check'],consumed),consumed)
    m.need(nr['passed'] and nr['reader_invocations']==1 and nr['all_original_native_guards'],
           'Actual unique new short native review required')
    short.good_call(short.bound(q['actual_native_call'],consumed),consumed)
    done=short.take(short.bound(q['native_completion'],consumed),consumed)
    m.need(done['passed'] and done['samples']==4 and done['completed_steps']==2006001
           and done['typed_arrays']==22 and done['actual_native_IDs_per_frame']==6805
           and done['max_scalar_clock_error_s']<=1e-14 and done['max_signed_dterror_s']<=1e-14
           and not done['native_rewritten'],'Original short native guards must remain unchanged')
    for leaf in ('native_r1/typed22.bin','native_r1/typed22_layout.csv','native_r1/clocks.csv',
                 'C08OptPlasticHG.csv','C08OptPlasticHGPolicy.json'):
        refs=[entry for entry in q['consumed'] if Path(entry['path']).resolve()==(short.OUT/leaf).resolve()]
        m.need(len(refs)==1,'One exact sealed own-short prefix artifact required: '+leaf)
        short.bound(refs[0],consumed)
    return b,dict(run=m.stat(short.RUN),review=m.stat(short.REVIEW),native_check=m.stat(short.NATIVE_CHECK),
        native_completion=q['native_completion'],samples=4,completed_steps=list(short.STEPS),
        native_and_signed_prefix_review_pending=True)


def control(consumed):
    r=short.take(CRUN,consumed);p=short.take(CPREP,consumed)
    n=short.take(CNATIVE,consumed);v=short.take(CREVIEW,consumed)
    m.need(r['passed'] and r['solver_completed'] and r['consumed_stats_unchanged']
           and r['actual_exit']==r['actual_Win32_exit']==r['actual_tool_exit']==0
           and r['actual_steps']==END and r['saved_frames']==FRAMES and r['AS_coefficient']==.3
           and r['AS_exponent']==2.55 and r['hdp']==1.8 and r['fixed_dt_s']==DT and not r['keep_bed_overlap']
           and p['stage']==CONTROL+'.prepare' and p['prepared_only'] and p['exact_inverse_original_XML_bytes'] and p['consumed_stats_unchanged']
           and p['program']==r['program'] and p['source_pre_file']==r['source_pre_file']
           and p['planned_steps']==r['planned_steps'] and p['source_build']==r['source_build']
           and p['source_native']==r['source_native'] and p['source_run']==r['source_run']
           and p['group']==r['group']=='psi0' and p['Kernel']==r['Kernel']==2
           and p['planned_global_end']==r['planned_global_end']==END
           and p['planned_new_updates']==r['planned_new_updates']==600000
           and p['expected_saved_frames']==r['expected_saved_frames']==FRAMES
           and p['planned_TimeOut']==r['planned_TimeOut']==.01
           and p['AS_coefficient']==r['AS_coefficient']==.3 and p['AS_exponent']==r['AS_exponent']==2.55
           and n['passed'] and n['reader_invocations']==1 and n['consumed_stats_unchanged']
           and v['analysis_complete'] and v['consumed_stats_unchanged'],
           'Original completed HG0 full301 generated input/control must remain adopted, not rerun')
    for key in ('source_pre_file','source_run','source_native','input_xml','planned_steps','native_profile'):
        short.bound(r[key],consumed)
    for ref in r['seed']:short.bound(ref,consumed)
    source=short.take(r['source_native']['path'],consumed)
    m.need(source['passed'] and source['certified_PRE'] and source['expected_handoff_schema']==2
           and source['same_material_plastic_PRE'] and source['completed_steps']==PRESTEP
           and source['group']=='psi0' and source['actual_end_s']==9.9999999997060076
           and source['kernel_name_declared']=='Wendland' and source['declared_Kernel_XML_CSV']==2,
           'Original same-material schema2 PRE is required; no new preload or exact-HG restart')
    return r,p,source


def prepare():
    m.need(not OUT.exists() and not PLAN.exists() and not PREP.exists(),'Existing full3 preparation/partial protected')
    consumed=[m.stat(SCRIPT),m.stat(NOTE)]
    try:
        ad,adref=admission('prepare',consumed);b,gate=prerequisites(consumed);r,p,source=control(consumed)
        shortprep=short.take(short.PREP,consumed)
        m.need(shortprep['source_pre_file']==r['source_pre_file'],'Candidate short and full3 must use the exact same certified PRE')
        rows=m.table(r['planned_steps']['path'])
        replay,source_clocks,end=oldowner.clock_plan(JOB,source['actual_end_s'],rows)
        m.need(end==12.999999999592434 and len(rows)==301 and len(r['seed'])==3
               and len(m.table(r['native_profile']['path']))==17,'Original full301/17-key input extent required')
        host.summary(T/'outputs'/CONTROL/'Run.csv')
        m.verify(consumed);OUT.mkdir()
        seeds=[host.copy_exact(ref['path'],OUT/Path(ref['path']).name) for ref in r['seed']]
        profile=host.copy_exact(r['native_profile']['path'],OUT/'native_profile.csv')
        plan=host.copy_exact(r['planned_steps']['path'],PLAN)
        xml=next(ref for ref in seeds if Path(ref['path']).suffix=='.xml');seed=Path(xml['path']).with_suffix('')
        argv=[b['program']['path'],'-gpu:0','-stable','-mdbc_freeslip:1',str(seed),str(OUT),'-dirdataout','data','-svres','-nsteps:2600000']
        m.verify(consumed)
        m.save(PREP,dict(stage=TAG+'.prepare',passed=True,prepared_only=True,profile='full3',configuration='Release',
            program=b['program'],source_build=m.stat(BUILD),source_capture=b['source_capture'],source_archive=b['source_archive'],
            replacement_physical_object=b['replacement_physical_object'],root_build_review=m.stat(BUILD_REVIEW),
            component_review=m.stat(COMP_REVIEW),implementation_prerequisites=gate,
            candidate_is_numerical_change=True,output_only=False,retained_objects=113,actual_link_objects=114,
            private_HG_Node_material_recompiled=False,host_fault_capture_retained=True,original_guards_unchanged=True,
            source_pre_file=r['source_pre_file'],source_run=r['source_run'],source_native=r['source_native'],
            control_run=m.stat(CRUN),control_native=m.stat(CNATIVE),control_review=m.stat(CREVIEW),
            control_is_HG0_different_operator_not_half=True,input_xml=xml,seed=seeds,native_profile=profile,
            planned_steps=plan,planned_rows=replay,save_source_clocks_s=source_clocks,runtime=b['runtime'],
            actual_source_time_s=source['actual_end_s'],planned_actual_end_s=end,fixed_dt_s=DT,
            global_nsteps_limit=END,new_updates=600000,expected_saved_frames=FRAMES,
            HG_history_cold_zero=True,DynamicNoPenetrationReactionClosed=False,
            environment_override={ENVIRONMENT:'1'},argv=argv,cwd=str(C),output=str(OUT),
            codex=ad['codex'],physical_decision=ad['physical_decision'],root_admission=adref,
            execution_script=m.stat(SCRIPT),note=m.stat(NOTE),consumed=consumed,consumed_stats_unchanged=True,
            seed_and_profile_and_plan_byte_copied=True,original301_plan_unchanged=True,PRE_adopted_original_absolute_path=True,
            solver_invocations=0,GenCase_invocations=0,reader_invocations=0,VTK_invocations=0,SHA_scans=0,
            physical_acceptance=False,automatic_native=False,automatic_next_job=False,other_psi_held=True,
            terminal_queue_once=True,watcher=False))
    except Exception as error:
        if not PREP.exists():m.save(PREP,dict(stage=TAG+'.prepare',passed=False,first_failure=str(error),consumed=consumed,partial_preserved=True,automatic_retry=False))
        raise


def terminal_once(prep):
    m.need(not QUEUE.exists() and not REPLY.exists(),'Terminal attempt already exists; never resend')
    message=('The single admitted C08 C-quality retry psi0 full3 GPU diagnostic is terminal: '+str(RUN)
        +'. Read original owned start/call/run/status/solver_completed, exact Win32/Popen exits, separate root admissions, '
        'candidate build/source/program and original schema2 Wendland PRE/input/whole301 scalar plan. '
        'Only stage1 finite-nonpositive-C enables the original one nearest retry; this is numerical, not output-only. '
        'One physical CUDA object is new,113 objects and private cached plasticHG remain retained. '
        'Actual10fixture memcheck and own four-frame plastic native22/clock/signed/HG byte regression passed first. '
        'AS.3/n2.55/AV.1/WendlandH1.8/fixed5us/keepfalse/fixed-plane/CompletedOnly remain; '
        '600000new updates/global2600000/301planned saves. PRE is reused with coldzeroHG; ReactionClosed=false. '
        'Exit0/normal summary is pending independent unique native and physical/paper review, never acceptance. '
        'Check existing/active readers before any separately admitted original AS255 formal psi0 read; '
        'all22/6805/P0/J/kappa/FS/ledger/plane/actualclock/signed and HG phase/work/history guards remain. '
        'Own first4 actual native/time/signed/HG states must be compared with retained ownprefix4; preserve headers. '
        'Old HG0 is a descriptive different-operator control, not half truth; old failed99 and forced .9 final stay preserved. '
        'On failure preserve actual first error, handles/exits, partials and last original console PART; '
        'never reconstruct unsaved arrays/time or retry. Host fault capture is actual inputs, not rejected fit registers '
        'or a saved native state. Completed solver plus derived failure requires offline repair only. '
        'No automatic reader/VTK/otherpsi/half/PRE/nextsolver. This directowner queues once45s; '
        'timeout may have delivered, never resend/rearm/addwatcher or selftest.')
    argv=[str(CODEX),'queue','--thread',THREAD,'--message',message]
    m.save(QUEUE,dict(stage=TAG,run=m.stat(RUN),status=m.stat(STATUS),thread=THREAD,program=prep['codex'],
        arguments=argv,attempts=1,timeout_s=45,only_completion_mechanism='same_direct_run_owner',do_not_resend=True))
    result=dict(stage=TAG,attempts=1,do_not_resend=True)
    try:
        m.need(os.environ.get('CODEX_THREAD_ID')==THREAD and prep['codex']==CODEX_STAT,'Current root notifier binding changed')
        m.bind(prep['codex'])
        call=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        result.update(actual_exit=call.returncode,status='queued' if call.returncode==0 else 'queue_failed',stdout=call.stdout,stderr=call.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    m.save(REPLY,result)


def run():
    m.need(all(not q.exists() for q in (RUN,CALL,START,SEAL,STATUS,QUEUE,REPLY,L/(TAG+'.log'))),
           'Existing full3 owner/attempt/completion protected; never rerun or rearm')
    consumed=[m.stat(SCRIPT),m.stat(NOTE)];p=None;call=None
    result=dict(stage=TAG,passed=False,solver_completed=False,solver_invocations=0,solver_launch_attempts=0,
        candidate_is_numerical_change=True,output_only=False,physical_acceptance=False,
        native_review_pending=True,HG_sidecar_review_pending=True,automatic_native=False,automatic_next_job=False,
        other_psi_held=True,terminal_queue_once=True,watcher=False,unsaved_state_reconstructed=False,SHA_scans=0)
    try:
        ad,adref=admission('run',consumed);b,gate=prerequisites(consumed);p=short.take(PREP,consumed)
        m.need(p['passed'] and p['prepared_only'] and p['consumed_stats_unchanged'] and p['profile']=='full3'
               and p['execution_script']==m.stat(SCRIPT) and p['note']==m.stat(NOTE)
               and p['source_build']==m.stat(BUILD) and p['program']==b['program']
               and p['implementation_prerequisites']==gate and p['codex']==ad['codex']
               and p['physical_decision']==ad['physical_decision'] and p['global_nsteps_limit']==END
               and p['new_updates']==600000 and p['expected_saved_frames']==FRAMES
               and p['environment_override']=={ENVIRONMENT:'1'},'Exact own prepared full3 and new short gates required')
        for key in ('program','source_capture','source_archive','source_pre_file','source_run','source_native',
                    'input_xml','native_profile','planned_steps','codex','physical_decision'):
            short.bound(p[key],consumed)
        for ref in p['seed']+p['runtime']:short.bound(ref,consumed)
        m.need(OUT.is_dir() and not (OUT/'data').exists() and not (OUT/'Run.out').exists()
               and p['argv'][0]==b['program']['path'] and p['argv'][-1]=='-nsteps:2600000',
               'Fresh exact prepared full3 output and global cap required')
        for proc in psutil.process_iter(['exe']):
            try:m.need(not proc.info['exe'] or Path(proc.info['exe']).resolve()!=Path(p['program']['path']).resolve(),'Exact candidate program already active; no duplicate solver')
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        proc=psutil.Process();owner=dict(pid=proc.pid,created_epoch=proc.create_time(),exe=proc.exe(),argv=proc.cmdline(),parent_pid=proc.ppid())
        env=dict(os.environ)
        for key in list(env):
            if key.upper()==ENVIRONMENT:env.pop(key)
        env[ENVIRONMENT]='1';m.verify(consumed)
        m.save(START,dict(stage=TAG+'.start',owner=owner,preparation=m.stat(PREP),root_admission=adref,
            program=p['program'],source_build=p['source_build'],source_capture=p['source_capture'],source_archive=p['source_archive'],
            source_pre_file=p['source_pre_file'],input_xml=p['input_xml'],planned_steps=p['planned_steps'],argv=p['argv'],
            cwd=p['cwd'],environment_override=p['environment_override'],consumed=consumed,automatic_native=False,automatic_next_job=False))
        result.update({key:p[key] for key in ('program','source_build','source_capture','source_archive','replacement_physical_object',
            'implementation_prerequisites','source_pre_file','source_run','source_native','control_run','control_native','control_review',
            'input_xml','seed','native_profile','planned_steps','actual_source_time_s','planned_actual_end_s','fixed_dt_s',
            'global_nsteps_limit','new_updates','expected_saved_frames','environment_override','HG_history_cold_zero',
            'DynamicNoPenetrationReactionClosed','codex','physical_decision')})
        result.update(owner=owner,preparation=m.stat(PREP),root_admission=adref,argv=p['argv'],output=str(OUT),solver_launch_attempts=1)
        result['actual_call']=m.invoke(TAG,p['argv'],C,env=env)
    except Exception as error:result['first_failure']=str(error)
    if CALL.exists():
        result['actual_call']=m.stat(CALL);call=m.read(CALL);child=call.get('child')
        matches=bool(p and child and Path(child['exe']).resolve()==Path(p['program']['path']).resolve()
            and child['argv']==p['argv'] and child['creation_filetime_100ns']>0
            and child['parent_pid']==result['owner']['pid'] and call['owner']['pid']==result['owner']['pid']
            and abs(call['owner']['created_epoch']-result['owner']['created_epoch'])<=5e-6)
        result.update(actual_exit=call.get('actual_Popen_wait_exit'),actual_Win32_exit=call.get('actual_Win32_exit'),
            actual_tool_exit=call.get('actual_Popen_wait_exit'),actual_tool_Win32_exit=call.get('actual_Win32_exit'),
            ownership_failure=call.get('ownership_failure'),solver_identity=child,solver_identity_matches=matches,solver_invocations=1 if child else None)
    try:
        m.need(call and result['solver_identity_matches'] and result['actual_exit']==result['actual_Win32_exit']==0
               and result['ownership_failure'] is None,'Actual owned full3 solver normal exit unproved')
        text=(OUT/'Run.out').read_text(encoding='utf-8-sig')
        m.need('Finished execution (code=0).' in text and '[Simulation INTERRUPTED' not in text
               and 'certified same-material plastic schema/contract2' in text,'Normal original schema2 completion required')
        # Seal actual physical completion before any Run.csv/postcheck failure.
        m.save(SEAL,dict(stage=TAG+'.solver_completed',solver_completed=True,actual_call=m.stat(CALL),original_start=m.stat(START),
            owner=result['owner'],solver_identity=result['solver_identity'],program=p['program'],source_build=p['source_build'],
            source_capture=p['source_capture'],source_archive=p['source_archive'],source_pre_file=p['source_pre_file'],
            input_xml=p['input_xml'],planned_steps=p['planned_steps'],actual_solver_Win32_exit=result['actual_Win32_exit'],
            actual_tool_exit=result['actual_tool_exit'],Run_out=m.stat(OUT/'Run.out'),native_review_pending=True,
            HG_sidecar_review_pending=True,no_solver_retry=True,physical_acceptance=False))
        result.update(solver_completed=True,solver_completion=m.stat(SEAL))
        summary=host.summary(OUT/'Run.csv');parts=sorted((OUT/'data').glob('Part_*.bi4'))
        m.need(int(summary['Steps'])==END and int(summary['PartFiles'])==FRAMES
               and summary['PartsOut']==summary['PartsOutRhop']==summary['PartsOutVel']=='0'
               and [q.name for q in parts]==['Part_%04d.bi4'%i for i in range(FRAMES)],
               'Actual full301/global2600000/no-exclusion summary differs')
        m.need(math.isfinite(float(summary['PhysicalTime'])) and abs(float(summary['PhysicalTime'])-p['planned_actual_end_s'])<=.00000051,
               'Rounded Run.csv endpoint differs; exact native clocks remain pending')
        m.need('first_failure' not in result,'Preserve an earlier actual owner failure')
        m.verify(consumed)
        result.update(passed=True,consumed_stats_unchanged=True,summary=summary,actual_steps=END,saved_frames=FRAMES,
            Run_out=m.stat(OUT/'Run.out'),Run_csv=m.stat(OUT/'Run.csv'),PARTs=[m.stat(q) for q in parts],
            particle_data_files=[m.stat(q) for q in sorted((OUT/'data').iterdir()) if q.is_file()],Run_csv_endpoint_is_rounded_not_native_clock=True)
    except Exception as error:result.setdefault('first_failure',str(error))
    if (OUT/'Run.out').exists():
        text=(OUT/'Run.out').read_text(encoding='utf-8-sig',errors='replace')
        exception=re.search(r'^(?:Text: |\*\*\* Exception\(exc\): )(.*)$',text,re.M)
        result.update(Run_out=m.stat(OUT/'Run.out'),first_engine_exception_text=exception[1] if exception else None,
            reported_wall_rejection_lines=[line for line in text.splitlines() if line.startswith('DynamicPoreWall rejected:')],
            observed_saved_files=len(list((OUT/'data').glob('Part_*.bi4'))))
    if call and Path(call['log']['path']).is_file():
        raw=Path(call['log']['path']).read_text(encoding='mbcs',errors='replace')
        rows=[line for line in raw.splitlines() if re.match(r'^Part_\d+\s',line)]
        result.update(console_log=m.bind(call['log']),last_original_console_PART_line=rows[-1] if rows else None,
            raw_console_wall_rejection_lines=[line for line in raw.splitlines() if line.startswith('DynamicPoreWall rejected:')],
            raw_console_first_exception_lines=[line for line in raw.splitlines() if line.startswith('*** Exception') or line.startswith('Text:')][:2])
    try:
        capture=host.capture_summary(OUT);capture.pop('expected_99_saved_prefix_comparison_pending',None)
        capture['saved_prefix_comparison_requires_actual_shared_steps']=True;result['host_fault_capture_observation']=capture
    except Exception as error:result['host_capture_observation_error']=str(error)
    try:unchanged=all(m.stat(ref['path'])==ref for ref in consumed)
    except Exception as error:unchanged=False;result['terminal_stat_error']=str(error)
    if not unchanged:result['passed']=False
    result.update(consumed=consumed,consumed_stats_unchanged=unchanged)
    if result['solver_launch_attempts'] and call is None:result.update(solver_invocations=None,solver_launch_outcome_not_handle_proven=True)
    if not result['passed']:result['surviving_process_observations']=host.observe_survivors(call)
    m.save(RUN,result)
    m.save(STATUS,dict(stage=TAG,status='completed_pending_unique_native_and_physical_review' if result['passed'] else
        'completed_solver_review_failed' if result['solver_completed'] else 'failed_preserved_no_retry',run=m.stat(RUN),
        automatic_native=False,automatic_next_job=False,terminal_queue_once=True,watcher=False,physical_acceptance=False))
    if call is not None and result['solver_launch_attempts']==1:terminal_once(p)
    return 0 if result['passed'] else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('prepare','run'))
    parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    m.need(args.execution_authorized,'Separate root prepare/run admission required; no automatic solver')
    if args.phase=='prepare':prepare()
    else:raise SystemExit(run())
