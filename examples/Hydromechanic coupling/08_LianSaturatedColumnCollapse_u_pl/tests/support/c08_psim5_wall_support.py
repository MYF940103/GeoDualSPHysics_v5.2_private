"""Measure saved soil support at the bed sample named in the failed psim5 run."""
import csv
import re
import sys
from pathlib import Path

import numpy as np

CASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CASE / "support"))
from upl_tpi_partial_bi4_r1 import read


def main():
    out = CASE / "CaseLianCollapse_psim5_GPU_out"
    log = (out / "Run.out").read_text(encoding="utf-8", errors="replace")
    fault, = re.findall(r"^DynamicPoreWall rejected: stage=0 sorted_slot=\d+ native_id=(\d+) "
                        r"step_start=([^ ]+) step=\d+ B=\(([^)]+)\) normal=\(([^)]+)\)\.", log, re.M)
    wall_id, failure_start, coord, normal = fault
    assert int(wall_id) == 1074 and "Finished execution (code=1)." in log
    bed = np.fromstring(coord, sep=",")
    mirror = bed + np.fromstring(normal, sep=",").astype("f4").astype("f8")
    checkpoint = CASE / "CaseLianCollapse_psim5_pre_GPU_out/data/Part_1000.bi4"
    source_time = float(read(checkpoint)["part"]["values"]["TimeStep"])
    rows = []
    for part in range(60, 68):
        frame = read(out / "data" / f"Part_{part:04}.bi4")
        a, meta, registry = frame["arrays"], frame["part"]["values"], frame["root"]["values"]
        ids = a["Idp"]
        soil = (ids >= 2060)
        assert np.array_equal(np.sort(ids), np.r_[np.arange(1805), np.arange(2060, 7060)])
        assert np.allclose(a["Posd"][ids == int(wall_id)][0], bed, atol=1e-14, rtol=0)
        assert meta["Cpart"] == part and meta["TimeStep"] < float(failure_start)
        size = 2 * float(registry["H"])
        assert np.isclose(size, .144, rtol=0, atol=1e-8)
        pos = a["Posd"][soil]
        rb2 = np.square(pos - bed).sum(axis=1)
        rg2 = np.square(pos - mirror).sum(axis=1)
        size2 = np.float32(size**2)
        # B uses physical coordinates; packed cell floats used by the GPU are not saved.
        # At G the native kernel compares float-rounded squared distance.
        primary = rg2.astype("f4") <= size2
        source = rg2.argmin()
        source_id = int(ids[soil][source])
        rows.append(dict(part=part, time_s=meta["TimeStep"], tau_s=meta["TimeStep"] - source_time,
                         completed_step=meta["Step"] + 1, wall_id=wall_id,
                         Bx_m=bed[0], Bz_m=bed[2], Gx_m=mirror[0], Gz_m=mirror[2],
                         support_2H_m=size, n_soil_within_B_2H=int(np.count_nonzero((rb2 > 0) & (rb2 <= size2))),
                         n_soil_within_G_2H=int(primary.sum()),
                         front_x_m=float(pos[:, 0].max()), front_id=int(ids[soil][np.argmax(pos[:, 0])]),
                         closest_B_m=float(np.sqrt(rb2.min())), closest_G_m=float(np.sqrt(rg2[source])),
                         closest_G_id=source_id, closest_G_x_m=pos[source, 0], closest_G_z_m=pos[source, 2],
                         closest_G_p_kPa=float(a["PorePress"][soil][source])/1000,
                         closest_G_excess_kPa=float(a["ExcessPorePress"][soil][source])/1000,
                         closest_G_J=a["PoroVolumeRatio"][soil][source],
                         closest_G_speed_m_s=float(np.linalg.norm(a["Vel"][soil][source].astype("f8")))))
    dest = CASE / "tests/figures/c08_psim5_wall_support.csv"
    with dest.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
