"""One hidden notification for the two fixed, already-running Cryer cleanup owners."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import psutil

V = Path(__file__).resolve().parent
NAME = 'poromech_disk_followup_r1'
THREAD = '01a07683-bc64-7463-8db7-9ee6243967d8'
PYTHON = Path('D:/anaconda3/python.exe')
SRC = V.parents[2] / 'src'
NOTE = V / (NAME + '.json')
LOCK, STATUS, LOG, TERMINAL, ATTEMPT, RESULT = [V / (NAME + suffix) for suffix in
    ('.lock.json', '.status.json', '.worker.log', '.terminal.json', '.queue_attempt.json', '.queue_result.json')]
TEMP = V / (NAME + '.status.tmp')
OWNERS = {'legacy': (30096, 1793684882.2350483, 2697), 'closed': (10644, 1793685981.4438329, 8021)}
PINS = [
    ('compact_cryer_legacy_vtk_r1.py', 8573, '044b4c0c6957cabdf8631b2446aa865b77fcfec6e747a51d8781008a58d31757'),
    ('compact_cryer_legacy_vtk_r1.before.json', 2010414, '4f38a0315c812e5c463fbd1d74be63d570499ab173f3ae3751a06841c2be408e'),
    ('compact_cryer_legacy_vtk_r1.scheduling.json', 616, '672415ad923c0576a091fa40c62f70f844354e3c9c9f999778a609a29e4b0355'),
    ('compact_cryer_closed_vtk_r1.py', 15748, 'df3c25000500f2a208cc3b0bdb815ba51ba6085a71b4b2a350a0aeda9b52c4aa'),
    ('compact_cryer_closed_vtk_r1.json', 6057, '6199ff9fefec2ad81504499305cee1b9af6f3c35e8a11cc1d0354ab58c71bdc4'),
    ('compact_cryer_closed_vtk_r1.targets.json', 4863172, '47089411638bce589912bf7c19a30bca0ee514d6750ae8031ccc870cbcdf439c'),
    ('remove_sw_link_cache_r1.offline_r1.check.json', 4302, '07a13f1bd459f3333558bd654058c33d57ec5f62616e975d42829599171a4862')]


def need(ok, why):
    if not ok:
        raise ValueError(why)


def utc():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def entry(path):
    path = Path(path).resolve(strict=True)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    info = path.stat()
    return dict(path=str(path), bytes=info.st_size, mtime_ns=info.st_mtime_ns, sha256=digest.hexdigest())


def observe(expected):
    row = dict(expected=expected, actual=None, unchanged=False, error=None)
    try:
        row['actual'] = entry(expected['path'])
        row['unchanged'] = row['actual']['sha256'] == expected['sha256'].lower() and (
            'bytes' not in expected or row['actual']['bytes'] == expected['bytes']) and (
            'mtime_ns' not in expected or row['actual']['mtime_ns'] == expected['mtime_ns'])
    except (OSError, ValueError) as error:
        row['error'] = str(error)
    return row


def observe_metadata(expected):
    row = dict(scope='poll_size_mtime_only', expected=expected, actual=None, unchanged=False, error=None)
    try:
        info = Path(expected['path']).stat()
        row['actual'] = dict(path=expected['path'], bytes=info.st_size, mtime_ns=info.st_mtime_ns)
        row['unchanged'] = info.st_size == expected['bytes'] and info.st_mtime_ns == expected['mtime_ns']
    except OSError as error:
        row['error'] = str(error)
    return row


def verify(expected):
    row = observe(expected)
    need(row['unchanged'], 'Immutable mismatch: ' + json.dumps(row))
    return row['actual']


def seal(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def status(value):
    seal(TEMP, dict(stage=NAME, utc=utc(), worker_pid=os.getpid(), **value))
    os.replace(TEMP, STATUS)


def owner(which):
    pid, created, _ = OWNERS[which]
    expected = dict(pid=pid, created_epoch=created, exe=str(PYTHON), cwd=str(SRC), command=[str(PYTHON), '-u', '-B',
        '..\\examples\\Hydromechanic coupling\\validation\\compact_cryer_' + which + '_vtk_r1.py', '--execution-authorized'])
    row = dict(expected=expected, actual=None, state='absent')
    try:
        process = psutil.Process(pid)
        row['actual'] = dict(pid=pid, created_epoch=process.create_time(), exe=process.exe(), cwd=process.cwd(), command=process.cmdline())
        actual = row['actual']
        row['state'] = 'live' if process.is_running() and process.status() != psutil.STATUS_ZOMBIE else 'absent'
        if abs(actual['created_epoch'] - created) > .002 or actual['command'] != expected['command'] or any(
                actual[key].casefold() != expected[key].casefold() for key in ('exe', 'cwd')):
            row['state'] = 'identity_changed'
    except psutil.NoSuchProcess:
        pass
    except psutil.Error as error:
        row.update(state='unobservable', error=str(error))
    return row


def checked_final(which):
    prefix = 'compact_cryer_' + which + '_vtk_r1'
    path = V / (prefix + '.check.json')
    receipt = entry(path)
    result = read(path)
    need(entry(path) == receipt, 'Final changed during read')
    need(result.get('stage') == prefix and type(result.get('passed')) is bool and result.get('physical_acceptance') is False,
         'Final stage/status differs from fixed owner')
    if not result['passed']:
        return dict(state='failed_receipt', receipt=receipt, failure=result.get('failure')), [receipt]
    count = OWNERS[which][2]
    need(result.get('verified_files') == count and result.get('deleted_files') == 0, 'Final count/deletion guard failed')
    consumed = [receipt]
    if which == 'legacy':
        before = V / (prefix + '.before.json')
        need(Path(result['before_manifest']).resolve() == before and result.get('files') == count and
             result.get('unchanged_content_paths_and_mtime') is True, 'Legacy unchanged/count proof missing')
        consumed.append(entry(before))
        old, new, calls = read(before)['targets'], result['after'], result['calls']
    else:
        need(result.get('expected_files') == count and result.get('all8021_sha_bytes_mtime_exact') is True and
             result.get('every_target_path_retained') is True and result.get('formal_payload_unchanged_verified') is True,
             'Closed all-file payload/path proof missing')
        expected_paths = {V / (prefix + suffix) for suffix in ('.targets.json', '.before.jsonl', '.after.jsonl', '.calls.jsonl')}
        need({Path(row['path']).resolve() for row in result['evidence']} == expected_paths, 'Unexpected consumed evidence paths')
        consumed += [verify(row) for row in result['evidence'] + result['author_inputs']]
        def lines(suffix):
            return [json.loads(line) for line in (V / (prefix + suffix)).read_text(encoding='utf-8-sig').splitlines()]
        old, new, calls = lines('.before.jsonl'), lines('.after.jsonl'), lines('.calls.jsonl')
        need([row['index'] for row in old] == list(range(count)) == [row['index'] for row in new] and
             all(row['sha_bytes_mtime_exact'] is True and row['ntfs_compressed'] is True for row in new) and
             result['compact_calls'] == len(calls), 'Closed streaming proof differs')
    need(len(old) == len(new) == count and len({row['path'] for row in old}) == count and all(
        all(a[key] == b[key] for key in ('path', 'sha256', 'bytes', 'mtime_ns')) for a, b in zip(old, new)),
        'Per-file before/after proof differs')
    need(len(calls) == (69 if which == 'legacy' else 202) and all(type(row.get('exit_code')) is int and
         row['exit_code'] == 0 and not row.get('invocation_failure') for row in calls), 'Actual compact typed-exit calls missing')
    saved = sum(row['allocated_bytes'] for row in old) - sum(row['allocated_bytes'] for row in new)
    need(type(result.get('allocated_bytes_saved')) is int and saved == result['allocated_bytes_saved'] and saved > 0,
         'Stored-byte saving differs from owner evidence')
    return dict(state='completed_validated', receipt=receipt, verified_files=count, stored_bytes_saved=saved,
                free_bytes_before=result.get('free_bytes_before'), free_bytes_after=result.get('free_bytes_after'),
                raw_file_payloads_rehashed_by_watcher=False), consumed


def message(event):
    return ('这是用户已授权的同一线程清理续办提醒，事件：' + event + '。先核验 ' + str(TERMINAL) + ' 和 ' + str(ATTEMPT) +
        ' 的冻结哈希、两个原始 owner 身份、最终检查和所消费证据，检查实际回收量；过程退出不能替代有效检查。'
        '3个ILK删除的115584456逻辑字节不能声称是精确磁盘空闲增量；NTFS实际存储节省以两份验证检查为准，卷空闲变化只作描述。'
        '若失败、PID复用、绑定改变或owner消失而缺最终检查，离线审阅保留证据并报告实际观察，禁止盲目重跑清理或覆盖结果。'
        '核验后完成已授权的选择性Git清理说明/记录备份，保留无关既有改动、正式结果、原始BI4/NBI4、图CSV和程序源码归档。'
        '保护正在运行的CPU coarse和独立GPU component及全部依赖，不停止、恢复、重启或重新布防。继续已授权u-pl工作并中文主动汇报，不重复请求用户确认。'
        '本通知器不运行压缩、删除、求解器、构建、Git或后续任务；同线程只尝试一次队列投递，超时可能已投递，禁止自动重发或未来重新布防。')


def worker(args):
    lock_problem = None
    try:
        need(entry(LOCK)['sha256'] == args.lock_sha256, 'Frozen launch lock changed')
        lock = read(LOCK)
        need(lock['stage'] == NAME and lock['thread'] == THREAD and lock['codex'] == args.codex, 'Launch destination changed')
        need(entry(LOCK)['sha256'] == args.lock_sha256, 'Launch lock changed during read')
    except (OSError, ValueError, KeyError) as error:
        lock_problem = str(error)
        lock = dict(immutable=[dict(path=str(V / name), bytes=size, sha256=digest) for name, size, digest in PINS], free_bytes_before=None)
    startup_observations = [observe(row) for row in lock['immutable']] + [observe(dict(path=str(LOCK), sha256=args.lock_sha256))]
    startup_bindings = [row['actual'] if row['unchanged'] else row['expected'] for row in startup_observations]
    startup_problems = ([lock_problem] if lock_problem else []) + (
        ['Worker startup full-hash verification failed'] if any(not row['unchanged'] for row in startup_observations) else [])
    cached, proofs, dead = {}, [], {}
    while True:
        states = {which: owner(which) for which in OWNERS}
        # Large immutable programs/manifests are fully hashed at startup/end, never every30s.
        observations = [observe_metadata(row) for row in startup_bindings + proofs if 'mtime_ns' in row]
        problems = list(startup_problems)
        if any(not row['unchanged'] for row in observations):
            problems.append('Frozen consumed inputs changed or became unreadable; inspect expected/actual observations')
        for which in OWNERS:
            if which in cached:
                continue
            path = V / ('compact_cryer_' + which + '_vtk_r1.check.json')
            if path.exists():
                try:
                    cached[which], consumed = checked_final(which)
                    proofs += consumed
                except (json.JSONDecodeError, OSError) as error:
                    states[which]['final_read_error'] = str(error)
                except (ValueError, KeyError, TypeError) as error:
                    try:
                        actual = entry(path)
                    except (OSError, ValueError) as diagnostic_error:
                        actual = dict(path=str(path), read_error=str(diagnostic_error))
                    cached[which] = dict(state='rejected_receipt', failure=str(error), actual_final=actual)
            if which in cached:
                if cached[which]['state'] != 'completed_validated':
                    problems.append(which + ': ' + cached[which]['state'])
                continue  # A sealed valid completion can be adopted after its original owner has exited.
            state = states[which]['state']
            if state in ('identity_changed', 'unobservable'):
                problems.append(which + ': ' + state)
            if state == 'absent':
                dead.setdefault(which, time.monotonic())
                states[which]['absent_observed_s'] = time.monotonic() - dead[which]
                if states[which]['absent_observed_s'] > 120:
                    problems.append(which + ': owner absent over120s without validated final')
            else:
                dead.pop(which, None)
        status(dict(state='observing', owners=states, checks=cached, problems=problems, queue_attempts=0,
                    startup_full_hashes_verified=not startup_problems, polling_scope='size_mtime_only'))
        if problems or len(cached) == 2:
            break
        time.sleep(30)
    final_expected = startup_bindings + proofs
    observations = [observe(row) for row in final_expected]
    if any(not row['unchanged'] for row in observations):
        problems.append('Final consumed-evidence recheck failed; notification is still required')
    ilk_entry = next(row for row in lock['immutable'] if Path(row['path']).name == 'remove_sw_link_cache_r1.offline_r1.check.json')
    ilk = None
    try:
        if observe(ilk_entry)['unchanged']:
            ilk = read(ilk_entry['path'])
            need(ilk.get('passed') is True and len(ilk.get('deleted_files_verified_absent', [])) == 3,
                 'Three-ILK offline receipt status differs')
    except (OSError, ValueError, KeyError, TypeError) as error:
        problems.append('ILK offline receipt read/review failed: ' + str(error))
    event = 'cleanup_review_required' if problems else 'both_cleanup_checks_validated'
    free_now = shutil.disk_usage(V).free
    checks = {which: cached.get(which, dict(state='pending_or_unsealed',
              final_exists=(V / ('compact_cryer_' + which + '_vtk_r1.check.json')).exists())) for which in OWNERS}
    terminal = dict(stage=NAME, utc=utc(), event=event, problems=problems, owners=states, checks=checks,
        immutable_observations=observations, immutable_hashes_reverified=all(row['unchanged'] for row in observations),
        startup_full_hash_observations=startup_observations, polling_scope='size_mtime_only_not_continuous_hashing',
        final_full_hash_verification_performed=True, atomic_filesystem_snapshot_claimed=False,
        ILK_offline_receipt=ilk_entry,
        ILK_reported_deleted_logical_bytes=ilk.get('deleted_bytes') if ilk else None, ILK_logical_bytes_are_exact_disk_free_claim=False,
        verified_completed_ntfs_stored_bytes_saved=sum(row.get('stored_bytes_saved', 0) for row in cached.values()),
        volume_free_bytes_descriptive=free_now, volume_change_since_watch_launch_descriptive=free_now - lock['free_bytes_before'] if lock['free_bytes_before'] is not None else None,
        raw_VTK_BI4_payloads_rehashed=False, physical_acceptance=False, jobs_stopped_or_rearmed=False)
    seal(TERMINAL, terminal)  # Seal observations BEFORE the sole queue intent and call.
    argv = [args.codex, 'queue', '--thread', THREAD, '--message', message(event)]
    seal(ATTEMPT, dict(stage=NAME, utc=utc(), terminal=entry(TERMINAL), arguments=argv, attempt=1, max_attempts=1,
                       timeout_s=45, timeout_may_already_have_delivered=True, automatic_retry=False))
    outcome = dict(stage=NAME, utc=utc(), attempt=entry(ATTEMPT), attempts=1, automatic_retry=False)
    try:
        queued = subprocess.run(argv, cwd=V, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace', timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        outcome.update(status='queued' if queued.returncode == 0 else 'queue_failed', return_code=queued.returncode, output=queued.stdout)
    except subprocess.TimeoutExpired as error:
        output = error.stdout or b''
        outcome.update(status='queue_delivery_uncertain', return_code=None, output=output.decode('utf-8', errors='replace') if isinstance(output, bytes) else output,
                       error=str(error), may_already_have_queued=True, do_not_resend=True)
    except OSError as error:
        outcome.update(status='queue_failed', return_code=None, error=str(error), do_not_resend=True)
    seal(RESULT, outcome)
    status(dict(state=outcome['status'], terminal=entry(TERMINAL), queue_attempt=entry(ATTEMPT), queue_result=entry(RESULT), queue_attempts=1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--launch', action='store_true')
    mode.add_argument('--worker', action='store_true')
    parser.add_argument('--thread', required=True)
    parser.add_argument('--codex', required=True)
    parser.add_argument('--lock-sha256')
    args = parser.parse_args()
    need(os.name == 'nt' and args.thread == THREAD and Path(sys.executable).resolve() == PYTHON.resolve(), 'Exact Windows interpreter/root thread required')
    need(Path(args.codex).is_absolute() and (args.worker or Path(args.codex).is_file()),
         'Root must pass the literal existing absolute Codex executable')
    need(all(not path.exists() for path in (STATUS, TEMP, TERMINAL, ATTEMPT, RESULT)), 'Existing watcher records protected; no rearm')
    if args.worker:
        worker(args)
        return
    need(args.lock_sha256 is None and not LOCK.exists() and not LOG.exists(), 'Fresh one-shot lock/log required')
    fixed = [dict(path=str(V / name), bytes=size, sha256=digest) for name, size, digest in PINS]
    launch_observations = [observe(row) for row in fixed]
    own = [entry(path) for path in (Path(__file__), NOTE, PYTHON, Path(psutil.__file__), Path(args.codex))]
    immutable = fixed + own
    launch_observations += [dict(expected=row, actual=row, unchanged=True, scope='launch_full_hash') for row in own]
    seal(LOCK, dict(stage=NAME, utc=utc(), thread=THREAD, codex=args.codex, immutable=immutable,
                    launch_full_hash_observations=launch_observations,
                    owners={which: owner(which) for which in OWNERS}, free_bytes_before=shutil.disk_usage(V).free,
                    one_shot=True, rearm_allowed=False, solver_cleanup_or_build_started=False))
    argv = [str(PYTHON), '-u', '-B', str(Path(__file__).resolve()), '--worker', '--thread', THREAD,
            '--codex', args.codex, '--lock-sha256', entry(LOCK)['sha256']]
    with LOG.open('x', encoding='utf-8') as stream:
        process = subprocess.Popen(argv, cwd=V, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
    print(json.dumps(dict(stage=NAME, worker_pid=process.pid, lock=entry(LOCK), status=str(STATUS), queue_call_made_by_launcher=False)))


if __name__ == '__main__':
    main()
