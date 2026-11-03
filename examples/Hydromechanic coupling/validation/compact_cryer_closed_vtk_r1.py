"""Stream lossless NTFS compression over eight exact, closed June Cryer VTK groups."""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat as statmod
import subprocess

HERE = Path(__file__).resolve().parent
CASE = HERE.parent / '04_CryerProblem_PR'
TAG = 'compact_cryer_closed_vtk_r1'
NOTE = HERE / (TAG + '.json')
TARGETS = HERE / (TAG + '.targets.json')
BEFORE = HERE / (TAG + '.before.jsonl')
AFTER = HERE / (TAG + '.after.jsonl')
CALLS = HERE / (TAG + '.calls.jsonl')
STATUS = HERE / (TAG + '.status.json')
TEMP = HERE / (TAG + '.status.tmp')
FINAL = HERE / (TAG + '.check.json')
BATCH_SIZE = 40
GROUPS = {
    'CaseCryerProblem_PR_dp002_rampclosed_nu045_out': (1008, 8250572736),
    'CaseCryerProblem_PR_dp002_rampclosed_nu010_out': (1003, 8209647276),
    'CaseCryerProblem_PR_dp002_rampclosed_nu020_out': (1003, 8209647276),
    'CaseCryerProblem_PR_dp002_rampclosed_nu030_out': (1003, 8209647276),
    'CaseCryerProblem_PR_nu010_out': (1001, 4279711436),
    'CaseCryerProblem_PR_nu020_out': (1001, 4279711436),
    'CaseCryerProblem_PR_nu045_out': (1001, 4279711436),
    'CaseCryerProblem_PR_out': (1001, 4279711436),
}


def need(ok, why):
    if not ok:
        raise ValueError(why)


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def save_new(path, obj):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(obj, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def append(stream, obj):
    stream.write(json.dumps(obj, ensure_ascii=False, allow_nan=False) + '\n')


def flush(stream):
    stream.flush()
    os.fsync(stream.fileno())


def status(phase, **extra):
    obj = dict(stage=TAG, phase=phase, utc=utc(), pid=os.getpid(), **extra)
    if STATUS.exists():
        save_new(TEMP, obj)
        os.replace(TEMP, STATUS)
    else:
        save_new(STATUS, obj)
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def check_directories(directories):
    """Check shared ancestor chains once per phase/batch, not once per file read."""
    checked = set()
    for directory in directories:
        need(directory.is_absolute() and directory.is_relative_to(CASE),
             'Directory outside exact case root: ' + str(directory))
        for current in (directory, *directory.parents):
            if current in checked:
                continue
            checked.add(current)
            info = current.lstat()
            need(statmod.S_ISDIR(info.st_mode) and not (info.st_file_attributes & 0x400),
                 'Non-directory/reparse ancestor rejected: ' + str(current))


def metadata(path):
    info = path.lstat()
    need(statmod.S_ISREG(info.st_mode) and not (info.st_file_attributes & 0x400) and info.st_nlink == 1,
         'Ordinary non-reparse single-link file required: ' + str(path))
    return dict(path=str(path), bytes=info.st_size, mtime_ns=info.st_mtime_ns,
                attributes=info.st_file_attributes)


def same_metadata(path, old):
    now = metadata(path)
    need(now['bytes'] == old['bytes'] and now['mtime_ns'] == old['mtime_ns'],
         'File size/time changed: ' + str(path))
    return now


def allocated(path):
    high = wintypes.DWORD()
    ctypes.set_last_error(0)
    low = GET_SIZE(str(path), ctypes.byref(high))
    need(low != 0xffffffff or not ctypes.get_last_error(), 'GetCompressedFileSizeW failed: ' + str(path))
    return (high.value << 32) | low


def hashed(path, old=None):
    row = same_metadata(path, old) if old is not None else metadata(path)
    row['allocated_bytes'] = allocated(path)
    row['sha256'] = sha(path)
    end = metadata(path)
    row['stable_during_hash'] = end['bytes'] == row['bytes'] and end['mtime_ns'] == row['mtime_ns']
    if old is not None:
        need(row['stable_during_hash'], 'File changed during before hash: ' + str(path))
    return row


def entry(path):
    # Windows system tools may have legitimate WinSxS hardlinks; they are read-only bindings.
    info = path.lstat()
    need(statmod.S_ISREG(info.st_mode) and not (info.st_file_attributes & 0x400),
         'Bound input must be an ordinary non-reparse file: ' + str(path))
    row = dict(path=str(path), bytes=info.st_size, mtime_ns=info.st_mtime_ns,
               attributes=info.st_file_attributes)
    row['sha256'] = sha(path)
    return row


def preflight():
    check_directories([CASE])
    targets, runs, groups = [], [], []
    for name, (count, total) in GROUPS.items():
        directory = CASE / name / 'particles'
        data = CASE / name / 'data'
        check_directories([directory, data])
        run = CASE / name / 'Run.out'
        run_entry = entry(run)
        closed = run.read_bytes().decode('utf-8', errors='replace').strip().splitlines()
        need(closed and closed[-1].strip() == 'Finished execution (code=0).', 'Closed Run.out required: ' + name)
        stamp = datetime.fromtimestamp(run_entry['mtime_ns'] / 1e9, timezone.utc)
        need((stamp.year, stamp.month) == (2026, 6), 'Only the exact closed June runs are permitted')
        runs.append(run_entry)
        leaves = sorted(p for p in directory.iterdir() if p.suffix.lower() == '.vtk')
        expected = ['PartFluid_' + format(index, '04d') + '.vtk' for index in range(count)]
        need([p.name for p in leaves] == expected, 'Exact sequential VTK set changed: ' + name)
        raw = sorted(p.name for p in data.iterdir() if re.fullmatch(r'Part_\d+\.bi4', p.name))
        need(raw == ['Part_' + format(index, '04d') + '.bi4' for index in range(count)],
             'One retained BI4 for each VTK required: ' + name)
        group_rows = []
        for path in leaves:
            row = metadata(path)
            need(not (row['attributes'] & 0x800), 'Target already compressed; this fresh run will not adopt it')
            with path.open('rb') as stream:
                header = [stream.readline().strip() for _ in range(3)]
            need(header == [b'# vtk DataFile Version 3.0', b'vtk output', b'BINARY'], 'Unexpected VTK format')
            source = data / ('Part_' + path.stem.split('_')[-1] + '.bi4')
            row['retained_BI4'] = metadata(source)
            group_rows.append(row)
        need(sum(row['bytes'] for row in group_rows) == total, 'Reviewed group byte count changed: ' + name)
        targets.extend(group_rows)
        groups.append(dict(directory=str(directory), files=count, bytes=total, closed_run=run_entry))
    need(len(targets) == 8021 and len({row['path'] for row in targets}) == 8021 and
         sum(row['bytes'] for row in targets) == 49998360308, 'Exact eight-group whitelist changed')
    return targets, runs, groups


def compact(paths, batch):
    argv = [str(COMPACT), '/C', '/I', '/Q'] + [str(path) for path in paths]
    call = dict(batch=batch, started_utc=utc(), program=str(COMPACT), arguments=argv[1:],
                literal_file_arguments=True, shell=False, recursive=False, exit_code=None)
    try:
        result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, shell=False,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        call.update(exit_code=result.returncode, output=result.stdout.decode('mbcs', errors='replace'),
                    output_bytes=len(result.stdout), output_sha256=hashlib.sha256(result.stdout).hexdigest(),
                    invocation_failure=None)
    except Exception as exc:
        call['invocation_failure'] = str(exc)
    call['ended_utc'] = utc()
    return call


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    need(args.execution_authorized, 'Root must fully review this script before explicit execution')
    need(os.name == 'nt', 'Windows NTFS required')
    need(all(not path.exists() for path in (TARGETS, BEFORE, AFTER, CALLS, STATUS, TEMP, FINAL)),
         'Fresh evidence paths required; never rerun or overwrite a partial/completed attempt')
    global GET_SIZE, COMPACT
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    GET_SIZE = kernel.GetCompressedFileSizeW
    GET_SIZE.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    GET_SIZE.restype = wintypes.DWORD
    COMPACT = Path(os.environ['SystemRoot']) / 'System32' / 'compact.exe'
    need(COMPACT.is_file(), 'SystemRoot/System32/compact.exe required')
    import psutil
    # BelowNormal cleanup starved behind the ongoing CPU8 job in the observed first attempt.
    # Set only this process to standard Normal; never change another process or task.
    psutil.Process().nice(psutil.NORMAL_PRIORITY_CLASS)
    own = [entry(Path(__file__).resolve()), entry(NOTE), entry(COMPACT)]
    free_before = shutil.disk_usage(CASE).free
    targets, runs, groups = [], [], []
    verified, batches, saved = 0, 0, 0
    failure, probe = None, None
    with BEFORE.open('x', encoding='utf-8') as before, AFTER.open('x', encoding='utf-8') as after, CALLS.open('x', encoding='utf-8') as calls:
        try:
            status('preflight_metadata', free_bytes=free_before)
            targets, runs, groups = preflight()
            save_new(TARGETS, dict(stage=TAG, utc=utc(), author_inputs=own, groups=groups, targets=targets,
                                   files=8021, logical_bytes=49998360308, sha_preflight_all_files=False,
                                   policy='Only literal VTK files in eight closed June groups; NTFS compression only.'))
            selections = [(0, 1)] + [(start, min(start + BATCH_SIZE, len(targets)))
                                     for start in range(1, len(targets), BATCH_SIZE)]
            for batch, (start, stop) in enumerate(selections):
                directories = {Path(row['path']).parent for row in targets[start:stop]}
                directories.update(Path(row['retained_BI4']['path']).parent for row in targets[start:stop])
                check_directories(sorted(directories))
                status('hashing_batch_before', batch=batch, first=start, stop=stop, verified_files=verified,
                       verified_allocated_bytes_saved=saved)
                old_rows = []
                for index in range(start, stop):
                    old = targets[index]
                    same_metadata(Path(old['retained_BI4']['path']), old['retained_BI4'])
                    row = hashed(Path(old['path']), old)
                    need(not (row['attributes'] & 0x800), 'Concurrent compression or changed baseline detected')
                    old_rows.append(row)
                    append(before, dict(batch=batch, index=index, **row))
                flush(before)
                call = compact([Path(row['path']) for row in old_rows], batch)
                append(calls, call)
                flush(calls)
                batches += 1
                errors = []
                for index, old in zip(range(start, stop), old_rows):
                    # Journal actual after metadata/hash before judging it against the before row.
                    now = hashed(Path(old['path']))
                    exact = now['stable_during_hash'] and now['sha256'] == old['sha256'] and now['bytes'] == old['bytes'] and now['mtime_ns'] == old['mtime_ns']
                    compressed = bool(now['attributes'] & 0x800)
                    append(after, dict(batch=batch, index=index, sha_bytes_mtime_exact=exact,
                                       ntfs_compressed=compressed, **now))
                    same_metadata(Path(targets[index]['retained_BI4']['path']), targets[index]['retained_BI4'])
                    if exact and compressed:
                        verified += 1
                        saved += old['allocated_bytes'] - now['allocated_bytes']
                    else:
                        errors.append(old['path'])
                    if batch == 0:
                        probe = dict(path=old['path'], allocated_before=old['allocated_bytes'],
                                     allocated_after=now['allocated_bytes'], sha_bytes_mtime_exact=exact,
                                     at_least_10percent_saved=old['allocated_bytes'] > 0 and
                                     10 * now['allocated_bytes'] <= 9 * old['allocated_bytes'])
                flush(after)
                need(call['exit_code'] == 0 and not call['invocation_failure'], 'compact call failed; evidence retained')
                need(not errors, 'Batch payload/compression verification failed: ' + repr(errors))
                if batch == 0:
                    need(probe['at_least_10percent_saved'], 'Probe saves less than 10%; all remaining targets left untouched')
                status('batch_verified', batch=batch, verified_files=verified, files=len(targets),
                       verified_allocated_bytes_saved=saved, free_bytes=shutil.disk_usage(CASE).free)
            need(verified == 8021, 'Not every reviewed file was verified')
            check_directories([CASE / name / leaf for name in GROUPS for leaf in ('particles', 'data')])
            for row in targets:
                now = same_metadata(Path(row['path']), row)
                need(now['attributes'] & 0x800, 'Final compressed attribute missing')
                same_metadata(Path(row['retained_BI4']['path']), row['retained_BI4'])
            for old in runs + own:
                now = entry(Path(old['path']))
                need(now == old, 'Bound Run.out/script/note/tool changed')
        except Exception as exc:
            failure = str(exc)
        flush(before)
        flush(after)
        flush(calls)
    complete = failure is None and verified == 8021
    result = dict(stage=TAG, utc=utc(), passed=complete, failure=failure, expected_files=8021,
                  expected_logical_bytes=49998360308, metadata_snapshotted_files=len(targets),
                  verified_files=verified, compact_calls=batches, probe=probe,
                  allocated_bytes_saved=saved if complete else None,
                  verified_allocated_bytes_saved=saved, free_bytes_before=free_before,
                  free_bytes_after=shutil.disk_usage(CASE).free, author_inputs=own,
                  evidence=[entry(path) for path in (TARGETS, BEFORE, AFTER, CALLS) if path.exists()],
                  all8021_sha_bytes_mtime_exact=complete, every_target_path_retained=True if complete else None,
                  ntfs_storage_attributes_changed_only=complete, deleted_files=0, moved_files=0,
                  raw_BI4_contents_written=False, raw_BI4_size_and_mtime_rechecked=complete,
                  payload_writes_requested=False, formal_payload_unchanged_verified=complete,
                  production_source_written=False, other_jobs_or_tool_processes_touched=False,
                  legacy2697_compression_managed_by_this_script=False, physical_acceptance=False,
                  restore='compact.exe /U /I /Q with the same exact literal paths and sufficient free space',
                  rerun_allowed=False)
    save_new(FINAL, result)
    status('completed' if complete else 'failed_preserved', verified_files=verified,
           allocated_bytes_saved=result['allocated_bytes_saved'], failure=failure)
    return 0 if complete else 1


if __name__ == '__main__':
    raise SystemExit(main())
