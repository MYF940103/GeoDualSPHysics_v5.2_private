"""Independent regular spherical modes for the two-field Cryer harmonic reference."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import spherical_in

from cryer_coupled_shell_modes import DAMP, HYD, LAM, LONG, MU, N0, PREFIX, R, RHO, RHOW, T


def radial_columns(k, x):
    """Normalized strain and its regular radial displacement integral."""
    if abs(k) < 1.e-8:
        return 1 + (k*x)**2/6, x/3 + k*k*x**3/30
    return spherical_in(0,k*x), spherical_in(1,k*x)/k


def sphere_modes(frequency, storage, damping):
    s=2j*np.pi*frequency
    x=np.arange(1,21)/20
    # E=LONG*div(u), P=p. The two radial scalar Laplacians share eigenmodes.
    inertia=RHO*R**2*s*(s+damping)/LONG
    drainage=R**2*s*(1/HYD-RHOW*s)/LONG
    capacity=R**2*storage*s/HYD
    eig,modes=np.linalg.eig([[inertia+drainage,capacity],[drainage,capacity]])
    e,p,u=[np.empty((20,2),complex) for _ in range(3)]
    for n in range(2):
        f,g=radial_columns(np.sqrt(eig[n]),x)
        e[:,n]=modes[0,n]*f
        p[:,n]=modes[1,n]*f
        u[:,n]=modes[0,n]*g
    weight=np.linalg.solve(np.array([p[-1],e[-1]-4*MU/LONG*u[-1]-p[-1]]),[0,-1])
    return R/LONG*(u@weight),p@weight


def check(value,bound,label):
    if not (np.isfinite(value) and value<bound):
        raise ValueError(f"{label}: {value} exceeds {bound}")
    return float(value)


def main():
    table=pd.read_csv(T/"figures"/(PREFIX+"_shells.csv"))
    target=T/"logs"/(PREFIX+".reference.json")
    if target.exists():
        raise FileExistsError(target)
    max_p=max_u=max_identity=0.
    x=np.arange(1,21)/20
    for (model,frequency),group in table.groupby(["model","frequency_Hz"]):
        if not np.array_equal(group.shell,np.arange(1,21)):
            raise ValueError("Missing interior or drained radii")
        u,p=sphere_modes(frequency,0 if model=="M0" else N0/2e8,DAMP)
        orig_p=group.continuum_p_real+1j*group.continuum_p_imag
        orig_u=group.continuum_u_real_m_per_Pa+1j*group.continuum_u_imag_m_per_Pa
        max_p=max(max_p,np.max(abs(p-orig_p)))
        max_u=max(max_u,np.max(abs(u-orig_u)))
        if model=="M0":
            # Independent zero-damping map from dynamic transfer to quasistatic M=0.
            s=2j*np.pi*frequency
            s_q=s*(1+HYD*(RHO-RHOW)*s)
            k=R*np.sqrt(s_q/(HYD*LONG))
            f,g=radial_columns(k,x)
            transfer_q=(f[-1]-f)/(f[-1]-4*MU/LONG*g[-1])
            pred=(1-HYD*RHOW*s)/(1+HYD*(RHO-RHOW)*s)*transfer_q
            max_identity=max(max_identity,np.max(abs(sphere_modes(frequency,0,0)[1]-pred)))
    bulk=LAM+2*MU/3
    low_slope=R**2*(1-x*x)/(6*bulk*HYD)
    static_u=-R*x/(3*bulk)
    # At small positive frequency the first pressure derivative and drained displacement are known.
    slow_hz=1.e-5
    slow_s=2j*np.pi*slow_hz
    u,p=sphere_modes(slow_hz,0,DAMP)
    slow_p=np.max(abs(p/slow_s-low_slope))/np.max(abs(low_slope))
    slow_u=np.max(abs(u-static_u))/np.max(abs(static_u))
    results=dict(
        checked_model_frequency_shell_samples=len(table),
        maximum_bvp_pressure_difference=check(max_p,5.e-8,"collocation versus regular modes pressure"),
        maximum_bvp_displacement_difference_m_per_Pa=check(max_u,2.e-14,"collocation versus regular modes displacement"),
        m0_undamped_dynamic_quasistatic_transfer_identity=check(max_identity,1.e-11,"undamped transfer"),
        static_limit_frequency_hz=slow_hz,
        relative_static_displacement_difference=check(slow_u,5.e-5,"static displacement"),
        relative_low_frequency_pressure_slope_difference=check(slow_p,5.e-5,"static pressure slope"))
    target.write_text(json.dumps({"passed":True,**results},indent=2)+"\n",encoding="utf-8")
    print(json.dumps(results))


if __name__=="__main__":
    main()
