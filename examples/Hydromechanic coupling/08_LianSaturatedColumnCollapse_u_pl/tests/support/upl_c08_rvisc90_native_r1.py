"""One admitted rvisc90 original22 utility read plus exact retained30 prefix; never solve/build."""
import argparse,csv,math,os,struct
from pathlib import Path
import psutil
import mdbc_partition_components_r3 as e
T=Path(__file__).resolve().parents[1];C=T.parent;L=T/'logs'
TAG='upl_c08_rvisc90_native_r1';JOB='upl_c08_rvisc90_GPU_r1';OUT=T/'outputs'/JOB;NATIVE=OUT/'native_r1'
UTILITY='upl_c08_causal_native_r1';NOTE=T/'notes'/(TAG+'.md')
PRE=C/'CaseLianSaturatedColumnCollapse_shared_preload_r2_GPU_out/data/Part_1000.bi4'
END=4360000;SAMPLES=90;BED=[1800,1852,1904,1956,2008];POLICY='FixedPlaneStageProjectionReleaseOnly'
def lexical(p):return os.path.normcase(os.path.abspath(p))
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]

def retained30(run,before):
    path=L/'upl_c08_rvisc_window_GPU_r1.native_r1.json';r=e.read(path)
    e.need(r['passed'] and r['original_native_guards_passed'] and r['consumed_stats_unchanged'] and r['decoder_invocations']==1,'Closed completed rvisc30 native required')
    cp=Path(e.bind(r['completion'])['path']);d=e.read(cp);old=cp.parent
    e.need(old.samefile(T/'outputs/upl_c08_rvisc_window_GPU_r1/native_r1') and d['passed'] and d['samples']==30 and d['completed_steps']==4120000 and d['typed_arrays']==22 and d['actual_native_IDs_per_frame']==6805,'Retained actual30 native scope differs')
    rp=Path(e.bind(r['source_run'])['path']);prior=e.read(rp)
    e.need(prior['passed'] and prior['solver_completed'] and prior['actual_exit']==prior['actual_Win32_exit']==0 and all(prior[k]==run[k] for k in ('program','source_build','source_capture','source_archive','source_pre_file','actual_source_time_from_loader')),'Same actual program/source/PRE/clock as completed30 required')
    files={Path(q['path']).name:q for q in r['outputs']};before += [e.stat(path),e.stat(cp),e.stat(rp),e.bind(r['metadata']),e.bind(r['actual_call'])]
    for leaf in ('typed22.bin','typed22_layout.csv','clocks.csv'):
        q=e.bind(files[leaf]);e.need(Path(q['path']).samefile(old/leaf),'Retained30 file path differs');before.append(q)
    return path,old

def prefix30(old,reference):
    same_layout=(NATIVE/'typed22_layout.csv').read_bytes()==(old/'typed22_layout.csv').read_bytes()
    size=8+6805*212;first=None
    with (NATIVE/'typed22.bin').open('rb') as a,(old/'typed22.bin').open('rb') as b:
        ha,hb=struct.unpack('<III',a.read(12)),struct.unpack('<III',b.read(12))
        e.need(ha==(6805,22,90) and hb==(6805,22,30) and (NATIVE/'typed22.bin').stat().st_size==12+90*size and (old/'typed22.bin').stat().st_size==12+30*size,'Genuine90/30 headers/extents must remain intact')
        for part in range(30):
            x,y=a.read(size),b.read(size);e.need(len(x)==len(y)==size,'Truncated native prefix')
            if x!=y and first is None:first=dict(part=part,record_byte=next(i for i,(u,v) in enumerate(zip(x,y)) if u!=v))
        e.need(b.read(1)==b'','Extra retained30 payload')
    clocks=(NATIVE/'clocks.csv').read_bytes().splitlines(keepends=True);prior=(old/'clocks.csv').read_bytes().splitlines(keepends=True)
    e.need(len(clocks)==91 and len(prior)==31,'Actual90/30 clock row counts differ');same_clock=clocks[:31]==prior
    return dict(passed=first is None and same_layout and same_clock,reference_native=e.stat(reference),actual_common_saved_frames=30,new_original_header=list(ha),reference_original_header=list(hb),headers_rewritten=False,all22_and_actual_time_payload_byte_exact=first is None,typed_layout_byte_exact=same_layout,clock_and_signed_header_and_first30_rows_byte_exact=same_clock,first_different_record_byte=first,physical_acceptance=False)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();e.need(a.execution_authorized,'Root full-read and separate unique-reader authorization required')
    label=JOB+'.native_r1';receipt=L/(label+'.json');callpath=L/(label+'.call.json');log=L/(label+'.log')
    e.need(not NATIVE.exists() and not (OUT/'native').exists() and not any(q.exists() for q in (receipt,callpath,log)),'Existing/partial result or decoder call protected')
    before=[];actual=None;result=dict(stage=TAG,passed=False,profile='window90',physical_acceptance=False,solver_invocations=0,GenCase_invocations=0,decoder_invocations=0,VTK_invocations=0,queue_invocations=0,SHA_scans=0,native_directory=str(NATIVE),utility_reused_without_build=True,utility_stage_preserved=UTILITY,candidate_operator_is_not_BI4_metadata=True,candidate_sidecar_revalidated_by_reader=False)
    try:
        rp,cp,sp=(L/(JOB+s) for s in ('.run.json','.call.json','.start.json'));r,c,s=e.read(rp),e.read(cp),e.read(sp)
        e.need(r['passed'] and r['solver_completed'] and r['profile']=='window90' and r['configuration']=='Release' and r['actual_exit']==r['actual_Win32_exit']==0 and r['consumed_stats_unchanged'] and r['actual_steps']==END and r['saved_frames']==SAMPLES,'Closed actual normal90 run required')
        e.need(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==c['actual_solver_Win32_exit']==0 and c['ownership_errors']==[] and c['actual_outer']==c['actual_solver']==s['actual_outer']==s['actual_solver'] and c['admission']==s['admission'] and e.bind(r['actual_call'])==e.stat(cp),'Real direct solver/start/call closure differs')
        adpath=Path(e.bind(c['admission'])['path']);ad=e.read(adpath);rootentry=e.bind(ad['root_admission']);root=e.read(rootentry['path']);identity=c['actual_solver']
        e.need(c['stage']==s['stage']==ad['stage']==JOB and s['owner']==ad['owner'] and identity['parent_pid']==ad['owner']['pid'] and identity['pid']>0 and identity['creation_filetime_100ns']>0 and math.isfinite(ad['owner']['created_epoch']) and root['passed'] and root['allowed_job']==JOB and e.bind(r['owner_admission'])==e.stat(adpath),'Actual owner/creation/root admission differs')
        e.need(ad['planned_global_end']==END and ad['planned_new_updates']==360000 and ad['expected_saved_frames']==90 and all(ad[k]==r[k] for k in ('program','source_build','source_capture','source_archive','source_pre_file','input_xml','seed','planned_steps')),'Owner program/source/input/plan binding differs')
        program_entry=e.bind(r['program']);e.need(Path(identity['exe']).samefile(program_entry['path']) and Path(e.bind(r['source_pre_file'])['path']).samefile(PRE),'Actual program/original PRE differs')
        prefix=OUT/JOB;solver_argv=[program_entry['path'],'-gpu:0','-stable','-mdbc_freeslip:1',str(prefix),str(OUT),'-dirdataout','data','-svres','-nsteps:'+str(END)]
        e.need(identity['argv']==ad['solver_argv']==ad['argv']==c['arguments']==solver_argv and Path(e.bind(r['input_xml'])['path']).samefile(Path(str(prefix)+'.xml')),'Actual solver argv/generated input differs')
        genpath=Path(e.bind(r['GenCase_call'])['path']);gen=e.read(genpath);e.need(gen['actual_Popen_wait_exit']==gen['actual_Win32_exit']==0 and gen['ownership_failure'] is None,'Real successful GenCase call required')
        plan=Path(e.bind(r['planned_steps'])['path']);e.need(plan.samefile(OUT/'planned_steps.csv'),'Same-job launch plan required')
        with plan.open(encoding='utf-8',newline='') as f:planned=list(csv.DictReader(f))
        e.need(planned==[dict(part=str(i),completed_step=str(4000000+4000*(i+1))) for i in range(90)],'Normal90 cadence must be4000 actual updates')
        normal=r['summary'];parts=sorted((OUT/'data').glob('Part_*.bi4'));text=(OUT/'Run.out').read_text(encoding='utf-8-sig')
        e.need(int(normal['Steps'])==END and int(normal['PartFiles'])==90 and normal['Np']=='7060' and normal['Nbound']==normal['Nfixed']=='2060' and all(normal[k]=='0' for k in ('PartsOut','PartsOutRhop','PartsOutVel')) and 'Finished execution (code=0).' in text,'Original normal registry/no-loss differs')
        e.need([q.name for q in parts]==['Part_%04d.bi4'%i for i in range(90)] and r['PARTs']==[e.stat(q) for q in parts] and e.bind(r['Run_csv'])==e.stat(OUT/'Run.csv') and e.bind(r['Run_out'])==e.stat(OUT/'Run.out'),'Original PART/log stats differ')
        sbpath=Path(e.bind(r['source_build'])['path']);sb=e.read(sbpath)
        e.need(sbpath.samefile(L/'upl_c08_residual_visc_gpu_Release_r1.build.json') and sb['passed'] and sb['consumed_stats_unchanged'] and sb['profile']=='Release' and sb['configuration']=='Release' and sb['alpha']==.1 and all(sb[k]==r[k] for k in ('program','source_capture','source_archive','private_sources','runtime')) and sb['physical_objects_recompiled']==2 and sb['retained_physical_objects']==111 and sb['actual_link_objects']==113,'Exact same private Release program required')
        sidepath=Path(e.bind(r['telemetry_review'])['path']);side=e.read(sidepath)
        e.need(side['passed'] and side['profile']=='window90' and side['actual_call']==r['actual_call'] and side['source_program']==r['program'] and side['source_build']==r['source_build'] and side['input_xml']==r['input_xml'] and side['planned_steps']==r['planned_steps'] and side['CSV_columns']==26 and side['CSV_rows']==180 and side['alpha']==.1 and side['active'] and all(side[k]==360000 for k in ('actual_Pre_calls','actual_Cor_calls','actual_Pre_commits','actual_Cor_commits')) and side['not_BI4_metadata'],'Real owner90 sidecar review required; reader does not verify the new operator')
        sidefiles=[e.bind(r[k]) for k in ('policy_file','meter_file')];e.need(sidefiles==[e.bind(side[k]) for k in ('policy_file','meter_file')],'Sidecar file bindings differ')
        bp=L/(UTILITY+'.build.json');b=e.read(bp)
        e.need(b['passed'] and b['consumed_stats_unchanged'] and len(b['objects'])==6 and b['actual_link_objects']==7 and not b['JSph_objects_linked'] and not b['Debug_objects_or_CRT_used'],'Existing qualified six-utility Release reader required')
        program=Path(e.bind(b['program'])['path']);e.need(program.samefile(T/'outputs'/(UTILITY+'_build')/'C08CausalNative_win64.exe'),'Wrong retained utility program')
        for process in psutil.process_iter(['exe','cmdline']):
            try:
                exe=process.info['exe'];args=process.info['cmdline'] or []
                e.need(not (exe and lexical(exe) in (lexical(program),lexical(program_entry['path']))) and not any(lexical(x) in (lexical(NATIVE),lexical(OUT/'data')) for x in args[1:]),'Active exact solver/reader/DATA consumer protected; no process stopped')
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        before += [e.stat(q) for q in (Path(__file__),NOTE,Path(e.__file__),rp,cp,sp,adpath,Path(rootentry['path']),genpath,bp,plan,sidepath)]+r['consumed']+[e.bind(r[k]) for k in ('program','source_build','source_capture','source_archive','source_pre_file','input_xml','Run_out','Run_csv')]+[e.bind(q) for q in r['seed']+r['PARTs']]+sidefiles+[e.bind(b[k]) for k in ('program','source','generated_core','core_diff','core_derivation')]+[e.bind(q) for q in b['objects']+b['calls']]
        reference,old=retained30(r,before);e.need(all(e.stat(q['path'])==q for q in before),'Closed source/utility/PRE/retained30 inputs changed')
        argv=[str(program),'--read','psi0','GPU',str(OUT/'data'),str(PRE),str(END),'90','1',str(plan),str(NATIVE)]
        result['decoder_invocations']=1;actual=e.invoke(label,argv,C);call=e.read(actual['path'])
        e.need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None and call['child']['argv']==argv and Path(call['child']['exe']).samefile(program) and call['child']['parent_pid']==os.getpid() and call['child']['creation_filetime_100ns']>0,'One utility read actual exit/exe/argv/creation differs')
        d,m=e.read(NATIVE/'completion.json'),e.read(NATIVE/'bedkeep_metadata.json')
        counts=dict(samples=90,completed_steps=END,new_updates=360000,typed_arrays=22,typed_bytes_per_particle=212,original_ID_domain=7060,actual_native_IDs_per_frame=6805,soil_IDs=5000,actual_fixed_IDs=1805,ledger_checks=450000,fixed_marker_checks=162450,P0_bits_checks=612450,rho_cache_bits_checks=450000,kappa_nondecreasing_from_PRE_checks=450000,nonempty_signed_intervals=90,plane_gap_checks=900000)
        e.need(d['passed'] and d['stage']==UTILITY and d['backend_argument']=='GPU' and not d['backend_proven_by_reader'] and all(d[k]==v for k,v in counts.items()) and d['completed_runtime_Run_csv_checked'] and d['saved_steps_checked_against_launch_plan'] and d['FS23_pressure_checks']>0,'Original all90/22 numerical coverage or launch clock guard differs')
        e.need(d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14 and d['geometry_tolerance_m']==1e-6*.04 and d['min_soil_x_m']>=-d['geometry_tolerance_m'] and d['min_soil_z_m']>=-d['geometry_tolerance_m'] and d['source_actual_time_s']==r['actual_source_time_from_loader'] and d['source_completed_step']==4000000 and d['source_PREs_read']==1 and d['source_material_law_version']==1 and d['target_material_law_version']==2,'Original scalar/signed/ledger/geometry/PRE guards differ')
        e.need(d['NoPenOn_argument'] and d['DynamicNoPenetrationActive'] and d['DynamicNoPenetrationPolicy']==POLICY and not d['DynamicNoPenetrationReactionClosed'] and d['release_target_ID_begin']==1800 and d['release_target_ID_count']==260 and d['actual_retired_count']==255 and d['kept_bed_IDs']==BED and d['kept_bed_count']==d['kept_bed_source_geometry_checks']==5 and not d['actual_retired_IDs_contiguous'] and not d['native_rewritten'],'Original keep5/fixed-plane guards differ')
        e.need(m['passed'] and m['stage']==UTILITY+'.metadata' and m['profile']=='window' and not m['smoke_final_only'] and m['planned_cadence_steps']==4000 and m['completed_steps']==END and all(m[k]==90 for k in ('samples','metadata_header_scans','keep_policy_headers','AS_active_true_headers','ponding_policy_keys_absent_headers')) and m['keep_bed_overlap'] and m['actual_retired_count']==255 and m['kept_bed_IDs']==BED and m['kept_bed_count']==5,'Original utility90 lazy metadata profile differs')
        e.need(m['expected_AS'] and m['AS_policy']=='ReleaseOnly' and m['AS_coefficient_float_reference']==f32(.2) and m['AS_exponent_float_reference']==3. and m['expected_ponding_policy']=='CompletedOnly' and m['core_array_decode_passes']==1 and not m['metadata_scans_decode_field_arrays'] and not m['PRE_arrays_reloaded_by_adapter'] and not m['core_original_numerical_budgets_changed'],'Original AS/CompletedOnly/single22 decode guards differ')
        result['retained_rvisc30_prefix']=prefix30(old,reference);e.need(result['retained_rvisc30_prefix']['passed'],'Actual same-program first30 native prefix differs; preserve read, never retry')
        e.need(all(e.stat(q['path'])==q for q in before),'Closed artifacts changed during unique read')
        result.update(passed=True,source_run=e.stat(rp),utility_build=e.stat(bp),actual_call=actual,completion=e.stat(NATIVE/'completion.json'),metadata=e.stat(NATIVE/'bedkeep_metadata.json'),owner_telemetry_review=e.stat(sidepath),original_native_guards_passed=True,retained30_all22_time_layout_signed_byte_exact=True,consumed_stats_unchanged=True,outputs=[e.stat(q) for q in sorted(NATIVE.iterdir()) if q.is_file()])
    except Exception as error:result.update(first_failure=str(error),actual_call=e.stat(callpath) if callpath.exists() else actual)
    result['consumed']=before;e.save(receipt,result);print(dict(passed=result['passed'],receipt=str(receipt),first_failure=result.get('first_failure')));return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
