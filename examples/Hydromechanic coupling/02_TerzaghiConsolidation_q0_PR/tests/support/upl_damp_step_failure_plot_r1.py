"""Plot the sealed rejected timestep comparison; never alter its original limits."""
import csv, hashlib, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

T = Path(__file__).resolve().parents[1]
TAG = 'upl_damp_step_failure_plot_r1'

def entry(path):
    path = Path(path).resolve()
    return dict(path=str(path), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())

def main():
    image = T / 'figures' / (TAG + '.png')
    record = T / 'logs' / (TAG + '.check.json')
    if image.exists() or record.exists():
        raise ValueError('Retained analysis artifacts protected')
    proof_path = T / 'logs/upl_damp_step_half_r1.check.json'
    proof_entry = entry(proof_path)
    proof = json.loads(proof_path.read_text('utf-8'))
    expected = dict(pressure_RMS_all_times_le_5Pa=False,
                    material_XYZ_difference_all_times_le_0_005mm=True,
                    actual_time_difference_le_1e_minus14_s=True)
    if not (proof['stage'] == 'upl_damp_step_compare_r1' and
            proof['passed'] is False and proof['failure'] is None and
            proof['physical_acceptance'] is False and proof['gates'] == expected):
        raise ValueError('This diagnostic requires the unchanged numerical rejection')
    if len(proof['files']) != 1:
        raise ValueError('Expected one original comparison CSV')
    csv_entry = proof['files'][0]
    if entry(csv_entry['path']) != csv_entry:
        raise ValueError('Sealed comparison CSV changed')
    with Path(csv_entry['path']).open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    t = np.array([float(r['A_actual_time_s']) for r in rows])
    p = np.array([float(r['pressure_RMS_Pa']) for r in rows])
    u = np.array([float(r['material_XYZ_difference_max_mm']) for r in rows])
    if not (len(rows) == proof['samples'] == 1341 and np.isfinite(p).all()
            and p.max() == proof['max_pressure_RMS_Pa']
            and u.max() == proof['max_material_XYZ_displacement_difference_mm']):
        raise ValueError('Original CSV/proof metrics differ')
    peak = int(np.argmax(p)); event = proof['same_event_s']
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].plot(t, p, color='#2166ac', lw=1)
    axes[0].set(xlabel='Actual saved time (s)', ylabel='Coarse / half pressure RMS difference (Pa)',
                title='All 1,341 actual matched samples')
    take = np.abs(t - event) <= .0001
    axes[1].plot((t[take] - event) * 1e6, p[take], 'o-', color='#2166ac', ms=3, lw=1)
    axes[1].scatter((t[peak] - event) * 1e6, p[peak], color='#b2182b', zorder=3)
    axes[1].set(xlabel='Time since declared drainage opening (microseconds)',
                ylabel='Pressure RMS difference (Pa)', title='Opening transient: unchanged raw samples')
    for ax in axes:
        ax.axhline(5., color='#b2182b', ls='--', label='Original 5 Pa limit')
        ax.grid(alpha=.25); ax.legend(fontsize=8)
    fig.suptitle('Larger timestep REJECTED: %.6f Pa > 5 Pa' % p[peak])
    fig.text(.5, .02, 'Both solvers and native safety checks completed. This is timestep disagreement, not theory error. '
             'Retain the previously accepted smaller step; no limit relaxation.', ha='center', fontsize=8)
    fig.tight_layout(rect=(0, .075, 1, .94)); fig.savefig(image, dpi=180); plt.close(fig)
    inputs = [entry(__file__), proof_entry, csv_entry]
    for e in inputs:
        if entry(e['path']) != e: raise ValueError('Analysis input changed')
    result = dict(stage=TAG, passed=True, artifact_generation_only=True,
                  physical_acceptance=False, candidate_adopted=False,
                  original_numerical_rejection_preserved=True,
                  samples=len(rows), pressure_over_5Pa_samples=int(np.sum(p > 5.)),
                  peak_part=peak, peak_actual_time_s=float(t[peak]),
                  max_pressure_RMS_Pa=float(p[peak]),
                  max_material_XYZ_difference_mm=float(u.max()),
                  inputs=inputs, files=[entry(image)], visual_review_performed=False)
    with record.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps(dict(passed=True, record=str(record))))

if __name__ == '__main__': main()
