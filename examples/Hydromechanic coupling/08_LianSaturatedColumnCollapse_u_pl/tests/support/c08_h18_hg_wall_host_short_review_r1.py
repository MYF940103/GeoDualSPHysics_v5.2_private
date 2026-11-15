"""Offline only: exact no-feedback comparison of the two host-capture controls."""
import argparse
import csv
from pathlib import Path
import c08_h18_wend_matrix_r1 as m

T, L = m.T, m.L


def review(profile):
    debug = profile == 'debug2'
    frames, updates = (2, 2) if debug else (4, 6001)
    tag = 'c08_h18_hg_wall_host_' + profile + '_r1'
    oldtag = 'c08_h18_hg_opt_' + profile + '_r1'
    out, old = T / 'outputs' / tag, T / 'outputs' / oldtag
    path = L / (tag + '.check.json')
    m.need(not path.exists(), 'Existing offline result protected')
    consumed = []
    result = dict(stage=tag + '.no_feedback', passed=False, profile=profile,
                  physical_acceptance=False, solver_invocations=0, reader_invocations=0,
                  SHA_scans=0, automatic_next_job=False)

    def take(p):
        consumed.append(m.stat(p))
        return Path(p)

    def equal(a, b):
        a, b = take(a), take(b)
        m.need(a.read_bytes() == b.read_bytes(), 'Byte difference: ' + str(a))

    try:
        runpath = take(L / (tag + '.run.json'))
        run = m.read(runpath)
        m.need(run['passed'] and run['solver_completed'] and run['consumed_stats_unchanged']
               and run['actual_exit'] == run['actual_Win32_exit'] == run['actual_tool_exit']
               == run['actual_tool_Win32_exit'] == 0 and run['ownership_failure'] is None
               and run['solver_identity_matches'] and run['normal_short_no_fault_capture']
               and run['new_updates'] == updates and run['saved_frames'] == frames,
               'Actual complete own short run required')
        oldcheck = m.read(take(L / (oldtag + '.check.json')))
        m.need(oldcheck['passed'], 'Retained optimized control is not verified')
        callpath = take(L / (tag + '.native.call.json'))
        call = m.read(callpath)
        completionpath = take(out / 'native_r1/completion.json')
        completion = m.read(completionpath)
        m.need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0
               and call['ownership_failure'] is None and completion['passed']
               and completion['samples'] == frames and completion['typed_arrays'] == 22
               and completion['actual_native_IDs_per_frame'] == 6805
               and completion['completed_steps'] == 2000000 + updates
               and not completion['native_rewritten'], 'Unique original native safety required')
        m.need(not (out / 'WallFaultCaptureHostR1').exists(), 'Unexpected fault capture in normal short')
        for leaf in ('typed22.bin', 'typed22_layout.csv', 'clocks.csv'):
            equal(out / 'native_r1' / leaf, old / 'native_r1' / leaf)
        equal(out / 'C08OptPlasticHG.csv', old / 'C08OptPlasticHG.csv')
        policy = m.read(take(out / 'C08OptPlasticHGPolicy.json'))
        m.need(policy == m.read(take(old / 'C08OptPlasticHGPolicy.json')), 'HG policy differs')
        with (out / 'C08OptPlasticHG.csv').open(newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            m.need(len(reader.fieldnames) == 60, 'Original60-column phase schema required')
            phases = list(reader)
        m.need(len(phases) == 2 * frames, 'Actual phase-row count differs')
        result.update(actual_native_call=m.stat(callpath), native_completion=m.stat(completionpath),
                      clock_layout_signed_rows_byte_equal=True, policy_equal=True,
                      all_original_native_guards=True, normal_short_no_fault_capture=True,
                      cache_checks_are_coherence_not_independent_return=True)
        if debug:
            snapshot = out / 'C08OptPlasticHGDebugFirstN.bin'
            m.need(snapshot.stat().st_size == 907392, 'Complete first-n extent differs')
            equal(snapshot, old / snapshot.name)
            a = m.read(take(out / 'C08OptPlasticHGDebugFirstN.json'))
            m.need(a == m.read(take(old / 'C08OptPlasticHGDebugFirstN.json')), 'First-n configuration differs')
            log = take(run['actual_call']['path'])
            actual = m.read(log)
            text = take(actual['log']['path']).read_text(encoding='utf-8', errors='replace')
            m.need(run['memcheck_zero_errors_and_leaks']
                   and 'ERROR SUMMARY: 0 errors' in text and 'LEAK SUMMARY: 0 bytes leaked in 0 allocations' in text,
                   'Actual zero-error memcheck required')
            result.update(all22_native_full_two_records_byte_equal=True,
                          HG_four60column_rows_byte_equal=True,
                          first_n_snapshot_907392_bytes_equal=True, first_n_config_equal=True,
                          memcheck_zero_errors_and_leaks=True)
        else:
            m.need(any(int(row['smooth']) > 0 or int(row['tension']) > 0 for row in phases),
                   'Release control must contain a real plastic saved stage')
            result.update(all22_native_four_records_byte_equal=True,
                          HG_eight60column_rows_byte_equal=True, plastic_saved_stage_present=True)
        m.verify(consumed)
        result.update(passed=True, consumed_stats_unchanged=True)
    except Exception as error:
        result['first_failure'] = str(error)
        raise
    finally:
        result['consumed'] = consumed
        m.save(path, result)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('debug2', 'prefix4'), required=True)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    m.need(args.execution_authorized, 'Root offline review authorization required')
    review(args.profile)
