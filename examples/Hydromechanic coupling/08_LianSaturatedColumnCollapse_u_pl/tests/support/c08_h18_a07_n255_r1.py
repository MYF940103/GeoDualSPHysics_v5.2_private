"""One original raw-FS epsilon.7/exponent2.55 comparison to completed AS.5/n2.55; never auto-native."""
import argparse,csv,json,os,re,xml.etree.ElementTree as ET,subprocess
from pathlib import Path
import psutil
import c08_h18_as05_n255_r1 as previous
matrix=previous.matrix

base=matrix.base
T,C,L=matrix.T,matrix.C,matrix.L
need,read,stat,bind,save,invoke=matrix.need,matrix.read,matrix.stat,matrix.bind,matrix.save,matrix.invoke
TAG='c08_h18_a07_n255_r1';NOTE=T/'notes'/(TAG+'.md')
CONFIG=T/'configs'/(TAG+'_Def.xml');PREP=L/(TAG+'.prepare.json');ADMISSION=L/(TAG+'.admission.json')
CONTROL='c08_h18_as05_n255_r1';CONTROL_RUN=L/(CONTROL+'.run.json');CONTROL_AD=L/(CONTROL+'.admission.json')
NATIVE=L/'c08_h18_n255_native_run_r1.check.json';REVIEW=L/'c08_h18_n255_review_r1.check.json';ADAPTER=L/'c08_h18_n255_review_r1.adapter.json'
THREAD=matrix.THREAD


def original_context():
    original,oldad,oldconfig,build,program,material,runtime,window,preload,consumed=previous.original_context() # Once per phase.
    control=read(CONTROL_RUN);prior=read(CONTROL_AD);native=read(NATIVE);review=read(REVIEW);adapter=read(ADAPTER)
    need(control['stage']==CONTROL and control['passed'] and control['solver_completed'] and control['actual_exit']==control['actual_Win32_exit']==0 and control['actual_steps']==2180000 and control['saved_frames']==91 and control['consumed_stats_unchanged'] and control['AS_coefficient']==.5 and control['AS_exponent']==2.55,'Genuine completed AS05/n2.55 control required')
    for key in ('program','source_build','source_capture','source_archive','source_pre_file'):need(bind(control[key])==bind(original[key]),'N255 must retain original raw-FS schema2 closure: '+key)
    call=read(bind(control['actual_call'])['path']);need(call['actual_solver_Win32_exit']==call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and not call['ownership_errors'],'Actual N255 owned solver exits differ')
    config=Path(bind(prior['input_xml'])['path']);previous.check_input(config,oldconfig);previous.check_input(bind(control['input_xml'])['path'],original['input_xml']['path'],True)
    need(prior['passed'] and prior['allowed_job']==CONTROL and prior['AS_coefficient']==.5 and prior['AS_exponent']==2.55 and native['passed'] and native['consumed_stats_unchanged'] and native['reader_invocations']==1,'Passed actual N255 admission/native read required')
    done=read(bind(native['native_completion'])['path']);meta=read(bind(native['metadata'])['path']);reader=read(bind(native['reader_build'])['path']);nc=read(bind(native['actual_call'])['path'])
    need(done['passed'] and done['stage']=='c08_h18_wend_native_r1.receiver' and done['samples']==91 and done['completed_steps']==2180000 and done['typed_arrays']==22 and meta['passed'] and matrix.f32(meta['AS_coefficient_float_reference'])==matrix.f32(.5) and matrix.f32(meta['AS_exponent_float_reference'])==matrix.f32(2.55),'Exact full91 native N255 profile required')
    need(reader['passed'] and reader['consumed_stats_unchanged'] and nc['actual_Popen_wait_exit']==nc['actual_Win32_exit']==0 and nc['ownership_failure'] is None and Path(nc['program']).samefile(bind(reader['program'])['path']),'Actual N255 reader program/exit differs')
    need(review['analysis_complete'] and review['consumed_stats_unchanged'] and not review['physical_acceptance'] and review['exact_matching_option_rows']==91 and any(q['tag']==CONTROL and q['actual_samples']==91 for q in review['receiver_summaries']) and adapter['stats_unchanged'] and adapter['analysis_check']==stat(REVIEW),'Completed independent N255 analysis/binding required; no physical acceptance inferred')
    consumed.extend(stat(q) for q in (Path(__file__),NOTE,CONTROL_RUN,CONTROL_AD,NATIVE,REVIEW,ADAPTER,config))
    consumed.extend(bind(control[q]) for q in ('actual_call','input_xml','native_profile'));consumed.extend(bind(native[q]) for q in ('native_completion','metadata','reader_build','actual_call'));consumed.append(bind(reader['program']))
    matrix.verify(consumed)
    return control,prior,config,build,program,material,runtime,window,preload,consumed


def with_coefficient(root):
    nodes=root.findall("execution/parameters/parameter[@key='ArtificialStressCoef']");need(len(nodes)==1 and matrix.f32(nodes[0].get('value'))==matrix.f32(.5),'One prior AS0.5 coefficient required');nodes[0].set('value','0.7');nodes[0].set('comment','Single coefficient0.5 to0.7 comparison at fixed exponent2.55; all other numerical inputs unchanged')
    exp=root.findall("execution/parameters/parameter[@key='ArtificialStressExp']");need(len(exp)==1 and matrix.f32(exp[0].get('value'))==matrix.f32(2.55),'Prior exponent2.55 must stay fixed');exp[0].set('comment','AS exponent retained at2.55 for the coefficient comparison; CompletedOnly unchanged');return root


def check_input(path,control_config,generated=False):
    actual=ET.parse(path).getroot();expected=with_coefficient(ET.parse(control_config).getroot())
    sections=('execution/special','execution/parameters','execution/constants','execution/particles') if generated else (None,)
    need(all(matrix.signature(actual if key is None else actual.find(key))==matrix.signature(expected if key is None else expected.find(key)) for key in sections),'Only coefficient0.5->0.7 at exponent2.55 may differ from the completed N255 control')
    pars={q.get('key'):q.get('value') for q in actual.findall('execution/parameters/parameter')}
    need(matrix.f32(pars['ArtificialStressCoef'])==matrix.f32(.7) and matrix.f32(pars['ArtificialStressExp'])==matrix.f32(2.55) and float(pars['DtFixed'])==5e-6 and float(pars['TimeMax'])==10.9 and float(pars['TimeOut'])==.01,'Explicit epsilon.7/exponent2.55/full window values differ')
    return actual


def prepare():
    need(not CONFIG.exists() and not PREP.exists() and not (T/'outputs'/TAG).exists() and not any(L.glob(TAG+'.*')),'Existing n255 preparation/output protected')
    control,admission,config,build,program,material,runtime,window,preload,consumed=original_context()
    raw=config.read_bytes();cp=rb'(<parameter\s+key="ArtificialStressCoef"\s+value=")0\.5("\s+comment=")[^"]*(")';ep=rb'(<parameter\s+key="ArtificialStressExp"\s+value="2\.55"\s+comment=")[^"]*(")'
    need(len(re.findall(cp,raw))==len(re.findall(ep,raw))==1,'One coefficient value/comment and one exponent comment required')
    c,e=re.search(cp,raw),re.search(ep,raw);cb,eb=c[0],e[0]
    ca=c[1]+b'0.7'+c[2]+b'Single coefficient0.5 to0.7 comparison at fixed exponent2.55; all other numerical inputs unchanged'+c[3]
    ea=e[1]+b'AS exponent retained at2.55 for the coefficient comparison; CompletedOnly unchanged'+e[2]
    changed=raw.replace(cb,ca,1).replace(eb,ea,1)
    need(changed.count(ca)==changed.count(ea)==1 and changed.replace(ea,eb,1).replace(ca,cb,1)==raw,'Exact inverse must recover both original N255 lines and all XML bytes')
    with CONFIG.open('xb') as handle:handle.write(changed)
    check_input(CONFIG,config);matrix.verify(consumed)
    save(PREP,dict(stage=TAG+'.prepare',prepared_only=True,prior_N255_review=stat(REVIEW),prior_N255_adapter=stat(ADAPTER),exact_inverse_original_XML_bytes=True,native_reader_requires_separate_a07_n255_adapter=True,control_run=stat(CONTROL_RUN),control_configuration=stat(config),configuration=stat(CONFIG),program=stat(program),source_build=control['source_build'],source_capture=control['source_capture'],source_archive=control['source_archive'],source_pre_file=stat(matrix.PRE),planned_steps=stat(matrix.PLAN),planned_global_end=2180000,expected_saved_frames=91,AS_coefficient=.7,control_AS_coefficient=.5,AS_exponent=2.55,only_numerical_input_difference='ArtificialStressCoef 0.5 -> 0.7; Exp2.55 fixed',consumed=consumed,consumed_stats_unchanged=True,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,VTK_invocations=0,SHA_scans=0,physical_acceptance=False))


def context():
    control,prior,config,build,program,material,runtime,window,preload,consumed=original_context();prepared=read(PREP);admission=read(ADMISSION)
    need(prepared['stage']==TAG+'.prepare' and prepared['prepared_only'] and prepared['configuration']==stat(CONFIG) and prepared['control_configuration']==stat(config) and prepared['control_run']==stat(CONTROL_RUN) and prepared['exact_inverse_original_XML_bytes'] and prepared['consumed_stats_unchanged'] and prepared['AS_coefficient']==.7 and prepared['AS_exponent']==2.55 and prepared['prior_N255_review']==stat(REVIEW) and prepared['prior_N255_adapter']==stat(ADAPTER),'Exact separately prepared AS07/n2.55 input required');check_input(CONFIG,config)
    need(admission['passed'] and admission['allowed_job']==TAG and admission['prepared']==stat(PREP) and admission['input_xml']==stat(CONFIG) and admission['control_run']==stat(CONTROL_RUN) and admission['independent_parameter_admission'] is True and admission['completed_N255_reviewed'] is True and admission['prior_N255_review']==stat(REVIEW) and admission['prior_N255_adapter']==stat(ADAPTER) and admission['planned_steps']==stat(matrix.PLAN) and admission['planned_global_end']==2180000 and admission['expected_saved_frames']==91 and admission['AS_coefficient']==.7 and admission['AS_exponent']==2.55 and admission['native_auto_authorized'] is False and admission['terminal_queue_once'] is True,'Distinct independent root coefficient admission after full-read required')
    for key in ('program','source_build','source_capture','source_archive','source_pre_file'):
        need(bind(admission[key])==bind(control[key]) and bind(prepared[key])==bind(control[key]),'Only original raw-FS schema2 control binding allowed: '+key)
    need(admission['root_thread_id']==os.environ.get('CODEX_THREAD_ID')==THREAD and matrix.notifier_path() is not None,'Actual admitted root thread/current notifier required')
    consumed.extend(stat(q) for q in (PREP,ADMISSION,CONFIG));consumed.extend(bind(q) for q in prepared['consumed']);consumed.append(bind(admission['parameter_decision']))
    matrix.verify(consumed);matrix.old.old.idle(True)
    return control,prior,build,program,material,runtime,window,preload,consumed


def summary(path):
    lines=Path(path).read_text(encoding='utf-8-sig').splitlines();need(len(lines)==2,'One actual Run.csv header/data row required');match=re.match(r'^#?RunName([;,])',lines[0]);need(match,'Known Run.csv delimiter required');sep=match[1];keys=lines[0].lstrip('#').split(sep);values=lines[1].split(sep);need(len(set(keys))==len(keys) and keys.count('Configuration')==1,'Unique Run.csv keys required');at=keys.index('Configuration')
    if len(values)==len(keys)+1 and sep==';':values=values[:at]+[values[at]+';'+values[at+1]]+values[at+2:]
    need(len(values)==len(keys),'Only the known single AS semicolon is repairable');number=r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?';hits=re.findall(r'(?:^| - )AS_Bui2008\(('+number+r');('+number+r')\)(?= - |$)',values[at]);need(len(hits)==1 and values[at].count(';')==values[at].count('AS_Bui2008')==1 and matrix.f32(hits[0][0])==matrix.f32(.7) and matrix.f32(hits[0][1])==matrix.f32(2.55),'Actual complete epsilon.7/exponent2.55 token required');return dict(zip(keys,values))


def output_checks(out,preload):
    observed=summary(out/'Run.csv');text=(out/'Run.out').read_text(encoding='utf-8-sig');parts=sorted((out/'data').glob('Part_*.bi4'))
    need(int(observed['Steps'])==2180000 and int(observed['PartFiles'])==91 and int(observed['Np'])==7060 and int(observed['Nfixed'])==int(observed['Nbound'])==2060 and all(int(observed[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')) and 'Gpu_' in observed['Hardware'] and float(observed['H'])==.072 and float(observed['Dp'])==.04,'Actual full91 GPU/no-loss registry differs')
    need('Kernel="Wendland"' in text and 'Finished execution (code=0).' in text and '[Simulation INTERRUPTED' not in text and 'No Penetration=True' in text and 'Dynamic NoPen: '+base.POLICY in text and text.count('GravityPreload: phase=released ')==1 and text.count('GravityPreload: validated native right-wall range=[1805,2060), count=255.')==1 and 'retired=255; damping=OFF Shepard=OFF FreeSeepage=ON.' in text,'Actual completion/kernel/release/NoPen differs')
    for key,value in (('ArtificialStressCoef',.7),('ArtificialStressExp',2.55)):
        hits=re.findall(r'^\s*'+key+r'[:=]\s*([0-9.eE+-]+)\s*$',text,re.M);need(len(hits)==1 and matrix.f32(hits[0])==matrix.f32(value),'Actual explicit AS log differs')
    imported=re.findall(r'GravityPreload: state imported file=.*? actual=([0-9.eE+-]+) completed_step=(\d+);',text)
    need(len(imported)==1 and int(imported[0][1])==2000000 and float(imported[0][0])==preload['preload_actual_end_s'] and [q.name for q in parts]==['Part_%04d.bi4'%i for i in range(91)],'Actual source import/full PART sequence differs')
    return dict(actual_steps=2180000,saved_frames=91,summary=observed,actual_source_time_from_loader=float(imported[0][0]),Run_csv=stat(out/'Run.csv'),Run_out=stat(out/'Run.out'),PARTs=[stat(q) for q in parts])


def notify_once(run_path):
    attempt=L/(TAG+'.queue_attempt.json');reply=L/(TAG+'.queue_result.json');need(not attempt.exists() and not reply.exists() and os.environ.get('CODEX_THREAD_ID')==THREAD,'One actual-root terminal queue only; never resend/rearm')
    program=matrix.notifier_path();message=('The single admitted original/raw-FS AS0.7/exponent2.55 C08 window is terminal: '+str(run_path)+'. Read true owned run/start/call/status/root+owner admission, actual exits and original program/source/PRE/input/full91plan. Only coefficient0.5->0.7 changed numerically from completed c08_h18_as05_n255_r1; exponent2.55, original AV.1/damping/theta/NoPen/material/H1.8/5us/180k/2180000/91 remain. FS-normal/centroid are not carried forward. The existing n255 reader is exact0.5/2.55 and cannot certify this0.7 case: a separately reviewed profile/adapter and independent native admission are needed later. No auto decoder/VTK/next/PRE/half/control/otherpsi, no physical acceptance fromexit0. Preserve failures/partials and last actual console, no unsaved reconstruction. One same-current-thread45s queue; uncertain delivery never resend/rearm/watch.')
    argv=[str(program) if program else 'codex','queue','--thread',THREAD,'--message',message];save(attempt,dict(stage=TAG,run=stat(run_path),thread=THREAD,program=stat(program) if program else None,arguments=argv,attempts=1,timeout_s=45,do_not_resend=True));result=dict(stage=TAG,attempts=1,do_not_resend=True)
    try:
        need(program is not None,'Current notifier missing; preserve terminal evidence without retry');done=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=45,creationflags=subprocess.CREATE_NO_WINDOW);result.update(actual_exit=done.returncode,status='queued' if done.returncode==0 else 'queue_failed',stdout=done.stdout,stderr=done.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(reply,result)


def run():
    out=T/'outputs'/TAG;run_path=L/(TAG+'.run.json');need(not out.exists() and not any(q.name not in {PREP.name,ADMISSION.name} for q in L.glob(TAG+'.*')),'Existing job/partial protected; external launcher prefix must differ')
    claim=L/(TAG+'.claim.json');save(claim,dict(stage=TAG,owner_pid=os.getpid(),owner_created_epoch=psutil.Process().create_time(),single_attempt=True));consumed=[];phase='preflight';result=dict(stage=TAG,passed=False,solver_completed=False,physical_acceptance=False,native_review_pending=True,native_reader_requires_separate_a07_n255_adapter=True,automatic_next_job=False,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,VTK_invocations=0,SHA_scans=0)
    try:
        control,prior,build,program,material,runtime,window,preload,consumed=context();consumed.append(stat(claim));out.mkdir();prefix=out/TAG;gen=next(q for q in runtime if Path(q['path']).name=='GenCase_win64.exe')
        phase='GenCase';result['GenCase_invocations']=1;result['GenCase_call']=invoke(TAG+'.gencase',[gen['path'],str(CONFIG.with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml');actual=check_input(seed,control['input_xml']['path'],True);seeds=[stat(Path(str(prefix)+suffix)) for suffix in ('.xml','.bi4','_Normals.nbi4')];consumed.extend(seeds)
        profile=out/'native_profile.csv';values=matrix.actual_material(actual);matrix.match_material(values,material);pars={q.get('key'):q.get('value') for q in actual.findall('execution/parameters/parameter')};values.update(ArtificialStressCoef=pars['ArtificialStressCoef'],ArtificialStressExp=pars['ArtificialStressExp'])
        with profile.open('x',encoding='utf-8',newline='') as handle:writer=csv.writer(handle);writer.writerow(('key','value'));writer.writerows(values.items())
        consumed.append(stat(profile));matrix.verify(consumed);argv=[str(program),'-gpu:0','-stable','-mdbc_freeslip:1',str(prefix),str(out),'-dirdataout','data','-svres','-nsteps:2180000'];need(argv[1:4]==control['argv'][1:4] and argv[6:]==control['argv'][6:],'Only fresh input/output labels may change in original solver argv');owner=L/(TAG+'.owner_admission.json')
        closure={key:control[key] for key in ('program','source_build','source_capture','source_archive','source_pre_file','source_run','source_native')}
        save(owner,dict(stage=TAG,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),root_admission=stat(ADMISSION),**closure,runtime=runtime,input_xml=stat(seed),seed=seeds,planned_steps=stat(matrix.PLAN),planned_global_end=2180000,expected_saved_frames=91,planned_new_updates=180000,native_reader_requires_separate_a07_n255_adapter=True,group='psi0',Kernel=2,AS_coefficient=.7,AS_exponent=2.55,control_run=stat(CONTROL_RUN),only_numerical_input_difference='ArtificialStressCoef 0.5 -> 0.7; Exp2.55 fixed',argv=argv,solver_argv=argv,consumed=consumed));consumed.append(stat(owner))
        result.update(**closure,runtime=runtime,input_xml=stat(seed),seed=seeds,planned_steps=stat(matrix.PLAN),native_profile=stat(profile),owner_admission=stat(owner),argv=argv,group='psi0',kernel=2,kernel_name='Wendland',AS_coefficient=.7,AS_exponent=2.55,control_run=stat(CONTROL_RUN),only_numerical_input_difference='ArtificialStressCoef 0.5 -> 0.7; Exp2.55 fixed',geometry_profile='bedroles',keep_bed_overlap=False,hdp=1.8,fixed_dt_s=5e-6)
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
