"""Local initial-wall support audit, using the actual GenCase ledger and XML planes.

Double Cubic evaluation follows FunSphKernel.h; it is not CPU/GPU bit equivalence.
No solver, boundary update, image-fluid population, fallback or input edit is made.
"""
from pathlib import Path
import csv
import json
import os
import xml.etree.ElementTree as ET
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[key] = "1"
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lian_collapse_geometry_review_r1 import vtk

T = Path(__file__).resolve().parents[1]
TAG = "upl_wall_geometry_r1"
SEED = "CaseLianSaturatedColumnCollapse_geometry_r1"


def cubic(dr, h, volume):
    """2-D W/Fac branches in FunSphKernel.h:51-132, evaluated in binary64."""
    r = np.linalg.norm(dr, axis=1)
    keep = r <= 2*h
    d, r = dr[keep], r[keep]
    q = r/h
    a1 = 10/(7*np.pi)
    a2, aa = a1/h**2, a1/h**3
    outer = r > h
    w = np.where(outer, .25*a2*(2-q)**3, a2*(1+(.75*q-1.5)*q*q))
    fac = np.zeros_like(r)
    nz = r > 0  # Actual dynamic-wall code explicitly sets Fac=0 at a coincident mirror.
    fac[nz] = np.where(outer[nz], -.75*aa*(2-q[nz])**2/r[nz],
                       (-3*aa*q[nz]+2.25*aa*q[nz]**2)/r[nz])
    grad = d*fac[:, None]
    return d, w*volume, grad*volume


def support(at, soil, h, volume):
    dr = at-soil
    nearest = float(np.linalg.norm(dr, axis=1).min())
    d, w, grad = cubic(dr, h, volume)
    # Original, unscaled production a_corr2, not a least-squares Gram matrix.
    m = np.array([[w.sum(), np.dot(d[:, 0], w), np.dot(d[:, 1], w)],
                  [grad[:, 0].sum(), np.dot(d[:, 0], grad[:, 0]), np.dot(d[:, 1], grad[:, 0])],
                  [grad[:, 1].sum(), np.dot(d[:, 0], grad[:, 1]), np.dot(d[:, 1], grad[:, 1])]])
    determinant = float(np.linalg.det(m))
    try:
        condition = float(np.linalg.cond(m, np.inf))
    except np.linalg.LinAlgError:
        condition = float("inf")
    submerged = float(-np.sum(d*grad))
    return dict(nearest_soil_m=nearest, kernel_nodes=len(w), positive_W_nodes=int((w > 0).sum()),
                sumwab=float(w.sum()), submerged=submerged, raw_mls_det=determinant,
                raw_mls_cond_inf=condition, raw_mls_rank=int(np.linalg.matrix_rank(m)),
                raw_det_gate=bool(w.sum() > 0 and abs(determinant) >= 1e-3))


def main():
    csv_in = T/"figures/lian_collapse_geometry_r1_particles.csv"
    seed_dir = T/"outputs/lian_collapse_geometry_r1"
    xml = ET.parse(seed_dir/(SEED+".xml")).getroot()
    config = ET.parse(T/"configs"/(SEED+"_Def.xml")).getroot()
    ledger = list(csv.DictReader(csv_in.open(encoding="utf-8")))
    ids = np.array([int(row["GenCase_Idp"]) for row in ledger])
    mk = np.array([int(row["mk"]) for row in ledger])
    xyz = np.array([[float(row[c]) for c in ("x_m", "y_m", "z_m")] for row in ledger])
    actual, fields = vtk(seed_dir/(SEED+"_All.vtk"))
    assert np.array_equal(ids, fields["Idp"]) and np.array_equal(mk, fields["Mk"].ravel())
    assert np.array_equal(xyz, actual.astype(np.float64)) and np.all(xyz[:, 1] == 0)
    assert len(ids) == len(np.unique(ids)) == len(np.unique(xyz, axis=0)) == 7060
    assert [(v, int((mk == v).sum())) for v in (10, 11, 12, 1)] == [(10,255),(11,1545),(12,260),(1,5000)]
    variables = {v.get("name"): float(v.get("value")) for v in xml.findall(".//varnum")}
    # GenCase records Dp in execution/constants, not in its user-varnum list.
    variables["Dp"] = float(xml.find("execution/constants/dp").get("value"))
    def number(text):
        return variables[text[1:]] if text.startswith("#") else float(text)
    dp = number(xml.find("casedef/geometry/definition").get("dp"))
    hdp = float(xml.find("casedef/constantsdef/hdp").get("value"))
    h, radius = hdp*dp, 2*hdp*dp
    assert dp == .04 and hdp == 1.2 and variables["ColumnLength"] == 4 and variables["ColumnHeight"] == 2
    assert not any("Periodic" in p.get("key", "") for p in xml.findall("execution/parameters/parameter"))
    planes = {}
    for case in (config, xml):
        found = {}
        for p in case.findall("execution/special/initialize/boundnormal_plane"):
            point, normal = p.find("point"), p.find("normal")
            n = np.array([number(normal.get(c)) for c in ("x", "z")])
            origin = np.array([number(point.get(c)) for c in ("x", "z")])
            found[int(p.get("mkbound"))+10] = (origin, n)
            assert p.find("clear").get("v") == "true" and float(p.find("maxdisth").get("v")) == 0
        assert set(found) == {10,11,12}
        if planes:
            assert all(np.array_equal(planes[k][0], found[k][0]) and np.array_equal(planes[k][1], found[k][1]) for k in planes)
        planes = found
    assert np.array_equal(planes[10][0], [0,0]) and np.array_equal(planes[10][1], [1,0])
    assert np.array_equal(planes[11][0], [0,0]) and np.array_equal(planes[11][1], [0,1])
    assert np.array_equal(planes[12][0], [4,0]) and np.array_equal(planes[12][1], [-1,0])
    soil = xyz[mk == 1][:, [0,2]]
    output = T/"figures"/(TAG+".csv")
    png = T/"figures"/(TAG+".png")
    check = T/"logs"/(TAG+".check.json")
    note = T/"notes"/(TAG+".json")
    assert not any(p.exists() for p in (output, png, check, note)), "Preserve existing audit evidence"
    rows = []
    for i in np.flatnonzero(mk != 1):
        x = xyz[i, [0,2]]
        nearest = float(np.linalg.norm(soil-x, axis=1).min())
        eligible = nearest <= radius
        origin, normal = planes[int(mk[i])]
        single = x-2*np.dot(x-origin, normal)*normal
        raw = support(single, soil, h, dp*dp)
        row = dict(native_id=int(ids[i]), mk=int(mk[i]), role=ledger[i]["role"], x_m=float(x[0]), z_m=float(x[1]),
                   physical_nearest_soil_m=nearest, physical_in_kernel_support=eligible,
                   single_target_x_m=float(single[0]), single_target_z_m=float(single[1]))
        row.update({"single_"+key: value for key, value in raw.items()})
        # At most one reflection in each actually violated local x0/x4/z0 plane.
        # Never fold far bed points across the retaining wall to invent nonlocal support.
        if eligible:
            compound = single.copy()
            faces = [str(int(mk[i]))]
            if compound[0] < 0:
                compound[0] = -compound[0]; faces.append("10")
            elif compound[0] > 4:
                compound[0] = 8-compound[0]; faces.append("12")
            if compound[1] < 0:
                compound[1] = -compound[1]; faces.append("11")
            assert len(faces) == len(set(faces)) <= 2
            proposed = support(compound, soil, h, dp*dp)
            row.update(candidate_faces="+".join(faces), candidate_face_count=len(faces),
                       candidate_target_x_m=float(compound[0]), candidate_target_z_m=float(compound[1]))
            row.update({"candidate_"+key: value for key, value in proposed.items()})
        rows.append(row)
    columns = list(rows[0]) + [k for row in rows for k in row if k not in rows[0]]
    columns = list(dict.fromkeys(columns))
    with output.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns); writer.writeheader(); writer.writerows(rows)
    active = [r for r in rows if r["physical_in_kernel_support"]]
    far = [r for r in rows if not r["physical_in_kernel_support"]]
    corner = [r for r in active if r["candidate_face_count"] == 2]
    def counts(part):
        return dict(rows=len(part), single_with_no_positive_W=sum(r["single_positive_W_nodes"] == 0 for r in part),
                    single_raw_det_failed=sum(not r["single_raw_det_gate"] for r in part),
                    candidate_rows=sum("candidate_raw_det_gate" in r for r in part),
                    candidate_raw_det_failed=sum(not r["candidate_raw_det_gate"] for r in part if "candidate_raw_det_gate" in r))
    result = dict(stage=TAG, passed=True, scope="Offline initial local support audit, not a production wall acceptance",
                  dp_m=dp, h_m=h, radius_m=radius, J=1, periodic=False, actual_seed_CSV_VTK_IDs_equal=True,
                  original_fixed_ids=len(rows), soil_ids=len(soil), all=counts(rows), physically_near=counts(active),
                  physically_far=counts(far), eligible_two_face=counts(corner),
                  by_mk={str(m):dict(all=counts([r for r in rows if r["mk"]==m]), near=counts([r for r in active if r["mk"]==m])) for m in (10,11,12)},
                  far_candidate_targets_constructed=0, raw_mls_det_limit=1e-3,
                  matrix="Original unscaled 3x3 a_corr2 with W and radial Fac rows, not a Gram matrix",
                  float_kernel_or_GPU_bit_equivalence=False, solver_initialized_normals_read=False,
                  solver_or_GenCase_started=False, production_or_input_modified=False, physical_acceptance=False)
    fig, axes = plt.subplots(2, 2, figsize=(15,9), constrained_layout=True)
    for ax in axes.flat:
        ax.scatter(soil[:,0], soil[:,1], s=2, c="#c5d2da", label="Actual 5000 soil")
        ax.axhline(0, color="black", lw=.6); ax.axvline(0, color="black", lw=.6); ax.axvline(4, color="black", lw=.6)
        ax.set(xlabel="x (m)", ylabel="z (m)", aspect="equal"); ax.grid(alpha=.15)
    ax = axes[0,0]
    for part, color, name in ((far,"#aaaaaa","Far wall: no proposed images"),(active,"#2b9669","Wall within actual 2h soil support")):
        ax.scatter([r["x_m"] for r in part],[r["z_m"] for r in part],s=10,c=color,label=f"{name} ({len(part)})")
    ax.set(xlim=(-.24,12.25),ylim=(-.24,2.18),title="Physical eligibility uses distance from original wall to actual soil")
    ax.legend(fontsize=7,loc="upper right")
    for ax in (axes[0,1],axes[1,0],axes[1,1]):
        for valid, color, marker, name in ((True,"#d78b23","o","Original one-face target: det OK"),(False,"#c62e36","x","Original one-face target: det failed")):
            part=[r for r in active if r["single_raw_det_gate"]==valid]
            ax.scatter([r["single_target_x_m"] for r in part],[r["single_target_z_m"] for r in part],s=15,c=color,marker=marker,label=name)
        ax.scatter([r["candidate_target_x_m"] for r in corner],[r["candidate_target_z_m"] for r in corner],s=45,facecolors="none",edgecolors="#713d9d",marker="^",label="Local two-face target")
        for r in corner:
            ax.plot([r["single_target_x_m"],r["candidate_target_x_m"]],[r["single_target_z_m"],r["candidate_target_z_m"]],c="#713d9d",lw=.7,alpha=.6)
    axes[0,1].set(xlim=(-.24,4.25),ylim=(-.24,2.18),title="Only physically near wall targets are compared")
    axes[0,1].legend(fontsize=7,loc="upper center")
    axes[1,0].set(xlim=(-.2,.3),ylim=(-.2,.3),title="Left-bottom corner: one-face versus necessary double reflection")
    axes[1,1].set(xlim=(3.7,4.3),ylim=(-.2,.3),title="Right-bottom corner; no repeated reflection of remote bed")
    fig.suptitle("Case08 initial Cubic support audit (binary64 offline): not mixed-slip, flux or dynamics acceptance")
    with png.open("xb") as stream: fig.savefig(stream,format="png",dpi=160)
    plt.close(fig)
    authored = dict(purpose="Quantify local support obstacles before designing mixed-wall implementation", input_CSV=str(csv_in),
                    seed_XML=str(seed_dir/(SEED+".xml")), seed_VTK=str(seed_dir/(SEED+"_All.vtk")),
                    kernel_source="src/source/FunSphKernel.h:51-132", volume="dp^2*J at J=1", arithmetic="binary64, not production float kernel constants/evaluation",
                    original_target="Reflect the actual fixed coordinate across its XML per-MK initialize plane. GenCase normal VTK is not substituted for these solver-plane prescriptions.",
                    candidate_target="Only when original wall min distance to actual soil<=2h: start with its own face reflection; reflect once across any remaining violated x=0/x=4/z=0 half-space. At most two local faces; no virtual top wall, fluid images, infinite folding, recentering or far-bed target.",
                    det_scope="Report original dimensionful raw a_corr2 determinant/condition and the existing abs(det)>=1e-3 test. This alone does not reproduce mDBC active-threshold policy, float arithmetic, returned field values or physical validity.",
                    limitations="No stress/NoSlip/derivative/viscous parity or Darcy pressure/Ace proof; corner quadrature and duplicated virtual volume remain separate issues. Single/double target support is a necessary geometric observation, not operator or physical acceptance.",
                    source_or_input_changes=False, solver_or_build_or_Git=False, outputs=[str(output),str(png),str(check)])
    for path,value in ((note,authored),(check,result)):
        with path.open("x",encoding="utf-8") as stream: json.dump(value,stream,indent=2,allow_nan=False);stream.write("\n")
    print(json.dumps(result,ensure_ascii=False))


if __name__ == "__main__":
    main()
