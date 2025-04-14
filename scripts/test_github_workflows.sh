#!/bin/bash
# Script to assist with testing GitHub Actions workflows
# This simplifies the process of creating test branches, triggering workflows, and analyzing results

set -e

# Default values
BRANCH_NAME="ci-workflow-test"
REMOTE_NAME="origin"
TEST_UNIT=false
TEST_COMPONENT=false
TEST_INTEGRATION=false
TEST_ISO=false
SERVER_IP="192.168.2.230"
TRUENAS_IP="192.168.2.245"
OPENSHIFT_VERSION="4.18"
MONITOR_RUNNER=false

# Display help information
show_help() {
    echo "Usage: $0 [options]"
    echo ""
    echo "This script assists with testing GitHub Actions workflows."
    echo ""
    echo "Options:"
    echo "  -h, --help                 Show this help message"
    echo "  -b, --branch NAME          Set branch name for testing (default: ci-workflow-test)"
    echo "  -r, --remote NAME          Set remote name (default: origin)"
    echo "  --all                      Test all workflows"
    echo "  --unit                     Test unit test workflow"
    echo "  --component                Test component test workflow"
    echo "  --integration              Test integration test workflow"
    echo "  --iso                      Test ISO generation workflow"
    echo "  --server-ip IP             Set server IP for tests (default: 192.168.2.230)"
    echo "  --truenas-ip IP            Set TrueNAS IP for tests (default: 192.168.2.245)"
    echo "  --openshift-version VER    Set OpenShift version (default: 4.18)"
    echo "  --monitor                  Monitor self-hosted runner during tests"
    echo ""
    echo "Examples:"
    echo "  $0 --all                   Test all workflows"
    echo "  $0 --unit --component      Test only unit and component workflows"
    echo "  $0 --iso --openshift-version 4.17,4.18  Test ISO generation for multiple versions"
    echo ""
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -b|--branch)
            BRANCH_NAME="$2"
            shift
            ;;
        -r|--remote)
            REMOTE_NAME="$2"
            shift
            ;;
        --all)
            TEST_UNIT=true
            TEST_COMPONENT=true
            TEST_INTEGRATION=true
            TEST_ISO=true
            ;;
        --unit)
            TEST_UNIT=true
            ;;
        --component)
            TEST_COMPONENT=true
            ;;
        --integration)
            TEST_INTEGRATION=true
            ;;
        --iso)
            TEST_ISO=true
            ;;
        --server-ip)
            SERVER_IP="$2"
            shift
            ;;
        --truenas-ip)
            TRUENAS_IP="$2"
            shift
            ;;
        --openshift-version)
            OPENSHIFT_VERSION="$2"
            shift
            ;;
        --monitor)
            MONITOR_RUNNER=true
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
    shift
done

# Check if at least one workflow is selected
if [[ "$TEST_UNIT" == "false" && "$TEST_COMPONENT" == "false" && "$TEST_INTEGRATION" == "false" && "$TEST_ISO" == "false" ]]; then
    echo "Error: No workflows selected for testing"
    show_help
    exit 1
fi

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "GitHub CLI (gh) is not installed. It's required for workflow testing."
    echo "Install it from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated with GitHub
if ! gh auth status &> /dev/null; then
    echo "Not authenticated with GitHub. Please run 'gh auth login' first."
    exit 1
fi

# Create test branch
create_test_branch() {
    echo "Creating test branch: $BRANCH_NAME"
    
    # Check if branch exists and delete it if it does
    if git show-ref --verify --quiet refs/heads/$BRANCH_NAME; then
        echo "Branch $BRANCH_NAME already exists. Deleting it..."
        git branch -D $BRANCH_NAME
    fi
    
    # Create and checkout new branch
    git checkout -b $BRANCH_NAME
    
    # Create test changes based on selected workflows
    if [[ "$TEST_UNIT" == "true" ]]; then
        echo "# Test change for unit tests workflow" >> tests/unit/__init__.py
    fi
    
    if [[ "$TEST_COMPONENT" == "true" ]]; then
        echo "# Test change for component tests workflow" >> framework/components/__init__.py
    fi
    
    if [[ "$TEST_INTEGRATION" == "true" || "$TEST_ISO" == "true" ]]; then
        echo "# Test change for integration/ISO workflow" >> scripts/__init__.py
    fi
    
    # Commit changes
    git add .
    git commit -m "Test CI workflows with automated changes"
    
    # Push branch
    git push -f $REMOTE_NAME $BRANCH_NAME
    
    echo "Test branch created and pushed to $REMOTE_NAME/$BRANCH_NAME"
}

# Create pull request
create_pull_request() {
    echo "Creating pull request for testing CI workflows"
    PR_URL=$(gh pr create --base main --head $BRANCH_NAME --title "Test CI Workflows" --body "This PR is for testing GitHub Actions CI workflows.")
    echo "Pull request created: $PR_URL"
}

# Trigger workflows manually
trigger_workflows() {
    local REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
    
    if [[ "$TEST_UNIT" == "true" ]]; then
        echo "Triggering Unit Tests workflow"
        gh workflow run ci-unit-tests.yml -R "$REPO"
    fi
    
    if [[ "$TEST_COMPONENT" == "true" ]]; then
        echo "Triggering Component Tests workflow"
        gh workflow run ci-component-tests.yml -R "$REPO"
    fi
    
    if [[ "$TEST_INTEGRATION" == "true" ]]; then
        echo "Triggering Integration Tests workflow"
        gh workflow run ci-integration-tests.yml -R "$REPO" \
            -f server_ip="$SERVER_IP" \
            -f truenas_ip="$TRUENAS_IP" \
            -f test_components="truenas,iscsi,openshift,s3"
    fi
    
    if [[ "$TEST_ISO" == "true" ]]; then
        echo "Triggering ISO Generation workflow"
        gh workflow run ci-iso-generation.yml -R "$REPO" \
            -f versions="$OPENSHIFT_VERSION" \
            -f rendezvous_ip="$SERVER_IP" \
            -f truenas_ip="$TRUENAS_IP" \
            -f skip_upload="true"
    fi
}

# Monitor runner resources
monitor_runner() {
    if [[ "$MONITOR_RUNNER" != "true" ]]; then
        return
    fi
    
    echo "Monitoring runner resources (press Ctrl+C to stop)..."
    echo "Outputs will be saved to runner-monitoring.log"
    
    # Create monitoring log file
    echo "=== Runner Monitoring $(date) ===" > runner-monitoring.log
    
    while true; do
        echo "--- $(date) ---" >> runner-monitoring.log
        echo "CPU Usage:" >> runner-monitoring.log
        top -b -n 1 | grep "Cpu(s)" >> runner-monitoring.log
        
        echo "Memory Usage:" >> runner-monitoring.log
        free -h >> runner-monitoring.log
        
        # Add a blank line for readability
        echo "" >> runner-monitoring.log
        
        # Sleep for 5 seconds
        sleep 5
    done
}

# Analyze workflow results
analyze_results() {
    local REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
    
    echo "Fetching recent workflow runs..."
    gh run list -R "$REPO" -L 10
    
    echo ""
    echo "To view detailed results for a specific run:"
    echo "  gh run view <run-id> -R \"$REPO\""
    echo ""
    echo "To download artifacts from a specific run:"
    echo "  gh run download <run-id> -R \"$REPO\""
    echo ""
    echo "To view logs from a specific job:"
    echo "  gh run view <run-id> --log -R \"$REPO\""
}

# Main execution
echo "====================================="
echo "GitHub Actions Workflow Testing Tool"
echo "====================================="

echo "Testing workflows:"
[[ "$TEST_UNIT" == "true" ]] && echo "- Unit Tests"
[[ "$TEST_COMPONENT" == "true" ]] && echo "- Component Tests"
[[ "$TEST_INTEGRATION" == "true" ]] && echo "- Integration Tests"
[[ "$TEST_ISO" == "true" ]] && echo "- ISO Generation"
echo ""

read -p "Do you want to create a test branch and PR? (y/n): " CREATE_BRANCH_ANSWER
if [[ "$CREATE_BRANCH_ANSWER" == "y" || "$CREATE_BRANCH_ANSWER" == "Y" ]]; then
    create_test_branch
    
    read -p "Do you want to create a PR from this branch? (y/n): " CREATE_PR_ANSWER
    if [[ "$CREATE_PR_ANSWER" == "y" || "$CREATE_PR_ANSWER" == "Y" ]]; then
        create_pull_request
    fi
fi

read -p "Do you want to trigger workflows manually? (y/n): " TRIGGER_ANSWER
if [[ "$TRIGGER_ANSWER" == "y" || "$TRIGGER_ANSWER" == "Y" ]]; then
    trigger_workflows
fi

if [[ "$MONITOR_RUNNER" == "true" ]]; then
    read -p "Start monitoring self-hosted runner? (y/n): " MONITOR_ANSWER
    if [[ "$MONITOR_ANSWER" == "y" || "$MONITOR_ANSWER" == "Y" ]]; then
        monitor_runner
    fi
fi

read -p "Do you want to analyze recent workflow runs? (y/n): " ANALYZE_ANSWER
if [[ "$ANALYZE_ANSWER" == "y" || "$ANALYZE_ANSWER" == "Y" ]]; then
    analyze_results
fi

echo ""
echo "Testing complete. See the documentation at docs/CI_WORKFLOW_TESTING.md for more details."
echo ""
