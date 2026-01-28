# Backend CI/CD Workflow Documentation

## Overview

The `backend-ci.yml` GitHub Actions workflow provides automated quality assurance for the DbRevel backend codebase. It runs tests, linting, and build verification on every push and pull request to ensure code quality and prevent regressions.

## Workflow File Location

`.github/workflows/backend-ci.yml`

## Trigger Conditions

The workflow automatically runs when:

1. **Push Events:**
   - Code is pushed to `main` or `develop` branches
   - Only triggers if files in `backend/**` directory are changed
   - Also triggers if the workflow file itself is modified

2. **Pull Request Events:**
   - Pull requests targeting `main` branch
   - Only triggers if files in `backend/**` directory are changed

**Path Filtering:** This ensures the workflow only runs when backend code changes, saving CI resources and time.

## Workflow Structure

The workflow consists of three independent jobs that run in parallel (except build which depends on the others):

```
┌─────────┐
│  Test   │ (Runs on Python 3.11 & 3.12)
└─────────┘
     │
     ├─────────────────┐
     │                 │
┌─────────┐      ┌─────────┐
│  Lint   │      │  Build  │ (Waits for Test & Lint)
└─────────┘      └─────────┘
```

## Jobs Breakdown

### 1. Test Job

**Purpose:** Run the test suite and collect code coverage metrics

**Configuration:**
- **Runs on:** `ubuntu-latest`
- **Python Versions:** 3.11 and 3.12 (matrix strategy for compatibility testing)
- **Working Directory:** `backend/`

**Steps:**

1. **Checkout Repository**
   - Uses `actions/checkout@v4` to fetch the code

2. **Setup Python**
   - Uses `actions/setup-python@v5`
   - Installs the Python version from the matrix (3.11 or 3.12)
   - Enables pip caching for faster dependency installation

3. **Install Dependencies**
   - Upgrades pip to the latest version
   - Installs all packages from `requirements.txt`

4. **Run Tests**
   - Executes: `pytest tests/ -v --cov=app --cov-report=xml --cov-report=html`
   - **Flags:**
     - `-v`: Verbose output (shows individual test names)
     - `--cov=app`: Measure code coverage for the `app/` directory
     - `--cov-report=xml`: Generate XML coverage report (for CI tools)
     - `--cov-report=html`: Generate HTML coverage report (for viewing)

**Output:** Test results and coverage reports are available in the GitHub Actions UI

### 2. Lint Job

**Purpose:** Enforce code quality, style consistency, and type safety

**Configuration:**
- **Runs on:** `ubuntu-latest`
- **Python Version:** 3.11
- **Working Directory:** `backend/`

**Steps:**

1. **Checkout Repository**
   - Uses `actions/checkout@v4`

2. **Setup Python**
   - Uses `actions/setup-python@v5`
   - Python 3.11 with pip caching

3. **Install Dependencies**
   - Upgrades pip and installs from `requirements.txt`

4. **Run Ruff**
   - Executes: `ruff check .`
   - Fast Python linter that checks for:
     - Code style violations
     - Potential bugs
     - Unused imports
     - Import sorting

5. **Run Black (Check Mode)**
   - Executes: `black --check .`
   - Checks if code follows Black's formatting rules
   - Uses `--check` flag (doesn't modify files, only reports issues)

6. **Run Mypy**
   - Executes: `mypy app/ --ignore-missing-imports`
   - Static type checker for Python
   - `--ignore-missing-imports`: Ignores errors from third-party packages without type stubs

**Output:** Linting errors are reported in the GitHub Actions UI. PRs will show which files need formatting fixes.

### 3. Build Job

**Purpose:** Verify the application can be built and imported successfully

**Configuration:**
- **Runs on:** `ubuntu-latest`
- **Python Version:** 3.11
- **Working Directory:** `backend/`
- **Dependencies:** Requires both `test` and `lint` jobs to pass first

**Steps:**

1. **Checkout Repository**
   - Uses `actions/checkout@v4`

2. **Setup Python**
   - Uses `actions/setup-python@v5`
   - Python 3.11 with pip caching

3. **Install Dependencies**
   - Upgrades pip and installs from `requirements.txt`

4. **Verify Imports**
   - Executes: `python -c "import app.main; print('✓ Imports successful')"`
   - Ensures the main application module can be imported without errors
   - Catches import-time errors (missing dependencies, syntax errors, etc.)

5. **Build Docker Image (Test)**
   - Executes: `docker build -t dbrevel-backend:test .`
   - Tests that the Dockerfile works correctly
   - Verifies all Docker build steps complete successfully
   - Does not push the image (just validates the build)

**Output:** Build status and any Docker build errors are reported in the GitHub Actions UI

## Key Features

### 1. Path-Based Filtering
```yaml
paths:
  - "backend/**"
```
Only runs when backend files change, saving CI minutes and reducing noise.

### 2. Matrix Testing
```yaml
matrix:
  python-version: ["3.11", "3.12"]
```
Tests compatibility across multiple Python versions to catch version-specific issues.

### 3. Dependency Caching
```yaml
cache: "pip"
```
Caches pip packages between runs, significantly speeding up workflow execution.

### 4. Job Dependencies
```yaml
needs: [test, lint]
```
The build job only runs if tests and linting pass, preventing unnecessary builds.

### 5. Coverage Reporting
- **XML Report:** For CI/CD tools and coverage badges
- **HTML Report:** For detailed coverage visualization (can be uploaded as artifact)

## Workflow Execution Flow

```
┌─────────────────────────────────────────┐
│  Push/PR to main or develop             │
│  (with backend/** changes)              │
└──────────────┬──────────────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │  GitHub Actions      │
    │  Triggers Workflow   │
    └──────────┬───────────┘
               │
    ┌──────────┴───────────┐
    │                      │
    ▼                      ▼
┌─────────┐          ┌─────────┐
│  Test   │          │  Lint   │
│  Job    │          │  Job    │
└────┬────┘          └────┬────┘
     │                    │
     └──────────┬─────────┘
                │
                ▼
         ┌──────────┐
         │  Build   │
         │  Job     │
         └──────────┘
```

## What Happens When Workflow Runs

### On Push to `main` or `develop`:
1. All three jobs run in parallel (test and lint)
2. Build job waits for test and lint to complete
3. If any job fails, the workflow is marked as failed
4. Results are visible in the GitHub Actions tab

### On Pull Request:
1. Same process as push events
2. PR shows status checks (pass/fail) directly in the PR UI
3. PR cannot be merged if required checks fail (if branch protection is enabled)

## Benefits

1. **Early Bug Detection:** Catches issues before code reaches production
2. **Code Quality:** Enforces consistent code style and type safety
3. **Multi-Version Testing:** Ensures compatibility across Python versions
4. **Build Verification:** Confirms Docker builds work correctly
5. **Coverage Tracking:** Monitors test coverage over time
6. **Fast Feedback:** Developers get immediate feedback on their changes

## Viewing Results

### In GitHub UI:
1. Go to the **Actions** tab in your repository
2. Click on a workflow run to see detailed logs
3. Expand each job to see individual step outputs
4. View test results, coverage reports, and linting errors

### Coverage Reports:
- HTML coverage reports can be downloaded as artifacts
- XML reports can be used with coverage tools like Codecov

## Troubleshooting

### Tests Fail:
- Check test output in the Actions tab
- Run tests locally: `pytest tests/ -v`
- Ensure all dependencies are in `requirements.txt`

### Linting Fails:
- Run `ruff check .` locally to see errors
- Run `black .` to auto-format code
- Fix mypy type errors or add type hints

### Build Fails:
- Check Docker build logs in Actions
- Test Docker build locally: `docker build -t test .`
- Verify `Dockerfile` is correct

### Workflow Not Running:
- Check if files changed are in `backend/**` directory
- Verify workflow file is in `.github/workflows/`
- Check GitHub Actions is enabled for the repository

## Best Practices

1. **Run Locally First:** Always run tests and linting locally before pushing
2. **Fix Linting Early:** Address linting errors immediately to keep PRs clean
3. **Maintain Coverage:** Aim for 70%+ test coverage
4. **Review Failures:** Don't ignore CI failures - they indicate real issues
5. **Use Matrix Testing:** Keep Python version matrix up to date

## Future Enhancements

Future improvements testing and CI/CD workflow:

- [ ] Upload coverage reports to Codecov or similar service
- [ ] Add security scanning (e.g., `safety` or `bandit`)
- [ ] Cache Docker layers for faster builds
- [ ] Add performance benchmarking
- [ ] Set up deployment on successful builds (separate workflow)
- [ ] Add integration tests with test databases
- [ ] Generate and publish test reports as artifacts

## Related Files

- `backend/requirements.txt` - Python dependencies
- `backend/Dockerfile` - Docker build configuration
- `backend/tests/` - Test suite directory
- `backend/pytest.ini` or `pyproject.toml` - Pytest configuration (if exists)

## Summary

This CI/CD workflow ensures that:
- All tests pass on multiple Python versions
- Code follows style guidelines (Ruff, Black)
- Type hints are correct (Mypy)
- Application builds successfully (Docker)
- Code coverage is tracked

By running automatically on every push and PR, it provides continuous quality assurance and helps maintain a stable, production-ready codebase.
