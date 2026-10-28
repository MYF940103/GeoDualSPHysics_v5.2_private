"""Sparse visible raster reference points only; no solver, curve filling or RMSE."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

TESTS=Path(__file__).resolve().parents[1]
TAG='lian_server_return_r1_reference'


def bound(path):
    return dict(path=str(path.resolve()),bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main():
    record=TESTS/'logs'/(TAG+'_points.json')
    overlays=[TESTS/'figures'/(TAG+'_'+f+'_overlay.png') for f in ['fig11','fig12']]
    assert not any(p.exists() for p in [record]+overlays),'Never overwrite retained evidence'
    paths={f:TESTS/'figures'/(TAG+'_'+f+'.png') for f in ['fig11','fig12']}
    images={k:Image.open(p).convert('RGB') for k,p in paths.items()}
    assert images['fig11'].size==(1001,564) and images['fig12'].size==(1500,527)
    marks={f:ImageDraw.Draw(im) for f,im in images.items()};points=[];skipped=[]
    def add(fig,quantity,curve,point,x,y,value,units,**meta):
        number=len(points)+1;row=dict(number=number,figure=fig,quantity=quantity,reference_method=curve,
            paper_point=point,pixel_x=float(x),pixel_y=float(y),value=float(value),units=units,**meta)
        points.append(row);draw=marks['fig11' if fig=='11' else 'fig12']
        draw.ellipse((x-5,y-5,x+5,y+5),outline='#008800',width=2)
        draw.text((x+6,y-14),str(number),fill='#007700',stroke_width=1,stroke_fill='white')
    def red_groups(name,x,ymin,ymax):
        a=np.asarray(images[name]);mask=(a[:,x,0]>170)&(a[:,x,1]<110)&(a[:,x,2]<110)
        ys=np.flatnonzero(mask[ymin:ymax])+ymin
        return [g for g in np.split(ys,np.flatnonzero(np.diff(ys)>1)+1) if len(g)]
    # Fig11 axes: log10(time), x=.01/100 at 102/974; p=0/5kPa at y=441/12.
    for target in [.1,.5]:
        x=round(102+218*np.log10(target/.01));groups=red_groups('fig11',x,13,441);assert len(groups)==2
        for label,g in zip(['A','B'],groups):
            y=float(np.median(g));pixels=max(3.,(g[-1]-g[0])/2+1)
            add('11','excess pore pressure','SPH',label,x,y,(441-y)/85.8,'kPa',target_time_s=target,
                raster_time_s=.01*10**((x-102)/218),pixel_vertical_uncertainty=pixels,value_uncertainty=pixels/85.8,
                one_pixel_units=1/85.8,time_relative_one_pixel=np.expm1(np.log(10)/218))
    skipped += ['Fig11 t=1s sharp peak: no point retained because slope/marker envelope makes a single-pixel peak misleading.',
        'Fig11 t=3/10/50/100s: red branches overlap or approach axis; no separate A/B values retained.',
        'Fig11 FEM: blue hollow markers/line envelopes overlap red; no uniquely traceable sparse FEM pressure values retained.']
    # Fig12a axes: x=.01/100 at 98/745; settlement 0/20e-4m at y=120/427.
    for target in [.1,.5,1,3,10,50]:
        x=round(98+161.75*np.log10(target/.01));groups=red_groups('fig12',x,43 if target<1 else 180,427)
        assert len(groups)==2,(target,[(g[0],g[-1]) for g in groups])
        for label,g in zip(['B','A'],groups):
            y=float(np.median(g));pixels=max(3.,(g[-1]-g[0])/2+1)
            add('12a','downward-positive settlement','SPH',label,x,y,(y-120)*.002/307,'m',target_time_s=target,
                raster_time_s=.01*10**((x-98)/161.75),pixel_vertical_uncertainty=pixels,value_uncertainty=pixels*.002/307,
                one_pixel_units=.002/307,time_relative_one_pixel=np.expm1(np.log(10)/161.75))
    skipped += ['Fig12a t=100s red endpoints are hidden by blue strokes; no red endpoint was invented.',
        'Fig12a FEM histories were not digitized through blue marker outlines/occluded red curves.']
    # Fig12b signed ux: x=0/1e-4m at 1218/1355.5; elevation 0/10m at y=428/42.
    # Manually identified centers/envelopes are drawn back onto the unchanged original raster for review.
    for method,z,x in [('FEM',2,1278.),('FEM',3,1300.5),('FEM',5,1342.),('FEM',7,1391.5),('FEM',8,1411.),
            ('FEM',10,930.5),('SPH',6,1370.5),('SPH',7,1394.5),('SPH',8,1415.5)]:
        y=428-38.6*z
        add('12b','signed horizontal displacement',method,'x=1.25m section',x,y,(x-1218)*1e-4/137.5,'m',
            time_s=100.,elevation_m=z,depth_from_top_m=10-z,pixel_horizontal_uncertainty=3.,
            value_uncertainty=3e-4/137.5,one_pixel_units=1e-4/137.5,elevation_one_pixel_m=1/38.6,
            trace='Visible blue stroke-envelope/diamond center or isolated red stroke; sparse approximate center, not exact FEM/SPH data.')
    skipped.append('Fig12b upper steep-turn rows near elevation9-9.5m and bottom crossing are omitted; no hidden profile continuation is filled.')
    for path,image in zip(overlays,[images['fig11'],images['fig12']]):image.save(path)
    pdf=TESTS.parents[3]/'src/papers/PDF/Lian 2023 u-pl.pdf';pdf_identity=bound(pdf)
    assert pdf_identity['sha256']=='c5bb5e8862c87893cd5891758df1d46ea47ddd498e1e61096554e0622756943b'
    result=dict(source_pdf_sha256=pdf_identity['sha256'],
        source_pdf_relative_path='src/papers/PDF/Lian 2023 u-pl.pdf',source_page=18,source_xrefs=dict(fig11=69,fig12=71),
        sources=[bound(Path(__file__)),pdf_identity]+[bound(p) for p in paths.values()],artifacts=[bound(p) for p in overlays],
        calibration=dict(fig11=dict(x_log10_time_anchors=[[102,.01],[974,100]],y_pressure_kpa_anchors=[[441,0],[12,5]]),
            fig12a=dict(x_log10_time_anchors=[[98,.01],[745,100]],y_settlement_m_anchors=[[120,0],[427,.002]]),
            fig12b=dict(x_ux_m_anchors=[[1218,0],[1355.5,.0001]],y_elevation_m_anchors=[[428,0],[42,10]])),
        points=points,skipped=skipped,visual_review_passed=False,physical_reference_accepted=False,
        limitations=['Approximate raster numerical-reference observations, never analytical truth or original solver data.',
            '3px coordinate envelopes are conservative digitization-resolution estimates, not statistical confidence intervals.',
            'Rounded column has its actual raster time recorded; no curve interpolation or time-shift correction is applied.',
            'Only visible branches are assigned by the paper labels and separation; no occluded point is imputed.',
            'No whole-curve or whole-field RMSE is justified by this sparse table; use overlays and ranges for review.',
            'Fig12b paper does not specify material vs current line; current comparison tracks the initial x0=1.25m material line.'])
    with record.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps(dict(record=str(record),point_count=len(points),points=points),indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run',action='store_true')
    if parser.parse_args().run:main()
    else:parser.print_help()
