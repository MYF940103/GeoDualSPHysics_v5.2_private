import csv, ctypes, datetime, json, os, shutil, subprocess, traceback, zipfile
from ctypes import wintypes as w
from pathlib import Path
import psutil

R=Path(__file__).resolve().parents[5]; T=Path(__file__).resolve().parents[1]; S=R/'src'; L=T/'logs'; O=T/'outputs'
TAG='upl_free_seepage_CPU_r1'; SOURCE=T/'support/upl_free_seepage_cpu_r1.cpp'; NOTE=T/'notes/upl_free_seepage_cpu_r1.json'
CHECK=L/(TAG+'.check.json'); SNAP=L/(TAG+'.stats.json'); before={}; calls=[]; results={}
def need(ok,text):
    if not ok: raise RuntimeError(text)
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f: json.dump(d,f,ensure_ascii=False,indent=2)
def stat(p):
    p=Path(p).resolve(); a=p.stat(); return dict(path=str(p),bytes=a.st_size,mtime_ns=a.st_mtime_ns)
def bind(p,expected=None):
    e=stat(p); before.setdefault(e['path'],e)
    if expected: need(e['bytes']==expected['bytes'] and e['mtime_ns']==expected['mtime_ns'],'Consumed stat mismatch: '+e['path'])
    return e
def utc(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.GetProcessTimes.argtypes=[w.HANDLE,ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME)]
k.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)]
def invoke(label,argv,env):
    log=L/(TAG+'.'+label+'.log'); cp=L/(TAG+'.'+label+'.call.json'); need(not log.exists() and not cp.exists(),'Call collision')
    rec=dict(stage=TAG+'.'+label,program=argv[0],arguments=argv[1:],working_directory=str(S),started_utc=utc(),physical_acceptance=False)
    with log.open('xb') as f:
        p=subprocess.Popen(argv,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT)
        ft=[w.FILETIME() for _ in range(4)]; need(k.GetProcessTimes(int(p._handle),*[ctypes.byref(a) for a in ft]),'GetProcessTimes failed')
        created=((ft[0].dwHighDateTime<<32)|ft[0].dwLowDateTime)/1e7-11644473600
        size=w.DWORD(32768); image=ctypes.create_unicode_buffer(size.value); need(k.QueryFullProcessImageNameW(int(p._handle),0,image,ctypes.byref(size)),'QueryFullProcessImageNameW failed')
        try: actual_argv=psutil.Process(p.pid).cmdline()
        except psutil.NoSuchProcess: actual_argv=None
        rec['child']=dict(pid=p.pid,created_epoch=created,exe=image.value,command=actual_argv,parent_pid=os.getpid())
        rc=p.wait(); win=w.DWORD(); need(k.GetExitCodeProcess(int(p._handle),ctypes.byref(win)),'Win32 exit query failed')
        rec.update(exit_code=rc,actual_win32_exit_code=win.value,owned_call_exited=True,typed_returncode_captured_from_Popen_wait=True,ended_utc=utc(),log=str(log))
        save(cp,rec); calls.append(str(cp))
    need(Path(image.value).samefile(argv[0]),'Owned image mismatch'); need(rc==0 and win.value==0,'Actual call failed: '+label+'; see '+str(log))
    return rec
def stage(which,buildname,env,legacy):
    bp=L/(buildname+'.build.json'); b=read(bp); bind(bp); need(b['passed'] and b['actual_typed_exit_code']==0 and b['source_stats_unchanged'],'Unsealed source build')
    objects=[e for e in b['project_objects'] if Path(e['path']).name.lower()!='main.obj']; need(len(objects)==85 and b['non_main_objects']==85,'Wrong non-main closure')
    for e in objects: bind(e['path'],e)
    helper=O/('upl_free_seepage_CPU_'+which+'_helper_r1'); result=O/('upl_free_seepage_CPU_'+which+'_r1')
    need(not helper.exists() and not result.exists(),'Fresh helper/result collision'); helper.mkdir()
    source=read(b['source']);bind(b['source']); expected_source={str(Path(e['path']).resolve()):e for e in source['files']}
    include=S/'source'; archive_record=None
    if legacy:
        archive_record=bind(source['archive']['path'],source['archive']); dest=helper/'source_snapshot'
        with zipfile.ZipFile(archive_record['path']) as z:
            members=z.infolist(); need(all((dest/m.filename).resolve().is_relative_to(dest.resolve()) for m in members),'Archive path escapes destination')
            z.extractall(dest)
            save(helper/'archive_members.json',dict(source_archive=archive_record,CRC_checked_by_extraction=True,members=[dict(path=m.filename,bytes=m.file_size,crc32=m.CRC) for m in members]))
        include=dest/'src/source'; need((include/'JSph.h').is_file(),'Missing archived old header root')
    obj=helper/'helper.obj'; exe=helper/'upl_free_seepage_cpu_r1.exe'; deps=helper/'compile.dependencies.json'
    argv=[str(CL),'/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS','/I'+str(include),'/Fo'+str(obj),'/Fd'+str(helper/'compile.pdb'),'/sourceDependencies',str(deps),'/Od','/MTd','/Zi','/RTC1']
    if legacy: argv.append('/DUPL_FREE_SEEPAGE_LEGACY_ONLY')
    argv.append(str(SOURCE)); invoke(which+'.compile',argv,env)
    dependencies=read(deps)['Data']['Includes']; header_rows=[]
    for p in dependencies:
        p=Path(p).resolve(); e=bind(p,expected_source.get(str(p))); header_rows.append(e)
        if legacy and p.name.lower().startswith(('jsph','jarrays','typesdef','dualsphdef')): need(p.is_relative_to(include.resolve()),'Legacy project header escaped archive: '+str(p))
    need(not legacy or all(not Path(p).resolve().is_relative_to((S/'source').resolve()) for p in dependencies),'Old compile consumed a current source header')
    linkargs=[a for a in RECIPE['arguments'] if not a.lower().endswith('.obj') and not a.upper().startswith(('/OUT:','/PDB:'))]
    invoke(which+'.link',[str(LINK),*linkargs,'/OUT:'+str(exe),str(obj),*[e['path'] for e in objects],'/PDB:'+str(helper/'link.pdb')],env)
    runtime=[]
    for name in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):
        source=R/'bin/windows'/name; e=bind(source); shutil.copy2(source,helper/name); copy=stat(helper/name); need((e['bytes'],e['mtime_ns'])==(copy['bytes'],copy['mtime_ns']),'Runtime copy mismatch'); runtime.append(copy)
    save(L/(TAG+'.'+which+'.build.json'),dict(stage=TAG+'.'+which+'.build',passed=True,source_build=stat(bp),program=stat(exe),project_objects=objects,headers=header_rows,archive=archive_record,runtime=runtime,physical_acceptance=False,SHA_scans=0))
    invoke(which+'.run',[str(exe),'--out',str(result)],env)
    done=read(result/'completion.json'); need(done['passed'] and done['rate_rows']==243 and done['completed_physical_steps']==0 and done['legacy_only']==legacy,'Unexpected component completion')
    masks=list(csv.DictReader((result/'mask.csv').open(encoding='utf-8',newline=''))); need(len(masks)==243 and all(n>0 for n in done['inner_counts']) and all(n>0 for n in done['surface_counts']),'Empty actual mask coverage')
    for field in range(3): need(len({int(a['native_id']) for a in masks if int(a['field'])==field})==81,'Native ID coverage mismatch')
    need((result/'free_off_rates.bin').stat().st_size==972,'OFF payload size mismatch')
    if not legacy: need(done['projection_rows']==324 and done['nonfinite_input_bits_preserved']==2 and done['inner_bit_checks']>0 and done['hydrostatic_naive_negative_witnesses']>0,'Incomplete candidate checks')
    results[which]=dict(directory=str(result),completion=done,program=stat(exe)); print(which,done,flush=True); return result

try:
    need(not CHECK.exists() and not SNAP.exists(),'Final receipt collision')
    bind(SOURCE);bind(NOTE);bind(T.parent.parent/'02_TerzaghiConsolidation_q0_PR/tests/support/upl_p2_feedback_harness_r1.cpp')
    need(not any((p.info['name'] or '').lower()=='upl_free_seepage_cpu_r1.exe' for p in psutil.process_iter(['name'])),'Duplicate component active')
    CL=Path('D:/Program Files/VS2022/VC/Tools/MSVC/14.36.32532/bin/Hostx64/x64/cl.exe');LINK=CL.with_name('link.exe');bind(CL);bind(LINK)
    RECIPE=read(L/'upl_gravity_wall_cpu_r2_link.call.json')
    for a in RECIPE['arguments']:
        if a.endswith('.lib') and (S/'lib/vs2022'/a).is_file(): bind(S/'lib/vs2022'/a)
    cmd=Path(os.environ['SystemRoot'])/'System32/cmd.exe'; dev=Path('D:/Program Files/VS2022/Common7/Tools/VsDevCmd.bat')
    setup=subprocess.run('"'+str(cmd)+'" /d /c call "'+str(dev)+'" -arch=x64 -host_arch=x64 >nul && set',capture_output=True)
    need(setup.returncode==0,'VS setup failed: '+setup.stderr.decode('mbcs',errors='replace'))
    env=dict(os.environ);env.update(a.split('=',1) for a in setup.stdout.decode('mbcs').splitlines() if '=' in a and not a.startswith('='));env['OMP_NUM_THREADS']='1'
    new=stage('new','upl_free_seepage_DebugCPU_r1',env,False)
    old=stage('old','upl_container_DebugCPU_r1',env,True)
    comparisons={name:(new/name).read_bytes()==(old/name).read_bytes() for name in ('free_off_rates.bin','mask.csv')}
    need(all(comparisons.values()),'Old/new raw OFF or mask mismatch')
    changed=[p for p,e in before.items() if stat(p)!=e]; need(not changed,'Consumed stats changed: '+str(changed))
    save(SNAP,dict(stage=TAG+'.stats',inputs=list(before.values()),consumed_stats_unchanged=True,SHA_scans=0))
    save(CHECK,dict(stage=TAG,passed=True,results=results,comparisons=comparisons,calls=calls,consumed_stats_unchanged=True,SHA_scans=0,physical_acceptance=False));print('ALL PASSED',flush=True)
except BaseException as e:
    changed=[p for p,a in before.items() if not Path(p).exists() or stat(p)!=a]
    if not SNAP.exists(): save(SNAP,dict(stage=TAG+'.stats',inputs=list(before.values()),changed=changed,consumed_stats_unchanged=not changed,SHA_scans=0))
    if not CHECK.exists(): save(CHECK,dict(stage=TAG,passed=False,first_failure=str(e),traceback=traceback.format_exc(),calls=calls,results=results,changed=changed,SHA_scans=0,physical_acceptance=False))
    print(traceback.format_exc(),flush=True);raise
