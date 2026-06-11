# Contributing

## Workflow

1. Create a branch from `master`.
2. Make focused changes with tests or documentation updates when behavior changes.
3. Run the local checks:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m ruff check .
python -m kunity_yamae.cli release-check --json
```

4. Open a pull request.

Direct pushes to `master` are blocked. Pull requests require review, passing CI, and code owner review for owned paths.

## Release Source

GitHub Releases are the official installation source for users. Source installs are for maintainers and contributors working on the project.

## Security

Do not include secrets, tokens, Unity license files, or private project data in commits, issues, logs, screenshots, or pull requests.
