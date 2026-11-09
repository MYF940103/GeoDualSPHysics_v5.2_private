"""One admitted epsilon.25/exponent3 .30s receiver diagnostic; no automatic decoder or next job."""
import argparse,csv,json,os,re,struct,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import upl_c08_bedkeep_run_r1 as base
T,C,L,PRE=base.T,base.C,base.L,base.PRE;need,read,stat,bind,save,invoke=base.need,base.read,base.stat,base.bind,base.save,base.invoke
TAG='upl_c08_as025_window_GPU_r1';OUT=T/'outputs'/TAG;CONFIG=T/'configs'/(TAG+'_Def.xml');BAT=T/'configs'/('x'+TAG+'_win64_GPU.bat');NOTE=T/'notes/upl_c08_as025_window_r1.md'
ROOT=C/'CaseLianSaturatedColumnCollapse_psi0_shared_r6_Def.xml';RUNTIME=C/'support/runtime_r6';AD=L/(TAG+'.admission.json');RUN=L/(TAG+'.run.json');END=4120000;FRAMES=30
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8';CODEX=Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1021.22027-win32-x64/bin/windows-x86_64/codex.exe')
def signature(n):return n.tag,tuple(sorted((k,v) for k,v in n.attrib.items() if k!='comment' and not k.endswith('_comment'))),(n.text or '').strip(),tuple(signature(q) for q in n)
def verify(entries):need(all(Path(e['path']).is_file() and stat(e['path'])==e for e in entries),'Consumed frozen input/program/source changed')

def expected():
    root=ET.parse(ROOT).getroot();root.find('execution/special/gravitypreload').set('statefile',str(PRE.resolve()))
    for key,value in (('ArtificialStressCoef','0.25'),('ArtificialStressExp','3'),('TimeMax','10.30'),('TimeOut','0.01')):
        nodes=root.findall("execution/parameters/parameter[@key='"+key+"']");need(len(nodes)==1,'Unique retained parameter required');nodes[0].set('value',value)
    return root
def check_input(path,generated=False):
    actual=ET.parse(path).getroot();want=expected()
    if generated:
        need(all(signature(actual.find(q))==signature(want.find(q)) for q in ('execution/special','execution/parameters')),'Generated physical sections differ');ct=actual.find('execution/constants');need(float(ct.find('h').get('value'))==.048 and float(ct.find('dp').get('value'))==.04,'Original generated h/dp required')
    else:need(signature(actual)==signature(want),'Only coefficient.2->.25/end/clock/source binding and comments may differ from r6')

def summary(path):
    lines=Path(path).read_text(encoding='utf-8-sig').splitlines();need(len(lines)==2,'One Run.csv header/data row required');m=re.match(r'^#?RunName([;,])',lines[0]);need(m is not None,'Unsupported Run.csv delimiter');sep=m[1];keys=lines[0].lstrip('#').split(sep);values=lines[1].split(sep)
    need(len(set(keys))==len(keys) and keys.count('Configuration')==1,'Unique Run.csv columns required');i=keys.index('Configuration');extra=len(values)-len(keys)
    if extra==1 and sep==';':values=values[:i]+[values[i]+';'+values[i+1]]+values[i+2:]
    else:need(extra==0,'Only the one known AS Configuration semicolon is allowed')
    number=r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?';hits=list(re.finditer(r'(?:^| - )AS_Bui2008\(('+number+r');('+number+r')\)(?= - |$)',values[i]));need(len(values)==len(keys) and len(hits)==1 and values[i].count(';')==values[i].count('AS_Bui2008')==1,'Complete unique AS_Bui2008(0.25;3) token required')
    need(all(struct.pack('<f',float(hits[0][j+1]))==struct.pack('<f',v) for j,v in enumerate((.25,3.))),'Executed coefficient/exponent differs');return dict(zip(keys,values))

def context(notify):
    a=read(AD);need(a['passed'] and a['allowed_job']==TAG and a['ArtificialStressCoef']==.25 and a['ArtificialStressExp']==3 and a['FreeSeepagePondingPolicy']=='CompletedOnly' and a['planned_global_end']==END and a['expected_saved_frames']==FRAMES,'Root explicit one-job epsilon.25/n3 admission required');thread=os.environ.get('CODEX_THREAD_ID');need(not notify or (a['root_thread_id']==THREAD and thread in (None,'',THREAD) and CODEX.is_file()),'Only this admitted same root thread may notify')
    bp=L/'upl_c08_bedkeep_Release_r1.build.json';b=read(bp);need(b['passed'] and b['configuration']=='Release' and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and b['canonical_runtime_old_programs_unchanged'],'Closed original bedkeep Release build required')
    install=L/'upl_c08_formal_r6_runtime_r1.json';ri=read(install);need(ri['passed'],'Closed runtime_r6 installation required');dest={Path(q['destination']['path']).name:q['destination'] for q in ri['files']};runtime=[bind(dest[k]) for k in ('DualSPHysics5.2_GEO_win64.exe','GenCase_win64.exe','DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll')];program=RUNTIME/'DualSPHysics5.2_GEO_win64.exe'
    need(stat(program)==dest[program.name] and (stat(program)['bytes'],stat(program)['mtime_ns'])==(b['program']['bytes'],b['program']['mtime_ns']),'Use the original macro-off runtime_r6 solver, not a trace/experimental program')
    before=[stat(p) for p in (Path(__file__),NOTE,CONFIG,BAT,ROOT,AD,bp,install,PRE,PRE.parent/'Part_Head.ibi4',Path(base.__file__),Path(base.evidence.__file__))]+runtime+[bind(b[k]) for k in ('source_capture','source_archive')];check_input(CONFIG);verify(before)
    for q in psutil.process_iter(['exe','cmdline']):
        try:need(not(q.info['exe'] and Path(q.info['exe']).name.lower().startswith('dualsphysics') and any(v.lower().startswith('-gpu') for v in (q.info['cmdline'] or [])[1:])),'GPU physical target active; no process stopped')
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    return b,bp,program,before,thread

def output_checks():
    r=summary(OUT/'Run.csv');text=(OUT/'Run.out').read_text(encoding='utf-8-sig');parts=sorted((OUT/'data').glob('Part_*.bi4'))
    need(int(r['Steps'])==END and int(r['PartFiles'])==FRAMES and int(r['Np'])==7060 and int(r['Nfixed'])==int(r['Nbound'])==2060 and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')) and 'Gpu_' in r['Hardware'],'Actual GPU30-frame/original registry/no-exclusion differs')
    need('Finished execution (code=0).' in text and 'No Penetration=True' in text and 'ArtificialStress="Bui2008"' in text and 'Dynamic NoPen: '+base.POLICY in text,'Actual normal epsilon.25/n3/fixed-plane execution differs')
    for key,value in (('ArtificialStressCoef',.25),('ArtificialStressExp',3.)):
        matches=re.findall(r'^\s*'+key+r'[:=]\s*([0-9.eE+-]+)\s*$',text,re.M);need(len(matches)==1 and struct.pack('<f',float(matches[0]))==struct.pack('<f',value),'Actual AS coefficient/exponent log differs')
    marker='GravityPreload: release policy=KeepBedOverlap original_target=260 retired=255 kept_bed=5 kept_ids='+','.join(map(str,base.BED_IDS))+'; coordinates/IDs/fixed MK codes retained, bed normal=+DpZ NoSlip.';need(text.count('GravityPreload: phase=released ')==text.count(marker)==1 and 'retired=255; damping=OFF Shepard=OFF FreeSeepage=ON.' in text,'Actual one255/five-kept release differs')
    imported=re.findall(r'GravityPreload: state imported file=.*? actual=([0-9.eE+-]+) completed_step=(\d+);',text);need(len(imported)==1 and int(imported[0][1])==4000000,'Original actual r2GPU PRE import missing');need([p.name for p in parts]==['Part_%04d.bi4'%i for i in range(FRAMES)],'Actual30 contiguous PARTs required');need(not any((OUT/k).exists() for k in ('C08StageTrace.csv','C08CausalTrace.csv','C08CausalTotals.csv')),'Unexpected observer outputs from macro-off physical program')
    return dict(actual_steps=END,saved_frames=FRAMES,summary=r,actual_source_time_from_loader=float(imported[0][0]),Run_csv=stat(OUT/'Run.csv'),Run_out=stat(OUT/'Run.out'),PARTs=[stat(p) for p in parts],Hardware=r['Hardware'])

def queue_once():
    attempt=L/(TAG+'.queue_attempt.json');reply=L/(TAG+'.queue_result.json');need(not attempt.exists() and not reply.exists(),'Existing terminal queue protected; never resend')
    message=('The single admitted C08 AS epsilon.25/exponent3 .30s GPU diagnostic is terminal: '+str(RUN)+'. Verify original start/call/status/owner_admission/root admission, actual creation/exe/argv/parent and Popen/Win32 exits, original macro-off runtime_r6/bedkeep Release source, input/PRE stats. This is120000new updates/global4120000/30planned saves, same original r2GPU10s PRE, hdp1.2/fixed2.5us/keep5/fixedplane/CompletedOnly; only AS coefficient.2->.25 changes physics, exponent3 remains. It is not a repair/physical acceptance and does not replace the PRE with the .52s control. If solver0 and later output review fails, repair only derived checks, never rerun the physical job. Before separately authorized unique native decoding, check active/existing readers and require an adapter for epsilon.25/n3 and this30-frame plan; preserve all22/6805/5000/1805/P0/J/kappa/FS/ledger/keep/plane/clock/signed guards. Do not adopt an old epsilon.2/.5 or n4-specific native acceptance. Preserve actual first failure/partial/last original PART, no invented unsaved failure time. No automatic native/VTK/otherpsi/half/PRE/nextsolver; root decides later work after independent review under ongoing authorization. One45s same-thread queue only; timeout delivery uncertain, never resend/rearm/add watcher.')
    argv=[str(CODEX),'queue','--thread',THREAD,'--message',message];save(attempt,dict(stage=TAG,utc=base.utc(),thread=THREAD,run=stat(RUN),arguments=argv,attempts=1,timeout_s=45,do_not_resend=True));result=dict(stage=TAG,attempts=1,do_not_resend=True)
    try:
        p=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW);result.update(actual_exit=p.returncode,status='queued' if p.returncode==0 else 'queue_failed',stdout=p.stdout,stderr=p.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(reply,result)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');ap.add_argument('--notify',action='store_true');a=ap.parse_args();need(a.execution_authorized and AD.is_file(),'Root full-read and explicit admission required');need(not OUT.exists() and not any(p.name!=AD.name for p in L.glob(TAG+'.*')),'Existing owner/output/partial protected')
    claim=L/(TAG+'.claim.json');save(claim,dict(stage=TAG,owner_pid=os.getpid(),owner_created_epoch=psutil.Process().create_time(),single_attempt=True));before=[];stage='preflight';result=dict(stage=TAG,passed=False,solver_completed=False,physical_acceptance=False,native_review_pending=True,configuration='Release',ArtificialStress=True,keep_bed_overlap=True,expected_active_native_IDs=6805,policy=base.POLICY,ArtificialStressCoef=.25,ArtificialStressExp=3.,free_seepage_policy='CompletedOnly',solver_invocations=0,GenCase_invocations=0,reader_invocations=0,PartVTK_invocations=0,queue_invocations_at_run_seal=0,SHA_scans=0)
    try:
        b,bp,program,before,thread=context(a.notify);before.append(stat(claim));OUT.mkdir();plan=OUT/'planned_steps.csv'
        with plan.open('x',encoding='utf-8',newline='') as f:w=csv.writer(f);w.writerow(('part','completed_step'));w.writerows((i,4000000+(i+1)*4000) for i in range(FRAMES))
        before.append(stat(plan));prefix=OUT/TAG;stage='GenCase';result['GenCase_invocations']=1;result['GenCase_call']=invoke(TAG+'.gencase',[str(RUNTIME/'GenCase_win64.exe'),str(CONFIG.with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml');check_input(seed,True);seed_entries=[stat(Path(str(prefix)+s)) for s in ('.xml','.bi4','_Normals.nbi4')];before+=seed_entries;verify(before);argv=[str(program),'-gpu:0','-stable','-mdbc_freeslip:1',str(prefix),str(OUT),'-dirdataout','data','-svres','-nsteps:'+str(END)];ad=L/(TAG+'.owner_admission.json')
        save(ad,dict(stage=TAG,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(AD),actual_environment_thread=thread,notification_thread=THREAD if a.notify else None,program=stat(program),source_build=stat(bp),source_capture=b['source_capture'],source_archive=b['source_archive'],source_pre_file=stat(PRE),input_xml=stat(seed),seed=seed_entries,planned_steps=stat(plan),planned_new_updates=120000,planned_global_end=END,expected_saved_frames=FRAMES,argv=argv,solver_argv=argv,consumed=before));before.append(stat(ad))
        result.update(program=stat(program),source_build=stat(bp),source_capture=b['source_capture'],source_archive=b['source_archive'],source_pre_file=stat(PRE),input_xml=stat(seed),seed=seed_entries,argv=argv,planned_steps=stat(plan),owner_admission=stat(ad));stage='solver';result['solver_invocations']=1;result['actual_call']=base.owned(TAG,argv,program,False,stat(ad));result.update(solver_completed=True,actual_exit=0,actual_Win32_exit=0);stage='solver_output_review';result.update(output_checks());verify(before);result.update(passed=True,consumed_stats_unchanged=True)
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
