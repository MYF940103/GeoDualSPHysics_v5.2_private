# A SPH elastic-viscoplastic model for granular flows and bed-load transport

> Auto-converted from PDF for Codex/code-reference reading. Formatting, equations, figures, and tables may require checking against the original PDF.

- Source PDF: `Bedload transport.pdf`
- Pages: 18
- PDF metadata author: Alex Ghaïtanellis

## Extracted Text

### Page 1

Advances in Water Resources 111 (2018) 156–173

                                                  Contents lists available at ScienceDirect

                       Advances in Water Resources

                                   journal homepage: www.elsevier.com/locate/advwatres

A SPH elastic-viscoplastic model for granular ﬂows and bed-load transport                                                                                                  T
Alex Ghaïtanellis⁎,a, Damien Violeaua, Martin Ferrandb, Kamal El Kadi Abderrezzaka,
Agnès Leroya, Antoine Jolya

a EDF R&D/LNHE and Saint-Venant Laboratory for Hydraulics, 6 quai Watier, 78400 Chatou, France
b EDF R&D/MFEE, 6 quai Watier, 78400 Chatou, France

A R T I C L E  I N F O            A B S T R A C T

Keywords:                               An elastic-viscoplastic model (Ulrich, 2013) is combined to a multi-phase SPH formulation (Hu and Adams,
Smoothed particle hydrodynamics                   2006; Ghaitanellis et al., 2015) to model granular ﬂows and non-cohesive sediment transport. The soil is treated
Sediment transport                                  as a continuum exhibiting a viscoplastic behaviour. Thus, below a critical shear stress (i.e. the yield stress), the
Granular rheology                                         soil is assumed to behave as an isotropic linear-elastic solid. When the yield stress is exceeded, the soil ﬂows and
Viscoplastic materials
                                              behaves as a shear-thinning ﬂuid. A liquid-solid transition threshold based on the granular material properties is
                                                proposed, so as to make the model free of numerical parameter. The yield stress is obtained from Drucker–Prager
                                                       criterion that requires an accurate computation of the eﬀective stress in the soil. A novel method is proposed to
                                          compute the eﬀective stress in SPH, solving a Laplace equation. The model is applied to a two-dimensional soil
                                                    collapse (Bui et al., 2008) and a dam break over mobile beds (Spinewine and Zech, 2007). Results are compared
                                              with experimental data and a good agreement is obtained.

1. Introduction                                                       Modelling granular soils is particularly diﬃcult because they be-
                                                               have with some respect to both liquids and solids. Thus, as a ﬁrst
   The physics of granular material is a major concern for many phy-     approximation, they can suitably be assimilated to viscoplastic masical and industrial purposes, because of the wide range of problems it      terials (GDR MiDi, 2004; Morichon et al., 2013; Ulrich et al., 2013).
is involved into. In the ﬁeld of soil mechanics, the study of large de-    Below a critical shear-stress the soil behaves like a solid. When the
formations and post-failure behaviour of soils are active research topics.      critical shear stress is exceeded, the soil starts to ﬂow exhibiting a
In this kind of problem, the soil is assimilated to a continuum and     shear thinning behaviour (Campbell, 1990; Jop et  al., 2006; GDR
theories of elasticity, plasticity and viscosity are used. In the ﬁeld of     MiDi, 2004). Numerically, the solid state is usually approached by a
hydraulics, attention is focused on soil-water interactions in order to     highly viscous state. This kind of regularized viscoplastic model has
deal with sediment transport. Usually, the bed evolution is obtained    been applied in the framework of ﬁnite volumes (Morichon et al.,
from Exner equation combined to transport formulae involving the     2013). However, with such a multi-phase mesh-based method, the
empirical Shields erosion criterion. Therefore, the soil is not explicitly     presence of a free-surface requires to solve the air-ﬂow and to remodelled and the evolution of the mesh geometry is used to take the     construct interfaces between air, water and sediment. Moreover, the
bed evolution into account. Although this approach relies on a simple     highly non-linear deformations and the interface fragmentation make
mass balance equation, it has proven its eﬃciency in modelling bed     these problems diﬃcult to treat with traditional mesh-based Eulerian
load transport for large scale problems. However, this approach suﬀers    methods. On the contrary, Lagrangian approaches are particularly
from lack of physical modelling of the soil behaviour. As a consequence,    adapted  for modelling such phenomena. Regularized  viscoplastic
it is not suitable for problems involving highly dynamic behaviour.    models have been successfully applied with smoothed particle hySuch ﬂows involves several phases and exhibit highly non-linear de-    drodynamics method (SPH) to test cases such as saturation driven
formations. They are common in applied hydrodynamics problems and    embankment failure (Ulrich, 2013), submarine landslide (Capone
raise many scientiﬁc and technical issues. In particular, the modelling     et al., 2010; Xenakis et al., 2015), scouring and sediment ﬂushing
of local scour, ﬂow-induced erosion or landslide-induced water waves    problems (Fourtakas and Rogers, 2016; Manenti et al., 2011). Reare particularly complex since they require both an accurate treatment     cently Nabian and Farhadi (2016) used a similar approach in the
of mechanic behaviour of the soil and of soil-water interactions.         framework of Moving Particle Semi-implicit method (MPS).

  ⁎ Corresponding author.
    E-mail address: alex.ghaitanellis@gmail.com (A. Ghaïtanellis).

https://doi.org/10.1016/j.advwatres.2017.11.007
Received 31 March 2017; Received in revised form 3 November 2017; Accepted 6 November 2017
Available online 07 November 2017
0309-1708/ © 2017 Elsevier Ltd. All rights reserved.

### Page 2

A. Ghaïtanellis et al.                                                                                                       Advances in Water Resources 111 (2018) 156–173

   Nevertheless, regularized viscoplastic models exhibit severe draw-     weakly-compressible  materials,  pressure  is  related  to  the  density
backs regarding lowly deformed regions where the soil is supposed to    through the following state equation:
behave like a solid. According to Beverly and Tanner (1992), mis-
                                                                                                            2           ξ
leading velocity ﬁelds can result from these models when stresses are         ρ0 c 0 ⎡  ρ ⎞        + ⎤                                                                 p =    ⎢⎛⎜  ⎟ − 1 + pbg ⎥
everywhere very low compared to the yield stress, because they can             ξ                                                                               ρ0 ⎠        ⎦                                         (3)                                                                 ⎣ ⎝
only mimics the rigid body behaviour in low-stressed regions. This is
particularly important regarding erosion and scour development for     with ρ0 the reference density of the material, c0 the numerical speed of
which an accurate treatment of motionless regions is essential to cor-     sound, ξ the isentropic coeﬃcient and  pbg+ the dimensionless backrectly estimate the bed evolution.                                    ground pressure. It should be highlighted that the weakly-compressible
   Therefore, in this work the sediment  is treated as a continuum    model is less physical than numerical. The main idea is to allow the
whose behaviour law takes account for its granular nature. Ulrich’s     density to vary because of the particle Lagrangian motion, while
(2013) elastic-viscoplastic model was thus implemented in an in-house     maintaining the compressibility as weak as possible thanks to a large
GPU code based on the Cuda language,1 and improved on physical and    enough speed of sound. Given that it has no physical meaning, the same
numerical aspects. In this model, the sediment behaviour depends on a     equation of state can be used for both phases (i.e. water and soil), with
yield stress determined according to Drucker–Prager’s criterion. In     suitable values of ρ0 and c0, and ξ = 7.
unyielded regions, the shear stresses are calculated in line with the
linear elastic theory. In yielded regions, a shear thinning rheological     2.2. SPH multi-phase formulation
law is used and the transitions between solid and liquid states are ensured by a blending function driven by the strain rate magnitude and     2.2.1. Hu and Adams’ multi-phase formulation
sediment granular properties.                                        The main diﬃculty in simulating multi-phase ﬂows remains in the
   Three main improvements of Ulrich’s model (Ulrich, 2013) were     treatment of discontinuities across phase interfaces. With SPH the
presented; namely a simple and reliable method to compute the eﬀec-     density discontinuity raises particular issues. Indeed, the classical SPH
tive pressure within the material, which is essential to correctly capture     diﬀerential operators highly depend on the density of neighbouring
the failure process and the regime transitions, an improvement of solid      particles. Consequently, numerical instabilities can occur near the inforces  calculation  using a SPH second order  derivative  operator     terface for quite large density ratios. Note that the density ratio usually
(Espanol and Revenga, 2003), and a physical threshold for the liquid-     involved in sediment transport problems do not  strictly require a
solid transition. Therefore, contrary to Ulrich’s (2013) original model,     multi-phase  formulation   of  SPH  operators.  As  an  example,
the mechanical behaviour of the soil does not depend on any numerical    Manenti et al. (2011) and Ulrich (2013) successfully applied one-phase
parameter in the present model.                                SPH  models   to   such   problems.  However,   Colagrossi  and
   The granular and water phases are treated in the frame of Hu and     Landrini (2003) showed that the SPH gradient of pressure used in
Adams’s (2006) SPH multi-phase formulation. The multi-phase model    Manenti et al.’s (2011) and Ulrich’s (2013) formulations implicitly inwas adapted to semi-analytical wall boundary conditions (Ferrand     volves a gradient of density. Then, at the interface of two phases, this
et al., 2013) in order to model multi-phase ﬂows that both require an     formula computes the derivative of a discontinuous ﬁeld. Even if it does
accurate pressure and shear stress treatment at the wall, and present     not always lead to numerical instability, this formulation is formally not
complex boundary geometries.                                        adapted to multi-phase problem. On the other hand, Fourtakas and
    First, the SPH multi-phase model is presented and validated. A de-     Rogers (2016) used Colagrossi and Landrini’s (2003) multi-phase forscription of the soil constitutive equations, as well as their SPH discrete     mulation. Although this model is suitable for multi-phase problems, the
form are then provided. Numerical results are ﬁnally compared with     density ﬁeld is obtained through an explicit integration of the conexperimental data for two 2D cases. We assume that the reader is fa-     tinuity equation. This leads to the accumulation of systematic integramiliar with SPH (Violeau and Rogers, 2016).                               tion errors, which can make the density and velocity ﬁelds become
   Throughout this document, the sign convention of mechanics is     inconsistent (Ferrand et al., 2010; 2013; Vila, 1999). Thus Hu and
used.                                                            Adams’s (2006) multi-phase formulation will be used in this work.
                                                                               In standard one-phase SPH formulations, the density ρ of a particle a
                                                                                                is usually computed as the interpolation of the density of neighbouring
2. Weakly-compressible multi-phase SPH model
                                                                                 particles b:

2.1. Governing equations                                              ρa = ∑ Vb ρb wab
                                                                                                        b ∈ F                                                            (4)
   In this work, the sediment is treated as a continuum whose beha-                                                                    with V the particle volume, wab = w r(ab ) where w is the SPH kernel (in
viour law takes account for its granular nature. Thus, sediment trans-                                                                                            all this paper, we use Wendland’s 5th-order kernel (Wendland, 1995)),
port is modelled adopting a multi-phase approach. Water and soil de-                                                                                        rab =  r a − r b and r the particle position vector. F denotes the set of
viatoric stresses are calculated with diﬀerent behaviour laws, otherwise                                                                                free particles. One clearly sees that using Eq. (4) in the vicinity of the
the same set of equations is used for the two phases. For weakly-com-                                                                              interface between two phases of diﬀerent densities, leads to a numerical
pressible ﬂows, the Lagrangian form of continuity equation reads:                                                                 smoothing of the interface. This loss of information is a substantial
dρ                                                             drawback but it can be avoided since it is purely numerical.
  = − ρ div u
dt                                                                   (1)       To circumvent this issue, Hu and Adams (2006) proposed a for-
                                                                    mulation based on the interpolation of the inverse volume instead of
with ρ the density of the material, t the time and u the velocity. Then,     density:
momentum equation reads:
                                                                     1
                                                                      ⎛                                                                        ⎞                                                  =                                                         wab                              ∑du       1                 1                                                                      ⎝ V                                                                        ⎠ a                                                                                                                                                  (5)                                                                                                            b                                                                             ∈ F  = −          grad p +                     div τ + g
 dt     ρ         ρ                                                (2)
                                                             Then the deﬁnition of density becomes:
with p the pressure, g the gravity and τ the shear stress tensor. In the
                                                                             1
                                                                    ρa = m a ⎛  ⎞ = m a ∑ wab
                                                                             ⎝ V ⎠ a        b ∈ F                                             (6)
  1   The code  is based on a simpliﬁed version of the open source GPUSPH solver
(GPUSPH oﬃcial website).                                                     Therefore, the mass ma of a particle being constant in WCSPH (weakly-

                                                                       157

### Page 3

A. Ghaïtanellis et al.                                                                                                       Advances in Water Resources 111 (2018) 156–173

compressible SPH), the variation of density is only due to the evolution    boundary elements and vertex particles, the reference volume V  is
of the spatial organisation of neighbouring particles. Thus, the interface     obtained from a Shepard interpolation of the inverse volume (for more
smoothing is avoided. In order to simplify notation, we will refer to the      details, see Ferrand et al., 2013):
particle volume as Va deﬁned as:
            −1                                                                ⎡ ∑b ∈ F wab ⎤−1
                                                           ∀ a ∈ (V ∪ S)  Va = ⎢         ⎤         ⎞                                                ∑b ∈ F Vb wab ⎥⎦                            (10)                                                                           ⎣         ⎠ a                  ⎦⎥                                                        (7)Va = ⎡⎣⎢⎛⎝ V1
  Hu and Adams (2006) then proposed a pressure gradient that can be     For free particles, the volume is equal to the reference volume (θ = 1)
derived from (6) and the Lagrangian variational principle of Virtual    and is obtained adapting (5) and (7) to this framework:
Work (Grenier et al., 2009):                                                                         −1
                                                                      ⎡ 1           ⎤         1                                   ∑                                                           ∀ a ∈ F  Va = ⎢                                                                                           θb wab ⎥     ∑G a { pb } =                       (pa Va2 + pb Vb2 ) ∇ wab ≈ (grad p ) a                                                                         Γa b ∈ (                                                       F∪ V)       V                                                                      ⎣                                                                                    ⎦                             (11)                                                                     (8)             a b             ∈ F

where < uline > ∇< /uline > wab is the kernel gradient at the location    where Γ is a renormalization factor used to correct the interpolation
of particle a. Note that the pressure gradient does not depend on density     error due to the lack of particles beyond the boundary:
any more, and is consequently stable near the interface. In addition,
                                                                                                                   a ) dr ′                                                                                                                                       (12)Hu and Adams (2006) also proposed a modiﬁed viscous term so as to    Γa = ∫Ω ∩ Ωa w ( r ′ − r
deal with multiple viscosities, ensuring the continuity of velocity and
shear stress across the interface:                                           Thus, from (10) and (11), we see that the reference volume is not
                     2ηa ηb     2      2 u ab                                constant and only depends on the geometrical conﬁguration of neighL a { ηb , u b } = n a ∑            (Va + Vb )  2  r ab · ∇ wab                      bouring particles around the point of interest. For free particles, density
                       b ∈ F ηa + ηb            rab                                                                                                 is obtained adapting Vila’s form of the continuity equation (Vila, 1999):
      ≈⎛⎜div ⎛⎜       ⎞ ⎞                  η grad u ⎟ ⎟                                                                        d (Γ                                                                                                             ⎞                                                                                 d ⎛                                                                                                            a ρa )                                                                     (9)              ⎝   ⎝                          ⎠ ⎠ a                                                           =                                                           ∀ a ∈ F                                                       m a                                                                                                  θb wab                                      ∑                                                                                            ⎜                                                                                                             ⎟                                                                                                dt                                                                                                        dt                                                                                                                                       b ∈ (                                                           F∪ V)                                                                                            ⎝                                                                                                             ⎠                      (13)where η is the dynamic                          viscosity,                                                             a                           u ab = u a − u b with u the velocity of
particle.
                                                                   Then, adapting the variationally consistent pressure gradient to USAW
                                                                boundary conditions, we get an approximation of the pressure gradient:
2.2.2. Adaptation to USAW boundary conditions
  Hu and Adams’ formulation is a straightforward, robust and var-               1                       2         2                                 ∑                                                                                      θb (pa V a + pb V b ) ∇ wab                                                 G a { pb } =iationally consistent multi-phase model. However, a rigorous treatment                                                                   Γa Va b ∈ (                                                    F∪ V)
of boundary conditions is necessary to make it capable of simulating
                                                                                 1       1       2         2ﬂows presenting complex boundary geometries. To do so, the model is         −  ∑     (pa V a + ps V s ) ∇ Γas
                                                                     Γa Va  s ∈ S Vs                                         (14)adapted to uniﬁed semi-analytical wall (USAW) boundary conditions.
  USAW boundary conditions framework is based on a mesh used to
                                                              where p is the pressure and ∇Γas is the contribution of segment s to thediscretized boundaries of the domain (Ferrand et al., 2013). The mesh is
                                                                         gradient of Γa. For a 1-D segment s, delimited by two vertex particles
composed of boundary elements (S) being segments in two dimensions
                                                                                        (v1, v2), ∇Γas is deﬁned by:and triangles in three dimensions (see Fig. 1a). Free particles are placed
at the vertices of the mesh, they move at wall velocity and are referred                         v 2
to as vertex particles (V ). Contrary to boundary elements, they carry a   ∇ Γas = ( ∫v 1 w (r ) dl ) n                                                                                                                                                                            s                                        (15)
mass m and should be taken into account in the continuity equation.
Their volume V depends on the local geometry of the boundary and is    where ns is the inward normal of the segment s. Note that the discrete
calculated as a fraction θ of a reference volume V : V = θV (see Fig. 1b).    SPH diﬀerential operator (14) contains a volumic term, related to free
In two dimensions, θ is deﬁned as the angle between two connected    and vertex particles, and a boundary term related to boundary elesegments, divided by 2π. Thus, for vertex particles we have θb ∈]0; 1[.     ments. In the absence of boundaries, (14) gives back Hu and Adams’
In order to have a general formulation, we also deﬁne θa = 1 for free     original formula (8).
particles of matter (F ) and θs = 1/2 for boundary elements. In three         Similarly, we deﬁne the consistent divergence operator for a vector
dimensions, θ is calculated in a similar way using solid angles. For     ﬁeld A:

                                                                                                                                  Fig. 1. (a) Sketch of a boundary with: a vertex particle
                                                                                                                   b ∈ V, θv depends on the local shape of the boundary;
                                                                                                                 a   segment    s ∈ S (θs = 1/2) ;   a   free   particle
                                                                                                           a ∈ F (θa = 1) . (b) Sketch of a vertex particle in a
                                                                                                                               right-angled corner in 2-D, illustrating the relation be-
                                                                                                           tween volume Vb, the dimensionless angle θb and the
                                                                                                                             reference volume Vb .

                                                                       158

### Page 4

A. Ghaïtanellis et al.                                                                                                       Advances in Water Resources 111 (2018) 156–173

          V                            V                                           1                  a                                                 a                                                   −                                                                    ρa(n + 1)                                                                           ρa(n )Da { A b } = −                      θb A ab · ∇ wab +                                A as · ∇ Γas       ∑               ∑                                                       = − ρa(n ) Da { u b(n + 1) }           Γa                               Γa                                                                                    s                                                                                                                           t                                                      Δ                                                                          s                      b ∈ (           F∪ V)                                        ∈ S V
     ≈ (div A ) a                                              (16)                                               (n )  ⎧   (n )   Δt           (n )      ⎫
                                                       = − ρa Da u b −     (n ) G b { pc   } + Δt g
                                                                                                                                                      ⎨⎩       ρb                          ⎬⎭where Aab denotes A a − A b. Now we proceed the same way for the
viscous term, paying particular attention to the viscosity of segments            = − ρa(n ) (Da { u b(n ) } + ΔtDa { G b { pc(n ) }} + ΔtDa { G b { g · r b(n ) }})
and vertex particles. Since we do not want to assign a phase to                                                                    (23)
boundaries, we take ηb = ηa when  . First we adapt Hu and Adams’                                                              where Δt is the time-step. The latter equation shows that the approxviscous term (9) to USAW boundary conditions:                                                                                                                      (n )
                                                                    imate Laplacian of pressure Da { G b {pc   }} is implicitly contained into the
  H           1           2ηa ηb        2      2 u ab                         time-discretized equation of continuity, acting like a diﬀusion term.L a  { ηb , u b } =   ∑         θb (V a + V b )  2  r ab · ∇ wab                Fatehi and Manzari (2011), and more recently Hashemi et al. (2016),
           Γa Va b ∈ (F∪ V) ηa + ηb               rab
                                                                             stated that substituting this discrete form of the Laplacian by an SPH
                               u
        −                                                         as r as · ∇Γas                         Laplacian operator L to be deﬁned can signiﬁcantly reduce the nu-                1 ∑ η                                a (V a2 + V s2 )                                                   2
             Γa Va  s ∈ S Vs             ras                        (17)     merical pressure oscillations. This technique was ﬁrst introduced for
                                                                        ﬁnite volumes by Rhie and Chow (1983). It consists in adding to (13)
As of now, we will refer to it as Hu and Adams’ viscous term. Then, we     the diﬀerence between Da { G b {pc(n ) }} and La {pb(n ) } . This will result in a
write the  classical USAW Laplacian (resulting from the model of    smoothing term that will tend to zero as the particle spacing δr deMorris et al., 1997) in the multi-phase framework:                          creases. Several combinations of discrete Laplacian operators have been
                                                                             tested and we ﬁnally chose the following smoothing term:
  M          1              4ηa ηb u ab
L a  { ηb , u b } =  ∑   θb Vb            2  r ab · ∇ wab                                                                                                                                 (n )
           Γa b ∈ (F∪ V)     ηa + ηb rab                                                                    (n )        (n )  ⎡ M ⎧ 1         (n ) ⎫    + ⎧  −⎧ pc  ⎫ ⎫ ⎤
                                                  Δ  = ρa Δt ⎢La        (n ) , pb  − Da  G b       (n )   ⎥
         −                                                                                                                           b           ⎬⎭         ⎨⎩     ⎨⎩ ρb   ⎬⎭ ⎬⎭ ⎥⎦                (24)                                        as r as · ∇ Γas                                      ⎢⎣     ⎨⎩ ρ               1 ∑ 2ηa u2
             Γa  s ∈ S     ras                                   (18)                                    −                                                                    with LM the Morris operator (18), G  the symmetric SPH gradient deFrom now on, we will refer to it as Morris et al.’s (1997) viscous term.    ﬁned by:
Note that, this viscous term also ensures continuity of velocity and                                                                     −      Va                                                G a { Ab } = − ∑ θb (A a − Ab ) ∇ wabshear stress across the interface. The two latter formula are approx-
                                                                     Γa b ∈ F                                             (25)
imations of the Laplacian operators:
                                                              and D + the anti-symmetric divergence deﬁned by:

                            ⎞                           ⎞                                                                               1                   η grad u                           ⎟L aH / M { ηb , u b } ≈⎛⎜div ⎛⎜                            ⎟                            Da+ { A b } =                                ∑ θb ( A a V a2 + A b V b2 ) ∇ wab
              ⎝   ⎝       ⎠ ⎠ a                                 (19)            Γa Va b ∈ F                                             (26)

  A more general discrete second-order operator can also be deﬁned.    The last two SPH operators have inverse symmetry properties with
It will be referred to as Espanol and Revenga’s operator and will be     respect to the original ones used above. This particular combination
denoted LE. In the frame of the multi-phase formulation with USAW    was not chosen on a theoretical basis but after numerical tests. Moreboundary conditions, it is deﬁned for any vector and scalar ﬁelds A and     over, these operators are built on the basis of the multi-phase operators
B by:                                                                   (14) and (16) so the Rhie and Chow’s (1983) correction terms are
                                                              computed from all neighbouring particles, irrespective of the phase
  E          1              2Ba Bb                                    they belong to. On the other hand, this correction only occurs betweenL a {Bb , A b } =  ∑   θb Vb          ((d + 2)( A ab · e ab ) e ab
           Γa b ∈ (F∪ V)    Ba + Bb                                        free  particles, so the discrete operators in (24)–(26) do not have
            ∇ wab · e ab    1      A as                        boundary terms and do not include the vertex particles. The continuity
         + A ab )      −  ∑ 2Ba   2  r as · ∇ Γas                   Eq. (13) is corrected as follows:
                            rab     Γa  s ∈ S      ras                   (20)

                                                                                                                                               (n + 1)     1  ⎡   (n )   (n )                                     (n + 1)         (n ) ⎤           (n )
with d the space dimension. Contrary to (9) and (18), Espanol and     ρa   =    (n + 1) ⎢Γ  ρa + m a ∑   θb (wab  − wab ) ⎥+ ΛΔ                                                                  Γ
Revenga’s (2003) formula (20) is not an approximation of the Lapla-                                                                     ⎣                 b ∈ (F∪ V)             ⎦
cian. Indeed, Violeau (2009) showed:                                                                                                   (27)

                                                              where Λ is a weighting coeﬃcient. From numerical experiments, Λ = 1
  E          ⎛   ⎛ ⎡         ⎛      ⎞T ⎤ ⎞ ⎞                              gives satisfactory results.               div                     grad A + ⎜                               grad A ⎟              B ⎢                                ⎥L a { Bb , A b } ≈ ⎜                                         ⎟                 ⎜                                        ⎟                                                                   Note that no particle shifting algorithm is used in this work.                             ⎝                                    ⎠                ⎣                                ⎦                 ⎝                                        ⎠             ⎝                                         ⎠ a                   (21)

                                                                                 2.2.4. Time integration scheme
                                                               Time integration is done with a fully explicit symplectic method
2.2.3. Rhie and Chow correction                                         (Ferrand et al., 2013) that leads to the following scheme:
   Far from the boundaries and considering the time as a continuous
                                                                                                                                              t                                                                                                                                                                     t                                                               Δ                                                                         Δ                                                        ⎧variable,          Vila             (1999)                  showed                               that                                    that                                       the                                               discrete                                                  equation                                                                 of con-                                                              u a(n + 1) = u a(n ) −                                                                                                                                                                               (n                                                                                                                                                                                  ) G a { pb(n ) } +                                                                                                                                                                                                            (n                                                                                                                                                                                                              ) La {ηb , u b(n ) } + Δt g                                                        ⎪                                                                                   ρ                                                                                                 ρ                                                                                                                a                                                                                                                                  atinuity       (13)           can              be related                           to some                                kind                                          of                                             implicit                                               time                                                         integration                                                                      of                                                        ⎪
the continuity equation:                                      ⎪ r a(n + 1) = r a(n ) + Δt u a(n + 1)

                                                        ⎨                                                                      ⎡                                                                                                    ⎤                                                                               1dρ                                                        ⎪                                      ∑                                                                                                    θb (wab(n + 1) − wab(n ) )                                                                     ρa(n + 1) =                                                                         Γ (n ) ρa(n ) + m a                                                                      ⎢                                                                                                    ⎥                                                                               + 1)   a = − ρa Da { u b }                                                                   Γ (n                                                        ⎪                                                                                                                                         b ∈ (                                                            F∪ V)                                                               (22) dt                                                                      ⎣                                                                                                    ⎦                                                        ⎪
                                                        ⎩      + ΛΔ(n )                                              (28)
An implicit scheme being used for integrating (22) and neglecting the
viscous term in integrating the momentum Eq. (2) using the SPH gra-    Two restrictions on the time step must be enforced to ensure the nudient operator (14), we can write:                                       merical stability of this integration scheme. The ﬁrst one relies the

                                                                       159

### Page 5

A. Ghaïtanellis et al.                                                                                                       Advances in Water Resources 111 (2018) 156–173

classical Courant–Friedrichs–Levy (CFL) number. The CFL number
compares the time-step to the time for the information to travel the
characteristic distance of the simulation (i.e. the discretization scale h)
at the characteristic velocity of the problem. In WCSPH the CFL number
is deﬁned as:

        c 0 Δt
CCFL =
       h                                                     (29)

For the viscous forces, an additional condition must be enforce through
the following dimensionless number:

       η Δt
C visc =     2      ρh                                                      (30)

This number expresses the fact that, the higher the viscosity, the faster
the information propagate along the successive layers of the ﬂuid. More
details about the numerical  stability of WCSPH can be found in
Violeau and Leroy (2014) and Hashemi et al. (2016) (the latter includes
the eﬀect of density smoothing).

2.2.5. Validation
   The present formulation is validated on a two-ﬂuid laminar plane      Fig. 2. Bi-ﬂuid Poiseuille ﬂow – horizontal velocity proﬁle at the steady state for a
Poiseuille ﬂow in a closed channel, involving two ﬂuids of diﬀerent      Reynolds number of Re 1 = 1.25 , with density and viscosity ratio of λ = ω = 4 ( y+ ≤ 0⇔
kinematic viscosities (ν1, ν2) and densities (ρ1, ρ2). The 2D ﬂow is driven     ﬂuid 1). Morris et al.’s (1997) viscous term is used and L / δr = 384. The black dots re-
                                                                                            present the SPH numerical result, while the solid line corresponds to the analytical soby a gravity force ρg oriented in the direction of the ﬂow ex, (ex, ey)      lution (34).
being the base vectors. Periodic open boundaries are used and the
height of the channel is L = 1 m. The interface between the two ﬂuids is
in y = 0, the top wall in y = L/2 and the bottom wall in y = − L/2,     Table 1
                                                                                          Bi-ﬂuid Poiseuille ﬂow – physical and numerical parameters for a Reynolds number of
where ey denotes the transverse direction. In the present work, the     Re 1 = 1.25, with ω = λ = 4.
subscript 1 refers to the ﬂuid in the bottom part (y < 0). In all simulations, the ratio between δr and the smoothing length h is δrh = 2. Note                                                               Fluid 1             Fluid 2
that, in this case the Rhie and Chow’s (1983) correction presented in
                                                                                            Phys.            g          [m · s−2]               4.0·10−7             4.0·10−7Section 2.2.3 was not used. Instead, the Brezzi and Pitkäranta’s (1984)
                                                                                                                  ρ0            [kg   · m−3]          4000            1000
correction presented in Ghaitanellis et al. (2015) was used in order to
                                                                                                            η             [Pa   · s]               1.6                0.1
compare their results to the present results.                               Num.            c0          [m   · s−1]            0.02              0.02
    Results are compared with the analytical solution that depends on                         Pbg            [Pa]               0               0
the ratio between densities and viscosities, respectively denoted λ and                         ξ             –                  7               7
ω:                                                                                              ΛBP           –                     0.1                0.1
    ρ1        ν1
λ =      ,  ω =
    ρ2        ν 2                                               (31)         In order to validate further the multi-phase model, and to quanti-
                                                                                 tatively compare the three viscous terms (18), (17) and (20), we perWe also deﬁne u͠1 a characteristic velocity of the ﬂow and Re1 the cor-
                                                                formed a convergence study with the parameters summarized  in
responding Reynolds number:
                                                                     Table 1. For each simulation, velocity ﬁeld is initialized to zero, the
                       gL3                                                                     numerical solution converges to a steady-state (see Fig. 3a) that is                         1 L
              =u͠1 = gL2 ,   Re1 = u                                    2
     2ν1           ν1    2ν1                                    (32)    compared to the analytical solution (34) through the velocity  in-
                                                                       stantaneous L2 relative error E deﬁned as follows:
Finally, we deﬁne the following dimensionless quantities:

                                                                          u                                                                                                                                               t                                                                                 u                                                                                                                             )                                                                                                                                       (                                                                                                                                                                                             , t )) 2                                                             −      y             u                                                                                                                         b (                                                                                                                                                  th                                                                                                        yb                                                                                                              ( ∑b ∈                                                  Fy + =              ,  u+ =                                                       E (t ) =
                                                                                                                                         2     L              ux1 ,                                            (33)                                                                             u                                                                                                                            (                                                                                                                                 (y                                                                                                                                                                                     , t                                                                                                                          ))                                          ∑                                                                                                                                            th                                                                                                                                  b                                                                                                                     b ∈                                                                                                                                       (35)                                                    F
where u x = u e· x with u the velocity of the ﬂuid. With these notations,
                      +                                         where ub is the particle velocity, uth(yb) the theoretical velocity at the
the analytical solution uth reads:
                                                                            position of particle b. The steady state is assumed to be achieved when
       ⎧[1 − (y + ) 2 ] + 11+−λωω (y + − 1)       if    y + ∈ [0; 1]                the proﬁle is fully developed. The characteristic time of the viscous +  +                                                                        eﬀects                                                                            propagation                                                                                     through                                                                                                    the                                                                                                  channel                                                                                                      width                                                                                                           L can be                                                                                                                             evaluated                                                                                                                                              asu th (y  ) =                           −                                      1       ⎨        ω [1 − ( y + ) 2 ] + λω                               ω ( y + + 1)       if    y + ∈−[  1; 0]
                                   λω                                                                                                                 t                           +                                      1                                                                       we                                                                                     deﬁned                                                                                                            the                                                                                                               dimensionless                                                                                                                       time                                                                                                                                                                                                             t + = t t/                                                                                                                                                                                                           1.                                                                                                  1 = L2 ρ1                                                                                                 / η1 , from which       ⎩
                                                               (34)     Fig. 3a shows the instantaneous error with respect to the dimensionless
                                                                           time. We can see that the steady state is achieved at t + ≈ 1, and that the
                                                                            solution remains stable afterwards. In order to have an objective meaComparison of viscous terms ( Re1 = 1.25 ) –. Fig. 2 shows the longitudinal     sure of the error, independent from the small oscillations of the invelocity proﬁle obtained using Morris et al.’s (1997) viscous term (18),                                                                       stantaneous error, we deﬁne the time-averaged error E , computed from
with L / δr = 385 SPH particles on the channel width. Numerical results                                                                        (35) as:
are in excellent agreement with the analytical solution (34) represented
by the solid line. Results obtained with Hu and Adams’s (2006) viscous          1  Nt
                                                       E =                                                               E (t i )                              ∑term (17) and Espanol and Revenga’s (2003) one (20) also give such                                                  Nt                                                                                                                                       (36)                                                                                                                                                                                               i = 1
good qualitative results, thus demonstrating that the shear stresses at
the wall and at the interface are correctly calculated by the present    where t( i ) i ∈ {1.. N}t corresponds to the Nt iterations in the time interval
multi-phase model.                                                                                    t + ∈ [1.5, 3.5] (grey region in Fig. 3a).

                                                                       160

### Page 6

A. Ghaïtanellis et al.                                                                                                       Advances in Water Resources 111 (2018) 156–173

                                                                                                                            Fig. 3. Bi-ﬂuid Poiseuille ﬂow Re 1 = 1.25 – (a) evolution of
                                                                                                                     the instantaneous L2 relative error E with respect to the di-
                                                                                                                 mensionless time t + . (b) Convergence graph of the present
                                                                                                  method comparing Morris et al.’s (1997) (18), Hu and Adams’
                                                                                                                     (17) and Español and Revenga’s (20) viscous terms, for nine
                                                                                                                      values of δr/L.

    Fig. 3b shows the time-average error E with respect to the di-                               T
                                                                         1 ⎛        ⎛      ⎞ ⎞                                                                                grad u + ⎜grad u ⎟mensionless particle size δr/L (i.e. the inverse of the number of particles     γ˙ =                                                                                              ⎟                                                                         2 ⎜
along the channel height). We see that the convergence slope of the           ⎝        ⎝      ⎠ ⎠                                     (40)
present method using the three viscous terms is approximately of order
                     −                                            The ideal Bingham model (38) describes a material that behaves as a2 as long as δr / L ≤ 5·10 2. Afterwards, the convergence slope decreases
                                                                                 rigid body at low stresses and ﬂows as a ﬂuid when the yield stress is
for Morris et al.’s (1997) and Hu and Adams’ operators, while the error
                                                                      exceeded. Unfortunately,  ideal Bingham’s model, as well as Herstabilized for Espanol and Revenga’s (2003) viscous term. These results
                                                                            schel–Bulkley’s and Casson’s ones, all involve discontinuous behaviour
are consistent with those obtained by Ferrand et al. (2013) for one ﬂuid
                                                                law that corresponds to the liquid-solid phase change. They are thus
SPH formulation with USAW boundary conditions, thus validating the
                                                                       poorly adapted to numerical simulation because they require additional
present multi-phase model. Note that, contrary to the results obtained
                                                                     numerical procedures to track down yielded/unyielded regions. Indeed,
by Ghaitanellis et al. (2015), Hu and Adams’ operators is not less ac-
                                                                                                         it can be easily veriﬁed that the transitions between liquid and solid
curate than Morris’s one. This is because there was an implementation
                                                                                  states are not included in the model. To do so, let us calculate τ applying
error in Ghaitanellis et al.’s (2015) code.
                                                                        (37) to the second equation in (38), which corresponds to the liquid
                                                                                      state:
3. Sediment constitutive model
                                                                                     τ = η∞ γ˙ + τy                                                   (41)
3.1. Context
                                                         One can see that when the strain rate vanishes, the deviatoric stress
   The main diﬃculty in modelling granular materials is that they     decreases and tends to τy but never goes below. To circumvent this
cannot be classiﬁed as solids or liquids. Indeed they can behave like      issue, these models can be approximated assuming that the viscoplastic
both of them under slightly diﬀerent conditions. That is the reason why     material is a liquid that exhibits inﬁnitely high viscosity when the strain
rheological approach  is often adopted to model granular ﬂows. In     rate vanishes. Beverly and Tanner’s (1992) bi-viscosity model and
particular, soil is usually treated as a viscoplastic material. Thus it has a     Papanastasiou’s (1987) formula are two widely used examples of such
yield stress τy under which no deformation occurs. When the yield stress     regularized viscoplastic models. Thus the material is always liquid but
is exceeded, the material starts to ﬂow. In such a model, the yield stress    mimics the ideal models behaviour for all rates of deformation. Nuhas to be compared to an invariant measure of the deviatoric stress     merically, this is achieved using shear thinning rheological law and
tensor τ. In this work, the tensor second invariant is used according to     limiting the viscosity to a huge but ﬁnite maximum value. This method
Drucker–Prager yield criterion (Drucker and Prager, 1952):                     is straightforward and has been widely applied to the simulation of
                                                                    sediment  transport with  Finite Volumes (Morichon  et  al., 2013),
      1
                                                             Moving Particle Semi-implicit method (Nabian and Farhadi, 2016) andτ =                                ij τij   ∑i , j τ                                                               (37)      2
                                                               smoothed particle hydrodynamics method (Capone et al., 2010).
    Viscoplastic models include Herschel–Bulkley’s and Casson’s ones,        Regarding sediment transport modelling,  this approach  is well
but  the most common and best-known model was proposed by    adapted for highly dynamic scenarios but exhibits severe drawbacks
Bingham (1917) and reads:                                              regarding small strain-rates and deformations. Indeed, the maximum
                                                                                viscosity has to be large enough to guarantee that no signiﬁcant motion
  γ˙ = 0                    if  τ < τy⎧                                                                        occurs in unyielded regions. This is particularly important regarding
                                                                         erosion                                                                     and                                                                                    scour                                                                                  development                                                                                                                    for                                                                                              which                                                                                                    an accurate                                                                                                                            treatment                                                                                                                                                    of⎨                 γ˙   if  τ > τy  τ = 2 ( η∞ +  τγy˙ )                                                               (38)⎩                                                                        motionless                                                                                     regions                                                                                                                         is                                                                                                       essential to                                                                                                                 correctly                                                                                                                  estimate                                                                                                                          the bed                                                                                                                                         evolution.
                                                                      Thus, it is necessary to ensure that results do not depend on the chosenwhere η∞is the plastic viscosity,   γ˙ the strain rate tensor and  γ˙  its
second invariant deﬁned as:                                 maximum viscosity. But in practice, the maximum value of viscosity is
                                                                             actually limited  for  explicit time integration schemes, because of
γ˙ =  2 ∑i , j γ˙ij γ˙ij                                                (39)     computational cost.
                                                                  As a consequence, in the present paper, a diﬀerent approach is
with  γ˙ij the components of the strain rate tensor deﬁned as:                 tested. The model of Ulrich (2013) is implemented in the framework of

                                                                       161

### Page 7

A. Ghaïtanellis et al.                                                                                                       Advances in Water Resources 111 (2018) 156–173

multi-phase formulation, and adapted to USAW boundary conditions.     cases in which the material is initially totally dry (denoted by dry) or
The soil is treated as a linear-elastic solid in unyielded regions, and as a      fully saturated (denoted by sat), and remains that way for ever. For the
shear thinning liquid in yielded regions. A continuous transition be-     dry case, the mass of air in the pore is neglected, while for the saturated
tween the two states is ensured by a blending function driven by the     case, the equivalent density also depends on water density ρw:
strain rate magnitude. Besides, improvements of the yield stress and
solid forces computation are proposed, as well as phase transition    ⎧ ρeqdry = (1 − ϕ ) ρg
threshold based on the physical properties of the granular material.      ⎨                                                                     ρeqsat = (1 − ϕ ) ρg + ϕ ρw                                        (42)                                                        ⎩

3.2. Modelling assumptions                                           Although a weakly-compressible formulation is used in this work, we
                                                             aim at modelling incompressible materials. The equation of state (3) is a
    In this work, the granular material, being dry or saturated, is treated     numerical way of closing the equations of motion system, but the
as a continuum. Under this assumption, the continuous medium re-     compressible eﬀects are not supposed to play any role in the behaviour
presents a mixture of grains and air, or grains and water. Therefore, we     of the granular material. Thus, we assume here that ρw and ρeqsat are
need to deﬁne equivalent properties of the continuous material from the     constant. Secondly, neglecting the ﬂow through the porous material
physical properties of the granular material components. The continuum     also implies that the pore water pressure ﬁeld is unknown. Therefore,
properties should also depend on the grain concentration. However the     another approximation is necessary and the pore water pressure will be
continuum hypothesis presents a major diﬃculty within the framework of    assumed to be hydrostatic.
the SPH formulations presented in Section 2.2. Physically, the evolution         Finally the granular medium will be considered incompressible. In
of grain concentration results from diﬀerences of velocity between the      soil mechanics, this hypothesis is only valid for fully saturated soils
solid phase and the liquid phase. When the mixture is assumed to be    under fast loading (un-drained condition) (Craig, 1983; Davis and
continuous, the concentration evolution must be taken into account     Selvadurai, 2005). Thus, as regards bed-load transport and scouring
through the transport of a concentration ﬁeld. However, this  is not     resulting from violent ﬂows, this assumption is suitable. Although this
straightforward in the framework of the present SPH model because this     hypothesis is not valid for problems involving dry granular media, we
implies mass transfers between SPH particles. The particle masses being     will see that the model is able to give satisfactory results in that case
no longer constant, the SPH formulation presented in Section 2.2 is not     too.
valid anymore and a whole new SPH formulation would be necessary.
Such a model is beyond the scope of this paper. Thus, although it has be
                                                                                 3.3. Yield stress
shown that the grain concentration is an important parameter for the
description of dense granular ﬂows (Armanini et al., 2005; GDR MiDi,
                                                                     There are many yield criteria that are adapted to the diﬀerent kinds
2004), the grain concentration will be assumed to be constant and
                                                                              of  viscoplastic materials. Although the Mohr-Coulomb  criterion  is
homogeneous within the mixture domain. Therefore, in practise, ϕ is
                                                                    widely used in geotechnical engineering,  its implementation raises
simply the porosity of the granular material at initial time.
                                                                    numerical issues because the corresponding yield surface is an irregular
   In addition, the ﬂuid surrounding the grains will be assumed to be at
                                                                   hexagonal pyramid (Jiang and Xie, 2011). Thus, the Drucker–Prager
rest with respect to the granular material skeleton. Indeed solving the
                                                                             yield criterion is usually used as a smooth alternative. It is a pressure-
ﬂuid ﬂow through the porous medium raises many practical issues, in
                                                                  dependent model that can be expressed in terms of internal friction
particular at water-mixture interfaces. For example, let us consider an
                                                                       angle ψ for non-cohesive soils as:
outgoing water ﬂow from the mixture phase to the water phase. Then
the mixture SPH particles should give some water mass up to the water         2  3 sin ψ
                                                                                     τy =                                                                              peffSPH particles in order to ensure the mass conservation. Again, this                                                                         3 − sin ψ                                                                                                                                       (43)
would require variable SPH particle masses. Ulrich (2013) proposed a
simpliﬁed model of partly saturated soil, solving the ﬂow in the porous    where peﬀis the eﬀective pressure, that is to say the normal stress that
material and transporting a concentration ﬁeld. However, with this     the grains actually exert on each other. Considering a situation where
model, the mass of water is not conserved. Consequently, in his work     the stress conﬁguration is close to the failure, almost no motion occurs
the water ﬂow through the porous medium is also neglected and the     within the material. Therefore, the isotropic stress (i.e. the total presinterstitial water  is assumed to move at the mixture velocity. This     sure ptot) is solely due to pressure derived from the weight of the
simpliﬁcation implies several disadvantages. First, the seepage cannot    column of material and interstitial ﬂuid above a speciﬁed level. Conbe taken into account while it can have a signiﬁcant eﬀect when a     sequently, denoting zi the soil-water interface vertical position, zfs the
stable structure of dry granular material becomes partially saturated     free-surface vertical position and z the vertical position of the point of
(Liu and Li, 2015). Thus in the present work, we will only consider     interest (see Fig. 4), the total pressure reads:

                                                                                                                           Fig. 4. Characteristic pressures in a submerged bed of soil
                                                                                                                       saturated with water.

                                                                       162

### Page 8

A. Ghaïtanellis et al.                                                                                                       Advances in Water Resources 111 (2018) 156–173

ptot = ρw g (z fs − z i ) + ρeqsat g (z i − z )                               (44)     evaluated in line with linear elastic theory. The shear stress tensor in
                                                                        the solid regions reads:
   Moreover, Terzaghi’s principle (Terzaghi, 1936) states that the effective pressure depends on the total pressure ptot and the pore water      τ gs = 2 G γ                                                     (51)
pressure ppw according to the following relation:
                                                                  can be obtained from the following rate of stress equation:
peff = ptot − ppw                                                 (45)           s
                                                                                     τ˙ g = 2 G γ˙                                                     (52)
   Assuming no porous ﬂow inside the soil, the pore water pressure
reads:                                                         where the dot ˙ denotes the time derivative, the subscript g refers to the
                                                                        granular material, and the superscripts  s refers to the elastic-solid
ppw = ρw g (z fs − z )                                              (46)                                                                   model, i.e. the solid state and G is the shear modulus deﬁned by:
Finally, eﬀective pressure can be obtained using (45):                      E
                                       G =
                                                                             2(1 + ν )                                                   (53)
              ⎛  sat     ⎞
peff = g (z i − z ) ⎜ρeq − ρw ⎟
              ⎝        ⎠                                       (47)     with E the Young’s modulus and ν the Poisson’s coeﬃcient. Note that,
                                                                               similarly to many authors in SPH literature (Gray et al., 2001; Randles
Nevertheless, getting peﬀfrom (47) requires to detect soil-water inter-                                                              and Libersky, 1996; Ulrich, 2013), Hooke’s law will be used to model
face   beforehand.  Such   a   detection   has  been   tested  by
                                                                        the deviatoric part of the stress tensor, while an equation of state will be
Manenti et al. (2011) but it seems to us that it can lead to inaccurate
                                                                   used to compute the pressure according to the weakly-compressible
result when the interface is highly deformed. In order to get eﬀective
                                                                  approach (see Section 2). As mentioned in Section 2.1, here the compressure without interface tracking, Fourtakas and Rogers (2016) pro-
                                                                                    pressibility is only a numerical trick to mimic the incompressible beposed to use a modiﬁed state equation. However, we found that this
                                                                         haviour. This is consistent with the assumption of an incompressible
method leads to a large overestimation of peﬀwhen the soil is sub-                                                                                    linear-elastic material (see Section 3.2). Note that such a state equation
merged. Furthermore, with such an approach, the well known WCSPH
                                                                     has already been successfully used to compute the pressure in a linear
pressure oscillations (Fatehi and Manzari, 2011) also impact the yield
                                                                                     elastic material in the SPH literature, e.g. in Gray et al. (2001) and
stress.
                                                                          Ulrich (2013).
    Therefore, we propose here another simple and reliable solution.
                                 sat                                                         In (52) we diﬀerentiated the solid state behaviour law (51) for the
Recall that ρw and ρeq  are constant. In addition, zi is the function that     following reason. It can be shown that the rate of stress (52) is not
gives the mixture-water interface above the point of interest, so it does
                                                                               objective, i.e. it is not independent on the frame of reference. In partinot depend on the vertical coordinate. As long as the water-mixture
                                                                                 cular, it is not invariant with respect to rigid-body rotation. Though, the
interface is not too much deformed, we can besides assume that the
                                                                         material constitutive equations should be frame indiﬀerent since the
interface varies linearly in the horizontal directions in the vicinity of
                                                                   mechanical response of a material must not depend on the observer.
the point of interest (this is the strongest assumption done in this rea-
                                                               Thus the dynamic quantities, such as the Cauchy stress tensor, are
soning). Thus, taking the Laplacian of (47) yields:
                                                                  frame invariant (Dienes, 1979; Gurtin, 1981). To circumvent this issue,
Δpeff = 0                                                       (48)     objective material time derivatives must be used. The most commonly
                                                                   used in computational mechanics is the Jaumann time derivative, detaking the Laplacian of (47) with suitable boundary conditions we get
                                                                    noted with a triangle Δ and deﬁned by:
the following system:
                                                                                 Δ
                                                                 σ = σ˙ + σ ω˙ − ω˙ σ                                            (54)
⎧ Δpeff ( r ) = 0      for   r ∈ Ω
⎪
 peff ( r ) = 0        for   r ∈ I                                     where ω˙ is the rotation rate tensor that is directly related to the rate of
⎨                                                                        rigid-body rotation within a material:
  ∂   peff⎪
                                                                                                          T   ∂    n  ( r ) = g · n    for   r ∈ S                                  (49)⎩                                                                                               ⎞                                                                         1 ⎛                ⎞                                                   ω˙ =    grad u −⎛⎜grad u ⎟                                                                                               ⎟with Ω the simulation domain, S the solid boundaries, n the inward         2 ⎜                                                                            ⎝         ⎝      ⎠                                                                                               ⎠                                    (55)
boundary normal and I the boundary corresponding to soil free-surface and soil-water interface (see Fig. 4).                                 Note that, when no rigid-body rotation occurs within the material,
    In the present model peﬀis only used to compute the yield stress. It     the Jaumann material derivative (54) is tantamount to the standard
cannot be used in the momentum conservation equation, because (49)     material time derivative. Applying (54) to the deviatoric stress tensor τ
is valid when the total pressure is approximately lithostatic, which is      yields:
not true in yielded regions. Thus, the total pressure calculated with the      Δ s
                                                                                      τ g = 2 G γ˙ + J˙                                                (56)state Eq. (3) is used to compute the pressure gradient in the momentum
conservation equation. This amounts to assume that the pore water                                                                      denoting   J˙ the Jaumann rate tensor deﬁned by:
pressure gradient can be neglected compared to the eﬀective pressure
gradient:                                                                           J˙ = τ gs ω˙ − ω˙ τ gs                                               (57)
∇ peff = ∇ ptot −∇ ppw ≈∇ ptot                                     (50)    The shear stress tensor ﬁnally reads:
Note that it would be possible to eliminate this approximation obser-      τ gs = 2 G γ + J                                                 (58)
ving that (49) can easily be adapted to compute the hydrostatic pore
water pressure. The pressure gradient in the momentum conservation    which is more relevant than the initial attempt (51).
equation could thus be computed from ptot − ppw. This was not tested in
this work.                                                                      3.4.2. Viscoplastic ﬂuid state
                                                                               In yielded regions, the material is modelled as a shear thinning li-
3.4. Shear stresses                                                         quid. Thus the viscous ﬂuid behaviour law (Stokes, 1851) is used to
                                                              model the shear stress:
3.4.1. Elastic solid state                                                                                                                          l
                                                                                     τ g = 2 ηeff γ˙                                                     (59)    In the present model, the solid state of the granular material is

                                                                       163

### Page 9

A. Ghaïtanellis et al.                                                                                                       Advances in Water Resources 111 (2018) 156–173

where the superscript l refers to the viscoplastic model, i.e. the liquid          πd g Gρg
state. In Ulrich’s (2013) original model, the eﬀective viscosity ηeﬀwas    ηy =                                                                                  0.163ν + 0.877                                             (66)
calculated according to a rheological law similar to the μ(I) rheology
(Jop et al., 2006). Here, we propose a diﬀerent law in order to be     We can now use the blending function proposed by Ulrich (2013):
consistent with the Drucker–Prager yield criterion. The eﬀective visc-                              q           q + 1
                                                                                                                                            γ                                                                                                                               γ                                                                                                                                                                                                                                                                                                                                                          ˙                                                                                                                                                                                                                                                                                                                                                                                             ˙                                                              ⎧                                                                                       ⎞                                                                                               ⎞                                                              ⎪ (q + 1) ⎛                                                            − q ⎛osity is thus deﬁned by:                                                                                                                                                                      if  γ˙ < γ˙y                                                                                                                                                                                                                                                                                                                                                         ˙                                                                                                                                                                                                                                                                                                                                                                                            ˙                                                                                                                                         y                                                                                                                                                       y                                                                                                ζ (γ˙) =                                                                                    ⎝ γ                                                                                       ⎠                                                                                             ⎝ γ                                                                                               ⎠
       τy                                                        ⎨
                                                                                                                                                           y                       (67)                                                                                                                           ⎩⎪ 1                                    if  γ˙ ≥ γ˙ηeff =
             γ˙                                                        (60)
                                                                    with q a positive integer. The solid-liquid transition sharpness can be
where τy is the yield stress calculated according to (43). Therefore, si-     adjusted varying q. Similarly to Ulrich (2013), we use q = 2. Note that
milarly to the  μ(I) rheology (Jop et  al., 2006; Revil-Baudard and                                                                        the blending function has the same role as Papanastasiou’s (1987)
Chauchat, 2013), the eﬀective viscosity is related to the friction within                                                                              regularization. It smooths the phase transition, which is more approthe granular material. However, here the friction coeﬃcient is constant                                                                              priate than a sharp interface for numerical modelling. The liquid-solid
in time since the internal friction ψ is a constant parameter in our                                                                            deviatoric stress tensor is thus given by:
model. It should be noted that (60) ensures the continuity of the shear
stress magnitude in the liquid-solid transition since we have:                 τ = ζ τ gl + (1 − ζ ) τ gs                                           (68)

   l     1      l       l                                                                                      It is important to note that the solid stresses in the soil should vanish
τg =
      2          τ g : τ g = ηeff γ˙ = τy                                      (61)    when the liquid state is reached. After ﬂowing, the grains have no
                                                        memory of their initial position. Thus, the strain tensor must be re-
                                                                                    initialized when ζ →1.
3.4.3. Solid-ﬂuid transition
                                                                         Furthermore, the phase transition is based on a condition on the
    Similarly  to  the  ideal  viscoplastic  models  (Mitsoulis,  2007)
                                                                                 strain rate magnitude γ˙ while the elastic solid stresses do not depend on
(Bingham, Herschel–Bulkley, Casson), the elastic-viscoplastic model
                                                                        the strain rate. Thus, there can be situations where the liquid state is not
(Ulrich, 2013) involves a discontinuous behaviour law. Thus, the liquid-
                                                                                    fully reached (γ˙ < γ˙y), but where the solid stress magnitude exceeds thesolid phase transition cannot solely be based on the yield stress. Con-
                                                                              yield stress (τ > τy). This happens when the failure is followed by very
sider the material is in the liquid state, then the shear stress magnitude
                                                                   slow deformations. Thus the strain rate  γ˙ remains smaller than  γ˙y butis always equal to τy, as shows in (61). Thus the material cannot become
                                                                        the strain keeps increasing. Consequently, the solid stress magnitude
solid. As a consequence, similarly to regularized viscoplastic models
                                                                              also keeps increasing and ends up exceeding the yield stress. However,
(Papanastasiou, 1987; Tanner and Milthorpe, 1983), the yield criterion
                                                                        the material is supposed to yield when the stress magnitude reaches the
is not based on a dynamic condition anymore (τ > τy), but on a kine-
                                                                              yield stress, so this never happens physically. To avoid unphysical
matic condition (γ˙ > γ˙y). Thus we need to build a new threshold ex-                                                                        overestimation of the solid stresses, we need to rescale the solid stress
pressed in terms of strain rate that still depends on the yield stress. To
                                                                          tensor so that the solid stress magnitude never exceeds the yield stress:
do so we write:
      τy                                                   ⎧ τ gss = τ gs     if  τgs ≤ τy
γ˙y =
     ηy                                                         (62)    ⎨                                                                                       τ gss =  ττy                                                                                                τ gs   if  τgs > τy                                          (69)                                                        ⎩
where ηy is a dynamic viscosity referred to as yield viscosity. Thus, (62)                      ss
                                                              where τg  denotes the rescaled deviatoric stress tensor. The ﬁnal formpoints out that the solid-liquid transition now depends on an additional
                                                                              of the liquid-solid deviatoric stress tensor is thus:
parameter ηy. Moreover, the yield viscosity not only determines the
threshold strain rate but also the maximum possible viscosity for the      τ = ζ τ gl + (1 − ζ ) τ gss                                           (70)
material in liquid state.
    In Ulrich (2013), the value of ηy is chosen in a trial and error ap-         Finally, in this model the mechanical behaviour of the soil only
proach, increasing incrementally  its value until obtaining satisfying    depends on elastic (E, ν) and granular (dg, ρg, ϕ, ψ) properties of the
result. Here we propose to ﬁnd a value based on the physical properties     material, especially through (43) and (66) that drive the liquid-solid
of the material. To do so, we ﬁrst consider the Deborah number De     transition.
which characterizes the ﬂuidity of a material under the ﬂow conditions
of a speciﬁc experiment:                                                  4. SPH implementation

         tR
De =                                                                          In SPH the continuum is sampled in a set of interpolation points F
         t C                                                        (63)                                                                    having a constant mass ma and referred to as particles. An SPH particle
where tC is the characteristic time scale of the experiment, and tR the    used to discretize a granular material continuum represents a small
stress relaxation time. For a granular material, assuming spherical    volume that contains a mixture of solid grains and surrounding ﬂuid.
grains, Sun and Wang (2013) proposed to use the characteristic time of    The equivalent density of the continuum is calculated from (42). The
Rayleigh waves propagating along a grain surface:                        present granular material model is implemented within the scope of the
                                                                       multi-phase SPH formulation presented in Section 2.2. First, let us de-
        πd g       ρg                                                            ﬁne (or recall) the following sets of SPH particles:tRG =
     0.162ν + 0.887 G                                         (64)
                               V  is  the  set  of  vertex  particles  (see USAW framework  inwith dg the grain diameter. On the other hand, during the transition, the     •
soil can be seen as a viscoelastic material. In that case, the Deborah        Section 2.2.2)
                                S  is the  set of boundary elements (see USAW framework innumber is calculated with a relaxation time deﬁned as:                 •
                                                                             Section 2.2.2)
     ηy                                                                                                         is                                                                                 the set of free                                                                                                          particles of granular material (mixture of grains                            MtRVE =                                                               (65)     •   G                                                                 and                                                                            surrounding                                                                                        ﬂuid)
                           W is the set of free particles of water   For a given material, the two relaxation time deﬁnitions should     •
                              F is the set of free particles of matter: F = M ∪ Wmatch. Therefore, combining (64) and (65) gives a deﬁnition of the     •
                                    I is the set of free particles of matter at the water-mixture interface:yield viscosity:                                                 •

                                                                       164

### Page 10

A. Ghaïtanellis et al.                                                                                                       Advances in Water Resources 111 (2018) 156–173

  I ⊂ F                                                             Numerically, this implies two iterative use of ﬁrst order SPH derivative
                                                                            operators. Indeed, (77) requires computing the strain rate tensor   γ˙
4.1. Eﬀective pressure                                                    using the SPH gradient of velocity. Then, (78) requires to take the SPH
                                                                      divergence of the shear stress tensor (Gray et al., 2001; Ulrich, 2013).
   To compute the eﬀective pressure peﬀ, we need to solve the Laplace     Thus, focusing on the ﬁrst term in (78) yields:
Eq. (49). Thus we use Morris’ Laplacian (18) to write the corresponding                                                T                                                                               (div(2 G γ ))                                                         ≈ G D a {( G b { u c } + ( G b { u c }) )}                      (79)                                                                                                        adiscrete equation:

               U                                                   But due to the collocated nature of SPH, applying iteratively ﬁrst order
∀ a ∈ (M ∖I )  La {1, peff, b } = 0                                  (71)
                                                                            derivative operators to get higher order derivatives leads to signiﬁcant
where (M ∖I ) refers to the set of SPH particles of mixture that are not     inaccuracy (see Section 2.2.3). This can be avoided observing that the
located at the interface. At the wall, the Neumann boundary conditions     shear strain tensor γ can be calculated from the displacement X instead
(49) must be  satisﬁed. Applying the technique used by Ferrand     of the time-integration of the strain rate tensor:
et al. (2013) to compute the dynamic pressure at the wall, we use a                                 T
Shepard-like interpolation of the eﬀective pressure ﬁeld:                      1 ⎛         ⎛      ⎞ ⎞                                                                         γ =    grad X + ⎜grad X ⎟
                                                                         2 ⎜                   ⎟                                                                            ⎝         ⎝      ⎠ ⎠                                   (80)
                           1                         ⎛              ∑∀ a ∈ (V ∪ S), peff, a =                              Vb (peff, b + Δρeq g ·( r a − r b )) wab ⎞                                                                        This deﬁnition of shear strain tensor (80) is particularly adapted to SPH            ∑b ∈ F                                                      s Vb wab                                    ∈ Fs                         ⎝ b                                                  ⎠                                                             whose Lagrangian characteristic gives a direct access to particle dis-
                                                               (72)     placement:
with (V ∪ S) the set of boundary elements and vertex particles. Be-    X (t ) = r (t ) − r 0                                               (81)
sides, a particular attention must be paid to the Dirichlet condition
imposed to soil particles located at the soil-water interface (second line     with r the particle position and r0 the initial particle position. Note that
of (49)). Indeed, the pressure due to their own weight must be taken     the initial particle position is reinitialised every time the material passes
into account, otherwise the yield stress (43) is always zero at interface    from liquid to solid state: after ﬂowing, a grain has no memory of its
particles:                                                                               initial position. Then the shear strain divergence can be obtained using
                                                                     Espanol and Revenga’s (2003) second order derivative operator LE de-
∀ a ∈ (M ∩ I )  peff, a = gδr Δρeq                                (73)    ﬁned in (20). Contrary to (9) and (18), Espanol and Revenga’s (2003)
                                                                    formula (20) is not an approximation of the Laplacian (see (21)).with (M ∩ I ) the set of SPH particles of mixture located at the inter-
                                                             Now, applying (20) to shear modulus G and displacement X we get:face, and δr the initial particle spacing (i.e. the particle size). Finally,
(71) is solved using a Jacobi solver initialized with the previous time     (div(2 G γ ))                                                         ≈ G L aE {1, X b }                                    (82)                                                                                                        a
step solution, thus ensuring low computational cost.
                                                  A similar treatment of the Jaumann term does not seem to be possible,
4.2. Shear forces                                                        so the shear force density f ﬁnally reads:

                                                                      ⎛   s ⎞         E                                                          l ⎞                                                               ≈⎛⎜div τ g ⎟4.2.1. Elastic solid force density                                         ⎜ f g ⎟ = G L a {1, X b } + D a { J b }
   To compute elastic forces, we ﬁrst need to compute the strain rate     ⎝  ⎠ a                          ⎝     ⎠ a                       (83)
tensor  γ˙ and the rotation rate tensor ω˙ :                             where the tensor J follows from an explicit time-integration of the
      1                     T    1                                Jaumann rate tensor (57): γ˙   =           ( G a { u b } + ( G a { u b }) ) −                                 Tr( G a { u b }) I  a                                                               (74)                                                                      (n )                              3      2
                                                                                                                                                (n + 1)         (n )     ⎛   s               s ⎞
                                                                                     J   = J  + Δt ⎜ τ g ω˙ − ω˙ τ g ⎟      1
ω˙ a =           ( G a { u b } + ( G a { u b })T )                                                           ⎝           ⎠                                (84)
      2                                                        (75)                                              s                                                                The force density  f   is rescaled afterwards according to (69) (here
                                                                                                                                  g
where the multi-phase anti-symmetric gradient based on (16) is used    we omit the SPH particle labels for the sake of clarity):
here:
                                                        ⎧ f gss =  f gs      if  τgs ≤ τy
        V                a
                                                                                                                                       τy      ∑G a { u b } = −                    θb ( u a − u b ) ⊗∇ wab                        ⎨                                                                                                                       f                                                                                                                                    f                                                                                                                               ss =                                                                                                                                             s   if  τgs > τy          Γa                                                                                                                                       τ                                                                                                        g                                                                                                                   g                   b ∈ (          F∪ V)                                                                                                                                                                                                                                    gs                                                                                                                                       (85)                                                        ⎩
         Va     1      +  ∑     ( u a − u s ) ⊗∇ Γas                                  Note that the latter rescaling is not tantamount to (69). Indeed, here
          Γa  s ∈ S Vs                                          (76)    we rescale forces instead of stresses, which means that the following
                                                                    approximation is done:with ⊗denoting the tensor product. Note that the anti-symmetric
gradient (76) is used instead of (14) for more accuracy. It should also be
                                                                        ⎛ τy    s ⎞    τy    ⎛   s ⎞
reminded that the trace of the velocity gradient should be zero for an     div ⎜  s τ g ⎟ ≈    s div ⎜ τ g ⎟
                                                                                          τg   ⎠    τg    ⎝  ⎠                                        (86)incompressible ﬂuid. But within the scope of WCSPH, we have to re-       ⎝
move the trace from the strain rate tensor in (74), to ensure that the        This is mandatory when using (82) instead of (79) because the stress
deviatoric stress tensor τ is really traceless. The shear stress tensor then     tensor τgs is not directly used to compute the forces. Although it will be
follows from an explicit time-integration of the Jaumann rate of shear     seen that using (82) improves the computation of elastic forces (see
stress (56):                                                               Section 4.3), it would be necessary to evaluate the eﬀect of the latter
τ gs = 2 G γ˙ + τ ω˙ − ω˙ τ                                        (77)     approximation on the model accuracy to ascertain whether (82)  is
                                                                            globally better. Unfortunately, such an investigation has not been carwhere the overbar indicates explicit time integration. Then, the elastic     ried out in the scope of this work.
solid force density could be simply computed from the divergence of the
deviatoric stress tensor:                                                        4.2.2. Viscous force density
        s                                                   When the material is in the viscoplastic liquid state, the force dendiv τ g = div(2 G γ ) + div J                                      (78)      sity is given by:

                                                                       165

### Page 11

A. Ghaïtanellis et al.                                                                                                       Advances in Water Resources 111 (2018) 156–173

                                                                                                     It should be noted that, since there is no contribution of the water⎛            l ⎞
⎜div τ g ⎟ = (div(2 ηeff γ˙)) a                                             neighbour the elastic-solid term in (89), the action-reaction principle is
⎝     ⎠ a                                                       (87)
                                                                      not respected when ζ < 1. Indeed, from the two latter equations, we
   Thus, it is computed applying (20) to the eﬀective viscosity ηeﬀand    can see that we only have:
the velocity u:
                                                                                                    1 ⎛    l ⎞                                                                                                                                                                              f                                                                                                           ⎟
                                                                                                                                                       g                                                           ∀ a ∈ M, b ∈ W      ( f w ) b → a = − ζ ⎜⎛      l ⎞                                                                                                       ⎝                                                                                                           ⎠ a → b                     (93)⎜ f
   g   ⎟ = L aE { ηeff, b , u b } ≈ (div(2 ηeff γ˙)) a
⎝  ⎠ a                                                          (88)
                                                                           Nevertheless, the strain rate of granular material particles close to the
Here again, Espanol and Revenga’s (2003) operator is used instead of     interface is usually high, due to the water particles velocity that conMorris’ viscous term. This is due to the fact that the transposed velocity     tribute (74). Therefore, for particles in M having neighbours in W, we
gradient in (40) cannot be neglected when modelling non-Newtonian     usually have ζ →1 so the action-reaction principle is respected most of
ﬂuids. The eﬀective viscosity is computed according to (60) that de-     the time. Despite that, (93) remains a weakness of the present model,
pends on the yield stress (43) and the mean scalar rate of strain γ˙ (39).    and further investigation should be carried out to improve this aspect.
                                                                  As a consequence of (91) and (92), the suspended sediment and
4.2.3. Blending of shear forces                                         water only exert viscous forces on each other. When the sediment re-
   The continuous transition between solid and liquid state is ensured      settles, viscoplastic and elastic forces exert between sediment SPH
by the blending function ζ (67) deﬁned in Section 3.4.3 (here again we      particles.
omit the SPH particle labels):                                         As regards erosion, the water-sediment interaction could be im-
                     l                    s                                               proved taking account for turbulence. In the present model, the shear
 f g = ζ  f g + (1 − ζ ) f g                                          (89)      stress at the water-sediment interface depends on the shear rate, the
               s                  l                                                dynamic viscosity of water, and the local viscoplastic viscosity of thewhere  f  and  f  are computed respectively through (83) and (87).
            g          g                                                      sediment. Physically, erosion results from the viscous and turbulent
Note that, here the blending applies to the forces instead of the stresses,
                                                                        shear stresses exerted by water on the solid grains of sediment. Thus, it
even though (89) is not tantamount to (67) since ζ in not constant in
                                                      may be possible to use and SPH form of the standard k − ϵ model in the
space. However, the blending being a numerical trick to ensure a
                                                                   water phase (Ferrand et al., 2013), treating the water-sediment intercontinuous transition, (89) can be used too. A simple way of getting
                                                                            face as a solid wall. The stress exerted on the sediment SPH particles
(67) back would be to use:
                                                             would then be deduced from the action-reaction principle. That way,
                                                                        the bottom shear stress would not depend on the rheological law used⎛  ⎞      E                    E
⎜ f g ⎟ = L a { ζb ηeff, b , u b } + G L a {(1 − ζb ), X b } + D a {(1 − ζb ) J b }            within the granular material. This approach has not been tested here.
⎝  ⎠ a                                                          (90)

   However, the diﬀerences between (89) and (90) were not  in-     Conditions at wall–granular-material interface. Wall boundary conditions
vestigated in this work.                                           must enforced on both the viscoplastic term (88) and the elastic solid
                                                                 term (83). With regard to the former, the method proposed by Ferrand
4.2.4. Boundary conditions                                                     et al. (2013) for the viscous wall condition is simply applied. As regards
4.2.4.1. Conditions at water–granular-material interface. In the frame of     the elastic solid term, the displacement of vertex V and boundary
the multi-phase formulation presented in Section 2.2, the density and     elements S et imposed to zero. We recall Espanol and Revenga’s (2003)
the pressure ﬁelds do not require any  special treatment  for the    boundary term:
interaction of SPH particles of water W and of granular material M .
                                                                                 E ,bound           1The density is computed according to (13) from all the neighbouring    L a       {1, X b } = − ∑  (∇ X a + ∇ X s )· ∇ Γas
                                                                           Γa  s ∈ S                                      (94)particles, irrespective of the phase (W or M ) they belong to. Besides
that, both phases have a pressure ﬁeld, so the pressure gradient is                                                                    Using a Taylor expansion, we can write:
simply computed with the multi-phase gradient (14).
    In regard to the shear forces, the two phases only interact though       (∇ X ) a · e as ≈ X aras− X s
viscous eﬀects for which Espanol and Revenga’s (2003) viscous term                  X a − X s
                                                                                                   (∇ X ) s · e as ≈     ras                                                (95)(20) is used in the two phases. In water, the granular material neighbours are seen as liquid particles having a viscosity ηeﬀ. Thus the force
                                                                      Thus, imposing X s = 0, Espanol and Revenga’s (2003) boundary termdensity exerted by a particle b of granular material M on a particle a of
                                                                        (94) can be approximated as:
water W reads:
                                                                 ∇                                                                                      2                                                                                                                                                                            ·                                                                                                                            r as                                                                                       Γas
                                              a                                                       b                                ηw,                                   ηeff,                                                                        X a                                                            L aE ,bound {1, X b } ≈−                                   ∑                                                                                                                                             2                                                     [(d + 2)(( u a − u b )·                                                                           Γ                                                                                                                              r                                                                                                                                                            as                                                                                                                                       (96)                                                                                                                   a  s                                                                                          ∈ S                        +                                             a                                                         b∀ a ∈ W, b ∈ M, ( f w ) b → a = θb Vb ηw,                                    ηeff,
                            ∇wab                                                                                 · r ab                 The latter approximation is not exact because ∇Γas is a vector oriented                            e ab ) e ab + ( u a − u b )]                                                                 2
                                                         rab                      along the inward wall normal vector, not along ras.
                                                               (91)        Then, we assume a locally uniform distribution of J at the walls
                                                                                    (recall J is the time anti-derivative of the Jaumann tensor, as deﬁned in
where the subscript w refers to the water and d is the space dimension.
                                                                         Section 3.4.1). The corresponding boundary term reads:
On the other hand, the viscous force density exerted by the water
particle on the granular material contribute to the viscoplastic term in        bound     Va     1
                                                D a      { J b } =  ∑     ( J a − J s )· ∇ Γas
(89) through:                                                            Γa  s ∈ S Vs                                         (97)

                                                 a                                                           b                                                             The                                                                              present                                                                              assumption                                  ηw,                                      ηeff,                        ⎡                                                 l                 ⎛                     ⎞                                                                                                        yields J s = J a , hence:                               f                 = ζ                     ⎟∀ a ∈ M, b ∈ W, ⎜                            θb Vb                                                         [(d + 2)(( u a − u b )·                            g                        ⎢                          +                                                a                                                             b                                 ηw,                                       ηeff,                 ⎝                     ⎠ a → b                        ⎣                                                                                0                                                D abound                                                                                                                                       (98)                                                                                                                      { J b } =
                              ∇ wab · r ab ⎤
                             e ab )( − e ab ) − ( u a − u b )]                                                                                                            vertex                                                                                                                               particles                                                                                                                                                        (                                                                                                                                         the                                                                                                                    b ∈                                                   V), thus                                                                                                                                 b = J a for                                                               rab2   ⎥⎦               contributionSimilarly, weofassumevertex particlesJ                                                                                                             to the                                                                                                    volumic                                                                                                          term                                                                                                                                   also                                                                                                                                    vanishes.                                                                                                                   The
                                                               (92)     divergence of Jaumann rate ﬁnally simpliﬁes to:

                                                                       166

### Page 12

A. Ghaïtanellis et al.                                                                                                       Advances in Water Resources 111 (2018) 156–173

        Va                                                        parameters were determined experimentally by Bui et al. (2008) and
D a { J b } = − ∑ θb ( J a − J b )· ∇ wab
         Γa b ∈ F                                              (99)     are summarized in Table 2.
                                                                The simulations were performed using approximately 20,000 parwhere the boundary terms vanished and the sum now only extends to      ticles of soil and 1400 vertex and boundary elements, with an initial
free particles F .                                                               particle spacing of δr = 0.001 m. In all simulations, the ratio between δr
                                                              and the smoothing length h is δr / h = 2. The numerical speed of sound
4.3. Validation of elastic forces computation                          was set to 10 m · s−1.
                                                                                      Fig. 7 shows the simulation result at four physical times. We see
   This test case is a simple numerical experiment that aims at testing     that (49) leads to an accurate calculation of the yield stress, free of the
the improvement resulting from the computation of solid forces from     typical SPH numerical oscillations of pressure. Besides, almost no
the displacement ﬁeld, i.e. using (82) instead of (79) (see Section 4.2.1    deformation occurs between t = 1.5 s and t = 2.0 s, thus demonstrating
for a detailed description of the method). The quantity of interest is     that the model is able to represent the solid state even after a large
thus:                                                               time  compared  to  the  characteristic  time  of  the  experiment
                             T                            H / g = 0.1 s. In Fig. 8, the surface conﬁguration at the end of the
       ⎛                  ⎛                         ⎞ ⎞                                         experiment, as well as the failure line, are compared with numerical f = div         grad X + ⎜                   grad X ⎟       ⎜                   ⎟
       ⎝         ⎝      ⎠ ⎠                                (100)     results obtained at 1.5 s. Experimentally, the failure line is deﬁned as
                                                                       the line delimiting the non-deformed region. Numerically, we deﬁne
This is usually computed from the velocity ﬁeld, integrating the strain                                                                       the non-deformed region as the area where the displacement magnirate tensor  γ˙ and using (79):                                                                    tude is less than the grain size, i.e. 1.5 mm. Both surface conﬁguration

 f  U = D a {2 γ˙ n + Δt ( G b { u c } + ( G b { u c })T ) n }                     (101)    and failure line are well predicted by the model although we assume  a
                                                                           that the granular medium is incompressible while it is not a valid
   The proposed alternative consists in calculating  f from the dis-     hypothesis for dry  soils. Thus, compressible eﬀects are probably
placement ﬁeld X using Espanol and Revenga’s (2003) second order     negligible in that case.
diﬀerential operator (20):                                             Note that we observed signiﬁcant numerical noise when the solid
  X       E                                                                     state is reached. When its velocity tends to zero, the material should
 f   a = L a {1; X b }                                            (102)                                                                    reach a steady motionless state and behave like a pure elastic solid. In
   In order to compare the two approaches accuracy, we consider the     the present model, we thus expect the shear forces to be solely calperiodic case of 2D Taylor–Green vortices for which the analytical ve-     culated from the elastic solid model, i.e. the blending function should
locity ﬁeld is known:                                              be homogeneously equal to zero within the material. However, be-
                                                                    cause of numerical noise, some strain rate is artiﬁcially produced.
                                                                     Consequently,                                                                                      the sediment                                                                                                                                      is                                                                                                                in                                                                                              an unstable                                                                                                                           equilibrium,                                                                                                                                    con-           ⎛        − cos ( 2πxL ) sin ( 2πyL ) ⎞
u (x , y , t ) =                                                                        tinuously oscillating                                                                                between a                                                                                                                 solid                                                                                                                       state                                                                                                and a highly                                                                                                                               viscous liquid           ⎜                             ⎟ exp ⎜⎛ − 2ηt ⎞⎟
           ⎜                                                                                    state. This emphasizes the fact that the blending approach (70) has a
           ⎝               sin ( 2πxL ) cos ( 2πyL ) ⎟⎠   ⎝  ρ  ⎠                    (103)
                                                                               stabilization eﬀect: contrary to Bui et al. (2008), the tensile instability
In order to quantify the error due to the SPH operators only, we con-      is not directly observed. However, it still leads to numerical noise
sider a Cartesian grid of ﬁxed SPH particles. Their velocity and corre-    when the material is in the solid state. To circumvent this issue, the
sponding theoretical displacement are imposed according to (103). The     artiﬁcial stress method (Gray et al., 2001) could be tested in a future
simulation is carried out for L = 1, η / ρ = 0.1 m2 · s−2 and L / δr = 100.    work. This technique was developed to remove the tensile instability
After 10 s of physical time, expressions (101) and (102) are evaluated     that may be partly responsible for the above mentioned numerical
and compared to the exact value (100) obtained with Mathematica     noise.
(Wolfram Research, Inc., 2017). The comparison is performed calculating the error deﬁned by:                                                6. Simulation of 2D dam-break wave on movable beds

                                 2
       ⎛       ⎜ f          SPH − f (x a , ya ) ⎞⎟                                           The present model was also assessed to a case of dam-break wave            a
       ⎝               ⎠                                              propagating over a saturated granular bed. This study is based on theEa =

       N           1 ∑∈a F f (x a , ya )) 2                                    (104)     small-scale experiments carried out by Spinewine and Zech (2007). The
                                                                     experiments were performed in a ﬂume being 25 cm wide and 6 m long.
where  f         SPH is the quantity f calculated at particle a with SPH using    The initial conﬁguration of the experiment is illustrated in Fig. 9. The          a
either (101) or (102), f(xa, ya) is the theoretical values calculated with    dam-break is initiated by the sudden lowering of a gate that is not taken
Mathematica at the particle a position (xa, ya), and N  is the total     into account in the simulation. Two materials (sand and PVC) are tested
number of SPH particles. Results are plotted in Fig. 5 that shows the     to investigate the capability of the model to exhibit diﬀerent behaviours
error we got for both approaches. We clearly see that the error is much     with respect to diﬀerent materials. The physical parameters of the
larger using (79), with a maximum error twice the one obtained using     materials are summarized in Table 3. Note that experimental Young’s
(82). This demonstrates the accuracy gain due to the use of a second    modulus and Poisson’s coeﬃcient were available for these materials.
order operator instead of two iterative uses of a ﬁrst order operator     Consequently, we used generic values from Ulrich (2013) for similar
within the scope of collocated methods.                                      cases. The ﬁrst simulations were carried out setting a particle spacing of
                                                                               δr = 0.002 m, resulting in 525,000 particles of water, 150,000 particles
5. Simulation of 2D soil collapse                                         of saturated soil and 13,000 particles vertex and boundary particles.
                                                             The numerical speed of sound and isentropic coeﬃcient are set iden-
   To validate the present model, a simulation of an experimental 2-D      tically for the saturated granular material and the water, that  is
collapse of dry soil is ﬁrst carried out. The experiment was conducted     c 0 = 37 m · s−1 and ξ = 7. Rhie and Chow’s (1983) chequerboard corby Bui et al. (2008) and the experimental set-up is illustrated in Fig. 6.     rection (27) was applied with a coeﬃcient of ΛRC = 1.0, and no backThe material is composed of aluminium bars of diameter 1 mm and    ground pressure was used.
1.5 mm, length 50 mm and density 2650 kg · m−3. The material porosity         Fig. 10 shows a comparison of the experiment and the SPH simuis not speciﬁed by the authors so we approximate it using the highest     lation carried out for the sand for δr = 2d g. We can see that the dycompact binary circle packing, leading to ϕ ≈0.1. All other physical    namics of the ﬂow is qualitatively well reproduced by the model.

                                                                       167

### Page 13

A. Ghaïtanellis et al.                                                                                                       Advances in Water Resources 111 (2018) 156–173

                                                                                                                                   Fig. 5. Taylor–Green vortices – error on second order
                                                                                                                                  derivative of the displacement ﬁeld in (a) calculated
                                                                                                             from strain rate tensor integration with (79) and in (b)
                                                                                                                                calculated from displacement with (82). Results ob-
                                                                                                                             tained for L / δr = 100 m and η / ρ = 0.1 m2 · s−2 after 10
                                                                                                                                                 s of physical time.

   Fig. 6. 2D soil collapse – experimental set-up from Bui et al.’s (2008) experiments.

                                                                                                Fig. 8. 2D soil collapse – surface conﬁguration and failure line at t = 1.5 s. Comparison of
Table 2                                                                                   the present model to Bui et al.’s (2008) experiments.
2D soil collapse – physical parameters of the granular materials (aluminium bars).

            ρg [kg/m3]      dg [mm]     ϕ [1]     E [Pa]        ν [1]     ψ [o]

  Al.     2650             1.0 − 1.5      0.10       8.4 · 105      0.3        19.6

Total eroded mass of soil –. First, let us focus on the total mass of
sediments that reaches the downstream ﬂume outlet. To do so, we
deﬁne the relative error on the total eroded mass with respect to the
experimental value:
                                                                                                Fig. 9. Dam-break wave on movable beds – experimental set-up of Spinewine and Zech’s
   m SPH − m exp                                                                 (2007) experiments.
Er =
     m exp                                               (105)

    Fig. 11 shows the error Er as a function of the ratio δr/dg (particle
size/grain diameter). We can see that sand and PVC simulations exhibit     Table 3
                                                                              Dam-break wave on movable beds – physical parameters of the granular materials.
similar behaviours although they have diﬀerent grain sizes:
  PVC       Sand                                                                                              ρg [kg/m3]      dg [mm]    ϕ [1]     E [Pa]       ν [1]     ψ [o]
d g  ≈ 2 d g                                                  (106)
                                                                                Sand     2683           1.89         0.47       8.0 · 105      0.3      30
   For the two materials, decreasing the SPH particle size improves the                                                                     PVC     1580           3.90         0.42       8.0 · 105      0.3      38
result until the critical value δr = dg. Below this threshold, the soil
model is no more valid and erosion is dramatically overestimated. This
discretization limitation may be due to the fact that SPH particles are

                                                                                                                                              Fig. 7. 2D soil collapse – simulation results
                                                                                                                                                   at t = 0.1 s, t = 0.25 s, t = 1.5 s and 2.0 s.

                                                                       168

### Page 14

A. Ghaïtanellis et al.                                                                                                       Advances in Water Resources 111 (2018) 156–173

                                                                                                                                             Fig. 10. Dam-break wave on movable beds
                                                                                                                            – comparison of experimental and numer-
                                                                                                                                                              ical results, with sand at time t = 250 ms,
                                                                                                                                                                                                               t = 500 ms and 750 ms, for δr = 2d g.

                                                                  supposed to represent a macroscopic volume of the saturated soil.
                                                                The continuum hypothesis amounts to assume that the physical
                                                                                 state of a heterogeneous system (e.g. a multi-phase system involving
                                                                  ﬂuid and solid discrete particles) can be described by continuous ﬁeld
                                                                               variables, whose space and time dependence is represented by diﬀer-
                                                                                 ential equations for mass, momentum and energy balances (Baveye and
                                                                              Sposito, 1984). Such a description  is based on the concept of re-
                                                                           presentative elementary volume over which a local volume average
                                                                        allows “a transition from microscopic physical properties to macroscopic
                                                                          ﬁeld variables as well as from microscopic diﬀerential balance laws to
                                                                         macroscopic diﬀerential balance laws” (Baveye and Sposito, 1984). The
                                                                     continuous ﬁelds result from the microscopic properties of the system,
                                                                     but they are macroscopic quantities that do not have any physical sense
                                                                                at the microscopic scale. Thus the representative elementary volume
                                                                     should be small enough (with regards to the problem dimensions) to be
                                                               an approximation of a mathematical neighbourhood of its centre, but
                                                                            large enough to enclose many  spatial heterogeneity (Baveye and
                                                                              Sposito, 1984). As an example, the derivation of Darcy’s equations, that
                                                                           describes ﬂows in porous media, requires that the characteristic length
Fig. 11. Dam-break wave on movable beds – error on eroded mass as a function of the
particle size/grain diameter ratio.                                                  of the pores is smaller than the characteristic length of the averaging

                                                                       169

### Page 15

A. Ghaïtanellis et al.                                                                                                       Advances in Water Resources 111 (2018) 156–173

                                                                                                                            Fig. 12. Dam-break wave on movable beds – comparison of
                                                                                                                 experimental  (dotted  lines) and numerical  results  (solid
                                                                                                                                             lines), with sand at time t = 250 ms, t = 500 ms, t = 750 ms,
                                                                                                                                                                                      t = 1000 ms and t = 1250 ms, for δr = 2d g. (For interpretation
                                                                                                                             of the references to colour in the text, the reader is referred to
                                                                                                                    the web version of this article.)

volume (Whitaker, 1986). Using SPH particles or mesh cells smaller     Young’s modulus) of the granular materials are very diﬀerent from
than the pores (or the grains in our case) amounts to using averaging      elastic  properties  of  individual  grains  they  are  composed  of
volumes that do not satisfy this constraint. Thus, the numerical solution    Guan et al. (2012). Consequently, a particular attention must be paid to
approaches a theoretical solution that is not a correct description of the     the discretization limitations when modelling granular materials with
physical problem. Issues related to the length scales constraints and the    SPH. This might be avoided using alternative rheological laws or difcontinuum hypothesis have been addressed in the frame of porous     ferent elastic properties when δr < < dg. On the other hand, Fig. 11
media ﬂows (Baveye and Sposito, 1984; Whitaker, 1986). In the scope     clearly shows that a sub-particle model would be necessary to correctly
of multi-phase ﬂows, Gómez and Milioli (2005) claim that “a minimum     predict erosion when δr > > dg. Within the scope of the present elasticlimit should be enforced on numerical spatial mesh sizes having in view the     viscoplastic model, the problem depends on 10 physical parameters: the
validity of the average Eulerian continuum equations for the solid phase”.     density ρw and dynamic viscosity of water ηw, the grain density ρg, the
According to Clemiņš (1988), using mesh cells whose size does not     granular material porosity ϕ, the internal friction angle ψ, the Young’s
satisfy the minimum size condition may lead to non-physical ﬂuctua-    modulus E, the Poisson’s coeﬃcient, the grain size dg, the gravity actions of the resolved ﬁelds. In that case it is necessary to average the     celeration g and a characteristic length of the problem L. Applying the
result on a larger volume to get relevant physical quantities. Extending    Buckingham π theorem, we obtain 7 dimensionless parameters that
this conclusion to Lagrangian methods seems to raise additional issues.     characterize this problem:
Indeed, if a non-physical ﬂuctuation of the velocity ﬁeld occurs within
an SPH particle, the particle moves and the simulation is irreversibly         ρg                   g 1/2 L3/2 ρw  d g       E
                                                          ϕ ,           ,  ψ ,   ν ,   Re =                   ,      ,
aﬀected. Contrary to mesh-based methods, it is not possible to average         ρw                    ηw     L    d g (ρg − ρw ) g        (107)
the ﬂuctuating ﬁelds afterwards to get relevant physical quantities.
   Therefore, an SPH particle should not be smaller than the sediment     In a way, using δr < dg amounts to setting d g′ ≈ δr . We would then have
grain size, otherwise the model would lead to deformations that do not    SPH particles being solid matter while other are viscoplastic. The latter
occur in the real material, and overestimated strain rates. This may be    two dimensionless numbers are thus modiﬁed as:
partly due to the fact that the macroscopic elastic properties  (e.g.

                                                                       170

### Page 16

A. Ghaïtanellis et al.                                                                                                       Advances in Water Resources 111 (2018) 156–173

                                                                                                                            Fig. 13. Dam-break wave on movable beds – comparison of
                                                                                                                 experimental  (dotted  lines) and numerical  results  (solid
                                                                                                                                             lines), with PVC at time t = 250 ms, t = 500 ms, t = 750 ms,
                                                                                                                                                                                      t = 1000 ms and t = 1250 ms, for δr = 2d g.

δr       E                                                           motionless sediment (black), the water-sediment interface (blue) and    ,
L     δr (ρg − ρw ) g                                           (108)     the water free-surface (red) for the sand. The interface between the
                                                                       motionless and the moving sediment  is deﬁned in  line with the
Regarding the ﬁrst one, the decrease of the grain size has probably no     experimental detection method. In the experiment, a camera set to
inﬂuence on the results since we have δr/L < < 1 as well as dg/    200 images per second (i.e. one image every Δt = 5 ms) was used to
L < < 1. However we see that the second dimensionless number is     acquire image sequences of the ﬂow. Every image was then subtracted
signiﬁcantly changed. Recovering its physical value can be done by     to the preceding image. The black region in the resulting image was
changing Young’s modulus: when δr = αdg with α < 1, we would set    deﬁned as the motionless region. Given that the spatial resolution for
the Young’s modulus to αE. However, this was not tested in the scope of    one pixel is approximately Δx = 1 mm (Spinewine and Zech, 2007), we
this work.                                                     deﬁne a threshold velocity below which the sediment SPH particle is
   In Fig. 11 we see that an optimum seems to be achieved for δr ∈[dg;     considered as motionless:
3dg] for both sand and PVC. However,  it must be pointed out that
                                                         Δx
δr > 3dg is a coarse spatial discretization for this problem ( ≈22 par-    u motion =
                                                         Δt                                                 (109)ticles on the water height). Thus, the error due to the hydrodynamics
solver is also probably partly responsible on the erosion overestimation.
                                                                      Continuous lines represent the numerical results while experimental
Note that erosion is overestimated for almost all conﬁgurations. Thus,
                                                                      data are represented as dotted lines. A general good agreement is obat worst, simulations give a superior limit of the real erosion.
                                                                         tained for the sand bed. Interfaces as well as free-surface and water
   In the following, results are presented for δr ≈2dg, e.g. for the sand,                                                                              front are well predicted for the ﬁve considered times. Fig. 14 shows a
simulations were carried out setting a particle spacing of δr = 0.004 m,
                                                                  comparison of ﬂow interfaces for δr = 2d g (solid lines) and δr = d g /2
resulting in 130,000 particles of water, 38,000 particles of saturated
                                                                    (dashed lines). We clearly see that having SPH particles smaller that the
soil and 3000 particles vertex and boundary particles.
                                                                          grain size (dashed lines) leads to overestimated bed deformations while
                                                                        the results obtained for δr = 2d g (Figs. 12 and 14) match the experiFlows interfaces –  . Fig. 12 shows the interface between moving and    mental data.

                                                                       171

### Page 17

A. Ghaïtanellis et al.                                                                                                       Advances in Water Resources 111 (2018) 156–173

                                                                          turbulent viscosity of water near the soil-water interface. Moreover, a
                                                                              sub-particle model could improve erosion prediction when the particle
                                                                                  size is large compared to the grain size. More radically, uniﬁed solid-
                                                                               liquid models (Peshkov and Romenski, 2016) could be considered to
                                                              model granular ﬂows in SPH.

                                                                 References

                                                                                      Armanini, A., Capart, H., Fraccarollo, L., Larcher, M., 2005. Rheological stratiﬁcation in
                                                                                           experimental free-surface ﬂows of granular–liquid mixtures. J. Fluid Mech. 532,
                                                                                     269–319.
                                                                                      Baveye, P., Sposito, G., 1984. The operational signiﬁcance of the continuum hypothesis in
                                                                                              the theory of water movement through soils and aquifers. Water Resour. Res. 20 (5),
                                                                                     521–530.
                                                                                              Beverly, C., Tanner, R., 1992. Numerical analysis of three-dimensional Bingham plastic
Fig. 14. Dam-break wave on movable beds – comparison of experimental (dotted lines)        ﬂow. J. Non-Newton Fluid Mech. 42 (1), 85–115.
and numerical results, with sand at time t = 500 ms, for δr = d g /2 (dashed lines) and     Bingham, E., 1917. An Investigation of the Laws of Plastic Flow. 13 Govt. Print. Oﬀ.
δr = 2d g (solid lines).                                                                            Brezzi, F., Pitkäranta, J., 1984. On the stabilization of ﬁnite element approximations of
                                                                                              the Stokes equations. Eﬃcient Solutions of Elliptic Systems. Springer, pp. 11–19.
                                                                                                Bui, H., Fukagawa, R., Sako, K., Ohno, S., 2008. Lagrangian meshfree particles method
   For the PVC bed, Fig. 13 shows that the initial liquefaction is slightly         (SPH) for large deformation and failure ﬂows of geomaterial using elastic–plastic soil
underestimated. In particular, the experimental bed proﬁle  (i.e. the           constitutive model. Int. J. Numer. Anal. Methods Geomech. 32 (12), 1537–1570.
                                                                                     Campbell, C., 1990. Rapid granular ﬂows. Annu. Rev. Fluid Mech. 22 (1), 57–90.
black dotted line) at t = 250 ms is deeper than the numerical one. This      Capone, T., Panizzo, A., Monaghan, J., 2010. SPH modelling of water waves generated by
may be due to the fact that the lowering of a gate is not taken into         submarine landslides. J. Hydraul. Res. 48 (S1), 80–84.
account in the simulation. Moreover, there is a large uncertainty on      Clemiņš, A., 1988. Representation of two-phase ﬂows by volume averaging. Int. J.
                                                                                          Multiphase Flow 14 (1), 81–90.
PVC beds elastic properties. Indeed, elastic properties of sand are      Colagrossi, A., Landrini, M., 2003. Numerical simulation of interfacial ﬂows by smoothed
widely used in soil mechanics and a lot of experimental data is avail-           particle hydrodynamics. J. Comput. Phys. 191 (2), 448–475.
able. We did not ﬁnd such data for PVC soils, hence the diﬀerences      Craig, R., 1983. Eﬀective Stress. Springer US, Boston, MA, pp. 84–106. doi:http://dx.doi.
                                                                                         org/10.1007/978-1-4899-3474-1_3.
between numerical and experimental results. Nevertheless, simulations      Davis, R., Selvadurai, A., 2005. Plasticity and Geomechanics. Cambridge University Press.
give good results for the PVC too. In addition, they exhibit very dif-      Dienes, J., 1979. On the analysis of rotation and stress rate in deforming bodies. Acta
ferent behaviours for sand and PVC, demonstrating the capability of the         Mech. 32 (4), 217–232.
                                                                                         Drucker, D., Prager, W., 1952. Soil mechanics and plastic analysis or limit design. Q.
model to account for diﬀerent material properties.                                 Appl. Math. 10 (2), 157–165.
                                                                                           Espanol, P., Revenga, M., 2003. Smoothed dissipative particle dynamics. Phys. Rev. E 67
                                                                                                               (2), 026705.
7. Conclusion                                                                              Fatehi, R., Manzari, M., 2011. A remedy for numerical oscillations in weakly compressible
                                                                                  smoothed particle hydrodynamics. Int. J. Numer. Methods Fluids 67 (9), 1100–1114.
                                                                                           Ferrand, M., Laurence, D., Rogers, B., Violeau, D., 2010. Improved time scheme in-
    In this work, Ulrich’s (2013) elastic-viscoplastic model was im-           tegration approach for dealing with semi-analytical wall boundary conditions in
plemented and improves in the frame of a SPH multi-phase formulation.        SPARTACUS2D. Proceedings of the 5th International SPHERIC Workshop. pp.
Hu and Adams’s (2006) multi-phase formulation was adapted to USAW         98–105.
                                                                                           Ferrand, M., Laurence, D., Rogers, B., Violeau, D., Kassiotis, C., 2013. Uniﬁed semiboundary conditions and Vila’s (1999) continuity equation is used so           analytical wall boundary conditions for inviscid, laminar or turbulent ﬂows in the
that the model can handle free-surface ﬂows. The soil is treated as a          meshless SPH method. Int. J. Numer. Methods Fluids 71 (4), 446–472.
continuum whose behaviour depends on a yield stress determined ac-      Fourtakas, G., Rogers, B., 2016. Modelling multi-phase liquid-sediment scour and re-
                                                                                            suspension induced by rapid ﬂows using smoothed particle hydrodynamics (SPH)
cording to Drucker–Prager’s criterion. In unyielded regions, the shear          accelerated with a graphics processing unit (GPU). Adv. Water Resour. 92, 186–199.
stress is calculated in line with linear elastic theory. In yielded regions,       Ghaitanellis, A., Violeau, D., Leroy, A., Joly, A., Ferrand, M., 2015. Application of the
a shear thinning rheological law is used and the transitions between         uniﬁed semi-analytical wall boundary conditions to multi-phase SPH. Proceedings of
                                                                                              the 10th International SPHERIC Workshop. pp. 333–340.
solid and liquid states are ensured by a blending function driven by the     Gómez, L., Milioli, F., 2005. Numerical simulation of ﬂuid ﬂow in CFB risers: a turbulence
strain rate magnitude. A yield strain rate deﬁnition, based on the yield           analysis approach. J. Brazil. Soc. Mech. Sci. Eng. 27 (2), 141–149.
stress and physical properties of the soil, was proposed. Thus, contrary    GPUSPH oﬃcial website. http://www.gpusph.org. Accessed: 2017-03-31.
                                                                                        Gray, J., Monaghan, J., Swift, R., 2001. SPH elastic dynamics. Comput. Methods Appl.
to Ulrich (2013), the mechanical behaviour of the soil does not depend                                                                                  Mech. Eng. 190 (49), 6641–6662.
on any numerical parameter. In addition, a reliable method, based on a      Grenier, N., Antuono, M., Colagrossi, A., Le Touzé, D., Alessandrini, B., 2009. An
Laplace equation, was developed to compute the eﬀective pressure that         Hamiltonian interface SPH formulation for multi-ﬂuid and free surface ﬂows. J.
is mandatory to compute the yield stress.                                       Comput. Phys. 228 (22), 8380–8393.
                                                                                 Guan, C.-Y., Qi, J.-F., Qiu, N.-S., Zhao, G.-C., Yang, Q., Bai, X.-D., Wang, C., 2012.
   This elastic-viscoplastic model was tested on a two-dimensional soil         Macroscopic Young’s elastic modulus model of particle packing rock layers. Open J.
collapse test case. The soil surface conﬁguration and the failure line          Geol. 2 (3), 198–202.
were compared to experimental results and a good agreement was      Gurtin, M., 1981. An introduction to continuum mechanics. Mathematics in Science and
                                                                                               Engineering. 158.
found, the surface remaining constant after a few seconds. The model     Hashemi, M., Manzari, M., Fatehi, R., 2016. Evaluation of a pressure splitting formulation
was then applied to a two-dimensional dam-break wave on movable           for weakly compressible SPH: ﬂuid ﬂow around periodic array of cylinders. Comput.
beds. Two diﬀerent materials were tested, i.e. sand and PVC pullets.         Math. Appl. 71 (3), 758–778.
                                                                                Hu, X., Adams, N., 2006. A multi-phase SPH method for macroscopic and mesoscopic
Numerical   free-surface,  moving-soil/water  and   motionless-soil/         ﬂows. J. Comput. Phys. 213 (2), 844–861.
moving-soil interfaces were compared to experimental data. A good     Wolfram Research, Inc.. Mathematica, Version 10.4. Champaign, IL, 2017.
agreement was found for the sand. For the PVC, the lack of elastic      Jiang, H., Xie, Y., 2011. A note on the Mohr–Coulomb and Drucker–Prager strength
                                                                                                                  criteria. Mech. Res. Commun. 38 (4), 309–314.
properties experimental values leads to less accurate but still reasonable      Jop, P., Forterre, Y., Pouliquen, O., 2006. A constitutive law for dense granular ﬂows.
results. For both materials, the total mass of eroded sediment is pre-         Nature 441 (7094), 727–730.
dicted with a correct order of magnitude when the SPH particle size       Liu, Q., Li, J., 2015. Eﬀects of water seepage on the stability of soil-slopes. Procedia
                                                                     IUTAM 17, 29–39.
does not exceed three times the grain size. Note that this work may be                                                                                      Manenti, S., Sibilla, S., Gallati, M., Agate, G., Guandalini, R., 2011. SPH simulation of
implemented in future versions of the open source GPUSPH code         sediment ﬂushing induced by a rapid water ﬂow. J. Hydraul. Eng. 138 (3), 272–284.
(GPUSPH oﬃcial website).                                        GDR MiDi, 2004. On dense granular ﬂows. Eur. Phys. J. E–Soft Matter 14 (4).
   To improve results, turbulence models could be tested. Indeed, the       Mitsoulis, E., 2007. Flows of viscoplastic materials: models and computations. Rheol. Rev.
                                                                                       2007, 135–178.
force exerted by water on the sediment  is strongly related to the

                                                                       172

### Page 18

A. Ghaïtanellis et al.                                                                                                       Advances in Water Resources 111 (2018) 156–173

Morichon, D., Desombre, J., Simian, B., 2013. VOF simulation of sediment transport                stress. Numer Meth Lami Turb Flow Seattle. pp. 680–690.
    under high velocity ﬂow case of a dam break over a mobile bed. Coastal Dynamics       Terzaghi, K., 1936. The shearing resistance of saturated soils and the angle between the
    2013. pp. 1241–1250.                                                                     planes of shear. Proceedings of the 1st International Conference on Soil Mechanics
Morris, J., Fox, P., Zhu, Y., 1997. Modeling low Reynolds number incompressible ﬂows         and Foundation Engineering. 1. Harvard University Press Cambridge, MA, pp. 54–56.
    using SPH. J. Comput. Phys. 136 (1), 214–226.                                            Ulrich, C., 2013. Smoothed-particle-hydrodynamics simulation of port hydrodynamic
Nabian, M., Farhadi, L., 2016. Multiphase mesh-free particle method for simulating              problems. Technische Universitat Hamburg Harburg Ph.D. thesis.
    granular ﬂows and sediment transport. J. Hydraul. Eng. 04016102.                        Ulrich, C., Leonardi, M., Rung, T., 2013. Multi-physics SPH simulation of complex marinePapanastasiou, T., 1987. Flows of materials with yield. J. Rheol. (1978-Present) 31 (5),          engineering hydrodynamic problems. Ocean Eng. 64, 109–121.
    385–404.                                                                                        Vila, J., 1999. On particle weighted methods and smooth particle hydrodynamics. Math.
Peshkov, I., Romenski, E., 2016. A hyperbolic model for viscous Newtonian ﬂows.              Models Methods Appl. Sci. 9 (02), 161–209.
   Continuum Mech. Thermodyn. 28 (1–2), 85–104.                                        Violeau, D., 2009. Dissipative forces for Lagrangian models in computational ﬂuid dyRandles, P., Libersky, L., 1996. Smoothed particle hydrodynamics: some recent im-             namics and application to smoothed-particle hydrodynamics. Phys. Rev. E 80 (3),
    provements and applications. Comput. Methods Appl. Mech. Eng. 139 (1–4),               036705.
    375–408.                                                                               Violeau, D., Leroy, A., 2014. On the maximum time step in weakly compressible SPH. J.
Revil-Baudard, T., Chauchat, J., 2013. A two-phase model for sheet ﬂow regime based on         Comput. Phys. 256, 388–415.
    dense granular ﬂow rheology. J. Geophys. Res. 118 (2), 619–634.                        Violeau, D., Rogers, B., 2016. Smoothed particle hydrodynamics (SPH) for free-surface
Rhie, C., Chow, W., 1983. Numerical study of the turbulent ﬂow past an airfoil with            ﬂows: past, present and future. J. Hydraul. Res. 54 (1), 1–26.
     trailing edge separation. AIAA J. 21 (11), 1525–1532.                              Wendland, H., 1995. Piecewise polynomial, positive deﬁnite and compactly supported
Spinewine, B., Zech, Y., 2007. Small-scale laboratory dam-break waves on movable beds.           radial functions of minimal degree. Adv. Comput. Math. 4 (1), 389–396.
     J. Hydraul. Res. 45 (sup1), 73–86.                                                    Whitaker, S., 1986. Flow in porous media: a theoretical derivation of Darcy’s law. Transp.
Stokes, G., 1851. On the Eﬀect of the Internal Friction of Fluids on the Motion of               Porous Media 1 (1), 3–25.
    Pendulums. 9 Pitt Press Cambridge.                                                    Xenakis, A., Lind, S., Stansby, P., Rogers, B., 2015. An ISPH scheme with shifting for
Sun, Q., Wang, G., 2013. Mechanics of Granular Matter. Tsinghua University.                  newtonian and non-Newtonian multi-phase ﬂows. Proceedings of the 10th
Tanner, R., Milthorpe, J., 1983. Numerical simulation of the ﬂow of ﬂuids with yield             International SPHERIC Workshop. pp. 84–91.

                                                                       173
