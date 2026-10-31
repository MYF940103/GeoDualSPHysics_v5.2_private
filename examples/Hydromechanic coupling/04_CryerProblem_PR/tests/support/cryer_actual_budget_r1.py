"""Fixed saved-state audit, never an integrator or a CUDA numerical replay."""
import os
for _key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[_key] = '1'
import argparse
import json
import re
import time
import traceback
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
import cryer_full_native_r1 as fn
from cryer_load_pair_r1 import bound, batches, add_pair, tensor
from cryer_darcy_closed_r1 import constants
from cryer_radial_consistency_r1 import Reference, selftest

TAG = 'cryer_actual_budget_r1'
T = fn.TESTS
PARTS = [86, 112, 133]


def put(path, value):
    fn.seal(path, value)


def moment(x, pairs, h, volume, ctes):
    n = len(x); out = np.zeros((n, 3, 3))
    for i, j, d, g in batches(x, pairs, h):
        g *= ctes['helper_gradient_scale']
        for row in range(3):
            for col in range(3):
                term = -d[:, row]*g[:, col]
                out[:, row, col] += np.bincount(i, weights=term*volume[j], minlength=n)
                out[:, row, col] += np.bincount(j, weights=term*volume[i], minlength=n)
    eigen = np.linalg.eigvalsh(out)
    assert eigen.min() > 0
    corr = np.linalg.inv(out)
    closure = np.max(abs(out@corr-np.eye(3)))
    assert closure < 1e-12
    return corr, float(eigen.min()), float(closure)


def evaluate(x, pairs, h, rho, mass, corr, velocity, stress, pressure, ctes, cs):
    n = len(x); volume = mass/rho
    volop = (mass.astype(np.float32)/rho.astype(np.float32)).astype(float)
    used = stress.astype(np.float32).astype(float)
    gradop = np.zeros((n, 3, 3)); gradraw = np.zeros_like(gradop)
    gradwork = np.zeros_like(gradop); forces = np.zeros((4, n, 3)); lap = np.zeros(n)
    for i, j, d, g in batches(x, pairs, h):
        g *= ctes['helper_gradient_scale']; dv = velocity[j]-velocity[i]
        for row in range(3):
            for col in range(3):
                vg = dv[:, row]*g[:, col]
                for out, left, right in [
                    (gradop, vg*volop[j], vg*volop[i]),
                    (gradraw, vg*volume[j], vg*volume[i]),
                    (gradwork, vg*mass[j]/rho[i], vg*mass[i]/rho[j])]:
                    out[:, row, col] += np.bincount(i, weights=left, minlength=n)
                    out[:, row, col] += np.bincount(j, weights=right, minlength=n)
        denom = np.sum(d*d, axis=1)+ctes['eta2_float_m2']
        sig = np.einsum('nij,nj->ni', used[i]/rho[i, None, None]**2+used[j]/rho[j, None, None]**2, g)
        pore = (-(pressure[i]+pressure[j])/(rho[i]*rho[j]))[:, None]*g
        load = (10000*(1/rho[i]**2+1/rho[j]**2))[:, None]*g
        dot = np.sum(d*(velocity[i]-velocity[j]), axis=1)
        av = -.1*cs*h*np.minimum(dot, 0)/(denom*(rho[i]+rho[j])*.5)
        for k, value in enumerate([sig, pore, load, -av[:, None]*g]):
            add_pair(forces[k], i, j, mass[j, None]*value, -mass[i, None]*value)
        gi = np.einsum('nij,nj->ni', corr[i], g)
        gj = np.einsum('nij,nj->ni', corr[j], g)
        hij = np.sum(d*(gi+gj)*.5, axis=1)/denom
        delta = pressure[i]-pressure[j]
        lap += np.bincount(i, weights=2*volop[j]*delta*hij, minlength=n)
        lap += np.bincount(j, weights=-2*volop[i]*delta*hij, minlength=n)
    gradient = gradop@corr.swapaxes(1, 2)
    raw = np.trace(gradraw, axis1=1, axis2=2)
    div = np.trace(gradient, axis1=1, axis2=2)
    mf = ctes['backends']['GPU']['kwn_pa']
    kappa = ctes['conductivity_float_m_s']/(ctes['water_rho_float_kg_m3']*ctes['backends']['GPU']['ghyd_m_s2'])
    comp = -mf*div; darcy = mf*kappa*lap
    damping = -4e-5*np.sqrt(2e6/(rho*h*h))[:, None]*velocity
    power = lambda a: float(np.sum(mass[:, None]*velocity*a))
    ps = power(forces[0]); pp = power(forces[1]); pv = power(forces[3])
    sw = float(np.einsum('n,nij,nij->', volume, used, gradwork))
    pw = float(np.sum(volume*pressure*raw))
    tol = 1e-9*max(abs(ps)+abs(pp)+abs(sw)+abs(pw), 1e-6)
    assert abs(ps+sw) < tol and abs(pp-pw) < tol and pv <= tol
    closed_sum = float(volop@lap); closed_abs = float(volop@abs(lap))
    assert abs(closed_sum) <= 1e-10*max(closed_abs, 1e-15)
    darcy_work = float(np.sum(volop*pressure*darcy)/mf)
    assert darcy_work <= 1e-10
    force = forces*mass[None, :, None]
    net = np.linalg.norm(force.sum(axis=1), axis=1)
    scale = np.linalg.norm(force, axis=2).sum(axis=1)
    assert np.all(net <= 1e-10*np.maximum(scale, 1e-15))
    return dict(raw_div=raw, corrected_div=div, comp=comp, darcy=darcy, net_rate=comp+darcy,
        forces=forces, total_acc=forces.sum(axis=0)+damping,
        powers=dict(stress_W=ps, pore_W=pp, load_W=power(forces[2]), viscosity_W=pv,
            damping_W=power(damping), raw_stress_adjoint_residual_W=ps+sw,
            raw_pore_adjoint_residual_W=pp-pw, closed_symC_pressure_energy_rate_W=darcy_work,
            closed_symC_weighted_laplacian_sum=closed_sum,
            mixed_work_defect_W=ps+pp+float(np.einsum('n,nij,nij->', volume, stress, gradient))
                -float(np.sum(volume*pressure*div)),
            pair_net_force_norm_N=net.tolist()))


def metrics(values, mask, weights):
    a = np.asarray(values)[mask]; w = weights[mask]
    return dict(mean=float(np.average(a, weights=w)), rms=float(np.sqrt(np.average(a*a, weights=w))),
                absmax=float(abs(a).max()))


def main():
    check = T/'logs'/(TAG+'.check.json')
    paths = {k:T/'figures'/(TAG+suffix) for k, suffix in [
        ('regions', '_regions.csv'), ('centers', '_centers.csv'), ('shells', '_shells.csv'), ('plot', '.png')]}
    assert not any(p.exists() for p in [check]+list(paths.values())), 'Never overwrite retained evidence'
    started = time.perf_counter(); result = dict(analysis_checks_passed=False, solver_executed=False,
        physical_acceptance=False, production_implemented=False, automatic_long_run_admitted=False)
    try:
        previous = json.loads(fn.CHECK.read_text()); assert previous['native_safety_passed']
        manifest = json.loads(fn.INPUTS.read_text()); sealed = {e['path'].lower():e for e in manifest['inputs']}
        inputs = []; seen = set()
        def freeze(p, sealed_input=False):
            b = bound(p)
            if sealed_input: assert b['sha256'] == sealed[b['path'].lower()]['sha256'], b['path']
            if b['path'] not in seen: inputs.append(b); seen.add(b['path'])
        for p in [__file__, T/'notes'/(TAG+'.json'), fn.CHECK, fn.INPUTS,
                  T/'support/cryer_full_native_r1.py', T/'support/cryer_load_pair_r1.py',
                  T/'support/cryer_darcy_closed_r1.py', T/'support/cryer_radial_consistency_r1.py']:
            freeze(p)
        for p in [fn.CONFIG, fn.FOLDER/'Run.out', fn.READER, fn.READER_SOURCE,
                  *[fn.FOLDER/'data'/f'Part_{part:04d}.bi4' for part in [0]+PARTS]]:
            freeze(p, True)
        for e in previous['artifacts']:
            if e['path'].endswith('_summary.csv'):
                assert bound(e['path'])['sha256'] == e['sha256']; freeze(e['path'])
        initial = fn.native(fn.FOLDER, 0); ctx = fn.context(initial)
        params = fn.parameters(fn.CONFIG); grid, times = fn.schedule(params['dt'])
        assert not fn.inspect(initial, ctx, 0, params, grid, times)[2]
        x0 = ctx['x']; r0 = ctx['r']; er0 = x0/r0[:, None]
        h = float(initial.h.iloc[0]); mass = initial.mass.to_numpy(); w = ctx['v']
        ctes = constants(fn.CONFIG, h); ref = Reference(); result['reference_selftest'] = selftest(ref)
        cs = float(re.search(r'^Cs0=([^\r\n]+)', (fn.FOLDER/'Run.out').read_text(errors='replace'), re.M)[1])
        center = ctx['center']; surface = np.isin(ctx['fs'], [2, 3]); core = r0 <= .05-2*h
        regions = dict(center18=center, full_support_core=core,
            near_surface_non_drain=(~core)&(~surface), native_surface=surface, all_soil=np.ones(len(initial), bool))
        assert center.sum() == 18 and surface.sum() == 5153
        rows = []; centers = []; shells = []; runs = []
        initial_pairs = cKDTree(x0).query_pairs(2*h, output_type='ndarray')
        uniform = np.full(len(initial), 2100.)
        uniform_v = (mass.astype(np.float32)/uniform.astype(np.float32)).astype(float)
        initial_corr, initial_eig, initial_closure = moment(x0, initial_pairs, h, uniform_v, ctes)
        for part in PARTS:
            a = fn.native(fn.FOLDER, part); native_row, _, issues = fn.inspect(a, ctx, part, params, grid, times)
            assert not issues and np.array_equal(a.fstype, initial.fstype)
            t = native_row['time_s']; tau = t-params['TD']; x = a[['x', 'y', 'z']].to_numpy()
            pairs = cKDTree(x).query_pairs(2*h, output_type='ndarray')
            rad = np.linalg.norm(x, axis=1); er = x/rad[:, None]
            fa = ref.field(rad, tau); fi = ref.field(r0, tau)
            fields = dict(native=(a[['vx', 'vy', 'vz']].to_numpy(), tensor(a), a.pressure.to_numpy(), None),
                analytic_current=(np.float32(x*fa['v_over_r'][:, None]).astype(float),
                    fa['st'][:, None, None]*np.eye(3)+(fa['sr']-fa['st'])[:, None, None]*er[:, :, None]*er[:, None, :],
                    np.float32(fa['p']).astype(float), fa))
            for rho_label, rho in [('saved_rho', a.rho.to_numpy()), ('uniform_rho0', uniform)]:
                volop = (mass.astype(np.float32)/rho.astype(np.float32)).astype(float)
                corr, eig, closure = moment(x, pairs, h, volop, ctes)
                for field_label, (v, s, p, truth) in fields.items():
                    print(f'Part{part} {field_label} {rho_label}', flush=True)
                    z = evaluate(x, pairs, h, rho, mass, corr, v, s, p, ctes, cs)
                    save_case(part, t, tau, field_label, rho_label, rho, p, v, z, truth, eig, closure,
                              a, regions, w, r0, rows, centers, shells, runs, params, ctes)
            v = np.float32(x0*fi['v_over_r'][:, None]).astype(float)
            s = fi['st'][:, None, None]*np.eye(3)+(fi['sr']-fi['st'])[:, None, None]*er0[:, :, None]*er0[:, None, :]
            z = evaluate(x0, initial_pairs, h, uniform, mass, initial_corr, v, s, np.float32(fi['p']).astype(float), ctes, cs)
            save_case(part, t, tau, 'analytic_initial', 'uniform_rho0', uniform, np.float32(fi['p']).astype(float),
                      v, z, fi, initial_eig, initial_closure, a, regions, w, r0, rows, centers, shells, runs, params, ctes)
        for name, data in [('regions', rows), ('centers', centers), ('shells', shells)]:
            pd.DataFrame(data).to_csv(paths[name], index=False, float_format='%.17g')
        plot(rows, paths['plot'])
        result.update(analysis_checks_passed=True, inputs=inputs, artifacts=[bound(p) for p in paths.values()],
            parts=PARTS, initial_part=0, selected_native_safety_frames=4, cases=15, rows=len(rows),
            constants=ctes, runs=runs, wall_seconds=time.perf_counter()-started,
            note='Offline mathematical residuals and coefficient sensitivity only; see bound admission for limitations.')
    except Exception:
        result.update(error=traceback.format_exc(), wall_seconds=time.perf_counter()-started)
    put(check, result)
    print(json.dumps({k:result.get(k) for k in ['analysis_checks_passed', 'error', 'wall_seconds']}), flush=True)
    if not result['analysis_checks_passed']: raise SystemExit(1)


def save_case(part, t, tau, field_label, rho_label, rho, p, velocity, z, truth, eig, closure,
              a, regions, w, r0, rows, centers, shells, runs, params, ctes):
    base = dict(part=part, time_s=t, tau_s=tau, field=field_label, rho_choice=rho_label)
    mf = ctes['backends']['GPU']['kwn_pa']
    kappa = ctes['conductivity_float_m_s']/(ctes['water_rho_float_kg_m3']*ctes['backends']['GPU']['ghyd_m_s2'])
    vals = {k:z[k] for k in ['raw_div', 'corrected_div', 'comp', 'darcy', 'net_rate']}
    vals.update(rho=rho, pressure=p, speed=np.linalg.norm(velocity, axis=1),
                total_acc=np.linalg.norm(z['total_acc'], axis=1), raw_ar=-rho*z['raw_div'])
    for k, name in enumerate(['stress_acc', 'pore_acc', 'load_acc', 'viscosity_acc']):
        vals[name] = np.linalg.norm(z['forces'][k], axis=1)
    if truth is not None:
        vals.update(comp_error=z['comp']+mf*truth['div'],
                    darcy_error=z['darcy']-mf*kappa*truth['lap'], net_rate_error=z['net_rate']-truth['pt'],
                    continuum_scalar_rounding_residual=mf*(-truth['div']+kappa*truth['lap'])-truth['pt'])
    ar = vals['raw_ar']
    for fraction, label in [(1., 'full'), (.5, 'predictor_half')]:
        vals['conditional_'+label+'_density_increment'] = np.float32(rho+params['dt']*fraction*ar).astype(float)-rho
        vals['conditional_'+label+'_lost_nonzero'] = ((ar != 0)&(vals['conditional_'+label+'_density_increment'] == 0)).astype(float)
    for region, mask in regions.items():
        row = dict(**base, region=region, count=int(mask.sum()))
        for name, value in vals.items():
            row.update({name+'_'+k:v for k, v in metrics(value, mask, w).items()})
        rows.append(row)
    for i in np.flatnonzero(regions['center18']):
        centers.append(dict(**base, id=int(a.id.iloc[i]), **{k:float(v[i]) for k, v in vals.items()}))
    for shell in np.unique(np.rint(r0/.0025).astype(int)):
        mask = np.rint(r0/.0025).astype(int) == shell
        row = dict(**base, initial_radius_m=float(np.mean(r0[mask])), count=int(mask.sum()))
        for name in ['comp', 'darcy', 'net_rate', 'pressure', 'raw_div', 'corrected_div', 'rho', 'total_acc']:
            row.update({name+'_'+k:v for k, v in metrics(vals[name], mask, w).items()})
        shells.append(row)
    receiver = ~regions['native_surface']
    active_work = float(np.sum((a.mass.to_numpy().astype(np.float32)/rho.astype(np.float32)).astype(float)*p*np.where(receiver, z['darcy'], 0))/mf)
    runs.append(dict(**base, pair_matrix_min_eigenvalue=eig, affine_closure_absmax=closure,
        analytic_native_surface_pressure_absmax_pa=float(abs(p[regions['native_surface']]).max()),
        active_receiver_darcy_pressure_energy_rate_W=active_work, **z['powers']))


def plot(rows, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    df = pd.DataFrame(rows); fig, axes = plt.subplots(2, 2, figsize=(13, 8), layout='constrained')
    colors = {'native':'tab:blue', 'analytic_current':'tab:orange', 'analytic_initial':'tab:green'}
    for (field, rho), g in df[df.region.eq('center18')].groupby(['field', 'rho_choice']):
        g = g.sort_values('tau_s'); label = field+' / '+rho
        style = '--' if rho == 'uniform_rho0' and field != 'analytic_initial' else '-'
        for ax, key in [(axes[0, 0], 'comp_mean'), (axes[0, 1], 'darcy_mean'),
                        (axes[1, 0], 'net_rate_mean'), (axes[1, 1], 'total_acc_rms')]:
            ax.plot(g.tau_s, g[key], marker='o', linestyle=style, color=colors[field], label=label)
    for ax, title in zip(axes.flat, ['Compression source', 'symC Darcy', 'Unclamped source sum', 'Total acceleration RMS']):
        ax.set(xlabel='Actual time since drainage (s)', title=title); ax.grid(alpha=.25)
    for ax in [axes[0, 0], axes[0, 1], axes[1, 0]]: ax.set_ylabel('Center18 rate (Pa/s)')
    axes[1, 1].set_ylabel('Center18 (m/s²)')
    axes[0, 0].legend(fontsize=7)
    fig.suptitle('Cryer actual saved-state mathematics — not a CUDA replay or new trajectory')
    fig.savefig(output, dpi=170); plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--run', action='store_true')
    if parser.parse_args().run: main()
    else: parser.print_help()
