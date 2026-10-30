"""Offline gravity-on analytical-start profiles; finite-Kw references are quasi-static diagnostics."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
import sw_mode3_short_r1 as core


def reference(z, t, p, finite=True):
    z = np.asarray(z, dtype=float)
    b = (p['rho']-p['rho_w'])*p['g']
    B = p['Mf']/(p['M']+p['Mf'])
    cv0 = p['k']*p['M']/(p['rho_w']*p['g'])
    q0 = B*b*(p['H']-z)
    if t == 0:
        q, settlement = q0, np.zeros_like(z)
    else:
        lam = (2*np.arange(1024)+1)*np.pi/(2*p['H'])
        coefficients = 2*B*b/(p['H']*lam**2)
        decay = np.exp(-(B if finite else 1)*cv0*lam**2*t)
        q = np.cos(z[:, None]*lam)@(coefficients*decay)
        integral = np.sin(z[:, None]*lam)@(coefficients*decay/lam)
        settlement = (B*b*(p['H']*z-z*z/2)-integral)/p['M']*1000
    return dict(q_pa=q, p_pa=p['rho_w']*p['g']*(p['H']-z)+q,
                settlement_increment_mm=settlement, legacy_Tv=cv0*t/p['H']**2,
                finite_Kw_Tv=B*cv0*t/p['H']**2)


def review(tag):
    tests = core.TESTS
    paths = {key: tests/folder/(tag+suffix) for key, folder, suffix in [
        ('check', 'logs', '.analysis.json'), ('png', 'figures', '_review.png'),
        ('profiles', 'figures', '_review_profiles.csv'), ('history', 'figures', '_review_history.csv')]}
    assert not any(p.exists() for p in paths.values()), 'Fresh analysis only'
    check_path = tests/'logs'/(tag+'.check.json')
    check = core.read(check_path)
    assert check['passed'] and not check.get('held_jobs', [])
    run = core.read(check['run']['path']); prepared = core.read(run['prepared']['path'])
    records = [core.bound(__file__), core.bound(core.__file__), core.bound(check_path), check['run'], run['prepared']]
    profiles, histories, results = [], [], {}
    for job, rr in zip(prepared['jobs'], check['jobs']):
        r = core.read(rr['path']); done = core.read(r['sealed_completion']['path'])
        assert r['passed'] and done['solver_finished'] and done['exit_code'] == 0 and done['owned_exited']
        src = next(x for x in r['artifacts'] if Path(x['path']).name == job['name']+'_profiles.csv')
        records += [rr, r['sealed_completion'], job['config'], src]+r['artifacts']
        core.verify(records)
        p = core.parameters(Path(job['config']['path']).read_text(encoding='utf8'))
        a = pd.read_csv(src['path'], float_precision='round_trip')
        assert len(a) == job['frames']*100 and not a.duplicated(['part', 'layer']).any()
        a['job'] = job['name']; a['q_double_pa'] = a.pressure_pa-a.porepress0_pa
        top = a[a.layer == 99].set_index('part').z_m
        a['q_current_pa'] = a.pressure_pa-p['rho_w']*p['g']*(a.part.map(top)-a.z_m)
        h = []
        for row in r['rows']:
            b = a[a.part == row['part']].sort_values('layer')
            assert len(b) == 100 and b.time_s.eq(row['time_s']).all() and b.natural_step.eq(row['natural_step']).all()
            ref = reference(b.z0_m.to_numpy(), row['time_s'], p)
            oldref = reference(b.z0_m.to_numpy(), row['time_s'], p, finite=False)
            for key in ['q_pa', 'p_pa', 'settlement_increment_mm']:
                a.loc[b.index, 'H1_finite_'+key] = ref[key]
                a.loc[b.index, 'H1_legacy_'+key] = oldref[key]
            h.append(dict(row, job=job['name'], legacy_Tv=ref['legacy_Tv'], finite_Kw_Tv=ref['finite_Kw_Tv'],
                bottom_p_pa=float(b.pressure_pa.iloc[0]), bottom_native_q_pa=float(b.excess_native_pa.iloc[0]),
                bottom_current_q_pa=float(b.q_current_pa.iloc[0]), top_s_mm=float(b.settlement_mm.iloc[-1]),
                bottom_s_mm=float(b.settlement_mm.iloc[0]), H1_finite_bottom_p_pa=float(ref['p_pa'][0]),
                pressure_H1_finite_rms_pa=float(np.sqrt(np.mean((b.pressure_pa.to_numpy()-ref['p_pa'])**2))),
                settlement_H1_increment_rms_mm=float(np.sqrt(np.mean((b.settlement_mm.to_numpy()-ref['settlement_increment_mm'])**2)))))
        history = pd.DataFrame(h); final = a[a.part == job['frames']-1].sort_values('layer')
        results[job['name']] = dict(final=history.iloc[-1].to_dict(), maximum_pressure_reference_rms_pa=float(history.pressure_H1_finite_rms_pa.max()),
            initial_reference=r['initial_reference'], original_profiles=src)
        profiles.append(final); histories.append(history)
    core.verify(records)
    pd.concat(profiles).to_csv(paths['profiles'], index=False)
    pd.concat(histories).to_csv(paths['history'], index=False)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(13, 8), constrained_layout=True)
    for b, h in zip(profiles, histories):
        name = b.job.iloc[0].replace(tag+'_', '')
        axes[0, 0].plot(b.pressure_pa/1000, b.z0_m, label=name)
        axes[0, 1].plot(b.q_current_pa/1000, b.z0_m, label=name+' current hydro')
        axes[0, 1].plot(b.excess_native_pa/1000, b.z0_m, '--', label=name+' fixed p0')
        axes[0, 2].plot(b.settlement_mm, b.z0_m, label=name)
        axes[1, 0].plot(h.time_s, h.bottom_p_pa/1000, label=name)
        axes[1, 1].plot(h.time_s, h.top_s_mm, label=name+' top')
        axes[1, 1].plot(h.time_s, h.bottom_s_mm, '--', label=name+' bottom')
        axes[1, 2].plot(h.time_s, h.speed_max_m_s, label=name)
    axes[0, 0].plot(b.H1_finite_p_pa/1000, b.z0_m, 'k--', label='H1 finite-Kw diagnostic')
    axes[0, 0].plot(b.H1_legacy_p_pa/1000, b.z0_m, 'k:', label='H1 legacy-Cv diagnostic')
    axes[0, 2].plot(b.H1_finite_settlement_increment_mm, b.z0_m, 'k--', label='H1 quasi-static increment')
    axes[1, 0].plot(h.time_s, h.H1_finite_bottom_p_pa/1000, 'k--', label='H1 quasi-static diagnostic')
    titles = ['Final total p [kPa]', 'Final two excess definitions [kPa]', 'Material incremental settlement [mm]',
              'Bottom total p [kPa]', 'Top/bottom incremental settlement [mm]', 'Maximum native soil speed [m/s]']
    for i, (ax, title) in enumerate(zip(axes.flat, titles)):
        ax.set(title=title, xlabel='Actual saved time [s]' if i >= 3 else '', ylabel='Initial material z [m]' if i < 3 else '')
        ax.grid(alpha=.25); ax.legend(fontsize=7)
    fig.suptitle('Fresh analytical gravity-on startup; all saved observations, no smoothing; not physical acceptance')
    fig.savefig(paths['png'], dpi=180); plt.close(fig)
    core.verify(records)
    core.seal(paths['check'], dict(analysis_checks_passed=True, inputs=core.unique(records), jobs=results,
        theory_scope='Derived finite-Kw and legacy-Cv quasi-static H1 diagnostics of the ACTUAL mode3 hydro-preloaded state,not exact dynamic startup truth or paper zero-p initial state.',
        displacement_scope='Increment since analytical stress initialization,not absolute selfweight displacement. Native fixed p0 and current drained-material-plane hydro excess are kept separately.',
        no_theory_accuracy_gate_applied=True, physical_acceptance=False, solver_started=False,
        figures_require_visual_review=True, artifacts=[core.bound(p) for key,p in paths.items() if key != 'check']))
    print(paths['check'])


def selftest():
    xml = core.expected(core.JOBS[0], core.CASE/'private/solver.exe')[0]; p = core.parameters(xml)
    z = np.array([0., .005, .995, 1.])
    r0 = reference(z, 0., p); assert np.all(r0['settlement_increment_mm'] == 0) and r0['q_pa'][-1] == 0
    r = reference(z, 100., p); B=p['Mf']/(p['M']+p['Mf'])
    assert abs(r['settlement_increment_mm'][-1]-B*(p['rho']-p['rho_w'])*p['g']*p['H']**2/(2*p['M'])*1000)<1e-10
    assert reference(np.array([1.]), .001, p)['q_pa'][0] < 1e-9
    print(json.dumps(dict(passed=True, files_written=False, solver_started=False)))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__); modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--selftest',action='store_true'); modes.add_argument('--review',action='store_true')
    parser.add_argument('--tag',default=core.TAG); args=parser.parse_args()
    assert args.tag and Path(args.tag).name==args.tag and args.tag.replace('_','').isalnum()
    if args.selftest:selftest()
    elif args.review:review(args.tag)
    else:parser.print_help()
