import ctypes,datetime,json,os,shutil,subprocess,traceback,zipfile,zlib
from ctypes import wintypes as w
from pathlib import Path,PurePosixPath
import psutil
R=Path(__file__).resolve().parents[5];T=Path(__file__).resolve().parents[1];L=T/'logs';O=T/'outputs';S=R/'src'
TAG='upl_free_seepage_CPU_old_headers_r2';CHECK=L/(TAG+'.check.json');SNAP=L/(TAG+'.stats.json');before={};calls=[]
SOURCE=T/'support/upl_free_seepage_cpu_r1.cpp';NOTE=T/'notes/upl_free_seepage_cpu_r1.json'
def need(ok,text):
    if not ok:raise RuntimeError(text)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2)
def stat(p):
    p=Path(p).resolve();a=p.stat();return dict(path=str(p),bytes=a.st_size,mtime_ns=a.st_mtime_ns)
def bind(p,expected=None):
    e=stat(p);before.setdefault(e['path'],e)
    if expected:need((e['bytes'],e['mtime_ns'])==(expected['bytes'],expected['mtime_ns']),'Bound stat mismatch: '+e['path'])
    return e
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.GetProcessTimes.argtypes=[w.HANDLE,ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME)]
k.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]
def invoke(label,argv,env):
    log=L/(TAG+'.'+label+'.log');cp=L/(TAG+'.'+label+'.call.json');need(not log.exists() and not cp.exists(),'Call collision')
    rec=dict(stage=TAG+'.'+label,program=argv[0],arguments=argv[1:],working_directory=str(S),started_utc=utc(),physical_acceptance=False)
    with log.open('xb') as f:
        p=subprocess.Popen(argv,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT)
        ft=[w.FILETIME() for _ in range(4)];need(k.GetProcessTimes(int(p._handle),*[ctypes.byref(a) for a in ft]),'Process time query failed')
        created=((ft[0].dwHighDateTime<<32)|ft[0].dwLowDateTime)/1e7-11644473600
        size=w.DWORD(32768);image=ctypes.create_unicode_buffer(size.value);need(k.QueryFullProcessImageNameW(int(p._handle),0,image,ctypes.byref(size)),'Process image query failed')
        try:actual_argv=psutil.Process(p.pid).cmdline()
        except psutil.NoSuchProcess:actual_argv=None
        rec['child']=dict(pid=p.pid,created_epoch=created,exe=image.value,command=actual_argv,parent_pid=os.getpid())
        rc=p.wait();win=w.DWORD();need(k.GetExitCodeProcess(int(p._handle),ctypes.byref(win)),'Win32 exit query failed')
        rec.update(exit_code=rc,actual_win32_exit_code=win.value,owned_call_exited=True,typed_returncode_captured_from_Popen_wait=True,ended_utc=utc(),log=str(log));save(cp,rec);calls.append(str(cp))
    need(Path(image.value).samefile(argv[0]),'Owned image mismatch');need(rc==0 and win.value==0,'Actual '+label+' failed; '+str(log));return rec
try:
    need(not CHECK.exists() and not SNAP.exists(),'Receipt collision')
    prior_path=L/'upl_free_seepage_CPU_r1.check.json';prior=read(prior_path);bind(prior_path)
    need(not prior['passed'] and 'WinError 206' in prior['first_failure'] and prior['results']['new']['completion']['passed'],'Unexpected original failure/new result')
    need(not any('.old.' in Path(p).name for p in prior['calls']),'An original old call already occurred')
    bind(SOURCE);bind(NOTE);bind(T.parent.parent/'02_TerzaghiConsolidation_q0_PR/tests/support/upl_p2_feedback_harness_r1.cpp')
    helper=O/'upl_free_seepage_CPU_old_helper_r2';result=O/'upl_free_seepage_CPU_old_r2';headers=Path(os.environ['LOCALAPPDATA'])/'Temp/upl_fs_oldhdr_r2'
    need(not helper.exists() and not result.exists() and not headers.exists(),'Fresh old paths collide')
    need(not any((p.info['name'] or '').lower()=='upl_free_seepage_cpu_r1.exe' for p in psutil.process_iter(['name'])),'Duplicate component active')
    bp=L/'upl_container_DebugCPU_r1.build.json';b=read(bp);bind(bp);need(b['passed'] and b['actual_typed_exit_code']==0 and b['source_stats_unchanged'],'Old build unsealed')
    objects=[e for e in b['project_objects'] if Path(e['path']).name.lower()!='main.obj'];need(len(objects)==85 and b['non_main_objects']==85,'Wrong old non-main closure')
    for e in objects:bind(e['path'],e)
    src=read(b['source']);bind(b['source']);archive=bind(src['archive']['path'],src['archive']);helper.mkdir();headers.mkdir();members=[]
    with zipfile.ZipFile(archive['path']) as z:
        for member in z.infolist():
            rel=PurePosixPath(member.filename)
            if rel.parts[0]!='src' or rel.suffix.lower() not in ('.h','.hpp','.inl'):continue
            dest=headers/Path(*rel.parts[1:]);need(dest.resolve().is_relative_to(headers.resolve()),'Header path escapes root');data=z.read(member)
            need(len(data)==member.file_size and zlib.crc32(data)&0xffffffff==member.CRC,'Archive entry CRC/bytes mismatch');dest.parent.mkdir(parents=True,exist_ok=True)
            with dest.open('xb') as f:f.write(data)
            need(dest.stat().st_size==member.file_size,'Extracted header byte count differs');members.append(dict(archive_path=member.filename,crc32=member.CRC,**bind(dest)))
    include=headers/'source';need((include/'JSph.h').is_file() and (include/'JSphCpuSingle.h').is_file(),'Incomplete old header root')
    save(helper/'headers.json',dict(source_archive=archive,extracted_root=str(headers),CRC_and_actual_bytes_checked=True,entries=members,SHA_scans=0))
    CL=Path('D:/Program Files/VS2022/VC/Tools/MSVC/14.36.32532/bin/Hostx64/x64/cl.exe');LINK=CL.with_name('link.exe');bind(CL);bind(LINK)
    cmd=Path(os.environ['SystemRoot'])/'System32/cmd.exe';dev=Path('D:/Program Files/VS2022/Common7/Tools/VsDevCmd.bat')
    setup=subprocess.run('"'+str(cmd)+'" /d /c call "'+str(dev)+'" -arch=x64 -host_arch=x64 >nul && set',capture_output=True);need(setup.returncode==0,'VS environment setup failed')
    env=dict(os.environ);env.update(a.split('=',1) for a in setup.stdout.decode('mbcs').splitlines() if '=' in a and not a.startswith('='));env['OMP_NUM_THREADS']='1'
    obj=helper/'helper.obj';exe=helper/'upl_free_seepage_cpu_r1.exe';deps=helper/'compile.dependencies.json'
    invoke('compile',[str(CL),'/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS','/DUPL_FREE_SEEPAGE_LEGACY_ONLY','/I'+str(include),'/Fo'+str(obj),'/Fd'+str(helper/'compile.pdb'),'/sourceDependencies',str(deps),'/Od','/MTd','/Zi','/RTC1',str(SOURCE)],env)
    dependencies=read(deps)['Data']['Includes'];header_rows=[]
    for p in dependencies:
        p=Path(p).resolve();need(not p.is_relative_to((S/'source').resolve()),'Old compile consumed a current header: '+str(p));header_rows.append(bind(p))
    need(all(any(Path(p).resolve()==(include/name).resolve() for p in dependencies) for name in ('JSph.h','JSphCpu.h','JSphCpuSingle.h')),'Actual old JSph header dependency missing')
    recipe=read(L/'upl_gravity_wall_cpu_r2_link.call.json');linkargs=[a for a in recipe['arguments'] if not a.lower().endswith('.obj') and not a.upper().startswith(('/OUT:','/PDB:'))]
    for a in linkargs:
        if a.endswith('.lib') and (S/'lib/vs2022'/a).is_file():bind(S/'lib/vs2022'/a)
    invoke('link',[str(LINK),*linkargs,'/OUT:'+str(exe),str(obj),*[e['path'] for e in objects],'/PDB:'+str(helper/'link.pdb')],env)
    runtime=[]
    for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
        source=R/'bin/windows'/name;e=bind(source);shutil.copy2(source,helper/name);copy=stat(helper/name);need((e['bytes'],e['mtime_ns'])==(copy['bytes'],copy['mtime_ns']),'Runtime copy mismatch');runtime.append(copy)
    save(L/(TAG+'.build.json'),dict(stage=TAG+'.build',passed=True,source_build=stat(bp),program=stat(exe),objects=objects,headers=header_rows,archive=archive,runtime=runtime,physical_acceptance=False,SHA_scans=0))
    invoke('run',[str(exe),'--out',str(result)],env);done=read(result/'completion.json');need(done['passed'] and done['legacy_only'] and done['rate_rows']==243 and done['completed_physical_steps']==0,'Unexpected old completion')
    new=Path(prior['results']['new']['directory']);comparisons={}
    for name in ('free_off_rates.bin','mask.csv'):
        bind(new/name);bind(result/name);comparisons[name]=(new/name).read_bytes()==(result/name).read_bytes()
    need((result/'free_off_rates.bin').stat().st_size==972 and all(comparisons.values()),'Old/new OFF/mask raw mismatch')
    changed=[p for p,e in before.items() if stat(p)!=e];need(not changed,'Consumed stats changed: '+str(changed))
    save(SNAP,dict(stage=TAG+'.stats',inputs=list(before.values()),consumed_stats_unchanged=True,SHA_scans=0))
    save(CHECK,dict(stage=TAG,passed=True,original_driver_failure=stat(prior_path),original_old_calls=0,new_component_rerun=False,new_calls=prior['calls'],old_calls=calls,old_completion=done,comparisons=comparisons,old_headers_root=str(headers),archived_header_entries=len(members),consumed_stats_unchanged=True,SHA_scans=0,physical_acceptance=False));print(json.dumps(dict(passed=True,old_completion=done,comparisons=comparisons,old_calls=calls,headers=len(members)),ensure_ascii=False),flush=True)
except BaseException as e:
    changed=[p for p,a in before.items() if not Path(p).exists() or stat(p)!=a]
    if not SNAP.exists():save(SNAP,dict(stage=TAG+'.stats',inputs=list(before.values()),changed=changed,consumed_stats_unchanged=not changed,SHA_scans=0))
    if not CHECK.exists():save(CHECK,dict(stage=TAG,passed=False,first_failure=str(e),traceback=traceback.format_exc(),calls=calls,changed=changed,SHA_scans=0,physical_acceptance=False))
    print(traceback.format_exc(),flush=True);raise
