# CI Workflow Testing Guide

This guide provides step-by-step instructions for testing and validating the CI workflows implemented for the r630-iscsi-switchbot project.

## Prerequisites

Before testing the workflows, ensure:

1. **Self-hosted Runner**: Is properly configured and running
2. **GitHub Secrets**: All required secrets are set up in your repository:
   - `OPENSHIFT_PULL_SECRET`
   - `TRUENAS_SSH_KEY`
   - `TRUENAS_KNOWN_HOSTS` (optional)
3. **Test Environment**: Access to test servers and TrueNAS instance

## 1. Manual Workflow Testing

### 1.1 Unit Tests Workflow

This workflow runs matrix testing across multiple Python versions and components.

1. Navigate to GitHub Actions in your repository
2. Select the "CI - Unit Tests" workflow
3. Click the "Run workflow" dropdown
4. Run with default parameters on the `main` branch
5. Observe the execution to verify:
   - Code quality checks execute without modifying code
   - Matrix jobs run for all Python versions (3.9, 3.10, 3.11)
   - Test summary is generated

**Expected artifacts:**
- Code quality reports
- Coverage reports for each Python version and test group

### 1.2 Component Tests Workflow

This workflow tests individual components with containerized services.

1. Navigate to GitHub Actions in your repository
2. Select the "CI - Component Tests" workflow
3. Click the "Run workflow" dropdown
4. Run with default parameters on the `main` branch
5. Observe the execution to verify:
   - Docker services start correctly (MinIO, Vault)
   - Parallel component tests run for all components
   - Integration check executes
   - Cleanup job runs even if tests fail

**Expected artifacts:**
- Component test reports for S3, Vault, iSCSI, and OpenShift components

### 1.3 Integration Tests Workflow

This workflow tests the integrated system on self-hosted runners.

1. Navigate to GitHub Actions in your repository
2. Select the "CI - Integration Tests" workflow
3. Click the "Run workflow" dropdown
4. Enter parameters:
   - Server IP: `192.168.2.230` (or your R630 test server)
   - TrueNAS IP: `192.168.2.245` (or your TrueNAS instance)
   - Test components: `truenas,iscsi,openshift,s3`
5. Run the workflow
6. Observe the execution to verify:
   - Environment validation checks connectivity
   - Parallel component testing executes properly
   - End-to-end workflow test runs
   - Summary is generated

**Expected artifacts:**
- Integration test reports for each component
- End-to-end test report
- Integration test summary

### 1.4 ISO Generation Workflow

This workflow builds OpenShift ISOs in parallel.

1. Navigate to GitHub Actions in your repository
2. Select the "CI - ISO Generation" workflow
3. Click the "Run workflow" dropdown
4. Enter parameters:
   - Versions: `4.18` (single) or `4.17,4.18` (multiple)
   - Rendezvous IP: `192.168.2.230` (or your test server)
   - TrueNAS IP: `192.168.2.245` (or your storage server)
   - Skip upload: `true` (for initial testing)
5. Run the workflow
6. Observe the execution to verify:
   - Input validation works correctly
   - ISO generation runs in parallel for each version
   - Artifacts are uploaded to GitHub
   - Summary is generated

**Expected artifacts:**
- OpenShift ISO for each version specified
- ISO generation summary

## 2. PR-Triggered Workflow Testing

Test automatic triggering of workflows by creating a test PR:

```bash
# Create a new branch
git checkout -b ci-workflow-test

# Make test changes to trigger different workflows
echo "# Test comment for CI workflows" >> scripts/__init__.py
echo "# Test comment for CI workflows" >> framework/__init__.py

# Commit and push
git add .
git commit -m "Test CI workflows with minor changes"
git push origin ci-workflow-test
```

Now create a PR on GitHub from `ci-workflow-test` to `main` and observe:

1. Which workflows trigger automatically
2. PR checks appear correctly in GitHub UI
3. Workflow results are properly linked to the PR

## 3. Performance Monitoring

During workflow execution, monitor your self-hosted runner for:

1. **CPU Usage**: Check if parallelization is effective or causing contention
   ```bash
   top -b -n 1 | grep "Cpu(s)"
   ```

2. **Memory Consumption**: Verify if runner has sufficient memory
   ```bash
   free -h
   ```

3. **Disk I/O**: Especially important during ISO generation
   ```bash
   iostat -x 5
   ```

4. **Network Traffic**: Important for artifact uploads and downloads
   ```bash
   iftop -i <interface>
   ```

Record these metrics to determine if adjustments are needed:
- Optimal `max-parallel` settings
- Timeout values
- Memory or disk requirements

## 4. Testing Output Analysis

After workflows complete, analyze:

1. **Execution Time**: Check total duration and time for each job
2. **Job Dependencies**: Verify jobs execute in the correct order
3. **Artifacts**: Download and verify all artifacts are complete
4. **Error Handling**: Intentionally cause a job to fail to verify error reporting
5. **Resource Usage**: Compare observed resource usage with expected values

## 5. Workflow Adjustments

Based on testing results, consider these potential adjustments:

- **Parallelization**: Increase/decrease `max-parallel` based on runner performance
- **Timeouts**: Adjust timeout values for long-running jobs
- **Dependencies**: Refine job dependencies for optimal execution
- **Error Handling**: Add better error handling for specific conditions
- **Artifact Retention**: Adjust retention period for artifacts

## 6. Documentation Updates

After testing, document:

1. Any issues encountered and their solutions
2. Performance characteristics (resource usage, execution time)
3. Recommended settings for different environments
4. Common error messages and troubleshooting steps

Add these findings to the `docs/GITHUB_ACTIONS_USAGE.md` file to help others work with the CI system.

## Conclusion

After completing this testing process, you should have validated all CI workflows and gained insights into their performance characteristics. This knowledge will help you make informed decisions about how to optimize the CI system for your specific needs.
