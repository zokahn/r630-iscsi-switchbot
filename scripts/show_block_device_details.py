#!/usr/bin/python3
#
# show_block_device_details.py - Show detailed information about block devices on CentOS Stream 9
#

import argparse
import json
import subprocess
import sys
import os
import re
from pathlib import Path
from datetime import datetime

def parse_arguments():
    parser = argparse.ArgumentParser(description="Show detailed information about block devices on CentOS Stream 9")
    parser.add_argument("--json", help="Output in JSON format", action="store_true", default=False)
    parser.add_argument("--device", help="Only show information for specific device (e.g., sda)", default=None)
    parser.add_argument("--type", help="Filter by device type (raid, iscsi, usb, all)", 
                        choices=["raid", "iscsi", "usb", "all"], default="all")
    return parser.parse_args()

def execute_command(command, ignore_errors=False):
    """
    Execute a shell command and return the result
    """
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if not ignore_errors and result.returncode != 0:
            print(f"Error executing command: {command}")
            print(f"STDERR: {result.stderr}")
            return None
        return result.stdout.strip()
    except Exception as e:
        print(f"Exception executing command: {e}")
        return None

def ensure_dependencies():
    """
    Ensure required packages are installed
    """
    dependencies = ["sg3_utils", "lsscsi", "util-linux", "hdparm"]
    missing = []
    
    for dep in dependencies:
        if execute_command(f"rpm -q {dep}", ignore_errors=True) is None:
            missing.append(dep)
    
    if missing:
        print(f"Installing required dependencies: {', '.join(missing)}")
        execute_command(f"dnf install -y {' '.join(missing)}")

def get_block_devices():
    """
    Get list of all block devices
    """
    lsblk_output = execute_command("lsblk -o NAME,TYPE,SIZE,VENDOR,MODEL,SERIAL,TRAN,HCTL,MOUNTPOINT -J")
    if not lsblk_output:
        return []
    
    try:
        lsblk_data = json.loads(lsblk_output)
        return lsblk_data.get("blockdevices", [])
    except json.JSONDecodeError:
        print("Error parsing lsblk output")
        return []

def get_scsi_info():
    """
    Get SCSI information for devices
    """
    lsscsi_output = execute_command("lsscsi -g", ignore_errors=True)
    if not lsscsi_output:
        return {}
    
    scsi_info = {}
    for line in lsscsi_output.split('\n'):
        if line.strip():
            parts = line.strip().split()
            if len(parts) >= 3:
                device = parts[-2]
                if device.startswith('/dev/'):
                    device = device.replace('/dev/', '')
                    scsi_info[device] = {
                        'hctl': parts[0].strip('[]'),
                        'type': parts[1],
                        'vendor': parts[2],
                        'model': ' '.join(parts[3:-2]) if len(parts) > 4 else '',
                    }
    
    return scsi_info

def get_device_type(device, scsi_info):
    """
    Determine if device is from RAID controller, iSCSI, USB, etc.
    """
    # Get udev info
    udev_output = execute_command(f"udevadm info --query=property --name=/dev/{device}")
    if not udev_output:
        return "unknown"
    
    # Extract information from udev output
    udev_info = {}
    for line in udev_output.split('\n'):
        if '=' in line:
            key, value = line.split('=', 1)
            udev_info[key.strip()] = value.strip()
    
    # Check for USB devices
    if "usb" in udev_info.get("ID_BUS", "").lower():
        return "usb"
    
    # Check for iSCSI devices
    if "iscsi" in udev_info.get("ID_PATH", "").lower() or "iscsi" in udev_info.get("ID_MODEL", "").lower():
        return "iscsi"
    
    # Check for devices behind RAID controllers
    if device in scsi_info:
        vendor = scsi_info[device].get('vendor', '').lower()
        model = scsi_info[device].get('model', '').lower()
        
        # Check for common RAID controller vendors
        raid_vendors = ["lsi", "megaraid", "perc", "dell", "adaptec", "hp", "3ware"]
        if any(v in vendor or v in model for v in raid_vendors):
            return "raid"
    
    # Additional tests for RAID devices
    sg_inq_output = execute_command(f"sg_inq /dev/{device}", ignore_errors=True)
    if sg_inq_output and any(r in sg_inq_output.lower() for r in ["raid", "lsi", "megaraid", "perc", "dell perc"]):
        return "raid"
    
    # Check device-mapper and multipath
    if device.startswith("dm-"):
        dm_info = execute_command(f"dmsetup info /dev/{device}", ignore_errors=True)
        if dm_info and "multipath" in dm_info:
            return "multipath"
    
    # Additional checks for iSCSI
    if "iscsi" in execute_command(f"ls -la /sys/block/{device}/device/", ignore_errors=True) or \
       "iscsi" in execute_command(f"dmesg | grep {device} | grep -i iscsi", ignore_errors=True):
        return "iscsi"
    
    # Look at transport type
    transport = execute_command(f"lsblk -no TRAN /dev/{device}", ignore_errors=True)
    if transport:
        if transport == "sata" or transport == "ata":
            return "sata"
        elif transport == "sas":
            return "sas"
        elif transport == "nvme":
            return "nvme"
        elif transport == "usb":
            return "usb"
        elif transport == "fc":
            return "fibre_channel"
    
    # Check for virtual devices
    if device.startswith("vd"):
        return "virtual"
    
    # Use SCSI type as fallback
    if device in scsi_info:
        scsi_type = scsi_info[device].get('type', '').lower()
        if "disk" in scsi_type:
            if "raid" in udev_info.get("ID_MODEL", "").lower():
                return "raid"
            return "disk"
    
    return "unknown"

def get_detailed_device_info(device, device_type, scsi_info):
    """
    Get detailed information for a specific device
    """
    info = {
        "name": device,
        "type": device_type,
        "details": {}
    }
    
    # Get basic information from lsblk
    lsblk_output = execute_command(f"lsblk -o NAME,TYPE,SIZE,VENDOR,MODEL,SERIAL,TRAN,HCTL,MOUNTPOINT -J /dev/{device}")
    if lsblk_output:
        try:
            lsblk_data = json.loads(lsblk_output)
            if "blockdevices" in lsblk_data and lsblk_data["blockdevices"]:
                device_info = lsblk_data["blockdevices"][0]
                info["details"].update({
                    "size": device_info.get("size", ""),
                    "vendor": device_info.get("vendor", ""),
                    "model": device_info.get("model", ""),
                    "serial": device_info.get("serial", ""),
                    "transport": device_info.get("tran", ""),
                    "hctl": device_info.get("hctl", ""),
                    "mountpoint": device_info.get("mountpoint", ""),
                })
        except json.JSONDecodeError:
            pass
    
    # Add SCSI information if available
    if device in scsi_info:
        info["details"]["scsi"] = scsi_info[device]
    
    # Get SMART information if available
    smartctl_output = execute_command(f"smartctl -i /dev/{device}", ignore_errors=True)
    if smartctl_output:
        smart_info = {}
        for line in smartctl_output.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                smart_info[key.strip()] = value.strip()
        
        if smart_info:
            info["details"]["smart"] = {
                "device_model": smart_info.get("Device Model", ""),
                "serial_number": smart_info.get("Serial Number", ""),
                "firmware_version": smart_info.get("Firmware Version", ""),
                "capacity": smart_info.get("User Capacity", ""),
                "rotation_rate": smart_info.get("Rotation Rate", ""),
                "form_factor": smart_info.get("Form Factor", ""),
                "sata_version": smart_info.get("SATA Version is", ""),
            }
    
    # Additional information for iSCSI devices
    if device_type == "iscsi":
        # Get session information
        session_info = execute_command(f"ls -la /sys/block/{device}/device/", ignore_errors=True)
        if session_info:
            info["details"]["iscsi_session"] = session_info
        
        # Get target information
        target_info = execute_command("iscsiadm -m session -P 3", ignore_errors=True)
        if target_info:
            info["details"]["iscsi_target"] = target_info
    
    # Additional information for RAID devices
    if device_type == "raid":
        # Check MegaRAID information if available
        megacli_output = execute_command("megacli -LDInfo -Lall -aAll", ignore_errors=True)
        if megacli_output:
            info["details"]["megacli"] = megacli_output
        
        # Check for storcli information
        storcli_output = execute_command("storcli /c0 /vall show", ignore_errors=True)
        if storcli_output:
            info["details"]["storcli"] = storcli_output
    
    # Additional information for USB devices
    if device_type == "usb":
        usb_info = execute_command(f"lsusb | grep -i storage", ignore_errors=True)
        if usb_info:
            info["details"]["usb"] = usb_info
    
    # Add partitions
    fdisk_output = execute_command(f"fdisk -l /dev/{device}", ignore_errors=True)
    if fdisk_output:
        partitions = []
        for line in fdisk_output.split('\n'):
            if f"/dev/{device}" in line and "sectors" not in line:
                partitions.append(line.strip())
        
        if partitions:
            info["details"]["partitions"] = partitions
    
    # Get additional WWN/WWID information if available
    wwn_output = execute_command(f"ls -la /sys/block/{device}/device/wwid 2>/dev/null", ignore_errors=True)
    if wwn_output:
        wwid = execute_command(f"cat /sys/block/{device}/device/wwid 2>/dev/null", ignore_errors=True)
        if wwid:
            info["details"]["wwid"] = wwid
    
    return info

def main():
    args = parse_arguments()
    
    # Ensure dependencies are installed
    ensure_dependencies()
    
    # Get all block devices
    devices = get_block_devices()
    if not devices:
        print("No block devices found.")
        sys.exit(1)
    
    # Get SCSI information
    scsi_info = get_scsi_info()
    
    # Filter and get detailed information for each device
    detailed_devices = []
    
    print("Analyzing block devices...\n")
    
    for device_info in devices:
        device_name = device_info.get("name", "")
        
        # Skip if not a disk or if specific device is requested and this isn't it
        if device_info.get("type") != "disk" or (args.device and device_name != args.device):
            continue
        
        # Determine device type
        device_type = get_device_type(device_name, scsi_info)
        
        # Skip if filtering by type and this isn't the requested type
        if args.type != "all" and device_type != args.type:
            continue
        
        # Get detailed information for this device
        detailed_info = get_detailed_device_info(device_name, device_type, scsi_info)
        detailed_devices.append(detailed_info)
    
    # Output results
    if args.json:
        print(json.dumps(detailed_devices, indent=2))
    else:
        if not detailed_devices:
            print("No matching devices found.")
            sys.exit(0)
        
        # Print header
        print(f"{'Device':<8} {'Type':<12} {'Size':<10} {'Model':<30} {'Serial':<20} {'Transport':<10}")
        print("-" * 90)
        
        # Print device summary
        for device in detailed_devices:
            details = device["details"]
            print(f"{device['name']:<8} {device['type']:<12} {details.get('size', ''):<10} "
                  f"{details.get('model', ''):<30} {details.get('serial', ''):<20} "
                  f"{details.get('transport', ''):<10}")
        
        # Print detailed information for each device
        for device in detailed_devices:
            print(f"\n{'='*90}")
            print(f"Detailed information for {device['name']} ({device['type']})")
            print(f"{'='*90}")
            
            details = device["details"]
            
            print(f"Vendor:     {details.get('vendor', 'N/A')}")
            print(f"Model:      {details.get('model', 'N/A')}")
            print(f"Size:       {details.get('size', 'N/A')}")
            print(f"Serial:     {details.get('serial', 'N/A')}")
            print(f"Transport:  {details.get('transport', 'N/A')}")
            print(f"HCTL:       {details.get('hctl', 'N/A')}")
            
            if 'wwid' in details:
                print(f"WWID:       {details['wwid']}")
            
            if 'mountpoint' in details and details['mountpoint']:
                print(f"Mountpoint: {details['mountpoint']}")
            
            # Additional information based on device type
            if device["type"] == "iscsi":
                print("\niSCSI Details:")
                print("-" * 40)
                if 'iscsi_target' in details:
                    print(details['iscsi_target'])
            
            elif device["type"] == "raid":
                print("\nRAID Details:")
                print("-" * 40)
                if 'megacli' in details:
                    print("MegaRAID Information Available")
                if 'storcli' in details:
                    print("StorCLI Information Available")
            
            elif device["type"] == "usb":
                print("\nUSB Details:")
                print("-" * 40)
                if 'usb' in details:
                    print(details['usb'])
            
            # Show partitions if available
            if 'partitions' in details and details['partitions']:
                print("\nPartitions:")
                print("-" * 40)
                for partition in details['partitions']:
                    print(partition)

if __name__ == "__main__":
    main()
