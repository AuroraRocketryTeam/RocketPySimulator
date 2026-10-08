function export_flight_error(settings_list)
    global dispersion_error_file
        % Converts the struct in text (equivalent to str() in python)
        str_to_write = evalc('disp(settings_list)');

        % Writes the error in the log file
        fprintf(dispersion_error_file, "%s\n", str_to_write); 
end