"""Raster-only Fig.14 right-column bulk outlines; author-only until root review."""
import argparse,csv,json,math
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

T=Path(__file__).resolve().parents[1];TAG='upl_c08_lian14_outline_r1'
SOURCE=T/'outputs/upl_c08_paper_scope_r1/page20.png';NOTE=T/'notes'/(TAG+'.md')
# Independently read right-panel tick centers: tau, x(0), x(8), y(z=0), y(z=2).
PANELS=((.3,660.,1102.5,298.,187.),(.6,660.,1102.,503.,391.),(1.2,660.,1106.5,704.,592.))
def need(ok,message):
 if not ok:raise RuntimeError(message)
def stat(p):
 p=Path(p).resolve();s=p.stat();return dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def write_csv(path,rows):
 with path.open('x',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 out=T/'figures';check=T/'logs'/(TAG+'.check.json')
 products=[out/(TAG+'_outline.csv'),out/(TAG+'_summary.csv'),out/(TAG+'_qa.png'),check]
 need(not any(p.exists() for p in products),'Existing complete/partial raster extraction is protected')
 before=[stat(SOURCE),stat(__file__),stat(NOTE)];rgb=np.asarray(Image.open(SOURCE).convert('RGB'))
 need(rgb.shape==(1709,1252,3),'Manual tick calibration belongs only to this unchanged cached raster size')
 edges=[];summary=[];fig,axes=plt.subplots(3,1,figsize=(11,7.2),constrained_layout=True)
 cross=ndi.generate_binary_structure(2,1)
 for ax,(tau,x0,x8,y0,y2) in zip(axes,PANELS):
  sx=8./(x8-x0);sz=2./(y0-y2)
  left,right=math.floor(x0)-3,math.ceil(x8)+3;top,bottom=math.floor(y2)-3,math.ceil(y0)+3
  image=rgb[top:bottom+1,left:right+1];r,g,b=image.astype(np.int16).transpose(2,0,1)
  green=(g>=180)&(r<=180)&(b<=190)&(g-np.maximum(r,b)>=40)
  labels,count=ndi.label(green,structure=np.ones((3,3),dtype=bool));need(count>0,'No green component found')
  areas=np.bincount(labels.ravel());areas[0]=0;selected=int(areas.argmax());body=labels==selected
  yy,xx=np.where(body);u=xx+left;v=yy+top
  need(areas[selected]>=2000 and u.min()<=x0+3 and v.max()>=y0-4,'Largest component is not an unambiguous left/bed-connected visible bulk')
  seed=np.zeros_like(body);seed[0,:]=seed[-1,:]=True;seed[:,0]=seed[:,-1]=True
  outside=ndi.binary_propagation(seed&~body,structure=cross,mask=~body)
  boundary=body&ndi.binary_dilation(outside,structure=cross)
  ey,ex=np.where(boundary);eu=ex+left;ev=ey+top
  # Every output edge is an actual classified pixel; no contour fit, fill, or smoothing.
  for px,py in zip(eu,ev):
   color=rgb[py,px]
   edges.append(dict(requested_tau_s=tau,pixel_u=int(px),pixel_v=int(py),x_m=(px-x0)*sx,z_m=(y0-py)*sz,R=int(color[0]),G=int(color[1]),B=int(color[2]),m_per_pixel_x=sx,m_per_pixel_z=sz,edge_plus_axis_allowance_px=2,approx_center_extent_allowance_m=.02))
  other=areas.copy();other[selected]=0
  summary.append(dict(requested_tau_s=tau,selected_green_pixels=int(areas[selected]),discarded_green_pixels=int(green.sum()-areas[selected]),second_component_pixels=int(other.max()),outer_boundary_pixels=int(boundary.sum()),front_pixel_u=int(u.max()),front_colored_extent_m=(u.max()-x0)*sx,visible_colored_height_m=(y0-v.min())*sz,m_per_pixel_x=sx,m_per_pixel_z=sz,edge_plus_axis_allowance_px=2,front_digitization_allowance_m=2*sx,approx_center_extent_allowance_m=.02,particle_center_front_claimed=False))
  extent=((left-.5-x0)*sx,(right+.5-x0)*sx,(y0-bottom-.5)*sz,(y0-top+.5)*sz)
  ax.imshow(image,extent=extent,origin='upper',interpolation='nearest');ax.scatter((eu-x0)*sx,(y0-ev)*sz,s=.6,c='#d62728',linewidths=0,label='Selected original outer-edge pixels')
  ax.axvline((u.max()-x0)*sx,color='black',lw=.7,ls='--');ax.set(xlabel='x (m)',ylabel='z (m)',title=f'Fig.14 right, tau={tau:g} s: visible colored bulk; raster calibration only',xlim=(extent[0],extent[1]),ylim=(extent[2],extent[3]),aspect='equal')
 axes[0].legend(loc='upper right',fontsize=8);fig.suptitle('Lian2023 Fig.14: right-column raster outline QA; no pressure-color sampling',fontsize=11)
 write_csv(products[0],edges);write_csv(products[1],summary)
 with products[2].open('xb') as f:fig.savefig(f,format='png',dpi=180)
 plt.close(fig);need(all(stat(e['path'])==e for e in before),'Raster/script/note changed during extraction')
 result=dict(stage=TAG,passed=True,analysis_completed=True,source=before[0],consumed=before,consumed_stats_unchanged=True,calibration=[dict(tau_s=t,x0_px=x0,x8_px=x8,z0_y_px=y0,z2_y_px=y2) for t,x0,x8,y0,y2 in PANELS],summary=summary,outputs=[stat(p) for p in products[:3]],visual_QA_pending=True,physical_acceptance=False,particle_center_front_claimed=False,pressure_values_sampled=False,PDF_renderings=0,BI4_reads=0,native_decodes=0,solver_invocations=0,SHA_scans=0)
 with check.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,ensure_ascii=False,allow_nan=False)
 print(check,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execution-authorized',action='store_true');a=p.parse_args();need(a.execution_authorized,'Author-only until root full-read');main()
