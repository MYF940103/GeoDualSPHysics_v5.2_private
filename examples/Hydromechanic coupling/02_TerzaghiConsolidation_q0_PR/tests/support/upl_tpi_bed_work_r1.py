"""Compare a plane normal finite-volume work pair with the saved C02 material fields."""
import json
import subprocess
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from upl_tpi_bottom_cut_r1 import evaluate
from upl_tpi_bottom_patch_r1 import Bed, DATA, FIG, Q0, TEST, ordered, read, require

TAG = "upl_tpi_bed_work_r1"


def face_basis(nodes):
    """Wall plus four material centers; the upper cut is inside the real material."""
    faces = np.r_[nodes[0], .5*(nodes[1:-1]+nodes[2:])]
    basis = np.zeros((4, 5))
    basis[0, 0] = 1
    for face in range(1, 4):
        stencil = np.arange(face-1, face+2)
        for j in stencil:
            other = stencil[stencil != j]
            basis[face, j] = np.prod((faces[face]-nodes[other])/(nodes[j]-nodes[other]))
    return faces, basis


def material_basis(nodes, faces):
    # Map cell means at geometric centroids to material centers, exactly for a
    # linear gradient. The transpose map below acts on the stress quadrature.
    centers = .5*(faces[:-1]+faces[1:])
    recovery = np.zeros((3,3))
    for i, left in enumerate((0,0,1)):
        t = (nodes[i+1]-centers[left])/(centers[left+1]-centers[left])
        recovery[i, left:left+2] = (1-t,t)
    return recovery


def sample_column(z, velocity, total):
    faces, basis = face_basis(z)
    length = np.diff(faces)
    cell_gradient = np.diff(basis, axis=0)/length[:, None]
    recovery = material_basis(z,faces)
    gradient = recovery@cell_gradient
    # Positive geometric material integration weights ensure an exactly uniform
    # stress at the material points remains uniform on the faces' dual cells.
    point_weights = np.linalg.solve(recovery.T,length)
    require(np.all(point_weights>0), "Nonpositive material quadrature")
    # Force per unit cross-section. Assemble from face jumps without transposing
    # the gradient, then independently check the negative transpose and its work.
    def forces(stress):
        cell_stress = recovery.T@(point_weights*stress)/length
        jump = np.r_[cell_stress[0], np.diff(cell_stress), -cell_stress[-1]]
        return np.sum(basis*jump[:, None], axis=0)

    f = forces(total)
    force_error = np.max(abs(f + gradient.T@(point_weights*total)))
    trial = np.array([.31, -.23, .14, -.09, .37])
    nodal_power = f@trial
    cell_power = (point_weights*total)@(gradient@trial)
    scale = abs(f)@abs(trial) + abs(point_weights*total)@abs(gradient@trial)
    relative_power_error = abs(nodal_power+cell_power)/max(scale, 1.)
    # For a uniform stress include the upper cut's external traction and the
    # reaction at the physical wall in a separate static force balance.
    uniform = np.full(3, -Q0)
    patch = forces(uniform)
    uniform_closure = patch + uniform[-1]*basis[-1] - uniform[0]*basis[0]
    centroid = .5*(faces[:-1]+faces[1:])
    stress_linear = -Q0*(1+z[1:4])  # reference length 1 m; sigma(0)=-Q0
    # Quadratic displacement generates this linear plane-strain elastic stress.
    # Recovery of its known boundary traction is independent of velocity fitting.
    errors = {}
    for name, v, point_exact, cell_exact in (
        ("linear", z, np.ones(3), np.ones(3)),
        ("quadratic", z*z, 2*z[1:4], 2*centroid),
    ):
        cell = cell_gradient@v
        errors[name+"_cell_max"] = np.max(abs(cell-cell_exact))
        errors[name+"_point_max"] = np.max(abs(gradient@v-point_exact))
    d0, d1 = (gradient@velocity)[:2]
    spacing = z[2]-z[1]
    lower = (velocity[1]-velocity[0])/(z[1]-z[0])
    upper = (velocity[2]-velocity[1])/spacing
    return dict(lower_rate=lower, upper_rate=upper,
                lower_error=d0-.5*(z[1]-z[0])*(d1-d0)/spacing-lower,
                upper_error=.5*(d0+d1)-upper,
                work_rel=relative_power_error, transpose_Pa=force_error,
                uniform_closure_Pa=np.max(abs(uniform_closure)), uniform_bed_Pa=-patch[0],
                actual_bed_Pa=-f[0], linear_stress_bed_error_Pa=-forces(stress_linear)[0]-Q0,
                **errors)


def weighted_rms(time_s, y):
    delta = np.diff(time_s)
    return float(np.sqrt(delta@(.5*(y[1:]**2+y[:-1]**2))/delta.sum()))


def main():
    paths = [FIG/(TAG+".csv"), FIG/(TAG+".png"), TEST/"logs"/(TAG+".check.json")]
    require(not any(path.exists() for path in paths), "Preserve retained outputs")
    start = time.perf_counter()
    prior = pd.read_csv(FIG/"upl_tpi_bed_rate_r1_actual.csv", float_precision="round_trip")
    initial = read(DATA/"Part_0000.bi4")
    bed = Bed(initial)
    layer = np.rint(bed.z/.01-.5).astype(int)
    columns = np.stack([np.flatnonzero(layer == k)[np.argsort(bed.x[layer == k])]
                        for k in range(4)], axis=1)
    require(columns.shape == (10, 4) and np.max(np.ptp(bed.x[columns],axis=1)) < 1e-10,
            "Ten original material columns required")
    results = []
    for row in prior.itertuples():
        frame = read(DATA/f"Part_{row.part:04d}.bi4")
        require(frame["part"]["values"]["TimeStep"] == row.time_s, "Native clock mismatch")
        data = ordered(frame)
        velocity = frame["arrays"]["Vel"][np.argsort(frame["arrays"]["Idp"]), 2].astype(float)
        total = data["SigmaState_kk"][:, 2]-data["PorePress"].astype(float)
        values = pd.DataFrame([sample_column(np.r_[0., data["Posd"][ids, 2]],
                                             np.r_[0., velocity[ids]], total[ids[:3]])
                               for ids in columns])
        require(abs(values.lower_rate.mean()-row.bed_lower_half_rate_s1)<1e-10 and
                abs(values.upper_rate.mean()-row.bed_upper_interval_rate_s1)<1e-10,
                "Original material secants differ")
        cuts, patch, _ = evaluate(bed, data, layer, reflected=False, corrected=False)
        result = dict(part=row.part, time_s=row.time_s, native_bed_traction_Pa=cuts[0],
                      native_uniform_bed_Pa=patch[0], fv_bed_traction_Pa=values.actual_bed_Pa.mean(),
                      fv_uniform_bed_Pa=values.uniform_bed_Pa.mean(),
                      fv_linear_stress_bed_error_Pa=values.linear_stress_bed_error_Pa.mean(),
                      native_bottom_total_plus_load_Pa=total[columns[:,0]].mean()+Q0)
        for side, old in (("lower", "lower_half"), ("upper", "upper_rate")):
            for name, key in (("sph", "original"), ("quadratic_fit", "plane_quadratic")):
                result[f"{name}_{side}_error_s1"] = getattr(row, f"bed_{key}_{old}_error_s1")
            result[f"fv_{side}_error_s1"] = values[side+"_error"].mean()
        for key in ("work_rel","transpose_Pa","uniform_closure_Pa","linear_cell_max",
                    "linear_point_max","quadratic_cell_max","quadratic_point_max"):
            result[key] = values[key].max()
        results.append(result)
    table = pd.DataFrame(results)
    require(len(table)==26 and table.part.iloc[-1]==1652, "Existing frame set required")
    bounds = table[["work_rel","transpose_Pa","uniform_closure_Pa","linear_cell_max",
                    "linear_point_max","quadratic_cell_max","quadratic_point_max"]].max().to_dict()
    require(bounds["work_rel"]<1e-12 and bounds["transpose_Pa"]<1e-9 and
            bounds["uniform_closure_Pa"]<1e-9, "Independent force or power check failed")
    require(max(v for k,v in bounds.items() if k.endswith("_max"))<1e-12,
            "Manufactured velocity fields failed")
    late = table[table.time_s>=32.]
    metrics = {f"{scheme}_{side}": weighted_rms(late.time_s.to_numpy(),
                late[f"{scheme}_{side}_error_s1"].to_numpy())
               for scheme in ("sph","quadratic_fit","fv") for side in ("lower","upper")}
    end = table.iloc[-1]
    gains = {side: metrics["fv_"+side]<metrics["sph_"+side] for side in ("lower","upper")}
    end_force_preserved = abs(end.fv_bed_traction_Pa-Q0)<=abs(end.native_bed_traction_Pa-Q0)
    table.to_csv(paths[0], index=False)
    fig, ax = plt.subplots(1, 2, figsize=(9.5,3.7), layout="constrained")
    x = np.arange(2)
    for j,(scheme,label) in enumerate((("sph","Original SPH"),("quadratic_fit","Wall fit"),("fv","FV pair"))):
        ax[0].bar(x+.24*(j-1), [1e6*metrics[f"{scheme}_{side}"] for side in ("lower","upper")],
                  width=.24,label=label)
    ax[0].set_xticks(x,["Wall to first center","First to second center"])
    ax[0].set(ylabel="Rate residual RMS (10⁻⁶ s⁻¹)",title="Saved states from 32 s")
    ax[0].legend(fontsize=8)
    for key,label,marker in (("native_bed_traction_Pa","Original SPH","o"),("fv_bed_traction_Pa","FV pair","s")):
        ax[1].plot(late.time_s,late[key]-Q0,marker=marker,label=label)
    ax[1].axhline(0,color="0.35",lw=.7)
    ax[1].set(xlabel="Saved time (s)",ylabel="Bed traction minus 10 kPa (Pa)",title="Replay of saved stresses")
    ax[1].legend(fontsize=8)
    fig.savefig(paths[1],dpi=170)
    plt.close(fig)
    revision = subprocess.check_output(["git","rev-parse","HEAD"], cwd=TEST, text=True).strip()
    record = dict(source_revision=revision, analyzed_frames=table.part.tolist(),
                  source_data=str(DATA.relative_to(TEST)), elapsed_s=time.perf_counter()-start,
                  maxima=bounds, late_sample_count=len(late), late_rms_s1=metrics,
                  late_improves_each_half=gains, terminal_traction_preserved=bool(end_force_preserved),
                  terminal=end.to_dict(), formal_stress_limit_Pa=100,
                  full_coupled_run=False, physical_acceptance=False)
    paths[2].write_text(json.dumps(record,indent=2,allow_nan=False)+"\n",encoding="utf-8")


if __name__ == "__main__":
    main()
