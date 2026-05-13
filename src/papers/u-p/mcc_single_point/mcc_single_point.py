"""Standalone Modified Cam Clay material-point prototype.

This module is intentionally independent from the GeoDualSPHysics solver.  It
uses compression-positive MCC variables internally and provides small helpers to
map to/from the current GeoDualSPHysics ``Sigmac`` convention where compression
is stored as negative stress.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import exp, isfinite, log, sqrt
from typing import Dict, List, Sequence, Tuple

Matrix = List[List[float]]


def eye(scale: float = 1.0) -> Matrix:
    return [[scale, 0.0, 0.0], [0.0, scale, 0.0], [0.0, 0.0, scale]]


def zeros() -> Matrix:
    return [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]


def mat_add(a: Matrix, b: Matrix) -> Matrix:
    return [[a[i][j] + b[i][j] for j in range(3)] for i in range(3)]


def mat_sub(a: Matrix, b: Matrix) -> Matrix:
    return [[a[i][j] - b[i][j] for j in range(3)] for i in range(3)]


def mat_scale(a: Matrix, s: float) -> Matrix:
    return [[a[i][j] * s for j in range(3)] for i in range(3)]


def trace(a: Matrix) -> float:
    return a[0][0] + a[1][1] + a[2][2]


def deviator(a: Matrix) -> Matrix:
    m = trace(a) / 3.0
    return mat_sub(a, eye(m))


def tensor_dot(a: Matrix, b: Matrix) -> float:
    total = 0.0
    for i in range(3):
        for j in range(3):
            total += a[i][j] * b[i][j]
    return total


def principal_diag(x: float, y: float, z: float) -> Matrix:
    return [[x, 0.0, 0.0], [0.0, y, 0.0], [0.0, 0.0, z]]


def invariants(stress: Matrix) -> Tuple[float, float, float]:
    """Return compression-positive p, q, and J2 for an internal stress tensor."""
    p = trace(stress) / 3.0
    s = deviator(stress)
    j2 = 0.5 * tensor_dot(s, s)
    q = sqrt(max(0.0, 3.0 * j2))
    return p, q, j2


def to_sigmac_negative_compression(stress_cp: Matrix) -> Matrix:
    """Map compression-positive internal stress to current Sigmac convention."""
    return mat_scale(stress_cp, -1.0)


def from_sigmac_negative_compression(sigmac: Matrix) -> Matrix:
    """Map current Sigmac convention to compression-positive internal stress."""
    return mat_scale(sigmac, -1.0)


@dataclass
class MCCParams:
    m: float = 1.2
    lam: float = 0.20
    kappa: float = 0.04
    e0: float = 0.80
    pc0: float = 160.0
    young: float = 5000.0
    poisson: float = 0.30
    tension_cutoff: float = 1.0e-6
    return_tolerance: float = 1.0e-8
    return_max_iter: int = 40
    max_line_search: int = 12

    @property
    def bulk(self) -> float:
        return self.young / (3.0 * (1.0 - 2.0 * self.poisson))

    @property
    def shear(self) -> float:
        return self.young / (2.0 * (1.0 + self.poisson))

    def validate(self) -> None:
        if not (self.m > 0.0):
            raise ValueError("MCC M must be positive")
        if not (self.lam > self.kappa > 0.0):
            raise ValueError("MCC lambda must be greater than kappa > 0")
        if not (self.e0 > -1.0):
            raise ValueError("Initial void ratio must be greater than -1")
        if not (self.pc0 > 0.0):
            raise ValueError("Initial preconsolidation pressure must be positive")
        if not (self.young > 0.0 and -1.0 < self.poisson < 0.5):
            raise ValueError("Elastic E/nu values are invalid")
        if not (self.return_tolerance > 0.0 and self.return_max_iter > 0):
            raise ValueError("Return mapping tolerance/iteration settings are invalid")


@dataclass
class MCCState:
    stress: Matrix
    pc: float
    e: float
    eps_p_v: float = 0.0
    eps_p_eq: float = 0.0
    plastic_multiplier: float = 0.0
    yield_flag: int = 0
    return_status: str = "initial"
    iterations: int = 0
    residual: float = 0.0

    def copy(self) -> "MCCState":
        return replace(self, stress=[row[:] for row in self.stress])


@dataclass
class MCCStep:
    step: int
    path: str
    eps_xx: float
    eps_yy: float
    eps_zz: float
    eps_xy: float
    eps_yz: float
    eps_xz: float
    eps_v: float
    stress_xx: float
    stress_yy: float
    stress_zz: float
    stress_xy: float
    stress_yz: float
    stress_xz: float
    sigmac_xx: float
    sigmac_yy: float
    sigmac_zz: float
    p: float
    q: float
    pc: float
    e: float
    eps_p_v: float
    eps_p_eq: float
    plastic_multiplier: float
    yield_f: float
    return_status: str
    yield_flag: int
    iterations: int
    residual: float
    pore_pressure_proxy: float = 0.0

    def as_dict(self) -> Dict[str, float | int | str]:
        return self.__dict__.copy()


def yield_function(p: float, q: float, pc: float, params: MCCParams) -> float:
    return q * q + params.m * params.m * p * (p - pc)


def elastic_predictor(stress: Matrix, strain_inc: Matrix, params: MCCParams) -> Matrix:
    eps_v = trace(strain_inc)
    dev_eps = deviator(strain_inc)
    dstress = mat_add(eye(params.bulk * eps_v), mat_scale(dev_eps, 2.0 * params.shear))
    return mat_add(stress, dstress)


def _solve_linear4(a: List[List[float]], b: List[float]) -> List[float]:
    """Small Gaussian elimination helper for the Newton system."""
    n = 4
    mat = [a[i][:] + [b[i]] for i in range(n)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(mat[r][col]))
        if abs(mat[pivot][col]) < 1.0e-18:
            raise ZeroDivisionError("Singular Newton Jacobian")
        if pivot != col:
            mat[col], mat[pivot] = mat[pivot], mat[col]
        piv = mat[col][col]
        for j in range(col, n + 1):
            mat[col][j] /= piv
        for r in range(n):
            if r == col:
                continue
            fac = mat[r][col]
            if fac == 0.0:
                continue
            for j in range(col, n + 1):
                mat[r][j] -= fac * mat[col][j]
    return [mat[i][n] for i in range(n)]


def _mcc_residual(x: Sequence[float], p_tr: float, q_tr: float, pc_old: float,
                  e_old: float, params: MCCParams) -> List[float]:
    p, q, pc, dl = x
    a = params.m * params.m
    h = (1.0 + e_old) / (params.lam - params.kappa)
    df_dp = a * (2.0 * p - pc)
    df_dq = 2.0 * q
    depv = dl * df_dp
    # Guard exponent so failed Newton guesses do not overflow while line search
    # pulls the iteration back to the admissible region.
    expo = max(-60.0, min(60.0, h * depv))
    pc_hard = pc_old * exp(expo)
    return [
        p - p_tr + params.bulk * dl * df_dp,
        q - q_tr + 3.0 * params.shear * dl * df_dq,
        pc - pc_hard,
        yield_function(p, q, pc, params),
    ]


def _norm(values: Sequence[float]) -> float:
    return sqrt(sum(v * v for v in values))


def _numeric_jacobian(x: Sequence[float], p_tr: float, q_tr: float, pc_old: float,
                      e_old: float, params: MCCParams) -> List[List[float]]:
    base = _mcc_residual(x, p_tr, q_tr, pc_old, e_old, params)
    jac = [[0.0 for _ in range(4)] for _ in range(4)]
    for c in range(4):
        step = 1.0e-6 * max(1.0, abs(x[c]))
        xp = list(x)
        xp[c] += step
        rp = _mcc_residual(xp, p_tr, q_tr, pc_old, e_old, params)
        for r in range(4):
            jac[r][c] = (rp[r] - base[r]) / step
    return jac


def _initial_plastic_guess(p_tr: float, q_tr: float, pc_old: float,
                           params: MCCParams) -> List[float]:
    f_tr = yield_function(p_tr, q_tr, pc_old, params)
    denom = max(params.bulk * params.m * params.m + 6.0 * params.shear, 1.0)
    dl = max(0.0, f_tr / (denom * max(abs(p_tr) + abs(q_tr) + abs(pc_old), 1.0)))
    dl = min(dl, 1.0e-2)
    q = max(0.0, q_tr / (1.0 + 6.0 * params.shear * dl))
    p = max(params.tension_cutoff, min(max(p_tr, params.tension_cutoff), pc_old * 0.999))
    pc = max(pc_old, p + params.tension_cutoff)
    return [p, q, pc, max(dl, 1.0e-12)]


def return_mapping(trial_stress: Matrix, old: MCCState, params: MCCParams) -> MCCState:
    p_tr, q_tr, _ = invariants(trial_stress)
    if p_tr <= params.tension_cutoff:
        failed = old.copy()
        failed.stress = trial_stress
        failed.return_status = "tension_cutoff"
        failed.residual = p_tr - params.tension_cutoff
        return failed

    f_tr = yield_function(p_tr, q_tr, old.pc, params)
    scale = max(q_tr * q_tr + params.m * params.m * p_tr * max(old.pc, p_tr), 1.0)
    if f_tr <= params.return_tolerance * scale:
        elastic = old.copy()
        elastic.stress = trial_stress
        elastic.yield_flag = 0
        elastic.return_status = "elastic"
        elastic.iterations = 0
        elastic.residual = f_tr
        elastic.plastic_multiplier = 0.0
        return elastic

    x = _initial_plastic_guess(p_tr, q_tr, old.pc, params)
    residual = _mcc_residual(x, p_tr, q_tr, old.pc, old.e, params)
    best_norm = _norm(residual)
    status = "max_iter"
    iterations = 0
    for it in range(1, params.return_max_iter + 1):
        iterations = it
        try:
            jac = _numeric_jacobian(x, p_tr, q_tr, old.pc, old.e, params)
            dx = _solve_linear4(jac, [-r for r in residual])
        except (ZeroDivisionError, OverflowError, ValueError):
            status = "jacobian_failure"
            break

        accepted = False
        for ls in range(params.max_line_search + 1):
            fac = 0.5 ** ls
            cand = [x[i] + fac * dx[i] for i in range(4)]
            if cand[0] <= params.tension_cutoff or cand[1] < 0.0 or cand[2] <= params.tension_cutoff or cand[3] < 0.0:
                continue
            if not all(isfinite(v) for v in cand):
                continue
            rc = _mcc_residual(cand, p_tr, q_tr, old.pc, old.e, params)
            nc = _norm(rc)
            if isfinite(nc) and nc <= best_norm * (1.0 - 1.0e-4 * fac) + 1.0e-18:
                x = cand
                residual = rc
                best_norm = nc
                accepted = True
                break
        if not accepted:
            status = "line_search_failure"
            break

        norm_scale = max(abs(x[2]) * params.m * params.m * max(abs(x[0]), 1.0), 1.0)
        if best_norm <= params.return_tolerance * norm_scale:
            status = "plastic_converged"
            break

    p, q, pc, dl = x
    p_tr_final, q_tr_final, _ = invariants(trial_stress)
    dev_tr = deviator(trial_stress)
    if q_tr_final > 1.0e-14:
        dev_new = mat_scale(dev_tr, q / q_tr_final)
    else:
        dev_new = zeros()
    new_stress = mat_add(eye(p), dev_new)

    a = params.m * params.m
    depv = dl * a * (2.0 * p - pc)
    depeq = abs(dl) * sqrt((a * (2.0 * p - pc)) ** 2 + (2.0 * q) ** 2)

    new = old.copy()
    new.stress = new_stress
    new.pc = pc
    new.eps_p_v += depv
    new.eps_p_eq += depeq
    new.plastic_multiplier = dl
    new.yield_flag = 1
    new.return_status = status
    new.iterations = iterations
    new.residual = yield_function(p, q, pc, params)
    return new


def update_state(old: MCCState, strain_inc: Matrix, params: MCCParams) -> MCCState:
    params.validate()
    trial = elastic_predictor(old.stress, strain_inc, params)
    new = return_mapping(trial, old, params)
    eps_v = trace(strain_inc)
    new.e = max(-0.999, old.e - (1.0 + old.e) * eps_v)
    return new


def make_initial_state(p0: float, params: MCCParams, q0: float = 0.0) -> MCCState:
    if q0 == 0.0:
        stress = eye(p0)
    else:
        # Axisymmetric compression-positive stress with requested q at mean p.
        stress = principal_diag(p0 + 2.0 * q0 / 3.0, p0 - q0 / 3.0, p0 - q0 / 3.0)
    return MCCState(stress=stress, pc=params.pc0, e=params.e0)


def row_from_state(step: int, path: str, strain_inc: Matrix, state: MCCState,
                   pore_pressure_proxy: float = 0.0) -> MCCStep:
    p, q, _ = invariants(state.stress)
    sigmac = to_sigmac_negative_compression(state.stress)
    f = yield_function(p, q, state.pc, MCCParams())  # overwritten by caller if params differ in helper below.
    return MCCStep(
        step=step,
        path=path,
        eps_xx=strain_inc[0][0],
        eps_yy=strain_inc[1][1],
        eps_zz=strain_inc[2][2],
        eps_xy=strain_inc[0][1],
        eps_yz=strain_inc[1][2],
        eps_xz=strain_inc[0][2],
        eps_v=trace(strain_inc),
        stress_xx=state.stress[0][0],
        stress_yy=state.stress[1][1],
        stress_zz=state.stress[2][2],
        stress_xy=state.stress[0][1],
        stress_yz=state.stress[1][2],
        stress_xz=state.stress[0][2],
        sigmac_xx=sigmac[0][0],
        sigmac_yy=sigmac[1][1],
        sigmac_zz=sigmac[2][2],
        p=p,
        q=q,
        pc=state.pc,
        e=state.e,
        eps_p_v=state.eps_p_v,
        eps_p_eq=state.eps_p_eq,
        plastic_multiplier=state.plastic_multiplier,
        yield_f=f,
        return_status=state.return_status,
        yield_flag=state.yield_flag,
        iterations=state.iterations,
        residual=state.residual,
        pore_pressure_proxy=pore_pressure_proxy,
    )


def record_step(step: int, path: str, strain_inc: Matrix, state: MCCState,
                params: MCCParams, pore_pressure_proxy: float = 0.0) -> Dict[str, float | int | str]:
    row = row_from_state(step, path, strain_inc, state, pore_pressure_proxy).as_dict()
    p = float(row["p"])
    q = float(row["q"])
    pc = float(row["pc"])
    yf = yield_function(p, q, pc, params)
    scale = max(q * q + params.m * params.m * p * max(pc, p), 1.0)
    row["yield_f"] = yf
    row["yield_f_normalized"] = abs(yf) / scale
    return row


def log_p(value: float) -> float:
    return log(max(value, 1.0e-30))
