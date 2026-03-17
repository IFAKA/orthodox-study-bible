# Contributing to Orthodox Study Bible TUI

Thank you for your interest in contributing! We welcome bug reports, feature requests, and code contributions.

## How to Contribute

1.  **Report Bugs**: Open an issue describing the bug and how to reproduce it.
2.  **Suggest Features**: Open an issue describing the feature and why it would be useful.
3.  **Submit Pull Requests**:
    *   Fork the repository.
    *   Create a branch for your change.
    *   Write your code and add tests if applicable.
    *   Run `uv run pytest` to ensure tests pass.
    *   Submit a pull request.

## Development Setup

We use `uv` for dependency management.

```bash
# Clone the repository
git clone https://github.com/IFAKA/orthodox-study-bible
cd orthodox-study-bible

# Install dependencies
uv sync

# Run the app (requires your own OSB EPUB)
uv run osb
```

## Code Style

- Follow PEP 8 for Python code.
- Use meaningful variable and function names.
- Keep components focused and modular (following the existing Textual structure).

## Legal Notice

By contributing, you agree that your contributions will be licensed under the project's MIT License.
