import csv, ctypes, datetime, json, math, os, shutil, subprocess, time
from ctypes import wintypes
from pathlib import Path
import psutil

R=Path(r'D:/MYF/SPH/GeoDualSPHysics_redevelop_f66777b')
T=R/'examples/Hydromechanic coupling/08_LianSaturatedColumnCollapse_u_pl/tests'
TAG='upl_c08_global_GPU_r1'
HERE=Path(__file__).resolve().parent
OUT=T/'outputs'/TAG
LOG=T/'logs'
SRC=T/'support/upl_c08_gpu_global_r1.cpp'
NOTE=T/'notes/upl_c08_gpu_global_r1_author.json'
BUILD=LOG/'upl_wall_active_Debug_r2.build.json'
BSOURCE=LOG/'upl_wall_active_Debug_r2.source.json'
CPU=T/'outputs/upl_c08_global_CPU_r1/fields.csv'
SEED=T/'outputs/upl_c08_observer_r1_seed/CaseLianSaturatedColumnCollapse_geometry_r1'
SAN=Path(r'C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.3/compute-sanitizer/compute-sanitizer.exe')
EXE=HERE/'upl_c08_gpu_global_r1.exe'
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
    for suffix in ['compile.log','compile.call.json','link.log','link.call.json','memcheck.log','memcheck.start.json','target.start.json','memcheck.call.json','build.json','check.json']:
        need(not(LOG/(TAG+'.'+suffix)).exists(),'Fresh log collision: '+suffix)
    b=read(BUILD);s=read(BSOURCE)
    need(b['passed'] and b['actual_typed_exit_code']==0 and b['objects']==111 and b['source_stats_unchanged'] and b['protected_stats_unchanged'],'Corrected official build not sealed passed')
    need(not differences(s['files']) and not differences(s['protected']) and not differences(b['object_records']),'Corrected build source/protected/object metadata changed')
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
    extras=[SRC,NOTE,T/'notes/upl_c08_gpu_global_r1.json',BUILD,BSOURCE,LOG/'upl_wall_active_Debug_r2.call.json',CPU,LOG/'upl_c08_global_CPU_r1.call.json',LOG/'upl_c08_global_CPU_r1.check.json',SEED.with_suffix('.xml'),SEED.with_suffix('.bi4'),SEED.parent/(SEED.name+'_Normals.nbi4'),Path(comp['program']),Path(link['program']),SAN,Path(__file__)]+runtime+libs
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
    stage='memcheck';args=['--tool','memcheck','--leak-check','full','--error-exitcode','99',str(EXE),'--global','--cpu-reference',str(CPU),'-gpu:0','-stable','-mdbc_freeslip',str(SEED),str(OUT)]
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
    need(done['stage']=='upl_c08_gpu_global_r1' and done['passed'] and done['native_ids']==7060 and done['soil']==5000 and done['physical_steps']==0 and not done['physical_acceptance'],'Wrong native component completion')
    for key in ['in_range_OFF_rejected','genuine_observer_Init','real_PosCell_and_cell_table_preserved','all_original_state_controls_restored','prescribed_Ace_not_momentum']:need(done[key],'Missing required completion '+key)
    need(done['OFF_outside_or_missing_supported_pairs']==0 and done['finite_poison_live_typed_equal_rows']==done['CPU_descriptor_rows']==5000+done['active'],'Incomplete live/membership invariant')
    rowcounts={};fieldsets={0:{},1:{}}
    for name in ['ids','cells','pairs','walls','fields','cpu_descriptor']:
        with (OUT/(name+'.csv')).open(newline='',encoding='utf-8')as f:
            rows=csv.DictReader(f);count=0
            for row in rows:
                count+=1
                if name=='fields':
                    trial=int(row['trial']);nid=int(row['native_id']);need(nid not in fieldsets[trial],'Duplicate live row');fieldsets[trial][nid]={k:v for k,v in row.items() if k!='trial'}
                    need(all(math.isfinite(float(v)) for v in row.values()),'Nonfinite live CSV field')
                elif name=='pairs':need(row['real_search_covered']=='1' and row['mode']=='1' and int(row['sorted_fixed'])<int(row['NpbOk']),'Invalid real GPU support CSV')
        rowcounts[name]=count
    need(rowcounts['ids']==7060 and rowcounts['walls']==4120 and rowcounts['fields']==2*done['CPU_descriptor_rows'] and rowcounts['cpu_descriptor']==26*done['CPU_descriptor_rows'],'CSV cardinality mismatch')
    need(fieldsets[0]==fieldsets[1],'Finite/poison serialized live fields differ')
    need(not differences(protected) and not differences(copies),'Final consumed metadata changed')
    files=[stat(p) for p in OUT.iterdir() if p.is_file()]
    write(LOG/(TAG+'.check.json'),dict(stage=TAG+'.check',passed=True,source_build=stat(BUILD),helper_build=stat(LOG/(TAG+'.build.json')),memcheck_call=stat(LOG/(TAG+'.memcheck.call.json')),tool_actual_exit_code=tool_exit,target_actual_Win32_exit=target_exit,zero_memcheck_errors=True,zero_memcheck_leaks=True,completion=done,rows=rowcounts,own_finite_poison_serialized_fields_equal=True,files=files,consumed_stats_unchanged=True,helper_program_and_runtime_stats_unchanged=True,same_110_non_main_objects=True,target_invocations=1,unsanitized_target_invocations=0,SHA_scans=0,physical_steps=0,root_offline_affine_p_J_budget_join_pending=True,cross_backend_or_half_5Pa_bound_claimed=False,public_wall_or_physical_acceptance=False))
    print('COMPONENT STRUCTURAL CHECK PASSED',json.dumps(done,ensure_ascii=False),flush=True)
except BaseException as e:
    changed=differences(protected);copy_changed=differences(copies)
    failure=dict(stage=TAG+'.failure',failed_stage=stage,reason=str(e),helper_build_passed=build_ok,tool_actual_exit_code=tool_exit,target_actual_Win32_exit=target_exit,changed_consumed_paths=changed,changed_helper_runtime_paths=copy_changed,SHA_scans=0,physical_acceptance=False,no_auto_retry=True)
    fp=LOG/(TAG+'.failure.json')
    if not fp.exists():write(fp,failure)
    print('PRESERVED FAILURE',json.dumps(failure,ensure_ascii=False),flush=True)
    raise
