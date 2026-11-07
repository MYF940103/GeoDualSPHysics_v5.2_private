"""Explicit tiny generic reader build: six frozen BI4 utility objects only, no JSph object or solver."""
import os,subprocess,sys,shutil
from pathlib import Path
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).parent))
from upl_material_release_native_r2_run import T,L,need,read,stat,save,exitcode
TAG='mdbc_admission_native_r2';out=T/'outputs'/(TAG+'_build');bp=L/'upl_material_release_DebugCPU_r3.build.json'
need(sys.argv[1:]==['--execution-authorized'],'Use --execution-authorized; no automatic build')
need(not out.exists() and not (L/(TAG+'.build.json')).exists(),'Existing build protected')
b=read(bp);need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0,'Frozen r3 CPU build required')
objects=[e for e in b['project_objects'] if Path(e['path']).stem in ('JPartDataBi4','JPartDataHead','JBinaryData','JObject','JException','Functions')];need(len(objects)==6,'Exactly six standalone BI4 utility objects required')
archive=T/'outputs/upl_material_release_source_r3/source.zip';source=T/'support'/(TAG+'.cpp');consumed=[stat(__file__),stat(source),stat(bp),stat(archive)]+objects
need(all(stat(e['path'])==e for e in objects),'Frozen object stat changed');out.mkdir();headers=out/'headers';headers.mkdir()
with ZipFile(archive) as z:
    for item in z.infolist():
        if item.filename.startswith('src/source/') and Path(item.filename).suffix.lower() in ('.h','.hpp','.inl','.cuh'):
            target=headers/Path(item.filename).name;need(not target.exists(),'Duplicate archived header name');target.write_bytes(z.read(item))
cmd=Path(os.environ['SystemRoot'])/'System32/cmd.exe';dev=Path('D:/Program Files/VS2022/Common7/Tools/VsDevCmd.bat')
r=subprocess.run('"'+str(cmd)+'" /d /c call "'+str(dev)+'" -arch=x64 -host_arch=x64 >nul && set',capture_output=True);need(r.returncode==0,'Known MSVC environment failed')
env=dict(os.environ);env.update(x.split('=',1)for x in r.stdout.decode('mbcs').splitlines()if '=' in x and not x.startswith('='));cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe';obj=out/'reader.obj';exe=out/'reader.exe'
def invoke(name,argv):
    log=out/(name+'.log')
    with log.open('xb')as f:p=subprocess.Popen(argv,env=env,cwd=out,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);rc=p.wait();actual=exitcode(int(p._handle))
    save(out/(name+'.call.json'),dict(argv=argv,actual_Popen_wait_exit=rc,actual_Win32_exit=actual,log=stat(log),typed_exit_captured_first=type(rc)is int));need(rc==actual==0,'Compiler/linker failed; preserve original evidence')
invoke('compile',[str(cl),'/nologo','/c','/std:c++17','/D_HAS_STD_BYTE=0','/EHsc','/W3','/fp:precise','/Od','/MTd','/Zi','/RTC1','/DWIN32','/D_CONSOLE','/D_MBCS','/I'+str(headers),'/Fo'+str(obj),'/Fd'+str(out/'reader_compile.pdb'),str(source)])
invoke('link',[str(cl.with_name('link.exe')),'/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE','/ENTRY:wmainCRTStartup','/OUT:'+str(exe),'/DEBUG','/PDB:'+str(out/'reader.pdb'),str(obj),*[e['path']for e in objects]])
need(all(stat(e['path'])==e for e in consumed),'Consumed inputs changed during helper build')
save(L/(TAG+'.build.json'),dict(stage=TAG,passed=True,program=stat(exe),source=stat(source),source_build=stat(bp),source_archive=stat(archive),objects=objects,JSph_objects_linked=False,consumed=consumed,consumed_stats_unchanged=True,solver_launched=False,SHA_scans=0))
print('NATIVE_BUILD_PASSED',exe,flush=True)
