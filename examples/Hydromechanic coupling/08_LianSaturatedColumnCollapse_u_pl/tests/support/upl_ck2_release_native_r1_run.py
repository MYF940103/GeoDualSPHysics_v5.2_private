"""One owned decode of the closed Ck2 combined release; no solver, retry or queue."""
import ctypes,datetime,json,subprocess,sys,time
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];L=T/'logs'
def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2);f.write('\n')
need(len(sys.argv)==2 and sys.argv[1] in ('CPU','GPU'),'Use CPU|GPU')
window='on';backend=sys.argv[1];tag='upl_ck2_release_short_'+backend+'_r1';steps=800
OWNER=L/(tag+'.run.json');BUILD=L/'upl_ck2_release_native_r1.build.json';OUT=T/'outputs'/(tag+'_native_r1');DATA=T/'outputs'/tag/'data'
CALL=L/(tag+'_native_r1.call.json');START=L/(tag+'_native_r1.start.json');CHECK=L/(tag+'_native_r1.check.json');LOG=L/(tag+'_native_r1.log')
need(not any(p.exists() for p in (OUT,CALL,START,CHECK,LOG)),'Existing/partial decode artifacts protected; inspect them instead of retrying')
before={};result=dict(stage=tag+'_native_r1',passed=False,decoder_invocations=0,solver_invocations=0,physical_acceptance=False,SHA_scans=0)
def bind(e):
    a=stat(e['path']);need((a['bytes'],a['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Closed consumed binding changed: '+e['path']);before[a['path']]=a;return a
K=ctypes.WinDLL('kernel32',use_last_error=True);K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];K.GetExitCodeProcess.restype=w.BOOL
try:
    r,b=read(OWNER),read(BUILD);need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==steps and r['consumed_stats_unchanged'],'Matching original owned run must be closed and passed')
    need(b['passed'] and b['consumed_stats_unchanged'] and len(b['objects'])==85,'Closed new DebugCPU85 reader build required')
    bind(stat(OWNER));bind(stat(BUILD));bind(stat(__file__))
    for e in r['consumed']:bind(e)
    for key in ('program','source_build','source_capture','source_archive','admission','start_record','actual_call'):bind(r[key])
    need(len(r['seed'])==3,'Exactly XML/BI4/normals seed bindings required')
    for e in r['seed']:bind(e)
    rb=read(r['source_build']['path']);need(rb['passed'] and rb['actual_typed_exit_code']==rb['actual_Win32_exit']==0 and rb['source_stats_unchanged'] and Path(rb['program']['path']).samefile(r['program']['path']),'Matching original program build is not closed')
    call=read(r['actual_call']['path']);need(call['actual_Popen_wait_exit']==call['actual_tool_Win32_exit']==call['actual_solver_Win32_exit']==0 and call['typed_returncode_captured_first'] is True,'Original actual solver exits are not typed0')
    need(Path(call['program']['path']).samefile(r['program']['path']) and Path(call['solver']['exe']).samefile(r['program']['path']) and call['solver']['argv'][1:]==call['target_argv'][1:] and call['solver']['created_epoch']>0 and call['solver']['parent_pid']>0,'Original actual solver identity/program/argv binding differs')
    for key in ('program','source','source_build'):bind(b[key])
    for e in b['runtime']:bind(e)
    exe=Path(b['program']['path']);need(exe.samefile(T/'outputs/upl_ck2_release_native_r1/upl_ck2_release_native_r1.exe'),'Unexpected reader executable')
    need(not any((q.info['name'] or '').lower()==exe.name.lower() for q in psutil.process_iter(['name'])),'An actual release native reader is already active; do not duplicate')
    need(DATA.is_dir(),'Completed raw data absent');parts=sorted(DATA.glob('Part_*.bi4'));need(len(parts)==r['saved_frames'] and [p.name for p in parts]==['Part_%04d.bi4'%i for i in range(len(parts))],'Actual Run/PART sequence differs')
    for p in DATA.iterdir():
        if p.is_file():bind(stat(p))
    bind(stat(T/'outputs/upl_c08_global_CPU_r1/ids.csv'))
    argv=[str(exe),'--read',window,backend,str(DATA),str(OUT)];owner=psutil.Process();ownerid=dict(pid=owner.pid,created_epoch=owner.create_time(),exe=owner.exe(),argv=owner.cmdline());started=datetime.datetime.now(datetime.timezone.utc).isoformat();wall=time.monotonic();observation_error=None
    with LOG.open('xb') as f:
        p=subprocess.Popen(argv,cwd=T.parent,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);result['decoder_invocations']=1;child=dict(pid=p.pid)
        try:
            q=psutil.Process(p.pid);child=dict(pid=p.pid,created_epoch=q.create_time(),exe=q.exe(),argv=q.cmdline(),parent_pid=q.ppid());need(Path(child['exe']).samefile(exe) and child['argv'][1:]==argv[1:] and child['parent_pid']==ownerid['pid'],'Actual reader child identity differs')
            save(START,dict(stage=tag+'_native_r1.start',owner=ownerid,child=child,argv=argv,reader_build=stat(BUILD),source_run=stat(OWNER),physical_acceptance=False));print(json.dumps(dict(actual_reader_started=child)),flush=True)
        except Exception as e:observation_error=str(e)
        rc=p.wait();code=w.DWORD();got=bool(K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)))
    save(CALL,dict(stage=tag+'_native_r1.call',owner=ownerid,child=child,argv=argv,actual_Popen_wait_exit=rc,actual_Win32_exit=code.value if got else None,typed_returncode_captured_first=type(rc) is int,identity_observation_failure=observation_error,started_utc=started,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_s=time.monotonic()-wall,log=stat(LOG),consumed_stats=list(before.values()),decoder_invocations=1,solver_invocations=0,SHA_scans=0))
    result.update(reader_call=stat(CALL),actual_Popen_wait_exit=rc,actual_Win32_exit=code.value if got else None);need(got and rc==code.value==0 and observation_error is None,'Actual decode/ownership failed; retain partial output and first cause, no retry')
    d=read(OUT/'completion.json');counts=d['phase_saved_frames'];samples=r['saved_frames'];need(d['passed'] and d['stage']=='upl_ck2_release_native_r1' and d['input_run_tag']==tag and d['window']==window and d['backend_argument']==backend and d['samples']==samples and d['completed_steps']==steps,'Actual native completion identity/counts differ')
    need(len(counts)==2 and sum(counts)==samples and counts[0]>0 and (counts[1]>0 if window=='on' else counts[1]==0) and d['phase1_export_written']==(window=='on'),'Actual phase coverage differs')
    expected=dict(original_case_ID_domain=7060,soil_IDs=5000,original_fixed_IDs=2060,typed_arrays=22,typed_bytes_per_particle=212,HydroMechConductivityModel=1,HydroMechConductivityCk=2,conductivity_model_metadata_checks=samples,soil_conductivity_J_law_checks=5000*samples,soil_ledger_checks=5000*samples,soil_cache_float_bits_checks=5000*samples,fixed_marker_checks=2060*counts[0]+1800*counts[1],all_present_ID_p0_float_bits_checks=7060*counts[0]+6800*counts[1],soil_noninitial_kappa_monotonic_checks=5000*(samples-1),noninitial_signed_intervals=samples-1,unplanned_or_fluid_exclusions=0)
    need(all(d[k]==v for k,v in expected.items()),'Original all-ID/22-array/ledger/cache/P0/kappa/signed-interval counts differ')
    for key in ('all22_arrays_finite_and_original_ID_aligned','actual_scalar_clock_verified','actual_metadata_counted_before_export_headers','original_case_registry_unchanged','only_declared_fixed_ID_retirement_allowed','initial_effective_stress_zero','p0_fixed_initial_material_baseline','saved_FS23_soil_pressure_nonpositive'):need(d[key],'Original native guard not passed: '+key)
    need(d['dt_s']==2.5e-6 and d['max_scalar_clock_error_s']<=1e-14 and d['max_noninitial_signed_dterror_s']<=1e-14 and len(d['saved_FS23_soil_checks_by_part'])==samples and all(n>0 for n in d['saved_FS23_soil_checks_by_part']) and sum(d['saved_FS23_soil_checks_by_part'])==d['saved_FS23_soil_checks'],'Original actual clock/signed/trueFS coverage differs')
    need(d['native_saved_steps_or_arrays_rewritten'] is False and d['physical_acceptance'] is False,'Native proof limits differ')
    if window=='on':need(d['event_completed_step']==380 and d['retired_native_begin']==1800 and d['retired_native_count']==260,'Actual event target differs')
    else:need(d['OFF_metadata_absence_checked'] and not (OUT/'phase1_typed22.bin').exists(),'Absent-object OFF created an actual phase1 export')
    need(all(stat(p)==e for p,e in before.items()),'Consumed closed run/source/runtime/seed/raw/reader binding changed')
    result.update(passed=True,source_run=stat(OWNER),source_run_call=r['actual_call'],source_build=r['source_build'],reader_build=stat(BUILD),native_completion=stat(OUT/'completion.json'),actual_completion=d,original_native_guards_passed=True,files=[stat(p) for p in sorted(OUT.iterdir()) if p.is_file()],consumed_stats=list(before.values()),consumed_stats_unchanged=True)
except Exception as e:result.update(first_failure=str(e),consumed_stats=list(before.values()))
save(CHECK,result);print(json.dumps(dict(passed=result['passed'],check=str(CHECK),decoder_invocations=result['decoder_invocations'],first_failure=result.get('first_failure'))),flush=True)
raise SystemExit(0 if result['passed'] else 1)
