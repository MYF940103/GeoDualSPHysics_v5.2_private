"""Transparent offline Debug2 recovery review only; preserves the failed original run."""
import argparse
import json
import re
from pathlib import Path
import c08_h18_rv_implementation_review_r1 as old

T, L, typedcore = old.T, old.L, old.typedcore
need, read, stat, bind, entry, owned, same = old.need, old.read, old.stat, old.bind, old.entry, old.owned, old.same
PROFILES, ACTIVE, SOIL, BASE = old.PROFILES, old.ACTIVE, old.SOIL, old.BASE
TAG = 'c08_h18_rv_implementation_review_r2'
NOTE = T/'notes'/(TAG+'.md')


def check_native(profile, runpath, nativepath, recoverypath, consumed):
    count, end, configuration = PROFILES[profile]
    run, native, recovery = read(runpath), read(nativepath), read(recoverypath)
    need(profile == 'debug2', 'Only preserved Debug2 runtime recovery is exposed')
    need(same(runpath, L/'c08_h18_rv_debug2_GPU_r1.run.json')
         and same(recoverypath, L/'c08_h18_rv_debug2_GPU_r1.runtime_review_r1.check.json')
         and run['stage'] == 'c08_h18_rv_debug2_GPU_r1', 'Only the one named original failed wrapper/recovery pair is admitted')
    need(recovery['passed'] is True and recovery['consumed_stats_unchanged'] is True
         and entry(recovery, 'original_run') == stat(runpath), 'Passed independent runtime recovery must bind the unchanged original run')
    need(run['passed'] is False and run['solver_completed'] is True
         and run['first_failure'] == 'Actual schema2 RV policy differs'
         and run['first_engine_exception_text'] is None and run['actual_exit'] == run['actual_Win32_exit'] == run['actual_tool_exit'] == 0
         and run['ownership_failure'] is None and run['unsaved_state_reconstructed'] is False,
         'Only the exact known post-solver policy type-check failure is eligible')
    need(run['solver_completed'] and run['profile'] == profile and run['actual_steps'] == end and run['saved_frames'] == count and run['consumed_stats_unchanged']
         and run['RV_requested'] is (profile == 'debug2') and run['environment_override'] == {'C08_RV_H18': '1' if profile == 'debug2' else None}, 'Actual owned bounded solver result differs')
    need(native['passed'] and native['consumed_stats_unchanged'] and native['reader_invocations'] == 1 and entry(native, 'source_run') == stat(runpath), 'One independent native receipt bound to this exact run required')
    actual = entry(run, 'actual_call'); call = read(actual['path']); owned(call)
    need(call['child'] and entry(run, 'program')['path'] in [call['program'], *call['arguments']], 'Actual tool argv must contain the frozen physical program')
    startpath = Path(str(runpath).removesuffix('.run.json')+'.start.json'); start = read(startpath)
    adentry = entry(run, 'root_admission'); admission = read(adentry['path'])
    need(start['owner'] == run['owner'] and start['root_admission'] == adentry and start['argv'] == run['argv'] and start['solver_argv'] == run['solver_argv'] and start['environment_override'] == run['environment_override'], 'Original start/run owner/argv/environment differs')
    need(call['owner']['pid'] == run['owner']['pid'] and call['owner']['created_epoch'] == run['owner']['created_epoch'] and call['child']['parent_pid'] == run['owner']['pid'] and call['child']['argv'] == run['argv'], 'Actual child/owner creation/argv binding differs')
    need(admission['authorized'] and admission['allowed_job'] == run['stage'] and admission['profile'] == profile and admission['phase'] == 'run' and not admission['automatic_native'] and not admission['automatic_next_job'], 'Exact independent root run admission required')
    for key in ('program', 'source_build', 'source_capture', 'source_archive', 'source_pre_file', 'input_xml', 'planned_steps'):
        need(start[key] == run[key], 'Original start/run frozen input binding differs: '+key)
    if profile == 'debug2':
        need(call['actual_target'] and same(call['actual_target']['exe'], run['program']['path']) and call['actual_target_Win32_exit'] == 0, 'Actual Debug solver target handle/exit required')
        need('--tool' in call['arguments'] and call['arguments'][call['arguments'].index('--tool')+1] == 'memcheck' and '--error-exitcode' in call['arguments'] and call['arguments'][call['arguments'].index('--error-exitcode')+1] == '99', 'Actual memcheck invocation required')
        logfile = bind(call['log']); log = Path(logfile['path']).read_text(encoding='utf-8', errors='replace')
        errors = re.findall(r'ERROR SUMMARY: ([0-9,]+) errors', log)
        leaks = re.findall(r'LEAK SUMMARY: ([0-9,]+) bytes leaked in ([0-9,]+) allocations', log)
        need(errors and leaks and all(int(x.replace(',', '')) == 0 for x in errors) and all(int(x.replace(',', '')) == int(y.replace(',', '')) == 0 for x, y in leaks), 'Actual zero-error/zero-leak memcheck log required')
        need(recovery['memcheck_zero_errors_and_leaks'] is True and entry(recovery, 'memcheck_actual_call') == actual and call['actual_target']['parent_pid'] == call['child']['pid'] and call['actual_target']['argv'] == run['solver_argv'], 'Actual memcheck/target-parent/solver argv differs')
        consumed.append(logfile)
    ncallentry = entry(native, 'actual_call'); ncall = read(ncallentry['path']); owned(ncall)
    doneentry, metaentry = entry(native, 'native_completion'), entry(native, 'metadata')
    done, meta = read(doneentry['path']), read(metaentry['path']); root = Path(doneentry['path']).parent
    need(done['passed'] and done['stage'] == 'c08_h18_wend_native_r1.receiver' and done['samples'] == count and done['completed_steps'] == end and done['typed_arrays'] == 22 and done['typed_bytes_per_particle'] == 212, 'Actual original native profile/core differs')
    for key, value in {'actual_native_IDs_per_frame': ACTIVE, 'actual_fixed_IDs': 1805, 'soil_IDs': SOIL, 'ledger_checks': count*SOIL, 'P0_bits_checks': count*ACTIVE, 'nonempty_signed_intervals': count}.items():
        need(done[key] == value, 'Original complete native coverage differs: '+key)
    need(done['max_scalar_clock_error_s'] <= 1e-14 and done['max_ledger_relative_error'] <= 5e-13 and done['max_signed_dterror_s'] <= 1e-14 and done['FS23_pressure_checks'] > 0, 'Original native safety/clock/ledger/active-FS guard failed')
    need(meta['passed'] and meta['stage'] == 'c08_h18_rv_native_r1.metadata' and meta['profile'] == profile and meta['samples'] == count and meta['backend_argument'] == 'GPU' and meta['original_AV_private_keys_absent_headers'] == count and meta['residual_viscosity_proven_by_reader'] is False and meta['RV_program_owner_sidecar_review_required'] is True and meta['debug_profile_is_Release_bit_truth'] is False, 'RV-independent reader metadata required')
    planentry, preentry = entry(run, 'planned_steps'), entry(run, 'source_pre_file')
    need(same(preentry['path'], T/'outputs/c08_h18_wend_psi0_pre_r2/data/Part_1000.bi4'), 'Original certified PRE required')
    plan = typedcore.table(planentry['path']); need(len(plan) == count and list(plan[0]) == ['part', 'completed_step', 'saved_step', 'time_s', 'dt_s'], 'Original launch plan schema/count required')
    need([int(p['completed_step']) for p in plan] == list(range(BASE+1, end+1)), 'Only genuine first one/two updates admitted')
    args = ncall['arguments']
    need(len(args) == 8 and args[:3] == ['--receiver', profile, 'psi0'] and same(args[4], preentry['path']) and same(args[5], planentry['path']) and same(args[-1], root), 'Actual native profile/PRE/plan/output binding differs')
    rb = entry(native, 'reader_build'); reader = read(rb['path'])
    need(reader['passed'] and reader['consumed_stats_unchanged'] and reader['stage'] == 'c08_h18_rv_native_r1.build' and reader['actual_link_objects'] == 7 and not reader['JSph_objects_linked'] and same(ncall['program'], entry(reader, 'program')['path']), 'Actual frozen new seven-object reader required')
    buildentry = entry(run, 'source_build'); build = read(buildentry['path'])
    need(build['passed'] and build['configuration'] == configuration and build['consumed_stats_unchanged'] and build['actual_link_objects'] == 114 and build['retained_original_objects'] == 112 and build['private_objects'] == 2, 'Actual private configuration/build required')
    need(entry(build, 'program') == entry(run, 'program') and entry(build, 'source_capture') == entry(run, 'source_capture') and entry(build, 'source_archive') == entry(run, 'source_archive'), 'Actual frozen private source/program binding differs')
    source = entry(run, 'source_native'); sourcedone = read(source['path'])
    need(sourcedone['passed'] and sourcedone['certified_PRE'] and sourcedone['samples'] == 1001 and sourcedone['completed_steps'] == BASE, 'Original full qualified PRE receipt required')
    bundle = typedcore.typed(root, ACTIVE, count, consumed)
    for i, (clock, p) in enumerate(zip(bundle['clocks'], plan)):
        need(int(clock['part']) == int(p['part']) == i and int(clock['completed_step']) == int(p['completed_step']) and int(clock['saved_step']) == int(p['saved_step']) and float(clock['dt_s']) == float(p['dt_s']) == 5e-6 and abs(float(clock['time_s'])-float(p['time_s'])) <= 1e-14, 'Actual native clock/step/launch plan differs')
    need(set(build['private_sources']) == set(run['private_sources']) == {'host', 'CUDA', 'header'} and build['private_sources'] == run['private_sources'], 'Actual private host/CUDA/header source binding differs')
    consumed.extend(bind(q) for q in build['private_sources'].values())
    consumed.extend([stat(runpath), stat(nativepath), stat(recoverypath), stat(startpath), adentry, actual, ncallentry, doneentry, metaentry, planentry, preentry, rb, buildentry, source])
    consumed.extend(entry(run, key) for key in ('program', 'source_capture', 'source_archive', 'input_xml', 'Run_out'))
    return bundle, run, sourcedone, recovery


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile', choices=('debug2',), required=True)
    p.add_argument('--run-receipt', type=Path, required=True)
    p.add_argument('--runtime-recovery', type=Path, required=True)
    p.add_argument('--native-receipt', type=Path, required=True)
    p.add_argument('--execution-authorized', action='store_true')
    a = p.parse_args(); need(a.execution_authorized, 'Author-only until root full read and independent offline admission')
    check = L/'c08_h18_rv_debug2_implementation_review_r2.check.json'
    need(not check.exists(), 'Existing complete/failed transparent review protected')
    consumed = []; result = dict(stage=TAG, profile='debug2', passed=False, solver_invocations=0, native_invocations=0, build_invocations=0, GPU_actions=0, SHA_scans=0, physical_acceptance=False)
    try:
        consumed = [stat(Path(__file__)), stat(NOTE), stat(Path(old.__file__)), stat(old.NOTE), stat(Path(typedcore.__file__)), stat(Path(typedcore.core.__file__))]
        bundle, original, source, recovery = check_native(a.profile, a.run_receipt, a.native_receipt, a.runtime_recovery, consumed)
        # Only these output-stat aliases are added to the inspection view.
        # Memcheck is checked separately; never change original passed status.
        aliases = ('rv_policy', 'rv_sidecar', 'rv_manufactured')
        view = dict(original)
        for key in aliases:
            need(key not in original, 'Original run unexpectedly already has a recovered output alias')
            view[key] = entry(recovery, key)
        need(set(view)-set(original) == set(aliases) and all(view[key] == value for key, value in original.items())
             and view['passed'] is False, 'Transparent inspection view must preserve every original field')
        proof = old.on_debug(bundle, view, source, consumed)
        need(all(stat(q['path']) == q for q in consumed), 'Bound runtime/native/source/sidecar changed during offline review')
        result.update(passed=True, original_run=stat(a.run_receipt), original_run_passed=False,
            original_solver_completed=True, original_first_failure=original['first_failure'],
            original_run_unchanged=True, runtime_recovery=stat(a.runtime_recovery), native_receipt=stat(a.native_receipt),
            native_receipt_source_run_still_original_failed_run=True, inspection_view_added_fields=list(aliases),
            original_passed_promoted_or_fake_run_created=False, proof=proof,
            consumed=consumed, consumed_stats_unchanged=True, original_numeric_thresholds_changed=False,
            Debug_Release_bit_equivalence_claimed=False, manufactured_budget_basis_reconstructed_from_neighbors=False,
            clumping_repair_or_physical_acceptance_claimed=False)
    except Exception as error:
        result.update(first_failure=str(error), consumed=consumed, partial_outputs_preserved=True)
        raise
    finally:
        with check.open('x', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2); f.write('\n')


if __name__ == '__main__':
    main()
