"""Inspect the actual GenCase VTK/ID ledger; no physical solver or SHA scan."""
from pathlib import Path
import json, os, xml.etree.ElementTree as ET
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"): os.environ[key] = "1"
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

T = Path(__file__).resolve().parents[1]
TAG, STEM = "lian_collapse_geometry_r1", "CaseLianSaturatedColumnCollapse_geometry_r1"


def vtk(path):
    types = {"float": ">f4", "unsigned_int": ">u4", "unsigned_short": ">u2", "unsigned_char": "u1"}
    with path.open("rb") as stream:
        def line():
            text = stream.readline()
            while text in (b"\n", b"\r\n"): text = stream.readline()
            return text.decode("ascii").strip().split()
        def array(kind, count):
            dtype = np.dtype(types[kind]); raw = stream.read(dtype.itemsize*count)
            assert len(raw) == dtype.itemsize*count, "Truncated VTK data"
            return np.frombuffer(raw, dtype=dtype).astype(dtype.newbyteorder("="))
        assert stream.readline().startswith(b"# vtk DataFile Version")
        stream.readline()
        assert line() == ["BINARY"] and line() == ["DATASET", "POLYDATA"]
        head = line(); assert head[0] == "POINTS"
        count = int(head[1]); points = array(head[2], count*3).reshape(count, 3)
        head = line(); assert head == ["VERTICES", str(count), str(count*2)]
        vertices = np.frombuffer(stream.read(count*8), dtype=">i4").reshape(count, 2)
        assert np.all(vertices[:, 0] == 1) and np.array_equal(vertices[:, 1], np.arange(count))
        assert line() == ["POINT_DATA", str(count)]
        head = line(); assert head == ["SCALARS", "Idp", "unsigned_int"] and line() == ["LOOKUP_TABLE", "default"]
        fields = {"Idp": array("unsigned_int", count)}
        head = line(); assert head[:2] == ["FIELD", "FieldData"]
        for _ in range(int(head[2])):
            name, components, tuples, kind = line(); assert int(tuples) == count
            fields[name] = array(kind, count*int(components)).reshape(count, int(components))
        assert not stream.read().strip(), "Unexpected trailing VTK content"
    return points, fields


def main():
    out = T / "outputs" / TAG
    call = json.loads((T / "logs" / (TAG+".call.json")).read_text(encoding="utf-8"))
    assert call["direct_exit_captured"] and call["exit_code"] == 0 and not call["solver_started"]
    case = ET.parse(out / (STEM+".xml")).getroot()
    particles = case.find("execution/particles"); assert particles is not None
    xyz, fields = vtk(out / (STEM+"_All.vtk"))
    ids, mk = fields["Idp"], fields["Mk"].ravel()
    assert len(xyz) == int(particles.get("np")) == 7060 and np.array_equal(ids, np.arange(len(ids)))
    assert np.isfinite(xyz).all() and np.all(xyz[:, 1] == 0) and len(np.unique(xyz, axis=0)) == len(xyz)
    blocks = [row for row in particles if row.tag in ("fixed", "fluid")]
    assert [(row.tag, int(row.get("mk")), int(row.get("count"))) for row in blocks] == [("fixed",10,255),("fixed",11,1545),("fixed",12,260),("fluid",1,5000)]
    for row in blocks:
        start, count = int(row.get("begin")), int(row.get("count"))
        assert np.all(mk[start:start+count] == int(row.get("mk")))
    soil = xyz[mk == 1]
    expected = np.array([(x, 0, z) for x in .02+.04*np.arange(100) for z in .02+.04*np.arange(50)])
    assert len(soil) == 5000 and np.max(abs(soil-expected)) < 5e-7
    normxyz, normfields = vtk(out / (STEM+"_Normals.vtk"))
    assert np.array_equal(normfields["Idp"], ids[:2060]) and np.array_equal(normxyz, xyz[:2060])
    assert all(np.isfinite(value).all() for value in normfields.values())
    roles = {1: "soil", 10: "left FreeSlip", 11: "bottom NoSlip", 12: "right gate FreeSlip"}
    figs = T / "figures"; figs.mkdir(exist_ok=True)
    csvpath, pngpath, check = figs / (TAG+"_particles.csv"), figs / (TAG+".png"), T / "logs" / (TAG+".check.json")
    assert not any(path.exists() for path in (csvpath, pngpath, check)), "Retain existing review products"
    with csvpath.open("x", encoding="utf-8", newline="") as stream:
        import csv
        writer = csv.writer(stream); writer.writerow(["GenCase_Idp", "mk", "role", "x_m", "y_m", "z_m"])
        writer.writerows((int(i),int(m),roles[int(m)],*map(float,p)) for i,m,p in zip(ids,mk,xyz))
    fig, axes = plt.subplots(2, 1, figsize=(13, 7), constrained_layout=True)
    for ax in axes:
        for value, color in ((11,"#4a4a4a"),(10,"#229c76"),(12,"#d78325"),(1,"#2580bb")):
            points = xyz[mk == value]; ax.scatter(points[:,0],points[:,2],s=3 if value==1 else 6,c=color,label=f"{roles[value]} ({len(points)})")
        ax.set(xlabel="x (m)",ylabel="z (m)",ylim=(-.25,2.25),aspect="equal"); ax.grid(alpha=.2)
        ax.axvline(4,color="#d78325",lw=.6,ls=":"); ax.axhline(2,color="#2580bb",lw=.6,ls=":")
    axes[0].set(xlim=(-.25,12.3),title="Actual GenCase geometry: 12 m numerical bed; not a paper-specified bed length")
    axes[0].legend(loc="upper right",fontsize=8)
    axes[1].set(xlim=(-.25,4.3),title="Closed prestress container: 100 x 50 soil points, 4 m x 2 m, dp=.04 m")
    fig.suptitle("Case08 geometry admission only - no u-pl equilibrium, removal or collapse has been run")
    with pngpath.open("xb") as stream: fig.savefig(stream,format="png",dpi=150)
    plt.close(fig)
    result = dict(stage=TAG,passed=True,scope="Actual GenCase geometry only",soil_ids=5000,fixed_ids=2060,total_ids=7060,
                  soil_columns=100,soil_layers=50,soil_bbox=[soil.min(axis=0).tolist(),soil.max(axis=0).tolist()],
                  block_counts={str(value):int((mk==value).sum()) for value in roles},duplicate_positions=0,
                  GenCase_normals_generated=True,GenCase_normal_fields=list(normfields),solver_initialized_plane_normals_verified=False,
                  explicit_mkbound_slips={"0":"FreeSlip3","1":"NoSlip2","2":"FreeSlip3 before removal"},
                  numerical_bed_length_m=12,bed_length_is_paper_parameter=False,physical_solver_started=False,
                  equilibrium_or_removal_or_collapse_accepted=False,physical_acceptance=False,
                  files=[str(csvpath),str(pngpath)],fresh_SHA_scans=0)
    with check.open("x",encoding="utf-8") as stream: json.dump(result,stream,indent=2,allow_nan=False);stream.write("\n")
    print(json.dumps(result,ensure_ascii=False))


if __name__ == "__main__": main()
