            const float volp2=(PorosityFeedback? -float(porovol2): -massp2/velrhop2.w);
            float dv=dvx_grad_deriv*volp2;  gradvp1_xx_xy_xz.x+=dv*frx; gradvp1_xx_xy_xz.y+=dv*fry; gradvp1_xx_xy_xz.z+=dv*frz;
                  dv=dvy_grad_deriv*volp2;  gradvp1_yx_yy_yz.x+=dv*frx; gradvp1_yx_yy_yz.y+=dv*fry; gradvp1_yx_yy_yz.z+=dv*frz;
                  dv=dvz_grad_deriv*volp2;  gradvp1_zx_zy_zz.x+=dv*frx; gradvp1_zx_zy_zz.y+=dv*fry; gradvp1_zx_zy_zz.z+=dv*frz;
