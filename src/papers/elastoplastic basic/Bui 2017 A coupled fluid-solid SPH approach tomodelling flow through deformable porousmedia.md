# A coupled fluid-solid SPH approach to modelling flow through deformable porous media

> Auto-converted from PDF for Codex/code-reference reading. Formatting, equations, figures, and tables may require checking against the original PDF.

- Source PDF: `Bui 2017 A coupled fluid-solid SPH approach tomodelling flow through deformable porousmedia.pdf`
- Pages: 21
- PDF metadata author: Ha H. Bui

## Extracted Text

### Page 1

International Journal of Solids and Structures 125 (2017) 244–264

                                             Contents lists available at ScienceDirect

                  International Journal of Solids and Structures

                                           journal homepage: www.elsevier.com/locate/ijsolstr

A coupled ﬂuid-solid SPH approach to modelling ﬂow through
deformable porous media

Ha H. Bui a ,∗, Giang D. Nguyen b

a Department of Civil Engineering, Monash University, Australia
b School of Civil, Environmental & Mining Engineering, The University of Adelaide, Australia

a r t i c l e    i n f o              a b s t r a c t

Article history:                                     In this paper, a computational framework based on the mesh-free smoothed particle hydrodynamics
Received 20 November 2016                     (SPH) method is developed to study the coupled behaviour of ﬂuid and solid in a deformable porous
Revised 2 May 2017                         medium. The mathematical framework developed herein is derived from the Biot’s two-phase mixture
Available online 22 June 2017
                                             theory in which the solid is modelled as an elasto-plastic material and the pore-ﬂuid as an incompressKeywords:                                            ible ﬂuid. The key feature of the proposed numerical framework is that both solid and ﬂuid phases are
SPH                                           solved simultaneously in two different Lagrangian discretisations (or two different sets of Lagrangian parDeformable porous media                              ticles) using their own governing equations that are linked through several laws of physics. The capability
Coupled two-phase ﬂow                            of the SPH method to model large deformation of the solid materials enables the framework to account
Large deformation                                   for the permeability change due to the dilatant shear behaviour of the solid phase. To obtain a stable
Progressive failure                           and accurate SPH solution for the pore-ﬂuid, an incompressible SPH (ISPH) approach is adapted to corElasto-plasticity
                                                     rectly simulate the pore-pressure distribution of the ﬂuid phase inside the porous medium. The proposed
                                            coupled SPH framework is ﬁrstly validated against analytical and solutions obtained using ﬁnite element
                                      method (FEM) for a submerged soil medium subjected to a gravitational load and a seepage ﬂow through
                                         an elastic embankment, respectively. Then, it is employed for the simulation of ﬂows through rockﬁll
                                     dams and an embankment failure induced by seepage ﬂows. Simulation results predicted by SPH show
                                             very good agreements with analytical, FEM and experimental results. This suggests that the proposed
                                          two-phase SPH framework is a promising approach for future studies of coupled problems that involve
                                         complex water free-surface/seepage ﬂows and large deformation of soils which are diﬃcult to be mod-
                                                   elled using traditional FEM-based coupled two-phase ﬂow models.
                                                                    © 2017 Elsevier Ltd. All rights reserved.

1. Introduction                                                 The early study of coupled ﬂow-deformation in porous media
                                                        was mainly based on the concept of single porosity, which is as-
   Coupled ﬂow deformation analysis in saturated and unsaturated    sumed to be fully saturated and consisted of a solid matrix and a
porous media is important in many geophysics, engineering appli-     single ﬂuid phase. Any change of stresses in ﬂuid, as a result of
cations and industrial processes. Typical examples of these prob-    dynamic loading, is then accompanied by a corresponding change
lems include: soil liquefaction during earthquake, gravity driven     in the effective stresses in the solid matrix, which produces the
ﬂows such as fast landslides and debris ﬂows, failure of man-made    deformation of the porous medium. The ﬁnite element method
structure (e.g. dikes and embankments) due to internal seepage    (FEM) has been commonly known as a robust numerical tool for
erosion or overtopping ﬂows during intensive rainfall and ﬂooding     solving such single saturated porosity system with many applievents, oil gas extraction in energy sector or carbon dioxide se-     cations ranging from dynamic responses of saturated porous mequestration in geological formations. All of these applications typi-     dia ( Prevost, 1985; Zienkiewicz and Shiomi, 1984 ), land subsidence
cally involve complex ﬂow patterns and large deformations of the    above gas/oil reservoirs ( Gambolati et al., 2001; Lewis and Sukirsolid phase that require both an advanced theoretical framework    man, 1994 ), multiphase ﬂuid ﬂow in a deforming fractured reserand a robust computational platform to capture the salient mech-     voir  ( Gelet et  al., 2012; Lewis and Ghafouri, 1997 ), deformation
anisms of the complex multiphase interactions.                    and localisation behaviour of unsaturated soils ( Ehlers et al., 2004;
                                                                          Peric et al., 2014 ), behaviour of soil deposit under seismic loading
                                                                                           ( Popescu et  al., 2006 ) and landslide triggered by rainfall ( Cascini
                                                                            et  al., 2010 ). Although giving satisfactory results, the FEM-based  ∗Corresponding author. Tel.: +61 03 9905 2599; fax: +61 03 9905 4944.
    E-mail addresses: ha.bui@monash.edu , buihongha@gmail.com (H.H. Bui).          approach has some certain limitations. For instance,  it is impos-

http://dx.doi.org/10.1016/j.ijsolstr.2017.06.022
0020-7683/© 2017 Elsevier Ltd. All rights reserved.

### Page 2

H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264                                 245

sible to simulate complex problems involving ﬂow failure of soils,     ity (and thus on the seepage drag force) was considered in some
such as internal erosion due to seepage ﬂow, piping, and/or over-     recent studies such as in  ( Bui et  al., 2011b ), the effect of solid
topping ﬂows or transportation of contaminated substances in the    matrix deformation on the excess pore-water pressure was tosubsurface or fractured media, in which the Lagrangian description      tally ignored. In addition, most previous works adopted a weakly
of ﬂuid ﬂow is explicitly required. Moreover, as FEM is a mesh-    compressible SPH approach to simulate the pore-ﬂuid, in which
based method, it is most suitable for the pre-failure regime with    the ﬂuid pressure was calculated using an equation of state forsmall deformation of the porous media. In the post-failure regime    mulated as a function of density change. This approach normally
involving large deformations (for example catastrophic landslide     suffers from pressure oscillation and thus unable to remain stawith rapid progressive failure and long run distance of soil mass),     ble for modelling long physical time problems (up to 30 min.). FiFEM-based approaches suffer from severe mesh distortion issues     nally, the mathematical framework derived in previous works is
even when the updated Lagrangian discretisation or adaptive re-    not fully consistent owing to the simpliﬁcation of constant void
meshing is adopted ( Ehlers et al., 2004; Zienkiewicz et al., 1995 ).     fraction assumption, thus unable to achieve accurate simulation
In these particular problems, mesh-free methods offer an excellent     results. The above mentioned shortcomings make those studies,
alternative to model large deformation and failure behaviour satu-      strictly speaking, only suitable for ﬂow through rigid porous merated/unsaturated porous medium.                                     dia since the pressure ﬂuctuation of the pore-ﬂuid in the weakly
   In the last few decades, there is a blooming development of    compressible SPH model could produce signiﬁcant error when coumesh-free methods suitable for large deformation analysis such as:     pling with the solid phase. Accordingly, it is necessary to further
smoothed particle hydrodynamics (SPH) ( Gingold and Monaghan,    develop the original two-phase SPH model to improve its predic-
1977; Lucy, 1977 ), material point method (MPM) ( Sulsky, 1996 ),     tive capability as well as the accuracy of numerical solutions for
element free Galerkin method ( Belytschko et al., 1994; Krysl and    coupled ﬂow deformation analysis. Within the context of coupled
Belytschko, 1996 ), particle FEM ( Onate et al., 2004 ). Among these   ﬂow deformation analysis,  it is also worth to mention the work
methods, SPH is the oldest and truly mesh-free technique whereas    by Pastor and co-workers ( Blanc and Pastor, 2012; Pastor et  al.,
other methods are still strongly or weakly based on a computa-    2009 ) and Bui and Fukagawa (2009 ) who followed the u-p Biot–
tional mesh and therefore have some minor drawbacks such as cell     Zienkiewicz’s approach and used a single set of Lagrangian parcrossing noise in PIC/MPM ( Zhang et al., 2011 ), severe mesh dis-     ticles to solve the Biot’s mixture theory. Although this approach
tortions hence re-meshing required in PFEM ( Zhang et al., 2013 ) or    can simulate complex ﬂow phenomena of rapid landslides and dehigh computational cost since both neighbour-searching and mesh-     bris ﬂows, the usage of a single set of particles does not provide
based integration are required in EFG ( Duan and Belytschko, 2009 ).     insights into the mechanism of seepage ﬂows inside the porous
Initially invented for astrophysical applications, the SPH method     structure or the interaction of ﬂuid ﬂows inside and outside the
was quickly developed and successfully applied to various prob-    porous medium, and hence might be diﬃcult to model speciﬁc oclems in ﬂuid mechanics ( Colagrossi and Landrini, 2003; Monaghan,    currences such as internal erosions induced by seepage ﬂows caus-
1994; Shao and Lo, 2003 ), solid mechanics ( Gray et al., 2001; Le-     ing empty spaces inside the soil domain, overtopping ﬂow through
roch et  al., 2016; Libersky et  al., 1993 ) and geomechanics ( Blanc    dams/embankments, surface erosions and water wave impact on
and Pastor, 2013; Bui et al., 2006; Bui et al., 2008; Bui et al., 2011a;     geotechnical structures.
Nguyen et al., 2017; Pastor et al., 2009 ). In the context of coupled        In this paper, a two-phase SPH framework is further developed
ﬂow deformation analysis, Bui et al. (2007 ) presented the numer-    based on the original work by Bui et  al. (2007 ). The governing
ical simulation of soil-water interaction using the SPH method in    equations of the mixture consisting two constituents (ﬂuid and
which both ﬂuid and solid phases were solved simultaneously in     solid skeleton) are fully reformulated taking into consideration the
two different SPH discretisation platforms using their own set of     effects of void fractions on the dynamic response of the porous
governing equations. In their approach, the soil matrix was con-   medium as well as the seepage ﬂow. The effect of volumetric desidered as a cohesive-frictional material following an elasto-plastic    formation of the solid skeleton matrix on the pore-water pressure
model, whereas the pore space in the soil skeleton was assumed      is taken into consideration for the ﬁrst time within the SPH context
to be fully saturated with a weakly compressible ﬂuid. The in-    through a consistent mathematical framework that enables stable
teraction between two constituents (soil skeleton and ﬂuid) was    numerical solutions. In order to obtain a stable numerical solution
taken into consideration using a seepage force model formulated     for the pore-ﬂuid with an accurate pressure proﬁle and to make
based on the Darcy’s law and the pore-water pressure. Following    the two-phase SPH framework suitable for long physical time probthis framework, numerous studies have been conducted to simu-     lems, a fully explicit numerical scheme for incompressible ﬂuid
late soil-water interaction problems. For example, Maeda and Sakai   ﬂow (Explicit-ISPH) is adopted. Numerical algorithms for coupling
(2010 ) studied seepage ﬂow induced failures around sheet piles.    the two-phase system that makes use of the Explicit-ISPH model
In their study, soil was modelled by a non-linear elastic material,      is also presented. Finally, the proposed two-phase SPH framework
while water was treated as a weakly compressible ﬂuid. In these      is fully validated for both the seepage ﬂow patterns and failure reworks, the interaction between two phases was calculated using a    sponse of the porous medium.
seepage force model, while ignoring the contribution of the porewater pressure to the solid phase. Zhang and Maeda (2015 ) utilised
the same approach to study the seepage ﬂow induced dykes and
slope failure due to heavy rainfall. Huang Huang et al. (2013 ) studied ﬂow process in liqueﬁed soils using the SPH soil-water inter-     2. Mathematical framework
action model in which the soil was treated as an elastic material.
Grabe and Stefanova (2015 ) investigated hydraulic heave around a        In this section, the general mathematical framework describretaining wall and seabed erosion around a pipeline. Despite pro-     ing the coupling procedure of solid and ﬂuid phases is presented
viding some satisfactory results, the above studies based on the     to provide the theoretical basis for further development of the
two-phase SPH model still have some limitations. For instance, the    two-phase SPH model. The framework is essentially based on the
coupling between soil and ﬂuid in most previous works is weak    two-phase mixture theory, which was originally developed by Biot
in the sense that the inﬂuence of void fractions on the coupling    (1956 ) for linear elastic materials and further extended to account
behaviour of the mixture was not taken into consideration. De-     for nonlinear materials ( Prevost, 1980, 1982 ) and large deformation
spite the fact that the effect of void fractions on soil permeabil-    problems ( Zienkiewicz et al., 1999 ).

### Page 3

246                                        H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264

                                             Fig. 1. Continuum assumption of saturated porous medium, modiﬁed after ( Bui et al., 2007 ).

2.1. Basic assumptions                                         where ρw is the water density; ρs is the solid soil density; n w is
                                                                    the void fraction (or volume fraction) of water; and n s is the void
   The following assumptions are used in the derivation of the     fraction of soil. The volume fractions of water and soil are related
generic mathematical framework for coupling the motions of ﬂuid     by:
and solid phases in a porous medium:
                                                       n s + n w = 1                                                     (3)
  I. The saturated porous medium  is assumed to consist of two                                                                    Using the deﬁnitions ( 1 ) and ( 2 ), the saturated density of mix-
    constituents (solid skeleton and ﬂuid), each of which moves                                                                        ture is expressed as:
   with their own set of governing equations and occupies the
   same space at the same time. The interaction between two     ρsat = ¯ρ f + ¯ρs = n w ρw + n s ρs                                  (4)
   phases is considered via seepage force, pore-ﬂuid pressure and                                                                           Similar to the density, the partial stresses of soil and water are
   volumetric deformation ( Fig. 1 ).                                                          deﬁned respectively as:
 II. The Terzaghi’s effective stress concept is assumed to be valid
   and the  solid  skeleton  is modelled using an  elasto-plastic       ¯σs = n s σs                                                       (5)
   model.
III. Solid grains and ﬂuid ﬂow are assumed to be incompressible. In     ¯σw = n w σw                                                     (6)
    addition, the ﬂuid phase inside the porous medium is assumed
    to be Newtonian and the viscosity is negligible.                 where σw is the intrinsic stress tensor of water and σs is the inIV. No mass exchange and heat transfer between two phases are     trinsic stress tensor of soil. The total stress tensor of the saturated
   considered in this work.                                        mixture σ is then the sum of soil and water partial stresses:
                                                  σ = ¯σs + ¯σw = n s ( σs −σw ) + σw                               (7)
2.2. Deﬁnitions of partial density and partial stress in the porous
                                                               The ﬁrst term in the right hand-side of Eq. (7) is often calledmedium
                                                                    the “effective stress” in soil mechanics, while the second term is
                                                                    the total stress of water phase consisting of the hydrostatic static   As discussed, the porous medium considered herein is a two-
                                                                  pore-water pressure ( p w ) and viscous shear stress ( τw ). In soil me-phase mixture consisting of a soil skeleton and a water phase ( Biot,
                                                                          chanics, the viscous shear stress of pore-ﬂuid is often ignored, and1956 ). The pore-space inside the soil skeleton is assumed to be
                                                                        therefore the stress tensor of the pore-ﬂuid consists of the pore-fully saturated with water. Accordingly, the partial densities of the
                                                                water pressure only. Using these deﬁnitions, the partial stress ten-soil and water in the porous medium are respectively deﬁned as:
                                                                         sors of soil and water in the porous medium are rewritten as:
¯ρs = n s ρs                                                       (1)       ¯σs = σ′ −n s p w I                                                (8)

¯ρw = n w ρw                                                     (2)     ¯σw = −n w p w I                                                   (9)

### Page 4

H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264                                  247

where I is the unit tensor. It should be reminded here that negative    where R  is the force per unit volume; γ w  is the speciﬁc unit
stress in the context of this paper means compression.               weight of the water; and k is the permeability coeﬃcient. The ﬁrst
                                                             term in the right hand-side of Eq. (18) is commonly known as the
2.3. Mass balance equations of the deformable porous medium           viscous drag force (or seepage force) based on the linear Darcy’s
                                                                          law, while the second term is called ‘buoyancy term’, which is ac-
   The mass balance equations for a unit volume of mixture con-    counted for immiscible mixtures. The coeﬃcient of permeability
sisting of soil and water phases can be written as follows:           depends on several factors such as ﬂuid viscosity, pore size dis-
                                                                              tribution, grain size distribution, void ratio and saturation degree
d ¯ρs
   + ¯ρs ( ∇ · v s ) = 0                                        (10)     of soil. In large deformation analysis, the variation of void ratio re-
 dt                                                                              sults in a signiﬁcant change of soil permeability that needs to be
                                                                     properly taken into consideration. Various empirical equations ford ¯ρw
   + ¯ρw ( ∇ · v w ) = 0                                       (11)     estimating the coeﬃcient of permeability has been reported in the
 dt
                                                                               literature ( Bear and Cheng, 2010 ). Among these empirical formuwhere v s and v w are the velocity vectors of soil and water in the     lations, the Kozeny–Carman equation is selected in this work to
porous medium, respectively.  It is noted that Eqs. (10) and ( 11 )    estimate the permeability of soils undergoing large deformation:
were written under the assumption that the spatial gradient of                  3
                                                               n w                                                                                                                                   (19)void fractions over the distribution is suﬃciently small, thus can    k = Ck                                                                                               2
be considered negligible. Substituting Eqs. (1) and  ( 2 ) into Eqs.            ( 1 −n w )
(10) and ( 11 ) yields:                                                          where C k is Kozeny–Carman’s constant determined from laboratory
d( n s ρs )                                                                              test.
     + n s ρs ( ∇ · v s ) = 0                                  (12)       The momentum equations of the solid and ﬂuid phases in the   dt
                                                                deformable porous medium are then written as follows:
d( n w ρw )
      + n w ρw ( ∇ · v w ) = 0                               (13)      d v s    dt                                                                                             ¯ρs   = ∇ · ¯σs + ¯ρs g −R                                   (20)                                                                         dt
   Eq. (12) can be rewritten in the following form:
                                                            d v w
  d ρs     d n s                                                              ¯ρw   = ∇ · ¯σw + ¯ρw g + R                                 (21)
n s   + ρs   = −n s ρs ( ∇ · v s )                              (14)         dt
   dt       dt
                                                             By substituting Eqs. (8) and ( 9 ) into Eqs. (20) and ( 21 ) we get:
   Because the deformation of the solid phase (not the solid matrix) is negligible compared to that of the skeleton, the ﬁrst term      d v s
on the left hand-side of Eq. (14) vanishes, and Eq. (14) reduces to:       ¯ρs   = ∇ ·  σ′ −n s p w I + ¯ρs g −R                         (22)                                                                         dt

d n s                                                            d v w   = −n s ∇ · v s                                             (15)                                                                              ¯ρw                                             = −∇( n w p w ) + ¯ρw g + R                            (23) dt                                                                          dt
   Similarly, Eq. (13) can also be rewritten in the following form:        Substituting Eq. (18) into Eqs. (22) and ( 23 ) and expanding the
                                                                         ﬁrst terms in the right-hand side of these equations yield:
  d ρw     d n w
n w     + ρw           = −n w ρw ( ∇ · v w )                         (16)      d v s    dt              dt                                                                                                      ¯ρs   = ∇ · σ′ −( p w ∇ n s + n s ∇ p w ) + ¯ρs g
                                                                         dt
   Substituting Eq. (3) into Eq. (16) and making use of Eq. (15) lead
                                                               γw n 2wto the following mass balance equation for water phase in the de-        +                                                                                            ( v w −v s ) −p w ∇ n w
formable porous medium:                                                   k
                                                                                 γw n 2wd ρw                 1 −n w                          = ∇ · σ′ −n s ∇ p w + ¯ρs g +       ( v w −v s )            (24)
   = −ρw ( ∇ · v w ) −ρw        ( ∇ · v s )                     (17)                                    k
 dt                    n w

   Eq. (17) holds for the water ﬂow both inside and outside the                                                        2
                                                            d v w                             n wporous medium. In the latter case ( n w = 1), the second term in the     ¯ρw   = −( p w ∇ n w + n w ∇ p w ) + ¯ρw g −γw   ( v w −v s )
                                                                          dt                                 k
right hand side of Eq. (17) vanishes; thus Eq. (17) returns to the
                                               + p w ∇ n wstandard continuity equation of the ﬂuid ﬂow. In this paper, Eq.
(15) is solved for the void fraction of solid phase, while the void                             n 2w                                              = −n w ∇ p w + ¯ρw g −γw   ( v w −v s )                (25)
fraction of water phase is updated using Eq. (3) . On the other hand,                                k
Eq. (17) is used to enforce the incompressibility condition of water         Finally, dividing each equation by the corresponding  partial
ﬂow which will be described in Section 2.5 .                             density, the following momentum equations  for the ﬂuid-solid
                                                                mixture in the deformable porous medium can be derived:
2.4. Momentum equations of the deformable porous medium                                                         2                                                          d v s   1                    γw n w                                           =  ∇ · σ′ −n s ∇ p w + g +       ( v w −v s )            (26)
                                                                       dt      ¯ρs                                      ¯ρs k   The behaviour of saturated porous medium is determined by
the interaction between soil skeleton and pore-ﬂuid, each of which                                     2
                                                          d v w                  n wis regarded as a continuum that follows its own governing equa-      = −1 ∇ p w + g −γw   ( v w −v s )                     (27)
                                                                       dt     ρw              ¯ρw ktions. When the binary phase medium is deformed, the soil skeleton  is compressed and pore-ﬂuid ﬂows through the pores. The        Similar to the continuity Eq. (17), Eq. (27) holds for inviscid
force acting on the ﬂuid phase due to the soil skeleton, which rep-    ﬂuid ﬂows both inside and outside the porous medium. For the
resents the momentum exchange between two constituents, is de-   ﬂow outside the porous medium, such as in the reservoir of an
ﬁned as ( Bowen, 1976 ):                                       embankment, the seepage force (i.e. the last term) no longer ex-
            2                                                                               ists, thus Eq. (27) returns to the standard momentum equation of
       n wR = −γw   ( v w −v s ) + p w ∇ n w                              (18)     inviscid ﬂuids. It is worth to note that, in traditional FEM-based
       k

### Page 5

248                                        H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264

approach, the above momentum equations are further combined     to the transition behaviour from unsaturated to saturated condito derive a momentum equation for the entire mixture. In this     tions must be taken into consideration. Advanced unsaturated soil
work, a different approach is undertaken by solving the momen-     constitutive models ( Alonso et  al., 1990; Khalili and Loret, 2001;
tum equations of the ﬂuid-solid mixture separately. The advantage     Loret and Khalili, 20 0 0; Sheng et al., 20 08 ) can be used to model
of this approach is that the ﬂuid ﬂow through the porous media    the shear strength reduction of soils due to the decrease of soil
is explicitly simulated, thus facilitating the modelling of compli-    matrix suction owing to the saturation process. However, implecated physical problems, such as internal erosion. The proposed    mentation of such models in the current SPH framework is beSPH framework is, therefore, versatile to simulate and capture sev-    yond the scope of the current paper, and thus is reserved for fueral physical phenomena associated with multiphase ﬂows through     ture works. Alternatively, a simpler approach which based on the
deformable porous medium.                                          general concept in soil mechanics can be applied. It is well known
                                                             from unsaturated soil mechanics that the change of the degree of
2.5. Constitutive relations                                               saturation of soil does not have a signiﬁcant effect on the friction
                                                                    angle ( Fredlund and Rahardjo, 1993 ). However, the soil cohesion
   To complete the above mathematical descriptions of the cou-     strongly depends on the saturation condition. In particular,  it is
pled behaviour of ﬂuid and solid in the porous medium, a constitu-     generally accepted that the soil cohesion increases with increastive relation for the mechanical deformation of the porous medium     ing suction and reduces as the suction decreases. The degradation
must be speciﬁed. Any existing constitutive model capable of de-     of suction in soils is, on the other hand, the consequence of the
scribing the elasto-plastic behaviour of the porous medium can be     increasing degree of saturation and many empirical relations have
adopted in the current computational framework. For the sake of    been proposed to describe this behaviour ( Vangenuchten, 1980 ). In
simplicity, an elasto-plastic constitutive model employing Drucker–     this work, to account for this behaviour of cohesion, the following
Prager yield criterion is chosen. This model was ﬁrst implemented     linear relationship is adopted:
in the SPH framework by the ﬁrst author Bui et al. (2008 ), and
                                                                       c = c sat + ( 1 −s r ) ( c o −c sat )                                 (33)has been shown to be capable of describing large soil deformation
with the SPH method ( Bui and Fukagawa, 2013; Bui et al., 2011a ,    where c o is the initial cohesion at the initial degree of saturation
2014; Chen and Qiu, 2012; Deb and Pramanik, 2013; Nguyen et al.,     s or ; c sat is the apparent cohesion of soil at the fully saturated con-
2017 ). Details of the model derivation can be found in Bui and Fuk-     dition; and s r is the degree of saturation which ranges from s or to
agawa (2013 , 2008 ), and only a brief description of this model is      1.
presented here. Following the elasto-plastic framework, the general
stress-strain relationship is given as:
                                                                                      2.6. Time integration of the governing equations
σ˙ ′ = D e : ( ε˙ −˙ε p )                                         (28)
                                                                             In the proposed numerical framework, the motions of solid and
where the dot indicates time derivative, D e is the elastic stiffness
                                          p                           ﬂuid phases are solved separately using their own governing equa-tensor, ε˙ is the strain rate tensor and ε˙   is its plastic component
                                                                                tions. The solution methods to integrate the governing equations ofthat can be calculated using the plastic ﬂow rule:
                                                                   the solid phase without considering solid-ﬂuid coupling have been
           p                                                (29)    explained in details in Bui et al. (2008 ), in which the Leap-Frogε˙ p = λ∂˙  g
      ∂ σ′                                                      time integration scheme has been selected to advance solid variwhere λ˙  is the rate of change of plastic multiplier and g p is the     ables. To avoid repetition, this section will only present relevant
plastic potential function:                                              solution procedures for the ﬂuid phase. Further details of the cou-
                                                                        pling procedure are described in Section 3.8 .
g p = αψ I1 +    J2 −constant                                (30)       The two-step prediction and correction time integration scheme
                                                        method  ( Shao and Lo, 2003 )  is selected to solve the governing   In the above expression, I 1 and  J 2 are the ﬁrst and second in-
                                                                   equations of the incompressible ﬂuid ﬂows, both inside and out-variants of the stress tensor, αψ  is a dilatancy factor that can be
                                                                        side the deformable porous medium. In the ﬁrst prediction step,related to the dilatancy angle ψ in a fashion similar to that be-
                                                                                  w ) and position ( r ∗w ) of the ﬂuidtween αφ and friction angle φ (see Eq. 32 ). Plastic deformation    intermediate temporal velocity ( v ∗
                                                               phase is estimated without considering the pressure gradient, us-occurs only if the stress state reaches the yield surface of Drucker–
                                                                      ing the following equations:Prager type, deﬁned as:

                                                                         w ( v w −v s )    t                         (34) f y = αφI1 +    J2 −k c = 0                                    (31)    v ∗w = vtw +  g −γw n 2                                                                             k
where αφ and k c are Drucker–Prager constants that are calculated
from the Coulomb material constants c (cohesion) and φ (inter-       ∗        t      ∗
                                                                      r w = r w + v w   t                                            (35)nal friction). In plane-strain conﬁguration, the Drucker–Prager constants are computed by:                                      where vtw and rtw are the vector velocity and position at time t ,
          tan φ                 3 c                                respectively; and    t is the incremental time. The values of v ∗w and
                                                           (32)                 and k c =αφ =
                    2                                                 2                                                                                  r ∗w are then used to compute an intermediate ﬂuid water density      9 + 12 tan φ          9 + 12 tan φ
                                                                      as follows:
   This  soil model requires ﬁve parameters, which are Young’s    dρ∗w                 ∗      1 −n w
modulus ( E ), Poisson’s ratio ( ν), cohesion coeﬃcient ( c ), friction      = −ρw ( ∇ · v w ) −ρw        ( ∇ · v s )                   (36)
                                                                       dt                    n wangle ( φ) and dilatancy angle ( ψ).
   The above elasto-plastic model is established in the effective        This equation takes into account the effect of solid matrix destress context and therefore neglects the inﬂuence of saturation    formation through the last term. In the correction step, the force
condition of  soil. In  reality, properties of  soil, especially shear    due to the pressure gradient which has been ignored in the ﬁrst
strength, are greatly dependent on the saturation condition, or     prediction step is taken into consideration to adjust the velocity of
more speciﬁcally, on the water content, soil-water characteristic    ﬂuid phase as follows:
curve and suction. In order to correctly model seepage induced
                                                                                                 t+1progressive soil failure, the reduction in shear strengths of soil due    vt+1w = v ∗w −1 ∇p                                                                        w     t                                    (37)
                                                                     ρ∗w

### Page 6

H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–26 4                                 24 9

where pt+1w  and vt+1w   are the water pressure and particle velocity     interpolation process is based on the integral representation of a
at time ( t + 1).                                                     ﬁeld function:
   The pressure at time ( t + 1) is calculated by enforcing the in-                                     ′                   ′            ′       2                                                    A ( r ) =   A r W r −r , h d r + O h                       (44)compressibility condition for the water ﬂuid phase. This can be
done by taking the divergence of Eq. (37) and rearranging the ob-
                                                          where A is any variable deﬁned on the spatial coordinate r and
tained equation, leading to:
                                                                      kernel function W , which is taken to be a cubic-spline function
     vt+1w −v ∗w                    t+1                                            ( Monaghan and Lattanzio, 1985 ), and h is the smoothing function.∇ ·         = ∇ · −1 ∇p w                         (38)    The integral representation in Eq. (44) is then further discretised              t             ρ∗w
                                                                onto a ﬁnite set of interpolation points (the particles), which carry
   To enforce the incompressibility of the water ﬂuid phase, one    constant mass and other ﬁeld variables at their corresponding loneeds:                                                                      cations, by replacing the integral with a summation and the mass
        t+1                                                      element ρV with the particle mass m :
     v w
∇ ·     = 0                                           (39)                                      ′           t                                                      A r
                                        W r −r ′ , h ρ r ′ d r ′ + O h 2                                                    A ( r ) =
                                                              ρ( r ′ )   By combining Eqs. (37) & ( 38 ) and making use of the condition
( 39 ), the following equation is obtained:                                    N   A J
                                            ≈  m J W r −r J , h                                 (45)
     1     t+1    1       ∗                                                          J=1    ρJ
∇ · ρ∗∇p w  =    t ∇ · v w                               (40)
                                                          where the subscript  J refers to the quantity evaluated at the po-
   Alternatively, by substituting Eq. (36) into Eq. (40) , one gets:        sition of particle  J ; ρJ is the density of particle  J; m J is the mass
                                                                           of particle J ; and N is the number of “neighbouring particles”, i.e.,
     1     t+1    ρ0w −ρ∗w   −n w                                                                                 in                                                                            the                                                                             support domain                                                                                                                                                                                                                .               −1                    ∇ · v s                  (41)    those         w  =∇ · ρ∗∇p                         n w   t                ρ0w   t 2                                                               The                                                             SPH                                                                            approximation                                                                                                            for a                                                                                                       gradient term may be calculated
where ρ0w is the initial density of ﬂuid phase. Eqs. (40) and ( 41 ) are    by taking the analytical derivative of Eq. (45) , giving:
equivalent and commonly known as the pressure Poisson’s equa-                                                 ′
                                                                   ∂    A r                   ′              ′       ′       2                                           W r −r , h ρ r d r + O htions for the ﬂuid phase, which can be applied to both ﬂows inside   ∇A ( r ) =
                                                                  ∂r   ρ( r ′ )and outside the porous medium. For the latter case, the last term
of Eq. (41) vanishes, and Eq. (41) reduces to the same pressure              N   A J
Poisson’s equation derived by Shao and Lo (2003 ) for an incom-       ≈  m J ∇W r −r J , h                             (46)                                                                                           ρJ
pressible ﬂuid ﬂow. On the other hand, for ﬂows inside a porous                 J=1
medium, the source term on the right hand side of the Poisson’s        Eqs. (45) and ( 46 ) are the basic SPH formulations, which form
equation consists of both the variations of the ﬂuid phase den-      all other SPH formalisms in the literature. Further details of the
sity and solid void fraction, thus coupling the effect of solid matrix     gradient approximations and other issues of the SPH method can
deformation on the pore-water pressure. Details on solving these    be found in Monaghan (2012 ).
equations will be further discussed in the next section.
   The pressure calculated from either Eq. (40) or Eqs. (41) is then      3.2. SPH approximations of void fractions
used in Eq. (37) to calculate the velocity at time ( t + 1), and the
position at the corresponding time is ﬁnally calculated at:               To simplify our discretisation, it is convenient to reserve sub-
                        t     t+1                                                      scripts  i and  j for the solid phase, and subscripts a and b for the
 t+1       t   v w + v w
r w = r w +                t                                   (42)    ﬂuid phase. The variation of the void fraction of the solid phase is             2                                                                        calculated by solving Eq. (15) . By expanding the right hand-side of
where rtw and rt+1w   are the positions of the particle at time t and     this equation and applying the SPH approximation ( 46 ) to the di-
( t + 1), respectively.                                                vergence term, the following SPH approximation for the void frac-
   The current time integration scheme requires a suﬃciently     tion of the solid phase can be obtained:
small time step (   t ) to guarantee the stability of the solution. In
                                                          d n i
particular, the time step must satisfy the Courant-Friedrich-Levy     = −{ ∇ · ( n v ) −v · ( ∇n )}i                                                                       dt
(CFL) stability condition:
                                                                          N  ¯m j                N  ¯m j
                                           = −       n j v j   · ∇ i Wij +       n j v i   · ∇ i Wij   t ≤CF L min (   t w ,   t s )  with     t w = l / v max &    t s = l / c s                               ¯ρ j                             ¯ρ j
                                                                                             j=1                        j=1
                                                           (43)
                                                                        N  ¯m j
where l is the length scale of the numerical discretization; v max is     =      n j v i −v j   · ∇ i Wij                             (47)                                                                                                                 ¯ρ j
the maximum ﬂow velocity in the computation; c s  is the sound              j=1
speed of soil; and CFL is the Courant number taken to be 0.2.        where ¯m j  is the mass of particle  j , calculated as the product of
                                                                   the partial density (not the solid density) and the spatially dis-
3. Solution approximation using the SPH method                    cretised volume; and N is the total number of neighbouring par-
                                                                                    ticles of particle  i . The calculated void fraction of the solid phase
3.1. Smoothed particle hydrodynamics (SPH)                                     is then used to estimate the void fraction of the ﬂuid phase using
                                                                         Eq. (3) as follows:
   In the SPH method, the computational domain  is discretised
                                                       n a = 1 −n i                                                (48)into a ﬁnite number of particles. These particles carry material
properties (such as velocity, density, stress, etc.) and move with the       Because the void fraction of the ﬂuid phase is calculated at the
material velocity according to their governing equations. The ma-     location of a ﬂuid particle rather than at that of the solid partiterial properties of each particle are then calculated through the      cle, the SPH approximation of the void fraction of solid phase at
use of an interpolation process over its neighbouring particles. The    the location of ﬂuid particle a is required. By applying Eq. (45) to

### Page 7

250                                        H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264

calculate the void fraction of solid phase at the location of ﬂuid     section. The partial differential form of this equation was derived
particle a and substituting this calculation back to Eq. (48) , we ob-     in Section 2.3 , i.e. Eq. (26) , and is rearranged as follows:
tain:                                                                                                                     2                                                          d v s   1                    γw n w       M                                     =  ∇ · σ′ −1 n s ∇ p w + g +       ( v w −v s )           (55)
              ¯m i                                                        dt      ¯ρs             ¯ρs                      ¯ρs k
n a = 1 −      n i Wai                                      (49)
                     ¯ρi                                                  The ﬁrst term in the right hand-side of Eq. (55) can be rewrit-                     i =1
                                                                    ten as:
where M is the total number of solid particles located within the
support domain of ﬂuid particle a . Owing to the fact that the void     1                 σ′      σ′
                                        ∇ · σ′  = ∇ ·     +       · ( ∇ ¯ρs )i                    (56)
fraction of the solid phase is much less than 1, the above SPH ap-         ¯ρs                 i             ¯ρs     i    ¯ρ2s
proximation guarantees that the void fraction of ﬂuid is always
less than or equal to 1 for the ﬂow inside and outside the porous       Applying Eq. (46) to the divergent terms in the right hand-side
medium, respectively.                                                    of Eq. (55) yields:

                                                                              N                      N
                                                                                1                      ¯m j   σ′ j                 σ′ i      ¯m j                                               =                                        ∇ · σ′                                                                                                                                                                ¯ρ j   · ∇ i Wij                                                                                                                                                                                ¯ρj     ¯ρj                                                                                                                                                                                                                                 ¯ρj                                                                                                                                                                                      i3.3. SPH approximations of the continuity equations                                              ¯ρs
                                                                                                  j=1                                                                                                                                                            · ∇ i Wij +  ¯ρ2i  j=1
                                                                              N                                             (57)
                                                                                                                             σ′ i     σ′ j                                                                                                                                                                                                                                            i Wij   As noted in Section 2.2 , the continuity equation for the solid         =                                                                                           ¯m j   ¯ρ2i +  ¯ρ2j     · ∇                                                                                                 j=1
phase has been replaced by the void fraction equation and the SPH
approximation for the void fractions have been presented in the       The SPH approximation of the second term in the right handprevious section. This section will focus on the derivation of SPH     side of Eq. (55) can be obtained using the same approach, leading
approximations for the continuity equation of the ﬂuid phase. By     to:
adopting the approach similar to that for the void fraction, the ﬁrst                    N
                                                                                   p w j                                                         n s                                                                             p witerm in the right hand-side of Eq. (17) can be expanded as follows:                                                         +                                        ∇ p w  = n i    ¯m j                                                          ∇ i Wij                  (58)
                                                                                                        ¯ρs               i       j=1       ¯ρ2i      ¯ρ2j
−ρw ( ∇ · v w ) = −[ ∇ · ( ρw v w ) −v w · ( ∇ ρw )]                 (50)
                                                          where p wi and p wj are the pore-ﬂuid pressure of solid particles
   The SPH approximation of Eq. (50) can be obtained by apply-        i and  j , respectively. However, as proved by Bui and Fukagawa
ing Eq. (46) to each term on the right hand-side of this equation,    (2013 ), the use of Eq. (58) or its alternative formulations resulted
resulting in:                                                              in numerical instability for soil particles located near the inter-
                                                                         face between submerged soil and water, unless a suitable dynamic
                    N  ¯m b                                     boundary condition is enforced at this interface boundary. Treat-
−{ ρw ( ∇ · v w )} a = −        ( ρb v b ) · ∇ a Wij                                 ¯ρb                                    ments of such boundary condition require signiﬁcant computa-
                      b=1
                                                                            tional effort to search for soil particles located near the interface
                    N  ¯m b                                     boundary between submerged soil and water. To avoid this expen-
           +        ( ρb v a ) · ∇ a Wab
                                 ¯ρb                                              sive computational cost, a robust SPH approximation for the ﬂuid
                      b=1
                                                                     pressure gradient proposed by Bui and Fukagawa (2013 ), which au-
                   N  ¯m b                                              tomatically accounts for the dynamic boundary condition between
          =        ( v a −v b ) · ∇ a Wab                  (51)
                  n b                                      submerged solid phase and water, is adopted in this work. Accord-
                    b=1                                                        ingly, the second term in the right hand-side of Eq. (55) can be
   Similarly, by applying the same approach undertaken to obtain    approximated using the following equation:
Eq. (51) , the SPH approximation of the second term in the right
hand-side of Eq. (17) is:                                      1               N     p wi −p w j                                                          n s ∇ p w  = n i    ¯m j       ∇ i Wij                 (59)
                                                                                                                                                                                                                                       j                              N                                                       ¯ρs                    i       j=1             ¯ρi ¯ρ
 1 −n w             1 −n a     ¯m b    s       s             =      ρw ( ∇ · v s )                                 v a −v b   · ∇ a Wab     (52)    where p wi is the pore-water pressure at the location of a soil par-   n w                         a                     n a     n b
                                 b=1
                                                                                     ticle i and is calculated by taking the integration of the pore-water
where v sa and v sb are the velocity of solid phase at the location of    pressure from surrounding water particles located within the sup-
ﬂuid particle a and particle b , respectively. The velocity of solid     port domain of the soil particle i as follows:
phase at the location of ﬂuid particle a is calculated using the fol-
                                                        M  ¯m a      M  ¯m alowing equation:
                                                         p wi =      p a Wia /   Wia                              (60)
                                                                                                          ¯ρa                                                                                                                             ¯ρa    M         M                                                                    a =1                                                                                                              a =1
 a       ¯m i           ¯m i
          v i Wai /           Wai                                (53)v s =                                                               The SPH approximation of the last term in the right hand-side               ¯ρi                                   ¯ρi
            i =1                        i =1                                                     of Eq. (55) , i.e. seepage force per unit volume, is quite straight for-
   Substituting Eqs. (51) and ( 52 ) into Eq. (17) yields the following    ward as it does not involve any spatial derivative. However, it is
SPH approximation formulation for the mass balance of ﬂuid phase     noticed that the water velocity (v w ) in this formulation should be
in the deformable porous medium:                                    interpreted as the water velocity at the location of soil particle (not
                                                                   the velocity of water particle). This velocity is denoted as v sw and
d ρa    N  ¯m b                1 −n a  N  ¯m b    s       s             can be obtained using the similar approach undertaken to evalu-   =               ( v a −v b ) · ∇ a Wab +                                         v a −v b   · ∇ a Wab     ate the pore-water pressure at the location of soil particles, i.e. Eq. dt         n b                             n a     n b
        b=1                                b=1                          (60) . Accordingly, the seepage force term can be approximated us-
                                                           (54)     ing the following equation:

3.4. SPH approximations of momentum equations for solid             γw n 2w            γw ¯n 2ai  M  ¯m a    s           M  ¯m a
                                                                                  ( ¯v w −v s )  =              (v a −v i )Wia      Wia                                                                                                          ¯ρs k                                                                                                                                                                                                         i       ¯ρi k i    a =1 ¯ρa                      a =1 ¯ρa   The SPH approximation of the momentum equation for the
solid phase in the deformable porous medium is presented in this                                                                (61)

### Page 8

H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264                                  251

where ¯n ai is the arithmetic averages of the void fraction of soil and      3.5. SPH approximations of momentum equation for ﬂuid phase
water particles.
   Alternatively, a more formal form of the seepage force term,       As discussed in Section 2.5 , the two-step prediction-correction
which conserves both linear and angular momentums, can be ob-    time integration scheme is chosen to advance the velocity and potained by smoothing with the kernel employing the following in-     sition of the water phase. Thus, the SPH approximation for the motegral interpolation ( Bui et al., 2007; Monaghan, 1997 ):            mentum equation of the water phase will be derived in accordance
                                                               with the predictor-corrector scheme, i.e. Eqs. (34 )–( 41 ), using the
 γw n 2w                                                                  similar approach undertaken to derive the momentum equation        ( v w ( r ) −v s ( r ) )
    ¯ρs k                                                                       for the solid phase. The momentum equation of the ﬂuid phase
      γw n 2w       v ′ ·   r ′             ′         ′            ′                             is rewritten as follows:                                   r W r −r d r             (62)  = ϑ
                                                          d v w                  n 2w             ¯ρs k       (  r ′ ) 2 + η2                                            = −1 ∇ p w + g −γw   ( v w −v s )                     (66)
                                                                       dt     ρw              ¯ρw k
where:
                                                               The solution of the above equation in the two-step prediction-
  v ′ = v w ( r ) −v s r ′   and    r ′ = r −r ′                    (63)     correction time integration requires the approximation of the fol-
                                                                lowing equations:
   In Eq. (62) , η2 is a clipping constant (taken as 0.001 h 2 ), which                            2
                                                                                         ∗         t         n wprevents singularities when a water particle and a soil particle co-    v w = v w +  g −γw   ( v w −v s )    t                         (67)                                                                             k
incides, and ϑ is a constant equal to the inverse of the number of
dimensions, i.e. ϑ = 1/2 for two-dimension and ϑ = 1/3 for three-
                                                                                                 t+1
                                                                        w     t                                   (68)dimension. The clipping constant is effective only when the dis-    vt+1w = v ∗w −1 ∇p
                                                                     ρ∗w
tance between two SPH particles is less than 0.1 h In reality, such
a close distance (i.e. less than 0.1 h) should be avoided in SPH sim-        1     t+1    ρ0w −ρ∗w   −n w                                                    −1                                                          ∇ · v s                 (69)                                                                  w  =ulations as it reduces the accuracy of SPH approximation. Never-  ∇ · ρ∗∇p                                                                                n w   t                                                                        ρ0w   t 2theless, when the distance between two particles is much larger
than 0.1 h, which is the case of our simulations, the inclusion of        In the ﬁrst prediction step, the pressure gradient is ignored and
this parameter introduces negligible errors when the clip constant    only the last two terms in the right hand-side of Eq. (66) are used
is taken to be less than or equal to 0.001 h 2 . In the subsequent     to predict a temporal velocity ( v ∗) as shown in Eq. (67) . Thus, SPH
sections, this clip constant will be adopted whenever required to    approximation of the seepage force term is required. By adopting
avoid numerical singularities in SPH simulations when two parti-    the similar approach used for the approximation of the seepage
cles are getting too close to each other.                                 force acting on soil particle due to the water ﬂow, two alternative
   The SPH approximation of Eq. (62) for a soil particle is obtained    SPH approximations of the seepage drag force acting on water parby replacing the integral by a sum over water particles located      ticle ( a ) due to surrounding soils ( i ) can be obtained as follows:
within the supporting domain of the soil particle:

                                                                                                            2                                                                                     2                         M                                                                                                                                                      ¯n       2                                                           n                                                                                              N  ¯m                                                                                                                    N  ¯m                                                                        γw                                                        γw                                                                                                                                                         ai                                       ¯m                                                                                  ·    n                                                a  γw                        γw                                       v ia                                                    r ia                                                               ¯n 2ai                                                     =                                                             w ( v w −v s )                                                                                                                                                                                                                                                                                                      i Wia                                                                                                                                                                                                                                                 i ( v a −v wi )Wia               = ϑ     w ( ¯v w ( r ) −v s ( r ) )                                                          r ia Wia                                                                  k                                                                                    k                                                                                                          ¯ρs                                                                                                                                                     ¯ρi                                                                                                                                                                                                                            i                                                                                                                                                                      ¯ρi                                                                                                                                                                                                            ¯ρi    k                                                                                                            a                                                                                                                                                                                                                                    i =1                                                                                                                                                                                                                                                                                          i =1    ¯ρs                                                     ¯ρa                                                             ¯ρi                              +                                              η2                                                                |2                                                            |r ab                                                        i                           k i  a                                 =1
                                                          (64)                                                                (70)

   Eq. (64)          shows                   that                      the                         seepage                                     force                                      per unit                                          volume                                                             acts like                                                                                                                       2                                                                                     2                                                                        M  ¯m                                                                                                                                                                                           ·                                                           n                                                                                            v                                                                                                                                                                                                                                            i ¯n                                                                                         γa                                                                                                                                                                                  ai                                                                                                                    r ai                                                                                                                                                                        aia  repulsive            force             when                          particles                                 are                                    approaching,                                          and                                                                                    if                                                      they                                                               are     γw                                                     = ϑ                                                                                                                          r ai Wai    (71)                                                             w ( v w −v ws )                                                                  k                                                                                 ¯ρw                                                                                                                                        ¯ρa                                                                                   k i                                                                                                                                                                       ¯ρi                                                                   +                                                                                                     η2receding,              it             acts like                  an                           attractive                                       force.                                         This                                                force                                                       acts                                                     along                                                            the                                                                                                                                                 |r                                                                                                                                                     |2                                                                                                                                                                                ai                                                                                                             a                                                                                                                                                                                                                               i =1
line connecting two particles, and thus the conservation of linear
                                                               The second form of the seepage force is selected for consistencyand angular momentum is guaranteed. In this paper, Eq. (64) is
                                                               with the recommendation for the solid phase. Accordingly, the in-used rather than Eq. (61) . Both formulations yield similar results
                                                                   termediate temporal velocity of the ﬂuid phase inside the porousaccording to our numerical tests; however, in our experience Eq.
                                                         medium, i.e. Eq. (67) , is updated using the following equation:(64)  is more robust because  it requires no additional computational cost to calculate soil velocity at the location of water par-                   M      2
                                                                                         ∗        t          γa     ¯m i ¯n ai   v ai · r aiticle.                                                                                                                   r ai Wai     t       (72)                                                          v a = v a +  g −ϑ
                                                                             k i                                                                                                                              ¯ρa ¯ρi    |r ai |2 + η2    Finally, substituting Eqs. (57) , ( 59 ) and ( 64 ) into Eq. (55) yields                                                                                                                                                                                                               i =1
the following the SPH approximation for the momentum equation
                                                     On the other hand,  for the ﬂuid ﬂow outside the porous
of a soil particle in the deformable porous medium:
                                                         medium, the seepage force vanishes and the water phase becomes
       N                               N                              inviscid ﬂuid. However, to simulate more realistic behaviour of the
d v i           σ′ i   σ′ j                     p wi −p w j
  =    ¯m j   +  + C ij  ·∇ i Wij −n i    ¯m j       ∇ i Wij    ﬂuid ﬂow, viscosity should be considered for the motion of the
 dt                                                                                                                          j              ﬂuid phase. Accordingly, for the water ﬂow outside the porous        j=1                  ¯ρ2i    ¯ρ2j                     j=1            ¯ρi ¯ρ
           M      2                                       medium, the standard viscosity formulation commonly used for                  ¯m                                                 ·                       v                        a        γw                                             ia                               r ia                                ¯n ai                                                           ﬂow ( Shao                                                                               and                                                                                                              Lo,                                                                                    2003                                                                                                                                             ) is                                                                                                     adopted                                                                                                      and                                                                                                                         the                                                                                                                                                   inter-    + ϑ                                      r ia Wia + g i             (65)     free-surface
                           ¯ρa                             ¯ρi                  +                            η2                                  |r                                      |2                                                               mediate temporal                                                                                               velocity                                                                                                         of                                                                                                 the                                                                                                ﬂuid                                                                               ﬂow                                                                                                                   outside                                                                                                                        the                                                                                                                     porous                                           ai          k i  a =1
                                                    medium is:
where C ij is a stabilisation term utilised to remove the stress ﬂuc-
                                                                                N  ¯m b 4( νa + νb )  vtab · r abtuation and tensile instability in soils ( Bui et al., 2008; 2011a ). Eq.       ∗        t                                                              ∇ a Wab     t      (73)                                                          v a = v a +  g −(65) can be solved using the standard leap-frog integration scheme                                                                       n b ( ρa + ρb )2 |r ab |2 + η2                                                                                                                                                                                                             b̸= a
if the effective stress tensor and pore-water pressure are known.
Thus, it is necessary to establish SPH equations for these quanti-    where νa and νb are the kinematic viscosity of water particle a
ties.                                                        and b, respectively.

### Page 9

252                                        H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264

   Next, the SPH approximation for the gradient term of the pore-     deriving the governing equations for the two-phase mixture. For
water pressure is needed to adjust the velocity of water particles    the case of a rigid porous media, the additional source term due
in the correction step; see Eq. (68) . The gradient of the pore water     to soil deformation vanishes and Eq. (78) returns to the normal
pressure can be written as follows:                                   pressure Poisson’s equation for incompressible ﬂow. Eq. (78) can
                            t+1          t+1                          be solved eﬃciently using a precondition conjugate gradient itera-
                    p w                              p w           t+1                  − −1 ∇p        w   = −∇                                                ∗ ∇ρ∗w                (74)     tive method ( Shao and Lo, 2003 ) that involves solving large sparse   ρ∗w          a        ρ∗w    a    ρ2w          a                    systems of linear equations for large scale applications, which is
                                                                  not straightforward. Alternatively, a rather simpler approach which   Applying Eq. (46) to the gradient terms in the right hand-side
                                                                   uses a fully explicit integration scheme ( Nomeritae et  al., 2016 )of Eq. (74) yields the following SPH approximation for the pressure
                                                               can be applied to solve the above pressure Poisson’s equation ingradient of a certain ﬂuid particle a :
                                                                 a more eﬃcient way. The latter approach is adopted in the current
                                                         work                                                                    based                                                                    on                                                                                                               its                                                                                             merits, and                                                                                                the water pressure                                                                                                                                of                                                                                                                  a                                                                                                                                   certain                                                                                                            wa-                    N  ¯m b  pt+1a                              pt+1b           t+1                    + −1 ∇p                        ∇ a Wab           (75)        w   = −                                                                              ter particle                                                                          a                                                                                                            is                                                                                        calculated                                                                                   by rearranging                                                                                                                    Eq. (78)                                                                                                                               in                                                                                                                      the                                                                                                                              following
   ρ∗w          a     b=1 ¯ρb   ρ∗a    ρ∗b                                                            manner:
   Here, we have adopted the assumption of ρ∗a = ρ∗b to simplify                 N      t+1
the approximation, taking into consideration the incompressible          B a +   A ab p b
condition of the ﬂuid ﬂow.                                    pt+1a  =      b=1N                                             (79)
    Finally, to evaluate the pressure gradient in Eq. (75) , one needs
                                                                A ab
to solve the pressure Poisson’s Eq. (69) that involves the Lapla-                 b=1
cian operator and divergence of the velocity which need to be
                                                          where A ab and B a are deﬁned as follows:approximated in the SPH framework. The Laplacian operator can
be formulated in a standard way using the combination of the di-           N  ¯m b    8     r ab · ∇ a Wab
                                                                                                                              (80)vergence        and              gradient                       operators                                   of SPH                                         formulations.                                                 However,                                                                                            it   A ab =

                                                                                                                                                                                      b̸= ahas been         found                 that the                            resulting                                second                                              derivative                                                          of the ker-                                                               n b  ρ∗a + ρ∗b 2 (r 2ab + η2 )
nel is very sensitive to particle disorder and could easily lead to
pressure instability and decoupling in the computation due to the        ρ0a −ρ∗a   1 −n a M  ¯m j                                                 +                                                       B a =                                                                                                                                                                         ¯v ia −¯v ja   · ∇ a Wab            (81)co-location of the velocity and pressure ( Shao and Lo, 2003 ). In                                                                     n a   t                                                                                                                                        ¯ρ j                                                             ρ0a   t 2                                                                                                             j=1
this work, the same approach suggested by Shao and Lo (2003 ) is
adopted. The approach is a hybrid of a ﬁnite difference approxima-        For a small time increment of the explicit scheme, the value
tion and the standard SPH approximation for the ﬁrst derivative. By     of pt+1                                                                      can be assumed to be equal to ptb , thus there is no need                                                                                        b
considering the Taylor series expansions of the pressure and the     to perform numerical iteration for the solution of Eq. (78) . Accorddensity, taking the integral interpolation of the Taylor expansion     ingly, the pressure of each ﬂuid particle can be explicitly computed
functions and ﬁnally adopting the standard SPH approximation for     in time using the following simpliﬁed equation:
the gradient term, the following SPH approximation for the pres-
                                                                             N
sure Poisson equation can be derived:                                                                                                 t
                                                             B a +   A ab p b
                                                                              t+1         b=1
                                                                                       a  =     N                                              (82)     1     t+1      N  ¯m b    8     pt+1a −pt+1b    r ab · ∇ a Wab      p
                                                               A ab∇ · ρ∗∇ p     a =  b̸= a                   n b  ρ∗a + ρ∗b 2         r 2ab + η2                           b=1
                                                            (76)         Finally, at the end of each round of computation, the density of
                                                                each ﬂuid particle is forced to its initial density and thus the in-
   The divergence of the velocity can be approximated straightfor-
                                                                   compressible condition of the ﬂuid phase is also further enforced
wardly using the same approach employed to derive the continuity
                                                                              after each time step. The recent numerical tests for the ﬂuid ﬂow
equation, which yields:
                                                                  presented in Nomeritae et al. (2016 ) show that the proposed ex-
 1 −n w         1 −n a  N  ¯m b    s       s                                   plicit incompressible SPH method (EISPH) is four times as fast as
     ∇ · v s  =             v a −v b   · ∇ a Wab          (77)    the δ-SPH ( Antuono et  al., 2010 ), which is one of the most ad-  n w   t          a   n a   t       ¯ρb
                            b=1                                    vanced weakly compressible SPH models, while yielding the same
where v sa and v sb are the velocity of solid phase at the location of     level of accuracy. For further details of this approach, we refer
ﬂuid particle a and particle b , which are evaluated using Eq. (53) .     readers to prior publication ( Nomeritae et al., 2016 ).
Substituting Eq. (76 ) and ( 77 ) into Eq. (69) yields the following
coupled pressure Poisson’s equation for the ﬂuid ﬂow through the      3.6. SPH approximation of soil constitutive relation
deformable porous medium:
  N                     t+1    t+1                                           In the SPH framework, the  explicit expression  of the time
      ¯m b    8     p a −p b    r ab · ∇ a Wab                           derivative of a stress-strain relation is required for the numerical

    b̸= a    n b  ρ∗a + ρ∗b 2         r 2ab + η2                                    solution. By further expanding Eqs. (28) and ( 29 ), enforcing the
                                                                     consistency of the yield function and applying the SPH approxi-
     ρ0a −ρ∗a   1 −n a  N  ¯m b    s       s                              mation, the following explicit expression of the stress rate tensor  =         +                           v a −v b   · ∇ a Wab            (78)                                                                            at a soil particle i can be obtained ( Bui and Fukagawa, 2013 ):              n a   t                                      ¯ρb      ρ0a   t 2                         b=1
   Compared to the free-surface incompressible ﬂuid ﬂows or any    dσ′ αβi        αγ  βγ      γ β  αγ       αβ       γ γ                                             = σ′ i ω˙  i  + σ′ i ω˙  i + 2 G i e˙ i + Ka ε˙ i  δαβiprevious two-phase coupled models following the original two-       dt
phase ﬂow framework proposed by Bui et al. (2007 ), the current                                          αβ
                                                                  −˙λi 3 Ki αψ i δαβ + ( G i /   J2 i )i s ′ i                   (83)framework is novel in the sense that an additional source term due
to solid matrix deformations is taken into consideration when solv-                                                                                                                     αβ
ing the pressure Poisson’s equation for the pore-ﬂuid. Furthermore,    where G i is the shear modulus, K i is the bulk modulus, ε˙ i   and
                                                                 αβ                                              αβ    αβ
the variation of void fractions is fully taken into consideration in   ω˙ i   are the strain rate spin rate tensors, respectively; e˙ a = ε˙ a −

### Page 10

H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264                                 253

                                                             Fig. 2. Schematic view of water seeping through porous media.

13 ε˙ aγ γ δαβ is the deviatoric shear strain rate tensor, s ′ αβi    is the de-     following equation:
viatoric shear stress tensor and λi˙   is the rate of plastic multiplier        M  ¯m a
computed by:                                                               s ri =   Wia                                            (87)                                                                                                         ¯ρa
                                                                                            a =1
              γ γ             αβ αβ
                                                          where the summation has been taken over water particles. Owing    3 αφ i Ki ε˙ i  + ( G i /   J2 i ) s ′ i  ε˙ i                                                           (84)λi˙ =
          9 αφi Ki αψ i + G i                                            to the nature of SPH summation approximation, Eq. (87) will re-
                                                                               sult in s r ≈1 for soil particles whose supporting domain are fully
   The strain rate and spin rate tensors are calculated by:
                                                                        ﬁlled by water particles and s r = 0 for soil particles whose their
          N                      N                               support domain has no water particles. On the other hand, for soil
 αβ   1      ¯m j   α    α              ¯m j   β    β
ε˙ i  =            ( u˙ j −˙u i ) ∇ i Wij +        ( u˙ j −˙u i ) ∇ i Wij    (85)     particles located in the transition zone, because of the truncation     2                    ¯ρ j                                                      ¯ρ j                               of the kernel function, Eq. (87) will result in a degree of saturation            j=1                                         j=1
                                                                           of less than unity. The range of the transition zone above the sat-
  αβ   1   N  ¯m j   α    α          N  ¯m j   β    β                  urated soil domain depends on the smoothing length of the kernel
ω˙  i  =            ( u˙ j −˙u i ) ∇ i Wij −        ( u˙ j −˙u i ) ∇ i Wij   (86)     function.      2        ¯ρ j                                ¯ρ j
             j=1                          j=1
                                                                                      3.8. Coupled SPH algorithm for the ﬂuid-solid mixture
   The validations of the above soil model within the SPH framework has been extensively documented in previous works ( Bui and                                                               The coupled SPH algorithm for the ﬂuid-solid mixture requires
Fukagawa, 2013; Bui et al., 2008 , 2011a , 2014; Chen and Qiu, 2012;                                                                   information from two phases to be exchanged during the compuDeb and Pramanik, 2013; Nguyen et  al., 2017 ), in which excel-                                                                            tational process. The outline of the proposed coupled algorithm is
lent agreements between SPH solutions and ﬁnite element as well                                                       shown in Fig. 3 and details are explained below:
as experiments have been achieved. To avoid repetition, we refer
readers to previous publications for details of the validation pro-           (i) At the  start  of the computational procedure, both ﬂuid
cess and SPH performance for elaso-plastic computation.                 and solid particles are generated and each of which carries
                                                                                   their own physical properties and ﬁeld variables. The pro-
                                                                      cedure for searching contact interaction will be then under-
3.7. Calculation of the degree of saturation using SPH approximation
                                                                        taken to determine interaction pairs of particles in the same
                                                                    phase and from different phases. The interaction pair is only
   In soil mechanics, soil is said to be fully saturated  if the de-
                                                                  formed if the distance between two particles is less than the
gree of saturation is S r = 1, dry if the degree of saturation is S r = 0,
                                                                             radius of the supporting domain, which is equal to 2 h in
and unsaturated  if the degree of saturation is 0 < S r < 1. Dealing
                                                                                     this work.
with unsaturated soil behaviour is a quite complicated task and
                                                                                                        (ii) Next, based on the contact information, the void fraction of
is beyond the scope of this paper. Here, we mainly consider two
                                                                     ﬂuid particles, reference velocities of each phase particles at
conditions of soil, dry and fully saturated conditions. There is also
                                                                         the location of the other, and the pore-water pressure at the
a zone between dry and saturated soil which calls transition zone
                                                                               location of solid particles are calculated. This information is
rather than unsaturated zone. Fig. 2 shows a schematic diagram
                                                                      then used in the governing equations of each phase to conwhich outlines the progress of water seeping through the porous
                                                                                 sider the coupling effects in the seepage force and pressure
media. It can be seen that when a soil particle is fully submerged
                                                                               Poisson’s equation.
in water, its support domain is fully ﬁlled by water particles. On
                                                                                                         (iii) Finally, the governing equations of each phase will then be
the other hand, those located far away from water particles in the
                                                                           solved taking into consideration coupling terms calculated in
dry zone have no water particles in their supporting domain. For
                                                                          Step ii) and ﬁeld variables of each phase will be updated at
those solid soil particles located in the transition zone, part of their
                                                                         the end of each time step.
support domain is ﬁlled with water particles, while the other part
is ﬁlled with solid particles. The above soil condition can be ef-                                                                                 4. Treatment of boundary conditions
fectively modelled by taking advantage of the SPH approximation,
Eq. (45) . Accordingly, the degree of saturation of a soil particle i in                                                                       Despite its advantage in handling large deformation and movthe current computational framework can be estimated using the                                                                      ing interface problems, the treatment of solid or prescribed bound-

### Page 11

254                                        H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264

                                                            meable porous media (see Section 5.3 ) is modelled following the
                                                                            original work proposed by Lastiwka et al. (2009 ), in which an in-
                                                  ﬂow zone is deﬁned outside the ﬂow domain by extruding the in-
                                                                                     let boundary in the upstream direction. The length of the inﬂow
                                                             zone must be at least equal to the size of the kernel supporting do-
                                                         main used in the SPH simulation. Particles inside the inﬂow zone
                                                                             will move with a prescribed velocity, while leaving pressure and
                                                                      density to be determined by the information propagated from the
                                                                ﬂuid domain. During the computation, for any particle that moves
                                                                  out of the inﬂow zone at the boundary between the ﬂuid domain
                                                           and the inﬂow zone, a new particle will be created at the inlet
                                                              upstream to compensate for the particle loss.

                                                                                 5. Validations and application of the proposed model

                                                                             In this section, a series of benchmark tests are performed to
                                                                          validate the proposed SPH framework. In the ﬁrst test, a simple
                                                             problem of a fully submerged homogenous soil medium subjected
                                                                         to a gravity load is simulated. The numerical solutions obtained
                                                                      are validated against the analytical solutions for the hydrostatic
                                                                water pressure and soil stresses. The second test concerns a tran-
                                                                           sient seepage ﬂow through a linear elastic isotropic homogenous
                                                                                    soil embankment, in which the solutions of the ﬂow properties
                                                           and the distribution of pore-water pressure obtained with the pro-
                                                              posed framework are compared with FEM solutions. In the third
                                                                                       test, the proposed SPH framework is validated against several ex-
                                                                 periments of water ﬂows through rockﬁll dams performed in the
    Fig. 3. SPH computational procedure to solving coupled ﬂuid-solid mixtures.      XPRESS and E-DAMS projects ( Larese, 2012 ). In these experiments,
                                                                            different ﬂow discharges were imposed and corresponding evolu-
                                                                          tions of the pressure head were recorded; they will be used for the
                                                                         validation of the proposed framework. Finally, the proposed SPH
ary conditions in the SPH method is not straightforward. This is
                                                            framework is applied to simulate a laboratory scale experiment of
because when a particle (or material point) approaches the solid
                                                                 a seepage ﬂow induced large deformation and failure of an emboundaries of a problem domain, the supporting domain of a SPH
                                                          bankment conducted by the ﬁrst author.
kernel function will be truncated by the boundary, and thus SPH
approximations are no longer accurate. Accordingly, the treatment
of SPH boundary conditions has been an ongoing concern for an      5.1. Veriﬁcation with analytical solutions for initial in-situ stresses
accurate and successful implementation of the SPH approach. In
this work, two different types of boundary conditions are required,      A plane-strain problem of a saturated soil medium submerged
one for the solid porous medium phase and the other for the     in water is considered in this section. The main purpose of this
ﬂuid phase. The boundary conditions for the deformable porous    example is to examine the initial in-situ stress distribution inside
medium generally consist of full-ﬁxity and free-roller wall bound-    the undisturbed soil medium when the velocity of the water phase
aries, which can be modelled using ﬁxed boundary particles ( Bui et      is assumed to be zero. The geometry and boundary conditions of
al., 2008 ) and ghost particles ( Libersky et al., 1993 ), respectively.      the saturated soil medium are taken similar to Bui and Fukagawa
  On the other hand, three types of boundary conditions for the    (2013 ) as shown in Fig. 4 a. However, in contrast to Bui and Fuka-
ﬂuid phase are required in this work. These include impermeable    gawa (2013 ), both the soil and water are modelled herein by the
rigid wall boundary, free-surface boundary and water inlet bound-    SPH method. The soil is assumed to be an elastic isotropic hoary. The impermeable rigid wall boundaries of the ﬂuid phase can    mogenous material with the following properties: Young’s modbe simulated following the approach proposed by Shao and Lo     ulus E = 100 MPa, Poisson’s ratio ν = 0.3 and the dry unit weight
(2003 ), in which two set of ﬁxed boundary particles are used to    γ s = 26 kN/m 3 . The unit weight of water is γ w = 9.81 kN/m 3 . The
model the wall boundary (wall particles and dummy particles). The     porosity, i.e. void fraction of water, is kept constant at n = 0.3 as
pressure Poisson’s Eq. (82) is solved on the wall particles and then     this example deals with a still water body. In the SPH simulation,
copying to the dummy particles to satisfy the Neumann boundary    the model test is discretised using 5500 particles (3000 particles
condition, while the velocities of both wall and dummy particles     for water body and 2500 particles for soil medium) arranged in
are set to zero to represent the non-slip boundary conditions. In    a regular lattice with a uniform spacing of 0.2 m and a smoothaddition, to prevent ﬂuid particles moving too close to the solid     ing length of h = 0.24 m. Boundary conditions are treated as follows
walls for simulations with long physical time problem, a repulsive     (see Section 4 ): for the soil medium, ﬁxed boundary particles are
force following the Lennard–Johns form ( Monaghan, 1994 ) is ap-    used to model the full-ﬁxity at the bottom, while ghost particles
plied to ﬂuid particles that move close to the wall boundary.           satisfying the free-roller condition are assigned to vertical sides;
   The free-surface boundary condition for the ﬂuid phase re-     for the water body, wall and dummy particles were used to enquires a zero pressure value for those particles located on the     force the no-slip boundary condition. Initially, the soil stresses are
free-surface. In this work, a particle is regarded as a free-surface     set to zero, while the water pressure is set to the hydrostatic conparticle if its initial density ﬂuctuation exceeds 1% below that of     dition. The gravity loading is then applied in a single increment
the inner ﬂuid. A Dirichlet boundary condition of zero pressure is     to obtain the initial in-situ stress distributions in the soil medium.
then given to this particle during the computation. Finally, the in-     In order to avoid stress ﬂuctuations from the sudden application of
let boundary condition for incoming ﬂow discharges through per-     self-weight loading and the zero-energy mode in SPH, the damping

### Page 12

H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264                                 255

Fig. 4. Model test of a fully submerged soil medium in a still water body. (For interpretation of the references to colour in this ﬁgure legend, the reader is referred to the
web version of this article.)

                                                 Fig. 5. Comparisons of the stress proﬁled between the SPH and theoretical solutions.

force suggested by Bui and Fukagawa (2013 ) is adopted for soil par-    the analytical solutions for the horizontal stresses, vertical stresses
ticles with the damping coeﬃcient taken to be ξ = 0.02; no damp-    and pore-water pressure. In the SPH simulation, the soil stresses
ing force is applied to the water phase. In addition, for the purpose    and pore-water pressure are computed at the vertical central line
of validating the initial in-situ stresses under the quasi-static con-     of the soil medium with an interval of 1 m from the ground surface
dition, the seepage force is deactivated in the current simulation.     to the base. It can be seen that the current numerical model can
No additional efforts are taken to enforce the dynamic boundary     predict well the initial in-situ stresses and the pore-water pressure.
condition on the interface between the submerged soil and water.     At the ground surface, the effective stresses are zero and the total
    Fig. 4 b shows the colour plots of the in-situ effective vertical     stresses are equal to the weight per unit area of the free-standing
stress distribution in the soil medium using the proposed two-     water. At other locations, the numerically calculated stresses agree
phase SPH framework. A smooth stress proﬁle is achieved within     well with the analytical results. The hydrostatic pore-water presthe soil medium, suggesting that the explicit ISPH solution for the     sure is also correctly predicted using the explicit-ISPH model. The
pore-ﬂuid is stable. The effective vertical stress at the ground sur-    good agreement between SPH computation and theoretical soluface is zero and this corresponds to the fact that the total vertical     tions conﬁrmed that the coupling procedure in the two-phase SPH
stress is equal to the weight of the free standing surface. Similar    framework works well.
to the ﬁnding reported in Bui and Fukagawa (2013 ), although no
additional computational effort is taken to apply forces due to sur-      5.2. Veriﬁcation with FEM solutions for seepage ﬂow behaviour
charge pressure to particles located at the interface between soil
and water, the coupled numerical solution remains stable thanks        In this second test, the transient seepage ﬂow through an elasto the robust inclusion of the pore water pressure into soil parti-      tic isotropic homogeneous soil embankment is considered. The socles using Eq. (59) . On the other hand, a problem of particles ex-     lutions of the ﬂow properties and the distribution of pore water
pelling from the ground surface is observed if Eq. (58) is used to    pressure obtained with the two-phase SPH framework are comapproximate the gradient of the pore-water pressure. The accuracy    pared with the steady-state solutions obtained by the PLAXIS ﬁ-
of the proposed two-phase SPH framework is examined in Fig. 5     nite element (FE) commercial software package. For the purpose of
by comparing the results predicted by the SPH simulations with     testing the accuracy and performance of the two-phase SPH model

### Page 13

256                                        H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264

                                                           Fig. 6.  Initial geometry and setting conditions of an embankment.

for the seepage ﬂow through the embankment, the soil material     stage of the development, the wetting front of the seepage ﬂow
is assumed to be elastic to avoid the failure of the embankment,    develops rapidly in both vertical and horizontal directions owing
which could not be handled by FEM.                                   to the rapid increase of water level in the reservoir. Subsequently,
   The geometry and dimensions of the embankment are shown    the wetting front mainly progresses in the horizontal direction in
in Fig. 6 . The embankment model is 40 cm high with 40 cm top    which the inﬁltration process occurs faster at the bottom slope due
width and both the upstream and downstream slopes are  1:1.     to the increase of pressure towards the bottom. After reaching the
The soil properties are: Young’s modulus E = 3.0 MPa, Poisson’s ra-    downstream slope toe, the wetting front gradually propagates uptio υ = 0.3, the dry unit weight γ s = 25.5 kN/m 3 , initial permeabil-    ward due to the horizontal seepage force and ﬁnally reaches the
ity 1.1 × 10 −4 m/s and initial porosity 0.4. In the PLAXIS FE-model,    steady stage at 1151 s. The progressive development of the porethe embankment is discretised using 1568 15-node triangular el-    water pressure inside the embankment shows a trend similar to
ements, which correspond to 18,816 materials points  (i.e. Gauss     that of the wetting front. A very smooth pore-water proﬁle is obpoints). The constant ﬂux equivalent to the water head level of     tained from the proposed two-phase SPH framework thanks to the
30 cm is applied to the upstream slope of the embankment in a     explicit ISPH scheme employed. We noted that the weakly comform of the linear increasing head pressure on the side boundary.     pressible SPH technique adopted in most previous two-phase SPH
In the SPH model, on the other hand, the embankment is modelled    works showed pressure ﬂuctuation. This can be compromised by
with 3160 particles arranged in a regular lattice with an initial    adopting some recent SPH improvements such as using density
spacing of 1 cm and the smoothing length is 1.2 cm. To model the     ﬁlter techniques ( Colagrossi and Landrini, 2003 ) or adding a difincoming water ﬂow, SPH particles representing the water phase     fuse term into the continuity equation ( Antuono et al., 2010 ). Howare continuously generated and dropped gently from the left reser-     ever, the capability of these techniques to align the SPH simulation
voir during the computational process. It takes approximately 30 s    time to a long physical time problem is still questionable. The proto reach the required water level of 30 cm. In order to maintain    posed explicit ISPH, on the other hand, can handle these problems
the required water level in the reservoir, a computational routine is    without any problem owing to the fact that the density is reset
developed to generate water particles if the maximum water level     after each time step to achieve the incompressibility assumption.
in the reservoir is less than 30 cm. Water particles that move out       The accuracy of the proposed two-phase SPH framework is furof the right boundary are deleted from the computation to save     ther examined by comparing its solutions with those obtained by
the computational cost. The initial in-situ stress condition of the    the PLAXIS FE-model. Because the PLAXIS FE-model could not simembankment in both FEM and SPH simulations is obtained by ap-     ulate the transient coupled behaviour of seepage ﬂow development
plying gravity loading ( Bui and Fukagawa, 2013 ).                  shown in Fig. 7 , the ﬁnal steady-state solutions are used as the
    Fig. 7 shows the progressive development of the saturated zone    benchmark for the SPH simulations. Fig. 8 shows the comparison of
due to the seepage ﬂow and the corresponding pore-water pres-    the phreatic surface and the contour plot of the pore-water pressure distribution inside the embankment. On the left side of the     sure distribution inside the embankment. There is a good agree-
ﬁgure, the orange colour represents the fully saturated zone where    ment on the predictions of the ground water table by the SPH
S r = 1, whereas the blue colour indicates the fully dry zone where    framework and PLAXIS FE-model. The ﬁnal shape of the ground
S r = 0. There is a transition zone in which the degree of satura-    water table in both simulations is found to be a curve line with the
tion is in a range of S r = 0.0–1.0. It should be noted that this is a    upstream end normal to the upstream equipotential line (i.e. the
numerically-generated zone which is due to the truncation of the    upstream slope) and the downstream end tangent to the downkernel function at the boundary between the saturated and dry    stream slope. These results agree well with theoretical/graphical
zone in the SPH approximation of the degree of saturation (see     solutions as well as actual seepage behaviour through the earth
Section 3.7 ). On the right side, the zero-pressure head line is re-   dam reported in the literature. The pore-water pressure distribudrawn by connecting all water particles located on the free-surface     tions of SPH and FEM solutions are in very good agreement and
inside the embankment. It is noticed that there is also a thin zone    the pressure value at the upstream slope toe corresponds with the
of 2 h wide above these lines in which the pore-water pressure    water level in the reservoir of 0.3 m. This suggests that the provalue is not zero. This is again a numerically-generated value due    posed two-phase SPH framework could achieve high accuracy in
to the truncation of the kernel function when calculating the pore-     simulations of the seepage ﬂow through earth structures.
water pressure for soil particles. In fact, the kernel truncation error
in SPH is an interesting feature which can be very useful for the                                                                                      5.3. Validation with experiments from CEDEX
modelling of unsaturated soils whereas there is always a transient
zone between saturated and dry soils.                                                                             In this validation test, the experiments on the steady state seep-
    It can be seen that the progressive development of the seep-                                                                age ﬂow through a rockﬁll dam from XPRESS and E-DAMS projects
age ﬂow from the upstream slope to the downstream slope can be                                                                                           ( Larese, 2012 ) are simulated using the proposed two-phase SPH
well described using the two-phase SPH framework. In the early                                                                framework. These experiments were conducted in the Centre for

### Page 14

H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264                                 257

Fig. 7. Evolutions of the saturated zone and the pore -water pressure distribution predicted by the two-phase SPH framework. (For interpretation of the references to colour
in this ﬁgure legend, the reader is referred to the web version of this article.)

      Fig. 8. The ﬁnal phreatic surface and the pore-water pressure distribution predicted by the two-phase SPH framework (upper) and the PLAXIS-FE model (lower).

Hydrographical Studies of CEDEX to investigate the seepage ﬂow    mation on the phreatic surface inside the rockﬁll embankment at
through rockﬁll dams and serve as benchmarks to validate a parti-    corresponding locations.
cle ﬁnite element method (PFEM) code. The geometry setting and      Owing to the nature of a rapid ﬂow through high permeable
boundary conditions of the rockﬁll dam (Case A1) is shown in Fig.     rockﬁll porous media, the linear Darcy’s law adopted to calculate
9 . The rockﬁll dam is 1 m high, 3.2 m wide; both the upstream    the seepage force in the proposed two-phase SPH framework is
and downstream slopes are 1.5:1.0. The dam was constructed in    no longer applicable. In fact, the linear Darcy’s law is only valid
a ﬂume of 2.64 m width with several built-in sensors at the bot-     for laminar ﬂows in low permeability media where viscous forces
tom to record the pressure head and a regulation valve to control     are dominant, i.e. Reynolds numbers Re ∈ [1 −10] ( Bear and Cheng,
the incoming discharge. The rockﬁll material is quarry stone with    2010 ). For a high ﬂow rate through a highly permeable porous
D 50 = 35.04 mm and the porosity of n w = 0.4052. The dry and satu-    medium,  i.e. Re > 100, the viscous force  is dominated by the
rated densities are 1490 and 1910 kg/m 3 respectively. The incoming     inertial force which tends to produce instabilities causing turbu-
ﬂow discharge of Q = 25.46 L/s is imposed on the upstream slope     lence of the ﬂow; thus, the ﬂow rate is no longer linearly proand the steady ﬂow is achieved by keeping the constant ﬂow rate.     portional to the pressure gradient ( Bear and Cheng, 2010 ). SeepIn order to provide experimentally validated data for the numerical    age ﬂow through rockﬁll dams is an example of the ﬂow through
simulations, several pressure sensors were installed on the bottom    high permeable porous media, for which the linear Darcy’s law
ﬂoor of the embankment at the distance of 2.75, 3.25, 3.75, 4.3 m      is not applicable. In such cases, the nonlinear quadratic Darcy–
from the inlet water ﬂow. These experimental data provide infor-    Forchheimer’s law with empirical coeﬃcients taking into account

### Page 15

258                                        H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264

                                                Fig. 9. Geometry and setting conditions of the ﬂow through a rockﬁll dam experiment.

the physical properties of the rockﬁll material such as the size,      test, the curved shape of the ﬁnal water table inside the rockﬁll
porosity and shape  is widely employed  ( Larese, 2012 ). Accord-   dam is also achieved. The predicted phreatic surface at the location
ingly, in this particular application, instead of using the seepage     of the pressure gauges agrees very well with those measured in the
force based on the linear Darcy’s law,  i.e. Eq. (18) , the following    experiment (green dots A–D). In addition, the evolution of pressure
quadratic Darcy–Forchheimer’s resistance law with the Ergun’s co-    heads at four locations with time is plotted in Fig. 11 . As can be
eﬃcients is adopted:                                                   seen, steady state is reached at about 300 s, at which the pressure
                                                               heads at four locations are stable and agree well with the experi-
      μ      1 . 75 ρw n w
R = − n w  v ws + √  √    ∥ v ws ∥ v ws + p w ∇ n w       (88)    mental measurements. In short, thanks to the explicit ISPH model,
          k       150  kn 3 / 2                                    the pressure proﬁle of the water ﬂow and the time evolution of the
                                                                     pressure proﬁle at the four pressure gauges are very well simulated
where v ws is the relative vector velocity between water and soil
                                                                          in the numerical model. Very smooth pressure proﬁle is achievedparticles; ∥ v ws ∥ is the norm of the relative velocity; and k is the
                                                                          in the SPH simulation for the water ﬂow, both in the reservoir and
permeability coeﬃcient deﬁned as follows:
                                                                         inside the dam. Furthermore, the smooth transition of the pres-
      n 3w D 250                                                       sure curve is obtained at all measurement points, except the onek =                                                       (89)
    150 (1 −n w )2                                                         at the slope toe (Point D) which exhibits high pressure ﬂuctuation.
                                                                       This result is expected due to the sudden change of water velocity
with D 250 being the average diameter of the granular materials.       from the inside porous medium to free-surface conditions. On the
   In the SPH simulation, the above rockﬁll dam is modelled by    other hand, very high ﬂuctuations of the pressure proﬁle and pres-
4250 particles arranged in a regular square lattice with an ini-     sure gauge curves will be obtained if the weakly compressible SPH
tial spacing of 2 cm and a smoothing length of 2.4 cm. The rock-    model is adopted to simulate the water ﬂow, as in previous works
ﬁll dam is modelled as an elastic homogeneous material with the     utilising this model ( Bui et al., 2007; Grabe and Stefanova, 2015;
following material properties: Young’s modulus E = 3.5 MPa and    Maeda and Sakai, 2010; Zhang and Maeda, 2015 ).
Poisson’s ratio υ = 0.3. The incoming water ﬂow is modelled by       Comparing to the previous work utilising the PFEM to simumeans of periodic boundary condition described in Section 4 . For     late the same seepage ﬂow through the rigid rockﬁll dam ( Larese,
the incoming water ﬂow of Q = 25.46 l/s, the inlet water velocity    2012 ), the SPH simulation takes a longer time to reach the steadyis u in = 0.086 m/s, which corresponds to the height of the incom-     state water table level. This difference can be attributed to the noing ﬂow zone of h in = 0.12 cm, is adopted. No-slip boundary con-     slip boundary condition adopted in the current work for the ﬂuid
dition is applied to all boundaries for both water and solid phases.   ﬂow simulation. Nevertheless, both approaches only achieved good
In order to save the computational time, any water particle that    agreement with the experiment after adopting the seepage force
moves out of the rockﬁll dam and reaching the distance of 4.5 m    model based on the quadratic Darcy–Forchheimer’s resistance law.
is deleted from the computation. Similar to the previous test, the    Use of the seepage force model based on the linear Darcy’s law in
initial in-situ stress condition of the rockﬁll dam is obtained by    both the two-phase SPH model and PFEM led to signiﬁcant underapplying the gravity loading to solid particles ( Bui and Fukagawa,    estimation of the experimentally observed ﬁnal phreatic surface.
2013 ). The convergence of the SPH numerical results are also in-       The inﬂuence  of the material  porosity on the  steady-state
vestigated and it is conﬁrmed that the numerical solution is con-     phreatic  surface  is  investigated by  varying the  porosity from
verged at the spatial resolution of less than or equal to 2 cm.        n = 0.30, 0.35, 0.40 to 0.45, while keeping all other material prop-
    Fig. 10 shows the evolution of the water free-surface in the up-     erties and simulation conditions ﬁxed. It can be seen from Fig. 12
stream reservoir and inside the rockﬁll dam at several time inter-     that a uniform increase of the porosity results in a uniform invals. The green dots (A–D) represents the ﬁnal steady-state of the     crease of the phreatic surface which is consistent with the ﬁndphreatic surface obtained from the four pressure gauges installed     ing of ( Larese, 2012 ). Apparently, when the porosity reduces by
at the distances of 1.70, 2.20, 2.70 and 3.25 m from the upstream    50% (from 0.45 to 0.30), the intrinsic permeability, calculated by
slope toe in the experiment. It can be seen that the water level     Eq. (89) , declines more than 5 times, leading to an increase in
in the reservoir increases as the water starts ﬂowing in from the    the same amount of the ﬁrst two terms of the resistance in Eq.
water inlet gate. Because of the high permeability of the rockﬁll     (88) which makes the phreatic surface increase signiﬁcantly. The
material, the seepage ﬂow inside the dam is mainly driven by the    time to reach the ﬁnal steady-state of the phreatic surface also inincoming ﬂow velocity and progresses faster in the horizontal di-     creases as the porosity reduces.
rection. It takes approximately 64 s for the water ﬂow to reach the         Finally, the predictive capability of the proposed two-phase SPH
downstream slope toe. The phreatic surface inside the dam then    framework is further examined to analyse the experiment of tranrises simultaneously with the increase of the upstream water level     sitory incoming ﬂow discharges, Case A2 reported in Larese (2012 ).
in the reservoir. The steady state of the seepage ﬂow in the sim-     This example serves as a demonstration of the capability of the
ulation is achieved at around 300 s, although the water table has    proposed numerical framework to model a practical ﬂooding situalmost reached this level at around 190 s. Similarly to the previous

### Page 16

H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264                                 259

Fig. 10. Progressive development of the phreatic surface predicted by the two-phase SPH framework. (For interpretation of the references to colour in this ﬁgure legend, the
reader is referred to the web version of this article.)

### Page 17

260                                        H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264

                 Fig. 11. Evolution of pressure heads at four locations.                         Fig. 13. Evolution of the pressure head corresponding to raising inlet discharges.

                                                                                                     Table 1
ation where ﬂood curves of different incoming discharges can be                            Soil parameters used in simulations.
used as an input. Three levels of incoming discharges of Q = 25.26,                                 Initial water content ( w )    5(%)
51.75 and 69.07 l/s are imposed at the inﬂow gate in a total time                         Young’s modulus ( E )       3 Mpa
                                                                                                        Poisson ratio ( υ)            0.3of 450 s with a transition time of 10 s each to ensure smooth tran-
                                                                                                                      Friction angle ( φ)           31.2 °
sitory regimes as well as suﬃcient time to reach a steady-state of                                                                                                                                       Initial cohesion ( c )         0.55 kPa
each discharge in the experiment. The same geometry and bound-                          Dilatancy angle ( ψ)        10 °
ary conditions employed in the previous rockﬁll dam SPH simu-                             Particle density ( ρs )         2.6 (g/cm 3 )
lations are adopted in this test with the only difference being the                                 Initial porosity ( n )          0.4
                                                                                                                                       Initial permeability ( k 0 )      1.1 ×10 −4 m/sincoming ﬂow discharges. Fig. 13 shows the imposed incoming discharges and the corresponding time evolution of the pressure head
evaluated at the bottom ﬂoor at the location of 2.7 m from the
upstream slope toe  (i.e. back circle dots). The numerical results    more valid in the later stage of the experiment when there is no
show that, for the ﬁrst incoming ﬂow discharge (Q = 25.26  l/s),    more deformation of the rockﬁll dam.
the predicted ﬂow does not fully reach the steady-state condition
and therefore underestimates the measured pressure head (Point      5.4. Application for a seepage ﬂow-induced progressive failure
A). However, in the latter two incoming ﬂow discharges ( Q = 51.75
and 69.07 l/s), the ﬂow predicted by the two-phase SPH reaches        This section presents an application  of the two-phase SPH
the steady-state and the predicted pressure heads agree well with    framework to simulate a physical model test of seepage ﬂowthe experimental measurements at the same locations (Points B &    induced large deformation and progressive failure of an embankC). The underestimation of the SPH model for the ﬁrst inlet dis-    ment. The outline of the physical model test is ﬁrstly presented to
charge may be due to the Ergun’s coeﬃcients used in Eqs. (88) and     set out the scene for the application. Subsequently, details of the
( 89 ). These coeﬃcients were calibrated by Larese (2012 ) for PFEM    SPH model and numerical results of the physical model test are
simulations of the water ﬂow through a rigid rockﬁll dam in which    presented and discussed.
only the ﬂuid model was employed. Because of those assumptions,
full coupling between the ﬂuid ﬂow and the dam structure such      5.4.1. Outline of the physical model test
as variation of permeability according to the change of void ratio       The geometry and boundary conditions of the physical model
or dam’s deformation was not taken into account in their simula-     test is similar to those shown in Fig. 6 . The embankment was made
tions. As a result, the calibrated Ergun’s coeﬃcients are only appro-     of Masa soil, which is a weathered granite typically found in Kanpriate under the assumption of rigid dam. In fact, this assumption     sai area in Japan. The initial water content of slope was kept at
may not be appropriate in the early stage, in which rearrangement    approximately 5% and the corresponding soil properties are given
of the rockﬁll material might occur, before the water ﬂow reaches     in Table 1 . The embankment is 400 mm in height and 400 mm in
the steady state corresponding to the ﬁrst imposing discharge. It is    top-width with both upstream and downstream slopes of 1:1. The

                                                          Fig. 12. Inﬂuence of porosity n on the steady-state phreatic surface.

### Page 18

H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264                                 261

                                                                           c o = 0.55 kPa to c sat = 0.01 kPa which corresponds to the increase of
                                                                        saturation degree from S r = 0.05 to S r = 1, respectively. The inclu-
                                                                      sion of the small cohesion of c sat = 0.01 kPa to the fully saturated
                                                                                    soil is to account for the interlocking behaviour of soil owing to
                                                                            different particle shapes in reality. As for the seepage force model,
                                                           due to the relatively small permeability of the current sandy soil,
                                                                   the seepage force model based on the linear Darcy’s law is adopted
                                                                          in the simulation. All other geometry setting and boundary con-
                                                                          ditions follow the previous numerical model described in Section
                                                                         5.2 . In addition, prior to running the seepage ﬂow induced em-
                                                          bankment failure simulation, the initial in-situ stress condition of
                                                                   the embankment is obtained by applying the gravity loading to soil
                                                                             particles ( Bui and Fukagawa, 2013 ).
         Fig. 14. The completed view of the embankment after constructed.                 Fig. 16 shows the progressive failure process of the embank-
                                                       ment induced by the seepage ﬂow with the embedded failure
                                                                       surface observed in the experiment (i.e. dashed line). On the left
embankment was constructed in a ﬂume made of stainless steel     side of Fig. 16 are plots of the accumulated plastic strain whereas
with the front-side covered by thick glass to monitor the failure     plots of the void fraction distribution in the embankment dursurface. To reduce the sidewall boundary effect, lubricating oil was     ing the post-failure process of the embankment are presented on
applied between the soil and the sidewall to minimise the friction.    the right side of the ﬁgure. Before the seepage ﬂow gets to the
The test was started by gradually raising water in the upstream    downstream slope  toe, the deformation of the embankment  is
reservoir on the left-side of the embankment up to 30 cm in height     negligible although the saturated zone has a very low cohesion
and then kept constant at this level. Two cameras were setup on     of c sat = 0.01 kPa ( Fig. 16 a). As soon as the seepage ﬂow reaches
the front and side-views of the embankment to record the pro-    the downstream slope toe, the soil in this region loses its shear
gressive failure of the downstream slope. The complete front view     strength, triggering the failure of the embankment. The failure proof the embankment is shown in Fig. 14 .                               cess starts by a dramatic change of the plastic strain and the void
    Fig. 15 shows two typical snapshots of the embankment failure     ratio at the downstream slope toe as well as a minor settlement
process. The ﬁrst snapshot ( Fig. 15 a) was taken when the down-     of the downstream crest of the embankment ( Fig. 16 b). Comparstream slope toe was deteriorated by the seepage ﬂow causing a     ing with the experiment, although the two-phase SPH model could
local failure zone in the downstream slope toe. At this stage, sev-    not reproduce the local failure zone observed at the downstream
eral failure surfaces were visible from the sidewall indicating the     slope toe in the experiment ( Fig. 15 a), the model is able to capture
progressive failure. The failure mechanism of the slope toe can be    the major mechanism triggering the embankment failure which
attributed to the fact that the shear strength of the soil in this zone      is initiated from the downstream slope toe. Subsequently, starting
was signiﬁcantly reduced owing to the reduction of soil matrix    from the downstream slope toe, the ﬁrst shear band presented by
suction upon the soil wetting process. Losing the matrix suction,    the concentration of high plastic strains progressively develops upthe soil becomes cohesionless and could be easily washed away    ward following the experimentally-observed major failure surface
by the seepage ﬂow. The seepage front continuously developed in-     to the crest of the embankment. This localisation failure band corside the embankment owing to the constant water supply from the    responds to the loosening soil area developed due to the dilation
upstream reservoir, leading to the enlargement of the local failure    behaviour of the soil subjected to shearing. In particular, soil parzone in the downstream slope toe. The continuous development of     ticles along the shear band separate from each other because of a
the local failure zone at the downstream slope toe due to the de-     large amount of plastic volume change developed during the postvelopment of seepage force caused the downstream slope unstable,     failure regime, causing the void fraction of the soil along the shear
and eventually led to the catastrophic failure of the whole embank-    band to reduce. Corresponding to the generation of this localisament ( Fig. 15 b). The rotational failure mechanism was observed in     tion band, the downstream soil mass starts tilting along this main
the experiment with the loosen soil mass sliding along the ma-     potential slip surface ( Fig. 16 c). As the water ﬂow continues, the
jor failure surface. The circular failure surface was reconstructed    downstream slope completely fails in the tilting mode illustrated
by removing the failure soil mass. A quite uniform rotational fail-    by a large shear zone which divides the soil mass into two zones
ure mechanism was achieved in the lateral direction, suggesting    on the left and the right with negligible deformation or void fracthat the embankment failure experiment can be modelled under     tion change ( Fig. 16 d). On the other hand, the upstream slope rethe 2D plane-strain condition.                                   mains stable although the cohesion of the saturated zone signiﬁ-
                                                                        cantly reduces. This is thanks to the retaining water pressure from
5.4.2. Numerical prediction of the embankment collapse using the        the upstream reservoir which is automatically achieved through
two-phase SPH model                                                    Eq. (59) . At the ﬁnal stage ( Fig. 16 d), a signiﬁcant reduction of the
   As discussed above, owing to the relatively uniform lateral de-     solid void fraction is observed at the downstream toe where the
formation observed in the experiment (see Fig. 15 ), the embank-    seepage ﬂow goes out of the embankment, which clearly indicates
ment failure experiment can be considered in the plane-strain con-    the inﬂuence of the seepage force. The ﬁnal shear zone also con-
ﬁguration with homogenous  soil properties. Thus, the 2D two-      sists of one main slip surface developed from the initial-potential
phase SPH framework can be used for the simulation of the above     slip surface in Fig. 15 c and several secondary ones which are also
seepage ﬂow induced embankment failure. An elasto-plastic model    observed in the experiment. On the other hand, the discontinuous
employing the Drucker–Prager yield criterion described in Section    and cracking deformations on the downstream slope surface ob-
2.5 is adopted to describe the behaviour of the soil, with the ma-    served in the experiment ( Fig. 15 b) could not be reproduced in the
terial properties given in Table 1 . The simple strength reduction     current SPH simulation due to the simpliﬁcation of the soil conmodel, i.e. Eq. (33) , is adopted to account for the inﬂuence of sat-     stitutive model. In order to capture this behaviour, advanced unuration degree on the soil cohesion, and thus the reduction of     saturated soil models ( Alonso et al., 1990; Khalili and Loret, 2001;
soil matrix suction due to the wetting process observed in the     Loret and Khalili, 20 0 0; Sheng et al., 20 08 ) should be adopted and
experiment. In particular, the soil cohesion reduces linearly from    these are beyond the scope of this paper.

### Page 19

262                                        H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264

                                                             Fig. 15. Failure progress of the embankment in the experiment.

                                                            Fig. 16. Progressive failure of the embankment predicted by SPH.

   The above numerical applications demonstrate the capability of    ment from the original coupled two-phase SPH approach proposed
the proposed SPH approach in handling coupled problems involv-    by the ﬁrst author Bui et  al. (2007 ) that includes the following
ing complex water free-surface/seepage ﬂows and large deforma-    key features: 1) two layers of Lagrangian particles are used to
tion of soils, which are diﬃcult to be modelled using FEM-based     represent solid and ﬂuid phases which are solved simultaneously
approaches. However, owing to the requirement of two different    using their own governing equations; 2) effects of void fractions
Lagrangian discretisations to represent the solid and ﬂuid phases,    on the coupling behaviour of two phases are fully considered;
the proposed SPH approach generally incurs more computational     3) pore-pressure coupled with matrix soil deformation is considcost than FEM-based approaches, in which a single discretisation    ered for the ﬁrst time within the SPH context; 4) a fully consismesh consisting ﬁnite elements with different shape functions are     tent mathematical framework to achieve stable SPH numerical soused to solve the governing equations of the mixture. Neverthe-     lutions is described; and 5) a stable SPH solution for an incomless, the numerical implementation of the proposed SPH approach     pressible ﬂuid ﬂow that  is aligned to long physical time probis straightforward as computation domains are merely discretised     lems. The proposed two-phase SPH framework, in our opinion, is
using points (particles), which are arranged in a regular square    unique in the sense that it can be applied to a wide range of problattice. Special attentions might be required to handle complex     lems, including those which are unable to be resolved using traboundary conditions such as curvature solid boundaries. These are     ditional FEM-based coupled approach, such as scour due to overhowever beyond the scope of this paper.                            topping ﬂow, internal erosion due to seepage ﬂow, transportation
                                                                           of contaminated substances in subsurface, submarine landslides,
                                                                                    etc. The proposed two-phase SPH framework was ﬁrst validated6. Conclusions
                                                                        against analytical solutions for initial in-situ stresses of fully sub-
                                                          merged soil under gravity loading. Next, the framework was vali-   This paper presents the development of a new two-phase SPH
                                                                 dated with the PLAXIS FE-model and experiments for the seepageframework to enhance the predictive capability of existing compu-
                                                  ﬂow through low and high permeable porous media, respectively.tational approaches to study the coupled ﬂuid-solid interaction in
                                                                                   Finally, the framework was employed for the simulation of a phys-deformable porous media. The framework is a signiﬁcant advance-

### Page 20

H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264                                 263

ical model test of seepage ﬂow induced embankment failure that     Chen, W. , Qiu, T. , 2012. Numerical simulations for large deformation of granular
involves large deformations. Very good agreements with analytical          materials using smoothed particle hydrodynamics method. Int.  J. Geomech. 12,
                                                                               127–135 .
solutions, PLAXIS FE-model and experiments were achieved, sug-      Colagrossi, A. , Landrini, M. , 2003. Numerical simulation of  interfacial ﬂows by
gesting that the proposed two-phase SPH-framework is a promis-        smoothed particle hydrodynamics. J. Comput. Phys. 191, 448–475 .
ing approach for the study of coupled ﬂuid-solid interaction in de-     Deb, D. , Pramanik, R. , 2013. Failure process of brittle rock using smoothed particle
                                                                                    hydrodynamics. J. Eng. Mech. 139, 1551–1565 .
formable porous media that involve large deformations and failures                                                                               Duan, Q.L. , Belytschko, T. , 2009. Gradient and dilatational stabilizations for stress–
of the solid phase. In order to further advance the proposed two-         point integration in the element-free Galerkin method. Int.  J. Num. Meth. Eng.
phase SPH framework, unsaturated soil constitutive models should           77, 776–798 .
be adopted to replace the simple elasto-plastic constitutive model      Ehlers, W. , Graf, T. , Ammann, M. , 2004. Deformation and localization analysis of
                                                                                                       partially saturated soil. Comput. Metho. Appl. Mech. Eng. 193, 2885–2910 .
utilised in the current work. Furthermore, the modelling of post-      Fredlund, D.G. , Rahardjo, H. , 1993. In: Soil Mechanics for Unsaturated Soils, xxiv.
failure behaviour of soils needs further improvements as this pro-          Wiley, New York, p. 517 .
cess often involves ﬂuidised ﬂow behaviour and fractures on the      Gambolati, G. , Ferronato, M. ,  Teatini,  P. , Deidda, R. , Lecca, G. , 2001. Finite ele-
                                                                        ment analysis of land subsidence above depleted reservoirs with pore pressure
soil surfaces that are unable to model using existing constitutive          gradient and total stress formulations. Int.  J. Num. Anal. Meth. Geomech. 25,
models. On the other hand, computational algorithm is also an-        307–327 .
other topic that is worth to pay attention to, in order to reduce      Gelet, R. , Loret, B. , Khalili, N. , 2012. A thermo-hydro-mechanical coupled model in
                                                                                                      local thermal non-equilibrium for fractured HDR reservoir with double porosity.
computational costs required to simultaneously solve two layers of                 J. Geophys. Res. Solid Earth 117 .
Lagrangian particles in the two-phase SPH platform.                        Gingold, R.A. , Monaghan,  J.J. , 1977. Smoothed particle hydrodynamics - theory and
                                                                                              application to non-spherical stars. Mon. Not. R. Astron. Soc. 181, 375–389 .
                                                                                     Grabe,  J. , Stefanova,  B. , 2015. Numerical modeling of saturated  soils based on
                                                                             smoothed particle hydrodynamics (SPH). Geotechnik 38, 218–229 .
Acknowledgement                                                                  Gray, J.P. , Monaghan, J.J. , Swift, R.P. , 2001. SPH elastic dynamics. Comput. Meth. Appl.
                                                                                Mech. Eng. 190, 6641–6662 .
   Funding support from  the  Australian  Research  Council  via     Huang, Y. , Zhang, W.J. , Dai, Z.L. , Xu, Q. , 2013. Numerical simulation of ﬂow processes
projects DP160100775 (Ha H. Bui), FT140100408 (Giang D. Nguyen)          in liqueﬁed soils using a soil-water-coupled smoothed particle hydrodynamics
                                                                                 method. Nat. Hazards 69, 809–827 .
and DP170103793 (Nguyen & Bui) is gratefully acknowledged. The       Khalili, N. , Loret, B. , 2001. An elasto-plastic model for non-isothermal analysis of
authors would like to thank Mr. Chi T. Nguyen for his help in col-       ﬂow and deformation in unsaturated porous media: formulation. Int.  J. Solids
lecting rockﬁll experimental data for the validation of the proposed           Struct. 38, 8305–8330 .
                                                                                                  Krysl, P. , Belytschko, T. , 1996. Analysis of thin shells by the element-free Galerkin
numerical framework.                                                         method. Int. J. Solids Struct. 33, 3057–3078 .
                                                                                              Larese, A. , 2012. A coupled Eulerian-PFEM model for the simulation of overtopping
                                                                                                 in rockﬁll dams. A coupled Eulerian-PFEM model for the simulation of overReferences                                                                          topping in rockﬁll dams, 258 Ph.D. Thesis thesis. UPC BarcelonaTech, Barcelona,
                                                                                      Spain .
Alonso, E.E. , Gens, A. , Josa, A. , 1990. A constitutive model for partially saturated      Lastiwka, M. , Basa, M. , Quinlan, N.J. , 2009. Permeable and non-reﬂecting boundary
     soils. Geotechnique 40, 405–430 .                                                       conditions in SPH. Int. J. Num. Meth. Fluids 61, 709–724 .
Antuono, M. , Colagrossi, A. , Marrone, S. , Molteni, D. , 2010. Free-surface ﬂows solved      Leroch,  S. , Varga, M. , Eder,  S.J. , Vernes, A. , Ripoll, M.R. , Ganzenmuller, G. , 2016.
   by means of SPH schemes with numerical diffusive terms. Comput. Phys. Com-        Smooth particle hydrodynamics simulation of damage induced by a spherical
   mun. 181, 532–549 .                                                                   indenter scratching a viscoplastic material. Int. J. Solids Structures 81, 188–202 .
Bear,  J. , Cheng, A.H.D. , 2010. Modeling groundwater ﬂow and contaminant trans-      Lewis, R.W. , Ghafouri, H.R. , 1997. A novel ﬁnite element double porosity model for
    port. In: Theory and Applications of Transport in Porous Media, xxi. Springer,         multiphase ﬂow through deformable fractured porous media. Int. J. Num. Anal.
    Dordrecht; London, p. 834 .                                                       Meth. Geomech. 21, 789–816 .
Belytschko, T. , Lu, Y.Y. , Gu, L. , 1994. Element-free Galerkin methods. Int.  J. Num.      Lewis, R.W. , Sukirman, Y. , 1994. Finite-element modeling for simulating the surface
    Meth. Eng. 37, 229–256 .                                                             subsidence above a compacting hydrocarbon reservoir. Int.  J. Num. Anal. Meth.
Biot, M.A. , 1956. Theory of propagation of elastic waves in a ﬂuid-saturated porous        Geomech. 18, 619–639 .
     solid. J. Acoust. Soc. Am. 28, 168–191 .                                                  Libersky, L.D. , Petschek, A.G. , Carney, T.C. , Hipp, J.R. , Allahdadi, F.A. , 1993. High-strain
Blanc, T. , Pastor, M. , 2012. A stabilized fractional step, Runge–Kutta Taylor SPH algo-         Lagrangian hydrodynamics - a 3-dimensional sph code for dynamic material re-
    rithm for coupled problems in geomechanics. Comput. Meth. Appl. Mech. Eng.         sponse. J. Comput. Phys. 109, 67–75 .
    221, 41–53 .                                                                                 Loret, B. , Khalili, N. , 20 0 0. A three-phase model for unsaturated soils. Int.  J. Num.
Blanc, T. , Pastor, M. , 2013. A stabilized smoothed particle hydrodynamics, Taylor—          Anal. Meth. Geomech. 24, 893–927 .
    Galerkin algorithm for soil dynamics problems. Int.  J. Num. Anal. Meth. Ge-      Lucy, L.B. , 1977. Numerical approach to testing of ﬁssion hypothesis. Astron.  J. 82,
   omech. 37, 1–30 .                                                              1013–1024 .
Bowen, R.M. , 1976. Theory of mixtures.  In: Eringen,  A.C.  (Ed.).  In: Continuum     Maeda, K. , Sakai, H. , 2010. Seepage failure and erosion of ground with air bub-
    Physics, vol. III. Academic Press, New York, pp. 1–127 .                                    ble dynamics. In: Geoenvironmental Engineering and Geotechnics: Progress in
Bui, H.H. , Fukagawa, R. , 2009. A ﬁrst attempt to solve soil-water coupled problem        Modeling and Applications. American Society of Civil Engineers (ASCE), USA,
   by SPH. Japanese Terramech. 29, 33–38 .                                                 pp. 261–266 .
Bui, H.H. , Fukagawa, R. , 2013. An improved SPH method for saturated soils and its     Monaghan,  J.J. , 1994. Simulating free-surface ﬂows with sph.  J. Comput. Phys. 110,
    application to investigate the mechanisms of embankment failure: case of hy-        399–406 .
    drostatic pore-water pressure. Int. J. Num. Anal. Meth. Geomech. 37, 31–50 .        Monaghan,  J.J. , 1997. Implicit SPH drag and dusty gas dynamics.  J. Comput. Phys.
Bui, H.H. , Fukagawa, R. , Sako, K. , 2006. Smoothed particle hydrodynamics for soil          138, 801–820 .
    mechanics. In: Proceedings of the 6th European Conference on Numerical Meth-     Monaghan, J.J. , 2012. Smoothed particle hydrodynamics and its diverse applications.
   ods in Geotechnical Engineering - Numerical Methods in Geotechnical Engineer-         Ann. Rev. Fluid Mech. 44, 323–346 .
    ing, pp. 278–281 .                                                        Monaghan,  J.J. , Lattanzio,  J.C. , 1985. A reﬁned particle method for astrophysical
Bui, H.H. , Fukagawa, R. , Sako, K. , Ohno,  S. , 2008. Lagrangian meshfree particles         problems. Astron. Astrophys. 149, 135–143 .
   method (SPH) for large deformation and failure ﬂows of geomaterial using     Nguyen,  C.T. , Nguyen,  C.T. , Bui, H.H. , Nguyen, G.D. , Fukagawa, R. , 2017. A new
    elastic-plastic soil constitutive model. Int.  J. Num. Anal. Meth. Geomech. 32,         SPH-based approach to simulation of granular ﬂows using viscous damping and
   1537–1570 .                                                                                     stress regularisation. Landslides 14, 69–81 .
Bui, H.H. , Fukagawa, R. , Sako, K. , Wells, J.C. , 2011a. Slope stability analysis and dis-     Nomeritae , Daly, E. , Grimaldi, S. , Bui, H.H. , 2016. Explicit incompressible SPH algo-
    continuous slope failure simulation by elasto-plastic smoothed particle hydro-         rithm for free-surface ﬂow modelling: a comparison with weakly compressible
   dynamics (SPH). Geotechnique 61, 565–574 .                                         schemes. Adv. Water Resour. 97, 156–167 .
Bui, H.H. , Kodikara, J.K. , Bouazza, A. , Haque, A. , Ranjith, P.G. , 2014. A novel compu-      Onate, E. , Idelsohn, S.R. , Del Pin,  F. , Aubry, R. , 2004. The particle ﬁnite element
    tational approach for large deformation and post-failure analyses of segmental        method - an overview. Int. J. Comput. Meth. 1, 267–307 .
    retaining wall systems. Int. J. Num. Anal. Meth. Geomech. 38, 1321–1340 .             Pastor, M. , Haddad, B. , Sorbino, G. , Cuomo, S. , Drempetic, V. , 2009. A depth-inteBui, H.H. , Sako, K. , Fukagawa, R. , 2007. Numerical simulation of soil-water interac-          grated, coupled SPH model for ﬂow-like landslides and related phenomena. Int.
    tion using smoothed particle hydrodynamics (SPH) method.  J. Terramech. 44,                 J. Num. Anal. Meth. Geomech. 33, 143–172 .
   339–346 .                                                                                      Peric, D. , Zhao, G.F. , Khalili, N. , 2014. Strain localization in unsaturated elastic-plastic
Bui, H.H. , Sako, K. , Fukagawa, R. , Nguyen, C.T. , 2011b. An investigation of riverbank          materials subjected to plane strain compression. J. Eng. Mech. 140 .
    failure due to water level change using two-phase ﬂow SPH model. In: Com-      Popescu, R. , Prevost, J.H. , Deodatis, G. , Chakrabortty, P. , 2006. Dynamics of nonlinear
    puter Methods for Geomechanics: Frontiers and New Applications, pp. 116–123 .         porous media with applications to soil liquefaction. Soil Dyn. Earthquake Eng.
Cascini, L. , Cuomo, S. , Pastor, M. , Sorbin, G. , 2010. Modeling of rainfall-induced shal-          26, 648–665 .
   low landslides of the ﬂow-type. J. Geotech. Geoenviron. Eng. 136, 85–98 .

### Page 21

264                                        H.H. Bui, G.D. Nguyen / International Journal of Solids and Structures 125 (2017) 244–264

Prevost,  J.H. , 1980. Mechanics of continuous porous-media.  Int.  J. Eng.  Sci. 18,     Zhang, W. , Maeda, K. , 2015. SPH simulations for slope and levee failure under heavy
   787–800 .                                                                                             rainfall considering the effect of air phase. Comput. Meth. Recent Adv. Geomech.
Prevost,  J.H. , 1982. Non-linear transient phenomena in saturated porous media.        1465–1470 .
   Comput. Meth. Appl. Mech. Eng. 30, 3–18 .                                        Zhang, X. , Krabbenhoft, K. , Pedroso, D.M. , Lyamin, A.V. , Sheng, D. , Silva, M.V.da ,
Prevost, J.H. , 1985. Wave propagation in ﬂuid-saturated porous media: an eﬃcient        Wang, D. , 2013. Particle ﬁnite element analysis of large deformation and granu-
    ﬁnite element procedure. Int. J. Soil Dyn. Earthquake Eng. 4, 183–202 .                      lar ﬂow problems. Comput. Geotech. 54, 133–142 .
Shao, S.D. , Lo, E.Y.M. , 2003. Incompressible SPH method for simulating Newtonian      Zienkiewicz, O.C. , Chan, A.H.C. , Pastor, M. , Schreﬂer, B.A. , Shiomi, T. , 1999. In: Com-
   and non-Newtonian ﬂows with a free surface. Adv. Water Resour. 26, 787–800 .          putational Geomechanics With Special Reference to Earthquake Engineering, xi.
Sheng, D. , Fredlund, D.G. , Gens, A. , 2008. A new modelling approach for unsaturated         John Wiley & Sons, New York, p. 383. 2 p. of plates p .
     soils using independent stress variables. Can. Geotech. J. 45, 511–534 .                Zienkiewicz, O.C. , Huang, M.S. , Pastor, M. , 1995. Localization problems in plasticSulsky, D. , 1995. Application of a particle-in-cell method to solid mechanics. Com-           ity using ﬁnite-elements with adaptive remeshing. Int. J. Num. Anal. Meth. Ge-
    put. Phys. Commun. 87 (1–2), 236–252 .                                          omech. 19, 127–148 .
Vangenuchten, M.T. , 1980. A closed-form equation for predicting the hydraulic con-      Zienkiewicz, O.C. , Shiomi, T. , 1984. Dynamic behaviour of saturated porous media;
    ductivity of unsaturated soils. Soil Sci. Soc. Am. J. 44, 892–898 .                         the generalized Biot formulation and its numerical solution. Int.  J. Num. Anal.
Zhang, D.Z. , Ma, X. , Giguere, P.T. , 2011. Material point method enhanced by modiﬁed         Meth. Geomech. 8 (1), 71–96 .
    gradient of shape function. J. Comput. Phys. 230, 6379–6398 .
