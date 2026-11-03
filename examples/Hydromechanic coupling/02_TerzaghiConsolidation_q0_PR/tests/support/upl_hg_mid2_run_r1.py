"""One explicitly admitted CPU1 HG project-main run to 2 s; no decoder or following action."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time

import psutil

T = Path(__file__).resolve().parents[1]
SRC = T.parents[3] / 'src'
NAME = 'upl_hg_mid2_run_r1'
TAG = 'upl_hg_mid2_CPU1_coarse_r1'
OUT = T / 'outputs' / TAG
PREFIX = T / 'outputs/upl_hg_mid2_seed_r1/upl_hg_mid2_coarse_r1'
STEPS, FRAMES, DT = 1048576, 1517, 2.0 ** -19
COUNTERS = dict(forcecalls=2097152, ratecalls=2097152, predictorupdates=1048576,
                correctorupdates=1048576, ratecalculations=1048577, ratecachehits=1048575)
PINS = {
    'logs/upl_hg_column_ReleaseCPU_r1.build.json': (455112, 'f01ccdaf1c86ec036c598eba888a57d4d9b69d80839d76ccf7b4dc731cc19975'),
    'logs/upl_hg_cpu1_short_r1.compare.json': (21010, '21eb787965b20dce4d819693492e891e08712a0b66fc10e6757bd9c557a9431b'),
    'logs/upl_hg_column_full_review_r1_pair.check.json': (59862, '4f577bcfc5090e93505c8df20112dbc84694396e9078eff7185dcfe78644d2b0'),
}
GPU_REVIEW = T.parent.parent / '04_CryerProblem_PR/tests/logs/upl_cryer_gpu_component_Release_probe_r4_release_review_r1.check.json'
GPU_PIN = (263246, '3844c684f21b465552ce0fbf6e76b20a3079710b14ef744bad4a6f5b9f335b49')
BOUND = {}
SOURCE_MEMBERSHIP = None


def need(ok, why):
    if not ok:
        raise ValueError(why)


def utc():
    return datetime.now(timezone.utc).isoformat()


def entry(path):
    path = Path(path).resolve(strict=True)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def bind(expected):
    key = str(Path(expected['path']).resolve()).casefold()
    if key not in BOUND:
        BOUND[key] = entry(expected['path'])
    actual = BOUND[key]
    need(actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256'].lower(),
         'Changed consumed artifact: ' + expected['path'])
    return Path(actual['path'])


def adopt(path):
    key = str(Path(path).resolve()).casefold()
    if key not in BOUND:
        BOUND[key] = entry(path)
    return BOUND[key]


def same_entry(left, right):
    return ((str(Path(left['path']).resolve()).casefold(), left['bytes'], left['sha256'].lower()) ==
            (str(Path(right['path']).resolve()).casefold(), right['bytes'], right['sha256'].lower()))


def read(expected):
    return json.loads(bind(expected).read_text(encoding='utf-8-sig'))


def pin(name):
    size, digest = PINS[name]
    expected = dict(path=str((T / name).resolve()), bytes=size, sha256=digest)
    bind(expected)
    return expected


def fresh(*paths):
    need(all(not Path(path).exists() for path in paths), 'Retained path protected; never overwrite or retry')


def seal(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def inventory(directory):
    return [entry(path) for path in sorted(Path(directory).rglob('*')) if path.is_file()]


def reverify():
    for expected in list(BOUND.values()):
        need(entry(expected['path']) == expected, 'Consumed artifact changed during independent final rehash: ' + expected['path'])
    if SOURCE_MEMBERSHIP is not None:
        need(source_members() == SOURCE_MEMBERSHIP, 'Current 265 source/header membership changed')


def source_members():
    return {str(path.resolve()).casefold() for path in (SRC / 'source').iterdir()
            if path.is_file() and path.suffix.lower() in ('.cpp', '.h', '.cu', '.cuh')}


def typed_build(expected, log_required=False):
    call = read(expected)
    need(call.get('direct_native_call') is True and call.get('owned_call_exited') is True and
         call.get('typed_LASTEXITCODE_captured_immediately') is True and type(call.get('exit_code')) is int and
         call['exit_code'] == 0 and call.get('invocation_failure') is None, 'Actual retained typed build-tool exit zero required')
    bind(call['program'])
    need(not log_required or call.get('log') is not None, 'Actual retained compiler/linker call log required')
    if call.get('log') is not None:
        bind(call['log'])
    return call


def expected_arguments():
    return ['-cpu', '-ompthreads:1', '-stable', '-mdbc_freeslip', str(PREFIX), str(OUT),
            '-dirdataout', 'data', '-svres', '-nsteps:1048576']


def build_closure():
    global SOURCE_MEMBERSHIP
    build_e = pin('logs/upl_hg_column_ReleaseCPU_r1.build.json')
    build = read(build_e)
    need(build.get('stage') == 'upl_hg_column_build_r1' and build.get('passed') is True and
         build['configuration'] == 'ReleaseCPU' and build['platform'] == 'x64' and
         all(build.get(k) is True for k in ('source_bindings_unchanged', 'canonical_programs_unchanged',
             'runtime_unchanged', 'exact_object_basename_closure', 'objects_include_project_main')) and
         build['object_count'] == len(build['objects']) == 86 and build['non_main_object_count'] == 85 and
         len(build['source_snapshot']) == 265 and len(build['runtime']) == 4 and len(build['canonical_programs_before']) == 7 and
         build.get('old_objects_reused') is False and build.get('canonical_program_installed') is False and
         (build['program']['bytes'], build['program']['sha256']) ==
         (5115392, 'b5a44073b7303b7df917d01105d3cb0a20a0ca1a90a9a963ccb35be9b2b3530c'),
         'Genuine current authoritative CPU 86-object/265-source project-main build required')
    project = typed_build(build['project_call'])
    need(project['program']['sha256'] == build['build_tool']['sha256'] and project['arguments'] == build['arguments'],
         'Actual selected project build-tool arguments differ')
    for key in ('inputs', 'tools', 'libraries', 'objects', 'compile_sources', 'canonical_programs_before', 'runtime_before'):
        for e in build[key]:
            bind(e)
    for key in ('build_tool', 'program', 'log', 'binlog'):
        bind(build[key])
    for pair in build['source_snapshot'] + [build['documentation_snapshot'], build['case_readme_snapshot']]:
        need(all(pair['original'][k] == pair['snapshot'][k] for k in ('bytes', 'sha256')), 'Current source/archive pair differs')
        bind(pair['original']); bind(pair['snapshot'])
    SOURCE_MEMBERSHIP = {str(Path(pair['original']['path']).resolve()).casefold() for pair in build['source_snapshot']}
    need(len(SOURCE_MEMBERSHIP) == 265 and source_members() == SOURCE_MEMBERSHIP, 'Current 265 source/header membership differs')
    for pair in build['runtime']:
        need(all(pair['original'][k] == pair['copy'][k] for k in ('bytes', 'sha256')), 'Frozen runtime copy differs')
        bind(pair['original']); bind(pair['copy'])
    for pair in build['compiler_linker_command_tlogs']:
        bind(pair['original']); bind(pair['snapshot'])
    need(len({Path(e['path']).name.lower() for e in build['objects']}) == 86 and
         sum(Path(e['path']).name.lower() == 'main.obj' for e in build['objects']) == 1, 'Exact project-main object closure differs')
    return build_e, build


def prepared_job(build_e, build):
    manifest_e = adopt(T / 'logs/upl_hg_mid2_r1.inputs.json')
    manifest = read(manifest_e)
    need(manifest.get('stage') == 'upl_hg_mid2_prepare_r1' and
         all(manifest.get(k) is True for k in ('passed', 'prepared', 'input_and_generated_files_unchanged')) and
         manifest.get('solver_reader_or_build_invoked') is False and manifest.get('physical_acceptance') is False and
         manifest['source_build'] == build_e and manifest['source_program'] == build['program'] and
         len(manifest['jobs']) == 1 and len(manifest['files']) == 4, 'Successful independent mid2 preparation required')
    for e in manifest['inputs'] + manifest['files']:
        bind(e)
    bind(manifest['source_input_manifest'])
    job = manifest['jobs'][0]
    wanted = dict(tag=TAG, backend='CPU', configuration='ReleaseCPU', window='coarse', threads=1,
        input_variant='coarse', input_prefix=str(PREFIX), output_directory=str(OUT), arguments=expected_arguments(),
        steps=STEPS, dt_s=DT, end_s=2, expected_samples=FRAMES, event_completed_step=5243,
        post_open_frames=1313, post_open_drained_particle_checks_expected=13130,
        expected_native_total_arrays=22, expected_total_native_count=1040, expected_HG_counters=COUNTERS)
    need(all(job.get(k) == v for k, v in wanted.items()), 'Exact prepared CPU1 bounded coarse job differs')
    need(all(job.get(k) is True for k in ('inverse_DOM_exact', 'inverse_text_and_bytes_exact',
         'only_Xi_TimeMax_and_HG_comment_changed', 'original_five_timeouts_exact')) and
         job.get('initial_particle_fields_rewritten') is False, 'Original runtime inverse and seed-copy proof required')
    for key in ('runtime', 'configuration_file', 'initial_BI4', 'normals'):
        bind(job[key]); need(job[key] in manifest['files'], 'Prepared seed Entry is missing from generated file closure')
    source_job = manifest['source_job']
    need(all(job['initial_BI4'][k] == source_job['initial_BI4'][k] and job['normals'][k] == source_job['normals'][k]
             for k in ('bytes', 'sha256')) and
         all(job['configuration_file'][k] == job['runtime'][k] for k in ('bytes', 'sha256')),
         'Copied initial BI4/normals or matching configuration/runtime bytes differ')
    need(Path(job['runtime']['path']).resolve() == PREFIX.with_suffix('.xml').resolve() and
         Path(job['initial_BI4']['path']).resolve() == PREFIX.with_suffix('.bi4').resolve() and
         Path(job['configuration_file']['path']).resolve() == (T / 'configs/upl_hg_mid2_coarse_r1.xml').resolve(),
         'Prepared runtime/configuration/initial BI4 paths differ')
    clock = job['saved_clock_table']
    wanted_steps = sorted(set(range(0, 65537, 64)) | set(range(5120, 5377)) |
                          set(range(66560, 262145, 1024)) | set(range(278528, 1048577, 16384)))
    need(len(clock) == FRAMES and clock[0]['completed_steps'] == 0 and clock[-1]['completed_steps'] == STEPS and
         len(wanted_steps) == FRAMES and [row['completed_steps'] for row in clock] == wanted_steps and
         all(type(row['completed_steps']) is int and row['part'] == i and
             row['saved_step'] == (row['completed_steps'] - 1 if row['completed_steps'] else 0) and
             math.isfinite(float(row['time_s'])) for i, row in enumerate(clock)) and
         all(a['completed_steps'] < b['completed_steps'] for a, b in zip(clock, clock[1:])) and
         sum(row['completed_steps'] > 5243 for row in clock) == 1313, 'Exact integer dyadic clock table differs')
    return manifest_e, manifest, job


def reader_closure(build_e, build, manifest_e):
    helper_e = adopt(T / 'logs/upl_hg_mid2_reader_ReleaseCPU_r1.helper.json')
    helper = read(helper_e)
    need(helper.get('stage') == 'upl_hg_mid2_reader_build_r1' and helper.get('passed') is True and
         helper['configuration'] == 'ReleaseCPU' and helper['kind'] == 'reader' and helper['source_build'] == build_e and
         same_entry(helper['prepared_inputs'], manifest_e) and helper.get('status') == 'frozen_HG_mid2_CPU_reader_linked_not_run' and
         helper['CPU_non_main_objects'] == len(helper['objects']) == 85 and helper['link_object_count'] == 86 and
         len(helper['source_snapshots265']) == 265 and len(helper['libraries']) == 17 and len(helper['runtime']) == 4 and
         helper.get('exact_link_closure_verified') is True and helper.get('actual_headers_archived_not_live') is True and
         helper.get('independent_final_rehash_performed') is True and
         helper.get('frozen_build_program_inputs_runtime_unchanged') is True and helper.get('canonical_programs_rechecked') is True and
         all(helper.get(k) is False for k in ('production_build_executed', 'program_run', 'solver_started',
             'canonical_program_installed', 'physical_acceptance')),
         'Actual frozen mid2 reader 85+1/265/library17/runtime4 closure required')
    expected = [e for e in build['objects'] if Path(e['path']).name.lower() != 'main.obj']
    need(helper['objects'] == expected and helper['source_snapshots265'] == [p['snapshot'] for p in build['source_snapshot']],
         'Reader must use selected current build archives and exactly its non-main objects')
    for key in ('inputs', 'objects', 'source_snapshots265', 'actual_project_headers', 'author_files', 'tools', 'libraries'):
        for e in helper[key]:
            bind(e)
    for key in ('program', 'helper_object', 'compiler_dependency_record', 'neutral_include', 'documentation_snapshot',
                'case_readme_snapshot', 'retained_compiler_recipe', 'environment_source'):
        bind(helper[key])
    proof = helper['mechanical_source_transform']
    need(proof.get('whole_source_text_and_UTF8_bytes_exact') is True and
         proof.get('original_numerical_guard_bodies_unchanged') is True and
         proof.get('original1746_schedule_asserted_before1517_prefix') is True and
         proof.get('new_BI4_parser_or_solver_stub') is False and len(proof['substitutions']) == 10 and
         (proof['parent']['bytes'], proof['parent']['sha256']) ==
         (18447, '6956f50e9e619beffd4c7a4d347aef224773ed33dafb68790eaf811a9fd23a26') and
         (proof['derived']['bytes'], proof['derived']['sha256']) ==
         (18575, '194066fa3a332f511f434b38081eade1d4aa9f4a366de3f0a497f67c3007a4e4'),
         'Pinned whole-reader ten-substitution proof required')
    parent, derived = bind(proof['parent']), bind(proof['derived'])
    reconstructed = parent.read_bytes().decode('utf-8')
    for change in proof['substitutions']:
        need(change['occurrences'] == 1 and reconstructed.count(change['old']) == 1, 'Reader substitution occurrence differs')
        reconstructed = reconstructed.replace(change['old'], change['new'])
    need(reconstructed.encode('utf-8') == derived.read_bytes(), 'Reader changed outside whole-source mechanical proof')
    dep = read(helper['compiler_dependency_record'])['Data']
    archive = Path(helper['archived_header_include_root']).resolve()
    includes = [Path(value).resolve() for value in dep['Includes']]
    need(Path(dep['Source']).resolve() == derived.resolve() and
         helper['neutral_include']['sha256'] == '9f6668bfe3d1bbcca7c45c58809f7062c21fcb46baae76f0a2a1b0ef3ca56d38' and
         [path for path in includes if path.is_relative_to((T / 'support').resolve())] ==
         [Path(helper['neutral_include']['path']).resolve()] and
         not any(path.is_relative_to((SRC / 'source').resolve()) for path in includes) and
         {path for path in includes if path.parent == archive} ==
         {Path(e['path']).resolve() for e in helper['actual_project_headers']} and
         helper['actual_project_headers'] and all(e in helper['source_snapshots265'] for e in helper['actual_project_headers']),
         'Reader actual source/single neutral/archived project headers differ')
    typed_build(helper['compile_call'], log_required=True); link = typed_build(helper['link_call'], log_required=True)
    linked = [str(Path(a.strip('"')).resolve()).casefold() for a in link['arguments'] if a.strip('"').lower().endswith('.obj')]
    need(len(linked) == len(set(linked)) == 86 and set(linked) ==
         {str(Path(e['path']).resolve()).casefold() for e in expected + [helper['helper_object']]}, 'Reader actual 85+1 link membership differs')
    need([Path(a.strip('"')).name.casefold() for a in link['arguments'] if a.strip('"').lower().endswith('.lib')] ==
         [Path(e['path']).name.casefold() for e in helper['libraries']], 'Reader ordered library17 basename arguments differ')
    for pair in helper['runtime']:
        need(pair['original'] in [p['copy'] for p in build['runtime']] and
             all(pair['original'][k] == pair['copy'][k] for k in ('bytes', 'sha256')), 'Reader runtime differs from selected frozen build')
        bind(pair['original']); bind(pair['copy'])
    need(Path(helper['program']['path']).resolve() ==
         (T / 'outputs/upl_hg_mid2_reader_ReleaseCPU_r1/upl_hg_mid2_native_r1.exe').resolve(), 'Prepared reader program path differs')
    return helper_e


def admission(path, manifest_e, helper_e):
    admission_e = adopt(path)
    value = read(admission_e)
    need(value.get('stage') == 'upl_hg_mid2_admission_r1' and value.get('passed') is True and
         value.get('allowed_jobs') == [TAG] and value.get('physical_acceptance') is False,
         'Separate root admission must allow exactly this single mid2 coarse job')
    for e in value['inputs']:
        bind(e)
    compare_e = pin('logs/upl_hg_cpu1_short_r1.compare.json')
    pair_e = pin('logs/upl_hg_column_full_review_r1_pair.check.json')
    gpu_e = dict(path=str(GPU_REVIEW.resolve()), bytes=GPU_PIN[0], sha256=GPU_PIN[1]); gpu = read(gpu_e)
    need(all(any(same_entry(e, bound) for bound in value['inputs']) for e in (manifest_e, helper_e, compare_e, pair_e, gpu_e)),
         'Admission must bind successful prep/helper, CPU1 compare, independent half pair and GPU Release review')
    compare, pair = read(compare_e), read(pair_e)
    need(compare.get('stage') == 'upl_hg_cpu1_short_r1.compare' and compare.get('passed') is True and
         compare.get('bindings_unchanged') is True and compare.get('samples') == 458 and
         len(compare['thread_compatibility_gates']) == 3 and all(v is True for v in compare['thread_compatibility_gates'].values()) and
         compare.get('physical_acceptance') is False,
         'Actual successful CPU1 same-step short comparison required')
    need(pair.get('stage') == 'upl_hg_column_full_review_r1' and pair.get('phase') == 'pair' and
         pair.get('passed') is True and pair.get('independent_half_performed') is True and
         len(pair['independent_half_gates']) == 3 and all(v is True for v in pair['independent_half_gates'].values()) and
         pair.get('physical_acceptance') is False, 'Actual successful independent .5 s pair required')
    need(gpu.get('stage') == 'upl_cryer_gpu_component_release_review_r1' and gpu.get('passed') is True and
         gpu.get('configuration') == 'Release' and gpu.get('typed_owned_target_exit0') is True and
         gpu.get('direct_target_owned_exit0') is True and gpu.get('independent_final_rehash_performed') is True and
         gpu.get('component_completion_verified') is True and gpu.get('prior_Debug_memcheck_zero_errors_and_leaks') is True and
         gpu.get('observer_initialization_validated') is False and gpu.get('feedback_initialization_validated') is False and
         gpu.get('physical_acceptance') is False and gpu.get('public_3D_admitted') is False,
         'Actual separate successful GPU Release component review required without 3D initialization acceptance')
    return admission_e


def native_call(program, arguments, start_e):
    receipt, log = T / 'logs' / (TAG + '.call.json'), T / 'logs' / (TAG + '.log')
    fresh(receipt, log)
    code = failure = None
    started, wall = utc(), time.perf_counter()
    try:
        with log.open('xb') as stream:
            completed = subprocess.run([program['path'], *arguments], cwd=SRC, stdout=stream,
                stderr=subprocess.STDOUT, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
            code = completed.returncode  # First operation after the direct native call returns.
    except Exception as exc:
        failure = str(exc)
    seal(receipt, dict(stage='upl_hg_mid2_call_r1', tag=TAG, configuration='ReleaseCPU', window='coarse',
        program=program, target_program=program, arguments=arguments, target_arguments=arguments,
        working_directory=str(SRC), started_utc=started, ended_utc=utc(), start_record=start_e,
        direct_native_call=True, shell=False, typed_returncode_captured_immediately=type(code) is int,
        owned_call_exited=type(code) is int, exit_code=code, invocation_failure=failure,
        log=entry(log) if log.exists() else None, invocation_wall_seconds=time.perf_counter() - wall,
        actual_solver_call=True, public_project_main=True, fixture_or_Run_override=False,
        direct_target_call=True, restart=False, physical_acceptance=False))
    return adopt(receipt), code, failure


def check_output(result):
    result['run_out'] = adopt(OUT / 'Run.out')
    text = Path(result['run_out']['path']).read_text(encoding='utf-8-sig')
    need('Finished execution (code=0).' in text and 'RunMode="Stable - Pos-Double - Single core"' in text and
         re.search(r'Steps of simulation[.]+:\s*1048576(?:\s|$)', text) and
         re.search(r'Excluded particles[.]+:\s*0(?:\s|$)', text), 'Actual CPU1 finish/steps/no-exclusion gate failed')
    need(re.search(r'SoilHourglassXi: 0\.1\s', text) and 'SoilDamping="BuiFukagawa2013"' in text and
         re.search(r'SoilDampingCoef=0\.02(?:\s|$)', text) and 'SoilBoundaryDerivativeSPR="None"' in text,
         'Original HG xi/eta/SPR settings differ')
    force = re.search(r'SoilHourglass: forcecalls=(\d+) predictorupdates=(\d+) correctorupdates=(\d+) ratecalls=(\d+)', text)
    cache = re.search(r'SoilHourglass: ratecalculations=(\d+) endpoint_rate_reuses=(\d+)', text)
    need(force and cache and tuple(map(int, force.groups())) == (2097152, 1048576, 1048576, 2097152) and
         tuple(map(int, cache.groups())) == (1048577, 1048575), 'Actual original HG stage/cache counts differ')
    diagnostic = re.search(r'SoilHourglass: max\|sum\(M0\*Href\)\|=([^ ]+) max\|sum\(mi\*deltaAce\)\|=([^ ]+) max\(dt/tau\)=([^ ]+) spinbound=([^\r\n]+)', text)
    need(diagnostic, 'Actual single-J reference-history/current-inertia diagnostics missing')
    net, actual, tau, spin = map(float, diagnostic.groups())
    need(all(math.isfinite(v) and v >= 0 for v in (net, actual, tau, spin)) and tau <= .2 and spin < .01,
         'Original finite HG dt/tau/spin guards failed')
    result['HG'] = dict(counters=COUNTERS, max_reference_history_net_force=net,
        max_actual_float_add_net_force=actual, max_dt_over_tau=tau, spinbound=spin,
        reference_history_is_Q_over_M0=True, actual_inertia_is_current_mi=True)
    parts = sorted(path.name for path in (OUT / 'data').glob('Part_*.bi4') if path.is_file())
    need(parts == ['Part_%04d.bi4' % i for i in range(FRAMES)], 'Actual native 1517 PART sequence differs')
    for key, label in (('simulation_runtime_seconds_reported', 'Simulation Runtime'), ('total_runtime_seconds_reported', 'Total Runtime')):
        match = re.search(re.escape(label) + r'[.]+:\s*([0-9.eE+-]+) sec\.', text)
        need(match and math.isfinite(float(match[1])) and float(match[1]) >= 0, 'Actual runtime diagnostic missing')
        result[key] = float(match[1])
    result.update(steps=STEPS, native_frames=len(parts))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--admission', type=Path, required=True)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    need(args.execution_authorized, 'Root full read and explicit one-run authorization required')
    record, start_path = T / 'logs' / (TAG + '.run.json'), T / 'logs' / (TAG + '.start.json')
    fresh(record, start_path, OUT, T / 'logs' / (TAG + '.call.json'), T / 'logs' / (TAG + '.log'))
    result = dict(stage=NAME, tag=TAG, passed=False, backend='CPU', configuration='ReleaseCPU', window='coarse',
        threads=1, physical_acceptance=False, half_or_formal_jobs_admitted=False, failure=None,
        public_project_main=True, fixture_or_Run_override=False, native_decoder_invoked=False,
        all22_native_fields_review_pending=True, actual_native_clocks_review_pending=True,
        direct_owner_no_scheduler=True, automatic_follow_up=False)
    try:
        for path in (__file__, T / 'notes/upl_hg_mid2_run_r1.json', T / 'support/upl_hg_mid2_followup_r1.py',
                     T / 'notes/upl_hg_mid2_followup_r1.json', sys.executable, psutil.__file__):
            adopt(path)
        build_e, build = build_closure()
        manifest_e, manifest, job = prepared_job(build_e, build)
        helper_e = reader_closure(build_e, build, manifest_e)
        admission_e = admission(args.admission, manifest_e, helper_e)
        active = [p.info for p in psutil.process_iter(['pid', 'name', 'exe', 'cmdline', 'create_time'])
                  if (p.info['name'] or '').lower().startswith('dualsphysics') and
                  'cpu' in (p.info['name'] or '').lower() and (p.info['name'] or '').lower().endswith('.exe')]
        need(not active, 'Another actual CPU solver is active; no duplicate run')
        me = psutil.Process()
        owner = dict(pid=me.pid, created_epoch=me.create_time(), exe=me.exe(), command=me.cmdline(), cwd=str(Path.cwd().resolve()))
        result.update(job=job, input_manifest=manifest_e, source_input_manifest=manifest['source_input_manifest'],
            source_job=manifest['source_job'], source_build=build_e, program=build['program'], reader_helper=helper_e,
            admission=admission_e, arguments=job['arguments'], output_directory=str(OUT), CPU_processes_before=active)
        result['declared_JSON_time_roundtrip_max_abs_s'] = max(abs(float(row['time_s']) - row['completed_steps'] * DT)
                                                              for row in job['saved_clock_table'])
        seal(start_path, dict(stage='upl_hg_mid2_start_r1', tag=TAG, configuration='ReleaseCPU', window='coarse',
            utc=utc(), owner=owner, owner_script=adopt(__file__), job=job, arguments=job['arguments'],
            input_manifest=manifest_e, source_build=build_e, program=build['program'], reader_helper=helper_e,
            admission=admission_e, working_directory=str(SRC), direct_owner_no_scheduler=True,
            native_call_started_by_start_record=False, inputs=list(BOUND.values()), physical_acceptance=False))
        result['start_record'] = adopt(start_path)
        reverify()
        result['call'], code, failure = native_call(build['program'], job['arguments'], result['start_record'])
        call = read(result['call'])
        if call['log']:
            bind(call['log'])
        need(type(code) is int and code == 0 and failure is None, 'Actual direct CPU1 project-main call did not return integer zero')
        check_output(result)
        result['passed'] = True
    except Exception as exc:
        result['failure'] = str(exc)
    result['files'] = []
    try:
        if OUT.exists():
            result['files'] = inventory(OUT)
    except Exception as exc:
        result['failure'] = ((result['failure'] + '; ') if result['failure'] else '') + 'Raw inventory failed: ' + str(exc)
        result['passed'] = False
    try:
        reverify(); result['bindings_unchanged'] = True
    except Exception as exc:
        result['bindings_unchanged'] = False
        result['failure'] = ((result['failure'] + '; ') if result['failure'] else '') + str(exc)
        result['passed'] = False
    result['inputs'] = list(BOUND.values())
    result.update(saved_final_J_weighted_load_is_descriptive_only=True, same_force_stage_load_budget_verified=False,
        force_stage_guard_independently_observed=False, acceptance_gates_relaxed=False,
        source_project_formal_or_canonical_files_written_by_this_action=False, following_action_launched=False)
    seal(record, result)
    print(json.dumps(dict(passed=result['passed'], receipt=str(record), failure=result['failure'])))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
