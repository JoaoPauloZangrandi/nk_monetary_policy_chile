function export_results(scenario_id)
  % Export compact CSV files that Python can read without parsing MAT structs.
  global M_ oo_ options_

  repo_root = getenv('NK_REPO_ROOT');
  if isempty(repo_root)
    script_dir = fileparts(mfilename('fullpath'));
    repo_root = fileparts(script_dir);
  end
  out_dir = fullfile(repo_root, 'outputs', 'dynare', scenario_id);
  if ~exist(out_dir, 'dir')
    mkdir(out_dir);
  end

  variables = {'x', 'pi', 'i'};
  shocks = {'e_x', 'e_pi', 'e_i'};
  horizon = options_.irf;

  fid = fopen(fullfile(out_dir, 'irfs.csv'), 'w');
  fprintf(fid, 'horizon');
  for v = 1:length(variables)
    for s = 1:length(shocks)
      fprintf(fid, ',%s_%s', variables{v}, shocks{s});
    end
  end
  fprintf(fid, '\n');

  for t = 1:horizon
    fprintf(fid, '%d', t - 1);
    for v = 1:length(variables)
      for s = 1:length(shocks)
        field_name = [variables{v} '_' shocks{s}];
        value = 0;
        if isfield(oo_.irfs, field_name)
          series = oo_.irfs.(field_name);
          if length(series) >= t
            value = series(t);
          end
        end
        fprintf(fid, ',%.12g', value);
      end
    end
    fprintf(fid, '\n');
  end
  fclose(fid);

  fid = fopen(fullfile(out_dir, 'moments.csv'), 'w');
  fprintf(fid, 'variable,mean,std_dev,variance,autocorrelation_1\n');
  for v = 1:length(variables)
    mean_value = NaN;
    variance_value = NaN;
    autocorr_value = NaN;
    if isfield(oo_, 'mean') && length(oo_.mean) >= v
      mean_value = oo_.mean(v);
    end
    if isfield(oo_, 'var') && size(oo_.var, 1) >= v
      variance_value = oo_.var(v, v);
    end
    if isfield(oo_, 'autocorr') && length(oo_.autocorr) >= 1
      if size(oo_.autocorr{1}, 1) >= v
        autocorr_value = oo_.autocorr{1}(v, v);
      end
    end
    fprintf(fid, '%s,%.12g,%.12g,%.12g,%.12g\n', variables{v}, ...
            mean_value, sqrt(max(variance_value, 0)), variance_value, ...
            autocorr_value);
  end
  fclose(fid);

  if isfield(oo_, 'var') && size(oo_.var, 1) >= length(variables)
    covariance = oo_.var(1:length(variables), 1:length(variables));
    standard_deviations = sqrt(max(diag(covariance), 0));
    correlation = covariance ./ (standard_deviations * standard_deviations');
    fid = fopen(fullfile(out_dir, 'correlations.csv'), 'w');
    fprintf(fid, 'variable,x,pi,i\n');
    for v = 1:length(variables)
      fprintf(fid, '%s', variables{v});
      for other = 1:length(variables)
        fprintf(fid, ',%.12g', correlation(v, other));
      end
      fprintf(fid, '\n');
    end
    fclose(fid);
  end

  if isfield(oo_, 'variance_decomposition') && ...
     ~isempty(oo_.variance_decomposition)
    decomposition = oo_.variance_decomposition;
    fid = fopen(fullfile(out_dir, 'fevd.csv'), 'w');
    fprintf(fid, 'variable,e_x,e_pi,e_i\n');
    for v = 1:min(length(variables), size(decomposition, 1))
      fprintf(fid, '%s', variables{v});
      for s = 1:min(length(shocks), size(decomposition, 2))
        fprintf(fid, ',%.12g', decomposition(v, s));
      end
      fprintf(fid, '\n');
    end
    fclose(fid);
  end

end
