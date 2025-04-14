#!/usr/bin/env python3
"""
Test script to verify Python 3.12 compatibility.

This script tests for Python 3.12 features and reports if they're available.
"""

import sys
import importlib
import time
from typing import Optional, Any


def check_python_version() -> tuple[bool, str]:
    """Check if running on Python 3.12 or later."""
    version = sys.version_info
    
    is_compatible = (version.major == 3 and version.minor >= 12)
    
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    return is_compatible, version_str


def test_type_parameter_syntax() -> tuple[bool, str]:
    """Test for PEP 695 type parameter syntax."""
    try:
        # Test code that uses the new syntax
        exec("""
class Stack[T]:
    def __init__(self):
        self.items: list[T] = []
        
    def push(self, item: T) -> None:
        self.items.append(item)
        
    def pop(self) -> T | None:
        if not self.items:
            return None
        return self.items.pop()
""")
        return True, "Type parameter syntax available (PEP 695)"
    except SyntaxError:
        return False, "Type parameter syntax not available"


def test_f_string_improvements() -> tuple[bool, str]:
    """Test for PEP 701 f-string improvements."""
    
    try:
        # Test code that uses the new features
        name = "world"
        exec("""
# Quote character in f-string without escaping
greeting = f"Hello {"world"}"
        
# Arbitrary expressions in f-strings
nested = f"The uppercase is {name.upper() if name else 'UNKNOWN'}"
""")
        return True, "F-string improvements available (PEP 701)"
    except SyntaxError:
        return False, "F-string improvements not available"


def test_performance() -> tuple[bool, float]:
    """
    Test performance improvements in Python 3.12 (not definitive).
    
    Returns:
        Tuple of (is_likely_312, execution_time_seconds)
    """
    # Create a large list
    large_list = list(range(1_000_000))
    
    # Time a comprehension operation which is optimized in 3.12
    start_time = time.time()
    
    # This is faster in Python 3.12 due to comprehension optimizations
    result = [x for x in large_list if x % 100 == 0]
    result_dict = {x: x*2 for x in result if x > 5000}
    
    end_time = time.time()
    
    execution_time = end_time - start_time
    
    # This is a rough heuristic - not definitive
    is_likely_312 = execution_time < 0.3  # Rough benchmark
    
    return is_likely_312, execution_time


def main() -> None:
    """Run all tests and report results."""
    print("Python 3.12 Feature Compatibility Test")
    print("=====================================")
    
    # Check Python version
    is_py312, version_str = check_python_version()
    print(f"Running Python: {version_str}")
    print(f"Compatible with Python 3.12+: {'Yes' if is_py312 else 'No'}")
    print()
    
    # Test individual features
    features = [
        ("Type parameter syntax (PEP 695)", test_type_parameter_syntax),
        ("F-string improvements (PEP 701)", test_f_string_improvements),
    ]
    
    for name, test_func in features:
        result, message = test_func()
        print(f"{name}: {'✓' if result else '✗'} - {message}")
    
    # Test performance
    is_fast, execution_time = test_performance()
    print(f"Performance test: {'✓ Optimized' if is_fast else '✗ Not optimized'} "
          f"- Execution time: {execution_time:.6f} seconds")
    
    print("\nSummary:")
    if is_py312:
        print("✓ Python 3.12 detected and compatible!")
    else:
        print("⚠ Not running on Python 3.12. Some features may not be available.")


if __name__ == "__main__":
    main()
