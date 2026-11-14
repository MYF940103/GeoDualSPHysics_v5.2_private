"""Offline frozen-Part300 pressure-row review; no force, decoder or physical advance."""
import argparse
import csv
import json
import math
from pathlib import Path

T = Path(__file__).resolve().parents[1]
TAG = 'c08_h18_pressure_row_review_r1'
COMPONENT = 'c08_h18_pressure_row_r1'
SRC = T/'outputs'/COMPONENT
OUT = T/'figures'/TAG
REGIONS = ('all', 'interior_no_fixed', 'wall_adjacent', 'FS')
BASES = ('1', 'x', 'z', 'half_x2', 'xz', 'half_z2', 'half_x2_minus_z2')
WIDTHS = (0.000005, 0.000005/10, 0.000005/100)
HEADERS = {
    'rows.csv': 'part,time_s,tau_s,completed_step,native_id,region,FS,neighbors,fixed_neighbors,almostzero_excluded,x_m,z_m,p_Pa,J,n,V_m2,k_m_s,dkdJ,gamma_Pa_m,M_per_m,S_per_m_s,fluid_S_per_m_s,fixed_S_per_m_s,N_Pa_m_s,fixed_N_Pa_m_s,B_Pa_m_s,LP_pressure_Pa_m_s,Taylor_pressure_Pa_m_s,chain_pressure_Pa_m_s,row_pressure_Pa_m_s,N_minus_Sp_Pa_m_s,row_identity_error_Pa_m_s,row_identity_budget_Pa_m_s,actual_float_rate_Pa_s,literal_rate_Pa_s,row_rate_Pa_s,old_rate_budget_Pa_s,row_rate_error_Pa_s,A_min,A_max,negative_A,negative_fixed_A,A_absolute_sum,hS_over_M,soil_only_constant_shift1Pa_rate_Pa_s',
    'manufactured.csv': 'part,time_s,tau_s,completed_step,native_id,region,basis,full6805_analytic_donors,analytic_target_Pa_m_s,LP_Pa_m_s,Taylor_Pa_m_s,chain_Pa_m_s,row_pressure_Pa_m_s,direct_pressure_Pa_m_s,arithmetic_error,arithmetic_budget,full_N_minus_Sp,Eq22_gpx,Eq22_gpz,analytic_gpx,analytic_gpz',
    'shadows.csv': 'part,time_s,tau_s,completed_step,native_id,h_s,p_base_Pa,M_per_m,S_per_m_s,explicit_delta_Pa,BE_denominator,BE_defined,BE_positive_denominator,BE_delta_Pa,BE_new_Pa,BE_algebraic_error,BE_algebraic_budget,lagged_N_midpoint_denominator,lagged_N_midpoint_defined,lagged_N_midpoint_positive_denominator,lagged_N_midpoint_delta_Pa,lagged_N_midpoint_new_Pa,lagged_N_midpoint_algebraic_error,lagged_N_midpoint_algebraic_budget,rescaling_max_error_Pa,rescaling_budget_Pa',
    'summary.csv': 'region,basis,IDs,mean_response_Pa_m_s,RMS_error_Pa_m_s,max_abs_error_Pa_m_s',
    'coupled_CN.csv': 'node,h_normalized_s,M,S,A_neighbor,p_n,explicit_R_n,explicit_p_h,neighbor_p_h,diagonal_CN_p_new,rational_delta,second_Taylor_delta,measured_third_defect,exact_rational_third_defect,arithmetic_closure,arithmetic_budget',
}


def need(ok, message):
    if not bool(ok):
        raise RuntimeError(message)


def stat(path):
    path = Path(path).resolve()
    s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def bound(entry, consumed):
    need(stat(entry['path']) == entry, 'Bound input changed: '+entry['path'])
    consumed.append(entry)
    return Path(entry['path'])


def table(path, header, count):
    with path.open(newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        need(reader.fieldnames == header.split(','), 'Exact CSV schema differs: '+path.name)
        records = list(reader)
    need(len(records) == count and all(None not in q and None not in q.values() for q in records),
         'Complete rectangular CSV required: '+path.name)
    return records


def num(row, key):
    value = float(row[key])
    need(math.isfinite(value), 'Nonfinite CSV value '+key)
    return value


def integer(row, key):
    value = num(row, key)
    need(value.is_integer(), 'Noninteger CSV identity/count '+key)
    return int(value)


def gamma(n):
    t = n*0.5*float.fromhex('0x1.0000000000000p-52')
    need(t < 1, 'Arithmetic operation count outside original domain')
    return t/(1-t)


DMIN = float.fromhex('0x0.0000000000001p-1022')


def arithmetic_close(actual, reference, magnitude, operations=128, label='identity'):
    budget = gamma(operations)*magnitude + operations*DMIN
    need(math.isfinite(actual) and math.isfinite(reference) and math.isfinite(budget)
         and abs(actual-reference) <= budget, 'Binary64 arithmetic check failed: '+label)
    return budget


def original_budget(error, budget, label):
    need(math.isfinite(error) and math.isfinite(budget) and budget >= 0 and 0 <= error <= budget,
         'Original component budget failed: '+label)
    return error/budget if budget else 0.0


def write(path, records):
    need(records, 'Nonempty derived CSV required: '+path.name)
    with path.open('x', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execution-authorized', action='store_true')
    args = parser.parse_args()
    need(args.execution_authorized, 'Author-only until separate root review/admission')
    # Imports occur only after explicit offline-review admission; no project module is imported.
    global np, plt, SymLogNorm
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import SymLogNorm

    check = T/'logs'/(TAG+'.check.json')
    need(not check.exists() and not OUT.exists(), 'Existing complete/partial review is protected')
    component_path = T/'logs'/(COMPONENT+'.check.json')
    consumed = [stat(Path(__file__)), stat(T/'notes'/(TAG+'.md')), stat(component_path)]
    component = read(component_path)
    need(component['stage'] == COMPONENT and component['passed'] and component['consumed_stats_unchanged']
         and component['component_invocations'] == 1 and component['physical_steps'] == 0
         and component['physical_acceptance'] is False, 'A completed reviewed zero-step component is required')
    actual = read(bound(component['actual_call'], consumed))
    need(actual['actual_Popen_wait_exit'] == actual['actual_Win32_exit'] == 0
         and actual['ownership_failure'] is None, 'Actual owned component exits failed')
    build = read(bound(component['build'], consumed))
    need(build['passed'] and build['consumed_stats_unchanged'] and build['original_Single_no_hook']
         and build['physical_objects_compiled'] == 0 and build['actual_link_objects'] == 87,
         'Original physical-object closure is required')
    completed = read(bound(component['completion'], consumed))
    need(completed['stage'] == COMPONENT and completed['passed'] and completed['source_part'] == 300
         and completed['source_completed_step'] == completed['actual_completed_step'] == 2600000
         and completed['source_time_s'] == completed['actual_time_s'] == 12.999999999592434
         and completed['actual_force_calls'] == completed['actual_Darcy_calls'] == 1
         and completed['physical_steps'] == completed['material_return_calls'] == completed['extra_Darcy_calls'] == 0,
         'Only genuine Part300 zero-advance completion is admitted')
    for key in ('native_row_is_not_midpoint_field', 'all5000_primary_bits_unchanged',
                'all6805_normal_IDs_and_roles_unchanged', 'analytic_fixed_donors_in_manufactured_fields',
                'wall_values_lagged_in_native_pressure_block', 'acceleration_frozen_not_coupled_Jacobian'):
        need(completed[key] is True, 'Component scope/identity flag missing: '+key)
    need(completed['TPI_or_beta_implemented'] is False and completed['physical_acceptance'] is False,
         'This review cannot accept an integrator or physical repair')
    expected = dict(row_records=5000, manufactured_records=35000, shadow_records=15000,
                    summary_records=28, coupled_CN_manufactured_rows=6, literal_final_float_bits_matched=5000)
    need(all(completed[k] == v for k, v in expected.items()), 'Component exact coverage differs')
    sources = {leaf: SRC/leaf for leaf in HEADERS}
    consumed.extend(stat(p) for p in sources.values())
    # Only these new sealed CSVs/receipts are opened. No native, PRE, GPU runtime or source scanning.
    OUT.mkdir(exist_ok=False)
    result = dict(stage=TAG, analysis_complete=False, physical_acceptance=False, consumed=consumed,
                  source_component=COMPONENT, source_part=300, physical_steps=0,
                  solver_invocations=0, force_invocations=0, native_decodes=0, SHA_scans=0)
    outputs = []
    try:
        rows = table(sources['rows.csv'], HEADERS['rows.csv'], 5000)
        manufactured = table(sources['manufactured.csv'], HEADERS['manufactured.csv'], 35000)
        shadows = table(sources['shadows.csv'], HEADERS['shadows.csv'], 15000)
        summaries = table(sources['summary.csv'], HEADERS['summary.csv'], 28)
        coupled = table(sources['coupled_CN.csv'], HEADERS['coupled_CN.csv'], 6)
        by_id = {integer(q, 'native_id'): q for q in rows}
        need(len(by_id) == 5000 and set(by_id) == set(range(2060, 7060)), 'All5000 original soil IDs required once')
        tau = num(rows[0], 'tau_s')
        budget_ratios = {k: [] for k in ('original_rate', 'N_minus_Sp', 'manufactured', 'BE', 'lagged_N_midpoint', 'rescaling', 'toy_CN')}

        def common(q):
            ident = integer(q, 'native_id')
            need(ident in by_id and integer(q, 'part') == 300 and integer(q, 'completed_step') == 2600000
                 and num(q, 'time_s') == completed['actual_time_s'] and num(q, 'tau_s') == tau,
                 'Original native ID/actual clock/step changed')
            return ident

        row_metrics = []
        for q in rows:
            ident = common(q)
            need(q['region'] in REGIONS[1:], 'Unknown mutually exclusive native region')
            values = {k: num(q, k) for k in q if k != 'region'}
            fsflag, count, fixed = (integer(q, k) for k in ('FS', 'neighbors', 'fixed_neighbors'))
            need(0 <= fsflag <= 3 and count > 0 and 0 <= fixed <= count and integer(q, 'almostzero_excluded') >= 0,
                 'Actual stencil/FS counts invalid')
            need((q['region'] == 'FS') == (fsflag in (2, 3))
                 and (q['region'] != 'interior_no_fixed' or fixed == 0)
                 and (q['region'] != 'wall_adjacent' or fixed > 0), 'Native region classification differs')
            negative, negative_fixed = integer(q, 'negative_A'), integer(q, 'negative_fixed_A')
            need(0 <= negative_fixed <= min(negative, fixed) and negative <= count
                 and (values['A_min'] < 0) == (negative > 0) and values['A_min'] <= values['A_max'],
                 'Negative coefficient statistics are inconsistent')
            M, S, p = (values[k] for k in ('M_per_m', 'S_per_m_s', 'p_Pa'))
            need(M > 0 and 0 < values['n'] < 1 and values['V_m2'] > 0 and values['J'] > 1-float(np.float32(.35))
                 and values['k_m_s'] > 0 and values['dkdJ'] > 0, 'Finite-Kw/current-ledger row domain invalid')
            arithmetic_close(M, values['gamma_Pa_m']*values['n']/1e9, abs(M), label='M=gamma*n/Kw')
            arithmetic_close(S, values['fluid_S_per_m_s']+values['fixed_S_per_m_s'],
                             abs(S)+abs(values['fluid_S_per_m_s'])+abs(values['fixed_S_per_m_s']), label='fluid/wall S partition')
            need(values['A_absolute_sum']+gamma(128)*values['A_absolute_sum'] >= abs(S), 'Absolute coefficient sum invalid')
            literal, actual = values['literal_rate_Pa_s'], values['actual_float_rate_Pa_s']
            need(float(np.float32(actual)) == actual and np.float32(literal).view(np.uint32) == np.float32(actual).view(np.uint32),
                 'Original final-float literal bit check failed')
            float_budget = float(np.finfo(np.float32).eps)*abs(literal)+float(np.nextafter(np.float32(0), np.float32(1)))
            need(abs(actual-literal) <= float_budget, 'Original float-write budget failed')
            rate_error = abs(values['row_rate_Pa_s']-actual)
            need(rate_error == values['row_rate_error_Pa_s'], 'Recorded original rate error differs')
            budget_ratios['original_rate'].append(original_budget(rate_error, values['old_rate_budget_Pa_s'], 'original rate'))
            identity = values['N_Pa_m_s']-S*p
            need(identity == values['N_minus_Sp_Pa_m_s'] and abs(identity-values['row_pressure_Pa_m_s']) == values['row_identity_error_Pa_m_s'],
                 'Recorded N-S*pi identity/error differs')
            budget_ratios['N_minus_Sp'].append(original_budget(values['row_identity_error_Pa_m_s'], values['row_identity_budget_Pa_m_s'], 'N-S*pi'))
            expanded = values['LP_pressure_Pa_m_s']+values['Taylor_pressure_Pa_m_s']+values['chain_pressure_Pa_m_s']
            need(abs((values['B_Pa_m_s']+expanded)/M-actual) <= values['old_rate_budget_Pa_s'], 'Original seven-term pressure expansion failed')
            need(abs((values['B_Pa_m_s']+values['row_pressure_Pa_m_s'])/M-actual) <= values['old_rate_budget_Pa_s'], 'Complete row rate failed')
            arithmetic_close(values['soil_only_constant_shift1Pa_rate_Pa_s'], -values['fixed_S_per_m_s']/M,
                             abs(values['soil_only_constant_shift1Pa_rate_Pa_s']), label='lagged-wall constant-shift response')
            arithmetic_close(values['hS_over_M'], WIDTHS[0]*S/M, abs(values['hS_over_M']), label='native hS/M')
            row_metrics.append(dict(native_id=ident, region=q['region'], FS=fsflag, x_m=values['x_m'], z_m=values['z_m'],
                p_Pa=p, M_per_m=M, S_per_m_s=S, hS_over_M=values['hS_over_M'],
                neighbors=count, fixed_neighbors=fixed, negative_A=negative, negative_fixed_A=negative_fixed,
                negative_A_fraction=negative/count, A_min=values['A_min'], A_max=values['A_max'],
                A_absolute_sum=values['A_absolute_sum'], old_rate_budget_ratio=budget_ratios['original_rate'][-1],
                row_identity_budget_ratio=budget_ratios['N_minus_Sp'][-1],
                actual_float_rate_Pa_s=actual, row_rate_Pa_s=values['row_rate_Pa_s'],
                soil_only_constant_shift1Pa_rate_Pa_s=values['soil_only_constant_shift1Pa_rate_Pa_s']))
        need(sum(num(q, 'S_per_m_s') <= 0 for q in rows) == completed['nonpositive_S_rows']
             and sum(integer(q, 'negative_A') > 0 for q in rows) == completed['rows_with_negative_A'], 'Completion sign counters differ')
        need(max(budget_ratios['original_rate']) == completed['max_original_rate_budget_ratio']
             and max(budget_ratios['N_minus_Sp']) == completed['max_row_identity_budget_ratio'], 'Completion arithmetic extrema differ')

        mkeys, mby = set(), {}
        for q in manufactured:
            ident = common(q)
            key = (ident, q['basis'])
            need(q['basis'] in BASES and key not in mkeys and q['region'] == by_id[ident]['region']
                 and integer(q, 'full6805_analytic_donors') == 1, 'All-ID analytic soil+fixed manufacturing coverage differs')
            mkeys.add(key); mby[key] = q
            values = {k: num(q, k) for k in q if k not in ('region', 'basis')}
            error = abs(values['row_pressure_Pa_m_s']-values['direct_pressure_Pa_m_s'])
            need(error == values['arithmetic_error'] and values['full_N_minus_Sp'] == values['row_pressure_Pa_m_s'],
                 'Manufactured row/direct or full N-S*pi identity differs')
            budget_ratios['manufactured'].append(original_budget(error, values['arithmetic_budget'], 'manufactured row'))
            if q['basis'] == '1':
                need(all(values[k] == 0 for k in ('analytic_target_Pa_m_s', 'LP_Pa_m_s', 'Taylor_Pa_m_s', 'chain_Pa_m_s',
                     'row_pressure_Pa_m_s', 'direct_pressure_Pa_m_s', 'full_N_minus_Sp', 'Eq22_gpx', 'Eq22_gpz', 'analytic_gpx', 'analytic_gpz')),
                     'Full6805 constant field is not exactly null')
            else:
                need(values['analytic_gpx'] == (1.0 if q['basis'] == 'x' else 0.0)
                     and values['analytic_gpz'] == (1.0 if q['basis'] == 'z' else 0.0), 'Manufactured local analytic gradient differs')
                if q['basis'] not in ('x', 'z'):
                    target = num(by_id[ident], 'k_m_s') if q['basis'] in ('half_x2', 'half_z2') else 0.0
                    need(values['analytic_target_Pa_m_s'] == target, 'Local quadratic/harmonic target differs')
        need(mkeys == {(ident, basis) for ident in by_id for basis in BASES}, 'Every5000-ID/seven-basis combination required')
        for q in row_metrics:
            components = []
            for basis in ('x', 'z'):
                fixture = mby[q['native_id'], basis]
                response, target = num(fixture, 'row_pressure_Pa_m_s'), num(fixture, 'analytic_target_Pa_m_s')
                q['affine_'+basis+'_row_Pa_m_s'] = response
                q['affine_'+basis+'_reference_Pa_m_s'] = target
                q['affine_'+basis+'_difference_Pa_m_s'] = response-target
                components.append(response-target)
            q['affine_combined_difference_norm'] = math.hypot(*components)
        summary_by = {(q['region'], q['basis']): q for q in summaries}
        need(len(summary_by) == 28 and set(summary_by) == {(g, b) for g in REGIONS for b in BASES}, 'Exact28 cohort/basis summaries required')
        manufactured_metrics = []
        for region in REGIONS:
            for basis in BASES:
                selected = [q for q in manufactured if q['basis'] == basis and (region == 'all' or q['region'] == region)]
                q = summary_by[region, basis]
                need(integer(q, 'IDs') == len(selected), 'Manufactured summary ID count differs')
                if selected:
                    responses = [num(z, 'row_pressure_Pa_m_s') for z in selected]
                    errors = [v-num(z, 'analytic_target_Pa_m_s') for v, z in zip(responses, selected)]
                    mean = sum(responses)/len(selected)
                    rms = math.sqrt(sum(e*e for e in errors)/len(selected))
                    maximum = max(abs(e) for e in errors)
                    magnitude = sum(abs(v) for v in responses)/len(selected)+rms+maximum
                    for key, expected_value in (('mean_response_Pa_m_s', mean), ('RMS_error_Pa_m_s', rms), ('max_abs_error_Pa_m_s', maximum)):
                        arithmetic_close(num(q, key), expected_value, magnitude, 128*(len(selected)+1), 'manufactured cohort '+key)
                    gradient_rms = math.sqrt(sum((num(z, 'Eq22_gpx')-num(z, 'analytic_gpx'))**2
                                                  +(num(z, 'Eq22_gpz')-num(z, 'analytic_gpz'))**2 for z in selected)/len(selected))
                else:
                    need(all(q[k] == '' for k in ('mean_response_Pa_m_s', 'RMS_error_Pa_m_s', 'max_abs_error_Pa_m_s')),
                         'Empty manufactured cohort must remain explicitly empty')
                    mean = rms = maximum = gradient_rms = None
                manufactured_metrics.append(dict(region=region, basis=basis, IDs=len(selected), mean_response_Pa_m_s=mean,
                    RMS_error_Pa_m_s=rms, max_abs_error_Pa_m_s=maximum, Eq22_gradient_RMS=gradient_rms,
                    variable_k_affine_target_uses_frozen_numerical_gradJ=True, FS_error_is_descriptive=True))

        shadow_keys, shadow_metrics = set(), []
        undefined = {'BE': 0, 'lagged_N_midpoint': 0}
        for q in shadows:
            ident = common(q); row = by_id[ident]; h = num(q, 'h_s'); key = (ident, h)
            need(h in WIDTHS and key not in shadow_keys, 'Exact three-width/all-ID shadow coverage differs')
            shadow_keys.add(key)
            p, M, S = (num(row, k) for k in ('p_Pa', 'M_per_m', 'S_per_m_s'))
            need(num(q, 'p_base_Pa') == p and num(q, 'M_per_m') == M and num(q, 'S_per_m_s') == S, 'Shadow frozen row/base differs')
            explicit = h*num(row, 'row_rate_Pa_s'); lam = h*S/M
            need(num(q, 'explicit_delta_Pa') == explicit, 'Actual explicit algebraic increment differs')
            record = dict(native_id=ident, region=row['region'], h_s=h, p_base_Pa=p, hS_over_M=lam,
                          explicit_delta_Pa=explicit, row_rate_Pa_s=num(row, 'row_rate_Pa_s'))
            deltas = {}
            for method, factor in (('BE', 1.0), ('lagged_N_midpoint', .5)):
                den = 1+factor*lam
                defined = math.isfinite(den) and den != 0
                need(num(q, method+'_denominator') == den and integer(q, method+'_defined') == int(defined)
                     and integer(q, method+'_positive_denominator') == int(den > 0), 'Shadow denominator/domain flag differs')
                fields = [method+suffix for suffix in ('_delta_Pa', '_new_Pa', '_algebraic_error', '_algebraic_budget')]
                if defined:
                    delta = explicit/den
                    need(num(q, fields[0]) == delta and num(q, fields[1]) == p+delta, 'Frozen row shadow value differs')
                    error = abs((delta-explicit)+factor*lam*delta)
                    need(num(q, fields[2]) == error, 'Recorded shadow residual differs')
                    budget_ratios[method].append(original_budget(error, num(q, fields[3]), method+' identity'))
                    deltas[method] = delta
                    record.update({method+'_denominator': den, method+'_defined': True, method+'_positive_denominator': den > 0,
                        method+'_factor_from_explicit': 1/den, method+'_delta_Pa': delta,
                        method+'_minus_explicit_Pa': delta-explicit})
                else:
                    need(all(q[k] == '' for k in fields), 'Undefined shadow must have four blank values, no clamp')
                    undefined[method] += 1; deltas[method] = 0.0
                    record.update({method+'_denominator': den, method+'_defined': False, method+'_positive_denominator': den > 0,
                        method+'_factor_from_explicit': None, method+'_delta_Pa': None, method+'_minus_explicit_Pa': None})
            rescale_error = 0.0
            for scale in (1/num(row, 'gamma_Pa_m'), num(row, 'V_m2')):
                scaled_rate = (scale*num(row, 'B_Pa_m_s')+scale*num(row, 'row_pressure_Pa_m_s'))/(scale*M)
                scaled_lambda = h*(scale*S)/(scale*M)
                for method, factor in (('BE', 1.0), ('lagged_N_midpoint', .5)):
                    if record[method+'_defined']:
                        denominator = 1+factor*scaled_lambda
                        need(math.isfinite(denominator) and denominator != 0, 'Original rescaling changed a defined domain')
                        rescale_error = max(rescale_error, abs((p+h*scaled_rate/denominator)-(p+deltas[method])))
            need(num(q, 'rescaling_max_error_Pa') == rescale_error, 'Recorded full-row rescaling error differs')
            budget_ratios['rescaling'].append(original_budget(rescale_error, num(q, 'rescaling_budget_Pa'), 'row-unit rescaling'))
            shadow_metrics.append(record)
        need(shadow_keys == {(ident, h) for ident in by_id for h in WIDTHS}, 'All5000 IDs/three widths required')
        need(undefined['BE'] == completed['undefined_BE_shadows']
             and undefined['lagged_N_midpoint'] == completed['undefined_midpoint_shadows'], 'Completion undefined-shadow counters differ')

        toy_keys, toy_checks = set(), []
        masses, diagonals, coupling, pressure = (2., 3.), (6., 3.), (6., 3.), (2., -1.)
        rates, lrates = (-9., 3.), (36., -12.)
        for q in coupled:
            node, h = integer(q, 'node'), num(q, 'h_normalized_s')
            need(node in (0, 1) and h in (.01, .001, .0001) and (node, h) not in toy_keys, 'Six unique normalized CN manufacture rows required')
            toy_keys.add((node, h)); other = 1-node; s = diagonals[node]/masses[node]
            need(num(q, 'M') == masses[node] and num(q, 'S') == diagonals[node] and num(q, 'A_neighbor') == coupling[node]
                 and num(q, 'p_n') == pressure[node] and num(q, 'explicit_R_n') == rates[node], 'Original normalized two-node matrix differs')
            ph = pressure[node]+.5*h*rates[node]; phj = pressure[other]+.5*h*rates[other]
            delta = (h*rates[node]+.5*h*h*(coupling[node]/masses[node])*rates[other])/(1+.5*h*s)
            taylor = h*rates[node]+.5*h*h*lrates[node]
            next_p = ((masses[node]/h-.5*diagonals[node])*pressure[node]+coupling[node]*phj)/(masses[node]/h+.5*diagonals[node])
            defect = delta-taylor; exact = -.25*h*h*h*s*lrates[node]/(1+.5*h*s)
            for key, value in (('explicit_p_h', ph), ('neighbor_p_h', phj), ('diagonal_CN_p_new', next_p),
                               ('rational_delta', delta), ('second_Taylor_delta', taylor),
                               ('measured_third_defect', defect), ('exact_rational_third_defect', exact),
                               ('arithmetic_closure', defect-exact)):
                need(num(q, key) == value, 'Normalized CN arithmetic field differs: '+key)
            ratio = original_budget(abs(defect-exact), num(q, 'arithmetic_budget'), 'normalized CN third-defect identity')
            arithmetic_close(next_p-pressure[node], delta, abs(pressure[node])+abs(next_p)+abs(delta), 256, 'normalized CN base addition')
            budget_ratios['toy_CN'].append(ratio)
            toy_checks.append(dict(node=node, h_normalized_s=h, measured_third_defect=defect, exact_rational_third_defect=exact,
                arithmetic_budget=num(q, 'arithmetic_budget'), budget_ratio=ratio,
                absolute_defect_over_h3=abs(defect)/(h*h*h), constant_matrix_only=True, actual_native_midpoint=False))
        need(toy_keys == {(node, h) for node in (0, 1) for h in (.01, .001, .0001)}, 'Normalized CN key coverage differs')

        cohorts, ecdf = [], []
        for region in REGIONS:
            selected = [q for q in row_metrics if region == 'all' or q['region'] == region]
            out = dict(region=region, IDs=len(selected), nonpositive_S_rows=sum(q['S_per_m_s'] <= 0 for q in selected),
                       rows_with_negative_A=sum(q['negative_A'] > 0 for q in selected),
                       rows_with_negative_fixed_A=sum(q['negative_fixed_A'] > 0 for q in selected),
                       negative_A_coefficients=sum(q['negative_A'] for q in selected),
                       all_neighbor_coefficients=sum(q['neighbors'] for q in selected))
            for key in ('M_per_m', 'S_per_m_s', 'hS_over_M', 'neighbors', 'fixed_neighbors', 'negative_A_fraction'):
                values = [q[key] for q in selected]
                quantiles = np.quantile(values, (0, .01, .05, .25, .5, .75, .95, .99, 1)) if values else [None]*9
                for suffix, value in zip(('min', 'q01', 'q05', 'q25', 'median', 'q75', 'q95', 'q99', 'max'), quantiles):
                    out[key+'_'+suffix] = float(value) if value is not None else None
            cohorts.append(out)
            for rank, value in enumerate(sorted(q['hS_over_M'] for q in selected), 1):
                ecdf.append(dict(region=region, rank=rank, IDs=len(selected), hS_over_M=value, empirical_CDF=rank/len(selected)))
        shadow_summary = []
        for region in REGIONS:
            for h in WIDTHS:
                selected = [q for q in shadow_metrics if q['h_s'] == h and (region == 'all' or q['region'] == region)]
                for method in ('explicit', 'BE', 'lagged_N_midpoint'):
                    valid = selected if method == 'explicit' else [q for q in selected if q[method+'_defined']]
                    values = [q[method+'_delta_Pa'] for q in valid]
                    changes = [q[method+'_delta_Pa']-q['explicit_delta_Pa'] for q in valid]
                    shadow_summary.append(dict(region=region, h_s=h, method=method, IDs=len(selected), defined_IDs=len(valid),
                        nonpositive_denominator_IDs=0 if method == 'explicit' else sum(not q[method+'_positive_denominator'] for q in valid),
                        delta_RMS_Pa=math.sqrt(sum(v*v for v in values)/len(values)) if values else None,
                        delta_max_abs_Pa=max(map(abs, values)) if values else None,
                        effective_delta_over_h_RMS_Pa_s=math.sqrt(sum((v/h)**2 for v in values)/len(values)) if values else None,
                        change_from_explicit_RMS_Pa=math.sqrt(sum(v*v for v in changes)/len(changes)) if changes else None,
                        change_from_explicit_max_abs_Pa=max(map(abs, changes)) if changes else None,
                        native_midpoint_field=False, global_implicit_solution=False))
        arithmetic = [dict(check=key, records=len(values), max_original_budget_ratio=max(values) if values else None,
                           all_original_budgets_passed=True, physical_tolerance=False) for key, values in budget_ratios.items()]
        for leaf, records in (('row_metrics.csv', row_metrics), ('cohort_summary.csv', cohorts), ('stiffness_ecdf.csv', ecdf),
                              ('shadow_per_ID.csv', shadow_metrics), ('shadow_summary.csv', shadow_summary),
                              ('manufactured_metrics.csv', manufactured_metrics), ('coupled_CN_checks.csv', toy_checks),
                              ('arithmetic_checks.csv', arithmetic)):
            p = OUT/leaf; write(p, records); outputs.append(p)

        colors = {'all': 'black', 'interior_no_fixed': '#2467ac', 'wall_adjacent': '#c17a12', 'FS': '#ad3152'}
        labels = {'all': 'All soil', 'interior_no_fixed': 'Interior, no fixed donor', 'wall_adjacent': 'Wall-adjacent, not FS', 'FS': 'Raw free surface'}
        xs, zs = np.array([q['x_m'] for q in row_metrics]), np.array([q['z_m'] for q in row_metrics])
        lambdas = np.array([q['hS_over_M'] for q in row_metrics])
        fig, ax = plt.subplots(2, 2, figsize=(13.6, 10), layout='constrained')
        for region in REGIONS:
            q = [z for z in ecdf if z['region'] == region]
            if q: ax[0, 0].plot([z['hS_over_M'] for z in q], [z['empirical_CDF'] for z in q], color=colors[region], lw=1.7, label=labels[region])
        if np.any(lambdas < 0): ax[0, 0].set_xscale('symlog', linthresh=max(float(np.max(np.abs(lambdas)))/1000, float(np.finfo(float).tiny)))
        ax[0, 0].set(xlabel='hS/M, h = 5 microseconds', ylabel='Empirical cumulative fraction', title='All native rows; no outlier removal')
        ax[0, 0].legend(fontsize=8); ax[0, 0].grid(alpha=.2)
        pc = ax[0, 1].scatter(xs, zs, c=lambdas, s=5, cmap='viridis', rasterized=True)
        ax[0, 1].set(xlabel='x [m]', ylabel='z [m]', title='Native diagonal stiffness hS/M'); ax[0, 1].set_aspect('equal')
        fig.colorbar(pc, ax=ax[0, 1], label='hS/M')
        negative_mask = np.array([q['negative_A'] > 0 for q in row_metrics])
        ax[1, 0].scatter(xs, zs, s=4, color='#c5c8ce', rasterized=True)
        if np.any(negative_mask): ax[1, 0].scatter(xs[negative_mask], zs[negative_mask], s=32, color='#c12c35', marker='x', label='At least one negative A')
        ax[1, 0].set(xlabel='x [m]', ylabel='z [m]', title=f'Negative coefficient in {int(negative_mask.sum())}/5000 rows'); ax[1, 0].set_aspect('equal')
        if np.any(negative_mask): ax[1, 0].legend(fontsize=8)
        positions = np.arange(4)
        for j, (key, label) in enumerate((('nonpositive_S_rows', 'S <= 0'), ('rows_with_negative_A', 'Any A < 0'), ('rows_with_negative_fixed_A', 'Any fixed A < 0'))):
            ax[1, 1].bar(positions+(j-1)*.24, [100*q[key]/q['IDs'] if q['IDs'] else 0 for q in cohorts], width=.24, label=label)
        ax[1, 1].set_xticks(positions, ['All', 'Interior', 'Wall', 'FS']); ax[1, 1].set(ylabel='Fraction of receiver rows [%]', title='Signs reported, never clipped')
        ax[1, 1].legend(fontsize=8); ax[1, 1].grid(axis='y', alpha=.2)
        fig.suptitle(f'Frozen CPU pressure row: Part300, tau={tau:.6f} s\nZero advance; lagged walls/acceleration; no physical-repair conclusion', fontsize=12)
        p = OUT/'stiffness.png'; fig.savefig(p, dpi=200, bbox_inches='tight'); plt.close(fig); outputs.append(p)

        native_shadows = [q for q in shadow_metrics if q['h_s'] == WIDTHS[0]]
        native_shadow_by = {q['native_id']: q for q in native_shadows}
        fig, ax = plt.subplots(2, 2, figsize=(13.6, 10), layout='constrained')
        for method, color, label in (('BE', '#2467ac', 'Diagonal BE'), ('lagged_N_midpoint', '#b54c23', 'Lagged N midpoint algebra')):
            valid = sorted((q for q in native_shadows if q[method+'_defined']), key=lambda q: q['hS_over_M'])
            ax[0, 0].plot([q['hS_over_M'] for q in valid], [q[method+'_factor_from_explicit'] for q in valid], color=color, lw=1.3, label=label)
        ax[0, 0].axhline(1, color='black', ls=':', lw=.8); ax[0, 0].set(xlabel='Native hS/M at 5 microseconds', ylabel='Algebraic delta / explicit delta', title='Factors, not measured trajectory errors')
        ax[0, 0].legend(fontsize=8); ax[0, 0].grid(alpha=.2)
        for method, color, label in (('explicit', '#555555', 'Explicit row'), ('BE', '#2467ac', 'BE shadow'), ('lagged_N_midpoint', '#b54c23', 'Lagged N midpoint shadow')):
            selected = sorted((q for q in shadow_summary if q['region'] == 'all' and q['method'] == method), key=lambda q: q['h_s'])
            ax[0, 1].plot([q['h_s'] for q in selected], [q['effective_delta_over_h_RMS_Pa_s'] for q in selected], 'o-', color=color, label=label)
        ax[0, 1].set_xscale('log'); ax[0, 1].set(xlabel='Arithmetic shadow width h [s]', ylabel='RMS(delta/h) [Pa/s]', title='Same frozen state at all three widths')
        ax[0, 1].legend(fontsize=8); ax[0, 1].grid(alpha=.2)
        delta = np.array([native_shadow_by[q['native_id']]['lagged_N_midpoint_minus_explicit_Pa']
                          if native_shadow_by[q['native_id']]['lagged_N_midpoint_defined'] else np.nan for q in row_metrics])
        valid = np.isfinite(delta); extreme = float(np.max(np.abs(delta[valid]))) if np.any(valid) else 0.0
        norm = SymLogNorm(linthresh=max(extreme/1000, float(np.finfo(float).tiny)), vmin=-max(extreme, float(np.finfo(float).tiny)), vmax=max(extreme, float(np.finfo(float).tiny)))
        pc = ax[1, 0].scatter(xs[valid], zs[valid], c=delta[valid], s=5, cmap='coolwarm', norm=norm, rasterized=True)
        ax[1, 0].set(xlabel='x [m]', ylabel='z [m]', title='Lagged N shadow minus explicit delta, 5 microseconds'); ax[1, 0].set_aspect('equal')
        fig.colorbar(pc, ax=ax[1, 0], label='Increment difference [Pa]')
        chart_checks = [q for q in arithmetic if q['max_original_budget_ratio'] is not None]
        ax[1, 1].barh([q['check'] for q in chart_checks], [q['max_original_budget_ratio'] for q in chart_checks], color='#49778d')
        ax[1, 1].axvline(1, color='#b51e2b', ls='--', lw=1); ax[1, 1].set(xlabel='Maximum error / original arithmetic budget', title='Arithmetic checks; not physical tolerances', xlim=(0, 1.05))
        ax[1, 1].grid(axis='x', alpha=.2)
        fig.suptitle('Frozen B and N(p_n): algebraic shadows ONLY\nNot genuine midpoint fields, global implicit solutions or physical repairs', fontsize=12)
        p = OUT/'shadows.png'; fig.savefig(p, dpi=200, bbox_inches='tight'); plt.close(fig); outputs.append(p)

        fig, ax = plt.subplots(2, 2, figsize=(14.4, 10), layout='constrained')
        positions = np.arange(len(BASES))
        for j, region in enumerate(REGIONS[1:]):
            selected = [next(q for q in manufactured_metrics if q['region'] == region and q['basis'] == b) for b in BASES]
            values = [q['RMS_error_Pa_m_s'] if q['RMS_error_Pa_m_s'] is not None else np.nan for q in selected]
            ax[0, 0].bar(positions+(j-1)*.24, values, width=.24, color=colors[region], label=labels[region])
        ax[0, 0].set_xticks(positions, ['1', 'x', 'z', 'x²/2', 'xz', 'z²/2', '(x²-z²)/2'], rotation=20)
        ax[0, 0].set(xlabel='Local analytic pressure fixture', ylabel='RMS row-reference difference [fixture units]', title='Original raw-FS errors remain descriptive')
        ax[0, 0].legend(fontsize=8); ax[0, 0].grid(axis='y', alpha=.2)
        for j, region in enumerate(REGIONS[1:]):
            values = [next(q for q in manufactured_metrics if q['region'] == region and q['basis'] == b)['Eq22_gradient_RMS'] for b in ('x', 'z')]
            ax[0, 1].bar(np.arange(2)+(j-1)*.24, [v if v is not None else np.nan for v in values], width=.24, color=colors[region], label=labels[region])
        ax[0, 1].set_xticks(np.arange(2), ['Affine x', 'Affine z']); ax[0, 1].set(ylabel='RMS reconstructed-gradient error', title='Analytic values assigned to soil AND fixed donors')
        ax[0, 1].legend(fontsize=8); ax[0, 1].grid(axis='y', alpha=.2)
        affine_error = np.array([q['affine_combined_difference_norm'] for q in row_metrics])
        pc = ax[1, 0].scatter(xs, zs, c=affine_error, s=5, cmap='magma', rasterized=True)
        ax[1, 0].set(xlabel='x [m]', ylabel='z [m]', title='Combined affine row-reference difference'); ax[1, 0].set_aspect('equal')
        fig.colorbar(pc, ax=ax[1, 0], label='Affine fixture difference norm')
        for node, color in ((0, '#2467ac'), (1, '#b54c23')):
            selected = sorted((q for q in toy_checks if q['node'] == node), key=lambda q: q['h_normalized_s'])
            ax[1, 1].loglog([q['h_normalized_s'] for q in selected], [abs(q['measured_third_defect']) for q in selected], 'o-', color=color, label=f'Toy node {node}')
        guide_h = np.array([.0001, .001, .01]); guide = abs(toy_checks[0]['exact_rational_third_defect'])*(guide_h/toy_checks[0]['h_normalized_s'])**3
        ax[1, 1].loglog(guide_h, guide, ':', color='black', label='h³ guide, fixed toy matrix')
        ax[1, 1].set(xlabel='Normalized toy width h; NOT C08 physical time', ylabel='Absolute Taylor defect', title='True manufactured explicit-predictor neighbour only')
        ax[1, 1].legend(fontsize=8); ax[1, 1].grid(which='both', alpha=.2)
        fig.suptitle('All6805 analytic donor continuation; constant field exactly null for5000 receivers\nFrozen numerical gradJ reference; toy CN order does not establish native/coupled time order', fontsize=12)
        p = OUT/'manufactured.png'; fig.savefig(p, dpi=200, bbox_inches='tight'); plt.close(fig); outputs.append(p)

        need(all(stat(q['path']) == q for q in consumed), 'Consumed evidence changed during offline review')
        concise_cohorts = [{key: q[key] for key in ('region', 'IDs', 'nonpositive_S_rows', 'rows_with_negative_A',
                           'M_per_m_min', 'M_per_m_max', 'S_per_m_s_min', 'S_per_m_s_max',
                           'hS_over_M_min', 'hS_over_M_median', 'hS_over_M_max')} for q in cohorts]
        result.update(analysis_complete=True, consumed_stats_unchanged=True,
                      row_IDs=5000, manufactured_records=35000, shadow_records=15000, summary_records=28,
                      coupled_CN_records=6, constant_null_IDs=5000, literal_final_float_bits_matched=5000,
                      actual_time_s=completed['actual_time_s'], tau_s=tau, actual_completed_step=2600000,
                      cohorts=concise_cohorts, native_width_all_soil_shadows=[q for q in shadow_summary
                          if q['region'] == 'all' and q['h_s'] == WIDTHS[0]], arithmetic_checks=arithmetic,
                      force_seconds=completed['force_seconds'], row_and_output_seconds=completed['row_and_output_seconds'],
                      native_midpoint_field=False, global_implicit_solution=False, physical_repair_inferred=False,
                      coefficient_positivity_is_not_stability_proof=True, finite_Kw_capacity_retained=True,
                      variable_k_affine_reference_uses_frozen_numerical_gradJ=True,
                      original_rate_magnitude_budget_transitively_bound_not_reconstructed_from_incomplete_CSV=True,
                      rescaling_final_pressure_addition_may_hide_tiny_increment_differences=True,
                      visual_QA_pending=True, outputs=[stat(p) for p in outputs])
    except Exception as error:
        result.update(first_failure=str(error), partial_outputs_preserved=True)
        raise
    finally:
        with check.open('x', encoding='utf-8') as f:
            json.dump(result, f, indent=2, allow_nan=False)
            f.write('\n')


if __name__ == '__main__':
    main()
