"""One original raw-FS epsilon.5/exponent2.55 window; no automatic native/next job."""
import argparse,csv,json,os,re,xml.etree.ElementTree as ET,subprocess
from pathlib import Path
import psutil
import c08_h18_as05_n5_r1 as previous
matrix=previous.matrix

base=matrix.base
T,C,L=matrix.T,matrix.C,matrix.L
need,read,stat,bind,save,invoke=matrix.need,matrix.read,matrix.stat,matrix.bind,matrix.save,matrix.invoke
TAG='c08_h18_as05_n255_r1';NOTE=T/'notes'/(TAG+'.md')
CONFIG=T/'configs'/(TAG+'_Def.xml');PREP=L/(TAG+'.prepare.json');ADMISSION=L/(TAG+'.admission.json')
CONTROL='c08_h18_wend_psi0_a05_w09_r1';CONTROL_RUN=L/(CONTROL+'.run.json');CONTROL_AD=L/(CONTROL+'.admission.json')
THREAD=matrix.THREAD


def original_context():
    values=previous.original_context() # Exactly once per prepare/run phase; never calls the n5 owner.
    values[-1].extend(stat(q) for q in (Path(__file__),NOTE))
    return values


def with_exponent(root):
    nodes=root.findall("execution/parameters/parameter[@key='ArtificialStressExp']");need(len(nodes)==1,'One existing exponent required');nodes[0].set('value','2.55');nodes[0].set('comment','Single exponent2.55 parameter diagnostic; epsilon0.5 and CompletedOnly policy unchanged');return root


def check_input(path,control_config,generated=False):
    actual=ET.parse(path).getroot();expected=with_exponent(ET.parse(control_config).getroot())
    sections=('execution/special','execution/parameters','execution/constants','execution/particles') if generated else (None,)
    need(all(matrix.signature(actual if key is None else actual.find(key))==matrix.signature(expected if key is None else expected.find(key)) for key in sections),'Only the original AS.5 exponent3.825->2.55 numerical input difference is allowed')
    pars={q.get('key'):q.get('value') for q in actual.findall('execution/parameters/parameter')}
    need(matrix.f32(pars['ArtificialStressCoef'])==matrix.f32(.5) and matrix.f32(pars['ArtificialStressExp'])==matrix.f32(2.55) and float(pars['DtFixed'])==5e-6 and float(pars['TimeMax'])==10.9 and float(pars['TimeOut'])==.01,'Explicit epsilon.5/exponent2.55/full window values differ')
    return actual


def prepare():
    need(not CONFIG.exists() and not PREP.exists() and not (T/'outputs'/TAG).exists() and not any(L.glob(TAG+'.*')),'Existing n255 preparation/output protected')
    control,admission,config,build,program,material,runtime,window,preload,consumed=original_context()
    raw=config.read_bytes();pattern=rb'(<parameter\s+key="ArtificialStressExp"\s+value=")3\.825("\s+comment=")[^"]*(")'
    need(len(re.findall(pattern,raw))==1,'One exact original exponent/comment line required; preserve XML formatting')
    match=re.search(pattern,raw);replacement=match[1]+b'2.55'+match[2]+b'Single exponent2.55 parameter diagnostic; epsilon0.5 and CompletedOnly policy unchanged'+match[3]
    changed=raw[:match.start()]+replacement+raw[match.end():]
    need(changed.count(replacement)==1 and changed.replace(replacement,match[0],1)==raw,'Inverse exponent/comment replacement must recover exact original XML bytes')
    with CONFIG.open('xb') as handle:handle.write(changed)
    check_input(CONFIG,config);matrix.verify(consumed)
    save(PREP,dict(stage=TAG+'.prepare',prepared_only=True,exact_inverse_original_XML_bytes=True,native_reader_requires_separate_n255_adapter=True,control_run=stat(CONTROL_RUN),control_configuration=stat(config),configuration=stat(CONFIG),program=stat(program),source_build=control['source_build'],source_capture=control['source_capture'],source_archive=control['source_archive'],source_pre_file=stat(matrix.PRE),planned_steps=stat(matrix.PLAN),planned_global_end=2180000,expected_saved_frames=91,AS_coefficient=.5,control_AS_exponent=3.825,AS_exponent=2.55,only_numerical_input_difference='ArtificialStressExp 3.825 -> 2.55',consumed=consumed,consumed_stats_unchanged=True,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,VTK_invocations=0,SHA_scans=0,physical_acceptance=False))


def context():
    control,prior,config,build,program,material,runtime,window,preload,consumed=original_context();prepared=read(PREP);admission=read(ADMISSION)
    need(prepared['stage']==TAG+'.prepare' and prepared['prepared_only'] and prepared['configuration']==stat(CONFIG) and prepared['control_configuration']==stat(config) and prepared['control_run']==stat(CONTROL_RUN) and prepared['exact_inverse_original_XML_bytes'] and prepared['consumed_stats_unchanged'] and prepared['AS_coefficient']==.5 and prepared['AS_exponent']==2.55,'Exact separately prepared n255 input required');check_input(CONFIG,config)
    need(admission['passed'] and admission['allowed_job']==TAG and admission['prepared']==stat(PREP) and admission['input_xml']==stat(CONFIG) and admission['control_run']==stat(CONTROL_RUN) and admission['independent_parameter_admission'] is True and admission['original_AS05_reviewed'] is True and admission['planned_steps']==stat(matrix.PLAN) and admission['planned_global_end']==2180000 and admission['expected_saved_frames']==91 and admission['AS_coefficient']==.5 and admission['AS_exponent']==2.55 and admission['native_auto_authorized'] is False and admission['terminal_queue_once'] is True,'Distinct independent root parameter admission after full-read required')
    for key in ('program','source_build','source_capture','source_archive','source_pre_file'):
        need(bind(admission[key])==bind(control[key]) and bind(prepared[key])==bind(control[key]),'Only frozen original raw-FS schema2 control binding allowed: '+key)
    need(admission['root_thread_id']==os.environ.get('CODEX_THREAD_ID')==THREAD and matrix.notifier_path() is not None,'Actual admitted root thread/current notifier required')
    consumed.extend(stat(q) for q in (PREP,ADMISSION,CONFIG));consumed.extend(bind(q) for q in prepared['consumed']);consumed.append(bind(admission['original_physical_review']))
    matrix.verify(consumed);matrix.old.old.idle(True)
    return control,prior,build,program,material,runtime,window,preload,consumed


def summary(path):
    lines=Path(path).read_text(encoding='utf-8-sig').splitlines();need(len(lines)==2,'One actual Run.csv header/data row required');match=re.match(r'^#?RunName([;,])',lines[0]);need(match,'Known Run.csv delimiter required');sep=match[1];keys=lines[0].lstrip('#').split(sep);values=lines[1].split(sep);need(len(set(keys))==len(keys) and keys.count('Configuration')==1,'Unique Run.csv keys required');at=keys.index('Configuration')
    if len(values)==len(keys)+1 and sep==';':values=values[:at]+[values[at]+';'+values[at+1]]+values[at+2:]
    need(len(values)==len(keys),'Only the known single AS semicolon is repairable');number=r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?';hits=re.findall(r'(?:^| - )AS_Bui2008\(('+number+r');('+number+r')\)(?= - |$)',values[at]);need(len(hits)==1 and values[at].count(';')==values[at].count('AS_Bui2008')==1 and matrix.f32(hits[0][0])==matrix.f32(.5) and matrix.f32(hits[0][1])==matrix.f32(2.55),'Actual complete epsilon.5/exponent2.55 token required');return dict(zip(keys,values))


def output_checks(out,preload):
    observed=summary(out/'Run.csv');text=(out/'Run.out').read_text(encoding='utf-8-sig');parts=sorted((out/'data').glob('Part_*.bi4'))
    need(int(observed['Steps'])==2180000 and int(observed['PartFiles'])==91 and int(observed['Np'])==7060 and int(observed['Nfixed'])==int(observed['Nbound'])==2060 and all(int(observed[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')) and 'Gpu_' in observed['Hardware'] and float(observed['H'])==.072 and float(observed['Dp'])==.04,'Actual full91 GPU/no-loss registry differs')
    need('Kernel="Wendland"' in text and 'Finished execution (code=0).' in text and '[Simulation INTERRUPTED' not in text and 'No Penetration=True' in text and 'Dynamic NoPen: '+base.POLICY in text and text.count('GravityPreload: phase=released ')==1 and text.count('GravityPreload: validated native right-wall range=[1805,2060), count=255.')==1 and 'retired=255; damping=OFF Shepard=OFF FreeSeepage=ON.' in text,'Actual completion/kernel/release/NoPen differs')
    for key,value in (('ArtificialStressCoef',.5),('ArtificialStressExp',2.55)):
        hits=re.findall(r'^\s*'+key+r'[:=]\s*([0-9.eE+-]+)\s*$',text,re.M);need(len(hits)==1 and matrix.f32(hits[0])==matrix.f32(value),'Actual explicit AS log differs')
    imported=re.findall(r'GravityPreload: state imported file=.*? actual=([0-9.eE+-]+) completed_step=(\d+);',text)
    need(len(imported)==1 and int(imported[0][1])==2000000 and float(imported[0][0])==preload['preload_actual_end_s'] and [q.name for q in parts]==['Part_%04d.bi4'%i for i in range(91)],'Actual source import/full PART sequence differs')
    return dict(actual_steps=2180000,saved_frames=91,summary=observed,actual_source_time_from_loader=float(imported[0][0]),Run_csv=stat(out/'Run.csv'),Run_out=stat(out/'Run.out'),PARTs=[stat(q) for q in parts])


def notify_once(run_path):
    attempt=L/(TAG+'.queue_attempt.json');reply=L/(TAG+'.queue_result.json');need(not attempt.exists() and not reply.exists() and os.environ.get('CODEX_THREAD_ID')==THREAD,'One actual-root terminal queue only; never resend/rearm')
    program=matrix.notifier_path();message=('The single admitted original/raw-FS epsilon.5/exponent2.55 C08 window is terminal: '+str(run_path)+'. Read original run/start/call/status/root+owner admission and actual exits/PRE/program/source/input/full91plan. Only ArtificialStressExp3.825->2.55 changed from completed originalAS05; the private FS-normal candidate is not selected or carried forward. Original AV.1/damping/theta/NoPen/material/5us/PRE/180k/2180000/91 remain. Existing full native reader permits only3.825/3/5: exponent2.55 requires a separately reviewed narrow adapter and root admission later, never automatic. No decoder/VTK/next/PRE/half/control/otherpsi, no physical acceptance fromexit0. Preserve failures/partials/actual last console; no unsaved reconstruction. Actual-root current-Codex terminal queue once45s, no resend/rearm/watcher.')
    argv=[str(program) if program else 'codex','queue','--thread',THREAD,'--message',message];save(attempt,dict(stage=TAG,run=stat(run_path),thread=THREAD,program=stat(program) if program else None,arguments=argv,attempts=1,timeout_s=45,do_not_resend=True));result=dict(stage=TAG,attempts=1,do_not_resend=True)
    try:
        need(program is not None,'Current notifier missing; preserve terminal evidence without retry');done=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW);result.update(actual_exit=done.returncode,status='queued' if done.returncode==0 else 'queue_failed',stdout=done.stdout,stderr=done.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(reply,result)


def run():
    out=T/'outputs'/TAG;run_path=L/(TAG+'.run.json');need(not out.exists() and not any(q.name not in {PREP.name,ADMISSION.name} for q in L.glob(TAG+'.*')),'Existing job/partial protected; external launcher prefix must differ')
    claim=L/(TAG+'.claim.json');save(claim,dict(stage=TAG,owner_pid=os.getpid(),owner_created_epoch=psutil.Process().create_time(),single_attempt=True));consumed=[];phase='preflight';result=dict(stage=TAG,passed=False,solver_completed=False,physical_acceptance=False,native_review_pending=True,native_reader_requires_separate_n255_adapter=True,automatic_next_job=False,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,VTK_invocations=0,SHA_scans=0)
    try:
        control,prior,build,program,material,runtime,window,preload,consumed=context();consumed.append(stat(claim));out.mkdir();prefix=out/TAG;gen=next(q for q in runtime if Path(q['path']).name=='GenCase_win64.exe')
        phase='GenCase';result['GenCase_invocations']=1;result['GenCase_call']=invoke(TAG+'.gencase',[gen['path'],str(CONFIG.with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml');actual=check_input(seed,control['input_xml']['path'],True);seeds=[stat(Path(str(prefix)+suffix)) for suffix in ('.xml','.bi4','_Normals.nbi4')];consumed.extend(seeds)
        profile=out/'native_profile.csv';values=matrix.actual_material(actual);matrix.match_material(values,material);pars={q.get('key'):q.get('value') for q in actual.findall('execution/parameters/parameter')};values.update(ArtificialStressCoef=pars['ArtificialStressCoef'],ArtificialStressExp=pars['ArtificialStressExp'])
        with profile.open('x',encoding='utf-8',newline='') as handle:writer=csv.writer(handle);writer.writerow(('key','value'));writer.writerows(values.items())
        consumed.append(stat(profile));matrix.verify(consumed);argv=[str(program),'-gpu:0','-stable','-mdbc_freeslip:1',str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:2180000'];need(argv[1:4]==control['argv'][1:4] and argv[6:]==control['argv'][6:],'Only fresh input/output labels may change in original solver argv');owner=L/(TAG+'.owner_admission.json')
        closure={key:control[key] for key in ('program','source_build','source_capture','source_archive','source_pre_file','source_run','source_native')}
        save(owner,dict(stage=TAG,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(ADMISSION),**closure,runtime=runtime,input_xml=stat(seed),seed=seeds,planned_steps=stat(matrix.PLAN),planned_global_end=2180000,expected_saved_frames=91,planned_new_updates=180000,native_reader_requires_separate_n255_adapter=True,group='psi0',Kernel=2,AS_coefficient=.5,AS_exponent=2.55,control_run=stat(CONTROL_RUN),only_numerical_input_difference='ArtificialStressExp 3.825 -> 2.55',argv=argv,solver_argv=argv,consumed=consumed));consumed.append(stat(owner))
        result.update(**closure,runtime=runtime,input_xml=stat(seed),seed=seeds,planned_steps=stat(matrix.PLAN),native_profile=stat(profile),owner_admission=stat(owner),argv=argv,group='psi0',kernel=2,kernel_name='Wendland',AS_coefficient=.5,AS_exponent=2.55,control_run=stat(CONTROL_RUN),only_numerical_input_difference='ArtificialStressExp 3.825 -> 2.55',geometry_profile='bedroles',keep_bed_overlap=False,hdp=1.8,fixed_dt_s=5e-6)
        phase='solver';result['solver_invocations']=1;result['actual_call']=base.owned(TAG,argv,program,False,stat(owner));result.update(actual_exit=0,actual_Win32_exit=0,actual_tool_exit=0);phase='runtime_review';result.update(output_checks(out,preload));matrix.verify(consumed);result.update(passed=True,solver_completed=True,consumed_stats_unchanged=True)
    except Exception as error:result.update(first_failure=str(error),failed_stage=phase)
    call_path=L/(TAG+'.call.json')
    if call_path.exists():
        actual=read(call_path);result.update(actual_call=stat(call_path),actual_exit=actual['actual_solver_Win32_exit'],actual_Win32_exit=actual['actual_solver_Win32_exit'],actual_tool_exit=actual['actual_Popen_wait_exit'],ownership_errors=actual['ownership_errors'])
    if (out/'Run.out').exists():
        text=(out/'Run.out').read_text(encoding='utf-8-sig',errors='replace');hit=re.search(r'^Text: (.+)$',text,re.M);parts=sorted((out/'data').glob('Part_*.bi4'))
        result.update(Run_out=stat(out/'Run.out'),first_engine_exception_text=hit[1] if hit else None,reported_wall_rejection_lines=[q for q in text.splitlines() if q.startswith('DynamicPoreWall rejected:')],observed_saved_files=len(parts),PARTs=[stat(q) for q in parts])
    unchanged=False
    try:unchanged=all(stat(q['path'])==q for q in consumed)
    except Exception as error:result['terminal_stat_error']=str(error)
    if not unchanged:result['passed']=False
    result.update(consumed=consumed,consumed_stats_unchanged=unchanged,last_original_console_line=base.last_part(out),unsaved_state_reconstructed=False,unsaved_failure_time_reconstructed=False,native_invocation_authorized_by_this_owner=False);save(run_path,result);base.publish(TAG,out,None,None,'completed_pending_explicit_native_review' if result['solver_completed'] else 'failed_preserved_no_next_job')
    if call_path.exists():notify_once(run_path)
    return 0 if result['passed'] else (result.get('actual_exit') or 1)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','run'));parser.add_argument('--execution-authorized',action='store_true');args=parser.parse_args();need(args.execution_authorized,'Author-only until root full-read and separate preparation/run authorization')
    prepare() if args.action=='prepare' else exit(run())

