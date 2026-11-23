"""An equal-total-mass outer shell for the original fixed-reference Cryer study."""
import argparse
import json

import numpy as np
import pandas as pd

from cryer_pair_window import T, DT, execute
from cryer_weak_geovol import DLL, RHO, donor_viscosity, check_forces, summarize
from cryer_weak_window import configure


TAG = "cryer_surface_inertia_open_r1"
OUT = T/"outputs"/TAG
GEOMETRY = T/"outputs/cryer_tet_reference_r1.npz"


def surface_mass(m):
    with np.load(GEOMETRY) as z:
        tri = z["faces"]
        old = z["native_mass_kg"]
        if not np.array_equal(z["native_ids"], m.ids):
            raise ValueError("Material identity mismatch")
    rhat = m.x/np.linalg.norm(m.x,axis=1)[:,None]
    a,b,c = rhat[tri].transpose(1,0,2)
    # Exact spherical triangle solid angles; each facet gives one third to each material vertex.
    triple = np.einsum("ij,ij->i", a, np.cross(b,c))
    denom = 1 + np.einsum("ij,ij->i",a,b)+np.einsum("ij,ij->i",b,c)+np.einsum("ij,ij->i",c,a)
    omega = 2*np.arctan2(abs(triple),denom)
    weights = np.bincount(tri.ravel(),weights=np.repeat(omega/3,3),minlength=m.n)
    if not (np.array_equal(np.flatnonzero(weights),m.surface) and abs(weights.sum()-4*np.pi)<1e-12):
        raise ValueError("Incomplete outer sphere")
    mass = old.copy()
    fs = m.surface
    mass[fs] = old[fs].sum() * weights[fs] / weights[fs].sum()
    if not (np.all(mass>0) and abs(mass.sum()-old.sum())<1e-13):
        raise ValueError("Initial mass changed")
    return old,mass


def prepare(m):
    _,m.mass = surface_mass(m)
    return donor_viscosity(m.x,m.mass/RHO)


def fixture(g,m,h):
    old,expected = surface_mass(m)
    if not np.array_equal(m.mass,expected):
        raise ValueError("Unexpected mass array")
    result = check_forces(g,m,h,av_volume=m.mass/RHO)
    result.pop("geometric_total_mass_kg")
    normal = m.x/np.linalg.norm(m.x,axis=1)[:,None]
    pressure = np.full(m.n,1e4)
    pressure[m.surface] = 0
    force = m.surface_force(1e4) + m.pressure_force(pressure)
    def scatter(mass):
        a = force/mass[:,None]
        ar = (a*normal).sum(axis=1)
        at = a - ar[:,None]*normal
        return {str(s):dict(radial_sd_m_s2=float(ar[m.shells==s].std()),
                            tangential_rms_m_s2=float(np.sqrt(np.sum(at[m.shells==s]**2,axis=1).mean())))
                for s in (19,20)}
    return dict(**result, adjusted_total_mass_kg=float(m.mass.sum()), fraction_old_surface_mass_preserved=float(
        m.mass[m.surface].sum()/old[m.surface].sum()), min_surface_mass_ratio=float((m.mass/old)[m.surface].min()),
        max_surface_mass_ratio=float((m.mass/old)[m.surface].max()), old_step_response=scatter(old),
        matched_mass_step_response=scatter(m.mass))


def review():
    target=T/"logs"/(TAG+".check.json")
    tab=T/"figures"/(TAG+".csv")
    if tab.exists() or target.exists():
        raise FileExistsError("Keep previous review")
    seal=json.loads((OUT/"completed.json").read_text())
    if not (seal["steps"]==4160 and seal["closed_pass"] and seal["material_ids"]==37173):
        raise ValueError("Incomplete window")
    rows=[]
    with np.load(GEOMETRY) as z:
        ids,x,shell=(z[k] for k in ("native_ids","x0","material_shell"))
    for step in (4096,4097,4160):
        with np.load(OUT/f"state_{step}.npz") as s:
            if not np.array_equal(s["ids"],ids) or int(s["step"])!=step:
                raise ValueError("Unexpected physical sample")
            rows.append(summarize(s["p"],s["J"],x+s["u"],ids,x,shell,step,"matched surface mass"))
    old=pd.read_csv(T/"figures/cryer_weak_geovol_open_r1.csv",float_precision="round_trip")
    result=pd.concat([old.drop(columns="legacy_Tv"),pd.DataFrame(rows)],ignore_index=True)
    if not np.array_equal(result.time_s,result.step*DT):
        raise ValueError("Clock mismatch")
    result.to_csv(tab,index=False,mode="x")
    with target.open("x") as f:
        json.dump(dict(closed_pass=True,old_native_shell_totals=True,changed_ids=5153,
            scope="Constant initial inertia and AV donor redistribution on the outer shell only. Retained P1 work and water operators.",
            final=result[result.step==4160].to_dict(orient="records")),f,indent=2,allow_nan=False)
        f.write("\n")
    print(result[result.step==4160][["source","center18_Pa","angular_rms_Pa","p_max_Pa","surface_inward_mm"]].to_string(index=False))


def plot_review():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    data = pd.read_csv(T/"figures"/(TAG+".csv"))
    out = T/"figures"/(TAG+".png")
    if out.exists():
        raise FileExistsError(out)
    data = data[data.step == 4160].set_index("source")
    labels = ["Server P3", "Geometric mass", "Native mass", "Redistributed\nsurface mass"]
    data = data.loc[["returned server P3", "geometric weak", "native-mass weak", "matched surface mass"]]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.5), layout="constrained")
    for ax, field, scale, axis in zip(axes, ["center18_Pa", "angular_rms_Pa", "surface_inward_mm"],
        [0.001, 1., 1000.], ["Center (18 IDs), kPa", "Within-shell pressure RMS, Pa", "Surface inward motion, µm"]):
        values = data[field].to_numpy()*scale
        bars = ax.bar(range(len(values)), values, width=0.65, color=["#89949c", "#aa7550", "#36668d", "#579878"])
        ax.bar_label(bars, labels=[f"{v:.2f}" for v in values], padding=3, fontsize=9)
        ax.set_xticks(range(len(values)), labels, rotation=18, ha="right", fontsize=8)
        ax.set_ylim(0, 1.2*max(values))
        ax.set_ylabel(axis)
        ax.spines[["right","top"]].set_visible(False)
    fig.suptitle("Cryer sphere at 0.12207 ms after drainage opens")
    fig.savefig(out, dpi=180)
    plt.close(fig)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review",action="store_true")
    parser.add_argument("--plot",action="store_true",help="Draw only the reviewed three-diagnostic comparison")
    args=parser.parse_args()
    if args.plot:
        plot_review()
    else:
        if not args.review:
            execute(DLL,OUT,4160,weak=configure,prepare_viscosity=prepare,check_forces=fixture)
        review()
