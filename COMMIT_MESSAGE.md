feat(python312): Complete major components migration and update documentation

This commit finalizes the core components migration to Python 3.12 and updates
documentation to reflect the current state of the migration.

### Components
- Migrate all core components to Python 3.12:
  - BaseComponent
  - S3Component
  - VaultComponent
  - OpenShiftComponent
  - ISCSIComponent
  - R630Component

### Scripts
- Complete migration of 5 key scripts:
  - workflow_iso_generation_s3_py312.py
  - setup_minio_buckets_py312.py
  - test_iscsi_truenas_py312.py
  - generate_openshift_iso_py312.py
  - config_iscsi_boot_py312.py

### Testing
- Add comprehensive unit tests for all migrated scripts
- Set up Docker-based testing environment
- Create GitHub Actions workflow for Python 3.12

### Documentation
- Update PR_DESCRIPTION.md with current migration status
- Add Python 3.12 section to README.md with:
  - Migration status overview
  - Benefits and features
  - Usage examples for components and scripts
  - Testing instructions

### Python 3.12 Features
- Implement TypedDict for all data structures
- Add pattern matching for error handling
- Use dictionary merging with | operator
- Apply assignment expressions for cleaner code
- Leverage Path objects for improved file handling

Project remains on track for full completion by May 3, 2025, with all major
components and high-priority scripts already migrated.
