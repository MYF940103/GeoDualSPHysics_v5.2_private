"""Fixed-reference Cryer opening with geometric inertial and AV quadrature, from rest."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.spatial import cKDTree

from cryer_pair_window import T, DT, DAMP, execute, save_json
from cryer_tet_av_reference import H, SOUND, ALPHA, artificial_viscosity
from cryer_weak_window import configure
from cryer_p3_verify_r1 import snapshot, SOIL, CENTER

TAG = "cryer_weak_geovol_open_r1"
RHO = 2100.
OUTPUT = T / "outputs" / TAG
DLL = T / "outputs/cryer_weak_window_build_r1/cryer_weak_window.dll"


def prepare(m):
    """Set mass before GPU geometry upload; each directed AV row uses its donor's volume."""
    if not np.all(m.volume > 0) or np.ptp(m.volume) == 0:
        raise ValueError("Expected positive, nonuniform tetrahedral dual volumes")
    m.mass = RHO * m.volume
    return donor_viscosity(m.x, m.volume)


def donor_viscosity(x, volume):
    """Directed acceleration weights at fixed density, with the donor's material volume."""
    i, j = cKDTree(x).query_pairs(2*H, output_type="ndarray").T
    r = x[i] - x[j]
    r2 = np.einsum("ij,ij->i", r, r)
    kernel = ALPHA*SOUND*H*(-2.08891/H**5)*(1-np.sqrt(r2)/(2*H))**3/(r2+.01*H**2)
    upper = sparse.coo_matrix((kernel, (i,j)), shape=(len(x),len(x))).tocsr()
    return (upper + upper.T).multiply(volume[None,:]).tocsr()


def check_forces(g, m, hydro, *, av_volume=None):
    """Reference sums one equal-and-opposite force per unordered pair before division by m_i."""
    pairs = cKDTree(m.x).query_pairs(2*H, output_type="ndarray")
    rho = np.full(m.n, RHO)
    with np.load(T/"outputs/cryer_tet_step_reference_r1.npz") as f:
        assert np.array_equal(f["native_ids"],m.ids) and np.array_equal(f["x_m"],m.x)
        assert np.array_equal(f["geometric_dual_volume_m3"],m.volume)
        native_mass = f["native_mass_kg"].sum()
        v,s,p,theta = (np.ascontiguousarray(f[k]) for k in
                       ("v_m_s","stress_Pa","p_Pa","divergence_v_per_s"))
        load = float(f["q_Pa"])
    mass = m.mass[:,None]
    av,pa,total = [np.empty_like(v) for _ in range(3)]
    zero = np.zeros_like(p)
    zero_stress = np.zeros_like(s)
    for field in (np.tile([.001,-.002,.003],(m.n,1)), .02*m.x):
        g.call("forceFixture",np.ascontiguousarray(field),zero_stress,zero,0.,av,pa,total)
        if np.any(av):
            raise ValueError("Nonzero AV in rigid translation or affine expansion")
    visc,stats = artificial_viscosity(m.x,m.volume if av_volume is None else av_volume,rho,v,pairs)
    if not (0 < stats["approaching_pairs"] < len(pairs) and stats["nodal_power_W"] < 0
            and stats["net_force_N"] < 1e-10 and stats["net_torque_Nm"] < 1e-11):
        raise ValueError("Independent compression-only pair force/work balance")
    pf = m.pressure_force(p)
    expected = (m.internal_stress(s)+pf+m.surface_force(load)+visc)/mass-DAMP*v
    g.call("forceFixture",v,s,p,load,av,pa,total)
    errors = {k:float(np.max(np.abs(a-b))) for k,a,b in (
        ("viscosity_m_s2",av,visc/mass),("pressure_m_s2",pa,pf/mass),
        ("total_with_damping_m_s2",total,expected))}
    if max(errors.values()) > 1e-8:
        raise ArithmeticError(f"Per-ID force mismatch {errors}")
    a = expected.astype(np.float32).astype(np.float64)
    div = m.divergence(a)
    out = np.zeros_like(p)
    for drain in (False,True):
        g.call("pressureFixture",p,total,theta,int(drain),out)
        ref = hydro.sweep(p,theta,a,div,drain)
        errors["strong_fixture_"+("open" if drain else "closed")+"_Pa"] = float(np.max(abs(ref-out)))
        if not np.array_equal(ref,out):
            raise ArithmeticError(f"Per-ID pressure fixture {errors}")
    return dict(**errors,material_ids=m.n,pairs=len(pairs),av=stats,
                translation_expansion_av_max_m_s2=0.,native_total_mass_kg=native_mass,
                geometric_total_mass_kg=m.mass.sum(),min_mass_kg=m.mass.min(),max_mass_kg=m.mass.max(),
                density_kg_m3=RHO,av_H_m=H,av_alpha=ALPHA,av_sound_m_s=SOUND,damping_per_s=DAMP)


def summarize(p,J,pos,ids,x,shell,step,source):
    if not (np.isfinite(p).all() and np.isfinite(J).all() and np.isfinite(pos).all()):
        raise ValueError("Nonfinite material-state field")
    surface = shell==20
    means = np.bincount(shell,weights=p)[1:]/np.bincount(shell)[1:]
    if step>4096 and np.any(p[surface]):
        raise ArithmeticError("Nonzero drained pressure")
    radius0 = np.linalg.norm(x[surface],axis=1)
    inward = 1000*(radius0-np.linalg.norm(pos[surface],axis=1))
    return dict(step=step,time_s=step*DT,tau_s=(step-4096)*DT,source=source,
                center18_Pa=p[shell==1].mean(),shell17_Pa=means[16],shell18_Pa=means[17],
                shell17_minus18_Pa=means[16]-means[17],
                angular_rms_Pa=np.sqrt(np.mean((p-means[shell-1])**2)),
                p_min_Pa=p.min(),min_first_id=int(ids[np.argmin(p)]),
                p_max_Pa=p.max(),max_first_id=int(ids[np.argmax(p)]),
                J_min=J.min(),J_max=J.max(),surface_inward_mm=inward.mean(),
                surface_pressure_absmax_Pa=np.max(abs(p[surface])))


def review():
    check = T/"logs"/(TAG+".check.json")
    table = T/"figures"/(TAG+".csv")
    image = table.with_suffix(".png")
    if any(f.exists() for f in (table,image,check)):
        raise FileExistsError("Opening review outputs already present")
    with np.load(T/"outputs/cryer_tet_reference_r1.npz") as f:
        ids,x,shell = (f[k] for k in ("native_ids","x0","material_shell"))
    assert np.array_equal(ids,np.arange(8,37181)) and np.array_equal(ids[shell==1],CENTER)
    assert np.count_nonzero(shell==20)==5153
    original = "CaseCryer_TPI_P3_nu030_peak_r1_GPU_out"
    series = [("geometric weak",OUTPUT),("native-mass weak",T/"outputs/cryer_weak_open_r1")]
    retained = pd.read_csv(T/"figures/cryer_weak_angular_opening_r1_summary.csv")
    native_hist = pd.read_csv(T/"figures/cryer_p3_server_peak_actual_r1/physical/native_and_theory.csv")
    sources = []
    rows = []
    for step in (4096,4097,4160):
        part = 65 if step==4097 else step//64
        folder = (T/"outputs/cryer_p3_gpu_drain4097_r1" if step==4097 else T/"outputs"/original/original)
        path = folder/"data"/f"Part_{part:04d}.bi4"
        a,_ = snapshot(path,part,step,DT)
        assert np.array_equal(a["Idp"][SOIL],ids) and np.array_equal(np.isin(a["FSType"][SOIL],(2,3)),shell==20)
        native_name = "retained local P3" if step==4097 else "returned server P3"
        row = summarize(a["PorePress"][SOIL].astype(float),a["PoroVolumeRatio"][SOIL],a["Posd"][SOIL],
                        ids,x,shell,step,native_name)
        rows.append(row)
        sources.append(str(path.relative_to(T.parent)))
        for name,folder in series:
            path = folder/f"state_{step}.npz"
            with np.load(path) as f:
                assert int(f["step"])==step and np.array_equal(f["ids"],ids)
                rows.append(summarize(f["p"],f["J"],x+f["u"],ids,x,shell,step,name))
            sources.append(str(path.relative_to(T.parent)))
        for ix,label in ((-3,"original_P3"),(-1,"weak_flux_3D")):
            entry = retained[(retained.step==step)&(retained.model==label)].iloc[0]
            for col,refcol in (("center18_Pa","center18_mean_Pa"),("shell17_minus18_Pa","shell17_minus18_Pa"),
                               ("angular_rms_Pa","all_within_shell_angular_rms_Pa")):
                if abs(rows[ix][col]-entry[refcol]) > 1e-7:
                    raise ArithmeticError(f"Retained summary mismatch at {step} for {label}: {col}")
    df = pd.DataFrame(rows)
    tv_rate = native_hist.loc[native_hist.completed_step==4160,"legacy_Tv"].item()/(64*DT)
    df.insert(3,"legacy_Tv",df.tau_s*tv_rate)
    df.to_csv(table,index=False,mode="x")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig,axs = plt.subplots(1,3,figsize=(10,3.5),layout="constrained")
    for model,color in (("P3","#666666"),("native-mass weak","#ab5826"),("geometric weak","#176885")):
        mask = df.source.str.endswith("P3") if model=="P3" else df.source==model
        data = df[mask]
        for ax,field in zip(axs,("shell17_minus18_Pa","angular_rms_Pa","surface_inward_mm")):
            ax.plot(data.step-4096,data[field],"o-",ms=4,color=color,label=model)
    for ax,unit in zip(axs,("Shell 17 minus 18 (Pa)","Within-shell angular RMS (Pa)","True surface inward motion (mm)")):
        ax.set(xlabel="Steps since opening event",ylabel=unit)
        ax.grid(alpha=.2)
    axs[0].legend(fontsize=8)
    fig.savefig(image,dpi=160)
    plt.close(fig)
    seal = json.loads((OUTPUT/"completed.json").read_text(encoding="utf8"))
    assert seal["steps"]==4160 and seal["closed_pass"] and len(df)==9
    with (OUTPUT/"history.csv").open() as fp:
        start = pd.read_csv(fp).iloc[0]
    assert start.step==0 and start.center_Pa==0 and start.min_J==start.max_J==1 and start.max_speed_m_s==0
    inputs = [DLL,Path(__file__),T/"support/cryer_pair_window.py",T/"support/cryer_weak_window.py",
              T/"outputs/cryer_tet_reference_r1.npz",T/"outputs/cryer_tet_step_reference_r1.npz",
              T/"outputs/c04_p3_pressure_component_r1.npz"]
    hashes = {}
    for path in inputs:
        with path.open("rb") as fp:
            hashes[str(path.relative_to(T))] = hashlib.file_digest(fp,"sha256").hexdigest()
    save_json(check,dict(steps=4160,dt_s=DT,closed_pass=True,wall_seconds=seal["wall_seconds"],
                         comparison_rows=len(df),original_server_available_steps=[4096,4160],
                         retained_local_substitute_step=4097,ids=len(ids),center_ids=CENTER,
                         surface_count=int((shell==20).sum()),mass_av_and_pressure_fixtures=seal["fixture"],
                         original_evidence=sources,inputs_sha256=hashes))
    print(df.to_string(index=False),flush=True)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review",action="store_true",help="Only compare already completed state files")
    args = parser.parse_args()
    if not args.review:
        execute(DLL,OUTPUT,4160,weak=configure,prepare_viscosity=prepare,check_forces=check_forces)
    review()
