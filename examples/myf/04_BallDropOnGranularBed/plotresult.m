##Test on Octave
##%% Input data
##plot(time,velz+0.3)
A=dlmread('./CaseBallDrop3D_vel1.12_out/floatinginfo/FloatingMotion_mk11.csv');
##
sett=A(:,11)-A(2,11);
sett(1,1)=0;
sett=100*sett;
heave=100*A(:,14);
plot(A(:,2),sett,'k')
D=[A(:,2) sett];
hold on
A=dlmread('./CaseBallDrop3D_vel1.87_out/floatinginfo/FloatingMotion_mk11.csv');
sett=A(:,11)-A(2,11);
sett(1,1)=0;
sett=100*sett;
plot(A(:,2),sett,'r')
D=[D A(:,2) sett];
A=dlmread('./CaseBallDrop3D_vel3.03_out/floatinginfo/FloatingMotion_mk11.csv');
sett=A(:,11)-A(2,11);
sett(1,1)=0;
sett=100*sett;
plot(A(:,2),sett,'b')
D=[D A(:,2) sett];
A=dlmread('./CaseBallDrop3D_vel3.3_out/floatinginfo/FloatingMotion_mk11.csv');
sett=A(:,11)-A(2,11);
sett(1,1)=0;
sett=100*sett;
plot(A(:,2),sett,'g')
D=[D A(:,2) sett];
A=dlmread('./CaseBallDrop3D_vel3.63_out/floatinginfo/FloatingMotion_mk11.csv');
sett=A(:,11)-A(2,11);
sett(1,1)=0;
sett=100*sett;
plot(A(:,2),sett,'m')
D=[D A(:,2) sett];

B=dlmread('./exp_data.csv');

scatter(B(:,11),B(:,12),'k')
scatter(B(:,13),B(:,14),'r')
scatter(B(:,15),B(:,16),'b')
scatter(B(:,17),B(:,18),'g')
scatter(B(:,19),B(:,20),'m')

axis([0 0.2 -20 5])

figure(2)
A=dlmread('./CaseBallDrop3D_vel1.12_out/floatinginfo/FloatingMotion_mk11.csv');
plot(A(:,2),A(:,5)+1.2,'k')
hold on
A=dlmread('./CaseBallDrop3D_vel1.87_out/floatinginfo/FloatingMotion_mk11.csv');
plot(A(:,2),A(:,5)+0.9,'r')
A=dlmread('./CaseBallDrop3D_vel3.03_out/floatinginfo/FloatingMotion_mk11.csv');
plot(A(:,2),A(:,5)+0.6,'b')
A=dlmread('./CaseBallDrop3D_vel3.3_out/floatinginfo/FloatingMotion_mk11.csv');
plot(A(:,2),A(:,5)+0.3,'g')
A=dlmread('./CaseBallDrop3D_vel3.63_out/floatinginfo/FloatingMotion_mk11.csv');
plot(A(:,2),A(:,5),'m')

scatter(B(:,1),B(:,2),'m')
scatter(B(:,3),B(:,4),'g')
scatter(B(:,5),B(:,6),'b')
scatter(B(:,7),B(:,8),'r')
scatter(B(:,9),B(:,10),'k')
axis([0 0.2 -4 2])
