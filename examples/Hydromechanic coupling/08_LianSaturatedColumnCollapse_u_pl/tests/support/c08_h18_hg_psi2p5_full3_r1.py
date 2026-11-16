"""One independently admitted psi2p5 HG full3 direct owner; no reader/next job."""
import argparse
import math
import csv
import xml.etree.ElementTree as ET
import os
import re
import subprocess
from pathlib import Path
import psutil
import c08_h18_wend_matrix_r1 as m
import c08_h18_hg_groups_psi0_prefix4_r1 as short
import c08_h18_hg_opt_full3_r1 as oldowner
import c08_h18_hg_wall_host_jobs_r2 as host

T,C,L=m.T,m.C,m.L
TAG='c08_h18_hg_psi2p5_full3_r1'
SCRIPT=Path(__file__).resolve();NOTE=T/'notes'/(TAG+'.md')
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8'
OUT=T/'outputs'/TAG;PLAN=T/'configs'/(TAG+'.steps.csv')
PREP=L/(TAG+'.prepare.json');RUN=L/(TAG+'.run.json');START=L/(TAG+'.start.json')
CALL=L/(TAG+'.call.json');SEAL=L/(TAG+'.solver_completed.json');STATUS=L/(TAG+'.status.json')
QUEUE=L/(TAG+'.queue_attempt.json');REPLY=L/(TAG+'.queue_result.json')
BUILD=short.BUILD;BUILD_REVIEW=short.BUILD_REVIEW;MATERIAL_CHECK=short.MATERIAL_CHECK
SOURCE_TAG='c08_h18_wend_branches_psi2p5_pre_r1';SOURCE_RUN=L/(SOURCE_TAG+'.run.json')
SOURCE_PRE=T/'outputs'/SOURCE_TAG/'data/Part_1000.bi4'
SOURCE_NATIVE=T/'outputs'/SOURCE_TAG/'native_r2/completion.json'
SOURCE_NATIVE_CHECK=L/'c08_h18_wend_psi2p5_native_r2.check.json'
CONTROL='c08_h18_as03n255_full3_r1'
CRUN=L/(CONTROL+'.run.json');CPREP=L/(CONTROL+'.prepare.json')
CODEX=oldowner.CODEX;CODEX_STAT=oldowner.CODEX_STAT
ENVIRONMENT='C08_HG_OPT_H18'
DT=.000005;PRESTEP=2000000;END=2600000;FRAMES=301
JOB=dict(steps=tuple(2000001+2000*part for part in range(300))+(END,),updates=600000,frames=FRAMES)


def admission(phase,consumed):
    path=L/(TAG+'.root_'+phase+'_admission.json');q=short.take(path,consumed)
    m.need(q['authorized'] and q['allowed_stage']==TAG and q['phase']==phase
           and q['execution_script']==m.stat(SCRIPT) and q['note']==m.stat(NOTE)
           and q['source_build']==m.stat(BUILD) and q['build_review']==m.stat(BUILD_REVIEW)
           and q['material_probe']==m.stat(MATERIAL_CHECK) and q['new_prefix4_review']==m.stat(short.REVIEW)
            and q['group']=='psi2p5' and q['source_run']==m.stat(SOURCE_RUN)
            and q['source_pre_file']==m.stat(SOURCE_PRE) and q['source_native_check']==m.stat(SOURCE_NATIVE_CHECK)
            and q['source_native_completion']==m.stat(SOURCE_NATIVE)
           and q['root_thread_id']==os.environ.get('CODEX_THREAD_ID')==THREAD
           and q['single_full3_only'] and q['terminal_queue_once'] and not q['watcher']
           and not q['automatic_native'] and not q['automatic_next_job'] and q['codex']==CODEX_STAT,
           'Separate exact current-root prepare/run and one terminal queue admission required')
    if phase=='run':m.need(q['preparation']==m.stat(PREP),'Prepared full3 binding differs')
    for key in ('codex','physical_decision','source_physical_review','source_root_review'):short.bound(q[key],consumed)
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
           and q['consumed_stats_unchanged'] and not q['candidate_is_numerical_change']
           and q['material_guard_only'] and not q['output_only']
           and q['all22_native_four_records_byte_equal'] and q['clock_layout_signed_rows_byte_equal']
           and q['HG_eight60column_rows_byte_equal'] and q['policy_equal'] and q['plastic_saved_stage_present']
           and q['all_original_native_guards'] and q['normal_short_no_fault_capture'],
           'The groups host guard must pass the actual psi0 plastic prefix4 implementation regression first')
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
        groups_psi0_implementation_review_passed=True,new_group_prefix_equivalence_not_claimed=True)


def source_and_template(ad,consumed):
    r=short.take(SOURCE_RUN,consumed);n=short.take(SOURCE_NATIVE_CHECK,consumed)
    done=short.take(SOURCE_NATIVE,consumed)
    expected=dict(coh=5000.,dlt=2.5,DilationDecay=.2,phi=25.,phi_r=25.,n_phi=0.,
                  coh_r=1000.,n_coh=5.,ModulusE=20e6,PRvs=.33)
    m.need(r['passed'] and r['solver_completed'] and r['postprocess_completed']
           and r['actual_exit']==r['actual_Win32_exit']==0 and r['consumed_stats_unchanged']
           and r['group']=='psi2p5' and r['material']==expected and r['kernel']==2
           and not r['elastic_source'] and not r['keep_bed_overlap']
           and r['actual_steps']==PRESTEP and r['saved_frames']==1001
           and r['source_pre_file']==m.stat(SOURCE_PRE),'Genuine new same-material psi2p5 source required')
    call=short.take(short.bound(r['actual_call'],consumed),consumed)
    m.need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==call['actual_solver_Win32_exit']==0
           and not call['ownership_errors'],'Actual source owner/solver exits failed')
    m.need(n['passed'] and n['reader_invocations']==1 and n['consumed_stats_unchanged']
           and n['source_run']==m.stat(SOURCE_RUN) and n['completion']==m.stat(SOURCE_NATIVE),
           'The one genuine native_r2 source read is required; r1 was not a physical read')
    short.good_call(short.bound(n['call'],consumed),consumed)
    m.need(done['passed'] and done['certified_PRE'] and done['same_material_plastic_PRE']
           and done['source_group_certificate_checked'] and done['source_yield_uses_actual_kappa']
           and done['expected_handoff_schema']==2 and done['group']=='psi2p5'
           and done['samples']==1001 and done['completed_steps']==PRESTEP and done['typed_arrays']==22
           and done['native_IDs']==7060 and done['soil_IDs']==5000 and done['fixed_IDs']==2060
           and done['release_target_ID_begin']==1805 and done['release_target_ID_count']==255
           and not done['keep_bed_overlap'] and done['declared_Kernel_XML_CSV']==2
           and done['actual_end_s']==9.9999999997060076 and done['max_scalar_clock_error_s']<=1e-14
           and not done['native_rewritten'],'Original new-group source native guards/contract must pass')
    for key in ('program','source_build','source_capture','source_archive','input_xml','source_pre_file','source_head'):
        short.bound(r[key],consumed)
    short.bound(n['material_csv'],consumed)
    physical=short.take(ad['source_physical_review']['path'],consumed)
    root=short.take(ad['source_root_review']['path'],consumed)
    m.need(physical['analysis_complete'] and physical['source_native_qualified']
           and physical['consumed_stats_unchanged'] and physical['group']=='psi2p5'
           and physical['source_run']==m.stat(SOURCE_RUN)
           and physical['source_native_check']==m.stat(SOURCE_NATIVE_CHECK)
           and physical['source_native_completion']==m.stat(SOURCE_NATIVE),
           'Completed source physical analysis required, not exact equilibrium')
    expected_refs=dict(source_run=m.stat(SOURCE_RUN),source_native_check=m.stat(SOURCE_NATIVE_CHECK),
                       source_native_completion=m.stat(SOURCE_NATIVE),source_physical_review=ad['source_physical_review'],
                       source_pre_file=m.stat(SOURCE_PRE))
    m.need(root['accepted_for_bounded_release_comparison'] and
           all(root[key]==value for key,value in expected_refs.items()),
           'Independent root acceptance of this source for bounded release comparison required')
    old=short.take(CRUN,consumed);prep=short.take(CPREP,consumed)
    m.need(old['passed'] and old['solver_completed'] and old['consumed_stats_unchanged']
           and old['actual_exit']==old['actual_Win32_exit']==old['actual_tool_exit']==0
           and old['actual_steps']==END and old['saved_frames']==FRAMES and old['group']=='psi0'
           and old['AS_coefficient']==.3 and old['AS_exponent']==2.55 and old['Kernel']==2
           and prep['prepared_only'] and prep['exact_inverse_original_XML_bytes']
           and prep['consumed_stats_unchanged'] and len(old['seed'])==3,
           'Retained complete original AS03n255 full3 generated template required; not a new spatial reference')
    for key in ('input_xml','planned_steps','native_profile'):short.bound(old[key],consumed)
    for ref in old['seed']:short.bound(ref,consumed)
    return r,n,done,old


def receiver_xml_bytes(oldxml):
    raw=Path(oldxml).read_bytes();changes=[]
    for pattern,value in ((rb'(<dlt\s+value=")0(")',b'2.5'),
                          (rb'(<DilationDecay\s+value=")0(")',b'0.2'),
                          (rb'(<gravitypreload\b[^>]*\bstatefile=")[^"]*(")',
                           str(SOURCE_PRE.resolve()).encode('utf-8'))):
        matches=list(re.finditer(pattern,raw));m.need(len(matches)==1,'One exact original receiver attribute required')
        hit=matches[0];replacement=hit[1]+value+hit[2]
        changes.append((replacement,hit[0]));raw=raw[:hit.start()]+replacement+raw[hit.end():]
    inverse=raw
    for changed,original in reversed(changes):
        m.need(inverse.count(changed)==1,'Unique inverse receiver patch required');inverse=inverse.replace(changed,original,1)
    m.need(inverse==Path(oldxml).read_bytes(),'Only dlt/decay/statefile receiver bytes may change')
    return raw


def check_receiver(path,oldxml):
    actual=ET.parse(path).getroot();expected=ET.fromstring(receiver_xml_bytes(oldxml))
    m.need(m.signature(actual)==m.signature(expected),'Only the three declared receiver attributes may differ')
    soil=actual.find('execution/special/soils')
    for key,value in dict(coh=5000,dlt=2.5,DilationDecay=.2,phi=25,phi_r=25,n_phi=0,coh_r=1000,n_coh=5).items():
        nodes=soil.findall(key);m.need(len(nodes)==1 and float(nodes[0].get('value'))==value,'Actual receiver material differs: '+key)
    g=actual.find('execution/special/gravitypreload')
    m.need(Path(g.get('statefile')).samefile(SOURCE_PRE) and g.get('elastic_source')==g.get('keep_bed_overlap')=='false',
           'Actual receiver source/phase flags differ')


def prepare():
    m.need(not OUT.exists() and not PLAN.exists() and not PREP.exists(),'Existing full3 preparation/partial protected')
    consumed=[m.stat(SCRIPT),m.stat(NOTE)]
    try:
        ad,adref=admission('prepare',consumed);b,gate=prerequisites(consumed)
        source_run,source_check,source,old=source_and_template(ad,consumed)
        rows=m.table(old['planned_steps']['path'])
        replay,source_clocks,end=oldowner.clock_plan(JOB,source['actual_end_s'],rows)
        m.need(end==12.999999999592434 and len(rows)==301
               and len(m.table(old['native_profile']['path']))==17,'Original full301/17-key input extent required')
        m.verify(consumed);OUT.mkdir();seeds=[]
        for ref in old['seed']:
            destination=OUT/Path(ref['path']).name
            if destination.suffix=='.xml':
                with destination.open('xb') as f:f.write(receiver_xml_bytes(ref['path']))
                check_receiver(destination,ref['path']);seeds.append(m.stat(destination))
            else:seeds.append(host.copy_exact(ref['path'],destination))
        profile=OUT/'native_profile.csv'
        profile_rows=m.table(old['native_profile']['path'])
        values={q['key']:q['value'] for q in profile_rows}
        m.need(len(profile_rows)==len(values)==17 and values['group']=='psi0'
               and values['dlt']=='0' and values['DilationDecay']=='0','Original exact psi0 receiver profile required')
        values.update(group='psi2p5',dlt='2.5',DilationDecay='0.2')
        material=source_check['material_values']
        m.need(len(material)==15 and set(values)==set(material)|{'ArtificialStressCoef','ArtificialStressExp'}
               and all(values[key]==value if key=='group' else m.f32(values[key])==m.f32(value)
                       for key,value in material.items()),'All fifteen certified source material values must match receiver')
        with profile.open('x',encoding='utf-8',newline='') as f:
            writer=csv.writer(f);writer.writerow(('key','value'))
            writer.writerows((q['key'],values[q['key']]) for q in profile_rows)
        plan=host.copy_exact(old['planned_steps']['path'],PLAN)
        xml=next(ref for ref in seeds if Path(ref['path']).suffix=='.xml');seed=Path(xml['path']).with_suffix('')
        argv=[b['program']['path'],'-gpu:0','-stable','-mdbc_freeslip:1',str(seed),str(OUT),'-dirdataout','data','-svres','-nsteps:2600000']
        m.verify(consumed)
        m.save(PREP,dict(stage=TAG+'.prepare',passed=True,prepared_only=True,group='psi2p5',profile='full3',configuration='Release',
            program=b['program'],source_build=m.stat(BUILD),source_capture=b['source_capture'],source_archive=b['source_archive'],
            root_build_review=m.stat(BUILD_REVIEW),material_probe=m.stat(MATERIAL_CHECK),implementation_prerequisites=gate,
            material_guard_only=True,output_only=False,retained_objects=113,actual_link_objects=114,
            private_HG_Node_material_recompiled=False,host_fault_capture_retained=True,original_guards_unchanged=True,
            source_pre_file=m.stat(SOURCE_PRE),source_run=m.stat(SOURCE_RUN),source_native=m.stat(SOURCE_NATIVE),
            source_native_check=m.stat(SOURCE_NATIVE_CHECK),source_material_profile=source_check['material_csv'],
            source_physical_review=ad['source_physical_review'],source_root_review=ad['source_root_review'],
            template_run=m.stat(CRUN),template_preparation=m.stat(CPREP),template_input=old['input_xml'],
            template_is_psi0_geometry_schedule_not_same_material_truth=True,input_xml=xml,seed=seeds,native_profile=m.stat(profile),
            planned_steps=plan,planned_rows=replay,save_source_clocks_s=source_clocks,runtime=b['runtime'],
            actual_source_time_s=source['actual_end_s'],planned_actual_end_s=end,fixed_dt_s=DT,
            global_nsteps_limit=END,new_updates=600000,expected_saved_frames=FRAMES,
            HG_history_cold_zero=True,DynamicNoPenetrationReactionClosed=False,
            environment_override={ENVIRONMENT:'1'},argv=argv,cwd=str(C),output=str(OUT),
            codex=ad['codex'],physical_decision=ad['physical_decision'],root_admission=adref,
            execution_script=m.stat(SCRIPT),note=m.stat(NOTE),consumed=consumed,consumed_stats_unchanged=True,
            exact_inverse_three_XML_attributes=True,GenCase_BI4_Normals_byte_copied=True,original301_plan_unchanged=True,
            PRE_adopted_original_absolute_path=True,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,VTK_invocations=0,SHA_scans=0,
            physical_acceptance=False,automatic_native=False,automatic_next_job=False,other_psi_held=True,
            terminal_queue_once=True,watcher=False))
    except Exception as error:
        if not PREP.exists():m.save(PREP,dict(stage=TAG+'.prepare',passed=False,first_failure=str(error),consumed=consumed,partial_preserved=True,automatic_retry=False))
        raise


def terminal_once(prep):
    m.need(not QUEUE.exists() and not REPLY.exists(),'Terminal attempt already exists; never resend')
    message=('The single admitted C08 psi2p5 energy-normalized HG full3 GPU diagnostic is terminal: '+str(RUN)
        +'. Read original owned start/call/run/status/solver_completed and prepare/run admissions, actual Win32/Popen exits, '
        'groups-program/source/input/full301 scalar plan and the new same-material psi2p5 PRE native_r2/root physical review. '
        'PRE is genuine coh5000/dlt2.5deg/decay.2 schema2/law2 with actual kappa/J/p/stress retained, never the old psi0 PRE. '
        'AS.3/n2.55/AV.1/WendlandH1.8/fixed5us/keepfalse/fixed-plane/CompletedOnly/HGxi.1 remain; '
        '600000new updates/global2600000/301planned saves, source adopted with coldzero HG, ReactionClosed=false. '
        'CPU21 and the actual psi0 groups-program prefix4 implementation regression passed first; they are not psi2p5 physics acceptance. '
        'Exit0/normal summary remains pending independently admitted unique native formal psi2p5 and physical/paper/HG review. '
        'Check existing/active readers before any read; retain all22/6805/P0/J/kappa/FS/ledger/plane/actualclock/signed gates. '
        'The original psi0 is a cross-material descriptive comparison, not an exact prefix/half truth or a5Pa equivalence gate. '
        'Preserve actual first error, handles/exits, partials and last original console PART; never reconstruct unsaved arrays/time. '
        'Host fault capture is actual substage inputs, not rejected fit registers or a saved native state. '
        'A completed solver plus derived failure requires offline repair only, never a solver rerun. '
        'No automatic reader/VTK/otherpsi/half/PRE/nextsolver. This directowner queues once45s; '
        'uncertain delivery is never resent/rearmed and no watcher or connectivity self-test follows.')
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
        candidate_is_numerical_change=True,material_group_change=True,output_only=False,physical_acceptance=False,
        native_review_pending=True,HG_sidecar_review_pending=True,automatic_native=False,automatic_next_job=False,
        other_psi_held=True,terminal_queue_once=True,watcher=False,unsaved_state_reconstructed=False,SHA_scans=0)
    try:
        ad,adref=admission('run',consumed);b,gate=prerequisites(consumed)
        source_and_template(ad,consumed);p=short.take(PREP,consumed)
        m.need(p['passed'] and p['prepared_only'] and p['consumed_stats_unchanged'] and p['profile']=='full3'
               and p['execution_script']==m.stat(SCRIPT) and p['note']==m.stat(NOTE)
               and p['source_build']==m.stat(BUILD) and p['program']==b['program']
               and p['implementation_prerequisites']==gate and p['codex']==ad['codex']
               and p['physical_decision']==ad['physical_decision'] and p['global_nsteps_limit']==END
               and p['new_updates']==600000 and p['expected_saved_frames']==FRAMES
               and p['environment_override']=={ENVIRONMENT:'1'} and p['group']=='psi2p5'
               and p['source_pre_file']==m.stat(SOURCE_PRE) and p['source_native']==m.stat(SOURCE_NATIVE)
               and p['source_native_check']==m.stat(SOURCE_NATIVE_CHECK)
               and p['source_physical_review']==ad['source_physical_review'] and p['source_root_review']==ad['source_root_review'],
               'Exact own psi2p5 preparation, source acceptance and groups implementation gates required')
        for key in ('program','source_capture','source_archive','source_pre_file','source_run','source_native',
                    'source_native_check','source_material_profile','source_physical_review','source_root_review',
                    'input_xml','native_profile','planned_steps','template_input','codex','physical_decision'):
            short.bound(p[key],consumed)
        for ref in p['seed']+p['runtime']:short.bound(ref,consumed)
        m.need(OUT.is_dir() and not (OUT/'data').exists() and not (OUT/'Run.out').exists()
               and p['argv'][0]==b['program']['path'] and p['argv'][-1]=='-nsteps:2600000',
               'Fresh exact prepared full3 output and global cap required')
        check_receiver(p['input_xml']['path'],p['template_input']['path'])
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
        m.save(START,dict(stage=TAG+'.start',owner=owner,preparation=m.stat(PREP),root_admission=adref,
            program=p['program'],source_build=p['source_build'],source_capture=p['source_capture'],source_archive=p['source_archive'],
            source_pre_file=p['source_pre_file'],input_xml=p['input_xml'],planned_steps=p['planned_steps'],argv=p['argv'],
            cwd=p['cwd'],environment_override=p['environment_override'],consumed=consumed,automatic_native=False,automatic_next_job=False))
        result.update({key:p[key] for key in ('program','source_build','source_capture','source_archive','material_probe',
            'implementation_prerequisites','source_pre_file','source_run','source_native','source_native_check',
            'source_material_profile','source_physical_review','source_root_review','template_run','template_preparation','template_input',
            'input_xml','seed','native_profile','planned_steps','actual_source_time_s','planned_actual_end_s','fixed_dt_s',
            'global_nsteps_limit','new_updates','expected_saved_frames','environment_override','HG_history_cold_zero',
            'DynamicNoPenetrationReactionClosed','codex','physical_decision')})
        result.update(group='psi2p5',owner=owner,preparation=m.stat(PREP),root_admission=adref,argv=p['argv'],output=str(OUT),solver_launch_attempts=1)
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

