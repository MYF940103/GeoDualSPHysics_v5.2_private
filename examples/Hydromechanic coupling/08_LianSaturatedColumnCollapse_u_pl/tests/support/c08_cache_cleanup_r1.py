"""Explicit, recoverable cleanup of closed ILK caches only; author does not execute."""
import argparse
import binascii
import ctypes
from ctypes import wintypes as w
import datetime
import json
import msvcrt
import os
from pathlib import Path
import psutil
import zipfile

T=Path(__file__).resolve().parents[1];ROOT=T/'outputs';TAG='c08_cache_cleanup_r1'
INVENTORY=T/'logs'/(TAG+'.inventory.json');NOTE=T/'notes'/(TAG+'.md');OUT=ROOT/TAG
ARCHIVE=OUT/'cache.zip';VERIFIED=OUT/'archive_verified.json';CHECK=OUT/'check.json'
CHUNK=1024*1024;REPARSE=0x400;COMPRESSED=0x800;SPARSE=0x200
BUILD_NAMES={'cl.exe','link.exe','nvcc.exe','msbuild.exe','ptxas.exe','cicc.exe','ninja.exe','cmake.exe'}
K=ctypes.WinDLL('kernel32',use_last_error=True)


class Standard(ctypes.Structure):
    _fields_=[('AllocationSize',ctypes.c_longlong),('EndOfFile',ctypes.c_longlong),('NumberOfLinks',w.DWORD),('DeletePending',w.BOOLEAN),('Directory',w.BOOLEAN)]


class Identity(ctypes.Structure):
    _fields_=[('attributes',w.DWORD),('creation',w.FILETIME),('access',w.FILETIME),('write',w.FILETIME),('volume',w.DWORD),('size_high',w.DWORD),('size_low',w.DWORD),('links',w.DWORD),('id_high',w.DWORD),('id_low',w.DWORD)]


K.CreateFileW.argtypes=[w.LPCWSTR,w.DWORD,w.DWORD,ctypes.c_void_p,w.DWORD,w.DWORD,w.HANDLE];K.CreateFileW.restype=w.HANDLE
K.GetFileInformationByHandleEx.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD];K.GetFileInformationByHandleEx.restype=w.BOOL
K.GetFileInformationByHandle.argtypes=[w.HANDLE,ctypes.POINTER(Identity)];K.GetFileInformationByHandle.restype=w.BOOL
K.CloseHandle.argtypes=[w.HANDLE];K.CloseHandle.restype=w.BOOL
K.GetCurrentProcess.restype=w.HANDLE
K.SetPriorityClass.argtypes=[w.HANDLE,w.DWORD];K.SetPriorityClass.restype=w.BOOL
K.GetPriorityClass.argtypes=[w.HANDLE];K.GetPriorityClass.restype=w.DWORD
K.GetDiskFreeSpaceExW.argtypes=[w.LPCWSTR,ctypes.POINTER(ctypes.c_ulonglong),ctypes.POINTER(ctypes.c_ulonglong),ctypes.POINTER(ctypes.c_ulonglong)];K.GetDiskFreeSpaceExW.restype=w.BOOL


def need(ok,text):
    if not ok:raise RuntimeError(text)


def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def absolute(value):return Path(os.path.abspath(str(value)))
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def stat(path):
    path=absolute(path);s=path.stat();return dict(path=str(path),bytes=s.st_size,mtime_ns=s.st_mtime_ns)


def bind(ref):
    actual=stat(ref['path']);need(all(actual[k]==ref[k] for k in ('path','bytes','mtime_ns')),'Bound file changed: '+ref['path']);return actual


def save(path,data):
    with Path(path).open('x',encoding='utf8') as f:json.dump(data,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())


def parents_safe(path):
    for parent in (path.parent,*path.parent.parents):
        s=parent.lstat();need(parent.is_dir() and not (s.st_file_attributes&REPARSE),'Parent is not a plain directory: '+str(parent))


def cache_path(value):
    path=absolute(value);root=absolute(ROOT)
    need(path.is_relative_to(root) and path!=root and path.suffix.lower()=='.ilk','Only literal ILK files below C08 tests/outputs are allowed')
    for component in path.relative_to(root).parts[:-1]:
        name=component.lower()
        need(name not in {'source','src','frozen','data','particles','figures','configs','logs'} and not name.startswith('native')
             and not name.startswith('runtime') and not name.endswith(('_runtime','_source','_source_capture','_source_archive')),
             'Protected source/runtime/native/PRE/data subtree: '+str(path))
    parents_safe(path);return path


def info(handle):
    a,b=Standard(),Identity()
    need(K.GetFileInformationByHandleEx(handle,1,ctypes.byref(a),ctypes.sizeof(a)) and K.GetFileInformationByHandle(handle,ctypes.byref(b)),
         'Actual Win32 allocation/identity query failed: '+str(ctypes.get_last_error()))
    need(not a.Directory and not (b.attributes&REPARSE) and a.AllocationSize>=0 and a.EndOfFile>=0,'Not a plain file stream')
    return dict(allocation_bytes=int(a.AllocationSize),bytes=int(a.EndOfFile),nlinks=int(a.NumberOfLinks),identity_nlinks=int(b.links),
                volume_serial=int(b.volume),file_id=(int(b.id_high)<<32)|int(b.id_low),attributes=int(b.attributes),delete_pending=bool(a.DeletePending))


def handle_info(path):
    h=K.CreateFileW(str(path),0x80,7,None,3,0x00200000,None)
    need(h not in (None,ctypes.c_void_p(-1).value),'Cannot inspect literal file identity: '+str(path))
    try:return info(h)
    finally:K.CloseHandle(h)


def hold(path,expected):
    # Deny writers for the whole archive/delete transaction; allow our later literal unlink.
    h=K.CreateFileW(str(path),0x80010000,5,None,3,0x08200000,None)
    need(h not in (None,ctypes.c_void_p(-1).value),'Cannot acquire read/delete handle without write sharing: '+str(path))
    try:fd=msvcrt.open_osfhandle(int(h),os.O_RDONLY|os.O_BINARY)
    except Exception:K.CloseHandle(h);raise
    stream=os.fdopen(fd,'rb')
    try:
        actual=info(msvcrt.get_osfhandle(stream.fileno()));s=os.fstat(stream.fileno())
        need(actual['nlinks']==actual['identity_nlinks']==1 and not actual['delete_pending']
             and not (actual['attributes']&(COMPRESSED|SPARSE)),'Require one-link uncompressed/nonsparse ILK stream: '+str(path))
        need(s.st_size==actual['bytes']==expected['bytes'] and s.st_mtime_ns==expected['mtime_ns'],'Actual held ILK stat differs: '+str(path))
        return stream,dict(**actual,mtime_ns=s.st_mtime_ns,atime_ns=s.st_atime_ns)
    except Exception:stream.close();raise


def live_exclusions():
    parents=[];builds=[]
    for p in psutil.process_iter(['pid','name','exe','create_time']):
        q=p.info;name=(q.get('name') or '').lower()
        if name in BUILD_NAMES:builds.append(q)
        if q.get('exe'):parents.append(str(absolute(q['exe']).parent))
    need(not builds,'An active compiler/linker/build process exists; no cleanup or restore is admitted')
    return sorted(set(parents))


def excluded(path,roots):
    need(not any(path.is_relative_to(absolute(q)) for q in roots),'Active or declared protected dependency contains candidate: '+str(path))


def lower_self_priority():
    own=K.GetCurrentProcess();need(K.SetPriorityClass(own,0x4000) and K.GetPriorityClass(own)==0x4000,'Cannot lower cleanup helper priority')
    return dict(pid=os.getpid(),priority='BELOW_NORMAL_PRIORITY_CLASS',priority_class=int(K.GetPriorityClass(own)),only_current_process_changed=True)


def volume_free():
    available,total,free=ctypes.c_ulonglong(),ctypes.c_ulonglong(),ctypes.c_ulonglong()
    need(K.GetDiskFreeSpaceExW(ROOT.anchor,ctypes.byref(available),ctypes.byref(total),ctypes.byref(free)),'Volume free-space query failed')
    return dict(observed_utc=utc(),available_bytes=available.value,total_free_bytes=free.value,volume_bytes=total.value,descriptive_only=True)


def context():
    inv=read(INVENTORY);need(inv['stage']==TAG+'.inventory' and inv['inventory_only'] and inv['complete'] and inv['cleanup_invocations']==0
        and absolute(inv['outputs_root'])==absolute(ROOT) and not inv['active_build_processes'],'A complete closed inventory with no cleanup/build invocation is required')
    if inv['parse_failures']:
        need(inv['parse_failures_quarantined'] and inv['all_failure_raw_screens_no_ILK_reference'],'Incomplete JSON scans must be explicitly quarantined')
        for q in inv['parse_failures']:need(q['raw_screen']['contains_ilk_token'] is False and not q['raw_screen']['exact_candidate_path_hits'],'A failed JSON screen references an ILK candidate')
    before=[stat(q) for q in (Path(__file__),NOTE,INVENTORY)]
    for q in inv['dependency_documents']:before.append(bind(q))
    roots=[q['path'] for q in inv['protected_roots']]+inv['active_executable_parents']+live_exclusions()
    for q in inv['protected_roots']:
        if q.get('source') is not None:before.append(bind(q['source']))
    candidates=inv['candidates'];need(candidates,'No cache candidates; refuse an empty archive')
    paths=set();closed=[]
    for c in candidates:
        path=cache_path(c['path']);excluded(path,roots);need(str(path).lower() not in paths and not c['binding_matches'],'Duplicate or declared dependency candidate')
        paths.add(str(path).lower());need(str(path.parent)==c['parent'],'Literal candidate parent differs')
        proof=c['closed_build'];receipt=read(proof['receipt']['path']);before.extend((bind(proof['receipt']),bind(proof['program'])))
        need(receipt['passed'] and proof['calls'],'An actual closed passed build is required')
        for call in proof['calls']:
            before.append(bind(call['receipt']));actual=read(call['receipt']['path'])
            need(call['actual_Popen_wait_exit']==call['actual_Win32_exit']==0 and call['ownership_failure'] is None
                 and call['matching_original_child_active'] is False and actual['actual_Popen_wait_exit']==actual['actual_Win32_exit']==0
                 and actual.get('ownership_failure') is None and actual.get('child')==call['child'],'Closed original tool-call evidence differs')
        need(stat(path)['bytes']==c['bytes'] and stat(path)['mtime_ns']==c['mtime_ns'],'Candidate changed since inventory')
        closed.append((path,c))
    return inv,before,roots,closed


def apply():
    need(not OUT.exists(),'Existing complete/partial cleanup evidence is protected; never retry this tag')
    held=[];events=[];before=[];result=dict(stage=TAG,passed=False,deletion_started=False,solver_invocations=0,build_invocations=0,VTK_invocations=0,SHA_scans=0)
    try:
        priority=lower_self_priority();inv,before,roots,candidates=context();ids=set()
        for path,c in candidates:
            stream,details=hold(path,c);held.append((path,stream,details));identity=(details['volume_serial'],details['file_id'])
            need(identity not in ids,'Two candidates resolve to the same physical stream');ids.add(identity)
        need(all(stat(q['path'])==q for q in before),'Inventory/closed/dependency evidence changed before archive')
        free_before=volume_free();OUT.mkdir();save(OUT/'inventory_consumed.json',dict(inventory=stat(INVENTORY),priority=priority,protected_roots=roots,candidates=[dict(path=str(p),**d) for p,_,d in held]))
        entries=[]
        with zipfile.ZipFile(ARCHIVE,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
            for index,(path,stream,details) in enumerate(held):
                arc=path.relative_to(ROOT).as_posix();crc=0;length=0
                with z.open(arc,'w',force_zip64=True) as target:
                    while True:
                        block=stream.read(CHUNK)
                        if not block:break
                        target.write(block);length+=len(block);crc=binascii.crc32(block,crc)
                need(length==details['bytes'],'Original stream length changed')
                entries.append(dict(index=index,path=str(path),archive_entry=arc,bytes=length,crc32=crc&0xffffffff,source=details))
        with ARCHIVE.open('r+b') as f:f.flush();os.fsync(f.fileno())
        with zipfile.ZipFile(ARCHIVE,'r') as z:
            need(len(z.infolist())==len(entries) and len(set(z.namelist()))==len(entries),'Archive entries duplicated or missing')
            for entry,(path,stream,details) in zip(entries,held):
                crc=0;length=0
                with z.open(entry['archive_entry'],'r') as f:
                    while True:
                        block=f.read(CHUNK)
                        if not block:break
                        length+=len(block);crc=binascii.crc32(block,crc)
                zi=z.getinfo(entry['archive_entry']);need(length==zi.file_size==entry['bytes'] and crc&0xffffffff==zi.CRC==entry['crc32'],'ZIP CRC32/length differs from the original stream')
                fresh=info(msvcrt.get_osfhandle(stream.fileno()));need(all(fresh[k]==details[k] for k in ('file_id','volume_serial','bytes','allocation_bytes','nlinks','identity_nlinks','attributes')) and stat(path)['mtime_ns']==details['mtime_ns'],'Held source changed during archive')
            need(z.testzip() is None,'Full ZIP testzip failed')
        zip_info=handle_info(ARCHIVE);need(not zip_info['attributes']&(COMPRESSED|SPARSE),'New ZIP must have ordinary NTFS storage for AllocationSize accounting')
        need(all(stat(q['path'])==q for q in before),'Bound inventory/closed evidence changed before deletion')
        save(VERIFIED,dict(stage=TAG+'.archive_verified',passed=True,archive=stat(ARCHIVE),archive_win32=zip_info,entries=entries,CRC32_is_not_cryptographic=True,
             stream_lengths_and_CRC32_match=True,all_entries_testzip_passed=True,all_source_handles_deny_write=True,inventory=stat(INVENTORY),priority=priority,scientific_data_read=False,SHA_scans=0))
        # Only this sealed, tested archive allows deletion. Every action stays a literal ILK unlink.
        roots+=live_exclusions();journal=OUT/'deletions.jsonl';deleted=0;deleted_allocation=0
        with journal.open('x',encoding='utf8') as log:
            for entry,(path,stream,details) in zip(entries,held):
                event=dict(index=entry['index'],path=str(path),before=details,status='not_attempted')
                try:
                    cache_path(path);excluded(path,roots);now=handle_info(path)
                    need(all(now[k]==details[k] for k in ('file_id','volume_serial','bytes','allocation_bytes','nlinks','identity_nlinks','attributes'))
                         and stat(path)['mtime_ns']==details['mtime_ns'],'Literal ILK identity/stat changed before unlink')
                    log.write(json.dumps(dict(index=entry['index'],path=str(path),action='before_literal_unlink',observed_utc=utc()))+'\n');log.flush();os.fsync(log.fileno())
                    result['deletion_started']=True;path.unlink();stream.close();need(not os.path.lexists(path),'Deleted ILK path still exists')
                    event.update(status='deleted',absent_after=True,observed_utc=utc());deleted+=1;deleted_allocation+=details['allocation_bytes']
                except Exception as error:event.update(status='failed_preserved',error=str(error),absent_after=not os.path.lexists(path))
                events.append(event);log.write(json.dumps(event)+'\n');log.flush();os.fsync(log.fileno())
                if event['status']!='deleted':break
        for _,stream,_ in held:stream.close()
        after_zip=handle_info(ARCHIVE);need(all(after_zip[k]==zip_info[k] for k in ('file_id','volume_serial','bytes','allocation_bytes')),'Verified archive changed during deletion')
        result.update(passed=deleted==len(entries),planned_ILKs=len(entries),deleted_ILKs=deleted,entry_results=events,not_attempted_indices=list(range(len(events),len(entries))),
            archive_verified=stat(VERIFIED),archive=stat(ARCHIVE),archive_win32=after_zip,original_all_candidate_stream_allocation_bytes=sum(d['allocation_bytes'] for _,_,d in held),
            deleted_stream_allocation_bytes=deleted_allocation,ZIP_new_allocation_bytes=after_zip['allocation_bytes'],net_stream_allocation_minus_ZIP_bytes=deleted_allocation-after_zip['allocation_bytes'],
            net_formula_excludes_metadata_files=True,volume_free_before=free_before,volume_free_after=volume_free(),volume_free_delta_is_not_attributed_to_cleanup=True,
            CRC32_is_not_SHA_or_cryptographic=True,only_ILK_primary_streams_archived_and_unlinked=True,no_directory_deleted=True,scientific_data_read=False,
            priority=priority,partial_outputs_preserved=True,automatic_retry=False,automatic_next_job=False,consumed=before)
    except Exception as error:result.update(first_failure=str(error),entry_results=events,partial_outputs_preserved=True,automatic_retry=False)
    finally:
        for _,stream,_ in held:stream.close()
    if OUT.exists():save(CHECK,result)
    else:save(T/'logs'/(TAG+'.preflight_failed.json'),result)
    need(result['passed'],result.get('first_failure','Partial cleanup stopped; preserve archive/journal and never retry this tag'))


def restore(index):
    priority=lower_self_priority();proof=read(VERIFIED);need(proof['passed'] and proof['all_entries_testzip_passed'],'Original verified archive required');bind(proof['archive'])
    entries=proof['entries'];need(0<=index<len(entries),'Select an original archived entry index');entry=entries[index];path=cache_path(entry['path'])
    excluded(path,live_exclusions());need(not os.path.lexists(path),'Restore refuses any existing destination; nothing is overwritten')
    report=OUT/f'restore_{index:04d}.json';need(not report.exists(),'Existing restore attempt protected')
    crc=0;length=0;result=dict(stage=TAG+'.restore',passed=False,index=index,path=str(path),priority=priority,solver_invocations=0,SHA_scans=0)
    try:
        with zipfile.ZipFile(ARCHIVE,'r') as z,z.open(entry['archive_entry'],'r') as source,path.open('xb') as target:
            while True:
                block=source.read(CHUNK)
                if not block:break
                need(target.write(block)==len(block),'Incomplete restored stream write');length+=len(block);crc=binascii.crc32(block,crc)
            target.flush();os.fsync(target.fileno())
        need(length==entry['bytes'] and crc&0xffffffff==entry['crc32'],'Restored archive stream CRC32/length differs');os.utime(path,ns=(entry['source']['atime_ns'],entry['source']['mtime_ns']))
        restored=stat(path);need(restored['bytes']==entry['bytes'] and restored['mtime_ns']==entry['source']['mtime_ns'],'Restored bytes/mtime differ')
        result.update(passed=True,restored=restored,restored_win32=handle_info(path),crc32=crc&0xffffffff,bytes_and_mtime_restored=True,
            original_FileId_or_ACL_restored=False,alternate_streams_or_security_metadata_archived=False,archive_unchanged=bind(proof['archive']))
    except Exception as error:result.update(first_failure=str(error),partial_restore_preserved=True)
    save(report,result);need(result['passed'],result.get('first_failure','Restore failed; partial file is protected, no overwrite retry'))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('phase',choices=('apply','restore'));p.add_argument('--entry',type=int);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args()
    need(a.execution_authorized,'Root full-read and separate execution authorization required; author has not deleted anything')
    if a.phase=='apply':need(a.entry is None,'Apply has no entry selector');apply()
    else:need(a.entry is not None,'Restore one original index explicitly');restore(a.entry)


if __name__=='__main__':main()
