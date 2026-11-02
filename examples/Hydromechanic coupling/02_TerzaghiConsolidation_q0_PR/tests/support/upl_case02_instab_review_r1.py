"""Compare two rejected startup diagnostics; never a convergence or physical pass."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

TESTS = Path(__file__).resolve().parents[1]


def entry(path):
    path = Path(path)
    return dict(path=str(path.resolve()), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def verify(item):
    actual = entry(item['path'])
    assert actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256'].lower(), item['path']


def main():
    report = TESTS/'logs/upl_case02_instab_r1.review.json'
    table = TESTS/'figures/upl_case02_instab_r1_history.csv'
    if report.exists() or table.exists():
        raise ValueError('Retained review protected')
    source = TESTS/'logs/upl_case02_instab_half_r1.export.json'
    receipt = json.loads(source.read_text(encoding='utf-8-sig'))
    assert receipt['passed'] is False and receipt['exit_code'] == 0 and receipt['failure'] is None
    assert receipt['typed_LASTEXITCODE_captured_immediately'] and receipt['owned_call_exited']
    assert receipt['bindings_unchanged'] and receipt['CSV_frames'] == 76
    assert not receipt['native_frame_sequence_0000_through_0075']
    assert receipt['statistics_CSV_count'] == 1 and receipt['other_CSV_count'] == 0
    coarse_path = TESTS/'logs/upl_case02_short_failure_r1.review.json'
    coarse = json.loads(coarse_path.read_text(encoding='utf-8'))
    assert coarse['analysis_completed'] and not coarse['physical_acceptance']
    bindings = [entry(__file__), entry(source), entry(coarse_path)] + receipt['bindings'] + receipt['files'] + coarse['files']
    for item in bindings:
        verify(item)
    files = {Path(e['path']).name: Path(e['path']) for e in receipt['files']}
    assert set(files) == {f'native_{n:04}.csv' for n in range(76)} | {'native_stats.csv'}
    # The old PS5 Sort-Object path inspected an OrderedDictionary property rather
    # than its path key. Check the complete filename set independently, not its order.
    rows = []
    for part in range(76):
        d = pd.read_csv(files[f'native_{part:04}.csv'], skiprows=3).sort_values('Idp')
        assert np.array_equal(d.Idp.to_numpy(), np.arange(1040))
        s = d[d.Idp >= 40]
        p, j = s.PorePress.to_numpy(), s.PoroVolumeRatio.to_numpy()
        assert np.isfinite(s.select_dtypes(include='number').dropna(axis=1, how='all').to_numpy()).all()
        layer = (s.Idp.to_numpy() - 40) % 100
        energy = float(p @ p)
        rows.append(dict(part=part, nominal_saved_time_s=part*.000025,
                         nominal_completed_step=20*part,
                         pressure_RMS_Pa=float(np.sqrt(np.mean(p*p))),
                         pressure_min_Pa=float(p.min()), pressure_max_Pa=float(p.max()),
                         max_abs_vz_m_s=float(s['Vel.z [m/s]'].abs().max()),
                         min_J=float(j.min()), max_J=float(j.max()),
                         max_saved_Kplastic=float(s.Kplastic.abs().max()),
                         max_within_layer_pressure_spread_Pa=max(float(np.ptp(p[layer == z])) for z in range(100)),
                         top10_pressure_energy_fraction=float(p[layer >= 90] @ p[layer >= 90]/energy) if energy else 0.))
    half = pd.DataFrame(rows)
    reference = pd.read_csv(coarse['files'][0]['path'])
    assert np.array_equal(half.part, reference.part)
    # Rounded PartVTK time labels and finite-precision CSV only: no exact-clock
    # or raw-bit comparison, and both physical trajectories were rejected.
    joined = half.merge(reference, on='part', suffixes=('_half', '_coarse'), validate='one_to_one')
    assert len(joined) == 76
    assert np.max(np.abs(joined.nominal_saved_time_s_half-joined.nominal_saved_time_s_coarse)) <= 1e-16
    joined.to_csv(table, index=False, float_format='%.17g')
    for item in bindings:
        verify(item)
    result = dict(stage='upl_case02_instab_r1', analysis_completed=True,
                  solver_or_converter_started=False, physical_acceptance=False, accepted_half_pair=False,
                  old_export_and_failed_solver_records_preserved=True,
                  converter_exit0_adopted_offline_only=True,
                  old_sequence_failure='PS5 OrderedDictionary entries require Sort-Object {$_.path}; independent filename-set verification found all76 frames plus one statistics CSV.',
                  original_solver_exit_codes=[1, 1], frames_each=76,
                  times_are_nominal_diagnostic_labels_not_decoded_binary_clocks=True,
                  CSV_precision_not_raw_bit_exact=True, failure_unsaved_branch_unknown=True,
                  all_half_saved_Kplastic_zero=bool((half.max_saved_Kplastic == 0).all()),
                  selected_history=joined[joined.part.isin([20, 40, 60, 75])].to_dict(orient='records'),
                  half_extrema=dict(pressure_min_Pa=float(half.pressure_min_Pa.min()),
                                    pressure_max_Pa=float(half.pressure_max_Pa.max()),
                                    min_J=float(half.min_J.min()), max_J=float(half.max_J.max())),
                  files=[entry(table)], bindings=bindings)
    with report.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(report)


if __name__ == '__main__':
    main()
