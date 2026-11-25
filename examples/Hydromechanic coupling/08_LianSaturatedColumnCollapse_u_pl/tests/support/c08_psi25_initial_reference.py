"""Compare the same-material 10 s PRE with the three observable fields in Lian Fig. 13."""
import csv
import io
from pathlib import Path
import sys

import fitz
import numpy as np
from PIL import Image

CASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CASE / "support"))
from postprocess_lian_release import PRE_IDS, SOIL_IDS, native, verify_source_material

PDF = CASE.parents[2] / "src/papers/PDF/Lian 2023 u-pl.pdf"
PRE = CASE / "CaseLianCollapse_psi2p5_pre_GPU_out/data"
OUT = CASE / "tests/figures/c08_psi25_tpi/initial_fields.csv"
# Original PDF p.19, 1700 x 858 embedded JPEG. Field boundaries are physical edges
# between soil and the gate, bed or air. Colorbar coordinates are original pixel centers.
# colorbar x1,x2,y; soil left,right,top,bed; top of color scale in kPa.
PANELS = {
    "p":          (95,377,590, 91,505,632.5,840.5, 20.),
    "total_zz":   (651,935,594, 652,1067,631.5,839.5, 40.),
    "eff_zz":     (1241,1528,590, 1242,1663,626.5,837.5, 20.),
}


def read_panel(pixels, panel, height):
    b0,b1,by,left,right,top,bed,cap = panel
    palette = np.median(pixels[by-2:by+3,b0:b1+1],axis=0)
    band = slice(round(left+(right-left)*.25),round(left+(right-left)*.75)+1)
    y = round(bed-height*(bed-top)/2)
    values = []
    for j in (y-1,y,y+1):
        rgb = np.median(pixels[j,band],axis=0)
        ix = np.argmin(np.sum((palette-rgb)**2,axis=1))
        values.append(cap*ix/(b1-b0))
    delta = cap/(b1-b0)
    return values[1], max(0,min(values)-delta), min(cap,max(values)+delta)


def main():
    with fitz.open(PDF) as doc:
        page = doc[18]
        ref, = page.get_images()
        pixels = np.asarray(Image.open(io.BytesIO(doc.extract_image(ref[0])["image"])).convert("RGB"))
    assert pixels.shape == (858,1700,3)
    _, initial = native(PRE/"Part_0000.bi4")
    meta, final = native(PRE/"Part_1000.bi4")
    verify_source_material(meta,"psi2p5")
    assert meta["Step"]+1 == 2_000_000 and np.array_equal(initial["Idp"],PRE_IDS)
    assert np.array_equal(final["Idp"],PRE_IDS)
    source = initial["Posd"][SOIL_IDS]
    pos = final["Posd"][SOIL_IDS]
    p = final["PorePress"][SOIL_IDS].astype(float)/1000
    eff = -final["SigmaState_kk"][SOIL_IDS]/1000  # positive in compression, as printed
    k0 = eff[:,0]/eff[:,2]
    total = eff[:,2]+p
    layers = np.rint((source[:,2]-.02)/.04).astype(int)
    center = (source[:,0]>1) & (source[:,0]<3)
    rows = []
    for layer in range(50):
        use = (layers==layer) & center
        assert use.sum()==50
        z = np.median(pos[use,2])
        row = dict(layer_from_bed=layer+1,time_s=meta["TimeStep"],completed_step=meta["Step"]+1,particles=50,
                   native_z_m=z,native_initial_z_m=np.median(source[use,2]),depth_from_two_m=2-z,
                   native_eff_xx_kPa=np.median(eff[use,0]),native_K0_median=np.median(k0[use]))
        for name,field in (("p",p),("total_zz",total),("eff_zz",eff[:,2])):
            pub,lo,hi = read_panel(pixels,PANELS[name],z)
            ref = np.median(field[use])
            row.update({name+"_native_kPa":ref, name+"_paper_kPa":pub,
                        name+"_paper_low_kPa":lo, name+"_paper_high_kPa":hi,
                        name+"_native_minus_paper_kPa":ref-pub})
        rows.append(row)
    with OUT.open("x",encoding="utf8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


if __name__=="__main__":
    main()
