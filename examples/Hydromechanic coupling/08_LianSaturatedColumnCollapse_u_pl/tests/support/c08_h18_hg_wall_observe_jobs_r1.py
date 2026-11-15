"""Separately admitted wall-observer Debug2/prefix4 and one bounded failure replay; no reader."""
import argparse
import csv
import math
import os
import re
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import c08_h18_wend_matrix_r1 as m

T, C, L = m.T, m.C, m.L
SCRIPT = Path(__file__).resolve()
NOTE = T / 'notes/c08_h18_hg_wall_observe_jobs_r1.md'
THREAD = '01a07683-bc64-7463-8db7-9ee6243967d8'
WINDOW_CONTROL = 'c08_h18_as03_n255_r1'
FULL_CONTROL = 'c08_h18_as03n255_full3_r1'
REPLAY_TAG = 'c08_h18_hg_wall_observe_replay_GPU_r1'
CODEX = Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1106.51428-win32-x64/bin/windows-x86_64/codex.exe')
CODEX_STAT = dict(path=str(CODEX), bytes=373698352, mtime_ns=1794391544005116300)
ENVIRONMENT = 'C08_HG_OPT_H18'
OPERATOR = 'EnergyNormalizedAdjointLoadingOnlyCachedMaterial'
OPTIMIZATION = 'block_error_snapshot_and_summary_reuse'
DT, PRESTEP = .000005, 2000000
SAN = Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/compute-sanitizer/compute-sanitizer.exe')
JOBS = {
    'debug2': dict(tag='c08_h18_hg_wall_observe_debug2_r1', configuration='Debug', on=True,
                  steps=(2000001, 2000002), updates=2, frames=2, base_frames=91),
    'prefix4': dict(tag='c08_h18_hg_wall_observe_prefix4_r1', configuration='Release', on=True,
                   steps=(2000001, 2002001, 2004001, 2006001), updates=6001, frames=4, base_frames=91),
    'replay': dict(tag=REPLAY_TAG, configuration='Release', on=True,
                  steps=tuple(2000001 + 2000 * part for part in range(99)) + (2196680,),
                  updates=196680, frames=100, base_frames=301),
}


def paths(job):
    suffixes = dict(prep='.prepare.json', prepare_admission='.root_prepare_admission.json',
                    run_admission='.root_run_admission.json', start='.start.json',
                    call='.call.json', log='.log', run='.run.json', status='.status.json',
                    completed='.solver_completed.json', queue='.queue_attempt.json', reply='.queue_result.json')
    return {key: L / (job['tag'] + suffix) for key, suffix in suffixes.items()}


def f32(value):
    return struct.unpack('<f', struct.pack('<f', float(value)))[0]


def admission(path, profile, phase, build):
    q = m.read(path)
    m.need(q['authorized'] and q['allowed_job'] == JOBS[profile]['tag']
           and q['profile'] == profile and q['phase'] == phase
           and q['execution_script'] == m.stat(SCRIPT) and q['note'] == m.stat(NOTE)
           and q['source_build'] == m.stat(build)
           and q['root_thread_id'] == os.environ.get('CODEX_THREAD_ID') == THREAD
           and not q['automatic_native'] and not q['automatic_next_job']
           and q.get('terminal_queue_once', False) == (profile == 'replay') and not q.get('watcher', False),
           'Separate exact current-root prepare/run admission required')
    if profile == 'replay':
        m.need(q['single_bounded_replay_only'] and q['codex'] == CODEX_STAT, 'One current-root replay completion mechanism required')
        m.bind(q['codex']); m.bind(q['physical_decision'])
    return q


def copy_exact(source, target):
    source, target = Path(source), Path(target)
    m.need(not target.exists(), 'Existing copied input protected')
    shutil.copy2(source, target)
    m.need(target.read_bytes() == source.read_bytes(), 'Copied input is not byte-identical')
    return m.stat(target)


def clock_plan(job, source_time, original_rows):
    keys = ['part', 'completed_step', 'saved_step', 'time_s', 'dt_s']
    m.need(len(original_rows) == job['base_frames'] and list(original_rows[0]) == keys,
           'Original unchanged91 or301 base receiver plan required')
    clock, previous, rows, source_clocks = float(source_time), PRESTEP, [], []
    m.need(math.isfinite(clock), 'Actual certified PRE clock is not finite')
    for part, step in enumerate(job['steps']):
        m.need(step > previous, 'Nonincreasing absolute-step cap')
        for _ in range(previous, step):
            before = clock
            clock += DT
        rows.append(dict(part=part, completed_step=step, saved_step=step - 1,
                         time_s=clock, dt_s=DT))
        source_clocks.append(before)
        previous = step
    m.need(previous - PRESTEP == job['updates'] and len(rows) == job['frames'],
           'Closed profile clock/update/frame extent differs')
    old = original_rows[0]
    m.need(int(old['completed_step']) == rows[0]['completed_step']
           and int(old['saved_step']) == rows[0]['saved_step']
           and float(old['dt_s']) == DT and abs(float(old['time_s']) - rows[0]['time_s']) <= 1e-14,
           'Retained actual first-post scalar clock differs')
    if job['base_frames'] == 301:
        for actual, old in zip(rows[:99], original_rows[:99]):
            m.need(all(int(old[key]) == actual[key] for key in ('part', 'completed_step', 'saved_step'))
                   and float(old['time_s']) == actual['time_s'] and float(old['dt_s']) == DT,
                   'All99 actual shared full3 saves must match; no metadata rewrite')
        m.need(rows[98]['completed_step'] == 2196001 and rows[99]['completed_step'] == 2196680
               and rows[99]['saved_step'] == 2196679, 'Closed100-row replay cap differs')
    return rows, source_clocks, clock


def optimized_build(profile, original):
    job = JOBS[profile]
    path = L / ('c08_h18_hg_opt_' + job['configuration'] + '_r1.build.json')
    b = m.read(path)
    m.need(b['passed'] and b['consumed_stats_unchanged']
           and b['configuration'] == job['configuration']
           and b['retained_original_objects'] == 111 and b['private_objects'] == 3
           and b['actual_link_objects'] == 114 and b['compile_invocations'] == 3
           and b['link_invocations'] == 1 and len(b['calls']) == 4
           and b['original_physical_CUDA_objects_retained']
           and not b['public_source_changed'] and not b['class_or_CTE_layout_changed']
           and b['source_archive'] == original['source_archive']
           and b['baseline_source_capture'] == original['source_capture']
           and b['ON_runtime_env'] == ENVIRONMENT + '=1'
           and b['OFF_env_absent_no_HG_allocation_launch_sidecar']
           and b['operator'] == OPERATOR and b['xi'] == .1 and b['policy_schema'] == 2
           and b['neighbor_capacity'] == 128
           and b['single_material_producer'] and b['OFF_calls_original_compiled_integrators']
           and not b['cache_consumer_writeback_is_independent_material_solve']
           and b['optimization_scope'] == OPTIMIZATION and b['NodeKernel_source_bytes_exact']
           and b['new_binary_equivalence_not_yet_proven']
           and b['Debug_first_n_snapshot_macro_enabled'] == (profile == 'debug2'),
           'Exact separately passed private111+3 optimized HG build required')
    entries = [m.stat(path)]
    entries += [m.bind(b[key]) for key in ('program', 'source_capture', 'source_archive',
                'baseline_source_capture', 'base_cached_source_capture')]
    m.need(set(b['private_sources']) == {'host', 'gpu_host', 'CUDA', 'header', 'integrators'}, 'Five actual private host/CUDA/header/integrator captures required')
    entries += [m.bind(q) for q in b['private_sources'].values()]
    entries += [m.bind(q) for q in b['runtime']]
    m.need(len(b['runtime']) == 9 and len({Path(q['path']).name.lower() for q in b['runtime']}) == 9,
           'Original nine-file private runtime closure required')
    cap = m.read(b['source_capture']['path'])
    m.need(cap['passed'] and cap['prepared_only'] and cap['operator'] == OPERATOR
           and cap['policy_schema'] == 2 and cap['xi'] == .1
           and cap['default_OFF_env_absent'] and cap['explicit_ON_env'] == ENVIRONMENT + '=1'
           and cap['exact_reverse_original_hosts_bytes'] and cap['exact_reverse_original_integrators_bytes'] and cap['original_CUDA_members_unchanged']
           and not cap['public_source_changed'] and not cap['class_or_CTE_layout_changed']
           and cap['private_sources'] == b['private_sources']
           and cap['source_archive'] == original['source_archive']
           and cap['baseline_source_capture'] == original['source_capture']
           and cap['optimization_scope'] == OPTIMIZATION and cap['NodeKernel_source_bytes_exact']
           and cap['base_cached_source_capture'] == b['base_cached_source_capture'],
           'Actual reversible private HG host/CUDA source proof required')
    entries += [m.bind(cap[key]) for key in ('source_diff', 'source_proof')]
    optimization = m.read(cap['source_proof']['path'])['optimization']
    m.need(optimization['base_cached_source_capture'] == b['base_cached_source_capture']
           and optimization['nonNode_block_poll_kernels'] == ['CheckConsumedKernel', 'NeighborKernel',
               'FitKernel', 'RowKernel', 'AdjointFitKernel', 'AdjointRowKernel', 'ForceKernel',
               'AceUnchangedKernel', 'CheckCommitKernel']
           and all(optimization[key] for key in ('complete_cached_CUDA_reverse_equal',
               'NodeKernel_source_bytes_exact', 'block_poll_before_out_of_range_return',
               'Ace_check_precedes_readonly_summary', 'normal_summary_uses_error_field',
               'full_ErrorNow_on_failure', 'same_stage_launch_count', 'same_numeric_formulas',
               'same_topology_and_native_ID_order', 'source_proof_not_machine_code_equivalence')),
           'Only the closed non-Node failure-poll and StageForce scheduling optimization is admitted')
    for entry in b['calls']:
        entries.append(m.bind(entry))
        call = m.read(entry['path'])
        m.need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0
               and call['ownership_failure'] is None, 'Actual private build tool exits must pass')
    return path, b, entries


def private_build(profile, original):
    oldpath, old, entries = optimized_build(profile, original)
    configuration = JOBS[profile]['configuration']
    path = L / ('c08_h18_hg_wall_observe_r2_' + configuration + '.build.json')
    b = m.read(path)
    m.need(b['passed'] and b['consumed_stats_unchanged'] and b['configuration'] == configuration
           and b['original_optimized_build'] == m.stat(oldpath)
           and b['original_source_capture'] == old['source_capture']
           and b['original_source_archive'] == old['source_archive']
           and b['actual_link_objects'] == 114 and b['retained_original_physical_objects'] == 110
           and b['retained_private_host_HG_objects'] == 3 and b['recompiled_physical_CUDA_objects'] == 1
           and b['compile_invocations'] == b['link_invocations'] == 1 and len(b['calls']) == 2
           and b['failure_only'] and b['exact_inverse_original_frozen_bytes']
           and b['old_optimized_operator_source_unchanged'] and not b['private_HG_Node_and_consumers_recompiled']
           and not b['public_source_changed'] and not b['physical_arithmetic_changed']
           and not b['threshold_changed'] and not b['normal_path_extra_loops']
           and b['target_stage'] == 1 and b['target_B'] == [4.9000000000000004, 0., -.019999999999999962]
           and b['donor_identity'] == 'actual_sorted_slot_no_native_ID_array' and b['incomplete_M_explicit'],
           'Exact new110+3+1 failure-only observation build required')
    entries += [m.stat(path)]
    entries += [m.bind(b[key]) for key in ('program', 'source_capture', 'source_archive', 'source_diff',
                'original_optimized_build', 'original_actual_link_call')]
    entries += [m.bind(q) for q in b['runtime']]
    cap = m.read(b['source_capture']['path'])
    m.need(cap['original_build'] == m.stat(oldpath) and cap['original_source_capture'] == old['source_capture']
           and cap['exact_inverse_original_frozen_bytes'] and cap['failure_only']
           and cap['original_reject_atomicMin_return_counts_unchanged']
           and cap['archive'] == b['source_archive'] and cap['diff'] == b['source_diff']
           and cap['source_files'] == b['frozen_sources']
           and cap['modified_members'] == ['JSphGpu_ker.cu', 'JSphGpu_mdbc_ker.cuh'],
           'Actual closed failure-only source derivation required')
    physical = {}
    for key, leaf in [('physical_CUDA', 'JSphGpu_ker.cu'), ('wall_include', 'JSphGpu_mdbc_ker.cuh')]:
        matches = [q for q in b['frozen_sources'] if Path(q['path']).name == leaf]
        m.need(len(matches) == 1, 'One actual frozen observer physical source required')
        physical[key] = m.bind(matches[0]); entries.append(physical[key])
    for entry in b['calls']:
        entries.append(m.bind(entry)); call = m.read(entry['path'])
        m.need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0
               and call['ownership_failure'] is None, 'Actual new observer compile/link exits required')
    # This normalized job contract exposes both actual builds; it is not a new
    # synthetic build receipt and does not relabel the retained optimized source.
    result = dict(old)
    result.update(program=b['program'], source_capture=b['source_capture'], source_archive=b['source_archive'],
                  runtime=b['runtime'], private_sources={**old['private_sources'], **physical},
                  base_optimized_build=m.stat(oldpath), base_optimized_source_capture=old['source_capture'])
    return path, result, entries


def short_gates(build):
    entries, receipts = [], []
    for profile, updates, frames in [('debug2', 2, 2), ('prefix4', 6001, 4)]:
        job = JOBS[profile]; tag = job['tag']
        rp, qp = L / (tag + '.run.json'), L / (tag + '.check.json')
        run, check = m.read(rp), m.read(qp); entries += [m.stat(rp), m.stat(qp)]
        m.need(run['passed'] and run['solver_completed'] and run['consumed_stats_unchanged']
               and run['profile'] == profile and run['new_updates'] == updates and run['saved_frames'] == frames
               and run['actual_exit'] == run['actual_Win32_exit'] == run['actual_tool_exit'] == run['actual_tool_Win32_exit'] == 0
               and run['ownership_failure'] is None and run['solver_identity_matches']
               and check['passed'] and not check['physical_acceptance'],
               'Both own observer short runs and independent root native/HG reviews must pass before replay')
        expected_build = L / ('c08_h18_hg_wall_observe_r2_' + job['configuration'] + '.build.json')
        actual_build = m.read(expected_build)
        m.need(run['program'] == actual_build['program'] and run['source_build'] == m.stat(expected_build)
               and actual_build['original_source_capture'] == build['base_optimized_source_capture'],
               'Own short implementation checks must bind these actual observer builds/operator')
        for key in ('actual_call', 'solver_completion', 'program', 'source_build', 'source_capture', 'source_pre_file'):
            entries.append(m.bind(run[key]))
        native_call = check.get('actual_native_call', check.get('actual_call'))
        m.need(native_call is not None and 'native_completion' in check, 'Actual unique native call and completion required')
        entries += [m.bind(native_call), m.bind(check['native_completion'])]
        call, native = m.read(native_call['path']), m.read(check['native_completion']['path'])
        m.need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0 and call['ownership_failure'] is None
               and native['passed'] and native['samples'] == frames and native['completed_steps'] == PRESTEP + updates
               and native['typed_arrays'] == 22 and native['actual_native_IDs_per_frame'] == 6805
               and not native['native_rewritten'], 'Original22/IDs/clock/signed native safety must pass')
        m.need(check.get('policy_equal', False) or check.get('policy_only_family_label_changed', False),
               'Root must review the unchanged HG policy/model parameters')
        if profile == 'debug2':
            m.need(all(check[key] for key in ('all22_native_full_two_records_byte_equal',
                'clock_layout_signed_rows_byte_equal', 'HG_four60column_rows_byte_equal',
                'first_n_snapshot_907392_bytes_equal', 'first_n_config_equal', 'memcheck_zero_errors_and_leaks')),
                'Own Debug2 exact native/HG/first-n/memcheck qualification required')
        else:
            m.need(all(check[key] for key in ('all22_native_four_records_byte_equal',
                'clock_layout_signed_rows_byte_equal', 'HG_eight60column_rows_byte_equal', 'plastic_saved_stage_present')),
                'Own Release four-frame exact native/HG qualification must include real plasticity')
        receipts.append(dict(profile=profile, run=m.stat(rp), root_check=m.stat(qp),
                             actual_native_call=native_call, native_completion=check['native_completion']))
    return entries, receipts


def prepare(profile):
    job, before = JOBS[profile], []
    p = paths(job)
    out = T / 'outputs' / job['tag']
    config = T / 'configs' / (job['tag'] + '_Def.xml')
    stepfile = T / 'configs' / (job['tag'] + '.steps.csv')
    m.need(not out.exists() and not config.exists() and not stepfile.exists()
           and all(not p[key].exists() for key in ('prep', 'run', 'start', 'call', 'log', 'status', 'completed', 'queue', 'reply')),
           'Existing complete/partial profile is protected; no retry')
    try:
        bp = L / ('c08_h18_hg_wall_observe_r2_' + job['configuration'] + '.build.json')
        a = admission(p['prepare_admission'], profile, 'prepare', bp)
        control = FULL_CONTROL if profile == 'replay' else WINDOW_CONTROL
        cr, cp = L / (control + '.run.json'), L / (control + '.prepare.json')
        cn = L / ('c08_h18_as03n255_full3_native_r1.check.json' if profile == 'replay' else 'c08_h18_as03_n255_native_r1.check.json')
        cv = L / ('c08_h18_as03n255_full3_review_r1.check.json' if profile == 'replay' else 'c08_h18_as03n255_review_r1.check.json')
        original, prepared, native, review = map(m.read, (cr, cp, cn, cv))
        m.need(original['passed'] and original['solver_completed'] and original['consumed_stats_unchanged']
               and original['actual_exit'] == original['actual_Win32_exit'] == original['actual_tool_exit'] == 0
               and original['actual_steps'] == (2600000 if profile == 'replay' else 2180000)
               and original['saved_frames'] == job['base_frames']
               and original['AS_coefficient'] == .3 and original['AS_exponent'] == 2.55
               and original['hdp'] == 1.8 and original['fixed_dt_s'] == DT and not original['keep_bed_overlap']
               and prepared['prepared_only'] and prepared['consumed_stats_unchanged']
               and native['passed'] and native['reader_invocations'] == 1 and native['consumed_stats_unchanged']
               and review['analysis_complete'] and review['consumed_stats_unchanged'],
               'Actual retained AS03 seed/control/native proof required')
        before = [m.stat(q) for q in (SCRIPT, NOTE, p['prepare_admission'], cr, cp, cn, cv)]
        before += [m.bind(original[key]) for key in ('program', 'source_build', 'source_capture', 'source_archive',
                   'source_pre_file', 'source_run', 'source_native', 'input_xml', 'planned_steps', 'native_profile', 'actual_call')]
        before += [m.bind(native[key]) for key in ('actual_call', 'native_completion', 'metadata', 'reader_build')]
        source = m.read(original['source_native']['path'])
        m.need(source['passed'] and source['certified_PRE'] and source['expected_handoff_schema'] == 2
               and source['same_material_plastic_PRE'] and source['completed_steps'] == PRESTEP
               and source['group'] == 'psi0' and source['actual_end_s'] == 9.9999999997060076
               and source['kernel_name_declared'] == 'Wendland'
               and source['samples'] == 1001 and source['soil_IDs'] == 5000 and source['fixed_IDs'] == 2060
               and source['declared_Kernel_XML_CSV'] == 2,
               'Original certified schema2 same-material Wendland PRE required, not equilibrium proof')
        bp, b, build_entries = private_build(profile, original)
        before += build_entries
        gate_receipts = []
        if profile == 'replay':
            gate_entries, gate_receipts = short_gates(b); before += gate_entries
            before += [m.bind(a[key]) for key in ('codex', 'physical_decision')]
        definition = m.bind(prepared['configuration'])
        before.append(definition)
        tree = ET.parse(original['input_xml']['path']).getroot()
        params = {q.get('key'): q.get('value') for q in tree.findall('execution/parameters/parameter')}
        m.need(len(params) == len(tree.findall('execution/parameters/parameter'))
               and all(float(params[key]) == value for key, value in dict(Kernel=2, DtFixed=DT,
                       TimeMax=(13. if profile == 'replay' else 10.9), TimeOut=.01, SoilHourglassXi=0, NoPenetration=1, SavePosDouble=1).items())
               and all(f32(params[key]) == f32(value) for key, value in dict(Visco=.1,
                       ArtificialStressCoef=.3, ArtificialStressExp=2.55).items()),
               'Original input physics and output cadence must remain unchanged')
        gravity = tree.find('execution/special/gravitypreload')
        m.need(gravity is not None and Path(gravity.get('statefile')).resolve() == Path(original['source_pre_file']['path']).resolve()
               and gravity.get('elastic_source') == gravity.get('keep_bed_overlap') == 'false'
               and gravity.get('release_mkbound') == '2' and float(gravity.get('time')) == 10,
               'Original same-material PRE/release contract differs')
        profile_rows = m.table(original['native_profile']['path'])
        m.need(len(profile_rows) == 17 and all(list(q) == ['key', 'value'] for q in profile_rows)
               and len({q['key'] for q in profile_rows}) == 17, 'Original seventeen-key material profile required')
        seed = Path(original['input_xml']['path']).with_suffix('')
        m.need(len(original['seed']) == 3 and seed.name == control, 'Original generated triple/basename required')
        seeds = []
        for suffix in ('.xml', '.bi4', '_Normals.nbi4'):
            leaf = Path(str(seed) + suffix)
            entry = next(q for q in original['seed'] if Path(q['path']).resolve() == leaf.resolve())
            seeds.append(m.bind(entry))
            before.append(entry)
        oldrows = m.table(original['planned_steps']['path'])
        rows, source_clocks, end = clock_plan(job, source['actual_end_s'], oldrows)
        if profile == 'replay':
            reference_path = L / 'c08_h18_hg_opt_full3_GPU_r1.run.json'
            expected_steps, expected_count = list(job['steps'][:99]), 99
        else:
            reference_path = L / ('c08_h18_hg_opt_' + profile + '_r1.run.json')
            expected_steps, expected_count = list(job['steps']), job['frames']
        reference = m.read(reference_path)
        reference_parts = reference.get('PARTs')
        if profile == 'replay':
            # The failed wrapper has no normal-completion PARTs seal. Observe the
            # existing immutable partial files now; never invent an old receipt.
            files = sorted((Path(reference['output']) / 'data').glob('Part_*.bi4'))
            reference_parts = [m.stat(q) for q in files]
        m.need(reference['source_capture'] == b['base_optimized_source_capture']
               and reference['source_pre_file'] == original['source_pre_file']
               and reference_parts is not None and len(reference_parts) == expected_count
               and [Path(q['path']).name for q in reference_parts] == ['Part_%04d.bi4' % i for i in range(expected_count)],
               'Actual unchanged-physics optimized saved-prefix reference required')
        if profile == 'replay':
            m.need(not reference['passed'] and not reference['solver_completed']
                   and reference['actual_exit'] == reference['actual_Win32_exit'] == reference['actual_tool_exit'] == 1
                   and reference['ownership_failure'] is None and reference['solver_identity_matches']
                   and reference['global_nsteps_limit'] == 2600000 and reference['observed_saved_files'] == 99,
                   'Actual failed full3/99 prefix must stay failed, not be relabelled as completed')
            reference_rows = m.table(reference['planned_steps']['path'])
            m.need(len(reference_rows) == 301, 'Failed full3 original301 plan stays separate from new100 plan')
            for actual, old in zip(rows[:99], reference_rows[:99]):
                m.need(all(int(actual[key]) == int(old[key]) for key in ('part', 'completed_step', 'saved_step'))
                       and actual['time_s'] == float(old['time_s']) and float(old['dt_s']) == DT,
                       'All99 actual matching old failed saves must match the new scalar plan')
            before.append(m.bind(reference['planned_steps']))
        else:
            m.need(reference['passed'] and reference['solver_completed'] and reference['consumed_stats_unchanged']
                   and reference['actual_exit'] == reference['actual_Win32_exit'] == reference['actual_tool_exit'] == 0,
                   'Actual completed optimized short reference required')
        comparison = dict(run=m.stat(reference_path), actual_call=reference['actual_call'], source_capture=reference['source_capture'],
            PARTs=reference_parts, completed_steps=expected_steps, samples=expected_count,
            original_plan=reference['planned_steps'], reference_is_failed=(profile == 'replay'),
            reference_PART_stats_observed_after_failed_exit=(profile == 'replay'),
            same_dt=True, native_byte_and_signed_clock_review_pending=True)
        before += [comparison['run']] + [m.bind(comparison[key]) for key in ('actual_call', 'source_capture', 'original_plan')]
        before += [m.bind(q) for q in comparison['PARTs']]
        m.verify(before)
        out.mkdir()
        copied_definition = copy_exact(definition['path'], config)
        copied_seeds = [copy_exact(q['path'], out / Path(q['path']).name) for q in seeds]
        copied_profile = copy_exact(original['native_profile']['path'], out / 'native_profile.csv')
        with stepfile.open('x', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        argv = [b['program']['path'], '-gpu:0', '-stable', '-mdbc_freeslip:1',
                str(out / seed.name), str(out), '-dirdataout', 'data', '-svres',
                '-nsteps:' + str(job['steps'][-1])]
        m.verify(before)
        m.save(p['prep'], dict(stage=job['tag'] + '.prepare', passed=True, prepared_only=True,
            profile=profile, configuration=job['configuration'], HG_requested=job['on'],
            program=b['program'], source_build=m.stat(bp), source_capture=b['source_capture'],
            source_archive=b['source_archive'], baseline_source_capture=b['baseline_source_capture'],
            base_cached_source_capture=b['base_cached_source_capture'], optimization_scope=OPTIMIZATION,
            base_optimized_build=b['base_optimized_build'], base_optimized_source_capture=b['base_optimized_source_capture'],
            private_sources=b['private_sources'], runtime=b['runtime'],
            source_pre_file=original['source_pre_file'], source_run=original['source_run'], source_native=original['source_native'],
            control_run=m.stat(cr), control_native=m.stat(cn), control_review=m.stat(cv),
            control_original_plan=original['planned_steps'], configuration_xml=copied_definition,
            input_xml=copied_seeds[0], seed=copied_seeds, native_profile=copied_profile,
            planned_steps=m.stat(stepfile), planned_rows=rows, save_source_clocks_s=source_clocks,
            same_dt_prefix_comparison_reference=comparison, implementation_prerequisites=gate_receipts,
            codex=(a['codex'] if profile == 'replay' else None),
            physical_decision=(a['physical_decision'] if profile == 'replay' else None),
            actual_source_time_s=source['actual_end_s'], planned_actual_end_s=end,
            global_nsteps_limit=job['steps'][-1], new_updates=job['updates'], expected_saved_frames=job['frames'],
            fixed_dt_s=DT, environment_override={ENVIRONMENT: '1' if job['on'] else None},
            argv=argv, cwd=str(C), output=str(out), execution_script=m.stat(SCRIPT), note=m.stat(NOTE),
            root_prepare_admission=m.stat(p['prepare_admission']), consumed=before, consumed_stats_unchanged=True,
            seed_copied_byte_identical=True, generated_basename_preserved=seed.name, original_base_plan_unchanged=True,
            base_plan_frames=job['base_frames'], new_plan_frames=job['frames'], expected_failure_is_not_acceptance=(profile == 'replay'),
            HG_sidecar_review_pending=True, solver_invocations=0, GenCase_invocations=0, reader_invocations=0,
            VTK_invocations=0, SHA_scans=0, physical_acceptance=False, automatic_next_job=False,
            terminal_queue_once=(profile == 'replay'), watcher=False))
    except Exception as error:
        if not p['prep'].exists():
            m.save(p['prep'], dict(stage=job['tag'] + '.prepare', passed=False, first_failure=str(error),
                consumed=before, partial_outputs_preserved=True, solver_invocations=0, automatic_retry=False))
        raise


def summary(path):
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    m.need(len(lines) == 2 and lines[0].startswith('#RunName;'), 'One actual Run.csv summary row required')
    keys, values = lines[0][1:].split(';'), lines[1].split(';')
    index = keys.index('Configuration')
    m.need(len(set(keys)) == len(keys) and len(values) == len(keys) + 1,
           'Only the original embedded ArtificialStress semicolon is permitted')
    values = values[:index] + [values[index] + ';' + values[index + 1]] + values[index + 2:]
    row = dict(zip(keys, values))
    stress = re.findall(r'(?:^| - )AS_Bui2008\(([^;]+);([^\)]+)\)(?= - |$)', row['Configuration'])
    m.need(len(stress) == 1 and row['Configuration'].count(';') == 1
           and all(f32(a) == f32(b) for a, b in zip(stress[0], (.3, 2.55)))
           and 'Wendland' in row['Configuration'], 'Actual original AS03/n255/Wendland configuration required')
    return row


def observe_survivors(call):
    observations = []
    for role in ('child', 'actual_target'):
        original = call.get(role) if call else None
        if not original:
            continue
        entry = dict(role=role, original=original)
        try:
            proc = psutil.Process(original['pid'])
            current = dict(pid=proc.pid, created_epoch=proc.create_time(), exe=proc.exe(),
                           argv=proc.cmdline(), parent_pid=proc.ppid())
            expected_time = original['creation_filetime_100ns'] / 1e7 - 11644473600
            entry.update(current=current, original_identity_matches=(
                Path(current['exe']).resolve() == Path(original['exe']).resolve()
                and abs(current['created_epoch'] - expected_time) <= 5e-6
                and current['argv'] == original.get('argv')))
        except psutil.NoSuchProcess:
            entry['current'] = None
        except (psutil.AccessDenied, KeyError, OSError) as error:
            entry['observation_error'] = str(error)
        observations.append(entry)
    return observations



def trace_summary(raw):
    # Descriptive completeness only. Scientific matrix/donor interpretation and
    # no-feedback native prefix review remain separate, including after failure.
    lines = raw.splitlines()
    reasons = [q for q in lines if q.startswith('C08_HG_WALL_OBS reason=')]
    target = [q for q in reasons if 'stage=1 ' in q
              and 'B=(4.9000000000000004,0,-0.019999999999999962)' in q]
    summaries = []
    for line in target:
        match = re.search(r'reason=(\d+).* stage=1 slot=(\d+) ', line)
        if match is None:
            continue
        reason, slot = map(int, match.groups())
        donor_rows = [q for q in lines if q.startswith('C08_HG_WALL_OBS_DONOR ')
                      and ('reason=%d stage=1 wall_slot=%d ' % (reason, slot)) in q]
        c_rows = [q for q in lines if q.startswith('C08_HG_WALL_OBS_DONOR_C ')
                  and ('reason=%d stage=1 wall_slot=%d ' % (reason, slot)) in q]
        w_rows = [q for q in lines if q.startswith('C08_HG_WALL_OBS_DONOR_W ')
                  and ('reason=%d stage=1 wall_slot=%d ' % (reason, slot)) in q]
        ends = [q for q in lines if q.startswith('C08_HG_WALL_OBS_DONORS_END ')
                and ('reason=%d stage=1 wall_slot=%d ' % (reason, slot)) in q]
        indices = [int(re.search(r' index=(\d+) ', q)[1]) for q in donor_rows]
        counts = [int(re.search(r' donors=(\d+) ', q)[1]) for q in ends]
        complete = len(ends) == 1 and len(donor_rows) == len(c_rows) == len(w_rows) == counts[0]
        complete = complete and sorted(indices) == list(range(counts[0])) and len(set(indices)) == len(indices)
        summaries.append(dict(reason=reason, actual_sorted_wall_slot=slot, base_record=line,
            fit_record_present=any(q.startswith('C08_HG_WALL_OBS_FIT ') and ('reason=%d stage=1 slot=%d ' % (reason, slot)) in q for q in lines),
            M_record_present=any(q.startswith('C08_HG_WALL_OBS_M ') and ('reason=%d stage=1 slot=%d ' % (reason, slot)) in q for q in lines),
            actual_C_record_present=any(q.startswith('C08_HG_WALL_OBS_C stage=1 slot=%d ' % slot) for q in lines),
            raw_fitted_C_record_present=any(q.startswith('C08_HG_WALL_OBS_RAW_C ') and ('reason=%d stage=1 slot=%d ' % (reason, slot)) in q for q in lines),
            B_union_record_present=any(q.startswith('C08_HG_WALL_OBS_B ') and ('reason=%d stage=1 slot=%d ' % (reason, slot)) in q for q in lines),
            actual_donor_rows=len(donor_rows), actual_donor_C_rows=len(c_rows), actual_donor_weight_rows=len(w_rows),
            end_markers=len(ends), donor_counts_reported=counts, donor_row_count_and_indices_complete=complete,
            donor_native_IDs_available=False, numeric_interpretation_pending=True))
    codes = sorted({int(re.search(r'reason=(\d+)', q)[1]) for q in reasons})
    return dict(reason_code_map={1:'invalid_receiver', 2:'raw_donor_J_partial_M', 3:'geometry_exhausted_or_ineligible',
        4:'nonfinite_fitted_component', 5:'stage0_domain', 6:'stage1_reconstructed_C_determinant', 7:'stage2_nonfinite_acceleration'},
        actual_reason_codes=codes, actual_base_reason_rows=len(reasons), target_stage1_records=summaries,
        actual_target_reason_observed=bool(target), native_or_physical_acceptance=False,
        unsaved_arrays_reconstructed=False, expected_99_saved_prefix_comparison_pending=True,
        complete_donor_output_requires_root_review=True, missing_trace_does_not_authorize_retry=True)


def terminal_once(p, prep):
    m.need(not p['queue'].exists() and not p['reply'].exists(), 'Terminal attempt already exists; never resend')
    message = ('The single admitted private C08 optimized-HG wall-failure observation replay is terminal: '
        + str(p['run']) + '. Read original owned start/call/run/status, actual Win32/Popen exits and root admissions, '
        'new observer-r2 physicalCUDA source/program/build, original Wendland schema2 PRE, full3 input, base301 '
        'and new100 scalar plans separately. Targetcap2196680 means196680new updates with100planned saves; '
        'old failed full3 has99saved only throughPart98/completed2196001. Never relabel oldfailureaspassed '
        'or infer unsavednativeclock. HG sameAS.3/n2.55/AV.1/H1.8/5us/keepfalse/fixedplane/CompletedOnly; '
        'originalPRE/coldzeroHG, noHG PARTrestart. Own Debug2 memcheck/native/HG/snapshot and Releasefour '
        'realplastic exact-prefix checks passed before launch. Normal0/cap100 is unexpected completion, '
        'not failure reproduction or physical acceptance. Failure remains failed; preserve first actual '
        'exception and last raw console, reported sourceclock is not a saved native state. C08_HG_WALL_OBS '
        'reason1-7/M/C/donor/B-union printf is failure-only evidence, not unsavedarray reconstruction. '
        'Partial M and absent target donor ends stay incomplete; sorted donor slots are not native IDs. '
        'Root separately reviews actual reasonbranch/donor completeness. Check existing/active readers '
        'before any unique newly admitted native22/6805/P0/J/kappa/FS/ledger/plane/clock/signed partial '
        '99 or complete100 profile; old failed99 reader tiedto301metadata is not this new100plan. '
        'Actual saved shared99 record/time/signed/HG prefix comparison is pending, no header rewriting '
        'or interpolation. No automaticdecoder/VTK/PRE/otherpsi/half/nextsolver. This directowner queues '
        'once45s only; timeout may have delivered, never resend/rearm/add watcher/selftest.')
    argv = [str(CODEX), 'queue', '--thread', THREAD, '--message', message]
    m.save(p['queue'], dict(stage=REPLAY_TAG, run=m.stat(p['run']), status=m.stat(p['status']),
        thread=THREAD, program=prep['codex'], arguments=argv, attempts=1, timeout_s=45,
        only_completion_mechanism='same_direct_run_owner', do_not_resend=True))
    reply = dict(stage=REPLAY_TAG, attempts=1, do_not_resend=True)
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


def run(profile):
    job, before, prep, call = JOBS[profile], [], None, None
    p = paths(job)
    out = T / 'outputs' / job['tag']
    bp = L / ('c08_h18_hg_wall_observe_r2_' + job['configuration'] + '.build.json')
    m.need(all(not p[key].exists() for key in ('run', 'start', 'call', 'log', 'status', 'completed', 'queue', 'reply')),
           'Existing owned attempt/completion/partial protected; never rerun')
    result = dict(stage=job['tag'], passed=False, solver_completed=False, profile=profile,
        configuration=job['configuration'], HG_requested=job['on'], solver_invocations=0,
        solver_launch_attempts=0, native_review_pending=True, HG_sidecar_review_pending=True,
        physical_acceptance=False, GenCase_invocations=0, reader_invocations=0, VTK_invocations=0,
        SHA_scans=0, automatic_next_job=False, terminal_queue_once=(profile == 'replay'), watcher=False,
        unsaved_state_reconstructed=False)
    try:
        prep = m.read(p['prep'])
        ad = admission(p['run_admission'], profile, 'run', bp)
        m.need(prep['passed'] and prep['prepared_only'] and prep['consumed_stats_unchanged']
               and prep['profile'] == profile and prep['configuration'] == job['configuration']
               and prep['HG_requested'] == job['on'] and prep['execution_script'] == m.stat(SCRIPT)
               and prep['note'] == m.stat(NOTE) and ad['preparation'] == m.stat(p['prep'])
               and (profile != 'replay' or (ad['codex'] == prep['codex'] and ad['physical_decision'] == prep['physical_decision'])),
               'Independent exact prepared-job run admission required')
        before = [m.stat(q) for q in (SCRIPT, NOTE, p['prep'], p['run_admission'])]
        before += [m.bind(prep[key]) for key in ('program', 'source_build', 'source_capture', 'source_archive',
            'baseline_source_capture', 'base_cached_source_capture', 'base_optimized_build', 'base_optimized_source_capture', 'source_pre_file', 'source_run', 'source_native', 'control_run',
            'control_native', 'control_review', 'control_original_plan', 'configuration_xml',
            'input_xml', 'native_profile', 'planned_steps')]
        before += [m.bind(q) for q in prep['seed'] + prep['runtime'] + list(prep['private_sources'].values())]
        comparison = prep['same_dt_prefix_comparison_reference']
        m.need(prep['optimization_scope'] == OPTIMIZATION and comparison['samples'] == (99 if profile == 'replay' else job['frames']),
               'Exact observer/profile saved-prefix comparison contract required')
        before += [m.bind(comparison[key]) for key in ('run', 'actual_call', 'source_capture', 'original_plan')]
        before += [m.bind(q) for q in comparison['PARTs']]
        if profile == 'replay':
            before += [m.bind(prep[key]) for key in ('codex', 'physical_decision')]
            gate_entries, gate_receipts = short_gates(prep)
            m.need(gate_receipts == prep['implementation_prerequisites'], 'Own short-review receipt binding changed')
            before += gate_entries
        program, argv = Path(prep['program']['path']), list(prep['argv'])
        m.need(out.is_dir() and not (out / 'data').exists() and not (out / 'Run.out').exists()
               and argv[0] == str(program) and argv[-1] == '-nsteps:' + str(PRESTEP + job['updates'])
               and prep['global_nsteps_limit'] == PRESTEP + job['updates']
               and prep['new_updates'] == job['updates'] and prep['expected_saved_frames'] == job['frames']
               and prep['environment_override'] == {ENVIRONMENT: '1' if job['on'] else None},
               'Fresh bounded original-input directory and exact global cap required')
        for proc in psutil.process_iter(['pid', 'exe']):
            try:
                m.need(not proc.info['exe'] or Path(proc.info['exe']).resolve() != program.resolve(),
                       'Exact private executable is already active; no duplicate launch')
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        tool = list(argv)
        if profile == 'debug2':
            before.append(m.stat(SAN))
            tool = [str(SAN), '--tool', 'memcheck', '--leak-check', 'full',
                    '--target-processes', 'all', '--error-exitcode', '99', *argv]
        env = dict(os.environ)
        for key in list(env):
            if key.upper() == ENVIRONMENT:
                env.pop(key)
        if job['on']:
            env[ENVIRONMENT] = '1'
        owner_proc = psutil.Process()
        owner = dict(pid=owner_proc.pid, created_epoch=owner_proc.create_time(), exe=owner_proc.exe(),
                     argv=owner_proc.cmdline(), parent_pid=owner_proc.ppid())
        m.verify(before)
        m.save(p['start'], dict(stage=job['tag'] + '.start', owner=owner, preparation=m.stat(p['prep']),
            root_admission=m.stat(p['run_admission']), program=prep['program'], source_build=prep['source_build'],
            source_capture=prep['source_capture'], source_archive=prep['source_archive'],
            source_pre_file=prep['source_pre_file'], input_xml=prep['input_xml'], planned_steps=prep['planned_steps'],
            argv=tool, solver_argv=argv, cwd=prep['cwd'], environment_override=prep['environment_override'],
            consumed=before, automatic_native=False, automatic_next_job=False, terminal_queue_once=(profile == 'replay'),
            physical_acceptance=False))
        result.update({key: prep[key] for key in ('program', 'source_build', 'source_capture', 'source_archive',
            'baseline_source_capture', 'base_cached_source_capture', 'base_optimized_build', 'base_optimized_source_capture', 'optimization_scope',
            'private_sources', 'runtime', 'source_pre_file', 'source_run',
            'source_native', 'control_run', 'control_native', 'control_review', 'control_original_plan',
            'configuration_xml', 'input_xml', 'seed', 'planned_steps', 'native_profile', 'actual_source_time_s',
            'planned_actual_end_s', 'global_nsteps_limit', 'new_updates', 'expected_saved_frames', 'environment_override',
            'same_dt_prefix_comparison_reference', 'implementation_prerequisites', 'codex', 'physical_decision')})
        result.update(owner=owner, preparation=m.stat(p['prep']), root_admission=m.stat(p['run_admission']),
                      argv=tool, solver_argv=argv, output=str(out), fixed_dt_s=DT, solver_launch_attempts=1)
        result['actual_call'] = m.invoke(job['tag'], tool, Path(prep['cwd']), env=env,
                                         target=program if profile == 'debug2' else None)
    except Exception as error:
        result['first_failure'] = str(error)
    if p['call'].exists():
        result['actual_call'] = m.stat(p['call'])
        call = m.read(p['call'])
        solver = call.get('actual_target') if profile == 'debug2' else call.get('child')
        result.update(actual_tool_exit=call.get('actual_Popen_wait_exit'),
            actual_tool_Win32_exit=call.get('actual_Win32_exit'),
            actual_exit=call.get('actual_target_Win32_exit') if profile == 'debug2' else call.get('actual_Win32_exit'),
            actual_Win32_exit=call.get('actual_target_Win32_exit') if profile == 'debug2' else call.get('actual_Win32_exit'),
            ownership_failure=call.get('ownership_failure'), solver_invocations=1 if solver else None,
            solver_identity=solver)
        expected_parent = call['child']['pid'] if profile == 'debug2' else result['owner']['pid']
        result['solver_identity_matches'] = bool(solver and prep and
            Path(solver['exe']).resolve() == Path(prep['program']['path']).resolve()
            and solver.get('creation_filetime_100ns', 0) > 0 and solver.get('parent_pid') == expected_parent
            and solver.get('argv') == prep['argv'] and call['owner']['pid'] == result['owner']['pid']
            and abs(call['owner']['created_epoch'] - result['owner']['created_epoch']) <= 5e-6)
    try:
        m.need(call is not None and result.get('solver_identity_matches')
               and result['actual_exit'] == result['actual_Win32_exit'] == 0
               and result['ownership_failure'] is None, 'Actual owned native solver normal exit is unproved')
        text = (out / 'Run.out').read_text(encoding='utf-8-sig')
        m.need('Finished execution (code=0).' in text and '[Simulation INTERRUPTED' not in text
               and 'certified same-material plastic schema/contract2' in text,
               'Actual normal schema2 completion required')
        # Independent solver seal FIRST. Summary/memcheck/HG/native are later reviews.
        completed = dict(stage=job['tag'] + '.solver_completed', solver_completed=True,
            actual_call=result['actual_call'], original_start=m.stat(p['start']), owner=result['owner'],
            solver_identity=result['solver_identity'], program=prep['program'], source_build=prep['source_build'],
            source_capture=prep['source_capture'], source_archive=prep['source_archive'],
            source_pre_file=prep['source_pre_file'], input_xml=prep['input_xml'], planned_steps=prep['planned_steps'],
            actual_solver_Win32_exit=result['actual_Win32_exit'], actual_tool_exit=result['actual_tool_exit'],
            Run_out=m.stat(out / 'Run.out'), target_coverage_review_pending=True,
            HG_sidecar_review_pending=True, native_review_pending=True, no_solver_retry=True,
            physical_acceptance=False)
        m.save(p['completed'], completed)
        result.update(solver_completed=True, solver_completion=m.stat(p['completed']), Run_out=completed['Run_out'])
        row = summary(out / 'Run.csv')
        frames = sorted((out / 'data').glob('Part_*.bi4'))
        m.need(int(row['Steps']) == prep['global_nsteps_limit'] and int(row['PartFiles']) == job['frames']
               and int(row['PartsOut']) == 0 and int(row['PartsOutRhop']) == 0 and int(row['PartsOutVel']) == 0
               and [q.name for q in frames] == ['Part_%04d.bi4' % i for i in range(job['frames'])],
               'Actual global-step/frame/no-exclusion coverage differs')
        m.need(math.isfinite(float(row['PhysicalTime']))
               and abs(float(row['PhysicalTime']) - prep['planned_actual_end_s']) <= .00000051,
               'Rounded Run.csv physical endpoint differs; exact saved clocks remain pending native review')
        result.update(summary=row, actual_steps=int(row['Steps']), saved_frames=len(frames),
            Run_csv=m.stat(out / 'Run.csv'), PARTs=[m.stat(q) for q in frames],
            particle_data_files=[m.stat(q) for q in sorted((out / 'data').iterdir()) if q.is_file()],
            Run_csv_endpoint_is_rounded_not_native_clock=True)
        m.need(result['actual_tool_exit'] == result['actual_tool_Win32_exit'] == 0
               and 'first_failure' not in result, 'Actual tool exit/owned invocation must also pass')
        if profile == 'debug2':
            log = Path(call['log']['path']).read_text(encoding='mbcs', errors='replace')
            errors = re.findall(r'ERROR SUMMARY: ([0-9,]+) errors', log)
            leaks = re.findall(r'LEAK SUMMARY: ([0-9,]+) bytes leaked in ([0-9,]+) allocations', log)
            m.need(errors and leaks and all(int(q.replace(',', '')) == 0 for q in errors)
                   and all(int(a.replace(',', '')) == int(b.replace(',', '')) == 0 for a, b in leaks),
                   'Actual memcheck zero errors/leaks is absent')
            result.update(memcheck_actual_call=result['actual_call'], memcheck_zero_errors_and_leaks=True)
        m.verify(before)
        result.update(passed=True, consumed_stats_unchanged=True)
    except Exception as error:
        result.setdefault('first_failure', str(error))
    if (out / 'Run.out').exists():
        text = (out / 'Run.out').read_text(encoding='utf-8-sig', errors='replace')
        exception = re.search(r'^(?:Text: |\*\*\* Exception\(exc\): )(.*)$', text, re.M)
        result.update(Run_out=m.stat(out / 'Run.out'), first_engine_exception_text=exception[1] if exception else None,
                      observed_saved_files=len(list((out / 'data').glob('Part_*.bi4'))))
    if call and Path(call['log']['path']).is_file():
        raw = Path(call['log']['path']).read_text(encoding='mbcs', errors='replace')
        rows = [line for line in raw.splitlines() if re.match(r'^Part_\d+\s', line)]
        result.update(console_log=m.bind(call['log']), last_original_console_PART_line=rows[-1] if rows else None)
        if profile == 'replay':
            result['terminal_observation'] = trace_summary(raw)
            result['expected_failure_remains_solver_failure'] = result.get('actual_exit') != 0
            result['unexpected_normal_cap_completed'] = bool(result.get('solver_completed'))
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
        result['surviving_process_observations'] = observe_survivors(call)
    m.save(p['run'], result)
    m.save(p['status'], dict(stage=job['tag'],
        status='completed_pending_unique_native_and_HG_review' if result['passed'] else
               'completed_solver_review_failed' if result['solver_completed'] else 'failed_preserved_no_retry',
        run=m.stat(p['run']), automatic_native=False, automatic_next_job=False,
        terminal_queue_once=(profile == 'replay'), watcher=False, physical_acceptance=False,
        terminal_observation=result.get('terminal_observation'), exact_reason_and_donor_numeric_review_pending=(profile == 'replay'),
        unexpected_normal_cap_completed=result.get('unexpected_normal_cap_completed', False)))
    if profile == 'replay' and call is not None and result['solver_launch_attempts'] == 1:
        terminal_once(p, prep)
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'run'))
    parser.add_argument('--profile', choices=tuple(JOBS), required=True)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    m.need(args.execution_authorized, 'Separate root prepare/run admission required')
    if args.phase == 'prepare':
        prepare(args.profile)
    else:
        raise SystemExit(run(args.profile))
