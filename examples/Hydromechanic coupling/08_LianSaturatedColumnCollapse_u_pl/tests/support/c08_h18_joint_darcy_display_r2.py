"""Redraw only the completed joint-Darcy cancellation panel with readable labels."""
import argparse
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_joint_darcy_display_r2'


def stamp(path):
    path = Path(path).resolve()
    s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    if not parser.parse_args().execution_authorized:
        raise RuntimeError('Root display-only admission required')
    source = T / 'figures/c08_h18_joint_darcy_review_r1_summary.csv'
    review = T / 'logs/c08_h18_joint_darcy_review_r1.check.json'
    png = T / 'figures' / (TAG + '_cancellation.png')
    check = T / 'logs' / (TAG + '.check.json')
    if png.exists() or check.exists():
        raise RuntimeError('Existing display or partial protected')
    q = json.loads(review.read_text(encoding='utf-8'))
    entry = next(e for e in q['files'] if Path(e['path']).resolve() == source.resolve())
    if not q['passed'] or stamp(source) != entry:
        raise RuntimeError('Passed compact source binding required')
    consumed = [stamp(source), stamp(review), stamp(__file__)]
    with source.open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    lookup = {(int(r['part']), r['field'], r['oracle']): r for r in rows
              if r['family'] == 'soil' and r['region'] == 'legal_flat_bed'}
    if len(rows) != 60 or len(lookup) != 12:
        raise RuntimeError('Original compact cohort coverage differs')
    colors = ('#2368a0', '#d17b21')
    fig, axes = plt.subplots(2, 3, figsize=(14.5, 8.2), sharey=True)
    extent = 0.
    fields = ('H_hydro_affine', 'N_normal_quadratic', 'X_cross_cubic')
    labels = ('Pressure\nLP', 'Taylor\ncorrection', 'Acceleration\nDa',
              'FS Ace', 'k chain', 'Net')
    for row, part in enumerate((29, 30)):
        for col, field in enumerate(fields):
            ax = axes[row, col]
            for oracle_index, oracle in enumerate(('real_wall', 'analytic_ghost')):
                r = lookup[part, field, oracle]
                if int(r['count']) == 0:
                    ax.text(.5, .5, 'Empty cohort', transform=ax.transAxes, ha='center')
                    continue
                y = [float(r[k + '_mean_Pa_s']) for k in
                     ('LP', 'Taylor_pressure', 'Da', 'FS_Ace_Lx')]
                y += [float(r['chain_pressure_mean_Pa_s']) + float(r['chain_Ace_mean_Pa_s']),
                      float(r['rate_mean_Pa_s'])]
                extent = max(extent, max(abs(v) for v in y))
                ax.bar(np.arange(6) + (oracle_index - .5) * .28, y, .26,
                       color=colors[oracle_index], alpha=.87)
            ax.set_title(f'P{part}: {field[0]} — legal flat bed', fontsize=12)
            ax.set_xticks(range(6), labels, fontsize=8)
            ax.set_yscale('symlog', linthresh=1.)
            ax.axhline(0, color='.35', lw=.7)
            ax.grid(axis='y', alpha=.22)
            if col == 0:
                ax.set_ylabel('Signed mean source contribution [Pa/s]')
    for ax in axes.flat:
        ax.set_ylim(-extent * 1.35, extent * 1.35)
    fig.suptitle('Joint Darcy: pressure / acceleration / k-chain cancellation', fontsize=16, y=.982)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors]
    fig.legend(handles, ('Real wall API', 'Analytic p/Ace ghost oracle'),
               loc='upper center', bbox_to_anchor=(.5, .945), ncol=2, frameon=False)
    fig.text(.5, .024, 'Signed spatial means can cancel. Channel RMS and same-ID differences are retained in the source CSV.',
             ha='center', fontsize=9)
    fig.text(.5, .007, 'Display only; symlog linear range 1 Pa/s. No changed operator or physical acceptance.',
             ha='center', fontsize=9)
    fig.subplots_adjust(top=.84, bottom=.13, wspace=.15, hspace=.40)
    with png.open('xb') as f:
        fig.savefig(f, format='png', dpi=180)
    plt.close(fig)
    if any(stamp(e['path']) != e for e in consumed):
        raise RuntimeError('Consumed display input changed')
    proof = dict(stage=TAG, passed=True, display_only=True, source_summary_rows=60,
                 displayed_groups=12, physical_acceptance=False, SHA_scans=0,
                 visual_QA_pending=True, consumed=consumed, files=[stamp(png)])
    with check.open('x', encoding='utf-8') as f:
        json.dump(proof, f, indent=2, allow_nan=False)
        f.write('\n')


if __name__ == '__main__':
    main()
