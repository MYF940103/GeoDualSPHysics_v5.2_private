"""One root-admitted ReleasedSubstages GPU window; no automatic reader or next solver."""
import argparse,csv,json,os,shutil,struct,subprocess
from pathlib import Path
import psutil
import upl_c08_stage_ponding_smoke_r2 as smoke
import upl_c08_asn3_window_r1 as n3

T,C,L,PRE,base=smoke.T,smoke.C,smoke.L,smoke.PRE,smoke.base
need,read,stat,bind,save,verify=smoke.need,smoke.read,smoke.stat,smoke.bind,smoke.save,smoke.verify
TAG='upl_c08_stage_ponding_window_GPU_r1';SOURCE=4000000;UPDATES=264000;FRAMES=66;CADENCE=4000
OLD='upl_c08_asn3_window_GPU_r1';DEF=T/'configs'/(OLD+'_Def.xml');SEED=T/'outputs'/OLD/(OLD+'.xml');THREAD=n3.THREAD;CODEX=n3.CODEX
ROLES=('cpu_smoke_native','gpu_debug_smoke_native','gpu_release_smoke_native','gpu_debug_trace','gpu_release_trace')

def short_gates(ad):
    entries=[];runs={};adopt=bind(ad['cpu_adoption']);need(Path(adopt['path']).samefile(L/'upl_c08_stage_ponding_CPU_adopt_r1.json'),'Literal CPU adoption required');a=read(adopt['path'])
    need(a['passed'] and a['offline_adoption_only'] and a['actual_exit']==a['actual_Win32_exit']==0 and a['solver_invocations']==0 and a['original_solver_invocations']==1 and a['consumed_stats_unchanged'],'Closed CPU solver-success/log-postcheck adoption required');entries.append(adopt)
    for role,conf in zip(ROLES[:3],('DebugCPU','Debug','Release')):
        ne=bind(ad[role]);n=read(ne['path']);need(n['passed'] and n['configuration']==conf and n['original_native_guards_passed'] and n['consumed_stats_unchanged'] and n['decoder_invocations']==1,'Actual original smoke native guards required: '+role)
        re=bind(n['source_run']);r=read(re['path']);need(r['passed'] and r['actual_exit']==r['actual_Win32_exit']==0 and r['actual_steps']==4000800 and r['saved_frames']==2 and r['consumed_stats_unchanged'],'Closed actual800-update/two-frame smoke required')
        if conf=='DebugCPU':need(re==adopt,'CPU native must consume the explicit adoption')
        if conf=='Debug':need(r['memcheck_zero_errors_and_leaks'],'Closed GPU Debug memcheck0 required')
        ce,me=bind(n['completion']),bind(n['metadata']);d,m=read(ce['path']),read(me['path'])
        need(d['passed'] and d['samples']==2 and d['typed_arrays']==22 and d['actual_native_IDs_per_frame']==6805 and d['soil_IDs']==5000 and d['completed_steps']==4000800,'Literal original smoke native coverage required')
        need(m['passed'] and m['FreeSeepagePondingPolicy']=='ReleasedSubstages' and m['FreeSeepagePondingActive'] and m['samples']==m['ponding_policy_active_headers']==2 and m['AS_coefficient_float_reference']==struct.unpack('<f',struct.pack('<f',.2))[0] and m['AS_exponent_float_reference']==3.,'Actual typed ReleasedSubstages/AS metadata required')
        need(r['source_pre_file']==stat(PRE) and Path(r['source_capture']['path']).samefile(T/'outputs/upl_c08_stage_ponding_source_r2/source.json'),'Same original PRE/new source_r2 smoke required')
        entries.extend((ne,re,ce,me));runs[conf]=r
    for role,conf in zip(ROLES[3:],('Debug','Release')):
        qe=bind(ad[role]);q=read(qe['path']);need(q['passed'] and q['profile']=='smoke2ms' and q['CSV_consistency_checked'] and q['released_half_projection_checked'] and q['half_projection_preserves_saved_old_step_base'],'Strict original2ms half-mask/update/p_n trace review required')
        need(bind(q['trace'])==bind(runs[conf]['trace_file']),'Smoke trace must be the actually checked run file');entries.extend((qe,q['trace']))
    for leaf in (OLD+'.run.json',OLD+'.native_r1.json','upl_c08_stage_trace_asn3_window_r1.check.json'):
        p=L/leaf;r=read(p);need(r['passed'],'Closed n3 comparator required');entries.append(stat(p))
    return entries,runs['Release']['program']

def check_input(path,generated=False):
    actual=base.ET.parse(path).getroot();expected=base.ET.parse(SEED if generated else DEF).getroot()
    if generated:
        names={OLD+'_hdp_Actual.vtk':TAG+'_hdp_Actual.vtk',OLD+'__Actual.vtk':TAG+'__Actual.vtk'};nodes=expected.findall('execution/vtkout/vtkfile');need(len(nodes)==2 and {q.get('name') for q in nodes}==set(names),'Exactly two original generated VTK labels required')
        for q in nodes:q.set('name',names[q.get('name')])
        actual.attrib.pop('date',None);expected.attrib.pop('date',None)
    need(n3.signature(actual)==n3.signature(expected),'Whole n3 input must remain literal except exact generated labels/date; no physical or clock changes')
    event=actual.find('execution/special/gravitypreload');need(Path(event.get('statefile','')).is_absolute() and Path(event.get('statefile')).samefile(PRE),'Original absolute r2 GPU PRE required')

def notify_once(receipt):
    need(not any((L/(TAG+s)).exists() for s in ('.queue_attempt.json','.queue_result.json')),'Existing terminal queue attempt protected; never resend')
    message=('The one admitted C08 ReleasedSubstages GPU .66s window is terminal. Read '+str(receipt)+' and original start/call/status/owner_admission/root admission; verify actual owned PID/creation/exe/argv/parent, Popen and native Win32 exits, frozen Release_r2/source_r2/PRE/input bindings. This is264000 new updates/global4264000 with66 saves, same n3 AS epsilon.2/exponent3/Cubic hdp1.2 and original r2 GPU10s PRE. The candidate changes only released half positive free-surface pressure timing. Startup text precedes gravity configuration and does not prove policy OFF; actual typed ReleasedSubstages metadata plus genuine half PONDING/update/p_n trace checks are required. Preserve negative pressure and original22/P0/J/ledger/FS/keep5/plane/clock/signed guards. Check for existing/active readers before any separately authorized unique66-frame reader; do not call the old completed-only adapter/checker or skip the saved p_n base check. Expected trace includes half events (about540003 rows); count actual rows in one pass without rewriting. On failure preserve first actual error/partials and do not invent unsaved native time. Do not rearm this owner. This owner starts no further solver: root decides the next stage after independent native and physical review under the continuing user authorization. No automatic reader/VTK/other psi/PRE solve/half chain. Normal exit is not physical acceptance. One45s terminal queue attempt only; timeout delivery is uncertain, never resend or add a watcher.')
    argv=[str(CODEX),'queue','--thread',THREAD,'--message',message];save(L/(TAG+'.queue_attempt.json'),dict(stage=TAG,utc=base.utc(),thread=THREAD,run=stat(receipt),arguments=argv,attempts=1,timeout_s=45,do_not_resend=True));result=dict(stage=TAG,attempts=1,do_not_resend=True)
    try:
        q=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW);result.update(actual_exit=q.returncode,status='queued' if q.returncode==0 else 'queue_failed',stdout=q.stdout,stderr=q.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(L/(TAG+'.queue_result.json'),result)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');ap.add_argument('--notify',action='store_true');args=ap.parse_args();need(args.execution_authorized,'Root full-read and explicit independent single-window admission required')
    need(not args.notify or (os.environ.get('CODEX_THREAD_ID')==THREAD and CODEX.is_file()),'Only explicitly root-started same-thread terminal queue is allowed')
    out=T/'outputs'/TAG;config=T/'configs'/(TAG+'_Def.xml');rp=L/(TAG+'.run.json');rootad=L/(TAG+'.admission.json');bp=L/'upl_c08_stage_ponding_Release_r2.build.json'
    need(not out.exists() and not config.exists() and not any(p.name!=rootad.name for p in L.glob(TAG+'.*')),'Existing complete/partial job protected; no retry')
    before=[];result=dict(stage=TAG,passed=False,configuration='Release',physical_acceptance=False,solver_invocations=0,reader_invocations=0,queue_invocations_at_run_seal=0,terminal_queue_requested=args.notify,SHA_scans=0,native_review_pending=True,free_seepage_policy='ReleasedSubstages',keep_bed_overlap=True,expected_active_native_IDs=6805,ArtificialStress=True,ArtificialStressCoef=.2,ArtificialStressExp=3.,policy=base.POLICY,startup_policy_proves_released_substages=False,released_policy_native_and_trace_review_pending=True)
    try:
        ad=read(rootad);need(ad['passed'] and ad['allowed_job']==TAG and ad['FreeSeepagePondingPolicy']=='ReleasedSubstages' and ad['ArtificialStressCoef']==.2 and ad['ArtificialStressExp']==3.,'Explicit one-job ReleasedSubstages admission required');gates,smoked_program=short_gates(ad)
        b=read(bp);need(b['passed'] and b['configuration']=='Release' and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and b['canonical_runtime_PRE_unchanged'] and len(b['project_objects'])==113 and b['trace_macro_enabled'] and b['trace_macro']=='C08_STAGE_TRACE' and b['environment_macro']['appended']=={'CL':'/DC08_STAGE_TRACE','NVCC_PREPEND_FLAGS':'-DC08_STAGE_TRACE'},'Closed new macro-enabled Release_r2 build required')
        need(Path(b['source_capture']['path']).samefile(T/'outputs/upl_c08_stage_ponding_source_r2/source.json') and bind(b['program'])==smoked_program,'Same actually smoke-checked Release_r2/source_r2 program required');program=Path(b['program']['path'])
        helpers={Path(base.__file__),Path(base.evidence.__file__),Path(base.summary.__code__.co_filename),Path(smoke.__file__),Path(n3.__file__),Path(n3.control.__file__),Path(n3.previous.__file__),Path(n3.smoke.__file__),Path(n3.repair.__file__),Path(n3.trace.__file__)}
        before=[stat(p) for p in (Path(__file__),T/'notes/upl_c08_stage_ponding_window_r1.md',T/'configs/xCaseLianSaturatedColumnCollapse_stage_ponding_window_r1_win64_GPU.bat',DEF,SEED,bp,rootad,PRE,PRE.parent/'Part_Head.ibi4',*sorted(helpers))]+gates+[bind(b[k]) for k in ('program','source_capture','source_archive')];runtime=[]
        for leaf in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll'):
            origin=C/'support/runtime_r5'/leaf;e=stat(origin);dest=program.parent/leaf
            if not dest.exists():shutil.copy2(origin,dest)
            d=stat(dest);need((d['bytes'],d['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Existing/new known runtime copy differs');before.extend((e,d));runtime.append(d)
        for proc in psutil.process_iter(['exe','cmdline']):
            try:need(not(proc.info['exe'] and Path(proc.info['exe']).name.lower().startswith('dualsphysics') and any(x.lower().startswith('-gpu') for x in (proc.info['cmdline'] or [])[1:])),'GPU physical solver active; no process stopped')
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        with config.open('xb') as f:f.write(DEF.read_bytes())
        check_input(config);before.append(stat(config));gen=C/'support/runtime_r5/GenCase_win64.exe';before.append(stat(gen));prefix=out/TAG;result['GenCase_call']=base.invoke(TAG+'.gencase',[str(gen),str(config.with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml');check_input(seed,True);before.extend(stat(Path(str(prefix)+s)) for s in ('.xml','.bi4','_Normals.nbi4'));plan=out/'planned_steps.csv'
        with plan.open('x',encoding='utf8',newline='') as f:w=csv.writer(f);w.writerow(('part','completed_step'));w.writerows((i,SOURCE+(i+1)*CADENCE) for i in range(FRAMES))
        before.append(stat(plan));argv=[str(program),'-gpu:0','-stable','-mdbc_freeslip:1',str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:'+str(SOURCE+UPDATES)];adpath=L/(TAG+'.owner_admission.json')
        save(adpath,dict(stage=TAG,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(rootad),program=stat(program),source_build=stat(bp),source_pre_file=stat(PRE),planned_steps=stat(plan),planned_new_updates=UPDATES,planned_global_end=SOURCE+UPDATES,expected_saved_frames=FRAMES,argv=argv,solver_argv=argv,consumed=before))
        result['solver_invocations']=1;result['actual_call']=base.owned(TAG,argv,program,False,stat(adpath));result.update(n3.normal_output(out));need('Gpu_' in result['summary']['Hardware'],'Actual GPU backend required');verify(before)
        result.update(passed=True,actual_exit=0,actual_Win32_exit=0,program=stat(program),source_build=stat(bp),source_capture=b['source_capture'],input_xml=stat(seed),source_pre_file=stat(PRE),planned_steps=stat(plan),runtime=runtime,consumed_stats_unchanged=True,expected_trace_base_rows_without_extra_events=540000)
    except Exception as error:
        result['first_failure']=str(error);cp=L/(TAG+'.call.json')
        if cp.exists():
            call=read(cp);result.update(actual_call=stat(cp),actual_exit=call['actual_solver_Win32_exit'],actual_Win32_exit=call['actual_solver_Win32_exit'],actual_tool_exit=call['actual_Popen_wait_exit'],ownership_errors=call['ownership_errors'])
    result.update(consumed=before,last_original_console_line=base.last_part(out));save(rp,result);base.publish(TAG,out,None,None,'completed_pending_native' if result['passed'] else 'failed_preserved_pending_diagnosis')
    if args.notify and result['solver_invocations']:notify_once(rp)
    print(json.dumps(dict(passed=result['passed'],receipt=str(rp),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
