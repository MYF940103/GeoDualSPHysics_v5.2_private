"""Standalone SI TPI pressure-row algebra; no spatial assembly or solver integration."""
import argparse
import cmath
import csv
import json
import math
from decimal import Decimal, localcontext
from pathlib import Path

T = Path(__file__).resolve().parents[1]
TAG = 'c08_tpi_row_r1'
OUT, CHECK = T / 'outputs' / TAG, T / 'logs' / (TAG + '.check.json')
EPS, DENORM = 2.0**-52, float.fromhex('0x0.0000000000001p-1022')


def need(ok, message):
    if not ok:
        raise ValueError(message)


def pressure_row(S, neighbor_sum, B, p_n, p_nm1, alpha, beta_capacity_m_inv,
                 dt, plastic_eligible, negative_branch_enabled):
    """S[1/(m s)], neighbor_sum/B[Pa/(m s)], p[Pa], beta[1/m], dt[s]."""
    values = (S, neighbor_sum, B, p_n, p_nm1, alpha, beta_capacity_m_inv, dt)
    try:
        finite = all(isinstance(v, (int, float)) and not isinstance(v, bool)
                     and math.isfinite(v) for v in values)
    except (OverflowError, TypeError):
        finite = False
    need(finite, 'Inputs must be finite binary64-range real scalars')
    need(type(plastic_eligible) is bool and type(negative_branch_enabled) is bool,
         'Eligibility and branch controls must be bool')
    need(S > 0 and dt > 0, 'Positive S and dt required; no denominator repair')
    need(0 <= alpha <= 1 and beta_capacity_m_inv >= 0, 'Invalid alpha or capacity')
    tilde = p_n + alpha * (p_n - p_nm1)
    active = plastic_eligible and negative_branch_enabled and p_n < 0
    capacity = beta_capacity_m_inv / dt if active else 0.0
    need(not (active and beta_capacity_m_inv > 0 and capacity == 0),
         'Positive capacity/step underflow; no silent removal')
    diagonal = S + capacity
    numerator = B + neighbor_sum + capacity * tilde
    need(all(math.isfinite(v) for v in (tilde, capacity, diagonal, numerator))
         and diagonal > 0, 'Nonfinite intermediate or invalid diagonal')
    pressure = numerator / diagonal
    need(math.isfinite(pressure), 'Nonfinite pressure result')
    return dict(tilde_i_Pa=tilde, negative_branch_active=active,
                capacity_over_dt=capacity, diagonal=diagonal,
                numerator=numerator, pressure_Pa=pressure)


def exact_row(q):
    """Independent 90-digit evaluation of exact binary64 inputs and rational row."""
    with localcontext() as ctx:
        ctx.prec = 90
        S, W, B, pn, pm, a, beta, dt = (Decimal.from_float(float(q[k])) for k in
            ('S', 'neighbor_sum', 'B', 'p_n', 'p_nm1', 'alpha', 'beta_capacity_m_inv', 'dt'))
        tilde = (1 + a) * pn - a * pm
        c = beta / dt if q['plastic_eligible'] and q['negative_branch_enabled'] and pn < 0 else Decimal(0)
        p = (W + B + c * tilde) / (S + c)
        scale = (abs(W) + abs(B) + abs(c) * (abs(pn) + abs(a) * (abs(pn) + abs(pm)))) / abs(S + c) + abs(p)
        return p, tilde, c, scale


def gamma(n):
    u = n * (.5 * EPS)
    need(u < 1, 'Invalid roundoff operation count')
    return u / (1 - u)


def stat(path):
    path = Path(path).resolve(); s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns)


def write_csv(path, rows):
    need(bool(rows), 'No empty expected CSV')
    with path.open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def algebra_tests():
    rows, invalid = [], []
    calls = 0
    base = dict(S=2.0, neighbor_sum=-230.0, B=-7.0, p_n=-120.0, p_nm1=-110.0,
                alpha=.5, beta_capacity_m_inv=.04, dt=.000005,
                plastic_eligible=True, negative_branch_enabled=True)

    def call(q):
        nonlocal calls
        calls += 1
        return pressure_row(**q)

    def check(name, q):
        got = call(q); exact, tilde, capacity, scale = exact_row(q)
        budget = gamma(32) * float(scale) + 32 * DENORM
        with localcontext() as ctx:
            ctx.prec = 90
            error = abs(Decimal.from_float(got['pressure_Pa']) - exact)
        need(error <= Decimal.from_float(budget), 'Decimal row mismatch: ' + name)
        rows.append(dict(name=name, **q, **got, decimal_pressure_Pa=str(exact),
                         absolute_error_Pa=float(error), arithmetic_budget_Pa=budget))
        return got, exact, tilde, capacity, budget

    for p in (20.0, -20.0, 0.0):
        q = dict(base, p_n=p, p_nm1=p, neighbor_sum=base['S'] * p, B=0.0)
        got, *_ = check('constant_' + str(p), q)
        need(got['pressure_Pa'] == p, 'Constant fixed point lost')
    # External neighbor histories, weights sum to one; no hidden spatial operator.
    for alpha, expected in ((0.0, 12.5), (.5, 13.625), (1.0, 14.75)):
        weighted = 2 * (.25 * (10 + alpha * (10 - 7)) + .75 * (14 + alpha * (14 - 12)))
        q = dict(base, p_n=8.0, p_nm1=6.0, alpha=alpha, neighbor_sum=weighted, B=-1.0)
        got, *_ = check('history_alpha_' + str(alpha), q)
        need(got['pressure_Pa'] == expected and got['tilde_i_Pa'] == 8 + 2 * alpha,
             'Declared neighbor/self histories differ')
    original, exact, tilde, capacity, budget = check('negative_capacity', base)
    with localcontext() as ctx:
        ctx.prec = 90
        residual = (Decimal.from_float(base['B']) + Decimal.from_float(base['neighbor_sum'])
                    - Decimal.from_float(base['S']) * tilde) / (Decimal.from_float(base['S']) + capacity)
        need(abs((Decimal.from_float(original['pressure_Pa']) - tilde) - residual)
             <= Decimal.from_float(budget), 'Negative-branch residual identity failed')
    for name, patch in (('nonnegative', dict(p_n=4.0)), ('zero_old', dict(p_n=0.0)),
                        ('plastic_off', dict(plastic_eligible=False)),
                        ('branch_off', dict(negative_branch_enabled=False)),
                        ('zero_beta', dict(beta_capacity_m_inv=0.0))):
        got, *_ = check(name, dict(base, **patch))
        need(got['capacity_over_dt'] == 0 and got['pressure_Pa'] == -118.5,
             'Ordinary or zero-capacity row changed')
    crossing, *_ = check('old_negative_result_positive', dict(base, B=2000000.0))
    need(crossing['negative_branch_active'] and crossing['pressure_Pa'] > 0,
         'Branch must use old pressure, without clipping the result')
    for factor in (2.0**-20, .1, 2.0**20):
        q = dict(base, **{k: base[k] * factor for k in ('S', 'neighbor_sum', 'B', 'beta_capacity_m_inv')})
        got, _, _, _, eb = check('whole_row_scale_' + str(factor), q)
        need(abs(got['pressure_Pa'] - original['pressure_Pa']) <= budget + eb,
             'Whole-row scaling including beta is not invariant')
    wrong = dict(base, **{k: base[k] * 1000 for k in ('S', 'neighbor_sum', 'B')})
    wrong_value, *_ = check('unscaled_beta_counterexample', wrong)
    need(abs(wrong_value['pressure_Pa'] - original['pressure_Pa']) > budget * 100,
         'Missing beta rescaling counterexample unexpectedly invariant')
    bad = [('zero_S', {'S': 0.0}), ('negative_S', {'S': -1.0}), ('infinite_S', {'S': math.inf}),
           ('zero_dt', {'dt': 0.0}), ('negative_dt', {'dt': -1.0}), ('nan_dt', {'dt': math.nan}),
           ('alpha_below', {'alpha': -.01}), ('alpha_above', {'alpha': 1.01}),
           ('negative_beta', {'beta_capacity_m_inv': -.04}), ('infinite_beta', {'beta_capacity_m_inv': math.inf}),
           ('nan_B', {'B': math.nan}), ('infinite_neighbor', {'neighbor_sum': math.inf}),
           ('infinite_pn', {'p_n': math.inf}), ('nan_previous', {'p_nm1': math.nan}),
           ('non_bool_control', {'plastic_eligible': 1}), ('bool_scalar', {'S': True}),
           ('integer_outside_float_range', {'S': 10**1000}),
           ('overflow_capacity', {'beta_capacity_m_inv': 1e308, 'dt': 1e-308}),
           ('underflow_capacity', {'beta_capacity_m_inv': DENORM, 'dt': 1e308})]
    for name, patch in bad:
        try:
            call(dict(base, **patch))
        except ValueError as error:
            invalid.append(dict(name=name, explicitly_rejected=True, reason=str(error)))
        else:
            raise ValueError('Invalid input silently accepted: ' + name)
    return rows, invalid, calls


def scalar_tests():
    modes = []
    for alpha in (0.0, .5, 1.0):
        lower = -1 / (1 + 2 * alpha)
        for mu in sorted(set((-1.0, -.75, lower, -.25, 0.0, .25, .75, 1.0, 1.25))):
            a, b = (1 + alpha) * mu, alpha * mu
            root = cmath.sqrt(a * a - 4 * b)
            roots = ((a + root) / 2, (a - root) / 2); radius = max(abs(z) for z in roots)
            residual = max(abs(z * z - a * z + b) for z in roots)
            rb = 128 * EPS * max(abs(z)**2 + abs(a * z) + abs(b) for z in roots) + 128 * DENORM
            need(residual <= rb, 'Characteristic-root arithmetic failed')
            strict = lower < mu < 1
            jury = (1 - mu > 0 and 1 + (1 + 2 * alpha) * mu > 0 and 1 - alpha * mu > 0)
            need(strict == jury, 'Real-mu Schur/Jury domain differs')
            boundary = mu == lower or mu == 1
            need(radius < 1 if strict else abs(radius - 1) <= 64 * EPS if boundary else radius > 1,
                 'Computed roots disagree with declared real-mu domain')
            modes.append(dict(alpha=alpha, mu=mu, strict_lower_mu=lower, strict_Schur=strict,
                              boundary=boundary, spectral_radius=radius,
                              root1_real=roots[0].real, root1_imag=roots[0].imag,
                              root2_real=roots[1].real, root2_imag=roots[1].imag,
                              characteristic_error=residual, arithmetic_budget=rb))
    histories = []
    for name, alpha, mu, previous, current in (
            ('negative_mu_growth', .5, -.75, 1.0, 1.0), ('alpha1_mu1_drift', 1.0, 1.0, 0.0, 1.0)):
        dprev, dcur = Decimal.from_float(previous), Decimal.from_float(current)
        eprev = ecur = 0.0
        for n in range(25):
            value = mu * ((1 + alpha) * current - alpha * previous)
            with localcontext() as ctx:
                ctx.prec = 90
                dnext = Decimal.from_float(mu) * ((1 + Decimal.from_float(alpha)) * dcur - Decimal.from_float(alpha) * dprev)
            scale = abs(mu) * ((1 + alpha) * abs(current) + alpha * abs(previous))
            eb = abs(mu) * ((1 + alpha) * ecur + alpha * eprev) + gamma(8) * scale + 8 * DENORM
            with localcontext() as ctx:
                ctx.prec = 90
                error = abs(Decimal.from_float(value) - dnext)
            need(error <= Decimal.from_float(eb), 'History recurrence exceeds propagated arithmetic bound')
            if name == 'alpha1_mu1_drift':
                need(value == n + 2, 'Alpha1/mu1 expected exact linear drift lost')
            histories.append(dict(sequence=name, index_n=n, alpha=alpha, mu=mu,
                                  u_previous=previous, u_current=current, u_next=value,
                                  decimal_u_next=str(dnext), error=float(error), arithmetic_budget=eb))
            previous, current, dprev, dcur, eprev, ecur = current, value, dcur, dnext, ecur, eb
        if name == 'negative_mu_growth':
            need(abs(current) > 1, 'Declared unstable illustrative history did not grow')
    return modes, histories


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--execution-authorized', action='store_true')
    need(p.parse_args().execution_authorized, 'Separate root review and algebra-only execution admission required')
    need(not OUT.exists() and not CHECK.exists(), 'Existing complete/failed outputs are immutable')
    before = [stat(Path(__file__)), stat(T / 'notes' / (TAG + '.md'))]
    result = dict(stage=TAG, passed=False, consumed=before, force_calls=0, solver_invocations=0,
                  native_decodes=0, build_invocations=0, physical_steps=0, SHA_scans=0, physical_acceptance=False)
    OUT.mkdir()
    try:
        rows, invalid, calls = algebra_tests(); modes, histories = scalar_tests()
        for name, data in (('rows', rows), ('invalid', invalid), ('scalar_modes', modes), ('histories', histories)):
            write_csv(OUT / (name + '.csv'), data)
        need(all(stat(q['path']) == q for q in before), 'Author files changed during algebra test')
        result.update(passed=True, consumed_stats_unchanged=True, pressure_row_calls=calls,
                      row_cases=len(rows), explicit_invalid_cases=len(invalid), scalar_modes=len(modes),
                      history_rows=len(histories), independent_Decimal_precision=90,
                      beta_has_capacity_unit_m_inv=True, beta004_not_selected_for_C08=True,
                      spatial_A_B_E_not_assembled=True, no_integrator_or_restart_interface=True,
                      real_mu_Schur_domain='-1/(1+2alpha)<mu<1; 0<=alpha<=1',
                      alpha1_not_actual_implicit=True, full_coupled_stability_claim=False,
                      files=[stat(OUT / (name + '.csv')) for name in ('rows', 'invalid', 'scalar_modes', 'histories')])
    except Exception as error:
        result.update(first_failure=str(error), partial_outputs_preserved=True)
        raise
    finally:
        with CHECK.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2, allow_nan=False)


if __name__ == '__main__':
    main()
