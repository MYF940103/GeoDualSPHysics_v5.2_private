"""Offline old/new 128-update comparison; only rewrites its own derived JSON/CSV."""
import csv
import json
import struct
from pathlib import Path

import numpy as np

T = Path(__file__).resolve().parents[1]
DIRS = {k: T / f'outputs/upl_density_cache_column_{k}_native_r1' for k in ('old', 'new')}


def read(directory, layout):
    raw = (directory / 'typed22.bin').read_bytes()
    assert struct.unpack_from('<III', raw) == (1040, 22, 8)
    offset, result = 12, []
    for _ in range(8):
        time = struct.unpack_from('<d', raw, offset)[0]
        offset += 8
        fields = {}
        for field in layout:
            dtype = {'uint32': '<u4', 'float32': '<f4', 'float64': '<f8'}[field['type']]
            width = int(field['components'])
            value = np.frombuffer(raw, dtype=dtype, count=1040 * width, offset=offset).reshape(1040, width)
            offset += value.nbytes
            fields[field['array']] = value.copy()
        assert np.array_equal(fields['Idp'].ravel(), np.arange(1040))
        result.append((time, fields))
    assert offset == len(raw)
    return result


def review():
    for name in ('typed22_layout.csv', 'native_ids.csv', 'clocks.csv'):
        assert (DIRS['old'] / name).read_bytes() == (DIRS['new'] / name).read_bytes(), name
    with (DIRS['new'] / 'typed22_layout.csv').open(newline='') as file:
        layout = list(csv.DictReader(file))
    old, new = (read(DIRS[k], layout) for k in ('old', 'new'))
    x0 = new[0][1]['Posd']
    top = np.flatnonzero((np.arange(1040) >= 40) & np.isclose(x0[:, 2], .995, atol=1e-14, rtol=0))
    bottom = np.flatnonzero((np.arange(1040) >= 40) & np.isclose(x0[:, 2], .005, atol=1e-14, rtol=0))
    assert len(top) == len(bottom) == 10
    summary, history = {}, []
    for part, ((time, a), (new_time, b)) in enumerate(zip(old, new)):
        assert struct.pack('<d', time) == struct.pack('<d', new_time)
        for name, x in a.items():
            y = b[name]
            item = summary.setdefault(name, {'max_abs_difference': 0., 'changed_byte_count': 0, 'bit_exact': True})
            item['max_abs_difference'] = max(item['max_abs_difference'], float(np.abs(x.astype(float) - y.astype(float)).max()))
            item['changed_byte_count'] += int(np.count_nonzero(x.view(np.uint8) != y.view(np.uint8)))
            item['bit_exact'] &= x.tobytes() == y.tobytes()
        expected = (1000 + 1100 / b['PoroVolumeRatio'][40:]).astype('<f4')
        assert expected.tobytes() == b['native_Rhop'][40:].tobytes()
        po, pn = a['PorePress'][40:].astype(float), b['PorePress'][40:].astype(float)
        history.append({'part': part, 'time_s': time,
                        'old_pressure_RMS_Pa': float(np.sqrt(np.mean(po ** 2))),
                        'new_pressure_RMS_Pa': float(np.sqrt(np.mean(pn ** 2))),
                        'pressure_RMS_difference_Pa': float(np.sqrt(np.mean((po - pn) ** 2))),
                        'max_abs_theta_per_s': float(np.abs(b['PoroThetaLastStage'][40:]).max()),
                        'top_material_settlement_mm': float(-1000 * (b['Posd'][top, 2] - x0[top, 2]).mean()),
                        'bottom_material_settlement_mm': float(-1000 * (b['Posd'][bottom, 2] - x0[bottom, 2]).mean()),
                        'native_Rhop_max_abs_difference': float(np.abs(a['native_Rhop'][40:] - b['native_Rhop'][40:]).max())})
    return {'stage': 'upl_density_cache_column_pair_root_r1', 'actual_samples': 8,
            'native_ids_per_frame': 1040, 'typed_arrays': 22, 'actual_end_s': new[-1][0],
            'physical_fields_byte_exact_except_Rhop': all(v['bit_exact'] for k, v in summary.items() if k != 'native_Rhop'),
            'actual_clock_and_signed_dterror_CSV_byte_exact': True, 'new_native_cache_float_checks': 8000,
            'max_abs_theta_per_s': max(q['max_abs_theta_per_s'] for q in history),
            'field_comparison': summary, 'history': history,
            'CODE_not_exported_not_claimed_equal': True, 'saved_load_proxy_not_original_force_gate': True,
            'no_new_half_or_full_cycle_acceptance': True, 'new_SHA': 0,
            'analysis_note': 'RMS reductions use binary64; native arrays keep their original types.'}


if __name__ == '__main__':
    result = review()
    (T / 'notes/upl_density_cache_column_pair_root_r1.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    with (T / 'figures/upl_density_cache_column_pair_r1.csv').open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=list(result['history'][0]))
        writer.writeheader()
        writer.writerows(result['history'])
    print(json.dumps({k: v for k, v in result.items() if k not in ('history', 'field_comparison')}, indent=2))
