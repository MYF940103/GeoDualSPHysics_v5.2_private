"""Closed-sphere Darcy algebra only; explicit --run, never advances a solver."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import traceback
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from cryer_load_pair_r1 import (CASE, TESTS, REPO, LIAN, READER, R, DP,
    native, bound, write_json, batches, correction)

TAG = 'cryer_darcy_closed_r1'
FIELDS = ['constant_10k', 'quartic_Neumann', 'quartic_Neumann_plus_10k']
OPERATORS = ['current_receiver_C', 'raw_I_offline', 'symmetric_C_offline']


def arithmetic_selftest():
    vi, vj, difference, hi, hj = .6, .4, 1.5, -3., -5.
    left, right = vj*difference*hi, -vi*difference*hj
    predicted = vi*vj*difference*(hi-hj)
    assert abs(vi*left+vj*right-predicted) < 1e-14
    common = (hi+hj)/2
    assert abs(vi*(vj*difference*common)+vj*(-vi*difference*common)) < 1e-14
    return dict(passed=True, checks=['Reverse-end pressure difference changes sign; d and grad both reverse.',
        'Receiver-C weighted pair sum equals ViVj(pi-pj)(Hi-Hj).',
        'Common pair H cancels the weighted pair sum.'], physical_acceptance=False)


def constants(xml, h):
    root = ET.parse(xml).getroot()
    get = lambda name: float(np.float32(root.find('.//hydromechanics/'+name).get('value')))
    kw, por, k, rw = [get(n) for n in ['PoreWaterBulkModulus','Porosity','HydraulicConductivity','PoreWaterRho']]
    gravity = root.find('.//constantsdef/gravity')
    assert all(float(gravity.get(axis)) == 0 for axis in 'xyz'), 'No gravity-head term is admitted here'
    cpu_kw_n = kw/por
    gpu_kw_n = float(np.float32(np.float32(kw)/np.float32(por)))
    bwen = float(np.float32(-2.08891/h**4))
    scale = bwen/(-2.08891/h**4)
    eta2 = float(np.float32((h*.1)**2))
    backends = dict(CPU=dict(kwn_pa=cpu_kw_n, ghyd_m_s2=9.80665),
        GPU=dict(kwn_pa=gpu_kw_n, ghyd_m_s2=float(np.float32(9.80665))))
    for values in backends.values(): values['diffusion_factor_m2_s'] = values['kwn_pa']*2*k/(rw*values['ghyd_m_s2'])
    return dict(h_m=h, bwen_float=bwen, helper_gradient_scale=scale, eta2_float_m2=eta2,
        kw_float_pa=kw, porosity_float=por, conductivity_float_m_s=k, water_rho_float_kg_m3=rw,
        backends=backends)


def metrics(rate, pressure, volume, kwn):
    integrated = float(np.dot(volume, rate))
    absolute = float(np.dot(volume, np.abs(rate)))
    quadratic = .5*float(np.dot(volume, pressure*pressure))
    quadratic_change = float(np.dot(volume, pressure*rate))
    return dict(volume_integrated_rate_pa_m3_s=integrated,
        volume_integrated_abs_rate_pa_m3_s=absolute,
        relative_signed_drift=integrated/absolute if absolute else 0.,
        relative_abs_drift=abs(integrated)/absolute if absolute else 0.,
        volume_weighted_mean_rate_pa_s=integrated/float(volume.sum()),
        volume_weighted_rate_rms_pa_s=float(np.sqrt(np.average(rate*rate, weights=volume))),
        rate_min_pa_s=float(rate.min()), rate_max_pa_s=float(rate.max()), rate_abs_max_pa_s=float(np.abs(rate).max()),
        pressure_quadratic_pa2_m3=quadratic, pressure_quadratic_change_pa2_m3_s=quadratic_change,
        pore_energy_J=quadratic/kwn, pore_energy_change_W=quadratic_change/kwn)


def main():
    target = TESTS/'logs'/(TAG+'.check.json'); csv = TESTS/'figures'/(TAG+'_metrics.csv')
    assert not target.exists() and not csv.exists(), 'Never overwrite retained evidence'
    started = time.perf_counter(); rows = []
    result = dict(scope='Offline complete all-soil Darcy rates on a sealed initial sphere; drainage inactive.',
        physical_acceptance=False, production_implemented=False, solver_executed=False, analysis_checks_passed=False)
    try:
        folder = TESTS/'outputs/cryer_grad_peak_r1'; config = TESTS/'configs/cryer_grad_peak_r1_Def.xml'
        prior_path = TESTS/'logs/cryer_radial_patch_r1.check.json'; prior = json.loads(prior_path.read_text())
        assert prior['analysis_checks_passed']
        for entry in prior['inputs']:
            assert bound(entry['path'])['sha256'] == entry['sha256'], entry['path']
        inputs = [Path(__file__), TESTS/'notes'/(TAG+'.md'), prior_path,
            REPO/'src/source/JSphCpuSingle.cpp', REPO/'src/source/JSphGpu.cpp', REPO/'src/source/JSphGpuSingle.cpp',
            folder/'cryer_grad_peak_r1.xml']
        result['inputs'] = [bound(p) for p in inputs]+prior['inputs']
        result['arithmetic_selftest'] = arithmetic_selftest()
        a = native(folder, 0)
        assert len(a) == 37173 and a.id.nunique() == len(a)
        assert np.isfinite(a.to_numpy(dtype='<f8')).all() and a.position_double.eq(1).all()
        assert a.rho.eq(2100).all() and a.nout.eq(0).all() and a.time_s.eq(0).all()
        assert a.mass.eq(a.mass.iloc[0]).all()
        x = a[['x','y','z']].to_numpy(); radius = np.linalg.norm(x,axis=1)
        mass, rho, h = a.mass.to_numpy(), a.rho.to_numpy(), float(a.h.iloc[0]); volume = mass/rho
        operator_volume = (mass.astype(np.float32)/rho.astype(np.float32)).astype(float)
        volume_scale = float(operator_volume[0]/volume[0])
        assert np.array_equal(operator_volume/volume,np.full(len(a),volume_scale))
        result['constants'] = ctes = constants(config,h)
        result['native_identity'] = dict(soil_count=len(a), actual_time_s=0.,
            ids_sha256=hashlib.sha256(a.id.to_numpy(dtype='<u4').tobytes()).hexdigest(),
            native_volume_m3=float(volume.sum()), initial_position_double=1,
            operator_float_division_volume_m3=float(operator_volume.sum()),
            operator_volume_over_native_volume=volume_scale,
            surface_count=int(a.fstype.isin([2,3]).sum()), all_soil_receivers_enabled=True,
            pressure_fields_storage='Manufactured double values; production pressure storage is float. No integration or0ULP replay.')
        pairs = cKDTree(x).query_pairs(2*h, output_type='ndarray')
        corr, affine = correction(x,mass,rho,h,pairs)
        # Production vol2 is float mass/rho promoted to double. Both rescalings are uniform here.
        corr = corr/(ctes['helper_gradient_scale']*volume_scale)
        result.update(pair_count=len(pairs), correction=affine,
            correction_definition='Current CorrMat inverse from free-surface tracking, also used as porecorr; not the SoilStressRateGradCorr switch.',
            kernel_note='Uses actual float bwen/Eta2 and CPU/GPU scalar constants, but double distances and arithmetic; not float sqrt/qq/cell-order0ULP.')
        shape = (1-(radius/R)**2)**2
        pressure = np.stack([np.full(len(a),10000.), 10000.*shape, 10000.*shape+10000.])
        # The continuum quartic has dp/dr=-4P r/R²(1-r²/R²), exactly0 at r=R.
        result['manufactured_field'] = dict(amplitude_pa=10000., boundary_radial_derivative_pa_m=0.,
            pressure_formula='P*(1-r²/R²)^2, optionally plus constant10000Pa.',
            continuum_laplacian='-12P/R²+20P r²/R^4; integral over the exact sphere is0.',
            constant_pressure_is_computed=True, baseline_is_not_a_new_loading_state=True)
        lap = np.zeros((3,3,len(a))); pair_sum = np.zeros((3,3)); negative_h = np.zeros(3,dtype=np.int64)
        for i,j,d,g in batches(x,pairs,h):
            g = g*ctes['helper_gradient_scale']
            denom = np.sum(d*d,axis=1)+ctes['eta2_float_m2']
            hi = np.einsum('ni,nij,nj->n',d,corr[i],g)/denom
            hj = np.einsum('ni,nij,nj->n',d,corr[j],g)/denom
            raw = np.sum(d*g,axis=1)/denom; sym = .5*(hi+hj)
            for op,(left,right) in enumerate([(hi,hj),(raw,raw),(sym,sym)]):
                negative_h[op] += int(np.count_nonzero(left<0))
                for f,p in enumerate(pressure):
                    delta = p[i]-p[j]
                    lap[op,f] += np.bincount(i,weights=operator_volume[j]*delta*left,minlength=len(a))
                    lap[op,f] += np.bincount(j,weights=-operator_volume[i]*delta*right,minlength=len(a))
                    pair_sum[op,f] += float(np.sum(delta*(volume[i]*operator_volume[j]*left-volume[j]*operator_volume[i]*right)))
        result['pair_h_negative_counts'] = dict(zip(OPERATORS,map(int,negative_h)))
        for backend, scalar in ctes['backends'].items():
            factor = scalar['diffusion_factor_m2_s']; rates = factor*lap
            for op,name in enumerate(OPERATORS):
                for f,label in enumerate(FIELDS):
                    row = dict(backend_scalar=backend, operator=name, field=label,
                        **metrics(rates[op,f],pressure[f],volume,scalar['kwn_pa']))
                    predicted = float(factor*pair_sum[op,f])
                    row.update(pair_predicted_integrated_rate_pa_m3_s=predicted,
                        pair_identity_difference_pa_m3_s=row['volume_integrated_rate_pa_m3_s']-predicted,
                        baseline_rate_max_difference_pa_s=float(np.abs(rates[op,2]-rates[op,1]).max()))
                    rows.append(row)
            # A constant-p null result is checked only after every actual neighbour pair was accumulated.
            assert np.array_equal(rates[:,0],np.zeros_like(rates[:,0])), 'Constant-pressure null check failed'
        for entry in result['inputs']:
            assert bound(entry['path'])['sha256'] == entry['sha256'], entry['path']
        result['analysis_checks_passed'] = True
    except Exception as error:
        result.update(error=repr(error),traceback=traceback.format_exc())
    if rows:
        pd.DataFrame(rows).to_csv(csv,index=False,float_format='%.17g'); result['metrics_csv'] = bound(csv)
    result.update(wall_seconds=time.perf_counter()-started,limitations=[
        'No source/formal/input/geometry change, solver execution, dynamic preload or physical acceptance.',
        'All soil nodes evolve by this diagnostic Darcy term; no artificial p0 surface overwrite or external ghost reservoir.',
        'Absence of an external pair is not proof of a continuum Neumann condition or exact fluid-mass conservation.',
        'Raw I and symmetric-C are offline contrasts, not accepted production candidates. Zero integrated drift is not sufficient for local consistency.',
        'Pressure-energy uses fixed initial native volumes and Kwn; its derivative is a frozen-state diagnostic, not coupled total energy.',
        'CPU/GPU scalar factors are separate; geometry, kernel-distance arithmetic and manufactured pressure are shared offline double, not actual backend bitwise controls.'])
    write_json(target,result)
    print(json.dumps(dict(analysis_checks_passed=result['analysis_checks_passed'],physical_acceptance=False,
        wall_seconds=result['wall_seconds'],error=result.get('error'))),flush=True)
    if not result['analysis_checks_passed']: raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--run',action='store_true')
    if parser.parse_args().run: main()
    else: parser.print_help()
