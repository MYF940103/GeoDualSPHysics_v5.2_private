              const double coeff=porovol2/pororhot1;
              const double pw=double(porepress[p1])+double(porepress[p2]);
              const double sxx=double(sigmap1.xx)+sigmap2.xx-pw,syy=double(sigmap1.yy)+sigmap2.yy-pw;
              const double szz=double(sigmap1.zz)+sigmap2.zz-pw,sxy=double(sigmap1.xy)+sigmap2.xy;
              const double sxz=double(sigmap1.xz)+sigmap2.xz,syz=double(sigmap1.yz)+sigmap2.yz;
              acep1.x+=float(coeff*(sxx*frx+sxy*fry+sxz*frz));
              acep1.y+=float(coeff*(syy*fry+sxy*frx+syz*frz));
              acep1.z+=float(coeff*(szz*frz+syz*fry+sxz*frx));
