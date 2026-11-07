"""Fresh basic-case runs using frozen old/new whole ReleaseCPU programs; no production writes."""
import argparse,csv,ctypes,datetime,json,os,re,shutil,subprocess,time,xml.etree.ElementTree as ET
from ctypes import wintypes as w
from pathlib import Path
import psutil
R=Path(__file__).resolve().parents[5];B=R/'examples/Elastoplastic_basic';H=R/'examples/Hydromechanic coupling/08_LianSaturatedColumnCollapse_u_pl/tests'
K=ctypes.WinDLL('kernel32',use_last_error=True);K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,x):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')
def context(case):
    if case=='column':folder='10_StaticDrySoilColumn';stem='CaseStaticDrySoilColumn2D_Feng2021_dp002';short=.5;full=5.;soil=750;fixed=60
    else:folder='12_GranularColumnCollapse';stem='CaseGranularColumnCollapse2D_a10';short=.1;full=1.;soil=2500;fixed=2028
    c=B/folder;t=c/'tests'
    for sub in ('configs','outputs','logs','notes','figures','support'):(t/sub).mkdir(parents=True,exist_ok=True)
    return c,t,stem,short,full,soil,fixed
def xml_time(source,target,end):
    text=Path(source).read_text(encoding='utf-8-sig');doc=ET.fromstring(text);old=doc.find(".//parameters/parameter[@key='TimeMax']").get('value')
    text,n=re.subn(r'(<parameter\s+key="TimeMax"\s+value=")[^"]+',lambda m:m[1]+str(end),text);need(n==1,'Exactly one TimeMax required')
    with Path(target).open('x',encoding='utf-8',newline='') as f:f.write(text)
    return old
def invoke(t,tag,argv,cwd):
    start=t/'logs'/(tag+'.start.json');call=t/'logs'/(tag+'.call.json');log=t/'logs'/(tag+'.log')
    need(not any(p.exists() for p in (start,call,log)),'Existing process evidence protected')
    owner=psutil.Process();beg=time.monotonic();started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with log.open('xb') as f:
        p=subprocess.Popen(argv,executable=argv[0],cwd=cwd,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        q=psutil.Process(p.pid);ident=dict(pid=p.pid,created_epoch=q.create_time(),exe=q.exe(),argv=q.cmdline(),parent_pid=q.ppid())
        save(start,dict(owner=dict(pid=owner.pid,created_epoch=owner.create_time()),child=ident,argv=argv,cwd=str(cwd),started_utc=started));print('ACTUAL_STARTED',tag,p.pid,flush=True)
        while True:
            try:rc=p.wait(timeout=30);break
            except subprocess.TimeoutExpired:print('OWNED_RUNNING',tag,p.pid,round(time.monotonic()-beg,2),flush=True)
        out=w.DWORD();got=bool(K.GetExitCodeProcess(int(p._handle),ctypes.byref(out)))
    record=dict(stage=tag+'.call',actual_Popen_wait_exit=rc,actual_Win32_exit=out.value if got else None,typed_exit_captured_first=True,child=ident,argv=argv,cwd=str(cwd),elapsed_s=time.monotonic()-beg,log=stat(log),program=stat(argv[0]))
    save(call,record);need(got and rc==out.value==0 and Path(ident['exe']).samefile(argv[0]) and ident['parent_pid']==owner.pid,'Owned process failed; preserve evidence')
    return record
def prepare(case,finish=False):
    c,t,stem,short,full,soil,fixed=context(case);manifest=t/'logs/basic_material_r1.inputs.json';need(not manifest.exists(),'Prepared input already exists')
    seed=t/'outputs/basic_material_r1_seed';need(not seed.exists() or (finish and case=='column'),'Fresh seed required');seed.mkdir(exist_ok=finish)
    original=c/(stem+'_Def.xml');protected=[stat(original)];cfg=t/'configs'/(stem+'_Def.xml')
    if not finish:shutil.copy2(original,cfg)
    else:need(cfg.read_bytes()==original.read_bytes(),'Partial prepared Def changed')
    if case=='column':
        old=c/(stem+'_CPU_out');sources=[old/(stem+s) for s in ('.xml','.bi4','_Normals.nbi4')];protected += [stat(p) for p in sources]
        for p in sources:
            if not finish:shutil.copy2(p,seed/p.name)
            else:need(p.read_bytes()==(seed/p.name).read_bytes(),'Partial prepared seed differs')
        gencase=None
    else:
        gencase=invoke(t,'basic_material_r1.gencase',[str(R/'bin/windows/GenCase_win64.exe'),str(cfg.with_suffix('')),str(seed/stem),'-save:all'],c)
    comp=seed/(stem+'.xml');d=ET.parse(comp);particles=d.find('.//particles');need(int(particles.get('np'))==soil+fixed and int(particles.get('nb'))==fixed,'Actual GenCase native counts differ')
    shorts=t/'configs'/(stem+'_short.xml');fulls=t/'configs'/(stem+'_full.xml')
    if not finish:xml_time(comp,shorts,short);xml_time(comp,fulls,full)
    else:
        for p,end in ((shorts,short),(fulls,full)):need(float(ET.parse(p).find(".//parameters/parameter[@key='TimeMax']").get('value'))==end,'Partial clock config differs')
    programs={}
    for mode,buildtag in [('old','upl_preload_handoff_ReleaseCPU_r2'),('new','upl_material_release_ReleaseCPU_r3')]:
        bp=H/'logs'/(buildtag+'.build.json');b=read(bp);need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0,'Closed frozen build required');e=b['program'];need(stat(e['path'])==e,'Frozen program changed')
        folder=t/'outputs'/('basic_material_r1_runtime_'+mode);need(not folder.exists(),'Fresh local runtime required');folder.mkdir();shutil.copy2(e['path'],folder/Path(e['path']).name)
        src=H/'outputs/upl_preload_handoff_ReleaseCPU_r2';runtime_source=[stat(src/n) for n in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll')]
        for s in runtime_source:shutil.copy2(s['path'],folder/Path(s['path']).name)
        runtime=[stat(folder/Path(s['path']).name) for s in runtime_source]
        programs[mode]=dict(program=stat(folder/Path(e['path']).name),frozen_program=e,build=stat(bp),source_capture=b['source_capture'],runtime=runtime,runtime_sources=runtime_source)
    need(all(stat(e['path'])==e for e in protected),'Retained formal input changed')
    save(manifest,dict(stage='basic_material_r1.prepare',passed=True,case=case,stem=stem,soil=soil,fixed=fixed,short_end=short,full_end=full,configs=dict(short=stat(shorts),full=stat(fulls)),seed=[stat(seed/(stem+s)) for s in ('.xml','.bi4','_Normals.nbi4')],programs=programs,protected=protected,gencase=gencase,SHA_scans=0))
    print('PREPARED',case,soil,fixed,flush=True)
def run(case,window,mode):
    c,t,stem,short,full,soil,fixed=context(case);mp=t/'logs/basic_material_r1.inputs.json';m=read(mp);need(m['passed'],'Input preparation failed');tag='basic_material_'+window+'_'+mode+'_CPU_r1';out=t/'outputs'/tag;receipt=t/'logs'/(tag+'.run.json');need(not out.exists() and not receipt.exists(),'Fresh run output/evidence required')
    p=m['programs'][mode];inputs=[p['program'],p['frozen_program'],p['build'],p['source_capture'],*p['runtime'],*p['runtime_sources'],*m['seed'],m['configs'][window],*m['protected']];need(all(stat(e['path'])==e for e in inputs),'Frozen dependency stat changed')
    exe=Path(p['program']['path']);duplicates=[]
    for q in psutil.process_iter(['pid','exe','cmdline']):
        try:
            if q.info['exe'] and Path(q.info['exe'])==exe:duplicates.append(q.info)
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    need(not duplicates,'Matching frozen solver already active')
    runseed=t/'outputs'/(tag+'_seed');need(not runseed.exists(),'Fresh per-run XML seed required');runseed.mkdir()
    shutil.copy2(m['configs'][window]['path'],runseed/(stem+'.xml'))
    for suffix in ('.bi4','_Normals.nbi4'):shutil.copy2(Path(m['seed'][0]['path']).parent/(stem+suffix),runseed/(stem+suffix))
    argv=[str(exe),'-cpu','-ompthreads:1','-stable','-mdbc_noslip',str(runseed/stem),str(out),'-dirdataout','data','-svres']
    result=dict(stage=tag+'.run',passed=False,case=case,window=window,mode=mode,consumed=inputs,input_manifest=stat(mp),physical_acceptance=False)
    try:
        call=invoke(t,tag,argv,c);result['actual_call']=call
        with (out/'Run.csv').open(newline='',encoding='utf-8-sig') as f:rows=list(csv.DictReader(f,delimiter=';'))
        need(len(rows)==1,'Actual one-row Run.csv required');r=rows[0];text=(out/'Run.out').read_text(encoding='utf-8',errors='replace')
        need('[Simulation finished' in text and int(r['Np'])==soil+fixed and int(r['Nfixed'])==fixed and all(int(r[k])==0 for k in ('PartsOut','PartsOutRhop','PartsOutVel')),'Normal completion/native count/no-exclusion failed')
        need('Symplectic' in r['Configuration'] and 'Wendland' in r['Configuration'] and 'No-slip' in r['Configuration'],'Actual scheme/kernel/boundary changed')
        parts=list((out/'data').glob('Part_*.bi4'));n=int(r['PartFiles']);need(len(parts)==n and all((out/'data'/f'Part_{i:04d}.bi4').is_file() for i in range(n)),'Native save sequence differs')
        need(all(stat(e['path'])==e for e in inputs),'Frozen input/program/runtime changed')
        result.update(passed=True,actual_steps=int(r['Steps']),saved_frames=n,RunCSV=r,last_console_PART_line=next((x for x in reversed(text.splitlines()) if re.match(r'^Part_\d+\s',x)),None),consumed_stats_unchanged=True,native_review_pending=True)
    except Exception as e:result['first_failure']=str(e)
    save(receipt,result);print(json.dumps({k:v for k,v in result.items() if k not in ('consumed','RunCSV')},indent=2),flush=True);need(result['passed'],'Run checks failed; no retry')
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('action',choices=['prepare','finish-prepare','run']);a.add_argument('case',choices=['column','collapse']);a.add_argument('window',nargs='?',choices=['short','full']);a.add_argument('mode',nargs='?',choices=['old','new']);x=a.parse_args()
    prepare(x.case,x.action=='finish-prepare') if x.action!='run' else run(x.case,x.window,x.mode)
