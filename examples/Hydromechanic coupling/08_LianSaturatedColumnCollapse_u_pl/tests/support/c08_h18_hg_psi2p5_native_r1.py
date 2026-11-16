"""One separately admitted existing AS255 formal psi2p5 read; no solver or analysis."""
import argparse
import csv
import math
import ntpath
import os
import struct
from pathlib import Path
import psutil
import c08_h18_hg_psi2p5_full3_r1 as full

m,short,T,C,L=full.m,full.short,full.T,full.C,full.L
TAG='c08_h18_hg_psi2p5_native_r1'
SCRIPT=Path(__file__).resolve();NOTE=T/'notes'/(TAG+'.md')
ADMISSION=L/(TAG+'.root_admission.json');CHECK=L/(TAG+'.check.json')
CALL=L/(TAG+'.call.json');LOG=L/(TAG+'.log')
TERMINAL=L/(full.TAG+'.terminal_review_r1.json')
READER_BUILD=L/'c08_h18_as255_native_r1.build.json'
OUT=full.OUT/'native_r1'
LEAVES=('completion.json','bedkeep_metadata.json','typed22.bin','typed22_layout.csv',
        'clocks.csv','history.csv','plane_gaps.csv')


def take(path,consumed):return short.take(path,consumed)


def bound(ref,consumed):return short.bound(ref,consumed)


def lexical(path):
    # Never resolve arbitrary foreign argv (e.g. Chrome named pipes) on the filesystem.
    return ntpath.normcase(ntpath.abspath(os.fspath(path)))


def no_active_reader(program):
    target=lexical(program);data=lexical(full.OUT/'data');output=lexical(OUT)
    for proc in psutil.process_iter(['pid','exe','cmdline']):
        try:
            exe=proc.info['exe'];args=proc.info['cmdline'] or []
            same_program=bool(exe and lexical(exe)==target)
            reader_like=bool(exe and any(k in ntpath.basename(exe).lower() for k in ('native','reader')))
            consumes_same=reader_like and any(lexical(q) in (data,output) for q in args[1:])
            m.need(not(same_program or consumes_same),'An existing reader is active; no duplicate read or process change')
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass


def context(consumed):
    ad=take(ADMISSION,consumed);r=take(full.RUN,consumed);p=take(full.PREP,consumed)
    start=take(full.START,consumed);call=take(full.CALL,consumed);seal=take(full.SEAL,consumed)
    terminal=take(TERMINAL,consumed)
    refs=dict(run=m.stat(full.RUN),start=m.stat(full.START),actual_call=m.stat(full.CALL),
              solver_completion=m.stat(full.SEAL),preparation=m.stat(full.PREP),program=r['program'])
    m.need(ad['authorized'] and ad['allowed_stage']==TAG and ad['execution_script']==m.stat(SCRIPT)
           and ad['note']==m.stat(NOTE) and ad['terminal_review']==m.stat(TERMINAL)
           and ad['reader_build']==m.stat(READER_BUILD) and ad['group']=='psi2p5'
           and ad['samples']==301 and ad['completed_steps']==2600000
           and ad['root_thread_id']==os.environ.get('CODEX_THREAD_ID')==full.THREAD
           and not ad['automatic_next_job'] and not ad['automatic_analysis'] and not ad['automatic_VTK']
           and not ad['solver_authorized'],'Separate current-root one-read admission required')
    m.need(all(ad[key]==value for key,value in refs.items()),'Root native admission consumed stage binding differs')
    m.need(terminal['passed'] and all(terminal[key]==value for key,value in refs.items())
           and terminal['solver_identity_verified'] and terminal['actual_owned_exits_zero']
           and terminal['no_owned_survivors'] and terminal['saved_frames']==301
           and terminal['global_steps']==2600000 and terminal['native_review_pending'],
           'Independent root terminal/ownership review required')
    m.need(r['passed'] and r['solver_completed'] and r['consumed_stats_unchanged']
           and r['actual_exit']==r['actual_Win32_exit']==r['actual_tool_exit']==r['actual_tool_Win32_exit']==0
           and r['ownership_failure'] is None and r['solver_identity_matches']
           and r['group']=='psi2p5' and r['new_updates']==600000 and r['actual_steps']==2600000
           and r['saved_frames']==301 and r['program']==p['program'] and r['preparation']==m.stat(full.PREP),
           'One genuine completed full301 psi2p5 solver required; never rerun it')
    child=call['child']
    m.need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None
           and child==r['solver_identity'] and child['creation_filetime_100ns']>0
           and Path(child['exe']).resolve()==Path(r['program']['path']).resolve()
           and child['argv']==r['argv']==start['argv'] and child['parent_pid']==r['owner']['pid']
           and start['owner']==r['owner'] and call['owner']['pid']==r['owner']['pid']
           and abs(call['owner']['created_epoch']-r['owner']['created_epoch'])<=5e-6
           and seal['actual_call']==m.stat(full.CALL) and seal['original_start']==m.stat(full.START)
           and seal['solver_identity']==child and seal['actual_solver_Win32_exit']==seal['actual_tool_exit']==0,
           'Actual direct child creation/exe/argv/parent/handle exits do not close')
    runad=take(bound(r['root_admission'],consumed),consumed)
    prepad=take(bound(p['root_admission'],consumed),consumed)
    m.need(runad['authorized'] and runad['phase']=='run' and prepad['authorized'] and prepad['phase']=='prepare'
           and runad['allowed_stage']==prepad['allowed_stage']==full.TAG
           and runad['preparation']==m.stat(full.PREP) and start['root_admission']==r['root_admission']
           and p['execution_script']==runad['execution_script']==prepad['execution_script']==m.stat(full.SCRIPT),
           'Actual separate prepare/run admissions differ')
    build,implementation=full.prerequisites(consumed)
    full.source_and_template(runad,consumed)
    m.need(r['program']==build['program'] and r['source_build']==m.stat(full.BUILD)
           and r['implementation_prerequisites']==implementation
           and p['source_pre_file']==r['source_pre_file']==m.stat(full.SOURCE_PRE)
           and r['source_native']==m.stat(full.SOURCE_NATIVE)
           and r['source_native_check']==m.stat(full.SOURCE_NATIVE_CHECK),'Implementation/new-source binding differs')
    for key in ('program','source_build','source_capture','source_archive','input_xml','native_profile','planned_steps',
                'source_pre_file','source_run','source_native','source_native_check','source_material_profile',
                'source_physical_review','source_root_review','physical_decision','Run_out','Run_csv'):
        bound(r[key],consumed)
    for ref in r['seed']+r['PARTs']:bound(ref,consumed)
    m.need(len(r['PARTs'])==301,'Exactly301 original input PART stats required')
    full.check_receiver(r['input_xml']['path'],r['template_input']['path'])
    profile=m.table(r['native_profile']['path']);values={q['key']:q['value'] for q in profile}
    expected=dict(Kernel=2,ModulusE=20e6,PRvs=.33,DPCtes=3,phi=25,phi_r=25,n_phi=0,coh=5000,
                  coh_r=1000,n_coh=5,dlt=2.5,DilationDecay=.2,SoilTriggerFos=1.65,fresh_trigger_active=0,
                  ArtificialStressCoef=.3,ArtificialStressExp=2.55)
    m.need(len(profile)==len(values)==17 and values.get('group')=='psi2p5'
           and set(values)==set(expected)|{'group'} and
           all(m.f32(values[key])==m.f32(value) for key,value in expected.items()),'Actual seventeen-key receiver profile differs')
    b=take(READER_BUILD,consumed)
    m.need(b['passed'] and b['consumed_stats_unchanged'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0
           and b['formal_samples']==301 and b['receiver_material_CSV_keys']==17
           and b['source_material_CSV_keys']==15 and b['explicit_AS_exponent']==2.55
           and b['allowed_AS_coefficients']==[.3,.5,.7] and not b['original_field_and_numerical_guards_changed'],
           'Passed unchanged original AS255 full reader required; no reader build or physics change')
    program=bound(b['program'],consumed)
    for ref in b['calls']:short.good_call(bound(ref,consumed),consumed)
    for key in ('source','core_derivation','core_diff'):bound(b[key],consumed)
    argv=[str(program),'--receiver','formal','psi2p5',str(full.OUT/'data'),r['source_pre_file']['path'],
          r['planned_steps']['path'],r['native_profile']['path'],str(OUT)]
    no_active_reader(program);m.verify(consumed)
    return ad,r,b,argv


def completion_checks():
    done=m.read(OUT/'completion.json');meta=m.read(OUT/'bedkeep_metadata.json')
    m.need(done['passed'] and done['group']=='psi2p5' and done['samples']==301 and done['completed_steps']==2600000
           and done['new_updates']==600000 and done['actual_end_s']==done['scalar_replay_end_s']==12.999999999592434
           and done['source_actual_time_s']==9.9999999997060076 and done['source_handoff_schema']==2
           and done['source_material_law_version']==done['target_material_law_version']==2
           and done['same_material_plastic_PRE'] and not done['source_elastic'] and done['typed_arrays']==22
           and done['actual_native_IDs_per_frame']==6805 and done['soil_IDs']==5000 and done['actual_fixed_IDs']==1805
           and done['ledger_checks']==done['rho_cache_bits_checks']==done['kappa_nondecreasing_from_PRE_checks']==1505000
           and done['fixed_marker_checks']==543305 and done['P0_bits_checks']==2048305
           and done['FS23_pressure_checks']>0 and done['nonempty_signed_intervals']==301
           and done['max_scalar_clock_error_s']<=1e-14 and done['max_signed_dterror_s']<=1e-14
           and done['max_ledger_relative_error']<=5e-13 and not done['native_rewritten']
           and done['NoPenOn_argument'] and done['DynamicNoPenetrationActive']
           and done['DynamicNoPenetrationPolicy']=='FixedPlaneStageProjectionReleaseOnly'
           and not done['DynamicNoPenetrationReactionClosed'] and done['plane_gap_checks']==3010000,
           'All original full301 field/ID/clock/signed/ledger/P0/history/FS/plane guards must pass')
    m.need(meta['passed'] and meta['profile']=='formal' and meta['group']=='psi2p5'
           and meta['samples']==301 and meta['completed_steps']==2600000
           and meta['receiver_material_CSV_keys']==17 and meta['expected_source_handoff_schema']==2
           and meta['first_post_completed_step']==2000001 and not meta['keep_bed_overlap']
           and meta['actual_retired_count']==255 and meta['AS_policy']=='ReleaseOnly'
           and m.f32(meta['AS_coefficient_float_reference'])==m.f32(.3)
           and m.f32(meta['AS_exponent_float_reference'])==m.f32(2.55)
           and meta['AS_active_true_headers']==301 and meta['expected_ponding_policy']=='CompletedOnly'
           and meta['ponding_policy_keys_absent_headers']==301 and meta['core_array_decode_passes']==1,
           'Original typed AS/source/profile metadata differs')
    m.need({q.name for q in OUT.iterdir()}==set(LEAVES),'Missing/extra native derived exports')
    with (OUT/'typed22.bin').open('rb') as f:header=struct.unpack('<III',f.read(12))
    m.need(header==(6805,22,301) and (OUT/'typed22.bin').stat().st_size==434243080,
           'Original typed22 header/full301 extent differs')
    layout=m.table(OUT/'typed22_layout.csv');rows=m.table(OUT/'clocks.csv')
    plan=m.table(full.PLAN)
    m.need(len(layout)==22 and len(rows)==len(plan)==301,'Full layout/clock extent differs')
    for row,expected in zip(rows,plan):
        error=float(row['signed_dterror_s'])
        m.need(int(row['part'])==int(expected['part']) and int(row['completed_step'])==int(expected['completed_step'])
               and int(row['saved_step'])==int(expected['saved_step']) and float(row['dt_s'])==.000005
               and abs(float(row['time_s'])-float(expected['time_s']))<=1e-14
               and math.isfinite(error) and error<=1e-14 and row['dterror_interval_empty']=='0'
               and row['native_IDs']=='6805' and row['phase']=='1','Exported original signed/actual clock row differs')
    return done,meta


def main():
    m.need(not any(q.exists() for q in (CHECK,CALL,LOG,OUT)),'Existing reader attempt/partial/completion protected; never decode twice')
    consumed=[m.stat(SCRIPT),m.stat(NOTE),m.stat(full.SCRIPT),m.stat(short.SCRIPT)]
    result=dict(stage=TAG,passed=False,original_safety_passed=False,reader_invocations=0,reader_launch_attempts=0,
                solver_invocations=0,build_invocations=0,VTK_invocations=0,SHA_scans=0,
                physical_acceptance=False,HG_sidecar_review_pending=True,automatic_analysis=False,automatic_next_job=False)
    try:
        ad,r,b,argv=context(consumed);result.update(root_admission=m.stat(ADMISSION),run=m.stat(full.RUN),
            source_run=r['source_run'],terminal_review=m.stat(TERMINAL),reader_build=m.stat(READER_BUILD),
            program=b['program'],argv=argv,reader_launch_attempts=1)
        entry=m.invoke(TAG,argv,C);result['actual_call']=entry;result['reader_invocations']=1
        call=short.good_call(bound(entry,consumed),consumed)
        m.need(call['child']['argv']==argv and Path(call['child']['exe']).resolve()==Path(b['program']['path']).resolve()
               and call['child']['parent_pid']==call['owner']['pid'],'Actual unique reader exe/argv/parent differs')
        done,meta=completion_checks()
        outputs=[m.stat(OUT/leaf) for leaf in LEAVES];m.verify(consumed)
        result.update(passed=True,original_safety_passed=True,reader_invocations=1,native_completion=m.stat(OUT/'completion.json'),
            metadata=m.stat(OUT/'bedkeep_metadata.json'),outputs=outputs,typed_header=[6805,22,301],
            group='psi2p5',samples=301,actual_native_IDs_per_frame=6805,source_material_is_actual_new_PRE=True,
            current_safe_completion_is_not_physical_acceptance=True,consumed_stats_unchanged=True)
    except Exception as error:
        result['first_failure']=str(error)
        if CALL.exists():
            result['actual_call']=m.stat(CALL);call=m.read(CALL)
            result.update(reader_invocations=1 if call.get('child') else None,
                actual_Popen_wait_exit=call.get('actual_Popen_wait_exit'),actual_Win32_exit=call.get('actual_Win32_exit'),
                ownership_failure=call.get('ownership_failure'))
        elif result['reader_launch_attempts']:result.update(reader_invocations=None,launch_outcome_not_handle_proven=True)
        result['partial_outputs_preserved']=OUT.exists()
    result['consumed']=consumed;m.save(CHECK,result)
    m.need(result['passed'],result.get('first_failure','Native failed; preserve data and diagnose offline only'))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    m.need(args.execution_authorized,'Separate root full-read and one unique native admission required')
    main()

