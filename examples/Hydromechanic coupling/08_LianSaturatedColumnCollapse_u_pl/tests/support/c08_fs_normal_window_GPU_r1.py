"""One root-admitted .9s psi0 normal-Taylor GPU window; no automatic native or next job."""
import argparse, json, os, re, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import c08_h18_as05_n5_r1 as control

matrix, base = control.matrix, control.base
T, C, L = control.T, control.C, control.L
need, read, stat, bind, save, invoke = matrix.need, matrix.read, matrix.stat, matrix.bind, matrix.save, matrix.invoke
TAG = 'c08_fs_normal_window_GPU_r1'; NOTE = T / 'notes' / (TAG + '.md')
CONFIG = T / 'configs' / (TAG + '_Def.xml'); PREP = L / (TAG + '.prepare.json'); ADMISSION = L / (TAG + '.admission.json')
BUILD = L / 'c08_fs_normal_gpu_Release_r1.build.json'; DEBUG = L / 'c08_fs_normal_gpu_Debug_r1.build.json'
PROGRAM = T / 'outputs/c08_fs_normal_gpu_Release_r1_build/DualSPHysics5.2_GEO_win64.exe'
INTERVENTION = 'free_surface_normal_taylor_projection'; THREAD = matrix.THREAD


def original_context():
    # Reuse only the completed AS05/PRE validator; no exponent5 preparation/run is called.
    original, prior, config, oldbuild, oldprogram, material, runtime, window, preload, consumed = control.original_context()
    consumed += [stat(q) for q in (Path(__file__), NOTE, Path(control.__file__))]
    return original, prior, config, material, runtime, window, preload, consumed


def candidate_context(original, consumed):
    release, debug = read(BUILD), read(DEBUG)
    for path, build, configuration in ((BUILD, release, 'Release'), (DEBUG, debug, 'Debug')):
        need(build['passed'] and build['configuration'] == configuration and build['intervention'] == INTERVENTION and build['consumed_stats_unchanged'] and build['actual_typed_exit_code'] == build['actual_Win32_exit'] == 0 and build['actual_link_objects'] == 113 and len(build['runtime']) == 7 and build['physical_objects_recompiled'] == 1 and build['original_mdbc_include_unchanged'] and build['exact_inverse_original_bytes'] and not build['public_source_changed'], 'Closed exact private GPU build required: ' + configuration)
        need(build['baseline_source_capture'] == original['source_capture'] and build['baseline_source_archive'] == original['source_archive'] and set(build['source_differences']) == {'src/source/JSphCpu.cpp', 'src/source/JSphGpu_ker.cu'}, 'Only the reviewed original-archive FS closure may differ')
        consumed.append(stat(path)); consumed += [bind(build[q]) for q in ('source_capture', 'source_archive', 'baseline_source_build', 'baseline_source_capture', 'baseline_source_archive', 'private_gpu_source', 'private_wall_include', 'candidate_object')]
        consumed += [bind(q) for q in build['runtime']] + [bind(q) for q in build['programs'].values()]
        for entry in build['calls']:
            consumed.append(bind(entry)); actual = read(entry['path'])
            need(actual['actual_Popen_wait_exit'] == actual['actual_Win32_exit'] == 0 and actual['ownership_failure'] is None, 'Actual private compile/link ownership must be closed')
    need(release['baseline_source_build'] == original['source_build'] and release['program'] == stat(PROGRAM) and release['programs'] == {'Normal': stat(PROGRAM)} and release['retained_public_objects'] == 112 and len(release['project_objects']['Normal']) == 113, 'Exact one-replacement Release solver required')
    need(set(debug['programs']) == {'Raw', 'Normal'} and debug['retained_public_objects'] == 111 and debug['shared_entry_object'] and all(len(debug['project_objects'][q]) == 113 for q in ('Raw', 'Normal')) and all(debug[q] == release[q] for q in ('source_capture', 'source_archive')), 'Root reviews must cover the same Debug pair and Release source')
    capture = read(release['source_capture']['path'])
    need(capture['intervention'] == INTERVENTION and capture['all_other_archived_bytes_identical'] and capture['exact_inverse_original_bytes'] and capture['archive'] == release['source_archive'] and set(capture['actual_differences']) == set(release['source_differences']), 'Sealed two-file source derivation required')
    return release, debug


def prepare():
    need(not CONFIG.exists() and not PREP.exists() and not (T / 'outputs' / TAG).exists() and not any(L.glob(TAG + '.*')), 'Existing preparation/output protected; no retry')
    original, prior, config, material, runtime, window, preload, consumed = original_context(); build, debug = candidate_context(original, consumed)
    with CONFIG.open('xb') as handle: handle.write(config.read_bytes())
    matrix.check_input(CONFIG, .5); need(CONFIG.read_bytes() == config.read_bytes(), 'Exact original AS05 configuration copy required'); matrix.verify(consumed)
    save(PREP, dict(stage=TAG + '.prepare', prepared_only=True, intervention=INTERVENTION, configuration=stat(CONFIG), original_configuration=stat(config), control_run=stat(control.CONTROL_RUN), candidate_build=stat(BUILD), debug_build=stat(DEBUG), program=build['program'], source_capture=build['source_capture'], source_archive=build['source_archive'], source_pre_file=stat(matrix.PRE), planned_steps=stat(matrix.PLAN), planned_global_end=matrix.END, expected_saved_frames=matrix.SAMPLES, AS_coefficient=.5, AS_exponent=3.825, numerical_input_identical_to_original=True, consumed=consumed, consumed_stats_unchanged=True, GenCase_invocations=0, solver_invocations=0, physical_acceptance=False))


def context():
    original, prior, config, material, runtime, window, preload, consumed = original_context(); build, debug = candidate_context(original, consumed)
    prepared, admission = read(PREP), read(ADMISSION)
    need(prepared['prepared_only'] and prepared['stage'] == TAG + '.prepare' and prepared['intervention'] == INTERVENTION and prepared['consumed_stats_unchanged'] and prepared['numerical_input_identical_to_original'] and prepared['configuration'] == stat(CONFIG) and prepared['original_configuration'] == stat(config) and prepared['control_run'] == stat(control.CONTROL_RUN) and prepared['candidate_build'] == stat(BUILD) and prepared['debug_build'] == stat(DEBUG), 'Exact separately prepared candidate required')
    need(CONFIG.read_bytes() == config.read_bytes(), 'Original AS05 XML must remain byte-identical'); matrix.check_input(CONFIG, .5)
    need(admission['passed'] and admission['allowed_job'] == TAG and admission['intervention'] == INTERVENTION and admission['root_scientific_admission'] is True and admission['unit_review_covers_exact_candidate'] is True and admission['prepared'] == stat(PREP) and admission['candidate_build'] == stat(BUILD) and admission['debug_build'] == stat(DEBUG) and admission['input_xml'] == stat(CONFIG) and admission['control_run'] == stat(control.CONTROL_RUN) and admission['source_pre_file'] == stat(matrix.PRE) and admission['planned_steps'] == stat(matrix.PLAN) and admission['planned_global_end'] == matrix.END and admission['expected_saved_frames'] == matrix.SAMPLES and admission['native_auto_authorized'] is False and admission['terminal_queue_once'] is True, 'Distinct root scientific admission after actual CPU/GPU control reviews required')
    for key in ('program', 'source_capture', 'source_archive'): need(bind(admission[key]) == bind(build[key]), 'Admitted candidate binding differs: ' + key)
    need(admission['debug_programs'] == debug['programs'], 'Reviewed Debug Raw/Normal program pair differs')
    consumed += [bind(admission[q]) for q in ('cpu_control_matrix_review', 'gpu_control_review')]
    need(admission['root_thread_id'] == os.environ.get('CODEX_THREAD_ID') == THREAD and matrix.notifier_path() is not None, 'Actual admitted root thread/current notifier required')
    consumed += [stat(q) for q in (PREP, ADMISSION, CONFIG)] + [bind(q) for q in prepared['consumed']]
    matrix.verify(consumed); matrix.old.old.idle(True)
    return original, prior, build, material, runtime, window, preload, consumed, admission


def notify_once(run_path):
    attempt, reply = L / (TAG + '.queue_attempt.json'), L / (TAG + '.queue_result.json')
    need(not attempt.exists() and not reply.exists() and os.environ.get('CODEX_THREAD_ID') == THREAD, 'One actual-root terminal queue only; never resend/rearm')
    program = matrix.notifier_path(); message = ('The single admitted private FS-normal C08 psi0 window is terminal: ' + str(run_path) + '. Read actual owned call/start/status/exits, root/owner admissions, candidate Release and Debug Raw/Normal sources/programs, CPU/GPU review bundles, original AS05 input/PRE/full91plan. Only private GPU free-surface normal Taylor closure changes; AS.5/n3.825, AV, theta, NoPen, materials and original5us/2180000/180k/91 remain. Runtime completion is not physical acceptance. Preserve failures/partials and actual last console; no unsaved state reconstruction. Root independently admits any native/physical review. No automatic decoder/VTK, solver retry, watcher, PRE/half/other-psi/control run or next job. Same-thread queue attempted once45s; uncertain delivery never resends/rearms.')
    argv = [str(program) if program else 'codex', 'queue', '--thread', THREAD, '--message', message]
    save(attempt, dict(stage=TAG, run=stat(run_path), thread=THREAD, program=stat(program) if program else None, arguments=argv, attempts=1, timeout_s=45, do_not_resend=True)); result = dict(stage=TAG, attempts=1, do_not_resend=True)
    try:
        need(program is not None, 'Current notifier unavailable; preserve terminal evidence without retry')
        done = subprocess.run(argv, cwd=C, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=45, creationflags=subprocess.CREATE_NO_WINDOW)
        result.update(actual_exit=done.returncode, status='queued' if done.returncode == 0 else 'queue_failed', stdout=done.stdout, stderr=done.stderr)
    except subprocess.TimeoutExpired as error: result.update(status='delivery_uncertain', error=str(error))
    except Exception as error: result.update(status='queue_failed', error=str(error))
    save(reply, result)


def run():
    out, run_path = T / 'outputs' / TAG, L / (TAG + '.run.json')
    need(not out.exists() and not any(q.name not in {PREP.name, ADMISSION.name} for q in L.glob(TAG + '.*')), 'Existing owner/partial protected; external launcher artifacts need another prefix')
    claim = L / (TAG + '.claim.json'); save(claim, dict(stage=TAG, owner_pid=os.getpid(), owner_created_epoch=psutil.Process().create_time(), single_attempt=True))
    consumed, phase = [], 'preflight'
    result = dict(stage=TAG, passed=False, solver_completed=False, intervention=INTERVENTION, physical_closure_change=True, physical_acceptance=False, native_review_pending=True, automatic_next_job=False, solver_invocations=0, GenCase_invocations=0, reader_invocations=0, PartVTK_invocations=0, SHA_scans=0)
    try:
        original, prior, build, material, runtime, window, preload, consumed, admission = context(); consumed.append(stat(claim)); out.mkdir(); prefix = out / TAG
        gen = next(q for q in runtime if Path(q['path']).name == 'GenCase_win64.exe'); phase = 'GenCase'; result['GenCase_invocations'] = 1
        result['GenCase_call'] = invoke(TAG + '.gencase', [gen['path'], str(CONFIG.with_suffix('')), str(prefix), '-save:all'], C)
        seed = Path(str(prefix) + '.xml'); actual = matrix.check_input(seed, .5, True); expected = ET.parse(bind(original['input_xml'])['path']).getroot()
        need(all(matrix.signature(actual.find(q)) == matrix.signature(expected.find(q)) for q in ('execution/special', 'execution/parameters', 'execution/constants', 'execution/particles')), 'Generated AS05 numerical sections changed')
        seeds = [stat(Path(str(prefix) + q)) for q in ('.xml', '.bi4', '_Normals.nbi4')]; consumed += seeds
        profile = out / 'native_profile.csv'; matrix.write_profile(profile, actual, .5, material)
        need(profile.read_bytes() == Path(original['native_profile']['path']).read_bytes(), 'Original17-key AS05 material profile must match'); consumed.append(stat(profile)); matrix.verify(consumed)
        argv = [str(PROGRAM), '-gpu:0', '-stable', '-mdbc_freeslip:1', str(prefix), str(out), '-dirdataout', 'data', '-svres', '-nsteps:' + str(matrix.END)]
        need(argv[1:4] == original['argv'][1:4] and argv[6:] == original['argv'][6:], 'Only executable and fresh input/output labels may change in argv')
        closure = dict(program=build['program'], source_build=stat(BUILD), source_capture=build['source_capture'], source_archive=build['source_archive'], runtime=build['runtime'], baseline_source_build=original['source_build'], baseline_source_capture=original['source_capture'], baseline_source_archive=original['source_archive'], source_pre_file=stat(matrix.PRE), source_run=prior['source_run'], source_native=prior['source_native'], candidate_build=stat(BUILD), debug_build=stat(DEBUG), debug_programs=admission['debug_programs'], cpu_control_matrix_review=admission['cpu_control_matrix_review'], gpu_control_review=admission['gpu_control_review'])
        owner = L / (TAG + '.owner_admission.json')
        save(owner, dict(stage=TAG, owner=dict(pid=os.getpid(), created_epoch=psutil.Process().create_time()), root_admission=stat(ADMISSION), **closure, source_native_call=prior['source_native_call'], source_material_profile=prior['source_material_profile'], source_physical_review=prior['source_physical_review'], input_xml=stat(seed), seed=seeds, planned_steps=stat(matrix.PLAN), planned_new_updates=180000, planned_global_end=matrix.END, expected_saved_frames=matrix.SAMPLES, Kernel=2, AS_coefficient=.5, AS_exponent=3.825, group='psi0', same_material_plastic_PRE=True, intervention=INTERVENTION, physical_closure_change=True, argv=argv, solver_argv=argv, consumed=consumed)); consumed.append(stat(owner))
        result.update(**closure, input_xml=stat(seed), seed=seeds, planned_steps=stat(matrix.PLAN), native_profile=stat(profile), owner_admission=stat(owner), argv=argv, group='psi0', kernel=2, kernel_name='Wendland', geometry_profile='bedroles', keep_bed_overlap=False, same_material_plastic_PRE=True, expected_source_handoff_schema=2, AS_coefficient=.5, AS_exponent=3.825, hdp=1.8, fixed_dt_s=matrix.DT)
        phase = 'solver'; result['solver_invocations'] = 1; result['actual_call'] = base.owned(TAG, argv, PROGRAM, False, stat(owner)); result.update(actual_exit=0, actual_Win32_exit=0, actual_tool_exit=0)
        phase = 'runtime_review'; result.update(matrix.old.old.output_checks(out, .5, window, preload))
        text = (out / 'Run.out').read_text(encoding='utf-8-sig'); need('Wendland' in result['summary']['Configuration'] and '[Simulation INTERRUPTED' not in text and 'GravityPreload: source material law=unified2; certified same-material plastic schema/contract2; native stress/kappa/J/p history retained.' in text, 'Actual kernel/completion/schema2 loader differs')
        matrix.verify(consumed); result.update(passed=True, solver_completed=True)
    except Exception as error: result.update(first_failure=str(error), failed_stage=phase)
    errors, unchanged = [], False; call_path = L / (TAG + '.call.json')
    try:
        if call_path.exists():
            call = read(call_path); result.update(actual_call=stat(call_path), actual_exit=call['actual_solver_Win32_exit'], actual_Win32_exit=call['actual_solver_Win32_exit'], actual_tool_exit=call['actual_Popen_wait_exit'], ownership_errors=call['ownership_errors'])
        raw = out / 'Run.out'
        if raw.exists():
            text = raw.read_text(encoding='utf-8-sig', errors='replace'); hit = re.search(r'^Text: (.+)$', text, re.M); parts = sorted((out / 'data').glob('Part_*.bi4'))
            result.update(Run_out=stat(raw), first_engine_exception_text=hit[1] if hit else None, reported_wall_rejection_lines=[q for q in text.splitlines() if q.startswith('DynamicPoreWall rejected:')], observed_saved_files=len(parts), PARTs=[stat(q) for q in parts])
        unchanged = all(stat(q['path']) == q for q in consumed); result['last_original_console_line'] = base.last_part(out)
    except Exception as error: errors.append(str(error))
    if errors or not unchanged: result['passed'] = False
    result.update(consumed=consumed, consumed_stats_unchanged=unchanged, terminal_observation_errors=errors, unsaved_state_reconstructed=False, unsaved_failure_time_reconstructed=False, original_target_completed_step=matrix.END, original_target_samples=matrix.SAMPLES, native_invocation_authorized_by_this_owner=False)
    save(run_path, result); base.publish(TAG, out, None, None, 'completed_pending_explicit_native_review' if result['solver_completed'] else 'failed_preserved_no_next_job')
    if call_path.exists(): notify_once(run_path)
    print(json.dumps(dict(run=str(run_path), solver_completed=result['solver_completed'], actual_exit=result.get('actual_exit'), physical_acceptance=False)), flush=True)
    return 0 if result['passed'] else (result.get('actual_exit') or 1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('action', choices=('prepare', 'run')); parser.add_argument('--execution-authorized', action='store_true'); args = parser.parse_args()
    need(args.execution_authorized, 'Author-only until root full-read and separately authorized prepare/run')
    prepare() if args.action == 'prepare' else exit(run())
