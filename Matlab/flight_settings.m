% Yield a flight setting
function settings_list = flight_settings(params, total_number)
    settings_list = cell(total_number,1);
    keys = fieldnames(params);
    i = 1;

    while i <= total_number
        % Generate a flight setting

        flight_setting = struct();

        for k = 1:numel(keys)
            key = keys{k};
            val = params.(key);

            if isnumeric(val) && numel(val) == 2 % Matlab is unable to define the type tuple, so this one detects if it's a cell and composted of 2 elements
                flight_setting.(key) = normrnd(val(1), val(2));
            else
                idx = randi(numel(val));
                flight_setting.(key) = val(idx);
            end
        end

        % Skip if certain values are negative, which happens due to the normal curve but isnt realistic
        if (isfield(flight_setting, 'lag_rec') && flight_setting.lag_rec < 0) || ...
           (isfield(flight_setting, 'lag_se') && flight_setting.lag_se < 0)
            continue
        end
        settings_list{i} = flight_setting;

        % Update counter
        i = i + 1;
    end
end