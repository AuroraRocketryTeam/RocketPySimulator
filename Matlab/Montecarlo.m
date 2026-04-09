% RocketPy Preliminary Simulation of the Atlas rocket, Aurora Rocketry Team, EuRoC 2025

clc, clear, close all

%% Imposta pyenv
pyenv('ExecutionMode','OutOfProcess');

rocketpy = py.importlib.import_module('rocketpy');
Environment = rocketpy.environment.Environment;
SolidMotor = rocketpy.motors.solid_motor.SolidMotor;
Rocket     = rocketpy.rocket.Rocket;
Flight     = rocketpy.simulation.flight.Flight;
CompareFlights = rocketpy.CompareFlights;

% Matplotlib

mpl = py.importlib.import_module('matplotlib');
mpl.use('Qt5Agg');  % imposta il backend di rendering

plt = py.importlib.import_module('matplotlib.pyplot');

% Import del modulo time
time = py.importlib.import_module('time');

% Import di process_time
process_time = py.importlib.import_module('time').process_time;
% 
% % Altre librerie Python
np = py.importlib.import_module('numpy');
imageio = py.importlib.import_module('imageio.v2');
norm = py.importlib.import_module('scipy.stats').norm;
pathlib = py.importlib.import_module('pathlib');
json = py.importlib.import_module('json');
os = py.importlib.import_module('os');
pickle = py.importlib.import_module('pickle');

    % === Mass Details ===

analysis_parameters = struct( ...
    "rocket_dry_mass",              [25.557316146344952, 5/1000], ...          % Rocket dry mass (kg)
    "rocket_dry_inertia_11",        [14.24264697322362, 5/1000], ...          % Rocket inertia I11 (kg*m^2)
    "rocket_dry_inertia_33",        [0.07475822585846044, 122/100000], ...         % Rocket inertia I33 (kg*m^2)
    "motor_dry_mass",               [0.00014008279656163892, 5/10000], ...            % Motor dry mass (kg)
    "motor_inertia_11",             [0, 0], ...                        % Motor inertia I11 (kg*m^2)
    "motor_inertia_33",             [0, 0], ...                        % Motor inertia I33 (kg*m^2)
    "motor_dry_mass_position",      [-0.0009085305748945343, 5/10000], ...                  % Motor COM position (m)
    "impulse",                      [9974.69314944336, 1/2], ...                   % Total impulse (N*s)
    "burn_time",                    [4.241530000474283, 5/10000], ...              % Burn time (s)
    "nozzle_radius",                [0.029609041769879437, 5/100000], ...           % Nozzle radius (m)
    "throat_radius",                [0.02061346614970209, 5/100000], ...           % Throat radius (m)
    "grain_separation",             [0.0030038288314371397, 1/100000], ...            % Grain separation (m)
    "grain_density",                [1793.144452848121, 1], ...                 % Grain density (kg/m^3)
    "grain_outer_radius",           [0.0358862665080544, 1/10000], ...           % Grain outer radius (m)
    "grain_initial_inner_radius",   [0.018244189740641525, 1/10000], ...         % Grain inner radius (m)
    "grain_initial_height",         [0.15606465340865924, 1/10000], ...        % Grain height (m)
    "radius",                       [0.07505427553527239, 5/10000], ...             % Rocket radius (m)
    "nozzle_position",              [-1.4356434056096632, 5/10000], ...          % Nozzle axial position (m)
    "grains_center_of_mass_position", [-0.9416508541354824, 5/10000], ...      % Propellant COM (m)
    "power_off_drag_corr",          [0.999662229247697, 5/10000], ...                   % Drag correction (power off)
    "power_on_drag_corr",           [0.999684901446651, 5/10000], ...                   % Drag correction (power on)
    "nose_length",                  [0.4318204474378214, 5/10000], ...              % Nose length (m)
    "nose_pwr",                     [0.0013344335093664473, 5/10000], ...                   % Nose shape exponent
    "tail_distance_to_RCDM",        [-1.3817218728592324, 5/10000], ...          % Tail–RCDM distance (m)
    "nose_distance_to_RCDM",        [1.186553244548323, 5/10000], ...           % Nose–RCDM distance (m)
    "fin_number",                   [3, 0], ...                         % Number of fins
    "fin_span",                     [0.1411278097292937, 5/10000], ...              % Fin span (m)
    "fin_root_chord",               [0.27961219250706315, 5/10000], ...              % Fin root chord (m)
    "fin_tip_chord",                [0.060099338721757094, 5/10000], ...             % Fin tip chord (m)
    "fin_distance_to_RCDM",         [-1.0944302263040155, 5/10000], ...           % Fin–RCDM distance (m)
    "fin_sweep_angle",              [58.20330491214908, 5/10000], ...                  % Fin sweep angle (deg)
    "tail_length",                  [0.07548110603059785, 5/10000], ...            % Tail length (m)
    "tail_bottom_radius",           [0.050987990564273125, 5/10000], ...             % Tail bottom radius (m)
    "tail_top_radius",              [0.07536245478270502, 5/10000], ...             % Tail top radius (m)
    "inclination",                  [83.28515711632079, 0], ...                        % Rail inclination (deg)
    "heading",                      [145.8682799655182, 0], ...                       % Rail heading (deg)
    "rail_length",                  [10.996068095179226, 5/1000], ...             % Rail length (m)
    "ensemble_member",              0:9, ...                             % Ensemble forecast members
    "cd_s_drogue",                  [0.8856717513467018, 6/1000], ... % Drogue chute Cd·S (m²)
    "cd_s_main",                    [13.663905632394899, 277/1000], ...% Main chute Cd·S (m²)
    "lag_rec",                      [1.77566338618894, 1/10], ...                 % Parachute inflation delay (s)
    "upper_button_y",               [1.0468103443907182, 1/200], ...                  % Upper rail button pos (m)
    "lower_button_y",               [-0.5209702470425779, 1/200], ...              % Lower rail button pos (m)
    "angular_button",               [-0.00507449010544642, 1/100], ...                      % Button angle (deg)
    "lag_se",                       [0.04326722662182819, 3/200], ...                   % Sensor→ejection delay (s)
    "noise_mean",                   [-0.00023540291268519788, 1/1000], ...                     % Pressure noise mean (Pa)
    "noise_p_stdev",                [6.486121224039615, 1/100], ...                   % Pressure noise std dev (Pa)
    "noise_p_tc",                   [0.31510046729879354, 1/100] ...                     % Pressure noise time correlation
);



% Definition of global variables, to be used inside and outside parachute functions

global last_negative_time apogee_detected sampling_rate %parachute_timer
last_negative_time=[]; % This variable marks the first instant in which a negative velocity is detected
apogee_detected=false;% This variable indicates whether the algorythm has acknowledged the rocket has reached apogee. A "False" value may mean that negative velocity has not yet been detected, or that it has been detected but has not yet been consistent for enough seconds (the threshold)
sampling_rate=105;% This variable indicates the sampling rate of the recovery activation algorythm
parachute_stopwatch=0;% This variable keeps track of the flight time from ignition to the first recovery event

this_file = mfilename('fullpath');
BASE_DIR = fileparts(this_file);

%% Base directory e file name
if ~exist('BASE_DIR','var')
    BASE_DIR = pwd;
end

filename = fullfile(BASE_DIR, "Atlas");

disp("Filename is:");
disp(filename);

number_of_simulations = 10;

%% Crea file per input, output ed errori e mantienili aperti
global dispersion_error_file dispersion_input_file dispersion_output_file
dispersion_error_file  = fopen(filename + ".disp_errors.txt", "w");
dispersion_input_file  = filename + ".disp_inputs.json";
dispersion_output_file = filename + ".disp_outputs.json";

%% Inizializza contatore e timer
i = 0;

initial_wall_time = tic;   % equivalente a time.time()
initial_cpu_time  = process_time();   % equivalente a process_time()

% # Define basic Environment object
Env = Environment(pyargs( ...
        'date', py.tuple({py.int(2025), py.int(10), py.int(13), py.int(18)}), ...  %(Year, Month, Day, Hour)
        'longitude', -8.288963, ...
        'latitude', 39.3897, ...
        'elevation', 160, ...
        'max_expected_height', 4500 ...
    ) ...
);

% Import the .json file with the mean environment values
data = jsondecode(fileread(fullfile(BASE_DIR, "mean_environment_values.json")));

% Set the environment model with either of the 3 options below
Env.set_atmospheric_model(pyargs( ...
    'type', py.str('Ensemble'), ...
    'file', py.str(fullfile(BASE_DIR, 'SantaMargarida_Ensemble_LaunchDayWeatherData.nc')), ...
    'dictionary', py.dict({ ...
        {'ensemble', py.str('number')}, ...
        {'time', py.str('valid_time')}, ...
        {'latitude', py.str('latitude')}, ...
        {'longitude', py.str('longitude')}, ...
        {'level', py.str('pressure_level')}, ...
        {'temperature', py.str('t')}, ...
        {'surface_geopotential_height', py.None}, ...
        {'geopotential_height', py.None}, ...
        {'geopotential', py.str('z')}, ...
        {'u_wind', py.str('u')}, ...
        {'v_wind', py.str('v')} ...
    }) ...
));
% =================================================================== OPTION 1: average metheorological conditions ===================================================================

    % In order to define the mean environment features, we used the built-in function "Environment Analysis" from RocketPy. This generates a .json file with the mean environment values based on 
    % a sample of 19 years, from 2005 to 2024, between the 10th and 15th of October, by feeding the NetCDF4 data from Copernicus. The .json file contains a series of .csv profiles based on the altitude 
    % that define pressure, temperature and wind vectors on an hourly basis. For more information consult the "mean_environment_values.json" file inside the directory.

    % REMOVE COMMENT FROM THE FOLLOWING SECTION TO RUN SIMULATION USING THESE SETTINGS ---------------------------------%
    %                                                                                                                   %
    % type="custom_atmosphere",                                                                                         %
    %                                                                                                                   %
    % pressure = data("atmospheric_model_pressure_profile")(num2str(Env.date{4})),                                       %
    % temperature= data("atmospheric_model_temperature_profile")(num2str(Env.date{4})),                                   %
    % wind_u= data("atmospheric_model_wind_velocity_x_profile")(num2str(Env.date{4})),                                     %
    % wind_v= data("atmospheric_model_wind_velocity_y_profile")(num2str(Env.date{4}))                                      %
    %                                                                                                                   %
    %-------------------------------------------------------------------------------------------------------------------%
      
    % =================================================================== OPTION 2: worst successful launch day recorded from past EuRoC editions ===================================================================

    % We researched the worst weather conditions in which launches at EuRoC have still taken place, and found that 11/10/2024 qualified for being one of the most windy in which launches were still conducted. We used
    % ensemble-type weather models to simulate flight operations using data from that day and evaluate predicted flight performance, finding that the apogee would be severely lowered, but would still be satisfactory.

    % REMOVE COMMENT FROM THE FOLLOWING SECTION TO RUN SIMULATION USING THESE SETTINGS ---------------------------------%
    %   
        %                                                                                                                   %
    %-------------------------------------------------------------------------------------------------------------------%

    % =================================================================== OPTION 3: worst plausible case scenario ===================================================================

    % To evaluate the worst case for bending stresses on the structure, we decided to run a simulation assuming constant winds as strong as the peak values in the worst day (11/10/2024) and aligned with the launch
    % heading, causing the rocket to steer violently into the wind and generate high bending moment on the structure in this maneouvre. The apogee would be reduced to just under 2700 m, but the airframe
    % of the rocket would resist the stress. Ailerons, however, would have to sustain a high load factor (presumably around 4Gs, by the look of the acceleration profiles)

    % REMOVE COMMENT FROM THE FOLLOWING SECTION TO RUN SIMULATION USING THESE SETTINGS ---------------------------------%
    %                                                                                                                   %
    %  type="custom_atmosphere",                                                                                         %
    %  wind_u=[                                                                                                          %
    %      (0, -1.5), % 10.60 m/s at 0 m                                                                                %
    %      (4500, -1.5), % 10.60 m/s at 3000 m                                                                          %
    %  ],                                                                                                                %
    %  wind_v=[                                                                                                          %
    %      (0, 0), % -16.96 m/s at 3000 m   
    %      (4500, 0)                                                                     %
    %  ],                                                                                                                %
                                                                                                                       %
    %-------------------------------------------------------------------------------------------------------------------%

    % =================================================================== OPTION 4: actual weather forecast ===================================================================

    % REMOVE COMMENT FROM THE FOLLOWING SECTION TO RUN SIMULATION USING THESE SETTINGS ---------------------------------%
    %                                                                                                                   %
    % type = "forecast",                                                                                                 %
    % file = "GFS"                                                                                                      %
                                                                                                                       %
    %-------------------------------------------------------------------------------------------------------------------%

% Initiate collection of flight data. This allows to compare different flight from the Montecarlo analysis and visualize data dispersion and overall characteristics of the flight and the simulation itself
flights = {};  % Lista di risultati

% Iterate over flight settings
settings_list = flight_settings(analysis_parameters, number_of_simulations);

t_vec=[]; %rimuovere
for idx = 1:length(settings_list)
    global last_negative_time apogee_detected

     setting = settings_list{idx};
    
    % Reinitialize global variables for each simulation
    last_negative_time = [];
    apogee_detected = false;
    parachute_stopwatch = 0;
    
    start_time = process_time();  % MATLAB equivalent of process_time()
    i = i+1;
    fprintf('\rCurrent iteration: %d', i);
   
    if Env.atmospheric_model_type == "Ensemble"
        ensemb = py.int(setting.ensemble_member);
        Env.select_ensemble_member(py.int(ensemb));
    end

    % Define COTS motor
    inertia_vec = [setting.motor_inertia_11, setting.motor_inertia_11, setting.motor_inertia_33];
    dry_inertia_py = py.list(num2cell(double(inertia_vec)));  % ensure scalars -> Python numbers
    reshape_thrust_curve_py = py.tuple(num2cell( [setting.burn_time, setting.impulse] ));

    Pro75_8187M1545_P = SolidMotor(pyargs( ...
        'thrust_source', fullfile(BASE_DIR, 'Cesaroni_8187M1545_P.csv'), ...
        'burn_time', setting.burn_time, ...
        'reshape_thrust_curve', reshape_thrust_curve_py, ...
        'interpolation_method', 'linear', ...
        'nozzle_radius', setting.nozzle_radius, ...
        'throat_radius', setting.throat_radius, ...
        'grain_number', int32(6), ...
        'grain_separation', setting.grain_separation, ...
        'grain_density', setting.grain_density, ...
        'grain_outer_radius', setting.grain_outer_radius, ...
        'grain_initial_inner_radius', setting.grain_initial_inner_radius, ...
        'grain_initial_height', setting.grain_initial_height, ...
        'nozzle_position', setting.nozzle_position, ...
        'grains_center_of_mass_position', setting.grains_center_of_mass_position, ...
        'dry_mass', setting.motor_dry_mass, ...
        'dry_inertia', dry_inertia_py, ...
        'center_of_dry_mass_position', setting.motor_dry_mass_position, ...
        'coordinate_system_orientation', 'nozzle_to_combustion_chamber' ...
    )); 
    

% Create rocket
Atlas = Rocket(pyargs( ...
    'radius', setting.radius, ...
    'mass', setting.rocket_dry_mass, ...
    'inertia', [setting.rocket_dry_inertia_11, setting.rocket_dry_inertia_11, setting.rocket_dry_inertia_33], ...
    'power_off_drag', fullfile(BASE_DIR, 'Nemesis150_v4.0_RAS_CDMACH_pwrOFF.csv'), ...
    'power_on_drag', fullfile(BASE_DIR, 'Nemesis150_v4.0_RAS_CDMACH_pwrON.csv'), ...
    'center_of_mass_without_motor', 0, ...     % Define the center of dry mass as the origin of the frame of reference, and set the positive axis orientation
    'coordinate_system_orientation', 'tail_to_nose' ...
));

% Define rail buttons
Atlas.set_rail_buttons(pyargs( ...
    'upper_button_position', setting.upper_button_y, ...
    'lower_button_position', setting.lower_button_y, ...
    'angular_position', setting.angular_button ...
));

% Add the motor to the rocket assembly
Atlas.add_motor(Pro75_8187M1545_P, pyargs('position', 0));

% Add uncertainty to the drag curves, by multiplying them by a small, random corrective factor
Atlas.power_off_drag = Atlas.power_off_drag * setting.power_off_drag_corr;
Atlas.power_on_drag  = Atlas.power_on_drag  * setting.power_on_drag_corr;

% Define and add the Nosecone section
NoseCone = Atlas.add_nose(pyargs( ... 
    'length', setting.nose_length, ...
    'kind', 'lvhaack', ...
    'power', setting.nose_pwr, ...
    'position', setting.nose_distance_to_RCDM + setting.nose_length ...
));

% Define and add the Fins
FinSet = Atlas.add_trapezoidal_fins(pyargs( ...
    'n', int32(3), ...
    'span', setting.fin_span, ...
    'root_chord', setting.fin_root_chord, ...
    'tip_chord', setting.fin_tip_chord, ...
    'position', setting.fin_distance_to_RCDM, ...
    'sweep_angle', setting.fin_sweep_angle, ...
    'cant_angle', 0, ...
    'airfoil', py.None ...
));

% Define and add the Boat-tail
Tail = Atlas.add_tail(pyargs( ...
    'top_radius', setting.tail_top_radius, ...
    'bottom_radius', setting.tail_bottom_radius, ...
    'length', setting.tail_length, ...
    'position', setting.tail_distance_to_RCDM ...
));

% Define and add the Drogue parachute
triggers = py.importlib.import_module('simulation_triggers');
py.importlib.reload(triggers);

Drogue = Atlas.add_parachute(pyargs( ...
    'name', 'Drogue', ...
    'cd_s', setting.cd_s_drogue, ...
    'trigger', triggers.simulator_check_drogue_opening ...
));
    Drogue.sampling_rate=sampling_rate;
    Drogue.lag=setting.lag_rec + setting.lag_se;
    Drogue.noise=[setting.noise_mean, setting.noise_p_stdev, setting.noise_p_tc];

% triggers = py.importlib.import_module('simulation_triggers');
% py.importlib.reload(triggers);

Main = Atlas.add_parachute(pyargs( ...
    'name', 'Main', ...
    'cd_s', setting.cd_s_main, ...
    'trigger', triggers.simulator_check_main_opening ...
));
    Main.sampling_rate=sampling_rate;
    Main.lag=setting.lag_rec + setting.lag_se;
    Main.noise=[setting.noise_mean, setting.noise_p_stdev, setting.noise_p_tc];

% Run trajectory simulation

    try
        % Creo oggetto Python Flight
        rocket_flight = Flight(pyargs( ...
            'rocket', Atlas, ...
            'environment', Env, ...
            'rail_length', setting.rail_length, ...
            'inclination', setting.inclination, ...
            'heading', setting.heading, ...
            'max_time', int32(600) ...
        ));
        flight_result=export_flight_data(setting, rocket_flight, process_time() - start_time());

        flights{i} = rocket_flight;

    catch ME
        disp(ME.message);
        export_flight_error(setting)
    end

% Salva il volo completo se serve
flights{end+1} = rocket_flight;
end

%% Draw the rocket
Atlas.draw();

%% Print comparison graphs to visualize data dispersion during flight
Env.all_info(); 

comparison = CompareFlights(flights);
comparison.velocities();
comparison.accelerations();
comparison.attitude_angles();
comparison.euler_angles();
comparison.attitude_frequency();
comparison.aerodynamic_forces();
comparison.aerodynamic_moments();
comparison.angular_velocities();
comparison.trajectories_3d();
comparison.rail_buttons_forces();
comparison.stability_margin();

%% Done

% Print and save total time
final_string = sprintf('Completed %d iterations successfully. Total CPU time: %.2f s. Total wall time: %.2f s', ...
    i, cputime - initial_cpu_time, toc(initial_wall_time));
disp(final_string);

filename = fullfile(BASE_DIR, 'Atlas');

%% Initialize variable to store all results
% Lista di tutti i voli (vuota)
dispersion_general_results = {};   

% Struct vuota con tutti i campi inizializzati a [] (equivalente Python)
dispersion_results = struct( ...
    'out_of_rail_time', [], ...
    'out_of_rail_velocity', [], ...
    'apogee_time', [], ...
    'apogee_altitude', [], ...
    'apogee_x', [], ...
    'apogee_y', [], ...
    'impact_time', [], ...
    'impact_x', [], ...
    'impact_y', [], ...
    'impact_velocity', [], ...
    'initial_static_margin', [], ...
    'out_of_rail_static_margin', [], ...
    'final_static_margin', [], ...
    'number_of_events', [], ...
    'max_velocity', [], ...
    'max_acceleration', [], ...
    'max_aerodynamic_drag', [], ...
    'max_aerodynamic_lift', [], ...
    'max_aerodynamic_spin_moment', [], ...
    'max_aerodynamic_bending_moment', [], ...
    'drogue_triggerTime', [], ...
    'drogue_inflated_time', [], ...
    'drogue_inflated_velocity', [], ...
    'execution_time', [] ...
);


fid = fopen(filename + ".disp_outputs.json", "r");

% Leggi riga per riga
while ~feof(fid)
    line = fgetl(fid);  % legge riga senza newline
    if isempty(line)
        continue
    end
    
    % Salta commenti (righe che non iniziano con '{')
    if line(1) ~= '{'
        continue
    end
    
    % Decodifica JSON (equivalente di eval(line) in Python)
    flight_result = jsondecode(line);
    
    % Aggiungi al cell array generale
    dispersion_general_results{end+1} = flight_result;
    
    % Aggiorna struct dispersion_results
    keys = fieldnames(flight_result);
    for k = 1:numel(keys)
        key = keys{k};
        value = flight_result.(key);
        dispersion_results.(key) = [dispersion_results.(key), value];  % append
    end
end

fclose(fid);

%% Numero di simulazioni
N = numel(dispersion_general_results);
disp(['Number of simulations: ', num2str(N)]);

%% Creazione cartelle per salvataggio grafici
output_folder_svg = fullfile(BASE_DIR, 'images', 'svg');
if ~exist(output_folder_svg,'dir')
    mkdir(output_folder_svg);
end
output_folder_fig = fullfile(BASE_DIR, 'images', 'fig');
if ~exist(output_folder_fig,'dir')
    mkdir(output_folder_fig);
end

%% OUT OF RAIL TIME

out_data = toNumericColumn(dispersion_results.out_of_rail_time);

if numel(out_data) >= 2
    pd_out = fitdist(out_data,'Normal');

    mu_out    = pd_out.mu;
    sigma_out = pd_out.sigma;

    fprintf('Out of Rail Time - Mean: %.3f s\n', mu_out);
    fprintf('Out of Rail Time - Std:  %.3f s\n', sigma_out);

    fig_out = figure('Visible','off');
    histogram(out_data,'Normalization','pdf', ...
        'FaceColor',[0.94 0.5 0.5],'EdgeColor','k');
    hold on

    x_out = linspace(min(out_data), max(out_data), 1000);
    plot(x_out, pdf(pd_out,x_out),'k','LineWidth',2);

    title('Out of Rail Time');
    xlabel('Time (s)');
    ylabel('Probability Density');
    grid on

    saveas(fig_out, fullfile(output_folder_svg,'out_of_rail_time.svg'));
    savefig(fig_out, fullfile(output_folder_fig,'out_of_rail_time.fig'));
    close(fig_out);
else
    warning('Not enough data to fit distribution for Out of Rail Time.');
end
%% OUT OF RAIL VELOCITY

vel_data = dispersion_results.out_of_rail_velocity;

vel_data = vel_data(:);

if numel(vel_data) >= 2
    % Fit distribuzione normale
    pd_vel = fitdist(vel_data, 'Normal');
    mu_vel = pd_vel.mu;
    sigma_vel = pd_vel.sigma;

    fprintf('Out of Rail Velocity - Mean: %.3f m/s\n', mu_vel);
    fprintf('Out of Rail Velocity - Std:  %.3f m/s\n', sigma_vel);

    % Crea figura senza visualizzazione automatica
    fig_vel = figure('Visible','off');
    histogram(vel_data, 'Normalization', 'pdf', ...
        'FaceColor', [0.53 0.81 0.92], 'EdgeColor', 'k');
    hold on

    x_vel = linspace(min(vel_data), max(vel_data), 1000);
    plot(x_vel, pdf(pd_vel, x_vel), 'k', 'LineWidth', 2);

    title('Out of Rail Velocity');
    xlabel('Velocity (m/s)');
    ylabel('Probability Density');
    grid on

    % Salva figure
    saveas(fig_vel, fullfile(output_folder_svg, 'out_of_rail_velocity.svg'));
    savefig(fig_vel, fullfile(output_folder_fig, 'out_of_rail_velocity.fig'));
    close(fig_vel);
else
    warning('Not enough data to fit distribution for Out of Rail Velocity.');
end
%% === APOGEE TIME ===

apo_data = dispersion_results.apogee_time;

% Controllo sufficiente di dati
if numel(apo_data) >= 2
    % Fit distribuzione normale
    pd_apo = fitdist(apo_data(:), 'Normal');
    mu_apo  = pd_apo.mu;
    sigma_apo = pd_apo.sigma;

    fprintf('Apogee Time - Mean: %.3f s\n', mu_apo);
    fprintf('Apogee Time - Std:  %.3f s\n', sigma_apo);

    % Crea figura (invisibile, ma salvabile)
    fig_apo = figure('Visible','off');
    histogram(apo_data, 'Normalization', 'pdf', ...
        'FaceColor', [0.56 0.93 0.56], 'EdgeColor', 'k');
    hold on

    x_apo = linspace(min(apo_data), max(apo_data), 1000);
    plot(x_apo, pdf(pd_apo, x_apo), 'k', 'LineWidth', 2);

    title('Apogee Time');
    xlabel('Time (s)');
    ylabel('Probability Density');
    grid on

    % Salva figure
    saveas(fig_apo, fullfile(output_folder_svg, 'apogee_time.svg'));
    savefig(fig_apo, fullfile(output_folder_fig, 'apogee_time.fig'));
    close(fig_apo);
else
    warning('Not enough data to fit distribution for Apogee Time.');
end


%% === APOGEE ALTITUDE ===

alt_data = dispersion_results.apogee_altitude;

if numel(alt_data) >= 2
    % Fit distribuzione normale
    pd_alt = fitdist(alt_data(:), 'Normal');
    mu_alt  = pd_alt.mu;
    sigma_alt = pd_alt.sigma;

    fprintf('Apogee Altitude - Mean: %.3f m\n', mu_alt);
    fprintf('Apogee Altitude - Std:  %.3f m\n', sigma_alt);

    % Crea figura (invisibile ma salvabile)
    fig_alt = figure('Visible','off');
    histogram(alt_data, 'Normalization', 'pdf', ...
        'FaceColor', [0.53 0.81 0.92], 'EdgeColor', 'k');
    hold on

    x_alt = linspace(min(alt_data), max(alt_data), 1000);
    plot(x_alt, pdf(pd_alt, x_alt), 'k', 'LineWidth', 2);

    title('Apogee Altitude');
    xlabel('Altitude (m)');
    ylabel('Probability Density');
    grid on

    % Salva figure
    saveas(fig_alt, fullfile(output_folder_svg, 'apogee_altitude.svg'));
    savefig(fig_alt, fullfile(output_folder_fig, 'apogee_altitude.fig'));
    close(fig_alt);
else
    warning('Not enough data to fit distribution for Apogee Altitude.');
end
%% === APOGEE X POSITION ===

x_data = dispersion_results.apogee_x;

if numel(x_data) >= 2
    % Fit distribuzione normale
    pd_x = fitdist(x_data(:), 'Normal');
    mu_x  = pd_x.mu;
    sigma_x = pd_x.sigma;

    fprintf('Apogee X Position - Mean: %.3f m\n', mu_x);
    fprintf('Apogee X Position - Std:  %.3f m\n', sigma_x);

    % Crea figura (invisibile ma salvabile)
    fig_x = figure('Visible','off');
    histogram(x_data, 'Normalization', 'pdf', ...
        'FaceColor', [0.94 0.5 0.5], 'EdgeColor', 'k');
    hold on

    x_vals = linspace(min(x_data), max(x_data), 1000);
    plot(x_vals, pdf(pd_x, x_vals), 'k', 'LineWidth', 2);

    title('Apogee X Position');
    xlabel('Apogee X Position (m)');
    ylabel('Probability Density');
    grid on

    % Salva figure
    saveas(fig_x, fullfile(output_folder_svg, 'apogee_x_position.svg'));
    savefig(fig_x, fullfile(output_folder_fig, 'apogee_x_position.fig'));
    close(fig_x);
else
    warning('Not enough data to fit distribution for Apogee X Position.');
end

%% === APOGEE Y POSITION ===

y_data = dispersion_results.apogee_y;

if numel(y_data) >= 2
    % Fit distribuzione normale
    pd_y = fitdist(y_data(:), 'Normal');
    mu_y  = pd_y.mu;
    sigma_y = pd_y.sigma;

    fprintf('Apogee Y Position - Mean: %.3f m\n', mu_y);
    fprintf('Apogee Y Position - Std:  %.3f m\n', sigma_y);

    % Crea figura (invisibile ma salvabile)
    fig_y = figure('Visible','off');
    histogram(y_data, 'Normalization', 'pdf', ...
        'FaceColor', [0.56 0.93 0.56], 'EdgeColor', 'k');
    hold on

    x_vals = linspace(min(y_data), max(y_data), 1000);
    plot(x_vals, pdf(pd_y, x_vals), 'k', 'LineWidth', 2);

    title('Apogee Y Position');
    xlabel('Apogee Y Position (m)');
    ylabel('Probability Density');
    grid on

    saveas(fig_y, fullfile(output_folder_svg, 'apogee_y_position.svg'));
    savefig(fig_y, fullfile(output_folder_fig, 'apogee_y_position.fig'));
    close(fig_y);
else
    warning('Not enough data to fit distribution for Apogee Y Position.');
end

%% === IMPACT TIME ===

impact_time = dispersion_results.impact_time;

if numel(impact_time) >= 2
    % Fit distribuzione normale
    pd_imp_time = fitdist(impact_time(:), 'Normal');
    mu_impact_time  = pd_imp_time.mu;
    sigma_impact_time = pd_imp_time.sigma;

    fprintf('Impact Time - Mean: %.3f s\n', mu_impact_time);
    fprintf('Impact Time - Std:  %.3f s\n', sigma_impact_time);

    % Crea figura (invisibile ma salvabile)
    fig_imp_time = figure('Visible','off');
    histogram(impact_time, 'Normalization', 'pdf', ...
        'FaceColor', [0.53 0.81 0.92], 'EdgeColor', 'k');
    hold on

    x_vals = linspace(min(impact_time), max(impact_time), 1000);
    plot(x_vals, pdf(pd_imp_time, x_vals), 'k', 'LineWidth', 2);

    title('Impact Time');
    xlabel('Time (s)');
    ylabel('Probability Density');
    grid on

    % Salva figure
    saveas(fig_imp_time, fullfile(output_folder_svg, 'impact_time.svg'));
    savefig(fig_imp_time, fullfile(output_folder_fig, 'impact_time.fig'));
    close(fig_imp_time);
else
    warning('Not enough data to fit distribution for Impact Time.');
end

%% === IMPACT X POSITION ===

impact_x = dispersion_results.impact_x;

if numel(impact_x) >= 2
    % Fit distribuzione normale
    pd_imp_x = fitdist(impact_x(:), 'Normal');
    mu_x  = pd_imp_x.mu;
    sigma_x = pd_imp_x.sigma;

    fprintf('Impact X Position - Mean: %.3f m\n', mu_x);
    fprintf('Impact X Position - Std:  %.3f m\n', sigma_x);

    % Crea figura (invisibile ma salvabile)
    fig_imp_x = figure('Visible','off');
    histogram(impact_x, 'Normalization', 'pdf', ...
        'FaceColor', [0.94 0.5 0.5], 'EdgeColor', 'k');  % lightcoral
    hold on

    % Curva di densità della distribuzione normale
    x_vals = linspace(min(impact_x), max(impact_x), 1000);
    plot(x_vals, pdf(pd_imp_x, x_vals), 'k', 'LineWidth', 2);

    title('Impact X Position');
    xlabel('Impact X Position (m)');
    ylabel('Probability Density');
    grid on

    % Salva figure
    saveas(fig_imp_x, fullfile(output_folder_svg, 'impact_x_position.svg'));
    savefig(fig_imp_x, fullfile(output_folder_fig, 'impact_x_position.fig'));
    close(fig_imp_x);
else
    warning('Not enough data to fit distribution for Impact X Position.');
end

%% === IMPACT Y POSITION ===

impact_y = dispersion_results.impact_y;

if numel(impact_y) >= 2
    % Fit distribuzione normale
    pd_imp_y = fitdist(impact_y(:), 'Normal');
    mu_imp_y  = pd_imp_y.mu;
    sigma_imp_y = pd_imp_y.sigma;

    fprintf('Impact Y Position - Mean: %.3f m\n', mu_imp_y);
    fprintf('Impact Y Position - Std:  %.3f m\n', sigma_imp_y);

    % Crea figura (invisibile ma salvabile)
    fig_imp_y = figure('Visible','off');
    histogram(impact_y, 'Normalization', 'pdf', ...
        'FaceColor', [0.56 0.93 0.56], 'EdgeColor', 'k');
    hold on

    x_vals = linspace(min(impact_y), max(impact_y), 1000);
    plot(x_vals, pdf(pd_imp_y, x_vals), 'k', 'LineWidth', 2);

    title('Impact Y Position');
    xlabel('Impact Y Position (m)');
    ylabel('Probability Density');
    grid on

    % Salva figure
    saveas(fig_imp_y, fullfile(output_folder_svg, 'impact_y_position.svg'));
    savefig(fig_imp_y, fullfile(output_folder_fig, 'impact_y_position.fig'));
    close(fig_imp_y);
else
    warning('Not enough data to fit distribution for Impact Y Position.');
end

%% === IMPACT VELOCITY ===

impact_velocity = dispersion_results.impact_velocity;

if numel(impact_velocity) >= 2
    % Fit distribuzione normale
    pd_imp_v = fitdist(impact_velocity(:), 'Normal');
    mu_v  = pd_imp_v.mu;
    sigma_v = pd_imp_v.sigma;

    fprintf('Impact Velocity - Mean: %.3f m/s\n', mu_v);
    fprintf('Impact Velocity - Std:  %.3f m/s\n', sigma_v);

    % Crea figura (invisibile ma salvabile)
    fig_imp_v = figure('Visible','off');
    histogram(impact_velocity, 'Normalization', 'pdf', ...
        'FaceColor', [0.53 0.81 0.92], 'EdgeColor', 'k');
    hold on

    % Curva di densità della distribuzione normale
    x_vals = linspace(min(impact_velocity), max(impact_velocity), 1000);
    plot(x_vals, pdf(pd_imp_v, x_vals), 'k', 'LineWidth', 2);

    title('Impact Velocity');
    xlabel('Velocity (m/s)');
    ylabel('Probability Density');
    grid on

    % Salva figure
    saveas(fig_imp_v, fullfile(output_folder_svg, 'impact_velocity.svg'));
    savefig(fig_imp_v, fullfile(output_folder_fig, 'impact_velocity.fig'));
    close(fig_imp_v);
else
    warning('Not enough data to fit distribution for Impact Velocity.');
end

%% === STATIC MARGINS ===

% Recupera dati
initial_margin = dispersion_results.initial_static_margin;
out_of_rail_margin = dispersion_results.out_of_rail_static_margin;
final_margin = dispersion_results.final_static_margin;

% Fit distribuzione normale (calcola media e deviazione standard)
mu_initial = mean(initial_margin);
std_initial = std(initial_margin);

mu_out = mean(out_of_rail_margin);
std_out = std(out_of_rail_margin);

mu_final = mean(final_margin);
std_final = std(final_margin);

% Stampa valori
fprintf('Initial Static Margin -             Mean Value: %.3f c\n', mu_initial);
fprintf('Initial Static Margin -     Standard Deviation: %.3f c\n', std_initial);
fprintf('Out of Rail Static Margin -         Mean Value: %.3f c\n', mu_out);
fprintf('Out of Rail Static Margin - Standard Deviation: %.3f c\n', std_out);
fprintf('Final Static Margin -               Mean Value: %.3f c\n', mu_final);
fprintf('Final Static Margin -       Standard Deviation: %.3f c\n', std_final);

% Numero di bin simile a sqrt(N)
N = numel(initial_margin);
bins = round(sqrt(N));

% Crea figura invisibile
fig_static = figure('Visible','off'); hold on; grid on;

% Istogrammi normalizzati
histogram(initial_margin, bins, 'Normalization','pdf', 'FaceColor',[0.53 0.81 0.98], 'EdgeColor','k', 'FaceAlpha',0.4);
histogram(out_of_rail_margin, bins, 'Normalization','pdf', 'FaceColor',[1 0.5 0], 'EdgeColor','k', 'FaceAlpha',0.4);
histogram(final_margin, bins, 'Normalization','pdf', 'FaceColor',[0.56 0.93 0.56], 'EdgeColor','k', 'FaceAlpha',0.4);

% Genera vettori x per le PDF
x_initial = linspace(min(initial_margin), max(initial_margin), 1000);
x_out = linspace(min(out_of_rail_margin), max(out_of_rail_margin), 1000);
x_final = linspace(min(final_margin), max(final_margin), 1000);

% Sovrapponi PDF della distribuzione normale stimata
plot(x_initial, normpdf(x_initial, mu_initial, std_initial), 'b-', 'LineWidth',2);
plot(x_out, normpdf(x_out, mu_out, std_out), 'Color',[1 0.55 0], 'LineWidth',2); % dark orange
plot(x_final, normpdf(x_final, mu_final, std_final), 'g-', 'LineWidth',2);

% Titolo, etichette, legenda
title('Static Margin Distribution');
xlabel('Static Margin (c)');
ylabel('Probability Density');
legend('Initial','Out of Rail','Final');
grid on;

% Salva figure
saveas(fig_static, fullfile(output_folder_svg,'static_margin_distribution.svg'));
savefig(fig_static, fullfile(output_folder_fig,'static_margin_distribution.fig'));

% Chiudi figura
close(fig_static);

%% === MAXIMUM VELOCITY ===

% Recupera dati
max_velocity = dispersion_results.max_velocity;

% Fit distribuzione normale
mu_max_velocity = mean(max_velocity);
std_max_velocity = std(max_velocity);

% Stampa valori
fprintf('Maximum Velocity -         Mean Value: %.3f m/s\n', mu_max_velocity);
fprintf('Maximum Velocity - Standard Deviation: %.3f m/s\n', std_max_velocity);

% Numero di bin simile a sqrt(N)
N = numel(max_velocity);
bins = round(sqrt(N));

% Crea figura invisibile
fig_max_velocity = figure('Visible','off'); hold on; grid on;

% Istogramma normalizzato
histogram(max_velocity, bins, 'Normalization','pdf', 'FaceColor',[0.68 0.85 0.9], 'EdgeColor','k', 'FaceAlpha',0.6);

% Genera vettore x per la PDF
x_max_velocity = linspace(min(max_velocity), max(max_velocity), 1000);

% Sovrapponi PDF della distribuzione normale stimata
plot(x_max_velocity, normpdf(x_max_velocity, mu_max_velocity, std_max_velocity), 'k-', 'LineWidth',2);

% Titolo ed etichette
title('Maximum Velocity');
xlabel('Velocity (m/s)');
ylabel('Probability Density');
grid on;

% Salva figure
saveas(fig_max_velocity, fullfile(output_folder_svg,'maximum_velocity_plot.svg'));
savefig(fig_max_velocity, fullfile(output_folder_fig,'maximum_velocity_plot.fig'));

% Chiudi figura
close(fig_max_velocity);

%% === MAXIMUM ACCELERATION ===

% Recupera dati
max_acc = dispersion_results.max_acceleration;

% Fit distribuzione normale
mu_max_acc = mean(max_acc);
std_max_acc = std(max_acc);

% Stampa valori
fprintf('Maximum Acceleration -         Mean Value: %.3f m/s²\n', mu_max_acc);
fprintf('Maximum Acceleration - Standard Deviation: %.3f m/s²\n', std_max_acc);

% Numero di bin simile a sqrt(N)
N = numel(max_acc);
bins = round(sqrt(N));

% Crea figura invisibile
fig_max_acc = figure('Visible','off'); hold on; grid on;

% Istogramma normalizzato
histogram(max_acc, bins, 'Normalization','pdf', 'FaceColor',[0.94 0.50 0.50], 'EdgeColor','k', 'FaceAlpha',0.6);

% Genera vettore x per la PDF
x_max_acc = linspace(min(max_acc), max(max_acc), 1000);

% Sovrapponi PDF della distribuzione normale stimata
plot(x_max_acc, normpdf(x_max_acc, mu_max_acc, std_max_acc), 'k-', 'LineWidth',2);

% Titolo ed etichette
title('Maximum Acceleration');
xlabel('Acceleration (m/s²)');
ylabel('Probability Density');
grid on;

% Salva figure
saveas(fig_max_acc, fullfile(output_folder_svg,'maximum_acceleration_plot.svg'));
savefig(fig_max_acc, fullfile(output_folder_fig,'maximum_acceleration_plot.fig'));

% Chiudi figura
close(fig_max_acc);

%% === NUMBER OF PARACHUTE EVENTS ===

% Recupera dati
num_events = dispersion_results.number_of_events;

% Crea figura invisibile
fig_parachute = figure('Visible','off'); hold on; grid on;

% Istogramma (conteggio degli eventi)
histogram(num_events, 'FaceColor', [1 0.6 0], 'EdgeColor', 'k');

% Titolo ed etichette
title('Parachute Events');
xlabel('Number of Parachute Events');
ylabel('Number of Occurrences');
grid on;

% Salva figure
saveas(fig_parachute, fullfile(output_folder_svg,'parachute_events_plot.svg'));
savefig(fig_parachute, fullfile(output_folder_fig,'parachute_events_plot.fig'));

% Chiudi figura
close(fig_parachute);

%% === DROGUE PARACHUTE TRIGGER TIME ===

% Recupera dati
drogue_trigger = dispersion_results.drogue_triggerTime;

% Fit distribuzione normale
pd_drogue = fitdist(drogue_trigger(:), 'Normal');
mu_drogue = pd_drogue.mu;
sigma_drogue = pd_drogue.sigma;

fprintf('Drogue Parachute Trigger Time - Mean: %.3f s\n', mu_drogue);
fprintf('Drogue Parachute Trigger Time - Std:  %.3f s\n', sigma_drogue);

% Crea figura invisibile
fig_drogue = figure('Visible','off'); hold on; grid on;

% Istogramma normalizzato
histogram(drogue_trigger, 'Normalization', 'pdf', 'FaceColor', [1 0.84 0], 'EdgeColor', 'k');

% Sovrapponi PDF normale
x_vals = linspace(min(drogue_trigger), max(drogue_trigger), 1000);
plot(x_vals, pdf(pd_drogue, x_vals), 'k', 'LineWidth', 2);

% Titolo ed etichette
title('Drogue Parachute Trigger Time');
xlabel('Time (s)');
ylabel('Probability Density');
grid on;

% Salva figure
saveas(fig_drogue, fullfile(output_folder_svg, 'drogue_trigger_time_plot.svg'));
savefig(fig_drogue, fullfile(output_folder_fig, 'drogue_trigger_time_plot.fig'));

% Chiudi figura
close(fig_drogue);

%% === DROGUE PARACHUTE FULLY INFLATED TIME ===

% Recupera dati
drogue_inflated_time = dispersion_results.drogue_inflated_time;

% Fit distribuzione normale
pd_drogue_inflated = fitdist(drogue_inflated_time(:), 'Normal');
mu_drogue_inflated = pd_drogue_inflated.mu;
sigma_drogue_inflated = pd_drogue_inflated.sigma;

fprintf('Drogue Parachute Fully Inflated Time - Mean: %.3f s\n', mu_drogue_inflated);
fprintf('Drogue Parachute Fully Inflated Time - Std:  %.3f s\n', sigma_drogue_inflated);

% Crea figura invisibile
fig_drogue_inflated = figure('Visible','off'); hold on; grid on;

% Istogramma normalizzato
histogram(drogue_inflated_time, 'Normalization', 'pdf', 'FaceColor', [0.78 0.57 0.8], 'EdgeColor', 'k');

% Sovrapponi PDF normale
x_vals = linspace(min(drogue_inflated_time), max(drogue_inflated_time), 1000);
plot(x_vals, pdf(pd_drogue_inflated, x_vals), 'k', 'LineWidth', 2);

% Titolo ed etichette
title('Drogue Fully Inflated Time');
xlabel('Time (s)');
ylabel('Probability Density');
grid on;

% Salva figure
saveas(fig_drogue_inflated, fullfile(output_folder_svg, 'drogue_inflated_time_plot.svg'));
savefig(fig_drogue_inflated, fullfile(output_folder_fig, 'drogue_inflated_time_plot.fig'));

% Chiudi figura
close(fig_drogue_inflated);

%% === DROGUE PARACHUTE FULLY INFLATED VELOCITY ===

% Recupera dati
drogue_velocity = dispersion_results.drogue_inflated_velocity;

% Fit distribuzione normale
pd_drogue_velocity = fitdist(drogue_velocity(:), 'Normal');
mu_drogue_velocity = pd_drogue_velocity.mu;
sigma_drogue_velocity = pd_drogue_velocity.sigma;

fprintf('Drogue Parachute Fully Inflated Velocity - Mean: %.3f m/s\n', mu_drogue_velocity);
fprintf('Drogue Parachute Fully Inflated Velocity - Std:  %.3f m/s\n', sigma_drogue_velocity);

% Crea figura invisibile
fig_drogue_velocity = figure('Visible','off'); hold on; grid on;

% Istogramma normalizzato
histogram(drogue_velocity, 'Normalization', 'pdf', 'FaceColor', [0.13 0.7 0.67], 'EdgeColor', 'k');

% Sovrapponi PDF normale
x_vals = linspace(min(drogue_velocity), max(drogue_velocity), 1000);
plot(x_vals, pdf(pd_drogue_velocity, x_vals), 'k', 'LineWidth', 2);

% Titolo ed etichette
title('Drogue Inflated Velocity');
xlabel('Velocity (m/s)');
ylabel('Probability Density');
grid on;

% Salva figure
saveas(fig_drogue_velocity, fullfile(output_folder_svg, 'drogue_inflated_velocity_plot.svg'));
savefig(fig_drogue_velocity, fullfile(output_folder_fig, 'drogue_inflated_velocity_plot.fig'));

% Chiudi figura
close(fig_drogue_velocity);

%% === MAXIMUM AERODYNAMIC DRAG ===

% Recupera dati
drag = dispersion_results.max_aerodynamic_drag;

% Fit distribuzione normale
pd_drag = fitdist(drag(:), 'Normal');
mu_drag = pd_drag.mu;
sigma_drag = pd_drag.sigma;

fprintf('Maximum Aerodynamic Drag - Mean: %.3f N\n', mu_drag);
fprintf('Maximum Aerodynamic Drag - Std:  %.3f N\n', sigma_drag);

% Crea figura invisibile
fig_drag = figure('Visible','off'); hold on; grid on;

% Istogramma normalizzato
histogram(drag, 'Normalization', 'pdf', 'FaceColor', [0.39 0.58 0.93], 'EdgeColor', 'k');

% Sovrapponi PDF normale
x_vals = linspace(min(drag), max(drag), 1000);
plot(x_vals, pdf(pd_drag, x_vals), 'k', 'LineWidth', 2);

% Titolo ed etichette
title('Maximum Aerodynamic Drag');
xlabel('Drag Force (N)');
ylabel('Probability Density');

% Salva figure
saveas(fig_drag, fullfile(output_folder_svg, 'max_aero_drag_plot.svg'));
savefig(fig_drag, fullfile(output_folder_fig, 'max_aero_drag_plot.fig'));

% Chiudi figura
close(fig_drag);

%% === MAXIMUM AERODYNAMIC LIFT ===

% Recupera dati
lift = dispersion_results.max_aerodynamic_lift;

% Fit distribuzione normale
pd_lift = fitdist(lift(:), 'Normal');
mu_lift = pd_lift.mu;
sigma_lift = pd_lift.sigma;

fprintf('Maximum Aerodynamic Lift - Mean: %.3f N\n', mu_lift);
fprintf('Maximum Aerodynamic Lift - Std:  %.3f N\n', sigma_lift);

% Crea figura invisibile
fig_lift = figure('Visible','off'); hold on; grid on;

% Istogramma normalizzato
histogram(lift, 'Normalization', 'pdf', 'FaceColor', [0.60 0.80 0.68], 'EdgeColor', 'k');

% Sovrapponi PDF normale
x_vals = linspace(min(lift), max(lift), 1000);
plot(x_vals, pdf(pd_lift, x_vals), 'k', 'LineWidth', 2);

% Titolo ed etichette
title('Maximum Aerodynamic Lift');
xlabel('Lift Force (N)');
ylabel('Probability Density');

% Salva figure
saveas(fig_lift, fullfile(output_folder_svg, 'max_aero_lift_plot.svg'));
savefig(fig_lift, fullfile(output_folder_fig, 'max_aero_lift_plot.fig'));

% Chiudi figura
close(fig_lift);

%% === MAXIMUM AERODYNAMIC SPIN MOMENT ===

% Recupera dati
spin_moment = dispersion_results.max_aerodynamic_spin_moment;

% Fit distribuzione normale
pd_spin = fitdist(spin_moment(:), 'Normal');
mu_spin = pd_spin.mu;
sigma_spin = pd_spin.sigma;

fprintf('Maximum Aerodynamic Spin Moment - Mean: %.3f N*m\n', mu_spin);
fprintf('Maximum Aerodynamic Spin Moment - Std:  %.3f N*m\n', sigma_spin);

% Crea figura invisibile
fig_spin = figure('Visible','off'); hold on; grid on;

% Istogramma normalizzato
histogram(spin_moment, 'Normalization', 'pdf', 'FaceColor', [0.47 0.53 0.60], 'EdgeColor', 'k');

% Sovrapponi PDF normale
x_vals = linspace(min(spin_moment), max(spin_moment), 1000);
plot(x_vals, pdf(pd_spin, x_vals), 'k', 'LineWidth', 2);

% Titolo ed etichette
title('Maximum Aerodynamic Spin Moment');
xlabel('Spin Moment (N*m)');
ylabel('Probability Density');

% Salva figure
saveas(fig_spin, fullfile(output_folder_svg, 'max_spin_moment_plot.svg'));
savefig(fig_spin, fullfile(output_folder_fig, 'max_spin_moment_plot.fig'));

% Chiudi figura
close(fig_spin);

%% === MAXIMUM AERODYNAMIC BENDING MOMENT ===

% Recupera dati
bending_moment = dispersion_results.max_aerodynamic_bending_moment;

% Fit distribuzione normale
pd_bend = fitdist(bending_moment(:), 'Normal');
mu_bend = pd_bend.mu;
sigma_bend = pd_bend.sigma;

fprintf('Maximum Aerodynamic Bending Moment - Mean: %.3f N*m\n', mu_bend);
fprintf('Maximum Aerodynamic Bending Moment - Std:  %.3f N*m\n', sigma_bend);

% Crea figura invisibile
fig_bend = figure('Visible','off'); hold on; grid on;

% Istogramma normalizzato
histogram(bending_moment, 'Normalization', 'pdf', 'FaceColor', [0.27 0.51 0.71], 'EdgeColor', 'k');

% Sovrapponi PDF normale
x_vals = linspace(min(bending_moment), max(bending_moment), 1000);
plot(x_vals, pdf(pd_bend, x_vals), 'k', 'LineWidth', 2);

% Titolo ed etichette
title('Maximum Aerodynamic Bending Moment');
xlabel('Bending Moment (N*m)');
ylabel('Probability Density');

% Salva figure
saveas(fig_bend, fullfile(output_folder_svg, 'max_bending_moment_plot.svg'));
savefig(fig_bend, fullfile(output_folder_fig, 'max_bending_moment_plot.fig'));

% Chiudi figura
close(fig_bend);


%% Import background map
img = imread('santamargarida_launchpoint.jpg');

%% Retrieve dispersion data por apogee and impact XY position

apogee_x = dispersion_results.apogee_x;
apogee_y = dispersion_results.apogee_y;
impact_x = dispersion_results.impact_x;
impact_y = dispersion_results.impact_y;

% Crea la figura
figure('Color','w','Renderer','painters','Units','pixels','Position',[100 100 800 600]);

% Crea assi
ax = axes;  % restituisce l'oggetto axes per controllare il grafico

imagesc([-1500 1500], [-1500 1500], flipud(img));
set(gca,'YDir','normal');  % y cresce verso l'alto
axis equal;
hold on;  % da qui in poi tutto sarà sopra l'immagine

% Calcola la matrice di covarianza
impactCov = cov([impact_x(:), impact_y(:)]);  % 2x2

% Calcola autovalori e autovettori ordinati decrescenti
[impactVals, impactVecs] = eigsorted(impactCov);  % usa la funzione MATLAB eigsorted vista prima

% Calcola l'angolo di rotazione dell'ellisse (in gradi)
impactTheta = atan2d(impactVecs(2,1), impactVecs(1,1));  
% impactVecs(:,1) = primo autovettore (massima varianza)
% atan2d(y, x) restituisce l'angolo in gradi

% Dimensioni dell'ellisse
impactW = 2 * sqrt(impactVals(1));  % semiasse maggiore * 2
impactH = 2 * sqrt(impactVals(2));  % semiasse minore * 2

hold on;  % mantieni grafici precedenti

% Centro ellisse
cx = mean(impact_x);
cy = mean(impact_y);

% Colore riempimento RGBA (qui trasparente blu)
faceColor = [0 0 1 0.2];

% Disegna 3 ellissi concentriche
for j = 1:3
    % Crea ellisse con funzione rectangle + Curvature
    h = rectangle('Position',[cx - impactW*j/2, cy - impactH*j/2, impactW*j, impactH*j], ...
                  'Curvature',[1 1], ...
                  'EdgeColor','k', ...
                  'LineWidth',1.5, ...
                  'FaceColor',faceColor);
    
    % Ruota l'ellisse attorno al centro
    rotate(h, [0 0 1], impactTheta, [cx cy 0]);
end

axis equal;

% Calcola la matrice di covarianza
apogeeCov = cov([apogee_x(:), apogee_y(:)]);

% Calcola autovalori e autovettori ordinati decrescenti
[apogeeVals, apogeeVecs] = eigsorted(apogeeCov);  % usa la funzione eigsorted MATLAB

% Calcola angolo di rotazione dell'ellisse (in gradi)
apogeeTheta = atan2d(apogeeVecs(2,1), apogeeVecs(1,1));

% Dimensioni dell'ellisse
apogeeW = 2 * sqrt(apogeeVals(1));
apogeeH = 2 * sqrt(apogeeVals(2));

hold on;  % mantiene eventuali grafici precedenti

% Centro ellisse
cx = mean(apogee_x);
cy = mean(apogee_y);

% Colore di riempimento RGBA (verde trasparente)
faceColor = [0 1 0 0.2];

%ellissi
theta = linspace(0,2*pi,100);  % parametri angolo
R = [cosd(apogeeTheta) -sind(apogeeTheta);
     sind(apogeeTheta)  cosd(apogeeTheta)];

hold on;
for j = 1:3
    % semiassi moltiplicati per j (1σ,2σ,3σ)
    x = (apogeeW*j)/2 * cos(theta);
    y = (apogeeH*j)/2 * sin(theta);
    
    % ruota ellisse
    rotated = R * [x; y];
    
    % trasla al centro
    x_rot = rotated(1,:) + cx;
    y_rot = rotated(2,:) + cy;
    
    % disegna ellisse ruotata con patch
    patch(x_rot, y_rot, [0 1 0], 'FaceAlpha',0.2, 'EdgeColor','k', 'LineWidth',1.5);
end

axis equal;  % assi proporzionati

hold on;  % mantiene eventuali grafici precedenti

% Disegna launch point
scatter(0, 0, 100, 'k', '*', 'DisplayName', 'Launch Point');  
% 100 ≈ s=30 in Python, 'k' = nero, '*' = stella

% Disegna punti apogeo simulati
scatter(apogee_x, apogee_y, 25, [1 0.5 0], '^', 'filled', 'DisplayName', 'Simulated Apogee');  
% 25 ≈ s=5, [1 0.5 0] = arancione, '^' = triangolo su, 'filled' riempie il marker

% Disegna punti impatto simulati
scatter(impact_x, impact_y, 25, [1 1 0], 'v', 'filled', 'DisplayName', 'Simulated Landing Point');  
% [1 1 0] = giallo, 'v' = triangolo giù

legend('Location','best');  % mostra la legenda

title('1\sigma, 2\sigma and 3\sigma Dispersion Ellipses: Apogee and Landing Points', ...
      'Interpreter','tex');  % puoi usare 'latex' se vuoi simboli LaTeX

xlabel('East (m)');
ylabel('North (m)');

hold on;


% Disegna assi centrali
plot([ -1500 1500 ], [ 0 0 ], 'k', 'LineWidth', 0.5);  % asse x
plot([ 0 0 ], [ -1500 1500 ], 'k', 'LineWidth', 0.5);  % asse y

% Imposta limiti assi
xlim([-1500 1500]);
ylim([-1500 1500]);

axis equal;  % proporzioni uguali tra x e y

% Nome file senza estensione
filename = 'my_plot';  % sostituire con il nome desiderato

% Salva figura in PDF
saveas(gcf, [filename '.pdf']);  

% Salva figura in SVG
saveas(gcf, [filename '.svg']);  

% Mostra la figura (di default in MATLAB le figure si aprono già)
figure(gcf);

%% Visualizzazione del razzo e del motore
Atlas.draw();
Atlas.info();
Pro75_8187M1545_P.draw();
Pro75_8187M1545_P.info();