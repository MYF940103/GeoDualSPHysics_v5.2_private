"""Compress an exact cold Cryer VTK whitelist; preserve every byte and path."""
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
import subprocess

HERE = Path(__file__).resolve().parent
CASE = HERE.parent / '04_CryerProblem_PR'
ROOT = CASE / 'refinement'
GROUPS = {
    'damping_sweep_20260622': ['damp_0', 'damp_0p005', 'damp_0p01', 'damp_0p02', 'damp_0p05', 'damp_0p1', 'damp_0p2'],
    'ramp_drain_timing_20260624': ['closed_ramp_0p0025s', 'closed_ramp_0p005s', 'closed_ramp_0p01s', 'closed_ramp_0p02s', 'open_ramp_0p005s', 'open_ramp_0p01s', 'open_ramp_0p02s', 'ramp_0_open'],
    'k1e5_convergence_20260622': ['dp0025_early_tv001_dtv1e-4', 'dp0025_full_tv1_dtv1e-2', 'dp0025_tv010', 'dp002_tv010', 'dp003_tv010'],
    'sweep_corrected_20260621': ['k1e5_tv008_toutTv001', 'r0000_d0_full', 'r0000_d0_full_tout0250', 'r0000_d0_full_tout0250_afterfix'],
}
TAG = 'compact_cryer_legacy_vtk_r1'
PRE = HERE / (TAG + '.before.json')
FINAL = HERE / (TAG + '.check.json')
STATUS = HERE / (TAG + '.status.json')


def need(ok, why):
    if not ok:
        raise ValueError(why)


def save_new(path, obj):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(obj, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def status(phase, **kw):
    obj = dict(stage=TAG, phase=phase, utc=datetime.now(timezone.utc).isoformat(), pid=os.getpid(), **kw)
    temp = STATUS.with_suffix('.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, STATUS)
    print(json.dumps(obj, ensure_ascii=False), flush=True)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def allocated(path):
    high = wintypes.DWORD()
    ctypes.set_last_error(0)
    low = GET_SIZE(str(path), ctypes.byref(high))
    need(low != 0xffffffff or not ctypes.get_last_error(), 'Cannot read allocated bytes: ' + str(path))
    return (high.value << 32) | low


def snapshot(path):
    s = path.stat()
    return dict(path=str(path), bytes=s.st_size, sha256=sha(path),
                allocated_bytes=allocated(path), attributes=s.st_file_attributes,
                mtime_ns=s.st_mtime_ns)


def compress(paths):
    argv = [str(COMPACT), '/C', '/I', '/Q'] + [str(p) for p in paths]
    # All arguments are literal files. No /S, wildcard, shell, deletion or move.
    result = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    need(result.returncode == 0, 'compact exited ' + str(result.returncode) + ': ' + result.stdout.decode(errors='replace'))
    return dict(program=str(COMPACT), arguments=argv[1:], exit_code=result.returncode)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    need(args.execution_authorized, 'Root reviewed execution flag required')
    need(os.name == 'nt' and all(not p.exists() for p in (PRE, FINAL, STATUS)), 'Windows and fresh record paths required')
    global GET_SIZE, COMPACT
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    GET_SIZE = kernel.GetCompressedFileSizeW
    GET_SIZE.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    GET_SIZE.restype = wintypes.DWORD
    COMPACT = Path(os.environ['SystemRoot']) / 'System32' / 'compact.exe'
    need(COMPACT.is_file(), 'Windows compact.exe missing')
    # Low priority avoids competing aggressively with the two authorized development jobs.
    import psutil
    psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    root = ROOT.resolve(strict=True)
    targets = []
    for family, groups in GROUPS.items():
        for group in groups:
            directory = (root / family / group / 'out' / 'particles').resolve(strict=True)
            need(directory.is_relative_to(root) and not directory.is_symlink(), 'Target leaves intended refinement root')
            leaves = sorted(directory.glob('PartFluid_*.vtk'))
            need(leaves, 'Declared legacy group has no VTK: ' + str(directory))
            for path in leaves:
                match = re.fullmatch(r'PartFluid_(\d+)\.vtk', path.name)
                resolved = path.resolve(strict=True)
                need(match and resolved.is_relative_to(root) and not path.is_symlink() and
                     not (path.stat().st_file_attributes & 0x400), 'Invalid/reparse VTK target')
                source = directory.parent / 'data' / ('Part_' + match[1] + '.bi4')
                need(source.is_file(), 'Original BI4 missing: ' + str(source))
                targets.append((resolved, source.resolve(strict=True)))
    need(len(targets) == 2697 and len({p for p, _ in targets}) == 2697 and
         sum(p.stat().st_size for p, _ in targets) == 8343279118, 'Exact reviewed24-group whitelist changed')
    before_free = shutil.disk_usage(root).free
    status('hashing_before', files=len(targets), free_bytes=before_free)
    rows = []
    for index, (path, source) in enumerate(targets):
        row = snapshot(path)
        row['retained_BI4'] = dict(path=str(source), bytes=source.stat().st_size, mtime_ns=source.stat().st_mtime_ns)
        rows.append(row)
        if (index + 1) % 500 == 0:
            status('hashing_before', completed=index + 1, files=len(targets))
    save_new(PRE, dict(stage=TAG, script=dict(path=str(Path(__file__).resolve()), sha256=sha(Path(__file__))),
                       policy='Lossless NTFS compression only; all paths/content retained; no deletion or raw/formal/active file mutation.',
                       targets=rows, free_bytes_before=before_free))
    calls = []
    failure = None
    after = []
    try:
        status('compressing_probe', files=len(rows))
        calls.append(compress([targets[0][0]]))
        probe = snapshot(targets[0][0])
        need(probe['bytes'] == rows[0]['bytes'] and probe['sha256'] == rows[0]['sha256'], 'Probe payload changed')
        need(probe['allocated_bytes'] <= .9 * rows[0]['allocated_bytes'], 'Probe saves less than10percent; leave remaining files untouched')
        for start in range(1, len(targets), 40):
            calls.append(compress([p for p, _ in targets[start:start + 40]]))
            status('compressing', completed=min(start + 40, len(targets)), files=len(rows))
        status('verifying_after', files=len(rows))
        for index, ((path, source), old) in enumerate(zip(targets, rows)):
            now = snapshot(path)
            need(now['bytes'] == old['bytes'] and now['sha256'] == old['sha256'] and now['mtime_ns'] == old['mtime_ns'],
                 'Payload or modification time changed: ' + str(path))
            need(now['attributes'] & 0x800, 'VTK was not marked NTFS compressed')
            need(source.stat().st_size == old['retained_BI4']['bytes'] and source.stat().st_mtime_ns == old['retained_BI4']['mtime_ns'],
                 'Retained BI4 size/time changed')
            after.append(now)
            if (index + 1) % 500 == 0:
                status('verifying_after', completed=index + 1, files=len(rows))
    except Exception as exc:
        failure = str(exc)
    saved = sum(r['allocated_bytes'] for r in rows) - sum(r['allocated_bytes'] for r in after) if len(after) == len(rows) else None
    result = dict(stage=TAG, passed=failure is None, failure=failure, before_manifest=str(PRE),
                  files=len(rows), verified_files=len(after), calls=calls, after=after,
                  logical_bytes=sum(r['bytes'] for r in rows), allocated_bytes_saved=saved,
                  free_bytes_after=shutil.disk_usage(root).free, deleted_files=0,
                  unchanged_content_paths_and_mtime=len(after) == len(rows) and failure is None,
                  raw_BI4_program_source_formal_or_active_files_changed=False,
                  restore='compact.exe /U /I /Q with these exact literal file paths; sufficient free space required',
                  development_jobs_stopped=False, physical_acceptance=False)
    save_new(FINAL, result)
    status('completed' if result['passed'] else 'failed_preserved', allocated_bytes_saved=saved, failure=failure)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
