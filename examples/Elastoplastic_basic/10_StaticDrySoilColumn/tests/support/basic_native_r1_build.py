"""One helper build, frozen r3 headers/85 CPU objects. No production compilation."""
import json,os,subprocess,sys,zlib
from pathlib import Path
from zipfile import ZipFile
sys.path.insert(0,str(Path(__file__).parent));from basic_material_r1 import R,H,context,need,read,stat,save,invoke
c,t,*_=context('column');out=t/'outputs/basic_native_r1_build';need(not out.exists(),'Fresh helper required');out.mkdir()
bp=H/'logs/upl_material_release_DebugCPU_r3.build.json';b=read(bp);need(b['passed'] and b['actual_typed_exit_code']==b['actual_Win32_exit']==0,'Frozen r3 DebugCPU build required')
archive=H/'outputs/upl_material_release_source_r3/source.zip';headers=Path(os.environ['LOCALAPPDATA'])/'Temp/basic_native_r1_headers';need(not headers.exists(),'Fresh archived header extraction required');headers.mkdir()
with ZipFile(archive) as z:
    for e in z.infolist():
        if e.filename.startswith('src/') and Path(e.filename).suffix.lower() in ('.h','.hpp','.inl','.cuh'):
            data=z.read(e);need(len(data)==e.file_size and zlib.crc32(data)==e.CRC,'Archived header CRC mismatch');p=headers/e.filename;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
cmd=Path(os.environ['SystemRoot'])/'System32/cmd.exe';dev=Path('D:/Program Files/VS2022/Common7/Tools/VsDevCmd.bat');s=subprocess.run('"'+str(cmd)+'" /d /c call "'+str(dev)+'" -arch=x64 -host_arch=x64 >nul && set',capture_output=True);need(s.returncode==0,'Known VS setup failed');env=dict(os.environ);env.update(x.split('=',1) for x in s.stdout.decode('mbcs').splitlines() if '=' in x and not x.startswith('='))
old=read(H/'logs/upl_material_stage_cpu_r1.compile.call.json')['argv'];source=t/'support/basic_native_r1.cpp';obj=out/'helper.obj';cl=Path(env['VCToolsInstallDir'])/'bin/Hostx64/x64/cl.exe'
compile=[str(cl),'/nologo','/c','/std:c++17','/EHsc','/W3','/openmp','/fp:precise','/DWIN32','/D_CONSOLE','/D_MBCS','/I'+str(headers/'src/source'),'/Fo'+str(obj),'/Fd'+str(out/'compile.pdb'),'/Od','/MTd','/Zi','/RTC1',str(source)]
consumed=[stat(source),stat(archive),stat(bp)]+b['project_objects'];need(all(stat(x['path'])==x for x in b['project_objects']),'Frozen object stat differs')
# invoke uses explicit env only for this compiler/link subprocess via inherited environment.
os.environ.update(env);invoke(t,'basic_native_r1.compile',compile,R/'src')
oldlink=read(H/'logs/upl_material_stage_cpu_r1.link.call.json')['argv'];libs=[x for x in oldlink if x.lower().endswith('.lib')];exe=out/'basic_native_r1.exe';objects=[x['path'] for x in b['project_objects'] if Path(x['path']).name.lower()!='main.obj']
link=[str(cl.with_name('link.exe')),'/NOLOGO','/MACHINE:X64','/SUBSYSTEM:CONSOLE','/OUT:'+str(exe),'/LIBPATH:'+str(R/'src/lib/vs2022'),str(obj),*objects,*libs,'/DEBUG','/PDB:'+str(out/'link.pdb')];invoke(t,'basic_native_r1.link',link,R/'src')
runtime_source=H/'outputs/upl_preload_handoff_ReleaseCPU_r2'
import shutil
for n in ('DsphConfig.xml','ChronoEngine.dll','dsphchrono.dll','vcomp140.dll'):shutil.copy2(runtime_source/n,out/n)
need(all(stat(x['path'])==x for x in consumed),'Consumed source/archive/object stat changed');save(t/'logs/basic_native_r1.build.json',dict(passed=True,program=stat(exe),source=stat(source),source_archive=stat(archive),source_build=stat(bp),frozen_objects_unchanged=True,SHA_scans=0))
print('READER_BUILD_PASSED',exe,flush=True)
