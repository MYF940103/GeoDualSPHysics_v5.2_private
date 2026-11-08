"""One admitted epsilon=.2/exponent3 locality diagnostic; no automatic decoder or next job."""
import argparse,csv,json,os,re,shutil,struct,subprocess
from copy import deepcopy
from pathlib import Path
import psutil
import upl_c08_stage_trace_window_r1 as control
import upl_c08_as05_window_r1 as previous
T,C,L,PRE,SOURCE,base=control.T,control.C,control.L,control.PRE,control.SOURCE,control.base
smoke,repair,trace=control.smoke,control.repair,control.trace
need,read,stat,bind,save,verify=control.need,control.read,control.stat,control.bind,control.save,control.verify
TAG='upl_c08_asn3_window_GPU_r1';UPDATES=264000;CADENCE=4000;FRAMES=66;END='10.66';TOUT='0.01'
THREAD=control.THREAD;CODEX=control.CODEX;BASELINE='upl_c08_stage_trace_window_GPU_r1'
BASE_SEED=T/'outputs'/BASELINE/(BASELINE+'.xml')
trace_identity=control.trace_identity

def baseline_gates():
    entries=previous.baseline_gates();rp=L/'upl_c08_as05_review_r1.json';cp=L/'upl_c08_clustering_plot_r2.check.json';r,c=read(rp),read(cp)
    need(r['review_completed'] and r['implementation_and_native_guards_passed'] and not r['AS05_selected_for_formal'] and not r['default_epsilon_changed'] and not r['physical_acceptance'],'Closed AS05 scientific rejection review required')
    need(c['passed'] and c['analysis_completed'] and c['plot_completed'] and c['current_source_bindings_revalidated'] and c['retained_CSV_rows']==2196 and c['retained_actual_times']==366 and not c['original_CSV_rewritten'],'Closed clustering plot-r2 repair/retained history review required')
    return entries+[stat(p) for p in (rp,cp)]

def make_input():
    root=base.ET.parse(smoke.ROOTXML).getroot();root.find('execution/special/gravitypreload').set('statefile',str(PRE.resolve()));params=root.find('execution/parameters')
    for key,value,comment in (('TimeMax',END,'Bounded single exponent comparison: actual imported PRE plus0.66 s; not formal3 s'),('TimeOut',TOUT,'Bounded comparison save interval0.01 s; retain actual scalar clocks'),('ArtificialStressExp','3','Fixed epsilon0.2/Cubic h1.2dp locality probe; n3 is not a paper-calibrated repair')):
        nodes=[x for x in params if x.get('key')==key];need(len(nodes)==1,'Unique existing input parameter required: '+key);nodes[0].set('value',value);nodes[0].set('comment',comment)
    return root

def signature(node):
    return node.tag,tuple(sorted(node.attrib.items())),(node.text or '').strip(),tuple(signature(x) for x in node)

def check_input(path,generated=False):
    actual=base.ET.parse(path).getroot();expected=make_input()
    if generated:
        source=base.ET.parse(BASE_SEED).getroot();execution=source.find('execution')
        for section in ('special','parameters'):
            old=execution.find(section);index=list(execution).index(old);execution.remove(old);execution.insert(index,deepcopy(expected.find('execution/'+section)))
        expected_names={BASELINE+'_hdp_Actual.vtk':TAG+'_hdp_Actual.vtk',BASELINE+'__Actual.vtk':TAG+'__Actual.vtk'}
        nodes=source.findall('execution/vtkout/vtkfile');need(len(nodes)==2 and {n.get('name') for n in nodes}==set(expected_names),'Exactly two known GenCase VTK filename labels required')
        for node in nodes:node.set('name',expected_names[node.get('name')])
        expected=source;actual.attrib.pop('date',None);expected.attrib.pop('date',None)
    need(signature(actual)==signature(expected),'Only TimeMax/TimeOut/AS exponent/source binding and declared comments plus exact generated VTK labels/date may differ; all other body physics remain literal')
    event=actual.find('execution/special/gravitypreload');source=Path(event.get('statefile',''))
    need(source.is_absolute() and source.is_file() and source.samefile(PRE),'Original absolute same-backend PRE required')

def summary(path):
    lines=Path(path).read_text(encoding='utf-8-sig').splitlines();need(len(lines)==2,'Exactly one Run.csv header and data row required');match=re.match(r'^#?RunName([;,])',lines[0]);need(match is not None,'Unsupported Run.csv header')
    sep=match[1];header=lines[0][1:] if lines[0].startswith('#') else lines[0];keys=header.split(sep);values=lines[1].split(sep)
    need(len(set(keys))==len(keys) and all(keys) and keys.count('Configuration')==1,'Unique nonempty keys and one Configuration required');index=keys.index('Configuration');extra=len(values)-len(keys)
    if extra==1 and sep==';':values=values[:index]+[values[index]+';'+values[index+1]]+values[index+2:]
    else:need(extra==0,'Only one embedded AS Configuration semicolon is admitted')
    configuration=values[index];number=r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?';matches=list(re.finditer(r'(?:^| - )AS_Bui2008\(('+number+r');('+number+r')\)(?= - |$)',configuration))
    need(len(matches)==1 and configuration.count(';')==configuration.count('AS_Bui2008')==1,'Complete unique AS_Bui2008(0.2;3) token required')
    need(all(struct.pack('<f',float(matches[0][j+1]))==struct.pack('<f',v) for j,v in enumerate((.2,3.))),'Actual Run.csv AS coefficient/exponent differs from0.2f/3f');need(len(values)==len(keys),'Reconstructed width differs')
    return dict(zip(keys,values))

def normal_output(out):
    r=summary(out/'Run.csv');text=(out/'Run.out').read_text(encoding='utf-8-sig');parts=sorted((out/'data').glob('Part_*.bi4'))
    need(int(r['Steps'])==SOURCE+UPDATES and int(r['PartFiles'])==FRAMES and int(r['Np'])==7060 and int(r['Nbound'])==int(r['Nfixed'])==2060 and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'Actual registry/steps/frames/no-exclusion differs')
    need('Finished execution (code=0).' in text and 'No Penetration=True' in text and 'ArtificialStress="Bui2008"' in text and 'Dynamic NoPen: '+base.POLICY in text,'Actual normal AS1/fixed-plane mode differs')
    for key,value in (('ArtificialStressCoef',.2),('ArtificialStressExp',3.)):
        values=base.re.findall(r'^\s*'+key+r'[:=]\s*([0-9.eE+-]+)\s*$',text,base.re.M);need(len(values)==1 and struct.pack('<f',float(values[0]))==struct.pack('<f',value),'Actual AS log differs')
    marker='GravityPreload: release policy=KeepBedOverlap original_target=260 retired=255 kept_bed=5 kept_ids='+','.join(map(str,base.BED_IDS))+'; coordinates/IDs/fixed MK codes retained, bed normal=+DpZ NoSlip.'
    need(text.count('GravityPreload: phase=released ')==1 and text.count(marker)==1 and 'retired=255; damping=OFF Shepard=OFF FreeSeepage=ON.' in text,'Actual one255/five-kept release differs')
    imported=base.re.findall(r'GravityPreload: state imported file=.*? actual=([0-9.eE+-]+) completed_step=(\d+);',text);need(len(imported)==1 and int(imported[0][1])==SOURCE,'Original source clock/import missing')
    need([p.name for p in parts]==['Part_%04d.bi4'%i for i in range(FRAMES)],'Actual native sequence differs')
    return dict(actual_steps=SOURCE+UPDATES,saved_frames=FRAMES,summary=r,actual_source_time_from_loader=float(imported[0][0]),Run_csv=stat(out/'Run.csv'),Run_out=stat(out/'Run.out'),PARTs=[stat(p) for p in parts],**trace_identity(out))

def notify_once(check):
    need(not any((L/(TAG+s)).exists() for s in ('.queue_attempt.json','.queue_result.json')),'A terminal queue attempt already exists; never resend')
    message=('The explicitly admitted C08 epsilon.2/exponent3 single-factor complete-body locality .66 s GPU window is terminal. Read '+str(check)+' and original start/call/status/owner_admission/root admission; verify owned creation/exe/argv/parent, real Win32/Popen exits and program/PRE/input stats first. This is only tau .66 s,264000 new updates,66 planned saves, AS1 epsilon.2 exponent3/Cubic hdp1.2/fixed-plane/keep5, not physical acceptance. The original r2 GPU10 s PRE was reused, not rerun. C08StageTrace.csv observes IDs5809/4956/4959 every40 steps before tau .60 and every step from .60 to .66. Never rearm this old owner. This owner starts no further solver; after independent native and physical review, root decides the next development stage under the existing user authorization. On failure preserve the first real error and partials, without inventing unsaved native time. Before any reader invocation check existing/active readers; only a separately reviewed66-frame6805-ID reader and window CSV review may be authorized. Keep all original22/P0/J/ledger/FS/keep/clock/signed guards and scalar clocks; the separately built n3 native adapter must expect epsilon.2/exponent3, not the old exponent2.55 or AS05 metadata. This is one mathematical locality diagnostic, not a paper-calibrated repair. No new SPR/HG/filter/FOS action is admitted. No automatic native/VTK, other psi, half-step chain or source restart. This terminal queue is attempted once with45 s timeout; delivery may be uncertain after timeout, so never resend or add a watcher.')
    argv=[str(CODEX),'queue','--thread',THREAD,'--message',message]
    save(L/(TAG+'.queue_attempt.json'),dict(stage=TAG,utc=base.utc(),thread=THREAD,run=stat(check),arguments=argv,attempts=1,timeout_s=45,do_not_resend=True))
    result=dict(stage=TAG,attempts=1,do_not_resend=True)
    try:
        q=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW);result.update(actual_exit=q.returncode,status='queued' if q.returncode==0 else 'queue_failed',stdout=q.stdout,stderr=q.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(L/(TAG+'.queue_result.json'),result)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execution-authorized',action='store_true');ap.add_argument('--notify',action='store_true');a=ap.parse_args();need(a.execution_authorized,'Root full-read and explicit single-window admission required')
    need(not a.notify or (os.environ.get('CODEX_THREAD_ID')==THREAD and CODEX.is_file()),'Only explicit root-started same-thread terminal notification is allowed')
    out=T/'outputs'/TAG;config=T/'configs'/(TAG+'_Def.xml');rp=L/(TAG+'.run.json');root_ad=L/(TAG+'.admission.json')
    need(not out.exists() and not config.exists() and not any(p.name!=root_ad.name for p in L.glob(TAG+'.*')),'Existing/partial job preserved; no retry')
    before=[];result=dict(stage=TAG,passed=False,configuration='Release',physical_acceptance=False,solver_invocations=0,reader_invocations=0,queue_invocations_at_run_seal=0,terminal_queue_requested=a.notify,SHA_scans=0,native_review_pending=True,keep_bed_overlap=True,expected_active_native_IDs=6805,ArtificialStress=True,ArtificialStressCoef=.2,ArtificialStressExp=3.,policy=base.POLICY,comparison='single exponent2.55 to3 at epsilon.2/Cubic hdp1.2; not a proven repair')
    try:
        ad=read(root_ad);need(ad['passed'] and ad['allowed_job']==TAG,'Root explicit admission for this one window required');need(ad['ArtificialStressCoef']==.2 and ad['ArtificialStressExp']==3,'Only explicit epsilon.2/exponent3 root admission is valid');gates=baseline_gates()
        bp=L/'upl_c08_stage_trace_Release_r1.build.json';b=read(bp);need(b['passed'] and b['configuration']=='Release' and b['actual_typed_exit_code']==b['actual_Win32_exit']==0 and b['source_stats_unchanged'] and b['trace_macro_enabled'] and b['trace_macro']=='C08_STAGE_TRACE' and b['environment_macro']['appended']=={'CL':'/DC08_STAGE_TRACE','NVCC_PREPEND_FLAGS':'-DC08_STAGE_TRACE'} and len(b['project_objects'])==113,'Closed macro-enabled Release build required')
        need(Path(b['source_capture']['path']).samefile(T/'outputs/upl_c08_stage_trace_source_r1/source.json'),'Isolated trace source capture required');program=Path(bind(b['program'])['path'])
        need(bind(read(smoke.locations('Release')[2])['program'])==stat(program),'Use the same actually checked Release program')
        before=[stat(p) for p in (Path(__file__),T/'notes/upl_c08_asn3_window_r1.md',T/'configs/xCaseLianSaturatedColumnCollapse_asn3_window_r1_win64_GPU.bat',Path(previous.__file__),Path(control.__file__),Path(smoke.__file__),Path(repair.__file__),Path(trace.__file__),Path(base.__file__),Path(base.summary.__code__.co_filename),T/'support/mdbc_partition_components_r3.py',smoke.ROOTXML,bp,root_ad,PRE,PRE.parent/'Part_Head.ibi4')]+gates+[bind(b[k]) for k in ('program','source_capture','source_archive')];runtime=[]
        for leaf in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll'):
            origin=C/'support/runtime_r5'/leaf;old=stat(origin);dest=program.parent/leaf
            if not dest.exists():shutil.copy2(origin,dest)
            copied=stat(dest);need((copied['bytes'],copied['mtime_ns'])==(old['bytes'],old['mtime_ns']),'Existing/new runtime copy differs');before.extend((old,copied));runtime.append(copied)
        for q in psutil.process_iter(['exe','cmdline']):
            try:
                exe=q.info['exe'];argv=q.info['cmdline'] or [];need(not(exe and Path(exe).name.lower().startswith('dualsphysics') and any(v.lower().startswith('-gpu') for v in argv[1:])),'GPU physical target active; no process stopped')
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        root=make_input()
        with config.open('xb') as f:f.write(base.ET.tostring(root,encoding='utf-8',xml_declaration=True)+b'\n')
        check_input(config);before.append(stat(config));gen=C/'support/runtime_r5/GenCase_win64.exe';before.append(stat(gen));prefix=out/TAG
        result['GenCase_call']=base.invoke(TAG+'.gencase',[str(gen),str(config.with_suffix('')),str(prefix),'-save:all'],C);seed=Path(str(prefix)+'.xml');check_input(seed,generated=True);before.extend(stat(Path(str(prefix)+s)) for s in ('.xml','.bi4','_Normals.nbi4'))
        plan=out/'planned_steps.csv'
        with plan.open('x',encoding='utf-8',newline='') as f:
            writer=csv.writer(f);writer.writerow(('part','completed_step'));writer.writerows((i,SOURCE+(i+1)*CADENCE) for i in range(FRAMES))
        before.append(stat(plan));argv=[str(program),'-gpu:0','-stable','-mdbc_freeslip:1',str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:'+str(SOURCE+UPDATES)]
        admission=L/(TAG+'.owner_admission.json');save(admission,dict(stage=TAG,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(root_ad),program=stat(program),source_build=stat(bp),source_pre_file=stat(PRE),planned_steps=stat(plan),planned_new_updates=UPDATES,planned_global_end=SOURCE+UPDATES,expected_saved_frames=FRAMES,argv=argv,solver_argv=argv,consumed=before))
        result['solver_invocations']=1;result['actual_call']=base.owned(TAG,argv,program,False,stat(admission));result.update(normal_output(out));verify(before);result.update(passed=True,actual_exit=0,actual_Win32_exit=0,program=stat(program),source_build=stat(bp),input_xml=stat(seed),source_pre_file=stat(PRE),runtime=runtime,consumed_stats_unchanged=True)
    except Exception as error:
        result['first_failure']=str(error);cp=L/(TAG+'.call.json')
        if cp.exists():
            call=read(cp);result.update(actual_call=stat(cp),actual_exit=call['actual_solver_Win32_exit'],actual_Win32_exit=call['actual_solver_Win32_exit'],actual_tool_exit=call['actual_Popen_wait_exit'],ownership_errors=call['ownership_errors'])
    result.update(consumed=before,last_original_console_line=base.last_part(out));save(rp,result);base.publish(TAG,out,None,None,'completed_pending_native' if result['passed'] else 'failed_preserved_pending_diagnosis')
    if a.notify and result['solver_invocations']:notify_once(rp)
    print(json.dumps(dict(passed=result['passed'],receipt=str(rp),first_failure=result.get('first_failure'))),flush=True);return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
