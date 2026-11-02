"""Display-only Cryer revision: log x-axis to 5; SPH symbols without lines."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

CASE = Path(__file__).resolve().parents[1]
DEST = CASE / 'figures/formal_validation'
OLD = 'cryer_formal_four_nu_r1'
NEW = 'cryer_formal_four_nu_r2'
CHECK = CASE / 'tests/logs' / (NEW + '.style.check.json')


def bound(path):
    path = Path(path).resolve()
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def main():
    outputs = {key: DEST / (NEW + '_' + key + '.png')
               for key in ('log', 'paper_limit_log')}
    assert not CHECK.exists() and not any(p.exists() for p in outputs.values()), 'Fresh display revision only'
    prior = CASE / 'tests/logs' / (OLD + '.check.json')
    seal = json.loads(prior.read_text(encoding='utf-8-sig'))
    assert seal['passed']
    protected = [bound(prior), bound(__file__)]
    for record in seal['artifacts']:
        assert bound(record['path']) == record, record['path']
        protected.append(record)
    native = pd.read_csv(DEST / (OLD + '_native.csv'), float_precision='round_trip')
    theory = pd.read_csv(DEST / (OLD + '_theory.csv'), float_precision='round_trip')
    assert len(native) == 4260 and len(theory) == 5600
    plt.rcParams.update({'font.family': 'serif',
                         'font.serif': ['Times New Roman', 'DejaVu Serif'],
                         'font.size': 12, 'mathtext.fontset': 'stix'})
    colors = ['#0072B2', '#D55E00', '#009E73', '#CC79A7']
    markers = ['o', 's', '^', 'D']
    definitions = [
        ('log', 'finite_Kw_fixed18_p_over_q0',
         'Finite water bulk modulus; fixed initial center18, $r_0/a=0.05$'),
        ('paper_limit_log', 'paper_incompressible_r0_p_over_q0',
         'Paper reference limit: incompressible water, exact center $r=0$')]
    checks = []
    for key, column, description in definitions:
        fig, ax = plt.subplots(figsize=(11, 7.5), constrained_layout=True)
        groups = []
        for nu, color, marker in zip((.1, .2, .3, .45), colors, markers):
            a = native.loc[native.nu.eq(nu) & native.legacy_Tv.gt(0)]
            d = theory.loc[theory.nu.eq(nu)]
            assert len(a) == 1000 and len(d) == 1400
            # Keep the original every-12-save symbols, plus the actual final save.
            take = np.unique(np.r_[np.arange(0, len(a), 12), len(a) - 1])
            selected = a.iloc[take]
            analytic, = ax.plot(d.legacy_Tv, d[column], color=color,
                                ls=(0, (6, 3)), lw=1.9,
                                label=fr'Theory, $\nu={nu:g}$')
            sph, = ax.plot(selected.legacy_Tv, selected.sim_p_over_q0,
                           color=color, linestyle='None', marker=marker,
                           ms=4, mfc='none', mew=.85,
                           label=fr'SPH, $\nu={nu:g}$')
            assert sph.get_linestyle() == 'None'
            assert np.array_equal(sph.get_xdata(), a.legacy_Tv.iloc[take])
            assert np.array_equal(sph.get_ydata(), a.sim_p_over_q0.iloc[take])
            assert np.array_equal(analytic.get_ydata(), d[column])
            groups.append(dict(nu=nu, native_positive_rows=len(a),
                               displayed_symbols=len(take), marker=marker,
                               sph_linestyle=sph.get_linestyle(),
                               native_final_Tv=float(a.legacy_Tv.iloc[-1]),
                               theory_max_Tv=float(d.legacy_Tv.max())))
        ax.set(xscale='log', xlim=(5e-4, 5), ylim=(0, 1.6),
               xlabel=r'Drainage-relative $T_v=c_v(t-t_D)/a^2$',
               ylabel=r'Normalized pore pressure, $p^w/p_0$')
        ax.set_xticks([.001, .01, .1, 1., 5.],
                      labels=[r'$10^{-3}$', r'$10^{-2}$', r'$10^{-1}$', r'$10^0$', r'$5$'])
        ax.grid(True, which='major', color='.84', lw=.7)
        ax.grid(True, which='minor', color='.9', ls=':', lw=.6)
        ax.legend(loc='lower left', ncol=2, fontsize=11, frameon=True,
                  fancybox=False, edgecolor='.45')
        ax.set_title('Cryer: four Poisson ratios, returned formal GPU runs\n' +
                     description, fontsize=14)
        fig.supxlabel(
            r'$d_p=0.0025$ m, $k=10^{-5}$ m/s, $p_0=10$ kPa; $t_D=2^{-7}$ s. Legacy $c_v$ uses $g=9.81$.' +
            '\nSPH symbols: every 12 saved samples plus final; runs end near $T_v=1$, theory data at 1.2. No extrapolation.',
            fontsize=9)
        assert ax.get_xscale() == 'log' and ax.get_xlim() == (5e-4, 5.)
        fig.savefig(outputs[key], dpi=240)
        checks.append(dict(figure=str(outputs[key]), xscale=ax.get_xscale(),
                           xlim=list(ax.get_xlim()), groups=groups))
        plt.close(fig)
    assert all(bound(r['path']) == r for r in protected), 'Prior data/figures/script changed'
    record = dict(passed=True, display_only=True, inputs=protected,
                  artifacts=[bound(p) for p in outputs.values()], artist_checks=checks,
                  data_and_metrics_unchanged=True, prior_figures_unchanged=True,
                  solver_started=False, theory_recomputed_or_extrapolated=False,
                  production_modified=False, physical_acceptance=False)
    with CHECK.open('x', encoding='utf8') as stream:
        json.dump(record, stream, indent=2, allow_nan=False)
    print(json.dumps(dict(passed=True, figures=[str(p) for p in outputs.values()],
                          check=str(CHECK)), indent=2))


if __name__ == '__main__':
    main()
