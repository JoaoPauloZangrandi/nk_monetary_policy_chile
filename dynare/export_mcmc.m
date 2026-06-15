function export_mcmc(scenario_id)
  % Export posterior MCMC summaries produced by Dynare.
  global oo_
  repo_root = getenv('NK_REPO_ROOT');
  if isempty(repo_root); repo_root = pwd(); end
  out_dir = fullfile(repo_root, 'outputs', 'tables');
  if ~exist(out_dir, 'dir'); mkdir(out_dir); end

  fid = fopen(fullfile(out_dir, 'mcmc_posterior.csv'), 'w');
  fprintf(fid, 'parameter,type,posterior_mean,posterior_median,posterior_std,hpd90_low,hpd90_high\n');

  shocks = {'e_x','e_pi','e_i'};
  for j = 1:numel(shocks)
    nm = shocks{j};
    fprintf(fid, 'stderr %s,shock_std,%.12g,%.12g,%.12g,%.12g,%.12g\n', ...
            nm, oo_.posterior_mean.shocks_std.(nm), ...
            oo_.posterior_median.shocks_std.(nm), ...
            oo_.posterior_std.shocks_std.(nm), ...
            oo_.posterior_hpdinf.shocks_std.(nm), ...
            oo_.posterior_hpdsup.shocks_std.(nm));
  end

  params = {'sigma','kappa','rho_i','phi_pi','phi_x'};
  for j = 1:numel(params)
    nm = params{j};
    fprintf(fid, '%s,param,%.12g,%.12g,%.12g,%.12g,%.12g\n', ...
            nm, oo_.posterior_mean.parameters.(nm), ...
            oo_.posterior_median.parameters.(nm), ...
            oo_.posterior_std.parameters.(nm), ...
            oo_.posterior_hpdinf.parameters.(nm), ...
            oo_.posterior_hpdsup.parameters.(nm));
  end
  fclose(fid);
  fprintf('export_mcmc: posterior summaries written.\n');
end
