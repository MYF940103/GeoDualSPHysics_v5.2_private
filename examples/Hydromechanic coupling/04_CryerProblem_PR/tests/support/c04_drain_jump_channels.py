"""Shell-resolved force and hydraulic residual channels on two frozen C04 operators."""
import hashlib
import json
import argparse
from pathlib import Path

import numpy as np
from c04_p3_pressure_component import CACHE
from cryer_coupled_shell_modes import DAMP, DT, HYD, RHOW, T
from cryer_tet_av_reference import artificial_viscosity
from cryer_tet_darcy_spectrum import assemble
from cryer_tet_mechanics import TetMechanics
from cryer_voronoi_window import INTERIOR, SURFACE, direct_flux, face_matrices

TAG = "c04_drain_jump_channels"
GEOM = T / "outputs/cryer_tet_reference_r1.npz"


def sha(path):
    with path.open("rb") as inp:
        return hashlib.file_digest(inp, "sha256").hexdigest()


def norm_rms(x):
    return float(np.sqrt(np.mean(x * x)))


class Shells:
    def __init__(self, m):
        self.s = m.shells
        self.count = np.bincount(self.s, minlength=21)
        self.unit = m.x / np.linalg.norm(m.x, axis=1)[:, None]
        self.groups = {str(i): self.s == i for i in range(1, 21)}
        self.groups["free"] = self.s < 20
        self.groups["near_free_17_19"] = (self.s >= 17) & (self.s < 20)

    def mean_field(self, y):
        sums = np.bincount(self.s, weights=y, minlength=21)
        return (sums[1:] / self.count[1:])[self.s - 1]

    def scalar(self, y):
        angular = y - self.mean_field(y)
        return {name: dict(mean=float(y[mask].mean()), rms=norm_rms(y[mask]),
                           angular_rms=norm_rms(angular[mask])) for name, mask in self.groups.items()}

    def radial_model(self, a):
        radial = np.einsum("ij,ij->i", self.unit, a)
        return self.mean_field(radial)[:, None] * self.unit

    def vector(self, a):
        radial = np.einsum("ij,ij->i", self.unit, a)
        tangent = a - radial[:, None] * self.unit
        radial_fluc = radial - self.mean_field(radial)
        tangent2 = np.einsum("ij,ij->i", tangent, tangent)
        return {name: dict(mean_outward=float(radial[mask].mean()), radial_angular_rms=norm_rms(radial_fluc[mask]),
                           tangent_vector_rms=float(np.sqrt(tangent2[mask].mean())),
                           angular_vector_rms=float(np.sqrt((radial_fluc[mask]**2 + tangent2[mask]).mean())))
                for name, mask in self.groups.items()}


def acceleration(m, p, stress, v, pairs):
    a = dict(effective=m.internal_stress(stress) / m.mass[:, None],
             pressure=m.pressure_force(p) / m.mass[:, None], traction=m.surface_force(10000.) / m.mass[:, None])
    a["mechanical"] = a["effective"] + a["pressure"] + a["traction"]
    if np.any(v):
        av, _ = artificial_viscosity(m.x, m.native_volume, m.mass / m.native_volume, v, pairs)
        a["AV_and_damping"] = av / m.mass[:, None] - DAMP * v
    else:
        a["AV_and_damping"] = np.zeros_like(v)
    a["posterior"] = a["mechanical"] + a["AV_and_damping"]
    return a


def pressure_channels(m, shells, matrices, p, v, acc):
    stiff, flux, denominator = matrices
    def rhoF(a):
        return RHOW * sum(F @ a[:, k] for k, F in enumerate(flux))
    kp = stiff @ p
    # These paired controls preserve shell membership and the actual operators.
    kp_radial = stiff @ shells.mean_field(p)
    fa = rhoF(acc["posterior"])
    ar = shells.radial_model(acc["posterior"])
    fa_radial = rhoF(ar)
    theta_term = m.volume * m.divergence(v) / HYD
    fields = dict(Kp=kp, Kp_radial=kp_radial, Kp_angular=kp-kp_radial,
                  rhoFa=fa, rhoFa_radial=fa_radial, rhoFa_angular=fa-fa_radial,
                  rhoFa_effective=rhoF(acc["effective"]), rhoFa_pressure=rhoF(acc["pressure"]),
                  rhoFa_traction=rhoF(acc["traction"]), rhoFa_AV_damping=rhoF(acc["AV_and_damping"]),
                  hydraulic_sum=kp+fa, volume_source=theta_term, residual=kp+fa+theta_term)
    assert abs(fa-fields["rhoFa_effective"]-fields["rhoFa_pressure"]-fields["rhoFa_traction"]-fields["rhoFa_AV_damping"]).max()<1e-9
    out = {}
    for kind, field in fields.items():
        out[kind] = dict(integrated_Pa_m=shells.scalar(field), rate_per_s=shells.scalar(field*HYD/m.volume),
                         one_frozen_correction_Pa=shells.scalar(-field/denominator))
    # Covariance measures cancellation of shell-demeaned pressure and inertia terms.
    kk = kp*HYD/m.volume
    aa = fa*HYD/m.volume
    kk -= shells.mean_field(kk)
    aa -= shells.mean_field(aa)
    out["rate_Kp_rhoFa_angular_correlation"] = {}
    for g, mask in shells.groups.items():
        k, a = kk[mask], aa[mask]
        denom = np.linalg.norm(k)*np.linalg.norm(a)
        out["rate_Kp_rhoFa_angular_correlation"][g] = float(k@a/denom) if denom > 1e-22 else None
    return out


def plot(path, records):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(10.8, 4.2), layout="constrained")
    shells = np.arange(16, 21)
    for case, color, label in (("ideal", "#258448", "Ideal drain step"),
                               ("weak_4097", "#315c96", "Weak P1, step 4097"),
                               ("face_4097", "#a25530", "Face flux, step 4097")):
        rows = records[case]["acceleration_m_s2"]["mechanical"]
        axs[0].plot(shells, [rows[str(s)]["angular_vector_rms"] for s in shells], "o-", color=color, label=label)
    axs[0].set(ylabel="Angular acceleration RMS (m/s²)", title="Common mechanics", xlabel="Material shell", xticks=shells)
    h = records["ideal"]["hydraulic"]
    shells = np.arange(16,20)
    for op, color in (("P1", "#315c96"), ("face", "#a25530")):
        for key, style, label in (("Kp", "o-", "Kp"), ("rhoFa", "s--", "ρFa")):
            vals = [h[op][key]["rate_per_s"][str(s)]["angular_rms"] for s in shells]
            axs[1].plot(shells, vals, style, color=color, label=f"{op} {label}")
    axs[1].set(ylabel="Shell-demeaned rate RMS (s⁻¹)", title="Ideal drain step, free rows", xlabel="Material shell", xticks=shells)
    for ax in axs:
        ax.grid(alpha=.2)
        ax.legend(fontsize=8)
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    report = T/"logs"/(TAG+".json")
    figure = T/"figures"/(TAG+".png")
    if report.exists() or figure.exists():
        raise FileExistsError("Existing drain-jump evidence")
    m = TetMechanics(GEOM)
    shells = Shells(m)
    assert m.n == 37173 and len(m.surface) == 5153 and shells.count[1] == 18
    with np.load(CACHE) as z:
        assert np.array_equal(z["ids"], m.ids)
        i = np.repeat(np.arange(m.n, dtype=np.int32), np.diff(z["indptr"]))
        j = z["indices"]
        pairs = np.column_stack((i[i<j], j[i<j]))
    assert len(pairs) == 3392720
    stiffness = assemble(GEOM)[-1]
    i, j, trans, areas, face_stiff, F = face_matrices(m)
    operators = {}
    P = [H.multiply((1/m.mass)[:,None]).tocsr() for H in m.HT]
    velocity_jac = (DT/HYD)*sum(D@Q for D,Q in zip(m.D,P)).multiply(m.volume[:,None])
    for key, K, flux in (("P1", stiffness, m.HT), ("face", face_stiff, F)):
        jac = K + RHOW*(1-DAMP*DT)*sum(H@Q for H,Q in zip(flux,P)) + velocity_jac
        row = np.asarray(abs(jac).sum(axis=1)).ravel()
        assert row.min() > 0 and np.isfinite(row).all()
        operators[key] = (K, flux, row)
    initial = np.full(m.n, 10000.)
    equilibrium = (m.pressure_force(initial) + m.surface_force(10000.)) / m.mass[:,None]
    assert abs(equilibrium).max() < 1e-10
    initial[m.surface] = 0.
    fields = dict(ideal=(initial, np.zeros((m.n,6)), np.zeros_like(m.x)))
    sources = {}
    for key, folder in (("weak_4097","cryer_weak_open_r1"), ("face_4097","cryer_voronoi_window_open_r1")):
        path = T/"outputs"/folder/"state_4097.npz"
        with np.load(path) as z:
            assert int(z["step"])==4097 and np.array_equal(z["ids"],m.ids) and np.all(z["p"][m.surface]==0)
            fields[key] = tuple(z[k] for k in ("p","stress","v"))
        sources[key] = dict(file=str(path.relative_to(T)), sha256=sha(path))
    records = {}
    for key,(p,stress,v) in fields.items():
        acc = acceleration(m,p,stress,v,pairs)
        hyd = {op: pressure_channels(m,shells,mats,p,v,acc) for op,mats in operators.items()}
        check = direct_flux(p,acc["posterior"],i,j,trans,areas)
        p1 = face_stiff@p+RHOW*sum(A @ acc["posterior"][:,k] for k,A in enumerate(F))
        assert abs(check-p1).max() < 1e-9
        records[key] = dict(acceleration_m_s2={k:shells.vector(a) for k,a in acc.items()},
                            pressure_Pa=shells.scalar(p), hydraulic=hyd)
    plot(figure, records)
    inputs = [GEOM,INTERIOR,SURFACE,CACHE]
    data = dict(script_sha256=sha(Path(__file__)), geometry_sha256={str(p.relative_to(T)):sha(p) for p in inputs},
                state_inputs=sources, native_mass_kg=float(m.mass.sum()), initial_volume_weight_m3=float(m.volume.sum()),
                shell_counts=shells.count[1:].tolist(), closed_uniform_pressure_plus_face_max_m_s2=float(abs(equilibrium).max()),
                sign="Radial acceleration positive outward. Hydraulic residual Kp + rho Fa + beta W div v. One frozen pressure correction equals minus each component divided by its full operator row sum; surface rows are prescribed and never applied.",
                units="Integrated rows Pa m. Rates multiply by (k/gamma)/W, with common P1 work volume W used in both actual solvers. Angular RMS removes each shell's own mean; tangent magnitude is the Euclidean norm, with zero solid-body tangential base.",
                scope="Same fixed reference geometry and native mass for both operators; no solver or time advance. Ideal input has zero stress/velocity. Step 4097 fields are committed endpoint values; artificial viscosity here uses saved velocity, not unavailable stage-frozen velocity. Shell-mean controls measure spatial mapping; a frozen correction is not an actual substep.", records=records)
    with report.open("x",encoding="utf8") as stream:
        json.dump(data,stream,indent=1,allow_nan=False)
    print(report)


def volume_control():
    # Test why an orthogonal pure-diffusion patch and the coupled volume-scaled
    # pressure term give different shell scatter for the same imposed pressure.
    out = T/"logs"/(TAG+"_volume.json")
    if out.exists():
        raise FileExistsError(out)
    prior = T/"logs"/(TAG+".json")
    recorded = json.loads(prior.read_text())["records"]
    m = TetMechanics(GEOM)
    shells = Shells(m)
    with np.load(INTERIOR) as inner, np.load(SURFACE) as wall:
        volume = np.zeros(m.n)
        volume[inner["interior_slots"]] = inner["interior_volume_m3"]
        volume[wall["surface_slots"]] = wall["volume_m3"]
    assert volume.min() > 0 and abs(volume.sum()-m.volume.sum()) < 1e-15
    i,j,trans,normal,K,F = face_matrices(m)
    ratio = volume / m.volume
    ideal = np.full(m.n, 1e4)
    ideal[m.surface] = 0
    pressures = {"ideal":ideal}
    for key, folder in (("weak_4097","cryer_weak_open_r1"), ("face_4097","cryer_voronoi_window_open_r1")):
        with np.load(T/"outputs"/folder/"state_4097.npz") as z:
            assert np.array_equal(z["ids"],m.ids)
            pressures[key] = z["p"]
    result = {}
    for key,p in pressures.items():
        # With h=HYD*Kp/Vvor, the actual common-W rate is exactly r*h
        # apart from rounding. Split it at each shell's own mean h.
        natural = HYD*(K@p)/volume
        actual = HYD*(K@p)/m.volume
        mean_h = shells.mean_field(natural)
        components = {"face_volume_rate":natural, "common_W_rate":actual,
                      "ratio_times_shell_mean":ratio*mean_h,
                      "ratio_times_within_shell_variation":ratio*(natural-mean_h)}
        assert abs(actual-components["ratio_times_shell_mean"]-components["ratio_times_within_shell_variation"]).max() < 1e-12
        result[key] = {name:shells.scalar(v) for name,v in components.items()}
        for sh in ("18","19","free"):
            expected=recorded[key]["hydraulic"]["face"]["Kp"]["rate_per_s"][sh]["angular_rms"]
            assert abs(result[key]["common_W_rate"][sh]["angular_rms"]-expected)<1e-12
    data = dict(script_sha256=sha(Path(__file__)), prior_receipt_sha256=sha(prior),
                Voronoi_over_P1_volume=shells.scalar(ratio), records=result,
                scope="Fixed pressure field and same integrated orthogonal face Kp for both divisions. Units 1/s. Diagnostic decomposition around each shell mean is additive before RMS. In both time steppers P1 W multiplies the mechanical volumetric rate; this comparison makes no change to either stepper.")
    with out.open("x",encoding="utf8") as f:
        json.dump(data,f,indent=1,allow_nan=False)
    print(out)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--volume-control",action="store_true")
    if parser.parse_args().volume_control:
        volume_control()
    else:
        main()
