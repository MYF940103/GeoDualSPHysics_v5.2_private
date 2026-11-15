"""Fresh layout-only NN rendering from completed scientific CSV; no native read."""
import csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
import c08_h18_wend_matrix_r1 as m

T, L = m.T, m.L
TAG = 'c08_h18_hg_cached_nn_visual_r2'
CHECK = L / (TAG + '.check.json')
OUT = T / 'figures' / (TAG + '.png')


def main():
    m.need(not OUT.exists() and not CHECK.exists(), 'Existing rendering protected')
    prior = T / 'logs/c08_h18_hg_cached_physical_r1.check.json'
    q = m.read(prior)
    m.need(q['passed'] and q['analysis_complete'], 'Completed physical analysis required')
    source = T / 'figures/c08_h18_hg_cached_physical_r1_spatial.csv'
    sealed = [v for v in q['files'] if Path(v['path']).resolve() == source.resolve()]
    m.need(len(sealed) == 1, 'One actual completed spatial CSV seal required')
    before = [m.stat(Path(__file__)), m.stat(prior), m.bind(sealed[0])]
    rows = list(csv.DictReader(source.open(encoding='utf-8', newline='')))
    m.need(len(rows) == 30000, 'Every selected material point required')
    cases, parts = ('Retained HG0', 'Cached HG xi0.1'), (38, 76, 90)
    values = np.asarray([float(r['NN_over_dp']) for r in rows])
    x = np.asarray([float(r['x_m']) for r in rows])
    z = np.asarray([float(r['z_m']) for r in rows])
    m.need(np.isfinite(values).all() and np.isfinite(x).all() and np.isfinite(z).all(), 'Finite original values required')
    fig, axes = plt.subplots(2, 3, figsize=(17, 8))
    fig.subplots_adjust(left=.05, right=.89, bottom=.09, top=.85, wspace=.25, hspace=.45)
    norm = Normalize(vmin=float(values.min()), vmax=float(values.max()))
    for i, case in enumerate(cases):
        for j, part in enumerate(parts):
            selected = [r for r in rows if r['case'] == case and int(r['part']) == part]
            m.need(len(selected) == 5000 and len({r['native_id'] for r in selected}) == 5000, 'All 5000 actual soil IDs required')
            ax = axes[i, j]
            sc = ax.scatter([float(r['x_m']) for r in selected], [float(r['z_m']) for r in selected],
                c=[float(r['NN_over_dp']) for r in selected], s=4, norm=norm, cmap='viridis', rasterized=True)
            # These are the original accepted fixed contact planes, not invented particles.
            ax.axvline(0, color='.6', lw=1)
            ax.axhline(0, color='.6', lw=1)
            ax.set_xlim(min(0., float(x.min()))-.04, float(x.max())+.04)
            ax.set_ylim(min(0., float(z.min()))-.04, float(z.max())+.04)
            ax.set_aspect('equal')
            ax.set_title(case + '\nActual release time ' + format(float(selected[0]['tau_s']), '.9g') + ' s', fontsize=11)
            ax.set_xlabel('x [m]')
            ax.set_ylabel('z [m]')
    fig.suptitle('Soil nearest-neighbor spacing', y=.975, fontsize=17)
    fig.text(.5, .925, 'Common full 30000-point range; all soil points retained; reference wall planes shown in grey', ha='center', fontsize=11)
    cax = fig.add_axes([.925, .20, .018, .58])
    fig.colorbar(sc, cax=cax, label='Nearest-neighbor distance / dp')
    fig.savefig(OUT, dpi=160)
    plt.close(fig)
    m.verify(before)
    m.save(CHECK, dict(stage=TAG, passed=True, layout_only=True, source=m.stat(source), prior_analysis=m.stat(prior),
        all_selected_soil_points=30000, limits=[float(values.min()), float(values.max())], values_changed=False,
        reference_walls_are_particle_exports=False, native_reads=0, solver_invocations=0, reader_invocations=0,
        original_figures_unchanged=True, physical_acceptance=False, SHA_scans=0, consumed=before, output=m.stat(OUT)))


if __name__ == '__main__':
    main()
