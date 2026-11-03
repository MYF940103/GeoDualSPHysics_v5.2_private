"""One same-thread notification for one exact admitted mid2 owner; no computation runner."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil

T = Path(__file__).resolve().parents[1]
TAG = 'upl_hg_mid2_CPU1_coarse_r1'
NAME = 'upl_hg_mid2_followup_r1'
ROOT_THREAD = '01a07683-bc64-7463-8db7-9ee6243967d8'
START, RUN, CALL = (T / 'logs' / (TAG + suffix) for suffix in ('.start.json', '.run.json', '.call.json'))
NOTE = T / 'notes' / (NAME + '.json')
LOCK, STATUS, WORKER_LOG, TERMINAL, ATTEMPT, RESULT, STATUS_TEMP = (
    T / 'logs' / (NAME + suffix) for suffix in
    ('.lock.json', '.status.json', '.worker.log', '.terminal.json', '.queue_attempt.json', '.queue_result.json', '.status.json.tmp'))


def need(ok, why):
    if not ok:
        raise ValueError(why)


def utc():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def entry(path):
    path = Path(path).resolve(strict=True)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def verify(expected):
    actual = entry(expected['path'])
    need(actual == expected, 'Immutable artifact changed: ' + expected['path'])
    return Path(expected['path'])


def metadata(path):
    stat = Path(path).stat()
    return dict(bytes=stat.st_size, mtime_ns=stat.st_mtime_ns)


def fresh(paths):
    need(all(not path.exists() for path in paths), 'Existing followup artifact protected; never restart or rearm')


def seal(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def save_status(state):
    if STATUS.exists():
        previous = read(STATUS)
        need(previous['stage'] == NAME and previous['worker_pid'] == state['worker_pid'] and
             previous['lock_sha256'] == state['lock_sha256'], 'Status belongs to another watcher')
    state['updated_utc'] = utc()
    seal(STATUS_TEMP, state)
    os.replace(STATUS_TEMP, STATUS)


def expected_arguments():
    return ['-cpu', '-ompthreads:1', '-stable', '-mdbc_freeslip',
        str(T / 'outputs/upl_hg_mid2_seed_r1/upl_hg_mid2_coarse_r1'), str(T / 'outputs' / TAG),
        '-dirdataout', 'data', '-svres', '-nsteps:1048576']


def validate_start(expected):
    verify(expected)
    need(Path(expected['path']).resolve() == START.resolve(), 'Only the fixed new mid2 start path is allowed')
    start = read(START)
    need(start.get('stage') == 'upl_hg_mid2_start_r1' and start.get('tag') == TAG and
         start.get('configuration') == 'ReleaseCPU' and start.get('window') == 'coarse' and
         start.get('direct_owner_no_scheduler') is True and start.get('native_call_started_by_start_record') is False and
         start.get('physical_acceptance') is False, 'Exact new direct start schema differs')
    need(Path(start['owner_script']['path']).resolve() == (T / 'support/upl_hg_mid2_run_r1.py').resolve(), 'Owner script differs')
    job = start['job']
    wanted = dict(tag=TAG, backend='CPU', configuration='ReleaseCPU', window='coarse', threads=1,
        input_variant='coarse', steps=1048576, dt_s=2.0 ** -19, end_s=2, expected_samples=1517,
        event_completed_step=5243, post_open_frames=1313, post_open_drained_particle_checks_expected=13130,
        expected_native_total_arrays=22, expected_total_native_count=1040)
    need(all(job.get(k) == v for k, v in wanted.items()) and
         start['arguments'] == job['arguments'] == expected_arguments() and
         job['output_directory'] == str(T / 'outputs' / TAG), 'Fixed prepared CPU1 job/arguments differ')
    need(len(job['saved_clock_table']) == 1517 and job['saved_clock_table'][0]['completed_steps'] == 0 and
         job['saved_clock_table'][-1]['completed_steps'] == 1048576, 'Pinned start clock membership differs')
    immutable = [expected] + start['inputs']
    for key in ('owner_script', 'program', 'input_manifest', 'source_build', 'reader_helper', 'admission'):
        need(start[key] in start['inputs'], 'Owner start omitted a required frozen input: ' + key)
    unique = {}
    for item in immutable:
        key = str(Path(item['path']).resolve()).casefold()
        need(key not in unique or unique[key] == item, 'Conflicting immutable Entries in start')
        unique[key] = item
    return start, list(unique.values())


def owner_identity(start):
    expected = start['owner']
    need(type(expected['pid']) is int and expected['pid'] > 0 and type(expected['created_epoch']) in (int, float),
         'Actual owner PID/creation is missing')
    owner = psutil.Process(expected['pid'])
    need(owner.is_running() and abs(owner.create_time() - expected['created_epoch']) <= .002 and
         owner.cmdline() == expected['command'] and owner.exe() == expected['exe'] and
         str(Path(owner.cwd()).resolve()) == expected['cwd'], 'Actual owner instance differs from the pinned start')
    command, cwd = expected['command'], Path(expected['cwd'])
    def resolve_argument(value):
        path = Path(value)
        return (path if path.is_absolute() else cwd / path).resolve()
    need(sum(resolve_argument(value) == Path(start['owner_script']['path']).resolve() for value in command) == 1 and
         command.count('--execution-authorized') == 1 and command.count('--admission') == 1,
         'Owner command is not the new explicitly authorized Python owner')
    position = command.index('--admission')
    need(position + 1 < len(command) and resolve_argument(command[position + 1]) == Path(start['admission']['path']).resolve(),
         'Owner command admission differs')
    return dict(expected, launch_observed_live=True)


def owner_state(frozen):
    try:
        owner = psutil.Process(frozen['pid'])
        if not owner.is_running() or owner.status() == psutil.STATUS_ZOMBIE:
            return 'dead'
        if (abs(owner.create_time() - frozen['created_epoch']) > .002 or owner.cmdline() != frozen['command'] or
                owner.exe() != frozen['exe'] or str(Path(owner.cwd()).resolve()) != frozen['cwd']):
            return 'identity_changed'
        return 'live'
    except psutil.NoSuchProcess:
        return 'dead'
    except psutil.AccessDenied:
        return 'unobservable'  # Missing access never proves owner exit.


def sealed_run(start, start_e):
    run_e = entry(RUN)
    run = read(RUN)
    need(entry(RUN) == run_e, 'Run changed while read')
    need(run.get('stage') == 'upl_hg_mid2_run_r1' and run.get('tag') == TAG and
         run.get('backend') == 'CPU' and run.get('configuration') == 'ReleaseCPU' and run.get('window') == 'coarse' and
         type(run.get('passed')) is bool and run.get('physical_acceptance') is False and
         run.get('start_record') == start_e and run.get('job') == start['job'] and
         all(run.get(key) == start[key] for key in ('program', 'source_build', 'input_manifest', 'reader_helper', 'admission', 'arguments')),
         'Sealed run belongs to a changed start/owner/job/input/program')
    need(run.get('native_decoder_invoked') is False and run.get('automatic_follow_up') is False and
         run.get('all22_native_fields_review_pending') is True and run.get('actual_native_clocks_review_pending') is True,
         'Run scope must leave native and physical review pending')
    artifacts = [run_e]
    call = None
    if run.get('call'):
        need(Path(run['call']['path']).resolve() == CALL.resolve(), 'Run points to another native call')
        verify(run['call']); call = read(CALL); artifacts.append(run['call'])
        need(call.get('stage') == 'upl_hg_mid2_call_r1' and call.get('tag') == TAG and
             call.get('configuration') == 'ReleaseCPU' and call.get('window') == 'coarse' and
             call.get('program') == call.get('target_program') == start['program'] and
             call.get('arguments') == call.get('target_arguments') == start['arguments'] and call.get('start_record') == start_e and
             call.get('direct_native_call') is True and call.get('shell') is False and
             call.get('actual_solver_call') is True and call.get('public_project_main') is True and
             call.get('fixture_or_Run_override') is False and call.get('physical_acceptance') is False,
             'Actual Python direct-call identity differs')
        if call.get('log'):
            artifacts.append(call['log'])
    if run['passed']:
        need(call is not None and call.get('owned_call_exited') is True and
             call.get('typed_returncode_captured_immediately') is True and type(call.get('exit_code')) is int and
             call['exit_code'] == 0 and call.get('invocation_failure') is None and run.get('bindings_unchanged') is True and
             run.get('steps') == 1048576 and run.get('native_frames') == 1517,
             'Passed run lacks original owned integer exit/step/frame/input guards')
    if run.get('run_out'):
        artifacts.append(run['run_out'])
    # These are raw native solver files, not decoded physical acceptance.
    files = run['files']
    root = (T / 'outputs' / TAG).resolve()
    paths = {Path(e['path']).resolve() for e in files}
    need(len(paths) == len(files) and all(path.is_relative_to(root) for path in paths), 'Sealed raw-file paths escape the fixed run output')
    need(paths == {p.resolve() for p in root.rglob('*') if p.is_file()}, 'Raw native output membership changed after seal')
    if run['passed']:
        need({p.name for p in paths if p.parent == root / 'data' and p.name.startswith('Part_') and p.suffix == '.bi4'} ==
             {'Part_%04d.bi4' % i for i in range(1517)}, 'Passed run raw PART membership differs')
    artifacts += files
    return dict(event='mid2_run_passed' if run['passed'] else 'mid2_run_failed', run_receipt=run_e,
        call_receipt=run.get('call'), passed=run['passed'], owned_exit_code=call.get('exit_code') if call else None,
        failure=run.get('failure'), reported_steps=run.get('steps'), reported_native_frames=run.get('native_frames'),
        raw_native_files_sealed=len(files), native_decoding_or_physical_review_performed_by_notifier=False,
        physical_acceptance=False), artifacts


def message(event):
    return ('这是用户已授权的同一线程继续处理提醒，不是新的人类观测。事件：' + event + '；固定运行：' + TAG + '。'
        '先完整核验 ' + str(TERMINAL) + ' 与 ' + str(ATTEMPT) + ' 的实际所有权、预期和实测哈希、原始 start/call/run、程序、输入及 native 文件身份。'
        '正常出口或本提醒不代表 native 或物理验收。失败、绑定变化、PID 复用或缺少有效最终 run 时，保留证据，报告实际状态并继续已授权诊断，不盲目重跑。'
        '成功 run 仍须根线程检查是否已有或正在运行的 reader/native owner；只在已有授权和新文件完整审阅后单独解码一次，禁止覆盖、重复解码或自动扩展。'
        '保持 1517 帧、全部 1040 IDs、22 数组、真实时钟、ledger、排水和原始 HG 门槛；native completion 应为 upl_hg_mid2_native_r1 / bounded_2s / CPU_public / coarse / c。'
        '逐帧核验排水接收数在 completed step <=5243 时为零、之后为 10，总计 1313 帧和 13130 检查，不能仅相信旧 C++ 的汇总声明。'
        '检查孔压、固定初始材料顶部和底部沉降、总应力与交替 X 列 Uz；HG0 是描述性不同算子对照。2 s coarse 不等于独立 half、理论、完整固结、晚期模态解决或正式工况验收。'
        '当前 CPU/GPU/清理状态必须重新观察，保护所有正式文件、原始 BI4/NBI4、快照及冻结依赖。不修改或重启独立任务。'
        '请用中文主动汇报定量结果并继续已授权工作，不等待用户追问。本 watcher 不运行求解器、解码、分析、构建、Git 或清理；本提醒最多一次，超时也不得重发或重新布防。')


def worker(args):
    lock_e = entry(LOCK)
    need(lock_e['sha256'] == args.lock_sha256, 'Frozen launch lock changed')
    lock = read(LOCK)
    need(lock['stage'] == NAME and lock['thread'] == args.thread == ROOT_THREAD and lock['codex'] == args.codex and
         lock['owner']['pid'] == args.owner_pid and lock['owner']['created_epoch'] == args.owner_created,
         'Worker arguments do not match the single frozen owner')
    fresh([STATUS, STATUS_TEMP, TERMINAL, ATTEMPT, RESULT])
    report = dict(stage=NAME, status='waiting', worker_pid=os.getpid(), worker_created_epoch=psutil.Process().create_time(),
        lock_sha256=lock_e['sha256'], owner=lock['owner'], thread=args.thread, started_utc=utc(), queue_attempts=0,
        solver_or_decoder_or_analysis_or_build_launched=False, physical_acceptance=False,
        startup_and_terminal_full_hash=True, polling_checks='size and mtime_ns only; no continuous-hash or atomic-race proof')
    save_status(report)
    terminal, terminal_inputs, dead_since = None, [], None
    try:
        for item in lock['immutable']:
            verify(item)
        start, _ = validate_start(lock['start_record'])
        snapshots = {item['path']: metadata(item['path']) for item in lock['immutable']}
    except (OSError, ValueError, KeyError, TypeError) as error:
        terminal = dict(event='watch_startup_binding_rejected', failure=str(error), physical_acceptance=False)
        start, snapshots = lock['start'], {}
    while terminal is None:
        began = time.monotonic()
        try:
            for path, expected in snapshots.items():
                need(metadata(path) == expected, 'Frozen polling metadata changed: ' + path)
            state = owner_state(lock['owner'])
            report.update(owner_state=state, last_poll_utc=utc())
            if RUN.exists():
                try:
                    terminal, terminal_inputs = sealed_run(start, lock['start_record'])
                except (json.JSONDecodeError, OSError) as error:
                    report['run_read_error'] = str(error)  # A writer may still be sealing its exclusive JSON.
                except (ValueError, KeyError, TypeError) as error:
                    terminal = dict(event='mid2_run_receipt_rejected', failure=str(error), physical_acceptance=False)
                    if RUN.is_file():
                        terminal_inputs.append(entry(RUN))
            if terminal is None and state == 'identity_changed':
                terminal = dict(event='fixed_owner_identity_changed', failure='PID creation/command/cwd/exe differs', physical_acceptance=False)
            if state == 'dead':
                dead_since = dead_since or time.monotonic()
                report['owner_dead_observed_for_s'] = time.monotonic() - dead_since
                if terminal is None and time.monotonic() - dead_since > 120:
                    terminal = dict(event='owner_exited_without_valid_run_receipt', failure=report.get('run_read_error'),
                                    completed_window_claimed=False, physical_acceptance=False)
            else:
                dead_since = None
            save_status(report)
        except (OSError, ValueError, KeyError, TypeError, psutil.Error) as error:
            terminal = dict(event='watch_binding_or_identity_rejected', failure=str(error), physical_acceptance=False)
        if terminal is None:
            time.sleep(max(0., 30. - (time.monotonic() - began)))
    observations = []
    expected_inputs = lock['immutable'] + terminal_inputs + [lock_e]
    for item in expected_inputs:
        observation = dict(expected=item, actual=None, unchanged=False, error=None)
        try:
            observation['actual'] = entry(item['path'])
            observation['unchanged'] = observation['actual'] == item
            if not observation['unchanged']:
                observation['error'] = 'Immutable artifact changed'
        except (OSError, ValueError) as error:
            observation['error'] = str(error)
        observations.append(observation)
    mismatches = [value for value in observations if not value['unchanged']]
    if mismatches:
        terminal.update(previous_event=terminal['event'], event='watch_final_binding_rejected',
            reported_run_passed=terminal.get('passed'), passed=False, completed_window_claimed=False,
            failure='Frozen consumed artifacts changed or became unreadable; inspect actual observations',
            immutable_binding_mismatches=mismatches)
    terminal.update(stage=NAME, observed_utc=utc(), tag=TAG, owner=lock['owner'], thread=args.thread,
        start_record=lock['start_record'], inputs=expected_inputs, immutable_hashes_reverified=not mismatches,
        immutable_hash_observations=observations, decoded_native_fields_or_physics_checked=False)
    seal(TERMINAL, terminal)
    argv = [args.codex, 'queue', '--thread', args.thread, '--message', message(terminal['event'])]
    seal(ATTEMPT, dict(stage=NAME, utc=utc(), attempt=1, max_attempts=1, thread=args.thread,
        terminal_file=entry(TERMINAL), terminal_report=terminal, immutable_hash_observations=observations,
        arguments=argv, timeout_s=45, timeout_may_have_delivered_no_resend=True, solver_or_analysis_invoked=False))
    report.update(status='queue_attempt_sealed', event=terminal['event'], queue_attempts=1,
                  terminal=entry(TERMINAL), queue_attempt=entry(ATTEMPT))
    save_status(report)
    outcome = dict(stage=NAME, utc=utc(), queue_attempt=entry(ATTEMPT), attempts=1, automatic_retry=False)
    try:
        queued = subprocess.run(argv, cwd=T.parent, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', timeout=45,
            creationflags=subprocess.CREATE_NO_WINDOW)
        outcome.update(status='queued' if queued.returncode == 0 else 'queue_failed', return_code=queued.returncode, output=queued.stdout)
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ''
        if isinstance(output, bytes):
            output = output.decode('utf-8', errors='replace')
        outcome.update(status='queue_delivery_uncertain', return_code=None, output=output, error=str(error),
                       may_already_have_queued=True, do_not_resend=True)
    except OSError as error:
        outcome.update(status='queue_failed', return_code=None, output='', error=str(error), do_not_resend=True)
    seal(RESULT, outcome)
    report.update(status=outcome['status'], queue_result=entry(RESULT), ended_utc=utc())
    save_status(report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--launch', action='store_true'); mode.add_argument('--worker', action='store_true')
    parser.add_argument('--thread', required=True); parser.add_argument('--codex', required=True)
    parser.add_argument('--start-bytes', type=int); parser.add_argument('--start-sha256')
    parser.add_argument('--owner-pid', type=int); parser.add_argument('--owner-created', type=float)
    parser.add_argument('--lock-sha256')
    args = parser.parse_args()
    need(args.thread == ROOT_THREAD, 'Pass the explicit authorized root thread, never an environment or agent thread')
    codex = Path(args.codex)
    need(codex.is_absolute() and codex.is_file(), 'Root-inspected literal absolute Codex executable is required')
    args.codex = str(codex.resolve())
    if args.worker:
        worker(args)
        return
    need(args.owner_pid is None and args.owner_created is None and args.lock_sha256 is None and
         args.start_bytes is not None and args.start_bytes > 0 and
         args.start_sha256 is not None and len(args.start_sha256) == 64 and
         all(c in '0123456789abcdef' for c in args.start_sha256), 'Launch requires root-pinned actual start bytes and SHA256')
    fresh([LOCK, STATUS, STATUS_TEMP, WORKER_LOG, TERMINAL, ATTEMPT, RESULT])
    start_e = dict(path=str(START.resolve()), bytes=args.start_bytes, sha256=args.start_sha256)
    start, immutable = validate_start(start_e)
    owner = owner_identity(start)
    immutable += [entry(__file__), entry(NOTE), entry(sys.executable), entry(psutil.__file__), entry(args.codex)]
    for item in immutable:
        verify(item)
    seal(LOCK, dict(stage=NAME, tag=TAG, utc=utc(), thread=args.thread, codex=args.codex,
        start_record=start_e, start=start, owner=owner, immutable=immutable, one_shot=True,
        rearm_or_restart_allowed=False, solver_or_analysis_or_build_launched=False))
    lock_e = entry(LOCK)
    argv = [sys.executable, '-B', str(Path(__file__).resolve()), '--worker', '--thread', args.thread,
        '--codex', args.codex, '--owner-pid', str(owner['pid']), '--owner-created', repr(owner['created_epoch']),
        '--lock-sha256', lock_e['sha256']]
    with WORKER_LOG.open('x', encoding='utf-8') as stream:
        process = subprocess.Popen(argv, cwd=T.parent, stdin=subprocess.DEVNULL, stdout=stream,
            stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    print(json.dumps(dict(status='one_followup_started', worker_pid=process.pid, owner_pid=owner['pid'],
        lock=lock_e, status_file=str(STATUS), solver_or_decoder_launched=False)))


if __name__ == '__main__':
    main()
