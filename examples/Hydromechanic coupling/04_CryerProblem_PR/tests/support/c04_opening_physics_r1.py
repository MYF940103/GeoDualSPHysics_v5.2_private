"""Ideal early radial pressure and geometry-only mass checks on the retained ideal pressure jump."""
import hashlib
import json
from pathlib import Path

import numpy as np
from c04_m0_radial_inertia_r1 import invert_boundary, material, read_reference, TESTS, XML
from cryer_tet_mechanics import TetMechanics


def main():
    receipt = TESTS / "logs/c04_opening_physics_r1.json"
    if receipt.exists():
        raise FileExistsError(receipt)
    ref = read_reference()
    rho, water, _ = material(XML)
    b, d = ref.kappa * (rho - water), ref.kappa * rho
    ideal = []
    for after in (1, 64, 128):
        t = after * 2.**-19
        for shell in (1, 17, 18):
            r = .0025 * shell
            row = dict(steps_after_drain=after, tau_s=t, material_shell=shell)
            for label, beta, delta in (("quasi", 0., 0.), ("dynamic", b, d)):
                v = [invert_boundary(ref, r, t, beta, delta, n) for n in (32, 48)]
                assert abs(v[0] - v[1]) < 1e-4
                row[label + "_Pa"] = v[1]
                row[label + "_degrees32minus48_Pa"] = v[0] - v[1]
            ideal.append(row)

    # Geometric P1 node volume, normalized independently on each initial shell.
    # This is an algebraic control only; forces, storage and physical parameters
    # remain those of the original weak calculation.
    geom = TESTS / "outputs/cryer_tet_reference_r1.npz"
    m = TetMechanics(geom)
    shell = m.shells
    total = np.bincount(shell, weights=m.mass)[1:]
    volume = np.bincount(shell, weights=m.volume)[1:]
    mass = m.volume * (total / volume)[shell - 1]
    assert np.all(mass > 0) and np.max(abs(np.bincount(shell, weights=mass)[1:] - total)) < 1e-12
    external = m.surface_force(10000)
    forces = {"surface_traction": external,
              "net": m.pressure_force(np.where(shell == 20, 0., 10000.)) + external}
    unit = m.x / np.linalg.norm(m.x, axis=1)[:, None]
    controls = []
    for name, inertia in (("native", m.mass), ("shell_normalized_P1_volume", mass)):
        for term, force in forces.items():
            a = force / inertia[:, None]
            radial = np.einsum("ij,ij->i", a, unit)
            tangent = a - radial[:, None]*unit
            for j in (19, 20):
                sel = shell == j
                controls.append(dict(mass=name, force=term, shell=j,
                    radial_mean_m_s2=float(radial[sel].mean()), radial_std_m_s2=float(radial[sel].std()),
                    tangent_rms_m_s2=float(np.sqrt(np.mean(np.sum(tangent[sel]**2, axis=1))))))
    record = dict(ideal_M0_drained_radial_pressures=ideal, tests="Independent 32- and 48-degree de Hoog boundary inversions",
                  actual_force_mass_controls=controls, shell_mass_over_geometric_volume_kg_m3=(total/volume).tolist(),
                  mass_total_kg=float(sum(mass)), native_mass_total_kg=float(sum(m.mass)),
                  shell_normalized_mass_over_native_range=[float(min(mass/m.mass)),float(max(mass/m.mass))],
                  source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                 (geom, XML, Path(__file__), Path(__file__).with_name("c04_m0_radial_inertia_r1.py"))},
                  scope="Ideal, suddenly drained spherically symmetric homogeneous M0 sphere and fixed saved geometry static force; no new coupled trajectory.")
    with receipt.open("x", encoding="utf8") as f:
        json.dump(record, f, indent=2, allow_nan=False)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
