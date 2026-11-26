"""Paired frozen-state Wendland support comparison of four native C08 release frames."""
import csv
import json

import numpy as np
from scipy.spatial import cKDTree

from c08_h18_wend_partial_review_r1 import kernel
from c08_psi25_suction_row import pressure_row
from c08_psi25_suction_stencil import V0
from c08_positive_suction_sites import DP, H, RUNS, checked
from c08_psi25_tpi_native import SOIL_IDS, TESTS, require

OUT = TESTS / "figures/c08_kernel_range"
H_NARROW = float(np.float32(.05625))
SOLID0 = 1. - float(np.float32(.35))
GAMMA = 9806.65
PARTS = (42, 72, 100, 132)


def reconstruct(a, h):
    """First moments and wall-free production spatial terms on the complete geometry."""
    xz = a["Posd"][:, [0, 2]]
    n = len(SOIL_IDS)
    fixed = len(xz)-n
    volume = V0*a["PoroVolumeRatio"]
    require(np.allclose(volume[fixed:], a["PoroCurrentVolume"][fixed:], rtol=1e-12, atol=0),
            "Saved and reconstructed donor volumes differ")

    radius = float(np.float32(2*h))
    left, right = cKDTree(xz).query_pairs(np.nextafter(radius, np.inf), output_type="ndarray").T
    receiver = np.r_[left[left>=fixed], right[right>=fixed]]-fixed
    donor = np.r_[right[left>=fixed], left[right>=fixed]]
    d = xz[donor]-xz[fixed+receiver]
    rr2 = np.einsum("ni,ni->n", d, d)
    keep = (rr2.astype("f4")<=np.float32(radius**2)) & (rr2>0)
    receiver, donor, d, rr2 = receiver[keep], donor[keep], d[keep], rr2[keep]
    soil = donor>=fixed
    _, fac = kernel(rr2, h, np.float32(.557/h**2), np.float32(-2.7852/h**3))
    vg = ((-fac)*volume[donor])[:, None]*d

    def add(idx, vals):
        if vals.ndim==1:
            return np.bincount(idx, weights=vals, minlength=n)
        flat = vals.reshape(len(vals), -1)
        return np.stack([add(idx, col) for col in flat.T], axis=1).reshape((n, *vals.shape[1:]))

    moment = add(receiver, d[:, :, None]*vg[:, None, :])
    ev = np.linalg.eigvalsh(moment)
    regular = (ev[:,0]>np.finfo(float).eps*np.maximum(1.,ev[:,1])) & (ev[:,1]>0)
    conditions = np.full(n, np.inf)
    conditions[regular] = ev[regular,1]/ev[regular,0]
    inverse = np.full_like(moment, np.nan)
    inverse[regular] = np.linalg.inv(moment[regular])

    wall_count = np.bincount(receiver[~soil], minlength=n)
    soil_count = np.bincount(receiver[soil], minlength=n)
    grad = np.einsum("nij,nj->ni", inverse[receiver], vg)
    first = add(receiver, d[:, :, None]*grad[:, None, :])
    affine_error = np.max(abs(first-np.eye(2)), axis=(1,2))
    require(regular.any() and np.max(affine_error[regular])<1e-10, "First-moment affine test failed")

    # Residual derivatives require the true new wall fits. Restrict the comparison
    # to receivers with no wall in either candidate support, matched below.
    use = soil & (wall_count[receiver]==0) & regular[receiver]
    i, j, dx, r2, grad_i = receiver[use], donor[use], d[use], rr2[use].astype(float), grad[use]
    grad_j = np.einsum("nij,nj->ni", inverse[j-fixed], vg[use])
    weights = np.sum(dx*(grad_i+grad_j), axis=1)/(r2+float(np.float32((.1*h)**2)))
    vel = a["Vel"][:, [0, 2]].astype(float)
    dv = vel[j]-vel[i+fixed]
    grad_v = add(i, dv[:, :, None]*grad_i[:, None, :])
    theta = np.trace(grad_v, axis1=1, axis2=2)
    shear = np.hypot(grad_v[:,0,0]-grad_v[:,1,1], grad_v[:,0,1]+grad_v[:,1,0])

    p = a["PorePress"].astype(float)
    p_jump = p[j]-p[i+fixed]
    k = a["PoroHydraulicConductivity"][fixed:]
    grad_p = add(i, p_jump[:,None]*grad_i)
    J = a["PoroVolumeRatio"]
    grad_jvol = add(i, (J[j]-J[i+fixed])[:,None]*grad_i)
    grad_k = k[:,None]/(2*SOLID0)*grad_jvol
    linear_correction = add(i, weights[:,None]*dx)
    coefficients = weights-np.sum(grad_i*linear_correction[i], axis=1)
    p_term = k*add(i, coefficients*p_jump)+np.sum(grad_k*grad_p, axis=1)
    diagonal = k*add(i, weights)

    # Manufactured constant and affine pressure at each retained native geometry.
    # For constant k the interior Laplacian annihilates both; variable k is tracked separately.
    constant_error = np.max(abs(add(i, coefficients*(np.ones(len(j))-1.))))
    affine_pressure_error = np.max(abs(add(i, coefficients[:,None]*dx)), axis=1)
    valid = (wall_count==0)&regular&np.isfinite(p_term)&(diagonal>0)
    require(valid.any() and constant_error==0 and np.max(affine_pressure_error[valid])<1e-8,
            "Interior constant or affine pressure test failed")
    return dict(wall_count=wall_count, soil_count=soil_count, cond=conditions, valid=valid,
                affine_grad_error=affine_error, affine_pressure_error=affine_pressure_error,
                trace=np.trace(moment,axis1=1,axis2=2), theta=theta, shear=shear,
                p_term=p_term, diagonal=diagonal, partial_residual=p_term-GAMMA*theta)


def summary(mask, paired, original, narrow, area):
    count = int(mask.sum())
    sample = mask&paired
    row = dict(count=count, paired_wall_free=int(sample.sum()),
               area_m2=float(area[mask].sum()))
    if count:
        for label,s in (("wide",original),("narrow",narrow)):
            rr = s["cond"][mask]
            row.update({f"{label}_soil_median":float(np.median(s["soil_count"][mask])),
                        f"{label}_soil_min":int(np.min(s["soil_count"][mask])),
                        f"{label}_with_wall":int(np.count_nonzero(s["wall_count"][mask])),
                        f"{label}_moment_singular":int(np.sum(~np.isfinite(rr))),
                        f"{label}_cond_p95":float(np.quantile(rr[np.isfinite(rr)],.95))})
        row["loses_wall_donors_entirely"] = int(np.sum(mask & (original["wall_count"]>0) & (narrow["wall_count"]==0)))
    if not sample.any():
        return row
    w = area[sample]
    for metric in ("theta", "shear", "p_term", "diagonal", "partial_residual"):
        ref, trial = original[metric][sample], narrow[metric][sample]
        delta = trial-ref
        row.update({f"wide_{metric}_mean":float(np.average(ref,weights=w)),
                    f"narrow_{metric}_mean":float(np.average(trial,weights=w)),
                    f"delta_{metric}_rms":float(np.sqrt(np.average(delta*delta,weights=w))),
                    f"delta_{metric}_abs_p95":float(np.quantile(abs(delta),.95)),
                    f"{metric}_sign_change":int(np.count_nonzero((ref*trial)<0))})
    return row


def write(name, rows):
    fields = list(dict.fromkeys(field for row in rows for field in row))
    with (OUT/name).open("x", encoding="utf8", newline="") as f:
        writer = csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def plot(site, samples, result):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2,2,figsize=(11.3,7.4),layout="constrained")
    selected = samples[(samples["fs"]==0)&(samples["x"]>2.8)]
    shown = axes[0,0].scatter(selected["x"],selected["z"],c=selected["delta_theta"],
                              cmap="coolwarm",vmin=-.15,vmax=.15,s=9)
    axes[0,0].set(title="0.88 s  ·  Narrow minus wide divergence",
                  xlabel="x (m)",ylabel="z (m)",aspect="equal")
    fig.colorbar(shown,ax=axes[0,0],label="Divergence difference (1/s)",extend="both")
    late = [r for r in result if r["region"]=="p_below_minus5"]
    active = [r for r in result if r["region"]=="recent_plastic_rate_ge_0p2"]
    for rows,label,style in ((late,"p < −5 kPa","-o"),(active,"Recent plastic rate ≥ 0.2/s","--s")):
        axes[0,1].plot([r["tau_s"] for r in rows],[r.get("delta_theta_rms",np.nan) for r in rows],
                       style,label=label)
    axes[0,1].set(title="Paired wall-free zones",xlabel="Time after release (s)",
                  ylabel="Divergence difference, area-weighted RMS (1/s)")
    axes[0,1].legend()
    key = [r for r in site if r["id"]==6918]
    for ax,metric,unit in ((axes[1,0],"theta","Divergence (1/s)"),
                           (axes[1,1],"p_term","Pressure diffusion + variable k [Pa/(m·s)]")):
        for label,h in (("wide",.072),("narrow",.05625)):
            x=[r["tau_s"] for r in key]
            ax.plot(x,[r.get(f"{label}_{metric}",np.nan) for r in key],
                    "-o",label=f"H = {h:g} m")
        ax.set(title="Material point 6918",xlabel="Time after release (s)",ylabel=unit)
        ax.legend()
    for ax in axes.flat:
        ax.grid(alpha=.2)
    fig.suptitle("C08 +2.5°  ·  Frozen coarse-grid support comparison",fontsize=16)
    fig.savefig(OUT/"comparison.png",dpi=175)
    plt.close(fig)


def main():
    require(not OUT.exists(), "Preserve the existing kernel-range comparison")
    tag = RUNS["beta004"]
    receipt = json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text(encoding="utf8"))
    require(receipt["passed"] and receipt["frames"]==132 and receipt["tag"]==tag, "Baseline is unreviewed")
    source = TESTS/"outputs"/tag/"data"
    site_rows, summary_rows, moment_checks = [], [], []
    sample = None
    for part in PARTS:
        m,a,_ = checked(source/f"Part_{part:04d}.bi4",receipt)
        old,b,_ = checked(source/f"Part_{part-4:04d}.bi4",receipt)
        fixed = len(a["Idp"])-len(SOIL_IDS)
        soil = slice(fixed,None)
        time=m["TimeStep"]-receipt["release_time_s"]
        require(m["Step"]-old["Step"]==8000 and abs(m["TimeStep"]-old["TimeStep"]-.04)<1e-9,
                "The actual plastic-rate interval changed")
        rate = (a["Kplastic"][soil].astype(float)-b["Kplastic"][soil])/(m["TimeStep"]-old["TimeStep"])
        require(np.all(rate>=-1e-12), "Plastic history mismatch")
        p = a["PorePress"][soil].astype(float)/1000
        fs = a["FSType"][soil]
        area = a["PoroCurrentVolume"][soil]
        high, low = reconstruct(a,H),reconstruct(a,H_NARROW)
        trace_error = np.max(abs(high["trace"]-a["PosDiv"][soil]))
        require(trace_error<.001, "Production geometry did not reproduce native PosDiv")
        both = high["valid"]&low["valid"]&(fs!=2)&(fs!=3)
        theta_error = abs(high["theta"][both]-a["PoroThetaLastStage"][soil][both])
        point = int(np.searchsorted(SOIL_IDS,6918))
        require(both[point], "Reference 6918 lacks matched wall-free supports")
        check = pressure_row(a,fixed+point)
        require(abs(check["pressure_total"]-high["p_term"][point])<1e-7,
                "Production pressure decomposition differs from independent baseline replay")
        moment_checks.append(dict(part=part,tau_s=time,max_native_trace_error=trace_error,
            baseline_theta_rms=np.sqrt(np.mean(theta_error**2)), baseline_theta_abs_p95=np.quantile(theta_error,.95),
            compared_wall_free=int(np.count_nonzero(both)), wide_affine_grad_max=high["affine_grad_error"][both].max(),
            narrow_affine_grad_max=low["affine_grad_error"][both].max(),
            wide_affine_lap_max=high["affine_pressure_error"][both].max(),
            narrow_affine_lap_max=low["affine_pressure_error"][both].max()))
        for name,mask in (("all", np.ones(len(SOIL_IDS),bool)), ("active_free_surface",(fs==2)|(fs==3)),
                          ("p_below_minus5",p< -5),("p_below_minus20",p< -20),
                          ("recent_plastic_rate_ge_0p2",rate>=.2)):
            row = summary(mask,both,high,low,area)
            summary_rows.append(dict(part=part,tau_s=time,region=name,**row))
        for idx in sorted(set([point, int(np.argmin(p)), *np.searchsorted(SOIL_IDS,[6919,6920,7010])])):
            row = dict(part=part,tau_s=time,id=int(SOIL_IDS[idx]),p_kPa=p[idx],fs=int(fs[idx]),
                x=a["Posd"][fixed+idx,0],z=a["Posd"][fixed+idx,2],is_minimum=bool(idx==int(np.argmin(p))),
                recent_plastic_rate=rate[idx],native_theta=a["PoroThetaLastStage"][fixed+idx],paired=bool(both[idx]))
            for label,s in (("wide",high),("narrow",low)):
                for field in ("soil_count","wall_count","cond"):
                    row[f"{label}_{field}"] = s[field][idx]
                if both[idx]:
                    for field in ("theta","shear","p_term","diagonal","partial_residual"):
                        row[f"{label}_{field}"] = s[field][idx]
            site_rows.append(row)
        if part==100:
            pos = a["Posd"][soil]
            sample = np.rec.fromarrays((pos[both,0],pos[both,2],fs[both],low["theta"][both]-high["theta"][both]),
                                       names=("x","z","fs","delta_theta"))
    OUT.mkdir()
    write("regions.csv",summary_rows)
    write("sites.csv",site_rows)
    write("checks.csv",moment_checks)
    plot(site_rows,sample,summary_rows)
    print(OUT)


if __name__=="__main__":
    main()
