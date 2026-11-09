"""One admitted release-only AV.15 with AS.2/n3 .30s receiver diagnostic; no automatic decoder or next job."""
import argparse,csv,json,os,re,struct,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import upl_c08_bedkeep_run_r1 as base
T,C,L,PRE=base.T,base.C,base.L,base.PRE;need,read,stat,bind,save,invoke=base.need,base.read,base.stat,base.bind,base.save,base.invoke
TAG='upl_c08_av15_window_GPU_r1';OUT=T/'outputs'/TAG;CONFIG=T/'configs'/(TAG+'_Def.xml');BAT=T/'configs'/('x'+TAG+'_win64_GPU.bat');NOTE=T/'notes/upl_c08_av15_window_r1.md'
PREPARE=T/'support/upl_c08_av15_window_r1_prepare.py'
ROOT=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r6_Def.xml';RUNTIME=C/'support/runtime_r6';AD=L/(TAG+'.admission.json');RUN=L/(TAG+'.run.json');END=4120000;FRAMES=30
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8';CODEX=Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1021.22027-win32-x64/bin/windows-x86_64/codex.exe')
def signature(n):return n.tag,tuple(sorted((k,v) for k,v in n.attrib.items() if k!='comment' and not k.endswith('_comment'))),(n.text or '').strip(),tuple(signature(q) for q in n)
def verify(entries):need(all(Path(e['path']).is_file() and stat(e['path'])==e for e in entries),'Consumed frozen input/program/source changed')

def expected():
    root=ET.parse(ROOT).getroot();need(root.find("execution/parameters/parameter[@key='Visco']").get('value')=='0.1','Original certified XML Visco.1 must remain literal');root.find('execution/special/gravitypreload').set('statefile',str(PRE.resolve()))
    for key,value in (('ArtificialStressCoef','0.2'),('ArtificialStressExp','3'),('TimeMax','10.30'),('TimeOut','0.01')):
        nodes=root.findall("execution/parameters/parameter[@key='"+key+"']");need(len(nodes)==1,'Unique retained parameter required');nodes[0].set('value',value)
    return root
def check_input(path,generated=False):
    actual=ET.parse(path).getroot();want=expected()
    if generated:
        need(all(signature(actual.find(q))==signature(want.find(q)) for q in ('execution/special','execution/parameters')),'Generated physical sections differ');ct=actual.find('execution/constants');need(float(ct.find('h').get('value'))==.048 and float(ct.find('dp').get('value'))==.04,'Original generated h/dp required')
    else:need(signature(actual)==signature(want),'Only end/clock/source binding and comments may differ from r6')

def summary(path):
    lines=Path(path).read_text(encoding='utf-8-sig').splitlines();need(len(lines)==2,'One Run.csv header/data row required');m=re.match(r'^#?RunName([;,])',lines[0]);need(m is not None,'Unsupported Run.csv delimiter');sep=m[1];keys=lines[0].lstrip('#').split(sep);values=lines[1].split(sep)
    need(len(set(keys))==len(keys) and keys.count('Configuration')==1,'Unique Run.csv columns required');i=keys.index('Configuration');extra=len(values)-len(keys)
    if extra==1 and sep==';':values=values[:i]+[values[i]+';'+values[i+1]]+values[i+2:]
    else:need(extra==0,'Only the one known AS Configuration semicolon is allowed')
    number=r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?';hits=list(re.finditer(r'(?:^| - )AS_Bui2008\(('+number+r');('+number+r')\)(?= - |$)',values[i]));need(len(values)==len(keys) and len(hits)==1 and values[i].count(';')==values[i].count('AS_Bui2008')==1,'Complete unique AS_Bui2008(0.2;3) token required')
    need(all(struct.pack('<f',float(hits[0][j+1]))==struct.pack('<f',v) for j,v in enumerate((.2,3.))),'Executed coefficient/exponent differs');return dict(zip(keys,values))

def context(notify):
    a=read(AD);need(a['passed'] and a['allowed_job']==TAG and a['ArtificialStressCoef']==.2 and a['ArtificialStressExp']==3 and a['input_ArtificialViscosityCoef']==.1 and a['released_ArtificialViscosityCoef']==.15 and a['AV_policy']=='ReleaseOnly' and a['FreeSeepagePondingPolicy']=='CompletedOnly' and a['planned_global_end']==END and a['expected_saved_frames']==FRAMES,'Root explicit one-job release-only AV.15 admission required');thread=os.environ.get('CODEX_THREAD_ID');need(not notify or (a['root_thread_id']==THREAD and thread in (None,'',THREAD) and CODEX.is_file()),'Only this admitted same root thread may notify')
    smoke=[bind(a[k]) for k in ('cpu_smoke_run','cpu_smoke_native')];sr,sn=[read(q['path']) for q in smoke];need(sr['passed'] and sr['solver_completed'] and sr['actual_exit']==sr['actual_Win32_exit']==0 and sn['passed'] and sn['source_run']==smoke[0] and sn['original_native_guards_passed'],'Root-filled CPU implementation smoke and original native guards required; no physical acceptance inferred')
    bp=L/'upl_c08_av15_release_Release_r1.build.json';b=read(bp);need(b['passed'] and b['configuration']=='Release' and b['consumed_stats_unchanged'] and b['physical_objects_recompiled']==2 and b['retained_physical_objects']==111 and b['actual_link_objects']==113 and b['compile_invocations']==2 and b['link_invocations']==1 and b['CUDA_compile_invocations']==0 and b['AV_policy']=='ReleaseOnly' and b['preload_input_AV_literal']=='.1f' and b['released_AV_literal']=='.15f' and b['actual_AV_metadata_key']=='DynamicArtificialViscosityCoef' and b['AS_stress_space']=='original_total' and not b['trace_macros_enabled'],'Closed private two-host-TU AV.15 Release build required')
    sc=read(bind(b['source_capture'])['path']);need(all(sc[k] for k in ('reverse_reconstruction_original_bytes_exact','all_other_archive_member_bytes_exact','only_release_AV_override_and_actual_metadata_changed')) and not any(sc[k] for k in ('GetGravityPreloadContract_changed','class_layout_changed','public_interfaces_changed','CUDA_source_changed','trace_macros_enabled')) and sc['archive']==b['source_archive'],'Private release-AV/actual-metadata-only source proof required')
    calls=[bind(q) for q in b['calls']];need(len(calls)==3 and all((q['actual_Popen_wait_exit']==q['actual_Win32_exit']==0 and q['ownership_failure'] is None) for q in (read(v['path']) for v in calls)),'Actual two compiler and one linker typed exits required')
    program=Path(bind(b['program'])['path']);runtime=[bind(q) for q in b['runtime']];names=('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll');need(len(runtime)==7 and {Path(q['path']).name for q in runtime}==set(names) and all(Path(q['path']).parent==program.parent for q in runtime),'Use the private program and its seven closed local dependencies')
    origins=[stat(RUNTIME/k) for k in names];need(all((q['bytes'],q['mtime_ns'])==(next(v for v in origins if Path(v['path']).name==Path(q['path']).name)['bytes'],next(v for v in origins if Path(v['path']).name==Path(q['path']).name)['mtime_ns']) for q in runtime),'Private dependency copies must match original runtime_r6 sources')
    before=[stat(p) for p in (Path(__file__),PREPARE,NOTE,CONFIG,BAT,ROOT,AD,bp,PRE,PRE.parent/'Part_Head.ibi4',RUNTIME/'GenCase_win64.exe',Path(base.__file__),Path(base.evidence.__file__))]+smoke+calls+runtime+origins+[bind(b[k]) for k in ('program','source_capture','source_archive','baseline_source_build')]+[bind(sc['diff'])]+[bind(q) for q in b['private_host_sources']];check_input(CONFIG);verify(before)
    for q in psutil.process_iter(['exe','cmdline']):
        try:need(not(q.info['exe'] and Path(q.info['exe']).name.lower().startswith('dualsphysics') and any(v.lower().startswith('-gpu') for v in (q.info['cmdline'] or [])[1:])),'GPU physical target active; no process stopped')
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    return b,bp,program,before,thread


def output_checks():
    r=summary(OUT/'Run.csv');text=(OUT/'Run.out').read_text(encoding='utf-8-sig');parts=sorted((OUT/'data').glob('Part_*.bi4'))
    need(int(r['Steps'])==END and int(r['PartFiles'])==FRAMES and int(r['Np'])==7060 and int(r['Nfixed'])==int(r['Nbound'])==2060 and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')) and 'Gpu_' in r['Hardware'],'Actual GPU30-frame/original registry/no-exclusion differs')
    need('Finished execution (code=0).' in text and 'No Penetration=True' in text and 'ArtificialStress="Bui2008"' in text and 'Dynamic NoPen: '+base.POLICY in text,'Actual normal release-only AV.15/AS.2n3/fixed-plane execution differs')
    for key,value in (('ArtificialStressCoef',.2),('ArtificialStressExp',3.)):
        matches=re.findall(r'^\s*'+key+r'[:=]\s*([0-9.eE+-]+)\s*$',text,re.M);need(len(matches)==1 and struct.pack('<f',float(matches[0]))==struct.pack('<f',value),'Actual AS coefficient/exponent log differs')
    marker='GravityPreload: release policy=KeepBedOverlap original_target=260 retired=255 kept_bed=5 kept_ids='+','.join(map(str,base.BED_IDS))+'; coordinates/IDs/fixed MK codes retained, bed normal=+DpZ NoSlip.';need(text.count('GravityPreload: phase=released ')==text.count(marker)==1 and 'retired=255; damping=OFF Shepard=OFF FreeSeepage=ON.' in text,'Actual one255/five-kept release differs')
    imported=re.findall(r'GravityPreload: state imported file=.*? actual=([0-9.eE+-]+) completed_step=(\d+);',text);need(len(imported)==1 and int(imported[0][1])==4000000,'Original actual r2GPU PRE import missing');need([p.name for p in parts]==['Part_%04d.bi4'%i for i in range(FRAMES)],'Actual30 contiguous PARTs required');need(not any((OUT/k).exists() for k in ('C08StageTrace.csv','C08CausalTrace.csv','C08CausalTotals.csv')),'Unexpected observer outputs from macro-off physical program')
    av=re.findall(r'^Private AV: policy=ReleaseOnly input_coefficient=([0-9.eE+-]+) actual_coefficient=([0-9.eE+-]+) completed_step=(\d+) actual=([0-9.eE+-]+); startup Configuration records the certified input, runtime metadata records the released coefficient\.$',text,re.M);need(len(av)==1 and int(av[0][2])==4000000 and all(struct.pack('<f',float(av[0][i]))==struct.pack('<f',v) for i,v in enumerate((.1,.15))) and struct.pack('<d',float(av[0][3]))==struct.pack('<d',float(imported[0][0])),'Unique actual release-only AV input/override log and imported clock required; startup AV.1 is not the released coefficient')
    return dict(actual_steps=END,saved_frames=FRAMES,summary=r,actual_source_time_from_loader=float(imported[0][0]),actual_released_AV_coefficient_from_log=float(av[0][1]),Run_csv=stat(OUT/'Run.csv'),Run_out=stat(OUT/'Run.out'),PARTs=[stat(p) for p in parts],Hardware=r['Hardware'])

def queue_once():
    attempt=L/(TAG+'.queue_attempt.json');reply=L/(TAG+'.queue_result.json');need(not attempt.exists() and not reply.exists(),'Existing terminal queue protected; never resend')
    message=('The single admitted C08 release-only AV.15 with baseline total-AS epsilon.2/exponent3 .30s GPU diagnostic is terminal: '+str(RUN)+'. Verify original start/call/status/owner_admission/root admission, actual creation/exe/argv/parent and Popen/Win32 exits, private two-host-TU AV build/source proof, input/PRE stats. XML Visco.1 and original r2GPU10s PRE certification remain unchanged; the private program overrides AV to actual float.15 only after the certified keep5 release. Startup Configuration still records input AV.1; require actual DynamicArtificialViscosityPolicy ReleaseOnly, OverrideActive true and Coef .15f in a separately reviewed native adapter. This is120000new updates/global4120000/30planned saves, hdp1.2/fixed2.5us/keep5/fixedplane/CompletedOnly, AS.2/n3 and releaseShepardOFF. Exit0/CPU smoke/native safety is not repair or physical acceptance. If solver0 and output review fails, repair only derived checks, never rerun this physical job. Before separately authorized unique native decoding, check active/existing readers and require this actual AV metadata/30-frame plan while preserving all22/6805/5000/1805/P0/J/kappa/FS/ledger/keep/plane/clock/signed guards. Preserve first failure/partial/last original PART without inventing unsaved failure time. This owner does not automatically launch native/VTK/otherpsi/half/PRE/nextsolver; root decides the next stage after independent review under ongoing authorization. One45s same-thread queue only; timeout delivery uncertain, never resend/rearm/add watcher.')
    argv=[str(CODEX),'queue','--thread',THREAD,'--message',message];save(attempt,dict(stage=TAG,utc=base.utc(),thread=THREAD,run=stat(RUN),arguments=argv,attempts=1,timeout_s=45,do_not_resend=True));result=dict(stage=TAG,attempts=1,do_not_resend=True)
    try:
        p=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW);result.update(actual_exit=p.returncode,status='queued' if p.returncode==0 else 'queue_failed',stdout=p.stdout,stderr=p.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(reply,result)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');ap.add_argument('--notify',action='store_true');a=ap.parse_args();need(a.execution_authorized and AD.is_file(),'Root full-read and explicit admission required');need(not OUT.exists() and not any(p.name!=AD.name for p in L.glob(TAG+'.*')),'Existing owner/output/partial protected')
    claim=L/(TAG+'.claim.json');save(claim,dict(stage=TAG,owner_pid=os.getpid(),owner_created_epoch=psutil.Process().create_time(),single_attempt=True));before=[];stage='preflight';result=dict(stage=TAG,passed=False,solver_completed=False,physical_acceptance=False,native_review_pending=True,configuration='Release',ArtificialStress=True,keep_bed_overlap=True,expected_active_native_IDs=6805,policy=base.POLICY,ArtificialStressCoef=.2,ArtificialStressExp=3.,AV_policy='ReleaseOnly',input_ArtificialViscosityCoef=.1,released_ArtificialViscosityCoef=.15,actual_AV_metadata_key='DynamicArtificialViscosityCoef',AV_active_metadata_review_pending=True,free_seepage_policy='CompletedOnly',solver_invocations=0,GenCase_invocations=0,reader_invocations=0,PartVTK_invocations=0,queue_invocations_at_run_seal=0,SHA_scans=0)
    try:
        b,bp,program,before,thread=context(a.notify);before.append(stat(claim));OUT.mkdir();plan=OUT/'planned_steps.csv'
        with plan.open('x',encoding='utf-8',newline='') as f:w=csv.writer(f);w.writerow(('part','completed_step'));w.writerows((i,4000000+(i+1)*4000) for i in range(FRAMES))
        before.append(stat(plan));prefix=OUT/TAG;stage='GenCase';result['GenCase_invocations']=1;result['GenCase_call']=invoke(TAG+'.gencase',[str(RUNTIME/'GenCase_win64.exe'),str(CONFIG.with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml');check_input(seed,True);seed_entries=[stat(Path(str(prefix)+s)) for s in ('.xml','.bi4','_Normals.nbi4')];before+=seed_entries;verify(before);argv=[str(program),'-gpu:0','-stable','-mdbc_freeslip:1',str(prefix),str(OUT),'-dirdataout','data','-svres','-nsteps:'+str(END)];ad=L/(TAG+'.owner_admission.json')
        save(ad,dict(stage=TAG,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(AD),actual_environment_thread=thread,notification_thread=THREAD if a.notify else None,program=stat(program),source_build=stat(bp),source_capture=b['source_capture'],source_archive=b['source_archive'],runtime=b['runtime'],AV_policy='ReleaseOnly',input_ArtificialViscosityCoef=.1,released_ArtificialViscosityCoef=.15,source_pre_file=stat(PRE),input_xml=stat(seed),seed=seed_entries,planned_steps=stat(plan),planned_new_updates=120000,planned_global_end=END,expected_saved_frames=FRAMES,argv=argv,solver_argv=argv,consumed=before));before.append(stat(ad))
        result.update(program=stat(program),source_build=stat(bp),source_capture=b['source_capture'],source_archive=b['source_archive'],runtime=b['runtime'],AV_policy='ReleaseOnly',input_ArtificialViscosityCoef=.1,released_ArtificialViscosityCoef=.15,source_pre_file=stat(PRE),input_xml=stat(seed),seed=seed_entries,argv=argv,planned_steps=stat(plan),owner_admission=stat(ad));stage='solver';result['solver_invocations']=1;result['actual_call']=base.owned(TAG,argv,program,False,stat(ad));result.update(solver_completed=True,actual_exit=0,actual_Win32_exit=0);stage='solver_output_review';result.update(output_checks());verify(before);result.update(passed=True,consumed_stats_unchanged=True)
    except Exception as error:
        result.update(first_failure=str(error),failed_stage=stage);cp=L/(TAG+'.call.json')
        if cp.exists():
            call=read(cp);result.update(actual_call=stat(cp),actual_exit=call['actual_solver_Win32_exit'],actual_Win32_exit=call['actual_solver_Win32_exit'],actual_tool_exit=call['actual_Popen_wait_exit'],ownership_errors=call['ownership_errors'])
        log=OUT/'Run.out'
        if log.exists():
            m=re.search(r'^Text: (.+)$',log.read_text(encoding='utf-8-sig'),re.M);result['first_engine_exception_text']=m[1] if m else None;result['Run_out']=stat(log)
    result.update(consumed=before,consumed_stats_unchanged=bool(before) and all(Path(e['path']).is_file() and stat(e['path'])==e for e in before),last_original_console_line=base.last_part(OUT),unsaved_failure_time_known=False)
    try:base.publish(TAG,OUT,None,None,'completed_pending_native' if result['passed'] else 'failed_preserved_pending_diagnosis')
    except Exception as error:result['terminal_status_error']=str(error)
    save(RUN,result)
    if a.notify and (L/(TAG+'.call.json')).exists():queue_once()
    print(json.dumps(dict(passed=result['passed'],run=str(RUN),solver_completed=result['solver_completed'],first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
