
# integrate this with what we learned from identifien the device from truenas scale

To integrate the process of identifying iSCSI devices from TrueNAS Scale with a Single Node OpenShift (SNO) agent-based installation, follow these steps to ensure reliable identification and configuration of the root disk. This approach combines persistent disk identification methods and TrueNAS Scale iSCSI setup principles.

---

## **Steps to Configure iSCSI Disk for SNO Installation**

### **1. Configure iSCSI on TrueNAS Scale**

Set up an iSCSI target and extent on TrueNAS Scale to serve as the boot disk for your SNO installation:

1. **Create a ZFS Dataset or Zvol**:
    - If using ZFS, create a dedicated dataset for the root disk.
    - For block storage, create a Zvol under your dataset (ensure it is correctly configured as an extent).
2. **Set Up iSCSI Block Share**:
    - Use the TrueNAS Scale wizard or manual configuration:
        - **Extent Type**: Select "Device" if using a full disk or Zvol.
        - **Target IQN**: Create a unique IQN (e.g., `iqn.2025-04.com.example:boot-disk`).
        - **Portal Configuration**: Add the IP address of your TrueNAS server.
3. **Record Persistent Identifiers**:
    - Note the LUN ID, IQN, and portal IP address for use in Red Hat-based systems.

---

### **2. Discover and Identify the iSCSI Disk on Red Hat Systems**

After configuring TrueNAS Scale, discover the iSCSI device on your Red Hat system using persistent attributes:

1. **Login to the iSCSI Target**:
Use `iscsiadm` to discover and log in to the target:

```bash
iscsiadm -m discovery -t sendtargets -p &lt;TrueNAS_IP&gt;
iscsiadm -m node --login
```

2. **Verify Disk Mapping**:
Check which local block device corresponds to the iSCSI LUN:

```bash
lsblk
iscsiadm --mode session -P 3
```

This will display detailed mappings, including LUNs and their associated local devices (e.g., `/dev/sda`).
3. **Retrieve Persistent Attributes**:
Use `lsblk` or `udevadm` to gather persistent identifiers like WWN, serial number, or model:

```bash
lsblk -o NAME,WWN,MODEL,SERIAL
udevadm info --query=all --name=/dev/sda | grep ID_
```


---

### **3. Configure Agent-Based Installation with Persistent Disk Hints**

Update your SNO agent configuration (`agent-config.yaml`) to ensure the installer uses the correct disk:

#### Example Configuration:

```yaml
hosts:
  - hostname: master-0
    rootDeviceHints:
      wwn: "0x50014ee2bae7ffa5"  # Replace with actual WWN
      serialNumber: "BTHV507002P71P6GN"  # Replace with actual serial number
```


#### Steps:

1. Replace `/dev/sda` with persistent identifiers like WWN or serial number.
2. Validate that these identifiers match the iSCSI device discovered earlier.

---

### **4. Integrate Automation Scripts**

In your automation scripts for creating volumes on TrueNAS Scale and configuring SNO installations:

1. **Automate Volume Creation**:
Use TrueNAS APIs or CLI commands to create Zvols and configure iSCSI shares dynamically.
2. **Automate Disk Discovery on Red Hat Systems**:
Run `iscsiadm` commands in your script to discover targets and retrieve persistent attributes automatically.
3. **Update Agent Configuration Dynamically**:
Parse output from `lsblk` or `udevadm` to populate `rootDeviceHints` in `agent-config.yaml`.

---

### **5. Verify Installation**

After configuring the agent-based installation:

1. Check that the installer uses the correct disk by inspecting logs for errors like `WARNING BootstrapInPlace.InstallationDisk: /dev/sda is ignored`.
2. Validate that `/dev/disk/by-path/` or `/dev/disk/by-uuid/` points to the correct iSCSI device.

---

## **Best Practices**

1. Use persistent identifiers (WWN, serial number) instead of transient names like `/dev/sda`.
2. Ensure LUN IDs are unique across targets in TrueNAS Scale.
3. Regularly test automation scripts in isolated environments before deploying them in production.

By combining persistent disk identification methods with robust TrueNAS Scale configurations, you can reliably integrate SAN boot processes into your SNO installations without encountering device mapping issues.

<div>⁂</div>

[^1]: https://forum.proxmox.com/threads/proxmox-ve-and-zfs-over-iscsi-on-truenas-scale-my-steps-to-make-it-work.125387/

[^2]: https://www.reddit.com/r/truenas/comments/pqk4b3/corescale_as_iscsi_initiator/

[^3]: https://www.truenas.com/community/threads/adding-an-external-iscsi-share-to-truenas-scale.108988/

[^4]: https://www.reddit.com/r/homelab/comments/uiwqdn/what_am_i_missing_iscsi_between_truenas_scale_and/

[^5]: https://www.truenas.com/docs/scale/scaletutorials/shares/iscsi/addingiscsishares/

[^6]: https://www.truenas.com/community/threads/truenas-scale-22-iscsi-device-extend-not-show-device.104740/

[^7]: https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html/managing_storage_devices/configuring-an-iscsi-initiator_managing-storage-devices

[^8]: https://jonathangazeley.com/2021/01/05/using-truenas-to-provide-persistent-storage-for-kubernetes/

