"""One separately authorized epsilon.2/exponent3 native read; no solver or later action."""
import argparse,csv,json,math,os,struct
from pathlib import Path
import psutil
import mdbc_partition_components_r3 as e
import upl_c08_asn3_window_r1 as owner

T,L,PRE=owner.T,owner.L,owner.PRE;RUN_TAG=owner.TAG;OUT=T/'outputs'/RUN_TAG
READER_TAG='upl_c08_asn3_window_native_r1';TAG='upl_c08_asn3_window_native_run_r1';SAMPLES=66;END=4264000
def lexical(path):return os.path.normcase(os.path.abspath(path))
def f32(value):return struct.unpack('<f',struct.pack('<f',value))[0]

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');args=ap.parse_args();e.need(args.execution_authorized,'Root full-read and separate unique native-read authorization required')
    native=OUT/'native_r1';label=RUN_TAG+'.native_r1';receipt=L/(label+'.json');callpath=L/(label+'.call.json');log=L/(label+'.log')
    e.need(not native.exists() and not (OUT/'native').exists() and not receipt.exists() and not callpath.exists() and not log.exists(),'Existing/partial native result or reader invocation protected')
    before=[];actual=None;result=dict(stage=label,passed=False,physical_acceptance=False,solver_invocations=0,GenCase_invocations=0,decoder_invocations=0,VTK_invocations=0,analysis_invocations=0,queue_invocations=0,SHA_scans=0,actual_output_directory=str(OUT),native_directory=str(native),expected_AS_coefficient=f32(.2),expected_AS_exponent=3.)
    try:
        rp=L/(RUN_TAG+'.run.json');cp=L/(RUN_TAG+'.call.json');sp=L/(RUN_TAG+'.start.json');r,c,start=e.read(rp),e.read(cp),e.read(sp)
        e.need(r['passed'] and r['stage']==RUN_TAG and r['actual_exit']==r['actual_Win32_exit']==0 and r['consumed_stats_unchanged'] and r['solver_invocations']==1 and r['reader_invocations']==0 and r['actual_steps']==END and r['saved_frames']==SAMPLES,'Sealed normal n3 target required; no active/failed job decoder admission')
        e.need(r['ArtificialStress'] and r['ArtificialStressCoef']==.2 and r['ArtificialStressExp']==3. and r['keep_bed_overlap'] and r['expected_active_native_IDs']==6805 and r['policy']==owner.base.POLICY,'Actual epsilon.2/exponent3/fixed-plane/keep-bed scope differs')
        e.need(c['actual_Popen_wait_exit']==c['actual_Win32_exit']==c['actual_solver_Win32_exit']==0 and c['ownership_errors']==[] and start['actual_outer']==start['actual_solver']==c['actual_outer']==c['actual_solver'],'Original direct target/start identity or actual exit differs')
        adpath=Path(e.bind(c['admission'])['path']);ad=e.read(adpath);rootpath=Path(e.bind(ad['root_admission'])['path']);root=e.read(rootpath);identity=c['actual_solver']
        e.need(c['admission']==start['admission'] and c['stage']==start['stage']==ad['stage']==RUN_TAG and start['owner']==ad['owner'] and identity['parent_pid']==ad['owner']['pid'] and c['arguments']==ad['argv']==ad['solver_argv']==identity['argv'],'Actual owned stage/argv/parent/admission differs')
        e.need(identity['pid']>0 and identity['creation_filetime_100ns']>0 and math.isfinite(ad['owner']['created_epoch']) and ad['owner']['created_epoch']>0,'Captured process creation identity missing')
        e.need(root['passed'] and root['allowed_job']==RUN_TAG and root['ArtificialStressCoef']==.2 and root['ArtificialStressExp']==3. and ad['planned_new_updates']==264000 and ad['planned_global_end']==END and ad['expected_saved_frames']==SAMPLES,'Original root/owner single n3 window admission differs')
        e.need(e.bind(r['actual_call'])==e.stat(cp) and Path(identity['exe']).samefile(r['program']['path']) and ad['program']==r['program'] and ad['source_build']==r['source_build'] and ad['source_pre_file']==r['source_pre_file'] and Path(e.bind(r['source_pre_file'])['path']).samefile(PRE),'Actual call/program/build/original PRE binding differs')
        prefix=OUT/RUN_TAG;command=[r['program']['path'],'-gpu:0','-stable','-mdbc_freeslip:1',str(prefix),str(OUT),'-dirdataout','data','-svres','-nsteps:'+str(END)];e.need(c['arguments']==command,'Only the original same-tag output/seed argv is admitted')
        input_path=Path(e.bind(r['input_xml'])['path']);e.need(input_path.samefile(Path(str(prefix)+'.xml')),'Actual generated input must match this job/output');owner.check_input(input_path,generated=True)
        genpath=Path(e.bind(r['GenCase_call'])['path']);gen=e.read(genpath);e.need(gen['actual_Popen_wait_exit']==gen['actual_Win32_exit']==0 and gen['ownership_failure'] is None,'Original single successful GenCase receipt required')
        plan=Path(e.bind(ad['planned_steps'])['path']);e.need(plan.samefile(OUT/'planned_steps.csv'),'Original owner plan differs')
        with plan.open(newline='') as f:planned=list(csv.DictReader(f))
        e.need(len(planned)==SAMPLES and all(int(q['part'])==i and int(q['completed_step'])==4000000+4000*(i+1) for i,q in enumerate(planned)),'Original66/4000-step planned saves differ')
        normal=owner.summary(OUT/'Run.csv');parts=sorted((OUT/'data').glob('Part_*.bi4'));text=(OUT/'Run.out').read_text(encoding='utf-8-sig')
        e.need(normal==r['summary'] and int(normal['Steps'])==END and int(normal['PartFiles'])==SAMPLES and normal['Np']=='7060' and normal['Nbound']==normal['Nfixed']=='2060' and all(normal[k]=='0' for k in ('PartsOut','PartsOutRhop','PartsOutVel')) and 'Finished execution (code=0).' in text,'Actual normal n3 Run.csv/registry/no-exclusion differs')
        e.need([p.name for p in parts]==['Part_%04d.bi4'%i for i in range(SAMPLES)] and r['PARTs']==[e.stat(p) for p in parts] and e.bind(r['Run_out'])==e.stat(OUT/'Run.out') and e.bind(r['Run_csv'])==e.stat(OUT/'Run.csv'),'Actual native files/normal logs differ from sealed run')
        e.need(r['trace_rows']==450003 and r['trace_sampled_steps_per_ID']==30000,'Run-sealed trace coverage differs; this wrapper does not rescan it')
        solverbuild=e.read(e.bind(r['source_build'])['path']);e.need(solverbuild['passed'] and solverbuild['actual_typed_exit_code']==solverbuild['actual_Win32_exit']==0 and solverbuild['source_stats_unchanged'] and solverbuild['trace_macro_enabled'] and e.bind(solverbuild['program'])==r['program'],'Executed program differs from closed trace Release build')
        bp=L/(READER_TAG+'.build.json');b=e.read(bp);e.need(b['passed'] and b['consumed_stats_unchanged'] and len(b['objects'])==6 and b['actual_link_objects']==7 and not b['JSph_objects_linked'],'Passed separate n3 native reader build required');program=Path(e.bind(b['program'])['path']);e.need(program.samefile(T/'outputs'/(READER_TAG+'_build')/'C08ASN3WindowNative_win64.exe'),'Wrong native program; old exponent2.55/AS05 readers forbidden')
        for proc in psutil.process_iter(['exe','cmdline']):
            try:
                exe=proc.info['exe'];argv=proc.info['cmdline'] or [];e.need(not(exe and lexical(exe) in (lexical(program),lexical(r['program']['path']))) and not any(lexical(token) in (lexical(native),lexical(OUT/'data')) for token in argv[1:]),'Solver or reader using this data/output is active; no process stopped')
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        before=[e.stat(p) for p in (Path(__file__),T/'notes'/(TAG+'.md'),Path(owner.__file__),Path(e.__file__),rp,cp,sp,adpath,rootpath,genpath,bp,plan)]+r['consumed']+[r[k] for k in ('program','source_build','input_xml','source_pre_file','Run_csv','Run_out','trace_file')]+r['PARTs']+[b[k] for k in ('program','source','generated_core','core_diff','core_derivation')]
        e.need(all(e.stat(q['path'])==q for q in before),'Consumed source/program/runtime/input/output or reader identity changed')
        argv=[str(program),'--read','psi0','GPU',str(OUT/'data'),str(PRE),str(END),str(native)];result['decoder_invocations']=1;actual=e.invoke(label,argv,T.parent)
        call=e.read(actual['path']);e.need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None and call['child']['argv']==argv and Path(call['child']['exe']).samefile(program) and call['child']['parent_pid']==os.getpid() and call['child']['creation_filetime_100ns']>0,'Actual reader typed exit/argv/creation/parent differs')
        d,m=e.read(native/'completion.json'),e.read(native/'bedkeep_metadata.json');counts=dict(samples=SAMPLES,completed_steps=END,typed_arrays=22,typed_bytes_per_particle=212,actual_native_IDs_per_frame=6805,soil_IDs=5000,actual_fixed_IDs=1805,ledger_checks=330000,fixed_marker_checks=119130,P0_bits_checks=449130,rho_cache_bits_checks=330000,kappa_nondecreasing_from_PRE_checks=330000,nonempty_signed_intervals=66,plane_gap_checks=660000)
        e.need(d['passed'] and d['stage']==READER_TAG and d['backend_argument']=='GPU' and all(d[k]==v for k,v in counts.items()) and d['completed_runtime_Run_csv_checked'] and d['saved_steps_checked_against_window_profile'] and d['window_save_cadence_steps']==4000 and d['window_saved_samples']==66,'Original66/6805/22 coverage or actual window differs')
        e.need(d['max_scalar_clock_error_s']<=1e-14 and d['max_ledger_relative_error']<=5e-13 and d['max_signed_dterror_s']<=1e-14 and d['min_soil_x_m']>=-d['geometry_tolerance_m'] and d['min_soil_z_m']>=-d['geometry_tolerance_m'] and d['source_actual_time_s']==r['actual_source_time_from_loader'],'Original signed/clock/ledger/plane/source-time guard differs')
        e.need(d['NoPenOn_argument'] and d['DynamicNoPenetrationActive'] and d['DynamicNoPenetrationPolicy']==owner.base.POLICY and not d['DynamicNoPenetrationReactionClosed'] and d['release_target_ID_begin']==1800 and d['release_target_ID_count']==260 and d['actual_retired_count']==255 and not d['actual_retired_IDs_contiguous'] and d['kept_bed_IDs']==list(owner.base.BED_IDS) and d['kept_bed_count']==d['kept_bed_source_geometry_checks']==5,'Original fixed-plane/five-bed/255-retirement scope differs')
        e.need(m['passed'] and m['stage']==READER_TAG+'.metadata' and m['samples']==m['metadata_header_scans']==m['keep_policy_headers']==m['AS_active_true_headers']==66 and m['completed_steps']==END and m['keep_bed_overlap'] and m['expected_AS'] and m['AS_policy']=='ReleaseOnly' and m['AS_coefficient_float_reference']==f32(.2) and m['AS_exponent_float_reference']==3. and m['original_target_count']==260 and m['actual_retired_count']==255 and m['kept_bed_IDs']==list(owner.base.BED_IDS) and m['core_array_decode_passes']==1 and not m['metadata_scans_decode_field_arrays'] and not m['core_original_numerical_budgets_changed'],'Typed epsilon.2/exponent3 ReleaseOnly/keep metadata or unique array decode differs')
        e.need(all(e.stat(q['path'])==q for q in before),'Consumed files changed during one native read');result.update(passed=True,actual_call=actual,source_run=e.stat(rp),original_run=e.stat(rp),completion=e.stat(native/'completion.json'),metadata=e.stat(native/'bedkeep_metadata.json'),original_native_guards_passed=True,consumed_stats_unchanged=True,outputs=[e.stat(p) for p in sorted(native.iterdir()) if p.is_file()])
    except Exception as error:result.update(first_failure=str(error),actual_call=e.stat(callpath) if callpath.exists() else actual)
    result['consumed']=before;e.save(receipt,result);print(json.dumps(dict(passed=result['passed'],receipt=str(receipt),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
