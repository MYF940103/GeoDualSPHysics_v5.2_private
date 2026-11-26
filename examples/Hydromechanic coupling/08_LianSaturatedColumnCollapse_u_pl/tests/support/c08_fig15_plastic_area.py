"""Whole-body Fig. 15 equivalent plastic strain with registration and annotation bounds."""
import csv
import json
import argparse

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation, binary_erosion, binary_fill_holes
from scipy.spatial import cKDTree

from c08_fig16_pressure_area import quantile
from c08_positive_suction_sites import OUT, RUNS, checked
from c08_psi25_tpi_fields import CACHE, PDF, STRAIN_AXES, load_pages, palette_limits, paper_panels
from c08_psi25_tpi_native import SOIL_IDS, TESTS, require
from c08_psi25_suction_stencil import V0


# Original 180 dpi page coordinates referenced to u=115,v=145 (cropped display).
# Boxed inset, text, straight leader segments, hand/arrowhead and zoom rectangle.
MARKS={
    .3: ((345,56,524,175), (77,95,183,140), (253,134,297,158),
         [(193,114,245,135),(245,135,231,135),(245,135,236,125),
          (253,134,349,58),(297,158,349,171)]),
    .6: ((344,274,524,393), (81,313,177,360), (249,350,293,373),
         [(176,327,235,349),(235,349,222,349),(235,349,226,340),
          (249,350,348,277),(293,373,348,390)]),
    1.2: ((344,506,524,617), None,(268,589,310,612),
          [(268,589,348,508),(310,612,348,612)])}


def annotation(page,t,us,vs):
    canvas=Image.new("1",(page.shape[1],page.shape[0]))
    draw=ImageDraw.Draw(canvas)
    inset,box,zoom,segments=MARKS[t]
    def pts(p):
        return tuple(n+(115 if i%2==0 else 145) for i,n in enumerate(p))
    draw.rectangle(pts(inset),fill=1)
    x1,y1,x2,y2=zoom
    for segment in [*segments,(x1,y1,x2,y1),(x2,y1,x2,y2),(x2,y2,x1,y2),(x1,y2,x1,y1)]:
        draw.line(pts(segment),fill=1,width=6)
    marks=np.array(canvas)
    broad=marks.copy()
    if box:
        u,v,uu,vv=pts(box)
        broad[v:vv+1,u:uu+1]=True
        rgb=page[v:vv+1,u:uu+1].astype(int)
        yellow=(np.minimum(rgb[:,:,0],rgb[:,:,1])>rgb[:,:,2]+10)
        marks[v:vv+1,u:uu+1]|=binary_dilation(yellow,iterations=3)
    return marks[np.ix_(vs,us)],broad[np.ix_(vs,us)]


def paper(t,page,upper_band=False):
    palette,lo,hi=palette_limits(page,"kappa",t)
    require(lo==0. and hi in (.3,1.,2.),"Fig. 15 original equivalent strain scale")
    _,right,extent=paper_panels(page,"excess",t)[0]
    # The paired pressure panel shows the same physical body without an enlarged inset.
    # Bridge short gaps from the thin red annotation on that outline with its column envelope.
    mask=binary_fill_holes(right[:,:,3]>0)
    x0,x8,bed,z2=STRAIN_AXES[t]
    us=np.arange(int(x0)-2,int(np.ceil(x8))+3)
    vs=np.arange(z2-3,bed+2)
    x=(us-x0)*8/(x8-x0)
    z=(bed-vs)*2/(bed-z2)
    xmin,xmax,zmin,zmax=extent
    ri=np.clip(np.floor((x-xmin)*mask.shape[1]/(xmax-xmin)).astype(int),0,mask.shape[1]-1)
    rj=np.clip(np.floor((zmax-z)*mask.shape[0]/(zmax-zmin)).astype(int),0,mask.shape[0]-1)
    shape=mask[np.ix_(rj,ri)]
    solidcols=np.flatnonzero(shape.any(axis=0))
    require(np.all(np.diff(solidcols)==1),"Discontinuous pressure-panel body extent")
    top=np.argmax(shape[:,solidcols],axis=0)
    bot=(shape.shape[0]-1)-np.argmax(shape[::-1,solidcols],axis=0)
    for col,head,foot in zip(solidcols,top,bot):
        shape[head:foot+1,col]=True
    marks,broad=annotation(page,t,us,vs)
    rgb=page[np.ix_(vs,us)]
    dist,idx=cKDTree(palette.astype(float)).query(rgb.reshape(-1,3).astype(float))
    dist,idx=dist.reshape(shape.shape),idx.reshape(shape.shape)
    delta=hi/(len(palette)-1)
    ku=idx*delta
    inside=(x[None,:]>=0)&(z[:,None]>=0)
    core=binary_erosion(shape,structure=np.ones((3,3)),iterations=3)&inside
    outer=binary_dilation(shape,structure=np.ones((3,3)),iterations=3)&inside
    if upper_band:
        slab=(z[:,None]>=1.50)&(z[:,None]<1.75)
        core &= slab
        outer &= slab
        shape &= slab
    use=core&~marks&(dist<=18)
    confident=core&~broad&(dist<=18)
    area=8/(x8-x0)*2/(bed-z2)
    common=dict(source="Lian Fig15 printed",nominal_s=t,actual_s="",scale_max=hi,
        n=use.sum(),area_analyzed_m2=use.sum()*area,
        valid_pct_of_central_body=100*use.sum()/shape.sum(),
        annotation_or_inset_pixels=int((core&marks).sum()),unread_color_pixels=int((core&~marks&(dist>18)).sum()),
        conservative_known_pct=100*confident.sum()/outer.sum())
    def coverage(cut):
        known_above=confident&(ku>=cut+delta)
        known_below=confident&(ku<cut-delta)
        if upper_band:
            # Consider every palette value compatible with the 18-unit RGB tolerance,
            # plus one printed-color sample of calibration uncertainty around the cutoff.
            ticks=np.arange(len(palette))*delta
            lo_colors=cKDTree(palette[ticks<cut+delta].astype(float))
            hi_colors=cKDTree(palette[ticks>=cut-delta].astype(float))
            rgb_valid=rgb[confident].astype(float)
            known_above[confident]=lo_colors.query(rgb_valid)[0]>18.
            known_below[confident]=hi_colors.query(rgb_valid)[0]>18.
        return (100*np.mean(ku[use]>=cut),100*known_above.sum()/outer.sum(),
                100*(1-known_below.sum()/outer.sum()))
    for threshold,key in ((.1,"01"),(.2,"02")):
        central,low,high=coverage(threshold)
        common.update({f"area_ge_{key}_pct":central,f"ge_{key}_lower_pct":low,f"ge_{key}_upper_pct":high})
        if upper_band:
            common[f"ge_{key}_known_width_m"]=low/100*outer.sum()*area/.25
            common[f"ge_{key}_possible_width_m"]=high/100*outer.sum()*area/.25
    for q in (.5,.90,.95,.99):
        common[f"q{int(q*100)}"]=float(np.quantile(ku[use],q,method="inverted_cdf"))
    common.update(lowest_bin_pct=100*np.mean(idx[use]==0),highest_bin_pct=100*np.mean(idx[use]==len(palette)-1),
                  lowest_two_bins_pct=100*np.mean(idx[use]<=1),highest_two_bins_pct=100*np.mean(idx[use]>=len(palette)-2))
    return common


def main():
    args=argparse.ArgumentParser(description=__doc__)
    args.add_argument("--upper-band",action="store_true",help="Limit both bodies to 1.50 <= z < 1.75 m.")
    upper_band=args.parse_args().upper_band
    tag=RUNS["beta004"]
    receipt=json.loads((TESTS/"logs"/(tag+".native_review.json")).read_text(encoding="utf8"))
    require(receipt["passed"] and receipt["tag"]==tag and receipt["frames"]==132,"Native source")
    page,_=load_pages(CACHE,PDF)
    rows=[]
    for t in STRAIN_AXES:
        pr=paper(t,page,upper_band)
        rows.append(pr)
        part=round(100*t)+12
        m,a,_=checked(TESTS/"outputs"/tag/"data"/f"Part_{part:04d}.bi4",receipt)
        tau=m["TimeStep"]-receipt["release_time_s"]
        soil=np.isin(a["Idp"],SOIL_IDS)
        require(np.array_equal(a["Idp"][soil],SOIL_IDS) and abs(tau-t)<1e-9,"Actual soil IDs and time")
        if upper_band:
            soil &= (a["Posd"][:,2]>=1.50)&(a["Posd"][:,2]<1.75)
        area=V0*a["PoroVolumeRatio"][soil]
        k=a["Kplastic"][soil].astype(float)
        hi=pr["scale_max"]
        palette,_,_=palette_limits(page,"kappa",t)
        delta=hi/(len(palette)-1)
        def pct(s): return 100*area[s].sum()/area.sum()
        row=dict.fromkeys(pr,"")
        row.update(source="C08 TPI beta=.04",nominal_s=t,actual_s=tau,scale_max=hi,n=len(k),
                   area_analyzed_m2=area.sum(),area_ge_01_pct=pct(k>=.1),area_ge_02_pct=pct(k>=.2),
                   lowest_bin_pct=pct(k<=0),highest_bin_pct=pct(k>=hi),lowest_two_bins_pct=pct(k<=delta),
                   highest_two_bins_pct=pct(k>=hi-delta))
        for q in (.5,.90,.95,.99):
            row[f"q{int(q*100)}"]=quantile(k,area,q)
        if upper_band:
            for threshold,key in ((.1,"01"),(.2,"02")):
                width=area[k>=threshold].sum()/.25
                row[f"ge_{key}_known_width_m"]=width
                row[f"ge_{key}_possible_width_m"]=width
        rows.append(row)
    name="fig15_plastic_upper_band.csv" if upper_band else "fig15_plastic_area.csv"
    with (OUT/name).open("x",encoding="utf8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


if __name__=="__main__":
    main()
