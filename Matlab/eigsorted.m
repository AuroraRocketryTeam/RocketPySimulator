function [vals_sorted, vecs_sorted] = eigsorted(cov)
    % Define function to calculate eigen values
    [vecs, vals_matrix] = eig(cov);
    vals = diag(vals_matrix);

    [vals_sorted, order] = sort(vals, 'descend');

    vecs_sorted = vecs(:, order);
end