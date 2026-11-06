import csv,ctypes,datetime,json,os,shutil,subprocess,time,traceback,zipfile,zlib
from ctypes import wintypes as w
from pathlib import Path,PurePosixPath
import psutil
R=Path(__file__).resolve().parents[5];T=Path(__file__).resolve().parents[1];S=R/'src';L=T/'logs';O=T/'outputs'
TAG='upl_free_seepage_GPU_r1';CHECK=L/(TAG+'.check.json');STATS=L/(TAG+'.stats.json')
SOURCE=T/'support/upl_free_seepage_gpu_r1.cpp';NOTE=T/'notes/upl_free_seepage_gpu_r1.json';before={};calls=[];results={}
def need(b,s):
    if not b:raise RuntimeError(s)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,j):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(j,f,indent=2)
def stat(p):
    p=Path(p).resolve();v=p.stat();return dict(path=str(p),bytes=v.st_size,mtime_ns=v.st_mtime_ns)
def bind(p,e=None):
    a=stat(p);before.setdefault(a['path'],a)
    if e:need((a['bytes'],a['mtime_ns'])==(e['bytes'],e['mtime_ns']),'Bound stat mismatch: '+str(p))
    return a
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.GetProcessTimes.argtypes=[w.HANDLE,*([ctypes.POINTER(w.FILETIME)]*4)]
k.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]
k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
k.CloseHandle.argtypes=[w.HANDLE]
def identity(handle,pid):
    ft=[w.FILETIME() for _ in range(4)];need(k.GetProcessTimes(handle,*[ctypes.byref(a) for a in ft]),'Process times unavailable')
    size=w.DWORD(32768);image=ctypes.create_unicode_buffer(size.value);need(k.QueryFullProcessImageNameW(handle,0,image,ctypes.byref(size)),'Process image unavailable')
    try:argv=psutil.Process(pid).cmdline()
    except psutil.NoSuchProcess:argv=None
    return dict(pid=pid,created_epoch=((ft[0].dwHighDateTime<<32)|ft[0].dwLowDateTime)/1e7-11644473600,exe=image.value,argv=argv)
def invoke(label,argv,env,target=None):
    log=L/(TAG+'.'+label+'.log');receipt=L/(TAG+'.'+label+'.call.json');need(not log.exists() and not receipt.exists(),'Call collision')
    record=dict(stage=TAG+'.'+label,program=argv[0],arguments=argv[1:],working_directory=str(S),owner=dict(pid=os.getpid(),created_epoch=psutil.Process().create_time()),started_utc=utc(),SHA_scans=0,physical_acceptance=False)
    target_handle=None
    try:
        with log.open('xb') as f:
            process=subprocess.Popen(argv,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT);record['child']=identity(int(process._handle),process.pid)
            if target:
                while process.poll() is None:
                    if target_handle is None:
                        try:descendants=psutil.Process(process.pid).children(recursive=True)
                        except psutil.NoSuchProcess:descendants=[]
                        for child in descendants:
                            try:
                                if child.name().lower()!=target.name.lower():continue
                                handle=k.OpenProcess(0x1000|0x100000,False,child.pid)
                                if not handle:continue
                                item=identity(handle,child.pid)
                                if not Path(item['exe']).samefile(target):k.CloseHandle(handle);continue
                                target_handle=handle;record['target']=item;break
                            except psutil.NoSuchProcess:continue
                    time.sleep(.005)
            rc=process.wait();code=w.DWORD();need(k.GetExitCodeProcess(int(process._handle),ctypes.byref(code)),'Tool Win32 exit unavailable')
            record.update(actual_Popen_wait_exit=rc,actual_tool_Win32_exit=code.value,ended_utc=utc(),console_log=str(log))
            if target_handle:
                c=w.DWORD();need(k.GetExitCodeProcess(target_handle,ctypes.byref(c)),'Target Win32 exit unavailable');record['actual_target_Win32_exit']=c.value
            save(receipt,record);calls.append(str(receipt))
        need(Path(record['child']['exe']).samefile(argv[0]),'Owned tool image mismatch');need(rc==0 and code.value==0,'Actual call failed: '+label+'; see '+str(log))
        if target:need(target_handle is not None and record['actual_target_Win32_exit']==0,'Missing/nonzero retained target exit')
        return record
    finally:
        if target_handle:k.CloseHandle(target_handle)
def build_run(which,buildtag,legacy):
    bp=L/(buildtag+'.build.json');b=read(bp);bind(bp);need(b['passed'] and b['actual_typed_exit_code']==0 and b['source_stats_unchanged'],'Unsealed authoritative GPU build')
    objects=[e for e in b['project_objects'] if Path(e['path']).name.lower()!='main.obj'];need(len(objects)==110 and b['non_main_objects']==110,'Wrong nonmain110 closure')
    for e in objects:bind(e['path'],e)
    src=read(b['source']);bind(b['source']);expected={str(Path(e['path']).resolve()):e for e in src['files']}
    helper=O/('upl_free_seepage_GPU_'+which+'_helper_r1');result=O/('upl_free_seepage_GPU_'+which+'_r1');need(not helper.exists() and not result.exists(),'Fresh helper/result required');helper.mkdir()
    include=S/'source';archive=None
    if legacy:
        archive=bind(src['archive']['path'],src['archive']);headers=Path(os.environ['LOCALAPPDATA'])/'Temp/upl_fs_gpu_oldhdr_r1';need(not headers.exists(),'Old short header destination exists');headers.mkdir();members=[]
        with zipfile.ZipFile(archive['path']) as z:
            for item in z.infolist():
                rel=PurePosixPath(item.filename)
                if rel.parts[0]!='src' or rel.suffix.lower() not in ('.h','.hpp','.inl'):continue
                dest=headers/Path(*rel.parts[1:]);need(dest.resolve().is_relative_to(headers.resolve()),'Archive header escapes root');data=z.read(item)
                need(len(data)==item.file_size and zlib.crc32(data)&0xffffffff==item.CRC,'Header CRC/size mismatch');dest.parent.mkdir(parents=True,exist_ok=True)
                with dest.open('xb') as f:f.write(data)
                members.append(dict(archive_path=item.filename,crc32=item.CRC,**bind(dest)))
        include=headers/'source';need((include/'JSphGpu_ker.h').is_file(),'Old GPU declaration missing');save(helper/'headers.json',dict(archive=archive,entries=members,CRC_and_bytes_checked=True,SHA_scans=0))
    obj=helper/'helper.obj';exe=helper/'upl_free_seepage_gpu_r1.exe';deps=helper/'compile.dependencies.json'
    argv=[str(CL),'/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS','/D_WITHGPU','/I'+str(include),'/I'+str(CUDA/'include'),'/Fo'+str(obj),'/Fd'+str(helper/'compile.pdb'),'/sourceDependencies',str(deps),'/Od','/MTd','/Zi','/RTC1']
    if legacy:argv.append('/DUPL_FREE_SEEPAGE_LEGACY_ONLY')
    invoke(which+'.compile',[*argv,str(SOURCE)],ENV)
    dependencies=read(deps)['Data']['Includes'];headers=[]
    for p in dependencies:
        p=Path(p).resolve()
        if legacy:need(not p.is_relative_to((S/'source').resolve()),'Old compile used a current source header')
        headers.append(bind(p,expected.get(str(p))))
    need(any(Path(p).resolve()==(include/'JSphGpu_ker.h').resolve() for p in dependencies),'Actual selected GPU header dependency missing')
    invoke(which+'.link',[str(LINK),*LINKARGS,'/OUT:'+str(exe),str(obj),*[e['path'] for e in objects],'/PDB:'+str(helper/'link.pdb')],ENV)
    runtime=[]
    for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
        origin=R/'bin/windows'/name;e=bind(origin);shutil.copy2(origin,helper/name);a=stat(helper/name);need((e['bytes'],e['mtime_ns'])==(a['bytes'],a['mtime_ns']),'Runtime copy mismatch');runtime.append(a)
    save(L/(TAG+'.'+which+'.build.json'),dict(passed=True,source_build=stat(bp),program=stat(exe),objects=objects,headers=headers,old_archive=archive,runtime=runtime,SHA_scans=0,physical_acceptance=False))
    if legacy:invoke(which+'.run',[str(exe),'--out',str(result)],ENV)
    else:
        mem=L/(TAG+'.new.memcheck.log');need(not mem.exists(),'Memcheck collision')
        invoke(which+'.memcheck',[str(SAN),'--tool','memcheck','--leak-check','full','--target-processes','all','--error-exitcode','86','--log-file',str(mem),str(exe),'--out',str(result)],ENV,exe)
        text=mem.read_text(encoding='utf-8');need('ERROR SUMMARY: 0 errors' in text and 'LEAK SUMMARY: 0 bytes leaked in 0 allocations' in text,'Memcheck errors/leaks or missing summaries')
    done=read(result/'completion.json');need(done['passed'] and done['legacy_only']==legacy and done['rate_rows']==243 and done['completed_physical_steps']==0,'Component completion mismatch')
    need((result/'free_off_rates.bin').stat().st_size==972,'OFF payload is not243floats')
    if not legacy:need(done['projection_rows']==243 and done['nonfinite_input_bits_preserved']==2 and done['hydrostatic_naive_negative_witnesses']>0,'Missing candidate coverage')
    results[which]=dict(directory=str(result),completion=done,program=stat(exe));print(which,done,flush=True);return result
try:
    need(not CHECK.exists() and not STATS.exists(),'Receipt collision')
    cpucheck=L/'upl_free_seepage_CPU_old_headers_r2.check.json';need(read(cpucheck)['passed'],'CPU prerequisite not passed');bind(cpucheck)
    bind(SOURCE);bind(NOTE);bind(T/'support/upl_cubic_component_r2.cpp')
    need(not any((p.info['name'] or '').lower()=='upl_free_seepage_gpu_r1.exe' for p in psutil.process_iter(['name'])),'Duplicate component active')
    CL=Path('D:/Program Files/VS2022/VC/Tools/MSVC/14.36.32532/bin/Hostx64/x64/cl.exe');LINK=CL.with_name('link.exe');CUDA=Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7');SAN=CUDA/'compute-sanitizer/compute-sanitizer.exe';bind(CL);bind(LINK);bind(SAN)
    recipe=read(L/'upl_noslip_gpu_component_r1_link.call.json');LINKARGS=[a for a in recipe['arguments'] if not a.lower().endswith('.obj') and not a.upper().startswith(('/OUT:','/PDB:'))]
    for a in LINKARGS:
        if a.endswith('.lib'):
            for folder in (S/'lib/vs2022',CUDA/'lib/x64'):
                if (folder/a).is_file():bind(folder/a);break
    cmd=Path(os.environ['SystemRoot'])/'System32/cmd.exe';dev=Path('D:/Program Files/VS2022/Common7/Tools/VsDevCmd.bat')
    setup=subprocess.run('"'+str(cmd)+'" /d /c call "'+str(dev)+'" -arch=x64 -host_arch=x64 >nul && set',capture_output=True);need(setup.returncode==0,'VS setup failed')
    ENV=dict(os.environ);ENV.update(a.split('=',1) for a in setup.stdout.decode('mbcs').splitlines() if '=' in a and not a.startswith('='));ENV['OMP_NUM_THREADS']='1'
    new=build_run('new','upl_free_seepage_Debug_r1',False);old=build_run('old','upl_container_Debug_r1',True)
    comparison={name:(new/name).read_bytes()==(old/name).read_bytes() for name in ('free_off_rates.bin','mask.csv')};need(all(comparison.values()),'GPU OFF or mask differs from archived old source closure')
    cpup=Path(read(L/'upl_free_seepage_CPU_r1.check.json')['results']['new']['directory']);need(read(cpup/'completion.json')['passed'],'New CPU completion unavailable')
    def keyed(path):
        data=list(csv.DictReader(path.open(newline='',encoding='utf-8')));d={(int(r['field']),int(r['native_id'])):r for r in data};need(len(data)==len(d)==243,'Cross-descriptor IDs incomplete/duplicate');return d
    cpu=keyed(cpup/'rates.csv');gpu=keyed(new/'rates.csv');need(cpu.keys()==gpu.keys(),'CPU/GPU material ID sets differ');cross={}
    for field in range(3):
        keys=[q for q in cpu if q[0]==field];need(len(keys)==81,'Cross-descriptor field IDs incomplete')
        for q in keys:
            for column in ('p_pa','Ace_x','Ace_z'):need(float(cpu[q][column])==float(gpu[q][column]),'Cross-input prescribed field differs')
        cross[str(field)]=dict(IDs=81,FS_class_differences=sum(cpu[q]['fstype']!=gpu[q]['fstype'] for q in keys),max_abs_OFF_rate_Pa_s=max(abs(float(cpu[q]['free_off_rate'])-float(gpu[q]['free_off_rate'])) for q in keys),max_abs_ON_rate_Pa_s=max(abs(float(cpu[q]['free_on_rate'])-float(gpu[q]['free_on_rate'])) for q in keys),max_abs_reference_Pa_s=max(abs(float(cpu[q]['independent_reference'])-float(gpu[q]['independent_reference'])) for q in keys),new_5Pa_or_FSNormal_gate=False)
    changed=[p for p,e in before.items() if stat(p)!=e];need(not changed,'Consumed SMT changed: '+str(changed));save(STATS,dict(inputs=list(before.values()),consumed_stats_unchanged=True,SHA_scans=0))
    save(CHECK,dict(stage=TAG,passed=True,results=results,old_new_byte_comparisons=comparison,CPU_GPU_actual_ID_descriptors=cross,CPU_control=str(cpup),calls=calls,consumed_stats_unchanged=True,SHA_scans=0,solver_or_native_decoder_invocations=0,physical_acceptance=False));print(json.dumps(dict(passed=True,old_new_byte_comparisons=comparison,CPU_GPU_actual_ID_descriptors=cross)),flush=True)
except BaseException as e:
    changed=[p for p,a in before.items() if not Path(p).exists() or stat(p)!=a]
    if not STATS.exists():save(STATS,dict(inputs=list(before.values()),changed=changed,consumed_stats_unchanged=not changed,SHA_scans=0))
    if not CHECK.exists():save(CHECK,dict(stage=TAG,passed=False,first_failure=str(e),traceback=traceback.format_exc(),results=results,calls=calls,changed=changed,SHA_scans=0,physical_acceptance=False))
    print(traceback.format_exc(),flush=True);raise
