"""One admitted fresh same-runtime hdp1.2 .52s elastic-source control; no PRE certification or postprocessing."""
import argparse,json,os,re,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import upl_c08_bedkeep_run_r1 as base
from upl_c08_hdp15_preload_r1 import signature,verify
T,C,L=base.T,base.C,base.L;need,read,stat,bind,save,invoke=base.need,base.read,base.stat,base.bind,base.save,base.invoke
TAG='upl_c08_hdp12_preload_control_GPU_r1';OUT=T/'outputs'/TAG;CONFIG=T/'configs'/(TAG+'_Def.xml');BAT=T/'configs'/('x'+TAG+'_win64_GPU.bat')
NOTE=T/'notes/upl_c08_hdp12_preload_control_r1.md';ROOT=C/'CaseLianSaturatedColumnCollapse_shared_preload_r3_Def.xml';RUNTIME=C/'support/runtime_r6'
AD=L/(TAG+'.admission.json');RUN=L/(TAG+'.run.json');END=208000;FRAMES=53;THREAD='01a07683-bc64-7463-8db7-9ee6243967d8'
CODEX=Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1021.22027-win32-x64/bin/windows-x86_64/codex.exe')

def check_input(path,generated=False):
    expected=ET.parse(ROOT).getroot();actual=ET.parse(path).getroot();need(expected.find('casedef/constantsdef/hdp').get('value')=='1.2','Root source hdp changed')
    if generated:
        need(all(signature(actual.find(q))==signature(expected.find(q)) for q in ('execution/special','execution/parameters')),'Generated source physical sections differ');constants=actual.find('execution/constants');need(float(constants.find('h').get('value'))==.048 and float(constants.find('dp').get('value'))==.04,'Generated h/dp differs')
    else:need(signature(actual)==signature(expected),'Control may change only comments; all root source numbers remain literal')
    p={q.get('key'):q.get('value') for q in actual.findall('execution/parameters/parameter')};event=actual.find('execution/special/gravitypreload')
    need(float(p.get('NoPenetration','0'))==float(p.get('ArtificialStress','0'))==0 and event.get('elastic_source')=='true' and float(event.get('time'))==10 and not event.get('statefile') and event.get('keep_bed_overlap','false')=='false','Fresh strict-elastic source only; no import/release/AS/NoPen')

def context(notify):
    ad=read(AD);need(ad['passed'] and ad['allowed_job']==TAG and ad['hdp']==1.2 and ad['planned_global_end']==END and ad['expected_saved_frames']==FRAMES,'Root explicit one-control admission required');thread=os.environ.get('CODEX_THREAD_ID')
    need(not notify or (ad['root_thread_id']==THREAD and thread in (None,'',THREAD) and CODEX.is_file()),'Only this admitted same root thread may receive one terminal queue')
    rp=L/'upl_c08_formal_psi0_r6_r1.run.json';r=read(rp);need(r['passed'] and r['solver_completed'] and r['postprocess_completed'],'Closed official r6 provenance required');bp=Path(bind(r['source_build'])['path']);b=read(bp);program=RUNTIME/'DualSPHysics5.2_GEO_win64.exe'
    need(b['passed'] and b['configuration']=='Release' and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and bind(r['program'])==stat(program) and (stat(program)['bytes'],stat(program)['mtime_ns'])==(b['program']['bytes'],b['program']['mtime_ns']),'Same frozen runtime_r6 law2 program required')
    install=L/'upl_c08_formal_r6_runtime_r1.json';ri=read(install);need(ri['passed'],'Closed r6 runtime installation required');dest={Path(q['destination']['path']).name:q['destination'] for q in ri['files']}
    runtime=[bind(dest[k]) for k in ('DualSPHysics5.2_GEO_win64.exe','GenCase_win64.exe','DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll')]
    before=[stat(p) for p in (Path(__file__),NOTE,CONFIG,BAT,ROOT,AD,rp,bp,install,Path(base.__file__),Path(base.evidence.__file__),Path(base.summary.__code__.co_filename),Path(signature.__code__.co_filename))]+runtime+[bind(b[k]) for k in ('source_capture','source_archive')];check_input(CONFIG);verify(before)
    for q in psutil.process_iter(['exe','cmdline']):
        try:need(not(q.info['exe'] and Path(q.info['exe']).name.lower().startswith('dualsphysics') and any(v.lower().startswith('-gpu') for v in (q.info['cmdline'] or [])[1:])),'GPU physical target active; no process stopped')
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    return b,bp,program,before,thread

def output_checks():
    r=base.summary(OUT/'Run.csv');text=(OUT/'Run.out').read_text(encoding='utf-8-sig');parts=sorted((OUT/'data').glob('Part_*.bi4'))
    need(int(r['Steps'])==END and int(r['PartFiles'])==FRAMES and int(r['Np'])==7060 and int(r['Nfixed'])==int(r['Nbound'])==2060 and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')) and 'Gpu_' in r['Hardware'] and float(r['Dp'])==.04 and float(r['H'])==.048,'Actual .52s GPU control schedule/registry/h/no-exclusion differs')
    need('Finished execution (code=0).' in text and 'GravityPreload: requested=10 event_completed_step=4000000 release_mkbound=2;' in text and 'GravityPreload: phase=released' not in text and 'GravityPreload: state imported' not in text,'Bounded source must stop before PRE/release/import')
    need('No Penetration=False' in text and 'ArtificialStress="None"' in text and 'SoilDamping="BuiFukagawa2013"' in text and 'SoilDampingCoef=0.02' in text and 'PoreShepardRegularization="Enabled"' in text and 'PoreShepardInterval: 40' in text,'Actual unchanged source controls differ');need([p.name for p in parts]==['Part_%04d.bi4'%i for i in range(FRAMES)],'Actual53 contiguous PARTs required')
    return dict(actual_steps=END,saved_frames=FRAMES,Run_csv=stat(OUT/'Run.csv'),Run_out=stat(OUT/'Run.out'),PARTs=[stat(p) for p in parts],physical_time_Run_csv_rounded_text=r['PhysicalTime'],Hardware=r['Hardware'])

def queue_once():
    attempt=L/(TAG+'.queue_attempt.json');reply=L/(TAG+'.queue_result.json');need(not attempt.exists() and not reply.exists(),'Existing terminal queue protected; never resend')
    message=('The one authorized C08 same-runtime hdp1.2 .52s control is terminal: '+str(RUN)+'. Read original run/start/call/status/owner_admission/root admission; verify owned creation/exe/argv/parent and real Popen/Win32 exits, frozen runtime_r6 law2/source/input stats. This is fresh sigma0/ConstantZ, dt2.5us,208000updates/53 planned PARTs, elastic_source strict, AS/NoPen off, damping.02/Shepard40. It is not a10s PRE, certified handoff, equilibrium or physical acceptance. On failure retain first actual exception/partial/last original console PART and do not invent an unsaved failure time or restart. Before any independently authorized unified partial reader, check existing/active readers; native22/IDs/P0/J/kappa/FS/clocks remain pending. No automatic decode/VTK/nextsolver/otherpsi/PRE/half chain. Root decides later work under continuing authorization. One45s same-thread queue attempt only; timeout delivery is uncertain, never resend/rearm/add watcher.')
    argv=[str(CODEX),'queue','--thread',THREAD,'--message',message];save(attempt,dict(stage=TAG,utc=base.utc(),thread=THREAD,run=stat(RUN),arguments=argv,attempts=1,timeout_s=45,do_not_resend=True));result=dict(stage=TAG,attempts=1,do_not_resend=True)
    try:
        p=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW);result.update(actual_exit=p.returncode,status='queued' if p.returncode==0 else 'queue_failed',stdout=p.stdout,stderr=p.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(reply,result)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');ap.add_argument('--notify',action='store_true');a=ap.parse_args();need(a.execution_authorized and AD.is_file(),'Root full-read and explicit admission required')
    need(not OUT.exists() and not any(p.name!=AD.name for p in L.glob(TAG+'.*')),'Existing owner/output/partial protected');claim=L/(TAG+'.claim.json');save(claim,dict(stage=TAG,owner_pid=os.getpid(),owner_created_epoch=psutil.Process().create_time(),single_attempt=True));before=[];stage='preflight'
    result=dict(stage=TAG,passed=False,solver_completed=False,normal_exit_meaning=None,certified_PRE=False,equilibrium_acceptance=False,physical_acceptance=False,native_review_pending=True,source_material_law_version_expected=2,source_material_law_version_native_observed=False,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,PartVTK_invocations=0,queue_invocations_at_run_seal=0,SHA_scans=0)
    try:
        b,bp,program,before,thread=context(a.notify);before.append(stat(claim));OUT.mkdir();prefix=OUT/TAG;stage='GenCase';result['GenCase_invocations']=1;result['GenCase_call']=invoke(TAG+'.gencase',[str(RUNTIME/'GenCase_win64.exe'),str(CONFIG.with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml');check_input(seed,True);seed_entries=[stat(Path(str(prefix)+s)) for s in ('.xml','.bi4','_Normals.nbi4')];before+=seed_entries;verify(before);argv=[str(program),'-gpu:0','-stable','-mdbc_freeslip',str(prefix),str(OUT),'-dirdataout','data','-svres','-nsteps:'+str(END)]
        ad=L/(TAG+'.owner_admission.json');save(ad,dict(stage=TAG,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(AD),actual_environment_thread=thread,notification_thread=THREAD if a.notify else None,program=stat(program),source_build=stat(bp),source_capture=b['source_capture'],source_archive=b['source_archive'],input_xml=stat(seed),seed=seed_entries,planned_global_end=END,expected_saved_frames=FRAMES,argv=argv,solver_argv=argv,consumed=before));before.append(stat(ad))
        result.update(program=stat(program),source_build=stat(bp),source_capture=b['source_capture'],source_archive=b['source_archive'],input_xml=stat(seed),seed=seed_entries,argv=argv,owner_admission=stat(ad),hdp=1.2,expected_native_H=0.04800000041723251)
        stage='solver';result['solver_invocations']=1;result['actual_call']=base.owned(TAG,argv,program,False,stat(ad));result.update(solver_completed=True,actual_exit=0,actual_Win32_exit=0);stage='solver_output_review';result.update(output_checks());verify(before);result.update(passed=True,normal_exit_meaning='bounded_control_completed',consumed_stats_unchanged=True)
    except Exception as error:
        result.update(first_failure=str(error),failed_stage=stage);cp=L/(TAG+'.call.json')
        if cp.exists():
            call=read(cp);result.update(actual_call=stat(cp),actual_exit=call['actual_solver_Win32_exit'],actual_Win32_exit=call['actual_solver_Win32_exit'],actual_tool_exit=call['actual_Popen_wait_exit'],ownership_errors=call['ownership_errors'])
        log=OUT/'Run.out'
        if log.exists():
            match=re.search(r'^Text: (.+)$',log.read_text(encoding='utf-8-sig'),re.M);result['first_engine_exception_text']=match[1] if match else None;result['Run_out']=stat(log)
    parts=sorted((OUT/'data').glob('Part_*.bi4'));result.update(consumed=before,consumed_stats_unchanged=bool(before) and all(Path(e['path']).is_file() and stat(e['path'])==e for e in before),PARTs_on_disk=[stat(p) for p in parts],PART_files_on_disk=len(parts),last_original_console_line=base.last_part(OUT),unsaved_failure_time_known=False)
    try:base.publish(TAG,OUT,None,None,'bounded_control_completed_pending_native' if result['passed'] else 'failed_preserved_pending_diagnosis')
    except Exception as error:result['terminal_status_error']=str(error)
    save(RUN,result)
    if a.notify and (L/(TAG+'.call.json')).exists():queue_once()
    print(json.dumps(dict(passed=result['passed'],run=str(RUN),solver_completed=result['solver_completed'],first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
