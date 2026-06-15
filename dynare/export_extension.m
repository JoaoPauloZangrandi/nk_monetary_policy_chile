function export_extension(scenario_id)
  % Generic CSV exporter for macro extensions with arbitrary variables/shocks.
  global M_ oo_ options_

  repo_root = getenv('NK_REPO_ROOT');
  if isempty(repo_root); repo_root = pwd(); end
  out_dir = fullfile(repo_root, 'outputs', 'dynare', scenario_id);
  if ~exist(out_dir, 'dir'); mkdir(out_dir); end

  variables = local_names(M_.endo_names);
  shocks = local_names(M_.exo_names);
  horizon = options_.irf;

  fid = fopen(fullfile(out_dir, 'irfs.csv'), 'w');
  fprintf(fid, 'horizon');
  for v = 1:numel(variables)
    for s = 1:numel(shocks)
      fprintf(fid, ',%s_%s', variables{v}, shocks{s});
    end
  end
  fprintf(fid, '\n');
  for t = 1:horizon
    fprintf(fid, '%d', t-1);
    for v = 1:numel(variables)
      for s = 1:numel(shocks)
        field_name = [variables{v} '_' shocks{s}];
        value = 0;
        if isfield(oo_.irfs, field_name)
          series = oo_.irfs.(field_name);
          if numel(series) >= t; value = series(t); end
        end
        fprintf(fid, ',%.12g', value);
      end
    end
    fprintf(fid, '\n');
  end
  fclose(fid);

  fid = fopen(fullfile(out_dir, 'moments.csv'), 'w');
  fprintf(fid, 'variable,mean,std_dev,variance,autocorrelation_1\n');
  for v = 1:numel(variables)
    mean_value = oo_.mean(v);
    variance_value = oo_.var(v, v);
    autocorr_value = NaN;
    if isfield(oo_, 'autocorr') && numel(oo_.autocorr) >= 1
      autocorr_value = oo_.autocorr{1}(v, v);
    end
    fprintf(fid, '%s,%.12g,%.12g,%.12g,%.12g\n', variables{v}, ...
            mean_value, sqrt(max(variance_value,0)), variance_value, autocorr_value);
  end
  fclose(fid);

  if isfield(oo_, 'variance_decomposition') && ~isempty(oo_.variance_decomposition)
    decomposition = oo_.variance_decomposition;
    fid = fopen(fullfile(out_dir, 'fevd.csv'), 'w');
    fprintf(fid, 'variable');
    for s = 1:numel(shocks); fprintf(fid, ',%s', shocks{s}); end
    fprintf(fid, '\n');
    for v = 1:numel(variables)
      fprintf(fid, '%s', variables{v});
      for s = 1:numel(shocks)
        fprintf(fid, ',%.12g', decomposition(v, s));
      end
      fprintf(fid, '\n');
    end
    fclose(fid);
  end
end

function names = local_names(raw)
  if iscell(raw)
    names = raw;
  else
    names = cell(size(raw,1),1);
    for r = 1:size(raw,1); names{r} = strtrim(raw(r,:)); end
  end
end
