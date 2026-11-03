"""One later native read of the completed, fixed CPU1 mid2 run. Never a solver or retry."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import time
import types

import psutil

T = Path(__file__).resolve().parents[1]
NAME = 'upl_hg_mid2_native_run_r1'
TAG = 'upl_hg_mid2_CPU1_coarse_r1'
OUT = T / 'outputs' / TAG
NATIVE = T / 'outputs' / (TAG + '_native')
N, DT, EVENT, STEPS = 1517, 2.0 ** -19, 5243, 1048576
SAVE = sorted(set(range(0, 65537, 64)) | set(range(5120, 5377)) |
              set(range(66560, 262145, 1024)) | set(range(278528, 1048577, 16384)))
PINS = {
    'support/upl_hg_mid2_run_r1.py': (27672, '1a0c59f65f207a08b96833b941c51eac270d7c9f527a3f4137b02df1796904ca'),
    'notes/upl_hg_mid2_run_r1.json': (4597, 'b9d64c093500bfb7e70887ca5fe8ee4c384fd8f271367f9019523209fd39ebfd'),
    'support/upl_hg_column_short_review_r1.py': (31041, '39067679271b7b56413710f0c94643692451d17b96eba0cf497a91b192351dc9'),
    'notes/upl_hg_column_short_review_r1.json': (5645, 'b97f028987e14aa6c04ebeb22071cc8d088184609691d997a83e26f57a26c8e1'),
    'logs/upl_hg_mid2_CPU1_coarse_r1.start.json': (407752, '44c6009766d8b2d40da87e983a8a9712e20001e6452c2d7bb94cb68729b26ec9'),
    'logs/upl_hg_mid2_r1.inputs.json': (1593497, 'b595ea644faf20d8dadaace5e58980066128a596db1c8ffa07edde2ce015da9f'),
    'logs/upl_hg_mid2_reader_ReleaseCPU_r1.helper.json': (532547, 'd3d86f3ed7647d32b457a48bd253160b197ae8d955adae097b708aac8e5dab5c'),
}
LEAVES = {'original15.bin', 'physical.bin', 'clock.bin', 'common_j_theta.bin', 'soil_n.bin',
          'native_ids.csv', 'fixed_ids.csv', 'history.csv', 'ledger.csv', 'fixed_samples.csv',
          'last_poro.csv', 'columns.csv', 'completion.json'}


def utc():
    return datetime.now(timezone.utc).isoformat()


def load_definitions(relative, module_name):
    path = T / relative
    raw = path.read_bytes()
    if (len(raw), hashlib.sha256(raw).hexdigest()) != PINS[relative]:
        raise ValueError('Pinned pure definitions changed: ' + relative)
    module = types.ModuleType(module_name)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)  # Non-main definitions only, never its main or call function.
    return module


def definitions():
    owner = load_definitions('support/upl_hg_mid2_run_r1.py', 'frozen_mid2_owner_definitions')
    schema = load_definitions('support/upl_hg_column_short_review_r1.py', 'frozen_native_schema_definitions')
    for name, (size, digest) in PINS.items():
        owner.bind(dict(path=str((T / name).resolve()), bytes=size, sha256=digest))
    return owner, schema


def raw_closure(owner, run):
    owner.need(Path(run['output_directory']).resolve() == OUT.resolve(), 'Source run output directory differs')
    paths = {Path(e['path']).resolve() for e in run['files']}
    owner.need(len(paths) == len(run['files']) and all(path.is_relative_to(OUT.resolve()) for path in paths) and
               paths == {path.resolve() for path in OUT.rglob('*') if path.is_file()}, 'Frozen raw solver membership changed')
    owner.need(sorted(path.name for path in (OUT / 'data').glob('Part_*.bi4') if path.is_file()) ==
               ['Part_%04d.bi4' % i for i in range(N)], 'Exactly 1517 sequential raw PART files required')
    for e in run['files']:
        owner.bind(e)


def completed_solver(owner):
    # Only the actual fixed Python owner and its genuine future successful seal can admit a decode.
    run_path = T / 'logs' / (TAG + '.run.json')
    owner.need(run_path.is_file(), 'The fixed solver has no completed run seal; no reader is admitted')
    run_e = owner.adopt(run_path)
    run = owner.read(run_e)
    owner.need(owner.entry(run_path) == run_e, 'Solver run seal changed while read')
    start_e = dict(path=str((T / 'logs' / (TAG + '.start.json')).resolve()),
                   bytes=PINS['logs/' + TAG + '.start.json'][0], sha256=PINS['logs/' + TAG + '.start.json'][1])
    start = owner.read(start_e)
    exact = dict(stage='upl_hg_mid2_run_r1', tag=TAG, passed=True, backend='CPU', configuration='ReleaseCPU',
        window='coarse', threads=1, steps=STEPS, native_frames=N, bindings_unchanged=True,
        physical_acceptance=False, half_or_formal_jobs_admitted=False, public_project_main=True,
        fixture_or_Run_override=False, native_decoder_invoked=False, all22_native_fields_review_pending=True,
        actual_native_clocks_review_pending=True, direct_owner_no_scheduler=True, automatic_follow_up=False)
    owner.need(all(run.get(k) == v for k, v in exact.items()) and run.get('failure') is None and
               run['start_record'] == start_e, 'A completed genuine CPU1 mid2 solver seal is required')
    owner.need(start['stage'] == 'upl_hg_mid2_start_r1' and start['tag'] == TAG and
               start['owner']['pid'] == 33092 and start['owner']['created_epoch'] == 1793694119.7353027 and
               start['owner_script']['sha256'] == PINS['support/upl_hg_mid2_run_r1.py'][1] and
               start['native_call_started_by_start_record'] is False and start['physical_acceptance'] is False,
               'Actual original start/PID/creation/source identity differs')
    build_e, build = owner.build_closure()
    manifest_e, manifest, job = owner.prepared_job(build_e, build)
    helper_e = owner.reader_closure(build_e, build, manifest_e)
    helper = owner.read(helper_e)
    admission_e = owner.admission(Path(run['admission']['path']), manifest_e, helper_e)
    owner.need(run['job'] == start['job'] == job and run['source_build'] == start['source_build'] == build_e and
               run['program'] == start['program'] == build['program'] and
               run['input_manifest'] == start['input_manifest'] == manifest_e and
               run['reader_helper'] == start['reader_helper'] == helper_e and
               owner.same_entry(run['admission'], admission_e) and start['admission'] == run['admission'] and
               run['source_input_manifest'] == manifest['source_input_manifest'] and run['source_job'] == manifest['source_job'],
               'Actual run/start/current build/input/admission/reader provenance differs')
    owner.need(helper['program']['bytes'] == 513536 and
               helper['program']['sha256'] == '2cda7e9a223fa0618f1b065126968b24871a29461966d1f29b95a539807ebfbf',
               'Only the actual frozen built mid2 reader is allowed')
    for e in start['inputs'] + run['inputs']:
        owner.bind(e)
    call_e = run['call']
    owner.need(Path(call_e['path']).resolve() == (T / 'logs' / (TAG + '.call.json')).resolve(), 'Source solver call path differs')
    call = owner.read(call_e)
    owner.need(call['stage'] == 'upl_hg_mid2_call_r1' and call['tag'] == TAG and call['configuration'] == 'ReleaseCPU' and
               call['window'] == 'coarse' and call['program'] == call['target_program'] == build['program'] and
               call['arguments'] == call['target_arguments'] == run['arguments'] == start['arguments'] == job['arguments'] and
               Path(call['working_directory']).resolve() == owner.SRC.resolve() and call['start_record'] == start_e and
               call['direct_native_call'] is True and call['shell'] is False and call['owned_call_exited'] is True and
               call['typed_returncode_captured_immediately'] is True and type(call['exit_code']) is int and call['exit_code'] == 0 and
               call['invocation_failure'] is None and call['actual_solver_call'] is True and call['public_project_main'] is True and
               call['fixture_or_Run_override'] is False and call['restart'] is False and call['physical_acceptance'] is False,
               'Real original Python solver call/target/argv/integer returncode differs')
    owner.bind(call['program']); owner.bind(call['log']); owner.bind(run['run_out'])
    raw_closure(owner, run)
    observed = {}
    owner.check_output(observed)  # Same frozen Run.out HG counters/cache/current-J/tau/spin/sequence predicates; no program call.
    owner.need(observed['HG'] == run['HG'] and observed['steps'] == STEPS and observed['native_frames'] == N,
               'Original solver HG diagnostics or actual PART sequence changed')
    return dict(run=run, run_entry=run_e, start=start_e, call=call_e, manifest=manifest_e,
                source_build=build_e, helper_entry=helper_e, helper=helper, job=job)


def reader_call(owner, context):
    program = context['helper']['program']
    arguments = ['--read', 'CPU', str(OUT / 'data'), 'coarse', str(NATIVE)]
    receipt, log = T / 'logs' / (TAG + '_reader.call.json'), T / 'logs' / (TAG + '_reader.log')
    owner.fresh(receipt, log, NATIVE)
    active = []
    for process in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'create_time']):
        name = (process.info['name'] or '').lower()
        if (name.startswith('dualsphysics') and 'cpu' in name and name.endswith('.exe')) or name == 'upl_hg_mid2_native_r1.exe':
            active.append(process.info)
    owner.need(not active, 'An actual CPU solver or mid2 reader is active; no concurrent or duplicate decode')
    me = psutil.Process()
    identity = dict(pid=me.pid, created_epoch=me.create_time(), exe=me.exe(), command=me.cmdline(), cwd=str(Path.cwd().resolve()))
    code = failure = None
    started, wall = utc(), time.perf_counter()
    try:
        with log.open('xb') as stream:
            completed = subprocess.run([program['path'], *arguments], cwd=T.parent, stdout=stream,
                stderr=subprocess.STDOUT, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
            code = completed.returncode  # First operation after the single unchanged native reader returns.
    except Exception as exc:
        failure = str(exc)
    owner.seal(receipt, dict(stage='upl_hg_mid2_reader_call_r1', tag=TAG, program=program, target_program=program,
        arguments=arguments, target_arguments=arguments, working_directory=str(T.parent), owner=identity,
        owner_script=owner.adopt(__file__), source_run=context['run_entry'], source_start=context['start'],
        started_utc=started, ended_utc=utc(), direct_native_call=True, shell=False,
        typed_returncode_captured_immediately=type(code) is int, owned_call_exited=type(code) is int,
        exit_code=code, invocation_failure=failure, log=owner.entry(log) if log.exists() else None,
        invocation_wall_seconds=time.perf_counter() - wall, pure_native_reader=True,
        solver_or_build_invoked=False, physical_acceptance=False))
    call_e = owner.adopt(receipt)
    actual = owner.read(call_e)
    if actual['log']:
        owner.bind(actual['log'])
    return call_e, code, failure


def exports(owner, schema, native_dir, files, completion):
    """Pure fixed-1517 export validation, usable later without any producer or provenance function."""
    need, np = owner.need, schema.np
    directory = Path(native_dir).resolve()
    leaves = {Path(e['path']).name: e for e in files}
    need(len(files) == len(leaves) == 13 and set(leaves) == LEAVES and leaves['completion.json'] == completion and
         all(Path(e['path']).resolve().parent == directory for e in files) and
         {path.name for path in directory.iterdir()} == LEAVES, 'Exactly thirteen unmodified native export leaves required')
    for e in files:
        schema.bind(e)
    done = schema.read(completion)
    exact = dict(stage='upl_hg_mid2_native_r1', backend='CPU_public', window='bounded_2s', preset='coarse', grid='c',
        model='constant', conductivity_model=0, conductivity_Ck=0, native_count=1000, fixed_count=40,
        total_native_count=1040, samples=N, physical_columns=26, physical_schema=schema.SCHEMA,
        original_typed_arrays=15, native_dynamic_double_arrays=6, native_total_arrays=22, dt_s=DT,
        actual_end_s=2, planned_end_s=2, planned_completed_steps=STEPS, declared_ramp_and_drain_event_s=EVENT * DT,
        noninitial_signed_dterror_intervals=1516, soil_ledger_checks=1517000, fixed_public_zero_marker_checks=60680,
        all_native_J_theta_rows=1577680, soil_native_n_rows=1517000, post_open_completed_step_threshold=EVENT,
        post_open_frames=1313, post_open_drained_particle_checks=13130, max_activeDrainCount=10)
    required = ('public_schema', 'public_master_on', 'PART_typed_public_metadata_verified', 'native_PosDiv_present',
        'native_PosDiv_is_float', 'native_V_rho_k_present', 'no_exclusions', 'initial_rest_and_decimal_lattice_verified',
        'double_stress_and_float_display_verified', 'all_exported_physical_fields_finite', 'declared_saved_completed_steps_exact',
        'actual_time_step_locked_dt_exact', 'initial_dterror_excluded_from_noninitial_summary',
        'fixed_J_theta_original15_not_zeroed_or_masked', 'common26_column21_is_actual_ExcessPorePress',
        'pre_open_event_pressure_not_forced_zero', 'density_and_J_not_frozen_on_drained_receivers',
        'event_is_declared_preset_not_BI4_metadata', 'descriptive_saved_field_summaries')
    forbidden = ('GPU_private_fixed_n_mirror_to_public_zero_is_schema_change', 'PosDiv_fabricated_or_derived',
        'new_scientific_acceptance_gate', 'same_force_stage_load_budget_verified', 'force_stage_guard_independently_observed',
        'historical_private_comparison_performed_by_reader', 'backend_argument_proved_from_owned_program',
        'input_SHA_or_owned_solver_exit_verified_by_reader', 'live_final_compared_by_reader',
        'drainage_nonempty_acceptance_claimed', 'independent_half_performed', 'physical_acceptance')
    need(done.get('passed') is True and all(done.get(k) == v for k, v in exact.items()) and
         all(done.get(k) is True for k in required) and all(done.get(k) is False for k in forbidden),
         'Actual mid2 completion schema/counts/original unmasked guard scopes differ')
    need(type(done['initial_empty_dterror_intervals']) is int and done['initial_empty_dterror_intervals'] in (0, 1) and
         all(math.isfinite(done[k]) for k in ('min_noninitial_signed_dterror_s', 'max_noninitial_signed_dterror_s', 'max_ledger_relative_error')) and
         done['min_noninitial_signed_dterror_s'] <= done['max_noninitial_signed_dterror_s'] <= 1e-14 and
         0 <= done['max_ledger_relative_error'] <= 5e-13, 'Original signed noninitial/finite ledger bounds differ')
    headers = []
    for name, header, stride in (('original15.bin', (1040, 15, N), 166408), ('physical.bin', (1000, 26, N), 208008),
        ('clock.bin', (N, 28), 28), ('common_j_theta.bin', (1040, 2, N), 16648), ('soil_n.bin', (1000, 1, N), 8008)):
        path = schema.bind(leaves[name])
        with path.open('rb') as stream:
            need(struct.unpack('<' + 'I' * len(header), stream.read(4 * len(header))) == header, 'Binary header differs: ' + name)
        need(path.stat().st_size == 4 * len(header) + N * stride, 'Binary length differs: ' + name)
        headers.append(dict(file=leaves[name], header=header, record_bytes=stride, length_verified=True))
    p = schema.mapped(leaves['physical.bin'], (1000, 26, N), [('time', '<f8'), ('q', '<f8', (1000, 26))], N)
    raw = schema.mapped(leaves['original15.bin'], (1040, 15, N), [('time', '<f8'), ('payload', 'V166400')], N)
    clock = schema.mapped(leaves['clock.bin'], (N, 28), [('time', '<f8'), ('step', '<u4'), ('dt', '<f8'), ('error', '<f8')], N)
    jt = schema.mapped(leaves['common_j_theta.bin'], (1040, 2, N), [('time', '<f8'), ('q', '<f8', (1040, 2))], N)
    n = schema.mapped(leaves['soil_n.bin'], (1000, 1, N), [('time', '<f8'), ('q', '<f8', (1000,))], N)
    times = np.asarray(SAVE, dtype=np.int64) * DT
    need(len(SAVE) == N and SAVE[-1] == STEPS and all(schema.bits(a['time'], times) for a in (p, raw, clock, jt, n)) and
         schema.bits(clock['dt'], np.full(N, DT)) and
         np.array_equal(clock['step'], np.where(np.asarray(SAVE) > 0, np.asarray(SAVE) - 1, 0)) and
         np.isfinite(clock['error']).all() and np.all(clock['error'][1:] <= 1e-14) and
         np.all(clock['error'][1:] != -np.finfo(float).max), 'Actual dyadic binary clock/Step/locked dt or signed interval differs')
    need(float(np.min(clock['error'][1:])) == done['min_noninitial_signed_dterror_s'] and
         float(np.max(clock['error'][1:])) == done['max_noninitial_signed_dterror_s'] and
         int(clock['error'][0] == -np.finfo(float).max) == done['initial_empty_dterror_intervals'] and
         (clock['error'][0] == -np.finfo(float).max or clock['error'][0] <= 1e-14), 'Actual original signed sentinel/summary semantics differ')
    positions = {}
    for kind, count, first in (('native', 1000, 40), ('fixed', 40, 0)):
        rows = schema.csv_rows(leaves[kind + '_ids.csv'])
        need(len(rows) == count and all((int(row['row']), int(row['id'])) == (i, first + i) for i, row in enumerate(rows)),
             'All 1040 original native/fixed IDs differ')
        positions[kind] = np.asarray([[float(row[k]) for k in ('x0', 'y0', 'z0')] for row in rows])
        need(np.isfinite(positions[kind]).all(), 'Nonfinite original coordinates')
    need(schema.bits(p['q'][0, :, :3], positions['native']), 'Initial material coordinate export differs')
    columns = schema.csv_rows(leaves['columns.csv'])
    need([row['name'] for row in columns] == schema.FIELDS and [int(row['column']) for row in columns] == list(range(26)),
         'All 26 original column semantics, including actual ExcessPorePress, are required')
    history = schema.csv_rows(leaves['history.csv'])
    need(len(history) == N, 'Exactly 1517 history rows required')
    post_frames = actual_receivers = 0
    n0 = float(np.float32(.3))
    for i, row in enumerate(history):
        completed, post = SAVE[i], SAVE[i] > EVENT
        need((int(row['part']), int(row['completed_step']), int(row['saved_step']),
              int(row['post_open_by_completed_step']), int(row['activeDrainCount'])) ==
             (i, completed, completed - 1 if i else 0, int(post), 10 if post else 0) and
             schema.bits(float(row['time_s']), times[i]) and schema.bits(float(row['dt_s']), DT) and
             schema.bits(float(row['signed_dterror_s']), clock['error'][i]) and
             0 <= float(row['max_ledger_relative_error']) <= 5e-13,
             'Per-history actual clock/Step/drain-mask/ledger differs')
        error = float(row['signed_dterror_s'])
        need(math.isfinite(error) and int(row['dterror_used_in_noninitial_summary']) == int(i > 0) and
             int(row['dterror_interval_empty']) == int(error == -np.finfo(float).max) and
             ((int(row['dterror_interval_empty']) == 0 and error <= 1e-14) if i else
              (int(row['dterror_interval_empty']) == 1 or error <= 1e-14)), 'Original signed interval/sentinel was changed or omitted')
        values, common, porosity = p['q'][i], jt['q'][i], n['q'][i]
        need(np.isfinite(values).all() and np.isfinite(common).all() and np.isfinite(porosity).all() and
             schema.bits(values[:, 8:10], common[40:]) and np.all(common[:40, 1] == 0) and
             np.all(common[:, 0] > 1 - n0) and np.all((porosity > 0) & (porosity < 1)) and
             np.all(np.abs((1 - porosity) * common[40:, 0] - (1 - n0)) <= 5e-13),
             'Finite unmasked all-ID J/theta or original single-J soil ledger export differs')
        fstype = values[:, 17]
        need(np.all((fstype >= 0) & (fstype <= 4) & (fstype == np.floor(fstype))), 'Actual FSType export is not its original native integer class')
        mask = ((fstype == 2) | (fstype == 3)) & post
        count = int(np.count_nonzero(mask))
        need(count == (10 if post else 0) and count == int(row['activeDrainCount']) and
             np.all(values[mask, 6] == 0), 'Actual post-open FSType 2/3 pressure-zero receiver coverage differs')
        post_frames += int(post); actual_receivers += count
    need(post_frames == 1313 and actual_receivers == 13130, 'Actual nonempty post-opening frame/receiver totals differ')
    final = schema.csv_rows(leaves['last_poro.csv'])
    need(len(final) == 1000 and all(int(row['id']) == i + 40 and all(math.isfinite(float(row[k])) for k in ('J', 'n', 'theta'))
                                  for i, row in enumerate(final)), 'Final all-soil J/n/theta rows differ')
    final_values = np.asarray([[float(row[k]) for k in ('J', 'n', 'theta')] for row in final])
    need(schema.bits(final_values[:, 0], jt['q'][-1, 40:, 0]) and schema.bits(final_values[:, 1], n['q'][-1]) and
         schema.bits(final_values[:, 2], jt['q'][-1, 40:, 1]), 'Final J/n/theta text and actual binary exports differ')
    return dict(p=p, raw=raw, clock=clock, jt=jt, n=n, x0=positions['native'], fixed_x0=positions['fixed'],
        columns=columns, history=history, headers=headers, leaves=leaves, completion=done,
        post_open_frames=post_frames, actual_drained_receiver_checks=actual_receivers)


def final_bindings(owner, schema):
    combined = {}
    for e in list(owner.BOUND.values()) + list(schema.BOUND.values()):
        key = str(Path(e['path']).resolve()).casefold()
        owner.need(key not in combined or owner.same_entry(combined[key], e), 'Conflicting consumed binding caches')
        combined[key] = e
    for e in combined.values():
        owner.need(owner.entry(e['path']) == e, 'Consumed input/raw/native file changed during independent final rehash: ' + e['path'])
    if owner.SOURCE_MEMBERSHIP is not None:
        owner.need(owner.source_members() == owner.SOURCE_MEMBERSHIP, 'Current 265 source/header membership changed')
    return list(combined.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    if not args.execution_authorized:
        raise ValueError('Root must full-read this new native owner before explicitly authorizing one completed-run decode')
    record, call_path, log = (T / 'logs' / (TAG + suffix) for suffix in ('.native.json', '_reader.call.json', '_reader.log'))
    if any(path.exists() for path in (record, call_path, log, NATIVE)):
        raise ValueError('Fresh-only native owner; retain completed/failed/partial decode evidence without rerunning')
    owner = schema = context = None
    result = dict(stage=NAME, tag=TAG, passed=False, backend='CPU', configuration='ReleaseCPU', window='coarse',
        physical_acceptance=False, reader_executed_by_this_action=False, adopted_completed_reader=False,
        reader_invocation_attempt_recorded=False, solver_or_build_invoked=False, automatic_follow_up=False, failure=None)
    try:
        owner, schema = definitions()
        for path in (__file__, T / 'notes/upl_hg_mid2_native_run_r1.json', sys.executable, psutil.__file__, schema.np.__file__):
            owner.adopt(path)
        context = completed_solver(owner)
        result.update(job=context['job'], source_run=context['run_entry'], source_start=context['start'],
            source_call=context['call'], input_manifest=context['manifest'], source_build=context['source_build'],
            program=context['run']['program'], reader_helper=context['helper_entry'],
            paths=dict(solver_dir=str(OUT), native_dir=str(NATIVE)))
        owner.reverify()
        # The real reader call is sealed before any completion, binary or CSV analysis.
        result['reader_call'], code, failure = reader_call(owner, context)
        result['reader_invocation_attempt_recorded'] = True
        result['reader_executed_by_this_action'] = type(code) is int
        owner.need(type(code) is int and code == 0 and failure is None,
                   'Actual native reader did not return integer zero; preserve its call and outputs')
        result['completion'] = owner.adopt(NATIVE / 'completion.json')
        result['files'] = [owner.adopt(path) for path in sorted(NATIVE.iterdir()) if path.is_file()]
        checked = exports(owner, schema, NATIVE, result['files'], result['completion'])
        result.update(binary_header_length_checks=checked['headers'], history_rows=N,
            original_native_guards_passed=True, typed_native_total_arrays=22, typed_native_total_ID_count=1040,
            typed_soil_ledger_checks=1517000, typed_fixed_zero_marker_checks=60680,
            typed_all_native_J_theta_rows=1577680, ledger_CSV_rows_reparsed=0, fixed_samples_CSV_rows_reparsed=0,
            post_open_frames_verified=checked['post_open_frames'], actual_drained_receiver_checks=checked['actual_drained_receiver_checks'],
            drainage_nonempty_per_frame_verified=True, physical_FSType_receiver_mask_independently_recounted=True,
            saved_step_plan_verified=True, signed_noninitial_dterror_intervals_verified=1516,
            reader_rebuilt=False, historical_reader_originals_asserted_current=False,
            independent_mid_half_or_theory_performed=False, actual_prefix_proved=False)
        raw_closure(owner, context['run'])
        result['passed'] = True
    except Exception as exc:
        result['failure'] = str(exc)
    if owner is not None:
        if NATIVE.exists() and 'files' not in result:
            try:
                result['files'] = [owner.adopt(path) for path in sorted(NATIVE.rglob('*')) if path.is_file()]
            except Exception as exc:
                result['failure'] = ((result['failure'] + '; ') if result['failure'] else '') + 'Partial inventory failed: ' + str(exc)
                result['passed'] = False
        try:
            if schema is None:
                raise ValueError('Pure native schema definitions were not available')
            if context is not None:
                raw_closure(owner, context['run'])
            result['inputs'] = final_bindings(owner, schema)
            result['bindings_unchanged'] = result['independent_final_rehash_performed'] = True
        except Exception as exc:
            result['inputs'] = list(owner.BOUND.values()) + (list(schema.BOUND.values()) if schema is not None else [])
            result['bindings_unchanged'] = result['independent_final_rehash_performed'] = False
            result['failure'] = ((result['failure'] + '; ') if result['failure'] else '') + str(exc)
            result['passed'] = False
    else:
        result.update(inputs=[], bindings_unchanged=False, independent_final_rehash_performed=False)
    result.update(saved_final_J_weighted_load_is_descriptive_only=True, same_force_stage_load_budget_verified=False,
        force_stage_guard_independently_observed=False, source_or_metadata_or_values_masked=False,
        existing_solver_or_reader_receipts_rewritten=False, following_action_launched=False)
    # Exclusive receipt creation also preserves a genuine completed reader if a later check fails.
    with record.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(passed=result['passed'], receipt=str(record), failure=result['failure'])))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
