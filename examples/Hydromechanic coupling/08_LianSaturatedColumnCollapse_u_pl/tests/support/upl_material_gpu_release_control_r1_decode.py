"""Exactly one completed Release-source native read; no solver/retry/automatic review."""
import ctypes,json,subprocess,sys
from ctypes import wintypes as w
from pathlib import Path
import psutil
import upl_material_release_native_r2_run as base
T=base.T;L=base.L;TAG='upl_material_release_native_r1_source_GPU_release';HELP='upl_material_gpu_release_control_r1'
def main():
    base.need(sys.argv[1:]==['--execution-authorized'],'Use --execution-authorized');RUN=L/(TAG+'.run.json');BUILD=L/(HELP+'.build.json');OUT=T/'outputs'/(TAG+'_native');DATA=T/'outputs'/TAG/'data';CHECK=L/(TAG+'.native.check.json');CALL=L/(TAG+'.native.call.json');START=L/(TAG+'.native.start.json');LOG=L/(TAG+'.native.log');base.need(not OUT.exists() and not any(p.exists() for p in [CHECK,CALL,START,LOG]),'Existing/partial decode protected');frozen=[];result=dict(stage=TAG+'.native',passed=False,decoder_invocations=0,solver_invocations=0,SHA_scans=0,physical_acceptance=False)
    def bind(e):
        q=base.stat(e['path']);base.need(q==e,'Consumed binding changed: '+e['path']);frozen.append(q);return q
    try:
        r,b=base.read(RUN),base.read(BUILD);base.need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==800 and r['consumed_stats_unchanged'],'Actual owned Release source must pass');base.need(b['passed'] and b['consumed_stats_unchanged'] and len(b['objects'])==85,'Current-ABI special-entry reader must pass')
        for p in [RUN,BUILD,Path(__file__),Path(base.__file__)]:bind(base.stat(p))
        for e in r['consumed']:bind(e)
        for k in ['program','source_build','source_capture','source_archive','start_record','actual_call']:bind(r[k])
        c=base.read(r['actual_call']['path']);base.need(c['actual_Popen_wait_exit']==c['actual_tool_Win32_exit']==c['actual_solver_Win32_exit']==0 and c['typed_returncode_captured_first'] and not c['ownership_errors'] and Path(c['solver']['exe']).samefile(r['program']['path']) and c['solver']['argv'][1:]==c['target_argv'][1:],'Original direct Release owner/exits differ')
        for k in ['program','source','source_build']:bind(b[k])
        for e in b['runtime']:bind(e)
        exe=Path(b['program']['path']);base.need(exe.samefile(T/'outputs'/HELP/(HELP+'.exe')),'Wrong special-entry reader program');base.need(not any((q.info['name'] or '').lower()==exe.name.lower() for q in psutil.process_iter(['name'])),'Reader already active; do not duplicate');parts=sorted(DATA.glob('Part_*.bi4'));base.need(len(parts)==r['saved_frames'] and [p.name for p in parts]==['Part_%04d.bi4'%i for i in range(len(parts))],'Actual native membership differs')
        for p in DATA.iterdir():
            if p.is_file():bind(base.stat(p))
        bind(base.stat(T/'outputs/upl_c08_global_CPU_r1/ids.csv'));argv=[str(exe),'--data',str(DATA),'--out',str(OUT)];oid=base.identity(psutil.Process());started=base.utc();errors=[];child={}
        with LOG.open('xb') as stream:
            p=subprocess.Popen(argv,cwd=T.parent,stdout=stream,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);result['decoder_invocations']=1
            try:child=base.identity(psutil.Process(p.pid));base.need(Path(child['exe']).samefile(exe) and child['argv'][1:]==argv[1:] and child['parent_pid']==oid['pid'],'Actual reader owner/argv differs')
            except Exception as e:errors.append(str(e))
            base.save(START,dict(stage=TAG+'.native.start',owner=oid,child=child,argv=argv,source_run=base.stat(RUN),reader_build=base.stat(BUILD)));rc=p.wait();win=base.exitcode(int(p._handle))
        base.save(CALL,dict(stage=TAG+'.native.call',owner=oid,child=child,argv=argv,actual_Popen_wait_exit=rc,actual_Win32_exit=win,typed_returncode_captured_first=type(rc) is int,ownership_errors=errors,started_utc=started,ended_utc=base.utc(),log=base.stat(LOG)));result.update(reader_call=base.stat(CALL),actual_Popen_wait_exit=rc,actual_Win32_exit=win);base.need(rc==win==0 and not errors,'Actual native decoder exit/identity failed')
        d=base.read(OUT/'completion.json');base.need(d['passed'] and d['stage']=='upl_material_release_native_r1' and d['input_run_tag']==TAG and d['backend_argument']=='GPU_release' and d['window']=='source' and d['samples']==r['saved_frames']==22 and d['completed_steps']==800 and d['phase_saved_frames']==[11,11],'Actual Release native profile/count differs')
        expected=dict(original_case_ID_domain=7060,soil_IDs=5000,original_fixed_IDs=2060,typed_arrays=22,typed_bytes_per_particle=212,soil_ledger_checks=110000,soil_cache_float_bits_checks=110000,all_present_ID_p0_float_bits_checks=152460,fixed_marker_checks=42460,soil_noninitial_kappa_monotonic_checks=105000,noninitial_signed_intervals=21,conductivity_model_metadata_checks=22,soil_conductivity_J_law_checks=110000)
        base.need(all(d[k]==v for k,v in expected.items()),'Original22/all-ID/ledger/clock coverage differs')
        for k in ['qualified_PRE_read_by_current_helper','all22_arrays_finite_and_original_ID_aligned','actual_scalar_clock_verified','actual_metadata_counted_before_export_headers','original_case_registry_unchanged','only_declared_fixed_ID_retirement_allowed','p0_fixed_initial_material_baseline','saved_FS23_soil_pressure_nonpositive']:base.need(d[k],'Original native safety missing: '+k)
        base.need(d['source_material_law_version']==2 and d['source_PRE_completed_step']==380 and d['max_scalar_clock_error_s']<=1e-14 and d['max_noninitial_signed_dterror_s']<=1e-14 and all(n>0 for n in d['saved_FS23_soil_checks_by_part']) and sum(d['saved_FS23_soil_checks_by_part'])==d['saved_FS23_soil_checks'],'Typed PRE/actual clock/signed/trueFS checks differ');pre=DATA/d['certified_pre_filename'];bind(base.stat(pre));base.need(all(base.stat(e['path'])==e for e in frozen),'Consumed binding changed')
        result.update(passed=True,source_run=base.stat(RUN),reader_build=base.stat(BUILD),native_completion=base.stat(OUT/'completion.json'),actual_completion=d,qualified_elastic_PRE_verified=True,certified_pre_file=base.stat(pre),original_native_guards_passed=True,files=[base.stat(p) for p in sorted(OUT.iterdir()) if p.is_file()],consumed_stats=frozen,consumed_stats_unchanged=True)
    except Exception as e:result.update(first_failure=str(e),consumed_stats=frozen)
    base.save(CHECK,result);print(json.dumps(result),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
