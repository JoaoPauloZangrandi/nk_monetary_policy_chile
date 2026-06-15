function export_history(scenario_id)
  % Export the Kalman-smoothed structural shocks and the historical shock
  % decomposition (oo_.shock_decomposition) to CSV for plotting in Python.
  global M_ oo_ options_

  repo_root = getenv('NK_REPO_ROOT');
  if isempty(repo_root)
    script_dir = fileparts(mfilename('fullpath'));
    repo_root = fileparts(script_dir);
  end
  out_dir = fullfile(repo_root, 'outputs', 'dynare', 'history');
  if ~exist(out_dir, 'dir'); mkdir(out_dir); end

  % --- Smoothed structural shocks ---------------------------------------
  try
    sh = oo_.SmoothedShocks;
    names = fieldnames(sh);
    T = numel(sh.(names{1}));
    fid = fopen(fullfile(out_dir, 'smoothed_shocks.csv'), 'w');
    fprintf(fid, 'period');
    for k = 1:numel(names); fprintf(fid, ',%s', names{k}); end
    fprintf(fid, '\n');
    for t = 1:T
      fprintf(fid, '%d', t);
      for k = 1:numel(names); fprintf(fid, ',%.10g', sh.(names{k})(t)); end
      fprintf(fid, '\n');
    end
    fclose(fid);
    fprintf('export_history: wrote smoothed_shocks (T=%d).\n', T);
  catch err
    fprintf(2, 'export_history: smoothed shocks failed: %s\n', err.message);
  end

  % --- Historical shock decomposition -----------------------------------
  try
    sd = oo_.shock_decomposition;            % [endo, exo+2, nobs]
    [nendo, ncomp, nobs] = size(sd);
    endo = local_names(M_.endo_names, nendo);
    exo  = local_names(M_.exo_names, M_.exo_nbr);
    % Dynare layout: [shock_1..shock_n, initial condition, smoothed value].
    % The shocks plus the initial condition sum to the smoothed value (last col).
    comp = exo;
    comp{end+1} = 'initial';
    comp{end+1} = 'smoothed';
    while numel(comp) < ncomp; comp{end+1} = sprintf('c%d', numel(comp)+1); end

    fid = fopen(fullfile(out_dir, 'shock_decomp.csv'), 'w');
    fprintf(fid, 'variable,period');
    for c = 1:ncomp; fprintf(fid, ',%s', comp{c}); end
    fprintf(fid, '\n');
    for v = 1:nendo
      for t = 1:nobs
        fprintf(fid, '%s,%d', endo{v}, t);
        for c = 1:ncomp
          fprintf(fid, ',%.10g', sd(v, c, t));
        end
        fprintf(fid, '\n');
      end
    end
    fclose(fid);
    fprintf('export_history: wrote shock_decomp (%d vars x %d periods x %d comps).\n', ...
            nendo, nobs, ncomp);
  catch err
    fprintf(2, 'export_history: shock decomposition failed: %s\n', err.message);
  end
end

function names = local_names(raw, n)
  % Return a cell array of variable names from a char matrix or cell array.
  if iscell(raw)
    names = raw;
  else
    names = cell(size(raw, 1), 1);
    for r = 1:size(raw, 1)
      names{r} = strtrim(raw(r, :));
    end
  end
  while numel(names) < n; names{end+1} = sprintf('v%d', numel(names)+1); end
end
