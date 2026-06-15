% Run the baseline and generated Dynare scenarios under GNU Octave.
%
% The repository can live in a OneDrive path containing spaces and accents.
% Octave's copyfile may hang on that path before Dynare starts, so this entry
% point delegates staging to the Python batch runner. The runner copies the
% public .mod files to an ASCII-only temporary directory, launches Octave and
% Dynare there, and copies the exported CSV files back to the repository.

script_dir = fileparts(mfilename('fullpath'));
repo_root = fileparts(script_dir);
runner = fullfile(repo_root, 'python', 'run_dynare_batch.py');

if ~exist(runner, 'file')
  error('Python Dynare runner not found: %s', runner);
end

python_bin = getenv('PYTHON_BIN');
if isempty(python_bin)
  python_bin = 'python';
end

run_all_scenarios = ~strcmp(getenv('NK_RUN_ALL_SCENARIOS'), '0');
all_flag = '';
if run_all_scenarios
  all_flag = ' --all';
end

command = sprintf('"%s" "%s"%s', python_bin, runner, all_flag);
fprintf('Delegating robust Dynare staging to:\n%s\n', command);
[status, output] = system(command);
fprintf('%s', output);

if status ~= 0
  error('Dynare batch runner exited with status %d.', status);
end
