"""One admitted output-only pairtrace AS.2/n3 .30s receiver diagnostic; no automatic decoder or next job."""
import argparse,csv,json,os,re,struct,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import upl_c08_bedkeep_run_r1 as base
from upl_c08_asn3_window_r1 import summary
T,C,L,PRE=base.T,base.C,base.L,base.PRE;need,read,stat,bind,save,invoke=base.need,base.read,base.stat,base.bind,base.save,base.invoke
TAG='upl_c08_pairtrace_window_GPU_r1';OUT=T/'outputs'/TAG;CONFIG=T/'configs'/(TAG+'_Def.xml');BAT=T/'configs'/('x'+TAG+'_win64_GPU.bat');NOTE=T/'notes/upl_c08_pairtrace_window_r1.md'
PREPARE=T/'support/upl_c08_pairtrace_window_r1_prepare.py';IDS=(7011,7012,6230)
ROOT=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r6_Def.xml';RUNTIME=C/'support/runtime_r6';AD=L/(TAG+'.admission.json');RUN=L/(TAG+'.run.json');END=4120000;FRAMES=30
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8';CODEX=Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1021.22027-win32-x64/bin/windows-x86_64/codex.exe')
def signature(n):return n.tag,tuple(sorted((k,v) for k,v in n.attrib.items() if k!='comment' and not k.endswith('_comment'))),(n.text or '').strip(),tuple(signature(q) for q in n)
def verify(entries):need(all(Path(e['path']).is_file() and stat(e['path'])==e for e in entries),'Consumed frozen input/program/source changed')

def expected():
    root=ET.parse(ROOT).getroot();need(root.find("execution/parameters/parameter[@key='Visco']").get('value')=='0.1','Original AV.1 required');root.find('execution/special/gravitypreload').set('statefile',str(PRE.resolve()))
    for key,value in (('ArtificialStressCoef','0.2'),('ArtificialStressExp','3'),('TimeMax','10.30'),('TimeOut','0.01')):
        nodes=root.findall("execution/parameters/parameter[@key='"+key+"']");need(len(nodes)==1,'Unique retained parameter required');nodes[0].set('value',value)
    return root
def check_input(path,generated=False):
    actual=ET.parse(path).getroot();want=expected()
    if generated:
        need(all(signature(actual.find(q))==signature(want.find(q)) for q in ('execution/special','execution/parameters')),'Generated physical sections differ');ct=actual.find('execution/constants');need(float(ct.find('h').get('value'))==.048 and float(ct.find('dp').get('value'))==.04,'Original generated h/dp required')
    else:need(signature(actual)==signature(want),'Only end/clock/source binding and comments may differ from r6')


def context(notify):
    a=read(AD);need(a['passed'] and a['allowed_job']==TAG and a['ArtificialStressCoef']==.2 and a['ArtificialStressExp']==3 and a['FreeSeepagePondingPolicy']=='CompletedOnly' and a['observed_native_IDs']==list(IDS) and a['planned_global_end']==END and a['expected_saved_frames']==FRAMES,'Root explicit one-job output-only pairtrace admission required');thread=os.environ.get('CODEX_THREAD_ID');need(not notify or (a['root_thread_id']==THREAD and thread in (None,'',THREAD) and CODEX.is_file()),'Only this admitted same root thread may notify')
    before=[stat(p) for p in (Path(__file__),PREPARE,NOTE,CONFIG,BAT,ROOT,AD,PRE,PRE.parent/'Part_Head.ibi4',RUNTIME/'GenCase_win64.exe',Path(base.__file__),Path(base.evidence.__file__),Path(summary.__code__.co_filename))];builds={};capture=None
    for conf,objects,retained,compiles,cuda in (('DebugCPU',87,86,1,0),('Release',113,110,3,2)):
        bp=L/('upl_c08_pairtrace_'+conf+'_r1.build.json');b=read(bp);need(b['passed'] and b['configuration']==conf and b['consumed_stats_unchanged'] and b['observed_IDs']==list(IDS) and b['trace_macros_enabled']==(conf=='Release') and not b['CPU_observer_enabled'] and b['CPU_check_recompiles_unchanged_TU']==(conf=='DebugCPU') and b['physical_objects_recompiled']==compiles and b['retained_physical_objects']==retained and b['actual_link_objects']==objects and b['compile_invocations']==compiles and b['CUDA_compile_invocations']==cuda and b['link_invocations']==1,'Corresponding closed pairtrace CPU/GPU build and actual TU counts required')
        se,archive=bind(b['source_capture']),bind(b['source_archive']);need(capture is None or se==capture,'Same frozen ID-only capture required');capture=se;calls=[bind(q) for q in b['calls']];need(len(calls)==compiles+1 and all(q['actual_Popen_wait_exit']==q['actual_Win32_exit']==0 and q['ownership_failure'] is None for q in (read(v['path']) for v in calls)),'Actual compiler/linker typed exits required');before.extend([stat(bp),bind(b['program']),se,archive,bind(b['baseline_source_build']),*calls]);builds[conf]=(bp,b)
    sc=read(capture['path']);need(sc['observed_IDs']==list(IDS) and sc['old_observed_IDs']==[7017,5944,6814] and sc['ID_mapping_sites_changed']==4 and all(sc[k] for k in ('only_observer_ID_literals_changed','reverse_reconstruction_original_bytes_exact','all_other_archive_member_bytes_exact')) and not any(sc[k] for k in ('observer_layout_changed','sampler_changed','physical_equations_changed')),'Exactly four observer-ID mapping literals may change; layout/sampler/physics unchanged')
    bp,b=builds['Release'];need(sc['archive']==b['source_archive'],'Actual private source archive differs');before.extend([bind(sc['diff']),*[bind(q) for q in sc['private_sources']]]);program=Path(b['program']['path']);runtime=[bind(q) for q in b['runtime']];names=('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll');need(len(runtime)==7 and {Path(q['path']).name for q in runtime}==set(names) and all(Path(q['path']).parent==program.parent for q in runtime),'Seven closed local GPU dependencies required');origins=[stat(RUNTIME/k) for k in names];need(all((q['bytes'],q['mtime_ns'])==(v['bytes'],v['mtime_ns']) for q in runtime for v in origins if Path(q['path']).name==Path(v['path']).name),'Private local dependencies must match original runtime sources');before+=runtime+origins;check_input(CONFIG);verify(before)
    for q in psutil.process_iter(['exe','cmdline']):
        try:need(not(q.info['exe'] and Path(q.info['exe']).name.lower().startswith('dualsphysics') and any(v.lower().startswith('-gpu') for v in (q.info['cmdline'] or [])[1:])),'GPU physical target active; no process stopped')
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    return b,bp,program,before,thread


def output_checks():
    r=summary(OUT/'Run.csv');text=(OUT/'Run.out').read_text(encoding='utf-8-sig');parts=sorted((OUT/'data').glob('Part_*.bi4'))
    need(int(r['Steps'])==END and int(r['PartFiles'])==FRAMES and int(r['Np'])==7060 and int(r['Nfixed'])==int(r['Nbound'])==2060 and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')) and 'Gpu_' in r['Hardware'],'Actual GPU30-frame/original registry/no-exclusion differs')
    need('Finished execution (code=0).' in text and 'No Penetration=True' in text and 'ArtificialStress="Bui2008"' in text and 'Dynamic NoPen: '+base.POLICY in text,'Actual normal AS.2/n3/fixed-plane execution differs')
    for key,value in (('ArtificialStressCoef',.2),('ArtificialStressExp',3.)):
        matches=re.findall(r'^\s*'+key+r'[:=]\s*([0-9.eE+-]+)\s*$',text,re.M);need(len(matches)==1 and struct.pack('<f',float(matches[0]))==struct.pack('<f',value),'Actual AS coefficient/exponent log differs')
    marker='GravityPreload: release policy=KeepBedOverlap original_target=260 retired=255 kept_bed=5 kept_ids='+','.join(map(str,base.BED_IDS))+'; coordinates/IDs/fixed MK codes retained, bed normal=+DpZ NoSlip.';need(text.count('GravityPreload: phase=released ')==text.count(marker)==1 and 'retired=255; damping=OFF Shepard=OFF FreeSeepage=ON.' in text,'Actual one255/five-kept release differs')
    imported=re.findall(r'GravityPreload: state imported file=.*? actual=([0-9.eE+-]+) completed_step=(\d+);',text);need(len(imported)==1 and int(imported[0][1])==4000000,'Original actual r2GPU PRE import missing');need([p.name for p in parts]==['Part_%04d.bi4'%i for i in range(FRAMES)],'Actual30 contiguous PARTs required');trace,totals=OUT/'C08CausalTrace.csv',OUT/'C08CausalTotals.csv';need(trace.is_file() and trace.stat().st_size>0 and totals.is_file(),'Actual observer CSVs required');seen={identity:set() for identity in IDS};rows=0
    with totals.open(encoding='utf-8-sig',newline='') as stream:
        for q in csv.DictReader(stream):
            identity,step=int(q['native_id']),int(q['completed_step']);count=step-4000000;need(identity in seen and count in range(4000,120001,4000) and step not in seen[identity] and int(q['errors'])==0 and all(int(q[k])==count for k in ('material_pre_count','material_cor_count','plane_pre_count','plane_cor_count')),'Actual three-ID cumulative coverage/errors differ');seen[identity].add(step);rows+=1
    need(rows==90 and all(v==set(range(4004000,END+1,4000)) for v in seen.values()),'Actual30 saved cumulative snapshots per ID required')
    return dict(actual_steps=END,saved_frames=FRAMES,summary=r,actual_source_time_from_loader=float(imported[0][0]),Run_csv=stat(OUT/'Run.csv'),Run_out=stat(OUT/'Run.out'),PARTs=[stat(p) for p in parts],Hardware=r['Hardware'],trace_file=stat(trace),totals_file=stat(totals),observed_native_IDs=list(IDS),cumulative_counters_checked=True,cumulative_final_updates_per_ID=120000,causal_trace_scientific_review_pending=True)

def queue_once():
    attempt=L/(TAG+'.queue_attempt.json');reply=L/(TAG+'.queue_result.json');need(not attempt.exists() and not reply.exists(),'Existing terminal queue protected; never resend')
    message=('The single admitted output-only C08 pairtrace .30s GPU window is terminal: '+str(RUN)+'. Verify start/call/status/owner_admission/root admission, actual creation/exe/argv/parent and Popen/Win32 exits, new closed pairtrace Release source/program and original PRE/input stats. Only four observer ID mapping literals changed to7011/7012/6230; physics,97/56column layouts and sampling stay unchanged. This is120000updates/global4120000/30planned saves, AS total.2/n3, AV.1, hdp1.2/fixed2.5us/keep5/fixedplane/CompletedOnly/releaseShepardOFF, original r2GPU10s PRE; no new PRE or physical-parameter trial. Normal exit/trace counters are not physical acceptance or no-feedback proof. Native must be separately authorized once with this30profile, then all22 records/time/signed clocks must be compared bytewise with truecausal90 first30 while preserving30/90headers. Do not use AV15/AS025-specific metadata expectations. Retain actual first failure/partial/last original PART and do not invent unsaved failure time. This owner starts no automatic native/VTK/otherpsi/half/PRE/nextsolver; root independently reviews and decides subsequent work under ongoing authorization. One45s same-thread terminal queue only; timeout delivery uncertain, never resend/rearm/add watcher.')
    argv=[str(CODEX),'queue','--thread',THREAD,'--message',message];save(attempt,dict(stage=TAG,utc=base.utc(),thread=THREAD,run=stat(RUN),arguments=argv,attempts=1,timeout_s=45,do_not_resend=True));result=dict(stage=TAG,attempts=1,do_not_resend=True)
    try:
        p=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW);result.update(actual_exit=p.returncode,status='queued' if p.returncode==0 else 'queue_failed',stdout=p.stdout,stderr=p.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(reply,result)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');ap.add_argument('--notify',action='store_true');a=ap.parse_args();need(a.execution_authorized and AD.is_file(),'Root full-read and explicit admission required');need(not OUT.exists() and not any(p.name!=AD.name for p in L.glob(TAG+'.*')),'Existing owner/output/partial protected')
    claim=L/(TAG+'.claim.json');save(claim,dict(stage=TAG,owner_pid=os.getpid(),owner_created_epoch=psutil.Process().create_time(),single_attempt=True));before=[];stage='preflight';result=dict(stage=TAG,passed=False,solver_completed=False,physical_acceptance=False,native_review_pending=True,configuration='Release',source_backend='GPU',target_backend='GPU',observed_native_IDs=list(IDS),output_only_observer=True,ArtificialStress=True,keep_bed_overlap=True,expected_active_native_IDs=6805,policy=base.POLICY,ArtificialStressCoef=.2,ArtificialStressExp=3.,free_seepage_policy='CompletedOnly',solver_invocations=0,GenCase_invocations=0,reader_invocations=0,PartVTK_invocations=0,queue_invocations_at_run_seal=0,SHA_scans=0)
    try:
        b,bp,program,before,thread=context(a.notify);before.append(stat(claim));OUT.mkdir();plan=OUT/'planned_steps.csv'
        with plan.open('x',encoding='utf-8',newline='') as f:w=csv.writer(f);w.writerow(('part','completed_step'));w.writerows((i,4000000+(i+1)*4000) for i in range(FRAMES))
        before.append(stat(plan));prefix=OUT/TAG;stage='GenCase';result['GenCase_invocations']=1;result['GenCase_call']=invoke(TAG+'.gencase',[str(RUNTIME/'GenCase_win64.exe'),str(CONFIG.with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml');check_input(seed,True);seed_entries=[stat(Path(str(prefix)+s)) for s in ('.xml','.bi4','_Normals.nbi4')];before+=seed_entries;verify(before);argv=[str(program),'-gpu:0','-stable','-mdbc_freeslip:1',str(prefix),str(OUT),'-dirdataout','data','-svres','-nsteps:'+str(END)];ad=L/(TAG+'.owner_admission.json')
        save(ad,dict(stage=TAG,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(AD),actual_environment_thread=thread,notification_thread=THREAD if a.notify else None,program=stat(program),source_build=stat(bp),source_capture=b['source_capture'],source_archive=b['source_archive'],runtime=b['runtime'],observed_native_IDs=list(IDS),source_pre_file=stat(PRE),input_xml=stat(seed),seed=seed_entries,planned_steps=stat(plan),planned_new_updates=120000,planned_global_end=END,expected_saved_frames=FRAMES,argv=argv,solver_argv=argv,consumed=before));before.append(stat(ad))
        result.update(program=stat(program),source_build=stat(bp),source_capture=b['source_capture'],source_archive=b['source_archive'],runtime=b['runtime'],observed_native_IDs=list(IDS),source_pre_file=stat(PRE),input_xml=stat(seed),seed=seed_entries,argv=argv,planned_steps=stat(plan),owner_admission=stat(ad));stage='solver';result['solver_invocations']=1;result['actual_call']=base.owned(TAG,argv,program,False,stat(ad));result.update(solver_completed=True,actual_exit=0,actual_Win32_exit=0);stage='solver_output_review';result.update(output_checks());verify(before);result.update(passed=True,consumed_stats_unchanged=True)
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
