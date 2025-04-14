# Non-Intrusive Linting Policy

## Core Principles

1. **WARNING-ONLY LINTING**: All linting tools in our CI/CD pipeline operate in warning-only mode. They identify potential issues but **NEVER** automatically modify code.

2. **NO AUTOMATIC CODE CHANGES**: Under no circumstances should linters reformat code, reorganize imports, or make any other automated changes.

3. **Developer Autonomy**: We respect developer coding styles and preferences. Our linters suggest improvements but don't enforce them.

4. **Focus on Substance, Not Style**: We prioritize catching bugs, security vulnerabilities, and logical errors over style concerns.

## Rationale

Our team has adopted this non-intrusive approach because:

1. **Unexpected modifications** from linters can introduce bugs or break working code
2. **False confidence** in code quality based solely on passing lint checks is dangerous
3. **Creative constraint** from overly strict linting can impede innovation
4. **Maintenance overhead** of complex lint configurations can be burdensome

## Approved Linting Tools

We use these tools in warning-only mode:

1. **Flake8**: For identifying potential errors (with `--exit-zero` flag)
2. **Bandit**: For security vulnerability scanning (with `--exit-zero` flag)

## Configuration Guidelines

All linting tools MUST be configured with these constraints:

```yaml
# Example GitHub Actions configuration
- name: Lint with flake8 (warning only)
  run: |
    # Will report issues but won't modify code or fail the build
    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exit-zero
```

## Linting in CI Pipeline

Our GitHub Actions workflows:
- Generate linting reports as artifacts
- Never fail builds based on style issues
- Provide warnings for review at the developer's convenience
- NEVER include automated formatting tools

## Local Development

For local development, we provide:
- VS Code settings to display warnings without interrupting workflow
- Optional pre-commit hooks (disabled by default)
- Documentation on how to interpret linting warnings

## Exceptions

Team members can add exceptions for specific rules in specific files using standard comment-based directives:

```python
# noqa: E501  # For long lines
# nosec  # For security exceptions with justification
```

These exceptions should include comments explaining why the exception is necessary.

## Why We Don't Auto-Format

While tools like Black, autopep8, and isort can ensure code consistency, we've chosen not to use them for these reasons:

1. **Unexpected Changes**: Automatic formatting can change code in ways the developer didn't intend
2. **Merge Conflicts**: Auto-formatting increases the likelihood of merge conflicts
3. **Team Preferences**: Our team has diverse formatting preferences
4. **Legacy Code**: Auto-formatting can break carefully formatted legacy code
5. **Cognitive Flow**: Automatic changes interrupt developer flow and focus

## Conclusion

This non-intrusive linting policy aims to balance code quality with developer autonomy. By providing warnings without forcing changes, we help identify potential issues while respecting the expertise and preferences of our development team.
