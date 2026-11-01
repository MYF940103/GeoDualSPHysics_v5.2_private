"""P0 algebra/units checks only: no coupled solver or production state updates."""
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parents[1]
REPO = Path(__file__).resolve().parents[5]
OUT = TESTS / "logs" / "upl_p0_closure_r1.check.json"
TOL = 5e-13


def state(j, n0=0.3, rho0=2000.0, rhow=1000.0, mass=0.2):
    if not (0 < n0 < 1 and j > 1-n0 and rho0 > n0*rhow and rhow > 0 and mass > 0):
        raise ValueError("outside saturated incompressible-grain closure")
    v0 = mass/rho0
    rhos = (rho0-n0*rhow)/(1-n0)
    n = 1-(1-n0)/j
    return dict(J=j, n=n, V=v0*j, V0=v0, rho_s=rhos,
                rho_t=(1-n)*rhos+n*rhow, solid_mass=(1-n)*rhos*v0*j)


def relative(x, ref):
    return abs(x-ref)/max(1.0, abs(ref))


def run():
    if OUT.exists():
        raise FileExistsError(f"preserve retained receipt: {OUT}")
    checks = []
    rows = []
    for j in (0.75, 0.9, 1.0, 1.1, 1.5):
        s = state(j)
        rows.append(s)
        checks.append((f"solid_fraction_J_{j}", abs((1-s['n'])*j-0.7) <= TOL))
        checks.append((f"solid_mass_{j}", relative(s['solid_mass'], 0.17) <= TOL))
        # Reference-water inertia is not the constant original mixture mass.
        checks.append((f"inertia_positive_{j}", s['rho_t'] > 0))
        kw = 2e8
        p = -kw*math.log(s['n']*j/0.3)
        rho_eos = 1000*math.exp(p/kw)
        checks.append((f"undrained_EOS_mass_reference_{j}",
                       relative(rho_eos*s['n']*j, 300) <= TOL))
    checks.append(("initial_inertia_identity", relative(state(1)['rho_t'], 2000) <= TOL))
    # Hydrostatic and uniformly accelerated equilibrium: grad p=rhow*(g-a_s).
    for acceleration in ((0, 0, 0), (1.2, -0.4, 3.0)):
        gravity = (0, 0, -9.80665)
        gradp = [1000*(g-a) for g, a in zip(gravity, acceleration)]
        flux = [-1e-4/(1000*9.80665)*(gp-1000*(g-a))
                for gp, g, a in zip(gradp, gravity, acceleration)]
        checks.append((f"accelerated_equilibrium_flux_{acceleration}", max(map(abs, flux)) <= 1e-20))
    # No volumetric strain (rigid motion or isochoric shear) leaves this closure unchanged.
    checks.append(("zero_theta_null", state(1*(1+0.0*0.01)) == state(1)))
    for args in ((0.7,), (1, 0), (1, 1), (1, 0.3, 200)):
        try:
            state(*args)
        except ValueError:
            checks.append((f"invalid_state_rejected_{args}", True))
        else:
            checks.append((f"invalid_state_rejected_{args}", False))
    count, increment = 10000, 1e-12
    jd = jf = 1.0
    for _ in range(count):
        jd += increment
        jf = struct.unpack("f", struct.pack("f", jf+increment))[0]
    rounding_budget = 4*count*sys.float_info.epsilon
    checks.append(("double_microincrement_budget", abs(jd-(1+count*increment)) <= rounding_budget))
    checks.append(("float_microincrement_loss_observed", jf == 1.0 and jd > 1.0))
    sources = ["src/source/JSphCpu.cpp", "src/source/JSphCpuSingle.cpp",
               "src/source/JSphHourglassCpu.cpp", "src/source/DualSphDef.h",
               "examples/Hydromechanic coupling/validation/upl_p0_ledger_r1.md"]
    receipts = []
    for name in sources:
        data = (REPO/name).read_bytes()
        receipts.append(dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    result = dict(stage="P0_algebra_only", passed=all(v for _, v in checks),
                  physical_acceptance=False, production_changed=False,
                  switch_implemented=False, invariants_relative_or_absolute_tolerance=TOL,
                  checks=[dict(name=n, passed=v) for n, v in checks], states=rows,
                  microincrement=dict(count=count, increment=increment, double_J=jd,
                                      float_J=jf, binary64_absolute_budget=rounding_budget),
                  sources=receipts,
                  limitations="Algebra only; no coupled force, state sorting, integrator, wall flux, GPU or physical mass-conservation acceptance")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=True, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(dict(passed=result['passed'], checks=len(checks), receipt=str(OUT)), ensure_ascii=True))
    return 0 if result['passed'] else 1


if __name__ == "__main__":
    raise SystemExit(run())
