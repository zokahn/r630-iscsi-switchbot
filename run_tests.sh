#!/bin/bash
# Script to run tests for r630-iscsi-switchbot with various options

# Set default values
TEST_PATH="tests"
COVERAGE=false
VERBOSE=false
HTML_REPORT=false
SPECIFIC_COMPONENT=""

# Print usage information
function show_help {
    echo "Usage: $0 [OPTIONS]"
    echo "Run tests for r630-iscsi-switchbot project"
    echo ""
    echo "Options:"
    echo "  -h, --help                 Show this help message"
    echo "  -c, --coverage             Run tests with coverage report"
    echo "  -H, --html-report          Generate HTML coverage report (implies -c)"
    echo "  -v, --verbose              Run tests with verbose output"
    echo "  -b, --base                 Test only the base component"
    echo "  -s, --s3                   Test only the S3 component"
    echo "  -i, --iscsi                Test only the iSCSI component"
    echo "  -o, --openshift            Test only the OpenShift component"
    echo "  -r, --r630                 Test only the R630 component"
    echo "  -p, --path PATH            Specify a custom test path"
    echo ""
    echo "Examples:"
    echo "  $0 -c                      Run all tests with coverage"
    echo "  $0 -c -H                   Run all tests with coverage and HTML report"
    echo "  $0 -s -v                   Run S3 component tests with verbose output"
    echo "  $0 -p tests/unit/framework Test only framework tests"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -H|--html-report)
            HTML_REPORT=true
            COVERAGE=true
            shift
            ;;
        -b|--base)
            SPECIFIC_COMPONENT="test_base_component.py"
            shift
            ;;
        -s|--s3)
            SPECIFIC_COMPONENT="test_s3_component.py"
            shift
            ;;
        -i|--iscsi)
            SPECIFIC_COMPONENT="test_iscsi_component.py"
            shift
            ;;
        -o|--openshift)
            SPECIFIC_COMPONENT="test_openshift_component.py"
            shift
            ;;
        -r|--r630)
            SPECIFIC_COMPONENT="test_r630_component.py"
            shift
            ;;
        -p|--path)
            TEST_PATH="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "Error: pytest is not installed. Please install it with:"
    echo "pip install pytest pytest-cov pytest-mock"
    exit 1
fi

# Build command based on options
CMD="pytest"

if [ "$VERBOSE" = true ]; then
    CMD="$CMD -v"
fi

if [ "$COVERAGE" = true ]; then
    # Check if pytest-cov is installed
    if ! python -c "import pytest_cov" &> /dev/null; then
        echo "Error: pytest-cov is not installed. Please install it with:"
        echo "pip install pytest-cov"
        exit 1
    fi
    
    # Configure coverage reports
    if [ "$HTML_REPORT" = true ]; then
        CMD="$CMD --cov=framework --cov-report=term --cov-report=html"
        echo "HTML coverage report will be generated in coverage_html_report/"
    else
        CMD="$CMD --cov=framework --cov-report=term"
    fi
fi

# Add specific component if requested
if [ -n "$SPECIFIC_COMPONENT" ]; then
    # Search for the component test file
    if [ "$SPECIFIC_COMPONENT" = "test_base_component.py" ]; then
        TEST_PATH="tests/unit/framework/$SPECIFIC_COMPONENT"
    else
        TEST_PATH="tests/unit/framework/components/$SPECIFIC_COMPONENT"
    fi
fi

# Run tests
echo "Running: $CMD $TEST_PATH"
$CMD $TEST_PATH

# Exit with the pytest exit code
exit $?
