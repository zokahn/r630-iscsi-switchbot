# Python 3.12 Migration Guide

This document outlines the plan and changes required to migrate the r630-iscsi-switchbot project to Python 3.12.

## Summary

Python 3.12 offers several benefits for this project:

- **Performance Improvements**: 5% overall performance boost, with specific optimizations for list/dict comprehensions (PEP 709)
- **Enhanced Error Messages**: Clearer error reporting with better suggestions for typos
- **Improved Type Hinting**: More user-friendly generic type syntax (PEP 695)
- **Better Debugging**: Low-impact monitoring API for profiling without overhead
- **Security Enhancements**: Safer memory handling through buffer protocol improvements

## Completed Changes

### Updated Dependencies

The `requirements.txt` file has been updated to ensure compatibility with Python 3.12:

```
# R630 iSCSI SwitchBot Requirements (Python 3.12 Compatible)
# Core dependencies
boto3>=1.34.0  # Latest version with improved S3 performance
requests>=2.31.0
python-dotenv>=1.0.0
pyyaml>=6.0.1  # Updated for Python 3.12 support

# For TrueNAS integration
urllib3>=2.2.0  # Updated for better security
certifi>=2024.2.0  # Latest certificate bundle

# For OpenShift
# pyyaml already defined above

# For HashiCorp Vault
hvac>=1.2.1  # Latest Vault client with enhanced API support

# For testing
pytest>=7.4.3  # Latest compatible with Python 3.12
pytest-mock>=3.12.0
pytest-cov>=4.1.0  # For test coverage
pytest-xdist>=3.5.0  # Parallel test execution for Python 3.12
moto>=4.2.0  # For testing S3

# New tools for CI/CD modernization
bandit>=1.7.6  # Security scanning
types-requests>=2.31.0.2  # Type stubs for requests
mypy>=1.8.0  # Static type checking
pylint>=3.0.3  # Code linting
safety>=2.3.5  # Dependency vulnerability scanning
```

## Changes Required for CI Workflows

### Update Python Version

In all CI workflows, update Python version references to use 3.12:

```yaml
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: '3.12'
```

For matrix testing, simplify to only test with Python 3.12:

```yaml
strategy:
  fail-fast: false
  matrix:
    python-version: ['3.12']
```

### Add Static Type Checking

Add mypy static type checking to the code quality steps:

```yaml
- name: Static type checking
  id: mypy
  run: |
    # Run mypy on core modules
    mkdir -p reports
    mypy framework scripts --python-version 3.12 --show-error-codes --ignore-missing-imports \
      --pretty --html-report reports/type-report > reports/mypy-output.txt || true
    
    # Count type issues
    TYPE_ISSUES=$(grep -c "error:" reports/mypy-output.txt 2>/dev/null || echo "0")
    echo "type_issues=${TYPE_ISSUES}" >> ${GITHUB_OUTPUT}
    
    echo "Found ${TYPE_ISSUES} type issues"
```

### Enhance Security Scanning

Expand security scanning to include dependency vulnerability checks:

```yaml
- name: Security check
  id: security
  run: |
    # Run comprehensive security checks
    echo "Running bandit security scan..."
    bandit -r . -f json -o reports/security-report.json --exit-zero
    
    echo "Running dependency vulnerability scan..."
    safety check --json > reports/safety-report.json || true
    
    # Count security issues
    SEC_COUNT=$(jq '.results | length' reports/security-report.json)
    HIGH_COUNT=$(jq '.metrics.baseline.SEVERITY.HIGH' reports/security-report.json)
    
    # Count dependency vulnerabilities
    VULN_COUNT=$(jq 'length' reports/safety-report.json 2>/dev/null || echo "0")
    
    echo "security_issues=${SEC_COUNT}" >> ${GITHUB_OUTPUT}
    echo "high_severity=${HIGH_COUNT}" >> ${GITHUB_OUTPUT}
    echo "vulnerabilities=${VULN_COUNT}" >> ${GITHUB_OUTPUT}
```

### Update Docker Compose Commands

Replace all instances of `docker-compose` with `docker compose` for compatibility with Docker Compose V2:

```yaml
# Before
- name: Start test services
  run: docker-compose -f docker-compose.test.yml up -d

# After
- name: Verify Docker Compose
  run: docker compose version

- name: Start test services
  run: docker compose -f docker-compose.test.yml up -d
```

## Type Annotation Strategy

To leverage Python 3.12's typing improvements, the following files should be annotated with type hints:

1. Core framework components in `framework/components/*.py`
2. Utility functions in `framework/base_component.py`
3. Critical scripts in `scripts/`

For example:

```python
# Before
def process_data(input_data, config=None):
    # Function implementation

# After
from typing import Dict, Any, Optional

def process_data(input_data: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> bool:
    # Function implementation
```

## Testing Strategy

1. Update test fixtures to handle Python 3.12 changes
2. Leverage `pytest-xdist` for parallel testing
3. Implement specific tests for new Python 3.12 features

Example test command:

```bash
python -m pytest tests/unit/framework \
  --cov=framework \
  --cov-report=xml:reports/coverage-3.12-framework.xml \
  --cov-report=html:reports/htmlcov-3.12-framework \
  --junitxml=reports/junit-3.12-framework.xml \
  -v -n auto
```

## Next Steps

1. **Update GitHub Actions Workflows**: Fix all YAML files in `.github/workflows/` 
2. **Add Type Annotations**: Incrementally add type hints to core modules
3. **Update Docker Configurations**: Update Docker base images to Python 3.12
4. **Refactor String Formatting**: Leverage improved f-string capabilities
5. **Enhance Error Handling**: Update error handling to benefit from better error messages

## References

- [Python 3.12 Release Notes](https://docs.python.org/3.12/whatsnew/3.12.html)
- [PEP 709: Inlined Comprehensions](https://peps.python.org/pep-0709/)
- [PEP 695: Type Parameter Syntax](https://peps.python.org/pep-0695/)
- [PEP 701: F-String Enhancements](https://peps.python.org/pep-0701/)
