"""Separate one-read and offline-review phases for one C04 CPU startup128 job.

No solver, build, VTK, hash or later-job action. The retained C04 r1 reader
validates 22 typed arrays but exports common26, not a raw22 bit comparison.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
import os
from pathlib import Path
import re
import struct
import sys
sys.dont_write_bytecode = True
import numpy as np
import psutil
import upl_tpi_cryer_cpu_build_r1 as b

T, L = b.T, b.L
STAGE = 'upl_tpi_cryer_cpu_native_review_r2'
READER = T / 'outputs/upl_cryer_public_native_DebugCPU_r1/reader.exe'
OLD_CALL = L / 'upl_cryer_freebody_smoke128_CPU_r1.call.json'
OLD_NATIVE_CALL = L / 'upl_cryer_freebody_smoke128_CPU_r1.native.call.json'
OLD_NATIVE = T / 'outputs/upl_cryer_freebody_smoke128_CPU_r1_native'
DT, TOTAL, FIXED, SOIL = 2.**-20, 37181, 8, 37173
TAG_RE = re.compile(r'upl_tpi_cryer_cpu_DebugCPU_([ABC])_startup128_r[1-9][0-9]*\Z')
SIDECAR = ['part','native_id','source_step_zero_based','completed_step','source_time_s','actual_save_time_s','dt_s',
    'pn_Pa','previous_Pa','prediction_double_Pa','half_actual_float_Pa','endpoint_q_actual_float_Pa',
    'S_1_per_m_s','Rgamma_Pa_per_m_s','raw_final_float_Pa','final_float_Pa','theta_half_for_J_1_per_s',
    'theta_endpoint_1_per_s','Jn','Jhalf','Jfull','source_drained','endpoint_drained','commit_drained',
    'commits','endpoint_calls','core_field_bit_checks','hg_snapshot_checks']


def bits(value):
    return struct.pack('<d', float(value))


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


class Admission:
    def __init__(self, path, phase, tag):
        self.entry = b.stat(path); self.data = b.read(path)
        b.need(self.data.get('stage') == STAGE + '.' + phase + '_admission'
               and self.data.get('passed') is True and self.data.get('tag') == tag
               and (self.data.get('one_native_read_only') is True if phase == 'native' else self.data.get('offline_only') is True),
               'Independent matching root phase/tag admission required')
        self.frozen = {b.key(x['path']): x for x in self.data['inputs']}; self.consumed = {}
        b.need(len(self.frozen) == len(self.data['inputs']), 'Duplicate frozen input')

    def pin(self, path):
        k = b.key(path); b.need(k in self.frozen, 'Consumed input absent from root admission: ' + str(path))
        self.consumed[k] = b.same(self.frozen[k]); return self.consumed[k]

    def finish(self):
        for x in self.consumed.values():
            b.same(x)
        b.same(self.entry); return list(self.consumed.values())


def actual_job(ad, tag):
    for p in (Path(__file__), T / 'notes/upl_tpi_cryer_cpu_native_review_r2.md',
              T / 'support/upl_tpi_cryer_cpu_build_r1.py', sys.executable, np.__file__, psutil.__file__):
        ad.pin(p)
    runpath = L / (tag + '.run.json'); ad.pin(runpath); run = b.read(runpath)
    match = TAG_RE.fullmatch(tag); b.need(bool(match), 'Only the exact C04 CPU startup128 tags admitted')
    scheme = match.group(1)
    b.need(run['stage'] == 'upl_tpi_cryer_cpu_run_r1.run' and run['passed'] and run['tag'] == tag
           and run['configuration'] == 'DebugCPU' and run['window'] == 'startup128' and run['scheme'] == scheme
           and run['actual_Popen_wait_exit'] == run['actual_Win32_exit'] == 0
           and run['solver_invocations'] == 1 and run['native_invocations'] == 0
           and run['consumed_stats_unchanged'] and run['actual_scalar_end'] == 2.**-13,
           'Genuine successfully sealed one-job solver result required')
    startpath = L / (tag + '.start.json'); ad.pin(startpath); start = b.read(startpath)
    ad.pin(run['call']['path']); b.same(run['call']); call = b.read(run['call']['path'])
    b.need(call['passed'] and call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0
           and call['child'] == run['child'] == start['child'] and call['owner']['pid'] == call['child']['parent']
           and call['arguments'] == run['arguments'] == start['arguments']
           and b.key(call['child']['exe']) == b.key(run['program']['path'])
           and call['child']['argv'][1:] == call['arguments'], 'Actual owned solver identity/argv/exit captures differ')
    native_created = (call['creation_FILETIME_ticks'] - 116444736000000000) / 1e7
    b.need(abs(native_created - call['child']['created']) <= 1e-6, 'Actual solver creation capture differs')
    b.need(call['actual_environment'] == run['actual_environment'] == start['actual_environment']
           == {'UPL_TPI_CPU_R1': scheme, 'UPL_TPI_GPU_R1': None}, 'Actual scheme environment differs')
    for name in ('program', 'source_build_review', 'original_failed_build', 'prepared', 'root_admission', 'plan'):
        ad.pin(run[name]['path']); b.same(run[name])
    build = b.read(run['source_build_review']['path'])
    b.need(build['passed'] and build['adopted_completed_build'] and build['original_build_passed'] is False
           and build['program_copy_byte_equal'] and build['program_relinked'] is False
           and build['program'] == run['program'] and build['object_count'] == 86,
           'Independently adopted completed build/program copy binding differs')
    ad.pin(build['source_program']['path']); b.same(build['source_program'])
    for x in build['runtime']:
        ad.pin(x['destination']['path']); b.same(x['destination'])
    data = Path(run['data']); output = Path(run['output_directory'])
    b.need(b.key(data) == b.key(output / 'data'), 'Actual native data directory differs')
    raw = sorted([*data.glob('*.bi4'), *data.glob('*.ibi4')])
    b.need({x.name for x in raw if x.suffix == '.bi4'} == {'Part_0000.bi4','Part_0001.bi4'}, 'Actual two-frame raw sequence differs')
    for p in raw:
        ad.pin(p)
    for name in ('Run.csv','Run.out'):
        ad.pin(output / name)
    ad.pin(call['log']['path']); b.same(call['log'])
    with Path(run['plan']['path']).open(encoding='utf-8-sig', newline='') as f:
        plan = list(csv.DictReader(f))
    scalar = 0.
    for _ in range(128):
        scalar += DT
    b.need(len(plan) == 2 and list(plan[0]) == ['part','time_s','completed_step','saved_step','dt_s'], 'Five-column actual clock plan differs')
    for p, row in enumerate(plan):
        b.need(int(row['part']) == p and int(row['completed_step']) == (128 if p else 0)
               and int(row['saved_step']) == (127 if p else 0)
               and bits(float(row['time_s'])) == bits(scalar if p else 0.)
               and bits(float(row['dt_s'])) == bits(DT), 'Genuine scalar +=dt actual clocks differ')
    return dict(tag=tag, scheme=scheme, run=run, runpath=runpath, data=data, output=output,
                native=T / 'outputs' / (tag + '_native_r2'), plan=Path(run['plan']['path']))


def preflight_recovery(ad, ctx):
    """Only the sealed A missing-root-admission failure occurred before decode.

    The original failed receipt remains false. No failed/partial reader may be
    adopted here, and fresh B/C use r2 directly without a prior attempt.
    """
    tag, run = ctx['tag'], ctx['run']
    oldreceipt = L / (tag + '.native_r1.json')
    oldoutput = T / 'outputs' / (tag + '_native_r1')
    oldcall = L / (tag + '.native_r1.call.json')
    oldlog = L / (tag + '.native_r1.log')
    b.need(not oldoutput.exists() and not oldcall.exists() and not oldlog.exists(),
           'Any prior r1 native directory/call/log forbids preflight recovery or another read')
    declared = ad.data.get('adopt_preflight_failure')
    if not oldreceipt.exists():
        b.need(declared is None, 'No prior failure exists to adopt; fresh job must use r2 normally')
        return dict(required=False, prior_reader_artifacts_present=False)
    b.need(tag == 'upl_tpi_cryer_cpu_DebugCPU_A_startup128_r1' and ctx['scheme'] == 'A'
           and isinstance(declared, dict) and b.key(declared['path']) == b.key(oldreceipt),
           'Only the exact A missing-root-admission preflight may be explicitly recovered')
    ad.pin(oldreceipt); b.same(declared); failed = b.read(oldreceipt)
    expected = 'Consumed input absent from root admission: ' + run['root_admission']['path']
    b.need(failed.get('stage') == 'upl_tpi_cryer_cpu_native_review_r1'
           and failed.get('phase') == 'native' and failed.get('tag') == tag and failed.get('passed') is False
           and failed.get('first_error') == expected and failed.get('solver_invocations') == 0
           and failed.get('build_invocations') == 0 and failed.get('VTK_invocations') == 0
           and all(k not in failed for k in ('reader_call', 'native_directory', 'native_products',
                                           'native_completion', 'reader_invocations')),
           'Prior failure was not the exact observed before-reader missing-input rejection')
    ad.pin(failed['root_admission']['path']); b.same(failed['root_admission'])
    prior_ad = b.read(failed['root_admission']['path'])
    b.need(prior_ad.get('stage') == 'upl_tpi_cryer_cpu_native_review_r1.native_admission'
           and prior_ad.get('passed') is True and prior_ad.get('tag') == tag
           and prior_ad.get('one_native_read_only') is True
           and b.key(run['root_admission']['path']) not in {b.key(e['path']) for e in prior_ad['inputs']},
           'Original failed admission does not independently demonstrate its exact omitted run-root binding')
    for original in (T / 'support/upl_tpi_cryer_cpu_native_review_r1.py',
                     T / 'notes/upl_tpi_cryer_cpu_native_review_r1.md'):
        recorded = [e for e in prior_ad['inputs'] if b.key(e['path']) == b.key(original)]
        b.need(len(recorded) == 1, 'Original preflight source/note binding missing')
        ad.pin(original); b.same(recorded[0])
    return dict(required=True, exact_prior_preflight_failure=b.stat(oldreceipt),
                prior_native_admission=failed['root_admission'],
                original_failed_receipt_modified=False, old_native_directory_call_log_absent=True,
                original_reader_invocations_field_present=False,
                failure_precedes_decode_function=True, original_missing_input=run['root_admission'])


def completion(directory):
    done = b.read(directory / 'completion.json')
    b.need(done['stage'] == 'upl_cryer_public_native_r1' and done['passed'] and done['samples'] == 2
           and done['completed_steps'] == 128 and bits(done['actual_end_s']) == bits(2.**-13)
           and bits(done['dt_s']) == bits(DT) and done['total_native_ids'] == TOTAL
           and done['soil_ids'] == SOIL and done['fixed_ids'] == FIXED and done['native_typed_arrays'] == 22
           and done['soil_ledger_checks'] == 2*SOIL and done['fixed_marker_checks'] == 2*FIXED
           and done['noninitial_signed_dterror_intervals'] == 1 and done['post_open_frames'] == 0
           and done['post_open_FS23_zero_pressure_checks'] == 0
           and done['signed_dterror_is_original_necessary_step_guard'] is True
           and done['raw_BI4_modified'] is False, 'Original complete native/ledger/clock/startup coverage differs')
    return done


def decode(ad, ctx, result):
    tag, native = ctx['tag'], ctx['native']; callpath = L / (tag + '.native_r2.call.json')
    b.need(not native.exists() and not callpath.exists() and not (L / (tag + '.native_r2.log')).exists(),
           'Existing/partial native output or reader call must be diagnosed, never redecoded')
    ad.pin(READER); ad.pin(OLD_NATIVE_CALL)
    oldcall = b.read(OLD_NATIVE_CALL)
    b.need(oldcall['exit_code'] == 0 and oldcall['direct_exit'] and b.key(oldcall['program']['path']) == b.key(READER),
           'Retained reader was not the genuinely successful CPU128 decoder')
    b.same(oldcall['program'])
    for p in READER.parent.iterdir():
        if p.is_file() and p.suffix.lower() in ('.dll','.xml'):
            ad.pin(p)
    for proc in psutil.process_iter(['pid','exe','cmdline']):
        info = proc.info
        if info['exe'] and b.key(info['exe']) == b.key(READER):
            argv = info['cmdline'] or []
            b.need(not any(b.key(x) in {b.key(ctx['data']), b.key(native)} for x in argv[1:]),
                   'Matching original reader is active; do not duplicate it')
    env = os.environ.copy(); env.pop('UPL_TPI_CPU_R1', None); env.pop('UPL_TPI_GPU_R1', None)
    ad.finish()
    call, _ = b.invoke(tag + '.native_r2', [str(READER),'--read','CPU',str(ctx['data']),str(ctx['plan']),str(native)],
                       READER.parent, env)
    result.update(reader_call=call, native_directory=str(native), native_completion=completion(native),
                  native_products=[b.stat(p) for p in native.iterdir() if p.is_file()],
                  reader_invocations=1, consumed=ad.finish(), consumed_stats_unchanged=True, passed=True)


def common(directory):
    raw = (directory / 'common26.bin').read_bytes()
    b.need(struct.unpack_from('<III', raw) == (TOTAL,26,2), 'Original common26 header differs')
    dtype = np.dtype([('time','<f8'),('values','<f8',(TOTAL,26))])
    b.need(len(raw) == 12 + 2*dtype.itemsize, 'Original common26 payload length differs')
    data = np.frombuffer(raw, dtype=dtype, offset=12)
    clock = (directory / 'clock.bin').read_bytes()
    b.need(struct.unpack_from('<II', clock) == (2,28) and len(clock) == 64, 'Original clock header/payload length differs')
    for p in range(2):
        time, step, dt, error = struct.unpack_from('<dIdd', clock, 8+28*p)
        b.need(bits(time) == bits(data['time'][p]) == bits(2.**-13 if p else 0.)
               and step == (127 if p else 0) and bits(dt) == bits(DT)
               and math.isfinite(error) and error <= 1e-14, 'Actual signed clock or original bound differs')
        if p:
            b.need(error != -sys.float_info.max, 'Noninitial signed interval is empty')
    return raw, data, clock


def pressure_history(ctx, values):
    output, scheme = ctx['output'], ctx['scheme']
    if scheme == 'A':
        b.need(not any((output / ('UplTpiCpuR1' + x)).exists() for x in ('.csv','.policy.json','.summary.json')),
               'Default A entered the private numerical branch')
        return dict(private_branch_entered=False, HG_snapshot_checks=0)
    policy = b.read(output / 'UplTpiCpuR1.policy.json'); end = b.read(output / 'UplTpiCpuR1.summary.json')
    alpha = .5 if scheme == 'B' else 0.
    expected_name = 'B_TPI_alpha_0p5_beta0' if scheme == 'B' else 'C_PPE_t_alpha0_beta0'
    b.need(policy['stage'] == 'upl_tpi_cpu_r1' and policy['scheme'] == expected_name
           and policy['alpha'] == alpha and policy['beta'] == 0
           and policy['M0'] and policy['native_count'] == TOTAL and policy['soil_count'] == SOIL
           and policy['history_ID_owned'] and policy['history_cold_start'] and not policy['full_restart_supported'],
           'Actual pressure policy differs')
    b.need(end['completed'] and end['scheme'] == expected_name and end['alpha'] == alpha and end['beta'] == 0
           and end['commits'] == end['endpoint_calls'] == 128
           and end['core_field_bit_checks'] == 7*SOIL*128 and end['HG_readonly_snapshot_checks'] == 0
           and bits(end['actual_end']) == bits(2.**-13), 'Actual complete pressure lifecycle/HG0 summary differs')
    seen = [set(),set()]; min_s, max_r, j_checks = math.inf, 0., 0
    last_source_time = 0.
    for _ in range(127):
        last_source_time += DT
    with (output / 'UplTpiCpuR1.csv').open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f); b.need(reader.fieldnames == SIDECAR, 'Actual generic sidecar schema differs')
        for row in reader:
            p, k = int(row['part']), int(row['native_id'])
            b.need(p in (0,1) and FIXED <= k < TOTAL and k not in seen[p], 'Sidecar material identity/record duplicated')
            seen[p].add(k); x = {n: float(row[n]) for n in SIDECAR if n not in ('part','native_id')}
            b.need(all(math.isfinite(v) for v in x.values()), 'Nonfinite actual sidecar value')
            commits = 128 if p else 0; source_time = last_source_time if p else 0.
            b.need(x['source_step_zero_based'] == (127 if p else 0) and x['completed_step'] == commits
                   and bits(x['source_time_s']) == bits(source_time)
                   and bits(x['actual_save_time_s']) == bits(2.**-13 if p else 0.) and bits(x['dt_s']) == bits(DT)
                   and x['commits'] == x['endpoint_calls'] == commits
                   and x['core_field_bit_checks'] == 7*SOIL*commits and x['hg_snapshot_checks'] == 0
                   and x['source_drained'] == x['endpoint_drained'] == x['commit_drained'] == 0,
                   'Actual sidecar clocks/lifecycle or closed-startup drainage differs')
            prediction = x['pn_Pa'] if alpha == 0. else x['pn_Pa'] + .5*(x['pn_Pa']-x['previous_Pa'])
            b.need(bits(prediction) == bits(x['prediction_double_Pa'])
                   and bits(f32(prediction)) == bits(x['half_actual_float_Pa']) == bits(x['endpoint_q_actual_float_Pa'])
                   and bits(x['final_float_Pa']) == bits(values[p,k,6])
                   and bits(x['Jfull']) == bits(values[p,k,8]), 'Actual pressure prediction/native commit or J differs')
            if p:
                S, residual = x['S_1_per_m_s'], x['Rgamma_Pa_per_m_s']
                b.need(S > 0 and bits(f32(x['endpoint_q_actual_float_Pa'] + residual/S)) == bits(x['raw_final_float_Pa'])
                       == bits(x['final_float_Pa']), 'Actual double leading-LP defect row/float write differs')
                expected_j = x['Jn'] + ((DT*x['Jhalf'])*x['theta_half_for_J_1_per_s'])
                b.need(bits(expected_j) == bits(x['Jfull']), 'Original unique J corrector arithmetic differs')
                min_s = min(min_s,S); max_r = max(max_r,abs(residual)); j_checks += 1
            else:
                b.need(x['S_1_per_m_s'] == x['Rgamma_Pa_per_m_s'] == 0.
                       and x['Jn'] == x['Jhalf'] == x['Jfull'] == 1., 'Cold initial pressure/J record differs')
    b.need(all(s == set(range(FIXED,TOTAL)) for s in seen) and j_checks == SOIL, 'Missing actual two-frame material sidecar coverage')
    return dict(private_branch_entered=True, sidecar_rows=2*SOIL, actual_end_J_checks=j_checks,
                actual_end_pressure_row_checks=SOIL, core_field_bit_checks=7*SOIL*128,
                HG_snapshot_checks=0, minimum_end_S=min_s, maximum_abs_end_Rgamma=max_r,
                all128_rows_exported=False, note='All128 lifecycle counts are checked; only genuine two saved states have per-ID sidecar rows.')


def offline(ad, ctx, result):
    tag, native = ctx['tag'], ctx['native']; decode_path = L / (tag + '.native_r2.json')
    ad.pin(decode_path); decoded = b.read(decode_path)
    b.need(decoded['passed'] and decoded['reader_invocations'] == 1 and b.key(decoded['native_directory']) == b.key(native),
           'Existing successful unique native read required; never repeat a failed or partial decode')
    ad.pin(decoded['reader_call']['path']); b.same(decoded['reader_call']); call = b.read(decoded['reader_call']['path'])
    b.need(call['passed'] and call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0,
           'Actual reader tool exits did not pass')
    for p in native.iterdir():
        if p.is_file():
            ad.pin(p)
    done = completion(native); payload, data, signed = common(native)
    with (native / 'native_ids.csv').open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    b.need(len(rows) == TOTAL and all(int(x['id']) == k and int(x['is_soil']) == int(k>=FIXED) for k,x in enumerate(rows)),
           'Actual sorted native IDs/roles differ')
    for suffix in ('.policy.json','.summary.json','.csv'):
        p = ctx['output'] / ('UplTpiCpuR1' + suffix)
        if p.exists():
            ad.pin(p)
    history = pressure_history(ctx, data['values'])
    comparison = {}
    if ctx['scheme'] == 'A':
        for p in (OLD_CALL,OLD_NATIVE_CALL,OLD_NATIVE/'completion.json',OLD_NATIVE/'common26.bin',OLD_NATIVE/'clock.bin',OLD_NATIVE/'native_ids.csv'):
            ad.pin(p)
        b.need(b.read(OLD_CALL)['exit_code'] == b.read(OLD_NATIVE_CALL)['exit_code'] == 0,
               'Actual retained CPU128 solver/reader call exits differ; no invented old run/start')
        completion(OLD_NATIVE); prior, _, prior_clock = common(OLD_NATIVE)
        b.need(payload == prior and signed == prior_clock
               and (native/'native_ids.csv').read_bytes() == (OLD_NATIVE/'native_ids.csv').read_bytes(),
               'New default A differs from actual retained CPU128 common26/clock/identity bytes')
        comparison = dict(retained_CPU128_common26_and_signed_clock_bit_equal=True,
                          raw22_all_arrays_bit_comparison_performed=False,
                          original_control_has_run_or_start_receipt=False)
    else:
        path = ad.data.get('reference_A_review'); b.need(path, 'Actual passed new A review required for descriptive comparison')
        ad.pin(path); ar = b.read(path)
        b.need(ar['passed'] and ar['scheme'] == 'A' and ar.get('stage') == STAGE and ar.get('phase') == 'review', 'New r2 A reference review did not pass')
        reference = Path(ar['native_directory'])
        for name in ('common26.bin','clock.bin','completion.json'):
            ad.pin(reference/name)
        _, prior, _ = common(reference); pv = prior['values'][-1,FIXED:]; v = data['values'][-1,FIXED:]
        comparison = dict(reference_new_A_review=b.stat(path), descriptive_only=True,
            final_pressure_RMS_difference_Pa=float(np.sqrt(np.mean((v[:,6]-pv[:,6])**2))),
            final_material_XYZ_difference_max_mm=float(1000*np.max(np.linalg.norm(v[:,:3]-pv[:,:3],axis=1))),
            cross_model_5Pa_half_bound_applied=False, cross_model_equivalence_claimed=False)
    result.update(passed=True, scheme=ctx['scheme'], native_directory=str(native), native_completion=done,
                  native_read_receipt=b.stat(decode_path), history_review=history, comparison=comparison,
                  consumed=ad.finish(), consumed_stats_unchanged=True, reader_invocations=0,
                  startup_not_postdrain_or_peak_or_physical_acceptance=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--phase', choices=('native','review'), required=True)
    ap.add_argument('--tag', required=True); ap.add_argument('--admission', required=True, type=Path)
    ap.add_argument('--execution-authorized', action='store_true'); args = ap.parse_args()
    b.need(args.execution_authorized and TAG_RE.fullmatch(args.tag), 'Explicit root phase and exact tag required')
    receipt = L / (args.tag + ('.native_r2.json' if args.phase=='native' else '.native_review_r2.json'))
    b.need(not receipt.exists(), 'Existing review/decode receipt is protected; do not overwrite/retry')
    result = dict(stage=STAGE, phase=args.phase, tag=args.tag, passed=False, solver_invocations=0,
                  build_invocations=0, VTK_invocations=0, SHA_scans=0, raw_BI4_modified=False,
                  raw22_all_arrays_bit_comparison_performed=False, physical_acceptance=False, automatic_follow_up=False)
    try:
        ad = Admission(args.admission,args.phase,args.tag); result['root_admission'] = ad.entry
        ctx = actual_job(ad,args.tag)
        result['prior_preflight_recovery'] = preflight_recovery(ad,ctx)
        (decode if args.phase=='native' else offline)(ad,ctx,result)
    except Exception as exc:
        result.update(passed=False, first_error=str(exc), partials_preserved=True)
    b.write_new(receipt,result)
    print(json.dumps(dict(passed=result['passed'],receipt=str(receipt),first_error=result.get('first_error')),ensure_ascii=False))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
