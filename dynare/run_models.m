% Run every .mod file in the current (ASCII) working directory through Dynare.
% Each model exports its CSVs through the verbatim blocks calling export_stability
% and export_results; NK_REPO_ROOT controls where those CSVs are written.
%
% The Python wrapper (run_dynare_batch.py) stages the .mod files, the export
% helpers and this script into a disposable ASCII temp directory and then copies
% the resulting CSVs back into the repository. Running entirely under an ASCII
% path avoids the OneDrive file-locking / accented-path problems seen when Dynare
% preprocesses directly inside the synced project folder.

addpath(pwd());
files = dir('*.mod');
names = sort({files.name});

% Run the baseline first when it is present.
is_base = strcmp(names, 'nk_chile_base.mod');
names = [names(is_base), names(~is_base)];

log_dir = fullfile(getenv('NK_REPO_ROOT'), 'outputs', 'logs');
if ~exist(log_dir, 'dir'); mkdir(log_dir); end
fid = fopen(fullfile(log_dir, 'dynare_driver.log'), 'w');
fprintf('Dynare %s; running %d model(s).\n', dynare_version, numel(names));
fprintf(fid, 'Dynare %s; %d model(s).\n', dynare_version, numel(names));

failures = {};
for k = 1:numel(names)
  m = names{k};
  fprintf('[%d/%d] %s\n', k, numel(names), m);
  fprintf(fid, '[%d/%d] %s ... ', k, numel(names), m); fflush(fid);
  try
    dynare(m, 'noclearall', 'nolog', 'nograph');
    fprintf(fid, 'OK\n');
  catch e
    failures{end+1} = m;
    fprintf(fid, 'FAIL: %s\n', e.message);
    fprintf(2, 'FAIL %s: %s\n', m, e.message);
  end
  fflush(fid);
end
fprintf(fid, 'Completed with %d failure(s).\n', numel(failures));
fclose(fid);
fprintf('Batch done with %d failure(s).\n', numel(failures));
