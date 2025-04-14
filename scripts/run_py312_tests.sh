#!/bin/bash
#
# Run Python 3.12 component tests in Docker container
#
# This script builds and runs a Docker container with Python 3.12
# to test the enhanced components.

set -e

# Set working directory to project root
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo "===> Building Python 3.12 Docker image..."
docker build -t r630-iscsi-switchbot-py312 -f Dockerfile.python312 .

echo "===> Running S3 Component Python 3.12 tests..."
docker run --rm \
  -v "$PROJECT_ROOT:/app" \
  -e S3_ENDPOINT \
  -e S3_ACCESS_KEY \
  -e S3_SECRET_KEY \
  r630-iscsi-switchbot-py312 \
  python scripts/test_s3_component_py312.py

echo "===> Running Vault Component Python 3.12 tests..."
docker run --rm \
  -v "$PROJECT_ROOT:/app" \
  -e VAULT_ADDR \
  -e VAULT_TOKEN \
  -e VAULT_MOUNT_POINT \
  -e VAULT_PATH_PREFIX \
  -e VAULT_SKIP_VERIFY \
  r630-iscsi-switchbot-py312 \
  python scripts/test_vault_component_py312.py

echo "===> Running OpenShift Component Python 3.12 tests..."
docker run --rm \
  -v "$PROJECT_ROOT:/app" \
  -e S3_ENDPOINT \
  -e S3_ACCESS_KEY \
  -e S3_SECRET_KEY \
  -e OPENSHIFT_VERSION \
  -e OPENSHIFT_REAL_RUN \
  -e KEEP_TEST_FILES \
  r630-iscsi-switchbot-py312 \
  python scripts/test_openshift_component_py312.py

echo "===> Running iSCSI Component Python 3.12 tests..."
docker run --rm \
  -v "$PROJECT_ROOT:/app" \
  -e TRUENAS_URL \
  -e TRUENAS_API_KEY \
  -e ISCSI_DRY_RUN=true \
  r630-iscsi-switchbot-py312 \
  python scripts/test_iscsi_component_py312.py

echo "===> Running R630 Component Python 3.12 tests..."
docker run --rm \
  -v "$PROJECT_ROOT:/app" \
  -e IDRAC_HOST \
  -e IDRAC_USERNAME \
  -e IDRAC_PASSWORD \
  -e SERVER_ID \
  -e DRY_RUN=true \
  r630-iscsi-switchbot-py312 \
  python scripts/test_r630_component_py312.py

echo "===> Running Workflow ISO Generation Python 3.12 tests..."
docker run --rm \
  -v "$PROJECT_ROOT:/app" \
  -e S3_ENDPOINT \
  -e S3_ACCESS_KEY \
  -e S3_SECRET_KEY \
  -e OPENSHIFT_VERSION \
  -e DRY_RUN=true \
  r630-iscsi-switchbot-py312 \
  python -m unittest tests/unit/scripts/test_workflow_iso_generation_s3_py312.py

echo "===> Running MinIO Bucket Setup Python 3.12 tests..."
docker run --rm \
  -v "$PROJECT_ROOT:/app" \
  -e S3_ENDPOINT \
  -e S3_ACCESS_KEY \
  -e S3_SECRET_KEY \
  -e DRY_RUN=true \
  r630-iscsi-switchbot-py312 \
  python -m unittest tests/unit/scripts/test_setup_minio_buckets_py312.py

echo "===> Running TrueNAS iSCSI Python 3.12 tests..."
docker run --rm \
  -v "$PROJECT_ROOT:/app" \
  -e TRUENAS_IP \
  -e TRUENAS_API_KEY \
  -e DRY_RUN=true \
  r630-iscsi-switchbot-py312 \
  python -m unittest tests/unit/scripts/test_test_iscsi_truenas_py312.py

echo "===> Running OpenShift ISO Generation Python 3.12 tests..."
docker run --rm \
  -v "$PROJECT_ROOT:/app" \
  -e OPENSHIFT_VERSION \
  -e OPENSHIFT_DOMAIN \
  -e TRUENAS_IP \
  -e DRY_RUN=true \
  r630-iscsi-switchbot-py312 \
  python -m unittest tests/unit/scripts/test_generate_openshift_iso_py312.py

echo "===> Running iSCSI Boot Configuration Python 3.12 tests..."
docker run --rm \
  -v "$PROJECT_ROOT:/app" \
  -e IDRAC_HOST \
  -e IDRAC_USERNAME \
  -e IDRAC_PASSWORD \
  -e TRUENAS_IP \
  -e TRUENAS_API_KEY \
  -e DRY_RUN=true \
  r630-iscsi-switchbot-py312 \
  python -m unittest tests/unit/scripts/test_config_iscsi_boot_py312.py

echo "===> All tests completed"
