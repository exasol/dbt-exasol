## 1. Directory Restructure
- [x] 1.1 Rename `tests/` to `test/`
- [x] 1.2 Rename `test/functional/` to `test/integration/`
- [x] 1.3 Update pytest.ini testpaths
- [x] 1.4 Update pyproject.toml mypy overrides

## 2. Simplify noxfile.py
- [x] 2.1 Remove unit_tests session override
- [x] 2.2 Remove integration_tests session override
- [x] 2.3 Remove coverage session override
- [x] 2.4 Remove project:check session override
- [x] 2.5 Remove _test_command helper (use toolbox default)
- [x] 2.6 Remove _unit_tests, _integration_tests helpers
- [x] 2.7 Simplify artifacts:copy (remove debug logging)
- [x] 2.8 Keep db:start, db:stop sessions
- [x] 2.9 Remove FutureWarning suppression (no longer needed)

## 3. Update CI Workflow
- [x] 3.1 Add setup job to output Python matrix from nox
- [x] 3.2 Update checks job to use dynamic matrix
- [x] 3.3 Add Python 3.13 to noxconfig.py (already there)
- [ ] 3.4 Test CI workflow runs correctly

## 4. Align mise.toml Tasks
- [x] 4.1 Update `tasks.lint` to wrap nox
- [x] 4.2 Update `tasks.test` to wrap nox
- [x] 4.3 Add `tasks.format` (nox -s format:fix)
- [x] 4.4 Add `tasks.format-check` (nox -s format:check)
- [x] 4.5 Add `tasks."test:unit"` (nox -s test:unit)
- [x] 4.6 Add `tasks."test:integration"` (nox -s test:integration)
- [x] 4.7 Add `tasks.check` (all checks)

## 5. Documentation
- [x] 5.1 Update AGENTS.md test path references
- [x] 5.2 Verify all tests pass after restructure

## 6. Validation
- [x] 6.1 Run `nox -s test:unit` successfully
- [ ] 6.2 Run `nox -s test:integration` successfully
- [x] 6.3 Run `nox -s format:check` successfully
- [ ] 6.4 Run full CI workflow locally
