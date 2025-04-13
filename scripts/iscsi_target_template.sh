#!/bin/bash
# iscsi_target_template.sh - Template for creating iSCSI targets on TrueNAS Scale
# This version uses jq to ensure proper JSON formatting
#
# Usage: ./iscsi_target_template.sh --server-id ID --hostname NAME [options]
# 
# Required:
#   --server-id ID         Server ID (e.g., 01, 02)
#   --hostname NAME        Server hostname
#
# Optional:
#   --openshift-version V  OpenShift version (default: stable)
#   --truenas-ip IP        TrueNAS IP (default: 192.168.2.245)
#   --zvol-size SIZE       Zvol size (default: 500G)
#   --zfs-pool POOL        ZFS pool name (default: test)
#   --ssh-key PATH         Path to SSH key
#   --dry-run              Don't execute, just show commands
#   --skip-zvol-check      Skip checking if zvol exists
#   --force                Force recreate zvol if it exists

set -e

# Default values
TRUENAS_IP="192.168.2.245"
OPENSHIFT_VERSION="stable"
ZVOL_SIZE="500G"
ZFS_POOL="test"
DRY_RUN=0
SKIP_ZVOL_CHECK=0
FORCE=0

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --server-id)
      SERVER_ID="$2"
      shift 2
      ;;
    --hostname)
      HOSTNAME="$2"
      shift 2
      ;;
    --openshift-version)
      OPENSHIFT_VERSION="$2"
      shift 2
      ;;
    --truenas-ip)
      TRUENAS_IP="$2"
      shift 2
      ;;
    --zvol-size)
      ZVOL_SIZE="$2"
      shift 2
      ;;
    --zfs-pool)
      ZFS_POOL="$2"
      shift 2
      ;;
    --ssh-key)
      SSH_KEY="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --skip-zvol-check)
      SKIP_ZVOL_CHECK=1
      shift
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --help|-h)
      echo "Usage: $0 --server-id ID --hostname NAME [options]"
      echo "Options:"
      echo "  --server-id ID         Server ID (e.g., 01, 02) (required)"
      echo "  --hostname NAME        Server hostname (required)"
      echo "  --openshift-version V  OpenShift version (default: stable)"
      echo "  --truenas-ip IP        TrueNAS IP (default: 192.168.2.245)"
      echo "  --zvol-size SIZE       Zvol size (default: 500G)"
      echo "  --zfs-pool POOL        ZFS pool name (default: test)"
      echo "  --ssh-key PATH         Path to SSH key"
      echo "  --dry-run              Don't execute, just show commands"
      echo "  --skip-zvol-check      Skip checking if zvol exists"
      echo "  --force                Force recreate zvol if it exists"
      echo "  --help, -h             Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Validate required arguments
if [ -z "$SERVER_ID" ] || [ -z "$HOSTNAME" ]; then
  echo "Error: --server-id and --hostname are required"
  exit 1
fi

# Format names
VERSION_FORMAT=$(echo $OPENSHIFT_VERSION | tr '.' '_')
ZVOL_NAME="${ZFS_POOL}/openshift_installations/r630_${SERVER_ID}_${VERSION_FORMAT}"
TARGET_NAME="iqn.2005-10.org.freenas.ctl:iscsi.r630-${SERVER_ID}.openshift${VERSION_FORMAT}"
EXTENT_NAME="openshift_r630_${SERVER_ID}_${VERSION_FORMAT}_extent"

# Auto-detect SSH key if not provided
if [ -z "$SSH_KEY" ]; then
  if [ -f "$HOME/.ssh/${TRUENAS_IP}.id_rsa" ]; then
    SSH_KEY="$HOME/.ssh/${TRUENAS_IP}.id_rsa"
  fi
fi

# Generate commands
echo "=== Creating iSCSI Target for ${HOSTNAME} (Server ID: ${SERVER_ID}) ==="
echo "OpenShift Version: ${OPENSHIFT_VERSION}"
echo "Zvol: ${ZVOL_NAME} (Size: ${ZVOL_SIZE})"
echo "Target: ${TARGET_NAME}"
echo "Extent: ${EXTENT_NAME}"
echo "============================================================"

# Create the remote shell script
cat > /tmp/create_iscsi_target_remote.sh << 'EOSCRIPT'
#!/bin/bash
set -e

# Args: zvol_name zvol_size target_name extent_name server_hostname skip_zvol_check force
ZVOL_NAME=$1
ZVOL_SIZE=$2
TARGET_NAME=$3
EXTENT_NAME=$4
HOSTNAME=$5
SKIP_ZVOL_CHECK=$6
FORCE=$7

# Function to check for errors and exit
fail() {
    echo "ERROR: $1" >&2
    exit 1
}

# Check iSCSI service (different name variations possible)
echo "Checking iSCSI service..."
if midclt call service.query '[["service","=","iscsitarget"]]' 2>/dev/null | grep -q '"state": "RUNNING"'; then
    echo "iSCSI service (iscsitarget) is running"
elif midclt call service.query '[["service","=","iscsi"]]' 2>/dev/null | grep -q '"state": "RUNNING"'; then
    echo "iSCSI service (iscsi) is running"
else
    echo "WARNING: iSCSI service does not appear to be running"
    echo "The service name might be different on this TrueNAS version"
    echo "Please manually ensure the iSCSI service is started"
    # We'll continue anyway and try to create the resources
fi

echo "Creating zvol ${ZVOL_NAME}..."
# Check if the zvol already exists
if [ "$SKIP_ZVOL_CHECK" != "1" ]; then
    if zfs list -t volume | grep -q "${ZVOL_NAME}"; then
        if [ "$FORCE" == "1" ]; then
            echo "ZVOL ${ZVOL_NAME} already exists - forcing recreation"
            zfs destroy -f "${ZVOL_NAME}" || fail "Failed to destroy existing zvol ${ZVOL_NAME}"
            zfs create -V ${ZVOL_SIZE} -s ${ZVOL_NAME} || fail "Failed to create zvol ${ZVOL_NAME}"
        else
            echo "ZVOL ${ZVOL_NAME} already exists - using existing zvol"
            # We continue to use the existing zvol
        fi
    else
        zfs create -V ${ZVOL_SIZE} -s ${ZVOL_NAME} || fail "Failed to create zvol ${ZVOL_NAME}"
    fi
else
    # Skip zvol check and just try to create it
    zfs create -V ${ZVOL_SIZE} -s ${ZVOL_NAME} || echo "Note: ZVOL creation failed, it may already exist - continuing anyway"
fi

echo "Creating target ${TARGET_NAME}..."
# Create target JSON directly (with proper concat format for TrueNAS middleware)
echo '{"name":"'${TARGET_NAME}'""alias":"OpenShift '${HOSTNAME}'""mode":"ISCSI""groups":[{"portal":1"initiator":1"auth":null}]}' > /tmp/target.json

echo "Target JSON: $(cat /tmp/target.json)"
TARGET_RESULT=$(midclt call iscsi.target.create - < /tmp/target.json)
echo "Target creation result: $TARGET_RESULT"
TARGET_ID=$(echo "$TARGET_RESULT" | jq '.id')

if [ -z "$TARGET_ID" ] || [ "$TARGET_ID" = "null" ]; then
    echo "WARNING: Failed to get target ID. Check if target already exists."
    # Try to find the target ID by name
    echo "Trying to find target by name..."
    TARGET_ID=$(midclt call iscsi.target.query "[['name','=','${TARGET_NAME}']]" | jq '.[0].id')
    if [ -z "$TARGET_ID" ] || [ "$TARGET_ID" = "null" ]; then
        fail "Failed to create or find target"
    else
        echo "Found existing target with ID: ${TARGET_ID}"
    fi
else
    echo "Target created with ID: ${TARGET_ID}"
fi

echo "Creating extent ${EXTENT_NAME}..."
# Create extent JSON directly (with proper concat format for TrueNAS middleware)
echo '{"name":"'${EXTENT_NAME}'""type":"DISK""disk":"zvol/'${ZVOL_NAME}'""blocksize":512"pblocksize":false"comment":"OpenShift '${HOSTNAME}' boot image""insecure_tpc":true"xen":false"rpm":"SSD""ro":false}' > /tmp/extent.json

echo "Extent JSON: $(cat /tmp/extent.json)"
EXTENT_RESULT=$(midclt call iscsi.extent.create - < /tmp/extent.json)
echo "Extent creation result: $EXTENT_RESULT"
EXTENT_ID=$(echo "$EXTENT_RESULT" | jq '.id')

if [ -z "$EXTENT_ID" ] || [ "$EXTENT_ID" = "null" ]; then
    echo "WARNING: Failed to get extent ID. Check if extent already exists."
    # Try to find the extent ID by name
    echo "Trying to find extent by name..."
    EXTENT_ID=$(midclt call iscsi.extent.query "[['name','=','${EXTENT_NAME}']]" | jq '.[0].id')
    if [ -z "$EXTENT_ID" ] || [ "$EXTENT_ID" = "null" ]; then
        fail "Failed to create or find extent"
    else
        echo "Found existing extent with ID: ${EXTENT_ID}"
    fi
else
    echo "Extent created with ID: ${EXTENT_ID}"
fi

echo "Associating extent with target..."
# Create target-extent association JSON directly
echo '{"target":'${TARGET_ID}'"extent":'${EXTENT_ID}'"lunid":0}' > /tmp/targetextent.json

echo "Target-Extent JSON: $(cat /tmp/targetextent.json)"
ASSOC_RESULT=$(midclt call iscsi.targetextent.create - < /tmp/targetextent.json)
echo "Association result: $ASSOC_RESULT"

# Clean up temp files
rm -f /tmp/target.json /tmp/extent.json /tmp/targetextent.json

echo "iSCSI target created successfully"
EOSCRIPT

chmod +x /tmp/create_iscsi_target_remote.sh

# Build SSH command
if [ -n "$SSH_KEY" ]; then
  SSH_CMD="ssh -i $SSH_KEY root@$TRUENAS_IP"
else
  SSH_CMD="ssh root@$TRUENAS_IP"
fi

# Execute or show dry run
if [ $DRY_RUN -eq 1 ]; then
  echo -e "\nDry run mode - commands that would be executed:"
  echo -e "------------------------------------------------------------"
  cat /tmp/create_iscsi_target_remote.sh
  echo -e "------------------------------------------------------------"
  echo -e "Arguments: ${ZVOL_NAME} ${ZVOL_SIZE} ${TARGET_NAME} ${EXTENT_NAME} ${HOSTNAME} ${SKIP_ZVOL_CHECK} ${FORCE}"
  echo -e "Command: ${SSH_CMD} 'bash -s' < /tmp/create_iscsi_target_remote.sh ${ZVOL_NAME} ${ZVOL_SIZE} ${TARGET_NAME} ${EXTENT_NAME} ${HOSTNAME} ${SKIP_ZVOL_CHECK} ${FORCE}"
  echo -e "------------------------------------------------------------"
  echo "No changes were made to TrueNAS."
else
  echo -e "\nExecuting commands on TrueNAS (${TRUENAS_IP})..."
  $SSH_CMD 'bash -s' < /tmp/create_iscsi_target_remote.sh "${ZVOL_NAME}" "${ZVOL_SIZE}" "${TARGET_NAME}" "${EXTENT_NAME}" "${HOSTNAME}" "${SKIP_ZVOL_CHECK}" "${FORCE}" || {
    echo -e "\nERROR: Command failed with exit code $?"
    echo "Check TrueNAS logs for more information."
    exit 1
  }
  echo -e "\nSuccess! iSCSI target created successfully."
fi

# Clean up temporary script
rm -f /tmp/create_iscsi_target_remote.sh
