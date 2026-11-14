"""Offline scientific audit of completed r3 conditional pressure feedback; no force/reader/solver."""
import os
for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_key, '1')
import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import SymLogNorm

T = Path(__file__).resolve().parents[1]
L = T / 'logs'
TAG = 'c08_h18_pressure_feedback_review_r1'
SOURCE = 'c08_h18_pressure_feedback_r3'
PARTS = (38, 76)
STEPS = {38: 2076001, 76: 2152001}
MODES = ('constant', 'initial_altX', 'pair4953_4954', 'pair6767_6865')
MODE_LABELS = ('Constant', 'Initial alt-X', '4953 / 4954', '6767 / 6865')
COHORTS = ('all', 'no_fixed_neighbors', 'fresh_FS2_or3')
TERMS = ('compression', 'LP', 'Taylor_pressure', 'Da', 'FS_Ace_Lx',
         'chain_pressure', 'chain_Ace', 'float_source_order_residual')
FOCUS = (4953, 4954, 6767, 6865)
N = 5000
EPS = np.finfo(np.float64).eps
TINY = float(np.nextafter(0., 1.))
BASE_COLUMNS = 'time_s,tau_s,completed_step,phi,baseline_p_Pa,fixed_P0_Pa,p_plus_Pa,p_minus_Pa,actual_central_dp_Pa,central_dp_over_requested_h,plus_quant_error_Pa,minus_quant_error_Pa,weight_nV_Kw,no_fixed_neighbors,fresh_FS,R0_Pa_s,Rplus_Pa_s,Rminus_Pa_s,central_dR_Pa_s,second_difference_Pa_s,central_Acex,central_Acey,central_Acez,ASplus_delta_norm,ASminus_delta_norm'.split(',')
CHANNEL_COLUMNS = ['central_' + k + '_Pa_s' for k in TERMS]
COLUMNS = BASE_COLUMNS + CHANNEL_COLUMNS
RESPONSE_HEADER = 'part,time_s,tau_s,completed_step,mode,requested_h_Pa,native_id,phi,baseline_p_Pa,fixed_P0_Pa,p_plus_Pa,p_minus_Pa,actual_central_dp_Pa,central_dp_over_requested_h,plus_quant_error_Pa,minus_quant_error_Pa,weight_nV_Kw,no_fixed_neighbors,fresh_FS,R0_Pa_s,Rplus_Pa_s,Rminus_Pa_s,central_dR_Pa_s,second_difference_Pa_s,central_Acex,central_Acey,central_Acez,ASplus_delta_norm,ASminus_delta_norm'.split(',') + CHANNEL_COLUMNS
TRIAL_HEADER = 'part,time_s,completed_step,mode,requested_h_Pa,sign,actually_changed_soil,quantization_max_Pa,AS_tensor_changed_soil,NpbOk,active_walls,inactive_effective_walls,ignored_walls,frozen_soil_checks,frozen_wall_checks,passed'.split(',')
SUMMARY_HEADER = 'part,time_s,tau_s,completed_step,mode,requested_h_Pa,receiver_cohort,count,sum_weight,central_dp_weighted_norm,Q,absQ,Q_over_norm_defined,Q_over_norm_s_1,central_rate_weighted_RMS_Pa_s,second_difference_weighted_RMS_Pa_s,quantization_max_Pa'.split(',') + ['Q_' + q for q in TERMS]
FOCUS_HEADER = 'part,time_s,tau_s,completed_step,mode,requested_h_Pa,native_id,baseline_p_Pa,fixed_P0_Pa,p_plus_Pa,p_minus_Pa,R0_Pa_s,Rplus_Pa_s,Rminus_Pa_s'.split(',') + ['AS_' + state + '_' + c for state in ('base', 'plus', 'minus') for c in ('xx', 'yy', 'zz', 'xy', 'yz', 'xz')]


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def stat(path):
    path = Path(path).resolve(); s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def bind(entry, consumed):
    need(stat(entry['path']) == entry, 'Bound source evidence changed: ' + entry['path'])
    consumed.append(entry)
    return Path(entry['path'])


def csv_rows(path, header):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        need(reader.fieldnames == header, 'Exact completed r3 CSV schema required: ' + path.name)
        yield from reader


def numeric(row, strings=(), optional=()):
    for key, value in row.items():
        if key not in strings and not (key in optional and value == ''):
            need(math.isfinite(float(value)), 'Nonfinite completed diagnostic value: ' + key)


def sum64(values):
    return math.fsum(float(v) for v in values)


def gamma(operations):
    u = .5 * EPS; x = operations * u
    need(x < 1, 'Invalid double arithmetic operation count')
    return x / (1 - x)


def aggregate(values, original, label):
    values = np.asarray(values, dtype=float)
    result = sum64(values); absolute = sum64(np.abs(values))
    budget = gamma(len(values) + 16) * absolute + 8 * EPS * abs(result) + 64 * TINY
    error = abs(float(original) - result)
    need(error <= budget, 'Reported summary double-aggregation mismatch: ' + label)
    return result, error, budget


def write(path, data):
    need(bool(data), 'Empty derived CSV is not expected')
    with path.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]))
        writer.writeheader(); writer.writerows(data)


def source_inputs(consumed):
    receipt = L / (SOURCE + '.check.json'); consumed.append(stat(receipt)); check = read(receipt)
    need(check['passed'] and check['consumed_stats_unchanged'] and check['component_invocations'] == 1
         and check['physical_steps'] == check['solver_invocations'] == 0 and not check['physical_acceptance'],
         'Only genuinely completed, sealed r3 component is admitted')
    build_path = bind(check['build'], consumed); build = read(build_path)
    need(build_path.resolve() == (L / (SOURCE + '.build.json')).resolve() and build['passed']
         and build['consumed_stats_unchanged'] and build['configuration'] == 'DebugCPU'
         and build['actual_link_objects'] == 87 and build['physical_objects_compiled'] == 0
         and build['original_Single_no_hook'] and build['ignored_BoundMode_not_read']
         and build['defined_active_wall_scope'], 'Original private r3/no-hook ABI and defined observer scope required')
    program = bind(build['program'], consumed); bind(build['source'], consumed)
    call = read(bind(check['actual_call'], consumed))
    need(call['actual_Popen_wait_exit'] == call['actual_Win32_exit'] == 0 and call['ownership_failure'] is None
         and Path(call['program']).resolve() == program.resolve(), 'Actual owned r3 component exit0 required')
    done = read(bind(check['completion'], consumed))
    need(done['stage'] == SOURCE and done['passed'] and done['parts'] == list(PARTS)
         and done['actual_force_calls'] == done['actual_Darcy_calls'] == 34
         and done['baseline_bit_rows'] == 10000 and done['baseline_actual5000_bits_per_state']
         and done['trial_rows'] == 34 and done['response_rows'] == 80000
         and done['summary_rows'] == 48 and done['focus_rows'] == 64
         and done['physical_steps'] == done['material_return_calls'] == done['PONDING_or_cap_calls_added'] == 0,
         'Closed34-call and original5000 baseline coverage differs')
    true_fields = ('numeric_residual_separate_eighth_channel',
        'conditioned_FS_masks_and_nonpressure_primaries_unchanged', 'ignored_OFF_scratch_not_read',
        'ignored_BoundMode_not_read', 'wall_partition_counts_and_IDs_frozen_each_call',
        'ghost_pressure_and_Ace_rebuilt_by_original_force', 'initial_altX_phase_reused_by_ID',
        'actual_quantized_pressure_used_in_Q', 'weight_is_nV_over_Kw', 'zero_or_signed_Q_is_not_a_physical_gate')
    need(all(done[key] is True for key in true_fields) and done['ignored_mode_local_sentinel'] == 255
         and done['active_wall_scratch_scope'] == 'i_lt_NpbOk_and_mode_MDBC2'
         and not done['full_coupled_spectrum'] and not done['physical_acceptance'], 'Original state/wall/pressure policy differs')
    need(all(math.isfinite(done[key]) and 0 <= done[key] <= 1 for key in
             ('max_final_float_budget_ratio', 'max_expanded_budget_ratio')),
         'An original literal-final-float or expanded arithmetic gate failed')
    paths = {}
    for name in ('trials.csv', 'responses.csv', 'focus.csv', 'summary.csv'):
        target = (T / 'outputs' / SOURCE / name).resolve()
        matches = [q for q in check['files'] if Path(q['path']).resolve() == target]
        need(len(matches) == 1, 'Unique sealed r3 CSV binding missing: ' + name)
        paths[name] = bind(matches[0], consumed)
    return done, paths


def trial_checks(path):
    trials = {}; clocks = {}; wall = {}
    for row in csv_rows(path, TRIAL_HEADER):
        numeric(row, strings=('mode',))
        p = int(row['part']); mode = row['mode']; h = float(row['requested_h_Pa']); sign = int(row['sign'])
        need(p in PARTS and int(row['completed_step']) == STEPS[p] and int(row['passed']) == 1
             and int(row['frozen_soil_checks']) == 5000 and int(row['frozen_wall_checks']) == 1805,
             'Original full-soil/full-fixed diagnostic gate not passed')
        key = (p, mode, h, sign)
        need(key not in trials and ((mode == 'baseline' and h == sign == 0) or
             (mode in MODES and h in (1., 10.) and sign in (-1, 1))), 'Unexpected/duplicate actual trial')
        time = float(row['time_s']); counts = tuple(int(row[k]) for k in
            ('NpbOk', 'active_walls', 'inactive_effective_walls', 'ignored_walls'))
        need(counts[0] == counts[1] + counts[2] and counts[3] == 1805 - counts[0]
             and sum(counts[1:]) == 1805 and min(counts) >= 0, 'Real wall partition coverage differs')
        if p not in clocks:
            clocks[p], wall[p] = time, counts
        need(clocks[p] == time and wall[p] == counts, 'Frozen actual clock/NpbOk/wall partition changed')
        need(0 <= int(row['actually_changed_soil']) <= 5000 and
             0 <= int(row['AS_tensor_changed_soil']) <= 5000 and float(row['quantization_max_Pa']) >= 0,
             'Invalid descriptive perturbation count')
        trials[key] = row
    expected = {(p, 'baseline', 0., 0) for p in PARTS}
    expected |= {(p, m, h, s) for p in PARTS for m in MODES for h in (1., 10.) for s in (-1, 1)}
    need(set(trials) == expected and len(trials) == 34, 'Exactly17 real calls per state required')
    return trials, clocks, wall


def response_arrays(path, trials, clocks):
    data = {(p, m, h): {k: np.empty(N) for k in COLUMNS} for p in PARTS for m in MODES for h in (1., 10.)}
    seen = {key: np.zeros(N, dtype=bool) for key in data}; rows = 0
    for row in csv_rows(path, RESPONSE_HEADER):
        numeric(row, strings=('mode',))
        key = (int(row['part']), row['mode'], float(row['requested_h_Pa'])); native_id = int(row['native_id'])
        need(key in data and 2060 <= native_id < 7060, 'Unexpected response profile/ID')
        i = native_id - 2060
        need(not seen[key][i], 'Duplicate response material ID'); seen[key][i] = True
        for name in COLUMNS:
            data[key][name][i] = float(row[name])
        rows += 1
    need(rows == 80000 and all(a.all() for a in seen.values()), 'Complete16 by5000 response coverage required')
    max_quant = 0.; max_central_closure = 0.; clock_tau = {}
    invariant = ('baseline_p_Pa', 'fixed_P0_Pa', 'weight_nV_Kw', 'no_fixed_neighbors', 'fresh_FS', 'R0_Pa_s')
    for key, a in data.items():
        part, mode, h = key; base = data[(part, 'constant', 1.)]
        need(all(np.array_equal(a[k], base[k]) for k in invariant), 'Saved baseline per-ID quantities vary between modes')
        need(np.all(a['time_s'] == clocks[part]) and np.all(a['completed_step'] == STEPS[part])
             and np.all(a['tau_s'] == a['tau_s'][0]), 'Actual response time/step differs')
        if part not in clock_tau:
            clock_tau[part] = float(a['tau_s'][0])
        need(clock_tau[part] == a['tau_s'][0] and np.all(a['weight_nV_Kw'] > 0)
             and np.isin(a['no_fixed_neighbors'], (0., 1.)).all(), 'Conditional capacity/cohort differs')
        phi = a['phi']
        if mode == 'constant':
            need(np.all(phi == 1), 'Constant profile differs')
        elif mode == 'initial_altX':
            need(np.isin(phi, (-1., 1.)).all() and np.count_nonzero(phi == 1) == 2500
                 and np.array_equal(phi, data[(38, mode, 1.)]['phi']), 'Sealed initial alt-X phase differs')
        else:
            target = np.zeros(N); ids = FOCUS[:2] if mode == MODES[2] else FOCUS[2:]
            target[ids[0]-2060], target[ids[1]-2060] = 1., -1.
            need(np.array_equal(phi, target), 'Unweighted fixed-ID dipole differs')
        for name in ('baseline_p_Pa', 'fixed_P0_Pa', 'p_plus_Pa', 'p_minus_Pa', 'R0_Pa_s', 'Rplus_Pa_s', 'Rminus_Pa_s'):
            need(np.array_equal(a[name], a[name].astype(np.float32).astype(float)), 'Original float pressure/rate representation differs')
        for sign, pk, qk in ((1, 'p_plus_Pa', 'plus_quant_error_Pa'), (-1, 'p_minus_Pa', 'minus_quant_error_Pa')):
            expected = (a['baseline_p_Pa'] + sign*h*phi).astype(np.float32).astype(float)
            need(np.array_equal(a[pk], expected), 'Actual pressure differs from original float perturbation')
            quant = (a[pk] - a['baseline_p_Pa']) - sign*h*phi
            need(np.array_equal(a[qk], quant), 'Reported perturbation quantization differs')
            observed = float(np.max(np.abs(quant))); max_quant = max(max_quant, observed)
            tr = trials[(part, mode, h, sign)]
            need(float(tr['quantization_max_Pa']) == observed and
                 int(tr['actually_changed_soil']) == np.count_nonzero(a[pk] != a['baseline_p_Pa']), 'Actual trial/response quantization or count differs')
        dp = (a['p_plus_Pa'] - a['p_minus_Pa']) * .5
        dr = (a['Rplus_Pa_s'] - a['Rminus_Pa_s']) * .5
        curve = a['Rplus_Pa_s'] + a['Rminus_Pa_s'] - 2*a['R0_Pa_s']
        need(np.array_equal(a['actual_central_dp_Pa'], dp) and np.array_equal(a['central_dp_over_requested_h'], dp/h)
             and np.array_equal(a['central_dR_Pa_s'], dr) and np.array_equal(a['second_difference_Pa_s'], curve),
             'Genuine central half-difference/second-difference arithmetic differs')
        # The original absolute plus/minus seven-term magnitude is not exported.
        # Thus this central closure is observed, not a fabricated reconstruction of the original row budget.
        closure = np.array([math.fsum(a[k][i] for k in CHANNEL_COLUMNS) - dr[i] for i in range(N)])
        a['_central_channel_closure'] = closure
        max_central_closure = max(max_central_closure, float(np.max(np.abs(closure))))
    return data, clock_tau, max_quant, max_central_closure


def summarize(data, path):
    original = {}; result = []; max_aggregate_ratio = 0.
    for row in csv_rows(path, SUMMARY_HEADER):
        numeric(row, strings=('mode', 'receiver_cohort'), optional=('Q_over_norm_s_1', 'central_rate_weighted_RMS_Pa_s', 'second_difference_weighted_RMS_Pa_s'))
        key = (int(row['part']), row['mode'], float(row['requested_h_Pa']), row['receiver_cohort'])
        need(key not in original and key[:3] in data and key[3] in COHORTS, 'Unexpected/duplicate summary profile')
        original[key] = row
    need(len(original) == 48, 'Exactly48 original cohort summaries required')
    for key, a in data.items():
        p, mode, h = key; weight = a['weight_nV_Kw']; dp = a['actual_central_dp_Pa']; dr = a['central_dR_Pa_s']; curve = a['second_difference_Pa_s']
        masks = (np.ones(N, dtype=bool), a['no_fixed_neighbors'] == 1, np.isin(a['fresh_FS'], (2., 3.)))
        for region, mask in zip(COHORTS, masks):
            row = original[(*key, region)]; count = int(np.count_nonzero(mask))
            need(int(row['count']) == count and float(row['time_s']) == a['time_s'][0]
                 and float(row['tau_s']) == a['tau_s'][0] and int(row['completed_step']) == STEPS[p], 'Original cohort clock/count differs')
            w, d, r = weight[mask], dp[mask], dr[mask]
            terms = {'sum_weight': w, 'central_dp_weighted_norm': w*d*d, 'Q': w*d*r, 'absQ': np.abs(w*d*r)}
            item = dict(part=p, time_s=float(a['time_s'][0]), tau_s=float(a['tau_s'][0]), completed_step=STEPS[p],
                        mode=mode, requested_h_Pa=h, receiver_cohort=region, count=count)
            max_error = 0.; max_budget = 0.; max_ratio = 0.
            for name, values in terms.items():
                value, error, budget = aggregate(values, float(row[name]), name)
                item[name] = value; max_error = max(max_error, error); max_budget = max(max_budget, budget)
                max_ratio = max(max_ratio, error/budget if budget else 0.)
            norm = item['central_dp_weighted_norm']; defined = norm > 0
            need(int(row['Q_over_norm_defined']) == int(defined), 'Undefined norm must not be clamped')
            if defined:
                need(float(row['Q_over_norm_s_1']) == float(row['Q']) / float(row['central_dp_weighted_norm']), 'Original reported Q/N arithmetic differs')
            else:
                need(row['Q_over_norm_s_1'] == '', 'Zero norm must have no reported ratio')
            item['Q_over_norm_defined'] = defined
            item['Q_over_norm_s_1'] = item['Q']/norm if defined else None
            for name, values in (('central_rate_weighted_RMS_Pa_s', dr[mask]), ('second_difference_weighted_RMS_Pa_s', curve[mask])):
                value = math.sqrt(sum64(w*values*values) / item['sum_weight']) if item['sum_weight'] > 0 else None
                if value is None:
                    need(row[name] == '', 'Empty receiver cohort RMS must be undefined')
                else:
                    report = float(row[name]); budget = (8*gamma(count+16)+16*EPS)*max(abs(value),abs(report)) + 128*TINY
                    need(abs(report-value) <= budget, 'Original descriptive RMS aggregation differs')
                item[name] = value
            qmax = float(max(np.max(np.abs(a['plus_quant_error_Pa'])), np.max(np.abs(a['minus_quant_error_Pa']))))
            need(float(row['quantization_max_Pa']) == qmax, 'Original per-mode quantization max differs')
            item['quantization_max_Pa'] = qmax
            for term, column in zip(TERMS, CHANNEL_COLUMNS):
                value, error, budget = aggregate(w*d*a[column][mask], float(row['Q_'+term]), 'Q_' + term)
                item['Q_'+term] = value; max_error = max(max_error,error); max_budget = max(max_budget,budget)
                max_ratio = max(max_ratio,error/budget if budget else 0.)
            item['eight_channel_Q_minus_actual_Q'] = math.fsum(item['Q_'+term] for term in TERMS) - item['Q']
            central_closure = a['_central_channel_closure'][mask]
            item['central_channel_closure_maxabs_Pa_s'] = float(np.max(np.abs(central_closure))) if count else None
            item['central_channel_closure_weighted_RMS_Pa_s'] = math.sqrt(sum64(w*central_closure*central_closure)/item['sum_weight']) if count else None
            item['original_summary_aggregation_max_budget_ratio'] = max_ratio
            max_aggregate_ratio = max(max_aggregate_ratio,max_ratio); result.append(item)
    return result, max_aggregate_ratio


def focus_rows(path, data):
    result = []; seen = set()
    for row in csv_rows(path, FOCUS_HEADER):
        numeric(row, strings=('mode',)); key = (int(row['part']), row['mode'], float(row['requested_h_Pa'])); native_id = int(row['native_id']); i = native_id-2060
        need(key in data and native_id in FOCUS and (*key,native_id) not in seen, 'Unexpected/duplicate focus profile')
        seen.add((*key,native_id)); a = data[key]
        for name in ('time_s','tau_s','completed_step','baseline_p_Pa','fixed_P0_Pa','p_plus_Pa','p_minus_Pa','R0_Pa_s','Rplus_Pa_s','Rminus_Pa_s'):
            need(float(row[name]) == a[name][i], 'Focus/response actual value differs: ' + name)
        tensors = {s: np.array([float(row['AS_'+s+'_'+k]) for k in ('xx','yy','zz','xy','yz','xz')]) for s in ('base','plus','minus')}
        need(all(np.array_equal(q,q.astype(np.float32).astype(float)) for q in tensors.values()), 'Actual float AS tensor differs')
        norms = {}
        for state in ('plus','minus'):
            d = tensors[state]-tensors['base']; norm = math.sqrt(sum64(d[:3]*d[:3]) + 2*sum64(d[3:]*d[3:]))
            report = a['AS'+state+'_delta_norm'][i]; budget = 64*EPS*max(abs(report),norm) + 64*TINY
            need(abs(report-norm) <= budget, 'Actual AS tensor norm/response differs')
            norms[state] = norm
        item = dict(row); h = key[2]
        item.update(actual_central_dp_Pa=float(a['actual_central_dp_Pa'][i]),
            central_dR_Pa_s=float(a['central_dR_Pa_s'][i]), central_dR_over_requested_h_s_1=float(a['central_dR_Pa_s'][i]/h),
            ASplus_delta_norm=norms['plus'], ASminus_delta_norm=norms['minus'])
        for name in CHANNEL_COLUMNS + ['central_Acex','central_Acey','central_Acez']:
            item[name] = float(a[name][i])
        result.append(item)
    need(len(result) == 64, 'Exactly64 focus cases required')
    return result


def amplitudes(summary):
    lookup = {(q['part'],q['mode'],q['requested_h_Pa'],q['receiver_cohort']):q for q in summary}; result = []
    for p in PARTS:
        for mode in MODES:
            for region in COHORTS:
                a,b = (lookup[(p,mode,h,region)] for h in (1.,10.))
                x,y = a['Q_over_norm_s_1'],b['Q_over_norm_s_1']
                result.append(dict(part=p,time_s=a['time_s'],tau_s=a['tau_s'],mode=mode,receiver_cohort=region,
                    Q_over_norm_1Pa_s_1=x,Q_over_norm_10Pa_s_1=y,ratio_10Pa_over_1Pa=(y/x if x not in (None,0.) and y is not None else None),
                    central_rate_RMS_per_requested_Pa_1=a['central_rate_weighted_RMS_Pa_s'],
                    central_rate_RMS_per_requested_Pa_10=(b['central_rate_weighted_RMS_Pa_s']/10 if b['central_rate_weighted_RMS_Pa_s'] is not None else None),
                    second_difference_RMS_1Pa=a['second_difference_weighted_RMS_Pa_s'],second_difference_RMS_10Pa=b['second_difference_weighted_RMS_Pa_s'],
                    quantization_max_1Pa=a['quantization_max_Pa'],quantization_max_10Pa=b['quantization_max_Pa']))
    return result


def plots(folder, summary, focus):
    lookup = {(q['part'],q['mode'],q['requested_h_Pa'],q['receiver_cohort']):q for q in summary}
    plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.22})
    colors = ('#0072B2','#D55E00','#009E73'); cohort_labels=('All5000','No fixed neighbors','Fresh FS2/3')
    fig,axes=plt.subplots(2,2,figsize=(14,8),constrained_layout=True)
    for r,p in enumerate(PARTS):
        tau=lookup[(p,'constant',1.,'all')]['tau_s']
        for region,color,label in zip(COHORTS,colors,cohort_labels):
            ys=[lookup[(p,'constant',h,region)]['Q_over_norm_s_1'] for h in (1.,10.)]
            axes[r,0].plot((1.,10.),ys,'o-',color=color,label=label)
            for h,marker in ((1.,'o'),(10.,'x')):
                values=[lookup[(p,m,h,region)]['Q_over_norm_s_1'] for m in MODES[1:]]
                axes[r,1].plot(np.arange(3),[np.nan if v is None else v for v in values],marker=marker,ls='-' if h==1 else '--',color=color,label=f'{label}, {h:g} Pa')
        axes[r,0].set_xscale('log');axes[r,0].set_xticks((1.,10.),('1','10'))
        axes[r,0].set(title=f'P{p}, tau={tau:.6f}s: constant pressure',xlabel='Requested amplitude [Pa]',ylabel='Conditional Q/N [1/s]')
        axes[r,0].set_yscale('symlog',linthresh=1.)
        axes[r,1].set_xticks(np.arange(3),MODE_LABELS[1:]);axes[r,1].set(title='High-frequency and fixed-pair local modes',ylabel='Conditional Q/N [1/s]')
        for ax in axes[r]:ax.axhline(0,color='#555555',lw=.7)
    axes[0,0].legend(fontsize=8);axes[0,1].legend(fontsize=7,ncol=2)
    fig.suptitle('Frozen-state pressure feedback: constant mode is not a gauge-null test; no full coupled stability claim',fontsize=12)
    first=folder/'conditional_work.png';fig.savefig(first,dpi=180);plt.close(fig)
    matrices=[]
    for p in PARTS:
        matrices.append(np.array([[lookup[(p,m,10.,'all')]['Q_'+term]/lookup[(p,m,10.,'all')]['central_dp_weighted_norm'] if lookup[(p,m,10.,'all')]['central_dp_weighted_norm']>0 else np.nan for term in TERMS] for m in MODES]))
    finite=np.concatenate([a[np.isfinite(a)] for a in matrices]);largest=float(np.max(np.abs(finite))) if len(finite) else 0.;display=max(largest,1.)
    norm=SymLogNorm(linthresh=1.,vmin=-display,vmax=display)
    fig,axes=plt.subplots(2,2,figsize=(15,8),constrained_layout=True)
    short=('Compression','LP','Taylor p','Da','FS Ace/Lx','Chain p','Chain Ace','Numeric residual')
    for r,p in enumerate(PARTS):
        image=axes[r,0].imshow(matrices[r],cmap='RdBu_r',norm=norm,aspect='auto')
        axes[r,0].set_yticks(np.arange(4),MODE_LABELS);axes[r,0].set_xticks(np.arange(8),short,rotation=35,ha='right')
        axes[r,0].set_title(f'P{p}: eight Q-channel/N values, all5000, requested10Pa')
        for h,color,offset in ((1.,'#0072B2',-.16),(10.,'#D55E00',.16)):
            chosen=[next(q for q in focus if int(q['part'])==p and q['mode']=='initial_altX' and float(q['requested_h_Pa'])==h and int(q['native_id'])==i) for i in FOCUS]
            axes[r,1].bar(np.arange(4)+offset,[float(q['central_dR_over_requested_h_s_1']) for q in chosen],.32,color=color,label=f'{h:g} Pa')
        axes[r,1].set_xticks(np.arange(4),[str(i) for i in FOCUS]);axes[r,1].set(title='Initial alt-X: four fixed material IDs',xlabel='Native material ID',ylabel='Central dR / requested h [1/s]');axes[r,1].axhline(0,color='#555555',lw=.7)
    axes[0,1].legend(fontsize=8);fig.colorbar(image,ax=axes[:,0],label='Signed conditional channel Q/N [1/s]')
    fig.suptitle('Seven source channels plus a separate numeric residual; saved states, no integration or causal repair',fontsize=12)
    second=folder/'channels_focus.png';fig.savefig(second,dpi=180);plt.close(fig)
    return [first,second]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execution-authorized',action='store_true')
    need(parser.parse_args().execution_authorized,'Root full-file review and separate offline admission required')
    check_path=L/(TAG+'.check.json');folder=T/'figures'/TAG
    need(not check_path.exists() and not folder.exists(),'Existing complete/failed derived outputs protected')
    consumed=[stat(Path(__file__)),stat(T/'notes'/(TAG+'.md'))];products=[]
    result=dict(stage=TAG,passed=False,component_invocations=0,solver_invocations=0,native_decodes=0,
                build_invocations=0,GPU_actions=0,physical_steps=0,SHA_scans=0,physical_acceptance=False)
    try:
        done,paths=source_inputs(consumed);trials,clocks,wall=trial_checks(paths['trials.csv'])
        data,tau,max_quant,max_closure=response_arrays(paths['responses.csv'],trials,clocks)
        need(max_quant==done['max_pressure_quantization_error_Pa'],'Completion quantization maximum differs')
        summary,max_aggregate_ratio=summarize(data,paths['summary.csv']);focus=focus_rows(paths['focus.csv'],data);amplitude=amplitudes(summary)
        folder.mkdir()
        for leaf,records in (('summary.csv',summary),('amplitude.csv',amplitude),('focus.csv',focus)):
            p=folder/leaf;write(p,records);products.append(p)
        products.extend(plots(folder,summary,focus))
        need(all(stat(q['path'])==q for q in consumed),'Bound input changed during offline review')
        all_values=[q['Q_over_norm_s_1'] for q in summary if q['receiver_cohort']=='all' and q['Q_over_norm_s_1'] is not None]
        result.update(passed=True,consumed=consumed,consumed_stats_unchanged=True,outputs=[stat(p) for p in products],
            original_actual_force_calls=34,baseline_bit_rows=10000,response_rows=80000,trial_rows=34,
            original_summary_rows=48,focus_rows=64,actual_times_s=clocks,actual_tau_s=tau,
            actual_wall_partition={str(p):dict(zip(('NpbOk','active','inactive_effective','ignored'),wall[p])) for p in PARTS},
            original_max_final_float_budget_ratio=done['max_final_float_budget_ratio'],
            original_max_expanded_budget_ratio=done['max_expanded_budget_ratio'],
            max_original_summary_double_aggregation_budget_ratio=max_aggregate_ratio,
            max_quantization_error_Pa=max_quant,max_observed_central_channel_closure_Pa_s=max_closure,
            independent_original_row_budget_reconstructed=False,
            original_row_budget_relied_on_actual_passed_component=True,
            eight_central_channel_closure_observed_not_new_physical_gate=True,
            numeric_residual_not_relabelled_physical_source=True,Q_sign_not_pass_gate=True,
            constant_mode_changes_total_stress_and_free_traction=True,full_coupled_stability_claim=False,
            all_cohort_Q_over_norm_range_s_1=([min(all_values),max(all_values)] if all_values else None),visual_QA_pending=True)
    except Exception as error:
        result.update(first_failure=str(error),consumed=consumed,partial_outputs_preserved=True)
        raise
    finally:
        with check_path.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2,allow_nan=False)


if __name__=='__main__':main()
