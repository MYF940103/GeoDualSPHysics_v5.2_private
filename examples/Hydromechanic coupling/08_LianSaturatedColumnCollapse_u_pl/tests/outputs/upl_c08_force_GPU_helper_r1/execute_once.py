import csv, ctypes, datetime, json, math, os, shutil, struct, subprocess, time
from ctypes import wintypes
from pathlib import Path
import psutil

R=Path(r'D:/MYF/SPH/GeoDualSPHysics_redevelop_f66777b')
T=R/'examples/Hydromechanic coupling/08_LianSaturatedColumnCollapse_u_pl/tests'
TAG='upl_c08_force_GPU_r1'
HERE=Path(__file__).resolve().parent
OUT=T/'outputs'/TAG
LOG=T/'logs'
SRC=T/'support/upl_c08_gpu_force_r1.cpp'
NOTE=T/'notes/upl_c08_gpu_force_r1.json'
BUILD=LOG/'upl_wall_active_Debug_r2.build.json'
BSOURCE=LOG/'upl_wall_active_Debug_r2.source.json'
CPU=T/'outputs/upl_c08_force_CPU_r1'
SEED=T/'outputs/upl_c08_observer_r1_seed/CaseLianSaturatedColumnCollapse_geometry_r1'
SAN=Path(r'C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.3/compute-sanitizer/compute-sanitizer.exe')
EXE=HERE/'upl_c08_gpu_force_r1.exe'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def need(b,s):
    if not b:raise RuntimeError(s)
def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def write(p,d):
    with Path(p).open('x',encoding='utf-8',newline='\n')as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def identity(pid):
    p=psutil.Process(pid)
    with p.oneshot():return dict(pid=p.pid,created_epoch=p.create_time(),parent_pid=p.ppid(),exe=p.exe(),argv=p.cmdline(),cwd=p.cwd())
def differences(records):
    out=[]
    for d in records:
        try:a=stat(d['path'])
        except OSError:a=None
        if a is None or not Path(a['path']).samefile(d['path']) or a['bytes']!=d['bytes'] or a['mtime_ns']!=d['mtime_ns']:out.append(dict(expected=d,observed=a))
    return out
def call(label,program,args,env):
    lp=LOG/(TAG+'.'+label+'.log');cp=LOG/(TAG+'.'+label+'.call.json')
    start=now()
    with lp.open('xb')as f:
        p=subprocess.Popen([str(program)]+args,cwd=HERE,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        child=identity(p.pid);rc=p.wait()
    rec=dict(stage=TAG+'.'+label,program=str(program),arguments=args,cwd=str(HERE),owner=OWNER,child=child,actual_exit_code=rc,direct_Popen_wait=True,started_utc=start,ended_utc=now(),log=stat(lp),SHA_scans=0,physical_acceptance=False)
    write(cp,rec);print(label,'actual_exit',rc,'child',child['pid'],flush=True)
    need(rc==0,label+' failed; preserve log and do not retry')
    return stat(cp)

OWNER=identity(os.getpid())
stage='preflight';protected=[];copies=[];build_ok=False;tool_exit=None;target_exit=None
try:
    need(not OUT.exists() and not EXE.exists() and not (HERE/'helper.obj').exists(),'Fresh output/helper required')
    for process in psutil.process_iter(['pid','name']):
        need((process.info['name']or'').casefold()!=EXE.name.casefold(),'Same-name GPU force target is already active')
    for suffix in ['compile.log','compile.call.json','link.log','link.call.json','memcheck.log','memcheck.start.json','target.start.json','memcheck.call.json','build.json','check.json']:
        need(not(LOG/(TAG+'.'+suffix)).exists(),'Fresh log collision: '+suffix)
    b=read(BUILD);s=read(BSOURCE)
    need(b['passed'] and b['actual_typed_exit_code']==0 and b['objects']==111 and b['source_stats_unchanged'] and b['protected_stats_unchanged'],'Corrected official build not sealed passed')
    need(not differences(s['files']) and not differences(s['protected']) and not differences(b['object_records']),'Corrected build source/protected/object metadata changed')
    cpucheck=read(LOG/'upl_c08_force_CPU_r1.check.json');cpucall=read(LOG/'upl_c08_force_CPU_r1.call.json');cpudone=read(CPU/'completion.json')
    need(cpucheck['passed'] and cpucall['exit_code']==0 and cpucall['typed_returncode_captured_from_Popen_wait'] and cpudone['passed'] and cpudone['actual_ct_calls']==1 and cpudone['physical_steps']==0,'Closed genuine CPU force reference not passed')
    comp=read(LOG/'upl_inactive_cutoff_GPU_r2.compile.call.json');link=read(LOG/'upl_inactive_cutoff_GPU_r2.link.call.json')
    intdir=Path(b['object_directory']);ca=[]
    for a in comp['arguments']:
        if a.startswith('/Fo'):a='/Fo'+str(HERE/'helper.obj')
        elif a.startswith('/Fd'):a='/Fd'+str(HERE/'compile.pdb')
        elif a.lower().endswith('.cpp'):a=str(SRC)
        ca.append(a)
    la=[]
    for a in link['arguments']:
        if a.startswith('/OUT:'):a='/OUT:'+str(EXE)
        elif a.startswith('/PDB:'):a='/PDB:'+str(HERE/'link.pdb')
        elif a.lower().endswith('.obj'):a=str(HERE/'helper.obj') if Path(a).name=='helper.obj' else str(intdir/Path(a).name)
        la.append(a)
    objects=[a for a in la if a.lower().endswith('.obj')]
    need(len(objects)==111 and len(set(objects))==111 and not any(Path(a).name.lower()=='main.obj' for a in objects),'Exact110 non-main plus fresh helper closure required')
    expected={str(Path(v['path']).resolve()) for v in b['object_records'] if Path(v['path']).name.lower()!='main.obj'}
    need({str(Path(a).resolve()) for a in objects if Path(a).name!='helper.obj'}==expected,'Object closure differs from corrected build')
    setup=subprocess.run('"'+str(Path(os.environ['SystemRoot'])/'System32/cmd.exe')+'" /d /c call "'+str(Path('D:/Program Files/VS2022/Common7/Tools/VsDevCmd.bat'))+'" -arch=x64 -host_arch=x64 >nul && set',capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
    need(setup.returncode==0,'Verified VS environment setup failed')
    env=dict(v.split('=',1) for v in setup.stdout.decode('mbcs').splitlines() if '=' in v and not v.startswith('='))
    libdirs=[Path(a[len('/LIBPATH:'):]) for a in la if a.startswith('/LIBPATH:')]+[Path(a) for a in env['LIB'].split(';') if a]
    libs=[]
    for a in la:
        if a.lower().endswith('.lib'):
            p=next((d/a for d in libdirs if (d/a).is_file()),None);need(p is not None,'Unresolved linker input '+a);libs.append(p)
    need(len(libs)==18,'Expected original18 libraries')
    runtime=[R/'bin/windows'/n for n in ['DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll']]
    extras=[SRC,NOTE,T/'support/upl_c08_force_r1.cpp',T/'notes/upl_c08_force_r1.json',BUILD,BSOURCE,LOG/'upl_wall_active_Debug_r2.call.json',LOG/'upl_c08_force_CPU_r1.call.json',LOG/'upl_c08_force_CPU_r1.check.json',SEED.with_suffix('.xml'),SEED.with_suffix('.bi4'),SEED.parent/(SEED.name+'_Normals.nbi4'),Path(comp['program']),Path(link['program']),SAN,Path(__file__)]+[CPU/(n+'.csv') for n in ['ids','kinematics','walls','rates']]+[CPU/'completion.json']+runtime+libs
    bypath={v['path']:v for v in s['files']+s['protected']+b['object_records']}
    for p in extras:
        d=stat(p)
        need(d['path'] not in bypath or d==bypath[d['path']],'Conflicting before metadata '+str(p));bypath[d['path']]=d
    protected=list(bypath.values())
    write(HERE/'consumed_before.json',dict(stage=TAG+'.consumed',source_build=stat(BUILD),source_archive=b['source_archive'],records=protected,SHA_scans=0))
    for p in [SRC,NOTE]:shutil.copy2(p,HERE/p.name);copies.append(stat(HERE/p.name))
    for p in runtime:
        dest=HERE/p.name;need(not dest.exists(),'Runtime copy collision');shutil.copy2(p,dest);need(dest.stat().st_size==p.stat().st_size and dest.stat().st_mtime_ns==p.stat().st_mtime_ns,'copy2 SMT mismatch');copies.append(stat(dest))
    stage='compile';cc=call('compile',comp['program'],ca,env)
    stage='link';lc=call('link',link['program'],la,env)
    need(not differences(protected) and not differences(copies),'Consumed metadata changed during helper build')
    build_ok=True;exe_stat=stat(EXE);copies.append(exe_stat)
    write(LOG/(TAG+'.build.json'),dict(stage=TAG+'.build',passed=True,source_build=stat(BUILD),compile_call=cc,link_call=lc,source=stat(SRC),author_note=stat(NOTE),program=exe_stat,objects=110,link_object_count=111,object_directory=str(intdir),runtime=[stat(HERE/p.name) for p in runtime],consumed_before=stat(HERE/'consumed_before.json'),consumed_stats_unchanged=True,SHA_scans=0,physical_acceptance=False))
    stage='memcheck';args=['--tool','memcheck','--leak-check','full','--error-exitcode','99',str(EXE),'--force','--cpu-dir',str(CPU),'-gpu:0','-stable','-mdbc_freeslip',str(SEED),str(OUT)]
    k32=ctypes.WinDLL('kernel32',use_last_error=True);k32.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k32.OpenProcess.restype=wintypes.HANDLE
    k32.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)];k32.GetExitCodeProcess.restype=wintypes.BOOL;k32.CloseHandle.argtypes=[wintypes.HANDLE];k32.CloseHandle.restype=wintypes.BOOL
    target=None;handle=None;lp=LOG/(TAG+'.memcheck.log');started=now()
    with lp.open('xb')as f:
        p=subprocess.Popen([str(SAN)]+args,cwd=HERE,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);tool=identity(p.pid)
        write(LOG/(TAG+'.memcheck.start.json'),dict(stage=TAG+'.memcheck.start',owner=OWNER,tool=tool,program=exe_stat,arguments=args,source_build=stat(BUILD),started_utc=started,SHA_scans=0))
        print('memcheck tool',p.pid,flush=True)
        while p.poll() is None:
            if target is None:
                try:
                    for child in psutil.Process(p.pid).children(recursive=True):
                        try:
                            if Path(child.exe()).resolve()==EXE.resolve():
                                handle=k32.OpenProcess(0x1000|0x00100000,False,child.pid);target=identity(child.pid)
                                write(LOG/(TAG+'.target.start.json'),dict(stage=TAG+'.target.start',target=target,tool=tool,handle_retained_for_actual_exit=bool(handle),started_utc=now(),SHA_scans=0));print('actual target',target['pid'],flush=True);break
                        except psutil.NoSuchProcess:pass
                except psutil.NoSuchProcess:pass
            time.sleep(.001)
        tool_exit=p.wait()
    exitcode=wintypes.DWORD(259);queried=bool(handle and k32.GetExitCodeProcess(handle,ctypes.byref(exitcode)));target_exit=exitcode.value if queried else None
    if handle:k32.CloseHandle(handle)
    write(LOG/(TAG+'.memcheck.call.json'),dict(stage=TAG+'.memcheck',program=str(SAN),arguments=args,cwd=str(HERE),owner=OWNER,tool=tool,target=target,tool_actual_exit_code=tool_exit,target_actual_Win32_exit=target_exit,target_exit_queried_from_retained_handle=queried,direct_Popen_wait=True,started_utc=started,ended_utc=now(),log=stat(lp),target_invocations=1,unsanitized_target_invocations=0,SHA_scans=0,physical_acceptance=False))
    print('SEALED actual exits tool',tool_exit,'target',target_exit,flush=True)
    changed=differences(protected);copy_changed=differences(copies)
    write(HERE/'consumed_after.json',dict(stage=TAG+'.consumed_after',records=[stat(v['path']) for v in protected],changed_paths=changed,helper_and_runtime_changed_paths=copy_changed,SHA_scans=0))
    need(not changed and not copy_changed,'Consumed metadata changed during component')
    need(tool_exit==0 and target_exit==0 and target and target['parent_pid']==tool['pid'],'Actual tool/target failed; do not retry')
    raw=lp.read_text(encoding='utf-8',errors='replace')
    need('ERROR SUMMARY: 0 errors' in raw and 'LEAK SUMMARY: 0 bytes leaked in 0 allocations' in raw,'Memcheck errors/leaks or missing summaries')
    stage='offline_structural_check';done=read(OUT/'completion.json')
    need(done['stage']=='upl_c08_gpu_force_r1' and done['passed'] and done['native_ids']==7060 and done['soil']==5000 and done['physical_steps']==0 and not done['physical_acceptance'],'Wrong native force completion')
    need(done['active_walls']==410 and done['OFF_in_prefix']==55 and done['actual_main_ct_calls']==1 and done['native_theta_checks']==5000 and done['native_sigma_rate_checks']==30000,'Incomplete original force coverage')
    for key in ['actual_finished_Ace_not_prescribed','G1_uploaded_then_original_CTE_restored','borrowed_derivative_NULL_before_free_Pos']:need(done[key],'Missing restoration/actual-force claim '+key)
    need(not done['production_allocator_proved'] and not done['half_or_cross_5Pa_claimed'],'Unsupported acceptance claim')
    def rows(path):
        with path.open(newline='',encoding='utf-8')as f:return list(csv.DictReader(f))
    data={n:rows(OUT/(n+'.csv')) for n in ['ids','kinematics','walls','rates','cpu_descriptor']};rowcounts={n:len(v) for n,v in data.items()}
    need(rowcounts==dict(ids=7060,kinematics=5000,walls=410,rates=5000,cpu_descriptor=70000),'CSV cardinality mismatch')
    def keyed(values):
        d={int(r['native_id']):r for r in values};need(len(d)==len(values),'Duplicate original ID');return d
    ids=keyed(data['ids']);kin=keyed(data['kinematics']);rates=keyed(data['rates']);walls=keyed(data['walls']);cpu_kin=keyed(rows(CPU/'kinematics.csv'));cpu_rates=keyed(rows(CPU/'rates.csv'));cpu_walls=keyed(rows(CPU/'walls.csv'))
    soil_ids=set(range(2060,7060));need(set(ids)==set(range(7060)) and set(kin)==set(rates)==set(cpu_kin)==set(cpu_rates)==soil_ids,'Original native membership mismatch')
    need(len({r['sorted_slot'] for r in data['ids']})==7060 and sum(int(r['is_fluid']) for r in data['ids'])==5000,'GPU sorted ID/code ledger invalid')
    need(set(walls)==set(cpu_walls),'Closed active wall ID membership differs')
    for values in data.values():
        for row in values:
            for key,value in row.items():
                if key!='field':need(math.isfinite(float(value)),'Nonfinite force CSV value')
    f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
    c=-1./8192.;h=f32(.048);n0=f32(.35);gz=f32(-9.81);kw=f32(1e9);mat=cpucheck['parsed_float_reference'];K=mat['K'];G=mat['G']
    need(mat['E']==f32(20e6) and mat['nu']==f32(.33),'CPU parsed float material differs')
    vmax=max(abs(float(r['stored_vz'])) for r in kin.values());db=128.*2.**-23*max(abs(c),vmax/h)+4096.*2.**-52*max(1.,abs(c));lam=K-2.*G/3.;mod=max(K+4.*G/3.,2.*G)
    names=['sxx','syy','szz','sxy','syz','sxz'];ref=[lam*c,lam*c,(lam+2.*G)*c,0.,0.,0.];bud=[db*mod+64.*2.**-23*max(1.,abs(v)) if i<3 else db*2.*G for i,v in enumerate(ref)]
    need(db==cpudone['derivative_budget_per_s']==done['derivative_budget_per_s'] and ref==cpudone['sigma_reference_Pa_s']==done['sigma_reference_Pa_s'] and bud==cpudone['sigma_budget_Pa_s']==done['sigma_budget_Pa_s'],'Original CPU predeclared budgets/reference mismatch')
    theta_max=0.;sigma_max=[0.]*6;max_image=0.;max_tangent=0.;max_wall_p_cpu=0.;max_wall_j_cpu=0.;max_ace=0.;rate_min=math.inf;rate_max=-math.inf;rate_sq=0.;rem_min=math.inf;rem_max=-math.inf
    for nid,a in kin.items():
        b0=cpu_kin[nid];r=rates[nid];theta=float(a['theta']);te=abs(theta-c)
        need(a['sorted_slot']==ids[nid]['sorted_slot'] and ids[nid]['is_fluid']=='1','Soil slot/code mismatch')
        for key in ['x','z','stored_vz']:need(float(a[key])==float(b0[key]),'CPU/GPU same input-coordinate/stored-velocity mismatch')
        need(float(a['x'])==float(ids[nid]['x']) and float(a['z'])==float(ids[nid]['z']) and float(a['stored_vz'])==f32(c*float(a['z'])),'Native manufactured field differs')
        need(float(a['theta_ref'])==c and float(a['theta_error'])==te and float(a['theta_budget'])==db and te<=db,'Independent theta original budget failed');theta_max=max(theta_max,te)
        for i,key in enumerate(names):
            err=abs(float(a[key])-ref[i]);need(float(a[key+'_ref'])==ref[i] and float(a[key+'_error'])==err and float(a[key+'_budget'])==bud[i] and err<=bud[i],'Independent sigma original budget failed '+key);sigma_max[i]=max(sigma_max[i],err)
        j=float(r['J']);n=1.-(1.-n0)/j;compression=-kw/n*theta;rate=float(r['rate_Pa_s']);remainder=rate-compression
        need(j>1.-n0 and float(r['theta'])==theta and float(r['n'])==n and float(r['local_compression_Pa_s'])==compression and float(r['spatial_acceleration_remainder_Pa_s'])==remainder,'Complete rate component ledger differs')
        for axis,g in [('x',0.),('y',0.),('z',gz)]:
            ace=float(a['Ace_'+axis]);need(float(r['Ace_'+axis])==ace and float(r['true_a'+axis])==ace+g,'Finished native Ace or true-acceleration ledger differs');max_ace=max(max_ace,abs(ace))
        rate_min=min(rate_min,rate);rate_max=max(rate_max,rate);rate_sq+=rate*rate;rem_min=min(rem_min,remainder);rem_max=max(rem_max,remainder)
    for nid,w in walls.items():
        need(nid<2060 and w['sorted_slot']==ids[nid]['sorted_slot'] and ids[nid]['is_fluid']=='0','Wall original membership mismatch')
        need(int(w['slipmode'])==(3 if nid<255 or nid>=1800 else 2) and float(w['legacy_rho'])==2072.5 and all(float(w['physical_v'+axis])==0. for axis in ['x','y','z']),'Wall physical velocity/rho/slip changed')
        image=c*float(w['B_z']);tangent=0. if int(w['slipmode'])==2 else image;ei=abs(float(w['derivative_vz'])-image);et=abs(float(w['tangent_vz'])-tangent)
        need(float(w['derivative_vz_affine'])==image and float(w['derivative_vz_error'])==ei and float(w['tangent_vz_affine'])==tangent and float(w['tangent_vz_error'])==et and float(w['J'])>1.-n0,'Wall image/physical J descriptor differs')
        max_image=max(max_image,ei);max_tangent=max(max_tangent,et);max_wall_p_cpu=max(max_wall_p_cpu,abs(float(w['p_Pa'])-float(cpu_walls[nid]['p_Pa'])));max_wall_j_cpu=max(max_wall_j_cpu,abs(float(w['J'])-float(cpu_walls[nid]['J'])))
    cross_names=['theta']+names+['Ace_x','Ace_y','Ace_z','legacy_Arc','rate_Pa_s','local_compression_Pa_s','spatial_acceleration_remainder_Pa_s'];seen=set();cross_max={k:0. for k in cross_names}
    for r in data['cpu_descriptor']:
        nid=int(r['native_id']);key=r['field'];need(nid in soil_ids and key in cross_names and (nid,key)not in seen and r['comparison_is_descriptive']=='1','CPU descriptor membership invalid');seen.add((nid,key));gp=rates[nid] if key in cross_names[11:] else kin[nid];cp=cpu_rates[nid] if key in cross_names[11:] else cpu_kin[nid];gv=float(gp[key]);cv=float(cp[key]);delta=abs(gv-cv)
        need(float(r['CPU_value'])==cv and float(r['GPU_value'])==gv and float(r['absolute_difference'])==delta,'Cross descriptor value is not genuine closed CPU/GPU row');cross_max[key]=max(cross_max[key],delta)
    need(theta_max==done['max_theta_error_per_s'] and sigma_max==done['max_sigma_error_Pa_s'],'Completion/error maxima mismatch')
    need(not differences(protected) and not differences(copies),'Final consumed metadata changed')
    files=[stat(p) for p in OUT.iterdir() if p.is_file()]
    write(LOG/(TAG+'.check.json'),dict(stage=TAG+'.check',passed=True,source_build=stat(BUILD),helper_build=stat(LOG/(TAG+'.build.json')),memcheck_call=stat(LOG/(TAG+'.memcheck.call.json')),source_CPU_check=stat(LOG/'upl_c08_force_CPU_r1.check.json'),tool_actual_exit_code=tool_exit,target_actual_Win32_exit=target_exit,zero_memcheck_errors=True,zero_memcheck_leaks=True,completion=done,independent_rows=rowcounts,original_derivative_budget=db,max_theta_error=theta_max,max_theta_error_over_original_budget=theta_max/db,original_sigma_reference=ref,original_sigma_budgets=bud,max_sigma_errors=sigma_max,max_sigma_error_over_original_budget=[e/b for e,b in zip(sigma_max,bud)],independent_wall_image_error_descriptive=max_image,independent_wall_tangent_error_descriptive=max_tangent,wall_CPU_p_error_descriptive=max_wall_p_cpu,wall_CPU_J_error_descriptive=max_wall_j_cpu,cross_CPU_maxima_descriptive=cross_max,max_native_Ace_component=max_ace,rate_min_max=[rate_min,rate_max],rate_RMS=math.sqrt(rate_sq/5000),spatial_remainder_min_max=[rem_min,rem_max],files=files,consumed_stats_unchanged=True,helper_program_and_runtime_stats_unchanged=True,same_110_non_main_objects=True,target_invocations=1,unsanitized_target_invocations=0,SHA_scans=0,physical_steps=0,cross_backend_or_half_5Pa_bound_claimed=False,public_wall_or_physical_acceptance=False))
    print('COMPONENT STRUCTURAL CHECK PASSED',json.dumps(done,ensure_ascii=False),flush=True)
except BaseException as e:
    changed=differences(protected);copy_changed=differences(copies)
    failure=dict(stage=TAG+'.failure',failed_stage=stage,reason=str(e),helper_build_passed=build_ok,tool_actual_exit_code=tool_exit,target_actual_Win32_exit=target_exit,changed_consumed_paths=changed,changed_helper_runtime_paths=copy_changed,SHA_scans=0,physical_acceptance=False,no_auto_retry=True)
    fp=LOG/(TAG+'.failure.json')
    if not fp.exists():write(fp,failure)
    print('PRESERVED FAILURE',json.dumps(failure,ensure_ascii=False),flush=True)
    raise
