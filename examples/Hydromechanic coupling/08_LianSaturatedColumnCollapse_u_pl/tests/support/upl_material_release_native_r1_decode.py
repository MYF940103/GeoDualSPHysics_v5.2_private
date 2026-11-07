"""Exactly one already-completed new-program decode; does not run a solver or chain reviews."""
import ctypes,datetime,json,subprocess,sys,time
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];L=T/'logs';TAG='upl_material_release_native_r1'
def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text())
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')
need(len(sys.argv)==4 and sys.argv[1] in ('source','alias0','receive_old','receive_new','fluid','plastic') and sys.argv[2] in ('CPU','GPU') and sys.argv[3]=='--execution-authorized','Use PROFILE CPU|GPU --execution-authorized')
mode,backend=sys.argv[1:3];tag=TAG+'_'+mode+'_'+backend;OUT=T/'outputs'/(tag+'_native');DATA=T/'outputs'/tag/'data';RUN=L/(tag+'.run.json');BUILD=L/(TAG+'.build.json');CHECK=L/(tag+'.native.check.json');START=L/(tag+'.native.start.json');CALL=L/(tag+'.native.call.json');LOG=L/(tag+'.native.log')
need(not any(p.exists() for p in (OUT,CHECK,START,CALL,LOG)),'Existing/partial decode protected; inspect rather than rerun')
before={};result=dict(stage=tag+'.native',passed=False,decoder_invocations=0,solver_invocations=0,SHA_scans=0,physical_acceptance=False)
def bind(e):
    a=stat(e['path']);need((a['bytes'],a['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Consumed binding changed: '+e['path']);before[a['path']]=a;return a
K=ctypes.WinDLL('kernel32',use_last_error=True);K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];K.GetExitCodeProcess.restype=w.BOOL
try:
    r,b=read(RUN),read(BUILD);steps=4 if mode=='fluid' else 256 if mode=='plastic' else 800
    need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==steps and r['consumed_stats_unchanged'],'Original matching solver run did not pass')
    need(b['passed'] and b['consumed_stats_unchanged'] and len(b['objects'])==85,'New current-ABI reader build required')
    bind(stat(RUN));bind(stat(BUILD));bind(stat(__file__))
    for e in r['consumed']:bind(e)
    for key in ('program','source_build','source_capture','source_archive','start_record','actual_call'):bind(r[key])
    call=read(r['actual_call']['path']);need(call['actual_Popen_wait_exit']==call['actual_tool_Win32_exit']==call['actual_solver_Win32_exit']==0 and call['typed_returncode_captured_first'] and not call['ownership_errors'],'Actual solver exits/ownership differ')
    need(Path(call['solver']['exe']).samefile(r['program']['path']) and call['solver']['argv'][1:]==call['target_argv'][1:],'Original exact program/argv binding differs')
    for key in ('program','source','source_build'):bind(b[key])
    for e in b['runtime']:bind(e)
    exe=Path(b['program']['path']);need(exe.samefile(T/'outputs'/TAG/(TAG+'.exe')),'Unexpected new reader program')
    need(not any((q.info['name'] or '').lower()==exe.name.lower() for q in psutil.process_iter(['name'])),'This reader is already active; do not duplicate')
    parts=sorted(DATA.glob('Part_*.bi4'));need(len(parts)==r['saved_frames'] and [p.name for p in parts]==['Part_%04d.bi4'%i for i in range(len(parts))],'Actual native membership differs')
    for p in DATA.iterdir():
        if p.is_file():bind(stat(p))
    bind(stat(T/'outputs/upl_c08_global_CPU_r1/ids.csv'));bind(stat(T/'support/upl_material_periodic_shear_r1_velocity.csv'))
    PRE='-'
    if mode.startswith('receive'):PRE=bind(r['source_pre_file'])['path']
    argv=[str(exe),'--read',mode,backend,str(DATA),str(PRE),str(OUT)];owner=psutil.Process();oid=dict(pid=owner.pid,created_epoch=owner.create_time(),exe=owner.exe(),argv=owner.cmdline());started=datetime.datetime.now(datetime.timezone.utc).isoformat();wall=time.monotonic();errors=[]
    with LOG.open('xb') as f:
        p=subprocess.Popen(argv,cwd=T.parent,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);result['decoder_invocations']=1;child=dict(pid=p.pid)
        try:
            q=psutil.Process(p.pid);child=dict(pid=p.pid,created_epoch=q.create_time(),exe=q.exe(),argv=q.cmdline(),parent_pid=q.ppid());need(Path(child['exe']).samefile(exe) and child['argv'][1:]==argv[1:] and child['parent_pid']==oid['pid'],'Actual decoder ownership differs')
            save(START,dict(stage=tag+'.native.start',owner=oid,child=child,argv=argv,reader_build=stat(BUILD),source_run=stat(RUN)))
        except Exception as e:errors.append(str(e))
        rc=p.wait();code=w.DWORD();got=bool(K.GetExitCodeProcess(int(p._handle),ctypes.byref(code)))
    save(CALL,dict(stage=tag+'.native.call',owner=oid,child=child,argv=argv,actual_Popen_wait_exit=rc,actual_Win32_exit=code.value if got else None,ownership_errors=errors,typed_returncode_captured_first=type(rc) is int,started_utc=started,ended_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_s=time.monotonic()-wall,log=stat(LOG)))
    result.update(reader_call=stat(CALL),actual_Popen_wait_exit=rc,actual_Win32_exit=code.value if got else None);need(got and rc==code.value==0 and not errors,'Actual native decode/ownership failed; no retry')
    d=read(OUT/'completion.json');need(d['passed'] and d['input_run_tag']==tag and d['completed_steps']==steps and d['samples']==r['saved_frames'] and d['physical_acceptance'] is False,'Native completion identity/count differs')
    need(d['actual_scalar_clock_verified'] and d['max_noninitial_signed_dterror_s']<=1e-14,'Original native actual-clock/signed safety failed')
    if mode in ('source','alias0','receive_old','receive_new'):
        need(d['stage']==TAG and d['typed_arrays']==22 and d['typed_bytes_per_particle']==212 and d['all22_arrays_finite_and_original_ID_aligned'] and d['max_scalar_clock_error_s']<=1e-14,'Gravity original 22-array/clock guard differs')
        counts=d['phase_saved_frames'];n=r['saved_frames'];expected=dict(original_case_ID_domain=7060,soil_IDs=5000,original_fixed_IDs=2060,soil_ledger_checks=5000*n,soil_cache_float_bits_checks=5000*n,all_present_ID_p0_float_bits_checks=7060*counts[0]+6800*counts[1],fixed_marker_checks=2060*counts[0]+1800*counts[1],soil_noninitial_kappa_monotonic_checks=5000*(n-1),noninitial_signed_intervals=n-(mode in ('source','alias0')),conductivity_model_metadata_checks=n,soil_conductivity_J_law_checks=5000*n)
        need(all(d[k]==v for k,v in expected.items()) and d['qualified_PRE_read_by_current_helper'] and d['source_PRE_completed_step']==380 and d['event_completed_step']==380 and d['retired_native_count']==260,'Gravity all-ID/ledger/certification coverage differs')
        need(d['source_material_law_version']==(1 if mode=='receive_old' else 2) and all(x>0 for x in d['saved_FS23_soil_checks_by_part']) and sum(d['saved_FS23_soil_checks_by_part'])==d['saved_FS23_soil_checks'],'Typed material source/true free-seepage coverage differs')
        certified=DATA/d['certified_pre_filename'] if mode in ('source','alias0') else Path(PRE);bind(stat(certified));result.update(qualified_elastic_PRE_verified=True,certified_pre_file=stat(certified))
    elif mode=='plastic':
        need(d['stage']==TAG+'_plastic' and d['typed_arrays']==22 and d['total_native_IDs']==1024 and d['samples']==5 and d['ledger_checks']==5120 and d['native_Rhop_float_cache_checks']==5120 and d['noninitial_kappa_monotonic_ID_checks']==4096 and d['final_kappa_nonzero_IDs']>0 and d['max_kappa']>0 and d['all22_arrays_finite_and_ID_aligned'],'Actual plastic/ledger/22-array witness failed')
    else:need(d['stage']==TAG+'_fluid' and d['typed_subset_arrays']==7 and d['native_IDs']==1024 and d['native_finite_zero_kappa_checks']==1024*d['samples'] and d['soil_version_metadata_absent'] and not d['full_22_array_schema_claimed'],'Pure-fluid independent subset witness failed')
    need(all(stat(p)==e for p,e in before.items()),'Consumed binding changed during native decode')
    result.update(passed=True,source_run=stat(RUN),reader_build=stat(BUILD),native_completion=stat(OUT/'completion.json'),actual_completion=d,original_native_guards_passed=True,files=[stat(p) for p in sorted(OUT.iterdir()) if p.is_file()],consumed_stats=list(before.values()),consumed_stats_unchanged=True)
except Exception as e:result.update(first_failure=str(e),consumed_stats=list(before.values()))
save(CHECK,result);print(json.dumps(dict(passed=result['passed'],check=str(CHECK),decoder_invocations=result['decoder_invocations'],first_failure=result.get('first_failure'))),flush=True);raise SystemExit(0 if result['passed'] else 1)
