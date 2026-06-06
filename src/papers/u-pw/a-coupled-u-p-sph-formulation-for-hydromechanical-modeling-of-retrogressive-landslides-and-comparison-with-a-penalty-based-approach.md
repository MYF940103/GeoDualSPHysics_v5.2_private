# A Coupled u&\#x02013;pw SPH Formulation for Hydromechanical Modeling of Retrogressive Landslides and Comparison With a Penalty&\#x02010;Based Approach

> Auto-converted from PDF for Codex/code-reference reading. Formatting, equations, figures, and tables may require checking against the original PDF.

- Source PDF: `a-coupled-u-p-sph-formulation-for-hydromechanical-modeling-of-retrogressive-landslides-and-comparison-with-a-penalty-based-approach.pdf`
- Pages: 31

## Extracted Text

### Page 1

International Journal for Numerical and Analytical Methods in Geomechanics

 RESEARCH ARTICLE

        uA Coupled –pw SPH Formulation for Hydromechanical
Modeling of Retrogressive Landslides and Comparison With
a Penalty-Based Approach

Enrique M. del Castillo1    Ronaldo I. Borja1      Alomir H. Fávero Neto2

1 Department of Civil and Environmental Engineering, Stanford University, Stanford, California, USA   2 Department of Civil and Environmental Engineering,
Bucknell University, Lewisburg, Pennsylvania, USA

Correspondence: Alomir H. Fávero Neto ( alomir.favero@bucknell.edu)

Received: 18 November 2025   Revised: 26 March 2026   Accepted: 30 March 2026

Keywords: penalty method | retrogressive landslides | smoothed particle hydrodynamics | solid–fluid coupling | spreads and flowslides | u –p formulation

 ABSTRACT
  We present a strongly coupled displacement ( 𝒖 ) and pore water pressure ( 𝑝𝑤 ) version of the Biot–Zienkiewicz ( 𝒖 – 𝑝𝑤 ) equations in
   saturated porous media for the meshfree Lagrangian smoothed particle hydrodynamics (SPH) method. We propose two distinct
  formulations using a single particle layer, two-phase framework, one based on a one-step solution of a pressure Poisson
  equation (PPE formulation) and another allowing compressibility of the fluid resulting in an explicit rate equation for the pore
  pressure (PR formulation). We discuss both formulations from a numerical perspective and verify them using benchmark problems
  from poroelasticity, including Cryer’s problem, as well as using undrained triaxial tests, where we additionally compare the results
   against a weakly coupled penalty-based undrained framework for SPH. Beyond the formulations, the focus of this work is on
  modeling retrogressive landslides in saturated sensitive clays, which are particularly destructive due to their extended runout and
   fast movement. Our simulations emphasize performing strongly coupled hydromechanical modeling even for quasi-undrained
   conditions, contrary to the predominant practices in the literature, as the structural features of the landslides change significantly
  when pore pressure dissipation and coupled effects are included. Additionally, spreads develop under a greater variety of slope
  conditions as opposed to the more fluidized flowslide type of retrogressive landslides captured when solely considering undrained
   behavior. Lastly, we apply the PR formulation to explore how slope steepness and height influence deformation modes and
  apply the framework to simulate the 1994 Sainte-Monique landslide, recreating the topographic profile, runout, and deformation
   features post-failure.

1    Introduction                                     and intensity of extreme weather events due to global climate
                                                              change, the likelihood of rainfall-driven geohazards such as landThe intrinsic strong coupling between the solid skeleton and pore     slides, mudflows, or flowslides is increasing [ 28 ]. Comprehending
fluid in saturated porous media is necessary to explain and model    landslide potential runout distances, final deformation configua wide range of (quasi)-static and dynamic geohazard-related     ration, and impact forces is paramount given the considerable
processes, such as subsidence, pore fluid induced fault weak-   damage (economic losses of $1–3.6 billion USD annually in the
ening, soil liquefaction, scouring, rainfall-triggered landslides,    United States [ 2 ]) and fatalities (600 + deaths per year globally on
multiphase flows and debris flows, as well as earthen and tailings    average [ 96 ]) caused by landslides with some individual disasters
embankment and dam failures. Due to the increasing frequency    responsible for as many as tens of thousands of deaths. At the

© 2026 John Wiley & Sons Ltd.

International Journal for Numerical and Analytical Methods in Geomechanics , 2026; 0:1–31                                                               1 of 31
https://doi.org/10.1002/nag.70322

### Page 2

same time, as rehabilitation of aging infrastructure and design    In the SPH method, two distinct approaches have been proposed
of new infrastructure is increasingly conducted up to safe-to-fail     to account for the different phases (solid skeleton and water) in
rather than fail–safe standards [ 43 ], knowledge of the expected    the case of a fluid saturated medium. In the first, each phase in
range of possible post-failure behavior, particularly of dams and    the saturated porous medium is represented by its own set (layer)
levees, is required [ 49 ].                                               of Lagrangian SPH particles, and the governing equations of each
                                                           phase are solved distinctly over the corresponding set of particles
The field of poromechanics, namely the mathematical theory     [ 21, 50 ]. In general, the fluid phase is modeled as incompressible
describing the mechanics of coupled saturated porous media,    or using the weakly compressible form of the SPH method, and
owes much to the seminal work of Maurice Biot, who expanded    the skeleton is modeled using an elastoplastic constitutive model,
upon the concept of effective stress and formalized the cou-    with the interaction between the phases given by a seepage or
pled equations of poroelasticity using mixture theory  [ 5–7 ].    drag force. The second is the single-layer approach, which is more
Owing to their complexity, these equations and their derivation    computationally inexpensive as there is only one particle type and
using mixture theory were later synthesized into four different   no need for interaction forces, and the governing equations can
simplified formulations which are collectively denoted the so-    be taken directly from Biot–Zienkiewicz theory and its simplified
called Biot-Zienkiewicz theory [ 116 ]. In the first, the 𝒖 – 𝒘 – 𝑝𝑤    forms with minimal modification. Some of the early efforts
formulation, the solid skeleton displacement 𝒖 , Darcy’s velocity     to develop a strongly coupled hydromechanical framework for
𝒘 , and the pore water pressure 𝑝𝑤 are the unknowns to be   SPH based on the Biot–Zienkiewicz equations followed a depthsolved. In addition, the further simplified 𝒖 – 𝑝𝑤 , 𝒖 – 𝒘 , and 𝒖 – 𝑼    integrated approach, using fluid-like rheology models, focusing
formulations, where 𝑼is the total displacement vector of the fluid   on debris flows [ 9, 79 ]. More recently, Morikawa and Asai [ 67 ]
phase, were also postulated, with the 𝒖 – 𝑝𝑤 variant considered    proposed a single-layer SPH 𝒖 – 𝒘 – 𝑝𝑤 framework based on
valid as long as highly dynamic loading is not considered, leading    an incompressible SPH (ISPH) approach, where both pore fluid
to its widespread adoption in geotechnics and geomechanics [ 11,    and soil skeleton are incompressible, which is imposed through
72, 74 ].                                                       a projection method sharing features with the moving-particle
                                                                    semi-implicit method [ 51 ] resulting in a pressure Poisson equaMesh-dependent methods such as the finite element method    tion (PPE). However, the condition of divergence-free velocity
(FEM) permit highly accurate solutions using the coupled for-     field may not always hold in physical systems and adds significant
mulations of Biot–Zienkiewicz theory, especially for problems    numerical complexity. Lian and coworkers [ 54 ] extended their
that deal with small deformations or with the prefailure phase    previous work on an SPH framework for seepage flow through
of geomaterials or engineered structures [ 10, 14–16 ]. In the case    unsaturated soil [ 53 ], to derive a single-layer strongly coupled
of slope stability, while FEM is particularly useful for capturing     explicit formulation for unsaturated porous media based on the
the failure mechanism, FEM is unable to capture the post-failure   𝒖 – 𝑝𝑤 equations. Chen et al. [ 25 ] developed a similar formulation
behavior and deformation of the slope due to issues resulting     to Lian et al. [ 54 ] where the pore pressure rate (PR) is calculated
from mesh distortion. For the same reason, the traditional FEM is    in an explicit rate equation based on volumetric strains and
unable to accurately model a number of other solid–fluid coupled    Darcy’s law, and successfully applied the model to seepagegeohazard problems such as debris flows, flowslides, or levee    induced sinkhole formation in fully saturated soils. Lian and
failures. Modeling and quantifying the post-failure stage is crucial    coworkers further proposed a three-point integration scheme to
to predict travel distances and velocities of the sliding or flowing    reduce the dependence of the pore fluid on the fluid bulk modulus
material, as well impact forces on any nearby structures [ 66, 90 ].    without relying on a fully implicit approach and permitting larger
                                                             time increments in the time integration and saving computational
Continuum-based particle or meshfree methods such as the mate-    cost [ 55 ]. The work of Yao and coauthors [ 110 ] likewise developed
rial point method (MPM) [ 1, 75, 88, 115 ], peridynamics [ 64, 89 ],    both fully explicit 𝒖 – 𝑝𝑤 and 𝒖 – 𝒘 – 𝑝𝑤 formulations, sharing
particle FEM (PFEM) [ 48, 65, 77 ], element free Galerkin method     similarities with past work [ 25, 54 ] and using absorbing boundary
(EFG) [ 4 ], reproducing kernel particle method (RKPM) [ 56 ], and    conditions demonstrated under harmonic and dynamic loading
smoothed particle hydrodynamics (SPH) [ 19, 20, 22, 31, 39, 40, 78 ]    in one and two dimensions. Yao et al. further demonstrated that
are all capable of accounting for the large deformations inherent    numerical dissipation techniques in the SPH method together
of the post-failure regime. Their continuum nature allows for the    with the explicit approach have the effect of averaging volumetric
discretization and solving of the coupled equations from Biot–     strains in the context of SPH, having a similar effect to the B-bar
Zienkiewicz theory, and a number of formulations to account for   method in mesh-based method like FEM or MPM, thus avoiding
fluid saturated porous media have been recently proposed [ 3, 62,    volumetric locking in the near-incompressibility limit.
63, 73, 85, 103–105 ]. Originally developed to deal with astrophysical applications [ 44, 60 ], SPH has a number of computational    In this paper, inspired by the aforementioned recent progress, we
advantages over its peers. For example, in MPM, a background    develop and lay out in detail the derivations, discretizations, and
Eulerian mesh is utilized to solve the governing equations while    implementations of a projection method PPE approach and an
the state variables are carried in the Lagrangian material points,     explicit pore PR equation method for a strongly coupled 𝒖 – 𝑝𝑤
adding to computational cost and making the method susceptible    hydromechanical formulation for fully saturated soil in the SPH
to cell crossing noise [ 112 ]. In PFEM, whenever the Lagrangian    method. We also present the required numerical stabilization
particles/nodes move such that the mesh is distorted, it must    techniques and the SPH form of boundary conditions for the
be deleted, and remeshed, a methodology resulting in extensive    pore pressure degree of freedom at drained and undrained
remeshing when dealing with large deformation problems [ 101 ].    boundaries. The hydromechanical models are implemented into
Since EFG also requires integration on a mesh [ 37 ], SPH is in    the in-house parallel SPH code GEOSPH developed by the authors
effect one of the few truly meshfree methods.                             [ 30, 38 ] and built on the open source framework PySPH [ 82 ],

2 of 31                                                                                 International Journal for Numerical and Analytical Methods in Geomechanics, 2026

### Page 3

which has been used in a number of applications relating to    thoughts as well as directions for further work are presented in
large geomaterial deformations that involve localized failure [ 32,    Section 7 .
34, 35, 42, 71 ]. We verify and compare the performance of the
presented formulations for one-dimensional, and for the first time
in the literature, three-dimensional benchmarks in poroelasticity,    1.1    Retrogressive Landslides in Sensitive Clays
including Cryer’s Problem. Next, we combine these formulations
with a modified Cam Clay (MCC) model from critical state soil    Retrogressive landslides, or retrogressive slope failures, are a
mechanics, to verify the performance against analytical solutions    type of progressive failure that occurs after an initial local slope
for various undrained triaxial compression stress paths, and     failure leads to a catastrophic series of successive failures trending
against results obtained with a penalty-based framework [ 12, 13 ]    upslope in a retrogressive manner. Retrogressive landslides can
specific to undrained loading developed in the authors’ previous    span kilometers in their runout, are very quick, and have signifiwork [ 33 ].                                                       cant destructive potential [ 23, 24, 93 ], as evidenced by numerous
                                                                     events, such as the flowslides in Heifangtai, China [ 81 ], and the
We take advantage of the strongly coupled hydromechanical    Gjerdrum slides in Norway [ 92 ]. They usually occur with minimal
model to study retrogressive landslides and the progressive failure    warning, and small disturbances coming from human activity
of sensitive clays, under fluid saturated conditions. Retrogressive    upslope can be sufficient to trigger and propagate an instability
landslides involve a series of sequential failure surfaces trending     [ 57 ]. Retrogressive landslides occur in sensitive clays exhibiting
upslope and are a product of strain softening behavior in sensitive     drastic strain softening behavior in undrained shear, as a result of
clays that transforms the clay into remolded liquid-like material    remolding, a process which transforms the clay into a liquid-like
with a low shear strength during localized failure within shear    material with a very low shear strength (often < 1 kPa) during
bands. Because of their short temporal duration, retrogressive    localized failure. Because of their short duration, and the fact
landslides are often treated as an undrained process, and most    that they usually involve saturated soils, retrogressive landslides
past computational modeling has completely ignored the role of    are treated as an undrained process [ 36, 95 ]. The two main
pore pressures, with very few exceptions [ 48, 55 ], and almost all    representative types of retrogressive landslides include flowslides
past studies have relied on total stress analyses capturing the soil’s    and spreads [ 57, 59, 100 ].
inability to deform volumetrically by adopting incompressible
elasticity (Poisson’s ratio close to 0.5), and by using the von Mises   A flowslide or the slide-flow mode occurs as a series of successive
( 𝐽2 ) or Tresca plasticity model which does not allow for plastic vol-    rotational slides, where the initial slide generates a new unstable
umetric strains [ 22, 36, 80, 87, 98, 113 ], even though this modeling    backscarp, and subsequent failures of these newly produced
choice is not realistic for many sensitive clays [ 48 ]. To account    backscarps continue until a final stable backscarp is obtained.
for the build-up and dissipation of pore pressures, we perform   As the name implies, during and after the slide, the failed
SPH simulations with the coupled hydromechanical framework,    remolded clay mass flows out of the crater as fluid-like debris.
as well as an isotropic strain softening elastoplastic model with   On the other hand, spreads are a type of progressive failure,
the Drucker–Prager yield criterion designed for describing the    where a soil mass delimited by a surface-parallel sliding plane
remolding and progressive failure behavior of sensitive clays. We     at depth begins to fail in extension forming intact blocks of
contrast the simulation results against equivalent simulations    clay known as horsts and grabens. Horsts are blocks with an
performed with the penalty-based undrained framework, com-    upwards-pointing sharp wedge shape ( Δ-shape) and grabens are
paring the runout distance, failure mechanism, pore pressure    downwards-pointing wedge-shaped blocks with a flat top surface
distributions, and respective computational efficiency. We also     ( ∇ -shaped). As pointed by Carson [ 23 ], tension cracks form
explore some of the factors promoting the distinct spreading    between the horsts and grabens and the angle of the slip surfaces
versus flowslide modes of retrogressive slope failure. Lastly, we    between graben and horsts should be oriented at 45◦+ 𝜙∕2 with
study the 1994 Sainte-Monique Landslide in Quebec, Canada,    respect to the horizontal, where 𝜙is the friction angle of the
an example of a retrogressive landslide showing the ability of     clay. Carson observed in the field that the bases of the grabens
strongly coupled hydromechanical SPH simulations to capture    also undergo remolding, and that horsts and grabens subside
the spreading mode of failure, and similar runout and post-failure    into this remolded clay, in turn squeezing the remolded clay
slope configuration.                                            along the cracks (slip planes) between the horsts and grabens
                                                                  as they slide. To initiate a spread, it has been hypothesized that
The order of presentation in the paper is as follows. In the    an initial rotational failure is often needed to reduce the lateral
remainder of Section 1 , in Subsection 1.1 , a brief introduction    earth pressure behind the backscarp and increase the shear
to retrogressive landslides is presented. This is followed by an     stress along the sliding plane at the bottom of the new scarp, in
exposition of the governing equations in the 𝒖 – 𝑝𝑤 formulation    turn promoting spreading upslope [ 57 ]. Field observations have
in Section 2 and of the SPH discretization and implementation,    corroborated this line of thought as some spread failures were
boundary treatment, constitutive equations, as well as stabiliza-      first triggered by a rotational slide, for example, as seen in the
tion in Section 3 . In Section 4 , the strongly coupled framework    Sköttorp landslide in Sweden [ 76 ]. Similarly, gradual erosion
is verified against analytical solutions pertaining to various    occurring at the slope toe due to fluvial processes may also
benchmark problems, and in Section 5 , we explore retrogressive    decrease the horizontal earth pressure and increase shear stress
failure of two idealized slopes, comparing the results between     sufficiently to trigger an initial instability in the slope [ 57 ].
the strongly coupled hydromechanical model and a penaltybased undrained (here forth referred to simply as undrained)   One of the main factors known to affect the particular failure
approach. Section 6 is dedicated to the simulation of the 1994   mode is the in situ stress condition, particularly the coefficient
Sainte-Monique Landslide, and some discussion and concluding     of earth pressure at rest, 𝐾0 , which  is the ratio of effective

International Journal for Numerical and Analytical Methods in Geomechanics, 2026                                                         3 of 31

### Page 4

horizontal to effective vertical stress. In their Eulerian-based                                                                      1 𝑑 𝑝𝑤                 𝜌𝑤large deformation finite-element study, Wang et al. [ 99 ] showed               − ∇ ⋅𝒗 − ∇ ⋅𝒗𝑠 −∇   ⋅𝒗 = 0 .            (1)                                                 𝑄 𝑑𝑡                 𝜌𝑤
that a higher 𝐾0 increased the potential for retrogressive failure
overall, and that a high enough 𝐾0 could change the emerging             ( 𝑑𝑤 𝒗𝑤    )failure patterns. For example, for low 𝐾0 , only singular slides          𝜌𝑑𝒗𝑠 + 𝜌𝑤      −𝑑𝒗𝑠  = ∇ ⋅𝝈′ + ∇ 𝑝𝑤 + 𝜌𝒈 .     (2)                                                                        𝑑𝑡         𝑑𝑡     𝑑𝑡
were generated, whereas for intermediate 𝐾0 values, flowslides
occurred, and for high enough 𝐾0 ≥ 1 . 0 , spreads were observed.
These results were largely corroborated by the MPM simulations    Here, 𝑝𝑤 is the pore (water) pressure, 𝝈′ is the effective Cauchy
of Wang et al. [ 100 ] and by the SPH simulations performed by Lian     stress tensor, 𝒗 is Darcy’s velocity, or the difference between
et al. [ 55 ]. Field evidence also points to 𝐾0 > 1 . 0 in some cases of     fluid ( 𝒗𝑤 ) and solid ( 𝒗𝑠 ) velocities per unit area of the mixture,
large spreads in sensitive clays [ 45 ].                          𝜌is the density of the mixture, 𝜌𝑤 is the density of the fluid
                                                                 phase, 𝜌𝑤 = 𝑛𝜌𝑤  is the partial density of the fluid phase, 𝑛
Much previous numerical modeling work has focused on improv-      is the mixture porosity, and 1∕ 𝑄 = (1 − 𝑛)∕ 𝐾𝑠 + 𝑛∕𝐾𝑤 , where
ing constitutive models, particularly strain softening models, to    𝐾𝑠 and 𝐾𝑤 are correspondingly the bulk moduli of the solid
match the behavior of sensitive clays [ 84, 94, 95, 107 ]. For example,   and fluid phases. In terms of notation, 𝑑 ()∕ 𝑑 𝑡is a material
Wang and coworkers found that by increasing the brittleness    time derivative following the motion of the solid phase, and
of the clay by increasing the rate of post-peak undrained shear    𝑑𝑤 ()∕ 𝑑𝑡is following the fluid phase. It is important to note
strength degradation, the possibility of flowslides increased,    that the porous medium in  this work  is assumed to have
whereas for more gradual degradation rates, spreads dominated     isotropic and homogeneous hydraulic conductivity, 𝒌 ( 𝒙 ) = 𝑘𝟏 .
[ 100 ]. However, considerably less focus has been put on account-   The formulation presented, in what follows, is limited to isotropic
ing for the effects of pore pressures or groundwater seepage,    and transversely isotropic  (e.g., layered soils) hydraulic conin part due to the focus on strain softening and the commonly     ductivity conditions. For situations where conductivities are
adopted total stress modeling approaches [ 58, 99 ]. In undrained     anisotropic, an approach using the framework proposed in
shearing, the increasing pore pressure will cause a reduction in     [ 55 ], with more robust approximations of second derivatives,
shearing resistance because of the decreased effective stress [ 8 ].     is recommended.
However, rather than directly modeling this hydromechanical
process, some authors prefer to account for this feature directly
in the softening response [ 93 ]. This modeling choice fails to    2.1   𝒖 – 𝒑𝒘 Pressure Poisson Equation (PPE)
acknowledge the important role pore pressure dissipation plays   Formulation
on ending progressive failure because of the resulting increasing
strength and frictional resistance in the clay [ 100 ].                                                        To derive the so-called 𝒖 – 𝑝𝑤 formulation, where only the
                                                              displacement of the solid 𝒖 and the pore water pressure 𝑝𝑤 are
Progressive  failures  are  highly  dynamical  processes.  The                                                                the independent variables, a few assumptions are necessary:
remolded clay debris in flowslides often flows at up to several
meters per second, and the horsts and grabens in spreads also
                                                                                             1.  Intrinsically incompressible pore fluid and solid fractions:
slide at considerable speeds (although not as great). Therefore, the
                                                                 𝐾𝑠 →∞and 𝐾𝑤 →∞, such that 1∕ 𝑄 →0 and ∇ 𝜌𝑤 = 0 .
prefailure slope and the amount of gravitational potential energy
at the moment of initial failure may also affect the resulting      2. The relative material acceleration between the fluid and solid
retrogressive landslide mode. From the point of view of numerical        phases is zero, that is, 𝑑𝑤 𝒗𝑤 ∕𝑑 𝑡 − 𝑑 𝒗𝑠 ∕𝑑 𝑡 = 0 .
simulation of retrogressive landslides, it is necessary to be able to
solve the dynamic equations of motion, and to handle the post-    For  the mixture  balance  of mass  equation, Equation  ( 1 ),
failure large deformations. Particle-based or meshfree methods    applying the first assumption and substituting the definition
have become the preferred approach for modeling large progres-     of Darcy’s velocity (Equation A12 in Appendix  I) gives the
sive failures [ 26, 91, 99, 104, 108 ], and SPH, which solves the fully    following:
dynamic equations of motion, is a natural method of choice [ 22 ].

                                                                            𝑘
                                                ∇ ⋅𝒗𝑠 +    ∇2 𝑝𝑤 + 𝑘∇2 𝑧 = 0 .               (3)
2    Governing Equations for the Coupled Problem                         𝜌𝑤 𝑔

In this section, we present the continuum equations for a fully                                                       where 𝑧is the elevation head, and ∇2 is the Laplacian operator.
saturated soil–water mixture derived using continuum mixture
                                                     Now, considering the mixture momentum balance, Equation ( 2 ),
theory, which follows an approach similar to that taken by Biot
                                                       and applying the second assumption results in
[ 5, 6 ] and Zienkiewicz [ 116 ]. In addition, we provide an overview
of the assumptions, variables of interest, and equations needed to
solve the strongly coupled problem. More details about the deriva-                    𝑑𝒗𝑠   1        1
                                                        = 𝜌∇ ⋅𝝈′ + 𝜌∇ 𝑝𝑤 + 𝒈 .                (4)tion of the mixture equations and their underlying assumptions                     𝑑𝑡
can be found in Appendix I.
                                           We see that the two governing equations in the 𝒖 – 𝑝𝑤 formulation
The equations for the balance of mass and of linear momentum    are Equations ( 3 ) and ( 4 ). Because the pore pressure 𝑝𝑤 is present
for the mixture, in their general form, are given by Equations ( 1 )    in both equations, the system is solved through a PPE type
and ( 2 ).                                                        equation and a projection method.

4 of 31                                                                                 International Journal for Numerical and Analytical Methods in Geomechanics, 2026

### Page 5

2.1.1   PPE Solution and Time Integration                  Applying the revised first assumption, such that 1 = 1 − 𝑛 +  𝑛 ≈
                                                                                                          𝑄     𝐾𝑠    𝐾𝑤
                                                                              𝑛
                                                                                                                         , we rewrite Equation ( 1 ) as follows:
The implicit solution of the PPE at time 𝑡𝑛+ 1 , corresponding to     𝐾𝑤
time step 𝑛 + 1 , is written as follows:
                                                                 𝑛 𝑑 𝑝𝑤
                                                           − ∇ ⋅𝒗 − ∇ ⋅𝒗𝑠 = 0 .                 (11)                       𝑔         1                1                          𝐾𝑤  𝑑𝑡          ∇2 𝑝𝑤𝑛+ 1 = −𝜌𝑤 ∇ ⋅𝒗𝑛+𝑠  − 𝜌𝑤 𝑔 ∇2 𝑧𝑛+  .            (5)                     𝑘
                                                      Now, using Darcy’s law (Equation A12  in Appendix  I)  to
The projection method consists of a predictor–corrector scheme    determine the relative water–solid velocity, we arrive at,
to determine the velocities at 𝑡𝑛+ 1 such that the corrected velocity               (               )
enforces the incompressibility of the saturated mixture, in line            𝑑 𝑝𝑤   𝐾𝑤   𝑘
                                                     =        ∇2 𝑝𝑤 + 𝑘∇2 𝑧 + ∇ ⋅𝒗𝑠    ,        (12)
with the assumptions used to derive the formulation. First,               𝑑𝑡    𝑛   𝜌𝑤 𝑔
a so-called predicted velocity, which does not depend on the
pore-water pressure, is calculated explicitly as follows:            which is a rate equation for the pore pressure 𝑝𝑤 that can be
                                                                            explicitly integrated in time. Unlike the PPE approach, which
                 (       )
                            1                              assumes the solid and fluid phases are incompressible, by relaxing
               𝒗∗𝑠 = 𝒗𝑛𝑠 + Δ𝑡   ∇ ⋅𝝈′𝑛 + 𝒈    ,                (6)    the assumption of incompressibility of the fluid phase, we arrive                             𝜌𝑛
                                                                         at a slightly more generalizable and computationally simpler
where Δ𝑡 = 𝑡𝑛+ 1 − 𝑡𝑛 . Then, the final solid velocity that satis-    formulation. Note that gravity (potential energy) is introduced
fies the incompressibility condition is determined implicitly, by    into the calculation of pore water pressure through an elevation
adding the contribution of the pore-water pressure               head in Equation ( 12 ) (Laplacian of the vertical position, 𝑧).

                  𝒗𝑛+𝑠  1 = 𝒗∗𝑠 + Δ𝑡1 ∇ 𝑝𝑤𝑛+ 1 ,                   (7)      It is important to emphasize that the PR equation, Equation ( 12 ),                                𝜌∗                              presented here can be seen as a slightly modified and particular
                                                                 case of the PR equation presented in [ 54 ]. Equation ( 12 ) assumes
where 𝜌∗ is the projected mass density of the mixture, calculated    that the soil is fully saturated and, hence, cannot accommodate
using the projected velocity                                      unsaturated flow. For a more general framework that accounts
                                                                         for the three phases of the porous medium, the reader is referred
                    𝜌∗ = 𝜌𝑛 + Δ𝑡𝜌𝑛 ∇ ⋅𝒗∗𝑠 .                     (8)     to the works of Lian and co-authors [ 53, 54 ] and refe3ein.

Finally, substituting Equation ( 7 ) into ( 5 ) and assuming that
𝑧𝑛+ 1 ≈𝑧∗ , after some algebra, the Laplacian of 𝑝𝑤 becomes                                                      3   SPH Discretization and Implementation
                           (             )
             ∇2 𝑝𝑤𝑛+ 1 = − 𝑎∗ ∇ ⋅𝒗∗𝑠 + 𝑘∇2 𝑧∗   ,               (9)   The SPH method is a continuum-based meshfree Lagrangian
                                                      method that discretizes the problem domain into a set of particles,
where                                                       which are both mathematical discretization points used to solve
                            𝑏𝜌∗                               the governing equations in addition to Lagrangian particles that
                      𝑎∗ =                  ,                      (10)    evolve physical properties of the domain (e.g., mass, mass density,
                           𝜌∗ + 𝑏Δ𝑡
                                                                               stress, and strain). The interactions between these particles are
                                                                     dictated by a weighting or kernel function 𝑊whose valuewith 𝑏 = 𝜌𝑤 𝑔∕𝑘. Equation ( 9 ) is then used to find the pore-
                                                          depends on the distance between two particles of interest, andwater pressure, as we will see in upcoming sections, using an
                                                     on a length scale called the smoothing length ℎ, which definesexplicit solution.
                                                                the size of the support domain of the kernel. The value of a field
                                                                 function 𝑓( 𝒙 ) can then be determined for a particular particle
                                                               using a convolution integral over a domain Ω2.2   𝒖 – 𝒑𝒘 Pore Pressure Rate
Equation Formulation
                                                                             ⟨𝑓( 𝒙 ) ⟩=   𝑓( 𝒙′) 𝑊( 𝒙 − 𝒙′, ℎ)d𝒙′ ,            (13)
                                                                       ∫Ω
An alternative formulation for the 𝒖 – 𝑝𝑤 can be cast such that
the incompressibility of the pore water phase is enforced using    where 𝒙 is the position vector in three dimensions, and 𝑡is time.
the bulk modulus of the water 𝐾𝑤 itself, to ultimately obtain a   The exact integral in Equation ( 13 ) can be approximated using the
rate equation for the pore pressure 𝑝𝑤 that can be integrated in    following summation:
time explicitly. The following assumptions are the same as those
in the PPE version of the 𝒖 – 𝑝𝑤 formulation, with a slight change           ∑𝑁 𝑚𝑗
                                                                           ⟨𝑓 ( 𝒙 ) ⟩𝑖 =     𝑓 ( 𝒙𝑗 ) 𝑊𝑖𝑗 ,                 (14)in the first assumption:                                                                                                            𝑗= 1 𝜌𝑗

 1.  Intrinsically incompressible solid fraction: 𝐾𝑠 →∞. Spatial    where ⟨⟩signifies approximation, the subscript 𝑗represents the
    gradient of water density is negligible, ∇ 𝜌𝑤 ≈0 although its   𝑁-numbered neighboring particles of particle 𝑖, located at 𝒙 =
    compressibility is determined by the water bulk modulus.           𝒙𝑖 , 𝑊𝑖𝑗 = 𝑊( 𝒙𝑖 − 𝒙𝑗 , ℎ) , 𝑚𝑗 is the mass, and 𝜌𝑗 is mass density
                                                                       of the 𝑗th particle. Note that the summation is performed over
Hence, 𝐾𝑤 →∞is no longer assumed and therefore 1∕ 𝑄 →0     all neighboring particles of particle  𝑖, including  itself. Only
does not hold.                                                          particles within a radius 𝑘ℎ ℎpertaining to the 𝑖th particle will

International Journal for Numerical and Analytical Methods in Geomechanics, 2026                                                             5 of 31

### Page 6

be considered neighbors ( 𝑗) and included in the summations in    For the conservation of momentum, Equation ( 4 ), we use EquaEquations 14 and 15 . The coefficient 𝑘ℎ = 2 . 0 is usually chosen in    tion ( 19 ) to discretize the divergence of the effective stress ∇ ⋅𝝈,
most SPH applications and in this work [ 39 ]. Replacing 𝑓( 𝒙 ) with   and Equation ( 20 ) for the gradient of the pore water pressure ∇ 𝑝𝑤 .
its spatial derivative, applying the divergence theorem, and taking    For the divergence of the solid velocity in the balance of mass
advantage of the symmetric and positive nature of the kernel,    equation (namely Equation 3 for the PPE approach or in the PR
yields a similar expression for the gradient of a field function,    form of the equation, Equation 12 ), we use the SPH operator in
approximated as follows:                                      Equation ( 21 ) with the corrected kernel gradient. For more details
                                                     on the proper selection of operators, see [ 22, 67 ].
         ∑𝑁 𝑚𝑗
            ⟨∇ 𝑓 ( 𝒙 ) ⟩𝑖 =     𝑓 ( 𝒙𝑗 )∇ 𝑊𝑖𝑗 ,               (15)
                                𝑗= 1 𝜌𝑗                           To discretize the Laplacian of the pore pressure in the balance of
                                                       mass equations, we utilize the operator in Equation ( 22 ), proposed
where ∇ = ( 𝜕 ∕𝜕 𝑥, 𝜕 ∕𝜕 𝑦 , 𝜕 ∕𝜕 𝑧)𝑖 is the vector of partial derivatives    by Morris et al. [ 70 ],
with respect to the three spatial coordinates, evaluated at the                       𝑁
                              ∑ 𝑚𝑗            𝒙𝑖𝑗position of particle 𝑖.                                                                     ⟨∇2 𝑓⟩𝑖 = 2         ( 𝑓𝑖 − 𝑓𝑗 )      ⋅̃∇𝑊𝑖𝑗 ,         (22)
                                                                                                     𝑗= 1 𝜌𝑗            |𝒙𝑖𝑗 |2

3.1   SPH Discrete Operators                         where  𝒙𝑖𝑗 = 𝒙𝑖 − 𝒙𝑗 . Although alternative SPH operators for
                                                                the Laplacian exist [ 41 ], they require additional computational
In order to spatially discretize the partial differential equa-    and arithmetic cost. Furthermore, recent work has shown that
tions (PDEs) seen in Section 2 , and to transform the PDEs into    Morris’s operator for the Laplacian does not cause accuracy
ordinary differential equations in time, we make use of the SPH     losses for large deformation problems with significant amounts
approximations, or so-called SPH operators for fields, gradients     of particle disorder [ 67–69 ].
of fields, and for Laplacians of fields. We note that the previously
mentioned SPH approximation (operator) in Equation ( 15 ) is not
ideal as it does not guarantee the vanishing of the gradient of a    3.2   SPH Discretization of the PPE Equation
constant field function 𝑓, which can be tensor- or scalar-valued.
One way to mitigate these errors is to use the following commonly    In the PPE version of the 𝒖 – 𝑝𝑤 formulation, Equations ( 4 ) and
adopted operator for the gradient:                                           ( 3 ) are discretized using the previously mentioned SPH operators
                                                                    yielding Equations ( 23 ) and ( 24 ), which are highlighted in the box
        ∑𝑁 𝑚𝑗                                    below.
           ⟨∇ 𝑓⟩𝑖 =         ( 𝑓𝑗 − 𝑓𝑖 ) ⊗̃∇𝑊𝑖𝑗 ,             (16)
                          𝑗= 1 𝜌𝑗
                                             PPE 𝒖 – 𝒑𝒘 Governing Equations and Discretization
where ̃∇𝑊𝑖𝑗 = 𝑳𝑖 ⋅∇ 𝑊𝑖𝑗 is the corrected gradient of the kernel
function, with                                                                 Let  ⊂ℝ𝑑 ( 𝑑 = 2 , 3 ) be the domain occupied by the porous
                                                      medium, with 𝑡 ∈(0 , 𝑇] . The governing equations are:                            𝜕𝑊𝑖𝑗
                                                                 ,                        (17)              ∇ 𝑊𝑖𝑗 =                                                              (                                                                    )                                                            ⟩                                                         ⟨                                 𝜕𝒙𝑖                                     ∑𝑁                                                                                                                  𝝈′𝑖   𝝈′𝑗                                                                  𝑑𝒗𝑠   1       1                                                                                              𝑑𝒗𝑠
                                                                    𝑑𝑡and                                                = 𝜌∇ ⋅𝝈′+ 𝜌∇ 𝑝𝑤 + 𝒈 →   𝑑𝑡     𝑖 = 𝑗= 1 𝑚𝑗  𝜌2𝑖 + 𝜌2𝑗  ⋅∇ 𝑊𝑖𝑗
                                              (                                                    )            [                             ]− 1                           ∑𝑁                                                                    𝑝𝑤𝑖 + 𝑝𝑤𝑗       ∑𝑛 𝑚𝑗                                                                𝑚𝑗                                                                                      𝟏 ⋅∇ 𝑊𝑖𝑗 + 𝒈 ,   in  × 𝑡          (23)               𝑳𝑖 =                                 ( 𝒙𝑗 − 𝒙𝑖 ) ⊗∇ 𝑊𝑖𝑗       ,            (18)        +                                                                                                          𝜌𝑖 𝜌𝑗                                                                                      𝑗= 1                       𝑗= 1 𝜌𝑗

which enables first-order consistency in the approximation of the               𝑘         ∑𝑁 𝑚𝑗 (      )
                                                                    ∇2 𝑝𝑤 + 𝑘∇2 𝑧 = 0 →                                                                                                                                                   𝒗𝑠𝑗 − 𝒗𝑠𝑖  ⋅̃∇𝑊𝑖𝑗gradient of 𝑓.                                   ∇ ⋅𝒗𝑠 +                                                                    𝜌𝑤 𝑔                                                                                                                       𝑗= 1 𝜌𝑗
                                                            [
For the divergence operator used to discretize the balance of                                                                                                         𝑘𝑖 ∑𝑁 𝑚𝑗 (      )  𝒙𝑖𝑗
linear momentum and the velocity divergence in the balance of           + 2           𝑝𝑤𝑖 − 𝑝𝑤𝑗         ⋅̃∇𝑊𝑖𝑗
                                                                       𝜌𝑤 𝑔  𝑗= 1 𝜌𝑗               |𝒙𝑖𝑗 |2mass, three operators are commonly utilized as follows:
                                                                        ]
                 (                      )                           ∑𝑁 𝑚𝑗 (                                                                                         )  𝒙𝑖𝑗        ∑𝑁                                      𝑓𝑖   𝑓𝑗                                                + 𝜌𝑤 𝑔                                                                                                                 𝑧𝑖 − 𝑧𝑗                                                                                                          ⋅̃∇𝑊𝑖𝑗 = 0 ,   in  × 𝑡     (24)
          ⟨∇ ⋅𝑓⟩𝑖 = 𝜌𝑖   𝑚𝑗   +   ∇ 𝑊𝑖𝑗 ,           (19)                 𝑗= 1 𝜌𝑗            |𝒙𝑖𝑗 |2                             𝑗= 1     𝜌2𝑖    𝜌2𝑗

        ∑𝑁 𝑚𝑗 (      )
           ⟨∇ ⋅𝑓⟩𝑖 =        𝑓𝑗 + 𝑓𝑖 ∇ 𝑊𝑖𝑗 ,            (20)
                             𝑗= 1 𝜌𝑗                       We notice that in the PPE approach, the pore pressure appears
                                                                    in both Equations ( 23 ) and ( 24 ) and these are coupled. To solve
                                                                the PPE, the projection method is used, taking Equation ( 9 ) fromand
                                                                the projection method and applying it to the SPH operators, and
         ∑𝑁 𝑚𝑗 (      )                     making ( 𝑝𝑤𝑖 )𝑛+ 1 an explicit function of parameters at 𝑡𝑛 , we obtain
            ⟨∇ ⋅𝑓⟩𝑖 =        𝑓𝑗 − 𝑓𝑖 ∇ 𝑊𝑖𝑗 .             (21)    the following:                             𝑗= 1 𝜌𝑗

6 of 31                                                                                 International Journal for Numerical and Analytical Methods in Geomechanics, 2026

### Page 7

∑𝑁 𝑚𝑗 [        1        ] 𝒙𝑛𝑖𝑗   2          ( 𝑝𝑤𝑖 )𝑛+ − ( 𝑝𝑤𝑗 )𝑛        ⋅̃∇𝑊𝑛𝑖𝑗 =     𝑗= 1 𝜌𝑛𝑗                   |𝒙𝑛𝑖𝑗 |2                                Pressure Rate 𝒖 – 𝒑𝒘 Discretized Formulation

    [                                            ]
  ∑𝑁 𝑚𝑗 (      )    ∑𝑁 𝑚𝑗 (     ) 𝒙𝑛𝑖𝑗                                                                 Let  ⊂ℝ𝑑 ( 𝑑 = 2 , 3 ) be the domain occupied by the porous − 𝑎∗         𝒗∗𝑠𝑗 − 𝒗∗𝑠𝑖  ⋅̃∇ 𝑊𝑛𝑖𝑗 + 2 𝑘         𝑧∗𝑖 − 𝑧∗𝑗        ⋅̃∇ 𝑊𝑛𝑖𝑗    .
        𝑗= 1 𝜌𝑛𝑗                          𝑗= 1 𝜌𝑛𝑗           |𝒙𝑛𝑖𝑗 |2             medium, with 𝑡 ∈(0 , 𝑇] . The governing equations are:
                                                                (25)                                                          ⟨  ⟩   𝑁  (    )
                                                                  𝑑𝒗𝑠   1       1             𝑑𝒗𝑠  ∑     𝝈′𝑖   𝝈′𝑗
The second           and  last step  is to isolate the term containing      𝑑𝑡 = 𝜌∇ ⋅𝝈′+ 𝜌∇ 𝑝𝑤 + 𝒈 →   𝑑𝑡     𝑖 = 𝑗= 1 𝑚𝑗  𝜌2𝑖 + 𝜌2𝑗  ⋅∇ 𝑊𝑖𝑗        1( 𝑝𝑤𝑖 )𝑛+ on the left-hand side of the equation, which after some
                                               (     )
manipulation, yields the explicit solution for the PPE         ∑𝑁     𝑝𝑤𝑖 + 𝑝𝑤𝑗
                                                  +   𝑚𝑗           𝟏 ⋅∇ 𝑊𝑖𝑗 + 𝒈 ,   in  × 𝑡          (30)                       𝑁 [       ]             ∑                                                     𝑗= 1         𝜌𝑖 𝜌𝑗
                           𝐴𝑗 ( 𝑝𝑤𝑗 )𝑛 + 𝐵𝑖
               (   )𝑛+ 1    𝑗= 1                                               (                                                               )                                                                               ,              (26)              𝑝𝑤𝑖   =                                                       𝑑 𝑝𝑤                                                                     𝑘                                                          𝐾𝑤                                 𝐴𝑖                                                =                                                                       ∇2 𝑝𝑤 + 𝑘∇2 𝑧 + ∇ ⋅𝒗𝑠
                                                                    𝑑𝑡    𝑛   𝜌𝑤 𝑔
where
                                                               [                                                 ⟩                                             ⟨
                                                                𝑑 𝑝𝑤                                 ∑𝑁 𝑚𝑗 (      )                                                                    𝐾𝑤        ∑𝑁 𝑚𝑗  𝒙𝑛𝑖𝑗                                                         =                                                                                                                                 𝒗𝑠𝑗 − 𝒗𝑠𝑖  ⋅̃∇𝑊𝑖𝑗                 𝐴𝑖 = 2                                                                       𝑛                                      ⋅̃∇𝑊𝑛𝑖𝑗 ,                (27)      →     𝑑𝑡                                                                                                              𝑗= 1 𝜌𝑗                                                                                                                                                                                                                  𝑖                            𝑗= 1 𝜌𝑛𝑗 |𝒙𝑛𝑖𝑗 |2

so                                                                                                     𝑘𝑖 ∑𝑁 𝑚𝑗 (      )  𝒙𝑖𝑗
                                                  + 2                                                                                                                  ⋅̃∇𝑊𝑖𝑗                                                                          𝑝𝑤𝑖 − 𝑝𝑤𝑗   ∑𝑁         [  (  )𝑛 ] ∑                                                                                                                                |𝒙𝑖𝑗 |2                        𝑁 𝑚𝑗 (  )𝑛  𝒙𝑛𝑖𝑗                                                                     𝜌𝑤 𝑔 𝑗= 1 𝜌𝑗
          𝐴𝑗  𝑝𝑤𝑗   = 2       𝑝𝑤𝑗          ⋅̃∇𝑊𝑛𝑖𝑗 ,     (28)
         𝑗= 1                   𝑗= 1 𝜌𝑛𝑗         |𝒙𝑛𝑖𝑗 |2                             𝑁                 ]
                           ∑ 𝑚𝑗 (      )  𝒙𝑖𝑗
                                               + 2 𝑘𝑖                                                                                                                 𝑧𝑖 − 𝑧𝑗                                                                                                        ⋅̃∇𝑊𝑖𝑗    ,   in  × 𝑡      (31)and                                                                                                                     |𝒙𝑖𝑗 |2                                                                                           𝑗= 1 𝜌𝑗              [
       ∑𝑁 𝑚𝑗 (      )
             𝐵𝑖 = − 𝑎∗          𝒗∗𝑠𝑗 − 𝒗∗𝑠𝑖  ⋅̃∇𝑊𝑛𝑖𝑗
                         𝑗= 1 𝜌𝑛𝑗                                To determine the pore water pressure at time step 𝑛 + 1 , we can
                                ]                   explicitly integrate Equation ( 31 ) in                                                                                                      time,
      ∑𝑁 𝑚𝑗 (     ) 𝒙𝑛𝑖𝑗                                                             ⟩                                                          ⟨
         + 2 𝑘                                                                                 𝑑 𝑝𝑤                           𝑧∗𝑖 − 𝑧∗𝑗                                           ⋅̃∇𝑊𝑛𝑖𝑗    .        (29)
                                                                                                Δ𝑡              (32)                                    |𝒙𝑛𝑖𝑗 |2                      𝑗= 1 𝜌𝑛𝑗                                                                                                      ( 𝑝𝑤𝑖 )𝑛+ 1 = ( 𝑝𝑤𝑖 )𝑛 +                                                                                                   𝑑𝑡
                                                                                                                                                                                                                                                                     𝑖
The overall algorithm and solution flow for the PPE 𝒖 – 𝑝𝑤                                                     The overall algorithm and solution flow for the PR 𝒖 – 𝑝𝑤
formulation is summarized in Algorithm B1 of Appendix  II.                                                               formulation is summarized in Algorithm B2 of Appendix II.
Note that the PPE solution above is based on an explicit time
integration scheme. This scheme, while only first-order accurate,
                                                            3.4    Boundary Conditionsprovides good results for the small time steps required, is in
line with the explicit nature of SPH, and is computationally
                                                             For a domain  ⊂ℝ𝑑 ( 𝑑 = 2 , 3 ) with boundary 𝜕 , partitionedinexpensive. However, second- or higher-order methods, such
                                                                     into velocity, traction, pressure, and flux boundaries 𝜕 𝑣 , 𝜕 ℎ ,as Runge–Kutta integrators, could likely provide more accurate
                                                           𝜕 𝑝 , and 𝜕 𝑞 , respectively, with mutually disjoint intersections,solutions, albeit requiring more computational time. The choice
                                                       and with 𝑡 ∈(0 , 𝑇] , the following boundary conditions must beof integrator that best balances accuracy and computational time
                                                                           satisfied in the initial boundary value problem,is outside the scope of this work.

                   ⎧ 𝝈⋅𝒏 = 𝒉 ,          on 𝜕ℎ × 𝑡  (Neumann: prescribed traction),
                   ⎪
                   ⎪ 𝒗 = ̂𝒗,             on 𝜕𝑣 × 𝑡   (Dirichlet: prescribed velocity),
                   ⎪
                   ⎨                                                                                                        (33)
                   ⎪ 𝑝𝑤 = ̄𝑝𝑤 ,           on 𝜕𝑝 × 𝑡   (Dirichlet: prescribed pore pressure),
                   ⎪
                   ⎪              −𝑘                     ∇ 𝑝𝑤 ⋅𝒏 = ̄𝑞𝑤 ,  on 𝜕𝑞 × 𝑡  (Neumann: prescribed fluid flux).                   ⎩                           𝜌𝑤 𝑔

3.3   SPH Discretization of the Pressure Rate         where 𝒏 is the unit normal vector to the boundary, 𝒉 is the
Formulation                                                   prescribed traction vector,  ̂𝒗 is a prescribed velocity, ̄𝑝𝑤  is a
                                                                  prescribed pore pressure, and ̄𝑞𝑤 is a prescribed fluid flux (equal
In the PR version of the 𝒖 – 𝑝𝑤 formulation, Equations ( 4 ) and ( 12 )    to zero for undrained boundaries).
are discretized using the SPH operators yielding Equations ( 30 )
and  ( 31 ). We note that only Equation  ( 31 )  is different from    For the Dirichlet-type boundary conditions for the solid velocEquation ( 24 ) in the PPE approach.                                             ity, so-called dummy or boundary particles are used, where

International Journal for Numerical and Analytical Methods in Geomechanics, 2026                                                           7 of 31

### Page 8

the domain particles are enveloped by 3–4 layers of boundary    3.6   Time Stepping and Numerical Stability
particles in lieu of solid physical walls, helping to enforce no
penetration of the boundaries by the domain particles, and also   Time integration stability of the discretized equations is guaranensuring that the particles near the domain edges do not have    teed by choosing the minimum time step required to calculate
truncated kernels. The boundary particles can be fixed in space    both the solid displacement 𝒖 , and the pore fluid pressure 𝑝𝑤 ,
or may move at a prescribed velocity, and their stresses are
determined through an extrapolation from the stress pertaining
to neighboring domain particles, using the formulation seen in                       Δ𝑡 ≤min(Δ𝑡𝑠 , Δ𝑡𝑤 )                    (37)
[ 109 ]. For Neumann boundary conditions (e.g., to apply tractions
or confining stresses), we use the flexible confined boundary    where the time step for the solid displacement arises from the CFL
conditions method proposed by [ 114 ], as seen in the examples of    condition,
Cryer’s problem and in undrained triaxial tests.
                                                                                                 Δ𝑡𝑠 ≤ 𝑎ℎ                         (38)
To apply Dirichlet boundary conditions for the pore pressure,                                         𝑐
it is important to first identify the location of the free surfaces,
                                                            with 𝑐the numerical sound speed of the solid phase. The
and here the tracking method of [ 52 ] is used. Dirichlet boundary
                                               maximum time step for fluid pressure is given by a similar von
conditions for the pore pressure are applied by either setting
                                                Neumann stability analysis (see [ 53 ]),
the pore pressure to zero at the free surfaces, as in the method
of Skillen  [ 86 ], or applied by setting a desired value of the                                      ℎ2pore pressure at the boundary (dummy particles). However, to                         Δ𝑡𝑤 ≤𝑎𝐶𝑤                         (39)                                                                                  𝑘
enforce Neumann boundary conditions for the pore pressure,
and to ensure ∇ 𝑝𝑤 ⋅𝒏 = 0 for undrained boundary conditions,    where 𝑎 ≤ 1 , ℎ = 𝑘ℎ Δ  is the smoothing length with 𝑘ℎ the
some additional treatment is needed. We adopt the moving least    smoothing length factor, and 𝐶𝑤 = 𝜌𝑤 𝑔𝑛 . In general, 𝑎 = 0 . 1 [ 20,
                                                                                                       𝐾𝑤
square (MLS) formulation presented in Chow et al. [ 27 ], which                                                               38 ] not only provides the method with stability, but also the
extrapolates the pore pressure from the domain particles to the                                                                necessary accuracy in the integration process.
boundary particles using a specially corrected (MLSs) kernel that
is zero- and first-order consistent, allowing for linear pressure                                                     The stability of the PPE approach, while still constrained by
fields to be recovered exactly.                                                                the CFL condition, is also governed by the parameter 𝑎∗ , which
                                                                    multiplies the pressure correction and effectively acts as a gain or
                                                                   amplification factor in the explicit Poisson update. The implicit
3.5    Constitutive Relations                                correction step introduces this feedback parameter 𝑎∗

We assume that the effective stress is driven by the deformation                             𝑏𝜌∗           𝜌𝑤 𝑔
                                                                           𝑎∗ ( 𝑘 , Δ𝑡 ) =                 ,    𝑏 =         ,          (40)
rate and can be evaluated using any elastoplastic constitutive                            𝜌∗ + 𝑏Δ𝑡         𝑘
model. In this work, we postulate a hypo-elastoplastic model that
relates the Jaumann rate of the effective stress tensor directly to    which controls the amplitude of the pore-pressure adjustment.
the deformation rate tensor, as follows:                          For very small time increments, Δ𝑡 →0 , 𝑎∗ →𝑏, which can
                                                      become arbitrarily large as the permeability decreases. In this
                             ▿′
                 𝝈 = 𝒄ep ∶ 𝒅 .                      (34)    regime the pressure correction acts with excessive gain, leading to
                                                            numerical instability. Conversely, for Δ𝑡 →∞, one obtains 𝑎∗ →
The Jaumann rate of the effective stress is given by the following:    𝜌∗ ∕Δ𝑡 →0 , which damps the feedback and stabilizes the scheme.
                                                                  Therefore, admissible time steps must  lie within a bounded
                      ▿′                                                 interval
             𝝈 = ̇𝝈′ − 𝝎 ⋅𝝈′ + 𝝈′ ⋅𝝎 .                 (35)
                                                                                       Δ𝑡min ( 𝑘) ≤ Δ𝑡 ≤ Δ𝑡CFLmax ,                 (41)
In Equation  ( 34 ),  𝒄ep denotes the  elastoplastic stress–strain
response tensor. For purely elastic behavior, 𝒄ep reduces to the
                                                       where the lower limit Δ𝑡min ( 𝑘) is defined implicitly by requiring
elastic tensor 𝒄e . For an isotropic material, 𝒄e can be expressed in                                                                     that 𝑎∗ ( 𝑘 , Δ𝑡 ) remain below a prescribed stability threshold, for
terms of the bulk modulus, 𝐾, and shear modulus, 𝜇, as follows:                                                             example, 𝑎∗ < 1 . In practice, stability is achieved by choosing
                                                        Δ𝑡within the overlap between the CFL restriction and the 𝑎∗ -
                   (      )
                                                             based lower bound, ensuring both accurate resolution of wave
                 𝒄e = 𝐾𝟏 ⊗𝟏 + 2 𝜇  𝑰 −1 𝟏 ⊗𝟏    .            (36)                                 3                          propagation and controlled pressure correction. In contrast to
                                                                the hypothesis of Morikawa and Asai [ 67 ] for the 𝒖 – 𝒘 – 𝑝𝑤
Here, 𝑰is the fourth rank symmetric identity tensor with com-    formulation, where the additional stability condition on 𝑘and Δ𝑡
ponents 𝐼𝑖 𝑗 𝑘𝑙 = ( 𝛿𝑖𝑘 𝛿𝑗𝑙 + 𝛿𝑖𝑙 𝛿𝑗𝑘 )∕2 (Einstein’s notation is assumed)    imposed an upper bound on the admissible time step, the PPE
and 𝟏 is the second-order identity tensor. Two different yield    formulation introduces a lower bound through 𝑎∗ . This reversal
criteria are adopted in this study to simulate the elastoplastic    creates an additional challenge: Stability in the 𝒖 – 𝑝𝑤 system
behavior of soils, the Drucker–Prager and the MCC models. For    requires time steps that are neither too large (CFL) nor too small
further details on the yield criteria, the reader is referred to [ 17, 18 ],     ( 𝑎∗ ), restricting the feasible range more severely. For a discussion
and for the return mappings in the context of the SPH method to   on the stabilization techniques employed in the paper, the reader
[ 33 ].                                                                                is referred to Supporting Information Section I.

8 of 31                                                                                 International Journal for Numerical and Analytical Methods in Geomechanics, 2026

### Page 9

1) 𝜋, and

                                                                                        𝑘(1 − 𝜈) 𝐸
                                                                                                    𝑐𝑣 =                                     (43)
                                                                                              (1 + 𝜈)(1 − 2 𝜈) 𝜌𝑤 𝑔

                                                                                      is the consolidation coefficient.

                                                              In Figure 2 , we compare the results of the analytical solutions for
                                                                the pore pressure against the pore pressure histories determined
                                                         from the SPH simulations using the PR formulation, given
                                                                        different combinations of the numerical stabilization parameters,
                                            𝛼and 𝜉, from the artificial viscosity and kinematic damping,
                                                                         respectively. The artificial viscosity parameter 𝛽is kept at a value
FIGURE  1    Setup (left) and contours of the normalized pore pres-
                                                                       of 0.0. Contours of the normalized pore pressure 𝑝𝑤 ∕𝑞0 are
sure 𝑝𝑤 ∕𝑞0  at different values of the dimensionless time factor 𝑇𝑣
                                                                  displayed at different elapsed dimensionless time in Figure 1 for
(right) for the 1-D consolidation problem. Solution obtained with the PR
                                                                the simulation with 𝛼= 0 and 𝜉= 4e − 5.
formulation.

                                                    As seen from the simulation  results, some combination of
4    Formulation Verification                                     artificial viscosity and kinematic damping is needed in order for
                                                                the solution not to diverge. In general, the artificial viscosity
In this section, we verify the performance of the two different    alone is enough to stabilize the solution, although there is some
𝒖 – 𝑝𝑤 formulations against analytical solutions from a series of     slight error for the earlier dimensionless times of 𝑇𝑣 = 0 . 005 and
different poroelasticity problems as well as against the analytical    𝑇𝑣 = 0 . 05 towards the bottom of the soil column. Greater accuracy
solutions to stress paths in undrained triaxial tests using the     relative to the analytical solution is shown for simulations with
MCC model.                                                  kinematic damping and 𝜉> 0 , although if the kinematic damping
                                                        becomes too large, the system becomes overdamped, leading to
                                                                      errors in the earlier dimensionless times, although in the case of
                                       𝜉= 1e-4, these are still small. From testing, we see that the ideal
4.1   1D Consolidation
                                                             range for 𝜉is between 10 and 50 times the magnitude of the time
                                                                           step, and that the stabilization effects of 𝛼on the solution are
As a first problem, we consider the one-dimensional consolida-
                                                                       largely superfluous. Thus, because large 𝛼is known to excessively
tion of a poroelastic column, known as the Terzaghi consolidation
                                                                       dissipate energy from the system, we keep 𝛼= 0 . 1 going forward
problem, both under an applied external load and due to self-
                                                                    in the coupled hydromechanical simulations, a value agreeing
weight. Results from self-weight consolidation are provided in
                                                            with other works in the literature [ 22 ].
Supporting Information Section II (see Figures S1 and S2 ). The
soil column is 1.0-m high and 0.1-m wide and is discretized into
                                                        To test the robustness of the PR formulation under different
1000 particles with an initial interparticle distance of Δ = 0 . 01 m
                                                                 hydraulic conductivities, we perform two additional simulations
(following [ 53–55, 67, 110 ], see the schematic in Figure 1 ). The
                                                            with 𝑘 = 1e − 2 and 𝑘 = 1e − 4 m/s noting good agreement with
effects of gravity are not included in the consolidation problem
                                                                the analytical solutions as seen in Figure 3 especially as the
under external load. The Young’s modulus and the Poisson’s
                                                                  conductivity is decreased.
ratio of the solid skeleton were 𝐸 = 2e 6 Pa and 𝜈= 0 . 3 , the bulk
modulus of the fluid was 𝐾𝑤 = 2e 8 Pa, the porosity was 𝑛 = 0 . 3 ,
                                                                         Similarly, we compare the performance of the PPE formulation
the conductivity was 𝑘 = 1e − 3 m/s, and the chosen time step was
                                                          under different conductivities against the analytical solutions,
Δ𝑡= 1e − 6 s. The bottom and lateral boundaries were assumed
                                                                   as seen in Figure 4 . In all three simulations, the time step
undrained, and a free surface with zero pore pressure is assigned
                                                                                      is kept fixed at Δ𝑡 = 1e − 6 s. The simulation with 𝑘 = 1e −
to the top. To initiate consolidation, an external load of magnitude
                                                          4 m/s does not converge and the simulation with 𝑘 = 1e −
𝑞0 = − 10 kPa was applied to the free surface particles in the form
                                                               3 m/s has some error at 𝑇𝑣 = 0.005 towards the bottom halfof an equivalent acceleration. Simulations are performed both
                                                                       of the soil column but  is otherwise satisfactory. For 𝑘 = 1e
with the PPE and PR formulations.
                                          − 2 m/s however, the simulation results follow the analytical
                                                                   solution closely. The loss of stability in the 𝑘 = 1e − 4 m/s
Terzaghi, in his one-dimensional consolidation theory, proposed
                                                                simulation can be attributed to the amplification factor 𝑎∗ ,
an analytical solution for the excess pore pressure build-up, and
                                                       which significantly outgrows that of the 𝑘 = 1e − 3 m/s and
then dissipation, as a function of time and of soil column depth,
                                                       𝑘 = 1e − 2 m/s simulations (see Figure 5 ), requiring a larger
𝑧,
                                                             time step, which  is at odds with the requirement from the
                   𝑗=∞     (  )                    CFL condition. In the case of 𝑘 = 1e − 3 m/s, increasing the
                    𝑀𝑧       ∑ 2 𝑝𝑤0
         𝑝𝑤 ( 𝑧) =                             sin                                 exp( − 𝑀2 𝑇𝑣 )        (42)    time step by an order of magnitude to Δ𝑡 = 1e − 5 s has the            𝑀    𝐻                       𝑗= 1                                                  effect of decreasing the amplification factor by around 5%–
                                                               10%, which is enough to improve fidelity with respect to the
where 𝑝𝑤0 = 𝑞0 is the initial excess pore pressure which holds if the     analytical solutions, see Figure 6A . Note that for the range
fluid and the solid particles are incompressible, 𝐻is the column     of parameters used in the simulations presented in this work,
height, 𝑇𝑣 = 𝑐𝑣 𝑡∕𝐻2 is a dimensionless time factor, 𝑀 = 0 . 5(2 𝑗 −    the PPE formulation is limited to 𝑘 > 10e − 4 m/s. For those

International Journal for Numerical and Analytical Methods in Geomechanics, 2026                                                        9 of 31

### Page 10

FIGURE  2    Normalized pore pressure 𝑝𝑤 ∕𝑞0 profiles compared to the theoretical solutions at 𝑇𝑣 = 0 . 005 , 0.05, 0.1, 0.25, 0.4, 0.5, 0.7, 1.0 for 𝑘 = 1e
− 3 m/s and Δ𝑡 = 1e − 6 s, for varying values of the artificial viscosity parameter 𝛼and the damping coefficient 𝜉. Solutions obtained with the PR
formulation.

FIGURE  3    Normalized pore pressure 𝑝𝑤 ∕𝑞0 profiles compared to the theoretical solutions at 𝑇𝑣 = 0 . 005 , 0.05, 0.1, 0.25, 0.4, 0.5, 0.7, 1.0 for 𝑘 = 1e
− 2 m/s, 𝑘 = 1e − 3 m/s, and 𝑘 = 1e − 4 m/s. Δ𝑡 = 1e − 6 s, 𝜉= 4e − 5 and 𝛼= 0 . 1 .

conditions, time steps obtained using the CFL condition (Equa-    and 𝑈is the degree of consolidation given by the following:
tion 39 ) can be used without significantly affecting the accuracy
of results.
                                                                                       𝑗=∞∑  2
The analytical solution for free surface settlement 𝑆of the soil            𝑈 = 1 −   𝑀2 exp( − 𝑀2 𝑇𝑣 ) .             (44)
column as a function of time is expressed as 𝑆( 𝑇𝑣 ) = 𝐻 𝑞0 𝑚𝑣 𝑈 ,                                               𝑗

10 of 31                                                                               International Journal for Numerical and Analytical Methods in Geomechanics, 2026

### Page 11

FIGURE 4    Normalized pore pressure 𝑝𝑤 ∕𝑞0 profiles for PPE approach compared to the theoretical solutions at 𝑇𝑣 = 0 . 005 , 0.05, 0.1, 0.25, 0.4, 0.5,
0.7, 1.0 for 𝑘 = 1e − 2 m/s, 𝑘 = 1e − 3 m/s, and 𝑘 = 1e − 4 m/s. Δ𝑡 = 1e − 6 s, 𝜉= 4e − 5, and 𝛼= 0 . 1 .

                                                            remaining examples in the paper. The PR formulation also has
                                                                the additional advantage that some degree of compressibility is
                                                              allowed for the fluid phase.

                                                            4.2     Cryer’s Problem

                                         A classical problem from poroelasticity is Cryer’s problem, where
                                                             a poroelastic sphere with a drained exterior surface boundary
                                                                                      is subjected to a uniform normal traction 𝑝0 at the surface. At
                                                                the center of the sphere, the pore pressure initially attains the
                                                                value of the traction 𝑝0 and then continues to rise to a peak
                                                                value before dissipating to zero. The pore pressure increase past
                                                               𝑝0 is caused by fluid draining along the surface boundary of the
                                                                   sphere, in turn leading to the transfer of a significant portion
FIGURE  5     Amplification factor 𝑎∗ as a function of time step Δ𝑡for     of the external applied load towards the center of the sphere
three different conductivity values, highlighting excessive gain for smaller    as the region facing the surface contracts due to pore pressure
conductivities at smaller time steps.                                       dissipation. This nonmonotonic pore pressure behavior is known
                                                                  as the Mandel–Cryer effect [ 29, 61 ], and can only be modeled
                                                            through a fully coupled solution such as that from the 𝒖 – 𝑝𝑤We note that 𝐻𝑞0 𝑚𝑣 is the final surface settlement of the soil
                                                                          set of equations stemming from Biot–Zienkiewicz theory, andcolumn after the excess pore pressure is fully dissipated, and 𝑚𝑣
                                                              not from uncoupled solutions such as Terzaghi’s one-dimensionalis the compression index defined as follows:
                                                                  consolidation theory. Thus, Cryer’s problem is used as a final
                           (1 + 𝜈)(1 − 2 𝜈)                      example to check the accuracy of the 𝒖 – 𝑝𝑤 pore PR formulation
               𝑚𝑣 =                           .                  (45)                              (1 − 𝜈) 𝐸                                for poroelasticity.

In Figure 6B , the normalized settlement 𝑆∕𝐻is plotted as a   The analytical solution for the pore pressure at the center of the
function of 𝑇𝑣 comparing the performance of both PPE and PR    sphere, that is, at 𝑅 = 0 , is given by the following:
formulations against the analytical solutions. We see that the PR
formulation follows the analytical solution very closely, but the    𝑝𝑤 ( 𝑅 = 0)  ∑∞          sin 𝜉𝑗 − 𝜉𝑗          (       )
solution from the PPE formulation is not as close with increasing          = 𝜂                           exp − 𝜉2𝑗 𝑐𝑣 𝑡∕𝑎2                                                                   𝑝0          𝑗= 1 𝜂𝜉𝑗 cos 𝜉𝑗 ∕2 + ( 𝜂− 1) sin 𝜉𝑗
dimensionless time, and experiences some  slight oscillation
                                                                                                                                  (46)
around the theoretical solution. This oscillation may be attributed
                                                       where the coefficients 𝜉𝑗 are the positive roots of the equation
to the lower stability of the PPE formulation for usual time steps,
and to an increased susceptibility to boundary effects near solid                  (       )
boundaries. The lower consistency on the approximation of pore                      1 − 𝜂𝜉2𝑗 ∕2  tan 𝜉𝑗 = 𝜉𝑗 .                 (47)
water pressures on the boundaries potentially counteract the
numerical damping necessary to reduce oscillations in the pore    Here the parameter 𝜂= (1 − 𝜈)∕(1 − 2 𝜈) holds for the case of
pressure field.                                                   incompressible fluid and incompressible solid matrix [ 97 ].

Overall, because of the decreased stability and additional time    Figure 7B plots the normalized pore pressure at the center of the
stepping restrictions in the PPE formulation, especially so around    sphere as a function of dimensionless time 𝑇𝑣 for four different
small conductivities pertaining to the undrained regime, which    simulations with different Poisson’s ratios, agreeing well with
are of interest in the retrogressive landslides studied in this paper,    the theoretical solution, and capturing the Mandel–Cryer effect.
we opt to use the pore PR form of the 𝒖 – 𝑝𝑤 formulation for the   As expected, decreasing the Poisson’s ratio has the effect of

International Journal for Numerical and Analytical Methods in Geomechanics, 2026                                                                      11 of 31

### Page 12

FIGURE 6    (A) Normalized pore pressure 𝑝𝑤 ∕𝑞0 profiles compared to the theoretical solutions at 𝑇𝑣 = 0 . 005 , 0.05, 0.1, 0.25, 0.4, 0.5, 0.7, 1.0 for
𝑘 = 1e − 3 m/s and Δ𝑡 = 1e − 5 s, 𝛼= 0 . 1 , 𝜉= 4e − 4 and the PPE formulation. (B) Comparison of the normalized settlement 𝑆∕𝐻as a function of 𝑇𝑣
for both the PPE and PR formulations. Note the results from the PR formulation are those shown with Δ𝑡 = 1e − 6 s, 𝛼= 0 . 1 , and 𝜉= 4e − 5.

FIGURE  7    (A) Schematic of Cryer’s problem with the poroelastic sphere of radius 𝑅 = 𝑎subjected to an all-around pressure 𝑝0 , and snapshots at
different 𝑇𝑣 showing a cross section of the sphere with contours of the normalized pore pressure 𝑝𝑤 ∕𝑝0 for the simulation with Poisson’s ratio 𝜈= 0 . 3 .
(B) Normalized pore pressure at the center of the sphere as a function of 𝑇𝑣 from the analytical solutions [ 97 ] compared to the GEOSPH simulations
for 𝜈= 0 . 1 , 0 . 2 , 0 . 3 , 0 . 45 . Δ𝑡 = 1e − 6 s, 𝛼= 0 . 1 , 𝜉= 4e − 5. Other than the varying Poisson’s ratio, the same elastic and material parameters as the
one-dimensional Terzaghi consolidation simulation are used.

enhancing the pore pressure peak past the magnitude of the    are applied to both sets of boundary particles at the top and
external traction. In Panel A of the figure, contours of the pore    bottom surfaces of the cylinder. All relevant material parameters
pressure are shown over a hemisphere to visualize the pore    from the soil pertaining to the MCC model are the same as
pressure increase and decay at the center.                           in  [ 33 ]. A permeability of 𝑘 = 1e − 8 m/s  is used to achieve
                                                            undrained conditions within the sample. To avoid any pore
                                                                         fluid dissipation at the boundaries and to ensure the sample is
4.3     Triaxial Testing in Undrained Limit              completely undrained, the free surfaces are treated as undrained,
                                                       and the free surface detection procedure for drained free surfaces
To test the 𝒖 – 𝑝𝑤 formulation in conjunction with an elastoplastic     is not performed. To apply the confining pressure 𝜎𝑐 , the flexible
constitutive model, we perform a series of triaxial tests under    confined boundary conditions of Zhao et al. [ 114 ] are imposed on
undrained conditions using the MCC model. We also compare    the lateral free surfaces of the cylinder.
these simulation results against those from similar triaxial simulations conducted with the weakly coupled undrained framework    Following the same procedure outlined in  [ 33 ],  stress and
in [ 33 ]. The soil cylinder used in the simulations is 0.15-m high,    deformation data are averaged from  all the particles within
has a diameter of 0.05 m, and is discretized using 53,175 particles,    a measurement region (cube) with a side length of 0.03 m
with an initial interparticle distance of 0.002 m. The top and    located at the center of the sample to ensure that the stress
bottom surfaces of the cylinder are constrained by a layer of     state of the measured particles follows a triaxial state and to
boundary particles, with the bottom fixed, and the top subjected    mitigate any particle disorder effects within the sample. In total,
to a constant velocity 𝑉 = 0 . 01 m/s in the vertical direction    three undrained simulations are performed, the first consisting
to compress the soil cylinder. Free-slip boundary conditions     of a lightly overconsolidated  soil  test (TU-L), a moderately

12 of 31                                                                               International Journal for Numerical and Analytical Methods in Geomechanics, 2026

### Page 13

FIGURE 8     Results of undrained triaxial test simulation using the 𝒖 – 𝑝𝑤 formulation and GEOSPH for a lightly overconsolidated soil (TU-L). The
stress history in 𝑝′ − 𝑞space is shown in (A) whereas the trajectory in log( 𝑝′) − 𝑒space is displayed in (B), and both are compared against the theoretical
solutions of Wood, see Supporting Information Section IV [ 102 ]. The blue to red color scheme depicts the temporal evolution of the load path computed
with SPH. In panel (C), a magnified region of panel (A) is shown comparing the 𝒖 – 𝑝𝑤 solution to the undrained framework of [ 33 ]. Snapshots of pore
pressure 𝑝𝑤 are shown at initial yielding (D) and at the CSL line (E) for the implementation without (left) and with (right) the Shepard regularization
technique.

overconsolidated test (TU-M), and a normally consolidated test
(TU-N). The initial preconsolidation pressure, ( 𝑝𝑐 )0 , was 200 kPa,
and the applied confining pressure, which equaled the initial
mean effective stress, was 150 kPa for TU-L, 200 kPa for TU-N,
and 30 kPa for TU-M. Results for the TU-L test can be seen in
Figure 8 , whereas for the TU-N and TU-M simulations, they are
displayed in Figure S3 and Figure S4 , respectively, in Supporting
Information Section III. For all three tests, the stress paths from
the SPH simulations closely follow the theoretical solution in 𝑝′ −
𝑞space as seen in Panel A, as well as in log ( 𝑝′) − 𝑒space in Panel
B, and the sample exhibits undrained behavior. In Panel C, we also
plot the stress path of the equivalent undrained simulation for
reference, showing how the 𝒖 – 𝑝𝑤 solution follows a stress path
closer to the analytical solution than does the undrained solution,
and also reaches the critical state line closer to the point where   FIGURE 9    Pore pressure ( 𝑝𝑤 ) histories for the three undrained
the analytical solution intersects. A discussion of the relative     simulations TU-M ( 𝑝0 = 30 and ( 𝑝𝑐 )0 = 200 kPa), TU-L ( 𝑝0 = 150 and
computational efficiency and costs of the undrained versus 𝒖 – 𝑝𝑤      ( 𝑝𝑐 )0 = 200 kPa), and TU-N ( 𝑝0 = 200 and ( 𝑝𝑐 )0 = 200 kPa), performed
formulations is shown in Supporting Information Section V (see    with the 𝒖 – 𝑝𝑤 formulation compared to the undrained framework of [ 33 ]
Figure S5 ).                                                         both implemented in GEOSPH , and to the theoretical solutions of Wood
                                                                                              [ 102 ].
The evolution of the pore pressure within the measurement
region in the SPH simulations is evaluated against predictions
from theoretical solutions, and is shown in Figure 9 . The pore    approaches a peak value as the stress state reaches the CSL. In
pressure compensates for the stresses not captured by the mean    TU-L, a slight kink appears at yielding, consistent with theoretical
effective pressure 𝑝′. For the lightly overconsolidated (TU-L) and     predictions. In contrast, for the moderately overconsolidated (TUnormally consolidated (TU-N) soils, it rises and asymptotically   M) soil, yielding causes the yield locus to contract, leading to

International Journal for Numerical and Analytical Methods in Geomechanics, 2026                                                               13 of 31

### Page 14

FIGURE 10    (A) Retrogressive slope failure simulation setup. (B) Initialized pore pressure 𝑝𝑤 and initialized effective vertical stress (C) after
𝐾0 = 0 . 5 and gravity loading.

a reduced difference between total and effective loading paths    the slope is supported by boundary particles along the base
and a gradual decline in pore pressure. Again the 𝒖 – 𝑝𝑤 solution     (no-slip condition) and left side wall (free-slip condition). The
shows slightly improved accuracy over the undrained framework,    computational domain of the second (Panel D) steeper slope, is
especially for axial strains greater than 5% in magnitude.            8-m-high, and possesses a length along the top of 16 m, and a
                                                                 length along the base of 17 m. The domain is also discretized
                                                            with the interparticle distance of Δ = 0 . 1 m, into 8470 particles,
5    Retrogressive Slope Failure                       and with similar boundary conditions as in the shallower slope
                                                            model. In the simulations, we use the Wendland 𝐶2 kernel, with
In this section, we compare the ability of the 𝒖 – 𝑝𝑤 formulation    a smoothing length factor of 1.5. To compare the strongly coupled
developed in this work and the undrained framework of [ 33 ] to    poromechanical model with a penalty-based approach suited
capture the flowslide and spread type retrogressive failures of     for undrained conditions, two different sets of simulations are
slopes under undrained conditions using the SPH method. In the    performed for each slope model, one with the 𝒖 – 𝑝𝑤 formulation
case of the 𝒖 – 𝑝𝑤 simulation, a very low permeability is used    presented here, and the second with the undrained framework of
to achieve the undrained limit or quasi-undrained conditions.     [ 33 ].
We take advantage of a benchmark slope geometry employed for
simulating retrogressive slope failure behavior in sensitive clays   The  sensitive  clay  material comprising both  slope models
in previous studies [ 22, 80 ], and focus on the effects of slope height     is assumed spatially homogeneous with an isotropic  elastic
and inclination on the landslide characteristics by considering    response with Young’s modulus 𝐸 = 25 . 0 MPa, and Poisson’s
two distinct computational models.                                    ratio 𝜈= 0 . 3 . The density of the mixture is 𝜌= 2 , 150 kg/ m3 ,
                                                              while that of water is 𝜌𝑤 = 1000 kg/ m3 , and the porosity is
To capture the behavior of sensitive clay, an elastoplastic model   𝑛 = 0 . 4 . Since undrained conditions are assumed, the value of
with isotropic strain softening behavior is used in conjunction    the internal friction angle is set to 𝜙= 𝜙𝑢 = 0◦, which reduces
with the Drucker–Prager yield criterion. The strain softening    the Drucker–Prager model to the isochoric von Mises model,
component degrades the strength parameters of the soil, namely    preventing the accumulation of volumetric plastic strains. The
the friction angle 𝜙and the cohesion 𝑐as a function of the accu-    peak cohesion is 𝑐𝑝 = 15 . 1 kPa, the residual cohesion, 𝑐𝑟 = 1 . 5
mulated plastic strain 𝜀𝑝𝑎 𝑐 𝑐 , following the exponential softening    kPa, the softening coefficient is 𝜂= 5 , and the dilatancy angle
rules of [ 106 ]:                                                                     is 𝜓 = 0◦. In both undrained and 𝒖 – 𝑝𝑤 simulations, the bulk
                                                       modulus of the fluid equals 𝐾𝑤 = 0 . 2 GPa, and in the 𝒖 – 𝑝𝑤
             ⎧                                                         𝑎 𝑐 𝑐                         simulation, the permeability is 𝑘 = 1e − 8 m/s to create quasi-                      𝑐 = 𝑐𝑟 + ( 𝑐𝑝 − 𝑐𝑟 ) 𝑒− 𝜂𝜀𝑝             ⎪
             ⎨                                        (48)    undrained conditions. The soil is assumed fully saturated with
             ⎪ 𝜙= 𝜙𝑟 + ( 𝜙𝑝 − 𝜙𝑟 ) 𝑒− 𝜂𝜀𝑝                                                          𝑎 𝑐 𝑐                       the water table coinciding with the slope’s free surfaces. In the             ⎩
                                                                   simulations, stresses are first initialized using the earth pressure
where the subscripts 𝑝and 𝑟denote peak and residual values     coefficient of 𝐾0 = 0 . 5 , and then with a gravity loading such that
of cohesion and friction, respectively, while 𝜂is the softening    the stresses achieve a geostatic state, where the particles reach
coefficient (or shape factor), which controls the rate of strength    a minimum kinetic energy. In the gravity loading simulation,
degradation as a function of the plastic strain.                      the peak strength parameters are used for the soil together with
                                       𝜂= 0 to stabilize the slope and achieve consolidation (for the
Two distinct sensitive clay slopes are analyzed with their respec-   𝒖 – 𝑝𝑤 simulation). The resulting effective stresses and pore
tive geometries shown in Figure 10 . The computational domain    pressures are taken for the retrogressive landslide simulation,
of the first (Panel A) consists of a 5-m-high slope at an inclination    which  is triggered by setting 𝜂= 5 and applying a strength
of 45 ◦, with a length of 25 m along the base and a length    reduction factor of 1.65 to the soil’s cohesion. In the undrained
along the top of 20 m. The slope is discretized into 11,275 SPH    simulation, the pore pressure is initialized to the hydrostatic
particles, with an initial interparticle distance of Δ = 0 . 1 m, and    condition prior to the strength reduction procedure, and the

14 of 31                                                                               International Journal for Numerical and Analytical Methods in Geomechanics, 2026

### Page 15

FIGURE  11     Retrogressive failure simulation progression over time for the simulation conducted with the undrained model. Contours show
accumulated plastic strain.

gravity loading step is performed under dry conditions. In terms    behind the sliding soil mass along the slip plane of Slide 1b,
of other simulation parameters, the time step is Δ𝑡 = 1e − 6 s, the    causing the development of a second slip surface (for Slide 2)
artificial viscosity, 𝛼𝜋= 0 . 1 , and the damping coefficient is 𝜉= 1e     after 3.5 s of simulation time. Slide 2 lasts until around 6.5 s of
− 5. Both simulations were run for a duration of 20 s.               simulation time and is followed by a third slide whose slip surface
                                                                                      is fully traced after around 8 s. After the third sliding event,
                                                                         sufficient failed mass is in place to buttress the exposed back-
5.1    5-m-High Slope Simulation                            scarp, ending the retrogressive failure process. In the simulation,
                                                                the final run-out distance was approximately 21.6 m and the final
In Figure 11 , snapshots at different moments in time, over the    retrogression distance was 14.0 m (see Figure 12 ).
duration of the undrained simulation, show contours of the
accumulated plastic strain and the evolution of the retrogressive   A few noteworthy observations can be drawn pertaining to the
slope failure process, with emerging slip planes and zones of    structure of the retrogressive slope failure. The slope fails under
localized plastic strain. In Figure 12 , contours of the displacement    a series of successive retrogressive slides involving rotational slip
are shown at the same time steps. Due to the strength reduction,     surfaces, typical of flowslides. After the rotational failure part of
the clay slope becomes unstable and lateral spreading initiates,    the different sliding events is concluded, however, the disturbed
leading to the development of an  initial horizontal zone of     failed soil mass now experiences spreading, reshaping the soil
localized plastic strain or shear band along the base of the slope    into intact Δ-shaped horsts and ∇ -shaped grabens. The horsts
propagating inwards away from the slope toe. Within the localized    and grabens become especially visible after 5.5–8.0 s of simulation
zones of plastic strain, the clay undergoes remolding and the    time, and the angle between the sliding surface and the horsts
strength is reduced through the strain softening model promoting      is close to the theoretical prediction of 45 ◦± 𝜙𝑢 ∕2 = 45◦. The
sliding. The bottom horizontal shear band proceeds to curve    undrained simulation manages to successfully capture the flow
upwards as it continues propagating, and reaches the top surface     of remolded clay between the model base and the graben and
after 0.6 s of simulation time. Subsequently, a secondary shear    horst blocks in addition to the squeezing of this clay through
band forms, located closer to the slope toe, forming two distinct    localized strain zones between the intact blocks. Lastly, the mass
and competing slip surfaces leading to sliding events with circular    displaced by the three main sliding events is similar, matching
failure surfaces, denoted Slides 1a and 1b (Figure 12 ). As the     field observations [ 48, 93 ]. In this way, the undrained simulations
initial slope failure continues, the sliding masses disintegrate,    predict flow and then some degree of spread behavior in the
breaking up into pieces delimited by secondary shear bands, as   same landslide.
first seen around 1.5 s of simulation time with the development of
a secondary v-shaped band, characteristic of some retrogressive    Results from the counterpart strongly coupled hydromechanical
landslides. The broken up soil blocks spread and flow as they    simulation using the 𝒖 – 𝑝𝑤 formulation, instead of the undrained
are deposited on the base, and an unstable back-scarp is exposed    framework, are displayed in Figures 13 and 14 , again showing

International Journal for Numerical and Analytical Methods in Geomechanics, 2026                                                                 15 of 31

### Page 16

FIGURE  12     Retrogressive failure simulation progression over time for the simulation conducted with the undrained framework. Contours show
displacement.

FIGURE  13     Retrogressive failure simulation progression over time for the simulation conducted with the 𝒖 – 𝑝𝑤 formulation and 𝑘 = 1e − 8 m/s.
Contours show accumulated plastic strain.

16 of 31                                                                               International Journal for Numerical and Analytical Methods in Geomechanics, 2026

### Page 17

FIGURE  14     Retrogressive failure simulation progression over time for the simulation conducted with the 𝒖 – 𝑝𝑤 formulation and 𝑘 = 1e − 8 m/s.
Contours show displacement.

FIGURE  15    (A) Evolution of the kinetic energy and (B) horizontal velocities over progressive failure for the undrained and 𝒖 – 𝑝𝑤 simulations.

the accumulated plastic strains and displacements, respectively.     splitting into subblocks, until a total runout distance of 19.5 m
Initially, the slope fails through two competing curved failure      is reached, and a retrogression distance of 20 m is obtained (in
surfaces, which exhibit less curvature than those forming in    part due to a lack of more soil material left to fail in the crater).
the undrained simulation, and are accompanied by an inclined   As is common in spread-type retrogressive landslides [ 94 ], the
v-shaped band pointing towards the slope toe. After 1.5 s of    retrogression distance is larger than the runout distance, and
simulation time, the soil between the first failure surface and      it is noteworthy that despite the structural differences between
the v-shaped band begins to subside, leaving the toe of the    the undrained and the 𝒖 – 𝑝𝑤 simulations, the runout distances
slope relatively untouched, and leading to the development of    are similar.
an additional failure surface upslope (Slide 2). The failing soil
mass resulting from these two slides is gradually reshaped into    In Figure 15 , the evolution of the kinetic energy (Panel A) and
blocks of horsts and grabens. From here on out, the retrogressive    the horizontal velocities, that is, both the maximum and front
landslide becomes fully dominated by the spreading mechanism,     velocities (Panel B) are reported for the undrained simulation
and by 5.5 s, two inclined shear bands are fully traced forming an    in Figure 15 . Three peaks correspond in time to the three major
additional set of graben and horsts after active failure, and the     sliding events that release significant pulses of kinetic energy. At
subsidence of the block is bounded by the two inclined bands    the conclusion of the slide, the kinetic energy of the mobilized
(graben). The slope continues to spread with some of the grabens    mass dissipates considerably, leading to an overall decrease of

International Journal for Numerical and Analytical Methods in Geomechanics, 2026                                                                  17 of 31

### Page 18

FIGURE 16    Comparison of pore pressure ( 𝑝𝑤 ) and excess pore pressure (excess 𝑝𝑤 ) contours for the undrained and 𝒖 – 𝑝𝑤 simulations.

the kinetic energy of the whole slope. In terms of the front and    steps are juxtaposed for both undrained and 𝒖 – 𝑝𝑤 simulations.
maximum velocities, only one main peak is observed after the    In the 𝒖 – 𝑝𝑤 simulation, the horsts undergo extension, even
first slide, followed by a gradual decrease of the velocities. Addi-    though the dilatancy angle is zero, which leads to negative excess
tionally, we note that the front velocity is close to the maximum    pore pressures. This feature is visible as early as 4.5 s into the
velocity of the system, and generally tracks its behavior. As the    simulation after the failed mass resulting from the second slide
third slide comes to a conclusion and sufficient mass stabilizes,    begins to reshape into horsts and grabens. By 14.0 s of simulation
both the kinetic energy and the velocity reduce to near zero.         time, after significantly more spreading, positive excess pore
                                                                 pressure is visible in the grabens where contraction occurs as
In Figure 15 , the kinetic energy evolution indicates three pulses    a result of subsidence, as they depress between the inclined
corresponding to the temporal locations of the three main sliding    bounding slip surfaces. The excess pore pressure is localized
events (the third, being the subsidence of a horst–graben com-    towards the bottom of the model as pore fluid is pressed-up
plex). The magnitude of the kinetic energy is slightly less in the    against the model base. In the undrained simulation, similar
𝒖 – 𝑝𝑤 simulation relative to the undrained simulation for the first    negative pore pressures are obtained in the horsts and, to a
two peaks, although for the third and the rest of the simulation is     lesser extent, positive excess pore pressures are found in the
slightly larger. This fact, and the smaller velocities, both at the    grabens, although both horsts and grabens are less-well developed
slide front and the maximum velocity within the slope as seen in    than in the 𝒖 – 𝑝𝑤 simulation. Also notable of the undrained
Panel B, can be explained with the larger kinetic energy released    simulation is the substantial positive excess pore pressure that
over a shorter time span in the rotational slides, as opposed to the    occurs in the highly compacted toe of the landslide as well as
horst–graben active failure events seen in spreading. In addition,    in other regions experiencing elastic compressive strains. This
the 𝒖 – 𝑝𝑤 formulation naturally dissipates energy via fluid–solid    feature also differs substantially from the run-out zone of the
coupling and excess pore pressure dissipation, leading to lower   𝒖 – 𝑝𝑤 simulation where the dissipation of pore pressures within
kinetic energy over time compared to the undrained simulation,    the flowing debris occurs as the disturbed clay consolidates. We
which lacks this mechanism. In both simulations, despite their    note the dissipation/consolidation of pore pressures can only be
different hydromechanical models, the kinetic energy eventually    modeled in the strongly coupled solid–fluid deformation 𝒖 – 𝑝𝑤
decays, as basal friction and viscosity-like resistance arrests the    simulation. In the majority of the shear bands in the undrained
spreading (or flowing) sensitive clay.                               simulation, however, some amount of dilative elastic strains are
                                                                 observed, as seen in the snapshot at 𝑡 = 4.5 s, leading to large
One of the main advantages of the 𝒖 – 𝑝𝑤 formulation in its    negative excess pore pressures, in many cases far larger than those
application to retrogressive landslides is its ability to capture    observed in the 𝒖 – 𝑝𝑤 simulation.
long-term drainage and pore pressure diffusion, which  is a
prominent feature of spreading failures. In Figure 16 , contours of      It is worth pointing out that no special treatment for negative pore
the pore pressure and of the excess pore pressure at different time    water pressures was implemented, but our numerical experience

18 of 31                                                                               International Journal for Numerical and Analytical Methods in Geomechanics, 2026

### Page 19

FIGURE  17     Retrogressive failure simulation progression over time for the 8-m-high slope simulation conducted with the undrained formulation.
Contours show accumulated plastic strain.

shows that for the typical problems of geotechnical engineering    boundary of the slope in the undrained simulation, and a similar
and the ones simulated here, the negative water pressures are    band also forms in the strongly coupled simulation, although in
relatively low and arising from small volumetric dilation, which    the latter case, a large amount of secondary inclined v-shaped
in practice would not cause significant tensile failure in the    bands form, further splitting the soil mass after the second slide
soil. Nonetheless, a more robust treatment of tensile stresses,    has formed, and leading to a significant zone of lateral spreading.
including improvements at the constitutive level, should be    In fact, after around 3.0 s, the slope can be divided into an area
considered in future works.                                    undergoing spreading, located towards the back boundary, and
                                                       an area that is fully fluidized and flowing towards the slope
                                                                            toe. This contrasts with the undrained simulation, where the
5.2    8-m-High Slope Simulation                            sensitive clay slope flows in its entirety after the collapse of the
                                                                           final back scarp and the triangular soil mass adjacent to the back
We introduce the second slope geometry (8-m-high, steeper, and    boundary. In the 𝒖 – 𝑝𝑤 simulation, the spreading zone does not
taller) to analyze the role of slope geometry on the predominance    form well-developed horst-graben complexes, with only one true
of flow versus spread mechanisms in retrogressive landslides. The    horst visible, as the grabens further disintegrate, breaking up into
material parameters of the sensitive clay in the slope and the other    pieces delimitated by secondary shear bands. In both simulations,
simulation parameters, excluding the geometry, are identical to    the retrogression distance consisted of the entire 16 m of the top
the shallower, 5-m-high, slope shown in Section 5.1 . Figures 17     of the clay deposit, and the runout distances at 41.1 and 40.9 m
and 18 show contours of the accumulated plastic strain and     for the undrained and strongly coupled simulations, respectively,
of the displacement, respectively, for the undrained approach.    are also very close to each other, alluding to the fact that despite
Meanwhile Figures 19 and 20 do the same but for the simulation   some evidence of spreading in the 𝒖 – 𝑝𝑤 case, the overall failure
with the strongly coupled 𝒖 – 𝑝𝑤 formulation.                      behavior is dominated by the flowing of the failed mass.

Both 𝒖 – 𝑝𝑤 and undrained simulations are initially unstable   The steeper, 8-m-high, slope model reaches a substantially greater
and begin to fail via a rotational slip surface (Slide 1) which    kinetic energy peak in both undrained and strongly coupled
is fully developed around 0.8 s of simulation time. In both    cases than the shallower, 5-m-high, slope model, as can be
simulations, the soil that is ejected out of the slide crater breaks    seen by comparing Panel A of Figure 21 with Figure 15 . The
apart and begins sliding, although a large intact block is left    greater kinetic energy resulting from the steeper and taller slope
behind, originating from the top right corner of the slope. In the   makes the retrogressive landslide favor flow behavior as opposed
undrained simulation, a second rotational failure occurs around     to spreading. In addition, the kinetic energy for the steeper
2.0 s of simulation time, whereas in the 𝒖 – 𝑝𝑤 simulation, the    slope in Figure 21A shows only one peak, which is typical of
second failure develops after roughly 1.6 s of elapsed time. An    rapid flow-dominated landslides, as the failure occurs almost
inclined shear band forms a triangular soil mass against the back    nearly at once with most of the gravitational potential energy

International Journal for Numerical and Analytical Methods in Geomechanics, 2026                                                             19 of 31

### Page 20

FIGURE  18     Retrogressive failure simulation progression over time for the 8-m-high slope simulation conducted with the undrained formulation.
Contours show displacement.

FIGURE 19     Retrogressive failure simulation progression over time for the 8-m-high slope simulation conducted with the 𝒖 – 𝑝𝑤 formulation and
𝑘 = 1e − 8 m/s. Contours show accumulated plastic strain.

20 of 31                                                                               International Journal for Numerical and Analytical Methods in Geomechanics, 2026

### Page 21

FIGURE 20     Retrogressive failure simulation progression over time for the 8-m-high slope simulation conducted with the 𝒖 – 𝑝𝑤 formulation and
𝑘 = 1e − 8 m/s. Contours show displacement.

FIGURE  21    (A) Evolution of the kinetic energy and (B) horizontal velocities over progressive failure for the undrained and 𝒖 – 𝑝𝑤 simulations of
the 8-m-high slope.

released into kinetic energy in a single burst. The peak for the    modeling approaches, they share significant similarities from
strongly coupled simulation occurs slightly prior to that of the    an energy-based standpoint. At the same time, in the steeper
undrained simulation, at 1.2 s, versus 2.2 s, and the kinetic energy    model, both the undrained and strongly coupled approaches
drops off more rapidly for the undrained simulation, which    generate failure responses that are clearly dominated by rapid
can be explained by some of the ongoing spreading and soil    flow behavior, despite the presence of some lateral spreading in
block rearrangements (which also cause some later spikes in the    the post-failure configuration of the 𝒖 – 𝑝𝑤 simulation.
maximum but not the front velocities). In spreading dominated
systems, or under a combination of flowslides and then spreading,    Figure 22 presents a comparison of pore pressures and excess pore
as seen in the shallower slope model, sequential block failure,    pressures generated from the undrained and strongly coupled
either through the formation of graben–horst complexes or    analyses for the steeper slope model. Some similar features can
rotational slides, leads to multiple peaks as the soil mass re-    be observed with respect to the shallower model (Figure 16 ) such
accelerates and reconfigures. These observations further suggest    as the generation of negative excess pore pressures forming in
that despite structural differences in the post-failure state of    the horsts and high positive excess pore pressures towards the
the shallower slope between undrained and strongly coupled    bottom of the highly-broken up grabens in the strongly coupled

International Journal for Numerical and Analytical Methods in Geomechanics, 2026                                                              21 of 31

### Page 22

FIGURE  22    Comparison of pore pressure ( 𝑝𝑤 ) and excess pore pressure (excess 𝑝𝑤 ) contours for the undrained simulations of the 8-m-high slope.

model due to contractive behavior. In the undrained model, the     of the models, allowing the upslope regions adjacent to the shear
toe of the slide shows significant compression leading again to    bands to experience negative excess pore water pressures, which
large positive excess pore pressures. At 𝑡 = 3 s, there is a delay in    tend to stabilize the soil in that region, favoring the formation
the build-up of excess pore pressures in the strongly coupled sim-     of horsts, and hence, a progressive spread failure mechanism.
ulation towards the rear of the slope, whereas in the undrained    Conversely, the more generalized generation of positive excess
simulation, large excess pore pressures are spatially distributed    pore water pressures in the undrained formulation is coherent
across the whole model, leading to larger strength loss, and    with the flow-like mode of failure observed in those simulapromoting flow. It is probable that the undrained method tends     tions. This comparison underscores the importance of using
to exaggerate fluidization of the clay by overestimating the excess    strongly coupled formulations in simulations aiming to resolve
pore pressure, leading to more uniform and rapid mobility. The    the nuanced dynamics of retrogressive landslides, especially for
strongly coupled model maintains a more fragmented failure    shallow slopes, or where spreading and drainage are expected
style near the rear of the slope, suggestive of spreading, and     to be central to the failure process. The authors note that an
consistent with the episodic failure and more heterogeneous    exhaustive exploration of the different factors promoting flow
drainage response enabled by the 𝒖 – 𝑝𝑤 formulation. However,    versus spreading behavior is outside the scope of this work and
the relatively steep geometry of the 8-m-high model still favors     is left for future work. Here, we have shown the importance
a dominant flow-type behavior, evident from the lack of fully     of slope geometry and on the hydromechanical model, but the
detached grabens.                                                    constitutive model, boundary conditions, and initial stress state
                                                         𝐾0 value are also known to contribute [ 55, 57–59 ]
In the two simplified slope models considered in this paper,
the undrained formulation, while more computationally efficient (see Supporting Information Section V for a discussion   6    Sainte-Monique Landslide
of computational efficiency), likely tends to over predict pore
pressure buildup and hence slope mobility, often leading to flow-   As a final numerical example, we validate the PR formulation
like behavior irrespective of geometry. Conversely, the 𝒖 – 𝑝𝑤    by recreating the representative, spread-type, retrogressive failure
formulation introduces realistic fluid–solid coupling that can     case-study, which took place at Sainte-Monique, Quebec, Canada,
suppress or delay failure, especially in upslope regions, allowing   on April 21, 1994. Located about 130 km northeast of Montreal,
for complex episodic failure sequences and spreading. It is worth    the landslide occurred along the Siméon-Provencher brook which
emphasizing the good agreement between the internal physics     likely eroded into the  initial sensitive clay slope generating
of the models and the overall failure modes captured. Looking    enough of a decrease in horizontal buttress to propagate a
at Figures 16 and 22 , it is evident that the capability of the 𝒖 –    progressive failure [ 58 ]. Specifically, the soil mass of the slope
𝑝𝑤 formulation to model pore water dissipation generates less    formed distinct horst and graben blocks, typical of spreads, and
positive excess pore water pressure at the base and free surface    the failure propagated in undrained conditions in a sensitive

22 of 31                                                                               International Journal for Numerical and Analytical Methods in Geomechanics, 2026

### Page 23

FIGURE  23    (A) Sainte-Monique landslide simulation setup. (B) Initialized pore pressure 𝑝𝑤 and initialized vertical stress (C) after 𝐾0 = 0 . 5 and
gravity loading.

clay undergoing strain-softening behavior. The geometry of the   TABLE  1    Sainte-Monique landslide simulation simulation paramecomputational model based on a cross section of the initial      ters. The constitutive parameters are based on field measurements from
prefailure slope is shown in Figure 23A . The left side slope is     sensitive clays [ 57, 58, 95 ].
inclined at 24.0 ◦whereas the right-hand side slope has a tilt of
                                                      Parameter                                Value26.0 ◦. The right-hand slope was formed from debris originating
in an earlier landslide in the same location in 1979. A total of                                                                                 Initial interparticle distance, Δ [m]                   0.6
7723 domain SPH particles are used to model the slope with an
initial interparticle distance of Δ = 0 . 6 m, and the base and right     Smoothing length factor, 𝑘ℎ                               1.5
hand slope are treated as boundary particles, as the right side       Artificial viscosity parameters, 𝛼𝜋and 𝛽𝜋          0.1 and 0.0
slope did not fail during the 1994 landslide. In the simulations,                                                     Damping coefficient, 𝜉                              1.0e − 5
the Wendland 𝐶2 kernel and a smoothing length factor of 1.5
                                                              Mixture density, 𝜌[kg/ m3 ]                         1700.0are employed. A strongly coupled hydromechanical analysis with
the 𝒖 – 𝑝𝑤 formulation is performed (PR formulation), and the      Porosity, 𝑛                                            0.2
water table is assumed to be at the slope ground surface. A      Elastic modulus, 𝐸[MPa]                             13.0
modeling simplification, following previous works [ 84, 87 ], is
                                                                      Poisson’s ratio, 𝜈                                     0.33
made in excluding the sandy crust layer found at the top of the
sensitive clay deposit, as it had limited influence on the runout     Bulk modulus of water, 𝐾𝑤 [MPa]                 200.0
and spread behavior, due to its negligible tensile strength, being     Peak internal friction angle, 𝜙[ ◦]                    10.0
simply carried away by the underlying sensitive clay. To model                                                                 Residual internal friction angle, 𝜙[ ◦]                0.0
the sensitive clays, the Drucker–Prager yield criterion is used in
conjunction with the same softening model seen in Equation ( 48 )     Peak cohesion, 𝑐𝑝 [kPa]                             45.0
[ 106 ]. Due to its ability to best describe the behavior of different      Residual cohesion, 𝑐𝑟 [kPa]                             1.0
geomaterials, including sensitive clays, a nonassociative flow                                                                      Permeability, 𝑘[m/s]                               1.0e − 8
rule is also used. The simulation’s numerical, geometric, and
                                                                   Softening coefficient, 𝜂                              2.0, 5.0, 10.0constitutive parameters are summarized in Table 1 . Important to
note is that site investigations found the in situ clay to be slightly
overconsolidated with an earth pressure coefficient of 𝐾0 = 0 . 5
[ 58 ].                                                         a first circular rotational slide after 2.0 s of simulation time. How-
                                                                          ever, the reduction of lateral support causes subsequent failures
In the computational model, stresses are first initialized using    or slides to occur in the form of horst–graben wedges, which
the earth pressure coefficient of 𝐾0 = 0 . 5 , and then subjected to    subside. In total, five major slides occur, with the first four leaving
a gravity loading where the peak material property values and    behind visible signatures in the kinetic energy and maximum
𝜂= 0 are used to stabilize the slope. Next, the resulting effective    horizontal velocities, and the fifth only affecting the front velocity,
stresses and pore pressures are taken for the actual retrogressive    plotted over time for the system in Figure 25 . An additional horst
landslide simulation, which is triggered by setting the desired    also forms at the tip of the slope as the initial rotational failure
softening coefficient 𝜂> 0 and allowing for softening behavior.      is more upslope. The final configuration for the simulation, in
The simulation ended after either 55 s or when the sliding ceased    terms of accumulated plastic strain and displacement for the 𝜂=
and the system reached a stable point in terms of kinetic energy    5 simulation, is visible in the left middle panels of Figure 26 .
and displacement.                                                 After around 18.0 s of simulation time, disturbed clay material
                                                                         at the tip of the slide front begins to override the rightmost
Figure 24 shows the accumulated plastic strains and the displace-     slope, inclined at 26.0 ◦(modeled with boundary particles), as
ments at different snapshots in time for the simulation with 𝜂= 5 .   was observed in the post-failure site analysis [ 58 ]. After 55 s of
The failure process begins with the propagation of a horizontal    simulation time, the post-failure topographic profile of the slope
band along the model base, which then curves upwards forming     is close to that measured in the field for the particular chosen

International Journal for Numerical and Analytical Methods in Geomechanics, 2026                                                        23 of 31

### Page 24

FIGURE 24     (Left) Contours of the accumulated plastic strain 𝜀𝑝𝑎 𝑐 𝑐 and (right) displacement at different snapshots in time for the Sainte-Monique
landslide simulation.

FIGURE  25    (A) Evolution of the kinetic energy and (B) horizontal velocities over progressive failure for the Sainte-Monique landslide simulation.

initial cross section at Sainte-Monique (displayed as a red line),    pressures are observed in areas undergoing contraction, such as
and the simulation runout of 52 m is close to the field-measured    in the grabens, which undergo subsidence. Positive excess pore
runout of 50 m. The final retrogression distance predicted by    pressures are also seen in the remolded clay, which is squeezed
the simulation was 116 m which is slightly larger than the 100    out in-between and below the grabens, and in other zones (e.g.,
m measured in the field, but the sensitivity of the retrogression    near the top surface or the slope toe). Pore pressures dissipate
distance to the softening coefficient 𝜂, as seen in the other panels    as the clay reconsolidates post-failure. A discussion on the state
of Figure 26 , indicates that the roughly selected 𝜂parameter can     of stress during the formation of the slip surfaces and the horst
be calibrated to match the expected retrogression distance in our    and grabens during the Sainte-Monique landslide is provided in
model. Overall, increasing 𝜂has the effect of promoting wedge    Supporting Information Section VI (see Figure S6 ).
formation, sliding events, and greater runout and retrogression
distance. We also see that increasing 𝜂(akin to a more brittle
behavior) has the effect of removing the horst at the slide toe, and    7    Discussion and Conclusions
the initial rotational failure propagates from the toe itself.
                                                              In this paper, we derived and presented two distinct strongly
The right-hand side panels of Figure 26 show the pore pressure    coupled hydromechanical 𝒖 – 𝑝𝑤 formulations for fully saturated
and excess pore pressure contours for the Sainte-Monique simu-     soils using the SPH method: a projection method PPE approach,
lation for different values of 𝜂. When horsts and grabens develop    and an explicit pore PR scheme based on the single-layer twomore clearly, like in the 𝜂= 5 , 10 cases, extension occurs in the    phase model. Unlike in the PPE approach, where both fluid and
horsts leading to negative excess pore pressures and positive pore     solid phases are assumed incompressible, the PR formulation

24 of 31                                                                               International Journal for Numerical and Analytical Methods in Geomechanics, 2026

### Page 25

FIGURE 26    Accumulated plastic strain ( 𝜀𝑝𝑎 𝑐 𝑐 ), displacement, pore pressure ( 𝑝𝑤 ), and excess pore pressure (Excess 𝑝𝑤 ) contours for the SainteMonique landslide simulation, performed with the 𝒖 – 𝑝𝑤 formulation after 55 s, given varying values of the softening coefficient 𝜂. The red line
superimposed over the 𝜀𝑝𝑎 𝑐 𝑐 plots indicates the observed in field ground surface profile after the slope failure.

allows variability in the fluid phase’s bulk modulus, offering more    approach predicted a series of successive rotational slides with
flexibility. The accuracy and stability of the two approaches are   some spreading occurring in the debris flowing out of the scarp.
compared in the context of multiple one-dimensional poroelastic-   On the contrary, in the 8-m-high and steeper slope, both fully
ity problems including one-dimensional (Terzaghi) consolidation    coupled and undrained models predicted flowslide behavior with
and self-weight consolidation. In addition, we explore the param-     significant fluidization of the debris, although some spreading
eter space of the different numerical stabilization terms added   was also present in the strongly coupled simulation. Overall, the
into the formulation, ultimately choosing the explicit PR formu-     proclivity of the strongly coupled 𝒖 – 𝑝𝑤 formulation towards
lation. We show that it is subject to less stringent restrictions    generating spreading in the landslides, points to the importance
pertaining to stability, because of the amplification term that     of incorporating pore fluid pressures in the analysis, as well
arises in the explicit update for the pore pressure when solving    as pore pressure dissipation, and further suggests that penaltythe PPE equation. Furthermore, the challenges arising with the    based undrained modeling approaches may overestimate the
amplification term become markedly more acute for poroelastic    potential for flow-like failures under certain conditions. Lastly,
media with lower permeabilities, which is of interest in the   we demonstrate that the strongly coupled 𝒖 – 𝑝𝑤 PR framework
case of undrained retrogressive landslides which we study in    successfully models the 1994 Sainte-Monique landslide and its
this work. Nevertheless, the PPE formulation may be applicable    deformation patterns without the need for any of the additional
in soils with permeabilities of approximately 𝑘 ≥ 1e-3 m/s, and    assumptions originating in the undrained approach. The SPH
particularly useful when both pore fluid and soil skeleton are    simulation reproduces the field-measured runout distance, as
incompressible, as it enforces the instantaneous, global drained    well as the final topographic profile quite closely, in addition to
response and smooth pressure equilibration expected in this    the expected spreading deformation mechanism.
regime. We next upscale to three dimensions, modeling Cryer’s
problem and lastly, we verify the results of stress paths and pore   Our numerical simulations also capture various important feapressures from undrained triaxial tests using the MCC model     tures, for example, that (1) the major slides or horst-graben
generated from both 𝒖 – 𝑝𝑤 and a penalty-based approach for    (wedge) forming events release kinetic energy bursts; (2) pore
undrained conditions against analytical solutions, noting that the    pressure dissipation and the resulting increase in effective stress
𝒖 – 𝑝𝑤 formulation gave slightly more accurate results.            and shear strength recovery helps arrest the landslide flow; and
                                                                            (3) contractile positive excess pore pressure builds up in the
When applying the proposed 𝒖 – 𝑝𝑤 framework to retrogressive    grabens and in areas compacted by subsidence, whereas extenlandslides, we show that the height and relative steepness of a    sional negative excess pore pressures are observed in the horsts.
slope may contribute to the predominant flowslide versus spread    Simulation of these features is mostly outside the scope of the
mode of failure. Furthermore, our simulations are consistent    undrained framework, but it is worth noting that irrespective of
with field observations indicating that circular slides are often    the pore fluid modeling approach and the differing deformation
required prior to the onset of spreading [ 76 ]. In the 5-m-high   modes produced, both types of simulations tended to have similar
slope, the strongly-coupled simulation predicted spread behavior    runout distances. Despite the inexpensive computational cost of
after the first initial rotational failure, whereas the undrained    the undrained framework relative to the 𝒖 – 𝑝𝑤 (wall-clock time

International Journal for Numerical and Analytical Methods in Geomechanics, 2026                                                          25 of 31

### Page 26

speed-ups of 3–5 times for a fixed CPU-core count), the latter    References
experiences better scalability under parallelization and better      1 . K. Abe, K. Soga, and S. Bandara, “Material Point Method for Coupled
agreement with theoretical speed-ups for lower CPU-core counts    Hydromechanical Problems,” Journal of Geotechnical and Geoenviron-
( < 10 cores), owing to its higher arithmetic intensity. More details    mental Engineering 140, no. 3 (2014): 04013033.
about computational costs and efficiency of the formulations     2 . Y. Alimohammadlou, A. Najafi, and A. Yalcin, “Landslide Process and
can be found in supplemental materials. Given the relative     Impacts: A Proposed Classification Method,” Catena 104 (2013): 219–232.
computational efficiency of both methods, and the advantages     3 . S. Bandara and K. Soga, “Coupling of Soil Deformation and Pore Fluid
of the strongly coupled modeling approach, this work shows the    Flow Using Material Point Method,” Computers and Geotechnics 63 (2015):
viability and potential of a large deformation 𝒖 – 𝑝𝑤 formulation     199–214.
in SPH towards retrogressive landslides and other geotechnical    4 . T. Belytschko, Y. Y. Lu, and L. Gu, “Element-Free Galerkin Methods,”
problems involving large material deformations.                       International Journal for Numerical Methods in Engineering 37, no. 2
                                                                                  (1994): 229–256.
Some limitations of the current work include the fact that the PR     5 . M. A. Biot, “General Theory of Three-Dimensional Consolidation,”
formulation is explicit in time, and the time step is regulated by     Journal of Applied Physics 12, no. 2 (1941): 155–164.
the CFL condition, which in turn depends on the bulk modulus    6 . M. A. Biot, “Theory of Propagation of Elastic Waves in a Fluid-Saturated
of the pore water phase. Here, different integration schemes    Porous Solid. I. Low Frequency Range,” Journal of the Acoustical Society
such as that proposed in [ 55 ] may help resolve this challenge.     of America 28, no. 2 (1956): 168–178.
However, even such formulations may still encounter instabilities     7 . M. A. Biot, “Theory of Propagation of Elastic Waves in a Fluid-Saturated
in the pore pressure field, which are common of coupled solid–    Porous Solid. II. Higher Frequency Range,” Journal of the Acoustical
fluid deformation analyses in the limit of low permeability with     Society of America 28, no. 2 (1956): 179–191.
incompressible pore fluid, and currently, the state-of-the-art is     8 . L. Bjrrum, “The Efective Shear Strength Parameters of Sensitive
limited to smoothing out nonphysical oscillations. Further work     Clays,” in 5th International Conference on Soil Mechanics and Foundation
on mitigating some of the effects of violating the so-called inf-sup     Engineering (International Society for Soil Mechanics and Geotechnical
or Ladyzenskaja–Babuška–Brezzi (LBB) conditions, and porting     Engineering, 1961).
or adapting techniques from FEM or MPM to SPH would be    9 . T. Blanc and M. Pastor, “A Stabilized Fractional Step, Runge–Kutta Tayvaluable, but is outside the scope of this work. Other directions     lor SPH Algorithm for Coupled Problems in Geomechanics,” Computer
for future research include the addition of newly developed    Methods in Applied Mechanics and Engineering 221-222 (2012): 41–53.
absorbing boundary conditions [ 46, 110 ] allowing for dynamic     10 . R. I. Borja and E. Alarcón, “A Mathematical Framework for Finite
loading of saturated soil, which is crucial in earthquakes and     Strain Elastoplastic Consolidation Part 1: Balance Laws, Variational Forsoil liquefaction–related failures. Lastly, the incorporation of     mulation, and Linearization,” Computer Methods in Applied Mechanics
                                                            and Engineering 122, no. 1-2 (1995): 145–171.
more advanced constitutive models which can naturally model
sands and surmount the limitations of the Drucker–Prager or      11 . R. I. Borja, C. Tamagnini, and E. Alarcón, “Elastoplastic Consolidation
                                                                                  at Finite Strain Part 2: Finite Element Implementation and NumericalMCC models, or capture anisotropic effects important in some
                                                                    Examples,” Computer Methods in Applied Mechanics and Engineering 159,
geological media [ 47, 83, 111 ] is currently being considered by
                                                                           no. 1-2 (1998): 103–122.
the authors.
                                                                             12 . R.  I. Borja, “Free Boundary, Fluid Flow, and Seepage Forces in
                                                                          Excavations,” Journal of Geotechnical Engineering  118, no.  1  (1992):
                                                                             125–146.

                                                                              13 . R. I. Borja, “Analysis of Incremental Excavation Based on Critical State
                                                                      Theory,” Journal of Geotechnical Engineering 116, no. 6 (1990): 964–985.

Author Contributions                                                    14 . R. I. Borja and J. A. White, “Continuum Deformation and Stability
                                                                     Analyses of a Steep Hillside Slope Under Rainfall Infiltration,” Acta
Enrique M. Del Castillo: conceptualization, validation, data generation
                                                                       Geotechnica 5 (2010): 1–14.
and analysis, visualization, writing – original draft, review and editing.
Ronaldo I. Borja: writing – review, funding acquisition. Alomir H.     15 . R. I. Borja, J. A. White, X. Liu, and W. Wu, “Factor of Safety in a
Fávero Neto: conceptualization, methodology, validation, supervision,     Partially Saturated Slope Inferred From Hydro-Mechanical Continuum
writing – original draft, review and editing.                               Modeling,” International Journal for Numerical and Analytical Methods
                                                                              in Geomechanics 36, no. 2 (2012): 236–248.

                                                                            16 . R. I. Borja, X. Liu, and J. A. White, “Multiphysics Hillslope ProcessesAcknowledgments
                                                                          Triggering Landslides,” Acta Geotechnica 7 (2012): 261–269.
This material is based upon work supported by the National Science
Foundation under Award Number CMMI-1914780 and Grant Number     17 . R. I. Borja, Plasticity Modeling & Computation (Springer, 2013).
1659397. The first author acknowledges the support by the U.S. National     18 . R.  I. Borja and S. R. Lee, “Cam-Clay  plasticity, Part  I: Implicit
Science Foundation (NSF) Graduate Research Fellowship under Grant     Integration of Elasto-Plastic Constitutive Relations,” Computer Methods
DGE 1656518, as well as by the Stanford Graduate Fellowship, and     in Applied Mechanics and Engineering 78, no. 1 (1990): 49–72.
the Siebel Scholars Award in Energy Science. Some of the parallel
                                                                            19 . H. H. Bui, R. Fukagawa, K. Sako, and J. C. Wells, “Slope Stability
computations for this project were performed on the Stanford University
                                                                        Analysis and Discontinuous Slope Failure Simulation by Elasto-Plastic
Research Computing Center’s Sherlock cluster.
                                                             Smoothed Particle Hydrodynamics (SPH),” Géotechnique 61, no. 7 (2011):
                                                                             565–574.
Data Availability Statement                                        20 . H. H. Bui, R. Fukagawa, K. Sako, and S. Ohno, “Lagrangian Meshfree
All data presented in the work can be made available upon reasonable     Particles Method (SPH) for Large Deformation and Failure Flows of
request to the corresponding author.                                     Geomaterial Using Elastic–Plastic Soil Constitutive Model,” International

26 of 31                                                                               International Journal for Numerical and Analytical Methods in Geomechanics, 2026

### Page 27

Journal for Numerical and Analytical Methods in Geomechanics 32 (2008):     38 . A. H. Favero Neto, “A Continuum Lagrangian Finite Deformation
1537–1570.                                                          Computational Framework for Modeling Granular Flows,” (PhD thesis,
                                                                         Stanford University, 2020).
21 . H. H. Bui and G. D. Nguyen, “A Coupled Fluid-Solid SPH Approach
to Modelling Flow Through Deformable Porous Media,” International     39 . A. H. Fávero Neto and R.  I. Borja, “Continuum Hydrodynamics
Journal of Solids and Structures 125 (2017): 244–264.                           of Dry Granular Flows Employing Multiplicative Elastoplasticity,” Acta
                                                                       Geotechnica 13 (2018): 1027–1040.
22 . H. H. Bui and G. D. Nguyen, “Smoothed Particle Hydrodynamics
(SPH) and Its Applications in Geomechanics: From Solid Fracture to    40 . A. H. Fávero Neto, A. Askarinejad, S. M. Springman, and R.  I.
Granular Behaviour and Multiphase Flows in Porous Media,” Computers     Borja, “Simulation of Debris Flow on an Instrumented Test Slope Using
and Geotechnics 138 (2021): 104315.                                   an Updated Lagrangian Particle Method,” Acta Geotechnica 15 (2020):
                                                                            2757–2777.
23 . M. A. Carson, “On the Retrogression of Landslides in Sensitive
Muddy Sediments,” Canadian Geotechnical Journal 14, no. 4 (1977): 582–     41 . R. Fatehi and M. Manzari, “Error Estimation in Smoothed Particle
602.                                                            Hydrodynamics and a New Scheme for Second Derivatives,” Computers
                                             & Mathematics with Applications 61, no. 2 (2011): 482–498.
24 . X. Chen, S. Ren, X. Guo, Y. Wang, F. Liu, H. Nguyen, and R. L.
Sousa, “Comparative Modelling of Retrogressive Landslide Runout: 2D    42 . A. H. Favero Neto, G. R. A. Oliveira, L. L. Rasmussen, and E. Rógenes,
and 3D Random Large-Deformation Analyses Using Coupled Eulerian-    “Large Deformation and Critical State Analysis of the Fundão Tailings
Lagrangian Method,” International Journal of Mining Science and Tech-    Dam,” in Proceedings of Geo-Extreme 2025 (ASCE, 2025).
nology 35, no. 11 (2025): 2011–2030.
                                                                   43 . A. H. Favero Neto, P. D. G. Orlando, and R. Rocha, “The Impacts
25 . X. Chen, Y. Leung, H. Mori, S. Uchida, and K. Takumi, “Single-     of Aging Infrastructure and Evolving Load Conditions: Case Study of
Layer Soil-Water Coupled SPH Method and Its Application to Sinkhole    an Earth Retaining Wall Failure,” in Proceedings of the 9th Forensic
Simulation,” Acta Geotechnica 19 (2024): 991–1018.                          Engineering Conference (ASCE, 2022).

26 . D. Chen, W. Huang, and C. Liang, “A Three-Dimensional Smoothed    44 . R. Gingold and J. Monaghan, “Smoothed Particle Hydrodynamics:
Particle Hydrodynamics Analysis of Multiple Retrogressive Landslides in    Theory and Application to Nonspherical Stars,” Monthly Notices of the
Sensitive Soil,” Computers and Geotechnics 170 (2024): 106284.              Royal Astronomical Society 181 (1977): 375–389.

27 . A. D. Chow, B. D. Rogers, S. J. Lind, and P. K. Stansby, “Incompressible    45 . K. K. Hamouche, S. Leroueil, M. Roy, and A.  J. Lutenegger, “In
SPH (ISPH) With Fast Poisson Solver on a GPU,” Computer Physics     Situ Evaluation of K0 in Eastern Canada Clays,” Canadian Geotechnical
Communications 226 (2018): 81–103.                                       Journal 32, no. 4 (1995): 677–688.

28 . M. J. Crozier, “Deciphering the Effect of Climate Change on Landslide    46 . T. N. Hoang, H. H. Bui, T. T. Nguyen, T. V. Nguyen, and G. D. Nguyen,
Activity: A Review,” Geomorphology 124, no. 3-4 (2010): 260–267.           “Development of Free-Field and Compliant Base SPH Boundary Condi-
                                                                              tions for Large Deformation Seismic Response Analysis of Geomechanics
29 . C. W. Cryer, “A Comparison of the Three-Dimensional Consolidation
                                                                      Problems,” Computer Methods in Applied Mechanics and Engineering 432,Theories of Biot and Terzaghi,” Quarterly Journal of Mechanics and
                                                                           no. A (2024): 117370.Applied Mathematics 16, no. 4 (1963): 401–412.
                                                                      47 . S. C. Y. Ip and R. I. Borja, “Hydromechanical Coupling in Unsaturated
30 . E. M. del Castillo, A. H. Fávero Neto, and R.  I. Borja, “Fault
                                                                     Clayey Rocks With Double Porosity Based on a Multiscale HomogenizaPropagation and Surface Rupture in Geologic Materials With a Meshfree
                                                                             tion Procedure,” Computers and Geotechnics 171 (2024): 106380.Continuum Method,” Acta Geotechnica 16 (2021): 2463–2486.
                                                                   48 . Y.-F. Jin and Z.-Y. Yin, “Two-Phase PFEM With Stable Nodal Inte-
31 . E. M. del Castillo, A. H. Fávero Neto, and R. I. Borja, “A Continuum
                                                                            gration for Large Deformation Hydromechanical Coupled Geotechnical
Meshfree Method for Sandbox-Style Numerical Modeling: Application to
                                                                      Problems,” Computer Methods in Applied Mechanics and Engineering 392Accretionary and Doubly Vergent Wedges,” Journal of Structural Geology
                                                                                (2022): 114660.
153 (2021): 104466.
                                                                   49 . Y. Kim,  T. Carvalhaes, A. Helmrich,  et  al., “Leveraging SETS32 . E. M. del Castillo, A. H. Fávero Neto, and R. I. Borja, “Modeling
                                                                            Resilience Capabilities for Safe-to-Fail Infrastructure Under ClimateFault Rupture Through Layered Geomaterials with SPH,” in Multiscale
                                                                  Change,” Current Opinion in Environmental Sustainability 54 (2022):Processes of Instability, Deformation and Fracturing in Geomaterials ,
                                                                                  101153.Springer Series in Geomechanics and Geoengineering, IWBDG 2022, ed.
A. Dyskin and E. Pasternak (Springer, 2023).                             50 . M. G. Korzani, S. A. Galindo-Torres, A. Scheuermann, and D.  J.
                                                                         Williams, “SPH Approach for Simulating Hydro-Mechanical Processes
33 . E. M. del Castillo, A. H. Fávero Neto, J. Geng, and R. I. Borja, “An
                                                              With Large Deformations and Variable Permeabilities,” Acta Geotechnica
SPH Framework for Drained and Undrained Loading Over Large Defor-
                                                                              13 (2018): 303–316.mations,” International Journal for Numerical and Analytical Methods in
Geomechanics 48, no. 12 (2024): 3227–3257.                                    51 . S. Koshizuka and Y. Oka, “Moving-Particle Semi-Implicit Method for
                                                                    Fragmentation of Incompressible Fluid,” Nuclear Science and Engineering
34 . E. M. del Castillo,  J. Geng, and R.  I. Borja, “A Nonlocal Kernel-
                                                                                   123, no. 3 (1996): 421–434.
Based Continuum Damage Model for Compaction Band Formation in
Porous Sedimentary Rock,” Computational Mechanics 75 (2025): 1745–     52 . E.-S. Lee, C. Moulinec, R. Xu, D. Violeau, D. Laurence, and P. Stansby,
1768.                                                             “Comparisons of weakly Compressible and Truly Incompressible Algo-
                                                                      rithms for the SPH Mesh Free Particle Method,” Journal of Computational35 . E. M. del Castillo, A. H. Fávero Neto, and R. I. Borja, “Fault Rupture
                                                                             Physics 227, no. 18 (2008): 8417–8436.
Propagation Through Stratified Sand-Clay Deposits and Engineered Earth
Structures: A Meshfree and Critical-State Modeling Approach,” Acta     53 . Y. Lian, H. H. Bui, G. D. Nguyen, H. Tran, and A. Haque, “A General
Geotechnica 19 (2024): 7767–7798.                               SPH Framework for Transient Seepage Flows Through Unsaturated
                                                                    Porous Media Considering Anisotropic Diffusion,” Computer Methods in
36 . R. Dey,  B. Hawlader, R.  Phillips, and K. Soga, “Large Defor-
                                                                       Applied Mechanics and Engineering 387 (2021): 114169.
mation Finite-Element Modelling of Progressive Failure Leading to
Spread in Sensitive Clay Slopes,” Géotechnique 65, no. 8 (2015): 657–    54 . Y. Lian, H. H. Bui, G. D. Nguyen, S. Zhao, and A. Haque, “A
668.                                                                 Computationally Efficient SPH Framework for Unsaturated Soils and Its
                                                                        Application to Predict the Entire Rainfall-Induced Slope Failure Process,”
37 . Q. Duan and T. Belytschko, “Gradient and Dilatational Stabilizations
                                                                      Géotechnique 74 (2022): 787–805.Dilatational Stabilizations for Stress-Point Integration in the ElementFree Galerkin Method,” International Journal for Numerical Methods in     55 . Y. Lian, H. H. Bui, G. D. Nguyen, and A. Haque, “An Effective and
Engineering 77, no. 6 (2009): 776–798.                                          Stabilised ( 𝑢 − 𝑝𝑙 ) SPH Framework for Large Deformation and Failure

International Journal for Numerical and Analytical Methods in Geomechanics, 2026                                                          27 of 31

### Page 28

Analysis of Saturated Porous Media,” Computer Methods in Applied     74 . P. Navas, M. M. Stickle, A. Yagüe, D. Manzanal, M. Molinos, and M.
Mechanics and Engineering 308 (2023): 115967.                                 Pastor, “Stabilized Explicit 𝒖 − 𝑝𝑤 Solution in Soil Dynamic Problems
                                                                Near the Undrained-Incompressible Limit,” Acta Geotechnica 18 (2023):
56 . W. K. Liu, S. Jun, and Y. F. Zhang, “Reproducing Kernel Particle
                                                                               1199–1213.Methods,” International Journal for Numerical Methods in Fluids 20, no.
8–9 (1995): 1081–1106.                                                      75 . M. Neuner, A. Dummer, S. Abrari Vajari, et al., “A B-Spline Based
                                                                   Gradient-Enhanced Micropolar  Implicit Material Point Method  for
57 . A. Locat, S. Leroueil, S. Bernander, D. Demers, H. P. Jostad, and
                                                                    Large Localized Inelastic Deformations,” Computer Methods in Applied
L. Ouehb, “Progressive Failures in Eastern Canadian and Scandinavian
                                                                   Mechanics and Engineering 431 (2024): 117291.Sensitive Clays,” Canadian Geotechnical Journal 48 (2011): 1696–1712.
                                                                        76 . S. Odenstad, “The Landslide at Sköttorp on the Lidan River, February
58 . A. Locat, S. Leroueil, A. Fortin, D. Demers, and H. P. Jostad, “The
                                                                                           2, 1946,” Royal Swedish Institute Proceedings 4 (1951): 1–38.
1994 Landslide at Sainte-Monique, Quebec: Geotechnical Investigation
and Application of Progressive Failure Analysis,” Canadian Geotechnical     77 . E. Oñate, S. R. Idelsohn, F. D. Pin, and R. Aubry, “The Particle Finite
Journal 52 (2015): 490–504.                                          Element Method. An Overview,” International Journal of Computational
                                                                 Methods 1, no. 2 (2004): 267–307.
59 . A.  Locat,  “Canadian  Geotechnical  Colloquium:  Understanding
Spreads in Canadian Sensitive Clays,” Canadian Geotechnical Journal 62     78 . M. Pastor, B. Haddad, G. Sorbino, S. Cuomo, and V. Drempetic, “A
(2025): 1–14.                                                             Depth-Integraded, Coupled SPH Model for Flow-Like Landslides and
                                                                        Related Phenomena,” International Journal for Numerical and Analytical
60 . L. B. Lucy, “A Numerical Approach to the Testing of the Fission
                                                                 Methods in Geomechanics 33 (2009): 143–172.Hypothesis,” Astronomical Journal 82, no. 12 (1977): 1013–1024.
                                                                      79 . M. Pastor, A. Yague, M. M. Stickle, D. Manzanal, and  P. Mira,61 . J. Mandel, “Consolidation Des Sols (Étude Mathématique),” Géotech-
                                                        “A Two-Phase SPH Model for Debris Flow Propagation,” Internationalnique 3, no. 7 (1953): 287–299.
                                                                        Journal for Numerical and Analytical Methods in Geomechanics 42 (2017):
62 . S. Menon and X. Song, “Computational Coupled Large-Deformation     418–448.
Periporomechanics for Dynamic Failure and Fracturing in Variably Satu-
                                                                  80 . Z. Qiao, W. Shen, P. Xin, T. Li, P. Li, and H. Jiao, “Simulation ofrated Porous Media,” International Journal for Numerical and Analytical
                                                                        the Failure and Run-Out Processes of Rotational–Translational LoessMethods in Geomechanics 124 (2023): 80–118.
                                                                        Landslides Using an SPH Model Considering Strain Softening,” Acta
63 . S. Menon and X. Song, “Computational Multiphase Periporomechan-     Geotechnica 19 (2024): 7799–7820.
ics for Unguided Cracking in Unsaturated Porous Media,” International
                                                                             81 . X. Qi, Q. Xu, and F. Liu, “Analysis of Retrogressive Loess FlowslidesJournal for Numerical and Analytical Methods in Geomechanics 123 (2023):
                                                                            in Heifangtai, China,” Engineering Geology 236 (2018): 119–128, https://doi.
2837–2871.
                                                                             org/10.1016/j.enggeo.2017.08.028 .
64 . S. Mohajerani, G. Wang, Y. Zhao, and F. Jin, “A Novel Peridynamics
                                                                       82 . P. Ramachandran, A. Bhosale, and K. Puri, “PySPH: A Python-BasedModelling of Cemented Granular Materials,” Acta Geotechnica 18 (2023):
                                                            Framework for Smoothed Particle Hydrodynamics,” ACM Transactions2529–2548.
                                                              on Mathematical Software (TOMS) 47, no. 4 (2021): 1–38.
65 . L. Monforte, M. Arroyo, J. M. Carbonell, and A. Gens, “Numerical
                                                                       83 . E. Rógenes,  I.  T. Paes, B. G. Delgado,  et  al., “Assessing  Static
Simulation of Undrained Insertion Problems in Goetechnical Engineer-
                                                                         Liquefaction  Triggers  in  Tailings Dams  Using  the  Critical  Stateing With the Particle Finite Element Method (PFEM),” Computers and
                                                                            Constitutive Models CASM and NorSand,” International Journal forGeotechnics 82 (2017): 144–156.
                                                                   Numerical and Analytical Methods in Geomechanics 49, no. 4 (2025):
66 . S. Moriguchi, R. I. Borja, A. Yashima, and K. Sawada, “Estimating the     1092–1112.
Impact Force Generated by Granular Flow on a Rigid Obstruction,” Acta
                                                                   84 . Z. Shan, W. Zhang, D. Wang, and L. Wang, “Numerical Inves-Geotechnica 4 (2009): 57–71.
                                                                                 tigations of Retrogressive Failure in Sensitive Clays: Revisiting 1994
67 . D. S. Morikawa and M. Asai, “Soil-Water Strong Coupled ISPH Based    Sainte-Monique Slide, Quebec,” Landslides 18 (2021): 1327–1336.
on u-w-p Formulation for Large Deformation Problems,” Computers and
                                                                         85 . T. Siriaksorn, S. W. Chi, C. Foster, and A. Mahdavi, “u-p Semi-Geotechnics 142, no. 104570 (2022): 104570.
                                                                    Lagrangian Reproducing Kernel Formulation for Landslide Modeling,”
68 . D. S. Morikawa and M. Asai, “A Phase-Change Approach to Landslide     International Journal for Numerical and Analytical Methods in GeomeSimulations: Coupling Finite Strain Elastoplastic TLSPH With Non-     chanics 2018 42, no. 2 (2018): 209–376.
Newtonian IISPH,” Computers and Geotechnics 148 (2022): 104815.
                                                                     86 . A. Skillen, S. Lind, P. K. Stansby, and B. D. Rogers, “Incompress-
69 . D. S. Morikawa and M. Asai, “Coupling Total Lagrangian SPH–EISPH     ible Smoothed Particle Hydrodynamics (SPH) With Reduced Temporal
for Fluid–Structure Interaction With Large Deformed Hyperelastic Solid    Noise and Generalised Fickian Smoothing Applied to Body–Water Slam
Bodies,” Computer Methods in Applied Mechanics and Engineering 381    and Efficient Wave–Body Interaction,” Computer Methods in Applied
(2021): 113832.                                                       Mechanics and Engineering 265 (2013): 163–173.
70 . J. P. Morris, P. J. Fox, and Y. Zhu, “Modeling Low Reynolds Number     87 . X. Song, H. Pashazad, and A.  Whittle, “Computational LargeIncompressible Flows Using SPH,” Journal of Computational Physics 136,     Deformation-Plasticity Periporomechanics for Localization and Instabilno. 1 (1997): 214–226.                                                                   ity in Deformable Porous Media,” International Journal for Numerical and
71 . B. Mullet, P. Segall, and A. H. Fávero Neto, “Numerical Modeling     Analytical Methods in Geomechanics 49 (2025): 1278–1298.
of Caldera Formation Using Smoothed Particle Hydrodynamics (SPH),”     88 . D. Sulsky, S.-J. Zhou, and H. L. Schreyer, “Application of a Particle-inGeophysical Journal International 234, no. 2 (2023): 887–902.                  Cell Method to Solid Mechanics,” Computer Physics Communications 87,
72 . P. Navas, M. Pastor, A. Yagüe, M. M. Stickle, D. Manzanal, and M.     no. 1-2 (1995): 236–252.
Molinos, “Fluid Stabilization of the 𝒖 − 𝒘 Biot’s Formulation at Large    89 . W. Sun and J. Fish, “Coupling of Non-Ordinary State-Based PeridyStrain,” International Journal for Numerical and Analytical Methods in    namics and Finite Element Method for Fracture Propagation in Saturated
Geomechanics 45 (2021): 336–352.                                       Porous Media,” International Journal  for Numerical and Analytical
73 . P. Navas, M. Molinos, M. M. Stickle, D. Manzanal, A. Yagüe, and    Methods in Geomechanics 45 (2021): 1260–1281.
M. Pastor, “Explicit Meshfree 𝒖 − 𝑝𝑤 Solution of the Dynamic Biot    90 . H. Teufelsbauer, Y. Wang, S. P. Pudasaini, R. I. Borja, and W. Wu,
Formulation at Large Strain,” Computational Particle Mechanics 9 (2022):   “DEM Simulation of Impact Force Exerted by Granular Flow on Rigid
655–671.                                                                      Structures,” Acta Geotechnica 6 (2011): 119–133.

28 of 31                                                                               International Journal for Numerical and Analytical Methods in Geomechanics, 2026

### Page 29

91 . Q.-A. Tran and W. So ł owski, “Generalized Interpolation Material Point     110 . C. Yao, G. Fourtakas, B. D. Rogers, and D. Lombardi, “2-D SPH
Method Modelling of Large Deformation Problems Including Strain-Rate    Modelling of Poroelasticity: 𝒖 − 𝒘 − 𝑝and 𝒖 − 𝑝Formulations With
Effects – Application to Penetration and Progressive Failure Problems,”    Absorbing Boundary Conditions and Volumetric Locking Treatments,”
Computers and Geotechnics 106 (2018): 249–265.                          Computers and Geotechnics 179 (2025): 107016.

92 . Q.-A. Tran, A. Rogstad,  I. Depina, et al., “3D Large Deformation      111 . Y. Zhao and R. I. Borja, “A Double-Yield-Surface Plasticity Theory for
Modeling of the 2020 Gjerdrum Quick Clay Landslide,” Canadian     Transversely Isotropic Rocks,” Acta Geotechnica 17 (2022): 5201–5221.
Geotechnical Journal 62 (2024): 1–21, https://doi.org/10.1139/cgj-2024-
                                                                                 112 . D. Z. Zhang, X. Ma, and P. T. Giguere, “Material Point Method
0044 .
                                                             Enhanced by Modified Gradient of Shape Function Author Links Open
93 . Z. A. Urmi, A. Saeidi, R. V.  P. Chavali, and A. Yerro, “Failure    Overlay Panel,” Journal of Computational Physics 231, no. 16 (2011):
Mechanism, Existing Constitutive Models and Numerical Modeling of     6379–6398.
Landslides in Sensitive Clay: A Review,” Geoenvironmental Disasters 10
                                                                                 113 . X. Zhang, D. Sheng, S. W. Sloan, and J. Bleyer, “Lagrangian Modelling
(2023): 14.                                                                                of Large Deformation Induced by Progressive Failure of Sensitive Clays
94 . Z. A. Urmi, A. Saeidi, A. Yerro, and R. V. P. Chavali, “Prediction of Post-    With Elastoviscoplasticity,” International Journal for Numerical Methods
Peak Stress-Strain Behavior for Sensitive Clays,” Engineering Geology 323     in Engineering 112 (2017): 963–989.
(2023): 107221.
                                                                                114 . S. Zhao, H. H. Bui, V. Lemiale, G. D. Nguyen, and F. Darve, “A Generic
95 . Z. A. Urmi, A. Yerro, A. Saeidi, and R. V. P. Chavali, “Prediction of    Approach to Modelling Flexible Confined Boundary Conditions in SPH
Retrogressive Landslide in Sensitive Clays by Incorporating a Novel Strain    and Its Application,” International Journal for Numerical and Analytical
Softening Law Into the Material Point Method,” Engineering Geology 340    Methods in Geomechanics 43, no. 5 (2019): 1005–1031.
(2024): 107669.
                                                                                   115 . Y. Zhao,  J. Choo, Y. Jiang, and L. Li, “Coupled Material Point
96 . D. J. Varnes, “Slope-Stability Problems of the Circum-Pacific Region    and Level Set Methods for Simulating Soils Interacting With Rigid
as Related to Mineral and Energy Resources,” in Energy resources of the     Objects With Complex Geometry,” Computers and Geotechnics 163 (2023):
Pacific Region. American Association of Petroleum Geologist Studies in     105708.
Geology , ed. M. T. Halbouty, vol. 12 (1981), 489–505.                                                                                116 . O. C. Zienkiewicz, A. H. C. Chan, M. Pastor, B. A. Schrefler, and T.
97 . A. Verrujit, An Introduction to Soil Dynamics (Springer, 2010).           Shiomi, Computational Geomechanics (John Wiley & Sons, 1999).

98 . B. Wang, P. J. Vardon, and M. A. Hicks, “Investigation of Retrogressive
and Progressive Slope Failure Mechanisms Using the Material Point
Method,” Computers and Geotechnics 78 (2016): 88–98.                   Supporting Information
99 . C. Wang, B. Hawlader, D. Perret, K. Soga, and J. Chen, “Modeling     Additional supporting information can be found online in the Supporting
of Initial Stresses and Seepage for Large Deformation Finite-Element    Information section.
Simulationof Sensitive Clay Landslides,” Journal of Geotechnical and    Supporting file
Geoenvironmental Engineering 147, no. 11 (2021): 04021111.

100 . C. Wang, B. Hawlader, D. Perret, and K. Soga, “Effects of Geometry
and Soil Properties on Type and Retrogression of Landslides in Sensitive    Appendix A: Coupled Formulation Derivation Details
Clays,” Géotechnique 72, no. 4 (2022): 322–336.
101 . L. Wang, X. Zhang, Q. Lei, S. Panayides, and S. Tinti, “A Three-    To derive the equations, we rely on the following set of assumptions:
Dimensional Particle Finite Element Model for Simulating Soil Flow With
Elastoplasticity,” Acta Geotechnica 17 (2022): 5639–5653.                                1. The soil is fully saturated, that is, the void fraction of the material is
                                                                                                full of water.102 . D. M. Wood, Soil Behavior and Critical State Soil Mechanics (Cambridge University Press, 1990).                                                         2. The water is inviscid.

103 . M. Xie, P. Navas, and S. López-Querol, “A Stabilised Semi-Implicit                                                                                             3.  There is no mass or heat exchange between solid and water phases,
Double-Point Material Point Method for Soil–Water Coupled Problems,”                                                                 and processes are isothermic.
Computational Particle Mechanics 12 (2025): 3389–3419.
                                                                                        4.  Terzaghi’s effective stress theory is valid.
104 . J. Yu, W. Liang, and J. Zhao, “Enhancing Dynamic Modeling of
Porous Media With Compressible Fluid: A THM Material Point Method
With Improved Fractional Step Formulation,” Computer Methods in   We now consider a two-phase soil consisting of solid matrix (subscript
Applied Mechanics and Engineering 444 (2025): 118100.                          𝑠) and water (subscript 𝑤) filling the void space between the solid
                                                                      matrix  ( 𝑉𝑣 ). We define the intrinsic mass densities as the mass of
105 . W.-H. Yuan, M. Liu, X.-W. Zhang, H.-L. Wang, W. Zhang, and W. Wu,                                                                        the phase divided by the volume of the phase. Hence, 𝜌𝑠 and 𝜌𝑤
“Stabilized Smoothed Particle Finite Element Method for Coupled Large                                                                           are the corresponding intrinsic mass densities of the solids and water,
Deformation Problems in Geotechnics,” Acta Geotechnica 18 (2023): 1215–                                                      𝑉𝑣
                                                                                  respectively. Moreover, we define porosity 𝑛 =      , where 𝑉is the total
1231.                                                                                                  𝑉
                                                              volume of the mixture. Porosity is also related to the void ratio of the soil
106 . F. Zabala and E. E. Alonso, “Progressive Failure of Aznalcóllar Dam    through the relationship 𝑛 = 𝑒∕(1 + 𝑒) .
Using the Material Point Method,” Géotechnique 61, no. 9 (2011): 795–808.

107 . X. Zhang,  S. W. Sloan, and E. Oñate, “Dynamic Modelling of    Based on the previous definitions, the partial densities (ratio of phase
Retrogressive Landslides With Emphasis on the Role of Clay Sensi-    mass and total volume) of the solid and water phases are defined,
tivity,” International Journal for Numerical and Analytical Methods in     respectively, as
Geomechanics 42 (2018): 1806–1822.
                                                                                                             𝜌𝑠 = 𝑛𝑠 𝜌𝑠                          (A1)108 . X. Zhang, L. Wang, K. Krabbenhoft, and S. Tini, “Dynamic Modelling of Retrogressive Landslides With Emphasis on the Role of Clay
Sensitivity,” Landeslides 17 (2020): 1117–1127.                                                 𝜌𝑤 = 𝑛𝜌𝑤 ,                        (A2)
109 . E. Yang, H. H. Bui, H. D. Sterck, and G. D. Nguyen, “A Scalable
Parallel Computing SPH Framework for Predictions of Geophysical    with 𝑛𝑠 = 1 − 𝑛, such that 𝜌𝑠 + 𝜌𝑤 = 𝜌, where 𝜌is the bulk mass density
Granular Flows,” Computers and Geotechnics 121 (2020): 103474.              of the mixture.

International Journal for Numerical and Analytical Methods in Geomechanics, 2026                                                       29 of 31

### Page 30

In terms of stress, we can also define partial stresses acting on the solid    Balance of Mass
and water phases as 𝝈𝑠 = 𝑛𝑠 𝝈𝑠 and 𝝈𝑤 = 𝑛𝝈𝑤 , where 𝝈𝑠 and 𝝈𝑤 are the
intrinsic total stresses in the solid and water phases, respectively. It is    In general, for a given phase 𝛼in mixture theory, the balance of mass (in
worth pointing out a few relationships pertaining to stress in the mixture     Eulerian form) is given by the following:

             𝝈= 𝝈𝑠 + 𝝈𝑤 = 𝝈′ + 𝝈𝑤                  (A3)             𝑑𝛼𝑀𝛼 = 𝑑𝛼   𝜌𝛼𝑑 𝑉 = 𝑑𝛼    𝜌𝛼𝐽𝑑 𝑉0
                                                                                     𝑑𝑡     𝑑𝑡 ∫𝑉       𝑑 𝑡 ∫𝑉0
                      𝝈𝑤 = 𝑝𝑤 𝟏                        (A4)                  ( 𝑑𝛼𝜌𝛼        )
                                                            =            𝐽 + 𝜌𝛼∇ ⋅𝒗𝛼𝐽 𝑑𝑉0 = 0 ,       (A14)
                                                                                          ∫𝑉0    𝑑𝑡
                     𝝈𝑤 = 𝑛𝑝𝑤 𝟏                        (A5)
                                                              where 𝐽is the deformation gradient tensor Jacobian, which maps the
                         𝝈𝑠 = 𝝈′ + 𝑛𝑠 𝑝𝑤 𝟏                     (A6)     current configuration of a deformed body (with volume, 𝑉) to  its
                                                               undeformed shape (reference volume, 𝑉0 ), and “∇ ⋅() ” is the divergence
                                                                               operator. Hence,
In the previous equations, 𝟏 is the second order identity tensor, and 𝝈′ is
                                                           (          )
the partial effective stress acting on the solid phase, which is determined              𝑑𝛼𝑀𝛼       𝑑𝛼𝜌𝛼
from any constitutive model selected to represent the behavior of the                     𝑑𝑡  = ∫𝑉    𝑑𝑡 + 𝜌𝛼∇ ⋅𝒗𝛼 𝑑𝑉 = 0 .         (A15)
solid skeleton.
                                                            Making use of the fundamental theorem of calculus and the fact that the
                                                                      balance of mass should hold for any arbitrary differential volume element,
Material Time Derivatives                                             the general equation for the balance of mass for a given phase 𝛼is finally

                                                                                   𝑑𝛼𝜌𝛼
We define a material time derivative following the motion of phase 𝛼( 𝛼=                      + 𝜌𝛼∇ ⋅𝒗𝛼= 0 .                  (A16)                                                                                                𝑑𝑡
𝑠or 𝑤) as follows:
                                                                    For the present case where we have two phases, solid and water, the
                       𝑑𝛼()    𝜕()                                      balance of mass for the solid phase, written in terms of volume fractions
                   =   + 𝒗𝛼⋅∇() ,                   (A7)
                        𝑑𝑡     𝜕𝑡                                 and intrinsic mass densities, is given by the following:

where 𝒗𝛼is the phase velocity, and “∇() ” is the gradient operator. Hence,      𝑑( 𝑛𝑠 𝜌𝑠 )                             1 𝑑𝜌𝑠                                                      + (𝑛𝑠 𝜌𝑠 )∇ ⋅𝒗𝑠 = 0 , →𝑑𝑛𝑠 + 𝑛𝑠     + 𝑛𝑠 ∇ ⋅𝒗𝑠 = 0 . (A17)
for the solid and water phases, the material time derivatives following         𝑑𝑡                          𝑑𝑡       𝜌𝑠 𝑑𝑡
each phase’s own motion are as follows:
                                                                                  Similarly, for the water phase, we have the following:
                         𝑑𝑠 ()    𝜕()
                   =                       + 𝒗𝑠 ⋅∇() ,                   (A8)        𝑑𝜌𝑤                                                                                  𝑑( 𝑛𝜌𝑤 )                        𝑑𝑡                                 𝜕𝑡                                                      =                                                             + ∇ ⋅𝒘 + (𝑛𝜌𝑤 ) ∇ ⋅𝒗𝑠
                                                                             𝑑𝑡       𝑑𝑡
                   𝑑𝑤 ()    𝜕()
                   =                       + 𝒗𝑤 ⋅∇() .                  (A9)
                        𝑑𝑡                                 𝜕𝑡                                                      = 0 , →𝑑𝑛 + 𝑛1 𝑑𝜌𝑤 + 1 ∇ ⋅𝒘 + 𝑛∇ ⋅𝒗𝑠 = 0 .     (A18)
                                                                                          𝑑𝑡    𝜌𝑤  𝑑𝑡   𝜌𝑤
If we subtract the previous equations, we obtain the relationship between
                                                              where 𝒘 = 𝜌𝑤 ( 𝒗𝑤 − 𝒗𝑠 ) = 𝜌𝑤 𝒗 is the Eulerian relative fluid velocity.material time derivatives following the water and solid phases:

                𝑑𝑤 ()    𝑑𝑠 ()                                  Now, assuming that solid phase’s and pore-water’s mass densities changes
                =                     + ( 𝒗𝑤 − 𝒗𝑠 ) ⋅∇() .              (A10)       (i.e., volumetric deformations) are due solely to the intrinsic pore-water                    𝑑𝑡                            𝑑𝑡
                                                                             pressure, 𝑝𝑤 , and that these changes arise from an elastic response [ 116 ],
For small relative velocities ( 𝒗𝑤 − 𝒗𝑠 ), we can use a Lagrangian frame-   we have
work and perform any analyses with respect to the solid motion only.
                                                                                    1 𝑑𝜌𝛼               𝑑 𝑝𝑤                                                                 = − ∇ ⋅𝒗𝛼= −1           ,              (A19)
                                                                                    𝜌𝛼  𝑑𝑡             𝐾𝛼  𝑑𝑡
The difference between fluid and solid velocities per unit area of the
mixture is also known as Darcy’s velocity, defined as follows:              where 𝐾𝛼is the intrinsic bulk modulus of phase 𝛼.

                     𝒗 = 𝑛( 𝒗𝑤 − 𝒗𝑠 ) .                       (A11)     Therefore, we can rewrite Equation ( A17 ) using Equation ( A19 ), which
                                                                              gives the following:
Darcy’s velocity is related to the hydraulic conductivity tensor of the soil
mixture, 𝒌 , and the head loss ℎalong the fluid through Darcy’s law                           𝑑𝑛𝑠      1 𝑑 𝑝𝑤
                                                               − 𝑛𝑠      + 𝑛𝑠 ∇ ⋅𝒗𝑠 = 0 .            (A20)
                                                                                          𝑑𝑡      𝐾𝑠  𝑑𝑡                      (     )
                              𝑝𝑤
               𝒗 = 𝒌 ⋅∇ ℎ = 𝒌 ⋅∇                            + 𝑧    ,              (A12)     Similarly, for the water phase, rewriting Equation ( A18 ) using Equa-                                𝜌𝑤 𝑔
                                                                             tion ( A19 ), we get the following:

where 𝒌 = 𝑘𝟏 in case of isotropic and homogeneous conductivity. Thus,
                                                                    𝑑𝑛       𝑑 𝑝𝑤    1we can rewrite Equation ( A10 ) as follows:                                  − 𝑛1    +  ∇ ⋅𝒘 + 𝑛∇ ⋅𝒗𝑠 = 0 .         (A21)
                                                                                     𝑑𝑡   𝐾𝑤  𝑑𝑡   𝜌𝑤
                   𝑑𝑤 ()    𝑑()   𝒗                   =   +   ⋅∇() .                  (A13)    Adding Equations ( A20 ) and ( A21 ), recalling that 𝑛𝑠 + 𝑛 = 1 , and rewrit-
                        𝑑𝑡     𝑑𝑡   𝑛                                                                         ing it in terms of Darcy’s velocity gives the mixture balance of mass,

In Equation ( A13 ) and moving forward, for simplicity of notation, we will
drop the superscript 𝑠for the time derivative following the motion of the                   1 𝑑 𝑝𝑤                𝜌𝑤
                                                                                                  ⋅𝒗 = 0 .          (A22)                                                               − ∇ ⋅𝒗 − ∇ ⋅𝒗𝑠 −∇solid phase. In what follows, we will use Equation ( A13 ) to determine             𝑄  𝑑𝑡                                                                                              𝜌𝑤
the differential governing equations with respect to the motion of the
solid phase.                                                     where 1∕ 𝑄 = 𝑛𝑠 ∕𝐾𝑠 + 𝑛∕𝐾𝑤 .

30 of 31                                                                               International Journal for Numerical and Analytical Methods in Geomechanics, 2026

### Page 31

Balance of Linear Momentum
                                                                          𝑑𝑤 𝒗𝑤                                                                                           [2 𝑒 𝑥] 𝜌𝑤    = 𝑛∇ 𝑝𝑤 + 𝑝𝑤 ∇ 𝑛 + 𝜌𝑤 𝒈 + 𝑹𝑤 .       (A26)
The balance of linear momentum for a given phase 𝛼is as follows:                          𝑑 𝑡

      𝑑𝛼                                                                      Alternatively, the balance of linear momentum of the water phase,
                      𝒕𝛼𝑑𝐴 +                              𝜌𝛼𝒈 𝑑𝑉 +                                    𝑹𝛼𝑑𝑉 ,       (A23)          𝜌𝛼𝒗𝛼𝑑𝑉 =                                                                          following the motion of the solid phase (using Equation A13 ), is given by       𝑑𝑡 ∫𝑉                   ∫𝐴                            ∫𝑉                                      ∫𝑉
                                                                        the following:
where 𝒈 is the gravity acceleration vector, 𝒕𝛼is the partial traction vector
for phase 𝛼, and 𝑹𝛼is the body force per unit total volume exerted         𝜌𝑤 𝑑𝒗𝑤 = 𝑛∇ 𝑝𝑤 + 𝑝𝑤 ∇ 𝑛 + 𝜌𝑤 𝒈 + 𝑹𝑤 − 𝜌𝑤 𝒗 ⋅∇ 𝒗𝑤 .       (A27)
on phase 𝛼by the other phase. Recalling that 𝒕𝛼= 𝒎 ⋅𝝈𝛼, with 𝒎 the               𝑑𝑡
unit normal vector to the traction surface, and applying the fundamental
                                                               To determine an equation for the balance of linear momentum of the
theorem of calculus and the divergence theorem, it can be shown that the
                                                               whole mixture, we add Equations ( A25 ) and ( A26 ). Noting that 𝜌𝑠 + 𝜌𝑤 =
balance of linear momentum for phase 𝛼becomes the following:
                                                                𝜌(the mass density of the mixture), 𝑛 + 𝑛𝑠 = 1 , and recalling that 𝑹𝑠 =
                𝜌𝛼𝑑𝛼𝒗𝛼 = ∇ ⋅𝝈𝛼+ 𝜌𝛼𝒈 + 𝑹𝛼.             (A24)   − 𝑹𝑤 , we obtain the following:
                       𝑑𝑡                                       (        )
                                                                          𝑑𝑤 𝒗𝑤Now, if we use the definitions of partial solid stress, 𝝈𝑠 , and of partial water          𝜌𝑑𝒗𝑠 + 𝜌𝑤      −𝑑𝒗𝑠  = ∇ ⋅𝝈′ + ∇ 𝑝𝑤 + 𝜌𝒈 .       (A28)
stress, 𝝈𝑤 , from Equations ( A6 ) and ( A5 ), respectively, we can write the              𝑑𝑡          𝑑𝑡     𝑑𝑡
balance of linear momentum for the solid and water phases,
                                                 We denote Equation ( A28 ) as the mixture balance of momentum equa-
              𝑑𝒗𝑠                                                                tion.             𝜌𝑠   = ∇ ⋅𝝈′ + 𝑛𝑠 ∇ 𝑝𝑤 + 𝑝𝑤 ∇ 𝑛𝑠 + 𝜌𝑠 𝒈 + 𝑹𝑠       (A25)
               𝑑𝑡

Appendix B: Algorithms

ALGORITHM B1    Proposed 𝒖 – 𝑝𝑤 formulation method using PPE approach.

ALGORITHM B2    Proposed 𝒖 – 𝑝𝑤 formulation method using pressure rate approach.

International Journal for Numerical and Analytical Methods in Geomechanics, 2026                                                              31 of 31
