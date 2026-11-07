"""Build authoritative VS solutions in isolated outputs; capture source once, no execution."""
import ctypes,datetime,json,os,re,subprocess,sys,time,zipfile
from ctypes import wintypes as w
from pathlib import Path
import psutil
T=Path(__file__).resolve().parents[1];R=T.parents[3];S=R/'src';L=T/'logs'
conf=sys.argv[1];assert len(sys.argv)==2 and conf in ('DebugCPU','ReleaseCPU','Debug','Release')
gpu=not conf.endswith('CPU');tag='mdbc_partition_'+conf+'_r1';out=T/'outputs'/tag
inter=Path(os.environ['LOCALAPPDATA'])/'Temp/mdbc_partition_r1'/conf/'int'
capture=T/'outputs/mdbc_partition_source_r1'

def stat(p):
    p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,d):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(d,f,indent=2);f.write('\n')
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
for p in (out,inter.parent,L/(tag+'.call.json'),L/(tag+'.build.json')):assert not p.exists(),p
if not capture.exists():
    baseline=read(L/'upl_config_cleanup_DebugCPU_r1.source.json')
    tracked=subprocess.check_output(['rg','--files','source','-g','*.h','-g','*.hpp','-g','*.cpp','-g','*.cu','-g','*.cuh','-g','*.inl','-g','*.c','-g','*.tpp'],cwd=S,text=True).splitlines()
    files=sorted({Path(e['path']) for e in baseline['files'] if Path(e['path']).is_relative_to(S)}|{S/p for p in tracked}|{S/'VS'/p for p in ('DualSPHysics5Re.sln','DualSPHysics5Re.vcxproj','DualSPHysics5ReCpu_vs2022.sln','DualSPHysics5ReCpu.vcxproj')}|{Path(__file__).resolve(),R/'doc/xml_format/_FmtXML_ElastoplasticSoil.xml'})
    before=[stat(p) for p in files];capture.mkdir()
    with zipfile.ZipFile(capture/'source.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in files:z.write(p,p.relative_to(R).as_posix())
    save(capture/'source.json',dict(files=before,archive=stat(capture/'source.zip'),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=S,text=True).strip(),SHA_scans=0))
snapshot=read(capture/'source.json');before=snapshot['files'];assert all(stat(e['path'])==e for e in before),'Source changed after common build snapshot'
canonical=[stat(p) for p in (R/'bin/windows').iterdir() if p.is_file() and p.suffix.lower() in ('.exe','.pdb','.dll','.xml')]
package=stat(T.parent/'support/LianCollapse_upl_win64_r2.zip')
call0=read(L/'upl_config_cleanup_DebugCPU_r1.call.json');args=call0['arguments'].copy()
args[0]=str(S/'VS'/('DualSPHysics5Re.sln' if gpu else 'DualSPHysics5ReCpu_vs2022.sln'))
args=[('/p:Configuration='+conf if a.startswith('/p:Configuration=') else '/p:OutDir='+out.as_posix()+'/' if a.startswith('/p:OutDir=') else '/p:IntDir='+inter.as_posix()+'/' if a.startswith('/p:IntDir=') else '/bl:'+str(L/(tag+'.binlog')) if a.startswith('/bl:') else a) for a in args]
setup=subprocess.run('cmd.exe /d /s /c "call "D:/Program Files/VS2022/VC/Auxiliary/Build/vcvarsall.bat" x64 -vcvars_ver=14.36 >nul && set"',stdout=subprocess.PIPE,stderr=subprocess.PIPE)
assert setup.returncode==0;env=dict(os.environ);env.update(x.split('=',1) for x in setup.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='));assert env['VCTOOLSVERSION']=='14.36.32532'
out.mkdir();inter.mkdir(parents=True);owner=psutil.Process();started=utc();wall=time.monotonic();log=L/(tag+'.log');rc=None;failure=None;child=None;winexit=None
try:
    with log.open('xb') as f:
        p=subprocess.Popen([call0['program'],*args],cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
        q=psutil.Process(p.pid);child=dict(pid=p.pid,created_epoch=q.create_time(),exe=q.exe(),argv=q.cmdline())
        save(L/(tag+'.start.json'),dict(stage=tag,owner=dict(pid=owner.pid,created_epoch=owner.create_time()),child=child,source_capture=stat(capture/'source.json')))
        print('MSBUILD',conf,p.pid,'owner',owner.pid,flush=True);rc=p.wait()
        K=ctypes.WinDLL('kernel32',use_last_error=True);K.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)]
        code=w.DWORD();assert K.GetExitCodeProcess(int(p._handle),ctypes.byref(code));winexit=code.value
except BaseException as e:failure=repr(e)
save(L/(tag+'.call.json'),dict(stage=tag,program=call0['program'],arguments=args,child=child,actual_Popen_wait_exit=rc,actual_Win32_exit=winexit,started_utc=started,ended_utc=utc(),elapsed_s=time.monotonic()-wall,invocation_failure=failure,log=str(log)))
exe=out/('DualSPHysics5.2CPU_win64_debug.exe' if conf=='DebugCPU' else 'DualSPHysics5.2CPU_win64.exe' if conf=='ReleaseCPU' else 'DualSPHysics5.2_win64_debug.exe' if conf=='Debug' else 'DualSPHysics5.2_GEO_win64.exe')
objects=[stat(p) for p in sorted(inter.glob('*.obj'))];expected=113 if gpu else 87
text=log.read_bytes().decode('mbcs',errors='replace');errors=[x for x in text.splitlines() if re.search(r'\b(?:fatal )?error [A-Z]+\d+|nvcc fatal',x,re.I)];warnings=[x for x in text.splitlines() if re.search(r'\bwarning [A-Z]+\d+',x,re.I)]
unchanged=all(stat(e['path'])==e for e in before);protected=all(stat(e['path'])==e for e in canonical) and stat(package['path'])==package
passed=rc==winexit==0 and failure is None and exe.is_file() and len(objects)==expected and unchanged and protected and not errors
save(L/(tag+'.build.json'),dict(stage=tag,passed=passed,actual_typed_exit_code=rc,actual_Win32_exit=winexit,source_capture=stat(capture/'source.json'),program=stat(exe) if exe.is_file() else None,project_objects=objects,non_main_objects=sum(Path(e['path']).name.lower()!='main.obj' for e in objects),source_stats_unchanged=unchanged,canonical_and_package_stats_unchanged=protected,error_lines=errors,warning_lines=warnings,compiler='MSVC14.36.32532',cuda='11.7 sm86 fresh CUDA objects' if gpu else None,program_or_component_started=False,SHA_scans=0,physical_acceptance=False))
print(json.dumps(dict(stage=tag,passed=passed,actual_exit=rc,objects=len(objects),warnings=len(warnings),errors=errors)),flush=True)
raise SystemExit(0 if passed else 1)
