% RocketPy Preliminary Simulation of the Atlas rocket, Aurora Rocketry Team, EuRoC 2025
% Authors: Daniele Bandini, Giovanni Bacchini, Caio Scattolini, Leonardo
% Francesco Neri, Alex Petrani, Federico Pedicini, Lorenzo Pintauro,
% Alessio Mrass, Andrea Di Maio; Matlab port Riccardo Bruscella

%% READ BEFORE USING !!!

% Sometimes, with certain versions of Python, it freezes inexplicably and throws an error; close and reopen Matlab if it says something like: Unable to launch Simple server: Unable to launch C:\Program Files\MATLAB\R2025b\interprocess\bin\win64\pycli\MATLABPyHost.exe
% because: An error occurred while initializing child process: While attempting to execute "C:\Program Files\MATLAB\R2025b\interprocess\bin\win64\pycli\MATLABPyHost.exe -layeredTransport -NamedPipeHandle 0000000000001910:000000000000190C":
% CreateProcessW: The parameter is incorrect [system:87] Also, it sometimes gets stuck at "out of rail time", simply turn it off and back on if it takes more than 10 seconds to load the next one. However, if it doesn't cause problems the first time, you can run as many simulations as you like.

%%

clc; clear; close all

%% Importing libraries
pyenv('ExecutionMode','OutOfProcess');

rocketpy = py.importlib.import_module('rocketpy');
Environment = rocketpy.environment.Environment;
SolidMotor = rocketpy.motors.solid_motor.SolidMotor;
Rocket     = rocketpy.rocket.Rocket;
Flight     = rocketpy.simulation.flight.Flight;
CompareFlights = rocketpy.CompareFlights;

% Matplotlib

mpl = py.importlib.import_module('matplotlib');
mpl.use('Qt5Agg');  % Sets the rendering backend

plt = py.importlib.import_module('matplotlib.pyplot');

time = py.importlib.import_module('time');

process_time = py.importlib.import_module('time').process_time;

np = py.importlib.import_module('numpy');
imageio = py.importlib.import_module('imageio.v2');
norm = py.importlib.import_module('scipy.stats').norm;
pathlib = py.importlib.import_module('pathlib');
json = py.importlib.import_module('json');
os = py.importlib.import_module('os');

analysis_parameters = struct( ...
    ...
    ... === Mass Details ===
    ...
    "rocket_dry_mass",              [25.557316146344952, 5/1000], ...       Rocket's dry mass without grains' weight (kg) and its uncertainty (standard deviation)
    "rocket_dry_inertia_11",        [14.24264697322362, 5/1000], ...        Rocket's dry inertia moment perpendicular to its axis (kg*m^2)
    "rocket_dry_inertia_33",        [0.07475822585846044, 122/100000], ...  Rocket's dry inertia moment relative to its axis (kg*m^2)
    "motor_dry_mass",               [0.00014008279656163892, 5/10000], ...  Motors's dry mass without propellant (kg) and its uncertainty (standard deviation). The weight of the motor structure is included in the rocket dry mass
    "motor_inertia_11",             [0, 0], ...                             Motor's dry inertia moment perpendicular to its axis (kg*m^2)
    "motor_inertia_33",             [0, 0], ...                             Motor's dry inertia moment relative to its axis (kg*m^2)
    "motor_dry_mass_position",      [-0.0009085305748945343, 5/10000], ...  Distance between the origin of the referential system and motor's center of dry mass (m)
    ...
    ... === Propulsion Details ===
    ...
    ... NOTE: many of these values have been estimated based on the few data made available by the motor producers, such as
    ... technical drawings for the exterior of the motor and information about the total mass of the grains.
    ... You can check the grain_dimensions.m file to see the algorithm we used to calculate the grain inner radius and length from known data.
    ...
    "impulse",                      [9974.69314944336, 1/2], ...            Motor total impulse (N*s)
    "burn_time",                    [4.241530000474283, 5/10000], ...       Motor burn out time (s)
    "nozzle_radius",                [0.029609041769879437, 5/100000], ...   Motor's nozzle radius (m), obtained by scaling the known geometry of a Pro54 rocket motor nozzle (real nozzle geometry for Pro75 motors is not publicly available)
    "throat_radius",                [0.02061346614970209, 5/100000], ...    Motor's nozzle throat radius (m), obtained by scaling the known geometry of a Pro54 rocket motor nozzle (real nozzle geometry for Pro75 motors is not publicly available)
    "grain_separation",             [0.0030038288314371397, 1/100000], ...  Motor's grain separation (axial distance between two grains) (m)
    "grain_density",                [1793.144452848121, 1], ...             Motor's grain density (kg/m^3)
    "grain_outer_radius",           [0.0358862665080544, 1/10000], ...      Motor's grain outer radius (m)
    "grain_initial_inner_radius",   [0.018244189740641525, 1/10000], ...    Motor's grain inner radius (m)
    "grain_initial_height",         [0.15606465340865924, 1/10000], ...     Motor's grain height (m)
    ...
    ... === Aerodynamic Details ===
    ...
    "radius",                       [0.07505427553527239, 5/10000], ...     Rocket's radius (m)
    "nozzle_position",              [-1.4356434056096632, 5/10000], ...     Distance between the origin of the referential system and nozzle exit plane (m)
    "grains_center_of_mass_position", [-0.9416508541354824, 5/10000], ...   Distance between the origin of the referential system and center of propellant mass (m) 
    "power_off_drag_corr",          [0.999662229247697, 5/10000], ...       Multiplier for rocket's power off drag curve to introduce uncertainty
    "power_on_drag_corr",           [0.999684901446651, 5/10000], ...       Multiplier for rocket's power on drag curve to introduce uncertainty
    "nose_length",                  [0.4318204474378214, 5/10000], ...      Rocket's nose cone length (m)
    "nose_pwr",                     [0.0013344335093664473, 5/10000], ...   Power of the function that describes the shape of the nose cone
    "tail_distance_to_RCDM",        [-1.3817218728592324, 5/10000], ...     Axial distance between Rocket's Center of Dry Mass (RCDM) and nearest point in its tail (m)
    "nose_distance_to_RCDM",        [1.186553244548323, 5/10000], ...       Axial distance between RCDM and nearest point in its nose cone (m)
    "fin_number",                   [3, 0], ...                             Number of fins
    "fin_span",                     [0.1411278097292937, 5/10000], ...      Fin span (m)
    "fin_root_chord",               [0.27961219250706315, 5/10000], ...     Fin root chord (m)
    "fin_tip_chord",                [0.060099338721757094, 5/10000], ...    Fin tip chord (m)
    "fin_distance_to_RCDM",         [-1.0944302263040155, 5/10000], ...     Axial distance between rocket's center of dry mass and nearest point in its fin (m)
    "fin_sweep_angle",              [58.20330491214908, 5/10000], ...       Fin sweep angle (degrees)
    "tail_length",                  [0.07548110603059785, 5/10000], ...     Tail length (m)
    "tail_bottom_radius",           [0.050987990564273125, 5/10000], ...    Tail bottom radius (m)
    "tail_top_radius",              [0.07536245478270502, 5/10000], ...     Tail top radius (m)
    ...
    ... === Launch and Environment Details ===
    ...
    "inclination",                  [83.28515711632079, 0], ...             Launch rail inclination angle relative to the horizontal plane (degrees)
    "heading",                      [145.8682799655182, 0], ...             Launch rail heading relative to north (degrees)
    "rail_length",                  [10.996068095179226, 5/1000], ...       Launch rail length (m)
    "ensemble_member",              0:9, ...                                Members of the ensemble forecast to be used
    ...
    ... === Parachute Details ===
    ...
    "cd_s_drogue",                  [0.8856717513467018, 6/1000], ...       Drag coefficient times reference area for the rocket drogue chute (m^2)
    "cd_s_main",                    [13.663905632394899, 277/1000], ...     Drag coefficient times reference area for the rocket main chute (m^2)
    "lag_rec",                      [1.77566338618894, 1/10], ...           Time delay between parachute ejection signal is detected and parachute is inflated (s)
    ...
    ... === Rail buttons Details ===
    ...
    "upper_button_y",               [1.0468103443907182, 1/200], ...        Position of the rail button closer to the tip of the rocket (m)
    "lower_button_y",               [-0.5209702470425779, 1/200], ...       Position of the rail button further to the tip of the rocket (m)
    "angular_button",               [-0.00507449010544642, 1/100], ...      Angular position of the buttons (degrees)
    ...
    ... === Electronic Systems and Sensors Details ===
    ...
    "lag_se",                       [0.04326722662182819, 3/200], ...       Time delay between sensor signal is received and ejection signal is fired (s)
    "noise_mean",                   [-0.00023540291268519788, 1/1000], ...  Mean noise value of the Pressure signal (Pa)
    "noise_p_stdev",                [6.486121224039615, 1/100], ...         Standard deviation of the Pressure signal (Pa)
    "noise_p_tc",                   [0.31510046729879354, 1/100] ...        Time correlation of the Pressure signal
);



% Definition of global variables, to be used inside and outside parachute functions

global last_negative_time apogee_detected sampling_rate
last_negative_time=py.None;  % This variable marks the first instant in which a negative velocity is detected
apogee_detected=false;  % This variable indicates whether the algorythm has acknowledged the rocket has reached apogee. A "False" value may mean that negative velocity has not yet been detected, or that it has been detected but has not yet been consistent for enough seconds (the threshold)
sampling_rate=105;      % This variable indicates the sampling rate of the recovery activation algorythm
parachute_stopwatch=0;  % This variable keeps track of the flight time from ignition to the first recovery event

% Importing parachute triggers from python
triggers = py.importlib.import_module('simulation_triggers');

this_file = mfilename('fullpath');
BASE_DIR = fileparts(this_file);

%% Base directory e file name
if ~exist('BASE_DIR','var')
    BASE_DIR = pwd;
end

% Basic analysis info
filename = fullfile(BASE_DIR, "Atlas");

disp("Filename is:");
disp(filename);

number_of_simulations = 10;

%% Create data files for inputs, outputs and error logging
global dispersion_error_file dispersion_input_file dispersion_output_file

% Deletion of already existing files
if exist(filename + ".disp_errors.txt", 'file'),  delete(filename + ".disp_errors.txt");  end
if exist(filename + ".disp_inputs.json", 'file'),  delete(filename + ".disp_inputs.json");  end
if exist(filename + ".disp_outputs.json", 'file'), delete(filename + ".disp_outputs.json"); end

dispersion_error_file  = fopen(filename + ".disp_errors.txt", 'w');
dispersion_input_file  = filename + ".disp_inputs.json";
dispersion_output_file = filename + ".disp_outputs.json";

%% Initialize counter and timer
i = 0;

initial_wall_time = tic;   % Equivalent to time.time()
initial_cpu_time  = process_time();   % Equivalent to process_time()

% Define basic Environment object
Env = Environment(pyargs( ...
        'date', py.tuple({py.int(2025), py.int(10), py.int(13), py.int(16)}), ...  %(Year, Month, Day, Hour)
        'longitude', -8.288963, ...
        'latitude', 39.3897, ...
        'elevation', 160, ...
        'max_expected_height', 4500 ...
    ) ...
);

% Import the .json file with the mean environment values
data = jsondecode(fileread(fullfile(BASE_DIR, "mean_environment_values.json")));

% Set the environment model with either of the 3 options below

% =================================================================== OPTION 1: average metheorological conditions ===================================================================

% In order to define the mean environment features, we used the built-in function "Environment Analysis" from RocketPy. This generates a .json file with the mean environment values based on 
% a sample of 19 years, from 2005 to 2024, between the 10th and 15th of October, by feeding the NetCDF4 data from Copernicus. The .json file contains a series of .csv profiles based on the altitude 
% that define pressure, temperature and wind vectors on an hourly basis. For more information consult the "mean_environment_values.json" file inside the directory.

% REMOVE COMMENT FROM THE FOLLOWING SECTION TO RUN SIMULATION USING THESE SETTINGS ---------------------------------%

% hour_str = sprintf('x%d', double(Env.date{4}));
% 
% Env.set_atmospheric_model(pyargs( ...
%     type="custom_atmosphere", ...                                                                                        %
% ...
%     pressure = data.atmospheric_model_pressure_profile.(hour_str), ...                                      %
%     temperature = data.atmospheric_model_temperature_profile.(hour_str), ...                                  %
%     wind_u = data.atmospheric_model_wind_velocity_x_profile.(hour_str), ...                                    %
%     wind_v = data.atmospheric_model_wind_velocity_y_profile.(hour_str) ...                                     %
% ));

    %-------------------------------------------------------------------------------------------------------------------%
      
    % =================================================================== OPTION 2: worst successful launch day recorded from past EuRoC editions ===================================================================

    % We researched the worst weather conditions in which launches at EuRoC have still taken place, and found that 11/10/2024 qualified for being one of the most windy in which launches were still conducted. We used
    % ensemble-type weather models to simulate flight operations using data from that day and evaluate predicted flight performance, finding that the apogee would be severely lowered, but would still be satisfactory.

    % REMOVE COMMENT FROM THE FOLLOWING SECTION TO RUN SIMULATION USING THESE SETTINGS ---------------------------------%
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
})));    
        %
    %-------------------------------------------------------------------------------------------------------------------%

    % =================================================================== OPTION 3: worst plausible case scenario ===================================================================

    % To evaluate the worst case for bending stresses on the structure, we decided to run a simulation assuming constant winds as strong as the peak values in the worst day (11/10/2024) and aligned with the launch
    % heading, causing the rocket to steer violently into the wind and generate high bending moment on the structure in this maneouvre. The apogee would be reduced to just under 2700 m, but the airframe
    % of the rocket would resist the stress. Ailerons, however, would have to sustain a high load factor (presumably around 4Gs, by the look of the acceleration profiles)

    % REMOVE COMMENT FROM THE FOLLOWING SECTION TO RUN SIMULATION USING THESE SETTINGS ---------------------------------%
% Env.set_atmospheric_model(pyargs( ...                                                                                                                  %
%     type="custom_atmosphere", ...                                                                                         %
%     wind_u = py.list({py.tuple({0, -1.5}), py.tuple({4500, -1.5})}), ...
%     wind_v = py.list({py.tuple({0, 0}), py.tuple({4500, 0})}) ...
% ));
                                                                                                                       %
    %-------------------------------------------------------------------------------------------------------------------%

    % =================================================================== OPTION 4: actual weather forecast ===================================================================

    % REMOVE COMMENT FROM THE FOLLOWING SECTION TO RUN SIMULATION USING THESE SETTINGS ---------------------------------%
% Env.set_atmospheric_model(pyargs( ...                                                                                                                 %
%     'type', py.str("forecast"), ...                                                                                                 %
%     'file', py.str("GFS") ...                                                                                                      %
% ));                                                                                                                %
    %-------------------------------------------------------------------------------------------------------------------%  

% Initiate collection of flight data. This allows to compare different flight from the Montecarlo analysis and visualize data dispersion and overall characteristics of the flight and the simulation itself
flights = cell(1, number_of_simulations); % Preallocation

% Iterate over flight settings
settings_list = flight_settings(analysis_parameters, number_of_simulations);

disp('Starting');
for idx = 1:length(settings_list)

    setting = settings_list{idx};
    
    % Reinitialize global variables for each simulation
    last_negative_time = py.None;
    apogee_detected = false;
    parachute_stopwatch = 0;
    
    start_time = process_time();
    i = i+1;
    fprintf('\rCurrent iteration: %d', i);
   
    if Env.atmospheric_model_type == "Ensemble"
        % Update environment object
        ensemb = py.int(setting.ensemble_member);
        Env.select_ensemble_member(ensemb);
    end

    % Define COTS motor

    % These variables are defined and then called inside the motor
    inertia_vec = [setting.motor_inertia_11, setting.motor_inertia_11, setting.motor_inertia_33];
    dry_inertia_py = py.list(num2cell(double(inertia_vec)));  % ensure scalars -> Python numbers
    reshape_thrust_curve_py = py.tuple(num2cell( [setting.burn_time, setting.impulse] ));

    Pro75_8187M1545_P = SolidMotor(pyargs( ...
        ... Thrust data
        'thrust_source', fullfile(BASE_DIR, 'Cesaroni_8187M1545_P.csv'), ...
        'burn_time', setting.burn_time, ...
        'reshape_thrust_curve', reshape_thrust_curve_py, ...
        'interpolation_method', 'linear', ...
        ... Nozzle data
        'nozzle_radius', setting.nozzle_radius, ...
        'throat_radius', setting.throat_radius, ...
        ... Grain data
        'grain_number', py.int(6), ...
        'grain_separation', setting.grain_separation, ...
        'grain_density', setting.grain_density, ...
        'grain_outer_radius', setting.grain_outer_radius, ...
        'grain_initial_inner_radius', setting.grain_initial_inner_radius, ...
        'grain_initial_height', setting.grain_initial_height, ...
        ... Geometric data
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
        ...
        ... Define the center of dry mass as the origin of the frame of reference, and set the positive axis orientation
        'center_of_mass_without_motor', 0, ...     
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
    Atlas.power_off_drag = Atlas.power_off_drag*setting.power_off_drag_corr;
    Atlas.power_on_drag = Atlas.power_on_drag*setting.power_on_drag_corr;
    
    % Define and add the Nosecone section
    NoseCone = Atlas.add_nose(pyargs( ... 
        'length', setting.nose_length, ...
        'kind', 'lvhaack', ...
        'power', setting.nose_pwr, ...
        'position', setting.nose_distance_to_RCDM + setting.nose_length ...
    ));
    
    % Define and add the Fins
    FinSet = Atlas.add_trapezoidal_fins(pyargs( ...
        'n', py.int(3), ...
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
    py.importlib.reload(triggers);
    
    % Reinitialize the trigger state in Python
    triggers.define_variables(py.None, false, 0, sampling_rate);

    Drogue = Atlas.add_parachute(pyargs( ...
        'name', 'Drogue', ...
        'cd_s', setting.cd_s_drogue, ...
        'trigger', triggers.simulator_check_drogue_opening ...
    ));
        Drogue.sampling_rate=sampling_rate;
        Drogue.lag=setting.lag_rec + setting.lag_se;
        Drogue.noise=[setting.noise_mean, setting.noise_p_stdev, setting.noise_p_tc];
    
    % Define and add the Main parachute
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

        % Creating Python flight object
        rocket_flight = Flight(pyargs( ...
            'rocket', Atlas, ...
            'environment', Env, ...
            'rail_length', setting.rail_length, ...
            'inclination', setting.inclination, ...
            'heading', setting.heading, ...
            'max_time', py.int(600) ...
        ));
        flight_result=export_flight_data(setting, rocket_flight, process_time() - start_time());
        flights{idx} = rocket_flight;

    catch ME
        disp(ME.message);
        export_flight_error(setting)
    end

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

% Done

%% Print and save total time
final_string = sprintf('Completed %d iterations successfully. Total CPU time: %.2f s. Total wall time: %.2f s', ...
    i, cputime - initial_cpu_time, toc(initial_wall_time));
disp(final_string);

%% Close files
fclose(dispersion_error_file);

filename = fullfile(BASE_DIR, 'Atlas');

%% Initialize variable to store all results
% List of all flights (empty)
dispersion_general_results = cell(1, number_of_simulations); % Preallocation

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

% Get all dispersion results
% Get file
fid = fopen(filename + ".disp_outputs.json", "r");

idx=1;

% Read each line of the file and convert to dict
while ~feof(fid)
    line = fgetl(fid);
    % Skip comments lines
    if isempty(line)
        continue
    end
    if line(1) ~= '{'
        continue
    end
    
    % Eval results and store them
    flight_result = jsondecode(line);
    dispersion_general_results{idx} = flight_result;
    idx=idx+1;
    
    keys = fieldnames(flight_result);
    for k = 1:numel(keys)
        key = keys{k};
        value = flight_result.(key);
        dispersion_results.(key) = [dispersion_results.(key), value];  % Small note that if you do 100000+ simulations in one sitting it might become slow and/or crash, but I don't think it'll ever matter
    end
end

% Close data file
fclose(fid);

%% Print number of flights simulated
N = numel(dispersion_general_results);
disp(['Number of simulations: ', num2str(N)]);

% Initialize the path in which the graphic results of the simulation will be saved, both in .svg and fig format. The fig format was 
% chosen so that the user can open the images/graphs files via Matlab

% Create an output folder for .svg files
output_folder_svg = fullfile(BASE_DIR, 'images', 'svg');
if ~exist(output_folder_svg,'dir')
    mkdir(output_folder_svg);
end

% Create an output folder for fig files
output_folder_fig = fullfile(BASE_DIR, 'images', 'fig');
if ~exist(output_folder_fig,'dir')
    mkdir(output_folder_fig);
end

% The following section generates the output distribution plots and automatically saves them on your PC, in the same folder this code is located.
% To create each picture, the algorythm performs the following actions:

% - Fits a normal distribution to the dataset and compute the average value and standard deviation;
% - Prints the fitted mean and standard deviation,
% - Creates a histogram of the data and overlays the corresponding normal distribution curve;
% - Adds title, axis labels, and a grid to the plot for better clarity;
% - Saves the plot as a .svg file for high-quality output (e.g., for reports or web use);
% - Saves the entire figure as a fig file for later reuse or resizing;

% An additional step may be included to prevent automatic sequential display while running the simulation:

% - Closes the figure to prevent automatic sequential display. This would be an obstacle for analysts trying to visualize more plots at once, after they have all been generated

% All distribution plots are generated, saved and made available using this architecture

%% OUT OF RAIL TIME
out_data = toNumericColumn(dispersion_results.out_of_rail_time);

if numel(out_data) >= 2 % Checking if there is data for out of rail time
    pd_out_time = fitdist(out_data,'Normal');

    mu_out_time    = pd_out_time.mu;
    sigma_out_time = pd_out_time.sigma;

    fprintf('Out of Rail Time - Mean: %.3f s\n', mu_out_time);
    fprintf('Out of Rail Time - Std:  %.3f s\n', sigma_out_time);


    % Create the figure
    fig_out = figure('Visible','off');

    % Number of bins (square-root rule matching Python)
    n_bins = floor(sqrt(numel(out_data)));

histogram(out_data, 'Normalization', 'pdf', ...
    'NumBins', n_bins, ...
    'FaceColor', [0.94 0.5 0.5], 'EdgeColor', 'k');
    hold on

    x_out = linspace(min(out_data), max(out_data), 1000);
    plot(x_out, pdf(pd_out_time,x_out),'k','LineWidth',2);

    title('Out of Rail Time');
    xlabel('Time (s)');
    ylabel('Probability Density');
    grid on

    % Save figure as SVG 
    saveas(fig_out, fullfile(output_folder_svg,'out_of_rail_time.svg'));

    % Save figure as MATLAB fig
    savefig(fig_out, fullfile(output_folder_fig,'out_of_rail_time.fig'));

    % Stop automatic printing of images
    close(fig_out);
else
    warning('Not enough data to fit distribution for Out of Rail Time.');
end



%% OUT OF RAIL VELOCITY
vel_data = dispersion_results.out_of_rail_velocity;
vel_data = vel_data(:);

if numel(vel_data) >= 2 % Checking if there is data for out of rail velocity
    pd_vel = fitdist(vel_data, 'Normal');
    mu_vel = pd_vel.mu;
    sigma_vel = pd_vel.sigma;

    fprintf('Out of Rail Velocity - Mean: %.3f m/s\n', mu_vel);
    fprintf('Out of Rail Velocity - Std:  %.3f m/s\n', sigma_vel);

    % Create the figure
    fig_vel = figure('Visible','off');

    % Number of bins (square-root rule matching Python)
    n_bins = floor(sqrt(numel(vel_data)));

    histogram(vel_data, 'Normalization', 'pdf', ...
        'NumBins', n_bins, ...
        'FaceColor', [0.53 0.81 0.92], 'EdgeColor', 'k');
    hold on

    x_vel = linspace(min(vel_data), max(vel_data), 1000);
    plot(x_vel, pdf(pd_vel, x_vel), 'k', 'LineWidth', 2);

    title('Out of Rail Velocity');
    xlabel('Velocity (m/s)');
    ylabel('Probability Density');
    grid on

    % Save figure as SVG 
    saveas(fig_vel, fullfile(output_folder_svg, 'out_of_rail_velocity.svg'));

    % Save figure as MATLAB fig
    savefig(fig_vel, fullfile(output_folder_fig, 'out_of_rail_velocity.fig'));

    % Stop automatic printing of images
    close(fig_vel);
else
    warning('Not enough data to fit distribution for Out of Rail Velocity.');
end


%% === APOGEE TIME ===
apo_data = dispersion_results.apogee_time;

if numel(apo_data) >= 2 % Checking if there is data for apogee time
    pd_apo = fitdist(apo_data(:), 'Normal');
    mu_apo  = pd_apo.mu;
    sigma_apo = pd_apo.sigma;

    fprintf('Apogee Time - Mean: %.3f s\n', mu_apo);
    fprintf('Apogee Time - Std:  %.3f s\n', sigma_apo);

    % Create the figure
    n_bins = floor(sqrt(numel(apo_data)));
    fig_apo = figure('Visible','off');
    histogram(apo_data, 'Normalization', 'pdf', ...
        'NumBins', n_bins, ...
        'FaceColor', [0.56 0.93 0.56], 'EdgeColor', 'k');
    hold on
    x_apo = linspace(min(apo_data), max(apo_data), 1000);
    plot(x_apo, pdf(pd_apo, x_apo), 'k', 'LineWidth', 2);
    
    title('Apogee Time');
    xlabel('Time (s)');
    ylabel('Probability Density');
    grid on

    % Save figure as SVG 
    saveas(fig_apo, fullfile(output_folder_svg, 'apogee_time.svg'));

    % Save figure as MATLAB fig
    savefig(fig_apo, fullfile(output_folder_fig, 'apogee_time.fig'));

    % Stop automatic printing of images
    close(fig_apo);
else
    warning('Not enough data to fit distribution for Apogee Time.');
end


%% === APOGEE ALTITUDE ===
alt_data = dispersion_results.apogee_altitude;

if numel(alt_data) >= 2 % Checking if there is data for apogee altitude
    pd_alt = fitdist(alt_data(:), 'Normal');
    mu_alt  = pd_alt.mu;
    sigma_alt = pd_alt.sigma;

    fprintf('Apogee Altitude - Mean: %.3f m\n', mu_alt);
    fprintf('Apogee Altitude - Std:  %.3f m\n', sigma_alt);

    % Create the figure
    n_bins = floor(sqrt(numel(alt_data)));
    fig_alt = figure('Visible','off');
    histogram(alt_data, 'Normalization', 'pdf', ...
        'NumBins', n_bins, ...
        'FaceColor', [0.53 0.81 0.92], 'EdgeColor', 'k');
    hold on
    x_alt = linspace(min(alt_data), max(alt_data), 1000);
    plot(x_alt, pdf(pd_alt, x_alt), 'k', 'LineWidth', 2);
    
    title('Apogee Altitude');
    xlabel('Altitude (m)');
    ylabel('Probability Density');
    grid on

    % Save figure as SVG 
    saveas(fig_alt, fullfile(output_folder_svg, 'apogee_altitude.svg'));

    % Save figure as MATLAB fig
    savefig(fig_alt, fullfile(output_folder_fig, 'apogee_altitude.fig'));
    
    % Stop automatic printing of images
    close(fig_alt);
else
    warning('Not enough data to fit distribution for Apogee Altitude.');
end


%% === APOGEE X POSITION ===
x_data = dispersion_results.apogee_x;

if numel(x_data) >= 2 % Checking if there is data for apogee x position
    pd_x = fitdist(x_data(:), 'Normal');
    mu_x  = pd_x.mu;
    sigma_x = pd_x.sigma;

    fprintf('Apogee X Position - Mean: %.3f m\n', mu_x);
    fprintf('Apogee X Position - Std:  %.3f m\n', sigma_x);

    % Create the figure
    n_bins = floor(sqrt(numel(x_data)));
    fig_x = figure('Visible','off');
    histogram(x_data, 'Normalization', 'pdf', ...
        'NumBins', n_bins, ...
        'FaceColor', [0.94 0.5 0.5], 'EdgeColor', 'k');
    hold on
    x_vals = linspace(min(x_data), max(x_data), 1000);
    plot(x_vals, pdf(pd_x, x_vals), 'k', 'LineWidth', 2);
    
    title('Apogee X Position');
    xlabel('Apogee X Position (m)');
    ylabel('Probability Density');
    grid on

    % Save figure as SVG 
    saveas(fig_x, fullfile(output_folder_svg, 'apogee_x_position.svg'));

    % Save figure as MATLAB fig
    savefig(fig_x, fullfile(output_folder_fig, 'apogee_x_position.fig'));

    % Stop automatic printing of images
    close(fig_x);
else
    warning('Not enough data to fit distribution for Apogee X Position.');
end


%% === APOGEE Y POSITION ===
y_data = dispersion_results.apogee_y;

if numel(y_data) >= 2 % Checking if there is data for apogee y position
    pd_y = fitdist(y_data(:), 'Normal');
    mu_y  = pd_y.mu;
    sigma_y = pd_y.sigma;

    fprintf('Apogee Y Position - Mean: %.3f m\n', mu_y);
    fprintf('Apogee Y Position - Std:  %.3f m\n', sigma_y);

    % Create the figure
    n_bins = floor(sqrt(numel(y_data)));
    fig_y = figure('Visible','off');
    histogram(y_data, 'Normalization', 'pdf', ...
        'NumBins', n_bins, ...
        'FaceColor', [0.56 0.93 0.56], 'EdgeColor', 'k');
    hold on
    x_vals = linspace(min(y_data), max(y_data), 1000);
    plot(x_vals, pdf(pd_y, x_vals), 'k', 'LineWidth', 2);
    
    title('Apogee Y Position');
    xlabel('Apogee Y Position (m)');
    ylabel('Probability Density');
    grid on

    % Save figure as SVG 
    saveas(fig_y, fullfile(output_folder_svg, 'apogee_y_position.svg'));

    % Save figure as MATLAB fig
    savefig(fig_y, fullfile(output_folder_fig, 'apogee_y_position.fig'));

    % Stop automatic printing of images
    close(fig_y);
else
    warning('Not enough data to fit distribution for Apogee Y Position.');
end


%% === IMPACT TIME ===
impact_time = dispersion_results.impact_time;

if numel(impact_time) >= 2 % Checking if there is data for impact time
    pd_imp_time = fitdist(impact_time(:), 'Normal');
    mu_impact_time  = pd_imp_time.mu;
    sigma_impact_time = pd_imp_time.sigma;

    fprintf('Impact Time - Mean: %.3f s\n', mu_impact_time);
    fprintf('Impact Time - Std:  %.3f s\n', sigma_impact_time);

    % Create the figure
    n_bins = floor(sqrt(numel(impact_time)));
    fig_imp_time = figure('Visible','off');
    histogram(impact_time, 'Normalization', 'pdf', ...
        'NumBins', n_bins, ...
        'FaceColor', [0.53 0.81 0.92], 'EdgeColor', 'k');
    hold on
    x_vals = linspace(min(impact_time), max(impact_time), 1000);
    plot(x_vals, pdf(pd_imp_time, x_vals), 'k', 'LineWidth', 2);
    
    title('Impact Time');
    xlabel('Time (s)');
    ylabel('Probability Density');
    grid on

    % Save figure as SVG 
    saveas(fig_imp_time, fullfile(output_folder_svg, 'impact_time.svg'));

    % Save figure as MATLAB fig
    savefig(fig_imp_time, fullfile(output_folder_fig, 'impact_time.fig'));

    % Stop automatic printing of images
    close(fig_imp_time);
else
    warning('Not enough data to fit distribution for Impact Time.');
end


%% === IMPACT X POSITION ===
impact_x = dispersion_results.impact_x;

if numel(impact_x) >= 2 % Checking if there is data for impact x position
    pd_imp_x = fitdist(impact_x(:), 'Normal');
    mu_x  = pd_imp_x.mu;
    sigma_x = pd_imp_x.sigma;

    fprintf('Impact X Position - Mean: %.3f m\n', mu_x);
    fprintf('Impact X Position - Std:  %.3f m\n', sigma_x);

    % Create the figure
    n_bins = floor(sqrt(numel(impact_x)));
    fig_imp_x = figure('Visible','off');
    histogram(impact_x, 'Normalization', 'pdf', ...
        'NumBins', n_bins, ...
        'FaceColor', [0.94 0.5 0.5], 'EdgeColor', 'k');
    hold on
    x_vals = linspace(min(impact_x), max(impact_x), 1000);
    plot(x_vals, pdf(pd_imp_x, x_vals), 'k', 'LineWidth', 2);
    
    title('Impact X Position');
    xlabel('Impact X Position (m)');
    ylabel('Probability Density');
    grid on

    % Save figure as SVG 
    saveas(fig_imp_x, fullfile(output_folder_svg, 'impact_x_position.svg'));

    % Save figure as MATLAB fig
    savefig(fig_imp_x, fullfile(output_folder_fig, 'impact_x_position.fig'));

    % Stop automatic printing of images
    close(fig_imp_x);
else
    warning('Not enough data to fit distribution for Impact X Position.');
end


%% === IMPACT Y POSITION ===
impact_y = dispersion_results.impact_y;

if numel(impact_y) >= 2 % Checking if there is data for impact y position
    pd_imp_y = fitdist(impact_y(:), 'Normal');
    mu_imp_y  = pd_imp_y.mu;
    sigma_imp_y = pd_imp_y.sigma;

    fprintf('Impact Y Position - Mean: %.3f m\n', mu_imp_y);
    fprintf('Impact Y Position - Std:  %.3f m\n', sigma_imp_y);

    % Create the figure
    n_bins = floor(sqrt(numel(impact_y)));
    fig_imp_y = figure('Visible','off');
    histogram(impact_y, 'Normalization', 'pdf', ...
        'NumBins', n_bins, ...
        'FaceColor', [0.56 0.93 0.56], 'EdgeColor', 'k');
    hold on
    x_vals = linspace(min(impact_y), max(impact_y), 1000);
    plot(x_vals, pdf(pd_imp_y, x_vals), 'k', 'LineWidth', 2);
    
    title('Impact Y Position');
    xlabel('Impact Y Position (m)');
    ylabel('Probability Density');
    grid on

    % Save figure as SVG 
    saveas(fig_imp_y, fullfile(output_folder_svg, 'impact_y_position.svg'));

    % Save figure as MATLAB fig
    savefig(fig_imp_y, fullfile(output_folder_fig, 'impact_y_position.fig'));

    % Stop automatic printing of images
    close(fig_imp_y);
else
    warning('Not enough data to fit distribution for Impact Y Position.');
end


%% === IMPACT VELOCITY ===
impact_velocity = dispersion_results.impact_velocity;

if numel(impact_velocity) >= 2 % Checking if there is data for impact velocity
    pd_imp_v = fitdist(impact_velocity(:), 'Normal');
    mu_v  = pd_imp_v.mu;
    sigma_v = pd_imp_v.sigma;

    fprintf('Impact Velocity - Mean: %.3f m/s\n', mu_v);
    fprintf('Impact Velocity - Std:  %.3f m/s\n', sigma_v);

    % Create the figure
    n_bins = floor(sqrt(numel(impact_velocity)));
    fig_imp_v = figure('Visible','off');
    histogram(impact_velocity, 'Normalization', 'pdf', ...
        'NumBins', n_bins, ...
        'FaceColor', [0.53 0.81 0.92], 'EdgeColor', 'k');
    hold on
    x_vals = linspace(min(impact_velocity), max(impact_velocity), 1000);
    plot(x_vals, pdf(pd_imp_v, x_vals), 'k', 'LineWidth', 2);
    
    title('Impact Velocity');
    xlabel('Velocity (m/s)');
    ylabel('Probability Density');
    grid on

    % Save figure as SVG 
    saveas(fig_imp_v, fullfile(output_folder_svg, 'impact_velocity.svg'));

    % Save figure as MATLAB fig
    savefig(fig_imp_v, fullfile(output_folder_fig, 'impact_velocity.fig'));
    
    % Stop automatic printing of images
    close(fig_imp_v);
else
    warning('Not enough data to fit distribution for Impact Velocity.');
end


%% === STATIC MARGINS ===
initial_margin = dispersion_results.initial_static_margin;
out_of_rail_margin = dispersion_results.out_of_rail_static_margin;
final_margin = dispersion_results.final_static_margin;

% Fit normal distributions (std with N normalization, like norm.fit)
mu_initial = mean(initial_margin);
std_initial = std(initial_margin, 1);
mu_out = mean(out_of_rail_margin);
std_out = std(out_of_rail_margin, 1);
mu_final = mean(final_margin);
std_final = std(final_margin, 1);

fprintf('Initial Static Margin -             Mean Value: %.3f c\n', mu_initial);
fprintf('Initial Static Margin -     Standard Deviation: %.3f c\n', std_initial);

fprintf('Out of Rail Static Margin -         Mean Value: %.3f c\n', mu_out);
fprintf('Out of Rail Static Margin - Standard Deviation: %.3f c\n', std_out);

fprintf('Final Static Margin -               Mean Value: %.3f c\n', mu_final);
fprintf('Final Static Margin -       Standard Deviation: %.3f c\n', std_final);

% Number of bins: square-root rule (int(N**0.5) in Python)
N = numel(initial_margin);
bins = floor(sqrt(N));

% Create the figure
fig_static = figure('Visible','off'); hold on;

histogram(initial_margin, linspace(min(initial_margin), max(initial_margin), bins+1), ...
    'Normalization','pdf', 'FaceColor',[0.529 0.808 0.922], 'EdgeColor','k', ...
    'FaceAlpha',0.4, 'EdgeAlpha',0.4, 'LineWidth',1, 'DisplayName','Initial');
histogram(out_of_rail_margin, linspace(min(out_of_rail_margin), max(out_of_rail_margin), bins+1), ...
    'Normalization','pdf', 'FaceColor',[1 0.647 0], 'EdgeColor','k', ...
    'FaceAlpha',0.4, 'EdgeAlpha',0.4, 'LineWidth',1, 'DisplayName','Out of Rail');
histogram(final_margin, linspace(min(final_margin), max(final_margin), bins+1), ...
    'Normalization','pdf', 'FaceColor',[0.565 0.933 0.565], 'EdgeColor','k', ...
    'FaceAlpha',0.4, 'EdgeAlpha',0.4, 'LineWidth',1, 'DisplayName','Final');

x_initial = linspace(min(initial_margin), max(initial_margin), 1000);
x_out = linspace(min(out_of_rail_margin), max(out_of_rail_margin), 1000);
x_final = linspace(min(final_margin), max(final_margin), 1000);

% PDF curves (HandleVisibility off: not in the legend, like Python)
plot(x_initial, normpdf(x_initial, mu_initial, std_initial), 'Color',[0 0 1], 'LineWidth',2, 'HandleVisibility','off');
plot(x_out, normpdf(x_out, mu_out, std_out), 'Color',[1 0.549 0], 'LineWidth',2, 'HandleVisibility','off');   % darkorange
plot(x_final, normpdf(x_final, mu_final, std_final), 'Color',[0 0.5 0], 'LineWidth',2, 'HandleVisibility','off');  % matplotlib 'g' is dark green

title('Static Margin Distribution');
xlabel('Static Margin (c)');
ylabel('Probability Density');
legend('show');
grid on;

% Save figure as SVG and fig (MATLAB equivalent of Pickle)
saveas(fig_static, fullfile(output_folder_svg, 'static_margin_distribution.svg'));
savefig(fig_static, fullfile(output_folder_fig, 'static_margin_distribution.fig'));

close(fig_static); % Stop automatic printing of images


%% === MAXIMUM VELOCITY ===
max_velocity = dispersion_results.max_velocity;
mu_max_velocity = mean(max_velocity);
std_max_velocity = std(max_velocity, 1);

fprintf('Maximum Velocity -         Mean Value: %.3f m/s\n', mu_max_velocity);
fprintf('Maximum Velocity - Standard Deviation: %.3f m/s\n', std_max_velocity);

% Number of bins: square-root rule (int(N**0.5) in Python)
N = numel(max_velocity);
bins = floor(sqrt(N));

% Create the figure
fig_max_velocity = figure('Visible','off'); hold on;
histogram(max_velocity, linspace(min(max_velocity), max(max_velocity), bins+1), ...
    'Normalization','pdf', 'FaceColor',[0.678 0.847 0.902], 'EdgeColor','k', ...
    'FaceAlpha',0.6, 'EdgeAlpha',0.6, 'LineWidth',1);
x_max_velocity = linspace(min(max_velocity), max(max_velocity), 1000);
plot(x_max_velocity, normpdf(x_max_velocity, mu_max_velocity, std_max_velocity), 'k', 'LineWidth',2);
title('Maximum Velocity');
xlabel('Velocity (m/s)');
ylabel('Probability Density');
grid on;

% Save figure as SVG and fig (MATLAB equivalent of Pickle)
saveas(fig_max_velocity, fullfile(output_folder_svg, 'maximum_velocity_plot.svg'));
savefig(fig_max_velocity, fullfile(output_folder_fig, 'maximum_velocity_plot.fig'));
close(fig_max_velocity); % Stop automatic printing of images


%% === MAXIMUM ACCELERATION ===
max_acc = dispersion_results.max_acceleration;
mu_max_acc = mean(max_acc);
std_max_acc = std(max_acc, 1);

fprintf('Maximum Acceleration -         Mean Value: %.3f m/s²\n', mu_max_acc);
fprintf('Maximum Acceleration - Standard Deviation: %.3f m/s²\n', std_max_acc);

% Number of bins: square-root rule (int(N**0.5) in Python)
N = numel(max_acc);
bins = floor(sqrt(N));

% Create the figure
fig_max_acc = figure('Visible','off'); hold on;
histogram(max_acc, linspace(min(max_acc), max(max_acc), bins+1), ...
    'Normalization','pdf', 'FaceColor',[0.941 0.502 0.502], 'EdgeColor','k', ...
    'FaceAlpha',0.6, 'EdgeAlpha',0.6, 'LineWidth',1);
x_max_acc = linspace(min(max_acc), max(max_acc), 1000);
plot(x_max_acc, normpdf(x_max_acc, mu_max_acc, std_max_acc), 'k', 'LineWidth',2);
title('Maximum Acceleration');
xlabel('Acceleration (m/s²)');
ylabel('Probability Density');
grid on;

% Save figure as SVG and fig (MATLAB equivalent of Pickle)
saveas(fig_max_acc, fullfile(output_folder_svg, 'maximum_acceleration_plot.svg'));
savefig(fig_max_acc, fullfile(output_folder_fig, 'maximum_acceleration_plot.fig'));
close(fig_max_acc); % Stop automatic printing of images


%% === NUMBER OF PARACHUTE EVENTS ===
num_events = dispersion_results.number_of_events;

% Create the figure
fig_parachute = figure('Visible','off'); hold on;

% 10 equal-width bins over [min, max], like the default of ax.hist
% (numpy widens the range by 0.5 on each side if all values are equal)
lo = min(num_events);
hi = max(num_events);
if lo == hi
    lo = lo - 0.5;
    hi = hi + 0.5;
end
histogram(num_events, linspace(lo, hi, 11), ...
    'FaceColor',[1 0.647 0], 'EdgeColor','k', ...
    'FaceAlpha',1, 'EdgeAlpha',1, 'LineWidth',1);
title('Parachute Events');
xlabel('Number of Parachute Events');
ylabel('Number of Occurrences');
grid on;

% Save figure as SVG and fig (MATLAB equivalent of Pickle)
saveas(fig_parachute, fullfile(output_folder_svg, 'parachute_events_plot.svg'));
savefig(fig_parachute, fullfile(output_folder_fig, 'parachute_events_plot.fig'));
close(fig_parachute); % Stop automatic printing of images


%% === DROGUE PARACHUTE TRIGGER TIME ===
drogue_trigger = dispersion_results.drogue_triggerTime;
mu_drogue_trigger = mean(drogue_trigger);
std_drogue_trigger = std(drogue_trigger, 1);

fprintf('Drogue Parachute Trigger Time -         Mean Value: %.3f s\n', mu_drogue_trigger);
fprintf('Drogue Parachute Trigger Time - Standard Deviation: %.3f s\n', std_drogue_trigger);

% Number of bins: square-root rule (int(N**0.5) in Python)
N = numel(drogue_trigger);
bins = floor(sqrt(N));

% Create the figure
fig_drogue_trigger = figure('Visible','off'); hold on;
histogram(drogue_trigger, linspace(min(drogue_trigger), max(drogue_trigger), bins+1), ...
    'Normalization','pdf', 'FaceColor',[1 0.843 0], 'EdgeColor','k', ...
    'FaceAlpha',0.6, 'EdgeAlpha',0.6, 'LineWidth',1);
x_drogue_trigger = linspace(min(drogue_trigger), max(drogue_trigger), 1000);
plot(x_drogue_trigger, normpdf(x_drogue_trigger, mu_drogue_trigger, std_drogue_trigger), 'k', 'LineWidth',2);
title('Drogue Parachute Trigger Time');
xlabel('Time (s)');
ylabel('Probability Density');
grid on;

% Save figure as SVG and fig (MATLAB equivalent of Pickle)
saveas(fig_drogue_trigger, fullfile(output_folder_svg, 'drogue_trigger_time_plot.svg'));
savefig(fig_drogue_trigger, fullfile(output_folder_fig, 'drogue_trigger_time_plot.fig'));
close(fig_drogue_trigger); % Stop automatic printing of images


%% === DROGUE PARACHUTE FULLY INFLATED TIME ===
drogue_inflated_time = dispersion_results.drogue_inflated_time;
mu_drogue_time = mean(drogue_inflated_time);
std_drogue_time = std(drogue_inflated_time, 1);

fprintf('Drogue Parachute Fully Inflated Time -         Mean Value: %.3f s\n', mu_drogue_time);
fprintf('Drogue Parachute Fully Inflated Time - Standard Deviation: %.3f s\n', std_drogue_time);

% Number of bins: square-root rule (int(N**0.5) in Python)
N = numel(drogue_inflated_time);
bins = floor(sqrt(N));

% Create the figure
fig_drogue_inflated = figure('Visible','off'); hold on;
histogram(drogue_inflated_time, linspace(min(drogue_inflated_time), max(drogue_inflated_time), bins+1), ...
    'Normalization','pdf', 'FaceColor',[0.867 0.627 0.867], 'EdgeColor','k', ...
    'FaceAlpha',0.6, 'EdgeAlpha',0.6, 'LineWidth',1);
x_drogue_inflated_time = linspace(min(drogue_inflated_time), max(drogue_inflated_time), 1000);
plot(x_drogue_inflated_time, normpdf(x_drogue_inflated_time, mu_drogue_time, std_drogue_time), 'k', 'LineWidth',2);
title('Drogue Fully Inflated Time');
xlabel('Time (s)');
ylabel('Probability Density');
grid on;

% Save figure as SVG and fig (MATLAB equivalent of Pickle)
saveas(fig_drogue_inflated, fullfile(output_folder_svg, 'drogue_inflated_time_plot.svg'));
savefig(fig_drogue_inflated, fullfile(output_folder_fig, 'drogue_inflated_time_plot.fig'));
close(fig_drogue_inflated); % Stop automatic printing of images


%% === DROGUE PARACHUTE FULLY INFLATED VELOCITY ===
drogue_velocity = dispersion_results.drogue_inflated_velocity;
mu_drogue_vel = mean(drogue_velocity);
std_drogue_vel = std(drogue_velocity, 1);

fprintf('Drogue Parachute Fully Inflated Velocity -         Mean Value: %.3f m/s\n', mu_drogue_vel);
fprintf('Drogue Parachute Fully Inflated Velocity - Standard Deviation: %.3f m/s\n', std_drogue_vel);

% Number of bins: square-root rule (int(N**0.5) in Python)
N = numel(drogue_velocity);
bins = floor(sqrt(N));

% Create the figure
fig_drogue_velocity = figure('Visible','off'); hold on;
histogram(drogue_velocity, linspace(min(drogue_velocity), max(drogue_velocity), bins+1), ...
    'Normalization','pdf', 'FaceColor',[0.125 0.698 0.667], 'EdgeColor','k', ...
    'FaceAlpha',0.6, 'EdgeAlpha',0.6, 'LineWidth',1);
x_drogue_velocity = linspace(min(drogue_velocity), max(drogue_velocity), 1000);
plot(x_drogue_velocity, normpdf(x_drogue_velocity, mu_drogue_vel, std_drogue_vel), 'k', 'LineWidth',2);
title('Drogue Inflated Velocity');
xlabel('Velocity (m/s)');
ylabel('Probability Density');
grid on;

% Save figure as SVG and fig (MATLAB equivalent of Pickle)
saveas(fig_drogue_velocity, fullfile(output_folder_svg, 'drogue_inflated_velocity_plot.svg'));
savefig(fig_drogue_velocity, fullfile(output_folder_fig, 'drogue_inflated_velocity_plot.fig'));
close(fig_drogue_velocity); % Stop automatic printing of images


%% === MAXIMUM AERODYNAMIC DRAG ===
drag = dispersion_results.max_aerodynamic_drag;
mu_drag = mean(drag);
std_drag = std(drag, 1);

fprintf('Maximum Aerodynamic Drag -         Mean Value: %.3f N\n', mu_drag);
fprintf('Maximum Aerodynamic Drag - Standard Deviation: %.3f N\n', std_drag);

% Number of bins: square-root rule (int(N**0.5) in Python)
N = numel(drag);
bins = floor(sqrt(N));

% Create the figure
fig_drag = figure('Visible','off'); hold on;
histogram(drag, linspace(min(drag), max(drag), bins+1), ...
    'Normalization','pdf', 'FaceColor',[0.392 0.584 0.929], 'EdgeColor','k', ...
    'FaceAlpha',0.6, 'EdgeAlpha',0.6, 'LineWidth',1);
x_drag = linspace(min(drag), max(drag), 1000);
plot(x_drag, normpdf(x_drag, mu_drag, std_drag), 'k', 'LineWidth',2);
title('Maximum Aerodynamic Drag');
xlabel('Drag Force (N)');
ylabel('Probability Density');
grid on;

% Save figure as SVG and fig (MATLAB equivalent of Pickle)
saveas(fig_drag, fullfile(output_folder_svg, 'max_aero_drag_plot.svg'));
savefig(fig_drag, fullfile(output_folder_fig, 'max_aero_drag_plot.fig'));
close(fig_drag); % Stop automatic printing of images


%% === MAXIMUM AERODYNAMIC LIFT ===
lift = dispersion_results.max_aerodynamic_lift;
mu_lift = mean(lift);
std_lift = std(lift, 1);

fprintf('Maximum Aerodynamic Lift -         Mean Value: %.3f N\n', mu_lift);
fprintf('Maximum Aerodynamic Lift - Standard Deviation: %.3f N\n', std_lift);

% Number of bins: square-root rule (int(N**0.5) in Python)
N = numel(lift);
bins = floor(sqrt(N));

% Create the figure
fig_lift = figure('Visible','off'); hold on;
histogram(lift, linspace(min(lift), max(lift), bins+1), ...
    'Normalization','pdf', 'FaceColor',[0.400 0.804 0.667], 'EdgeColor','k', ...
    'FaceAlpha',0.6, 'EdgeAlpha',0.6, 'LineWidth',1);
x_lift = linspace(min(lift), max(lift), 1000);
plot(x_lift, normpdf(x_lift, mu_lift, std_lift), 'k', 'LineWidth',2);
title('Maximum Aerodynamic Lift');
xlabel('Lift Force (N)');
ylabel('Probability Density');
grid on;

% Save figure as SVG and fig (MATLAB equivalent of Pickle)
saveas(fig_lift, fullfile(output_folder_svg, 'max_aero_lift_plot.svg'));
savefig(fig_lift, fullfile(output_folder_fig, 'max_aero_lift_plot.fig'));
close(fig_lift); % Stop automatic printing of images


%% === MAXIMUM SPIN MOMENT ===
spin_moment = dispersion_results.max_aerodynamic_spin_moment;
mu_spin = mean(spin_moment);
std_spin = std(spin_moment, 1);

fprintf('Maximum Aerodynamic Spin Moment -         Mean Value: %.3f N*m\n', mu_spin);
fprintf('Maximum Aerodynamic Spin Moment - Standard Deviation: %.3f N*m\n', std_spin);

% Number of bins: square-root rule (int(N**0.5) in Python)
N = numel(spin_moment);
bins = floor(sqrt(N));

% Create the figure
fig_spin = figure('Visible','off'); hold on;

% If all values are equal (e.g. spin moment is exactly 0 with zero cant angle)
% numpy widens the range by 0.5 on each side; without this linspace gives
% identical edges and histogram throws an error
lo = min(spin_moment);
hi = max(spin_moment);
if lo == hi
    lo = lo - 0.5;
    hi = hi + 0.5;
end
histogram(spin_moment, linspace(lo, hi, bins+1), ...
    'Normalization','pdf', 'FaceColor',[0.467 0.533 0.600], 'EdgeColor','k', ...
    'FaceAlpha',0.6, 'EdgeAlpha',0.6, 'LineWidth',1);
x_spin = linspace(min(spin_moment), max(spin_moment), 1000);
plot(x_spin, normpdf(x_spin, mu_spin, std_spin), 'k', 'LineWidth',2);
title('Maximum Aerodynamic Spin Moment');
xlabel('Spin Moment (N*m)');
ylabel('Probability Density');
grid on;

% Save figure as SVG and fig (MATLAB equivalent of Pickle)
saveas(fig_spin, fullfile(output_folder_svg, 'max_spin_moment_plot.svg'));
savefig(fig_spin, fullfile(output_folder_fig, 'max_spin_moment_plot.fig'));
close(fig_spin); % Stop automatic printing of images


%% === MAXIMUM BENDING MOMENT ===
bending_moment = dispersion_results.max_aerodynamic_bending_moment;
mu_bend = mean(bending_moment);
std_bend = std(bending_moment, 1);

fprintf('Maximum Aerodynamic Bending Moment -         Mean Value: %.3f N*m\n', mu_bend);
fprintf('Maximum Aerodynamic Bending Moment - Standard Deviation: %.3f N*m\n', std_bend);

% Number of bins: square-root rule (int(N**0.5) in Python)
N = numel(bending_moment);
bins = floor(sqrt(N));

% Create the figure
fig_bend = figure('Visible','off'); hold on;
histogram(bending_moment, linspace(min(bending_moment), max(bending_moment), bins+1), ...
    'Normalization','pdf', 'FaceColor',[0.275 0.510 0.706], 'EdgeColor','k', ...
    'FaceAlpha',0.6, 'EdgeAlpha',0.6, 'LineWidth',1);
x_bend = linspace(min(bending_moment), max(bending_moment), 1000);
plot(x_bend, normpdf(x_bend, mu_bend, std_bend), 'k', 'LineWidth',2);
title('Maximum Aerodynamic Bending Moment');
xlabel('Bending Moment (N*m)');
ylabel('Probability Density');
grid on;

% Save figure as SVG and fig (MATLAB equivalent of Pickle)
saveas(fig_bend, fullfile(output_folder_svg, 'max_bending_moment_plot.svg'));
savefig(fig_bend, fullfile(output_folder_fig, 'max_bending_moment_plot.fig'));
close(fig_bend); % Stop automatic printing of images


%% Import background map
img = imread('santamargarida_launchpoint.jpg');

%% Retrieve dispersion data for apogee and impact XY position
apogee_x = dispersion_results.apogee_x;
apogee_y = dispersion_results.apogee_y;
impact_x = dispersion_results.impact_x;
impact_y = dispersion_results.impact_y;

% You can translate the basemap by changing dx and dy (in meters)
dx = 0;
dy = 0;

% Create plot figure
figure('Color','w','Renderer','painters','Units','pixels','Position',[100 100 800 600]);
hold on;

% Add background image to plot
imagesc([-1500-dx 1500-dx], [-1500-dy 1500-dy], flipud(img));
set(gca,'YDir','normal');

theta = linspace(0, 2*pi, 100);

% Calculate error ellipses for impact
impactCov = cov([impact_x(:), impact_y(:)]);
[impactVals, impactVecs] = eigsorted(impactCov);
impactTheta = atan2d(impactVecs(2,1), impactVecs(1,1));
impactW = 2 * sqrt(impactVals(1));
impactH = 2 * sqrt(impactVals(2));
cx = mean(impact_x);
cy = mean(impact_y);
R_impact = [cosd(impactTheta) -sind(impactTheta);
            sind(impactTheta)  cosd(impactTheta)];

% Draw error ellipses for impact
for j = 1:3
    xy = R_impact * [(impactW*j)/2 * cos(theta); (impactH*j)/2 * sin(theta)];
    patch(xy(1,:)+cx, xy(2,:)+cy, [0 0 1], 'FaceAlpha',0.2, ...
          'EdgeColor','k', 'LineWidth',1, 'HandleVisibility','off');
end

% Calculate error ellipses for apogee
apogeeCov = cov([apogee_x(:), apogee_y(:)]);
[apogeeVals, apogeeVecs] = eigsorted(apogeeCov);
apogeeTheta = atan2d(apogeeVecs(2,1), apogeeVecs(1,1));
apogeeW = 2 * sqrt(apogeeVals(1));
apogeeH = 2 * sqrt(apogeeVals(2));
cx = mean(apogee_x);
cy = mean(apogee_y);
R_apogee = [cosd(apogeeTheta) -sind(apogeeTheta);
            sind(apogeeTheta)  cosd(apogeeTheta)];

% Draw error ellipses for apogee
for j = 1:3
    xy = R_apogee * [(apogeeW*j)/2 * cos(theta); (apogeeH*j)/2 * sin(theta)];
    patch(xy(1,:)+cx, xy(2,:)+cy, [0 1 0], 'FaceAlpha',0.2, ...
          'EdgeColor','k', 'LineWidth',1, 'HandleVisibility','off');
end

% Draw launch point, apogee points, impact points
scatter(0, 0, 30, 'k', '*', 'DisplayName','Launch Point');
scatter(apogee_x, apogee_y, 5, [1 0.647 0], '^', 'filled', 'DisplayName','Simulated Apogee');
scatter(impact_x, impact_y, 5, [1 1 0], 'v', 'filled', 'DisplayName','Simulated Landing Point');

% Central axes
plot([-1500 1500], [0 0], 'k', 'LineWidth',0.5, 'HandleVisibility','off');
plot([0 0], [-1500 1500], 'k', 'LineWidth',0.5, 'HandleVisibility','off');

legend('Location','best');
title('1\sigma, 2\sigma and 3\sigma Dispersion Ellipses: Apogee and Landing Points', ...
      'Interpreter','tex');
xlabel('East (m)');
ylabel('North (m)');

axis equal;
xlim([-1500 1500]);
ylim([-1500 1500]);

% Save plot and show result
saveas(gcf, [filename '.pdf']);
saveas(gcf, [filename '.svg']);

%% Rocket and motor visualization
Atlas.draw();
Atlas.info();
Pro75_8187M1545_P.draw();
Pro75_8187M1545_P.info();

%% NOTE: Sensitivity analysis is missing as in the montecarlo simulation I based this off of it wasn't working ¯\_(ツ)_/¯