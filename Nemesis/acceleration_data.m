close,clear,clc

acc = readmatrix("acceleration_data.csv");

rtm = readmatrix("flight_telemetry_50Hz_v8.csv");

tR = rtm(:,030);


axR = rtm(:,14);
ayR = rtm(:,15);
azR = rtm(:,16);

time = acc(:,1);
ax = acc(:,2);
ay = acc(:,3);
az = acc(:,4);

figure;

plot(tR,axR, 'b', "LineWidth", 1)
hold on;
plot(tR,ayR, "Color",[1, 0.5, 0], "LineWidth", 1)
hold on;
plot(tR,azR, 'g', "LineWidth", 1)
grid on;
legend('ax','ay','az')
