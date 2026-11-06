import csv,datetime,json,math,os,shutil,struct,subprocess
from pathlib import Path
import psutil
R=Path(r'D:/MYF/SPH/GeoDualSPHysics_redevelop_f66777b');T=R/'examples/Hydromechanic coupling/08_LianSaturatedColumnCollapse_u_pl/tests';L=T/'logs';TAG='upl_density_cache_CPU_r2'
NEW=Path(__file__).resolve().parent;OLD=T/'outputs/upl_density_cache_CPU_old_helper_r2';SRC=T/'support/upl_density_cache_cpu_r2.cpp';NOTE=T/'notes/upl_density_cache_cpu_r2.json'
SEED=T/'outputs/upl_c08_observer_r1_seed/CaseLianSaturatedColumnCollapse_geometry_r1'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def need(b,s):
    if not b:raise RuntimeError(s)
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def save(p,d):
    with Path(p).open('x',encoding='utf-8',newline='\n')as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def identity(pid):
    p=psutil.Process(pid)
    with p.oneshot():return dict(pid=p.pid,created_epoch=p.create_time(),parent_pid=p.ppid(),exe=p.exe(),argv=p.cmdline(),cwd=p.cwd())
def changes(rows):
    changed=[]
    for d in rows:
        try:a=stat(d['path']);ok=Path(a['path']).samefile(d['path'])and a['bytes']==d['bytes']and a['mtime_ns']==d['mtime_ns']
        except OSError:a=None;ok=False
        if not ok:changed.append(dict(expected=d,observed=a))
    return changed
def call(label,exe,args,cwd):
    lp=L/(TAG+'.'+label+'.log');cp=L/(TAG+'.'+label+'.call.json');started=now()
    with lp.open('xb')as f:
        p=subprocess.Popen([str(exe)]+args,cwd=cwd,env=ENV,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);child=identity(p.pid);rc=p.wait()
    d=dict(stage=TAG+'.'+label,program=stat(exe),arguments=args,cwd=str(cwd),owner=OWNER,child=child,actual_exit_code=rc,direct_Popen_wait=True,started_utc=started,ended_utc=now(),log=stat(lp),SHA_scans=0,physical_acceptance=False)
    save(cp,d);calls.append(stat(cp));print(label,'actual_exit',rc,'PID',child['pid'],flush=True);need(rc==0,label+' actual call failed; no retry');return stat(cp)
def table(path):
    with Path(path).open(newline='',encoding='utf-8')as f:return list(csv.DictReader(f))
f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
OWNER=identity(os.getpid());protected=[];generated=[];calls=[];results=[];stage='preflight';ENV=None
try:
    need(not OLD.exists()and set(p.name for p in NEW.iterdir())=={'execute_once.py'},'Fresh helper directories required')
    modes=[('new','feedback'),('new','off'),('new','observer'),('old','off'),('old','observer')]
    paths={(v,m):T/'outputs'/('upl_density_cache_CPU_'+v+'_'+m+'_r2')for v,m in modes}
    need(not any(p.exists()for p in paths.values()),'Fresh stage output collision')
    need(not list(L.glob(TAG+'.*')),'Fresh group log collision')
    for p in psutil.process_iter(['pid','name']):need((p.info['name']or'').lower()!='upl_density_cache_cpu_r2.exe','Same component target is active')
    builds={k:read(L/n)for k,n in [('new','upl_density_cache_DebugCPU_r1.build.json'),('old','upl_wall_gpuport_DebugCPU_r1.build.json'),('gpu','upl_density_cache_Debug_r1.build.json')]}
    for k,b in builds.items():need(b['passed']and b.get('actual_typed_exit_code',b.get('exit_code'))==0,'Official '+k+' build not passed')
    for k in ['new','old']:need(builds[k]['objects']==86 and len(builds[k]['project_objects'])==86,'CPU whole closure must have86 objects')
    records={}
    def add(p):
        d=stat(p);key=d['path'].casefold();need(key not in records or records[key]==d,'Conflicting consumed metadata '+str(p));records[key]=d
    def expected(ds):
        simple=[{k:d[k]for k in ['path','bytes','mtime_ns']}for d in ds];need(not changes(simple),'Previously sealed consumed/object metadata changed')
        for d in simple:add(d['path'])
    for k,b in builds.items():
        expected(b['project_objects']);expected([b['program']]);sp=Path(b['source']);s=read(sp);add(sp)
        if k!='old':expected(s['files'])
        archive=s['archive'];expected([archive]if isinstance(archive,dict)else[stat(archive)])
        add(L/('upl_density_cache_DebugCPU_r1.build.json'if k=='new'else'upl_wall_gpuport_DebugCPU_r1.build.json'if k=='old'else'upl_density_cache_Debug_r1.build.json'))
        for name in ['canonical_stats_before','protected_prior_program_object_runtime_stats']:
            if name in b:expected([d for d in b[name]if 'mtime_ns'in d])
    comp=read(L/'upl_c08_force_CPU_helper_r1_compile.call.json');link=read(L/'upl_c08_force_CPU_helper_r1_link.call.json')
    setup=subprocess.run('"'+str(Path(os.environ['SystemRoot'])/'System32/cmd.exe')+'" /d /c call "'+str(Path('D:/Program Files/VS2022/Common7/Tools/VsDevCmd.bat'))+'" -arch=x64 -host_arch=x64 >nul && set',capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
    need(setup.returncode==0,'Verified VS setup failed');ENV=dict(v.split('=',1)for v in setup.stdout.decode('mbcs').splitlines()if'='in v and not v.startswith('='))
    libdirs=[Path(a[9:])for a in link['arguments']if a.startswith('/LIBPATH:')]+[Path(a)for a in ENV['LIB'].split(';')if a]
    for a in link['arguments']:
        if a.lower().endswith('.lib'):
            p=next((d/a for d in libdirs if(d/a).is_file()),None);need(p is not None,'Unresolved library '+a);add(p)
    runtime=[R/'bin/windows'/n for n in ['DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll']]
    for p in [SRC,NOTE,Path(__file__),Path(comp['program']),Path(link['program']),L/'upl_c08_force_CPU_helper_r1_compile.call.json',L/'upl_c08_force_CPU_helper_r1_link.call.json',SEED.with_suffix('.xml'),SEED.with_suffix('.bi4'),SEED.parent/(SEED.name+'_Normals.nbi4')]+runtime:add(p)
    C=R/'examples/Hydromechanic coupling/04_CryerProblem_PR'
    for p in [C/'CaseCryerProblem_u_pl_nu030_r1_Def.xml',C/'xCaseCryerProblem_u_pl_nu030_r1_win64_GPU.bat',C/'Cryer_upl_nu030_Windows_RTXA6000_r1.zip',C/'support/README_cryer_upl_nu030_r1.md']:add(p)
    for directory in [C/'support/bin_upl_r1',C/'support/upl_seed_nu030_r1']:
        for p in directory.iterdir():
            if p.is_file():add(p)
    protected=list(records.values());save(NEW/'consumed_before.json',dict(stage=TAG+'.before',records=protected,SHA_scans=0))
    programs={}
    def build(k,directory):
        if k=='old':directory.mkdir()
        for p in [SRC,NOTE]+runtime:dest=directory/p.name;need(not dest.exists(),'Fresh source/runtime collision');shutil.copy2(p,dest);generated.append(stat(dest))
        exe=directory/'upl_density_cache_cpu_r2.exe';ca=[];skip=False
        for a in comp['arguments']:
            if skip:ca.append(str(directory/'compile.dependencies.json'));skip=False;continue
            if a.startswith('/Fo'):a='/Fo'+str(directory/'helper.obj')
            elif a.startswith('/Fd'):a='/Fd'+str(directory/'compile.pdb')
            elif a=='/sourceDependencies':skip=True
            elif a.lower().endswith('.cpp'):a=str(SRC)
            ca.append(a)
        la=[];intdir=Path(builds[k]['objects_directory'])
        for a in link['arguments']:
            if a.startswith('/OUT:'):a='/OUT:'+str(exe)
            elif a.startswith('/PDB:'):a='/PDB:'+str(directory/'link.pdb')
            elif a.lower().endswith('.obj'):a=str(directory/'helper.obj')if Path(a).name=='helper.obj'else str(intdir/Path(a).name)
            la.append(a)
        objects=[a for a in la if a.lower().endswith('.obj')];actual={str(Path(a).resolve()).casefold()for a in objects if Path(a).name!='helper.obj'};wanted={str(Path(d['path']).resolve()).casefold()for d in builds[k]['project_objects']if Path(d['path']).name.lower()!='main.obj'}
        need(len(objects)==86 and len(actual)==85 and actual==wanted,'Exact85 non-main closure mismatch')
        cc=call(k+'.compile',comp['program'],ca,directory);lc=call(k+'.link',link['program'],la,directory);need(not changes(protected)and not changes(generated),'SMT changed during helper build');programs[k]=stat(exe);generated.append(programs[k]);save(L/(TAG+'.'+k+'.build.json'),dict(stage=TAG+'.'+k+'.build',passed=True,program=programs[k],source=stat(SRC),compile_call=cc,link_call=lc,non_main_objects=85,link_objects=86,source_object_directory=str(intdir),source_build=stat(L/('upl_density_cache_DebugCPU_r1.build.json'if k=='new'else'upl_wall_gpuport_DebugCPU_r1.build.json')),SHA_scans=0,physical_acceptance=False))
    stage='new_build';build('new',NEW)
    def run(v,m):
        out=paths[v,m];exe=Path(programs[v]['path']);args=['--'+m,'-cpu','-ompthreads:1','-stable','-mdbc_freeslip',str(SEED),str(out)];cp=call(v+'.'+m,exe,args,exe.parent);done=read(out/'completion.json');rows=table(out/'stages.csv')
        need(done['stage']=='upl_density_cache_cpu_r2'and done['passed']and done['native_ids']==7060 and done['feedback']==(m=='feedback')and done['observer']==(m!='off')and done['all_original_state_restored']and done['Pre_and_scratch_pointers_released']and done['global_TimeStep_and_Nstep_unadvanced']and not done['physical_acceptance'],'Stage completion/schema/restoration failed')
        need(len(rows)==(14 if m=='feedback'else 2)and len(rows[0])==17,'Wrong stage CSV coverage/schema')
        result=dict(variant=v,mode=m,call=cp,completion=done,rows=len(rows),source=stat(out/'stages.csv'))
        if m=='feedback':
            need([done[k]for k in ['actual_Pre_calls','actual_Corr_calls','cache_checks','custom_range_rejections','invalid_J_rejections']]==[12,7,40000,4,6],'Actual feedback counts mismatch')
            prebad=[r for r in rows if r['phase']=='pre'and r['result']=='expected_rejection'];fullbad=[r for r in rows if r['phase']=='full'and r['result']=='expected_rejection'];need(len(prebad)==len(fullbad)==3,'Original checkpoint rows missing')
            for r in prebad:need(r['stage_density_written']=='0'and r['native_w']==r['wall_w']=='','Unwritten predictor density was read/reported')
            for r in fullbad:need(r['stage_density_written']=='1'and r['native_w']!=''and r['wall_w']!='','Written corrector density absent')
            text=(out/'rejections.txt').read_text(encoding='utf-8');need(sum(text.count('predictor badJ='+str(i))for i in range(3))==3 and sum(text.count('corrector badJ='+str(i))for i in range(3))==3 and text.count('saturated incompressible-grain')==3 and text.count('finite saturated elastic')==3,'Six actual original checkpoint messages missing')
            normal=[r for r in rows if r['result']=='completed'];ranges=[r for r in rows if r['result']=='out_rhop'];need(len(normal)==len(ranges)==4,'Success/range witness counts differ')
            for r in normal+ranges:
                j=float(r['current_J']);rho=1000.+1072.5/j;need(float(r['physical_rho_double'])==rho and float(r['native_w'])==f32(rho)and r['stage_density_written']=='1','Independent selected-stage cache mismatch')
                if r['phase']=='pre':want=f32(2072.5+.125*.5*16.)
                else:half=f32(2072.5+.125*.5*16.);e=(-16./half)*.125;want=f32(2072.5*(2.-e)/(2.+e))
                need(float(r['wall_w'])==max(2072.5,want),'Original literal fixed-wall stage update differs')
            for r in ranges:need(int(r['CODE'])&0xe000==0xa000 and(float(r['physical_rho_double'])<1800 or float(r['physical_rho_double'])>2400),'Independent component range tag differs')
            expected={('J_0p68','pre'):.68,('J_0p68','full'):.68,('changing_J','pre'):.6796875,('changing_J','full'):.7606201171875}
            for r in normal:
                need(float(r['current_J'])==expected[r['test'],r['phase']]and int(r['CODE'])&0xe000==0 and float(r['input_legacy_w'])>3000,'Valid-J stage witness differs/excluded')
                if r['phase']=='full':need(struct.pack('<d',float(r['preview_Jfull']))==struct.pack('<d',float(r['current_J'])),'Actual committed J differs from preview bits')
            result.update(independent_stage_checks=True,pre_unwritten_density_columns_empty=True,original_checkpoint_text=stat(out/'rejections.txt'),original_checkpoint_count=6,physical_rho_at_J_0p68=1000.+1072.5/.68)
        else:need(done['actual_Pre_calls']==done['actual_Corr_calls']==1 and done['cache_checks']==done['invalid_J_rejections']==0,'OFF/observer stage counts differ')
        need(not changes(protected)and not changes(generated),'SMT changed during target/check');results.append(result);save(L/(TAG+'.'+v+'.'+m+'.check.json'),result);return out
    stage='new_feedback';run('new','feedback')
    stage='old_build';build('old',OLD)
    for v,m in modes[1:]:stage=v+'_'+m;run(v,m)
    stage='whole_stage_byte_comparison';comparisons=[];actual_ids={}
    for m in ['off','observer']:
        for phase in ['pre','full']:
            a=paths['old',m]/(phase+'.bin');b=paths['new',m]/(phase+'.bin');av=a.read_bytes();bv=b.read_bytes();need(av==bv,'Whole stage binary mismatch '+m+' '+phase+' firstbyte='+str(next((i for i,(x,y)in enumerate(zip(av,bv))if x!=y),min(len(av),len(bv)))))
            np,npb,observer=struct.unpack_from('<II?',bv);stride=244+(16 if observer else 0);need(np==7060 and npb==2060 and observer==(m=='observer')and len(bv)==9+np*stride,'Actual stage binary header/types/size mismatch');ids=[struct.unpack_from('<I',bv,9+i*stride)[0]for i in range(np)];need(ids==list(range(7060)),'All original stage IDs missing/reordered');actual_ids[m+'_'+phase]=ids
            comparisons.append(dict(mode=m,phase=phase,old=stat(a),new=stat(b),all_bytes_identical=True,record_bytes=stride,native_ids=7060,columns_removed=False))
    need(not changes(protected)and not changes(generated),'Final SMT changed');save(NEW/'consumed_after.json',dict(stage=TAG+'.after',records=[stat(d['path'])for d in protected],changed=[],generated_stats_unchanged=True,SHA_scans=0))
    save(L/(TAG+'.check.json'),dict(stage=TAG,passed=True,calls=calls,results=results,whole_stage_binary_comparisons=comparisons,all_original_stage_IDs=actual_ids,actual_feedback_ID_membership_checked_by_real_restore=True,old_feedback_invoked=False,target_invocations=5,compiler_invocations=2,linker_invocations=2,consumed_source_object_runtime_canonical_Cryer_package_stats_unchanged=True,original_700_3000_limits_preserved=True,custom_ranges_are_fixture_only=True,physical_trajectory_or_128_update_invoked=False,SHA_scans=0,physical_acceptance=False));print('ALL FIVE COMPONENT TARGETS/CLOSED STAGE BYTE COMPARISONS PASSED',flush=True)
except BaseException as e:
    fp=L/(TAG+'.failure.json');d=dict(stage=TAG+'.failure',failed_stage=stage,reason=str(e),calls=calls,completed_results=results,changed_consumed=changes(protected),changed_generated=changes(generated),SHA_scans=0,no_auto_retry=True,physical_acceptance=False)
    if not fp.exists():save(fp,d)
    print('PRESERVED FAILURE',stage,str(e),flush=True);raise
