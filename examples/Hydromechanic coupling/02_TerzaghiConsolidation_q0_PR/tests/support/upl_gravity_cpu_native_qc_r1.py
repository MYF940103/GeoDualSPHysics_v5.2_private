"""Offline-only exact QC for the six explicitly delegated gamma regressions.
No subprocess, old workflow import, native parser, source or input mutation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd


def entry(path):
    path = Path(path)
    return dict(path=str(path.resolve()), bytes=path.stat().st_size,
                sha256=hashlib.file_digest(path.open('rb'), 'sha256').hexdigest())


def require(test, why):
    if not test:
        raise RuntimeError(why)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def verify(item):
    actual = entry(item['path'])
    require(actual['bytes'] == item['bytes'] and
            actual['sha256'].lower() == item['sha256'].lower(), 'Changed binding: '+item['path'])


def main(args):
    target = Path(args.out)
    require(not target.exists(), 'Retained offline QC protected')
    manifest = read(args.manifest)
    selected = [j for j in manifest['jobs'] if j['job'] == args.job]
    require(len(selected) == 1, 'Exactly one selected manifest job')
    job = selected[0]
    run = read(args.run)
    require(run['owned_solver_exit0'] and run['normal_finish_marker'] and
            run['native_frames'] == job['samples'], 'Real sealed solver prerequisite')
    call = read(run['call']['path'])
    require(call['typed_LASTEXITCODE_captured_immediately'] and
            call['owned_call_exited'] and call['exit_code'] == 0, 'Actual owned solver exit0')
    for binding in run['files']:
        verify(binding)
    review = Path(job['new_review'])
    detail = []
    ledger = None
    if job['comparison']['kind'] == 'lossless_native_38_CSV_binary64_comparison':
        initial = None
        expected_steps = [0, 499, 999, 1499, 1999]
        for part in range(5):
            a = pd.read_csv(review/f'candidate_{part}.csv', float_precision='round_trip')
            b = pd.read_csv(review/f'retained_{part}.csv', float_precision='round_trip')
            require(a.shape == b.shape == (1040, 38) and list(a) == list(b), 'Original native38 contract')
            aa, bb = a.to_numpy(dtype='<f8'), b.to_numpy(dtype='<f8')
            require(np.isfinite(aa).all() and np.isfinite(bb).all(), 'All original native values finite')
            bad = aa.view('<u8') != bb.view('<u8')
            row = dict(part=part, values=int(aa.size), different_values=int(bad.sum()),
                       different_fields=[str(c) for c in a.columns[bad.any(axis=0)]],
                       max_abs_difference=float(np.max(np.abs(aa-bb))))
            detail.append(row)
            require(not bad.any(), 'Original all38 exact difference: '+str(row))
            require(np.array_equal(a.id, np.arange(1040)), 'All native IDs0..1039')
            require(a.native_count.eq(1040).all() and a.nout.eq(0).all() and
                    a.position_double.eq(1).all() and a.stress_double.eq(1).all() and
                    a.load_available.eq(1).all(), 'Original native scope/precision/no-exclusion')
            require(a.kplastic.eq(0).all() and a.rho.gt(0).all(), 'Original finite elastic density')
            require(np.array_equal(a.is_boundary, np.r_[np.ones(40), np.zeros(1000)]), 'Fixed/native ownership')
            require(a.saved_step.eq(expected_steps[part]).all(), 'Actual original zero-based saved Step')
            require(a.time_s.eq(float(a.time_s.iloc[0])).all(), 'One actual clock per original frame')
            if part:
                require(a.has_dterror.eq(1).all() and a.dterror_s.le(1e-14).all(), 'Original signed actual dterror')
            require(np.array_equal(a.excess_native.to_numpy(dtype=np.float32),
                                   a.pressure.to_numpy(dtype=np.float32)-a.porepress0.to_numpy(dtype=np.float32)),
                    'Native float excess identity')
            if initial is None:
                initial = a
            require(np.array_equal(a.porepress0, initial.porepress0), 'Fixed original p0')
            soil = a.iloc[40:]
            drained = soil.fstype.isin([2, 3])
            require(set(soil.id[drained]) == set(initial.iloc[40:].id.iloc[99::100]) and
                    soil.pressure[drained].eq(0).all(), 'Original ten top true drained IDs')
        ledger = dict(original_five_frame_38_native_checks_passed=True,
                      initial_dterror_presence_not_fabricated=True,
                      metadata_absence_independently_reparsed=False)
    else:
        old = Path(job['comparison']['retained_review'])
        for leaf in job['comparison']['exact_leaf_names']:
            a, b = entry(review/leaf), entry(old/leaf)
            row = dict(leaf=leaf, candidate=a, retained=b,
                       equal=a['bytes'] == b['bytes'] and a['sha256'] == b['sha256'])
            detail.append(row)
            require(row['equal'], 'Exact native export differs: '+leaf)
        done_path = review/('completion.json' if job['comparison']['kind'] == 'periodic33' else 'complete.json')
        done = read(done_path)
        require(done['passed'] and done['samples'] == job['samples'] and
                done['native_count'] == job['soil'] and done['fixed_count'] == job['fixed'] and
                done['no_exclusions'] and done['native_ID_aligned'], 'Complete native identity/safety coverage')
        require(done['saved_clock_step_exact'], 'Real saved clock/Step exact')
        require(not done['physical_acceptance'], 'No physical acceptance escalation')
        history = pd.read_csv(review/'history.csv', float_precision='round_trip')
        require(len(history) == job['samples'] and np.isfinite(history.to_numpy(dtype='<f8')).all(), 'Complete finite signed history')
        require(history.dterror_s.le(1e-14).all(), 'Actual signed dterror every frame')
        require(np.array_equal(history.time_s.to_numpy(), np.arange(job['samples'])*job['cadence_s']), 'Exact actual dyadic times')
        step_column = 'saved_step' if 'saved_step' in history else 'native_step'
        wanted = np.arange(job['samples'])*int(round(job['cadence_s']/job['dt_s']))
        wanted[1:] -= 1
        require(np.array_equal(history[step_column].to_numpy(), wanted), 'Original actual saved Step including0')
        if job['ON']:
            if job['comparison']['kind'] == 'periodic33':
                require(done['native_J_arrays'] == 6 and done['native_PosDiv_observed'] and
                        done['public_dynamic_metadata'] and done['conductivity_model'] == 1 and
                        done['conductivity_Ck'] == 2**-13 and done['native_ledger_checks'] == job['soil']*job['samples'] and
                        done['max_ledger_relative_error'] <= 5e-13 and done['max_energy_ratio'] <= 1.1 and
                        done['max_saved_coupled_CFL'] <= .01 and done['max_saved_Ddt_h2'] <= .01 and
                        done['max_spatial_k_span_relative_to_k0'] >= .005, 'Original smooth native model/ledger/scales/energy')
            else:
                require(done['derived_arrays'] == 6 and done['posdiv_native_present'] and
                        done['model_metadata_verified'] and done['ledger_native_checks'] == job['soil']*job['samples'] and
                        done['fixed_marker_checks'] == job['fixed']*job['samples'] and
                        done['max_ledger_relative_error'] <= 5e-13 and done['max_energy_ratio'] <= 1.1 and
                        done['max_coupled_CFL'] <= .01 and done['max_Ddt_h2'] <= .01, 'Original public native ledger/markers/scales/energy')
            ledger = done
        else:
            require(done['derived_arrays'] == 0 and done['model_metadata_absent'] and
                    not (review/'physical.bin').exists(), 'Original OFF array/metadata absence')
            ledger = done
    result = dict(passed=True, job=args.job, manifest=entry(args.manifest), source_run=entry(args.run),
                  comparison_kind=job['comparison']['kind'], samples=job['samples'], soil=job['soil'], fixed=job['fixed'],
                  exact_details=detail, native_safety_and_extra_ledger=ledger,
                  no_excluded_dterror_or_signed_zero_or_interpolation=True,
                  second_BI4_parser=False, all_BI4_arrays_individually_byte_exported=False,
                  unknown_Prepare_exit_used_as_solver_exit=False,
                  new_half_or_theory_or_nonzero_g_positive_k_acceptance=False, physical_acceptance=False)
    target.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print('OFFLINE_NATIVE_EXACT_PASSED '+args.job)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('manifest', 'job', 'run', 'out'):
        parser.add_argument('--'+key, required=True)
    main(parser.parse_args())
