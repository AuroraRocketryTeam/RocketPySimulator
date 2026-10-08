function v = toNumericColumn(x)

    % Numeric case
    if isnumeric(x)
        v = x(:);
        v = v(~isnan(v));
        return
    end

    % Cell array case
    if iscell(x)
        mask = cellfun(@(y) isnumeric(y) && isscalar(y) && ~isnan(y), x);
        v = cell2mat(x(mask));
        v = v(:);
        return
    end

    % Case anything else (simply removes it)
    v = [];
end