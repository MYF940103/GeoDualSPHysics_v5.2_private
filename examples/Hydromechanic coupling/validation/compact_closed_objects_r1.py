"""Plan or explicitly apply NTFS compression to a fixed list of closed compilation outputs."""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
C02=HERE.parent/'02_TerzaghiConsolidation_q0_PR/tests/logs'
C04=HERE.parent/'04_CryerProblem_PR/tests'
TAG='compact_closed_objects_r1'
TARGETS=HERE/(TAG+'.targets.json')
JOURNAL=HERE/(TAG+'.executed.jsonl')
CONFIGS=('upl_case02_cpu_DebugCPU_r2','upl_case02_cpu_ReleaseCPU_r1',
         'upl_case02_flux_cpu_DebugCPU_r1','upl_case02_flux_cpu_ReleaseCPU_r1',
         'upl_gravity_cpu_DebugCPU_r2','upl_gravity_cpu_ReleaseCPU_r2',
         'upl_gravity_wall_cpu_DebugCPU_r1','upl_gravity_wall_cpu_ReleaseCPU_r1',
         'upl_hg_column_DebugCPU_r1','upl_hg_column_ReleaseCPU_r1','upl_hg_DebugCPU_r1','upl_hg_ReleaseCPU_r1',
         'upl_spr_av_ReleaseCPU_r1','upl_column_public_default_DebugCPU_r1','upl_column_public_ReleaseCPU_r1')
GROUPS={REPO/'src/VS/Intermediate'/n:C02/(n+'.build.json') for n in CONFIGS}
for group in ('cryer_darcy_switch_build_r1/DebugCPU/int','cryer_darcy_switch_build_r1/ReleaseCPU/int',
              'cryer_darcy_switch_build_r1/DebugCPU/out','cryer_darcy_switch_build_r2/Debug/out',
              'cryer_symc_gpu_build_r3/Debug','cryer_symc_gpu_build_r3/Release'):
    GROUPS[C04/'outputs'/group]=C04/'logs/cryer_darcy_switch_native_r1.check.json'


def require(ok,reason):
    if not ok:raise ValueError(reason)


def checked(path):
    require(path.parent in GROUPS and path.suffix.lower() in {'.obj','.ilk'},'Outside exact compiler directories: '+str(path))
    for q in (path,*path.parents):
        st=q.lstat()
        require(not (st.st_file_attributes & 0x400),'Reparse point: '+str(q))
        if q==REPO:break
    require(path.resolve(strict=True).is_relative_to(REPO),'Resolved target outside repository')
    st=path.lstat()
    require(stat.S_ISREG(st.st_mode) and st.st_nlink==1 and not (st.st_file_attributes & (0x4000|0x200)),
            'Unexpected encrypted/sparse file or shared identity: '+str(path))
    return st


def identity(st):
    return [st.st_size,st.st_mtime_ns,st.st_dev,st.st_ino]


class CompressionInfo(ctypes.Structure):
    _fields_=[('compressed_size',ctypes.c_longlong),('compression_format',wintypes.WORD),
              ('unit_shift',ctypes.c_ubyte),('chunk_shift',ctypes.c_ubyte),('cluster_shift',ctypes.c_ubyte),
              ('reserved',ctypes.c_ubyte*3)]


class StandardInfo(ctypes.Structure):
    _fields_=[('allocated',ctypes.c_longlong),('logical',ctypes.c_longlong),('links',wintypes.DWORD),
              ('delete_pending',ctypes.c_ubyte),('directory',ctypes.c_ubyte)]


def file_info(path,info_class,result):
    import msvcrt
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    fn=kernel.GetFileInformationByHandleEx
    fn.argtypes=(wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD)
    fn.restype=wintypes.BOOL
    with path.open('rb') as f:
        if not fn(msvcrt.get_osfhandle(f.fileno()),info_class,ctypes.byref(result),ctypes.sizeof(result)):
            raise ctypes.WinError(ctypes.get_last_error())
    return result


def stored_bytes(path):
    return file_info(path,8,CompressionInfo()).compressed_size


def allocated_bytes(path):
    return file_info(path,1,StandardInfo()).allocated


def plan():
    grouped=[]
    for folder,receipt in GROUPS.items():
        require(json.loads(receipt.read_text(encoding='utf-8-sig')).get('passed') is True,'Missing build/native evidence '+str(receipt))
        entries=[]
        for p in sorted(folder.iterdir()):
            if p.suffix.lower() not in ('.obj','.ilk'):continue
            st=checked(p)
            if st.st_size<1024*1024 or st.st_file_attributes&0x800:continue
            entries.append([p.name,*identity(st),stored_bytes(p)])
        require(entries,'Empty reviewed group '+str(folder))
        grouped.append(dict(folder=folder.relative_to(REPO).as_posix(),evidence=receipt.relative_to(REPO).as_posix(),files=entries))
    return dict(label=TAG,inventory_only=True,columns=['file','logical_bytes','mtime_ns','volume_id','file_id','storage_bytes'],
                groups=grouped,files=sum(len(g['files']) for g in grouped),
                logical_bytes=sum(row[1] for g in grouped for row in g['files']),
                storage_bytes_before=sum(row[-1] for g in grouped for row in g['files']))


def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def check_idle():
    cmd="Get-CimInstance Win32_Process | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    raw=subprocess.check_output(['powershell','-NoProfile','-Command',cmd],encoding='utf8',errors='replace')
    for proc in json.loads(raw):
        line=(proc.get('CommandLine') or '').lower()
        name=proc['Name'].lower()
        relevant=name.startswith(('dualsphysics','c08collapse','msbuild','link','cl.exe','nvcc','python'))
        busy=any(s.lower() in line for s in CONFIGS) or any(s in line for s in ('c08_m0_coupled_baseline_gpu',
             'c02_tpi_cost_r1.py run','geodualsphysics_tpir_review','cryer_darcy_switch_build_','cryer_symc_gpu_build_r3'))
        require(not (name.startswith('c08collapse') or (relevant and busy)),'Active dependency PID '+str(proc['ProcessId'])+' '+proc['Name'])


def execute():
    manifest=json.loads(TARGETS.read_text(encoding='utf8'))
    require(not JOURNAL.exists(),'Existing execution journal; inspect preserved results')
    current=plan()
    require(current==manifest,'Candidate file identities or allocation changed since planning')
    check_idle()
    compact=Path(os.environ['SystemRoot'])/'System32/compact.exe'
    total=0
    with JOURNAL.open('x',encoding='utf8',buffering=1) as out:
        for group in manifest['groups']:
            check_idle()
            for filename,*original,before_size in group['files']:
                path=REPO/group['folder']/filename
                require(identity(checked(path))==original,'Changed target '+str(path))
                before=digest(path)
                allocated_before=allocated_bytes(path)
                out.write(json.dumps(dict(before=str(path),sha256=before,stored=before_size,allocated=allocated_before))+'\n')
                result=subprocess.run([str(compact),'/C','/Q',str(path)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
                after=digest(path);st=checked(path);stored=stored_bytes(path)
                allocated=allocated_bytes(path)
                ok=result.returncode==0 and identity(st)==original and after==before and bool(st.st_file_attributes&0x800) and allocated<=allocated_before
                out.write(json.dumps(dict(after=str(path),sha256=after,stored=stored,allocated=allocated,compressed=bool(st.st_file_attributes&0x800),
                                          win32_exit=result.returncode,passed=ok))+'\n')
                require(ok,'Compression/content/identity check failed; retained evidence for '+str(path))
                total+=allocated_before-allocated
        out.write(json.dumps(dict(completed=True,files=manifest['files'],verified_storage_saving_bytes=total))+'\n')
    print('Verified NTFS storage savings (bytes):',total)


if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument('action',choices=['plan','verify-plan','execute'])
    task=cli.parse_args().action
    if task=='execute':execute()
    else:
        obj=plan()
        if task=='plan':
            with TARGETS.open('x',encoding='utf8') as f:json.dump(obj,f,ensure_ascii=False,separators=(',',':'))
        else:require(json.loads(TARGETS.read_text(encoding='utf8'))==obj,'Inventory changed')
        print(obj['files'],obj['logical_bytes'],obj['storage_bytes_before'])
