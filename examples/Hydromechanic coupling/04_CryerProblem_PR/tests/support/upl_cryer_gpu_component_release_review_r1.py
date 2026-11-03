"""Offline review of one fresh, directly owned Release r4 component call. No producer is run."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import types

T = Path(__file__).resolve().parents[1]
STAGE = 'upl_cryer_gpu_component_release_review_r1'
TAG = 'upl_cryer_gpu_component_Release_probe_r4'
OUT = T / 'outputs' / TAG
PINS = {
    'support/upl_cryer_gpu_component_review_r3.py': (23110, '0abbc8b4a1d0a7140ebc51ef121ec3707e0faf992263ae2edbec7111c19b4ce9'),
    'notes/upl_cryer_gpu_component_review_r3.json': (9776, '61e16422595a1629512976d43d44a7bb71f4f43e4784e018de29a26459883221'),
    'logs/upl_cryer_gpu_component_Debug_probe_r3_recovery_review_r1.check.json': (145508, '32a3d38fc1fad4c09fed03ad0370ff0cd72c12365cce93720f0d45232734dd71'),
    'logs/upl_cryer_gpu_component_Release_r2.helper.json': (473516, '2dcef1be2f179304942f77ce4196ce281ade5577bbe9456f6dc3bc245da0e7dd'),
}


def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def definitions():
    path = T / 'support/upl_cryer_gpu_component_review_r3.py'
    raw = path.read_bytes()
    if (len(raw), hashlib.sha256(raw).hexdigest()) != PINS['support/upl_cryer_gpu_component_review_r3.py']:
        raise ValueError('Pinned original GPU definitions changed')
    gpu = types.ModuleType('frozen_gpu_review_definitions')
    gpu.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), gpu.__dict__)  # Definitions only, never its review() or main().
    h = gpu.definitions()  # Its pinned, unchanged CPU metadata and CSV definitions only.
    for name, (size, digest) in PINS.items():
        h.bind(dict(path=str(T / name), bytes=size, sha256=digest))
    return gpu, h


def debug_prerequisite(gpu, h):
    need, bind, adopt, readjson = h.need, h.bind, h.adopt, h.readjson
    entry = adopt(T / 'logs/upl_cryer_gpu_component_Debug_probe_r3_recovery_review_r1.check.json')
    prior = readjson(bind(entry))
    expected = dict(stage='upl_cryer_gpu_component_recovery_review_r1', passed=True, configuration='Debug',
        win32_tool_exit0=True, win32_target_exit0=True, target_exit_independently_captured=True,
        independent_final_rehash_performed=True, component_completion_verified=True,
        memcheck_errors=0, memcheck_leaks=0, memcheck_zero_errors_and_leaks=True,
        initialization_metadata_only=True, no_particle_snapshots_or_exclusions=True,
        original_owner_exit_unknown=True, original_owner_final_input_output_seal_available=False,
        original_PowerShell_LASTEXITCODE_available=False, original_run_or_call_fabricated=False,
        original_run_or_call_read_or_created=False, existing_Release_gate_satisfied_by_alias=False,
        summary_rows=6, sample_rows=48, physical_acceptance=False, public_3D_admitted=False)
    need(all(prior.get(k) == v for k, v in expected.items()) and
         math.isfinite(prior['max_checked_ratio']) and 0 <= prior['max_checked_ratio'] <= 1,
         'Exact passed independent Win32 Debug recovery prerequisite required')
    entries = [entry] + prior['inputs'] + prior['files'] + [prior[k] for k in
        ('helper', 'source_build', 'program', 'completion', 'memcheck_log', 'live_capture_opened', 'live_capture_result')]
    entries += [prior['native_exit_records'][k] for k in ('tool', 'target')]
    for e in entries:
        bind(e)
    log = gpu.textlog(bind(prior['memcheck_log']))
    errors = re.findall(r'ERROR SUMMARY:\s*(\d+)\s+errors\b', log)
    leaks = re.findall(r'LEAK SUMMARY:\s*(\d+)\s+bytes leaked in\s+(\d+)\s+allocations\b', log)
    need(errors and leaks and all(int(v) == 0 for v in errors) and
         all(int(a) == int(b) == 0 for a, b in leaks), 'Prior actual Debug memlog must remain zero errors and leaks')
    return entry, prior, entries


def own_call(h, prior_e, prior_entries):
    need, bind, adopt, readjson = h.need, h.bind, h.adopt, h.readjson
    source = adopt(T / 'logs' / (TAG + '.run.json'))
    run = readjson(bind(source))
    expected = dict(stage='upl_cryer_gpu_component_release_run_r1', tag=TAG, passed=True, configuration='Release',
        kind='non_advancing_private_GPU3D_component', typed_owned_target_exit0=True,
        component_target_exit_independently_captured=True, sanitizer_used=False,
        basic_completion_verified=True, deep_component_review_completed=False,
        frozen_build_program_inputs_runtime_unchanged=True, independent_final_rehash_performed=True,
        direct_owner_no_scheduler=True, original_Debug_owner_exit_unknown=True,
        Debug_typed_LASTEXITCODE_alias_created=False, live_production_sources_frozen_by_this_run=False,
        canonical_programs_rechecked=False, caller_reconstructed_device_or_neighbor_proof=False,
        observer_initialization_validated=False, feedback_initialization_validated=False,
        CPU_GPU_or_Debug_Release_0ULP_compared=False, solver_trajectory_started=False,
        automatic_follow_up=False, public_3D_admitted=False, physical_acceptance=False)
    need(all(run.get(k) == v for k, v in expected.items()) and run['debug_recovery_review'] == prior_e and
         all(run[k] is None for k in ('component_call_failure', 'basic_analysis_failure', 'post_binding_failure', 'memcheck_log')),
         'Only a successful new directly owned Release call seal is accepted')
    need(run['inputs'] and len({str(Path(e['path']).resolve()).casefold() for e in run['inputs']}) == len(run['inputs']),
         'Owner input seal must be nonempty with unique paths')
    for e in run['inputs'] + run['files']:
        bind(e)
    start_e = run['owner_start']
    need(Path(start_e['path']).resolve() == (T / 'logs' / (TAG + '.start.json')).resolve(), 'New start path differs')
    start = readjson(bind(start_e))
    need(start['stage'] == 'upl_cryer_gpu_component_release_start_r1' and start['tag'] == TAG and
         start['configuration'] == 'Release' and type(start['owner_pid']) is int and start['owner_pid'] > 0 and
         type(start['owner_parent_pid']) is int and start['owner_parent_pid'] > 0 and
         start['owner_executable'] and start['owner_command_line'] and
         stamp(start['owner_creation_utc']) <= stamp(start['started_utc']) and
         start['helper'] == run['helper'] and start['program'] == run['program'] and
         start['source_build'] == run['source_build'] and start['debug_recovery_review'] == prior_e and
         start['direct_owner_no_scheduler'] is True and start['native_call_started_by_start_record'] is False and
         start['physical_acceptance'] is False, 'Actual fresh direct owner identity and start differ')
    own = [adopt(T / name) for name in ('support/upl_cryer_gpu_component_release_run_r1.ps1',
        'notes/upl_cryer_gpu_component_release_run_r1.json', 'support/upl_cryer_gpu_component_release_review_r1.py',
        'notes/upl_cryer_gpu_component_release_review_r1.json')]
    need(start['owner_script'] == own[0] and all(e in run['inputs'] for e in
         own + prior_entries + [start_e, run['helper'], run['source_build'], run['program']]),
         'Owner must bind its actual authors, new prerequisite, start and frozen target inputs')
    need(Path(run['call']['path']).resolve() == (T / 'logs' / (TAG + '.call.json')).resolve(), 'New call path differs')
    call = h.owned(run['call'])  # This is the real new Release call; never a reconstructed Debug call.
    need(call['stage'] == 'upl_cryer_gpu_component_release_call_r1' and call['tag'] == TAG and
         call['configuration'] == 'Release' and call['owner_start'] == start_e and
         call['program'] == call['target_program'] == run['program'] and
         call['arguments'] == call['target_arguments'] == run['arguments'] == start['arguments'] and
         call['working_directory'] == start['working_directory'] and
         call['component_call'] is True and call['actual_solver_call'] is False and call['sanitizer_used'] is False and
         call['target_exit_independently_captured'] is True and call['requested_OpenMP_threads'] == 1 and
         call['launcher_priority_during_call'] == 'Normal' and call['child_priority_independently_observed'] is False and
         call['physical_acceptance'] is False and stamp(start['started_utc']) <= stamp(call['started_utc']) <= stamp(call['ended_utc']) and
         Path(call['log']['path']).resolve() == (T / 'logs' / (TAG + '.log')).resolve(),
         'Real direct Release target, exact arguments, chronology or typed-exit attribution differs')
    return source, run, start_e, call


def helper_closure(h, run, call):
    # Same retained helper/build/object/header/library/runtime gates as the pinned original review.
    need, bind, readjson = h.need, h.bind, h.readjson
    helper_e = run['helper']; helper = readjson(bind(helper_e))
    need(Path(helper_e['path']).resolve() == (T / 'logs/upl_cryer_gpu_component_Release_r2.helper.json').resolve() and
         helper['stage'] == 'upl_cryer_gpu_component_build_r2' and helper['passed'] is True and
         helper['status'] == 'frozen_cryer_GPU_component_linked_not_run' and helper['configuration'] == 'Release' and
         helper['kind'] == 'component' and helper['actual_headers_archived_not_live'] is True and
         helper['frozen_build_program_inputs_runtime_unchanged'] is True and helper['exact_link_closure_verified'] is True and
         helper['program_run'] is False and helper['production_build_executed'] is False and
         helper['GPU_non_main_objects'] == 110 and helper['link_object_count'] == 111 and len(helper['objects']) == 110 and
         len(helper['retained_build_objects111']) == 111 and len(helper['source_snapshots265']) == 265 and
         len(helper['libraries']) == 18 and len(helper['runtime']) == 4, 'Sealed Release GPU110+1/265/library18/runtime4 helper required')
    for key in ('inputs', 'author_files', 'source_snapshots265', 'actual_project_headers', 'objects', 'retained_build_objects111', 'libraries', 'tools'):
        for e in helper[key]:
            bind(e)
    for key in ('program', 'source_build', 'compiler_dependency_record', 'helper_object', 'documentation_snapshot', 'case_readme_snapshot', 'neutral_include', 'retained_compiler_recipe'):
        bind(helper[key])
    need(run['source_build'] == helper['source_build'] and run['program'] == helper['program'] == call['target_program'] and
         helper['program']['bytes'] == 19750912 and helper['program']['sha256'] == '9a1fd4f81a4b38cee1dae015f30c74c3866987f7a28fe24e50f8f338475d2036',
         'Actual sealed Release build/target attribution differs')
    build = readjson(bind(helper['source_build'])); snapshots = [v['snapshot'] for v in build['source_snapshot']]
    need(build['stage'] == 'upl_damp_build_r2' and build['passed'] is True and build['configuration'] == 'Release' and
         len(build['objects']) == 111 and build['objects'] == helper['retained_build_objects111'] and
         snapshots == helper['source_snapshots265'] and len(snapshots) == 265 and
         build['documentation_snapshot']['snapshot'] == helper['documentation_snapshot'] and
         build['case_readme_snapshot']['snapshot'] == helper['case_readme_snapshot'], 'Selected archived source/build closure differs')
    for pair in build['source_snapshot'] + [build['documentation_snapshot'], build['case_readme_snapshot']]:
        need(all(pair['original'][k] == pair['snapshot'][k] for k in ('bytes', 'sha256')), 'Recorded as-of-build archive identity differs')
    project = readjson(bind(build['project_call']))
    need(project['direct_native_call'] is True and project['owned_call_exited'] is True and
         project['typed_LASTEXITCODE_captured_immediately'] is True and type(project['exit_code']) is int and
         project['exit_code'] == 0 and project.get('invocation_failure') is None and project['program'] == build['build_tool'],
         'Actual selected project build was not owned typed0')
    for e in (build['build_tool'], build['program'], build['log'], build['binlog']):
        bind(e)
    expected = [e for e in build['objects'] if Path(e['path']).name.lower() != 'main.obj']
    need(expected == helper['objects'] and len(expected) == 110 and len({Path(e['path']).name.lower() for e in expected}) == 110,
         'Exact non-main object membership differs')
    h.owned(helper['compile_call']); link = h.owned(helper['link_call'])
    linked = [str(Path(a).resolve()).casefold() for a in link['arguments'] if a.lower().endswith('.obj')]
    need(len(linked) == len(set(linked)) == 111 and set(linked) ==
         {str(Path(e['path']).resolve()).casefold() for e in expected + [helper['helper_object']]}, 'Actual linker110+1 membership differs')
    need([str(Path(a).resolve()).casefold() for a in link['arguments'] if a.lower().endswith('.lib')] ==
         [str(Path(e['path']).resolve()).casefold() for e in helper['libraries']], 'Actual ordered18 library arguments differ')
    dep = readjson(bind(helper['compiler_dependency_record']))['Data']; archive = Path(helper['archived_header_include_root']).resolve()
    includes = {str(Path(v).resolve()).casefold() for v in dep['Includes']}; neutral = helper['neutral_include']
    headers = {str(Path(v).resolve()).casefold() for v in dep['Includes'] if Path(v).resolve().parent == archive}
    need(Path(dep['Source']).resolve() == (T / 'support/upl_cryer_gpu_component_r2.cpp').resolve() and
         neutral['sha256'] == '9f6668bfe3d1bbcca7c45c58809f7062c21fcb46baae76f0a2a1b0ef3ca56d38' and
         str(Path(neutral['path']).resolve()).casefold() in includes and
         headers == {str(Path(e['path']).resolve()).casefold() for e in helper['actual_project_headers']} and
         all(e in snapshots for e in helper['actual_project_headers']), 'Actual source/single neutral/archived-header dependencies differ')
    support_roots = ((T / 'support').resolve(), (T.parent.parent / '02_TerzaghiConsolidation_q0_PR/tests/support').resolve())
    authored = [v for v in dep['Includes'] if Path(v).resolve().parent in support_roots]
    need(len(authored) == 1 and Path(authored[0]).resolve() == Path(neutral['path']).resolve(), 'Extra authored dependency beyond single neutral include')
    for pair in helper['runtime']:
        need(pair['original'] in [v['copy'] for v in build['runtime']] and
             all(pair['original'][k] == pair['copy'][k] for k in ('bytes', 'sha256')), 'Runtime must derive from selected frozen build copy')
        bind(pair['original']); bind(pair['copy'])
    note_e = next(e for e in helper['author_files'] if Path(e['path']).name == 'upl_cryer_gpu_component_r2.json')
    declaration = readjson(bind(note_e))['retained_input_provenance']; xml, seed = (T.parent / declaration[k] for k in ('runtime', 'seed'))
    for path, name in ((xml, 'runtime'), (seed, 'seed')):
        bind(dict(path=str(path), bytes=declaration[name + '_bytes'], sha256=declaration[name + '_sha256']))
    target = ['--input', str(xml), '--out', str(OUT)]
    need(call['arguments'] == target and Path(call['working_directory']).resolve() == Path(helper['program']['path']).resolve().parent,
         'Exact retained input/fresh output/runtime directory invocation differs')
    return helper_e, helper, snapshots


def payload(gpu, h, run):
    # These exact completion and numerical conditions are retained from the pinned original review.
    need, bind, adopt, readjson = h.need, h.bind, h.adopt, h.readjson
    files = [adopt(path) for path in sorted(OUT.rglob('*')) if path.is_file()]
    need(len(files) == len(run['files']) == 8 and
         {Path(e['path']).resolve().relative_to(OUT.resolve()).as_posix() for e in files} == gpu.LEAVES and
         {str(Path(e['path']).resolve()).casefold() for e in files} ==
         {str(Path(e['path']).resolve()).casefold() for e in run['files']}, 'Whole8-file membership differs; no PART trajectory allowed')
    parsed = [h.metadata(OUT / 'data/Part_Head.ibi4', 'JPartDataHead'), h.metadata(OUT / 'data/PartOut_000.obi4', 'JPartOutBi4')]
    done_e = adopt(OUT / 'completion.json'); need(done_e == run['completion'], 'Own Release completion binding differs')
    done = readjson(bind(done_e))
    values = dict(stage='upl_cryer_gpu_component_r2', passed=True, native_count=37173, fixed_dummy_count=8,
        total_native_count=37181, actual_force_calls=6, complete_rate_calls_from_force=6, explicit_complete_rate_calls=0,
        soil_reference_checks=223038, sample_rows=48, summary_rows=6, actual_physical_steps=0, actual_time_s=0,
        manual_J_pool_added8B=4, manual_validity_pool_added4B=2, observer_Init_guard_bypassed_by_fixture=True,
        feedback_Init_guard_bypassed_by_fixture=True, observer_initialization_validated=False,
        feedback_initialization_validated=False, legacy_GPU_initialization_validated=True, manual_J1_theta0_installed=True,
        packed_and_double_support_intervals_unambiguous=False, upper_support_edges_enclosed=True,
        zero_distance_ambiguity_rejected=True, reference_conditioned_on_observed_C_and_Ace=True,
        conditional_C_moment_uses_GPU_geometry_fastmath_budget=True, CUDA11p7_published_not_guaranteed_math_envelope_assumed=True,
        neighbor_search_independently_reimplemented=False, declared_input_bytes_restored=True, whole_object_restored=False,
        no_Run_ComputeStep_SaveData_restart=True, raw_LoadAce_gate_accounted=True, CPU_GPU_0ULP_compared=False,
        matched_formal_stabilization=False, physical_acceptance=False, public_3D_admitted=False)
    need(all(done.get(k) == v for k, v in values.items()) and math.isfinite(done['minimum_dummy_soil_distance_m']) and
         done['minimum_dummy_soil_distance_m'] > .009, 'Original zero-step/manual-init/conditional-math completion differs')
    maximum = h.csv_check(OUT)  # Unchanged finite/count/identity and eight-channel budgets, ratio <= 1.
    summary, samples = gpu.csv_rows(OUT / 'summary.csv'), gpu.csv_rows(OUT / 'samples.csv')
    for row in summary:
        probe = int(row['probe'])
        need(float(row['C_moment_abs_residual_max']) >= 0 and float(row['packed_double_displacement_difference_max_m']) >= 0,
             'Invalid GPU geometry diagnostic')
        if probe < 4:
            need(float(row['Ace_norm_max_m_s2']) == float(row['load_norm_max_m_s2']) == 0, 'Original zero-total-stress gate differs')
        if probe == 0:
            need(float(row['pdot_abs_max_Pa_s']) == 0, 'Original strict constant-pressure zero gate differs')
        if probe >= 4:
            need(int(row['raw_LoadAce_store_gate_open']) + int(row['raw_LoadAce_store_gate_closed']) == 37173,
                 'Conditional raw-load gate count differs')
        if probe == 4:
            need(float(row['Ace_norm_max_m_s2']) > 0 and float(row['load_norm_max_m_s2']) > 0, 'Original confinement-only source did not activate')
    for row in samples:
        need(int(row['packed_neighbors']) > 0 and int(row['double_neighbors']) > 0 and
             0 <= int(row['poscell_w_UINT_BITS']) < 2**32 and float(row['C_residual']) >= 0 and
             float(row['packed_double_dr_difference_m']) >= 0, 'GPU packed/reference diagnostics differ')
    totals = gpu.support_edges(summary, samples, done, need)
    return dict(completion=done_e, files=files, metadata=parsed, max_checked_ratio=maximum,
                support_edge_pair_counts=totals, kernel_edge_grad_bound_max=done['kernel_edge_grad_bound_max'])


def review(gpu, h):
    prior_e, prior, prior_entries = debug_prerequisite(gpu, h)
    source, run, start_e, call = own_call(h, prior_e, prior_entries)
    helper_e, helper, snapshots = helper_closure(h, run, call)
    checked = payload(gpu, h, run)
    producers = [e for e in snapshots if Path(e['path']).name in
        {'JSph.cpp', 'JPartDataHead.cpp', 'JPartOutBi4Save.cpp', 'JBinaryData.cpp', 'JBinaryData.h'}]
    h.need(len(producers) == 5, 'Archived metadata producer definitions missing')
    return dict(configuration='Release', tag=TAG, source_run=source, source_call=run['call'], owner_start=start_e,
        helper=helper_e, source_build=helper['source_build'], program=helper['program'], owned_target_program=call['program'],
        prior_Debug_recovery_review=prior_e, prior_Debug_win32_tool_exit0=True, prior_Debug_win32_target_exit0=True,
        prior_Debug_memcheck_zero_errors_and_leaks=True, prior_Debug_memcheck_log=prior['memcheck_log'],
        prior_Debug_owner_exit_unknown=True, prior_Debug_owner_final_seal_available=False,
        prior_Debug_PowerShell_LASTEXITCODE_available=False, Debug_typed_LASTEXITCODE_alias_created=False,
        original_r3_owner_or_reviewer_modified=False, old_reviewer_main_or_review_called=False,
        typed_owned_target_exit0=True, target_exit_independently_captured=True, direct_target_owned_exit0=True,
        direct_owner_no_scheduler=True, memcheck_executed_for_Release=False,
        component_completion_verified=True, summary_rows=6, sample_rows=48, metadata_producer_sources=producers,
        no_particle_snapshots_or_exclusions=True, particle_payload_bytes=0, excluded_particle_payload_count=0,
        upper_support_edges_enclosed=True, zero_distance_ambiguity_rejected=True,
        initialization_metadata_only=True, observer_initialization_validated=False,
        feedback_initialization_validated=False, whole_object_restored=False, conditional_fastmath_envelope_assumed=True,
        historical_live_production_source_originals_rehashed=False, canonical_project_programs_rehashed=False,
        caller_reconstructed_neighbor_or_device_proof=False, CPU_GPU_or_Debug_Release_0ULP_compared=False,
        solver_trajectory_started=False, public_3D_admitted=False, physical_acceptance=False,
        automatic_follow_up=False, programs_executed_by_reviewer=0, **checked)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    if not parser.parse_args().execution_authorized:
        raise ValueError('Root must read the whole new Release reviewer before explicit offline execution')
    target = T / 'logs' / (TAG + '_release_review_r1.check.json')
    if target.exists():
        raise ValueError('Fresh-only Release review output; preserve every prior check')
    if any(not (T / 'logs' / (TAG + suffix)).is_file() for suffix in ('.start.json', '.call.json', '.run.json')):
        raise ValueError('New direct Release owner is incomplete; no offline check is created')
    h = None
    result = dict(stage=STAGE, passed=False, configuration='Release', tag=TAG, physical_acceptance=False,
                  public_3D_admitted=False, programs_executed_by_reviewer=0)
    try:
        gpu, h = definitions()
        h.adopt(__file__); h.adopt(T / 'notes/upl_cryer_gpu_component_release_review_r1.json')
        result.update(review(gpu, h))
        for expected in list(h.BOUND.values()):
            h.need(h.entry(expected['path']) == expected, 'Consumed file changed during independent final rehash')
        result.update(passed=True, independent_final_rehash_performed=True, failure=None)
    except Exception as exc:
        result['failure'] = str(exc)
    result['inputs'] = list(h.BOUND.values()) if h else []
    result['limits'] = ('Conditional, non-advancing Release arithmetic and initialization metadata only. '
        'The prior Debug prerequisite is a separate pinned Win32 recovery and memcheck review; its missing original PowerShell exit and final seal remain unavailable. '
        'This Release call has its own directly captured typed target exit. Published CUDA11.7 fast-math bounds remain assumed, not universal guarantees. '
        'Upper support ambiguity is enclosed by the original zero reference and derived gradient bound; zero-distance ambiguity is rejected. '
        'No independent all-soil device/neighbor reconstruction, public3D/init/integration/trajectory/physical acceptance, or CPU-GPU/Debug-Release0ULP claim. '
        'No producer, decoder, build, scheduler, queue, retry or next stage is launched by this reviewer.')
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    if not result['passed']:
        raise ValueError('Release review failed; retain ' + str(target) + ': ' + str(result['failure']))
    print(target)


if __name__ == '__main__':
    main()
