"""One separately admitted .90s HG GPU window; one direct-owner terminal queue only."""
import argparse
import csv
import math
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import c08_h18_hg_gpu_jobs_r1 as short

m, T, C, L = short.m, short.T, short.C, short.L
TAG = 'c08_h18_hg_window_GPU_r1'
SCRIPT = Path(__file__).resolve()
NOTE = T / 'notes/c08_h18_hg_window_r1.md'
HELPER_NOTE = T / 'notes/c08_h18_hg_gpu_jobs_r1.md'
THREAD, DT, PRESTEP = short.THREAD, short.DT, short.PRESTEP
BUILD = L / 'c08_h18_hg_gpu_Release_r1.build.json'
CODEX = Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1106.51428-win32-x64/bin/windows-x86_64/codex.exe')
CODEX_STAT = dict(path=str(CODEX), bytes=373698352, mtime_ns=1794391544005116300)
GATES = (L / 'c08_h18_hg_gpu_off1_r1.check.json',
         L / 'c08_h18_hg_gpu_debug2_r1.check.json',
         L / 'c08_h18_hg_gpu_forcecheck_r1.check.json')
OUT = T / 'outputs' / TAG
CONFIG = T / 'configs' / (TAG + '_Def.xml')


def paths():
    suffixes = dict(prep='.prepare.json', prepare_admission='.root_prepare_admission.json',
                    run_admission='.root_run_admission.json', start='.start.json', call='.call.json',
                    log='.log', run='.run.json', status='.status.json', completed='.solver_completed.json',
                    queue='.queue_attempt.json', reply='.queue_result.json')
    return {key: L / (TAG + suffix) for key, suffix in suffixes.items()}


def admission(path, phase):
    a = m.read(path)
    m.need(a['authorized'] and a['allowed_job'] == TAG and a['profile'] == 'window' and a['phase'] == phase
           and a['execution_script'] == m.stat(SCRIPT) and a['note'] == m.stat(NOTE)
           and a['source_build'] == m.stat(BUILD)
           and a['root_thread_id'] == os.environ.get('CODEX_THREAD_ID') == THREAD
           and a['single_window_only'] and a['terminal_queue_once'] and a['codex'] == CODEX_STAT
           and not a['automatic_native'] and not a['automatic_next_job'] and not a.get('watcher', False)
           and a['implementation_gates'] == [m.stat(q) for q in GATES],
           'Separate frozen current-root single-window prepare/run admission required')
    m.bind(a['codex'])
    m.bind(a['physical_decision'])
    return a


def implementation_gates():
    before = [m.stat(q) for q in GATES]
    off, debug, force = map(m.read, GATES)
    m.need(off['passed'] and not off['physical_acceptance']
           and off['all22_and_actual_time_record_bytes_equal'] and off['byte_comparisons'] == 1442668
           and off['signed_clock_row_all_columns_equal'] and off['layout_equal']
           and off['HG_sidecars_absent'] and off['source_OFF_no_allocation_or_kernel_scope']
           and not off['source_recomputed'], 'Genuine OFF22/time/signed/layout regression required')
    m.need(debug['passed'] and not debug['physical_acceptance'] and debug['actual_updates'] == 2
           and debug['actual_force_stages'] == 4 and debug['actual_material_scalar_bit_checks'] == 140000
           and debug['all_returned_material_statuses_elastic'] and not debug['plastic_GPU_path_qualified']
           and debug['phase_rows'] == 4 and debug['native_all_22_and_original_safety_passed']
           and debug['memcheck_zero_errors_and_leaks'],
           'Actual Debug2 material/native/memcheck qualification required; plastic remains unqualified')
    for proof in (off, debug):
        before += [m.bind(proof[key]) for key in ('run', 'actual_native_call', 'native_completion')]
        run, call, native = [m.read(proof[key]['path']) for key in ('run', 'actual_native_call', 'native_completion')]
        m.need(run['passed'] and run['solver_completed'] and run['consumed_stats_unchanged']
               and run['actual_exit'] == run['actual_Win32_exit'] == run['actual_tool_exit'] == 0
               and call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0
               and call['ownership_failure'] is None and native['passed'],
               'Actual original smoke/native process receipts required')
        before += [m.bind(q) for q in proof['files']]
    m.need(force['passed'] and force['actual_scalar_comparisons'] == 10000
           and force['physical_updates'] == force['solver_invocations'] == force['reader_invocations'] == 0
           and not force['physical_acceptance'], 'Actual independent first-n force reference required')
    before += [m.bind(force[key]) for key in ('actual_call', 'completion', 'build')]
    before += [m.bind(q) for q in force['files']]
    call, done = [m.read(force[key]['path']) for key in ('actual_call', 'completion')]
    m.need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0
           and call['ownership_failure'] is None and done['passed'] and done['nodes'] == 5000
           and done['scalar_comparisons'] == 10000 and done['failed_scalars'] == 0
           and done['physical_updates'] == done['solver_invocations'] == done['reader_invocations'] == 0
           and not done['physical_acceptance'], 'Owned completed finite-budget force comparison required')
    return before


def prepare():
    p, before = paths(), []
    m.need(not OUT.exists() and not CONFIG.exists()
           and all(not p[key].exists() for key in ('prep', 'start', 'call', 'log', 'run', 'status', 'completed', 'queue', 'reply')),
           'Existing complete/partial window is protected; no repeat preparation')
    try:
        a = admission(p['prepare_admission'], 'prepare')
        before = implementation_gates()
        cr, cp = L / (short.CONTROL + '.run.json'), L / (short.CONTROL + '.prepare.json')
        cn, cv = L / 'c08_h18_as03_n255_native_r1.check.json', L / 'c08_h18_as03n255_review_r1.check.json'
        original, prepared, native, review = map(m.read, (cr, cp, cn, cv))
        m.need(original['passed'] and original['solver_completed'] and original['consumed_stats_unchanged']
               and original['actual_exit'] == original['actual_Win32_exit'] == original['actual_tool_exit'] == 0
               and original['actual_steps'] == 2180000 and original['saved_frames'] == 91
               and original['AS_coefficient'] == .3 and original['AS_exponent'] == 2.55
               and original['hdp'] == 1.8 and original['fixed_dt_s'] == DT and not original['keep_bed_overlap']
               and prepared['prepared_only'] and prepared['consumed_stats_unchanged']
               and native['passed'] and native['consumed_stats_unchanged'] and native['reader_invocations'] == 1
               and review['analysis_complete'] and review['consumed_stats_unchanged'],
               'Retained original91 seed/native/review and unchanged physics required')
        before += [m.stat(q) for q in (SCRIPT, NOTE, Path(short.__file__), HELPER_NOTE, p['prepare_admission'], cr, cp, cn, cv)]
        before += [m.bind(a[key]) for key in ('codex', 'physical_decision')]
        before += [m.bind(original[key]) for key in ('program', 'source_build', 'source_capture', 'source_archive',
            'source_pre_file', 'source_run', 'source_native', 'input_xml', 'native_profile', 'planned_steps', 'actual_call')]
        source = m.read(original['source_native']['path'])
        m.need(source['passed'] and source['certified_PRE'] and source['expected_handoff_schema'] == 2
               and source['same_material_plastic_PRE'] and source['completed_steps'] == PRESTEP
               and source['samples'] == 1001 and source['soil_IDs'] == 5000 and source['fixed_IDs'] == 2060
               and source['declared_Kernel_XML_CSV'] == 2,
               'Original certified same-material schema2 PRE required, not a new source solve')
        bp, build, entries = short.private_build('off1', original)
        m.need(bp == BUILD, 'Only the new original-physics Release HG build is allowed')
        before += entries
        definition = m.bind(prepared['configuration'])
        before.append(definition)
        tree = ET.parse(original['input_xml']['path']).getroot()
        params = {q.get('key'): q.get('value') for q in tree.findall('execution/parameters/parameter')}
        m.need(len(params) == len(tree.findall('execution/parameters/parameter'))
               and all(float(params[key]) == value for key, value in dict(Kernel=2, DtFixed=DT,
                   TimeMax=10.9, TimeOut=.01, SoilHourglassXi=0, NoPenetration=1, SavePosDouble=1).items())
               and all(short.f32(params[key]) == short.f32(value) for key, value in dict(Visco=.1,
                   ArtificialStressCoef=.3, ArtificialStressExp=2.55).items()),
               'Unchanged AS03/Wendland/5us physical input required')
        gravity = tree.find('execution/special/gravitypreload')
        m.need(gravity is not None and Path(gravity.get('statefile')).resolve() == Path(original['source_pre_file']['path']).resolve()
               and gravity.get('elastic_source') == gravity.get('keep_bed_overlap') == 'false'
               and gravity.get('release_mkbound') == '2' and float(gravity.get('time')) == 10,
               'Original schema2 PRE/normal bedroles retirement contract differs')
        material = m.table(original['native_profile']['path'])
        m.need(len(material) == 17 and all(list(q) == ['key', 'value'] for q in material)
               and len({q['key'] for q in material}) == 17, 'Original seventeen-key material profile required')
        oldrows = m.table(original['planned_steps']['path'])
        job = dict(steps=tuple(int(q['completed_step']) for q in oldrows), updates=180000, frames=91)
        rows, clocks, end = short.clock_plan(job, source['actual_end_s'], oldrows)
        m.need(job['steps'][0] == 2000001 and job['steps'][-1] == 2180000,
               'Original .90s first-post/end global plan differs')
        for actual, old in zip(rows, oldrows):
            m.need(all(int(actual[key]) == int(old[key]) for key in ('part', 'completed_step', 'saved_step'))
                   and float(old['dt_s']) == DT and abs(actual['time_s'] - float(old['time_s'])) <= 1e-14,
                   'Actual scalar +=dt replay differs from a retained planned save')
        seed = Path(original['input_xml']['path']).with_suffix('')
        m.need(len(original['seed']) == 3, 'Original generated seed triple required')
        seeds = []
        for suffix in ('.xml', '.bi4', '_Normals.nbi4'):
            path = Path(str(seed) + suffix)
            entry = next(q for q in original['seed'] if Path(q['path']).resolve() == path.resolve())
            seeds.append(m.bind(entry))
            before.append(entry)
        m.verify(before)
        OUT.mkdir()
        copied_definition = short.copy_exact(definition['path'], CONFIG)
        copied_seeds = [short.copy_exact(q['path'], OUT / Path(q['path']).name) for q in seeds]
        copied_profile = short.copy_exact(original['native_profile']['path'], OUT / 'native_profile.csv')
        argv = [build['program']['path'], '-gpu:0', '-stable', '-mdbc_freeslip:1',
                str(OUT / seed.name), str(OUT), '-dirdataout', 'data', '-svres', '-nsteps:2180000']
        m.verify(before)
        m.save(p['prep'], dict(stage=TAG + '.prepare', passed=True, prepared_only=True,
            profile='window', configuration='Release', program=build['program'], source_build=m.stat(BUILD),
            source_capture=build['source_capture'], source_archive=build['source_archive'],
            baseline_source_capture=build['baseline_source_capture'], private_sources=build['private_sources'],
            runtime=build['runtime'], source_pre_file=original['source_pre_file'], source_run=original['source_run'],
            source_native=original['source_native'], control_run=m.stat(cr), control_native=m.stat(cn),
            control_review=m.stat(cv), control_original_plan=original['planned_steps'],
            configuration_xml=copied_definition, input_xml=copied_seeds[0], seed=copied_seeds,
            native_profile=copied_profile, planned_steps=original['planned_steps'], planned_rows=rows,
            save_source_clocks_s=clocks, actual_source_time_s=source['actual_end_s'], planned_actual_end_s=end,
            global_nsteps_limit=2180000, new_updates=180000, expected_saved_frames=91, fixed_dt_s=DT,
            HG_requested=True, environment_override={short.ENVIRONMENT: '1'}, argv=argv, cwd=str(C), output=str(OUT),
            implementation_gates=[m.stat(q) for q in GATES], physical_decision=a['physical_decision'], codex=a['codex'],
            execution_script=m.stat(SCRIPT), note=m.stat(NOTE), root_prepare_admission=m.stat(p['prepare_admission']),
            consumed=before, consumed_stats_unchanged=True, seed_copied_byte_identical=True,
            generated_basename_preserved=seed.name, old91_plan_unchanged=True, native_review_pending=True,
            HG_sidecar_review_pending=True, plastic_GPU_window_review_pending=True, GenCase_invocations=0,
            solver_invocations=0, reader_invocations=0, VTK_invocations=0, SHA_scans=0,
            automatic_next_job=False, terminal_queue_once=True, watcher=False, physical_acceptance=False))
    except Exception as error:
        if not p['prep'].exists():
            m.save(p['prep'], dict(stage=TAG + '.prepare', passed=False, first_failure=str(error),
                consumed=before, partial_outputs_preserved=True, solver_invocations=0, automatic_retry=False))
        raise


def terminal_once(p, prep):
    m.need(not p['queue'].exists() and not p['reply'].exists(), 'Terminal attempt already exists; never resend')
    message = ('The single admitted C08 energy-normalized plastic-HG .90s GPU window is terminal: '
        + str(p['run']) + '. Read original start/call/run/status/solver_completed and root admissions, '
        'actual owned Win32/Popen exits, original schema2 PRE/program/source/input/91 scalar plan. '
        'AS.3/n2.55/AV.1/WendlandH1.8/fixed5us/keepfalse/fixed-plane/CompletedOnly remain; '
        '180000new updates/global2180000/91 planned saves, not physical acceptance. HG is new directed-row '
        'energy-normalized memory with full LS adjoint, same committed en for n/h and per-stage actual '
        'six-stress/kappa comparison. Prior Debug2 was entirely elastic, not plastic qualification. '
        'Independent native22/6805/P0/J/kappa/FS/ledger/clock/signed and genuine new HG phase/work/history '
        'review remain pending; check existing/active readers first and never decode twice. Generic native '
        'success is not HG correctness, diagnostic budgets are not outward/coupled-energy certificates. '
        'Preserve actual failures/partials/first cause/last raw console; never reconstruct unsaved time or '
        'rerun a completed solver. No automatic native/VTK/PRE/otherpsi/half/next solver. '
        'This direct owner queues once45s; timeout may already have delivered, never resend/rearm or add watcher/selftest.')
    argv = [str(CODEX), 'queue', '--thread', THREAD, '--message', message]
    m.save(p['queue'], dict(stage=TAG, run=m.stat(p['run']), status=m.stat(p['status']),
        thread=THREAD, program=prep['codex'], arguments=argv, attempts=1, timeout_s=45,
        only_completion_mechanism='same_direct_run_owner', do_not_resend=True))
    reply = dict(stage=TAG, attempts=1, do_not_resend=True)
    try:
        m.need(os.environ.get('CODEX_THREAD_ID') == THREAD, 'Actual current-root terminal thread changed')
        m.need(prep['codex'] == CODEX_STAT, 'Frozen current-root notifier contract differs')
        m.bind(prep['codex'])
        call = subprocess.run(argv, cwd=C, capture_output=True, text=True, encoding='utf-8',
            errors='replace', timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        reply.update(actual_exit=call.returncode, status='queued' if call.returncode == 0 else 'queue_failed',
                     stdout=call.stdout, stderr=call.stderr)
    except subprocess.TimeoutExpired as error:
        reply.update(status='delivery_uncertain', error=str(error))
    except Exception as error:
        reply.update(status='queue_failed', error=str(error))
    m.save(p['reply'], reply)


def run():
    p, before, prep, call = paths(), [], None, None
    m.need(all(not p[key].exists() for key in ('start', 'call', 'log', 'run', 'status', 'completed', 'queue', 'reply')),
           'Existing owned run/completion/queue/partial protected; never rearm or rerun')
    result = dict(stage=TAG, passed=False, solver_completed=False, profile='window', configuration='Release',
        solver_invocations=0, solver_launch_attempts=0, native_review_pending=True, HG_sidecar_review_pending=True,
        plastic_GPU_window_review_pending=True, GenCase_invocations=0, reader_invocations=0, VTK_invocations=0,
        SHA_scans=0, automatic_next_job=False, terminal_queue_once=True, watcher=False,
        physical_acceptance=False, unsaved_state_reconstructed=False)
    try:
        prep = m.read(p['prep'])
        a = admission(p['run_admission'], 'run')
        m.need(prep['passed'] and prep['prepared_only'] and prep['consumed_stats_unchanged']
               and prep['execution_script'] == m.stat(SCRIPT) and prep['note'] == m.stat(NOTE)
               and a['preparation'] == m.stat(p['prep']) and a['implementation_gates'] == prep['implementation_gates']
               and a['physical_decision'] == prep['physical_decision'] and a['codex'] == prep['codex'],
               'Independent exact prepared-window run admission required')
        before = implementation_gates()
        before += [m.stat(q) for q in (SCRIPT, NOTE, Path(short.__file__), HELPER_NOTE, p['prep'], p['run_admission'])]
        before += [m.bind(prep[key]) for key in ('program', 'source_build', 'source_capture', 'source_archive',
            'baseline_source_capture', 'source_pre_file', 'source_run', 'source_native', 'control_run',
            'control_native', 'control_review', 'control_original_plan', 'configuration_xml', 'input_xml',
            'native_profile', 'planned_steps', 'physical_decision', 'codex')]
        before += [m.bind(q) for q in prep['seed'] + prep['runtime'] + list(prep['private_sources'].values())]
        program, argv = Path(prep['program']['path']), list(prep['argv'])
        m.need(OUT.is_dir() and not (OUT / 'data').exists() and not (OUT / 'Run.out').exists()
               and argv[0] == str(program) and argv[-1] == '-nsteps:2180000'
               and prep['global_nsteps_limit'] == 2180000 and prep['new_updates'] == 180000
               and prep['expected_saved_frames'] == 91 and prep['HG_requested']
               and prep['environment_override'] == {short.ENVIRONMENT: '1'},
               'Fresh original-input single .90s window required')
        for proc in psutil.process_iter(['pid', 'exe']):
            try:
                m.need(not proc.info['exe'] or Path(proc.info['exe']).resolve() != program.resolve(),
                       'Exact private Release program is already active; do not duplicate')
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        env = dict(os.environ)
        for key in list(env):
            if key.upper() == short.ENVIRONMENT:
                env.pop(key)
        env[short.ENVIRONMENT] = '1'
        proc = psutil.Process()
        owner = dict(pid=proc.pid, created_epoch=proc.create_time(), exe=proc.exe(), argv=proc.cmdline(), parent_pid=proc.ppid())
        m.verify(before)
        m.save(p['start'], dict(stage=TAG + '.start', owner=owner, preparation=m.stat(p['prep']),
            root_admission=m.stat(p['run_admission']), program=prep['program'], source_build=prep['source_build'],
            source_capture=prep['source_capture'], source_archive=prep['source_archive'], source_pre_file=prep['source_pre_file'],
            input_xml=prep['input_xml'], planned_steps=prep['planned_steps'], argv=argv, solver_argv=argv,
            cwd=prep['cwd'], environment_override=prep['environment_override'], consumed=before,
            automatic_native=False, automatic_next_job=False, terminal_queue_once=True, watcher=False,
            physical_acceptance=False))
        result.update({key: prep[key] for key in ('program', 'source_build', 'source_capture', 'source_archive',
            'baseline_source_capture', 'private_sources', 'runtime', 'source_pre_file', 'source_run', 'source_native',
            'control_run', 'control_native', 'control_review', 'control_original_plan', 'configuration_xml',
            'input_xml', 'seed', 'native_profile', 'planned_steps', 'actual_source_time_s', 'planned_actual_end_s',
            'global_nsteps_limit', 'new_updates', 'expected_saved_frames', 'environment_override',
            'implementation_gates', 'physical_decision', 'codex')})
        result.update(owner=owner, preparation=m.stat(p['prep']), root_admission=m.stat(p['run_admission']),
            argv=argv, solver_argv=argv, cwd=prep['cwd'], output=str(OUT), fixed_dt_s=DT, HG_requested=True,
            solver_launch_attempts=1)
        result['actual_call'] = m.invoke(TAG, argv, Path(prep['cwd']), env=env)
    except Exception as error:
        result['first_failure'] = str(error)
    if p['call'].exists():
        result['actual_call'] = m.stat(p['call'])
        call = m.read(p['call'])
        solver = call.get('child')
        result.update(actual_exit=call.get('actual_Win32_exit'), actual_Win32_exit=call.get('actual_Win32_exit'),
            actual_tool_exit=call.get('actual_Popen_wait_exit'), actual_tool_Win32_exit=call.get('actual_Win32_exit'),
            ownership_failure=call.get('ownership_failure'), solver_invocations=1 if solver else None, solver_identity=solver)
        result['solver_identity_matches'] = bool(solver and prep and
            Path(solver['exe']).resolve() == Path(prep['program']['path']).resolve()
            and solver.get('creation_filetime_100ns', 0) > 0 and solver.get('parent_pid') == result['owner']['pid']
            and solver.get('argv') == prep['argv'] and call['owner']['pid'] == result['owner']['pid']
            and abs(call['owner']['created_epoch'] - result['owner']['created_epoch']) <= 5e-6)
    try:
        m.need(call is not None and result.get('solver_identity_matches')
               and result['actual_exit'] == result['actual_Win32_exit'] == 0
               and result['ownership_failure'] is None, 'Actual owned native solver normal exit is unproved')
        text = (OUT / 'Run.out').read_text(encoding='utf-8-sig')
        m.need('Finished execution (code=0).' in text and '[Simulation INTERRUPTED' not in text
               and 'certified same-material plastic schema/contract2' in text, 'Original normal contract2 completion required')
        # Seal the genuine solve BEFORE any summary/coverage/sidecar/native review.
        done = dict(stage=TAG + '.solver_completed', solver_completed=True, actual_call=result['actual_call'],
            original_start=m.stat(p['start']), owner=result['owner'], solver_identity=result['solver_identity'],
            program=prep['program'], source_build=prep['source_build'], source_capture=prep['source_capture'],
            source_archive=prep['source_archive'], source_pre_file=prep['source_pre_file'], input_xml=prep['input_xml'],
            planned_steps=prep['planned_steps'], actual_solver_Win32_exit=result['actual_Win32_exit'],
            actual_tool_exit=result['actual_tool_exit'], Run_out=m.stat(OUT / 'Run.out'),
            target_coverage_review_pending=True, HG_sidecar_review_pending=True, native_review_pending=True,
            no_solver_retry=True, physical_acceptance=False)
        m.save(p['completed'], done)
        result.update(solver_completed=True, solver_completion=m.stat(p['completed']), Run_out=done['Run_out'])
        row = short.summary(OUT / 'Run.csv')
        frames = sorted((OUT / 'data').glob('Part_*.bi4'))
        m.need(int(row['Steps']) == 2180000 and int(row['PartFiles']) == 91
               and int(row['PartsOut']) == int(row['PartsOutRhop']) == int(row['PartsOutVel']) == 0
               and [q.name for q in frames] == ['Part_%04d.bi4' % i for i in range(91)],
               'Actual completed global-step/frame/no-exclusion coverage differs')
        m.need(math.isfinite(float(row['PhysicalTime'])) and abs(float(row['PhysicalTime']) - prep['planned_actual_end_s']) <= .00000051,
               'Rounded Run.csv endpoint differs; native exact clocks remain pending')
        result.update(summary=row, actual_steps=int(row['Steps']), saved_frames=len(frames),
            Run_csv=m.stat(OUT / 'Run.csv'), PARTs=[m.stat(q) for q in frames],
            particle_data_files=[m.stat(q) for q in sorted((OUT / 'data').iterdir()) if q.is_file()],
            Run_csv_endpoint_is_rounded_not_native_clock=True)
        m.need(result['actual_tool_exit'] == result['actual_tool_Win32_exit'] == 0 and 'first_failure' not in result,
               'Actual Popen/Win32 invocation must also pass')
        m.verify(before)
        result.update(passed=True, consumed_stats_unchanged=True)
    except Exception as error:
        result.setdefault('first_failure', str(error))
    if (OUT / 'Run.out').exists():
        text = (OUT / 'Run.out').read_text(encoding='utf-8-sig', errors='replace')
        first = re.search(r'^Text: (.*)$', text, re.M)
        result.update(Run_out=m.stat(OUT / 'Run.out'), first_engine_exception_text=first[1] if first else None,
            observed_saved_files=len(list((OUT / 'data').glob('Part_*.bi4'))))
    if call and Path(call['log']['path']).is_file():
        raw = Path(call['log']['path']).read_text(encoding='mbcs', errors='replace')
        lines = [line for line in raw.splitlines() if re.match(r'^Part_\d+\s', line)]
        result.update(console_log=m.bind(call['log']), last_original_console_PART_line=lines[-1] if lines else None)
    try:
        unchanged = all(m.stat(q['path']) == q for q in before)
    except Exception as error:
        unchanged = False
        result['terminal_stat_error'] = str(error)
    if not unchanged:
        result['passed'] = False
    result.update(consumed=before, consumed_stats_unchanged=unchanged)
    if result['solver_launch_attempts'] and call is None:
        result.update(solver_invocations=None, solver_launch_outcome_not_handle_proven=True)
    if not result['passed']:
        result['surviving_process_observations'] = short.observe_survivors(call)
    m.save(p['run'], result)
    m.save(p['status'], dict(stage=TAG, status='completed_pending_unique_native_and_HG_review' if result['passed'] else
        'completed_solver_review_failed' if result['solver_completed'] else 'failed_preserved_no_retry',
        run=m.stat(p['run']), automatic_native=False, automatic_next_job=False, terminal_queue_once=True,
        watcher=False, physical_acceptance=False))
    if call is not None and result['solver_launch_attempts'] == 1:
        terminal_once(p, prep)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'run'))
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    m.need(args.execution_authorized, 'Separate current-root prepare/run admission required')
    if args.phase == 'prepare':
        prepare()
    else:
        raise SystemExit(run())
