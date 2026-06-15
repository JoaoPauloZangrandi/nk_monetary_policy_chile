function export_stability(scenario_id)
  % Save Dynare's generalized-eigenvalue diagnostic before simulation.
  global M_ oo_

  repo_root = getenv('NK_REPO_ROOT');
  if isempty(repo_root)
    script_dir = fileparts(mfilename('fullpath'));
    repo_root = fileparts(script_dir);
  end
  out_dir = fullfile(repo_root, 'outputs', 'dynare', scenario_id);
  if ~exist(out_dir, 'dir')
    mkdir(out_dir);
  end

  eigvals = [];
  if isfield(oo_, 'dr') && isfield(oo_.dr, 'eigval')
    eigvals = oo_.dr.eigval(:);
  end

  n_forward = NaN;
  n_both = 0;
  if isfield(M_, 'nfwrd')
    n_forward = M_.nfwrd;
  end
  % Variables with both a lead and a lag count as forward-looking for the
  % Blanchard-Kahn root count (e.g. inflation in the hybrid NKPC model).
  if isfield(M_, 'nboth')
    n_both = M_.nboth;
    n_forward = n_forward + n_both;
  end
  n_unstable = sum(abs(eigvals) > 1.0 + 1e-6);

  if isempty(eigvals)
    status = 'unknown_no_eigenvalues';
  elseif n_unstable == n_forward
    status = 'determinate_bk_count';
  else
    status = 'not_determinate_bk_count';
  end

  fid = fopen(fullfile(out_dir, 'stability.csv'), 'w');
  fprintf(fid, 'scenario,status,n_forward,n_both,n_unstable,n_eigenvalues\n');
  fprintf(fid, '%s,%s,%g,%g,%d,%d\n', scenario_id, status, n_forward, n_both, ...
          n_unstable, length(eigvals));
  fclose(fid);

  fid = fopen(fullfile(out_dir, 'eigenvalues.csv'), 'w');
  fprintf(fid, 'scenario,index,real,imaginary,modulus\n');
  for idx = 1:length(eigvals)
    fprintf(fid, '%s,%d,%.12g,%.12g,%.12g\n', scenario_id, idx, ...
            real(eigvals(idx)), imag(eigvals(idx)), abs(eigvals(idx)));
  end
  fclose(fid);
end
