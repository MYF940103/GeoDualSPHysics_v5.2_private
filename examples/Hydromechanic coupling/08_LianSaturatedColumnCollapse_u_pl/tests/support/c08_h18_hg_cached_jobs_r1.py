"""Two separately admitted private HG GPU smokes; no reader, queue or next job."""
import argparse
import csv
import math
import os
import re
import shutil
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
import psutil
import c08_h18_wend_matrix_r1 as m

T, C, L = m.T, m.C, m.L
SCRIPT = Path(__file__).resolve()
NOTE = T / 'notes/c08_h18_hg_cached_jobs_r1.md'
THREAD = '01a07683-bc64-7463-8db7-9ee6243967d8'
CONTROL = 'c08_h18_as03_n255_r1'
ENVIRONMENT = 'C08_HG_CACHED_H18'
OPERATOR = 'EnergyNormalizedAdjointLoadingOnlyCachedMaterial'
DT, PRESTEP = .000005, 2000000
SAN = Path('C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v11.7/compute-sanitizer/compute-sanitizer.exe')
JOBS = {
    'off1': dict(tag='c08_h18_hg_cached_off1_r1', configuration='Release', on=False,
                 steps=(2000001,), updates=1, frames=1),
    'debug2': dict(tag='c08_h18_hg_cached_debug2_r1', configuration='Debug', on=True,
                   steps=(2000001, 2000002), updates=2, frames=2),
}


def paths(job):
    suffixes = dict(prep='.prepare.json', prepare_admission='.root_prepare_admission.json',
                    run_admission='.root_run_admission.json', start='.start.json',
                    call='.call.json', log='.log', run='.run.json', status='.status.json',
                    completed='.solver_completed.json')
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
           and not q.get('terminal_queue', False) and not q.get('watcher', False),
           'Separate exact current-root prepare/run admission required')
    return q


def copy_exact(source, target):
    source, target = Path(source), Path(target)
    m.need(not target.exists(), 'Existing copied input protected')
    shutil.copy2(source, target)
    m.need(target.read_bytes() == source.read_bytes(), 'Copied input is not byte-identical')
    return m.stat(target)


def clock_plan(job, source_time, original_rows):
    keys = ['part', 'completed_step', 'saved_step', 'time_s', 'dt_s']
    m.need(len(original_rows) == 91 and list(original_rows[0]) == keys,
           'Original unchanged91 receiver plan required')
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
    return rows, source_clocks, clock


def private_build(profile, original):
    job = JOBS[profile]
    path = L / ('c08_h18_hg_cached_' + job['configuration'] + '_r1.build.json')
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
           and b['Debug_first_n_snapshot_macro_enabled'] == (profile == 'debug2'),
           'Exact separately passed private111+3 cached HG build required')
    entries = [m.stat(path)]
    entries += [m.bind(b[key]) for key in ('program', 'source_capture', 'source_archive', 'baseline_source_capture')]
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
           and cap['baseline_source_capture'] == original['source_capture'],
           'Actual reversible private HG host/CUDA source proof required')
    for entry in b['calls']:
        entries.append(m.bind(entry))
        call = m.read(entry['path'])
        m.need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0
               and call['ownership_failure'] is None, 'Actual private build tool exits must pass')
    return path, b, entries


def prepare(profile):
    job, before = JOBS[profile], []
    p = paths(job)
    out = T / 'outputs' / job['tag']
    config = T / 'configs' / (job['tag'] + '_Def.xml')
    stepfile = T / 'configs' / (job['tag'] + '.steps.csv')
    m.need(not out.exists() and not config.exists() and not stepfile.exists()
           and all(not p[key].exists() for key in ('prep', 'run', 'start', 'call', 'log', 'status', 'completed')),
           'Existing complete/partial profile is protected; no retry')
    try:
        bp = L / ('c08_h18_hg_cached_' + job['configuration'] + '_r1.build.json')
        admission(p['prepare_admission'], profile, 'prepare', bp)
        cr, cp = L / (CONTROL + '.run.json'), L / (CONTROL + '.prepare.json')
        cn, cv = L / 'c08_h18_as03_n255_native_r1.check.json', L / 'c08_h18_as03n255_review_r1.check.json'
        original, prepared, native, review = map(m.read, (cr, cp, cn, cv))
        m.need(original['passed'] and original['solver_completed'] and original['consumed_stats_unchanged']
               and original['actual_exit'] == original['actual_Win32_exit'] == original['actual_tool_exit'] == 0
               and original['actual_steps'] == 2180000 and original['saved_frames'] == 91
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
               and source['samples'] == 1001 and source['soil_IDs'] == 5000 and source['fixed_IDs'] == 2060
               and source['declared_Kernel_XML_CSV'] == 2,
               'Original certified schema2 same-material Wendland PRE required, not equilibrium proof')
        bp, b, build_entries = private_build(profile, original)
        before += build_entries
        definition = m.bind(prepared['configuration'])
        before.append(definition)
        tree = ET.parse(original['input_xml']['path']).getroot()
        params = {q.get('key'): q.get('value') for q in tree.findall('execution/parameters/parameter')}
        m.need(len(params) == len(tree.findall('execution/parameters/parameter'))
               and all(float(params[key]) == value for key, value in dict(Kernel=2, DtFixed=DT,
                       TimeMax=10.9, TimeOut=.01, SoilHourglassXi=0, NoPenetration=1, SavePosDouble=1).items())
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
        m.need(len(original['seed']) == 3, 'Original generated triple required')
        seeds = []
        for suffix in ('.xml', '.bi4', '_Normals.nbi4'):
            leaf = Path(str(seed) + suffix)
            entry = next(q for q in original['seed'] if Path(q['path']).resolve() == leaf.resolve())
            seeds.append(m.bind(entry))
            before.append(entry)
        rows, source_clocks, end = clock_plan(job, source['actual_end_s'], m.table(original['planned_steps']['path']))
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
            private_sources=b['private_sources'], runtime=b['runtime'],
            source_pre_file=original['source_pre_file'], source_run=original['source_run'], source_native=original['source_native'],
            control_run=m.stat(cr), control_native=m.stat(cn), control_review=m.stat(cv),
            control_original_plan=original['planned_steps'], configuration_xml=copied_definition,
            input_xml=copied_seeds[0], seed=copied_seeds, native_profile=copied_profile,
            planned_steps=m.stat(stepfile), planned_rows=rows, save_source_clocks_s=source_clocks,
            actual_source_time_s=source['actual_end_s'], planned_actual_end_s=end,
            global_nsteps_limit=job['steps'][-1], new_updates=job['updates'], expected_saved_frames=job['frames'],
            fixed_dt_s=DT, environment_override={ENVIRONMENT: '1' if job['on'] else None},
            argv=argv, cwd=str(C), output=str(out), execution_script=m.stat(SCRIPT), note=m.stat(NOTE),
            root_prepare_admission=m.stat(p['prepare_admission']), consumed=before, consumed_stats_unchanged=True,
            seed_copied_byte_identical=True, generated_basename_preserved=seed.name, old91_plan_unchanged=True,
            HG_sidecar_review_pending=True, solver_invocations=0, GenCase_invocations=0, reader_invocations=0,
            VTK_invocations=0, SHA_scans=0, physical_acceptance=False, automatic_next_job=False,
            terminal_queue=False, watcher=False))
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


def run(profile):
    job, before, prep, call = JOBS[profile], [], None, None
    p = paths(job)
    out = T / 'outputs' / job['tag']
    bp = L / ('c08_h18_hg_cached_' + job['configuration'] + '_r1.build.json')
    m.need(all(not p[key].exists() for key in ('run', 'start', 'call', 'log', 'status', 'completed')),
           'Existing owned attempt/completion/partial protected; never rerun')
    result = dict(stage=job['tag'], passed=False, solver_completed=False, profile=profile,
        configuration=job['configuration'], HG_requested=job['on'], solver_invocations=0,
        solver_launch_attempts=0, native_review_pending=True, HG_sidecar_review_pending=True,
        physical_acceptance=False, GenCase_invocations=0, reader_invocations=0, VTK_invocations=0,
        SHA_scans=0, automatic_next_job=False, terminal_queue=False, watcher=False,
        unsaved_state_reconstructed=False)
    try:
        prep = m.read(p['prep'])
        ad = admission(p['run_admission'], profile, 'run', bp)
        m.need(prep['passed'] and prep['prepared_only'] and prep['consumed_stats_unchanged']
               and prep['profile'] == profile and prep['configuration'] == job['configuration']
               and prep['HG_requested'] == job['on'] and prep['execution_script'] == m.stat(SCRIPT)
               and prep['note'] == m.stat(NOTE) and ad['preparation'] == m.stat(p['prep']),
               'Independent exact prepared-job run admission required')
        before = [m.stat(q) for q in (SCRIPT, NOTE, p['prep'], p['run_admission'])]
        before += [m.bind(prep[key]) for key in ('program', 'source_build', 'source_capture', 'source_archive',
            'baseline_source_capture', 'source_pre_file', 'source_run', 'source_native', 'control_run',
            'control_native', 'control_review', 'control_original_plan', 'configuration_xml',
            'input_xml', 'native_profile', 'planned_steps')]
        before += [m.bind(q) for q in prep['seed'] + prep['runtime'] + list(prep['private_sources'].values())]
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
            consumed=before, automatic_native=False, automatic_next_job=False, terminal_queue=False,
            physical_acceptance=False))
        result.update({key: prep[key] for key in ('program', 'source_build', 'source_capture', 'source_archive',
            'baseline_source_capture', 'private_sources', 'runtime', 'source_pre_file', 'source_run',
            'source_native', 'control_run', 'control_native', 'control_review', 'control_original_plan',
            'configuration_xml', 'input_xml', 'seed', 'planned_steps', 'native_profile', 'actual_source_time_s',
            'planned_actual_end_s', 'global_nsteps_limit', 'new_updates', 'expected_saved_frames', 'environment_override')})
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
        terminal_queue=False, watcher=False, physical_acceptance=False))
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
