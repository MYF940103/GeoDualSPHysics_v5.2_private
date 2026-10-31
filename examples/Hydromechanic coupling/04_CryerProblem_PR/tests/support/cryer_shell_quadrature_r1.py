"""Fixed-node radial-shell quadrature sensitivity; no solver or production mass change."""
import os
for _key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS']:
    os.environ[_key] = '1'
import argparse
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import re
import time
import traceback
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from cryer_actual_budget_r1 import moment, evaluate, metrics
import cryer_full_native_r1 as fn
from cryer_load_pair_r1 import bound, batches
from cryer_darcy_closed_r1 import constants
from cryer_radial_consistency_r1 import Reference, selftest as reference_selftest

TAG = 'cryer_shell_quadrature_r1'
TAUS = [.02, .04205180291164746, .0625]
R, Q, RHO = .05, 10000., 2100.


def shell_volumes(radius):
    shell = np.rint(radius/.0025).astype(int)
    labels = np.unique(shell); assert np.array_equal(labels, np.arange(1, 21))
    centers = np.array([radius[shell == b].mean() for b in labels])
    assert np.max(abs(radius-centers[shell-1])) < 1e-13
    edges = np.r_[0., .5*(centers[:-1]+centers[1:]), R]
    counts = np.bincount(shell, minlength=21)[1:]
    target = 4*np.pi/3*np.diff(edges**3)
    volume = (target/counts)[shell-1]
    assert np.all(volume > 0) and abs(volume.sum()/(4*np.pi*R**3/3)-1) < 1e-14
    return volume, shell, centers, edges, counts


def partition_gradient(x, pairs, h, volume, ctes):
    out = np.zeros_like(x)
    for i, j, d, g in batches(x, pairs, h):
        g *= ctes['helper_gradient_scale']
        for k in range(3):
            out[:, k] += np.bincount(i, weights=volume[j]*g[:, k], minlength=len(x))
            out[:, k] += np.bincount(j, weights=-volume[i]*g[:, k], minlength=len(x))
    return out


def selftest():
    radii = np.repeat(np.arange(1, 21)*.0025, np.arange(1, 21))
    v, b, r, e, n = shell_volumes(radii)
    assert np.allclose(np.bincount(b, weights=v)[1:], 4*np.pi/3*np.diff(e**3), rtol=1e-14)
    return dict(passed=True, files_written=False, native_reader_started=False, solver_started=False,
                shell_count=20, radial_second_moment_is_not_fitted=True)


def plot(regions, radial, quadrature, runs, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 2, figsize=(13, 11), layout='constrained')
    peak = TAUS[1]; colors = {'A_native_equal_mass':'tab:blue', 'B_shell_volume':'tab:orange'}
    for label, color in colors.items():
        q = quadrature[quadrature.quadrature.eq(label)]
        axes[0, 0].plot(q.radius_m, q.volume_fraction*100, 'o-', color=color, label=label)
        c = regions[regions.region.eq('center18') & regions.quadrature.eq(label)]
        for key, style in [('comp_error', ':'), ('darcy_error', '--'), ('net_rate_error', '-')]:
            axes[0, 1].plot(c.tau_s, c[key+'_mean']/1e6, style, color=color, marker='o', label=label+' / '+key)
        s = radial[radial.quadrature.eq(label) & radial.tau_s.eq(peak)]
        axes[1, 0].plot(s.radius_m, s.net_rate_error_mean/1e6, 'o-', color=color, label=label)
        for key, style in [('mechanical_acc', '-'), ('zeroth_acc', '--'), ('difference_acc', ':')]:
            axes[1, 1].plot(s.radius_m, s[key+'_rms'], style, color=color, label=label+' / '+key)
        axes[2, 0].plot(s.radius_m, s.mechanical_tangent_rms_m_s2, 'o-', color=color, label=label)
        z = pd.DataFrame([r for r in runs if r['quadrature'] == label])
        axes[2, 1].plot(z.tau_s, z.mixed_work_defect_W, 'o-', color=color, label=label)
    titles = ['Fixed-node shell volume fractions', 'Center18 instantaneous rate errors',
              'Peak-time unclamped rate error by shell', 'Peak-time raw force decomposition',
              'Peak-time within-shell tangential scatter', 'Raw force versus corrected-gradient work defect']
    ylabs = ['Volume fraction (%)', 'Rate error (MPa/s)', 'Rate error (MPa/s)',
             'Acceleration vector RMS (m/s²)', 'Tangential acceleration RMS (m/s²)', 'Power (W)']
    for i, (ax, title, ylabel) in enumerate(zip(axes.flat, titles, ylabs)):
        ax.set(title=title, ylabel=ylabel, xlabel='Time since drainage (s)' if i in [1, 5] else 'Initial radius (m)')
        ax.grid(alpha=.25); ax.legend(fontsize=6)
    fig.suptitle('Cryer fixed-node quadrature screen: hypothetical nonuniform weights, not a trajectory')
    with output.open('xb') as stream: fig.savefig(stream, format='png', dpi=170)
    plt.close(fig)


def main():
    target = fn.LOGS/(TAG+'.check.json'); logfile = fn.LOGS/(TAG+'.log')
    paths = {k:fn.FIGURES/(TAG+s) for k, s in [('regions', '_regions.csv'), ('radial', '_radial.csv'),
        ('quadrature', '_quadrature.csv'), ('powers', '_powers.csv'), ('plot', '.png')]}
    assert not any(p.exists() for p in [target, logfile]+list(paths.values())), 'Never overwrite retained evidence'
    started = time.perf_counter(); result = dict(analysis_checks_passed=False, solver_started=False,
        physical_acceptance=False, full_half_validation=False, production_implemented=False)
    with logfile.open('x', encoding='utf8') as log:
        def say(message):
            print(message, flush=True); log.write(message+'\n'); log.flush()
        try:
            if os.name == 'nt':
                api = ctypes.WinDLL('kernel32', use_last_error=True)
                api.GetCurrentProcess.restype = wintypes.HANDLE
                api.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
                assert api.SetPriorityClass(api.GetCurrentProcess(), 0x4000), ctypes.get_last_error()
            prior = json.loads(fn.CHECK.read_text()); assert prior['native_safety_passed'] and prior['initial35_passed']
            assert bound(fn.INPUTS)['sha256'] == prior['inputs_manifest']['sha256']
            sealed = {r['path'].lower():r for r in json.loads(fn.INPUTS.read_text())['inputs']}
            inputs = []
            for p in [Path(__file__), fn.TESTS/'notes'/(TAG+'.json'), fn.CHECK, fn.INPUTS,
                *[fn.TESTS/'support'/n for n in ['cryer_actual_budget_r1.py', 'cryer_full_native_r1.py',
                'cryer_load_pair_r1.py', 'cryer_darcy_closed_r1.py', 'cryer_radial_consistency_r1.py']]]:
                inputs.append(bound(p))
            for p in [fn.CONFIG, fn.FOLDER/'Run.out', fn.FOLDER/'data/Part_0000.bi4', fn.READER, fn.READER_SOURCE]:
                b = bound(p); assert b == sealed[b['path'].lower()], b['path']; inputs.append(b)
            a = fn.native(fn.FOLDER, 0); ctx = fn.context(a); params = fn.parameters(fn.CONFIG)
            grid, times = fn.schedule(); assert not fn.inspect(a, ctx, 0, params, grid, times)[2]
            assert a.rho.eq(RHO).all() and a.mass.eq(a.mass.iloc[0]).all() and params['Q'] == Q
            x = ctx['x']; r = ctx['r']; er = x/r[:, None]; h = float(a.h.iloc[0]); mass0 = a.mass.to_numpy()
            vb, shell, radii, edges, counts = shell_volumes(r); va = mass0/RHO
            rho = np.full(len(a), RHO); ctes = constants(fn.CONFIG, h)
            cs = float(re.search(r'^Cs0=([^\r\n]+)', (fn.FOLDER/'Run.out').read_text(errors='replace'), re.M)[1])
            ref = Reference(); result['reference_selftest'] = reference_selftest(ref)
            pairs = cKDTree(x).query_pairs(2*h, output_type='ndarray')
            surface = np.isin(ctx['fs'], [2, 3]); core = r <= R-2*h
            masks = dict(center18=ctx['center'], full_support_core=core,
                near_surface_non_drain=(~core)&(~surface), native_surface=surface, all_soil=np.ones(len(a), bool))
            rows = []; radial = []; quadrature = []; runs = []; quad_summary = []
            for label, volume in [('A_native_equal_mass', va), ('B_shell_volume', vb)]:
                mass = mass0 if label.startswith('A_') else RHO*volume
                volop = (mass.astype(np.float32)/rho.astype(np.float32)).astype(float)
                corr, eig, closure = moment(x, pairs, h, volop, ctes)
                partgrad = partition_gradient(x, pairs, h, volume, ctes)
                quad_summary.append(dict(quadrature=label, volume_m3=float(volume.sum()),
                    volume_over_sphere=float(volume.sum()/(4*np.pi*R**3/3)),
                    weighted_r2_over_R2=float(np.average((r/R)**2, weights=volume)),
                    moment_min_eigenvalue=eig, affine_closure_absmax=closure,
                    partition_gradient_center_rms_m_inv=float(np.sqrt(np.mean(np.sum(partgrad[ctx['center']]**2, axis=1))))))
                for b in range(1, 21):
                    m = shell == b; quadrature.append(dict(quadrature=label, shell=b, radius_m=radii[b-1], count=int(counts[b-1]),
                        inner_edge_m=edges[b-1], outer_edge_m=edges[b], volume_m3=float(volume[m].sum()),
                        volume_fraction=float(volume[m].sum()/volume.sum()), particle_volume_m3=float(volume[m][0])))
                for tau in TAUS:
                    say(f'{label} tau={tau:.17g}')
                    truth = ref.field(r, tau); p = np.float32(truth['p']).astype(float); p[surface] = 0.
                    velocity = np.float32(x*truth['v_over_r'][:, None]).astype(float)
                    stress = truth['st'][:, None, None]*np.eye(3)+(truth['sr']-truth['st'])[:, None, None]*er[:, :, None]*er[:, None, :]
                    z = evaluate(x, pairs, h, rho, mass, corr, velocity, stress, p, ctes, cs)
                    mechanical = z['forces'][:3].sum(axis=0)
                    shifted = stress.astype(np.float32).astype(float)+(Q-p)[:, None, None]*np.eye(3)
                    zeroth = 2/RHO*np.einsum('nij,nj->ni', shifted, partgrad)
                    difference = mechanical-zeroth
                    mf = ctes['backends']['GPU']['kwn_pa']
                    kappa = ctes['conductivity_float_m_s']/(ctes['water_rho_float_kg_m3']*ctes['backends']['GPU']['ghyd_m_s2'])
                    vals = dict(comp_error=z['comp']+mf*truth['div'], darcy_error=z['darcy']-mf*kappa*truth['lap'],
                        net_rate_error=z['net_rate']-truth['pt'], comp=z['comp'], darcy=z['darcy'], net_rate=z['net_rate'],
                        clamped_rate_error=np.where(surface, 0., z['net_rate'])-truth['pt'],
                        mechanical_acc=np.linalg.norm(mechanical, axis=1), zeroth_acc=np.linalg.norm(zeroth, axis=1),
                        difference_acc=np.linalg.norm(difference, axis=1), total_acc=np.linalg.norm(z['total_acc'], axis=1))
                    for k, name in enumerate(['stress_acc', 'pore_acc', 'load_acc', 'viscosity_acc']):
                        vals[name] = np.linalg.norm(z['forces'][k], axis=1)
                    for name, mask in masks.items():
                        row = dict(quadrature=label, tau_s=tau, region=name, count=int(mask.sum()))
                        for key, value in vals.items():
                            row.update({key+'_'+k:v for k, v in metrics(value, mask, va).items()})
                            row.update({key+'_own_weight_'+k:v for k, v in metrics(value, mask, volume).items()})
                        rows.append(row)
                    ar = np.sum(mechanical*er, axis=1); tangent = mechanical-ar[:, None]*er
                    for b in range(1, 21):
                        m = shell == b; row = dict(quadrature=label, tau_s=tau, shell=b, radius_m=radii[b-1], count=int(m.sum()),
                            mechanical_radial_mean_m_s2=float(ar[m].mean()), mechanical_radial_std_m_s2=float(ar[m].std()),
                            mechanical_tangent_rms_m_s2=float(np.sqrt(np.mean(np.sum(tangent[m]**2, axis=1)))))
                        for key, value in vals.items():row.update({key+'_'+k:v for k, v in metrics(value, m, va).items()})
                        radial.append(row)
                    runs.append(dict(quadrature=label, tau_s=tau, **z['powers'],
                        raw_mechanical_power_W=sum(z['powers'][n] for n in ['stress_W', 'pore_W', 'load_W']),
                        active_receiver_symC_work_W=float(np.sum(volop*p*np.where(surface, 0., z['darcy']))/mf),
                        scalar_continuum_rounding_residual_absmax_pa_s=float(abs(mf*(-truth['div']+kappa*truth['lap'])-truth['pt']).max())))
            dfs = [pd.DataFrame(v) for v in [rows, radial, quadrature, runs]]
            for name, df in zip(['regions', 'radial', 'quadrature', 'powers'], dfs):df.to_csv(paths[name], mode='x', index=False, float_format='%.17g')
            plot(*dfs[:3], runs, paths['plot'])
            result.update(analysis_checks_passed=True, inputs=inputs, artifacts=[bound(p) for p in paths.values()],
                quadratures=quad_summary, runs=runs, pair_count=len(pairs), theoretical_times_s=TAUS,
                native_states_decoded=1, actual_native_clock_s=0., constants=ctes,
                same_native_nodes=True, baseline_native_fields_unchanged=True,
                limits='B is a hypothetical nonuniform-mass quadrature, not supported by the current uniform-soil-mass solver. Instantaneous errors do not attribute the dynamic peak deficit.')
        except Exception:result['error'] = traceback.format_exc(); say(result['error'])
        result['wall_seconds'] = time.perf_counter()-started
        fn.seal(target, result); say(json.dumps({k:result.get(k) for k in ['analysis_checks_passed', 'wall_seconds', 'error']}))
    if not result['analysis_checks_passed']:raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--selftest', action='store_true'); mode.add_argument('--run', action='store_true'); args = parser.parse_args()
    if args.selftest:print(json.dumps(selftest()))
    elif args.run:main()
    else:parser.print_help()
