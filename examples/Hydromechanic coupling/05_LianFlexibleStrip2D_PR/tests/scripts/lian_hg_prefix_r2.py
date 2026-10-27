"""Exact saved-state comparison; dterror is an output-interval statistic."""
import numpy as np

NATIVE_COLUMNS = [
    'time_s', 'saved_step', 'id', 'x', 'y', 'z', 'vx', 'vy', 'vz', 'rho',
    'pressure', 'sigma_xx', 'sigma_yy', 'sigma_zz', 'sigma_xy', 'sigma_yz',
    'sigma_xz', 'kplastic', 'load_ax', 'load_ay', 'load_az', 'fstype',
    'normal_x', 'normal_y', 'normal_z', 'load_available', 'position_double',
    'stress_double', 'mass', 'dp', 'h', 'native_count', 'nout', 'has_dterror',
    'dterror_s',
]
STATE_COLUMNS = [c for c in NATIVE_COLUMNS if c != 'dterror_s']


def compare_prefix(a, b):
    assert list(a.columns) == list(b.columns) == NATIVE_COLUMNS, 'Native schema changed'
    assert len(a) == len(b) and len(a) > 0, 'Native row count changed'
    av = a.to_numpy(dtype='<f8')
    bv = b.to_numpy(dtype='<f8')
    assert np.isfinite(av).all() and np.isfinite(bv).all(), 'Nonfinite native data'
    physical = a[STATE_COLUMNS].to_numpy(dtype='<f8').tobytes() == b[STATE_COLUMNS].to_numpy(dtype='<f8').tobytes()
    assert physical, 'Physical/state/identity/time/step/flag prefix mismatch'
    for frame in (a, b):
        if frame.time_s.iloc[0] != 0:
            assert frame.has_dterror.eq(1).all(), 'Natural-step diagnostic missing'
            assert frame.dterror_s.le(1e-14).all(), 'Original natural-step guard failed'
    return dict(
        raw_all_columns0ulp=av.tobytes() == bv.tobytes(),
        physical_identity_columns0ulp=physical,
        compared_columns=STATE_COLUMNS.copy(),
        excluded_interval_statistic='dterror_s',
        a_dterror_s=float(a.dterror_s.iloc[0]),
        b_dterror_s=float(b.dterror_s.iloc[0]),
        dterror_abs_difference_s=float(abs(a.dterror_s.to_numpy() - b.dterror_s.to_numpy()).max()),
    )
