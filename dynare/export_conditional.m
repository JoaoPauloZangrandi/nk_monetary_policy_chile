function export_conditional(scenario_id)
  % Export a conditional_forecast result set to CSV. The exact nesting of
  % oo_.conditional_forecast varies across Dynare versions, so this helper logs
  % the available fields and then extracts the conditional/unconditional means
  % and confidence bands defensively.
  global M_ oo_ options_

  repo_root = getenv('NK_REPO_ROOT');
  if isempty(repo_root)
    script_dir = fileparts(mfilename('fullpath'));
    repo_root = fileparts(script_dir);
  end
  out_dir = fullfile(repo_root, 'outputs', 'dynare', 'forecast');
  if ~exist(out_dir, 'dir'); mkdir(out_dir); end

  variables = {'x', 'pi', 'i'};

  if ~isfield(oo_, 'conditional_forecast')
    fprintf(2, 'export_conditional(%s): oo_.conditional_forecast missing.\n', scenario_id);
    return;
  end
  cf = oo_.conditional_forecast;

  % Debug: record the structure once per scenario.
  try
    dbg = fopen(fullfile(out_dir, ['structure_' scenario_id '.txt']), 'w');
    fprintf(dbg, 'top: %s\n', strjoin(fieldnames(cf), ', '));
    if isfield(cf, 'cond');   fprintf(dbg, 'cond: %s\n',   strjoin(fieldnames(cf.cond), ', ')); end
    if isfield(cf, 'uncond'); fprintf(dbg, 'uncond: %s\n', strjoin(fieldnames(cf.uncond), ', ')); end
    if isfield(cf, 'cond') && isfield(cf.cond, 'Mean')
      fprintf(dbg, 'cond.Mean: %s\n', strjoin(fieldnames(cf.cond.Mean), ', '));
    end
    fclose(dbg);
  catch
  end

  fid = fopen(fullfile(out_dir, ['conditional_' scenario_id '.csv']), 'w');
  fprintf(fid, 'horizon,variable,cond_mean,cond_inf,cond_sup,uncond_mean\n');
  for v = 1:numel(variables)
    name = variables{v};
    [cm, ci_lo, ci_hi] = local_branch(cf, 'cond', name);
    [um, ~, ~]         = local_branch(cf, 'uncond', name);
    H = max([numel(cm), numel(um), 1]);
    for t = 1:H
      fprintf(fid, '%d,%s,%.12g,%.12g,%.12g,%.12g\n', t, name, ...
              local_at(cm, t), local_at(ci_lo, t), local_at(ci_hi, t), ...
              local_at(um, t));
    end
  end
  fclose(fid);
  fprintf('export_conditional: wrote scenario %s.\n', scenario_id);
end

function [m, lo, hi] = local_branch(cf, branch, name)
  m = []; lo = []; hi = [];
  if ~isfield(cf, branch); return; end
  b = cf.(branch);
  if isfield(b, 'Mean') && isfield(b.Mean, name)
    m = b.Mean.(name)(:);
  end
  if isfield(b, 'ci') && isfield(b.ci, name)
    band = b.ci.(name);
    if size(band, 1) == 2
      lo = band(1, :)'; hi = band(2, :)';
    elseif size(band, 2) == 2
      lo = band(:, 1); hi = band(:, 2);
    end
  end
end

function val = local_at(v, t)
  if numel(v) >= t; val = v(t); else; val = NaN; end
end
