"""One separately admitted private optimized-HG psi0 3s diagnostic; no reader or next job."""
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
NOTE = T / 'notes/c08_h18_hg_opt_full3_r1.md'
THREAD = '01a07683-bc64-7463-8db7-9ee6243967d8'
CONTROL = 'c08_h18_as03n255_full3_r1'
ENVIRONMENT = 'C08_HG_OPT_H18'
OPERATOR = 'EnergyNormalizedAdjointLoadingOnlyCachedMaterial'
OPTIMIZATION = 'block_error_snapshot_and_summary_reuse'
TAG = 'c08_h18_hg_opt_full3_GPU_r1'
CODEX = Path('C:/Users/syosh/.vscode/extensions/openai.chatgpt-26.1106.51428-win32-x64/bin/windows-x86_64/codex.exe')
CODEX_STAT = dict(path=str(CODEX), bytes=373698352, mtime_ns=1794391544005116300)
DT, PRESTEP = .000005, 2000000
SAN = Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/compute-sanitizer/compute-sanitizer.exe')
JOBS = {
    'full3': dict(tag='c08_h18_hg_opt_full3_GPU_r1', configuration='Release', on=True,
                  steps=tuple(2000001 + 2000 * part for part in range(300)) + (2600000,),
                  updates=600000, frames=301),
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
           and q['terminal_queue_once'] and q['single_full3_only'] and q['codex'] == CODEX_STAT
           and not q.get('watcher', False),
           'Separate exact current-root prepare/run admission required')
    m.bind(q['codex'])
    m.bind(q['physical_decision'])
    return q


def copy_exact(source, target):
    source, target = Path(source), Path(target)
    m.need(not target.exists(), 'Existing copied input protected')
    shutil.copy2(source, target)
    m.need(target.read_bytes() == source.read_bytes(), 'Copied input is not byte-identical')
    return m.stat(target)


def clock_plan(job, source_time, original_rows):
    keys = ['part', 'completed_step', 'saved_step', 'time_s', 'dt_s']
    m.need(len(original_rows) == 301 and list(original_rows[0]) == keys,
           'Original unchanged301 full3 receiver plan required')
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
    for actual, old in zip(rows, original_rows):
        m.need(all(int(old[key]) == actual[key] for key in ('part', 'completed_step', 'saved_step'))
               and float(old['dt_s']) == DT and float(old['time_s']) == actual['time_s'],
               'All301 retained actual scalar clocks/steps must match without interpolation')
    m.need(rows[90]['completed_step'] == 2180001 and rows[-1]['completed_step'] == 2600000
           and clock == 12.999999999592434, 'Original full3 scalar endpoint/cadence differs')
    return rows, source_clocks, clock


def private_build(profile, original):
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


def prerequisites(build):
    entries, receipts = [], []
    specs = [('off1', 'Release', 1, 1), ('debug2', 'Debug', 2, 2), ('prefix4', 'Release', 6001, 4)]
    for profile, configuration, updates, frames in specs:
        tag = 'c08_h18_hg_opt_' + profile + '_r1'
        rp, qp = L / (tag + '.run.json'), L / (tag + '.check.json')
        run, check = m.read(rp), m.read(qp)
        entries += [m.stat(rp), m.stat(qp)]
        m.need(run['passed'] and run['solver_completed'] and run['consumed_stats_unchanged']
               and run['profile'] == profile and run['new_updates'] == updates
               and run['saved_frames'] == frames and run['actual_steps'] == PRESTEP + updates
               and run['actual_exit'] == run['actual_Win32_exit'] == run['actual_tool_exit']
                   == run['actual_tool_Win32_exit'] == 0
               and run['ownership_failure'] is None and run['solver_identity_matches']
               and check['passed'] and not check['physical_acceptance'],
               'Each original optimized OFF1/Debug2/prefix4 run and independent root review must pass')
        expected_build = m.read(L / ('c08_h18_hg_opt_' + configuration + '_r1.build.json'))
        m.need(run['program'] == expected_build['program'] and run['source_capture'] == build['source_capture']
               and run['source_build'] == m.stat(L / ('c08_h18_hg_opt_' + configuration + '_r1.build.json')),
               'Implementation gates must bind these actual optimized programs/source')
        for key in ('actual_call', 'solver_completion', 'program', 'source_build', 'source_capture', 'source_pre_file'):
            entries.append(m.bind(run[key]))
        reader_entry = check.get('actual_native_call', check.get('actual_call'))
        m.need(reader_entry is not None and 'native_completion' in check,
               'Independent actual native call/completion must be exposed by each root check')
        entries += [m.bind(reader_entry), m.bind(check['native_completion'])]
        call, native = m.read(reader_entry['path']), m.read(check['native_completion']['path'])
        m.need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0
               and call['ownership_failure'] is None and native['passed']
               and native['samples'] == frames and native['completed_steps'] == PRESTEP + updates
               and native['typed_arrays'] == 22 and native['actual_native_IDs_per_frame'] == 6805
               and native['max_scalar_clock_error_s'] <= 1e-14 and not native['native_rewritten'],
               'Every independent original native completion must pass its unchanged extent/guards')
        if profile == 'off1':
            m.need(all(check[key] for key in ('all22_arrays_first_record_byte_equal', 'layout_byte_equal',
                'clock_and_signed_interval_whole_row_byte_equal', 'HG_sidecars_absent')),
                'OFF1 complete native byte equivalence is required')
        elif profile == 'debug2':
            m.need(all(check[key] for key in ('all22_native_full_two_records_byte_equal',
                'clock_layout_signed_rows_byte_equal', 'HG_four60column_rows_byte_equal',
                'policy_only_family_label_changed', 'first_n_snapshot_907392_bytes_equal',
                'first_n_config_equal', 'memcheck_zero_errors_and_leaks')),
                'Debug2 native/cache/first-force/memcheck implementation gates are required')
        elif profile == 'prefix4':
            m.need(all(check[key] for key in ('all22_native_four_records_byte_equal',
                'clock_layout_signed_rows_byte_equal', 'HG_eight60column_rows_byte_equal',
                'policy_only_family_label_changed', 'plastic_saved_stage_present')),
                'Release same-dt four-frame native/HG equality including actual plasticity is required')
        receipts.append(dict(profile=profile, run=m.stat(rp), root_check=m.stat(qp),
                             actual_native_call=reader_entry, native_completion=check['native_completion']))
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
        bp = L / ('c08_h18_hg_opt_' + job['configuration'] + '_r1.build.json')
        a = admission(p['prepare_admission'], profile, 'prepare', bp)
        cr, cp = L / (CONTROL + '.run.json'), L / (CONTROL + '.prepare.json')
        cn, cv = L / 'c08_h18_as03n255_full3_native_r1.check.json', L / 'c08_h18_as03n255_full3_review_r1.check.json'
        original, prepared, native, review = map(m.read, (cr, cp, cn, cv))
        m.need(original['passed'] and original['solver_completed'] and original['consumed_stats_unchanged']
               and original['actual_exit'] == original['actual_Win32_exit'] == original['actual_tool_exit'] == 0
               and original['actual_steps'] == 2600000 and original['saved_frames'] == 301
               and original['AS_coefficient'] == .3 and original['AS_exponent'] == 2.55
               and original['hdp'] == 1.8 and original['fixed_dt_s'] == DT and not original['keep_bed_overlap']
               and prepared['prepared_only'] and prepared['consumed_stats_unchanged']
               and native['passed'] and native['reader_invocations'] == 1 and native['consumed_stats_unchanged']
               and review['analysis_complete'] and review['consumed_stats_unchanged'],
               'Actual retained full3 AS03 seed/control/native proof required')
        before = [m.stat(q) for q in (SCRIPT, NOTE, p['prepare_admission'], cr, cp, cn, cv)]
        before += [m.bind(a[key]) for key in ('codex', 'physical_decision')]
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
        prerequisite_entries, implementation_receipts = prerequisites(b)
        before += prerequisite_entries
        definition = m.bind(prepared['configuration'])
        before.append(definition)
        tree = ET.parse(original['input_xml']['path']).getroot()
        params = {q.get('key'): q.get('value') for q in tree.findall('execution/parameters/parameter')}
        m.need(len(params) == len(tree.findall('execution/parameters/parameter'))
               and all(float(params[key]) == value for key, value in dict(Kernel=2, DtFixed=DT,
                       TimeMax=13., TimeOut=.01, SoilHourglassXi=0, NoPenetration=1, SavePosDouble=1).items())
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
        m.need(len(original['seed']) == 3 and seed.name == CONTROL, 'Original generated triple/basename required')
        seeds = []
        for suffix in ('.xml', '.bi4', '_Normals.nbi4'):
            leaf = Path(str(seed) + suffix)
            entry = next(q for q in original['seed'] if Path(q['path']).resolve() == leaf.resolve())
            seeds.append(m.bind(entry))
            before.append(entry)
        oldrows = m.table(original['planned_steps']['path'])
        rows, source_clocks, end = clock_plan(job, source['actual_end_s'], oldrows)
        comparison = None
        if profile == 'full3':
            for actual, old in zip(rows[:90], oldrows[:90]):
                m.need(all(int(actual[key]) == int(old[key]) for key in ('part', 'completed_step', 'saved_step'))
                       and float(old['dt_s']) == DT and abs(actual['time_s'] - float(old['time_s'])) <= 1e-14,
                       'Exact original first90 full3 cadence/scalar clocks differ')
            reference_path = L / 'c08_h18_hg_cached_window_GPU_r1.run.json'
            reference = m.read(reference_path)
            m.need(reference['passed'] and reference['solver_completed'] and reference['consumed_stats_unchanged']
                   and reference['actual_steps'] == 2180000 and reference['saved_frames'] == 91
                   and reference['actual_exit'] == reference['actual_Win32_exit']
                       == reference['actual_tool_exit'] == reference['actual_tool_Win32_exit'] == 0
                   and reference['source_capture'] == b['base_cached_source_capture']
                   and reference['source_pre_file'] == original['source_pre_file']
                   and len(reference['PARTs']) == 91
                   and [Path(q['path']).name for q in reference['PARTs'][:90]]
                       == ['Part_%04d.bi4' % i for i in range(90)],
                   'Completed cached .90s true first90 reference required; forced final2180000 is excluded')
            comparison = dict(run=m.stat(reference_path), solver_completion=reference['solver_completion'],
                actual_call=reference['actual_call'], source_capture=reference['source_capture'],
                PARTs=reference['PARTs'][:90], completed_steps=list(job['steps'][:90]),
                shared_samples=90, old_forced_final2180000_not_shared=True,
                full_part90_completed_step=2180001, same_dt=True,
                native_byte_and_signed_clock_review_pending=True)
            before += [comparison['run']]
            before += [m.bind(comparison[key]) for key in ('solver_completion', 'actual_call', 'source_capture')]
            before += [m.bind(q) for q in comparison['PARTs']]
        cached_plan = m.table(reference['planned_steps']['path'])
        before.append(m.bind(reference['planned_steps']))
        m.need(len(cached_plan) == 91 and int(cached_plan[-1]['completed_step']) == 2180000,
               'Original cached91 forced-final plan required')
        for actual, old in zip(rows[:90], cached_plan[:90]):
            m.need(all(int(actual[key]) == int(old[key]) for key in ('part', 'completed_step', 'saved_step'))
                   and float(old['time_s']) == actual['time_s'] and float(old['dt_s']) == DT,
                   'Only actual shared first90 cached states may be used in later prefix review')
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
            private_sources=b['private_sources'], runtime=b['runtime'],
            source_pre_file=original['source_pre_file'], source_run=original['source_run'], source_native=original['source_native'],
            control_run=m.stat(cr), control_native=m.stat(cn), control_review=m.stat(cv),
            control_original_plan=original['planned_steps'], configuration_xml=copied_definition,
            input_xml=copied_seeds[0], seed=copied_seeds, native_profile=copied_profile,
            planned_steps=m.stat(stepfile), planned_rows=rows, save_source_clocks_s=source_clocks,
            same_dt_prefix_comparison_reference=comparison, implementation_prerequisites=implementation_receipts,
            codex=a['codex'], physical_decision=a['physical_decision'],
            actual_source_time_s=source['actual_end_s'], planned_actual_end_s=end,
            global_nsteps_limit=job['steps'][-1], new_updates=job['updates'], expected_saved_frames=job['frames'],
            fixed_dt_s=DT, environment_override={ENVIRONMENT: '1' if job['on'] else None},
            argv=argv, cwd=str(C), output=str(out), execution_script=m.stat(SCRIPT), note=m.stat(NOTE),
            root_prepare_admission=m.stat(p['prepare_admission']), consumed=before, consumed_stats_unchanged=True,
            seed_copied_byte_identical=True, generated_basename_preserved=seed.name, old301_plan_unchanged=True,
            diagnostic_3s_not_physical_acceptance=True, other_psi_held=True, HG_history_cold_zero=True,
            HG_sidecar_review_pending=True, solver_invocations=0, GenCase_invocations=0, reader_invocations=0,
            VTK_invocations=0, SHA_scans=0, physical_acceptance=False, automatic_next_job=False,
            terminal_queue_once=True, watcher=False))
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


def terminal_once(p, prep):
    m.need(not p['queue'].exists() and not p['reply'].exists(), 'Terminal attempt already exists; never resend')
    message = ('The single admitted C08 optimized cached-HG psi0 fresh3s GPU diagnostic is terminal: '
        + str(p['run']) + '. Read original owned start/call/run/status/solver_completed, both root admissions, '
        'actual Win32/Popen exits, original same-material schema2 PRE/program/source/input and301 scalar plan. '
        'AS.3/n2.55/AV.1/WendlandH1.8/fixed5us/keepfalse/fixed-plane/CompletedOnly remain; '
        '600000new updates/global2600000/301 planned saves, not physical acceptance. HG is directed-row '
        'energy-normalized memory with full LS adjoint and single material producer per ID/stage. '
        'The optimized Node source is unchanged; OFF1/Debug2/prefix4 passed before launch. Cache13/commit7 '
        'checks are coherence, not an independent old material solve. Diagnostic budgets are not outward '
        'or coupled-energy certificates. Check existing/active readers before separately admitted unique '
        'full301 native22/6805/P0/J/kappa/FS/ledger/plane/clock/signed and HG phase/work/history review. '
        'Only actual first90 cached-window states are shared; old forced-final2180000 is not fullPart90 '
        '2180001. Preserve original91/301 headers and signed rows, no interpolation or fake byte proof. '
        'Inspect pressure, spacing/nonaffinity, stress, motion/plasticity and early arrest; normal exit '
        'does not establish physics/paper accuracy. Source PRE was reused with cold-zero HG, not exactHG '
        'PART restart. Preserve failures/partials/first real error/last raw console; never reconstruct '
        'unsaved time or rerun a completed solver. No automatic native/VTK/PRE/otherpsi/half/next solver. '
        'This direct owner queues once45s; timeout may have delivered, never resend/rearm/add watcher/selftest.')
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


def run(profile):
    job, before, prep, call = JOBS[profile], [], None, None
    p = paths(job)
    out = T / 'outputs' / job['tag']
    bp = L / ('c08_h18_hg_opt_' + job['configuration'] + '_r1.build.json')
    m.need(all(not p[key].exists() for key in ('run', 'start', 'call', 'log', 'status', 'completed', 'queue', 'reply')),
           'Existing owned attempt/completion/partial protected; never rerun')
    result = dict(stage=job['tag'], passed=False, solver_completed=False, profile=profile,
        configuration=job['configuration'], HG_requested=job['on'], solver_invocations=0,
        solver_launch_attempts=0, native_review_pending=True, HG_sidecar_review_pending=True,
        physical_acceptance=False, GenCase_invocations=0, reader_invocations=0, VTK_invocations=0,
        SHA_scans=0, automatic_next_job=False, terminal_queue_once=True, watcher=False,
        unsaved_state_reconstructed=False)
    try:
        prep = m.read(p['prep'])
        ad = admission(p['run_admission'], profile, 'run', bp)
        m.need(prep['passed'] and prep['prepared_only'] and prep['consumed_stats_unchanged']
               and prep['profile'] == profile and prep['configuration'] == job['configuration']
               and prep['HG_requested'] == job['on'] and prep['execution_script'] == m.stat(SCRIPT)
               and prep['note'] == m.stat(NOTE) and ad['preparation'] == m.stat(p['prep'])
               and ad['codex'] == prep['codex'] and ad['physical_decision'] == prep['physical_decision'],
               'Independent exact prepared-job run admission required')
        before = [m.stat(q) for q in (SCRIPT, NOTE, p['prep'], p['run_admission'])]
        before += [m.bind(prep[key]) for key in ('program', 'source_build', 'source_capture', 'source_archive',
            'baseline_source_capture', 'base_cached_source_capture', 'source_pre_file', 'source_run', 'source_native', 'control_run',
            'control_native', 'control_review', 'control_original_plan', 'configuration_xml',
            'input_xml', 'native_profile', 'planned_steps', 'codex', 'physical_decision')]
        before += [m.bind(q) for q in prep['seed'] + prep['runtime'] + list(prep['private_sources'].values())]
        comparison = prep['same_dt_prefix_comparison_reference']
        m.need(prep['optimization_scope'] == OPTIMIZATION and bool(comparison) == (profile == 'full3'),
               'Exact optimization/profile comparison contract required')
        if comparison:
            before += [m.bind(comparison[key]) for key in ('run', 'solver_completion', 'actual_call', 'source_capture')]
            before += [m.bind(q) for q in comparison['PARTs']]
        gate_entries, gate_receipts = prerequisites(m.read(bp))
        m.need(gate_receipts == prep['implementation_prerequisites'], 'Actual implementation receipts changed')
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
            consumed=before, automatic_native=False, automatic_next_job=False, terminal_queue_once=True,
            physical_acceptance=False))
        result.update({key: prep[key] for key in ('program', 'source_build', 'source_capture', 'source_archive',
            'baseline_source_capture', 'base_cached_source_capture', 'optimization_scope',
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
        terminal_queue_once=True, watcher=False, physical_acceptance=False))
    if call is not None and result['solver_launch_attempts'] == 1:
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
