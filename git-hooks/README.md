# Git Hooks

This project uses git hooks to run code quality checks before pushing to GitHub, similar to how Node.js projects use husky + lint-staged.

## Setup

Run the installation script to set up the git hooks:

```bash
bash install-git-hooks.sh
```

This will install the pre-push hook that runs:
- **black** (code formatting check)
- **ruff** (linting)
- **mypy** (type checking)

## What the hooks do

### Pre-push hook

Before you can push to GitHub, the hook will:
1. Check that `black`, `ruff`, and `mypy` are installed
2. Run `black --check app/` to verify formatting
3. Run `ruff check app/` to check for linting issues
4. Run `mypy app/ --ignore-missing-imports` for type checking

If any check fails, the push will be blocked and you'll see error messages telling you what to fix.

## Bypassing the hook (not recommended)

If you absolutely need to bypass the hook (e.g., for emergency hotfixes), you can use:

```bash
git push --no-verify
```

**Warning:** Only bypass hooks when absolutely necessary. The CI pipeline will still run these checks, so failing code will be caught there.

## For new team members

When cloning the repository, run:

```bash
bash install-git-hooks.sh
```

This ensures everyone has the same pre-push checks.

## Troubleshooting

### "black/ruff/mypy not found"

Make sure you've installed the Python dependencies:

```bash
cd backend
pip install -r requirements.txt
```

### Hook not running

1. Check that the hook is installed: `ls -la .git/hooks/pre-push`
2. Check that it's executable: `chmod +x .git/hooks/pre-push`
3. Re-run the install script: `bash install-git-hooks.sh`
