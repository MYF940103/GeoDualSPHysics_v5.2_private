"""Plot sealed r2 CSVs only; no binary reads, pair recomputation or solver calls."""
import csv
import hashlib
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

T = Path(__file__).resolve().parents[1]

def need(ok, message):
    if not ok:
        raise ValueError(message)

def entry(path):
    path = Path(path).resolve()
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def verify(item):
    actual = entry(item['path'])
    need(actual['bytes'] == item['bytes'] and actual['sha256'] == item['sha256'].lower(), 'Changed bound artifact: '+item['path'])
    return actual

def main():
    image = T/'figures/upl_gravity_periodic_summary_r2.png'
    log = T/'logs/upl_gravity_periodic_summary_r2.log'
    check = T/'logs/upl_gravity_periodic_summary_r2.check.json'
    need(not any(p.exists() for p in (image, log, check)), 'Fresh summary output paths required')
    adoption_path = T/'logs/upl_gravity_periodic_r2_adoption.json'; adoption = read(adoption_path)
    call_path = T/'logs/upl_gravity_periodic_adopt_r1.call.json'; call = read(call_path)
    need(adoption['passed'] is True and call['owned_call_exited'] is True and call['exit_code'] == 0 and call['typed_LASTEXITCODE_captured_immediately'] is True and call['solvers_called'] is False, 'Passed independent offline adoption required')
    inputs = [entry(__file__), entry(adoption_path), entry(call_path), verify(call['program']), verify(call['script']), verify(call['log'])]
    pairs = {p['pair']: p for p in adoption['pairs']}
    need(set(pairs) == {'half', 'frame_c', 'frame_h'}, 'Exactly three adopted pairs required')
    fig, axes = plt.subplots(3, 1, figsize=(8, 8), sharex=True)
    columns = ['pressure_RMS_over_Pstar', 'velocity_RMS_over_A', 'u_RMS_over_Ustar']
    labels = ['Gravity coarse / half', 'Gravity / zero-g, coarse', 'Gravity / zero-g, half']
    colors = ['#1f77b4', '#d95f02', '#238b45']; styles = ['-', '--', '-.']
    for pair, label, color, style in zip(('half', 'frame_c', 'frame_h'), labels, colors, styles):
        inputs.append(verify(pairs[pair]['check'])); done = read(pairs[pair]['check']['path'])
        need(done['passed'] is True and done['pair'] == pair and all(v is True for v in done['gates'].values()), 'Pair scientific gates not passed')
        csv_path = T/f'figures/upl_gravity_periodic_{pair}_r2.csv'
        bound = [e for e in done['files'] if Path(e['path']).resolve() == csv_path.resolve()]
        need(len(bound) == 1, 'CSV must be explicitly bound by its passed pair check'); inputs.append(verify(bound[0]))
        with csv_path.open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        time = [float(row['time_s']) for row in rows]
        need(len(rows) == 257 and time == [i*2.0**-23 for i in range(257)], 'All exact actual saved times required')
        for ax, column in zip(axes, columns):
            ppm = [float(row[column])*1e6 for row in rows]
            need(all(math.isfinite(x) and x >= 0 for x in ppm), 'Finite nonnegative RMS data required')
            ax.plot([t*1e6 for t in time], ppm, style, color=color, linewidth=1.5, label=label)
    for ax, label in zip(axes, ('Pressure RMS / P* [ppm]', 'Velocity RMS / A [ppm]', 'Material u RMS / U* [ppm]')):
        ax.set_ylabel(label); ax.grid(alpha=.25); ax.set_yscale('linear')
    axes[-1].set_xlabel('Actual saved time [microseconds]')
    fig.suptitle('Private CPU periodic gravity: bounded comparison errors', y=.995)
    fig.legend(*axes[0].get_legend_handles_labels(), loc='upper center', bbox_to_anchor=(.5, .96), ncol=3, fontsize=8)
    fig.text(.5, .012, 'Prior limit: 100 ppm (off-scale; unchanged). No all-field or physical acceptance.', ha='center', fontsize=8)
    fig.tight_layout(rect=(0, .04, 1, .91)); fig.savefig(image, dpi=180); plt.close(fig)
    for item in inputs: verify(item)
    log.write_text('Rendered three sealed r2 pairs, 257 unsmoothed samples each, three linear autoscaled ppm panels.\nOriginal analysis-call receipt gaps remain; no new numeric comparison or solver call.\n', encoding='utf-8')
    check.write_text(json.dumps({'passed': True, 'scope': 'Summary plot only; original adopted scientific gates unchanged', 'inputs': inputs, 'files': [entry(image), entry(log)], 'panels': 3, 'curves_per_panel': 3, 'points_per_curve': 257, 'normalization_to_ppm': 1e6, 'prior_limit_ppm': 100, 'limit_line_changes_axis_range': False, 'pair_recomputed': False, 'solvers_called': False, 'original_r2_typed_exit0_claimed': False, 'physical_acceptance': False}, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print('Summary plot and hash record completed: '+str(image))

if __name__ == '__main__':
    main()
