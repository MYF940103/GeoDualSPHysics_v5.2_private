"""Offline Debug r3 recovery review using actual Win32 exits, never synthetic old call/run receipts."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import types

T = Path(__file__).resolve().parents[1]
STAGE = 'upl_cryer_gpu_component_recovery_review_r1'
TAG = 'upl_cryer_gpu_component_Debug_probe_r3'
OUT = T / 'outputs' / TAG
XML = T.parent / 'CaseCryerProblem_PR_symc_nu030_out/CaseCryerProblem_PR_symc_nu030.xml'
TOOL = Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/compute-sanitizer/compute-sanitizer.exe')
PINS = {
    'support/upl_cryer_gpu_component_review_r3.py': (23110, '0abbc8b4a1d0a7140ebc51ef121ec3707e0faf992263ae2edbec7111c19b4ce9'),
    'notes/upl_cryer_gpu_component_review_r3.json': (9776, '61e16422595a1629512976d43d44a7bb71f4f43e4784e018de29a26459883221'),
    'support/upl_cryer_live_exit_r1.py': (9176, 'abab0800a6556151a60e6fa2681217544bb2792b53a6602e14db4f569005fc6e'),
    'notes/upl_cryer_live_exit_r1.json': (1580, '6aa7b7a5543a85d117be909ef12e6faa9765ca43d4ec962af1611510974398fa'),
    'logs/upl_cryer_live_exit_r1.opened.json': (6205, '1e2151e126f357dd99ee2cc6423b3cd5fd4c960524e5a5eea2b3854f8c19d9f9'),
    'logs/' + TAG + '.start.json': (2070, '922ce4bdbafbd0fea4495d309281444b20b7b219e54e9bb84a1840c77f10d29c'),
    'logs/' + TAG + '.task_attempt.json': (6141, 'ee2da979fe997df73662f50788920efe649429da7250cb5dc210ca73faa631b1'),
    'notes/upl_cryer_gpu_component_run_r3.json': (4033, '909e8b9398f15254eefe98f4b03e16f3ce20b362a48bfdd013faa72de33694c2'),
}
CREATION = {'tool': (52096, 57736, 134381503125468415), 'target': (43136, 52096, 134381503127367523)}


def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)


def definitions():
    path = T / 'support/upl_cryer_gpu_component_review_r3.py'
    raw = path.read_bytes()
    if (len(raw), hashlib.sha256(raw).hexdigest()) != PINS['support/upl_cryer_gpu_component_review_r3.py']:
        raise ValueError('Pinned original GPU reviewer definitions changed')
    gpu = types.ModuleType('frozen_gpu_review_definitions')
    gpu.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), gpu.__dict__)  # Definitions only; never call its review() or main().
    h = gpu.definitions()  # Its pinned, unchanged CPU metadata and CSV definitions only.
    for name, (size, digest) in PINS.items():
        h.bind(dict(path=str(T / name), bytes=size, sha256=digest))
    return gpu, h


def provenance(h):
    need, bind, adopt, readjson = h.need, h.bind, h.adopt, h.readjson
    start_e = adopt(T / 'logs' / (TAG + '.start.json'))
    start = readjson(bind(start_e))
    need(start['stage'] == 'upl_cryer_gpu_component_start_r3' and start['configuration'] == 'Debug' and
         start['owner_pid'] == 57736 and start['owner_parent_pid'] == 3408 and
         start['owner_creation_utc'] == '2026-11-03T03:31:45.6326490Z' and
         start['fresh_attempt_after_incomplete_r2'] is True and start['old_r2_exit_reconstructed'] is False and
         start['prior_native_completion_adopted'] is False and start['native_call_started_by_start_record'] is False and
         start['physical_acceptance'] is False, 'Original fresh Debug start identity differs')
    need(Path(start['owner_script']['path']).resolve() == (T / 'support/upl_cryer_gpu_component_run_r3.ps1').resolve(),
         'Original owner source differs')
    bind(start['owner_script'])
    task = readjson(bind(adopt(T / 'logs' / (TAG + '.task_attempt.json'))))
    run_note = adopt(T / 'notes/upl_cryer_gpu_component_run_r3.json')
    need(task['stage'] == 'upl_cryer_gpu_component_task_attempt_r3' and
         task['task_name'] == 'GeoDualSPH_upl_cryer_component_Debug_r3_20261103' and
         start['owner_script'] in task['inputs'] and run_note in task['inputs'],
         'Original task author bindings for the owner source and note differ')
    # The original owner also consumed its note and component author files before its lost final seal.
    for path in (T / 'notes/upl_cryer_gpu_component_run_r3.json', T / 'support/upl_cryer_gpu_component_r2.cpp',
                 T / 'notes/upl_cryer_gpu_component_r2.json'):
        adopt(path)
    audit_e = start['interruption_audit']
    audit = readjson(bind(audit_e))
    expected = (T.parent.parent / '02_TerzaghiConsolidation_q0_PR/tests/logs/upl_mid_gpu_interruption_r1.check.json').resolve()
    need(Path(audit_e['path']).resolve() == expected and audit_e['bytes'] == 1200299 and
         audit_e['sha256'] == '15c9b4fb9e23f8e89c540db9ccf2aadb0b68ff48934109613bf63f86716c8160' and
         audit['stage'] == 'upl_mid_gpu_interruption_r1' and audit['interruption_audited'] is True and
         audit['all_observed_owned_processes_absent'] is True and audit['real_exit_code'] is None and
         audit['typed_exit_evidence_available'] is False and audit['normal_completion_or_failure_exit_invented'] is False and
         audit['old_full_gate_preserved'] is True and audit['physical_acceptance'] is False and
         audit['GPU']['tag'] == 'upl_cryer_gpu_component_Debug_probe_r2' and audit['GPU']['completed_six_probes'] is False and
         audit['GPU']['real_tool_exit'] is None and audit['GPU']['memcheck_pass_claimed'] is False,
         'Interrupted r2 is not a completed native call and must remain unchanged')
    return start_e, start, audit_e, audit


def native_exits(h, start_e, start):
    need, bind, adopt, readjson = h.need, h.bind, h.adopt, h.readjson
    opened_e = adopt(T / 'logs/upl_cryer_live_exit_r1.opened.json')
    result_e = adopt(T / 'logs/upl_cryer_live_exit_r1.result.json')
    opened, captured = readjson(bind(opened_e)), readjson(bind(result_e))
    need(opened['stage'] == captured['stage'] == 'upl_cryer_live_exit_r1' and opened['observer_pid'] == 68212 and
         opened['original_owner_absent'] is True and opened['source_start'] == start and
         opened['native_processes_started_stopped_or_modified'] is False and opened['old_receipts_written'] is False and
         opened['physical_acceptance'] is False and captured['capture_complete'] is True and
         captured['all_actual_exits_zero'] is True and captured['failure'] is None and
         captured['opened_record'] == opened_e and captured['bindings'] == opened['bindings'] and
         captured['original_owner_exit_unknown'] is True and captured['original_r3_call_or_run_fabricated'] is False and
         captured['component_completion_memcheck_or_physics_validated'] is False and
         captured['solver_or_program_restarted'] is False and captured['physical_acceptance'] is False,
         'Complete unchanged independent Win32 capture is required')
    required = {T / 'support/upl_cryer_live_exit_r1.py', T / 'notes/upl_cryer_live_exit_r1.json',
                Path(start_e['path']), Path(start['program']['path']), TOOL}
    need(len(opened['bindings']) == 5 and {Path(e['path']).resolve() for e in opened['bindings']} ==
         {path.resolve() for path in required}, 'Observer binding membership differs')
    for e in opened['bindings']:
        bind(e)
    target = ['--input', str(XML), '--out', str(OUT)]
    mempath = T / 'logs' / (TAG + '.memcheck.log')
    target_argv = [start['program']['path']] + target
    tool_argv = [str(TOOL), '--tool', 'memcheck', '--leak-check', 'full', '--error-exitcode', '99',
                 '--log-file', str(mempath)] + target_argv
    need(set(opened['identities']) == set(captured['actual_exit_codes']) == {'tool', 'target'}, 'Both original instances are required')
    exits = {}
    for role, expected_argv in (('tool', tool_argv), ('target', target_argv)):
        identity = opened['identities'][role]
        pid, parent, creation = CREATION[role]
        need(identity['pid'] == pid and identity['parent_pid'] == parent and
             type(identity['created_FILETIME_100ns']) is int and identity['created_FILETIME_100ns'] == creation and
             abs(identity['created_epoch'] - (creation / 1e7 - 11644473600)) < .002 and
             identity['process_handle_opened'] is True and identity['access'] == 'SYNCHRONIZE|QUERY_LIMITED_INFORMATION' and
             Path(identity['exe']).resolve() == Path(expected_argv[0]).resolve() and identity['arguments'] == expected_argv,
             'Exact process creation, parent, executable or full argument vector differs: ' + role)
        exit_e = adopt(T / 'logs' / ('upl_cryer_live_exit_r1.' + role + '_exit.json'))
        observed = readjson(bind(exit_e))
        need(observed == captured['actual_exit_codes'][role] and observed['role'] == role and observed['pid'] == pid and
             type(observed['exit_code']) is int and observed['exit_code'] == 0 and observed['wait_object_signaled'] is True and
             observed['method'] == 'GetExitCodeProcess on handle opened while original process was live' and
             observed['original_PowerShell_LASTEXITCODE_claimed'] is False and
             stamp(identity['opened_utc']) <= stamp(observed['observed_utc']) <= stamp(captured['utc']),
             'Actual signaled Win32 exit0 receipt differs: ' + role)
        exits[role] = exit_e
    need(stamp(start['started_utc']) < stamp(opened['utc']) <= stamp(captured['utc']), 'Capture chronology differs')
    return dict(opened=opened_e, result=result_e, role_exits=exits, identities=opened['identities'],
                tool_program=next(e for e in opened['bindings'] if Path(e['path']).resolve() == TOOL.resolve()),
                target_arguments=target, mempath=mempath)


def helper_closure(h, start, audit):
    # Retained build/tool calls remain real owned typed-exit records. No component call/run is constructed.
    need, bind, readjson = h.need, h.bind, h.readjson
    configuration = 'Debug'
    helper_e = start['helper']; helper = readjson(bind(helper_e))
    need(helper['stage'] == 'upl_cryer_gpu_component_build_r2' and helper['passed'] is True and helper['status'] == 'frozen_cryer_GPU_component_linked_not_run' and helper['configuration'] == configuration and helper['kind'] == 'component' and helper['actual_headers_archived_not_live'] is True and helper['frozen_build_program_inputs_runtime_unchanged'] is True and helper['exact_link_closure_verified'] is True and helper['GPU_non_main_objects'] == 110 and helper['link_object_count'] == 111 and len(helper['objects']) == 110 and len(helper['retained_build_objects111']) == 111 and len(helper['source_snapshots265']) == 265 and len(helper['libraries']) == 18 and len(helper['runtime']) == 4, 'Sealed GPU110+1/265/library18/runtime4 helper required')
    for key in ('inputs', 'author_files', 'source_snapshots265', 'actual_project_headers', 'objects', 'retained_build_objects111', 'libraries', 'tools'):
        for e in helper[key]: bind(e)
    for key in ('program', 'source_build', 'compiler_dependency_record', 'helper_object', 'documentation_snapshot', 'case_readme_snapshot', 'neutral_include', 'retained_compiler_recipe'): bind(helper[key])
    need(audit['GPU']['helper'] == helper_e and start['program'] == helper['program'], 'Audited Debug helper or original target differs')
    build = readjson(bind(helper['source_build'])); snapshots = [v['snapshot'] for v in build['source_snapshot']]
    need(build['stage'] == 'upl_damp_build_r2' and build['passed'] is True and build['configuration'] == configuration and len(build['objects']) == 111 and build['objects'] == helper['retained_build_objects111'] and snapshots == helper['source_snapshots265'] and len(snapshots) == 265 and build['documentation_snapshot']['snapshot'] == helper['documentation_snapshot'] and build['case_readme_snapshot']['snapshot'] == helper['case_readme_snapshot'], 'Actual selected archived source/build closure differs')
    for pair in build['source_snapshot'] + [build['documentation_snapshot'], build['case_readme_snapshot']]:
        need(all(pair['original'][k] == pair['snapshot'][k] for k in ('bytes', 'sha256')), 'Recorded as-of-build archive identity differs')
    project = readjson(bind(build['project_call']))
    need(project['direct_native_call'] is True and project['owned_call_exited'] is True and project['typed_LASTEXITCODE_captured_immediately'] is True and type(project['exit_code']) is int and project['exit_code'] == 0 and project.get('invocation_failure') is None and project['program'] == build['build_tool'], 'Original selected project build was not owned typed0')
    for e in (build['build_tool'], build['program'], build['log'], build['binlog']): bind(e)
    expected = [e for e in build['objects'] if Path(e['path']).name.lower() != 'main.obj']
    need(expected == helper['objects'] and len(expected) == 110 and len({Path(e['path']).name.lower() for e in expected}) == 110, 'Exact non-main object membership differs')
    cc, lc = h.owned(helper['compile_call']), h.owned(helper['link_call'])
    linked = [str(Path(a).resolve()).casefold() for a in lc['arguments'] if a.lower().endswith('.obj')]
    need(len(linked) == len(set(linked)) == 111 and set(linked) == {str(Path(e['path']).resolve()).casefold() for e in expected + [helper['helper_object']]}, 'Actual linker110+1 membership differs')
    need([str(Path(a).resolve()).casefold() for a in lc['arguments'] if a.lower().endswith('.lib')] == [str(Path(e['path']).resolve()).casefold() for e in helper['libraries']], 'Actual ordered18 library arguments differ')
    dep = readjson(bind(helper['compiler_dependency_record']))['Data']; archive = Path(helper['archived_header_include_root']).resolve(); includes = {str(Path(v).resolve()).casefold() for v in dep['Includes']}; neutral = helper['neutral_include']
    headers = {str(Path(v).resolve()).casefold() for v in dep['Includes'] if Path(v).resolve().parent == archive}
    need(Path(dep['Source']).resolve() == (T / 'support/upl_cryer_gpu_component_r2.cpp').resolve() and neutral['sha256'] == '9f6668bfe3d1bbcca7c45c58809f7062c21fcb46baae76f0a2a1b0ef3ca56d38' and str(Path(neutral['path']).resolve()).casefold() in includes and headers == {str(Path(e['path']).resolve()).casefold() for e in helper['actual_project_headers']} and all(e in snapshots for e in helper['actual_project_headers']), 'Actual source/single neutral/archived-header dependencies differ')
    support_roots = ((T / 'support').resolve(), (T.parent.parent / '02_TerzaghiConsolidation_q0_PR/tests/support').resolve())
    authored = [v for v in dep['Includes'] if Path(v).resolve().parent in support_roots]
    need(len(authored) == 1 and Path(authored[0]).resolve() == Path(neutral['path']).resolve(), 'Extra authored dependency beyond the single neutral include')
    for pair in helper['runtime']:
        need(pair['original'] in [v['copy'] for v in build['runtime']] and all(pair['original'][k] == pair['copy'][k] for k in ('bytes', 'sha256')), 'Runtime must derive from selected frozen build copy')
        bind(pair['original']); bind(pair['copy'])
    note_e = next(e for e in helper['author_files'] if Path(e['path']).name == 'upl_cryer_gpu_component_r2.json')
    declaration = readjson(bind(note_e))['retained_input_provenance']; xml, seed = (T.parent / declaration[k] for k in ('runtime', 'seed'))
    for path, name in ((xml, 'runtime'), (seed, 'seed')): bind(dict(path=str(path), bytes=declaration[name + '_bytes'], sha256=declaration[name + '_sha256']))
    need(xml.resolve() == XML.resolve(), 'Captured and declared retained runtime differ')
    return helper_e, helper, snapshots


def payload(gpu, h):
    # These completion and numerical conditions are retained from the pinned original Debug review.
    need, bind, adopt, readjson = h.need, h.bind, h.adopt, h.readjson
    out = OUT
    files = [adopt(path) for path in sorted(out.rglob('*')) if path.is_file()]
    need(len(files) == 8 and {Path(e['path']).resolve().relative_to(out.resolve()).as_posix() for e in files} == gpu.LEAVES,
         'Whole8-file output membership differs; no unrecorded PART trajectory allowed')
    parsed = [h.metadata(out / 'data/Part_Head.ibi4', 'JPartDataHead'), h.metadata(out / 'data/PartOut_000.obi4', 'JPartOutBi4')]
    done_e = adopt(out / 'completion.json')
    need(done_e == next(e for e in files if Path(e['path']).name == 'completion.json'), 'Recovery post-exit completion snapshot differs')
    done = readjson(bind(done_e))
    values = dict(stage='upl_cryer_gpu_component_r2', passed=True, native_count=37173, fixed_dummy_count=8, total_native_count=37181, actual_force_calls=6, complete_rate_calls_from_force=6, explicit_complete_rate_calls=0, soil_reference_checks=223038, sample_rows=48, summary_rows=6, actual_physical_steps=0, actual_time_s=0, manual_J_pool_added8B=4, manual_validity_pool_added4B=2, observer_Init_guard_bypassed_by_fixture=True, feedback_Init_guard_bypassed_by_fixture=True, observer_initialization_validated=False, feedback_initialization_validated=False, legacy_GPU_initialization_validated=True, manual_J1_theta0_installed=True, packed_and_double_support_intervals_unambiguous=False, upper_support_edges_enclosed=True, zero_distance_ambiguity_rejected=True, reference_conditioned_on_observed_C_and_Ace=True, conditional_C_moment_uses_GPU_geometry_fastmath_budget=True, CUDA11p7_published_not_guaranteed_math_envelope_assumed=True, neighbor_search_independently_reimplemented=False, declared_input_bytes_restored=True, whole_object_restored=False, no_Run_ComputeStep_SaveData_restart=True, raw_LoadAce_gate_accounted=True, CPU_GPU_0ULP_compared=False, matched_formal_stabilization=False, physical_acceptance=False, public_3D_admitted=False)
    need(all(done.get(k) == v for k, v in values.items()) and math.isfinite(done['minimum_dummy_soil_distance_m']) and done['minimum_dummy_soil_distance_m'] > .009, 'Original zero-step/manual-init/conditional-math completion differs')
    maximum = h.csv_check(out)
    summary, samples = gpu.csv_rows(out / 'summary.csv'), gpu.csv_rows(out / 'samples.csv')
    for row in summary:
        probe = int(row['probe']); need(float(row['C_moment_abs_residual_max']) >= 0 and float(row['packed_double_displacement_difference_max_m']) >= 0, 'Invalid GPU geometry diagnostic')
        if probe < 4: need(float(row['Ace_norm_max_m_s2']) == float(row['load_norm_max_m_s2']) == 0, 'Original zero-total-stress momentum/source gate differs')
        if probe == 0: need(float(row['pdot_abs_max_Pa_s']) == 0, 'Original strict constant-pressure zero gate differs')
        if probe >= 4: need(int(row['raw_LoadAce_store_gate_open']) + int(row['raw_LoadAce_store_gate_closed']) == 37173, 'Conditional raw-load gate count differs')
        if probe == 4: need(float(row['Ace_norm_max_m_s2']) > 0 and float(row['load_norm_max_m_s2']) > 0, 'Original confinement-only source did not activate')
    for row in samples:
        need(int(row['packed_neighbors']) > 0 and int(row['double_neighbors']) > 0 and 0 <= int(row['poscell_w_UINT_BITS']) < 2**32 and float(row['C_residual']) >= 0 and float(row['packed_double_dr_difference_m']) >= 0, 'GPU packed/reference diagnostics differ')
    totals = gpu.support_edges(summary, samples, done, need)
    return dict(files=files, completion=done_e, metadata=parsed, max_checked_ratio=maximum,
                support_edge_pair_counts=totals, kernel_edge_grad_bound_max=done['kernel_edge_grad_bound_max'])


def review(gpu, h):
    start_e, start, audit_e, audit = provenance(h)
    capture = native_exits(h, start_e, start)
    helper_e, helper, snapshots = helper_closure(h, start, audit)
    mem_e = h.adopt(capture['mempath']); mempath = h.bind(mem_e)
    log = gpu.textlog(mempath)
    er = gpu.re.findall(r'ERROR SUMMARY:\s*(\d+)\s+errors\b', log)
    le = gpu.re.findall(r'LEAK SUMMARY:\s*(\d+)\s+bytes leaked in\s+(\d+)\s+allocations\b', log)
    h.need(er and le and all(int(v) == 0 for v in er) and all(int(a) == int(b) == 0 for a, b in le),
           'Actual memlog must report zero errors AND zero bytes/allocations leaked')
    stdout_e = h.adopt(T / 'logs' / (TAG + '.log'))  # Preserved partial owner stdout; not a new call seal.
    checked = payload(gpu, h)
    producers = [e for e in snapshots if Path(e['path']).name in {'JSph.cpp', 'JPartDataHead.cpp', 'JPartOutBi4Save.cpp', 'JBinaryData.cpp', 'JBinaryData.h'}]
    h.need(len(producers) == 5, 'Archived metadata producer definitions missing')
    return dict(configuration='Debug', interruption_audit=audit_e, original_owner_start=start_e,
        live_capture_opened=capture['opened'], live_capture_result=capture['result'], native_exit_records=capture['role_exits'],
        native_process_identities=capture['identities'], native_exit_evidence_kind='Independent Win32 held-process-handle observations',
        win32_tool_exit0=True, win32_target_exit0=True, target_exit_independently_captured=True,
        original_owner_exit_unknown=True, original_owner_final_input_output_seal_available=False,
        original_PowerShell_LASTEXITCODE_available=False, original_run_or_call_fabricated=False,
        original_run_or_call_read_or_created=False, old_reviewer_main_or_review_called=False,
        working_directory_source_declared=str(Path(helper['program']['path']).resolve().parent),
        native_working_directory_observed=False, observer_open_time_wait_state_recorded=False,
        source_declared_OpenMP_threads=1, runtime_OpenMP_threads_observed=False,
        helper=helper_e, source_build=helper['source_build'], program=helper['program'], owned_tool_program=capture['tool_program'],
        original_partial_stdout=stdout_e, current_frozen_helper_closure_matches_recorded_hashes=True,
        historical_live_production_source_originals_rehashed=False, canonical_project_programs_rehashed=False,
        recovery_post_exit_output_snapshot=True,
        memcheck_errors=0, memcheck_leaks=0, memcheck_log=mem_e, memcheck_zero_errors_and_leaks=True,
        component_completion_verified=True, summary_rows=6, sample_rows=48, metadata_producer_sources=producers,
        no_particle_snapshots_or_exclusions=True, particle_payload_bytes=0, excluded_particle_payload_count=0,
        incomplete_r2_adopted_as_pass=False, observer_initialization_validated=False, feedback_initialization_validated=False,
        whole_object_restored=False, upper_support_edges_enclosed=True, zero_distance_ambiguity_rejected=True,
        initialization_metadata_only=True, conditional_fastmath_envelope_assumed=True,
        caller_reconstructed_neighbor_or_device_proof=False, CPU_GPU_or_Debug_Release_0ULP_compared=False,
        solver_trajectory_started=False, public_3D_admitted=False, physical_acceptance=False,
        component_restarted=False, existing_Release_gate_satisfied_by_alias=False, programs_executed_by_reviewer=0, **checked)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    if not parser.parse_args().execution_authorized:
        raise ValueError('Root must review the whole recovery reviewer before explicit offline execution')
    target = T / 'logs' / (TAG + '_recovery_review_r1.check.json')
    if target.exists():
        raise ValueError('Fresh-only recovery check; preserve all prior evidence')
    required = [T / 'logs' / ('upl_cryer_live_exit_r1.' + name + '.json')
                for name in ('opened', 'result', 'tool_exit', 'target_exit')]
    if any(not path.is_file() for path in required):
        raise ValueError('Native exit capture is still incomplete; no recovery check is created')
    preliminary = json.loads(required[1].read_text(encoding='utf-8-sig'))
    if preliminary.get('capture_complete') is not True:
        raise ValueError('Observer has not sealed a complete unchanged capture; no recovery check is created')
    h = None
    result = dict(stage=STAGE, passed=False, configuration='Debug', physical_acceptance=False,
                  public_3D_admitted=False, programs_executed_by_reviewer=0)
    try:
        gpu, h = definitions()
        h.adopt(__file__); h.adopt(T / 'notes/upl_cryer_gpu_component_recovery_review_r1.json')
        result.update(review(gpu, h))
        for expected in list(h.BOUND.values()):
            h.need(h.entry(expected['path']) == expected, 'Consumed file changed during independent final rehash')
        result.update(passed=True, independent_final_rehash_performed=True, failure=None)
    except Exception as exc:
        result['failure'] = str(exc)
    result['inputs'] = list(h.BOUND.values()) if h else []
    result['limits'] = ('Conditional non-advancing arithmetic, metadata and memcheck only. Original PowerShell exit and final seal remain unavailable. '
        'This recovery check uses separate Win32 exit observations and a new post-exit file snapshot; it is not an alias for the original r3 owner or reviewer. '
        'Native cwd and open-time wait state were not recorded. Published CUDA11.7 fast-math bounds remain assumed, not universal guarantees. '
        'No independent all-soil device/neighbor reconstruction, public3D/init/integration/trajectory/physical acceptance, or CPU-GPU0ULP claim.')
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    if not result['passed']:
        raise ValueError('Recovery review failed; retain ' + str(target) + ': ' + str(result['failure']))
    print(target)


if __name__ == '__main__':
    main()
