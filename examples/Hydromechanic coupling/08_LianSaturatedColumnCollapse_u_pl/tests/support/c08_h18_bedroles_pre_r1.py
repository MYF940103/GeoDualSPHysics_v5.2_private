"""One fresh Cubic h/dp1.8 elastic10s source; no receiver, decoder, retry or next solver."""
import argparse, json, os, re, struct, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import upl_c08_bedkeep_run_r1 as base

T,C,L=base.T,base.C,base.L
need,read,stat,bind,save,invoke=base.need,base.read,base.stat,base.bind,base.save,base.invoke
TAG='c08_h18_bedroles_pre_r1'; OUT=T/'outputs'/TAG; CONFIG=T/'configs'/(TAG+'_Def.xml'); NOTE=T/'notes'/(TAG+'.md')
ROOT=C/'CaseLianSaturatedColumnCollapse_shared_preload_r3_Def.xml'; RUNTIME=C/'support/runtime_r6'
AD=L/(TAG+'.admission.json'); RUN=L/(TAG+'.run.json'); THREAD='01a07683-bc64-7463-8db7-9ee6243967d8'
CODEX=Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1021.22027-win32-x64/bin/windows-x86_64/codex.exe')
END=2000000; FRAMES=1001; DT=.000005; SELECTED=(0,100,500,1000)
VARS='-vars:-all,+idp,+mk,+vel,+rhop,+PorePress,+PorePress0,+ExcessPorePress,+SigmaState_kk,+SigmaState_ij,+Sigma_kk,+Sigma_ij,+Kplastic,+FSType,+FSNormal,+PoroVolumeRatio,+PoroPorosity,+PoroThetaLastStage,+PoroCurrentVolume,+PoroMixtureDensity,+PoroHydraulicConductivity,+PosDiv,+HydroMechLoadAce'


def verify(entries):need(all(stat(e['path'])==e for e in entries),'Consumed source/input/program/runtime changed')


def signature(n):return n.tag,tuple(sorted((k,v) for k,v in n.attrib.items() if k!='comment' and not k.endswith('_comment'))),(n.text or '').strip(),tuple(signature(q) for q in n)


def check_input(path,generated=False):
    expected=ET.parse(ROOT).getroot(); expected.find('casedef/constantsdef/hdp').set('value','1.8')
    main=expected.find('casedef/geometry/commands/mainlist'); commands=list(main)
    marks=[i for i,q in enumerate(commands) if q.tag=='setmkbound']; fluid=next(i for i,q in enumerate(commands) if q.tag=='setmkfluid')
    need([commands[i].get('mk') for i in marks]==['0','1','2'] and all(commands[i+1].tag=='drawbox' for i in marks),'Retained left/bed/right geometry blocks differ')
    left,bed,right=marks; need(bed==left+2 and right==bed+2 and fluid==right+2,'Retained geometry command pairing differs')
    main[:]=commands[:left]+commands[left:bed]+commands[right:fluid]+commands[bed:right]+commands[fluid:]
    params={q.get('key'):q for q in expected.findall('execution/parameters/parameter')}
    for key,value in (('DtIni','0.000005'),('DtFixed','0.000005'),('SoilDampingCoef','0.03'),('TimeMax','13.0')):need(key in params,'Retained template parameter missing'); params[key].set('value',value)
    actual=ET.parse(path).getroot()
    if generated:
        need(all(signature(actual.find(q))==signature(expected.find(q)) for q in ('execution/special','execution/parameters')),'GenCase changed source physics')
        constants=actual.find('execution/constants'); need(constants is not None and float(constants.find('h').get('value'))==.072 and float(constants.find('dp').get('value'))==.04,'Actual generated h/dp differs')
    else:need(signature(actual)==signature(expected),'Only hdp1.8/dt5us/damping.03/left-right-bed order/comments may differ from source template; TimeMax remains13')
    pairs=[(q.get('key'),q.get('value')) for q in actual.findall('execution/parameters/parameter')]; p=dict(pairs); need(len(p)==len(pairs),'Duplicate actual parameter')
    for key,value in dict(Kernel=1,DtIni=DT,DtFixed=DT,DtMin=1e-8,TimeMax=13.,TimeOut=.01,SoilDamping=1,SoilDampingCoef=.03,SavePosDouble=1,PartsOutMax=0).items():need(float(p.get(key,'nan'))==value,'Actual source parameter differs: '+key)
    event=actual.find('execution/special/gravitypreload'); need(event is not None and float(event.get('time'))==10. and event.get('release_mkbound')=='2' and event.get('elastic_source')=='true' and not event.get('statefile') and event.get('keep_bed_overlap','false')=='false','Fresh strict elastic source/event differs')
    need(float(p.get('NoPenetration','0'))==float(p.get('ArtificialStress','0'))==0,'Source NoPen/AS must remain OFF')


def context(notify):
    a=read(AD); need(a['passed'] and a['allowed_job']==TAG and a['hdp']==1.8 and a['fixed_dt_s']==DT and a['damping_coefficient']==.03 and a['planned_global_end']==END and a['expected_saved_frames']==FRAMES,'Root admission for this exact fresh source required')
    thread=os.environ.get('CODEX_THREAD_ID'); need(not notify or (a['root_thread_id']==THREAD and thread==THREAD and CODEX.is_file()),'Only the actual admitted root thread may queue once')
    rp=L/'upl_c08_formal_psi0_r6_r1.run.json'; r=read(rp); need(r['passed'] and r['solver_completed'] and r['postprocess_completed'],'Closed formal runtime_r6 provenance required')
    bp=Path(bind(r['source_build'])['path']); b=read(bp); program=RUNTIME/'DualSPHysics5.2_GEO_win64.exe'
    need(b['passed'] and b['configuration']=='Release' and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and len(b['project_objects'])==113,'Closed original Release source build required')
    need(bind(r['program'])==stat(program) and (stat(program)['bytes'],stat(program)['mtime_ns'])==(b['program']['bytes'],b['program']['mtime_ns']),'Official runtime_r6 program differs')
    install=L/'upl_c08_formal_r6_runtime_r1.json'; ri=read(install); need(ri['passed'],'Closed runtime_r6 installation required'); dest={Path(q['destination']['path']).name:q['destination'] for q in ri['files']}
    runtime=[bind(dest[k]) for k in ('DualSPHysics5.2_GEO_win64.exe','GenCase_win64.exe','PartVTK_win64.exe','DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll')]
    before=[stat(p) for p in (Path(__file__),NOTE,CONFIG,ROOT,AD,rp,bp,install,Path(base.__file__),Path(base.evidence.__file__),Path(base.summary.__code__.co_filename))]+runtime+[bind(b[k]) for k in ('source_capture','source_archive')]
    check_input(CONFIG); verify(before)
    for q in psutil.process_iter(['exe','cmdline']):
        try:need(not(q.info['exe'] and Path(q.info['exe']).name.lower().startswith('dualsphysics') and any(v.lower().startswith('-gpu') for v in (q.info['cmdline'] or [])[1:])),'GPU physical target active; no process stopped')
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    return b,bp,program,before,thread


def output_checks():
    r=base.summary(OUT/'Run.csv'); text=(OUT/'Run.out').read_text(encoding='utf-8-sig'); parts=sorted((OUT/'data').glob('Part_*.bi4'))
    need(int(r['Steps'])==END and int(r['PartFiles'])==FRAMES and int(r['Np'])==7060 and int(r['Nfixed'])==int(r['Nbound'])==2060 and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')) and 'Gpu_' in r['Hardware'] and float(r['Dp'])==.04 and float(r['H'])==.072,'Actual GPU source schedule/registry/h/no-exclusion differs')
    need('Finished execution (code=0).' in text and 'GravityPreload: requested=10 event_completed_step=2000000 release_mkbound=2;' in text and 'GravityPreload: phase=released' not in text and 'GravityPreload: state imported' not in text,'Must finish at complete PRE before release, without import')
    need('No Penetration=False' in text and 'ArtificialStress="None"' in text and 'SoilDamping="BuiFukagawa2013"' in text and 'SoilDampingCoef=0.03' in text and 'PoreShepardRegularization="Enabled"' in text and 'PoreShepardInterval: 40' in text,'Actual source AS/NoPen/damping/Shepard mode differs')
    need('GravityPreload: validated native right-wall range=[1805,2060), count=255.' in text,'Actual bed-last right-wall registry differs')
    need([p.name for p in parts]==['Part_%04d.bi4'%i for i in range(FRAMES)],'Actual1001 contiguous source PARTs required')
    return dict(actual_steps=END,saved_frames=FRAMES,Run_csv=stat(OUT/'Run.csv'),Run_out=stat(OUT/'Run.out'),summary=r,PARTs=[stat(p) for p in parts],source_pre_file=stat(OUT/'data/Part_1000.bi4'),source_head=stat(OUT/'data/Part_Head.ibi4'),Hardware=r['Hardware'])


def export_selected(seed,result):
    particles=OUT/'particles'; particles.mkdir(); calls=[]; files=[]
    for label,kind,npoints in (('PartFluid','fluid',5000),('PartBound','fixed',2060)):
        for part in SELECTED:
            argv=[str(RUNTIME/'PartVTK_win64.exe'),'-dirin',str(OUT/'data'),'-filexml',str(seed),'-first:'+str(part),'-last:'+str(part),'-savevtk',str(particles/label),'-onlytype:-all,'+kind,VARS,'-threads:1']
            result['PartVTK_invocations']+=1; calls.append(invoke(TAG+'.vtk_'+label+'_%04d'%part,argv,C)); p=particles/(label+'_%04d.vtk'%part)
            with p.open('rb') as f:m=re.search(rb'\bPOINTS\s+(\d+)\s+',f.read(4096))
            need(m and int(m[1])==npoints,'Selected '+label+' count differs'); files.append(stat(p))
    need({p.name for p in particles.iterdir()}=={Path(e['path']).name for e in files},'Unexpected/partial selected export'); return calls,files


def queue_once(thread):
    attempt=L/(TAG+'.queue_attempt.json'); reply=L/(TAG+'.queue_result.json'); need(not attempt.exists() and not reply.exists(),'Existing terminal queue protected; never resend')
    message=('The authorized fresh C08 hdp1.8 source is terminal: '+str(RUN)+'. Read original run/start/call/status/owner_admission/root admission and verify owned PID creation/exe/argv/parent, actual Popen/Win32/solver exits and source/program/input stats. This is runtime_r6 law2 Cubic h=.072/dp=.04, fixed5us, damping.03, Shepard40, AS/NoPen/keepbed OFF, strict elastic source, capped2M updates and1001 saves at10s before release. It is not native certification or equilibrium acceptance. Only if solver genuinely completed were0/1/5/10s Fluid5000/Bound2060 exported. If postprocessing failed after solver0, preserve completed BI4 and repair derived outputs only; never rerun the source. This source uses left-right-bed draw priority: original source MK0 begin0 count255, MK1 begin255 count1550, MK2 begin1805 count255, fluid2060+5000. Shallow corner samples are bed NoSlip/+Z from initialization; source and receiver keep_bed_overlap=false and normal retirement is255. New source and receiver geometry/H/dt contracts must match. Old h1.2 and keep5/260-derived readers are incompatible; never relabel old IDs or reuse them for this new source. A separately reviewed new native tool may qualify one PRE, but this owner decodes nothing and starts no receiver/otherpsi/next job. Preserve actual failure/partials/last console with no invented unsaved time. Continue the user-authorized parameter selection through independently reviewed tools after source qualification. This queue is attempted once with45s timeout; delivery can be uncertain, never resend/rearm or start a watcher.')
    argv=[str(CODEX),'queue','--thread',thread,'--message',message]; save(attempt,dict(stage=TAG,utc=base.utc(),thread=thread,run=stat(RUN),arguments=argv,attempts=1,timeout_s=45,do_not_resend=True)); result=dict(stage=TAG,attempts=1,do_not_resend=True)
    try:
        q=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW); result.update(actual_exit=q.returncode,status='queued' if q.returncode==0 else 'queue_failed',stdout=q.stdout,stderr=q.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(reply,result)


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--execution-authorized',action='store_true'); p.add_argument('--notify',action='store_true'); args=p.parse_args(); need(args.execution_authorized and AD.is_file(),'Root full-read and explicit admission required')
    need(not OUT.exists() and not any(p.name!=AD.name for p in L.glob(TAG+'.*')),'Existing owner/output/partial protected; no retry')
    claim=L/(TAG+'.claim.json'); save(claim,dict(stage=TAG,owner_pid=os.getpid(),owner_created_epoch=psutil.Process().create_time(),single_attempt=True)); before=[]; stage='preflight'
    result=dict(stage=TAG,passed=False,solver_completed=False,postprocess_completed=False,physical_acceptance=False,equilibrium_acceptance=False,native_review_pending=True,source_material_law_version_expected=2,source_material_law_version_native_observed=False,hdp=1.8,expected_native_H=struct.unpack('<f',struct.pack('<f',.072))[0],fixed_dt_s=DT,damping_coefficient=.03,planned_global_end=END,expected_saved_frames=FRAMES,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,PartVTK_invocations=0,queue_invocations_at_run_seal=0,SHA_scans=0)
    try:
        b,bp,program,before,thread=context(args.notify); before.append(stat(claim)); OUT.mkdir(); prefix=OUT/TAG; stage='GenCase'; result['GenCase_invocations']=1
        result['GenCase_call']=invoke(TAG+'.gencase',[str(RUNTIME/'GenCase_win64.exe'),str(CONFIG.with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml'); check_input(seed,True); seed_entries=[stat(Path(str(prefix)+q)) for q in ('.xml','.bi4','_Normals.nbi4')]; before+=seed_entries; verify(before)
        argv=[str(program),'-gpu:0','-stable','-mdbc_freeslip',str(prefix),str(OUT),'-dirdataout','data','-svres','-nsteps:'+str(END)]
        ad=L/(TAG+'.owner_admission.json'); save(ad,dict(stage=TAG,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(AD),actual_environment_thread=thread,notification_thread=THREAD if args.notify else None,program=stat(program),source_build=stat(bp),source_capture=b['source_capture'],source_archive=b['source_archive'],input_xml=stat(seed),seed=seed_entries,planned_global_end=END,expected_saved_frames=FRAMES,fixed_dt_s=DT,expected_native_H=result['expected_native_H'],argv=argv,solver_argv=argv,consumed=before)); before.append(stat(ad))
        result.update(program=stat(program),source_build=stat(bp),source_capture=b['source_capture'],source_archive=b['source_archive'],input_xml=stat(seed),seed=seed_entries,argv=argv,owner_admission=stat(ad))
        stage='solver'; result['solver_invocations']=1; result['actual_call']=base.owned(TAG,argv,program,False,stat(ad)); result.update(solver_completed=True,actual_exit=0,actual_Win32_exit=0)
        stage='solver_output_review'; result.update(output_checks()); stage='postprocess'; base.publish(TAG,OUT,None,None,'source_completed_selected_exports_running'); calls,files=export_selected(seed,result); verify(before)
        result.update(passed=True,postprocess_completed=True,PartVTK_calls=calls,particle_files=files,selected_part_numbers=list(SELECTED),selected_nominal_physical_times_s=[0,1,5,10],VTK_positions_are_float=True,consumed_stats_unchanged=True)
    except Exception as error:
        result.update(first_failure=str(error),failed_stage=stage); cp=L/(TAG+'.call.json')
        if cp.exists():
            call=read(cp); result.update(actual_call=stat(cp),actual_exit=call['actual_solver_Win32_exit'],actual_Win32_exit=call['actual_solver_Win32_exit'],actual_tool_exit=call['actual_Popen_wait_exit'],ownership_errors=call['ownership_errors'])
        path=OUT/'Run.out'
        if path.exists():
            result['Run_out']=stat(path); lines=path.read_text(encoding='utf-8-sig',errors='replace').splitlines(); first=next((i for i,line in enumerate(lines) if line.startswith('*** Exception')),None); result['first_engine_exception_lines']=lines[first:first+6] if first is not None else []
    result.update(consumed=before,last_original_console_line=base.last_part(OUT),unsaved_failure_time_reconstructed=False)
    try:base.publish(TAG,OUT,None,None,'completed_pending_native_and_equilibrium_review' if result['passed'] else 'failed_preserved_pending_diagnosis')
    except Exception as error:result['terminal_status_error']=str(error)
    save(RUN,result)
    if args.notify and (L/(TAG+'.call.json')).exists():queue_once(THREAD)
    print(json.dumps(dict(passed=result['passed'],run=str(RUN),solver_completed=result['solver_completed'],postprocess_completed=result['postprocess_completed'],first_failure=result.get('first_failure'))),flush=True); return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
