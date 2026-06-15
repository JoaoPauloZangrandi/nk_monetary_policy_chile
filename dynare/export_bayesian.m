function export_bayesian(scenario_id)
  % Export Bayesian posterior-mode (MAP) estimates to a simple CSV. Standard errors are
  % added afterwards in Python from the saved mode Hessian (run_bayesian.py). After
  % mode-finding Dynare sets M_.params and M_.Sigma_e to the posterior mode, so the point
  % estimates are read from there in the order of bayestopt_.name (shock stds first).
  global M_ estim_params_ bayestopt_

  repo_root = getenv('NK_REPO_ROOT');
  if isempty(repo_root); repo_root = pwd(); end
  out_dir = fullfile(repo_root, 'outputs', 'tables');
  if ~exist(out_dir, 'dir'); mkdir(out_dir); end

  names = bayestopt_.name;
  prior_mean = bayestopt_.p1;
  nvx = 0;
  if isfield(estim_params_, 'nvx'); nvx = estim_params_.nvx; end

  fid = fopen(fullfile(out_dir, 'bayesian_estimates.csv'), 'w');
  fprintf(fid, 'parameter,type,prior_mean,posterior_mode\n');
  for j = 1:numel(names)
    nm = names{j};
    est = NaN;
    if j <= nvx
      typ = 'shock_std';
      k = find(strcmp(cellstr(M_.exo_names), nm));
      if ~isempty(k); est = sqrt(M_.Sigma_e(k, k)); end
    else
      typ = 'param';
      k = find(strcmp(cellstr(M_.param_names), nm));
      if ~isempty(k); est = M_.params(k); end
    end
    pm = NaN;
    if numel(prior_mean) >= j; pm = prior_mean(j); end
    fprintf(fid, '%s,%s,%.6g,%.6g\n', nm, typ, pm, est);
  end
  fclose(fid);
  fprintf('export_bayesian: wrote %d parameters (posterior mode)\n', numel(names));
end
