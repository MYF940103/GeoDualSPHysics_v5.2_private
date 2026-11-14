              const double pdrx=double(drx);
              const double pdry=(Simulate2D? 0: double(dry));
              const double pdrz=double(drz);
              const double prr2=pdrx*pdrx+pdry*pdry+pdrz*pdrz;
              if(prr2<=double(KernelSize2) && prr2>=ALMOSTZERO){
                if(PorosityFeedback && (!std::isfinite(PoroJc[p2]) || PoroJc[p2]<=1.-double(SoilCte.Porosity))){
                  porosity_thetap1=std::numeric_limits<double>::quiet_NaN();continue; //-Existing J-stage validation must fail, never silently omit this source.
                }
                const double pfac=double(fsph::GetKernel_Fac<tker>(CSP,float(prr2)));
                const double pfrx=pfac*pdrx;
                const double pfry=(Simulate2D? 0: pfac*pdry);
                const double pfrz=pfac*pdrz;
                const double pcfrx=porecorr.a11*pfrx+porecorr.a12*pfry+porecorr.a13*pfrz;
                const double pcfry=porecorr.a21*pfrx+porecorr.a22*pfry+porecorr.a23*pfrz;
                const double pcfrz=porecorr.a31*pfrx+porecorr.a32*pfry+porecorr.a33*pfrz;
                const double dcfrx=(PoreCompressionGradCorr? pcfrx: pfrx);
                const double dcfry=(PoreCompressionGradCorr? pcfry: pfry);
                const double dcfrz=(PoreCompressionGradCorr? pcfrz: pfrz);
                const double vol2=(PorosityFeedback? porovol2: double((boundp2? MassBound: MassFluid)/velrhop[p2].w));
                const double pdvx=-double(dvx_grad_deriv);
                const double pdvy=(Simulate2D? 0: -double(dvy_grad_deriv));
                const double pdvz=-double(dvz_grad_deriv);
                const double pdotgrad=pdrx*pcfrx+pdry*pcfry+pdrz*pcfrz;
                const double divv=vol2*(pdvx*dcfrx+pdvy*dcfry+pdvz*dcfrz);
