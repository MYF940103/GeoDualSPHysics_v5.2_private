"""Offline AS.7 failed34 saved-prefix review; no solver or unsaved-stage replay."""
import argparse,json,re,struct,xml.etree.ElementTree as ET
from pathlib import Path
import c08_h18_wend_partial_review_r1 as previous

receiver,source,old=previous.receiver,previous.source,previous.old
T,need,path,stat,read,table,bind=old.T,old.need,old.path,old.stat,old.read,old.table,old.bind
np=old.np;same=previous.same
TAG='c08_h18_wend_partial_review_r2'
RUN='c08_h18_wend_psi0_a07_w09_r1'
BUILD=T/'logs/c08_h18_wend_partial_native_r2.build.json'
COUNT=34


def load_partial(spec,src,src_spec,consumed):
    for key in ('tag','native_dir','native_call','material_csv','plan','run','input_xml','actualAS'):
        need(key in spec,'Explicit failed34 case key missing: '+key)
    need(spec['tag']==RUN and old.f32(spec['actualAS']['coefficient'])==old.f32(.7) and old.f32(spec['actualAS']['exponent'])==old.f32(3.825),'Only the actual AS.7/n3.825 failed34 receiver is supported')
    root=path(spec['native_dir']);d=read(root/'completion.json');meta=read(root/'bedkeep_metadata.json')
    build=read(BUILD);call=read(spec['native_call']);run=read(spec['run']);source_run=read(src_spec['run'])
    plan=table(spec['plan'])
    need(len(plan)==91 and set(plan[0])=={'part','completed_step','saved_step','time_s','dt_s'} and int(plan[-1]['completed_step'])==2180000,'Retain the original complete91 five-column launch plan')
    last_step=int(plan[COUNT-1]['completed_step']);last_time=float(plan[COUNT-1]['time_s'])
    need(d['stage']=='c08_h18_wend_partial_native_r2.receiver' and not d['passed'] and d['diagnostic_complete'] and d['saved_prefix_native_passed'] and d['partial'] and not d['whole_run_native_passed'] and not d['full_run_completed'] and not d['certified_receiver'],'New failed34 native diagnostic must remain partial and failed overall')
    need(d['samples']==COUNT and d['completed_steps']==d['last_saved_completed_step']==last_step and d['last_saved_part']==COUNT-1 and d['original_target_completed_step']==2180000 and d['original_target_samples']==91 and not d['actual_terminal_solver_step_proven'] and not d['unsaved_state_reconstructed'],'Actual34 saved prefix cannot replace the uncompleted91 target or unsaved terminal state')
    need(d['typed_arrays']==22 and d['typed_bytes_per_particle']==212 and d['actual_native_IDs_per_frame']==6805 and d['actual_fixed_IDs']==1805 and d['soil_IDs']==5000 and d['ledger_checks']==d['rho_cache_bits_checks']==d['kappa_nondecreasing_from_PRE_checks']==COUNT*5000 and d['P0_bits_checks']==COUNT*6805 and d['fixed_marker_checks']==COUNT*1805 and d['plane_gap_checks']==COUNT*10000 and d['FS23_pressure_checks']>=COUNT,'Original all34 native ID/ledger/cache/P0/kappa/FS/plane coverage differs')
    need(d['max_scalar_clock_error_s']<=1e-14 and d['max_signed_dterror_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['nonempty_signed_intervals']==COUNT and d['saved_steps_checked_against_launch_plan'] and not d['completed_runtime_Run_csv_checked'] and d['actual_failed_Runout_text_checked'],'Original clock/signed/ledger guards or truthful failure annotations differ')
    need(d['H']==old.f32(.072) and d['group']=='psi0' and d['geometry_profile']=='bedroles' and d['release_target_ID_begin']==1805 and d['release_target_ID_count']==d['actual_retired_count']==255 and d['actual_retired_IDs_contiguous'] and not d['keep_bed_overlap'] and d['source_handoff_schema']==d['source_material_law_version']==d['target_material_law_version']==2 and d['source_PRE_is_complete'] and d['source_PREs_read']==1 and d['source_PRE_part']==1000 and d['source_actual_time_s']==src['done']['actual_end_s'] and d['source_PRE_contract_kernel_checked'] and d['declared_Kernel_XML_CSV']==2,'Actual same-material Wendland/bedroles/source PRE scope differs')
    need(d['NoPenOn_argument'] and d['DynamicNoPenetrationPolicy']=='FixedPlaneStageProjectionReleaseOnly' and d['DynamicNoPenetrationActive'] and not d['DynamicNoPenetrationReactionClosed'],'Original release-only contact policy differs')
    need(meta['stage']=='c08_h18_wend_partial_native_r2.metadata' and not meta['passed'] and meta['saved_metadata_passed'] and meta['partial'] and not meta['whole_run_native_passed'] and meta['profile']=='window_partial' and meta['samples']==COUNT and meta['receiver_material_CSV_keys']==17 and meta['AS_active_true_headers']==COUNT and meta['AS_policy']=='ReleaseOnly' and meta['AS_coefficient_float_reference']==old.f32(.7) and meta['AS_exponent_float_reference']==old.f32(3.825) and meta['expected_ponding_policy']=='CompletedOnly' and meta['ponding_policy_keys_absent_headers']==COUNT,'Actual AS.7 partial/CompletedOnly metadata differs')
    need(build['passed'] and build['consumed_stats_unchanged'] and not build['JSph_objects_linked'] and call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None and same(call['program'],bind(build['program'])['path']),'Actual r2 diagnostic reader build/program/exit differs')
    args=call['arguments']
    need(len(args)==8 and args[:3]==['--receiver','failed34_as07','psi0'] and same(args[3],path(spec['input_xml']).parent/'data') and same(args[4],bind(source_run['source_pre_file'])['path']) and same(args[5],spec['plan']) and same(args[6],spec['material_csv']) and same(args[7],root),'Actual failed34 DATA/PRE/full91plan/17CSV/native output binding differs')
    need(run['stage']==RUN and not run['passed'] and not run['solver_completed'] and run['actual_exit']==run['actual_Win32_exit']==1 and bind(run['source_pre_file'])==bind(source_run['source_pre_file']) and same(bind(run['input_xml'])['path'],spec['input_xml']),'Original failed AS.7 receiver/PRE cannot be relabelled complete')
    actual=read(bind(run['actual_call'])['path'])
    need(actual['actual_solver_Win32_exit']==actual['actual_Popen_wait_exit']==actual['actual_Win32_exit']==1 and not actual['ownership_errors'] and same(actual['actual_solver']['exe'],bind(run['program'])['path']),'Actual failed owned process identity/exits differ')
    physical_build=read(bind(run['source_build'])['path'])
    need(physical_build['passed'] and physical_build['consumed_stats_unchanged'] and bind(physical_build['program'])==bind(run['program']) and physical_build['source_archive']==run['source_archive'],'Actual physical program/source closure differs')
    xml=ET.parse(path(spec['input_xml'])).getroot();pars=receiver.profile_xml(spec,xml,src_spec['material_csv']);gravity=xml.find('execution/special/gravitypreload')
    need(gravity is not None and same(gravity.get('statefile'),args[4]) and gravity.get('keep_bed_overlap')=='false' and float(pars['DtFixed'])==5e-6 and int(pars['NoPenetration'])==int(pars['ArtificialStress'])==1,'Actual receiver source/plane/AS/fixed-step input differs')
    runout_path=path(spec['input_xml']).parent/'Run.out';runout=runout_path.read_text(encoding='utf-8-sig')
    need('Kernel="Wendland"' in runout and runout.count('GravityPreload: state imported file=')==1 and runout.count('GravityPreload: phase=released ')==1 and 'GPU dynamic wall requires a finite saturated first-order mirror fit at every active sample.' in runout and 'Finished execution (code=1).' in runout and 'Finished execution (code=0).' not in runout,'Actual failed Run.out cause/kernel/import/release differs')
    pattern=r'DynamicPoreWall rejected: stage=(\d+) sorted_slot=(\d+) native_id=(\d+) step_start=([0-9.eE+-]+) step=(\d+) B=\(([^)]+)\) normal=\(([^)]+)\)\.'
    matches=re.findall(pattern,runout);need(len(matches)==1,'One actual reported wall rejection required');value=matches[0]
    failure=dict(stage=int(value[0]),sorted_slot=int(value[1]),native_id=int(value[2]),reported_step_start_s=float(value[3]),reported_step=int(value[4]),B=[float(q) for q in value[5].split(',')],normal=[float(np.float32(q)) for q in value[6].split(',')])
    need(failure['stage']==0 and failure['native_id']==803 and failure['reported_step']==2066541 and failure['reported_step_start_s']==10.332704999693412 and failure['reported_step']>last_step and failure['reported_step_start_s']>last_time,'Only the actual unsaved wall803 log observation is admitted')
    thresholds=re.findall(r'mDBC-Threshold=([0-9.eE+-]+)',runout);need(len(thresholds)==1,'Actual mDBC threshold required');failure['MdbcThreshold']=float(thresholds[0])
    expected=np.concatenate((np.arange(1805,dtype=np.uint32),np.arange(2060,7060,dtype=np.uint32)))
    layout=table(root/'typed22_layout.csv');fields=[('time','<f8')];need(len(layout)==22,'Literal original22 schema required')
    for row,(name,kind,width) in zip(layout,old.SCHEMA):
        need((row['array'],row['type'],int(row['components']),int(row['bytes_per_particle']))==(name,kind,width,old.TYPES[kind].itemsize*width),'Original typed22 schema differs')
        fields.append((name,old.TYPES[kind],(6805,width)))
    raw=root/'typed22.bin';dtype=np.dtype(fields)
    with raw.open('rb') as handle:need(struct.unpack('<III',handle.read(12))==(6805,22,COUNT),'Genuine34 native header must remain34, not91')
    need(raw.stat().st_size==12+COUNT*dtype.itemsize,'Actual34 payload extent differs')
    clocks=table(root/'clocks.csv');need(len(clocks)==COUNT,'Actual34 clocks required')
    for part,(clock,planned) in enumerate(zip(clocks,plan)):
        need(int(clock['part'])==int(planned['part'])==part and int(clock['completed_step'])==int(planned['completed_step']) and int(clock['saved_step'])==int(planned['saved_step']) and float(clock['dt_s'])==float(planned['dt_s'])==5e-6 and abs(float(clock['time_s'])-float(planned['time_s']))<=1e-14,'Actual34 saved clocks differ from the untouched91-plan prefix')
    need(int(clocks[0]['completed_step'])==2000001 and float(clocks[0]['time_s'])>src['done']['actual_end_s'] and int(clocks[-1]['completed_step'])==last_step,'First save is PRE+1 and last completion comes from the retained plan')
    consumed.extend(stat(q) for q in (BUILD,root/'completion.json',root/'bedkeep_metadata.json',spec['native_call'],spec['run'],spec['input_xml'],spec['material_csv'],spec['plan'],runout_path))
    consumed.extend((bind(build['program']),bind(build['source'])))
    consumed.extend(bind(run[key]) for key in ('actual_call','program','source_build','source_capture','source_archive','input_xml','source_pre_file'))
    consumed.extend(stat(root/name) for name in ('typed22.bin','typed22_layout.csv','clocks.csv'))
    bundle=dict(spec=dict(tag=RUN,source=src['spec']['source'],group='psi0',actualAS=spec['actualAS'],H=.072),root=root,done=d,source=False,geometry_profile='bedroles',count=COUNT,nodes=6805,expected=expected,frames=np.memmap(raw,dtype=dtype,offset=12,mode='r',shape=(COUNT,)),clocks=clocks,kw=src['kw'],yield_rows={},runtime_observed=dict(passed=False,solver_completed=False,actual_exit=1,actual_Win32_exit=1),_source=src)
    return bundle,failure


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args()
    need(args.execution_authorized,'Root full-read before one unique offline review')
    manifest=read(args.manifest);tag=manifest['tag'];need(re.fullmatch(r'[A-Za-z0-9_]+',tag),'Safe fresh derived tag required')
    prefix=T/'figures'/tag;check=T/'logs'/(tag+'.check.json')
    need(not check.exists() and not list(prefix.parent.glob(tag+'_*')),'Retained complete or partial derived artifacts are protected')
    consumed=[stat(args.manifest),stat(__file__),stat(T/'notes'/(TAG+'.md')),stat(previous.__file__),stat(receiver.__file__),stat(source.__file__),stat(old.__file__)]
    result=dict(stage=TAG,analysis_complete=False,receiver_complete=False,whole_run_passed=False,physical_acceptance=False,winner_selected=False,consumed=consumed)
    try:
        src=source.load(manifest['source'],consumed);reference=old.reference_from(src)
        bundle,failure=load_partial(manifest['case'],src,manifest['source'],consumed)
        snapshots=manifest.get('snapshots_tau_s',[.1,.2,.3,.33])
        need(isinstance(snapshots,list) and snapshots and all(isinstance(t,(int,float)) and 0<=t<=float(bundle['clocks'][-1]['time_s'])-reference['time'] for t in snapshots),'Requested snapshots must lie in the actual34 saved window')
        analysis=old.analyze_case(bundle,reference,snapshots)
        definitions=receiver.add_total_settlement(analysis,reference);first=receiver.first_step(bundle,reference);files=[]
        for name in ('history','extrema','layers','tracks'):
            dest=Path(str(prefix)+'_'+name+'.csv');old.write_csv(dest,analysis[name]);files.append(dest)
        for name,rows in (('first_real_step',[first]),('selection_metrics',[receiver.selection_summary(analysis)])):
            dest=Path(str(prefix)+'_'+name+'.csv');old.write_csv(dest,rows);files.append(dest)
        fields=[]
        for part,snapshot in analysis['snapshots'].items():
            for index,position in enumerate(snapshot['pos']):
                fields.append(dict(tag=RUN,part=part,time_s=snapshot['time_s'],tau_s=snapshot['tau_s'],native_id=2060+index,x_m=float(position[0]),z_m=float(position[2]),p_Pa=float(snapshot['p'][index]),native_p_minus_fixedP0_Pa=float(snapshot['excess'][index]),kappa=float(snapshot['kappa'][index]),J=float(snapshot['J'][index])))
        if fields:
            dest=Path(str(prefix)+'_fields.csv');old.write_csv(dest,fields);files.append(dest)
        files.extend(old.plot_results([analysis],prefix));files.append(receiver.metrics_plot([analysis],prefix))
        need(all(stat(entry['path'])==entry for entry in consumed),'Sealed source, failed receiver or helper evidence changed')
        result.update(analysis_complete=True,saved_prefix_native_qualified=True,actual_saved_records=COUNT,original_target_records=91,last_saved_completed_step=int(bundle['clocks'][-1]['completed_step']),actual_source_time_s=reference['time'],reported_failure=failure,receiver_summary=analysis['summary'],first_real_step_changes=first,reference_definitions=definitions,saved_wall_replay_performed=False,unsaved_failure_state_reconstructed=False,no_new_parameter_choice_or_solver=True,solver_invocations=0,decoder_invocations=0,VTK_invocations=0,SHA_scans=0,visual_QA_pending=True,consumed_stats_unchanged=True,files=[stat(q) for q in files])
    except Exception as error:
        result.update(first_failure=str(error),partial_outputs_preserved=True);raise
    finally:
        with check.open('x',encoding='utf-8') as handle:json.dump(result,handle,indent=2,allow_nan=False);handle.write('\n')


if __name__=='__main__':main()
