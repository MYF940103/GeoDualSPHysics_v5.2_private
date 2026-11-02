"""Offline diagnosis of rejected startup CSVs; no solver, conversion, or numerical acceptance."""
import csv
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
    if entry(item['path']) != dict(item, sha256=item['sha256'].lower()):
        raise ValueError('Changed evidence: ' + item['path'])


def main():
    report = TESTS/'logs/upl_case02_short_failure_r1.review.json'
    history = TESTS/'figures/upl_case02_short_failure_r1_history.csv'
    profiles = TESTS/'figures/upl_case02_short_failure_r1_layers.csv'
    if any(p.exists() for p in (report, history, profiles)):
        raise ValueError('Retained analysis protected')
    source = TESTS/'logs/upl_case02_short_failure_r1.export.json'
    old = json.loads(source.read_text(encoding='utf-8-sig'))
    assert old['exit_code'] == 0 and old['typed_LASTEXITCODE_captured_immediately']
    assert old['owned_call_exited'] and old['bindings_unchanged'] and old['failure'] is None
    assert old['passed'] is False and old['CSV_frames'] == 77
    bindings = [entry(__file__), entry(source)] + old['bindings'] + old['files']
    for item in bindings:
        verify(item)
    files = {Path(e['path']).name: Path(e['path']) for e in old['files']}
    assert set(files) == {f'native_{n:04}.csv' for n in range(76)} | {'native_stats.csv'}
    initial = pd.read_csv(files['native_0000.csv'], skiprows=3).sort_values('Idp')
    assert np.array_equal(initial.Idp, np.arange(1040))
    material = initial[initial.Idp >= 40]
    layer = np.rint(material['Pos.z [m]'].to_numpy()/.01-.5).astype(int)
    column = np.rint(material['Pos.x [m]'].to_numpy()/.01-.5).astype(int)
    assert set(zip(column, layer)) == {(i, j) for i in range(10) for j in range(100)}
    rows, layers = [], []
    for part in range(76):
        path = files[f'native_{part:04}.csv']
        d = pd.read_csv(path, skiprows=3).sort_values('Idp')
        assert np.array_equal(d.Idp, np.arange(1040))
        s = d[d.Idp >= 40]
        names = ['PorePress', 'PoroVolumeRatio', 'PoroPorosity', 'PoroThetaLastStage',
                 'Kplastic', 'Vel.x [m/s]', 'Vel.y [m/s]', 'Vel.z [m/s]',
                 'SigmaState_kk.x', 'SigmaState_kk.y', 'SigmaState_kk.z',
                 'SigmaState_ij.x', 'SigmaState_ij.y', 'SigmaState_ij.z']
        assert np.isfinite(s[names].to_numpy()).all()
        p = s.PorePress.to_numpy()
        energy = np.dot(p, p)
        spread = max(float(np.ptp(p[layer == j])) for j in range(100))
        row = dict(part=part, nominal_completed_step=10*part,
                   nominal_saved_time_s=part*.000025, pressure_min_Pa=float(p.min()),
                   pressure_max_Pa=float(p.max()), pressure_RMS_Pa=float(np.sqrt(np.mean(p*p))),
                   top10_pressure_energy_fraction=float(np.dot(p[layer >= 90], p[layer >= 90])/energy) if energy else 0.,
                   bottom10_pressure_energy_fraction=float(np.dot(p[layer < 10], p[layer < 10])/energy) if energy else 0.,
                   max_within_layer_column_pressure_spread_Pa=spread,
                   min_J=float(s.PoroVolumeRatio.min()), max_J=float(s.PoroVolumeRatio.max()),
                   min_porosity=float(s.PoroPorosity.min()), max_porosity=float(s.PoroPorosity.max()),
                   max_abs_theta_per_s=float(s.PoroThetaLastStage.abs().max()),
                   max_abs_vz_m_s=float(s['Vel.z [m/s]'].abs().max()),
                   max_saved_Kplastic=float(s.Kplastic.abs().max()),
                   sigma_zz_min_Pa=float(s['SigmaState_kk.z'].min()),
                   sigma_zz_max_Pa=float(s['SigmaState_kk.z'].max()))
        rows.append(row)
        for j in range(100):
            z = s.iloc[np.flatnonzero(layer == j)]
            layers.append(dict(part=part, nominal_saved_time_s=row['nominal_saved_time_s'],
                               initial_layer=j, pressure_mean_Pa=float(z.PorePress.mean()),
                               vz_mean_m_s=float(z['Vel.z [m/s]'].mean()),
                               J_mean=float(z.PoroVolumeRatio.mean()),
                               theta_mean_per_s=float(z.PoroThetaLastStage.mean()),
                               sigma_zz_mean_Pa=float(z['SigmaState_kk.z'].mean())))
    pd.DataFrame(rows).to_csv(history, index=False, float_format='%.17g')
    pd.DataFrame(layers).to_csv(profiles, index=False, float_format='%.17g')
    for item in bindings:
        verify(item)
    result = dict(stage='upl_case02_short_failure_r1', analysis_completed=True,
                  solver_or_converter_started=False, physical_acceptance=False,
                  rejected_solver_not_reclassified_as_passed=True,
                  export_checker_repair='PartVTK exit0 produced76 particle CSVs plus one native_stats.csv. The original total-CSV=77 rejection is preserved; only this offline review separates them.',
                  times_are_nominal_diagnostic_labels_not_rewritten_native_clocks=True,
                  CSV_precision_not_a_bit_exact_or_theory_accuracy_reference=True,
                  failure_branch_not_observed_in_unsaved_step=True,
                  pressure_top_mode_localization_descriptive_only=True,
                  all_saved_Kplastic_zero=all(r['max_saved_Kplastic'] == 0 for r in rows),
                  all_exported_same_layer_pressure_values_identical=all(r['max_within_layer_column_pressure_spread_Pa'] == 0 for r in rows),
                  retained_frames=76, last_saved_diagnostic=rows[-1],
                  selected_history=[rows[n] for n in (20, 30, 40, 60, 70, 75)],
                  files=[entry(history), entry(profiles)], bindings=bindings)
    with report.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(report)


if __name__ == '__main__':
    main()
