"""Manufactured interior shear-layer test of the C08 corrected SPH velocity divergence.

Vary spacing at fixed h/dp or fixed physical h. Keep each analytical velocity field
the same in metres and seconds, so that its thickness never follows the spacing.
"""
import csv

import numpy as np
from scipy.spatial import cKDTree

from c08_h18_wend_partial_review_r1 import kernel
from c08_psi25_tpi_native import TESTS, require


WIDTHS = np.array([.04, .08, .16])
SPACINGS = (.04, .02, .01)
H0 = float(np.float32(.072))
ANGLE_DEG = 37.
PEAK_DILATION = .075
PEAK_SHEAR = 1.
GAMMA = 9806.65
HALF_LENGTH = .48
HALF_NORMAL = .28
ANGLE = np.deg2rad(ANGLE_DEG)
TANGENT = np.array([np.cos(ANGLE), np.sin(ANGLE)])
NORMAL = np.array([-np.sin(ANGLE), np.cos(ANGLE)])
LENGTHS = WIDTHS / (2 * np.arccosh(np.sqrt(2)))
SHARED_SLOPE = PEAK_DILATION * NORMAL + PEAK_SHEAR * TANGENT
OUT = TESTS / "figures/c08_shear_operator_spacing"


def sample_lattice(dp, h, jitter):
    """Provide all donors out to two smoothing lengths from every receiver."""
    radius = 2 * h
    fringe = np.sqrt(HALF_LENGTH**2 + HALF_NORMAL**2) + radius + dp
    index = np.arange(-np.ceil(fringe/dp), np.ceil(fringe/dp)+1)
    xy = dp * (np.stack(np.meshgrid(index, index), axis=-1).reshape(-1,2) + [.371,.227])
    if jitter:
        xy += dp*jitter*np.random.default_rng(20261126).uniform(-1.,1.,size=xy.shape)
    s, r = xy @ TANGENT, xy @ NORMAL
    receivers = np.flatnonzero((abs(s) <= HALF_LENGTH) & (abs(r) <= HALF_NORMAL))
    require(len(receivers)>0 and np.max(abs(xy[receivers])) + radius < fringe, "Incomplete donor halo")
    return xy, r, receivers


def gradients(dp, h, jitter):
    xy, distance, receivers = sample_lattice(dp,h,jitter)
    neighborhoods = cKDTree(xy).query_ball_point(xy[receivers], 2*h)
    profile = np.tanh(distance[:,None] / LENGTHS) * LENGTHS
    measured, affine, counts, condition = [], [], [], []
    awen, bwen = np.float32(.557/(h*h)), np.float32(-2.7852/(h*h*h))
    for i, neighbors in zip(receivers, neighborhoods):
        js = np.asarray(neighbors, dtype=int)
        js = js[js != i]
        dr = xy[js]-xy[i]
        _, fac = kernel(np.sum(dr*dr,axis=1),h,awen,bwen)
        vg = (dp**2 * -fac)[:,None]*dr
        moment = dr.T @ vg
        eigenvalues = np.linalg.eigvalsh(moment)
        require(eigenvalues[0] > 0 and len(js) >= 9, "Insufficient manufactured support")
        corrected = np.linalg.solve(moment,vg.T)
        grad = corrected @ (profile[js]-profile[i])
        # For v = (theta0*n + shear0*t) f(n.x), div v = grad(f).(theta0*n + shear0*t).
        measured.append(SHARED_SLOPE @ grad)
        a = np.array([[.3,-.4],[1.2,-.1]])
        affine.append(np.trace(corrected @ (dr @ a.T))-np.trace(a))
        counts.append(len(js))
        condition.append(eigenvalues[1]/eigenvalues[0])
    worst_affine = np.max(np.abs(affine))
    require(worst_affine < 1e-12, "Affine corrected divergence check failed")
    return distance[receivers],np.asarray(measured),np.asarray(counts),np.asarray(condition),worst_affine


def experiment(dp, h, jitter):
    distance, calculated, counts, condition, affine = gradients(dp,h,jitter)
    exact = PEAK_DILATION/np.cosh(distance[:,None]/LENGTHS)**2
    results=[]
    for i,width in enumerate(WIDTHS):
        core = abs(distance)<=width/4
        require(core.sum()>=8, "Insufficient paired core samples")
        reference, estimate = exact[:,i], calculated[:,i]
        # Width inferred from squared integral normalized by the integral of theta squared.
        # Use the same receiver quadrature for the exact and discretized profile.
        def effective(values):
            return 2*HALF_NORMAL * values.mean()**2 / np.mean(values**2)
        results.append(dict(
            dp_m=dp,h_m=h,h_over_dp=h/dp,support_to_fwhm=2*h/width,angle_deg=ANGLE_DEG,
            jitter_component_amplitude_dp=jitter,true_fwhm_m=width,
            true_peak_theta_per_s=PEAK_DILATION,true_peak_shear_per_s=PEAK_SHEAR,
            receivers=len(distance),paired_core_receivers=int(core.sum()),
            donors_min=int(counts.min()),donors_median=float(np.median(counts)),
            moment_cond_max=condition.max(),max_affine_error_s_inv=affine,
            core_calculated_theta=estimate[core].mean(),core_exact_theta=reference[core].mean(),
            core_calculated_over_exact=estimate[core].mean()/reference[core].mean(),
            peak_calculated_over_exact=estimate.max()/reference.max(),
            relative_rmse= np.sqrt(np.mean((estimate-reference)**2))/PEAK_DILATION,
            sampled_calculated_width_m=effective(estimate),sampled_exact_width_m=effective(reference),
            calculated_over_exact_width=effective(estimate)/effective(reference),
            mean_core_source_error_Pa_m_s=-GAMMA*np.mean(estimate[core]-reference[core])))
    return results


def plot(rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, panels = plt.subplots(1, 2, figsize=(11.4,4.4),layout="constrained")
    treatments = (("fixed_h_over_dp","Fixed h/dp = 1.8","o-"),
                  ("fixed_h","Fixed h = 0.072 m","s--"))
    for key,title,style in treatments:
        for width,color in zip(WIDTHS,("#b4483e","#186c89","#638a55")):
            selected = [r for r in rows if r["sequence"]==key and r["true_fwhm_m"]==width
                        and r["jitter_component_amplitude_dp"]>0]
            x = [r["dp_m"]*1000 for r in selected]
            for panel,field in zip(panels,("core_calculated_over_exact","calculated_over_exact_width")):
                panel.plot(x,[r[field] for r in selected],style,color=color,linewidth=1.5,
                           markersize=4,label=f"{width*100:.0f} cm, {title}")
    for panel in panels:
        panel.axhline(1,color=".55",linewidth=1,zorder=-1)
        panel.set(xlabel="Particle spacing (mm)")
        panel.set_xticks([10,20,40])
        panel.grid(alpha=.24)
    panels[0].set(ylabel="Reconstructed / analytical mean",title="Dilation within half the band width")
    panels[1].set(ylabel="Reconstructed / analytical effective width",title="Dilation profile width")
    panels[0].legend(fontsize=8,ncol=2,loc="lower left")
    fig.suptitle("Corrected SPH divergence of a fixed-width interior shear layer")
    fig.savefig(OUT.with_suffix(".png"),dpi=180)
    plt.close(fig)


def main():
    require(not any(OUT.with_suffix(ext).exists() for ext in (".csv",".png")), "Retained diagnostic already exists")
    rows = []
    for jitter in (0.,.15):
        for dp in SPACINGS:
            h = float(np.float32(1.8*dp))
            refined = experiment(dp,h,jitter)
            rows.extend(dict(sequence="fixed_h_over_dp", **r) for r in refined)
            fixed = refined if h==H0 else experiment(dp,H0,jitter)
            rows.extend(dict(sequence="fixed_h", **r) for r in fixed)
    with OUT.with_suffix(".csv").open("x",newline="",encoding="utf8") as output:
        writer = csv.DictWriter(output,fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    plot(rows)
    print(f"Completed {len(rows)} spacing/support/width records. Max affine error {max(r['max_affine_error_s_inv'] for r in rows):.3g} /s.")


if __name__=="__main__":
    main()
