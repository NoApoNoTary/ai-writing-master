# Claude project memory

- Canonical repo: `/home/amose/ai-writing-master`; do not copy runtime state.
- Layout: application code under `src/writing_master/`, tests under `tests/`, skills under `skills/`, docs under `docs/`.
- If `.codegraph/` exists, use CodeGraph first (`codegraph explore "..."`) before grep/find.
- Shared runtime is `~/.writing-master`; resume with an explicit `task_id`/`run_dir`, and never have two writers modify the same run.
- Validation: `PYTHONPATH=src python -m unittest discover -s tests -v`; `PYTHONPYCACHEPREFIX=/tmp/awm-pyc python -m compileall -q src tests`; `bash -n install.sh`; `./bin/writing-master --help`.
