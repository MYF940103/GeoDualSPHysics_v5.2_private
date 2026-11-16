"""One separately admitted psi2p5 .30 s HG/cache-OFF diagnostic; no reader."""
import argparse
import csv
import math
import os
import re
import subprocess
from pathlib import Path
import psutil
import c08_h18_hg_psi2p5_full3_r1 as full

m,short,host=full.m,full.short,full.host
T,C,L=full.T,full.C,full.L
TAG='c08_h18_psi2p5_hg0_w03_r1'
SCRIPT=Path(__file__).resolve();NOTE=T/'notes'/(TAG+'.md')
OUT=T/'outputs'/TAG;PLAN=T/'configs'/(TAG+'.steps.csv')
PREP=L/(TAG+'.prepare.json');RUN=L/(TAG+'.run.json');START=L/(TAG+'.start.json')
CALL=L/(TAG+'.call.json');SEAL=L/(TAG+'.solver_completed.json');STATUS=L/(TAG+'.status.json')
QUEUE=L/(TAG+'.queue_attempt.json');REPLY=L/(TAG+'.queue_result.json')
ENVIRONMENT='C08_HG_OPT_H18';DT=.000005;PRESTEP=2000000;END=2060000;FRAMES=31
STEPS=tuple(2000001+2000*part for part in range(30))+(END,)
SIDECARS=('C08OptPlasticHG.csv','C08OptPlasticHGPolicy.json')


def admission(phase,consumed,notify=False):
    path=L/(TAG+'.root_'+phase+'_admission.json');q=short.take(path,consumed)
    m.need(q['authorized'] and q['allowed_stage']==TAG and q['phase']==phase
           and q['execution_script']==m.stat(SCRIPT) and q['note']==m.stat(NOTE)
           and q['template_preparation']==m.stat(full.PREP) and q['template_run']==m.stat(full.RUN)
           and q['source_build']==m.stat(full.BUILD) and q['source_pre_file']==m.stat(full.SOURCE_PRE)
           and q['root_thread_id']==os.environ.get('CODEX_THREAD_ID')==full.THREAD
           and q['single_job_only'] and q['HG_and_cached_material_both_disabled']
           and q['terminal_queue_once']==notify and not q['watcher']
           and not q['automatic_native'] and not q['automatic_next_job'],
           'Exact separate current-root prepare/run admission required')
    short.bound(q['physical_decision'],consumed)
    if phase=='run':
        m.need(q['preparation']==m.stat(PREP) and q['no_parallel_gpu'],
               'Own preparation and no-parallel-GPU admission required')
        if notify:
            m.need(q['codex']==full.CODEX_STAT,'Current root terminal notifier differs')
            short.bound(q['codex'],consumed)
    return q,m.stat(path)


def template(consumed):
    # Existing build/component/prefix receipts are implementation evidence only.
    # Reuse their reviewed narrow helper; no source/object/hash sweep.
    consumed.append(m.stat(Path(full.__file__)))
    b,gate=full.prerequisites(consumed)
    p=short.take(full.PREP,consumed);r=short.take(full.RUN,consumed)
    m.need(p['passed'] and p['prepared_only'] and p['consumed_stats_unchanged']
           and p['group']=='psi2p5' and p['profile']=='full3' and p['program']==b['program']
           and p['source_build']==m.stat(full.BUILD) and p['implementation_prerequisites']==gate
           and p['source_pre_file']==m.stat(full.SOURCE_PRE) and p['fixed_dt_s']==DT
           and p['actual_source_time_s']==9.999999999706008
           and p['global_nsteps_limit']==2600000 and p['expected_saved_frames']==301
           and p['environment_override']=={ENVIRONMENT:'1'}
           and r['passed'] and r['solver_completed'] and r['consumed_stats_unchanged']
           and r['actual_exit']==r['actual_Win32_exit']==0 and r['ownership_failure'] is None
           and r['solver_identity_matches'] and r['program']==p['program']
           and r['preparation']==m.stat(full.PREP) and r['actual_steps']==2600000
           and r['saved_frames']==301,'Completed genuine same-material HG-on full3 template required')
    for key in ('program','source_capture','source_archive','source_pre_file','source_run','source_native',
                'source_native_check','source_material_profile','source_physical_review','source_root_review',
                'input_xml','native_profile','planned_steps'):
        short.bound(p[key],consumed)
    for ref in p['seed']+p['runtime']:short.bound(ref,consumed)
    return p,b,gate


def receiver_xml_bytes(path):
    raw=Path(path).read_bytes();pattern=rb'(<parameter\s+key="TimeMax"\s+value=")13\.0(")'
    hits=list(re.finditer(pattern,raw));m.need(len(hits)==1,'One original TimeMax13.0 attribute required')
    hit=hits[0];replacement=hit[1]+b'10.3'+hit[2]
    changed=raw[:hit.start()]+replacement+raw[hit.end():]
    m.need(changed.count(replacement)==1 and changed.replace(replacement,hit[0],1)==raw,
           'Only TimeMax13.0->10.3 bytes may change; original comments/parameters preserved')
    return changed


def clock_plan(source_time,original_rows):
    keys=['part','completed_step','saved_step','time_s','dt_s']
    m.need(len(original_rows)==301 and list(original_rows[0])==keys,'Original full301 plan required')
    clock=float(source_time);previous=PRESTEP;rows=[];source_clocks=[]
    for part,step in enumerate(STEPS):
        m.need(step>previous,'Nonincreasing actual saved step')
        for _ in range(previous,step):
            before=clock;clock+=DT
        row=dict(part=part,completed_step=step,saved_step=step-1,time_s=clock,dt_s=DT)
        if part<30:
            old=original_rows[part]
            m.need(all(int(old[k])==row[k] for k in keys[:3])
                   and float(old['time_s'])==clock and float(old['dt_s'])==DT,
                   'First30 actual plan records must retain original scalar clocks/steps')
        rows.append(row);source_clocks.append(before);previous=step
    m.need(previous==END and previous-PRESTEP==60000 and len(rows)==FRAMES
           and int(original_rows[30]['completed_step'])==2060001
           and rows[-1]['completed_step']==2060000,'Forced final cap is not original full3 Part30')
    return rows,source_clocks,clock


def prepare():
    m.need(not OUT.exists() and not PLAN.exists() and not PREP.exists(),'Existing preparation/partial protected')
    consumed=[m.stat(SCRIPT),m.stat(NOTE)]
    try:
        ad,adref=admission('prepare',consumed);p,b,gate=template(consumed)
        rows,source_clocks,end=clock_plan(p['actual_source_time_s'],m.table(p['planned_steps']['path']))
        m.verify(consumed);OUT.mkdir();seeds=[]
        for ref in p['seed']:
            destination=OUT/Path(ref['path']).name
            if destination.suffix=='.xml':
                with destination.open('xb') as f:f.write(receiver_xml_bytes(ref['path']))
                seeds.append(m.stat(destination))
            else:seeds.append(host.copy_exact(ref['path'],destination))
        profile=host.copy_exact(p['native_profile']['path'],OUT/'native_profile.csv')
        with PLAN.open('x',encoding='utf-8',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=['part','completed_step','saved_step','time_s','dt_s'])
            writer.writeheader();writer.writerows(rows)
        xml=next(ref for ref in seeds if Path(ref['path']).suffix=='.xml')
        argv=[b['program']['path'],'-gpu:0','-stable','-mdbc_freeslip:1',str(Path(xml['path']).with_suffix('')),
              str(OUT),'-dirdataout','data','-svres','-nsteps:2060000']
        m.verify(consumed)
        m.save(PREP,dict(stage=TAG+'.prepare',passed=True,prepared_only=True,group='psi2p5',profile='window31_hg0',
            program=b['program'],source_build=m.stat(full.BUILD),source_capture=b['source_capture'],source_archive=b['source_archive'],
            implementation_prerequisites=gate,runtime=p['runtime'],source_pre_file=p['source_pre_file'],
            source_run=p['source_run'],source_native=p['source_native'],source_native_check=p['source_native_check'],
            source_material_profile=p['source_material_profile'],source_physical_review=p['source_physical_review'],
            source_root_review=p['source_root_review'],template_preparation=m.stat(full.PREP),template_run=m.stat(full.RUN),
            template_input=p['input_xml'],template_native_profile=p['native_profile'],template_plan=p['planned_steps'],
            input_xml=xml,seed=seeds,native_profile=profile,planned_steps=m.stat(PLAN),planned_rows=rows,
            save_source_clocks_s=source_clocks,actual_source_time_s=p['actual_source_time_s'],planned_actual_end_s=end,
            fixed_dt_s=DT,global_nsteps_limit=END,new_updates=60000,expected_saved_frames=FRAMES,
            environment_remove=[ENVIRONMENT],HG_and_cached_material_both_disabled=True,pure_HG_force_single_factor=False,
            expected_absent_HG_sidecars=list(SIDECARS),DynamicNoPenetrationReactionClosed=False,
            argv=argv,cwd=str(C),output=str(OUT),physical_decision=ad['physical_decision'],root_admission=adref,
            execution_script=m.stat(SCRIPT),note=m.stat(NOTE),consumed=consumed,consumed_stats_unchanged=True,
            exact_inverse_TimeMax_only=True,BI4_Normals_profile_byte_copied=True,first30_plan_records_shared=True,
            forced_final_step_not_full3_shared=True,comparison_descriptive_not_half_or_5Pa=True,
            solver_invocations=0,GenCase_invocations=0,reader_invocations=0,VTK_invocations=0,SHA_scans=0,
            physical_acceptance=False,automatic_native=False,automatic_next_job=False,other_psi_held=True,watcher=False))
    except Exception as error:
        if not PREP.exists():m.save(PREP,dict(stage=TAG+'.prepare',passed=False,first_failure=str(error),consumed=consumed,partial_preserved=True,automatic_retry=False))
        raise


def terminal_once(prep,ad):
    m.need(not QUEUE.exists() and not REPLY.exists(),'Terminal attempt already exists; never resend')
    message=('The single admitted C08 psi2p5 HG/cache-OFF .30s window is terminal: '+str(RUN)
        +'. Read actual owned start/call/run/status/solver_completed, prepare/run admissions and original program/PRE/input31plan. '
        'Only child C08_HG_OPT_H18 is removed, not set0; both HG and cached-material producer revert, not a pureHGforce factor. '
        'Same certified psi2p5 PRE/AS.3n2.55/AV.1/WendlandH1.8/5us/NoPen/keepfalse/CompletedOnly p<=0 remain. '
        '60000new updates/global2060000/31planned saves; actual +=dt clocks and both HG sidecars absence must hold. '
        'Exit0 is pending independently admitted unique native31 and physical review, not acceptance. '
        'Original full301 first30 are cross-operator descriptive samples, not0ULP/half/5Pa truth; final2060000 is notfullPart30=2060001. '
        'Check existing/active readers before any read and retain all22/6805/P0/J/kappa/FS/ledger/plane/clock/signed gates. '
        'Preserve first actual error/partials/last raw console; never reconstruct unsaved state or rerun. '
        'No automatic reader/VTK/PRE/otherpsi/half/nextsolver. One45s queue attempt only, uncertain delivery never resends/rearms/watchers.')
    argv=[str(full.CODEX),'queue','--thread',full.THREAD,'--message',message]
    m.save(QUEUE,dict(stage=TAG,run=m.stat(RUN),status=m.stat(STATUS),thread=full.THREAD,program=ad['codex'],
        arguments=argv,attempts=1,timeout_s=45,only_completion_mechanism='same_direct_run_owner',do_not_resend=True))
    result=dict(stage=TAG,attempts=1,do_not_resend=True)
    try:
        m.need(os.environ.get('CODEX_THREAD_ID')==full.THREAD and ad['codex']==full.CODEX_STAT,'Current notifier binding changed')
        m.bind(ad['codex'])
        call=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        result.update(actual_exit=call.returncode,status='queued' if call.returncode==0 else 'queue_failed',stdout=call.stdout,stderr=call.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    m.save(REPLY,result)


def run(notify=False):
    m.need(all(not q.exists() for q in (RUN,CALL,START,SEAL,STATUS,QUEUE,REPLY,L/(TAG+'.log'))),
           'Existing owner/attempt/completion protected; never retry or rearm')
    consumed=[m.stat(SCRIPT),m.stat(NOTE)];p=None;call=None;ad=None
    result=dict(stage=TAG,passed=False,solver_completed=False,solver_invocations=0,solver_launch_attempts=0,
        candidate_is_numerical_change=True,HG_and_cached_material_both_disabled=True,pure_HG_force_single_factor=False,
        physical_acceptance=False,native_review_pending=True,automatic_native=False,automatic_next_job=False,
        other_psi_held=True,terminal_queue_once=notify,watcher=False,unsaved_state_reconstructed=False,SHA_scans=0)
    try:
        ad,adref=admission('run',consumed,notify);baseline,b,gate=template(consumed);p=short.take(PREP,consumed)
        m.need(p['passed'] and p['prepared_only'] and p['consumed_stats_unchanged'] and p['profile']=='window31_hg0'
               and p['execution_script']==m.stat(SCRIPT) and p['note']==m.stat(NOTE)
               and p['source_build']==m.stat(full.BUILD) and p['program']==b['program']
               and p['implementation_prerequisites']==gate and p['source_pre_file']==baseline['source_pre_file']
               and p['template_preparation']==m.stat(full.PREP) and p['template_run']==m.stat(full.RUN)
               and p['physical_decision']==ad['physical_decision'] and p['global_nsteps_limit']==END
               and p['new_updates']==60000 and p['expected_saved_frames']==FRAMES
               and p['environment_remove']==[ENVIRONMENT] and p['group']=='psi2p5',
               'Exact own bounded preparation and original source/program binding required')
        for key in ('program','source_capture','source_archive','source_pre_file','source_run','source_native',
                    'source_native_check','source_material_profile','source_physical_review','source_root_review',
                    'input_xml','native_profile','planned_steps','template_input','template_native_profile','template_plan','physical_decision'):
            short.bound(p[key],consumed)
        for ref in p['seed']+p['runtime']:short.bound(ref,consumed)
        m.need(OUT.is_dir() and not (OUT/'data').exists() and not (OUT/'Run.out').exists()
               and all(not (OUT/q).exists() for q in SIDECARS)
               and p['argv'][0]==b['program']['path'] and p['argv'][-1]=='-nsteps:2060000',
               'Fresh prepared window and absent HG sidecars required')
        m.need(Path(p['input_xml']['path']).read_bytes()==receiver_xml_bytes(p['template_input']['path'])
               and Path(p['native_profile']['path']).read_bytes()==Path(p['template_native_profile']['path']).read_bytes(),
               'Only TimeMax may differ; material17-key profile must retain exact bytes')
        rows,clocks,end=clock_plan(p['actual_source_time_s'],m.table(p['template_plan']['path']))
        actual=m.table(p['planned_steps']['path'])
        m.need(len(actual)==FRAMES and all(all(int(q[k])==v[k] for k in ('part','completed_step','saved_step'))
               and float(q['time_s'])==v['time_s'] and float(q['dt_s'])==DT for q,v in zip(actual,rows))
               and rows==p['planned_rows'] and clocks==p['save_source_clocks_s'] and end==p['planned_actual_end_s'],
               'All31 original scalar saved clocks and forced cap must hold')
        for proc in psutil.process_iter(['exe','cmdline']):
            try:
                m.need(not(proc.info['exe'] and Path(proc.info['exe']).name.lower().startswith('dualsphysics')
                       and any(q.lower().startswith('-gpu') for q in (proc.info['cmdline'] or [])[1:])),
                       'An actual GPU physical target is active; nothing stopped or changed')
            except psutil.NoSuchProcess:pass
        proc=psutil.Process();owner=dict(pid=proc.pid,created_epoch=proc.create_time(),exe=proc.exe(),argv=proc.cmdline(),parent_pid=proc.ppid())
        env=dict(os.environ)
        for key in list(env):
            if key.upper()==ENVIRONMENT:env.pop(key)
        m.need(not any(k.upper()==ENVIRONMENT for k in env),'Child HG environment must be absent, never0')
        m.verify(consumed)
        m.save(START,dict(stage=TAG+'.start',owner=owner,preparation=m.stat(PREP),root_admission=adref,
            program=p['program'],source_build=p['source_build'],source_capture=p['source_capture'],source_archive=p['source_archive'],
            source_pre_file=p['source_pre_file'],input_xml=p['input_xml'],planned_steps=p['planned_steps'],argv=p['argv'],
            cwd=p['cwd'],environment_remove=[ENVIRONMENT],child_HG_environment_present=False,
            consumed=consumed,automatic_native=False,automatic_next_job=False))
        result.update({key:p[key] for key in ('program','source_build','source_capture','source_archive','implementation_prerequisites',
            'source_pre_file','source_run','source_native','source_native_check','source_material_profile','source_physical_review',
            'source_root_review','template_preparation','template_run','template_input','input_xml','seed','native_profile','planned_steps',
            'actual_source_time_s','planned_actual_end_s','fixed_dt_s','global_nsteps_limit','new_updates','expected_saved_frames',
            'environment_remove','DynamicNoPenetrationReactionClosed','physical_decision')})
        result.update(group='psi2p5',owner=owner,preparation=m.stat(PREP),root_admission=adref,argv=p['argv'],
            output=str(OUT),solver_launch_attempts=1,child_HG_environment_present=False)
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
               and result['ownership_failure'] is None,'Actual owned bounded solver normal exit unproved')
        text=(OUT/'Run.out').read_text(encoding='utf-8-sig')
        m.need('Finished execution (code=0).' in text and '[Simulation INTERRUPTED' not in text
               and 'certified same-material plastic schema/contract2' in text,'Normal original schema2 completion required')
        m.save(SEAL,dict(stage=TAG+'.solver_completed',solver_completed=True,actual_call=m.stat(CALL),original_start=m.stat(START),
            owner=result['owner'],solver_identity=result['solver_identity'],program=p['program'],source_build=p['source_build'],
            source_capture=p['source_capture'],source_archive=p['source_archive'],source_pre_file=p['source_pre_file'],
            input_xml=p['input_xml'],planned_steps=p['planned_steps'],actual_solver_Win32_exit=result['actual_Win32_exit'],
            actual_tool_exit=result['actual_tool_exit'],Run_out=m.stat(OUT/'Run.out'),native_review_pending=True,
            no_solver_retry=True,physical_acceptance=False))
        result.update(solver_completed=True,solver_completion=m.stat(SEAL))
        summary=host.summary(OUT/'Run.csv');parts=sorted((OUT/'data').glob('Part_*.bi4'))
        m.need(int(summary['Steps'])==END and int(summary['PartFiles'])==FRAMES
               and summary['PartsOut']==summary['PartsOutRhop']==summary['PartsOutVel']=='0'
               and [q.name for q in parts]==['Part_%04d.bi4'%i for i in range(FRAMES)],
               'Actual31/global2060000/no-exclusion summary differs')
        m.need(math.isfinite(float(summary['PhysicalTime'])) and abs(float(summary['PhysicalTime'])-p['planned_actual_end_s'])<=.00000051,
               'Rounded summary endpoint differs; exact native clocks remain pending')
        m.need(all(not (OUT/q).exists() for q in SIDECARS),'HG/cache-OFF must produce neither HG sidecar')
        m.need('first_failure' not in result,'Preserve an earlier actual owner failure');m.verify(consumed)
        result.update(passed=True,consumed_stats_unchanged=True,summary=summary,actual_steps=END,saved_frames=FRAMES,
            HG_sidecars_absent=True,Run_out=m.stat(OUT/'Run.out'),Run_csv=m.stat(OUT/'Run.csv'),PARTs=[m.stat(q) for q in parts],
            particle_data_files=[m.stat(q) for q in sorted((OUT/'data').iterdir()) if q.is_file()],Run_csv_endpoint_is_rounded_not_native_clock=True)
    except Exception as error:result.setdefault('first_failure',str(error))
    if (OUT/'Run.out').exists():
        text=(OUT/'Run.out').read_text(encoding='utf-8-sig',errors='replace')
        exception=re.search(r'^(?:Text: |\*\*\* Exception\(exc\): )(.*)$',text,re.M)
        result.update(Run_out=m.stat(OUT/'Run.out'),first_engine_exception_text=exception[1] if exception else None,
            reported_wall_rejection_lines=[line for line in text.splitlines() if line.startswith('DynamicPoreWall rejected:')],
            observed_saved_files=len(list((OUT/'data').glob('Part_*.bi4'))),HG_sidecars_absent=all(not (OUT/q).exists() for q in SIDECARS))
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
        automatic_native=False,automatic_next_job=False,terminal_queue_once=notify,watcher=False,physical_acceptance=False))
    if notify and call is not None and result['solver_launch_attempts']==1:terminal_once(p,ad)
    return 0 if result['passed'] else 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('prepare','run'))
    parser.add_argument('--execution-authorized',action='store_true');parser.add_argument('--notify',action='store_true')
    args=parser.parse_args();m.need(args.execution_authorized,'Separate root prepare/run admission required')
    m.need(args.phase=='run' or not args.notify,'Prepare never notifies or depends on notifier')
    if args.phase=='prepare':prepare()
    else:raise SystemExit(run(args.notify))
