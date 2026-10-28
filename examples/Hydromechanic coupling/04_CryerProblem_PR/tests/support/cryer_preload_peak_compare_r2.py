"""Visual-only revision: reuse the sealed r1 CSVs, without recomputing theory or physics."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

TESTS = Path(__file__).resolve().parents[1]
TAG = 'cryer_preload_peak_compare_r2'
PNG = TESTS / 'figures' / (TAG + '_comparison.png')
CHECK = TESTS / 'logs' / (TAG + '.check.json')
R1 = TESTS / 'logs/cryer_preload_peak_compare_r1.check.json'


def bound(path):
    path = Path(path)
    return dict(path=str(path), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    assert not PNG.exists() and not CHECK.exists(), 'Fresh visual tag required'
    previous = json.loads(R1.read_text(encoding='utf-8-sig'))
    assert previous['passed'] and previous['numerical_self_checks_passed']
    for entry in previous['artifacts']:
        actual = bound(entry['path'])
        assert actual['sha256'] == entry['sha256'].lower() and actual['bytes'] == entry['bytes']
    paths = {name: TESTS/'figures'/('cryer_preload_peak_compare_r1_'+name+'.csv')
             for name in ['history', 'theory', 'shared']}
    history, theory, shared = [pd.read_csv(paths[k], float_precision='round_trip')
                               for k in ['history', 'theory', 'shared']]
    assert len(history) == 706 and len(theory) == 1200 and len(shared) == 129
    old = history[history.run.eq('abrupt')]
    new = history[history.run.eq('preload') & history.tau_from_drainage_s.ge(0)]
    assert len(old) == 129 and len(new) == 513
    assert np.isfinite(history.select_dtypes(include='number')).all().all()
    plt.rcParams.update({'font.size': 10, 'axes.titlesize': 11, 'axes.labelsize': 10,
                         'legend.fontsize': 8, 'savefig.facecolor': 'white'})
    fig, axes = plt.subplots(1, 3, figsize=(16.2, 5.8))
    fig.subplots_adjust(left=.055, right=.985, bottom=.21, top=.79, wspace=.28)
    for ax in axes[:2]:
        ax.plot(theory.tau_s*1000, theory.finite_storage_pressure_pa/1000,
                color='#30343a', lw=1.7, label='Finite-storage reference at r/R=0.05', zorder=1)
        ax.plot(old.tau_from_drainage_s*1000, old.center_fixed18_mean_pressure_pa/1000,
                color='#1763a6', lw=1.1, marker='o', ms=2.4, fillstyle='none',
                label='Abrupt load: 129 saved points', zorder=3)
        ax.plot(new.tau_from_drainage_s*1000, new.center_fixed18_mean_pressure_pa/1000,
                color='#cf6418', ls='--', lw=1.2, marker='.', ms=2.3,
                label='Preload: 513 saved axis points', zorder=4)
        ax.set(xlabel='Time from configured drainage event, tau (ms)',
               ylabel='Fixed 18-ID mean pressure (kPa)')
    axes[0].set(title='(a) Post-opening startup: saved samples', xlim=(0, 5), ylim=(0, 13.3))
    axes[0].legend(loc='lower right')
    axes[0].text(.025, .96, 'New tau=0 is pre-open; theory value is Bq.\nLines join saved points, not resolved waveforms.',
                 transform=axes[0].transAxes, va='top', fontsize=8.1)
    axes[1].set(title='(b) Mandel window: finite radius, not r=0', xlim=(4.5, 62.5), ylim=(10.1, 12.65))
    axes[1].text(.025, .06, 'Preload peak: 12.134018 kPa at 46.387 ms\nReference peak: 12.439176 kPa at 42.052 ms\nPeak change vs abrupt: +0.01514 Pa, 0 ms',
                 transform=axes[1].transAxes, va='bottom', fontsize=8.3,
                 bbox=dict(facecolor='white', edgecolor='none', alpha=.92, pad=3), zorder=6)
    axes[1].scatter([previous['reference_peak_recomputed_tau_s']*1000],
                    [previous['reference_peak_recomputed_pa']/1000],
                    marker='x', s=40, color='#30343a', zorder=5)
    axes[2].plot(shared.tau_s*1000, shared.new_minus_old_center_pressure_pa,
                 color='#65478f', marker='o', ms=2.2, lw=1)
    axes[2].axhline(0, color='#666666', lw=.7)
    axes[2].set_yscale('symlog', linthresh=1)
    axes[2].set(title='(c) New minus old: all 129 exact shared tau', xlim=(0, 62.5),
                xlabel='Matched time from drainage event, tau (ms)',
                ylabel='Centre pressure difference (Pa; symmetric log)')
    axes[2].text(.97, .95, 'Different loading histories,\nNOT half-step errors',
                 transform=axes[2].transAxes, va='top', ha='right', fontsize=8.3)
    for ax in axes:
        ax.grid(alpha=.2)
        ax.spines[['top', 'right']].set_visible(False)
    fig.suptitle('Cryer preload diagnostic: startup changes, Mandel peak remains nearly unchanged', y=.96, fontsize=14)
    fig.text(.055, .875, 'All native saved observations preserved; no filtering, interpolation, radius change or time fitting. Reference: finite Kw, quasistatic sphere, r/R=0.05.', fontsize=9)
    fig.text(.055, .085, 'New physical time = tau + 7.8125 ms; old physical time = tau. New curve includes the pre-open tau=0 state.\n360-root reference: tau=0 assigned exact Bq; positive plotted theory starts at 0.01 ms. Only short-window half evidence; no peak-half or full physical acceptance.', fontsize=8.7)
    fig.savefig(PNG, dpi=180)
    plt.close(fig)
    with Image.open(PNG) as image:
        dimensions = list(image.size)
        image.verify()
    result = dict(tag=TAG, utc=datetime.now(timezone.utc).isoformat(), passed=True,
        visual_only_revision=True, visual_review_passed=False, physical_accepted=False,
        theory_or_physics_recomputed=False, new_csv_files_created=False,
        change='Move only middle-panel peak annotation to lower-left white-backed empty region.',
        plotted_native_axis_points=dict(abrupt=129, preload=513), full_history_csv_rows=706,
        plotted_shared_tau_pairs=129, plotted_theory_points=1200,
        previous_check=bound(R1), sources=[bound(Path(__file__)), *[bound(p) for p in paths.values()]],
        artifacts=[bound(PNG)], png_dimensions=dimensions,
        limitations=previous['limitations'])
    CHECK.write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
