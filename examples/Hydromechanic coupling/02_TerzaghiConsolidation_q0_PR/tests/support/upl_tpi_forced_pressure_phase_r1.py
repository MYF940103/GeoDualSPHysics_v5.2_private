"""Forced pressure-row frequency response at fixed, nominal C02 Fourier symbols."""
import csv
import cmath
import json
import math
from pathlib import Path

T = Path(__file__).resolve().parents[1]
NAME = "upl_tpi_forced_pressure_phase_r1"


def response(alpha, iterations, m, omega, dt):
    # For frozen endpoint mechanics, a complete row maps (p-p*) to m*(p-p*).
    # Manufacture p*(t)=cos(omega*t). This is a prescribed pressure forcing;
    # neither the acceleration nor the strain is advanced in this focused test.
    residual = m**iterations
    new_weight = -math.expm1(iterations*math.log(m))
    z = cmath.exp(1j*omega*dt)
    difference = complex(2*math.sin(.5*omega*dt)**2, math.sin(omega*dt))  # 1-z^-1
    # Equivalent to (1-residual)/[1-residual*((1+alpha)/z-alpha/z²)].
    H = new_weight / (new_weight + residual*difference*(1-alpha/z))
    q_prev = (H / z).real
    q_now = H.real
    maximum = 0.
    # Initialize in the exact manufactured periodic steady state to isolate the
    # time scheme from a cold start. Recur independently through each separate round.
    for step in range(1,257):
        exact = math.cos(step*omega*dt)
        q = q_now + alpha*(q_now-q_prev)
        for _ in range(iterations):
            q = q + (1-m)*(exact-q)
        q_prev, q_now = q_now, q
        maximum = max(maximum, abs(q-(H*z**step).real))
    if maximum > 2e-11:
        raise ValueError("Independent causal recurrence differs from frequency response")
    return abs(H), -cmath.phase(H)/omega, abs(H-1.), maximum


def main():
    path=T/"figures"/(NAME+".csv")
    receipt=T/"logs"/(NAME+".check.json")
    if path.exists() or receipt.exists(): raise RuntimeError("Use existing review")
    old=T/"outputs/upl_tpi_case02_step_spectrum_r2"
    parameters=json.loads((old/"summary.json").read_text(encoding="utf-8-sig"))["parameters"]
    with (old/"nominal_modes.csv").open(encoding="utf-8-sig",newline="") as f:
        modes=list(csv.DictReader(f))
    rows=[]
    for which in (0,24):
        row=modes[which]
        assert int(row["mode"])==which and row["actual_C02_boundary_or_full_Rgamma_symbol"]=="False"
        q=float(row["q_P1_common_symbol_m_inv"]); mu=float(row["mu_normalized_neighbor_symbol"])
        ratio=parameters["rhow_kg_m3"]/parameters["rho_kg_m3"]
        m=1-(1-ratio)*(1-mu)
        # The undamped M0 slow eigenvalue in the same symbol model sets the frequency,
        # avoiding any adjustment to force, pressure or time to match native histories.
        d=parameters["rho_kg_m3"]-parameters["rhow_kg_m3"]
        decay=parameters["gamma_dynamic_Pa_m"]/(parameters["k_loaded_float_m_s"]*d)
        frequency=(2*parameters["Mc_loaded_double_Pa"]*q*q/d/
                   (decay+math.sqrt(decay*decay-4*parameters["Mc_loaded_double_Pa"]*q*q/d)))
        for label,alpha,iterations in (("C_lagged_1",0.,1),("B_extrapolated_1",.5,1),
                                       ("equal_work_lagged_3",0.,3),("B_P3",.5,3)):
            older=None
            for refinement in range(6):
                dt=parameters["dt_candidate_1_s"]/2**refinement
                amplitude,lag,err,forward_error=response(alpha,iterations,m,frequency,dt)
                order=math.log2(older/err) if older is not None else None
                rows.append(dict(symbol=which,q_m_inv=q,mu=mu,m=m,omega_s_inv=frequency,method=label,
                    alpha=alpha,complete_rows=iterations,refinement=refinement,dt_s=dt,
                    amplitude_ratio=amplitude,relative_amplitude_error=amplitude-1.,
                    phase_lag_s=lag,complex_response_error=err,observed_refinement_order=order,
                    zero_frequency_lag_s=dt*(1-alpha)*m**iterations/(1-m**iterations),
                    independent_recurrence_error=forward_error))
                older=err
    with path.open("x",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with receipt.open("x",encoding="utf-8") as f:
        json.dump(dict(rows=len(rows),nominal_modes=[0,24],pressure_only_linear_forcing=True,
            pressures_at_physical_Cryer_modes=False,p3_or_coupled_physical_acceptance=False,
            maximum_recurrence_error=max(r["independent_recurrence_error"] for r in rows),
            base_dt=[r for r in rows if r["refinement"]==0],
            finest_order=[dict(method=r["method"],symbol=r["symbol"],order=r["observed_refinement_order"])
                          for r in rows if r["refinement"]==5]),f,indent=2,allow_nan=False)
        f.write("\n")


if __name__=="__main__":main()
