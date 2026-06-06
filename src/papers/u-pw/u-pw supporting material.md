# u-pw supporting material

> Auto-converted from PDF for Codex/code-reference reading. Formatting, equations, figures, and tables may require checking against the original PDF.

- Source PDF: `u-pw supporting material.pdf`
- Pages: 10

## Extracted Text

### Page 1

Supporting Information for:
A Coupled u–pw SPH Formulation for Hydromechanical Modeling
of Retrogressive Landslides and Comparison with a Penalty-Based
                       Approach

       Enrique M. del Castillo1,2, Ronaldo I. Borja1, and Alomir H. F´avero Neto3∗

 1Department of Civil and Environmental Engineering, Stanford University, Stanford, CA
                                      94305, USA
   2Current affiliation: Department of Civil and Environmental Engineering, Princeton
                            University, Princeton, NJ 08540, USA
3Department of Civil and Environmental Engineering, Bucknell University, Lewisburg, PA
                                      17837, USA

                  *Corresponding author: alomir.favero@bucknell.edu

Section I: Details on Numerical Stabilization

In practice, the explicit and dynamic nature of SPH often leads to spurious oscillations of
particles and excessive clustering, particularly in regions of high compression. To stabilize
the system, it is common to introduce both artificial viscosity and numerical damping. In
this work, we employ the well-known Monaghan artificial viscosity [4, 3] together with a
global damping force added to the balance of linear momentum. The modified momentum
equation becomes

   dvs          N      σ′i   σ′j               N      pwi + pwj      = X mj   +  + Πij     + X mj          1             vi + g, (1)                                                           · ∇Wij                                                               ρiρj          · ∇Wij −cd                                                  j=1    dt     i    j=1      ρ2i    ρ2j

where Πij is the Monaghan artificial viscosity term, defined as

                                                                                            ij
                                                                              ,   if vij  xij < 0,                −α¯cijµij + βµ2                                      Πij =                ¯ρij                       ·                               (2)
                              0,                 otherwise,

                     h vij  xijwith vij = vi        µij =           ·            ¯cij the average speed of sound of particles i and j,           −vj,       + ηh2,                                |xij|2
¯ρij the average density, and η ≪1 a small regularization parameter.  Following commonpractice and extensive testing, artificial viscosity coefficients are chosen within the ranges
0.1 ≤α ≤0.8 and 0 ≤β ≤0.4. This term provides a dissipative mechanism active onlyduring particle approach, thereby suppressing non-physical tensile instability and shock-like
oscillations.
                                                                              attenuates   The damping force −cdvi acts as a global viscous resistance that uniformly                                  qhigh-frequency particle oscillations. The damping coefficient is defined as cd = ξ   ρh2,E  where
ξ is a dimensionless control parameter, typically chosen in the range 0 ≤ξ ≤0.05. This

                                       1

### Page 2

damping strategy is widely used in dynamic SPH simulations to control residual kinetic
energy without significantly altering the bulk deformation response.
   Non-physical oscillations in the pore pressure field are a well-documented numerical instability when solving the strongly coupled flow–deformation equations. This behavior is not
unique to SPH but is also well known in continuum-based methods such as FEM, where it is
typically associated with a violation of the Ladyzhenskaya–Babuˇska–Brezzi (LBB) or inf–sup
stability condition in mixed u– pw formulations. In practice, the instability manifests as spatially oscillatory pressure modes or checkerboarding, particularly in cases of incompressible
or nearly incompressible pore fluids and low-permeability materials.
   Within the proposed SPH framework, spurious pore pressure oscillations are only observed in strongly coupled flow–deformation analyses of low-permeability soils under large
deformation, consistent with the above mechanisms.  Several stabilization strategies exist
in the literature to address this issue, and in this study, a simple and efficient Shepard
regularization technique is adopted, where the pore pressure at particle i is updated as

                      PNj=1 mjρj pwj Wij                                                  reg
                                   pw,i   =        mj         .                               (3)
                       PNj=1 ρj Wij

Equation 3 is applied to each particle after every 20 to 40 time steps.  This approach is
computationally inexpensive, easy to implement, and sufficiently robust for the problems
considered here.

Section II: Self-Weight Consolidation Verification Tests

Under self-weight consolidation, a 1D poroelastic soil column sustains an instantaneous
undrained response where the elastic deformation of the soil under its own weight produces
volumetric strains across the soil column resulting in excess pore pressures. The analytical
solution for the initial undrained pore pressure response is given by

                                (Kw/n)ρg(H                           pw0 (z) =        4     −z) ,                              (4)
                     K + 3G + Kw/n

where H is the height of the soil column and the coordinate z is measured from the bottom of
the column upwards [1]. The undrained response has been shown to be accurately recoverable
in SPH simulations using a hydromechanical framework for undrained loading [2]. In the
setup of our simulations, herein using the pore pressure rate (PR) u– pw formulation, the top
free surface boundary is treated as drained after the initial undrained response. Two distinct
possibilities are modeled from here: (1) gravity is no longer imposed allowing for extensive
pore pressure dissipation, which can be modeled analytically modeled using Terzaghi’s one
dimensional theory of consolidation, or (2) if the gravity loading is maintained, the pore
pressure profile with depth converges to the hydrostatic gradient.
   In case (1), after the self-weight induced consolidation in a poroelastic 1-D column, the
subsequent decay of pore pressure over time after the initial undrained response follows an

                                       2

### Page 3

exponential behavior governed by the characteristic values λn and the coefficient of consolidation cv. The pore pressure distribution is given by a Fourier series solution,

                            N
                        pw(z, Tv) = X An cos(λnz) exp(−λ2nTvH2)                      (5)
                                   n=0

   where the characteristic eigenvalues are

                                      (2n + 1)π
                                λn =                  ,                                   (6)
                               2H

   and the Fourier coefficients are

                                2 Z H
                      An =       pw0 (z) cos(λnz)dz.                            (7)
                   H   0

Here, H is the height of the soil column and the dimensionless time factor is again

                                     Tv = cvt/H2.                                     (8)

   In the simulations, the same material parameters as those used in the Terzaghi onedimensional consolidation problem are employed.  Figure S1A displays the pore pressure
profiles for the SPH simulation and the analytical solution for Scenario (1). We see the
simulation first matches the undrained solution and then the pore pressure decays as gravity
is switched off and dissipation proceeds, following the solution closely. The simulation also
agrees with the expected analytical degree of consolidation in Panel B.

                                                                                    Tv = 0.005
                                          1.0  0.7   0.5 0.4      0.25         0.1   0.05                                                           an1Yr1bH4vWgpXPHMfWJ8/nmeRYA=</latexit>(A)                                                                                                                                                                                                                                                                                                                                                                                                      an1Yr1bH4vWgpXPHMfWJ8/n+2RYQ=</latexit>(B)

Figure S1: (A) Pore pressure profiles compared to the theoretical solutions at Tv = 0.005,
0.05, 0.1, 0.25, 0.4, 0.5, 0.7, 1.0 and the undrained solution for self-weight loading under
gravity. Here k = 1e-3 m/s, ∆t = 1e-6 s, α = 0.4, and ξ = 4e-5. (B) Evolution of degree of
consolidation as a function of Tv for the same simulation as in panel (A).

   The simulation solution in Scenario (2) is plotted in Figure S2A showing how the pore
pressure immediately matches the undrained case and then progressively decays towards the
hydrostatic gradient, and successfully reaches it as gravity is not removed in the simulation.
In Panel B, the pore pressure at the bottom of the column as a function of dimensionless
time Tv shows how the pore pressure trends to and reaches the hydrostatic value.

                                       3

### Page 4

progression

                                                                                                                                                                                                                                                                                                                                                                                                                                                             an1Yr1bH4vWgpXPHMfWJ8/nmeRYA=</latexit>(A)                            (B)

Figure S2: (A) Pore pressure profiles under constant gravity loading trending from the
undrained to hydrostatic response plotted at different normalized time intervals. Here k =
1e-3 m/s, ∆t = 1e-6 s, α = 0.4, and ξ = 4e-5. (B) Evolution of the pore pressure at the
bottom of the soil column z/H = 1 as function of Tv.

Section III: Additional Framework Verification

Here we include the visualizations and results of additional verification tests for the u– pw
formulation using the modified Cam Clay model under triaxial loading. We also compare the
stress path results in p′−q space against the undrained framework from [2]. Figures S3 and S4show the undrained normally consolidated soil (TU-N) simulation and undrained moderately
overconsolidated soil (TU-M) simulation, respectively. For the analytical solutions of the
stress paths, see Supporting Information Section IV.

Section IV: MCC Undrained Stress Path Solution

Here, we show the analytical solution for the undrained triaxial stress path given the modified
Cam Clay model. Prior to first yield, the undrained triaxial stress path follows a straight
Vertical line in the p′ −q plane, since the mean effective stress ratio remains constant. Onceyielding occurs, the evolution of the mean effective stress is governed by

                                             p′i  M 2 + η2  Λ
                      =                       ,                                  (9)
                                             p′  M 2 + η2i
where η = q/p′ and Λ = (λ −κ)/λ. The initial state (p′i, qi, ηi) corresponds to the onset ofyielding [6]. The solution is obtained by integrating the elastoplastic constitutive equations
under the assumptions of constant specific volume (undrained condition) and associated flow.
   In the log(p′) −e plane, the undrained condition enforces constant specific volume, sothe stress path is horizontal, until it reaches the critical state line, at which point the state
remains fixed.

                                       4

### Page 5

Figure S3: Results of undrained triaxial test simulation using the u– pw formulation for a
normally consolidated soil (TU-N). The stress history in p′ −q space is shown in (A) whereas
the trajectory in log(p′) −e space is displayed in (B), and both are compared against thetheoretical solutions of Wood [6]. In panel (C), a magnified region of panel (A) is shown
comparing the u– pw solution to the undrained framework of [2]. Snapshots of pore pressure
pw are shown at initial yielding (D) and at the CSL line (E) for the implementation without
(left) and with (right) the Shepard regularization technique.

                                       5

### Page 6

Figure S4: Same as Figure S3 but for the undrained moderately overconsolidated soil (TUM) simulation.

                                       6

### Page 7

Section V: Computational Efficiency of Hydromechanical Modeling Approaches

In this section we compare the computational efficiency of the undrained approach and of the
strongly coupled u– pw formulation, and discuss some of the advantages and disadvantages in
light of the results in Section 5 of the paper. Both methodologies are built into GEOSPH which
uses the parallel capabilities of PySPH [5], and which is implemented on the Stanford Sherlock
High-Performance Computing Cluster, supporting hybrid parallel computing, and enabling
both multi-threaded and distributed applications across CPU and GPU architectures. To
evaluate computational performance, the failure of the shallower slope described in Section
5.1 of the paper is used as a benchmark problem. The simulation is executed using an
increasing number of AMD EPYC 7543 Milan CPU cores via OpenMP, with one thread per
core and 4 GB of RAM allocated per core. The wall clock time, defined as the actual elapsed
time required for the CPU cores to complete the simulation, is recorded for each core count.
The results are shown in Figure S5A, and the corresponding speedup curves are displayed
in Panel B.
   As expected, the undrained framework achieves lower wall-clock times across all core
counts due to its simplicity. This approach avoids solving a coupled momentum–fluid system by computing pore pressure algebraically from the volumetric strain using a penalty
formulation. It involves fewer computational operations per particle and has lower memory
and arithmetic demands. However, the u– pw method exhibits better scalability with increasing core count. Despite its higher per-core computational cost, the parallel speedup is more
pronounced, which stems in part from its higher arithmetic intensity: each particle update
involves solving additional fluid equations, resulting in more operations per particle and better CPU utilization. Additionally, the particle interaction loops in the coupled method are
more computationally substantial, since they process multiple coupled fields, making them
more efficient to parallelize compared to the lighter loops of the undrained approach.

                                                 u −pw                      u −pw
                                                     u −pw

                                (A)                                                                                                                                                                                                                                                                                                                                                                                                       an1Yr1bH4vWgpXPHMfWJ8/n+2RYQ=</latexit>(B)

Figure S5: (A) Wall-clock time and (B) speedup for both undrained and u– pw retrogressive
landslide simulations performed in the GEOSPH code given different number of CPU cores.

                                       7

### Page 8

Section VI: Stress Evolution in the Sainte-Monique Landslide

Shear stresses drive localization of deformation into bands, when stresses on a potential
slip plane reach the soil shear strength, and also contribute through load transfer between
intact zones upslope and failed zones, ultimately controlling the progressive, block-by-block,
collapse in a spread failure. The shear stresses in the simulation are tracked in terms of
contours and across a horizontal transect at y = 4 m, close to the base of the computational
model, over time in Figure S6. The temporal window shown in the figure captures the
development of the 3rd and 4th slide (wedge). Within the already formed shear bands, the
shear stress is close to zero because the clay within the band undergoes unloading and also
has accumulated significant plastic deformation and softened, thus possessing a low shear
strength. Looking across the transect at y = 4 m, opposite-sense shearing across shear bands
is seen with positive σ′xy in the horsts and negative in the grabens due to their subsidence.
After the 3rd slide forms, as seen between x = 80 and x = 95 m along the transect at y = 4
m, the shear stress remains close to zero along the actual shear band but the magnitude of
the stress increases in between the bands from t = 6.0 to t = 18.0 seconds, indicating that
the soil is being loaded but does not yield. On the other hand, the stresses at the 2nd slide
event, between x = 120 and x = 135 m along the y = 4 m transect increase from 6.0 to 10.0
seconds (on either side of the slip plane not within it), but then begin decreasing after that,
as the subsidence of that graben ceases. Shear stress also accumulates over time as the 4th
slide begins to form, which is visible around x = 70 m along the y = 4 m transect prior
to yielding. Overall, we see that shear stresses build up in areas surrounding the eventual
slip planes until yielding and then localize, at which point the material in the shear bands
unloads and stress is transferred to the neighboring material. After slip ceases, due to the
end of a slide event, the shear stresses surrounding the slip planes relax and are transferred
further upslope as new slip planes form.

                                       8

### Page 9

Figure S6: (Left) shear strain σ′xy contours and (Right) shear stress profile along the transect
y = 4 m near the base of the sensitive clay deposit for different moments in time. The dotted
line overlying the stress contours shows the transect at y = 4 m.

                                       9

### Page 10

References

   [1] X. Chen, Y. Leung, H. Mori, S. Uchida, and K. Takumi. Single-layer soil-water coupled
    SPH method and its application to sinkhole simulation. Acta Geotechnica, 2023.

   [2] E. M. del Castillo, A. H. F´avero Neto, J. Geng, and R. I. Borja. An SPH framework
      for drained and undrained loading over large deformations. International Journal for
     Numerical and Analytical Methods in Geomechanics, 48(12): 3227-3257, 2024.

   [3] J. Gray, J. Monaghan, and R. Swift. SPH elastic dynamics. Computer Methods in
      Applied Mechanics and Engineering, 190(49-50):6641-6662, 2001.

   [4] J. J. Monaghan. Smoothed Particle Hydrodynamics. Annual Review of Astronomy and
      Astrophysics, 30: 543-574, 1992.

   [5] P. Ramachandran, A. Bhosale, K. Puri, et al. PySPH: A Python-based framework
      for smoothed particle hydrodynamics. ACM Transactions on Mathematical Software
    (TOMS), 47(4):1-38, 2021.

   [6] D. M. Wood. Soil behavior and critical state soil mechanics, Cambridge University
      Press, 1990.

                                       10
