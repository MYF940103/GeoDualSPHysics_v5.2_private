"""Prepare OR run one separately admitted same-material Wendland C08 branch PRE."""
import argparse
import csv
import json
import os
import re
import struct
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import psutil
import upl_c08_bedkeep_run_r1 as base

T,C,L=base.T,base.C,base.L
need,read,stat,bind,save,invoke=base.need,base.read,base.stat,base.bind,base.save,base.invoke
SELF=Path(__file__).resolve()
NOTE=T/'notes/c08_h18_wend_branches_pre_r1.md'
ROOT=C/'CaseLianSaturatedColumnCollapse_shared_preload_r3_Def.xml'
BUILD=L/'c08_preload_schema2_Release_r1.build.json'
RUNTIME=T/'outputs/c08_preload_schema2_Release_r1'
SOURCE_PLAN=T/'configs/c08_h18_pre_r2.steps.csv'
CODEX=Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1106.51428-win32-x64/bin/windows-x86_64/codex.exe')
THREAD='01a07683-bc64-7463-8db7-9ee6243967d8'
GROUPS={'psi2p5':('5000','2.5','0.2'),'psim5':('7500','-5','0.2')}
DT=.000005
END=2000000
FRAMES=1001
SELECTED=(0,100,500,1000)
VARS='-vars:-all,+idp,+mk,+vel,+rhop,+PorePress,+PorePress0,+ExcessPorePress,+SigmaState_kk,+SigmaState_ij,+Sigma_kk,+Sigma_ij,+Kplastic,+FSType,+FSNormal,+PoroVolumeRatio,+PoroPorosity,+PoroThetaLastStage,+PoroCurrentVolume,+PoroMixtureDensity,+PoroHydraulicConductivity,+PosDiv,+HydroMechLoadAce'
RUNTIME_NAMES={'GenCase_win64.exe','PartVTK_win64.exe','DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll','msvcp140.dll','vcruntime140.dll','vcruntime140_1.dll'}


def paths(group):
    need(group in GROUPS,'Only an independently admitted psi2p5 or psim5 source is supported')
    tag='c08_h18_wend_branches_'+group+'_pre_r1'
    return dict(tag=tag,out=T/'outputs'/tag,config=T/'configs'/(tag+'_Def.xml'),
                bat=T/'configs'/(tag+'_GPU.bat'),plan=T/'configs'/(tag+'.steps.csv'),
                prepare_admission=L/(tag+'.prepare_admission.json'),prepare=L/(tag+'.prepare.json'),
                admission=L/(tag+'.admission.json'),run=L/(tag+'.run.json'))


def verify(entries):
    need(all(stat(q['path'])==q for q in entries),'Consumed source/input/program/runtime stat changed')


def signature(node):
    return (node.tag,tuple(sorted((k,v) for k,v in node.attrib.items()
            if k!='comment' and not k.endswith('_comment'))),
            (node.text or '').strip(),tuple(signature(q) for q in node))


def f32(value):
    return struct.unpack('<f',struct.pack('<f',float(value)))[0]


def material(group):
    coh,dlt,decay=map(float,GROUPS[group])
    return dict(coh=coh,dlt=dlt,DilationDecay=decay,phi=25.,phi_r=25.,n_phi=0.,
                coh_r=1000.,n_coh=5.,ModulusE=20e6,PRvs=.33)


def material_storage(group):
    # JSph.cpp converts ReadElementFloat angles with the binary64 TORAD literal.
    # These are expected scalar storage values, not a certificate decoded from BI4.
    m=material(group);rad=.017453292519943295769
    return dict(coh_f32=f32(m['coh']),dlt_radians_f32=f32(rad*f32(m['dlt'])),
                phi_radians_f32=f32(rad*f32(m['phi'])),
                phi_r_radians_f32=f32(rad*f32(m['phi_r'])),
                DilationDecay_f32=f32(m['DilationDecay']),coh_r_f32=f32(m['coh_r']),
                n_coh_f32=f32(m['n_coh']),n_phi_f32=f32(m['n_phi']),
                SoilTriggerFos_default_f32=f32(1.65),native_certificate_pending=True)


def input_tree(group):
    root=ET.parse(ROOT).getroot()
    hdp=root.find('casedef/constantsdef/hdp');need(hdp is not None,'Original hdp missing');hdp.set('value','1.8')
    main=root.find('casedef/geometry/commands/mainlist');need(main is not None,'Original mainlist missing')
    commands=list(main);marks=[i for i,q in enumerate(commands) if q.tag=='setmkbound']
    fluid=next(i for i,q in enumerate(commands) if q.tag=='setmkfluid')
    need([commands[i].get('mk') for i in marks]==['0','1','2'] and
         all(commands[i+1].tag=='drawbox' for i in marks),'Original left/bed/right pairs differ')
    left,bed,right=marks
    need(bed==left+2 and right==bed+2 and fluid==right+2,'Original geometry pairing differs')
    main[:]=commands[:left]+commands[left:bed]+commands[right:fluid]+commands[bed:right]+commands[fluid:]
    pairs=root.findall('execution/parameters/parameter');p={q.get('key'):q for q in pairs}
    need(len(p)==len(pairs),'Duplicate original parameter')
    for key,value in (('Kernel','2'),('DtIni','0.000005'),('DtFixed','0.000005'),
                      ('SoilDampingCoef','0.03'),('TimeMax','13.0')):
        need(key in p,'Original parameter missing: '+key);p[key].set('value',value)
    g=root.find('execution/special/gravitypreload')
    need(g is not None and not g.get('statefile'),'Fresh template must not import a PRE')
    g.set('elastic_source','false');g.set('keep_bed_overlap','false')
    g.set('comment','Same-material plastic source; native history and equilibrium require independent review')
    soil=root.find('execution/special/soils');need(soil is not None,'Original soils missing')
    for key,value in zip(('coh','dlt','DilationDecay'),GROUPS[group]):
        nodes=soil.findall(key);need(len(nodes)==1,'Unique original material key required: '+key)
        nodes[0].set('value',value);nodes[0].set('comment','Same-material '+group+' source and receiver must match')
    return root


def check_input(path,group,generated=False):
    actual=ET.parse(path).getroot();expected=input_tree(group)
    if generated:
        need(all(signature(actual.find(q))==signature(expected.find(q))
                 for q in ('execution/special','execution/parameters')),'GenCase changed material/physics')
        constants=actual.find('execution/constants');particles=actual.find('execution/particles')
        need(constants is not None and float(constants.find('h').get('value'))==.072 and
             float(constants.find('dp').get('value'))==.04,'Generated H/dp differs')
        need(particles is not None and [particles.get(k) for k in ('np','nb','nbf')]==['7060','2060','2060'],
             'Generated source registry differs')
        need([(q.get('mkbound'),q.get('begin'),q.get('count')) for q in particles.findall('fixed')]==
             [('0','0','255'),('1','255','1550'),('2','1805','255')] and
             [(q.get('begin'),q.get('count')) for q in particles.findall('fluid')]==[('2060','5000')],
             'Generated bed-last roles/IDs differ')
    else:
        need(signature(actual)==signature(expected),'Only declared source/group changes are allowed')
    pairs=[(q.get('key'),q.get('value')) for q in actual.findall('execution/parameters/parameter')]
    p=dict(pairs);need(len(p)==len(pairs),'Duplicate actual parameter')
    locked=dict(Kernel=2,DPCtes=3,Boundary=2,SlipMode=3,DtIni=DT,DtFixed=DT,DtMin=1e-8,
                TimeMax=13,TimeOut=.01,SoilDamping=1,SoilDampingCoef=.03,SavePosDouble=1,
                PartsOutMax=0,SoilBoundaryDerivativeSPR=0,SoilHourglassXi=0,Shifting=0)
    for key,value in locked.items():need(float(p.get(key,'nan'))==value,'Source parameter differs: '+key)
    need(float(p.get('NoPenetration','0'))==float(p.get('ArtificialStress','0'))==0,'Source AS/NoPen must be OFF')
    g=actual.find('execution/special/gravitypreload')
    need(float(g.get('time'))==10 and g.get('release_mkbound')=='2' and
         g.get('elastic_source')==g.get('keep_bed_overlap')=='false' and not g.get('statefile'),
         'Fresh same-material source event/import flags differ')
    for section,values in (('soils',material(group)),('hydromechanics',dict(
            HydroMech=1,HydroMechDynamicSeepage=1,HydroMechConductivityModel=1,
            HydroMechConductivityCk=2,PoreShepardRegularization=1,PoreShepardInterval=40,
            PoreDarcySymmetricCorr=0,PoreMdbcInterpolationMode=0,PoreCompressionSourceMode=0,
            PoreCompressionGradCorr=1,PoreWaterRho=1000,PoreWaterBulkModulus=1e9,
            Porosity=.35,HydraulicConductivity=.0002,HydroMechDrainage=0,HydroMechFreeSeepage=1))):
        node=actual.find('execution/special/'+section)
        for key,value in values.items():
            q=node.findall(key);need(len(q)==1 and float(q[0].get('value'))==value,'Locked '+section+' differs: '+key)


def plan_records(path,scalar_verify=False):
    with path.open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f);need(reader.fieldnames==['part','completed_step','saved_step','time_s','dt_s'],
                                    'Original scalar plan schema differs');rows=list(reader)
    need(len(rows)==FRAMES,'Original1001-frame plan required')
    data=[dict(part=int(q['part']),completed_step=int(q['completed_step']),saved_step=int(q['saved_step']),
               time_s=float(q['time_s']),dt_s=float(q['dt_s'])) for q in rows]
    need(data[0]==dict(part=0,completed_step=0,saved_step=0,time_s=0.,dt_s=DT) and
         data[-1]['completed_step']==END,'Original initial/final plan differs')
    for i,q in enumerate(data):
        need(q['part']==i and q['dt_s']==DT and q['saved_step']==(q['completed_step']-1 if i else 0),
             'Original native saved-step convention differs')
        if i:need(data[i-1]['completed_step']<q['completed_step'] and data[i-1]['time_s']<q['time_s'],
                  'Plan must have strictly increasing actual saved clocks/steps')
    if scalar_verify:
        clock=0.;next_part=1
        for completed in range(1,END+1):
            clock+=DT
            if completed==data[next_part]['completed_step']:
                need(clock==data[next_part]['time_s'],'Plan is not the original binary64 scalar +=dt clock')
                next_part+=1
                if next_part==FRAMES:break
        need(next_part==FRAMES and completed==END,'Scalar plan verification incomplete')
    return data


def build_context():
    b=read(BUILD)
    need(b['passed'] and b['configuration']=='Release' and b['consumed_stats_unchanged'],
         'Passed frozen generic schema2 Release build required')
    program=RUNTIME/'DualSPHysics5.2_GEO_win64.exe'
    need(bind(b['program'])==stat(program),'Actual generic source program differs')
    call=read(bind(b['actual_call'])['path'])
    need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None,
         'Actual generic MSBuild exit/ownership failed')
    runtime=[bind(q['destination']) for q in b['runtime']]
    need({Path(q['path']).name for q in runtime}==RUNTIME_NAMES and
         all(Path(q['path']).parent.samefile(RUNTIME) for q in runtime),'Actual source runtime9 differs')
    before=[stat(q) for q in (SELF,NOTE,ROOT,BUILD,SOURCE_PLAN,Path(base.__file__),
            Path(base.evidence.__file__),Path(base.summary.__code__.co_filename))]
    before += [bind(b[k]) for k in ('program','actual_call','source_capture','source_archive')]+runtime
    return b,program,before,runtime


def root_admission(group,action,ctx,b,program,runtime):
    path=ctx['prepare_admission'] if action=='prepare' else ctx['admission'];a=read(path)
    locked=dict(authorized=True,allowed_action=action,allowed_job=ctx['tag'],group=group,
                kernel=2,kernel_name='Wendland',hdp=1.8,fixed_dt_s=DT,damping_coefficient=.03,
                planned_global_end=END,expected_saved_frames=FRAMES,gravity_event_s=10.,
                TimeMax_s=13.,elastic_source=False,keep_bed_overlap=False,
                source_contract_schema_expected=2,source_material_law_version_expected=2,
                material=material(group),single_source_only=True,terminal_queue_once=True)
    for key,value in locked.items():need(a.get(key)==value,'Exact single-source root admission differs: '+key)
    bindings=dict(script=stat(SELF),note=stat(NOTE),template=stat(ROOT),source_build=stat(BUILD),
                  program=stat(program),source_capture=b['source_capture'],source_archive=b['source_archive'],
                  source_plan=stat(SOURCE_PLAN))
    if action=='run':bindings.update(preparation=stat(ctx['prepare']),input_xml=stat(ctx['config']),
                                      planned_steps=stat(ctx['plan']),test_BAT=stat(ctx['bat']))
    for key,value in bindings.items():need(bind(a[key])==value,'Root admission binding differs: '+key)
    need(a['runtime']==runtime,'Root admission runtime differs')
    return a,path


def prepare(group):
    c=paths(group);need(c['prepare_admission'].is_file(),'Separate root prepare admission required')
    need(not any(c[k].exists() for k in ('out','config','bat','plan','prepare','run')),
         'Existing/partial preparation/source protected; use no automatic retry')
    result=dict(stage=c['tag']+'.prepare',passed=False,group=group,GenCase_invocations=0,
                solver_invocations=0,reader_invocations=0,physical_acceptance=False,SHA_scans=0)
    before=[]
    try:
        b,program,before,runtime=build_context();a,ad=root_admission(group,'prepare',c,b,program,runtime)
        before.append(stat(ad));rows=plan_records(SOURCE_PLAN,True)
        with c['config'].open('xb') as f:f.write(ET.tostring(input_tree(group),encoding='utf-8',xml_declaration=True)+b'\n')
        check_input(c['config'],group)
        with c['plan'].open('xb') as f:f.write(SOURCE_PLAN.read_bytes())
        need(c['plan'].read_bytes()==SOURCE_PLAN.read_bytes(),'Copied scalar plan bytes differ')
        body=('@echo off\r\nsetlocal\r\nset "PYTHON=D:\\anaconda3\\python.exe"\r\n'
              'if not exist "%PYTHON%" set "PYTHON=python"\r\n'
              '"%PYTHON%" -X utf8 -B "%~dp0..\\support\\'+SELF.name+'" run --group '+group+
              ' --execution-authorized --notify\r\nset "EC=%ERRORLEVEL%"\r\n'
              'if not "%~1"=="--unattended" pause\r\nexit /b %EC%\r\n')
        with c['bat'].open('xb') as f:f.write(body.encode('ascii'))
        verify(before)
        result.update(passed=True,root_prepare_admission=stat(ad),input_xml=stat(c['config']),
                      test_BAT=stat(c['bat']),planned_steps=stat(c['plan']),program=stat(program),
                      source_build=stat(BUILD),source_capture=b['source_capture'],source_archive=b['source_archive'],
                      runtime=runtime,material=material(group),expected_material_storage=material_storage(group),
                      kernel=2,kernel_name='Wendland',source_contract_schema_expected=2,
                      source_material_law_version_expected=2,scalar_clock_verified=True,initial_plan=rows[0],
                      final_plan=rows[-1],selected_actual_plan=[rows[i] for i in SELECTED],
                      outputs=[stat(c[k]) for k in ('config','bat','plan')],consumed_stats_unchanged=True,
                      native_review_pending=True,equilibrium_acceptance=False,notification_program_required=False)
    except Exception as error:result['first_failure']=str(error)
    result['consumed']=before;save(c['prepare'],result)
    need(result['passed'],result.get('first_failure','Preparation failed'))
    print('INDEPENDENT_WENDLAND_BRANCH_PREPARED',c['tag'],flush=True)


def context(group,notify):
    c=paths(group);b,program,before,runtime=build_context()
    a,ad=root_admission(group,'run',c,b,program,runtime);p=read(c['prepare'])
    need(p['passed'] and p['group']==group and p['GenCase_invocations']==p['solver_invocations']==
         p['reader_invocations']==0 and p['scalar_clock_verified'] and p['consumed_stats_unchanged'],
         'Passed prepare-only receipt required')
    before += [stat(c['prepare']),stat(ad)]+[bind(q) for q in p['outputs']]+[bind(q) for q in p['consumed']]
    rows=plan_records(c['plan']);check_input(c['config'],group)
    notifier=None
    if notify:
        need(os.environ.get('CODEX_THREAD_ID')==a.get('root_thread_id')==THREAD,
             'Only the admitted actual current root thread may queue once')
        need(CODEX.is_file() and bind(a['notification_program'])==stat(CODEX),
             'Current root-admitted Codex program stat differs; no notification self-test')
        notifier=stat(CODEX);before.append(notifier)
    verify(before)
    for q in psutil.process_iter(['exe','cmdline']):
        try:
            need(not(q.info['exe'] and Path(q.info['exe']).name.lower().startswith('dualsphysics') and
                     any(v.lower().startswith('-gpu') for v in (q.info['cmdline'] or [])[1:])),
                 'GPU physical target active; nothing stopped or changed')
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    return c,b,program,before,runtime,rows,notifier


def output_checks(out):
    r=base.summary(out/'Run.csv');text=(out/'Run.out').read_text(encoding='utf-8-sig')
    parts=sorted((out/'data').glob('Part_*.bi4'))
    need(all(int(r[k])==v for k,v in dict(Steps=END,PartFiles=FRAMES,Np=7060,Nbound=2060,
         Nfixed=2060,PartsOut=0,PartsOutRhop=0,PartsOutVel=0).items()) and 'Gpu_' in r['Hardware'] and
         float(r['Dp'])==.04 and float(r['H'])==.072,'Actual GPU source schedule/registry/H/exclusions differ')
    need('Wendland' in r['Configuration'] and '[Simulation INTERRUPTED' not in text,
         'Actual source was interrupted or uses a different kernel')
    required=('Finished execution (code=0).',
              'GravityPreload: requested=10 event_completed_step=2000000 release_mkbound=2;',
              'GravityPreload: validated native right-wall range=[1805,2060), count=255.',
              'No Penetration=False','ArtificialStress="None"','SoilDamping="BuiFukagawa2013"',
              'SoilDampingCoef=0.03','PoreShepardRegularization="Enabled"','PoreShepardInterval: 40')
    need(all(q in text for q in required) and 'GravityPreload: phase=released' not in text and
         'GravityPreload: state imported' not in text,'Actual fresh source/event/modes differ')
    need([q.name for q in parts]==['Part_%04d.bi4'%i for i in range(FRAMES)],
         'Actual1001 contiguous source saves required')
    return dict(actual_steps=END,saved_frames=FRAMES,summary=r,Run_csv=stat(out/'Run.csv'),
                Run_out=stat(out/'Run.out'),PARTs=[stat(q) for q in parts],
                source_pre_file=stat(out/'data/Part_1000.bi4'),source_head=stat(out/'data/Part_Head.ibi4'),
                native_saved_clocks_verified=False,native_review_pending=True)


def export_selected(tag,out,seed,result):
    particles=out/'particles';particles.mkdir();calls=[];files=[]
    result['PartVTK_calls']=calls;result['particle_files']=files
    for label,kind,count in (('PartFluid','fluid',5000),('PartBound','fixed',2060)):
        for part in SELECTED:
            argv=[str(RUNTIME/'PartVTK_win64.exe'),'-dirin',str(out/'data'),'-filexml',str(seed),
                  '-first:'+str(part),'-last:'+str(part),'-savevtk',str(particles/label),
                  '-onlytype:-all,'+kind,VARS,'-threads:1']
            result['PartVTK_invocations']+=1
            calls.append(invoke(tag+'.vtk_'+label+'_%04d'%part,argv,C))
            path=particles/(label+'_%04d.vtk'%part)
            with path.open('rb') as f:match=re.search(rb'\bPOINTS\s+(\d+)\s+',f.read(4096))
            need(match and int(match[1])==count,'Selected Fluid/Bound point count differs');files.append(stat(path))
    need({q.name for q in particles.iterdir()}=={Path(q['path']).name for q in files},
         'Unexpected/partial selected export')


def queue_once(c,group,notifier):
    tag=c['tag'];attempt=L/(tag+'.queue_attempt.json');reply=L/(tag+'.queue_result.json')
    need(not attempt.exists() and not reply.exists(),'Terminal notification already attempted; never resend')
    bind(notifier)
    message=('The independently admitted C08 Wendland same-material branch '+group+' PRE is terminal: '+
             str(c['run'])+'. Read original start/call/run/status/root and owner admissions and solver_completed seal; '
             'verify actual ownership and Popen/Win32 exits and program/source/input/plan bindings. '
             'This is a fresh schema2/law2 source only: Kernel2 H1.8/.072,5us,damping.03,Shepard40,AS/HG/NoPenOFF, '
             'elastic_source=false,keepfalse,event10/TimeMax13 capped2M/1001saves with bed-last255/1550/255 and5000soil. '
             'Native kappa/J/p/stress are retained, not assigned or reset. Normal completion is not PRE certification or equilibrium. '
             'Review complete material tuple and original22/IDs/P0/J/kappa/FS/ledger/actualscalarclock/signed safety before any handoff. '
             'Separate selected0/1/5/10s Fluid5000/Bound2060 VTK is derived output only; if export fails after sealed solve, '
             'repair only derived outputs and never rerun the source. This owner launches no native reader, collapse, otherpsi, '
             'half or nextsolver. Preserve actual failures/partials/last original console and never infer unsaved failure time. '
             'One terminal45s queue attempt only; uncertain delivery is never resent/rearmed and no watcher/self-test follows.')
    argv=[notifier['path'],'queue','--thread',THREAD,'--message',message]
    save(attempt,dict(stage=tag,utc=base.utc(),thread=THREAD,run=stat(c['run']),
                     notification_program=notifier,arguments=argv,attempts=1,timeout_s=45,do_not_resend=True))
    result=dict(stage=tag,attempts=1,do_not_resend=True)
    try:
        q=subprocess.run(argv,cwd=C,capture_output=True,text=True,encoding='utf-8',errors='replace',
                         timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
        result.update(actual_exit=q.returncode,status='queued' if q.returncode==0 else 'queue_failed',
                      stdout=q.stdout,stderr=q.stderr)
    except subprocess.TimeoutExpired as error:result.update(status='delivery_uncertain',error=str(error))
    except Exception as error:result.update(status='queue_failed',error=str(error))
    save(reply,result)


def run(group,notify):
    c=paths(group);tag=c['tag']
    need(c['admission'].is_file() and c['prepare'].is_file(),'Separate run admission/preparation required')
    allowed={c[k].name for k in ('prepare_admission','prepare','admission')}
    need(not c['out'].exists() and not any(q.name not in allowed for q in L.glob(tag+'.*')),
         'Existing owner/source/partial protected; no retry')
    claim=L/(tag+'.claim.json')
    save(claim,dict(stage=tag,owner_pid=os.getpid(),owner_created_epoch=psutil.Process().create_time(),single_attempt=True))
    before=[];notifier=None;stage='preflight'
    result=dict(stage=tag,group=group,passed=False,solver_completed=False,postprocess_completed=False,
                physical_acceptance=False,equilibrium_acceptance=False,native_review_pending=True,
                source_certificate_verified_by_owner=False,elastic_source=False,keep_bed_overlap=False,
                ArtificialStress=False,NoPenetration=False,HG=False,source_contract_schema_expected=2,
                source_material_law_version_expected=2,material=material(group),
                expected_material_storage=material_storage(group),kernel=2,kernel_name='Wendland',hdp=1.8,
                expected_native_H=f32(.072),fixed_dt_s=DT,damping_coefficient=.03,planned_global_end=END,
                expected_saved_frames=FRAMES,solver_invocations=0,GenCase_invocations=0,reader_invocations=0,
                PartVTK_invocations=0,queue_invocations_at_run_seal=0,SHA_scans=0)
    try:
        c,b,program,before,runtime,rows,notifier=context(group,notify);before.append(stat(claim))
        c['out'].mkdir();prefix=c['out']/tag;stage='GenCase';result['GenCase_invocations']=1
        result['GenCase_call']=invoke(tag+'.gencase',[str(RUNTIME/'GenCase_win64.exe'),
                                     str(c['config'].with_suffix('')),str(prefix),'-save:all'],C)
        seed=Path(str(prefix)+'.xml');check_input(seed,group,True)
        entries=[stat(Path(str(prefix)+q)) for q in ('.xml','.bi4','_Normals.nbi4')]
        before+=entries;verify(before)
        argv=[str(program),'-gpu:0','-stable','-mdbc_freeslip',str(prefix),str(c['out']),
              '-dirdataout','data','-svres','-nsteps:'+str(END)]
        ownerad=L/(tag+'.owner_admission.json')
        save(ownerad,dict(stage=tag,group=group,owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),
             root_admission=stat(c['admission']),preparation=stat(c['prepare']),
             actual_environment_thread=os.environ.get('CODEX_THREAD_ID'),notification_program=notifier,
             terminal_queue_once=notify,program=stat(program),source_build=stat(BUILD),
             source_capture=b['source_capture'],source_archive=b['source_archive'],runtime=runtime,
             input_xml=stat(seed),seed=entries,planned_steps=stat(c['plan']),material=material(group),
             expected_material_storage=material_storage(group),kernel=2,kernel_name='Wendland',
             elastic_source=False,keep_bed_overlap=False,source_contract_schema_expected=2,
             source_material_law_version_expected=2,planned_global_end=END,expected_saved_frames=FRAMES,
             fixed_dt_s=DT,initial_plan=rows[0],final_plan=rows[-1],argv=argv,solver_argv=argv,consumed=before))
        before.append(stat(ownerad))
        result.update(program=stat(program),source_build=stat(BUILD),source_capture=b['source_capture'],
                      source_archive=b['source_archive'],runtime=runtime,input_xml=stat(seed),seed=entries,
                      planned_steps=stat(c['plan']),preparation=stat(c['prepare']),argv=argv,owner_admission=stat(ownerad))
        stage='solver';result['solver_invocations']=1
        result['actual_call']=base.owned(tag,argv,program,False,stat(ownerad))
        result.update(solver_returned_zero=True,actual_exit=0,actual_Win32_exit=0)
        stage='solver_output_review';result.update(output_checks(c['out']));verify(before)
        result['solver_completed']=True
        sealed=L/(tag+'.solver_completed.json')
        save(sealed,dict(stage=tag,solver_completed=True,actual_call=result['actual_call'],
             actual_exit=0,actual_Win32_exit=0,program=result['program'],owner_admission=stat(ownerad),
             input_xml=stat(seed),planned_steps=stat(c['plan']),Run_csv=result['Run_csv'],Run_out=result['Run_out'],
             source_pre_file=result['source_pre_file'],source_head=result['source_head'],
             actual_steps=END,saved_frames=FRAMES,native_review_pending=True,physical_acceptance=False,
             equilibrium_acceptance=False,postprocessing_not_yet_started=True))
        result['solver_completed_seal']=stat(sealed)
        stage='postprocess';base.publish(tag,c['out'],None,None,'source_completed_selected_exports_running')
        export_selected(tag,c['out'],seed,result);verify(before)
        result.update(passed=True,postprocess_completed=True,selected_part_numbers=list(SELECTED),
                      selected_nominal_physical_times_s=[0,1,5,10],selected_actual_plan=[rows[i] for i in SELECTED],
                      VTK_positions_are_float=True,consumed_stats_unchanged=True)
    except Exception as error:
        result.update(first_failure=str(error),failed_stage=stage);cp=L/(tag+'.call.json')
        if cp.exists():
            a=read(cp);result.update(actual_call=stat(cp),actual_exit=a['actual_solver_Win32_exit'],
                 actual_Win32_exit=a['actual_solver_Win32_exit'],actual_tool_exit=a['actual_Popen_wait_exit'],
                 ownership_errors=a['ownership_errors'])
        path=c['out']/'Run.out'
        if path.exists():
            result['Run_out']=stat(path);lines=path.read_text(encoding='utf-8-sig',errors='replace').splitlines()
            first=next((i for i,line in enumerate(lines) if line.startswith('*** Exception')),None)
            result['first_engine_exception_lines']=lines[first:first+6] if first is not None else []
    result.update(consumed=before,last_original_console_line=base.last_part(c['out']),
                  unsaved_failure_time_reconstructed=False)
    state=('completed_pending_native_and_equilibrium_review' if result['passed'] else
           'solver_completed_postprocess_failed_preserved' if result['solver_completed'] else
           'failed_preserved_pending_diagnosis')
    try:base.publish(tag,c['out'],None,None,state)
    except Exception as error:result['terminal_status_error']=str(error)
    save(c['run'],result)
    if notify and notifier is not None:
        try:queue_once(c,group,notifier)
        except Exception as error:print('TERMINAL_QUEUE_NOT_RETRIED',str(error),flush=True)
    print(json.dumps(dict(passed=result['passed'],run=str(c['run']),solver_completed=result['solver_completed'],
                         postprocess_completed=result['postprocess_completed'],first_failure=result.get('first_failure'))),flush=True)
    return result['passed']


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','run'))
    parser.add_argument('--group',choices=tuple(GROUPS),required=True)
    parser.add_argument('--execution-authorized',action='store_true')
    parser.add_argument('--notify',action='store_true')
    args=parser.parse_args()
    need(args.execution_authorized and not(args.action=='prepare' and args.notify),
         'Root review and explicit single action required; no notification during prepare')
    if args.action=='prepare':prepare(args.group)
    else:raise SystemExit(0 if run(args.group,args.notify) else 1)
