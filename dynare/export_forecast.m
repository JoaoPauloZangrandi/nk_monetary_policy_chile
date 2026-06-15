function export_forecast(scenario_id)
  % Export the unconditional forecast (Mean + HPD bands) and the smoothed
  % historical series produced by estimation(..., forecast=N, smoother).
  global M_ oo_ options_

  repo_root = getenv('NK_REPO_ROOT');
  if isempty(repo_root)
    script_dir = fileparts(mfilename('fullpath'));
    repo_root = fileparts(script_dir);
  end
  out_dir = fullfile(repo_root, 'outputs', 'dynare', scenario_id);
  if ~exist(out_dir, 'dir'); mkdir(out_dir); end

  variables = {'x', 'pi', 'i'};

  % --- Unconditional forecast: Mean and HPD bands ------------------------
  try
    fc = oo_.forecast;
    H = numel(local_pick(fc.Mean, 'pi'));
    fid = fopen(fullfile(out_dir, 'forecast_unconditional.csv'), 'w');
    fprintf(fid, 'horizon,variable,mean,hpd_inf,hpd_sup\n');
    for v = 1:numel(variables)
      name = variables{v};
      meanv = local_pick(fc.Mean, name);
      infv  = local_field(fc, 'HPDinf', name, H);
      supv  = local_field(fc, 'HPDsup', name, H);
      for t = 1:H
        fprintf(fid, '%d,%s,%.12g,%.12g,%.12g\n', t, name, ...
                meanv(t), infv(t), supv(t));
      end
    end
    fclose(fid);
    fprintf('export_forecast: wrote unconditional forecast (H=%d).\n', H);
  catch err
    fprintf(2, 'export_forecast: unconditional export failed: %s\n', err.message);
  end

  % --- Smoothed historical series ----------------------------------------
  try
    sv = oo_.SmoothedVariables;
    xv = local_pick(sv, 'x'); pv = local_pick(sv, 'pi'); iv = local_pick(sv, 'i');
    T = numel(pv);
    fid = fopen(fullfile(out_dir, 'forecast_smoothed.csv'), 'w');
    fprintf(fid, 'period,x,pi,i\n');
    for t = 1:T
      fprintf(fid, '%d,%.12g,%.12g,%.12g\n', t, xv(t), pv(t), iv(t));
    end
    fclose(fid);
    fprintf('export_forecast: wrote smoothed series (T=%d).\n', T);
  catch err
    fprintf(2, 'export_forecast: smoothed export failed: %s\n', err.message);
  end
end

function v = local_pick(s, name)
  % Return s.(name) as a column vector, unwrapping a .Mean sub-struct if present.
  f = s.(name);
  if isstruct(f)
    if isfield(f, 'Mean'); f = f.Mean; else; fn = fieldnames(f); f = f.(fn{1}); end
  end
  v = f(:);
end

function v = local_field(s, group, name, H)
  % Safe accessor for an optional HPD group; returns NaNs if missing.
  v = nan(H, 1);
  if isfield(s, group) && isfield(s.(group), name)
    w = local_pick(s.(group), name);
    n = min(H, numel(w));
    v(1:n) = w(1:n);
  end
end
