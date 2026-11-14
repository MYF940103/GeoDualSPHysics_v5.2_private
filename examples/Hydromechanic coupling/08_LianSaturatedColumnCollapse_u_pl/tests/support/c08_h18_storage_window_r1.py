"""One conditional original-physics GPU observer window; never auto-native or next."""
import argparse
import os
import re
import subprocess
from pathlib import Path
import psutil
import c08_h18_storage_short_r1 as short
import c08_h18_storage_execute_r1 as executor

m = short.m
T, C, L = m.T, m.C, m.L
TAG = 'c08_h18_storage_window_GPU_r1'
NOTE = T / 'notes/c08_h18_storage_window_r1.md'
PREP, ADMISSION, RUN = [L / (TAG + suffix) for suffix in
                        ('.prepare.json', '.root_run_admission.json', '.run.json')]
OUT = T / 'outputs' / TAG
ROOT_THREAD = '01a07683-bc64-7463-8db7-9ee6243967d8'
GATES = [L / ('c08_h18_storage_' + name + '_review_r2.check.json')
         for name in ('debug2', 'short3')]
SHORT_PREP = L / 'c08_h18_storage_short3_GPU_r1.prepare.json'


def gates():
    before = []
    for path, profile, count, end in zip(GATES, ('debug2', 'short3'), (2, 3), (2000002, 2004001)):
        q = m.read(path); before.append(m.stat(path))
        m.need(q['passed'] and q['profile'] == profile and q['consumed_stats_unchanged'] and
               not q['physical_acceptance'] and q['observations']['actual_saved_states'] == count and
               q['observations']['actual_rows'] == count * 5000 and
               q['observations']['all5000IDs_per_state'] and q['observations']['all26_columns_exact'] and
               q['observations']['all_per_ID_endpoint_budgets_passed'] and
               q['observations']['independent_PRE_initial_and_native_final_S_checked'],
               'Passed genuine R2 short storage/native implementation gates required')
        before += [m.bind(q[k]) for k in ('source_run', 'native_receipt', 'observer_sidecar')]
        r, n = [m.read(q[k]['path']) for k in ('source_run', 'native_receipt')]
        m.need(r['passed'] and r['solver_completed'] and r['consumed_stats_unchanged'] and
               r['actual_steps'] == end and r['saved_frames'] == count and
               r['actual_exit'] == r['actual_Win32_exit'] == r['actual_tool_exit'] == 0 and
               r['ownership_failure'] is None and n['passed'] and n['consumed_stats_unchanged'] and
               n['source_run'] == q['source_run'] and n['reader_invocations'] == 1,
               'Actual completed short runs and their unique native reads required')
        before += [m.bind(r['actual_call'])] + [m.bind(n[k]) for k in
                   ('actual_call', 'native_completion', 'metadata', 'reader_build')]
        proof = q['no_feedback_byteproof']
        if profile == 'debug2':
            m.need(r['memcheck_zero_errors'] and not proof['required'] and
                   proof['Debug_is_not_Release_bit_truth'], 'Real Debug memcheck required; no Release bit claim')
        else:
            m.need(proof['required'] and proof['compared_records'] == 3 and
                   proof['genuine_new_header_samples'] == 3 and proof['genuine_control_header_samples'] == 91 and
                   proof['all22_and_actual_time_bytes_equal'] and proof['literal_layout_bytes_equal'] and
                   proof['all_signed_clock_row_bytes_equal'] and not proof['interpolation'] and
                   not proof['headers_rewritten'], 'Literal genuine first3 original no-feedback proof required')
    return before


def prepare():
    m.need(os.environ.get('CODEX_THREAD_ID') == ROOT_THREAD and not PREP.exists() and not OUT.exists(),
           'Actual root preparation only; existing output/preparation protected')
    config = T / 'configs' / (TAG + '_Def.xml')
    m.need(not config.exists(), 'Existing window configuration protected')
    before = gates() + [m.stat(p) for p in (Path(__file__), NOTE, Path(short.__file__),
                                          Path(executor.__file__), SHORT_PREP)]
    p = m.read(SHORT_PREP)
    m.need(p['passed'] and p['prepared_only'] and p['profile'] == 'short3' and
           p['configuration'] == 'Release' and p['consumed_stats_unchanged'], 'Actual passed short3 preparation required')
    prior_run = m.read(m.read(GATES[1])['source_run']['path'])
    m.need(all(p[k] == prior_run[k] for k in ('program', 'source_build', 'source_capture',
               'source_archive', 'source_pre_file', 'source_native')),
           'Window must use the exact observer/PRE that passed Release short3')
    before += [m.bind(p[k]) for k in ('program', 'source_build', 'source_capture', 'source_archive',
        'source_pre_file', 'source_run', 'source_native', 'configuration_xml', 'input_xml',
        'native_profile', 'control_original_plan')]
    before += [m.bind(q) for q in p['seed'] + p['runtime']]
    plan = m.table(p['control_original_plan']['path'])
    m.need(len(plan) == 91 and list(plan[0]) == ['part', 'completed_step', 'saved_step', 'time_s', 'dt_s'],
           'Original complete91 plan required')
    scalar, previous = float(p['actual_source_time_s']), 2000000
    for i, row in enumerate(plan):
        step = 2180000 if i == 90 else 2000001 + 2000 * i
        m.need(int(row['part']) == i and int(row['completed_step']) == step and
               int(row['saved_step']) == step - 1 and float(row['dt_s']) == .000005,
               'Original actual window step/clock layout differs')
        for _ in range(previous, step): scalar += .000005
        m.need(abs(float(row['time_s']) - scalar) <= 1e-14, 'Original scalar clock differs')
        previous = step
    m.verify(before); OUT.mkdir()
    definition = short.copy_exact(p['configuration_xml']['path'], config)
    prefix = OUT / Path(p['input_xml']['path']).stem
    seeds = [short.copy_exact(q['path'], OUT / Path(q['path']).name) for q in p['seed']]
    profile = short.copy_exact(p['native_profile']['path'], OUT / 'native_profile.csv')
    argv = [p['program']['path'], '-gpu:0', '-stable', '-mdbc_freeslip:1', str(prefix), str(OUT),
            '-dirdataout', 'data', '-svres', '-nsteps:2180000']
    prepared = dict(p)
    prepared.update(stage=TAG + '.prepare', profile='window', configuration_xml=definition,
        input_xml=seeds[0], seed=seeds, native_profile=profile, planned_steps=p['control_original_plan'],
        planned_rows=plan, new_updates=180000, global_nsteps_limit=2180000, expected_saved_frames=91,
        planned_actual_end_s=scalar, output=str(OUT), argv=argv, cwd=str(C),
        implementation_gates=[m.stat(q) for q in GATES], short_preparation=m.stat(SHORT_PREP),
        execution_script=m.stat(Path(__file__)), note=m.stat(NOTE), root_thread_id=ROOT_THREAD,
        root_direct_invoke_only=False, conditional_single_window_owner=True, terminal_queue_once=True,
        new_owner_or_notifier_created=False, consumed=before, consumed_stats_unchanged=True,
        pending_after_run=['Independent unique window91 native review',
                          'Independent R2 storage/whole91 no-feedback and physical interpretation'],
        solver_invocations=0, program_invocations=0, reader_invocations=0, GenCase_invocations=0,
        VTK_invocations=0, physical_acceptance=False, automatic_next_job=False)
    m.verify(before); m.save(PREP, prepared)


def notify_once():
    attempt, reply = [L / (TAG + suffix) for suffix in ('.queue_attempt.json', '.queue_result.json')]
    m.need(os.environ.get('CODEX_THREAD_ID') == ROOT_THREAD and not attempt.exists() and not reply.exists(),
           'One actual-root terminal delivery only; never resend/rearm')
    program = m.notifier_path()
    message = ('The one independently admitted original-physics C08 storage-observer GPU .90s window is terminal: '
        + str(RUN) + '. Read actual start/call/run/status/root admission and frozen program/source/PRE/input/91plan. '
        'Same WendlandH1.8/5us/AS.3n2.55/AV.1/keepfalse/NoPen/CompletedOnly,180000new/global2180000,not a repair. '
        'Original physical CUDA objects retained; exit0 is pending separate unique window91 native and R2 cumulative '
        'storage/no-feedback review. Check existing active/read receipts before one separately admitted native read. '
        'Preserve all22/6805/P0/J/kappa/FS/ledger/plane/clock/signed gates and all91 original records. '
        'Storage proxy is not fluid mass; Darcy remainder includes actual float-rate quantization. '
        'On completed-solver analysis failure repair offline only; on runtime failure preserve real exits, first error '
        'and last raw console, never invent unsaved time. No auto decoder/VTK/PRE/otherpsi/half/next solver. '
        'This direct owner queues once45s; uncertain delivery is never resent/rearmed and no watcher/self-test is added.')
    argv = [str(program) if program else 'codex', 'queue', '--thread', ROOT_THREAD, '--message', message]
    m.save(attempt, dict(stage=TAG, run=m.stat(RUN), thread=ROOT_THREAD,
        program=m.stat(program) if program else None, arguments=argv, attempts=1, timeout_s=45, do_not_resend=True))
    result = dict(stage=TAG, attempts=1, do_not_resend=True)
    try:
        m.need(program is not None, 'Current notifier absent; preserve terminal evidence without retry')
        q = subprocess.run(argv, cwd=C, capture_output=True, text=True, encoding='utf-8', errors='replace',
                           timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        result.update(actual_exit=q.returncode, status='queued' if q.returncode == 0 else 'queue_failed',
                      stdout=q.stdout, stderr=q.stderr)
    except subprocess.TimeoutExpired as error:
        result.update(status='delivery_uncertain', error=str(error))
    except Exception as error:
        result.update(status='queue_failed', error=str(error))
    m.save(reply, result)


def run():
    m.need(os.environ.get('CODEX_THREAD_ID') == ROOT_THREAD and not RUN.exists() and
           all(not (L / (TAG + suffix)).exists() for suffix in
               ('.call.json', '.log', '.start.json', '.status.json', '.queue_attempt.json', '.queue_result.json')),
           'Actual root single run only; existing complete/partial attempt protected')
    result = dict(stage=TAG, passed=False, solver_completed=False, physical_acceptance=False,
        native_review_pending=True, automatic_next_job=False, profile='window',
        solver_invocations=0, reader_invocations=0, VTK_invocations=0, GenCase_invocations=0,
        SHA_scans=0, unsaved_failure_time_reconstructed=False)
    before = []
    try:
        p, root = m.read(PREP), m.read(ADMISSION)
        m.need(p['passed'] and p['prepared_only'] and p['profile'] == 'window' and
               p['consumed_stats_unchanged'] and root['authorized'] and root['allowed_job'] == TAG and
               root['preparation'] == m.stat(PREP) and root['execution_script'] == m.stat(Path(__file__)) and
               root['note'] == m.stat(NOTE) and root['root_thread_id'] == ROOT_THREAD and
               root['implementation_gates'] == p['implementation_gates'] == [m.stat(q) for q in GATES] and
               root['single_window_only'] and root['terminal_queue_once'] and not root['automatic_native'],
               'Separate exact current-root window admission after short proof required')
        before = gates() + [m.stat(q) for q in (PREP, ADMISSION, Path(__file__), NOTE, Path(executor.__file__))]
        before += [m.bind(p[k]) for k in ('program', 'source_build', 'source_capture', 'source_archive',
            'source_pre_file', 'source_run', 'source_native', 'configuration_xml', 'input_xml', 'native_profile', 'planned_steps')]
        before += [m.bind(q) for q in p['seed'] + p['runtime']]
        m.need(OUT.is_dir() and p['output'] == str(OUT) and not (OUT / 'data').exists() and
               not (OUT / 'Run.out').exists() and not (OUT / 'C08StorageTrace.csv').exists() and
               p['global_nsteps_limit'] == 2180000 and p['new_updates'] == 180000 and
               p['expected_saved_frames'] == 91 and p['argv'][-1] == '-nsteps:2180000' and
               p['argv'][0] == p['program']['path'] and m.notifier_path() is not None,
               'Fresh original91 prepared observation and one actual terminal mechanism required')
        m.verify(before)
        owner = dict(pid=os.getpid(), created_epoch=psutil.Process().create_time(),
                     exe=psutil.Process().exe(), argv=psutil.Process().cmdline(), parent_pid=psutil.Process().ppid())
        m.save(L / (TAG + '.start.json'), dict(stage=TAG + '.start', owner=owner,
            preparation=m.stat(PREP), root_admission=m.stat(ADMISSION), program=p['program'],
            source_build=p['source_build'], source_capture=p['source_capture'], source_archive=p['source_archive'],
            source_pre_file=p['source_pre_file'], input_xml=p['input_xml'], planned_steps=p['planned_steps'],
            argv=p['argv'], solver_argv=p['argv'], actual_cwd=p['cwd'], consumed=before,
            automatic_next_job=False, physical_acceptance=False))
        result.update({k: p[k] for k in ('program', 'source_build', 'source_capture', 'source_archive',
            'source_pre_file', 'source_run', 'source_native', 'runtime', 'input_xml', 'seed', 'planned_steps',
            'native_profile', 'argv', 'actual_source_time_s', 'planned_actual_end_s', 'expected_saved_frames',
            'global_nsteps_limit', 'new_updates')})
        result.update(preparation=m.stat(PREP), root_admission=m.stat(ADMISSION), owner=owner,
            solver_argv=p['argv'], fixed_dt_s=.000005, AS_coefficient=.3, AS_exponent=2.55,
            original_AV=.1, group='psi0', kernel=2, hdp=1.8, keep_bed_overlap=False,
            observer_output_only=True, solver_invocations=1)
        result['actual_call'] = m.invoke(TAG, p['argv'], Path(p['cwd']))
        result['solver_completed'] = True  # Seal actual successful direct exit before any derived checks.
        call = m.read(result['actual_call']['path'])
        result.update(actual_exit=call['actual_Win32_exit'], actual_Win32_exit=call['actual_Win32_exit'],
                      actual_tool_exit=call['actual_Popen_wait_exit'], ownership_failure=call['ownership_failure'])
        text = (OUT / 'Run.out').read_text(encoding='utf-8-sig')
        m.need('Finished execution (code=0).' in text and '[Simulation INTERRUPTED' not in text and
               'certified same-material plastic schema/contract2' in text, 'Actual successful completion/schema2 import absent')
        d = executor.summary(OUT / 'Run.csv')
        parts = sorted((OUT / 'data').glob('Part_*.bi4'))
        m.need(int(d['Steps']) == 2180000 and int(d['PartFiles']) == 91 and int(d['PartsOut']) == 0 and
               'Wendland' in d['Configuration'] and [q.name for q in parts] == ['Part_%04d.bi4' % i for i in range(91)],
               'Actual complete original91 runtime coverage differs')
        sidecar = OUT / 'C08StorageTrace.csv'
        m.need(sidecar.is_file() and sidecar.stat().st_size > 0, 'Actual output-only sidecar absent')
        m.verify(before)
        result.update(passed=True, summary=d, actual_steps=2180000, saved_frames=91,
            consumed_stats_unchanged=True, observer_sidecar=m.stat(sidecar), Run_out=m.stat(OUT / 'Run.out'),
            Run_csv=m.stat(OUT / 'Run.csv'), output=str(OUT), PARTs=[m.stat(q) for q in parts])
    except Exception as error:
        result['first_failure'] = str(error)
    call_path = L / (TAG + '.call.json')
    if call_path.exists():
        call = m.read(call_path)
        result.update(actual_call=m.stat(call_path), actual_exit=call['actual_Win32_exit'],
            actual_Win32_exit=call['actual_Win32_exit'], actual_tool_exit=call['actual_Popen_wait_exit'],
            ownership_failure=call['ownership_failure'])
    if (OUT / 'Run.out').exists():
        text = (OUT / 'Run.out').read_text(encoding='utf-8-sig', errors='replace')
        hit = re.search(r'^Text: (.*)$', text, re.M)
        result.update(Run_out=m.stat(OUT / 'Run.out'), first_engine_exception_text=hit[1] if hit else None,
                      observed_saved_files=len(list((OUT / 'data').glob('Part_*.bi4'))))
    unchanged = False
    try: unchanged = all(m.stat(q['path']) == q for q in before)
    except Exception as error: result['terminal_stat_error'] = str(error)
    if not unchanged: result['passed'] = False
    result.update(consumed=before, consumed_stats_unchanged=unchanged,
                  last_original_console_line=m.base.last_part(OUT), unsaved_state_reconstructed=False)
    m.save(RUN, result)
    status = ('completed_pending_independent_native_and_storage' if result['passed'] else
              'completed_solver_runtime_review_failed') if result['solver_completed'] else 'failed_preserved_no_next_job'
    m.save(L / (TAG + '.status.json'), dict(stage=TAG, status=status, run=m.stat(RUN),
        automatic_next_job=False, physical_acceptance=False))
    if call_path.exists(): notify_once()
    return 0 if result['passed'] else (result.get('actual_exit') or 1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('prepare', 'run'), required=True)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    m.need(args.execution_authorized, 'Root full-read and separate preparation/run admission required')
    if args.phase == 'prepare': prepare()
    else: raise SystemExit(run())
