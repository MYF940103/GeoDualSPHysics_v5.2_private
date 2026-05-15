# Large deformation analysis of granular materials with stabilized and noise-free stress treatment in smoothed particle hydrodynamics (SPH)

> Auto-converted from PDF for Codex/code-reference reading. Formatting, equations, figures, and tables may require checking against the original PDF.

- Source PDF: `Feng 2021_CG.pdf`
- Pages: 19
- PDF metadata author: Ruofeng Feng

## Extracted Text

### Page 1

Computers and Geotechnics 138 (2021) 104356

                                                 Contents lists available at ScienceDirect
                        Computers and Geotechnics

                                          journal homepage: www.elsevier.com/locate/compgeo

Large deformation analysis of granular materials with stabilized and
noise-free stress treatment in smoothed particle hydrodynamics (SPH)
Ruofeng Feng *, Georgios Fourtakas , Benedict D. Rogers , Domenico Lombardi
Department of Mechanical, Aerospace & Civil Engineering, Faculty of Science and Engineering, The University of Manchester, M13 9PL, UK

A R T I C L E  I N F O                  A B S T R A C T

Keywords:                                         This paper presents a new smoothed particle hydrodynamics (SPH) model for the large deformation analysis of
Smoothed particle hydrodynamics (SPH)              granular materials with improved accuracy and stability. In order to remove the spurious stress profile during the
Wall boundary conditions                              post-failure process which is a common issue for the application of SPH to geotechnical problems, an innovative
Numerical diffusion term                                                         stress diffusion term is formulated. Further a new boundary treatment is proposed with the use of renormaliFixed ghost particle                                                  zation techniques to give a first-order consistent wall boundary conditions for geotechnical applications. ThisPost-failure flow
                                           methodology  is able to deal with complex geometries such as sharp corners. A number of test cases are
                                                considered to examine the robustness and accuracy of the proposed technique. Results show that the new
                                           boundary formulation is able to improve the accuracy of the solution even for a relatively coarse particle res
                                                     olution. The stress diffusion term reduces the numerical noise that affects the stress under large deformations,
                                                     resulting in a smooth stress field. The proposed SPH model is finally applied to the simulation of granular flow
                                          and tunnel face collapse, showing satisfactory agreement and convergence with experimental results.

1. Introduction                                                    methods, however this is computationally demanding and not always
                                                                                  practical.
   The geophysical flows involving large deformations are closely       Comparing to mesh-based methods, a more efficient solution for the
related to a number of natural phenomena and engineering applications,     large deformation problem is provided by meshless methods in which
including snow and rock avalanches, debris flow in disaster prevention,     the mesh connectivity is eliminated. Examples of meshless methods used
landslides in slope stability, soil liquefaction in seismic design, and in     for granular materials and geotechnical applications include Smooth
ternal erosion in dam maintenance. Numerical analysis is a powerful     Particle Hydrodynamics (SPH) (Gingold and Monaghan, 1977), the
tool to study the progressive failure in geophysical flows and predict     Material Point Method (MPM) (Sulsky et al., 1994), and the Particle
their potential catastrophic consequences, whereas the presences of free     Finite Element Method (PFEM) (Onate et al., 2004). Among them, SPH
surfaces and extremely large deformation are the main challenges of the    can be regarded as a truly meshless, Lagrangian method. In SPH, the
modelling of such flows (Huang and Dai 2014).                            physical domain is discretized into a set of Lagrangian particles carrying
   In computational geomechanics, the most widely used predictive     macroscopic field properties, and moving with the material velocity.
tools are based on the finite element (FE) and finite difference (FD)    The interaction between particles is controlled by a weighting function
methods. These methods are very efficient in solving partial differential     called a smoothing kernel. A background mesh is not needed for the
equations (PDEs), and have been widely applied in the studies of     integration of the governing partial differential equations since the local
geotechnical problems. Despite the success of mesh-based methods, the     interpolation is adopted to evaluate the field variables of each particle.
use of meshes still presents some numerical difficulties, such as mesh    These  features make SPH  ideal  for the problems involving high
distortion and domain discretisation, which hinder their applicability to     nonlinearity, a free surface and large deformations.
problems with large deformation and free surfaces, such as those       Although SPH was originally developed for astrophysical problems
encountered in granular flows and post-failure analysis of particulate    by Gingold and Monaghan (1977), and Lucy (1977), in the past decades
materials. The mesh regeneration technique (Wang et al. 2013) provides       it has been applied to a wide range of applications, including fluid dy
a possible solution for solving the mesh distortion problems in FE and FD    namics (Shao and Lo, 2003), fracture of solids (Benz and Asphaug,

 * Corresponding author.
    E-mail address: ruofeng.feng@postgrad.manchester.ac.uk (R. Feng).
https://doi.org/10.1016/j.compgeo.2021.104356
Received 10 March 2021; Received in revised form 3 June 2021; Accepted 7 July 2021
Available online 3 August 2021
0266-352X/© 2021 Elsevier Ltd. All rights reserved.

### Page 2

R. Feng et al.                                                                                                                 Computers and Geotechnics 138 (2021) 104356

1995), multi-phase flow (Colagrossi and Landrini, 2003), soil–water     of dummy boundary particles are extrapolated from their neighbouring
interaction (Bui et al., 2007), and debris flow (Pastor et al., 2009). The      soil particles by a Shepard corrected kernel function to give a zero-th
application of SPH in computational geomechanics was pioneered by     order consistency. It is also worth mentioning the work by DouilletBui et al. (2008). In their work, the elastic-perfectly plastic Drucker-     Grellier et al. (2017) and Zhao et al. (2019) on the development of stress
Prager model with associated and non-associated plastic flow rule was    boundary condition with no boundary particles. The basic idea of their
successfully implemented in the SPH scheme for the study of the post-     treatment is to complete the truncated kernel support of the particles
failure flow of cohesive and non-cohesive soils. Later, various rigorous     near the boundary with an extra stress term included in the momentum
constitutive models, such as Bingham flow model, rate-dependent vis     equation. This type of Dirichlet wall boundary condition can be applied
coplastic model, hypoplastic model, critical-state based constitutive    when boundary stresses are required, such as in the simulation of triaxial
model, and μ(I) rheological constitutive model, were incorporated into      test, Brazilian test, and penny-shaped crack problem.
the SPH framework for the modelling of different flow behaviour        Available boundary treatment techniques for geotechnical applica
(Huang et al. 2012, Prime et al., 2014, Peng et al., 2015, Yin et al., 2018,     tion of SPH can ensure only up to zero-th order consistency. The lack of
Yang et al., 2020). Furthermore, there are also several studies devoted to     consistency in boundary treatment may result in poor prediction of the
eliminate shortcomings such as tensile instability within SPH for large      stress field close to the boundaries. In addition, although many of these
deformation geomechanics problems, in which they combined SPH with    boundary methods work well for test cases with simple geometries, their
other methodologies to as in Taylor-Galerkin SPH (Blanc and Pastor,    performance has not been assessed for more complex geometries.
2013), and Stress-Particle SPH (Chalk et al., 2020).                           This work develops a new method that can minimise the spurious
   In most existing geotechnical applications of SPH, the focus was      stress field commonly involved in SPH modelling of geomechanical
primarily on the prediction of kinematics and satisfactory results were    problems and address to some of the limitations of existing boundary
obtained in comparison with experimental observations. However,     conditions. Inspired by density diffusion scheme in fluid dynamic
when analysing the stress distribution, the high-frequency short-length    (Antuono et al., 2012; Jandaghian and Shakibaeinia, 2020), which gives
oscillations are observed under the large deformation. Similar to the    a consistent numerical algorithm for removing the pressure noise and
pressure fluctuations observed in weakly compressible SPH for fluids    improving stability, the diffusion process is considered in this study to
(Molteni and Colagrossi 2009), this spurious stress field affects the ac    improve the stress field. In order to accurately resolve the stress profile
curacy and reduces the predictive capability of the SPH method since an     near the boundary while being able to handle complex geometries, the
accurate prediction of stress is very important for some practical ap     fixed ghost particle technique proposed by Marrone et al. (2011) is
plications (such as the simulation of impact of debris flow on structure).     modified in this work to treat the wall boundary condition. To the best of
   The stress regularisation technique recently proposed by Nguyen     authors’ knowledge, it is the first time for such a boundary technique
et al. (2017) provided a solution for the spurious stress field by per    extended to model the elasto-plastic solid with stress in SPH. Instead of
forming a filter over the entire domain to re-evaluate and re-assign the     using MLS interpolant to evaluate the flow quantities as presented by
stress of each particles in a certain time frequency. Nguyen et al. (2017)    Marrone et al. (2011), the corrected SPH interpolation proposed by Liu
suggested the regularisation of stress with moving least squares (MLS)    and Liu (2006) is employed to restore the first-order consistency at the
interpolants to achieve first-order correction. In their work, the regu    boundary. This procedure can be achieved within a single loop, thereby
larisation technique successfully filtered the high-frequency numerical     minimising the computational costs.
noise in the stress field. However, a common issue associated with using       The remaining part of this paper is organised as follows: Section 2
a filtering technique in SPH is that the field variables may be over-     presents a brief description of the governing equations and constitutive
filtered  for  long-time  simulations,  thereby  affecting  the  physics    model. Subsequently, the SPH discretisation of governing equations is
involved in the process being simulated (e.g., Sibilla, 2007). In addition,     given in Section 3 together with the development of a numerical diffu
the filtering procedure itself requires an extra particle sweep over the     sion term. Section 4 provides a detailed description of the first-order
entire domain, in which the computational costs are expensive, espe     consistent wall boundary treatment. In Section 5, the accuracy and
cially for a large dimension problem. Therefore, it is necessary to find an     robustness of the new SPH scheme is assessed with several validation
alternative for stress smoothing with the ability to maintain the mo     cases, including a Couette flow, simple shear test, static soil with wedge,
mentum conservation and consistency.                               2-D granular column collapse, and tunnel face collapse. Finally, the
   Another important issue associated with SPH is the treatment of the    main findings and conclusions are presented in Section 6.
boundary conditions (Vacondio et al. 2020). The accuracy and robust
ness of numerical simulation is highly dependent on the performance of     2. Numerical model
boundary conditions adopted in SPH models. For the application of SPH
in geomechanics, the most widely used boundary treatment is the one     2.1. Governing equations
proposed by Bui et al. (2008). In their work, for a soil particle near the
boundary, the stress values of the neighbouring boundary particles were        In continuum mechanics, the boundary-valued problem needs to be
assigned to be identical with that of this soil particle, giving a locally     formulated as a set of differential equations with initial/boundary
uniform stress profile near the solid boundary. The no-slip boundary     conditions. The conservation of mass and momentum for a particulate
condition was imposed by  constructing an  artificial  velocity  for     material with density ρ yields the following differential equations,
boundary particles as in Morris et al. (1997). Several corrections for
Bui’s boundary condition were proposed in the later studies. Peng et al.    Dρ = −ρ∇⋅v                                                        (1)
(2015) argued that Bui’s treatment on the stress of boundary particles     Dt
may fail to guarantee a no-penetration condition and proposed to take    Dv   1
                                              = ∇σ + f                                                       (2)the diagonal components of stress tensor of the boundary particles as the     Dt   ρ
maximum value of the soil particles of concern, while the off-diagonal
components were set to be the same; this ensured a sufficiently large    where v is the velocity, σ is the total stress tensor (which is negative for
pressure generated from the boundary. A different modification for the    compression in this study), and f is the external body force.
same issue was proposed by Chalk et al. (2020), who employed a single-       The above equations are independent of the mechanical properties of
layer of dummy wall particles that exert repulsive forces to ensure the     the particulate material and are not sufficient to complete the system of
no-penetration condition. Another possible boundary treatment relies     equations required to solve the boundary value problem. An additional
on the use of dummy particles and renormalization technique (e.g., Peng     constitutive equation is therefore needed to relate stress and strain as
et al., 2019; Yang et al., 2020). The field quantities (e.g., stress, velocity)     discussed in further detail in the following section.

                                                                        2

### Page 3

R. Feng et al.                                                                                                                 Computers and Geotechnics 138 (2021) 104356

2.2.  Constitutive model                                           )                                                                         1 (∂vα                                                                                                  ˙ωαβ =      −∂vβ                                              (11)
   In continuum mechanics, the stress and strain are tensorial quantities          2  ∂xβ   ∂xα
whose relationship is expressed in terms of constitutive equations. In the       The two-step elastic predictor-plastic corrector scheme, also known
present work, the equations are presented using the indicial notation     as return mapping algorithms is adopted for the integration of the
and Einstein convention, where  α, β and  γ denote the Cartesian     constitutive model. This procedure involves first calculating an elastic
coordinates.                                                                             trial solution by integrating the elastic constitutive equations with strain
    Elasto-plastic constitutive models have been extensively used to     increment. The predicted stress  is then examined against the yield
capture the real behaviour of soils and to simulate large deformation     function. If the stress lies within or on the yield surface, the trial solution
problems of geomaterials (e.g., Bui et al., 2008; Chen and Qiu, 2012;      is accepted, otherwise, the plastic corrector step is performed to return
Nguyen et al., 2017). The elasto-plastic constitutive relation is defined in     the trial stress to the yield surface by correcting the plastic strain
terms of a yield function and a plastic potential, or flow-rule. The yield     increment iteratively. More details of the algorithm can be found in
function f separates the purely elastic response from the elasto-plastic    Huang and Griffiths (2009).
behaviour. The plastic potential function g determines the direction of
plastic strain increment.                                                   3. SPH formulations
   The present work adopts the Drucker-Prager yield criterion with nonassociated flow rule, whose yield function and plastic potential function     3.1. SPH formalism
are given by,
     √̅̅̅̅                                                                In SPH, the integral approximation of spatial function f(x) at thef = αϕI1 +   J2 −kc                                                  (3)                                                                         point x is defined as,
     √ ̅̅̅̅                                                        ∫
g = αψI1 +   J2                                                      (4)     〈f(x) 〉=   f(x ′)W(x −x′, h)dx                                                                                                                                                                                                                                                                                                                                                           ′                                   (12)
                                                                               Ω
where I1 is the first principal stress invariant, J2 is the second deviatoric
                                                 Ω is the interpolation region, W is the smoothing kernel function,stress; αϕ and kc are Drucker-Prager constants. Their values can be    where
related to Coulomb’s material constants c (cohesion) and ϕ (internal    h is the smoothing length that defines the extent of the support domain
friction). For plane strain condition, the relation between Drucker-     of the kernel function and 〈⋯〉denotes the SPH interpolation.
Prager constants and material constants is given by,                      The discrete form of Eq. (12) can be written as,
         tanϕ                      ∑N
αϕ = √̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅                                                  (5)     〈f(x) 〉i =     fjWijVj                                             (13)
       9 + 12tan2ϕ                                                                                         j=1

kc = √ ̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅̅          3c                                                        (6)    where the subscript i and j stand for the interpolating particle and its
      9 + 12tan2ϕ                                                      neighbours, respectively, Wij = W(xi-xj, h) and fj = f(xj) are respectively
                                                                        the value of the kernel function W and the function f at the particle j with
αψ is a dilatancy factor. Its value can be related to the dilation angle ψ in     the position xj, N is the number of particles distributed in the support
a similar manner to that between αϕ and friction angle φ (Bui et al.,    domain and Vj represents the associated volume of particle j.
2014, Nguyen et al., 2017).                                                   Similar to the derivation of Eq. (13), the integral approximation of
   Substituting the yield function and plastic potential function, i.e.,     the gradient of a function ∇f(x) reads,
Eqs. (3) and (4), into the generalized form of the elastic-perfectly plastic             ∫
model shown in Appendix A, i.e, Eq. (A11), the stress–strain relationship     〈∇f(x) 〉=   ∇f(x′)W(x −x′, h)dx ′                               (14)
                                                                                 Ωfor Drucker-Prager elastic-perfectly plastic constitutive model can be
expressed as,                                                     The discrete approximation of Eq. (14) is given by,
                    [              ]
˙σαβ = 2G ˙eαβ + K˙εγγδαβ −˙λ 3Kαψδαβ + √G̅̅̅̅               ∑N                                                 sαβ                          (7)     〈∇f(x) 〉i =     fj∇iWijVj                                         (15)                                            J2
                                                                                                                    j=1
where ˙σαβ is the stress rate tensor, ˙εαβ is the strain rate tensor, ˙eαβ is the                                                              where ∇iWij=∇iW(xi-xj, h) is the derivative of the kernel function withdeviatoric strain rate tensor, G and K are the elastic shear modulus and                                                                           respect to particle i.elastic bulk modulus, respectively, δαβ is the Kronecker’s delta, sαβ is the                                                    A variety of kernel functions can be found in literature. In this study,
deviatoric stress, and ˙λ is the rate of plastic multiplier that is given by      the 5th-order Wendland kernel C2 is adopted. In studies by Robinson
                            (                       )           √ ̅̅̅̅
            G/                              sαβ ˙εαβ                                         (2009) and Dehnen and Aly (2012), it is shown the Wendland function    3αϕK˙εγγ +                         J2
˙λ =                                                                     (8)     possess a non-negative Fourier transform indicating that  it is stable         9αϕKαψ + G
                                                                           against clumping instability. The kernel function takes the following
   For large deformation problems, the Jaumann state that is invariant     form,
to rigid-body rotation is introduced. The final form of the stress–strain        ⎧  (     )4
relationship is,                                    ⎨ αd 1 −q  (2q + 1)  0⩽q⩽2
                                                                  W(q, h) =                                                                                     2                                           (16)                                  [              ]                                           ⎩
˙σαβ = σαγ ˙ωβγ + σγβ ˙ωαγ + 2G ˙eαβ + K˙εγγδαβ −˙λ 3Kαψδαβ + √G̅̅̅̅ sαβ         (9)               0                  q > 2
                                                               J2
                                                              where αd  is the normalization constant. In one-, two- and threewhere the strain rate tensor ˙εαβ and the spin rate tensor ˙ωαβ can be     dimensional space, αd  is equal to 3/4h, 7/(4πh2), and 21/(16πh3)
related to velocity gradient from kinematic relations according to           respectively and q is the dimensionless distance between points at x and
           )                                                                      x′, defined as q =|x - x′|/h.     1 (∂vα   ∂vβ
˙εαβ =    +                                                  (10)     2  ∂xβ   ∂xα

                                                                        3

### Page 4

R. Feng et al.                                                                                                                 Computers and Geotechnics 138 (2021) 104356

Fig. 1. Generation of boundary particles, b, (grey circles) and ghost nodes, g, (crosses) in flat surface and corner (soil particles are coloured by blue, those included in
kernel summation of ghost nodes are coloured by orange). (For interpretation of the references to colour in this figure legend, the reader is referred to the web version
of this article.)

                                                                         gradient and divergence operators used in Eqs. (17) and (18) are skew-
                                                                            adjoint for the benefit of energy conservation (Mayrhofer et al. 2013).
                                                                                                         It is well known that SPH exhibits unphysical oscillation and nu
                                                                       merical instability if a numerical dissipative term is not included in the
                                                                    governing equations (Antuono et al. 2012). To dissipate these numerical
                                                                                fluctuations, an artificial viscosity term is required to be added in the
                                                     momentum equation. This term was firstly designed to handle shocks
                                                               (Monaghan, 1992) and has been found to stabilise the numerical algo
                                                                          rithm. In this study, the artificial viscous term is introduced into the
                                                                         pressure term of the momentum equation in the following way,
                                                     (                                                               )
                                                                                           N                                                                  〈dvα 〉  ∑                                                                                                                         ∂Wij                                                                                                        σαβi + σαβj                                                 =     mj          −Πijδαβ    + gα                   (19)
                                                                                         dt      i       j=1         ρiρj              ∂xβi

Fig. 2. Numerical set-up of the Couette flow case, in which soil particles (SPs)    where
                                         ⎧and boundary particles (BPs) are marked as dark blue and light grey.
                          ∏                                         ⎪⎪⎪⎨ −α∏cijμij + β∏μij   vαijxαij < 0
                                                                                                                                               ρij                                              =                                                                                                                                    (20a)3.2. SPH discretization of governing equations
                                                                                                                                                                                             ij                                         ⎪⎪⎪⎩                                                                                  0            vαijxαij > 0
   With the use of standard SPH divergence and gradient operator, the
governing equations (1) and (2) take following form,                               hvαijxαij
                                                                                                                  μij = (                                                                                                                                 (20b)                                                                                                )2
                                                  + η2〈dρ 〉  ∑             N  mj (     ) ∂Wij                                                                                          xαij    = ρi         vαi −vαj                                        (17)
  dt     i       j=1 ρj           ∂xαi
                                                                                                                             cij = 0.5(ci + cj)                                                (20c)
〈dvα 〉     1 ∑                N  mj (         ) ∂Wij     =            σαβi + σαβj    + gα                          (18)        ρij = 0.5(ρi + ρj)                                             (20d)
   dt      i      ρi  j=1 ρj             ∂xβi
                                                                    with αП and βП are empirical constants used to control the magnitude of
where, for a field function f, the subscript ij denotes the difference in     viscous dissipation and normally take values from 0 to 1. According to
value in the function  fij =  fi-fj and g is the gravitational force. The    Monaghan (1992), the first term with αП produces a shear and bulk

Table 1
Adopted parameters in case study.
  Parameters                   Unit           Adopted values for test cases
                                            Element shear tests                                    Static dry soil                   Granular flow                   Tunnel
                                               Couette flow          Simple shear test            Flat         Wedge          Case1          Case2
  h/dp                        –                2.2                    2.2                        1.8             1.8              1.8             1.8              1.8
  Diffusion coefficient          –               –                    –                          0.1             0.1              0.1             0.1              0.1
  Viscous coefficient           –                1.0                    1.0                        0.1             0.1              0.1             0.1              0.1
  Courant number             –                0.2                    0.2                        0.2             0.2              0.2             0.2              0.2
  Density                   kg/m3         2100               2100                  2100         2100          1850          2079.5          2212.03
  Elastic modulus           MPa             5.0                   10.0                      15.0           15.0            10.0           5.84            5.84
  Possion ratio                 –                0.3                    0.3                        0.3             0.3              0.3             0.3              0.3
  Friction angle               deg             –                  30                    25           0             22             21.9            21.9
  Cohesion                  kPa            –                  20                    0             –             0             0             0
  Dilatancy angle             deg             –                  0                     0             –             0             0             0

                                                                        4

### Page 5

R. Feng et al.                                                                                                                 Computers and Geotechnics 138 (2021) 104356

                    Fig. 3. Velocity profile of Couette flow: (a) comparison against analytical value and (b) velocity contour (m/s) at t = 5 s.

                                                 (                        )
       0.1                                                                  1 ∑N  mj (     ) ∂Wij ∑N  mj (       ) ∂Wij
                                                               +                                                                                                                                         vβj −vβi                                                                                                                                       (22)                                                                                                                                                                                                                                                 j −vαi
                                                                                                                                     ∂xαi                 Present treatment                                                   〈˙εαβ〉i =  2    j=1 ρj  vα                                                                                                                                                     j=1 ρj                                                                                                                 ∂xβi                      First order
                                                                          )                                                 (               Second order      velocity.x                                                                             1                            ∑N  mj (     ) ∂Wij ∑N  mj (       ) ∂Wij
                                                                                                                                                                                                    −                                                                                                                                          vβj −vβi                                                                                                   〈˙ωαβ〉i =                                                                                                                                       (23)                                                                                                            vαj −vαi of 0.01                                                                                                                                      ∂xαi                                                                                                                  ∂xβi                                                                             2    j=1 ρj                                                                                                                                                      j=1 ρj
   error
  norm                                                                           3.3.  Stress diffusive term
     1E-3 L2                                                                Although SPH can capture well the kinematics of geomaterial under
                                                                            large deformation, there are still some drawbacks on the prediction of
                                                                        the stress field due to the presence of high-frequency noise. This issue
                                                                  can be attributed to the collocated nature and lack of consistency of SPH.      Normalized 1E-4                                             When the initial conditions are released in the early stages of simulation,
                   0.01                                 0.1       numerical oscillations or fluctuations are appear which cannot be
                            dp                                   dissipated without an artificial dissipative term. Following the idea of
                                                                          density diffusive term, which has been shown to provide excellent re
Fig. 4. Normalised L2 error norms of the velocity at t = 5 s for Couette flow.      sults in fluid dynamics (e.g., Molteni and Colagrossi 2009, Antuono et al.
                                                                      2012), a stress diffusion term is investigated in this study and included in
viscosity whereas the second term with βП is analogous to the Von     the stress equation, for the purpose of giving a more accurate and
Neumann-Richtmyer viscosity for high Mach number flow. For the    smoother stress profile.
modelling of geomaterials, the value of βП contributes  little to the        In order to achieve a smoothing process, according to Antuono et al.
dissipation and thus can be omitted (Mao et al., 2017). The factor η =     (2012), the diffusion term should approximate even derivatives of
0.1 h is inserted to the denominator to avoid numerical singularity. The     physical field, for example, a Laplacian operator, and it should vanish as
speed of sound c of the material, is computed according to,                the numerical accuracy increases to avoid unphysical behaviour and to
  √̅̅̅̅̅̅̅̅̅̅                                                             recover the consistency (hence the diffusion term should be multiplied
ci =   Ei/ρi                                                    (21)    by smoothing length h to make its influence decrease when the spatial
                                                                            resolution increases). Meanwhile, the diffusion term should be defined
where E is Young’s modulus of the soil.                                     to  satisfy  the  global  conservation  of  momentum,  and  global
   Furthermore, the equations for strain rate and spin rate of Equations     convergence.
(10) and (11) in SPH formulism are given by,                                Accordingly, the diffusion term proposed by Antuono et al. (2012)
                                                                    has a general form as follows,

          Fig. 5. Simple shear experiment for testing the Drucker-Prager elasto-plastic model in SPH (a) model set-up; (b) the obtained velocity profile.

                                                                        5

### Page 6

R. Feng et al.                                                                                                                 Computers and Geotechnics 138 (2021) 104356

                   Fig. 6. Results of simple shear tests with varying confining stresses: (a) stress path and (b) shear stress–strain relationships.

                                                                   (2009) can be modified as,
                                                                           ψαβij = σαβi −σαβj                                                   (27)
                                                                  As shown by Antuono et al. (2012), the use of Eq. (27) leads to,
                                                                        Dαβi  = 2∇σαβi ∇Γi + Γi∇2σαβi + O(h)                              (28)
                                                              where

                         ∑N    ∑N
                                                                                        Γi =     WijVj, ∇Γi =    ∇iWijVj                                 (29)
                                                                                                            j=1                  j=1
                                                                                                         It can be seen that Eq. (28) involves a Laplacian operator that acts as
                                                                        the diffusion term, and also a first-order differential operator. For the
                                                                                particle inside the bulk domain ∇Гi ≈0, the first term vanishes and the
                                                                              diffusion term can well approximate the Laplacian of the stress field.
                                                                However, it presents a problem for the particle with incomplete kernel
                                                                      support such as those close to the free surface, in which the first term is
                                                                         non-zero. Consequently, the formulation by Molteni and ColagrossiFig. 7. Static soil column (a) model set-up, in which soil particles and boundary                                                                   (2009) is no longer consistent near the free surface, causing a change ofparticles are marked as dark blue and light grey, respectively; (b) vertical stress
contour. (For interpretation of the references to colour in this figure legend, the      stress along the free surface. The resulting effect is not obvious for a
reader is referred to the web version of this article.)                        dynamic condition since the dynamic stress involved could be many
                                                                         orders of magnitude higher than this term, but it is important for static
   ∑   xji⋅∇iWij mj                                                cases as will be shown later.
Di = 2ζhc0                  ψji                                                               (24)       To recover a global convergence, the diffusion operator expressed in                  x2ji + η2  ρj                             j                                                                        Eq. (27) can be corrected according to Antuono et al. (2010), which
                                                                             reads,where ζ is the coefficient used to control the magnitude of diffusion and
normally take values as 0.1 for most application. The parameter ψji is a     ψαβij = ( σαβi −σαβj ) −1 (〈∇σαβ〉Lj + 〈 ∇σαβ〉Li )⋅xij                   (30)diffusion operator and changes for different formulations. It has the                      2
dimension of the physical quantities to be diffused.                              〈          〈
   Under the hypotheses made above, the stress rate equation (9)    where ∇σαβ〉Lj and ∇σαβ〉Li are the renormalised stress gradients defined
should be written as,                                                      as
                                                                                                                                                                (                                                                                                 )                                                                                                          mjDσαβ                                                                                                    Li∇iWij                                                                                                    σαβj −σαβi                                                                                                                                    (31a)                                                                        〈 ∇σαβ〉Lj = ∑       i = Dep ˙εαβi + Dαβi                                              (25)                                                                                                                                            ρj                                                                                                                                                                                                                         j Dt
where Dep is the elasto-plastic stiffness matrix and Dαβi   is the new stress    (∑(      )        mj )−1
diffusion term defined for each stress component as                           Li =         xj −xi ⊗∇iWij                                    (31b)                                                                                                                                                                                                               j                       ρj
    ∑       xij⋅∇iWij   mj
Dαβi = 2ζhc0
                                j               ψαβij  ⃒⃒xij ⃒⃒2 + 0.01h2 ρj                               (26)           It can be seen that with the use of Eq. (30), the first-order differential                                                                 term vanishes, and the resulting diffusion term can reproduce the Lap
   Eq. (26) is evaluated in particle interactions and contributes to the     lacian of stress within the whole domain. Nevertheless, there is a rela
stress integration.                                                              tively large computational cost for the evaluation of renormalised stress
   There are several options to construct the diffusion operator. The     gradients.
most easily applied form is the one proposed by Molteni and Colagrossi        In this study, following the idea of the diffusion algorithm recently
(2009) which adopts the SPH Laplacian operator by Morris et al. (1997).    proposed by Fourtakas et al. (2019), Eq. (27) is modified to restore
For the diffusion of stress field, the formula by Molteni and Colagrossi     consistency within the whole domain while avoiding computing the

                                                                        6

### Page 7

R. Feng et al.                                                                                                                 Computers and Geotechnics 138 (2021) 104356

Fig. 8. Normalised vertical stress profile at final instant (t = 5 s) for the different resolutions dp = 0.1 (first row), dp = 0.05 (second row), and dp = 0.02 (third row)
using the boundary treatment by Bui et al. (2008) (left) and present boundary treatment (right).

normalised stress gradient. This is achieved by using the dynamic stress     of the stress tensor. The final form of stress diffusion operator can be
rather than the total one in the diffusion term, which is given by,          expressed as,
                                      ⎧
                                                                             ψαβij = σαβij          α ∕= βψαβij = σαβ.Di   −σαβ.Dj                                                 (32)   ⎪⎪⎪⎪⎪⎪⎨   Since σαβ.D =  σαβ −σαβ.S, Eq. (32) can be rewritten as,                       ψxxij = σxxij −K0ρ0gzij                                                                                                                                       (34)
                                               =                                                                                                     σyy                                                                                                                                                                                                    ij                                                                                                                                                                                                                  ij                                                                                   −K0ρ0gzijψαβij = σαβij −σαβ.Sij                                                  (33)
                                                                                                            σzz                                      ⎪⎪⎪⎪⎪⎪⎩ ψyyψzz                                                                                      −ρ0gzij                                                                                                                                                                                                    ij =                                                                                                                                                                                                                  ij
where the superscript D and S refers to dynamic and static components,
respectively.                                                    where K0 is Jaky’s earth pressure coefficient at rest that will be defined
   Assuming the shear stress of soil at static condition is zero, this      later in Section 5.
modification only affects the diffusion operator for diagonal component

                                                                        7

### Page 8

R. Feng et al.                                                                                                                 Computers and Geotechnics 138 (2021) 104356

                           Fig. 9. Normalised vertical stress profile with zeroth-order boundary treatment (a) dp = 0.05; (b) dp = 0.02.

                                                                                         Fig. 12. Static dry soil with wedge: normalized stress contour at 10 s.

                                                                    time step. Further details of the time-stepping scheme can be found in
Fig. 10. Static soil column: normalised L2 error norms of vertical stress at 5 s.                                                                   Crespo et al. (2015).
                                                                The time-stepping schemes is restricted by the CFL (Courant–Frie
                                                                        drichs–Levy) condition, the maximum force term, and the numerical
                                                                   speed of sound. The variable time step  is calculated according to
                                                            (Monaghan and Kos, 1999),
                                                                (√ ̅̅̅̅̅̅̅̅̅̅ )
                                                                                      Δtf = min                                                                                                             h/|fi|                                            (35a)
                                                                                                                                                                                                             i

                                                                                  h
                                                                                     Δtcv = min                                                                                                                                                                                                               i                                                    (35b)
                                                                                                                                                                                              hvij⋅xij
                                                                                                              cs + max                                                                                                                                                                                                                                   j           ⃒⃒⃒⃒⃒                                                                                                                                                  x2ij+η2 ⃒⃒⃒⃒⃒

                                                                                                                                                           (        )
                                                                    Δt = C0min Δtcv, Δtf                                            (35c)

                                                              where Δtf  is the time step governed by forces, Δtcv the time step
                                                                                 restricted by the Courant and the viscous controls since the artificial
  Fig. 11. Schematic diagram for the static soil in a container with wedge.        viscosity is used in this study, f is the force per unit mass, cs is the sound
                                                                   speed of the material, C0 is the Courant number set to be 0.2.
3.4. Time-stepping scheme
                                                                           4. Wall boundary treatment
   The time integration scheme adopted is an explicit second-order
predictor–corrector scheme to integrate Equations (17) (19) (22) (23)      A common problem of SPH is the kernel truncation of particles near
and (25) in time. In this scheme, the predictor step evaluates the evo     the boundary. Due to the interpolation nature of SPH, the truncated
lution in time at the middle of the time step by Euler forward stepping,     kernel support may lead to inaccurate results and unphysical effects. At
and the obtained values are then corrected using the updated forces in     present, a particle-based treatment is widely used in which, a set of
the corrector step. The results obtained from the corrector step are      fictitious particles is created to characterize the boundary of simulated
finally used to evaluate the values of these variables at the end of the    domain. Their properties contribute to the SPH summation of real par
                                                                                        ticles near the boundary to ensure the kernel is fully supported.

                                                                        8

### Page 9

R. Feng et al.                                                                                                                 Computers and Geotechnics 138 (2021) 104356

Fig. 13. Static dry soil with wedge: normalised vertical stress profile at 10 s with stress diffusion term (x = 1.4 m). The boundary contribution to the diffusion term is
not considered in (a) and (b) whereas it is considered in (c) and (d).

                                                                                     Fig. 15. Schematic diagram of the initial configuration of collapsing granular
                                                                    column problem.

                                                              To arrange the boundary particles for arbitrary shaped geometries,
                                                             two options can be considered. One is to use a cubic lattice to place
Fig. 14. Static dry soil with wedge: normalised L2 norm error of vertical stress    boundary particles as shown in Fig. 1, and the other is to generate
at 10 s.                                                                     several layers of boundary particles offset from the physical boundary
                                                                                       lines. The first option is more suitable for angles of 45◦or 90◦as a
   In this treatment, the building block of the mDBC (modified dynamic     staircase effect can result with other angles. In such a condition, the
boundary condition) proposed by English et al. (2021), which combines    second option can be adopted.
the use of dummy and ghost particles, is introduced with some modifi        For each boundary particle, a ghost node (or interpolation point) is
cations. The solid wall is discretised with dummy particles. Boundary     projected into the soil domain in a similar manner to Marrone et al.
particles are placed with the same initial particle spacing dp as real     (2011). The position of a ghost particle is calculated according to the
particles shown in Fig. 1 but unlike mDBC their properties do not evolve     direction of the boundary normal and the normal distance of boundary
in time.                                                                        particle to the boundary surface. For a flat or curved surface, this

                                                                        9

### Page 10

R. Feng et al.                                                                                                                 Computers and Geotechnics 138 (2021) 104356

              Fig. 16. Vertical stress contour of 2-D granular flow with the diffusion term (left column) and without diffusion term (right column).

                                                                      technique is straightforward while it presents some difficulties for cor
                                                                         ners and may require the ghost node to be projected through the corner
                                                                         point according to the distance and direction of the boundary particle to
                                                                        the corner.
                                                                The velocity and stress of ghost nodes (denoted by the subscript g)
                                                                         are interpolated from neighbour soil particles, and then feedback to the
                                                                      corresponding boundary particles (denoted by the subscript b). The
                                                                                    stress and stress gradients of a ghost particle are computed using the
                                                                                   first-order consistent SPH interpolant proposed by Liu and Liu (2006),
                                                            ⎡ ∑      ⎤
                                                                                                          σαβj WgjVj
                                                     ⎡    ⎤                  j
                                                                                          σαβg   ∑                                                                                                         σαβj ∂xWgjVj
                                                                                        ∂xσαβg                      j
                                                                         Ag⋅     = ∑                                            (36)
                                                                                        ∂yσαβg                                                                                                         σαβj ∂yWgjVj                                                                                                                                                                                                                                                                                                                                                                                                                  ⎥⎥⎥⎥⎥⎥⎦                                                                                                                                                                                                                                                                                                                                                                                 ⎢⎢⎢⎢⎢⎢⎣
                                                                                                                                                                                                                                       j                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                ⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎥⎦                                                                                          ∂zσαβg                                               ⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎢⎣ ∑
                                                                                                         σαβj ∂zWgjVj
                                                                                                                                                                                                                                       j

                                                              where the renormalisation matrix Ag is              Fig. 17. Vertical stress profile of the final deposit.

   ∑   ∑(      )   ∑(      )   ∑(      )
     ⎡     WgjVj            xj −xg WgjVj            yj −yg WgjVj             zj −zg WgjVj ⎤
   ∑j   ∑j (     ∑j (     ∑j (            ∂xWgjVj          xj −xg )∂xWgjVj          yj −yg )∂xWgjVj          zj −zg )∂xWgjVj
Ag = ∑j   ∑j   (     ∑j   (     ∑j   (                                                                        (37)            ∂yWgjVj          xj −xg )∂yWgjVj          yj −yg )∂yWgjVj           zj −zg )∂yWgjVj                                          ⎢⎢⎢⎢⎢⎢⎢⎢⎣ ∑                         j   ∑j   (     ∑j   (     ∑j   (                                                                                                    ⎥⎥⎥⎥⎥⎥⎥⎥⎥⎦             ∂zWgjVj          xj −xg )∂zWgjVj          yj −yg )∂zWgjVj          zj −zg )∂zWgjVj
                         j                              j                                                  j                                                  j

                                                                        10

### Page 11

R. Feng et al.                                                                                                                 Computers and Geotechnics 138 (2021) 104356

Fig. 18. Comparison between the numerical simulation and the experiment for 2-D granular column collapse progress (red line denotes the experimental profile, a =
0.5). (For interpretation of the references to colour in this figure legend, the reader is referred to the web version of this article.)

Fig. 19. Comparison between the numerical simulation and the experiment for 2-D granular column collapse (red line denotes the experimental profile, a = 1.0).
(For interpretation of the references to colour in this figure legend, the reader is referred to the web version of this article.)

                                                                        11

### Page 12

R. Feng et al.                                                                                                                 Computers and Geotechnics 138 (2021) 104356

                    Fig. 20. Comparisons of the free-surface line between SPH simulation and experimental data (a) a = 0.5 and (b) a = 1.0.

                                                                dominated and non-singular even for very disordered particle distribu
                                                                                   tions. Yet, it is still possible to be ill-conditioned and the renormalisation
                                                                      matrix collapses to the zeroth order consistent SPH interpolant (Shepard
                                                                              function), given by,
                                      ∑
                                                                                                               jσαβj WgjVj                                                                                   σαβb =  σαβg = ∑                                               (39)
                                                                                                      jWgjVj
                                                                               In order  to recover the  static equilibrium condition near the
                                                                boundary and produce considerable repulsive forces to prevent particle
                                                                         penetration for this zeroth-order interpolation, the diagonal component
                                                                              of final stress tensor is corrected in a manner similar to Adami et al.
Fig. 21. Computational set-up of the tunnel model (soil particles and boundary    (2012) according to the force balance at equilibrium state, which is
particles are marked as blue and red). (For interpretation of the references to     given by,
colour in this figure legend, the reader  is referred to the web version of      σzzb = σzzg −ρ0gzbg                                              (40a)this article.)
                                                                                           σxxb = σxxg −K0ρ0gzbg                                           (40b)
Table 2
Geometric parameters of the tunnel model.                                             σyyb = σyyg −K0ρ0gzbg                                             (40c)
  Parameters                             Notations                      Values         The above procedure requires the calculation of the inversion of the
  Total length                          L                          42 cm        matrix Ag and the stress summation vector, in which a single extra loop
  Tunnel length                                 Lt                         12 cm           is needed. The computational overhead is similar with the boundary
  Tunnel diameter                 D                         8 cm         treatment using renormalization technique (e.g, Peng et al. 2019, Yang
  Overburden depth               H                                  8, 16 cm       et al. 2020) but it is slightly larger than those using the uniform stress
                                                                      technique (e.g., Bui et al. 2008). However, it can create smoother and
   The final stress value of the boundary particle σb is evaluated ac    more physical stress profile as will be demonstrated at later sections.
cording to the stress and stress gradients at ghost nodes using a Taylor       To create a free-slip/no-slip boundary condition, the velocity at the
series expansion,                                                       ghost nodes is calculated using Shepard corrected summation,
                                  ∑                    (                           (                           (
                                                                                                                                                                                                                 j WgjVj                                                 (41)σαβb = σαβg +  xb −xg )∂xσαβg +  yb −yg )∂yσαβg +  zb −zg )∂zσαβg           (38)      vαg = ∑jvα
                                                                                            jWgjVj
    It should be noted that although the matrix Ag  is diagonally-

                                                                        12

### Page 13

R. Feng et al.                                                                                                                 Computers and Geotechnics 138 (2021) 104356

            Fig. 22. Comparison between the numerical simulation and the experiment for 2-D tunnel face collapse (a) H/D = 1.0 and (2) H/D = 2.0.

                             Fig. 23. Comparison with experimental data (H/D = 1.0) for (a) face extrusion and (b) ground surface.

   To guarantee a no-slip condition at the boundary interface, the ve     reversed,
locity of ghost nodes is assigned to corresponding boundary particles                                                                                    vαb = vαg −2vαg.n                                                  (43)with reversed direction,
vαb = −vαg                                                       (42)    where the subscript n denotes the normal component.
                                                                              Similar to Bui et al. (2008), the density of boundary particles is set to
   For a free-slip condition, the boundary particle obtains the ghost                                                                 remain constant at the reference density ρ0.node tangential velocity whereas the normal ghost node velocity is

                                                                        13

### Page 14

R. Feng et al.                                                                                                                 Computers and Geotechnics 138 (2021) 104356

                             Fig. 24. Comparison with experimental data (H/D = 2.0) for (a) face extrusion and (b) ground surface.

    It’s worth noting that the proposed boundary condition is different       Note that a relatively large h/dp is used in all cases to improve the
from a mirror boundary condition that projects domain particles into     accuracy of the results. In addition, this selection is beneficial for the
boundary, in which the normal vectors or position of mirror boundary     study of convergence behaviour since total error is operated in the
particles need to be re-evaluated every time step. As we mirror boundary     smoothing-error dominated regime (Quinlan et al. 2006), and  it  is
particles to the domain and the boundary particles are fixed in space in     possible to achieve convergence with the refinement of dp.
present methodology, there is no additional efforts for computing the
position of mirrored ghost nodes during the simulation (position of ghost     5.1. Element shear test
nodes are fixed). The computations of the position of ghost nodes need to
carefully evaluate the normal vectors at the beginning of the simulation,     5.1.1. Implementation of no-slip condition: The Couette flow
which slightly increases the efforts for the initialisation of simulation,       The Couette flows of linear elastic material are simulated to examine
but the resulting boundary treatment gives improved accuracy and     the ability of the new boundary treatment to produce a no-slip boundary
consistency.                                                               condition. Fig. 2 shows the numerical set-up, which consists of two
   In addition, the periodic boundary condition (PBC) and the dynamic     horizontal boundary walls placed at z = -0.5 m and z = 0.5 m,
boundary condition (DBC) are also used in this study. PBC is adopted for     respectively.
the modelling of Couette flow and static dry soil column to produce a       The bottom wall is fixed whereas the top one moves with a velocity
uniform deformation. The DBC is used for the simulation of simple shear     vx = 0.001 m/s. The initial particle spacing is set to 0.04, 0.02, and 0.01
test solely to create a pure shear deformation. When using the DBC,    m, resulting in 25, 50, and 100 particles across the height of the domain.
dummy particles are employed for the discretization of wall boundary.     Periodicity is applied horizontally to ensure a uniform shear deforma
When adapted for our scheme, density, stress and strain of these      tion. The parameters adopted in the simulation are listed in Table 1. A
boundary particle share the same governing equations with soil particles     relatively large artificial viscosity parameter is used in this case to
and evolve with time, but the position of boundary particles is either     dissipate the numerical oscillations in the calculation of the momentum
fixed in space or moving with the prescribed wall boundary velocity.      and to stabilize the simulation. It is finally noted that gravity is not
                                                                       considered in the present simulation.
                                                                            = 5.0 s for the5. Validation of the proposed numerical model                              Fig. 3 shows the velocity field in the x direction at t
                                                                            coarsest resolution. The particle velocities at steady state after t = 5.0 s
   The numerical scheme described above is implemented in the CPU     are plotted against the corresponding analytical solution in Fig. 3(a).
version of the open-source SPH solver DualSPHysics (Crespo et al 2015)    From the comparison it can be seen that a satisfactory agreement has
and validated against several test cases, including Couette flow, simple    been achieved with the L2 norm error less than 0.75%. The convergence
shear test, and static dry soil column. Finally, the proposed method is     behaviour of velocity at steady state is shown in Fig. 4 with the order of
applied to study 2-D granular column collapse and tunnel face collapse.    convergence of approximately 1.21, indicating that the no-slip condition
In this study, the Jaky’s equation for the earth pressure coefficient at      is adequately reproduced with the new boundary treatment.
rest,  i.e., K0 = 1-sinφ, is adopted for the numerical diffusive term
expressed in Eq. (32) and zero-th order boundary treatment.

                                                                        14

### Page 15

R. Feng et al.                                                                                                                 Computers and Geotechnics 138 (2021) 104356

                                                     (                                                               )5.1.2. Validation of Drucker-Prager constitutive model: Simple shear test                                                                                           N                                                                  〈dvα 〉  ∑                                                                                                        σαβi + σαβj   To validate the implementation of the Drucker-Prager elasto-plastic        =     mj      + Πijδαβ  ∂Wij + gαi + dαi               (44)
model, the simulation of a series of simple-shear tests are conducted and        dt      i       j=1         ρiρj              ∂xβi
compared against analytical solutions. Fig. 5 shows a sketch of simpleshear test set-up and  its numerical implementation. The numerical    where d is the damping force term given by,
domain is square shaped with length of 0.1 m. The soil particles are      √̅̅̅̅̅̅̅
placed in the centre of the simulated domain with the boundary particles     dαi = −ξ  E vαi                                                 (45)
enclosing the central area. Since the relationship between stress and                ρh2
strain is independent of the particle spacing, a relatively coarse particle                                                                   Note that, the damping process is only considered when obtainingresolution is adopted. The initial particle distance dp is 0.01 m, resulting                                                                        the stress profile at static condition. For a dynamic case with particlein a total of 100 particles. The parameters and soil properties adopted in                                                                     motion, the damping term should be switched off as it will lead tothe simulation are listed in Table 1. The confining pressure is applied by                                                                       unphysical energy dissipation.assigning an initial mean principal stress for all the particles. Three                                                                                    Particles coloured by the vertical stress in the soil column at the finallevels of initial confining stress of 150, 225, and 300 kPa are tested.                                                                              instant are shown in Fig. 7(b). Fig. 8 shows the final distribution of  A constant velocity profile is prescribed for the boundary particles                                                                                 vertical stress with depth for different boundary treatments and particleand maintained throughout the simulation. DBC is adopted for this                                                                               resolutions.application to enable the pure shear deformation of boundary particles.                                                                                                         It can be seen that for the treatment by Bui et al. (2008), the stressIt has been a common choice for testing constitutive model in SPH (e.g.,                                                                              distribution near the boundary diverges from the analytical solution.Nonoyama et al. 2015; Zhao et al. 2019). Our aim of this test case is not                                                                        This discrepancy is clear for a large particle spacing. By contrast, theto investigate the effectiveness of the wall BCs but the validity of the                                                                   proposed boundary treatment results in a stress distribution closer to itsstress–strain relationship. The new BCs are demonstrated in other cases.                                                                              analytical value even for the lowest resolution of 0.1 m.In the horizontal direction, the velocity of the boundary particles is                                                                        Furthermore, the zero-th order option of the presented boundarygiven by of vx = 0.01z where z denotes the vertical distance from the                                                                        condition using Eq. (39) is also tested. The comparison between nucentral axis. A zero-vertical velocity, vz = 0 m/s, is prescribed for the                                                                       merical and analytical results is shown in Fig. 9. Similar to the boundaryboundary  particles,  corresponding  to  a  constant  shear  rate  of                                                                      treatment by Bui et al. (2008), there are fluctuations in the stress field˙γxz = 1.0%/s. The gradient renormalization technique, Eqs. (36)-(38),                                                                     near the boundary when using the presented zero-th order boundaryis applied in the calculation of strain rate equation to create an accurate                                                                      treatment since the stress value at the boundary is not accurately solved.prediction of strain rate. The calculated stress and strain of the single                                                                           In spite of that, the proposed treatment can still provide sufficient acparticle at the centre of the specimen are recorded throughout the                                                                     curacy when the first-order interpolation cannot be attained due to illsimulation.                                                                       conditioned matrices of Eq. (37).   The simulations are conducted assuming zero gravity. The Jaumann                                                                               In addition, the normalized L2 error norms of vertical stress for threerate is not considered in this simulation since the deformation of the                                                                                different particle resolutions are presented in Fig. 10. Clearly, both thespecimen is relatively small. The stress path and shear stress–strain re                                                                          zeroth-order and first-order boundary treatment show a convergentlationships at the centre of soil domain are plotted in Fig. 6 together with                                                                    behaviour with the refinement of particle spacing.the analytical solutions. From Fig. 6(a)  it can be seen the  initial
confining stress keeps constant until the stress state reaches the yielding                                                                                 5.2.2. Validation of complex geometries: The container with a wedgeline. The stress state remains on the yield surface after yielding, indi                                                                The simulation of static soil in a container with wedge is performedcating the consistency condition for elastic–plastic model is correctly                                                                            to demonstrate the ability of the presented boundary condition to handlereproduced. The obtained stress–strain relationship (Fig. 6b) agrees well                                                                        the complex geometry, such as the discontinuous points and slopeswith the analytical solution, demonstrating that the constitutive model                                                                       within the domain. As shown in Fig. 11, the container has dimension ofimplemented in DualSPHysics is able to produce the appropriate stress                                                            2 × 1.2 m and a triangular wedge is placed at the centre with a height ofstate with high accuracy.                                                                        0.4 m and π/4 rad angle. The initial soil height is set to be H = 1 m with
                                                               an initial soil density of 2100 kg/m3. The initial particle spacings for this5.2.  Static dry soil                                                                        case are taken as dp = 0.08, 0.04 and 0.02 m. The free-slip condition is
                                                                        applied for the side wall, and no-slip condition is enforced for the bottom5.2.1. Implementation of boundary conditions: The soil column test                                                                        wall using the proposed boundary conditions. Table 1 lists the param   The simulation of the static soil column with level ground is per                                                                                eters adopted. To obtain an analytical solution with such a complexformed to study the performance of the presented boundary condition                                                                boundary geometry, the elastic constitutive model is used in this caseunder stress increment. The model setup is shown in Fig. 7(a). Periodic                                                              and the shear modulus is set as zero (hence the deviatoric stresses are notboundaries are applied to both sides to reproduce the infinite lateral                                                                           considered), making the materials behave like a fluid. The proposedextent of the soil column. The depth of the soil layer is H = 1 m. Three                                                                                    stress diffusion term is also applied for this application, together withsets of particle resolutions of 0.1, 0.05 and 0.02 m are adopted, resulting                                                                        the use of diffusion operator proposed by Molteni and Colagrossi (2009)in 10, 20 and 50 particles along the column height, respectively. The no-                                                                                for comparison. Further, the damping algorithm of Eq. (44) is used toslip solid boundary condition proposed by Bui et al. (2008) is also used                                                                                      settle down initial numerical oscillations.for comparison with the proposed boundary condition treatment. Sim                                                                                      Fig. 12 shows the normalized vertical stress field at the final instant.ulations are conducted for 5 s of physical time. More details of the                                                                           Evidently, the use of present boundary treatment produces a smooth andadopted model and parameters can be found in Table 1.                                                                        accurate stress profile, not only in the flat surface but also in the corners.   As observed in previous studies (e.g., Bui and Fukagawa, 2013; Mao                                                                The vertical stress profile of soil particles at x = 1.4 m using the stresset  al. 2017), the sudden application of a force  (e.g., gravitational                                                                              diffusion term with Molteni and Colagrossi operator and the formulationloading) to the soil body results in high-frequency stress oscillation. To                                                                   proposed in this study is shown in Fig. 13. In Fig. 13(a), the diffusionsettle down the system to an equilibrium state, the damping term                                                                 term is only applied for the soil-soil interaction. The artificial diffusion(equation 52) developed by Bui and Fukagawa (2013), with damping                                                                 term of Molteni and Colagrossi operator shows a variation of stress nearcoefficient of ξ = 0.02, is introduced into the momentum equation as,                                                                   both the free-surface and wall boundary, which is caused by the lack of
                                                                         consistency of the operator with truncated kernel support at the surface.
                                                                                                       If the contribution of boundary particles is considered to complete the

                                                                        15

### Page 16

R. Feng et al.                                                                                                                 Computers and Geotechnics 138 (2021) 104356

kernel support of the diffusion term near the boundary, the variations of       To evaluate the accuracy of numerical scheme, a series of numerical
stress can be improved as shown in Fig. 13(c). However, it should be      tests is performed and compared with the experimental results presented
noted that the correct diffusion near the boundary requires the boundary    by Nguyen et al. (2017). The adopted material properties are from the
condition to be of sufficient accuracy. For the boundary condition where     original work and are summarised in Table 1. Two sets of initial aspect
the stress value  is not accurately resolved,  it  is possible to induce     ratio a (the ratio of the initial height to the initial width) of 0.5 and 1.0
unphysical diffusion along the soil-boundary interface  if the  soil-     are investigated, corresponding to the size of 20 × 10 cm and 10 × 10 cm
boundary interaction is included in the diffusion term.                  domain. The boundaries are assumed to be non-slip at the bottom and
   This problem can be improved by using the proposed modified     the side wall. The particle resolutions for this test series are dp = 0.002,
diffusion operator of Eq. (34). In Fig. 13(b) and (d), good agreement    0.001 and 0.0005 m, resulting in 5000, 20000, and 80,000 soil particles.
between numerical and analytical results are achieved regardless if the         Figs. 18 and 19 show the velocity profiles of the granular flows with
boundary contribution considered. Evidently, the use of the proposed     the discretised medium obtained from the simulation at several time
diffusive algorithm is able to restore the consistency for particles with     instants. The free-surface line from the experiment is also plotted for
incomplete kernel support.                                            comparison. The difference between numerical and experimental results
  A convergence study on the normalised L2 error of vertical stress is      is quantified as Gomez-Gesteira et al. (2010),
shown in Fig. 14. Although the orders of convergence of using these two      (                                                                                                                 )1/2
                          ∑N (         )2 ∑N (   )2diffusion operators are very close, the reduction of error by using the                                                                        Pd =            fjnum −fjexp  /         fjexp                               (46)proposed modified Fourtakas operator is evident.                                                                                       j                                            j

5.3. Analysis of large deformation problem                            where Pd is the phase difference between both signals, in which perfect
                                                                 agreement leads to Pd → 0, f is the variable under consideration (position
5.3.1. 2-D granular column collapse                                          of the free-surface particles in this case) and the subscripts denote
   This section presents results from a 2-D granular column collapse     experimental or numerical values.
used to examine the ability of the proposed scheme to simulate large           It can be seen that the movement starts at the granular front after the
deformation problems in the presence of a free-surface. Fig. 15 shows     flow is released, and it develops progressively towards the free surface
the  initial geometry and boundary condition of the test case. The    when the toe front stops. There exists a shear band interface where the
granular column has the dimension of 20 cm in length and 10 cm in     particles below remain stationary while those above move outwards.
height. The vertical wall is assumed to be free-slip, while the bottom    The evolutions of the free-surface profile are well predicted, with the
wall is treated as a no-slip boundary.                                  phase difference Pd generally on the order of 1%. In addition, it can be
   The initial particle spacing is set to 0.002 m, resulting in 5000 soil    found that for the larger aspect ratio a = 1.0, the column collapses
particles. The parameters and constitutive properties adopted in the     completely, leading to the final height being lower than its initial value,
simulation are listed in Table 1.                                        while for case with a = 0.5, the collapse follows a shear failure of the
    Fig. 16 shows the evolution of stress profile of the granular flows    column edge, leaving an undisturbed region found at the inner part with
with and without diffusion term at different time instants. In both cases,     the final height equal to the initial one. These results indicate that the
artificial viscosity is adopted. It can be observed that without the use of     failure mechanism of these two sets of aspect ratios is well captured by
diffusion term, the short-length-scale noise is developed especially in the     the proposed model.
region which undergoes large deformations. These fluctuating stress         Finally, a comparison of the final arrangement of the deposit against
distributions can be significantly improved by introducing numerical     the experimental results for all the three particle resolutions is presented
diffusion in stress, resulting in a noise-free smooth stress distribution. In     in Fig. 20. It can be seen that the numerical results agree well with
addition, the surface profiles of two configurations at each instant are     experimental results for both a = 0.5 and 1.0, and, as the resolution of
nearly identical, indicating the use of present diffusion term does not     the particle spacing increases, the predicted free-surface line shows to
alter the physics of the flow.                                          convergence to the experimental results.
   The predicted vertical stresses at the locations of x = 0 m and x =        In addition, it can be found that the toe front position of the final
0.15 m are plotted in Fig. 17 against the theoretical solution. It can be     deposit  increases with  increasing  particle  resolution, because the
seen that the simulation without the diffusion term provides smooth and     constitutive equations are continuous and particle-size independent.
accurate stress profile within the undisturbed region, but the stress    Once the material properties are specified, as long as the particle spacing
distribution is scattered in the highly deformed region. This can lead to     decreases, the height of the toe front keeps decreasing while the extent
discrepancies for cases that the stress/force prediction at the location     of run-out increases, giving a higher resolution for the flows of granular
experiencing large deformation, such as for transient cases i.e., evalua     materials with arbitrary grain size. As commonly defined in literature (e.
tion of the impact of debris. The spurious stress profile is improved with      g., Utili et al. 2015, Nguyen et al. 2020), only the collective behaviour of
the present SPH scheme, in which a smooth and accurate prediction of     granular  flow  is  considered  in  the  determination  of  the  flow
stress can be achieved for both undisturbed and deformed regions, thus    morphology. The final height of the toe front can be assumed to be
allowing better insight into the physics of the failure processes. The     consistent with the mean grain size of the granular bulk. Thus, for the
slight difference can be attributed to the change of bulk density during     prediction of final run-out distance from the proposed SPH model, one
the flow while the reference solution still uses the initial bulk density.     can use the actual mean grain size in practice to determine the final
    It is worth noting that a smooth stress profile over the entire domain     height of the toe front and also the run-out distance (for example in this
can also be attained with the stress regularisation technique recently     case the mean grain size is about 0.002 m, the final run-out distance can
proposed by Nguyen et al. (2017) as demonstrated in their work. This    be estimated as the x coordinate of the point with the height of 0.002 m).
involves applying an MLS-corrected SPH interpolation of stress every 5
time steps, in which an extra particle sweep is needed. By contrast, the     5.3.2. 2-D tunnel face collapse
proposed diffusion term is easy to implement and does not require any        In this case, the present numerical scheme is applied to study the
stress interpolation procedures, which has benefits in terms of simplicity     deformation and post-failure behaviour of tunnel faces. The geometries
and computational efficiency. In addition, since the diffusion term    and material properties of the tunnel model are defined to be the same as
contributes to the stress equation, which is time-integrated, for a prob     the experiments conducted by Matsuo et al. (2016) for comparison. Two
lem with relatively small time-step or a long-time simulation, there    overburden patterns are investigated, with the ratio of overburden depth
would not be a problem of over-filtering as may be encountered for the     to the tunnel diameter H/D equals to 1.0 and 2.0. The definition sketch
stress regularisation technique.

                                                                        16

### Page 17

R. Feng et al.                                                                                                                 Computers and Geotechnics 138 (2021) 104356

of the numerical model and the applied geometric parameters are shown     geotechnical problems. This new boundary formulation is applicable to
in Fig. 21 and listed in Table 2, respectively. The lining structure con    complex shaped geometries and is demonstrated to provide an accurate
structed at the tunnel roof is considered as rigid, which is implemented     prediction of stress and velocity. An improvement on the spurious stress
by using several layers of boundary particles. Open-face condition (e.g.,      field under large deformation, which is a common issue in the SPH
the new Austrian tunnelling method) is assumed in this application and     modelling of geomaterials, has been proposed by including a numerical
thus no face pressure is applied. The boundaries are assumed to be non-     diffusion term into the stress. Several approaches to construct the
slip for the base and horizontal wall (lining structure), while free-slip     diffusion term have been discussed, and compared with the new diffu
conditions are enforced at the vertical walls. Table 1 presents the     sive term algorithm. It is shown to be able to smooth out the numerical
adopted material properties and numerical parameters. The initial par     noise while maintaining the consistency at the boundary. This treatment
ticle spacings for this case are set as dp = 0.004, 0.002, and 0.001 m.        is easy to implement and does not require additional costly procedures
    Fig. 22 shows the comparisons of the final configuration of tunnel     for stress interpolation. Results from the Couette flow, static dry soil in a
model between the experiment and simulation for H/D = 1.0 and 2.0 for    complex geometry show a convergent and accurate prediction of the
dp = 0.002. Particles are coloured by the total displacement and vertical     velocity and stress profiles, demonstrating the accuracy, robustness and
stress. The red lines denote the measured surface profile. The white dots     applicability of the proposed techniques. The new scheme is finally used
refer to the measured failure lines that sperate the deformed region from     for the simulations of granular column collapse and tunnel face collapse,
the undisturbed region. The free-surface profile and the failure line are    showing an excellent agreement between numerical and experimental
well-predicted by the proposed SPH scheme, except for a slight over     results and providing smooth stress profiles.
estimation of the ground surface subsidence for a large overburden ratio
H/D = 2.0.                                                   CRediT authorship contribution statement
   Additionally, it is found that the predicted ground subsidence follows
a Gaussian distribution, which is consistent with previous studies (e.g.,       Ruofeng Feng: Conceptualization, Methodology, Software, Valida
Marshall et al. 2012). The maximum ground settlement develops at      tion, Investigation, Writing – original draft, Writing - review & editing.
around half of the tunnel diameter ahead of the tunnel faces, and the    Georgios  Fourtakas:  Conceptualization,  Methodology,  Software,
magnitude of subsidence for the case of H/D = 1.0 is lower than that of     Writing - review & editing. Benedict D. Rogers: Conceptualization,
H/D = 2.0, indicating a larger overburn depth, may lead to a shallow    Methodology, Resources, Writing - review & editing. Domenico Lom
settlement trough.                                                      bardi:  Conceptualization, Resources, Writing  - review &  editing,
    Finally, a comparison of the face extrusion and ground surface set     Supervision.
tlement against experiment results with 3 particle spacings for H/D =
1.0 and H/D = 2.0 is presented in Fig. 23 and Fig. 24. Again, the pre
dicted free-surface profile shows close agreement with the experimental    Declaration of Competing Interest
results especially as the particle resolutions increases.
                                                                The authors declare that they have no known competing financial
6. Conclusions                                                                interests or personal relationships that could have appeared to influence
                                                                        the work reported in this paper.
   This paper presents a new SPH methodology for the large deforma
tion analysis of geomaterials. A new no-slip/free-slip boundary treat    Acknowledgments
ment using the fixed ghost particle technique together with first-order
consistent interpolation is introduced. It is the first time for such a       The first author would like to acknowledge the financial support
boundary methodology extended for the application of SPH to solve     provided by the China Scholarship Council.

Appendix A. Generalized form of the elastic-perfectly plastic model

   Herein, the general form of the elastic-perfectly plastic model is derived. Initially, the total strain rate tensor is decomposed into two parts: elastic
strain rate tensor and plastic strain rate tensor,
˙εαβ = ˙εαβe + ˙εαβp                                                                                                                    (A1)

where the subscripts e and p denote elastic and plastic component, respectively.
   The elastic component can be calculated according to the generalized Hooke’s law as follow,
          ˙sαβ     ˙σγγ
˙εαβe =  +                                                                                                                      (A2)    2G  9Kδαβ

where ˙sαβ is the deviatoric stress rate tensor; G and K are the elastic shear modulus and elastic bulk modulus, respectively; δαβ is the Kronecker’s delta.
   The plastic component can be derived from the plastic flow rule according to,

       ∂g
˙εαβp = ˙λ                                                                                                                         (A3)       ∂σαβ

where ˙λ is the rate of plastic multiplier; g is the plastic potential function.
   Substituting Eqs. (A2) and (A3) into Eq. (A1), and rearranging the obtained equation, the generic form of the elastic-perfectly plastic model is given
by,
                 [(    )                 ]
                                  ∂g            ∂g˙σαβ = 2G ˙eαβ + K˙εγγδαβ −˙λ  K −2G       + 2G                                                                                 (A4)                             3   ∂σmnδmnδαβ      ∂σαβ

                                                                        17

### Page 18

R. Feng et al.                                                                                                                 Computers and Geotechnics 138 (2021) 104356

where ˙eαβ is the deviatoric strain rate tensor that can be expressed as,
˙eαβ = ˙εαβ −1                                                                                                                     (A5)              3˙εγγδαβ
   The plastic multiplier can be computed by the consistency condition that is defined as,

       δf
df =     dσαβ = 0                                                                                                                (A6)     δσαβ

where f is the yield function that defines the onset of plastic deformation.
   Combining Eq. (A4) and Eq. (A6), the plastic multiplier can be obtained as,
          [     (    )     ]
                 δf   2G˙εαβ + K −  2G3   δαβ ˙εγγ             δσαβ
˙λ = (    )(       )                                                                                                      (A7)
    K −  2G3     ∂σmnδmn∂f     ∂σmnδmn∂g   + 2G ∂σmn∂f   ∂σmn∂g

   Considering the following identities,

 ∂f     ∂f        ∂f          ∂f
   =    δαβ +    sαβ +      tαβ                                                                                                    (A8)
∂σαβ    ∂I1      ∂J2        ∂J3

 ∂g    ∂g     ∂g     ∂g
   =    δαβ +    sαβ +    tαβ                                                                                                      (A9)
∂σαβ    ∂I1      ∂J2      ∂J3

where I1 is the first principal stress invariant, J2 and J3 are the second and third deviatoric stress invariants, respectively. The term tαβ is defined as
follows,
tαβ =  sαm smβ −2                                                                                                            (A10)                 3J2δαβ

the generalized form of stress–strain relationship in terms of stress invariants for an elastic-perfectly plastic material is given by,
                    [        (        ) ]
                          ∂g          ∂g      ∂g
˙σαβ = 2G ˙eαβ + K˙εγγδαβ −˙λ 3K    δαβ + 2G      sαβ +     tαβ                                                                            (A11)                                  ∂I1           ∂J2      ∂J3
     [         (         ) ]
    1      ∂f               ∂f          ∂f
˙λ =   3K    δαβ + 2G      sαβ +      tαβ     ˙εαβ                                                                                   (A12)  H      ∂I1            ∂J2        ∂J3

where
                   (        )
         ∂f ∂g         ∂f ∂g        ∂g ∂f    ∂f ∂g
H= 9K     +4GJ2     +6GJ3     +
        ∂I1 ∂I1        ∂J2 ∂J2         ∂J2 ∂J3  ∂J2 ∂J3
    (         )                                                                                                    (A13)
                               ∂f ∂g + 2G  sαmsmβsαnsnβ−4 2                      3J2  ∂J3 ∂J3
   Once the yield function f and the plastic potential function g are given, and the strain rate tensor as well as current stress condition are prescribed,
the corresponding stress rate can be determined from Eq. (A11).

References                                                                                 Bui, H.H., Sako, K., Fukagawa, R., 2007. Numerical simulation of soil-water interaction
                                                                                             using smoothed particle hydrodynamics (SPH) method. J. Terramech. 44 (5),
                                                                                     339–346.Adami, S., Hu, X.Y., Adams, N.A., 2012. A generalized wall boundary condition for                                                                                          Chalk, C., Pastor, M., Peakall, J., Borman, D., et al., 2020. Stress-Particle Smoothed   smoothed particle hydrodynamics. J. Comput. Phys. 231 (21), 7057–7075.                                                                                                        Particle Hydrodynamics: An application to the failure and post-failure behaviour ofAntuono, M., Colagrossi, A., Marrone, S., 2012. Numerical diffusive terms in weakly-                                                                                                        slopes. Comput. Methods Appl. Mech. Eng. 366, 113034.    compressible SPH schemes. Comput. Phys. Commun. 183 (12), 2570–2580.                                                                                   Chen, W., Qiu, T., 2012. Numerical simulations for large deformation of granularAntuono, M., Colagrossi, A., Marrone, S., Molteni, D., 2010. Free-surface flows solved by                                                                                                 materials using smoothed particle hydrodynamics method. Int. J. Geomech. 12 (2),   means of SPH schemes with numerical diffusive terms. Comput. Phys. Commun. 181                                                                                     127–135.     (3), 532–549.                                                                                                Colagrossi, A., Landrini, M., 2003. Numerical simulation of interfacial flows by smoothedBenz, W., Asphaug, E., 1995. Simulations of brittle solids using smooth particle                                                                                                         particle hydrodynamics. J. Comput. Phys. 191 (2), 448–475.    hydrodynamics. Comput. Phys. Commun. 87 (1–2), 253–265.                                                                                          Crespo, A.J., Domínguez, J.M., Rogers, B.D., G´omez-Gesteira, M., et al., 2015.Blanc, T., Pastor, M., 2013. A stabilized smoothed particle hydrodynamics, Taylor-                                                                                           DualSPHysics: Open-source parallel CFD solver based on Smoothed Particle    Galerkin algorithm for soil dynamics problems. Int. J. Numer. Anal. Meth. Geomech.                                                                                  Hydrodynamics (SPH). Comput. Phys. Commun. 187, 204–216.   37 (1), 1–30.                                                                                 Dehnen, W., Aly, H., 2012. Improving convergence in smoothed particle hydrodynamicsBui, H.H., Fukagawa, R., 2013. An improved SPH method for saturated soils and its                                                                                               simulations without pairing instability. MNRAS 425 (2), 1068–1082.    application to investigate the mechanisms of embankment failure: Case of                                                                                                     Douillet-Grellier, T., Pramanik, R., Pan, K., Albaiz, A., et al., 2017. Development of stress    hydrostatic pore-water pressure. Int. J. Numer. Anal. Meth. Geomech. 37 (1), 31–50.                                                                                   boundary conditions in smoothed particle hydrodynamics (SPH) for the modeling ofBui, H.H., Fukagawa, R., Sako, K., Ohno, S., 2008. Lagrangian meshfree particles method                                                                                                          solids deformation. Comput. Particle Mech. 4 (4), 451–471.    (SPH) for large deformation and failure flows of geomaterial using elastic-plastic soil                                                                                                English, A., Domínguez, J.M., Vacondio, R., Crespo, A., et al., 2021. Modified dynamic    constitutive model. Int. J. Numer. Anal. Meth. Geomech. 32 (12), 1537–1570.                                                                                   boundary conditions (mDBC) for general-purpose smoothed particle hydrodynamicsBui, H.H., Kodikara, J.K., Bouazza, A., Haque, A., et al., 2014. A novel computational                                                                                            (SPH): application to tank sloshing, dam break and fish pass problems. Comput.    approach for large deformation and post-failure analyses of segmental retaining wall                                                                                                        Particle Mech. 1–15.    systems. Int. J. Numer. Anal. Meth. Geomech. 38 (13), 1321–1340.

                                                                        18

### Page 19

R. Feng et al.                                                                                                                 Computers and Geotechnics 138 (2021) 104356

Fourtakas, G., Dominguez, J.M., Vacondio, R., Rogers, B.D., 2019. Local uniform stencil      Nguyen, H.T.N., Bui, H.H., Nguyen, G.D., 2020. Effects of material properties on the
    (LUST) boundary condition for arbitrary 3-D boundaries in parallel smoothed                mobility of granular flow. Granular Matter 22, 59.
    particle hydrodynamics (SPH) models. Comput. Fluids 190, 346–361.                Nonoyama, H., Moriguchi, S., Sawada, K., Yashima, A., 2015. Slope stability analysis
Gingold, R.A., Monaghan, J.J., 1977. Smoothed particle hydrodynamics: theory and              using smoothed particle hydrodynamics (SPH) method. Soils Found. 55 (2),
    application to non-spherical stars. MNRAS 181 (3), 375–389.                             458–470.
Huang, J., Griffiths, D., 2009. Return mapping algorithms and stress predictors for failure      Onate, E., Idelsohn, S.R., Del Pin, F., Aubry, R., 2004. The particle finite element method:
    analysis in geomechanics. J. Eng. Mech. 135 (4), 276–284.                             an overview. Int. J. Comput. Methods 1 (02), 267–307.
Huang, Y.u., Zhang, W., Xu, Q., Xie, P., Hao, L., 2012. Run-out analysis of flow-like           Pastor, M., Haddad, B., Sorbino, G., Cuomo, S., et al., 2009. A depth-integrated, coupled
    landslides triggered by the Ms 8.0 2008 Wenchuan earthquake using smoothed           SPH model for flow-like landslides and related phenomena. Int. J. Numer. Anal.
    particle hydrodynamics. Landslides 9 (2), 275–283.                                     Meth. Geomech. 33 (2), 143–172.
Gomez-Gesteira, M., Rogers, B.D., Dalrymple, R.A., Crespo, A.J., et al., 2010. State-of-       Peng, C., Wang, S., Wu, W., Yu, H.-S., et al., 2019. LOQUAT: an open-source GPU-
    the-art of classical SPH for free-surface flows. J. Hydraul. Res. 48 (S1), 6–27.                 accelerated SPH solver for geotechnical modeling. Acta Geotech. 14 (5), 1269–1287.
Huang, Y., Dai, Z., 2014. Large deformation and failure simulations for geo-disasters         Peng, C., Wu, W., Yu, H.-S., Wang, C., 2015. A SPH approach for large deformation
    using smoothed particle hydrodynamics method. Eng. Geol. 168, 86–97.                      analysis with hypoplastic constitutive model. Acta Geotech. 10 (6), 703–717.
Jandaghian, M., Shakibaeinia, A., 2020. An enhanced weakly-compressible MPS method      Prime, N., Dufour, F., Darve, F., 2014. Solid-fluid transition modelling in geomaterials
    for free-surface flows. Comput. Methods Appl. Mech. Eng. 360, 112771.                  and application to a mudflow interacting with an obstacle. Int. J. Numer. Anal. Meth.
Liu, M., Liu, G.-R., 2006. Restoring particle consistency in smoothed particle                  Geomech. 38 (13), 1341–1361.
    hydrodynamics. Appl. Numer. Math. 56 (1), 19–36.                                    Quinlan, N.J., Basa, M., Lastiwka, M., 2006. Truncation error in mesh-free particle
Lucy, L.B., 1977. A numerical approach to the testing of the fission hypothesis.                 methods. Int. J. Numer. Meth. Eng. 66 (13), 2064–2085.
    Astronom. J. 82, 1013–1024.                                                        Robinson, M.J., 2009. Turbulence and viscous mixing using smoothed particle
Mao, Z., Liu, G., Dong, X., 2017. A comprehensive study on the parameters setting in           hydrodynamics. Monash University.
   smoothed particle hydrodynamics (SPH) method applied to hydrodynamics              Shao, S., Lo, E.Y., 2003. Incompressible SPH method for simulating Newtonian and non-
    problems. Comput. Geotech. 92, 77–95.                                              Newtonian flows with a free surface. Adv. Water Resour. 26 (7), 787–800.
Marrone, S., Antuono, M., Colagrossi, A., Colicchio, G., et al., 2011. δ-SPH model for           Sibilla, S., 2007. SPH simulation of local scour processes. Proc. SPHERIC, 2nd
    simulating violent impact flows. Comput. Methods Appl. Mech. Eng. 200 (13–16),            International Workshop. Universidad Polit´ecnica de Madrid, Spain.
    1526–1542.                                                                              Sulsky, D., Chen, Z., Schreyer, H.L., 1994. A particle method for history-dependent
Marshall, A., Farrell, R., Klar, A., Mair, R., 2012. Tunnels in sands: the effect of size,              materials. Comput. Methods Appl. Mech. Eng. 118 (1–2), 179–196.
    depth and volume loss on greenfield displacements. Geotechnique 62 (5), 385–399.        Utili, S., Zhao, T., Houlsby, G., 2015. 3D DEM investigation of granular column collapse:
Matsuo, T., Mori, K., Hiraoka, N., Sun, M., et al., 2016. Study of SPH simulation on tunnel           evaluation of debris motion and its destructive power. Eng. Geol. 186, 3–16.
    face collapse. Int. J. GEOMATE 10 (22), 2077–2082.                                  Vacondio, R., Altomare, C., De Leffe, M., Hu, X., et al., 2020. Grand challenges for
Mayrhofer, A., Rogers, B.D., Violeau, D., Ferrand, M., 2013. Investigation of wall              Smoothed Particle Hydrodynamics numerical schemes. Comput. Particle Mech.
   bounded flows using SPH and the unified semi-analytical wall boundary conditions.          1–14.
   Comput. Phys. Commun. 184 (11), 2515–2527.                                  Wang, D., Randolph, M., White, D., 2013. A dynamic large deformation finite element
Molteni, D., Colagrossi, A., 2009. A simple procedure to improve the pressure evaluation         method based on mesh regeneration. Comput. Geotech. 54, 192–201.
    in hydrodynamic context using the SPH. Comput. Phys. Commun. 180 (6), 861–872.      Yang, E., Bui, H.H., De Sterck, H., Nguyen, G.D., et al., 2020. A scalable parallel
Monaghan, J.J., 1992. Smoothed particle hydrodynamics. Ann. Rev. Astron. Astrophys.          computing SPH framework for predictions of geophysical granular flows. Comput.
   30 (1), 543–574.                                                                       Geotech. 121, 103474.
Monaghan, J.J., Kos, A., 1999. Solitary waves on a Cretan beach. J. Waterw. Port Coastal       Yin, Z.-Y., Jin, Z., Kotronis, P., Wu, Z.-X., 2018. Novel SPH SIMSAND-based approach for
   Ocean Eng. 125 (3), 145–155.                                                       modeling of granular collapse. Int. J. Geomech. 18 (11), 04018156.
Morris, J.P., Fox, P.J., Zhu, Y., 1997. Modeling low Reynolds number incompressible        Zhao, S., Bui, H.H., Lemiale, V., Nguyen, G.D., et al., 2019. A generic approach to
    flows using SPH. J. Comput. Phys. 136 (1), 214–226.                                     modelling flexible confined boundary conditions in SPH and its application. Int. J.
Nguyen, C.T., Nguyen, C.T., Bui, H.H., Nguyen, G.D., et al., 2017. A new SPH-based           Numer. Anal. Meth. Geomech. 43 (5), 1005–1031.
    approach to simulation of granular flows using viscous damping and stress
    regularisation. Landslides 14 (1), 69–81.

                                                                        19
