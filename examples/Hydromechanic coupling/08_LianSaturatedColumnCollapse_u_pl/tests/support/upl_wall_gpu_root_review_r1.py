"""Offline review of retained zero-step components; no solver, hashes or raw writes."""
import csv
import json
import math
from pathlib import Path

T = Path(__file__).resolve().parents[1]
OUT = T / 'notes/upl_wall_gpu_root_review_r1.json'


def rows(name):
    with (T / name).open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def check(name):
    value = json.loads((T / ('logs/' + name)).read_text(encoding='utf-8-sig'))
    assert value['passed'], name
    return value


def review():
    gpu = check('upl_c08_global_GPU_r1.check.json')
    cpu = check('upl_c08_force_CPU_r1.check.json')
    legacy = check('upl_gpu_nullj_off_r1.check.json')
    field = rows('outputs/upl_c08_global_GPU_r1/fields.csv')
    reference = {int(r['native_id']): r for r in rows('outputs/upl_c08_nearest_CPU_r1/walls.csv')
                 if r['actual_state_called'] == '1'}
    assert len(reference) == 410 and len(field) == 10820
    joined = []
    for r in field:
        if r['is_fluid'] != '0':
            continue
        ref = reference[int(r['native_id'])]
        ep = abs(float(r['p_Pa']) - float(ref['p_B_reference']))
        ej = abs(float(r['J']) - 1.)
        ratio = max(ep / float(ref['p_budget']), ej / float(ref['J_budget']))
        assert ratio <= 1., (r['trial'], r['native_id'], ratio)
        joined.append((ep, ej, ratio))
    assert len(joined) == 820
    descriptors = rows('outputs/upl_c08_global_GPU_r1/cpu_descriptor.csv')
    normals = [r for r in descriptors if r['field'] in ('FSnx', 'FSny', 'FSnz')]
    surface = {r['native_id'] for r in field if r['trial'] == '0' and r['FSType'] == '2'}
    assert len(surface) == 100
    used_normal = max(float(r['absolute_difference']) for r in normals if r['native_id'] in surface)
    kin = rows('outputs/upl_c08_force_CPU_r1/kinematics.csv')
    rate = rows('outputs/upl_c08_force_CPU_r1/rates.csv')
    assert len(kin) == len(rate) == 5000
    ids = set(range(2060, 7060))
    assert {int(r['native_id']) for r in kin} == {int(r['native_id']) for r in rate} == ids
    theta_ratio = max(float(r['theta_error']) / float(r['theta_budget']) for r in kin)
    stress_ratio = max(float(r[c + '_error']) / float(r[c + '_budget'])
                       for r in kin for c in ('sxx', 'syy', 'szz', 'sxy', 'syz', 'sxz'))
    assert theta_ratio <= 1. and stress_ratio <= 1.
    base = 'outputs/upl_gpu_nullj_off_'
    for filename in ('active.csv', 'off.csv', 'completion.json'):
        assert (T / (base + 'preport_r1/' + filename)).read_bytes() == (T / (base + 'current_r1/' + filename)).read_bytes()
    retained = T.parents[1] / '02_TerzaghiConsolidation_q0_PR/tests/outputs/bv_pair_gpu_debug_run_r2/pairs.csv'
    for label in ('preport', 'current'):
        assert (T / (base + label + '_r1/active.csv')).read_bytes() == retained.read_bytes()
    return {
        'stage': 'upl_wall_gpu_root_review_r1', 'passed': True,
        'GPU_affine_wall_pairs': len(joined),
        'GPU_wall_max_p_error_Pa': max(x[0] for x in joined),
        'GPU_wall_max_J_error': max(x[1] for x in joined),
        'GPU_wall_original_budget_max_ratio': max(x[2] for x in joined),
        'CPU_GPU_used_FSType2_normal_max_difference': used_normal,
        'unused_interior_normal_difference_is_not_a_new_gate': True,
        'CPU_actual_force_theta_max_budget_ratio': theta_ratio,
        'CPU_actual_force_sigma_max_budget_ratio': stress_ratio,
        'CPU_finished_Ace_rate_RMS_Pa_s': math.sqrt(sum(float(r['rate_Pa_s']) ** 2 for r in rate) / len(rate)),
        'CPU_finished_Ace_rate_absmax_Pa_s': max(abs(float(r['rate_Pa_s'])) for r in rate),
        'default_NULL_J_78_conditions_old_new_byte_exact': True,
        'default_72_active_conditions_retained_bytes_exact': True,
        'GPU_memcheck_zero_errors_and_leaks': gpu['zero_memcheck_errors'] and gpu['zero_memcheck_leaks'],
        'physical_steps': 0, 'new_SHA': 0,
        'limits': [
            'Global hydrostatic test prescribes Ace=-g; its 23.64048 Pa/s RMS is not mechanical equilibrium.',
            'Actual-force CPU test uses cold manufactured sigma=0 and compression. Its large complete pressure rates are not a gravity-equilibrium result.',
            'Default regression is a NULL-J main-force comparison, not a dynamic physical trajectory.',
            'No new tolerance, half-step chain, production allocation, gravity integration or plastic-collapse acceptance.'
        ],
        'consumed_checks': [gpu['stage'], cpu['stage'], legacy['stage']]
    }


if __name__ == '__main__':
    assert not OUT.exists(), 'Preserve existing root review; inspect it instead of overwriting.'
    result = review()
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
